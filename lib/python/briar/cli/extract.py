import sys
import os
import optparse

import pyvision as pv

import briar
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as srvc_pb2
from briar.media_converters import image_cv2proto
import briar.briar_media as briar_media
from briar import DEFAULT_PORT, __version__
import briar.briar_client as briar_client
from briar.cli.connection import addConnectionOptions
from briar.cli.detect import addDetectorOptions,DETECTION_FILE_EXT,detect_options2proto,save_detections
from briar.cli.track import save_tracklets
from briar.cli.media import addMediaOptions, collect_files
import briar.grpc_json as grpc_json
from briar.media import BriarProgress
from briar.media_converters import image_cv2proto,image_proto2cv
from briar import timing
import time

TEMPLATE_FILE_EXT = '.template'



def addExtractOptions(parser):
    """!
    Add options for extractions to the parser.

    @type parser: optparse.OptionParser
    @param parser: A parser to modify in place by adding options
    """
    extractor_group = optparse.OptionGroup(parser, "Extract Options",
                                          "Configuration for the feature extractor.")

    extractor_group.add_option("--extract-algorithm-id", type="str", dest="extract_algorithm_id", default=None,
                              help="Select the extraction algorithm to use.")
    
    extractor_group.add_option("--extract-debug", action="store_true", dest="extract_debug", default=None,
                              help="Enable server side debugging for this call.")

    extractor_group.add_option("-f", "--extract-whole-image", action="store_true", dest="extract_whole_image", default=False,
                      help="Create templates from the full image - overwrites the '-d' option. Default=False")

    extractor_group.add_option("--return-media", action="store_true", dest="return_media", default=False,
                              help="Enables returning of media from workers to the client - will significantly increase output file sizes!")

    # extractor_group.add_option("-o", "--output-dir", type="str", dest="output_dir", default=None,
    #                           help="Specify the output directory of .detection, .tracklet, and .template files.  If left unset, files will save to input file directory")
    extractor_group.add_option("--extract-batch", type="int", dest="extract_batch", default=-1,
                            help="How many frames per batch. Negative batch size denotes frame-wise streaming. Default = -1")

    parser.add_option("-d", "--use-detections", action="store_true", dest="use_detections", default=False,
                      help="Use saved detections to perform the extract. Default=False")


    parser.add_option_group(extractor_group)

def extract_options2proto(options):
	#StringOption algorithm_id = 1;
	#BoolOption debug = 2; // Save or print more info on the server side
	#repeated Attribute attributes = 3; // Used for passing algorithm specific options

    out_options = briar_pb2.ExtractOptions()
    
    val = options.extract_algorithm_id
    if val is not None:
        out_options.algorithm_id.override_default = True
        out_options.algorithm_id.value = val

    val = options.extract_debug
    if val is not None:
        out_options.debug.override_default = True
        out_options.debug.value = val
    val = options.extract_batch
    if val is not None:
        out_options.extract_batch.value = val

    if options.extract_whole_image:
        out_options.flag = briar_pb2.ExtractFlags.EXTRACT_FULL_IMAGE
    elif options.use_detections:
        out_options.flag = briar_pb2.ExtractFlags.EXTRACT_PROVIDED_DETECTION
    else:
        out_options.flag = briar_pb2.ExtractFlags.EXTRACT_AUTO_DETECTION

    val = options.return_media
    if val is not None:
        out_options.return_media.value = val

    return out_options


def extractParseOptions(inputCommand=None):
    """!
    Generate options for running extracts and parse command line arguments into them.

    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively
    """
    args = ['[image] [image_directory] [video] [...]']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description =   "Run extraction on a collection of media or detections. " + \
                    "Template files are output as serialized protobuf messages."
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = __version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s extract [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog,conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

    parser.add_option("-o", "--out-dir", type="str", dest="out_dir", default=None,
                      help="Output Directory: defaults to media_directory.")

    parser.add_option("-n", "--max-images", type="int", dest="max_images", default=None,
                      help="Process at N images and then stop.")
    parser.add_option("--track", action="store_true", dest="track", default=False,
                            help="Set this flag to enable tracking of detections, instead of just frame-wise detections")
    parser.add_option("--no-save", action="store_true", dest="no_save", default=False,
                      help="Disables saving of results on the client-side")
    # parser.add_option("--maximum-size", type="int", dest="max_size", default=faro.DEFAULT_MAX_SIZE,
    #                   help="If too large, images will be scaled to have this maximum size. Default=%d" % (
    #                       faro.DEFAULT_MAX_SIZE))

    parser.add_option("--detections_dir", type="int", dest="detections_dir", default=None,
                      help="Directory to read detections from. Unspecified means same folder(s) as media.")


    addDetectorOptions(parser)
    addExtractOptions(parser)
    addConnectionOptions(parser)

    # Parse the arguments and return the results.
    if inputCommand is not None:
        import shlex
        inp = shlex.split(inputCommand)
        (options, args) = parser.parse_args(inp)
    else:
        (options, args) = parser.parse_args()

    if len(args) < 2:
        parser.print_help()
        print("\n"
              "Error: Please supply at least one directory, image, or video.\n"
              "\n")
        exit(-1)

    return options, args



def extract(options=None, args=None):
    """!
    Using the options specified in the command line, runs an extract on the specified files. Writes results to disk
    to a location specified by the cmd arguments

    @return: No return - Function writes results to disk
    """
    api_start = time.time()
    if options is None and args is None:
        options, args = extractParseOptions()
    client = briar_client.BriarClient(options)

    # # Check the status
    # print("*" * 35, 'STATUS', "*" * 35)
    # print(client.get_status())
    # print("*" * 78)

    if options and options.verbose:
        print("Scanning directories for images and videos.")

    detect_options = detect_options2proto(options)
    extract_options = extract_options2proto(options)

    extract_options.modality = detect_options.modality


    image_list, video_list = collect_files(args[1:], options)
    media_list = image_list + video_list

    # trim off excess media files
    if options.max_images is not None and len(media_list) > options.max_images:
        if options.verbose:
            print("Limit is {} media files. Ignoring {} files."
                  "".format(options.max_images, options.max_images - len(options.media_list)))
        media_list = media_list[options.max_images]

    if options and options.out_dir:
        if options.verbose:
            print("Creating output directory:", options.out_dir)
        out_dir = options.out_dir
        os.makedirs(out_dir,exist_ok=True)

    if options and options.verbose:
        print("Processing images.")

    image_count = 0
    detect_queue = []
    enroll_queue = []

    media_files =  image_list + video_list
    det_list_list = []
    batch_start_time = api_end = time.time()  # api_end-api_start = total time API took to find files and initialize

    for filename in media_files:
        request_start = time.time()
        if options.verbose:
            print("Extracting from {}".format(filename))
        # TODO add options to do full image extracts
        if options.use_detections:
            # Run extracts on provided detections
            if options.detections_dir:
                detection_dir = options.detections_dir
                file_basename = os.path.splitext(os.path.basename(filename))[0] \
                                + DETECTION_FILE_EXT
                detections_path = os.path.join(options.detections_dir, file_basename)
                if not os.path.isfile(detections_path):
                    raise FileExistsError("Detection for {} does not exist".format(file_basename))
            else:
                detections_path = os.path.splitext(filename)[0] + DETECTION_FILE_EXT
            det_list_list.append(grpc_json.load(detections_path))

        if options.extract_whole_image:
            # Run extract on full image
            raise NotImplementedError("Full image extraction is not implemented")

    if (not options.use_detections) and (not options.extract_whole_image):
        # run auto-detections
        det_list_list = [None]*len(media_files)

    for media_file,det_list in zip(media_files,det_list_list):
        request_start = time.time()
        media_ext = os.path.splitext(media_file)[-1]

        if det_list is None:
            dets_in = None
        else:
            dets_in = [det_list]
        pbar = BriarProgress(options,name='Extracting')
        durations = []
        for i,reply in enumerate(client.extract_files([media_file],dets_in,detect_options,extract_options,request_start = request_start)):
            reply.durations.grpc_inbound_transfer_duration.end = time.time()
            length = reply.progress.totalSteps
            pbar.update(current=reply.progress.currentStep,total=length)

            if len(reply.templates) > 0:
                if not options.tracking_disable and media_ext.lower() in briar_media.BriarMedia.VIDEO_FORMATS:
                    if not options.progress:
                        print('extracted ', len(reply.templates), ' tracklets(s) in ', timing.timeElapsed(reply.durations.total_duration),
                          ' seconds')
                else:
                    if not options.progress:
                        print('extracted ',len(reply.templates), ' image(s) in ', timing.timeElapsed(reply.durations.total_duration), ' seconds')
                templates = reply.templates
                detections = reply.detect_reply.detections
                tracklets = reply.track_reply.tracklets
                durations.append(reply.durations)
                if not options.no_save:
                    save_detections(media_file, reply.detect_reply, options, i,modality=options.modality)
                    save_tracklets(media_file,tracklets,options,i,modality=options.modality)
                    save_extractions(media_file,templates,options,i,modality=options.modality)
                if options.verbose and not options.progress:
                    print("Extracted {} in {}s".format(os.path.basename(media_file),
                                                      timing.timeElapsed(reply.durations.total_duration)))

            if options.save_durations:
                timing.save_durations(media_file,durations,options,"extract")


def save_extractions(media_file,templates,options,i,modality=None,media_id=None):
    if len(templates) > 0:
        media_ext = os.path.splitext(media_file)[-1]
        if modality is not None:
            modality = "_"+modality
        else:
            modality = ""
        if media_id is not None:
            media_id = "_" + media_id
        else:
            media_id = ""
        if not (options and options.out_dir):
            out_dir = os.path.dirname(media_file)
        elif options.out_dir is not None:
            out_dir = options.out_dir
        template_filename = os.path.splitext(os.path.basename(media_file))[0] + modality + media_id + TEMPLATE_FILE_EXT
        if media_ext.lower() in briar_media.BriarMedia.VIDEO_FORMATS:
            out_dir = os.path.join(out_dir, template_filename+'s')
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
            template_filename = os.path.splitext(os.path.basename(media_file))[0] + "_" + str(i).zfill(
                6) + modality + TEMPLATE_FILE_EXT
        out_path = os.path.join(out_dir, template_filename)


        if options and options.verbose:
            print("Writing {} templates to '{}'".format(len(templates), out_path))
        if len(templates) > 0:
            grpc_json.save(templates, out_path)