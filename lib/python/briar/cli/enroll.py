import asyncio
import briar
import briar.briar_client as briar_client
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as srvc_pb2
import briar.grpc_json as grpc_json
import optparse
import os
import sys
import time

import briar.media_converters
from briar import timing
from briar.cli.connection import addConnectionOptions
from briar.cli.detect import addDetectorOptions, DETECTION_FILE_EXT, detect_options2proto, save_detections
from briar.cli.extract import addExtractOptions, extract_options2proto, TEMPLATE_FILE_EXT, save_extractions
from briar.cli.media import addMediaOptions, collect_files
from briar.cli.track import save_tracklets
from briar.media import BriarProgress
from briar.media import file_iter
from briar.media_converters import image_cv2proto, image_proto2cv, pathmap_str2dict, pathmap_path2remotepath, subjectList_string2list, attribute_val2proto


def addEnrollOptions(parser):
    """!
    Add options for enrollment into a database.

    This function adds a group of enrollment-related options to the provided optparse.OptionParser instance.
    These options allow the user to configure various aspects of the enrollment process, such as the database to use,
    the entry type, and whether to return or store media.

    @param parser optparse.OptionParser: A parser to modify in place by adding options.
    """
    enroll_group = optparse.OptionGroup(parser, "Enrollment Options",
                                        "Configuration for enrollment.")

    parser.add_option("-D", "--database", type="str", dest="database", default=None,
                      help="Select the database to enroll into.")

    parser.add_option("--subject-id", type="str", dest="subject_ids", default=None,
                      help="Define the subject_id(s) within the database. Multiple IDs should be comma separated.")
    parser.add_option("--media-id", type="str", dest="media_id", default=None,
                      help="Define the media_id within the database. This should be unique for a given media input.")

    parser.add_option("-T", "--entry-type", type="choice", choices=['subject', 'media', 'probe', 'gallery'],
                      dest="entry_type", default="subject",
                      help="Choose an enrollment mode: subject, media, probe, or gallery. Probe translates to media, while gallery translates to subject. Default=subject")
    enroll_group.add_option("--path-only", action="store_true", dest="path_only", default=None,
                            help="Indicates that the request being made will only provide a file path, and requires the server to perform all data loading server-side. INTENDED ONLY FOR LEGACY SYSTEMS, NOT FOR OPERATIONAL USE.")
    enroll_group.add_option("--enroll-debug", action="store_true", dest="enroll_debug", default=None,
                            help="Enable server side debugging for this call.")
    enroll_group.add_option("--max-frames", type="int", dest="max_frames", default=-1,
                      help="Maximum frames to extract from a video (leave unset or -1 to use all given frames)")
    
    enroll_group.add_option("--no-save", action="store_true", dest="no_save", default=False,
                            help="If flag is set, the BRIAR API will not save out detections, tracklets, or templates.")
    enroll_group.add_option("--return-media", action="store_true", dest="return_media", default=False,
                            help="Enables returning of media from workers to the client - will significantly increase output file sizes!")
    enroll_group.add_option("--store-media", action="store_true", dest="store_media", default=False,
                            help="Enables storing of media within the worker's database - could significantly increase database sizes!")
    enroll_group.add_option("--enroll-batch", type="int", dest="enroll_batch", default=-1,
                            help="How many frames per batch. Negative batch size denotes frame-wise streaming. Default = -1")

    parser.add_option("-N", "--name", type="str", dest="subject_name", default=None,
                      help="Enroll detected biometrics into a database.")

    parser.add_option("-t", "--use-templates", action="store_true", dest="use_templates", default=False,
                      help="Use saved templates to perform the extract. Default=False")

    parser.add_option("-w", "--enroll-whole-image", action="store_true", dest="whole_image", default=False,
                      help="Do not run autodetect or use existing detections. Instead, generate a template from the whole image.")

    parser.add_option_group(enroll_group)


def enroll_options2proto(options):
    """!
    Convert command line options to a protobuf object for gRPC.

    This function takes the parsed command line options and populates an EnrollOptions protobuf object
    with the corresponding values. This object is then used to configure the enrollment process in the gRPC request.

    @param options optparse.Values: Parsed command line options.
    @return: An EnrollOptions protobuf object populated with the command line options.
    """
    out_options = briar_pb2.EnrollOptions()

    val = options.enroll_debug
    if val is not None:
        out_options.debug.override_default = True
        out_options.debug.value = val

    val = options.entry_type
    if val is not None:
        if val == 'subject' or val == 'gallery':
            out_options.entry_type = briar_pb2.ENTRY_TYPE_SUBJECT
        elif val == 'media' or val == 'probe':
            out_options.entry_type = briar_pb2.ENTRY_TYPE_MEDIA
        else:
            out_options.entry_type = briar_pb2.ENTRY_TYPE_UNKNOWN

    if options.subject_ids is not None:
        val = subjectList_string2list(options.subject_ids)
        if val is not None:
            out_options.subject_ids.MergeFrom(val)
    val = options.media_id
    if val is not None:
        out_options.media_id = val

    val = options.subject_name
    if val is not None:
        out_options.subject_name = options.subject_name

    val = options.enroll_batch
    if val is not None:
        out_options.enroll_batch.value = val

    val = options.whole_image
    if val is not None:
        if val is True:
            out_options.enroll_flag = briar_pb2.ENROLL_FULL_IMAGE
        else:
            out_options.enroll_flag = briar_pb2.ENROLL_AUTO_DETECTION

    if options.use_detections:
        out_options.enroll_flag = briar_pb2.ENROLL_PROVIDED_DETECTION
    if options.use_templates:
        out_options.enroll_flag = briar_pb2.ENROLL_PROVIDED_TEMPLATE

    val = options.return_media
    if val is not None:
        out_options.return_media.value = val

    val = options.store_media
    if val is not None:
        out_options.store_media.value = val
    val = options.context
    if val is not None:
        out_options.attributes.append(attribute_val2proto('context', options.context))
    if hasattr(options, "integer_id"):
        val = options.integer_id
        if val is not None:
            out_options.use_subject_integer_id.value = val

    return out_options


def enrollParseOptions(inputCommand=None):
    """!
    Generate options for running enrollments and parse command line arguments into them.

    This function sets up an optparse.OptionParser instance with various options for running enrollments,
    including connection options, detector options, extract options, enroll options, and media options. It then parses
    the command line arguments into these options.

    @param inputCommand str: A string containing the command line input to parse. If None, the function will parse sys.argv.
    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively.
    """
    args = ['[image] [image_directory] [video] [...]']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = "Run detection and extraction on media files and enroll templates " + \
                  "into a database. Enroll is the primary function used to scan data " + \
                  "for experiments. This function can be used to do this manually or " + \
                  "to test enrollment functionality."
    epilog = "Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)"

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s enroll [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog, conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

    parser.add_option("-e", "--enroll-csv", type="str", dest="enroll_csv", default=None,
                      help="Save a log of the enrollments.")

    parser.add_option("-o", "--out-dir", type="str", dest="out_dir", default=None,
                      help="Output Directory: defaults to media_directory.")
    parser.add_option("--no-save", action="store_true", dest="no_save", default=False,
                      help="Disables saving of results on the client-side")

    addMediaOptions(parser)
    addDetectorOptions(parser)
    addExtractOptions(parser)
    addEnrollOptions(parser)
    addConnectionOptions(parser)

    # Parse the arguments and return the results.
    if inputCommand is not None:
        import shlex
        inp = shlex.split(inputCommand)
        (options, args) = parser.parse_args(inp)
    else:
        (options, args) = parser.parse_args()

    if options.database is None:
        parser.print_help()
        print("\n"
              "Error: The database_id needs to be defined using the -D or --database options.\n"
              "\n")
        exit(-1)

    if not options.database and len(args) < 2:
        parser.print_help()
        print("\n"
              "Error: Please supply at least one directory, image, or video\n"
              "\n")
        exit(-1)

    return options, args


def enroll(options=None, args=None, input_command=None, ret=False):
    """!
    Using the options specified in the command line, runs an enroll on the specified files. Can enroll media files
    (runs auto detection), detections (auto extracts ROI defined by detects) or templates (skips detect/extract).

    This function initializes a BriarClient, sets up the enrollment options, and processes the specified media files.
    It runs the enrollment process on each file, saves the results, and optionally returns the results.

    @param options optparse.Values: Parsed command line options.
    @param args list: List of command line arguments.
    @param input_command str: A string containing the command line input to parse. If None, the function will parse sys.argv.
    @param ret bool: If True, the function will return the enrollment results. Otherwise, it writes results to disk.
    @return: If ret is True, yields briar_service_pb2.EnrollReply containing results.
    """
    api_start = time.time()
    if options is None and args is None:
        options, args = enrollParseOptions(input_command)
    client = briar_client.BriarClient(options)

    detect_options = detect_options2proto(options)
    extract_options = extract_options2proto(options)
    enroll_options = enroll_options2proto(options)

    extract_options.modality = detect_options.modality
    enroll_options.modality = detect_options.modality

    if options.verbose:
        print("Scanning directories for images and videos.")

    database = options.database
    image_list, video_list = collect_files(args[1:], options)

    media_list = image_list + video_list

    if options.verbose:
        print("Enrolling {} media files in {} database.".format(len(media_list), database))
    image_count = 0
    batch_start_time = api_end = time.time()  # api_end-api_start = total time API took to find files and initialize
    try:
        for filename in media_list:
            request_start = time.time()

            pbar = BriarProgress(options, name='Enrolling')
            for it in file_iter([filename], options, {"detect_options": detect_options, "extract_options": extract_options,
                                                 "enroll_options": enroll_options}, database_name=database,
                           request_start=request_start, requestConstructor=enrollRequestConstructor):

                durations = []
                try:
                    i = 0
                    for i, enroll_reply in enumerate(client.enroll(it)):
                        enroll_reply.durations.grpc_inbound_transfer_duration.end = time.time()
                        length = enroll_reply.progress.totalSteps
                        pbar.update(total=length, current=enroll_reply.progress.currentStep)
                        enroll_reply.durations.total_duration.end = time.time()
                        if options.max_frames > 0 and i >= options.max_frames:
                            break
                        if not enroll_reply.progress_only_reply:
                            if len(enroll_reply.detections) > 0:
                                if options.verbose and not options.progress:
                                    print("Enrolled templates from {} detections in {}s"
                                        "".format(len(enroll_reply.detections),
                                                    timing.timeElapsed(enroll_reply.durations.total_duration)))
                            templates = enroll_reply.extract_reply.templates
                            detections = enroll_reply.extract_reply.detect_reply
                            tracklets = enroll_reply.extract_reply.track_reply.tracklets
                            if not options.no_save:
                                save_detections(filename, detections, options, i, modality=options.modality)
                                save_tracklets(filename, tracklets, options, i, modality=options.modality)
                                save_extractions(filename, templates, options, i, modality=options.modality)
                        durations.append(enroll_reply.durations)
                except Exception as e:
                    if options.verbose:
                        print('We have had an error in reading video frames at frame ', i, ':')
                        print(e)
                    delete_req = srvc_pb2.DatabaseInsertRequest(ids=briar_pb2.TemplateIds(ids=['cmd_delete_errored', enroll_options.media_id]), database=briar_pb2.BriarDatabase(name=database))
                    client.stub.database_insert(delete_req)
                if options.save_durations:
                    timing.save_durations(filename, durations, options, "enroll")
                    if ret:
                        yield enroll_reply
    except Exception as e:
        print('outside of loop exception:')
        print(e)
    image_count += 1


def enrollRequestConstructor(media: briar_pb2.BriarMedia, durations: briar_pb2.BriarDurations, options_dict={},
                             det_list_list=None, database_name: str = None):
    """!
    Construct an EnrollRequest for the gRPC call.

    This function constructs an EnrollRequest protobuf object for the gRPC call. It populates the request
    with the media, durations, enrollment options, and other relevant information.

    @param media briar_pb2.BriarMedia: The media to process.
    @param durations briar_pb2.BriarDurations: The durations object to log timing information.
    @param options_dict dict: A dictionary of options for configuring the enrollment process.
    @param det_list_list list: A list of detection lists.
    @param database_name str: The name of the database to use.
    @return: An EnrollRequest protobuf object populated with the relevant information.
    """
    durations.client_duration_frame_level.start = time.time()
    detect_options = options_dict['detect_options']
    extract_options = options_dict['extract_options']
    enroll_options = options_dict['enroll_options']

    database = briar_pb2.BriarDatabase()
    if database_name is not None:
        database.name = database_name

    req = srvc_pb2.EnrollRequest(database=database,
                                 media=media,
                                 subject_ids=enroll_options.subject_ids,
                                 media_id=enroll_options.media_id,
                                 subject_id_integer=enroll_options.subject_id_integer.value,
                                 detections=det_list_list,
                                 detect_options=detect_options,
                                 extract_options=extract_options,
                                 durations=durations,
                                 enroll_options=enroll_options)
    if media.source_type == briar_pb2.BriarMedia.DataType.GENERIC_IMAGE:
        req.detect_options.tracking_options.tracking_disable.value = True
    it_time = time.time()
    req.durations.client_duration_frame_level.end = it_time
    req.durations.grpc_outbound_transfer_duration.start = it_time
    return req
