import sys
import os
import optparse

import numpy as np
import pyvision as pv

import briar
import briar.briar_client as briar_client
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as srvc_pb2
from briar.cli.connection import addConnectionOptions
from briar.cli.media import addMediaOptions, collect_files
import briar.grpc_json as grpc_json
from briar.cli.detect import addDetectorOptions, DETECTION_FILE_EXT, detect_options2proto,save_detections
from briar.cli.extract import addExtractOptions, TEMPLATE_FILE_EXT,extract_options2proto,save_extractions
from briar.cli.track import save_tracklets
from briar.media_converters import image_cv2proto
from briar.media import BriarProgress

from matplotlib.patches import Circle
from matplotlib.offsetbox import (TextArea, DrawingArea, OffsetImage,
                                  AnnotationBbox)
from matplotlib.cbook import get_sample_data
import cv2

from briar import timing
import time
MATCHES_FILE_EXT = '.matches'




def addSearchOptions(parser):
    """!
    Add options for search of a database.

    @param parser optparse.OptionParser: A parser to modify in place by adding options
    """

    search_group = optparse.OptionGroup(parser, "Search Options",
                                        "Configuration for database search.")

    search_group.add_option("-o", "--out-dir", type="str", dest="out_dir", default=None,
                            help="Save the search results.")

    search_group.add_option("--output-type", type="choice", choices=['pickle','briar','numpy','pandas','xml'], dest="output_type",
                      default="briar",
                      help="Choose an enrollment mode: subject or media. Default=briar")
    search_group.add_option("-m", "--modality", type="choice",
                            choices=['unspecified', 'whole_body', 'face', 'gait', 'all'], dest="modality",
                            default="face",
                            help="Choose a biometric modality to detect/extract/enroll. Default=all")

    search_group.add_option("--database", type="str", dest="search_database", default='default',
                            help="Select the database to search.")

    search_group.add_option("--max-results", type="int", dest="max_results", default=3,
                            help="Set the maximum number of search results returned for each face.")

    search_group.add_option("-d", "--use-detections", action="store_true", dest="use_detections", default=False,
                      help="Use saved detections to perform the extract. Default=False")

    search_group.add_option("-t", "--use-templates", action="store_true", dest="use_templates", default=False,
                      help="Use saved templates to perform the extract. Default=False")

    search_group.add_option("-w", "--enroll-whole-image", action="store_true", dest="whole_image", default=False,
                      help="Do not run autodetect or use existing detections and generate a template from the whole "
                           "image.")
    search_group.add_option("--return-media", action="store_true", dest="return_media", default=False,
                               help="Enables returning of media from workers to the client - will significantly increase output file sizes!")

    # search_group.add_option("--probe-database", type="str", dest="probe_database", default=None,
    #                         help="Database to use as a probe set")

    # search_group.add_option("--search-batch", type="int", dest="search_batch", default=-1,
    #                         help="How many frames per batch. Negative batch size denotes frame-wise streaming. Default = -1")

    # search_group.add_option("-o", "--output-dir", type="str", dest="output_dir", default=None,
    #                            help="Specify the output directory of .detection, .tracklet, and .template files.  If left unset, files will save to input file directory")

    parser.add_option_group(search_group)


def search_options2proto(options):
    '''
    Parse command line options and populate a proto object for grpc
    '''

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
    # val = options.probe_database
    # if val is not None:
    #     search_options.search_database.value = options.search_database
    val = options.max_results
    if val is not None:
        search_options.max_results.value = val



    if val is not None:
        search_options.max_results.value = options.max_results
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


def searchParseOptions(inputCommand = None):
    """!
    Generate options for running searches and parse command line arguments into them.

    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively
    """
    args = ['[image] [image_directory] [video] [...]']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description =   "Run a 1:N search against a database. Input a probe entry" + \
                    " and finds the top matches in a gallery database."
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s search [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog,conflict_handler="resolve")

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
        # if options.search_database is not None:
        #     pass
        # else:
        parser.print_help()
        print()
        print(("Error: Please supply at least one directory, image, or video, or --probe-database flag"))
        print()
        exit(-1)

    return options, args



def search(options=None,args=None):
    """!
    Using the options specified in the command line, runs a search within the specified database using specified
    probe template(s). Writes results to disk to a location specified by the cmd arguments

    @return: No return - Function writes results to disk
    """
    api_start = time.time()

    if options is None and args is None:
        options, args = searchParseOptions()
    client = briar_client.BriarClient(options)


    # Check the status
    # print("*" * 35, 'STATUS', "*" * 35)
    # print(client.get_status())
    # print("*" * 78)

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
            print("Searching {} media files in {} database.".format(len(media_list),
                                                              database))
        elif options.probe_database is not None:
            print("Searching {} probe database against {} database.".format(options.probe_database,
                                                              database))

    image_count = 0
    batch_start_time = api_end = time.time()  #api_end-api_start = total time API took to find files and initialize

    for filename in media_list:
        request_start = time.time()
        if options.use_detections:
            # use provided detections to extract templates from, then enroll the results
            detection_filename = os.path.splitext(os.path.basename(filename))[0] + DETECTION_FILE_EXT
            if options.detections_dir:
                detections_path = os.path.join(options.detections_dir, detection_filename)
            else:
                detection_path = os.path.join(os.path.dirname(filename), detection_filename)
            if not os.path.exists(detections_path):
                raise FileNotFoundError("Detections file does not exist:", detections_path)
            detections = [grpc_json.load(detections_path)]
            searchReply=client.search(database,image_cv2proto(pv.Image(filename).asOpenCV2()),detect_options,extract_options,search_options) #TODO: make use detections work for search
            if options.verbose:
                print(searchReply)
        elif options.use_templates:
            # enroll provided templates into the database
            template_filename = os.path.splitext(os.path.basename(filename))[0] + TEMPLATE_FILE_EXT
            if options.templates:
                template_path = os.path.join(options.templates_dir, detection_filename)
            else:
                template_path = os.path.join(os.path.dirname(filename), detection_filename)
            templates = grpc_json.load(template_path)
            searchReply = client.search(database, image_cv2proto(pv.Image(filename).asOpenCV2()),detect_options,extract_options,search_options) #TODO: make use templates work for search
            if options.verbose:
                print(searchReply)
        else:
            # run auto-detection on provided files, extract the detections, and enroll the results
            searchReplies = client.search_files(database,[filename],detect_options,extract_options,search_options,request_start=request_start)
            # searchReply = client.search(database, image_cv2proto(pv.Image(filename).asOpenCV2()),detect_options,extract_options,search_options)
            pbar = BriarProgress(options,name='Searching')
            durations = []
            for i,searchReply in enumerate(searchReplies):
                length = searchReply.progress.totalSteps
                pbar.update(current=searchReply.progress.currentStep,total=length)

                templates = searchReply.extract_reply.templates
                detections = searchReply.extract_reply.detect_reply
                tracklets = searchReply.extract_reply.track_reply.tracklets
                if not options.no_save:
                    save_detections(filename, detections, options, i,modality=options.modality)
                    save_tracklets(filename, tracklets, options, i,modality=options.modality)
                    save_extractions(filename, templates, options, i,modality=options.modality)
                if options.verbose:
                    print('similarities:')
                    print(searchReply.similarities)
                if options.verbose and not options.progress:
                    print('searched 1 image in ',timing.timeElapsed(searchReply.durations.total_duration), ' seconds')
                out_dir = options.out_dir
                if not options.out_dir:
                    out_dir = os.path.dirname(filename)
                matches_name = os.path.splitext(os.path.basename(filename))[0] + MATCHES_FILE_EXT
                matches_path = os.path.join(out_dir, matches_name)
                durations.append(searchReply.durations)
                grpc_json.save(searchReply, matches_path)
            if options.save_durations:
                timing.save_durations(filename, durations, options, "search")

        image_count += 1
        if options.max_images is not None and image_count >= options.max_images:
            break