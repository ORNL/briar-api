"""!
Copyright 2021 Oak Ridge National Laboratory

The BRIAR API is divided into two primary parts, the client and the service. This, the client, is the part
which interfaces with grpc servers based off briar.service.BRIARService using the BRIARServiceStub.
The service stub contains the same methods contained in the service which, when invoked with the appropriate
request, sends said request to the service which the client is connected to, and accepts the reply containing
processed detections, extracts, templates, etc...

The BRIAR client is designed to serve as a unified interface with gRPC services which are designed after
BRIARService and implement various performer algorithms for face and body detection/extraction. From a performer
standpoint, The BRIAR client can be used as either part of the command line tools, or invoked alone as a module
"""
import grpc
import logging
import os

from briar import DEFAULT_MAX_MESSAGE_SIZE
import briar.briar_media as briar_media
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_pb2_grpc as briar_pb2_grpc
import briar.briar_grpc.briar_service_pb2 as srvc_pb2
import briar.briar_grpc.briar_service_pb2_grpc as srvc_pb2_grpc
from briar.media_converters import *
import briar.media
from briar import timing
# data processing
import numpy as np
import cv2
import pyvision as pv
import uuid
import time



class BriarClient(object):
    """!
    Provide a client to a BRIAR service. It defines and sends the messages which are sent to the connected server
    """
    DEFAULT_PORT = "127.0.0.1:50051"

    def __init__(self, options=None):
        """!
        Initialize the client and connect it to the specified server. Attempts a connection to localhost by default

        @param options optparse.Values: Options which define the connection being established
        """
        self.options = options

        if options and options.port:
            port = options.port
        else:
            port = self.DEFAULT_PORT

        if options and options.max_message_size:
            max_message_size = options.max_message_size
        else:
            max_message_size = DEFAULT_MAX_MESSAGE_SIZE


        # TODO: Do we need a reference to the channel for any reason
        # TODO: Update the options
        channel_options = [("grpc.max_send_message_length", max_message_size),
                           ("grpc.max_receive_message_length", max_message_size)]

        self.channel = grpc.insecure_channel(port,options=channel_options)
        self.stub = srvc_pb2_grpc.BRIARServiceStub(self.channel)

    ##################################################
    ## Service Functions
    ##################################################
    def get_status(self, options=None):
        """!
        Initialize the client and connect it to the specified server. Attempts a connection to localhost by default

        @param options optparse.Values: 

        @return: 5 element Tuple of str
        """
        reply = self.stub.status(srvc_pb2.StatusRequest())
        return reply.developer_name, reply.service_name, reply.version, reply.api_version, reply.status

    ##################################################
    ## Detection functions
    ##################################################
    @staticmethod
    def detect_files_iter(media_file_list):
        """!
        Iterates the paths in the media file list, loading them one by one and yielding grpc detect requests

        @param media_file_list: list of strings
        @yield: briar_service_pb2.DetectRequest
        """
        frame_id = 0
        for media_file in media_file_list:
            media_ext = os.path.splitext(media_file)[-1].lower()

            # create an image iterator
            if media_ext in briar_media.BriarMedia.IMAGE_FORMATS:
                frame = pv.Image(media_file)
                media = image_cv2proto(frame.asOpenCV2())
                media.frame_count = 1
                yield srvc_pb2.DetectRequest(media=media)

            # create a video iterator
            elif media_ext in briar_media.BriarMedia.VIDEO_FORMATS:
                video = pv.Video(media_file)
                for frame_num, frame in enumerate(video):
                    media = image_cv2proto(frame.asOpenCV2())
                    media.frame_count = int(video._numframes) # NOTE len(video) raises an error
                    yield srvc_pb2.DetectRequest(media=media,
                                                 frame=frame_num)

            else:
                print("File {} has unknown image type: {}".format(os.path.basename(media_file),
                                                                  media_ext))

            frame_id += 1

    @staticmethod
    def detect_frames_iter(frames):
        """!
        Iterates the PyVision frames, yielding detect requests

        @param frames list(pyvision.Image): Raw image data stored in a pyvision object - directly populates yield requests

        @yield: briar_service_pb2.DetectRequest
        """
        for frame_num,frame in enumerate(frames):
            yield srvc_pb2.DetectRequest(media=image_cv2proto(frame.asOpenCV2()),
                                                 frame=frame_num)

    def detect_files(self, media_file_list, options=None):
        """!
        Iterator which runs detections on the given file paths, automatically creating and yielding to detect
        requests initialized from the read images.

        @param media_file_list list(str): List of paths to the image and video files to detect on.

        @param: optparse.Values
        @param options: Additional options to feed to control the detect functions

        yield: briar_service_pb2.DetectReply containing results
        """
        media_iter = self.detect_files_iter(media_file_list)
        for reply in self.detect(media_iter, options=options):
            yield reply

    def detect_frames(self, frames, options=None):
        """!
        Runs detection on an iterable containing pyvision images.

        @param frames pyvision.Video||list(pyvision.Image): Iterable which yields pyvision.Images to run detections on

        @param options: optparse.Values
        @param options: Additional options to feed to control the detect functions

        yield: briar_service_pb2.DetectReply containing results
        """
        media_iter = self.detect_frames_iter(frames)
        for reply in self.detect(media_iter, options=options):
            yield reply

    def detect(self, detect_requests, options=None):
        """!
        Run detection on media contained in detect_requests.

        @param detect_requests Iterator yielding briar_service_pb2.DetectRequest: gRPC communication packet containing the data to run the detections on along with
                                any additional options

        @param options: optparse.Values
        @param options: Additional options to feed to control the detect functions

        yield: briar_service_pb2.DetectReply containing results
        """
        detections = list()
        detect_durations = list()

        for detect_reply in self.stub.detect(detect_requests):
            detections.append([d for d in detect_reply.detections])
            detect_durations.append(detect_reply.durations)
            self.print_verbose("Detected {} detections in {} seconds"
                               "".format(len(detect_reply.detections),
                                         timing.timeElapsed(detect_reply.durations.total_duration)))
            yield detect_reply

        self.print_verbose("Finished detect.")

    ##################################################
    ## Enhancement Functions
    ##################################################
    def enhance(self, enhance_requests, options=None):
        """!
        Run enhancement on media contained in enhance_requests.

        @param enhance_requests Iterator yielding briar_service_pb2.EnhanceRequest: gRPC communication packet containing the data to run the detections on along with
                                any additional options

        @param options: optparse.Values
        @param options: Additional options to feed to control the enhance functions

        yield: briar_service_pb2.EnhanceReply containing results
        """
        # enhancements = list()
        # enhance_durations = list()

        for enhance_reply in self.stub.enhance(enhance_requests):
            # enhancements.append(enhance_reply)
            # enhance_durations.append(enhance_reply.durations)
            self.print_verbose("Enhanced {} media in {} seconds"
                               "".format(1,
                                         timing.timeElapsed(enhance_reply.durations.total_duration)))
            yield enhance_reply

        self.print_verbose("Finished Enhancement.")

    ##################################################
    ## Tracking Functions
    ##################################################

    def track(self, track_iter):
        """!
        Track person instances contained in the tracking iterator

        @param extract_iter Generator: Generator object which yields extract requests

        @return: briar_service_pb2.ExtractReply
        """
        self.print_verbose("Beginning media extraction.")
        for reply in self.stub.track(track_iter):
            self.print_verbose("Tracked in {} seconds"
                               "".format(timing.timeElapsed(reply.durations.total_duration)))
            yield reply

    def track_files(self, media_list, detect_options = None,request_start=-1):
        """!
        Iterator which runs extracts on the given file paths, automatically creating and yielding track
        requests initialized from the read videos.

        @param media_list list(str): List of paths to the video files to extract on.

        @param detect_options briar_grpc.DetectionOptions: Detection options proto message (contains TrackOptions

        yield: briar_service_pb2.TrackReply containing results
        """
        media_iter = self.track_file_iter(media_list, detect_options=detect_options,request_start=request_start)
        for reply in self.track(media_iter):
            yield reply

    def track_file_iter(self, media_files, detect_options=None,request_start=-1):
        """!
        Iterates the paths in the media file list, loading them one by one and yielding grpc extract requests

        @param media_file_list: list of strings
        @yield: briar_service_pb2.ExtractRequest
        """

        # generate a template from the ROIs of automatically generated detections
        media_enum = zip(media_files)
        for media_file in media_files:

            media_ext = os.path.splitext(media_file)[-1].lower()
            self.print_verbose("Tracking in:", media_file)

            # create an image extract iterator
            if media_ext in briar_media.BriarMedia.IMAGE_FORMATS:
                print('skipping image ',media_file)

            # create a video extract iterator
            elif media_ext in briar_media.BriarMedia.VIDEO_FORMATS:

                video = pv.Video(media_file)
                file_level_client_time_end = time.time()
                for frame_num, frame in enumerate(video):
                    durations = briar_pb2.BriarDurations()

                    if frame_num == 0:  # if this is the first frame, include the durations for the file-level operations of the BRIAR client API
                        durations.client_duration_file_level.start = request_start
                        durations.client_duration_file_level.end = file_level_client_time_end
                    durations.client_duration_frame_level.start = time.time()
                    media = image_cv2proto(frame.asOpenCV2())
                    media.source = os.path.abspath(media_file)
                    media.frame_count = int(video._numframes) # NOTE len(video) raises an error
                    req = srvc_pb2.TrackRequest(media=media,
                                                detect_options=detect_options,
                                                durations = durations)
                    it_time = time.time()
                    req.durations.client_duration_frame_level.end = it_time
                    req.durations.grpc_outbound_transfer_duration.start = it_time
                    yield req

            else:
                print("File {} has unknown image type: {}".format(os.path.basename(media_file),
                                                                  media_ext))


    ##################################################
    ## Extract Functions
    ##################################################
    def extract_file_iter(self, media_files, det_list_list=None, detect_options=None, extract_options=None, whole_image=False,request_start = -1):
        """!
        Iterates the paths in the media file list, loading them one by one and yielding grpc extract requests

        @param media_file_list: list of strings
        @yield: briar_service_pb2.ExtractRequest
        """
        if whole_image:
            # generate a template using the entire image
            flag = briar_pb2.ExtractFlags.EXTRACT_FULL_IMAGE
            media_enum = zip(media_files)

        elif det_list_list:
            # generate a template from the ROIs of provided detections

            flag = briar_pb2.ExtractFlags.EXTRACT_PROVIDED_DETECTION
            if len(media_files) != len(det_list_list):
                raise IndexError("Error: Each Media file must have a list of detections provided")
            media_enum = zip(media_files, det_list_list)

        else:

            # generate a template from the ROIs of automatically generated detections
            flag = briar_pb2.ExtractFlags.EXTRACT_AUTO_DETECTION
            media_enum = zip(media_files)

        for i,iteration in enumerate(media_enum):
            # dynamically break out the iteration into individual components
            if det_list_list:
                media_file, det_list = iteration
            else:
                media_file = iteration[0]
                det_list = None
            media_ext = os.path.splitext(media_file)[-1].lower()
            self.print_verbose("Extracting:", media_file)

            # create an image extract iterator
            if media_ext in briar_media.BriarMedia.IMAGE_FORMATS:
                req = srvc_pb2.ExtractRequest()
                frame = pv.Image(media_file)
                media = image_cv2proto(frame.asOpenCV2())
                media.source = os.path.abspath(media_file)
                media.frame_count = 1
                durations = briar_pb2.BriarDurations()
                durations.client_duration_file_level.start = request_start

                req = srvc_pb2.ExtractRequest(media=media,
                                         detections=det_list,
                                         detect_options=detect_options,
                                         durations=durations,
                                         extract_options=extract_options)
                req.detect_options.tracking_options.tracking_disable.value = True
                it_end = time.time()
                req.durations.client_duration_file_level.end = it_end
                req.durations.grpc_outbound_transfer_duration.start = it_end
                yield req
            # create a video extract iterator
            elif media_ext in briar_media.BriarMedia.VIDEO_FORMATS:
                video = pv.Video(media_file)
                file_level_client_time_end = time.time()

                for frame_num, frame in enumerate(video):
                    durations = briar_pb2.BriarDurations()
                    if frame_num == 0:  # if this is the first frame, include the durations for the file-level operations of the BRIAR client API
                        durations.client_duration_file_level.start = request_start
                        durations.client_duration_file_level.end = file_level_client_time_end

                    durations.client_duration_frame_level.start = time.time()

                    media = image_cv2proto(frame.asOpenCV2())
                    media.source = os.path.abspath(media_file)
                    media.frame_number = frame_num
                    media.frame_count = int(video._numframes) # NOTE len(video) raises an error
                    req = srvc_pb2.ExtractRequest(media=media,
                                         detections=det_list,
                                         detect_options=detect_options,
                                         durations=durations,
                                         extract_options=extract_options)
                    if detect_options is None:
                        req.detect_options.tracking_options.tracking_disable.value = False
                    it_time = time.time()
                    req.durations.client_duration_frame_level.end = it_time
                    req.durations.grpc_outbound_transfer_duration.start = it_time
                    yield req

            else:
                print("File {} has unknown image type: {}".format(os.path.basename(media_file),
                                                                  media_ext))

    def extract_frames_iter(self, frame_list):
        """!
        Iterates the PyVision frames, yielding extract requests

        @param frame_list list(pyvision.Image): Raw image data stored in a pyvision object - directly populates requests yielded

        @yield: briar_service_pb2.ExtractRequest
        """
        for frame in frame_list:
            media = image_cv2proto(frame.asOpencv2())
            if isinstance(media, pv.Image):
                media.frame_count = 1
            elif isinstance(media, pv.Video):
                media.frame_count = media._numframes # NOTE len(video) raises an error
            else:
                raise TypeError("Passed frame is not a valid type. Must be a pyvision Image or video")
            yield srvc_pb2.ExtractRequest(media=media,
                                          flag=briar_pb2.ExtractFlags.EXTRACT_FULL_IMAGE)

    def extract_files(self, media_list, det_list_list=None, detect_options = None, extract_options = None, whole_image=False,request_start = -1):
        """!
        Iterator which runs extracts on the given file paths, automatically creating and yielding extract
        requests initialized from the read images.

        @param media_list list(str): List of paths to the image and video files to extract on.

        @param det_list_list list(list(briar_pb2.Detection)): If not None, it will contains 1 list of detections per media file

        @param boolean: Ignore detections and run an extract on the whole image

        yield: briar_service_pb2.ExtractReply containing results
        """
        if whole_image:
            self.print_verbose("Extracting from whole image")
        elif det_list_list:
            self.print_verbose("Extracting from provided detections")
        else:
            self.print_verbose("Extracting from auto-detection")
        media_iter = self.extract_file_iter(media_list, det_list_list=det_list_list,detect_options=detect_options,extract_options=extract_options,
                                            whole_image=whole_image,request_start = request_start)
        for reply in self.extract(media_iter):
            yield reply

    def extract_files(self, media_list, det_list_list=None, detect_options = None, extract_options = None, whole_image=False,request_start = -1):
        """!
        Iterator which runs extracts on the given file paths, automatically creating and yielding extract
        requests initialized from the read images.

        @param media_list list(str): List of paths to the image and video files to extract on.

        @param det_list_list list(list(briar_pb2.Detection)): If not None, it will contains 1 list of detections per media file

        @param boolean: Ignore detections and run an extract on the whole image

        yield: briar_service_pb2.ExtractReply containing results
        """
        if whole_image:
            self.print_verbose("Extracting from whole image")
        elif det_list_list:
            self.print_verbose("Extracting from provided detections")
        else:
            self.print_verbose("Extracting from auto-detection")
        media_iter = self.extract_file_iter(media_list, det_list_list=det_list_list,detect_options=detect_options,extract_options=extract_options,
                                            whole_image=whole_image,request_start = request_start)
        for reply in self.extract(media_iter):
            yield reply

    def extract_frames(self, frame_list, det_list_list, whole_image):
        """!
        Iterator which runs extracts on the given frames, automatically creating and yielding extract
        requests initialized from the read images.

        @param frame_list list(pyvision.Image): List containing data to extract on.

        @param det_list_list list(list(briar_pb2.Detection): If not None, it will contains 1 list of detections per media file

        @param boolean: Ignore detections and run an extract on the whole image

        yield: briar_service_pb2.ExtractReply containing results
        """
        self.print_verbose("Extracting {} whole images".format(len(frame_list)))
        media_iter = self.extract_frames_iter(frame_list, det_list_list=det_list_list,
                                              whole_image=whole_image)
        for reply in self.extract(media_iter):
            yield reply

    def extract(self, extract_iter):
        """!
        Extract images contained in the extract iterator

        @param extract_iter Generator: Generator object which yields extract requests

        @return: briar_service_pb2.ExtractReply
        """
        self.print_verbose("Beginning media extraction.")

        for reply in self.stub.extract(extract_iter):
            self.print_verbose("Extracted in {} seconds"
                               "".format(timing.timeElapsed(reply.durations.total_duration)))
            yield reply


    ##################################################
    ## Enroll Functions
    ##################################################
    def enroll_file_iter(self, database_name, media_files,detect_options=None, extract_options=None, enroll_options=None, det_list_list=None, whole_image=False,request_start=-1):
        """!
        Iterates the paths in the media file list, loading them one by one and yielding grpc enroll requests

        @param database_name str: Name of the database to enroll templates in

        @param media_files list(str): Paths to the media files to enroll from

        @param options briar_pb2.DetectionOptions: Command line options in protobuf format which control detection functionality

        @param options briar_pb2.ExtractOptions: Command line options in protobuf format which control extraction functionality

        @param options briar_pb2.EnrollOptions: Command line options in protobuf format which control enrollment functionality

        @param det_list_list list(list(briar_pb2.Detection)): If not None, it will contains 1 list of detections per media file

        @param boolean: Ignore detections and run an extract on the whole image

        @yield: briar_service_pb2.EnrollRequest
        """

        if detect_options is None:
            detect_options = briar_pb2.DetectionOptions()
        if extract_options is None:
            extract_options = briar_pb2.ExtractOptions()
        if enroll_options is None:
            enroll_options = briar_pb2.EnrollOptions()

        if whole_image:
            # flag = briar_pb2.EnrollFlags.ENROLL_FULL_IMAGE
            media_enum = zip(media_files)
        elif det_list_list:
            # flag = briar_pb2.EnrollFlags.EXTRACT_PROVIDED_DETECTION
            media_enum = zip(media_files, det_list_list)
        else:
            # flag = briar_pb2.EnrollFlags.ENROLL_AUTO_DETECTION
            media_enum = zip(media_files)

        database = briar_pb2.BriarDatabase(name=database_name)
        for iteration in media_enum:
            # Dynamically break the iteration into individual components
            if det_list_list:
                media_file, detections = iteration
            else:
                media_file = iteration[0]
                detections = None
            media_ext = os.path.splitext(media_file)[-1]
            self.print_verbose("Enrolling:", media_file)

            if media_ext.lower() in briar_media.BriarMedia.IMAGE_FORMATS:
                # Create an enroll request for an image
                frame = pv.Image(media_file)
                media = image_cv2proto(frame.asOpenCV2())
                media.source = os.path.abspath(media_file)
                media.frame_count = 1
                durations = briar_pb2.BriarDurations()
                durations.client_duration_file_level.start = request_start
                req = srvc_pb2.EnrollRequest(database=database,
                                             media=media,
                                             subject_id=enroll_options.subject_id,
                                             media_id=enroll_options.media_id,
                                             subject_name=enroll_options.subject_name,
                                             detections=detections,
                                             detect_options=detect_options,
                                             extract_options=extract_options,
                                             durations=durations,
                                             enroll_options=enroll_options)
                req.detect_options.tracking_options.tracking_disable.value = True
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
                    if frame_num == 0:  # if this is the first frame, include the durations for the file-level operations of the BRIAR client API
                        durations.client_duration_file_level.start = request_start
                        durations.client_duration_file_level.end = file_level_client_time_end

                    durations.client_duration_frame_level.start = time.time()
                    media = image_cv2proto(frame.asOpenCV2())
                    media.source = os.path.abspath(media_file)
                    media.frame_number = frame_num
                    media.frame_count = int(video._numframes)  # NOTE len(video) raises an error
                    # media_metadata = briar_pb2.MediaMetadata(attributes=[briar_pb2.Attribute(key="start_frame",ivalue=video.start_frame),
                    #              briar_pb2.Attribute(key="stop_frame",ivalue=video.stop_frame)])
                    # media.metadata.MergeFrom(media_metadata)
                    # print('media metadat:',media.metadata)
                    req = srvc_pb2.EnrollRequest(database=database,
                                                 media=media,
                                                 subject_id=enroll_options.subject_id,
                                                 media_id=enroll_options.media_id,
                                                 subject_name=enroll_options.subject_name,
                                                 detections=det_list_list,
                                                 detect_options=detect_options,
                                                 extract_options=extract_options,
                                                 durations=durations,
                                                 enroll_options=enroll_options)
                    it_time = time.time()
                    req.durations.client_duration_frame_level.end = it_time
                    req.durations.grpc_outbound_transfer_duration.start = it_time
                    yield req

    ##################################################
    ## Enroll Functions
    ##################################################
    def enroll_frames_iter(self, database_name, video, detect_options=None, extract_options=None, enroll_options=None, det_list_list=None, whole_image=False,request_start=-1):
        # print("enroll_frames_iter started")
        """!
        Iterates the paths in the media file list, loading them one by one and yielding grpc enroll requests

        @type database_name: str
        @param database_name: Name of the database to enroll templates in

        @type video: an iterator that generates cv2 frames
        @param media_files: Paths to the media files to enroll from

        @type detect_options: briar_pb2.DetectionOptions
        @param options: Command line options in protobuf format which control detection functionality

        @type optons: briar_pb2.ExtractOptions
        @param options: Command line options in protobuf format which control extraction functionality

        @type optons: briar_pb2.EnrollOptions
        @param options: Command line options in protobuf format which control enrollment functionality

        @type det_list_list: List of list of briar_pb2.Detection
        @param det_list_list: If not None, it will contains 1 list of detections per media file

        @type whole_image: boolean
        @param: Ignore detections and run an extract on the whole image

        @yield: briar_service_pb2.EnrollRequest
        """
        # print("enroll_frames_iter started")
        if detect_options is None:
            detect_options = briar_pb2.DetectionOptions()
        if extract_options is None:
            extract_options = briar_pb2.ExtractOptions()
        if enroll_options is None:
            enroll_options = briar_pb2.EnrollOptions()
        database = briar_pb2.BriarDatabase(name=database_name)
        file_level_client_time_end = time.time()
        # Create an enroll request for a video
        for frame_num, frame in enumerate(video):
            media = image_cv2proto(frame)
            media.source = video.filepath
            media.frame_number = frame_num
            durations = briar_pb2.BriarDurations()
            if frame_num == 0:  # if this is the first frame, include the durations for the file-level operations of the BRIAR client API
                durations.client_duration_file_level.start = request_start
                durations.client_duration_file_level.end = file_level_client_time_end

            durations.client_duration_frame_level.start = time.time()
            media_metadata = briar_pb2.MediaMetadata(
                attributes=[briar_pb2.Attribute(key="start_frame", ivalue=video.start_frame,type=briar_pb2.BriarDataType.INT),
                            briar_pb2.Attribute(key="stop_frame", ivalue=video.stop_frame,type=briar_pb2.BriarDataType.INT)])
            media.metadata.MergeFrom([media_metadata])
            # print('media metadat:', media.metadata)
            try:
                media.frame_count = len(video)  # NOTE len(video) raises an error
            except:
                pass
            req = srvc_pb2.EnrollRequest(database=database,
                                            media=media,
                                            subject_id=enroll_options.subject_id,
                                            media_id=enroll_options.media_id,
                                            subject_name=enroll_options.subject_name,
                                            detections=det_list_list,
                                            detect_options=detect_options,
                                            extract_options=extract_options,
                                            durations=durations,
                                            enroll_options=enroll_options)
            if isinstance(video,briar.media.ImageIterator):
                req.detect_options.tracking_options.tracking_disable.value = True
            else:
                req.detect_options.tracking_options.tracking_disable.value = False
            it_time = time.time()
            req.durations.client_duration_frame_level.end = it_time
            req.durations.grpc_outbound_transfer_duration.start = it_time
            yield req

    def enroll_files(self, database, file_list, detect_options=None,extract_options=None,enroll_options=None, det_list_list=None, whole_image=False,request_start=-1):
        """!
        Iterator which enrolls images from the given file paths, automatically creating and yielding enroll
        requests initialized from the read images.

        @param database str: Specifies which database to enroll in

        @param file_list list(str): List of paths to the image and video files to extract on.

        @param options optparse.Values: Command line options which control enrollment functionality

        @param det_list_list list(list(briar_pb2.Detection)): If not None, it will contains 1 list of detections per media file

        @param boolean: Ignore detections and run an extract on the whole image

        yield: briar_service_pb2.ExtractReply containing results
        """
        enroll_iter = self.enroll_file_iter(database, file_list, detect_options,extract_options,enroll_options, det_list_list, whole_image,request_start=request_start)
        for reply in self.enroll(enroll_iter):
            yield reply

    @staticmethod
    def _enroll_frames_iter(frame_list, database_name, subject_name, subject_id, media_id):
        """!
        Iterates the PyVision frames, yielding enroll requests

        @param frame_list list(pyvision.Image): Raw image data stored in a pyvision object - directly populates requests yielded

        @param database_name str: Database to enroll int

        @param subject_name str: Name of subject to enroll

        @param subject_id str: Uid of subject to enroll

        @param media_id str: Uid of media being enrolled # TODO media id does nothing

        @yield: briar_service_pb2.EnrollRequest
        """
        for frame_num, frame in enumerate(frame_list):
            request = srvc_pb2.EnrollRequest(media=image_cv2proto(frame.asOpenCV2()), frame=frame_num)
            if subject_id is not None:
                request.subject_id = str(subject_id)
            if media_id is not None:
                request.media_id = str(media_id)
            if subject_name is not None:
                request.subject_name = str(subject_name)
            request.database.name = str(database_name)
            yield request

    @staticmethod
    def _enroll_frames_iter2(frame_iter, database_name, subject_id,media_id, detect_options, extract_options, enroll_options, subject_name=None, record=None):
        """!
        Iterates the PyVision frames, yielding enroll requests

        @param frame_list list(pyvision.Image): Raw image data stored in a pyvision object - directly populates requests yielded

        @param database_name str: Database to enroll int

        @param subject_name str: Name of subject to enroll

        @param subject_id str: Uid of subject to enroll

        @param media_id str: Uid of media being enrolled # TODO media id does nothing

        @yield: briar_service_pb2.EnrollRequest
        """
        print('AAAAA')
        for frame_num, frame in enumerate(frame_iter):
            if isinstance(frame,pv.Image):
                frame = frame.asOpenCV2()
            while frame.shape[0] > 1500:
                print("Warning: Reducing large frame", frame.shape)
                frame= frame[::2,::2,:].copy()
            request = srvc_pb2.EnrollRequest(media=image_cv2proto(frame), frame=frame_num, subject_id=subject_id,media_id=media_id, detect_options=detect_options, extract_options=extract_options, enroll_options=enroll_options, record=record, subject_name=subject_name)
            print('Enroll sending', frame_num, frame.shape)
            yield request

    def enroll_frames(self, database_name, frame_list, subject_name=None, subject_id=None, media_id=None, options=None):
        """!
        Iterator which runs enrolls on the included frames, automatically creating and yielding enroll
        requests initialized from the read images.

        @param database_name str: Name of the database to enroll into

        @param frame_list list(pyvision.Image) or other iterable which yields pyvision.Image: List containing data to extract on.

        @param subject_name str: Name of subject to enroll

        @param subject_id str: Uid of the subject to enroll

        @param media_id str: Uid of the media

        @param options optparse.Values: Command line options which control enrollment functionality

        yield: briar_service_pb2.EnrollReply containing results
        """
        media_iter = self.enroll_frames_iter(frame_list, database_name, subject_id, media_id)
        for reply in self.enroll(media_iter):
            yield reply

    def enroll_frames2(self, frame_iter, database_name, subject_id, media_id, entity_type, detect_options, extract_options, enroll_options, subject_name=None, record=None):
        """!
        Iterator which runs enrolls on the included frames, automatically creating and yielding enroll
        requests initialized from the read images.

        @param database_name str: Name of the database to enroll into

        @param frame_iter list(pyvision.Image) or other iterable which yields pyvision.Image: List containing data to extract on.

        @param subject_name str: Name of subject to enroll

        @param subject_id str: Uid of the subject to enroll

        @param media_id str: Uid of the media

        @param options optparse.Values: Command line options which control enrollment functionality

        yield: briar_service_pb2.EnrollReply containing results
        """
        print('CCCCCC')
        media_iter = self._enroll_frames_iter2(frame_iter, database_name, subject_id, media_id, entity_type, detect_options, extract_options, enroll_options, subject_name=subject_name, record=record)
        
        #for each in media_iter:
        #    each.media.CopyFrom(briar_pb2.BriarMedia())
        #    print( each )
        for reply in self.enroll(media_iter):
            yield reply

    def enroll(self, enroll_iter):
        """!
        Enroll images contained in the enroll iterator

        @param enroll_iter Generator: Generator object which yields enroll requests

        @return: briar_service_pb2.ExtractReply
        """
        for enroll_reply in self.stub.enroll(enroll_iter):
            yield enroll_reply
        self.print_verbose("Finished enroll.")

    ##################################################
    ## Verify Functions
    ##################################################
    def verify(self, flag, reference_media=None, verification_media=None, reference_dets=None,
               verification_dets=None, reference_tmpls=None, verification_tmpls=None):
        """!
        Either takes probe templates or generates them from provided media and compares them against the
        'verification' variables of a matching type. I.e. templates<->templates, media<->media, etc.

        @param flag int briar_pb2.VerifyFlags: Tells the service details about the media it is going to verify
                     perform detections on the images then extract and verify, should it use existing dets,
                     or should it use the provided templates to verify

        @param reference_media briar_pb2.BriarMedia: This media is where the the probe templates will be pulled from

        @param verification_media briar_pb2.BriarMedia: This media is where the comparison templates will be pulled from

        @param reference_dets List of briar_pb2.Detection: These are the detections to extract probe templates from

        @param verification_dets List of briar_pb2.Detection: These are the detections to extract comparison templates from

        @param reference_tmpls list(briar_pb2.Template): Probe templates

        @param verification_tmpls list(briar_pb2.Template): Comparison Templates

        @return: 2 element Tuple (briar_pb2.MatchSimilarities, briar_pb2.BriarDurations)
        """
        """
        TODO Currently, this can only compare templates<->templates, detections<->detections, media<->media
        TODO Ideally any combination should be able to be compared, i.e. template<->media, detection<->template, etc.
        """
        if reference_media == None:
            reference_media = list()
        if verification_media == None:
            verification_media = list()
        if reference_dets == None:
            reference_dets = list()
        if verification_dets == None:
            verification_dets = list()
        if reference_tmpls == None:
            reference_tmpls = list()
        if verification_tmpls == None:
            verification_tmpls = None

        ver_kwargs = dict(flag=flag)
        if flag == briar_pb2.VerifyFlags.VERIFY_FULL_IMAGE:
            ver_kwargs["reference_media"] = reference_media
            ver_kwargs["verification_media"] = verification_media
        elif flag == briar_pb2.VerifyFlags.VERIFY_PROVIDED_DETECTIONS:
            ver_kwargs["reference_dets"] = reference_dets
            ver_kwargs["verification_dets"] = verification_dets
            ver_kwargs["reference_media"] = reference_media
            ver_kwargs["verification_media"] = verification_media
        elif flag == briar_pb2.VerifyFlags.VERIFY_PROVIDED_TEMPLATES:
            ver_kwargs["reference_tmpls"] = reference_tmpls
            ver_kwargs["verification_tmpls"] = verification_tmpls
        else:
            raise ValueError("Unknown Verify Flag Type")

        # TODO make this a bi-directional stream
        verify_req = srvc_pb2.VerifyRequest(**ver_kwargs)
        verify_repl = self.stub.verify(verify_req)
        return verify_repl.similarities, verify_repl.durations

    def verify_files(self, reference_file, verify_file, detect_options=None,extract_options=None,verify_options=None,verify_templates=None, det_list_list=None, whole_image=False,request_start=-1):
        """!
        Iterator which verifies images or videos from the given file paths, automatically creating and yielding enroll
        requests initialized from the read images.

        @type reference_media_files: File path string of reference media
        @param reference_media_files: File path string to the media that act as the reference media to be verify against

        @type verify_media_files: File path string
        @param verify_media_files: File path string of the media file that requires verification

        @type options: optparse.Values
        @param options: Command line options which control enrollment functionality

        @type det_list_list: List of list of briar_pb2.Detection
        @param det_list_list: If not None, it will contains 1 list of detections per media file

        @type whole_image: boolean
        @param: Ignore detections and run an extract on the whole image

        yield: briar_service_pb2.VerifyReply containing results
        """
        print('THE FILES',reference_file,verify_file)
        verify_iter = self.verify_file_iter(reference_file, verify_file, detect_options,extract_options,verify_options,verify_templates,det_list_list, whole_image,request_start=request_start)
        return self.stub.verify(verify_iter) #TODO:change this to the built in verify client function
        # return self.verify(verify_iter)

    def verify_file_iter(self, reference_media_file, verify_media_file,detect_options=None, extract_options=None, verify_options=None, verify_templates=None,det_list_list=None, whole_image=False,request_start=-1):
        """!
        Iterates the paths in the media file list, loading them one by one and yielding grpc verification requests

        @type reference_media_file: File path as string
        @param reference_media_file: File path as string to the media file that acts as the reference media to be verify against

        @type verify_media_file: File path as string
        @param verify_media_file: File path as string to the media file that requires verification, should be of same length as reference_media_files

        @type detect_options: briar_pb2.DetectionOptions
        @param options: Command line options in protobuf format which control detection functionality

        @type extract_optons: briar_pb2.ExtractOptions
        @param options: Command line options in protobuf format which control extraction functionality

        @type earch_optons: briar_pb2.SearchOptions
        @param options: Command line options in protobuf format which control search functionality

        @type det_list_list: List of list of briar_pb2.Detection
        @param det_list_list: If not None, it will contains 1 list of detections per media file

        @type whole_image: boolean
        @param: Ignore detections and run an extract on the whole image

        @yield: briar_service_pb2.EnrollRequest
        """

        if detect_options is None:
            detect_options = briar_pb2.DetectionOptions()
        if extract_options is None:
            extract_options = briar_pb2.ExtractOptions()
        if verify_options is None:
            verify_options = briar_pb2.VerifyOptions()


        self.print_verbose("Verifying:", verify_media_file, ' against ', reference_media_file)

        for media_file,role in zip((reference_media_file,verify_media_file),(srvc_pb2.VerifyRequest.VerifyRole.reference,srvc_pb2.VerifyRequest.VerifyRole.verify)):
            print('MAKING A REQUEST FOR',media_file,role)
            media_ext = os.path.splitext(media_file)[-1]
            if media_ext.lower() in briar_media.BriarMedia.IMAGE_FORMATS:
                # Create an enroll request for an image
                frame = pv.Image(media_file)
                media = image_cv2proto(frame.asOpenCV2())
                media.source = os.path.abspath(media_file)
                media.frame_count = 1
                durations = briar_pb2.BriarDurations()
                durations.client_duration_file_level.start = request_start
                req = srvc_pb2.VerifyRequest(media=media,
                                                    detect_options=detect_options,
                                                    extract_options=extract_options,
                                                    verify_options=verify_options,
                                                    durations=durations,
                                                    role = role
                                                    )
                req.detect_options.tracking_options.tracking_disable.value = True
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
                    if frame_num == 0:  # if this is the first frame, include the durations for the file-level operations of the BRIAR client API
                        durations.client_duration_file_level.start = request_start
                        durations.client_duration_file_level.end = file_level_client_time_end
                    durations.client_duration_frame_level.start = time.time()
                    im = frame.asOpenCV2()
                    media = image_cv2proto(im)

                    media.frame_count = int(video._numframes)  # NOTE len(video) raises an error
                    media.source = os.path.abspath(media_file)
                    media.frame_number = frame_num
                    req = srvc_pb2.VerifyRequest(media=media,
                                                 detect_options=detect_options,
                                                 extract_options=extract_options,
                                                 verify_options=verify_options,
                                                 durations=durations,
                                                 role=role)
                    req.detect_options.tracking_options.tracking_disable.value = False
                    it_time = time.time()
                    req.durations.client_duration_frame_level.end = it_time
                    req.durations.grpc_outbound_transfer_duration.start = it_time
                    yield req


    ##################################################
    ## Search Functions
    ##################################################
    def search(self, search_iter):#database_name, media=None,detect_options=briar_pb2.DetectionOptions(),extract_options=briar_pb2.ExtractOptions(),search_options=briar_pb2.SearchOptions(), search_templates=None, detections=None):
        """!
        Given a probe, search the database and return matches

        @param database_name str: Name of the database to search

        @param media briar_pb2.BriarMedia: Media to pull probes from

        @param search_templates briar_pb2.Template: Probe Template

        @param detections briar_pb2.Detection: Detections to extract probe templates from

        @param flag int, briar_pb2.SearchFlags: Tells search whether to use auto-detect, extract detections, or provided templates,

        @return: briar_service_pb2.SearchReply
        """
        for search_reply in self.stub.search(search_iter):
            yield search_reply
        self.print_verbose("Finished Search.")


    def search_file_iter(self, database_name, media_files,detect_options=None, extract_options=None, search_options=None, search_templates=None,det_list_list=None, whole_image=False,request_start=-1):
        """!
        Iterates the paths in the media file list, loading them one by one and yielding grpc search requests

        @type database_name: str
        @param database_name: Name of the database to enroll templates in

        @type media_files: List of strings
        @param media_files: Paths to the media files to enroll from

        @type detect_options: briar_pb2.DetectionOptions
        @param options: Command line options in protobuf format which control detection functionality

        @type extract_optons: briar_pb2.ExtractOptions
        @param options: Command line options in protobuf format which control extraction functionality

        @type earch_optons: briar_pb2.SearchOptions
        @param options: Command line options in protobuf format which control search functionality

        @type det_list_list: List of list of briar_pb2.Detection
        @param det_list_list: If not None, it will contains 1 list of detections per media file

        @type whole_image: boolean
        @param: Ignore detections and run an extract on the whole image

        @yield: briar_service_pb2.EnrollRequest
        """

        if detect_options is None:
            detect_options = briar_pb2.DetectionOptions()
        if extract_options is None:
            extract_options = briar_pb2.ExtractOptions()
        if search_options is None:
            search_options = briar_pb2.SearchOptions()

        if whole_image:
            # flag = briar_pb2.EnrollFlags.ENROLL_FULL_IMAGE
            media_enum = zip(media_files)
        elif det_list_list:
            # flag = briar_pb2.EnrollFlags.EXTRACT_PROVIDED_DETECTION
            media_enum = zip(media_files, det_list_list)
        else:
            # flag = briar_pb2.EnrollFlags.ENROLL_AUTO_DETECTION
            media_enum = zip(media_files)

        database = briar_pb2.BriarDatabase(name=database_name)
        for iteration in media_enum:
            # Dynamically break the iteration into individual components
            if det_list_list:
                media_file, detections = iteration
            else:
                media_file = iteration[0]
                detections = None
            media_ext = os.path.splitext(media_file)[-1]
            self.print_verbose("Searching:", media_file)

            if media_ext.lower() in briar_media.BriarMedia.IMAGE_FORMATS:
                # Create an enroll request for an image
                frame = pv.Image(media_file)
                media = image_cv2proto(frame.asOpenCV2())
                media.source = os.path.abspath(media_file)
                media.frame_count = 1
                durations = briar_pb2.BriarDurations()
                durations.client_duration_file_level.start = request_start
                probes = briar_pb2.TemplateList(tmpls=search_templates)
                req = srvc_pb2.SearchRequest(media=media,
                                                    database=database,
                                                    probes=probes,
                                                    detections=detections,
                                                    detect_options=detect_options,
                                                    extract_options=extract_options,
                                                    durations=durations,
                                                    search_options=search_options)
                req.detect_options.tracking_options.tracking_disable.value = True
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
                    if frame_num == 0:  # if this is the first frame, include the durations for the file-level operations of the BRIAR client API
                        durations.client_duration_file_level.start = request_start
                        durations.client_duration_file_level.end = file_level_client_time_end
                    durations.client_duration_frame_level.start = time.time()

                    media = image_cv2proto(frame.asOpenCV2())
                    media.frame_count = int(video._numframes)  # NOTE len(video) raises an error
                    media.source = os.path.abspath(media_file)
                    probes = briar_pb2.TemplateList(tmpls=search_templates)
                    media.frame_number = frame_num
                    req = srvc_pb2.SearchRequest(media=media,
                                                        database=database,
                                                        probes=probes,
                                                        detections=detections,
                                                        detect_options=detect_options,
                                                        extract_options=extract_options,
                                                        durations = durations,
                                                        search_options=search_options)
                    req.detect_options.tracking_options.tracking_disable.value = False
                    it_time = time.time()
                    req.durations.client_duration_frame_level.end = it_time
                    req.durations.grpc_outbound_transfer_duration.start = it_time
                    yield req

    def search_files(self, database, file_list, detect_options=None,extract_options=None,search_options=None,search_templates=None, det_list_list=None, whole_image=False,request_start=-1):
        """!
        Iterator which searches images or videos from the given file paths, automatically creating and yielding enroll
        requests initialized from the read images.

        @type database: str
        @param database: Specifies which database to enroll in

        @type file_list: List of str
        @param file_list: List of paths to the image and video files to extract on.

        @type options: optparse.Values
        @param options: Command line options which control enrollment functionality

        @type det_list_list: List of list of briar_pb2.Detection
        @param det_list_list: If not None, it will contains 1 list of detections per media file

        @type whole_image: boolean
        @param: Ignore detections and run an extract on the whole image

        yield: briar_service_pb2.ExtractReply containing results
        """
        search_iter = self.search_file_iter(database, file_list, detect_options,extract_options,search_options,search_templates,det_list_list, whole_image,request_start=request_start)
        for reply in self.search(search_iter):
            yield reply



    ##################################################
    ## Database functions
    ##################################################
    def get_database_names(self):
        """!
        Gets a list of names from the service representing the databases human readable names

        @return: 2 element Tuple (List of str, briar_pb2.Durations)
        """
        names_reply = self.stub.database_names(srvc_pb2.DatabaseNamesRequest())
        return names_reply.database_names, names_reply.durations

    def database_list_templates(self, database_name):
        """!
        Lists the templates stored inside the given database name

        @param database_name str: Name of the database to get the templates from

        @return: 2 element tuple (list of str, briar_pb2.Durations)
        """
        list_reply = self.stub.database_list_templates(srvc_pb2.DatabaseListRequest(database_name=database_name))
        return list_reply.template_ids, list_reply.durations

    def database_remove_templates(self, database_name, template_ids):
        """!
        Remove templates matching the ids from the database

        @param database_name str: Name of the database to remove from

        @param template_ids list(str): Ids of the templates to remove

        @return: briar_pb2.BriarDurations
        """
        database = briar_pb2.BriarDatabase(name=database_name)
        rem_req = srvc_pb2.DatabaseRemoveTmplsRequest(database=database,
                                                     ids=template_ids)
        reply = self.stub.database_remove_templates(rem_req)
        return reply.durations

    def finalize(self, database_name):
        """!
        Write the given database to disk on the server on which it is running.

        @param database_name str: Name of the database to write to disk

        @return: briar_pb2.durations
        """
        database = briar_pb2.BriarDatabase(name=database_name)
        finalize_req = srvc_pb2.DatabaseFinalizeRequest(database=database)
        finalize_reply = self.stub.database_finalize(finalize_req)
        return finalize_reply.durations

    ##################################################
    ## Database functions: Retrieve
    ##################################################
    def retrieve_req_iter(self, database_name, template_ids):
        """!
        Generator which yields retrieve requests

        @param database_name str: Name of the database to retrieve from

        @param template_ids list(str): The templates to retrieve

        @return: briar_service_pb2.DatabaseRetrieveRequest
        """
        for id in template_ids:
            dbase = briar_pb2.BriarDatabase(name=database_name)
            ids = briar_pb2.TemplateIds(ids=[id], length=1)
            yield srvc_pb2.DatabaseRetrieveRequest(database=dbase, ids=ids)

    def database_retrieve(self, database_name, template_ids):
        """!
        Iteratively grab and return templates matching template_ids from the database.

        @param database_name str: Name of the database to retrieve from 

        @param template_ids list(str): List of ids to retrieve from the database

        @return: 2 element Tuple (briar_pb2.Template, briar_pb2.BriarDurations
        """
        ret_iter = self.retrieve_req_iter(database_name, template_ids.ids)
        for retrieve_reply in self.stub.database_retrieve(ret_iter):
            yield retrieve_reply.templates.tmpls, retrieve_reply.durations

    ##################################################
    ## Database functions: Insert
    ##################################################
    def database_insert(self, database_name, template_list, template_ids):
        """!
        Insert the given templates and ids into the database
        # TODO remove template_ids: is superfluous - template_list is all that is needed
        # TODO Insert should automatically generate template ids for templates with no ids and return new ids

        @param database_name str: Name of the database to insert into

        @param template_list: List of briar_pb2.Template
        @param template_list: Templates to insert into database

        @param template_ids: List of str
        @param template_ids: IDs of templates being inserted

        @return: 2 element Tuple (list of str, briar_pb2.BriarDurations
        """
        database = briar_pb2.BriarDatabase(name=database_name)
        insert_req = srvc_pb2.DatabaseInsertRequest(database=database,
                                                   tmpls=template_list,
                                                   ids=template_ids)
        insert_reply = self.stub.database_insert(insert_req)
        return insert_reply.ids, insert_reply.durations

    ##################################################
    ## Database functions: Load/Create
    ##################################################
    def load_database(self, database_name):
        """!
        Load the database from disk into memory

        @param database_name str: Name of database to load

        @return: 3 element Tuple(list of str, list of records, briar_pb2.BriarDurations)
        """
        load_req = srvc_pb2.DatabaseLoadRequest(database_name=database_name)
        load_reply = self.stub.database_load(load_req)
        return load_reply.ids, load_reply.records, load_reply.durations

    def database_create(self, database_name):
        """!
        Creates an empty database of the given name

        @param database_name str: Name of database to create

        @return: briar_pb2.BriarDurations
        """
        create_req = srvc_pb2.DatabaseCreateRequest(database_name=database_name)
        create_reply = self.stub.database_create(create_req)
        return create_reply.durations

    ##################################################
    ## Utility Functions:
    ##################################################
    def print_verbose(self, *args):
        """!
        Simple helper function to print only when the verbose client is given the verbose flag

        @param args tuple(object): Arguments to get passed to print

        @return: None - outputs to screen
        """
        if self.options and self.options.verbose:
            print(*args)
