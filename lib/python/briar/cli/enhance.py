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
import sys
import time
from briar import timing
from briar.cli.connection import addConnectionOptions
from briar.cli.media import addMediaOptions
from briar.cli.media import collect_files
from briar.media import BriarProgress, file_iter
from briar.media_converters import image_cv2proto, pathmap_str2dict, pathmap_path2remotepath

ENHANCE_FILE_EXT = '.enh'


def addEnhanceOptions(parser):
    """!
    Add options for running enhancements to the parser. Modifies the parser in place.

    This function adds a group of enhancement-related options to the provided optparse.OptionParser instance.
    These options allow the user to configure various aspects of the enhancement process, such as the algorithm to use,
    whether to return media, and batch processing settings.

    @param parser optparse.OptionParser: A parser to modify in place by adding options.
    """
    enhance_group = optparse.OptionGroup(parser, "Enhancement Options",
                                         "Configuration for enhancement")
    enhance_group.add_option("--enhance-algorithm", type="str", dest="enhance_algorithm_id", default=None,
                             help="Select the enhancement algorithm to use. Optional.")

    enhance_group.add_option("--return-media", action="store_true", dest="return_media", default=False,
                             help="Enables returning of media from workers to the client - will significantly increase output file sizes!")

    enhance_group.add_option("--cropped", action="store_true", dest="cropped", default=False,
                             help="When set, the algorithm will return cropped images of just the enhanced ROIs (if applicable). Default is false. When false, the entire image should be returned.")

    enhance_group.add_option("-m", "--modality", type="choice",
                             choices=['unspecified', 'whole_body', 'face', 'gait', 'all'],
                             dest="modality",
                             default="all",
                             help="Choose a biometric modality. Default=all")

    enhance_group.add_option("--enhance-batch", type="int", dest="enhance_batch", default=-1,
                             help="How many frames per batch. Negative batch size denotes frame-wise streaming. Default = -1")

    enhance_group.add_option("--max-frames", type="int", dest="max_frames", default=-1,
                             help="Maximum frames to extract from a video (leave unset or -1 to use all given frames)")

    parser.add_option_group(enhance_group)


def enhanceParseOptions(inputCommand=None):
    """!
    Generate options for running enhancement and parse command line arguments into them.

    This function sets up an optparse.OptionParser instance with various options for running enhancements,
    including connection options, enhancement options, and media options. It then parses the command line arguments
    into these options.

    @param inputCommand str: A string containing the command line input to parse. If None, the function will parse sys.argv.
    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively.
    """
    args = ['[image] [video] [image_directory] [...]']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = "Run enhancement on a collection of images and videos. " + \
                  "This command scans media and directories from the commandline " + \
                  "for known media types and runs enhancement on those files. " + \
                  "Results are saved as csv files in the output directory."
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s enhance [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog, conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

    parser.add_option("-o", "--out-dir", type="str", dest="out_dir", default=None,
                      help="Output Directory: defaults to media_directory.")
    parser.add_option("--no-save", action="store_true", dest="no_save", default=False,
                      help="Disables saving of results on the client-side")

    addConnectionOptions(parser)  # -> initialize client connection
    addEnhanceOptions(parser)  # -> initialize client enhancement options
    addMediaOptions(parser)

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


def enhance_options2proto(options):
    """!
    Convert command line options to a protobuf object for gRPC.

    This function takes the parsed command line options and populates an EnhanceOptions protobuf object
    with the corresponding values. This object is then used to configure the enhancement process in the gRPC request.

    @param options optparse.Values: Parsed command line options.
    @return: An EnhanceOptions protobuf object populated with the command line options.
    """
    enhance_options = briar_pb2.EnhanceOptions()

    val = options.enhance_algorithm_id
    if val is not None:
        enhance_options.algorithm_id.override_default = True
        enhance_options.algorithm_id.value = val

    val = options.modality
    if val is not None:
        val = media_converters.modality_string2proto(val)
        enhance_options.modality = val

    val = options.return_media
    if val is not None:
        enhance_options.return_media.value = val

    val = options.enhance_batch
    if val is not None:
        enhance_options.enhance_batch.value = val

    val = options.cropped
    if val is not None:
        enhance_options.cropped = val

    return enhance_options


def enhance(options=None, args=None, input_command=None, ret=False):
    """!
    Using the options specified in the command line, runs an enhancement on the specified files. Writes results to disk
    to a location specified by the cmd arguments.

    This function initializes a BriarClient, sets up the enhancement options, and processes the specified media files.
    It runs the enhancement process on each file, saves the results, and optionally returns the results.

    @param options optparse.Values: Parsed command line options.
    @param args list: List of command line arguments.
    @param input_command str: A string containing the command line input to parse. If None, the function will parse sys.argv.
    @param ret bool: If True, the function will return the enhancement results. Otherwise, it writes results to disk.
    @return: If ret is True, yields briar_service_pb2.EnhanceReply containing results.
    """
    api_start = time.time()
    if options is None and args is None:
        options, args = enhanceParseOptions(input_command)

    client = briar_client.BriarClient(options)

    enhance_options = enhance_options2proto(options)

    # Get images from the cmd line arguments
    image_list, video_list = collect_files(args[1:], options)
    media_list = image_list + video_list
    all_durations = {}
    results = []
    if len(media_list) > 0:
        if options.verbose:
            print("Running Enhance on {} Images, {} Videos".format(len(image_list),
                                                                   len(video_list)))
        if options.out_dir:
            out_dir = options.out_dir
            os.makedirs(out_dir, exist_ok=True)

        i = 0
        batch_start_time = api_end = time.time()  # api_end-api_start = total time API took to find files and initialize
        for media_file in media_list:
            if options.max_frames > 0 and i >= options.max_frames:
                break
            request_start = time.time()
            # run enhancements
            media_ext = os.path.splitext(media_file)[-1]
            durations = []
            for it in file_iter([media_file], options, {'enhance_options': enhance_options}, request_start=request_start,
                           requestConstructor=enhanceRequestConstructor):
                replies = client.enhance(it)
                pbar = BriarProgress(options, name='Enhancing')
                for i, reply in enumerate(replies):
                    iter_start = time.time()
                    reply.durations.grpc_inbound_transfer_duration.end = time.time()
                    length = reply.progress.totalSteps
                    durs = reply.durations

                    pbar.update(total=length, current=reply.progress.currentStep)
                    # run enhancements
                    durations.append(durs)
                    durs.total_duration.end = time.time()
                    if not reply.progress_only_reply:
                        if options.verbose and not options.progress:
                            print(durs.total_duration)
                            print("Enhanced {} in {}s".format(os.path.basename(media_file),
                                                            timing.timeElapsed(durs.total_duration)))

                        if ret:
                            yield reply
                    i += 1
                    all_durations[media_file+str(i).zfill(6)] = briar_pb2.BriarDurationsList()
                    all_durations[media_file+str(i).zfill(6)].durations_list.extend(durations)
                    if options.save_durations:
                        timing.save_durations(media_file+str(i).zfill(6), all_durations[media_file+str(i).zfill(6)], options, "enhance")

        if options.verbose:
            print("Finished {} files in {} seconds".format(len(media_list),
                                                           time.time() - batch_start_time))

    else:
        print("Error. No image or video media found.")


def save_Enhancement(media_file, reply, options, i, modality=None):
    """!
    Save enhancement results to disk.

    This function saves the enhancement results to disk in JSON format. It generates the appropriate file path
    and writes the enhancement results to the specified location.

    @param media_file str: The path to the media file being processed.
    @param reply briar_service_pb2.EnhanceReply: The enhancement results to save.
    @param options optparse.Values: Parsed command line options.
    @param i int: The index of the current frame or media file.
    @param modality str: The biometric modality being processed.
    """
    dets = reply.detections
    if len(dets) > 0:
        media_ext = os.path.splitext(media_file)[-1]
        if modality is not None:
            modality = "_" + modality
        else:
            modality = ""
        det_name = os.path.splitext(os.path.basename(media_file))[0] + modality + ENHANCE_FILE_EXT
        is_video = media_ext.lower() in briar_media.BriarMedia.VIDEO_FORMATS
        if not options.out_dir:
            out_dir = os.path.dirname(media_file)
        else:
            out_dir = options.out_dir

        if is_video:
            out_dir = os.path.join(out_dir, det_name + 's')

            det_name = os.path.splitext(os.path.basename(media_file))[0] + '_' + str(i).zfill(
                6) + modality + ENHANCE_FILE_EXT
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        det_path = os.path.join(out_dir, det_name)
        if options.verbose:
            print('saved enhancements to :', det_path)
        grpc_json.save(reply, det_path)


def enhanceRequestConstructor(media: briar_pb2.BriarMedia, durations: briar_pb2.BriarDurations, options_dict={},
                              det_list_list=None, database_name: str = None):
    """!
    Construct an EnhanceRequest for the gRPC call.

    This function constructs an EnhanceRequest protobuf object for the gRPC call. It populates the request
    with the media, durations, enhancement options, and other relevant information.

    @param media briar_pb2.BriarMedia: The media to process.
    @param durations briar_pb2.BriarDurations: The durations object to log timing information.
    @param options_dict dict: A dictionary of options for configuring the enhancement process.
    @param det_list_list list: A list of detection lists.
    @param database_name str: The name of the database to use.
    @return: An EnhanceRequest protobuf object populated with the relevant information.
    """
    enhance_options = options_dict['enhance_options']
    req = srvc_pb2.EnhanceRequest(
        media=media,
        frame_id=media.frame_number,
        durations=durations,
        enhance_options=enhance_options
    )
    return req
