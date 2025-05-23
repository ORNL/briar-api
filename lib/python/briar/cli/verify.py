import asyncio
import briar
import briar.briar_client as briar_client
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as srvc_pb2
import briar.briar_media as briar_media
import briar.grpc_json as grpc_json
import optparse
import os
import sys
import time
from briar import DEFAULT_PORT, __version__
from briar import timing
from briar.cli.connection import addConnectionOptions
from briar.cli.detect import addDetectorOptions, DETECTION_FILE_EXT, detect_options2proto, save_detections
from briar.cli.extract import addExtractOptions, extract_options2proto, TEMPLATE_FILE_EXT, save_extractions
from briar.cli.media import addMediaOptions, collect_files
from briar.cli.track import save_tracklets
from briar.media import BriarProgress
from briar.media_converters import image_cv2proto, image_proto2cv
from briar.media_converters import pathmap_str2dict, pathmap_path2remotepath

VERIFICATION_FILE_EXT = ".verification"


def addVerifyOptions(parser):
    """!
    Add options for verification to the parser.

    This function adds a group of verification-related options to the provided optparse.OptionParser instance.
    These options allow the user to configure various aspects of the verification process, such as the debug mode,
    output type, and whether to return media.

    @param parser optparse.OptionParser: A parser to modify in place by adding options.
    """
    verify_group = optparse.OptionGroup(parser, "Verify Options",
                                        "Configuration for media-to-media verification.")

    verify_group.add_option("--verify-debug", action="store_true", dest="verify_debug", default=None,
                            help="Enable server side debugging for this call.")
    verify_group.add_option("-d", "--use-detections", action="store_true", dest="use_detections", default=False,
                            help="Use saved detections to perform the extract. Default=False")
    output_type_choices = ['pickle', 'briar', 'numpy', 'pandas', 'xml']
    verify_group.add_option("--output-type", type="choice", choices=output_type_choices, dest="output_type",
                            default="briar",
                            help="Choose an output type for saving results. Options: " + ",".join(
                                output_type_choices) + " Default=briar")

    verify_group.add_option("-t", "--use-templates", action="store_true", dest="use_templates", default=False,
                            help="Use saved templates to perform the extract. Default=False")

    verify_group.add_option("-w", "--verify-whole-image", action="store_true", dest="verify_whole_image",
                            default=False,
                            help="Create templates from the full image - overwrites the '-d' option. Default=False")
    verify_group.add_option("-m", "--modality", type="choice",
                            choices=['unspecified', 'whole_body', 'face', 'gait', 'all'], dest="modality",
                            default="all",
                            help="Choose a biometric modality to detect/extract/enroll. Default=all")

    verify_group.add_option("--return-media", action="store_true", dest="return_media", default=False,
                            help="Enables returning of media from workers to the client - will significantly increase output file sizes!")
    verify_group.add_option("--reference-database", type="str", dest="reference_database", default=None,
                            help="Specifies a reference database to verify against. If database contains 10 entries, the verify call will return 10 verification scores")
    verify_group.add_option("--verify-database", type="str", dest="verify_database", default=None,
                            help="Specifies a reference database to verify against. If verify database contains 10 entries, the verify call will return 10 sets of verification scores")
    parser.add_option("--verify-order-list", type="str", dest="verify_order_list", default=None,
                      help="Sigset XML file to use as the ordering of result output (only used for BRIAR evaluations)")
    parser.add_option("--reference-order-list", type="str", dest="reference_order_list", default=None,
                      help="Sigset XML file to use as the ordering of result output (only used for BRIAR evaluations)")
    parser.add_option("--max-frames", type="int", dest="max_frames", default=-1,
                      help="Maximum frames to extract from a video (leave unset or -1 to use all given frames)")

    parser.add_option_group(verify_group)


def verify_options2proto(options):
    """!
    Convert command line options to a protobuf object for gRPC.

    This function takes the parsed command line options and populates a VerifyOptions protobuf object
    with the corresponding values. This object is then used to configure the verification process in the gRPC request.

    @param options optparse.Values: Parsed command line options.
    @return: A VerifyOptions protobuf object populated with the command line options.
    """
    out_options = briar_pb2.VerifyOptions()

    if options.verify_whole_image:
        out_options.flag = briar_pb2.VerifyFlags.VERIFY_FULL_IMAGE
    elif options.use_detections:
        out_options.flag = briar_pb2.VerifyFlags.VERIFY_PROVIDED_DETECTIONS
    elif options.use_templates:
        out_options.flag = briar_pb2.VerifyFlags.VERIFY_PROVIDED_TEMPLATES
    else:
        out_options.flag = briar_pb2.VerifyFlags.VERIFY_AUTO_DETECTION

    val = options.return_media
    if val is not None:
        out_options.return_media.value = val

    val = options.modality
    if val is not None:
        val = briar.media_converters.modality_string2proto(val)
        out_options.modality = val

    return out_options


def verifyParseOptions(inputCommand=None):
    """!
    Generate options for running verifications and parse command line arguments into them.

    This function sets up an optparse.OptionParser instance with various options for running verifications,
    including connection options, detector options, extract options, verify options, and media options. It then parses
    the command line arguments into these options.

    @param inputCommand str: A string containing the command line input to parse. If None, the function will parse sys.argv.
    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively.
    """
    args = ['[reference image/video or directory] [verification image/video or directory] [...]']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = "Run verification on a pair of media or detections. " + \
                  "Template files are output as serialized protobuf messages."
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''
    version = __version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s verify [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog, conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

    parser.add_option("-o", "--out-dir", type="str", dest="out_dir", default=None,
                      help="Output Directory: defaults to media_directory.")

    parser.add_option("--gallery-data-filename", type="str", dest="gallery_data_filename", default=None,
                      help="Name of gallery_data.csv output file used for input to analysis suite")

    parser.add_option("-n", "--max-images", type="int", dest="max_images", default=None,
                      help="Process at N images and then stop.")
    parser.add_option("--track", action="store_true", dest="track", default=False,
                      help="Set this flag to enable tracking of detections, instead of just frame-wise detections")
    parser.add_option("--no-save", action="store_true", dest="no_save", default=False,
                      help="Disables saving of results on the client-side")
    parser.add_option("--single-subject", action="store_true", dest="single_subject", default=False,
                      help="Ensures single-subject outputs are pickled. Must be set to True for compatibility with Phase 1 report card.")
    parser.add_option("--detections_dir", type="str", dest="detections_dir", default=None,
                      help="Directory to read detections from. Unspecified means same folder(s) as media.")
    parser.add_option("--plot", action="store_true", dest="plot", default=False,
                      help="Plots the score matrix")

    addVerifyOptions(parser)
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
        print("\nError: Please supply at least one directory, image, or video.\n")
        exit(-1)

    return options, args


def verify(options=None, args=None, input_command=None, ret=False):
    """!
    Using the options specified in the command line, runs a verification on the specified files. Writes results to disk
    to a location specified by the command arguments.

    This function initializes a BriarClient, sets up the verification options, and processes the specified media files.
    It runs the verification process on each file, saves the results, and optionally returns the results.

    @param options optparse.Values: Parsed command line options.
    @param args list: List of command line arguments.
    @param input_command str: A string containing the command line input to parse. If None, the function will parse sys.argv.
    @param ret bool: If True, the function will return the verification results. Otherwise, it writes results to disk.
    @return: If ret is True, yields briar_service_pb2.VerifyReply containing results.
    """
    api_start = time.time()
    if options is None and args is None:
        options, args = verifyParseOptions(inputCommand=input_command)
    client = briar_client.BriarClient(options)

    if options.verbose:
        print("Scanning directories for images and videos.")

    detect_options = detect_options2proto(options)
    extract_options = extract_options2proto(options)
    verify_options = verify_options2proto(options)

    extract_options.modality = detect_options.modality

    reference_image_list, reference_video_list = collect_files([args[1]], options)
    reference_media_list = reference_image_list + reference_video_list

    verify_image_list, verify_video_list = collect_files([args[2]], options)
    verify_media_list = verify_image_list + verify_video_list

    # if verify media list contains only 1 and the reference is multiple, set up for 1-to-N matching
    if len(verify_media_list) == 1 and len(reference_media_list) > 1:
        verify_media_list = verify_media_list * len(reference_media_list)
    # if verify media list contains multiple, and reference contains only one, set up for N-to-1 matching
    if len(verify_media_list) > 1 and len(reference_media_list) == 1:
        reference_media_list = reference_media_list * len(verify_media_list)

    assert len(verify_media_list) == len(reference_media_list)

    if options.out_dir:
        if options.verbose:
            print("Creating output directory:", options.out_dir)
        out_dir = options.out_dir
        os.makedirs(out_dir, exist_ok=True)

    if options.verbose:
        print("Processing images.")

    image_count = 0
    det_list_list = []
    batch_start_time = api_end = time.time()  # api_end-api_start = total time API took to find files and initialize

    if not options.use_detections and not options.verify_whole_image:
        # run auto-detections
        det_list_list = [None] * len(reference_media_list)

    for media_file_pair, det_list in zip(zip(reference_media_list, verify_media_list), det_list_list):
        reference_media_file = media_file_pair[0]
        verify_media_file = media_file_pair[1]
        request_start = time.time()

        if det_list is None:
            dets_in = None
        else:
            dets_in = [det_list]
        pbar = BriarProgress(options, name='Verifying')
        durations = []
        reply = client.verify_files(reference_media_file, verify_media_file, options, detect_options, extract_options,
                                    request_start=request_start)

        reply.durations.grpc_inbound_transfer_duration.end = time.time()
        reply.durations.total_duration.end = time.time()
        joined_media_file = reference_media_file + "_" + os.path.basename(verify_media_file)
        if ret:
            return reply
        if options.verbose:
            for similarity in reply.similarities.match_list:
                print(similarity.score, similarity.verification_id, similarity.reference_id)
        if not options.no_save:
            save_verifications(joined_media_file, reply, options, 0, modality=options.modality)

        if options.save_durations:
            timing.save_durations(joined_media_file, durations, options, "verify")
        print(reply.similarities)


def save_verifications(media_file, reply, options, i, modality=None, media_id=None):
    """!
    Save verification results to disk.

    This function saves the verification results to disk in JSON format. It generates the appropriate file path
    and writes the verification results to the specified location.

    @param media_file str: The path to the media file being processed.
    @param reply briar_service_pb2.VerifyReply: The verification results to save.
    @param options optparse.Values: Parsed command line options.
    @param i int: The index of the current frame or media file.
    @param modality str: The biometric modality being processed.
    @param media_id str: The ID of the media being processed.
    """
    similarities = reply.similarities.match_list
    if len(similarities) > 0:
        media_ext = os.path.splitext(media_file)[-1]
        if modality is not None:
            modality = "_" + modality
        else:
            modality = ""
        if media_id is not None:
            media_id = "_" + media_id
        else:
            media_id = ""
        det_name = os.path.splitext(os.path.basename(media_file))[0] + modality + media_id + VERIFICATION_FILE_EXT
        is_video = media_ext.lower() in briar_media.BriarMedia.VIDEO_FORMATS
        if not options.out_dir:
            out_dir = os.path.dirname(media_file)
        else:
            out_dir = options.out_dir

        if is_video:
            out_dir = os.path.join(out_dir, det_name + 's')
            det_name = os.path.splitext(os.path.basename(media_file))[0] + '_' + str(i).zfill(
                6) + modality + VERIFICATION_FILE_EXT
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        det_path = os.path.join(out_dir, det_name)
        if options.verbose:
            print('saved verifications to :', det_path)
        grpc_json.save(reply, det_path)
