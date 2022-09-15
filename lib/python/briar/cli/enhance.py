import sys
import os
import optparse

import briar.media_converters as media_converters
import pyvision as pv

import briar
import briar.briar_client as briar_client
from briar.cli.connection import addConnectionOptions
import time
import briar.grpc_json as grpc_json

import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as srvc_pb2
import briar.briar_media as briar_media
from briar.media_converters import image_cv2proto

from briar.cli.media import addMediaOptions
from briar.cli.media import collect_files
from briar.media import BriarProgress
from briar import timing

def addEnhanceOptions(parser):
    """!
    Add options for running detections to the parser. Modifiers the parser in plase

    @param parser optparse.OptionParser: A parser to modify in place by adding options
    """
    enhance_group = optparse.OptionGroup(parser, "Enhancement Options",
                                          "Configuration for enhancement")
    enhance_group.add_option("--enhance-algorithm", type="str", dest="enhance_algorithm_id", default=None,
                              help="Select the enhancement algorithm to use. Optional.")


    enhance_group.add_option("--return-media", action="store_true", dest="return_media", default=False,
                              help="Enables returning of media from workers to the client - will significantly increase output file sizes!")

    enhance_group.add_option("-m", "--modality", type="choice", choices=['unspecified', 'whole_body', 'face', 'gait'],
                              dest="modality",
                              default="face",
                              help="Choose a biometric modality. Default=face")
    enhance_group.add_option("--enhance-batch", type="int", dest="enhance_batch", default=-1,
                             help="How many frames per batch. Negative batch size denotes frame-wise streaming. Default = -1")

    # detector_group.add_option("--detect-attributes", type="str", dest="attribute_filter", default=None,
    #                           help="A comma seperated list of additional attributes to pass to the algorithm. key1=value1,key2=value2,..."

    parser.add_option_group(enhance_group)

def enhanceParseOptions(inputCommand=None):
    """!
    Generate options for running enhancement and parse command line arguments into them.

    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively
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
    addEnhanceOptions(parser)  # -> initialize client enhancement options

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
    '''
    Parse command line options and populate a proto object for grpc
    '''

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

    return enhance_options

def enhance(options=None, args=None):
    """!
    Using the options specified in the command line, runs a detection on the specified files. Writes results to disk
    to a location specified by the cmd arguments

    @return: No return - Function writes results to disk
    """
    api_start = time.time()
    if options is None and args is None:
        options, args = enhanceParseOptions()

    client = briar_client.BriarClient(options)

    enhance_options = enhance_options2proto(options)

    # Get images from the cmd line arguments
    image_list, video_list = collect_files(args[1:], options)
    media_list = image_list + video_list
    all_durations = {}
    results = []
    if len(media_list) > 0:
        if options.verbose:
            print("Running Detect on {} Images, {} Videos".format(len(image_list),
                                                                  len(video_list)))
        if options.out_dir:
            out_dir = options.out_dir
            os.makedirs(out_dir, exist_ok=True)

        i = 0
        batch_start_time = api_end = time.time()  #api_end-api_start = total time API took to find files and initialize
        for media_file in media_list:
            request_start = time.time()
            # run detections
            media_ext = os.path.splitext(media_file)[-1]
            durations = []
            replies = client.enhance(enhance_file_iter([media_file], enhance_options,request_start=request_start))
            pbar = BriarProgress(options, name='Enhancing')
            for i, reply in enumerate(replies):
                iter_start = time.time()
                reply.durations.grpc_inbound_transfer_duration.end = time.time()
                length = reply.progress.totalSteps
                durs = reply.durations
                pbar.update(total=length, current=reply.progress.currentStep)
                # run detections
                durations.append(durs)
                # timing.print_durations(reply.durations)
                durs.total_duration.end = time.time()
                if options.verbose and not options.progress:
                    print(durs.total_duration)
                    print("Enhanced {} in {}s".format(os.path.basename(media_file),
                                                      timing.timeElapsed(durs.total_duration)))
                i += 1
            all_durations[media_file] = briar_pb2.BriarDurationsList()
            all_durations[media_file].durations_list.extend(durations)
            if options.save_durations:
                timing.save_durations(media_file, all_durations[media_file], options, "enhance")

        if options.verbose:
            print("Finished {} files in {} seconds".format(len(media_list),
                                                           time.time() - batch_start_time))

    else:
        print("Error. No image or video media found.")


def save_Enhancement(media_file, reply, options, i, modality=None):
    dets = reply.detections
    if len(dets) > 0:
        media_ext = os.path.splitext(media_file)[-1]
        if modality is not None:
            modality = "_" + modality
        else:
            modality = ""
        det_name = os.path.splitext(os.path.basename(media_file))[0] + modality + DETECTION_FILE_EXT
        is_video = media_ext.lower() in briar_media.BriarMedia.VIDEO_FORMATS
        if not options.out_dir:
            out_dir = os.path.dirname(media_file)
        else:
            out_dir = options.out_dir

        if is_video:
            out_dir = os.path.join(out_dir, det_name + 's')

            det_name = os.path.splitext(os.path.basename(media_file))[0] + '_' + str(i).zfill(
                6) + modality + DETECTION_FILE_EXT
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        det_path = os.path.join(out_dir, det_name)
        if options.verbose:
            print('saved detections to :', det_path)
        grpc_json.save(reply, det_path)


def enhance_file_iter(media_files, enhance_options=None, verbose=False,request_start = -1):
    """!
    Iterates the paths in the media file list, loading them one by one and yielding grpc detect requests

    @param media_files list(str): Paths to the media files to enroll from

    @param options briar_pb2.DetectionOptions: Command line options in protobuf format which control detection functionality

    @yield: briar_service_pb2.DetectRequest
    """

    if enhance_options is None:
        enhance_options = briar_pb2.EnhanceOptions()

    media_enum = zip(media_files)

    for i, iteration in enumerate(media_enum):
        # Dynamically break the iteration into individual components

        media_file = iteration[0]
        media_ext = os.path.splitext(media_file)[-1]
        if verbose:
            print("Enhancing:", media_file)

        if media_ext.lower() in briar_media.BriarMedia.IMAGE_FORMATS:
            # Create an enroll request for an image
            frame = pv.Image(media_file)
            media = image_cv2proto(frame.asOpenCV2())
            media.source = os.path.abspath(media_file)
            media.frame_count = 1
            durations = briar_pb2.BriarDurations()
            durations.client_duration_file_level.start=request_start
            durations.total_duration.start = request_start
            req = srvc_pb2.EnhanceRequest(
                media=media,
                frame_id=1,
                durations = durations,
                enhance_options=enhance_options
            )
            it_end = time.time()
            req.durations.client_duration_file_level.end = it_end
            req.durations.grpc_outbound_transfer_duration.start = it_end
            yield req

        elif media_ext.lower() in briar_media.BriarMedia.VIDEO_FORMATS:
            # Create an enroll request for a video
            video = pv.Video(media_file)

            file_level_client_time_end = time.time()

            for frame_num, frame in enumerate(video):
                durations = briar_pb2.BriarDurations()
                if frame_num == 0: # if this is the first frame, include the durations for the file-level operations of the BRIAR client API
                    durations.client_duration_file_level.start = request_start
                    durations.client_duration_file_level.end = file_level_client_time_end
                    durations.total_duration.start = request_start

                durations.client_duration_frame_level.start = time.time()
                media = image_cv2proto(frame.asOpenCV2())
                media.source = os.path.abspath(media_file)
                media.frame_count = int(video._numframes)  # NOTE len(video) raises an error
                media.frame_number = frame_num
                req = srvc_pb2.EnhanceRequest(
                    media=media,
                    frame_id=frame_num,
                    enhance_options=enhance_options,
                    durations = durations
                )

                it_time = time.time()
                req.durations.client_duration_frame_level.end = it_time
                req.durations.grpc_outbound_transfer_duration.start = it_time

                yield req
