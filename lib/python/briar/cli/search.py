import asyncio
import briar
import briar.briar_client as briar_client
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as srvc_pb2
import briar.grpc_json as grpc_json
import cv2
import numpy as np
import optparse
import os
import pyvision as pv
import sys
import time
from briar import media_converters
from briar import timing
from briar.cli.connection import addConnectionOptions
from briar.cli.detect import addDetectorOptions, DETECTION_FILE_EXT, detect_options2proto, save_detections
from briar.cli.extract import addExtractOptions, TEMPLATE_FILE_EXT, extract_options2proto, save_extractions
from briar.cli.media import addMediaOptions, collect_files
from briar.cli.track import save_tracklets
from briar.media import BriarProgress, file_iter
from briar.media_converters import image_cv2proto, pathmap_str2dict, pathmap_path2remotepath
from matplotlib.cbook import get_sample_data
from matplotlib.offsetbox import (TextArea, DrawingArea, OffsetImage,
                                  AnnotationBbox)
from matplotlib.patches import Circle
from google.protobuf.json_format import MessageToJson
from briar.media import is_streaming_url
MATCHES_FILE_EXT = '.matches'


def addSearchOptions(parser):
    """!
    Add options for search of a database.

    This function adds a group of search-related options to the provided optparse.OptionParser instance.
    These options allow the user to configure various aspects of the search process, such as the database to use,
    the output type, and whether to return media.

    @param parser optparse.OptionParser: A parser to modify in place by adding options.
    """
    search_group = optparse.OptionGroup(parser, "Search Options",
                                        "Configuration for database search.")

    search_group.add_option("-o", "--out-dir", type="str", dest="out_dir", default=None,
                            help="Save the search results.")

    search_group.add_option("--output-type", type="choice", choices=['pickle', 'briar', 'numpy', 'pandas', 'xml'],
                            dest="output_type",
                            default="briar",
                            help="Choose an output type for saving results. Default=briar")

    search_group.add_option("-m", "--modality", type="choice",
                            choices=['unspecified', 'whole_body', 'face', 'gait', 'all'], dest="modality",
                            default="all",
                            help="Choose a biometric modality to detect/extract/enroll. Default=all")

    search_group.add_option("--database", type="str", dest="search_database", default='default',
                            help="Select the database to search.")

    search_group.add_option("--max-results", type="int", dest="max_results", default=-1,
                            help="Set the maximum number of search results returned for each face.")

    search_group.add_option("-d", "--use-detections", action="store_true", dest="use_detections", default=False,
                            help="Use saved detections to perform the extract. Default=False")

    search_group.add_option("-t", "--use-templates", action="store_true", dest="use_templates", default=False,
                            help="Use saved templates to perform the extract. Default=False")

    search_group.add_option("-w", "--enroll-whole-image", action="store_true", dest="whole_image", default=False,
                            help="Do not run autodetect or use existing detections and generate a template from the whole image.")

    search_group.add_option("--return-media", action="store_true", dest="return_media", default=False,
                            help="Enables returning of media from workers to the client - will significantly increase output file sizes!")

    parser.add_option_group(search_group)


def search_options2proto(options):
    """!
    Convert command line options to a protobuf object for gRPC.

    This function takes the parsed command line options and populates a SearchOptions protobuf object
    with the corresponding values. This object is then used to configure the search process in the gRPC request.

    @param options optparse.Values: Parsed command line options.
    @return: A SearchOptions protobuf object populated with the command line options.
    """
    search_options = briar_pb2.SearchOptions()

    val = options.out_dir
    if val is not None:
        search_options.out_dir.value = options.out_dir

    val = options.output_type
    if val is not None:
        search_options.output_type.value = options.output_type

    val = options.search_database
    if val is not None:
        search_options.search_database.value = options.search_database

    val = options.modality
    if val is not None:
        val = media_converters.modality_string2proto(val)
        search_options.modality = val

    val = options.max_results
    if val is not None:
        search_options.max_results.value = val

    search_options.use_detections.value = options.use_detections
    search_options.use_templates.value = options.use_templates

    if options.use_detections:
        search_options.flag = briar_pb2.SEARCH_PROVIDED_DETECTIONS
    elif options.use_templates:
        search_options.flag = briar_pb2.SEARCH_PROVIDED_TEMPLATES
    elif options.whole_image:
        search_options.flag = briar_pb2.SEARCH_FULL_IMAGE
    else:
        search_options.flag = briar_pb2.SEARCH_AUTO_DETECTION

    val = options.return_media
    if val is not None:
        search_options.return_media.value = val

    return search_options


def searchParseOptions(inputCommand=None):
    """!
    Generate options for running searches and parse command line arguments into them.

    This function sets up an optparse.OptionParser instance with various options for running searches,
    including connection options, detector options, extract options, search options, and media options. It then parses
    the command line arguments into these options.

    @param inputCommand str: A string containing the command line input to parse. If None, the function will parse sys.argv.
    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively.
    """
    args = ['[image] [image_directory] [video] [...]']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = "Run a 1:N search against a database. Input a probe entry" + \
                  " and finds the top matches in a gallery database."
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s search [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog, conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

    parser.add_option("--notrack", action="store_true", dest="track", default=False,
                      help="Set this flag to disable tracking of detections and perform just frame-wise detections")
    parser.add_option("--no-save", action="store_true", dest="no_save", default=False,
                      help="Disables saving of results on the client-side")
    parser.add_option("--plot", action="store_true", dest="plot", default=False,
                      help="Plots the score matrix")
    addSearchOptions(parser)
    addDetectorOptions(parser)
    addExtractOptions(parser)
    addConnectionOptions(parser)
    addMediaOptions(parser)

    # Parse the arguments and return the results.
    if inputCommand is not None:
        import shlex
        inp = shlex.split(inputCommand)
        (options, args) = parser.parse_args(inp)
    else:
        (options, args) = parser.parse_args()

    if len(args) < 2:
        parser.print_help()
        print("\nError: Please supply at least one directory, image, or video, or --probe-database flag\n")
        exit(-1)

    return options, args


def search(options=None, args=None, input_command=None, ret=False):
    """!
    Using the options specified in the command line, runs a search within the specified database using specified
    probe template(s). Writes results to disk to a location specified by the cmd arguments.

    This function initializes a BriarClient, sets up the search options, and processes the specified media files.
    It runs the search process on each file, saves the results, and optionally returns the results.

    @param options optparse.Values: Parsed command line options.
    @param args list: List of command line arguments.
    @param input_command str: A string containing the command line input to parse. If None, the function will parse sys.argv.
    @param ret bool: If True, the function will return the search results. Otherwise, it writes results to disk.
    @return: If ret is True, yields briar_service_pb2.SearchReply containing results.
    """
    api_start = time.time()

    if options is None and args is None:
        options, args = searchParseOptions(input_command)
    client = briar_client.BriarClient(options)

    detect_options = detect_options2proto(options)
    extract_options = extract_options2proto(options)
    search_options = search_options2proto(options)

    extract_options.modality = detect_options.modality
    search_options.modality = detect_options.modality

    if options.verbose:
        print("Scanning directories for images and videos.")
    image_list = None
    video_list = None
    if options.search_database:
        image_list, video_list = collect_files(args[1:], options)
        database = options.search_database
    else:
        image_list, video_list = collect_files(args[2:], options)
        database = args[1]

    media_list = None
    if image_list is not None and video_list is not None:
        media_list = image_list + video_list

    if options.verbose:
        if media_list is not None:
            print("Searching {} media files in {} database.".format(len(media_list), database))
        elif options.probe_database is not None:
            print("Searching {} probe database against {} database.".format(options.probe_database, database))

    image_count = 0
    batch_start_time = api_end = time.time()  # api_end-api_start = total time API took to find files and initialize
    for filename in media_list:
        request_start = time.time()
        iterator_chunck_num = 0
        # run auto-detection on provided files, extract the detections, and enroll the results
        for it in file_iter([filename], options, options_dict={"detect_options": detect_options, "extract_options": extract_options,
                                                          "search_options": search_options}, database_name=database,
                       request_start=request_start, requestConstructor=searchRequestConstructor):
            
            searchReplies = client.search(it)
            pbar = BriarProgress(options, name='Searching')
            perfile_durations = []
            # for f in it:
            #     print('fake processing2')
            for i, searchReply in enumerate(searchReplies):
                if options.max_frames > 0 and i >= options.max_frames:
                    break

                length = searchReply.progress.totalSteps
                pbar.update(current=searchReply.progress.currentStep, total=length)
                if not searchReply.progress_only_reply:
                    templates = searchReply.extract_reply.templates
                    detections = searchReply.extract_reply.detect_reply
                    tracklets = searchReply.extract_reply.track_reply.tracklets
                    if not options.no_save:
                        save_detections(filename, detections, options, i, modality=options.modality)
                        save_tracklets(filename, tracklets, options, i, modality=options.modality)
                        save_extractions(filename, templates, options, i, modality=options.modality)
                    if options.verbose:
                        print('similarities:')
                        print(searchReply.similarities)
                    searchReply.durations.total_duration.end = time.time()
                    if options.verbose and not options.progress:
                        print('searched 1 image in ', timing.timeElapsed(searchReply.durations.total_duration), ' seconds')
                    out_dir = options.out_dir
                    if not options.out_dir:
                        if is_streaming_url(filename):
                            name,ext = os.path.splitext(os.path.basename(filename))
                            url_to_filename = name+"_"+str(iterator_chunck_num).zfill(5)+ext + MATCHES_FILE_EXT
                            out_dir = "./streams"
                            os.makedirs(out_dir, exist_ok=True)
                            matches_path = os.path.join(out_dir, url_to_filename)
                        else:
                            out_dir = os.path.dirname(filename)
                            if options.chop_frames > 0:
                                matches_name = os.path.splitext(os.path.basename(filename))[0]+ "_"+str(iterator_chunck_num).zfill(5) + MATCHES_FILE_EXT
                            else:
                                matches_name = os.path.splitext(os.path.basename(filename))[0] + MATCHES_FILE_EXT
                            matches_path = os.path.join(out_dir, matches_name)
                    perfile_durations.append(searchReply.durations)
                    if options.verbose:
                        print('Saving the final search matches to', matches_path)
                    
                    grpc_json.save(searchReply, matches_path)
                    if ret:
                        yield searchReply
            if options.save_durations:
                timing.save_durations(filename, perfile_durations, options, "search")
            iterator_chunck_num +=1 
            # print('stream cycle', iterator_chunck_num)
            if iterator_chunck_num >= options.max_stream_cycles and options.max_stream_cycles > 0:
                print('done with streaming, reached max_stream_cycles')
                break
        image_count += 1
        if options.max_images is not None and image_count >= options.max_images:
            break


def searchRequestConstructor(media: briar_pb2.BriarMedia, durations: briar_pb2.BriarDurations, options_dict={},
                             det_list_list=None, database_name: str = None):
    """!
    Construct a SearchRequest for the gRPC call.

    This function constructs a SearchRequest protobuf object for the gRPC call. It populates the request
    with the media, durations, search options, and other relevant information.

    @param media briar_pb2.BriarMedia: The media to process.
    @param durations briar_pb2.BriarDurations: The durations object to log timing information.
    @param options_dict dict: A dictionary of options for configuring the search process.
    @param det_list_list list: A list of detection lists.
    @param database_name str: The name of the database to use.
    @return: A SearchRequest protobuf object populated with the relevant information.
    """
    durations.client_duration_frame_level.start = time.time()
    detect_options = options_dict['detect_options']
    extract_options = options_dict['extract_options']
    search_options = options_dict['search_options']
    database = None
    if database_name is not None:
        database = briar_pb2.BriarDatabase(name=database_name)
    req = srvc_pb2.SearchRequest(media=media,
                                 database=database,
                                 detect_options=detect_options,
                                 extract_options=extract_options,
                                 durations=durations,
                                 search_options=search_options)

    if media.source_type == briar_pb2.BriarMedia.DataType.GENERIC_IMAGE:
        req.detect_options.tracking_options.tracking_disable.value = True
    it_time = time.time()
    req.durations.client_duration_frame_level.end = it_time
    req.durations.grpc_outbound_transfer_duration.start = it_time
    return req
