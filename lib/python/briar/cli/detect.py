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
DETECTION_FILE_EXT = ".detection"

def addDetectorOptions(parser):
    """!
    Add options for running detections to the parser. Modifiers the parser in plase

    @param parser optparse.OptionParser: A parser to modify in place by adding options
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

    # detector_group.add_option("-o", "--output-dir", type="str", dest="output_dir", default=None,
    #                   help="Specify the output directory of .detection, .tracklet, and .template files.  If left unset, files will save to input file directory")

    detector_group.add_option("-m","--modality", type="choice", choices=['unspecified', 'whole_body', 'face', 'gait','all'], dest="modality",
                                default="face",
                                                            help="Choose a biometric modality to detect/extract/enroll. Default=all")
    # detector_group.add_option("--detect-attributes", type="str", dest="attribute_filter", default=None,
    #                           help="A comma seperated list of additional attributes to pass to the algorithm. key1=value1,key2=value2,..."

   
    parser.add_option_group(detector_group)

    addTrackingOptions(parser)



def addTrackingOptions(parser):
    """!
    Add options for running detections to the parser. Modifiers the parser in place

    @param parser optparse.OptionParser: A parser to modify in place by adding options
    """
    tracker_group = optparse.OptionGroup(parser, "Tracking Options",
                                          "Configuration for the tracking algorithm.")

    tracker_group.add_option("--tracking-algorithm", type="str", dest="tracking_algorithm_id", default=None,
                              help="Select the detection algorithm to use.")
    
    tracker_group.add_option("--tracking-disable", action="store_true", dest="tracking_disable", default=None,
                              help="Disable tracking and process videos on a frame by frame basis.")

    tracker_group.add_option("--tracking-threshold", type="float", dest="tracking_thresh", default=None,
                              help="The threshold for face detection.")
    
    # tracker_group.add_option("--detect-attributes", type="str", dest="attribute_filter", default=None,
    #                           help="A comma seperated list of additional attributes to pass to the algorithm. key1=value1,key2=value2,..."
    tracker_group.add_option("--tracking-batch", type="int", dest="tracking_batch", default=-1,
                              help="How many frames per batch. Negative batch size denotes frame-wise streaming. Default = -1")
    parser.add_option_group(tracker_group)


def detectParseOptions(inputCommand=None):
    """!
    Generate options for running detections and parse command line arguments into them.

    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively
    """
    args = ['[image] [video] [image_directory] [...]']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description =   "Run detection on a collection of images and videos. " + \
                    "This command scans media and directories from the commandline " + \
                    "for known media types and runs detection and tracking on those files. " + \
                    "Results are saved as csv files in the output directory."
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s detect [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog,conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

    parser.add_option("-o", "--out-dir", type="str", dest="out_dir", default=None,
                      help="Output Directory: defaults to media_directory.")
    parser.add_option("--no-save", action="store_true", dest="no_save", default=False,
                              help="Disables saving of results on the client-side")

    addConnectionOptions(parser) # -> initialize client connection
    addDetectorOptions(parser)   # -> protobuf DetectorOptions 
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

def detect_options2proto(options):
    '''
    Parse command line options and populate a proto object for grpc
    '''

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
    '''
    Parse command line options and populate a proto object for grpc
    '''

    tracking_options = briar_pb2.TrackingOptions()
    
    val = options.tracking_algorithm_id
    if val is not None:
        tracking_options.algorithm_id.override_default = True
        tracking_options.algorithm_id.value = val
        
    val = options.tracking_thresh
    if val is not None:
        tracking_options.threshold.override_default = True
        tracking_options.threshold.value = val
            
    val = options.tracking_disable
    if val is not None:
        tracking_options.tracking_disable.override_default = True
        tracking_options.tracking_disable.value = val

    val = options.tracking_batch
    if val is not None:
        tracking_options.tracking_batch.value = val

    val = options.return_media
    if val is not None:
        tracking_options.return_media.value = val

    # StringOption algorithm_id = 1; // uid corresponding to which algorithm to use
	# BoolOption tracking_disable = 2;     // min score for candidate consideration
	# FloatOption threshold = 3;     // min score for candidate consideration
    # // FloatOption encoding = 4;
	# repeated Attribute attributes = 5;    // Used for passing algorithm specific or custom options

    return tracking_options 



def detect(options=None,args=None):
    """!
    Using the options specified in the command line, runs a detection on the specified files. Writes results to disk
    to a location specified by the cmd arguments

    @return: No return - Function writes results to disk
    """
    api_start = time.time()
    if options is None and args is None:
        options, args = detectParseOptions()

    client = briar_client.BriarClient(options)

    detect_options = detect_options2proto(options)

    # Check the status
    # print("*"*35,'STATUS',"*"*35)
    # print(client.get_status())
    # print("*"*78)

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
            os.makedirs(out_dir,exist_ok=True)

        i = 0
        batch_start_time = api_end =time.time()#api_end-api_start = total time API took to find files and initialize
        for media_file in media_list:
            #run detections
            request_start = time.time()
            media_ext = os.path.splitext(media_file)
            media_name = os.path.basename(media_ext[0])
            media_ext = media_ext[-1]

            replies = client.detect(detect_file_iter([media_file],detect_options,request_start=request_start))
            pbar = BriarProgress(options,name='Detecting')
            durations = []
            for i,reply in enumerate(replies):
                reply.durations.grpc_inbound_transfer_duration.end = time.time()
                length = reply.progress.totalSteps
                pbar.update(total=length,current=reply.progress.currentStep)
                # run detections
                dets = reply.detections
                durs = reply.durations
                durations.append(durs)
                # media_file = media_list[0]
                # results.append([media_list, dets, durs])
                if not options.no_save:
                    save_detections(media_file,reply,options,i,modality=options.modality)

                if options.verbose and not options.progress:
                    print("Detected {} in {}s".format(os.path.basename(media_file),
                                                        timing.timeElapsed(durs.total_duration)))
                i += 1
                # timing.print_durations(durs)
            all_durations[media_file] = briar_pb2.BriarDurationsList()
            all_durations[media_file].durations_list.extend(durations)
            if options.save_durations:
                timing.save_durations(media_file,all_durations[media_file],options,"detect")

        if options.verbose:
            print("Finished {} files in {} seconds".format(len(media_list),
                                                               time.time()-batch_start_time))

    else:
        print("Error. No image or video media found.")

def get_detection_path(media_file,options,i,modality=None,media_id=None):
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

def save_detections(media_file,reply,options,i,modality=None,media_id=None):
    dets = reply.detections
    if len(dets) > 0:
        media_ext = os.path.splitext(media_file)[-1]
        if modality is not None:
            modality = "_"+modality
        else:
            modality = ""
        if media_id is not None:
            media_id = "_"+media_id
        else:
            media_id = ""
        det_name = os.path.splitext(os.path.basename(media_file))[0] + modality + media_id + DETECTION_FILE_EXT
        is_video = media_ext.lower() in briar_media.BriarMedia.VIDEO_FORMATS
        if not options.out_dir:
            out_dir = os.path.dirname(media_file)
        else:
            out_dir = options.out_dir

        if is_video:
            out_dir = os.path.join(out_dir, det_name+'s')

            det_name = os.path.splitext(os.path.basename(media_file))[0] + '_' + str(i).zfill(6) + modality + DETECTION_FILE_EXT
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        det_path = os.path.join(out_dir, det_name)
        if options.verbose:
            print('saved detections to :', det_path)
        grpc_json.save(reply, det_path)

def detect_file_iter(media_files,detect_options=None,verbose=False,request_start = -1):
    """!
    Iterates the paths in the media file list, loading them one by one and yielding grpc detect requests

    @param media_files list(str): Paths to the media files to enroll from

    @param options briar_pb2.DetectionOptions: Command line options in protobuf format which control detection functionality

    @yield: briar_service_pb2.DetectRequest
    """

    if detect_options is None:
        detect_options = briar_pb2.DetectionOptions()

    media_enum = zip(media_files)

    for i,iteration in enumerate(media_enum):
        # Dynamically break the iteration into individual components

        media_file = iteration[0]
        media_ext = os.path.splitext(media_file)[-1]
        if verbose or True:
            print("Detecting:", media_file)

        if media_ext.lower() in briar_media.BriarMedia.IMAGE_FORMATS:
            # Create an enroll request for an image
            frame = pv.Image(media_file)
            media = image_cv2proto(frame.asOpenCV2())
            media.source = os.path.abspath(media_file)
            media.frame_count = 1
            durations = briar_pb2.BriarDurations()
            durations.client_duration_file_level.start = request_start
            durations.total_duration.start = request_start

            req = srvc_pb2.DetectRequest(
                media=media,
                frame=1,
                # entry_id=detect_options.entry_id,
                # entry_type=detect_options.entry_type,
                # subject_name=detect_options.entry_name,
                durations=durations,
                detect_options=detect_options

            )
            it_end = time.time()
            req.durations.client_duration_file_level.end = it_end
            req.durations.grpc_outbound_transfer_duration.start = it_end
            req.detect_options.tracking_options.tracking_disable.value = True
            yield req

        elif media_ext.lower() in briar_media.BriarMedia.VIDEO_FORMATS:
            # Create an enroll request for a video
            video = pv.Video(media_file)
            file_level_client_time_end = time.time()
            for frame_num, frame in enumerate(video):
                durations = briar_pb2.BriarDurations()
                if frame_num == 0:  # if this is the first frame, include the durations for the file-level operations of the BRIAR client API
                    durations.client_duration_file_level.start = request_start
                    durations.client_duration_file_level.end = file_level_client_time_end
                durations.client_duration_frame_level.start = time.time()
                durations.total_duration.start = request_start
                media = image_cv2proto(frame.asOpenCV2())
                media.source = os.path.abspath(media_file)
                media.frame_number = frame_num
                media.frame_count = int(video._numframes)  # NOTE len(video) raises an error
                req = srvc_pb2.DetectRequest(
                    media=media,
                    frame=frame_num,
                    # entry_id=detect_options.entry_id,
                    # entry_type=detect_options.entry_type,
                    # subject_name=detect_options.entry_name,
                    durations=durations,
                    detect_options=detect_options
                )
                if detect_options is None:
                    req.detect_options.tracking_options.tracking_disable.value = False
                it_time = time.time()
                req.durations.client_duration_frame_level.end = it_time
                req.durations.grpc_outbound_transfer_duration.start = it_time
                yield req
