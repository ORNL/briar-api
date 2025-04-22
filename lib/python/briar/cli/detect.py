import asyncio
import briar
import briar.briar_client as briar_client
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as srvc_pb2
import briar.briar_media as briar_media
import briar.grpc_json as grpc_json
import briar.media_converters as media_converters
import optparse
import os
import pyvision as pv
import sys
import time
from briar import timing
from briar.cli.connection import addConnectionOptions
from briar.cli.media import addMediaOptions
from briar.cli.media import collect_files
from briar.media import BriarProgress, file_iter
from briar.media_converters import image_cv2proto, pathmap_str2dict, pathmap_path2remotepath
DETECTION_FILE_EXT = ".detection"


def addDetectorOptions(parser):
    """!
    Add options for running detections to the parser. Modifies the parser in place.

    This function adds a group of detection-related options to the provided optparse.OptionParser instance.
    These options allow the user to configure various aspects of the detection process, such as the algorithm to use,
    thresholds for face and body detection, and batch processing settings.

    @param parser optparse.OptionParser: A parser to modify in place by adding detection options.
    """
    detector_group = optparse.OptionGroup(parser, "Detector Options",
                                          "Configuration for the detectors.")
    detector_group.add_option("--detect-algorithm", type="str", dest="detect_algorithm_id", default=None,
                              help="Select the detection algorithm to use.")

    detector_group.add_option("--detect-best", action="store_true", dest="detect_best", default=None,
                              help="Return only the 'best' (highest scoring) face/body in the image.")

    detector_group.add_option("--detect-face-thresh", type="float", dest="detect_face_thresh", default=None,
                              help="The threshold for face detection.")

    detector_group.add_option("--detect-body-thresh", type="float", dest="detect_body_thresh", default=None,
                              help="The threshold for body detection.")

    detector_group.add_option("--detect-face-min-height", type="int", dest="detect_face_min_height", default=None,
                              help="Limit the size of the smallest face detections.")

    detector_group.add_option("--detect-body-min-height", type="int", dest="detect_body_min_height", default=None,
                              help="Limit the size of the smallest body detections.")

    detector_group.add_option("--detect-batch", type="int", dest="detect_batch", default=-1,
                              help="How many frames per batch. Negative batch size denotes frame-wise streaming. Default = -1")

    detector_group.add_option("--detect-metadata", action="store_true", dest="detect_metadata", default=None,
                              help="Enable processing for additional metadata: landmarks, pose, demographics, etc.")

    detector_group.add_option("--return-media", action="store_true", dest="return_media", default=False,
                              help="Enables returning of media from workers to the client - will significantly increase output file sizes!")
    detector_group.add_option("--max-frames", type="int", dest="max_frames", default=-1,
                            help="Maximum frames to extract from a video (leave unset or -1 to use all given frames)")

    # detector_group.add_option("-o", "--output-dir", type="str", dest="output_dir", default=None,
    #                   help="Specify the output directory of .detection, .tracklet, and .template files.  If left unset, files will save to input file directory")

    detector_group.add_option("-m", "--modality", type="choice",
                              choices=['unspecified', 'whole_body', 'face', 'gait', 'all'], dest="modality",
                              default="all",
                              help="Choose a biometric modality to detect/extract/enroll. Default=all")
    # detector_group.add_option("--detect-attributes", type="str", dest="attribute_filter", default=None,
    #                           help="A comma seperated list of additional attributes to pass to the algorithm. key1=value1,key2=value2,..."

    parser.add_option_group(detector_group)

    addTrackingOptions(parser)


def addTrackingOptions(parser):
    """!
    Add options for running tracking to the parser. Modifies the parser in place.

    This function adds a group of tracking-related options to the provided optparse.OptionParser instance.
    These options allow the user to configure various aspects of the tracking process, such as the algorithm to use,
    thresholds for tracking, and whether to disable tracking.

    @param parser optparse.OptionParser: A parser to modify in place by adding tracking options.
    """
    tracker_group = optparse.OptionGroup(parser, "Tracking Options",
                                         "Configuration for the tracking algorithm.")

    tracker_group.add_option("--tracking-algorithm", type="str", dest="tracking_algorithm_id", default=None,
                             help="Select the tracking algorithm to use.")

    tracker_group.add_option("--tracking-disable", action="store_true", dest="tracking_disable", default=None,
                             help="Disable tracking and process videos on a frame by frame basis.")

    tracker_group.add_option("--tracking-threshold", type="float", dest="tracking_thresh", default=None,
                             help="The threshold for tracking.")

    tracker_group.add_option("--tracking-batch", type="int", dest="tracking_batch", default=-1,
                             help="How many frames per batch. Negative batch size denotes frame-wise streaming. Default = -1")
    parser.add_option_group(tracker_group)


def detectParseOptions(inputCommand=None):
    """!
    Generate options for running detections and parse command line arguments into them.

    This function sets up an optparse.OptionParser instance with various options for running detections,
    including connection options, detector options, media options, and tracking options. It then parses
    the command line arguments into these options.

    @param inputCommand str: A string containing the command line input to parse. If None, the function will parse sys.argv.
    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively.
    """
    args = ['[image] [video] [image_directory] [...]']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = "Run detection on a collection of images and videos. " + \
                  "This command scans media and directories from the commandline " + \
                  "for known media types and runs detection and tracking on those files. " + \
                  "Results are saved as csv files in the output directory."
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s detect [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog, conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

    parser.add_option("-o", "--out-dir", type="str", dest="out_dir", default=None,
                      help="Output Directory: defaults to media_directory.")
    parser.add_option("--no-save", action="store_true", dest="no_save", default=False,
                      help="Disables saving of results on the client-side")

    addConnectionOptions(parser)  # -> initialize client connection
    addDetectorOptions(parser)  # -> protobuf DetectorOptions
    addMediaOptions(parser)
    addTrackingOptions(parser)

    # Parse the arguments and return the results.
    if inputCommand is not None:
        import shlex
        inp = shlex.split(inputCommand)
        (options, args) = parser.parse_args(inp)
    else:
        (options, args) = parser.parse_args()

    if len(args) < 1:
        parser.print_help()
        print("\n"
              "Please supply exactly {} arguments.\n"
              "\n".format(n_args))
        exit(-1)

    return options, args


def detect_options2proto(options):
    """!
    Convert command line options to a protobuf object for gRPC.

    This function takes the parsed command line options and populates a DetectionOptions protobuf object
    with the corresponding values. This object is then used to configure the detection process in the gRPC request.

    @param options optparse.Values: Parsed command line options.
    @return: A DetectionOptions protobuf object populated with the command line options.
    """
    detect_options = briar_pb2.DetectionOptions()

    val = options.detect_algorithm_id
    if val is not None:
        detect_options.algorithm_id.override_default = True
        detect_options.algorithm_id.value = val

    val = options.detect_best
    if val is not None:
        detect_options.best.override_default = True
        detect_options.best.value = val

    val = options.detect_face_thresh
    if val is not None:
        detect_options.face_threshold.override_default = True
        detect_options.face_threshold.value = val

    val = options.detect_body_thresh
    if val is not None:
        detect_options.body_threshold.override_default = True
        detect_options.body_threshold.value = val

    val = options.detect_face_min_height
    if val is not None:
        detect_options.face_min_height.override_default = True
        detect_options.face_min_height.value = val

    val = options.detect_body_min_height
    if val is not None:
        detect_options.body_min_height.override_default = True
        detect_options.body_min_height.value = val

    val = options.detect_metadata
    if val is not None:
        detect_options.enable_metadata.override_default = True
        detect_options.enable_metadata.value = val

    val = options.modality
    if val is not None:
        val = media_converters.modality_string2proto(val)
        detect_options.modality = val

    val = options.detect_batch
    if val is not None:
        detect_options.detect_batch.value = val

    val = options.return_media
    if val is not None:
        detect_options.return_media.value = val

    tracking_options = tracking_options2proto(options)
    detect_options.tracking_options.CopyFrom(tracking_options)

    return detect_options


def tracking_options2proto(options):
    """!
    Convert command line options to a protobuf object for tracking.

    This function takes the parsed command line options and populates a TrackingOptions protobuf object
    with the corresponding values. This object is then used to configure the tracking process in the gRPC request.

    @param options optparse.Values: Parsed command line options.
    @return: A TrackingOptions protobuf object populated with the command line options.
    """
    tracking_options = briar_pb2.TrackingOptions()

    val = options.tracking_algorithm_id
    if val is not None:
        tracking_options.algorithm_id.override_default = True
        tracking_options.algorithm_id.value = val

    val = options.tracking_disable
    if val is not None:
        tracking_options.tracking_disable.override_default = True
        tracking_options.tracking_disable.value = val

    val = options.tracking_thresh
    if val is not None:
        tracking_options.threshold.override_default = True
        tracking_options.threshold.value = val

    val = options.tracking_batch
    if val is not None:
        tracking_options.tracking_batch.value = val

    val = options.return_media
    if val is not None:
        tracking_options.return_media.value = val

    val = options.path_map

    return tracking_options


def detect(options=None, args=None, input_command=None, ret=False):
    """!
    Using the options specified in the command line, runs a detection on the specified files. Writes results to disk
    to a location specified by the cmd arguments.

    This function initializes a BriarClient, sets up the detection options, and processes the specified media files.
    It runs the detection process on each file, saves the results, and optionally returns the results.

    @param options optparse.Values: Parsed command line options.
    @param args list: List of command line arguments.
    @param input_command str: A string containing the command line input to parse. If None, the function will parse sys.argv.
    @param ret bool: If True, the function will return the detection results. Otherwise, it writes results to disk.
    @return: If ret is True, yields briar_service_pb2.DetectReply containing results.
    """
    api_start = time.time()
    if options is None and args is None:
        options, args = detectParseOptions(input_command)

    client = briar_client.BriarClient(options)

    detect_options = detect_options2proto(options)

    # Get images from the cmd line arguments
    image_list, video_list = collect_files(args[1:], options)
    media_list = image_list + video_list

    results = []
    all_durations = {}
    if len(media_list) > 0:
        if options.verbose:
            print("Running Detect on {} Images, {} Videos".format(len(image_list),
                                                                  len(video_list)))
        if options.out_dir:
            out_dir = options.out_dir
            os.makedirs(out_dir, exist_ok=True)

        i = 0
        batch_start_time = api_end = time.time()  # api_end-api_start = total time API took to find files and initialize
        for media_file in media_list:
            # run detections
            request_start = time.time()
            media_ext = os.path.splitext(media_file)
            media_name = os.path.basename(media_ext[0])
            media_ext = media_ext[-1]
            for it in file_iter([media_file], options, {"detect_options": detect_options},
                                       request_start=request_start, requestConstructor=detectRequestConstructor):
                replies = client.detect(it)
                pbar = BriarProgress(options, name='Detecting')
                durations = []
                prev_duration = None

                for i, reply in enumerate(replies):
                    if options.max_frames > 0 and i >= options.max_frames:
                        break
                    if not isFinalReply(reply):
                        reply.durations.grpc_inbound_transfer_duration.end = time.time()
                        length = reply.progress.totalSteps
                        pbar.update(total=length, current=reply.progress.currentStep)
                        if reply.progress_only_reply:
                            durs = reply.durations
                            durs.total_duration.end = time.time()
                        else:
                            # run detections
                            dets = reply.detections
                            durs = reply.durations

                            durations.append(durs)
                            if not options.no_save:
                                save_detections(media_file, reply, options, i, modality=options.modality)
                            durs.total_duration.end = time.time()
                            if options.verbose and not options.progress:
                                client.print_verbose("Detected {} detections in {} seconds for file {}"
                                                "".format(len(reply.detections),
                                                            timing.timeElapsed(durs.total_duration), os.path.basename(media_file)))
                            if ret:
                                yield reply
                i += 1
                all_durations[media_file+str(i).zfill(6)] = briar_pb2.BriarDurationsList()
                all_durations[media_file+str(i).zfill(6)].durations_list.extend(durations)
                if options.save_durations:
                    timing.save_durations(media_file+str(i).zfill(6), all_durations[media_file+str(i).zfill(6)], options, "detect")

        if options.verbose:
            print("Finished {} files in {} seconds".format(len(media_list),
                                                           time.time() - batch_start_time))

    else:
        print("Error. No image or video media found.")


def get_detection_path(media_file, options, i, modality=None, media_id=None):
    """!
    Generate the file path for saving detection results.

    This function constructs the file path for saving detection results based on the media file name,
    modality, and media ID. It ensures that the results are saved in the appropriate directory.

    @param media_file str: The path to the media file being processed.
    @param options optparse.Values: Parsed command line options.
    @param i int: The index of the current frame or media file.
    @param modality str: The biometric modality being processed.
    @param media_id str: The ID of the media being processed.
    @return: The file path for saving detection results.
    """
    media_ext = os.path.splitext(media_file)[-1]
    if modality is not None:
        modality = "_" + modality
    else:
        modality = ""
    if media_id is not None:
        media_id = "_" + media_id
    else:
        media_id = ""
    det_name = os.path.splitext(os.path.basename(media_file))[0] + modality + media_id + DETECTION_FILE_EXT
    is_video = media_ext.lower() in briar_media.BriarMedia.VIDEO_FORMATS
    if not options.out_dir:
        out_dir = os.path.dirname(media_file)
    else:
        out_dir = options.out_dir
    if is_video:
        out_dir = os.path.join(out_dir, det_name + 's')
        det_name = os.path.splitext(os.path.basename(media_file))[0] + '_' + str(i).zfill(
            6) + modality + DETECTION_FILE_EXT
    det_path = os.path.join(out_dir, det_name)
    return det_path


def save_detections(media_file, reply, options, i, modality=None, media_id=None):
    """!
    Save detection results to disk.

    This function saves the detection results to disk in JSON format. It generates the appropriate file path
    and writes the detection results to the specified location.

    @param media_file str: The path to the media file being processed.
    @param reply briar_service_pb2.DetectReply: The detection results to save.
    @param options optparse.Values: Parsed command line options.
    @param i int: The index of the current frame or media file.
    @param modality str: The biometric modality being processed.
    @param media_id str: The ID of the media being processed.
    """
    dets = reply.detections
    if len(dets) > 0:
        det_path = get_detection_path(media_file, options, i, modality, media_id)
        if not options.no_save:
            if not os.path.exists(os.path.dirname(det_path)):
                os.makedirs(os.path.dirname(det_path))
            grpc_json.save(reply, det_path)
            if options.verbose:
                print('saved detections to :', det_path)


def isFinalReply(reply):
    """!
    Check if the reply is the final reply in the detection process.

    This function checks if the given reply is the final reply in the detection process by examining
    the start and end times of the client duration at the frame level.

    @param reply briar_service_pb2.DetectReply: The reply to check.
    @return: True if the reply is the final reply, False otherwise.
    """
    if reply.durations.client_duration_frame_level.start == 0 and reply.durations.client_duration_frame_level.end == 0:
        return True
    else:
        return False


def detectRequestConstructor(media, durations, options_dict={}, det_list_list=None, database_name=None):
    """!
    Construct a DetectRequest for the gRPC call.

    This function constructs a DetectRequest protobuf object for the gRPC call. It populates the request
    with the media, durations, detection options, and other relevant information.

    @param media briar_pb2.BriarMedia: The media to process.
    @param durations briar_pb2.BriarDurations: The durations object to log timing information.
    @param options_dict dict: A dictionary of options for configuring the detection process.
    @param det_list_list list: A list of detection lists.
    @param database_name str: The name of the database to use.
    @return: A DetectRequest protobuf object populated with the relevant information.
    """
    durations.client_duration_frame_level.start = time.time()
    detect_options = options_dict['detect_options']
    req = srvc_pb2.DetectRequest(
        media=media,
        frame=media.frame_number,
        durations=durations,
        detect_options=detect_options
    )
    if media.source_type == briar_pb2.BriarMedia.DataType.GENERIC_IMAGE:
        req.detect_options.tracking_options.tracking_disable.value = True
    return req
