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
import asyncio
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_pb2_grpc as briar_pb2_grpc
import briar.briar_grpc.briar_service_pb2 as srvc_pb2
import briar.briar_grpc.briar_service_pb2_grpc as srvc_pb2_grpc
import briar.briar_media as briar_media
import briar.media
import cv2
import grpc
import atexit
import logging
# data processing
import numpy as np
import os
import pyvision as pv
import time
import uuid
from briar import DEFAULT_MAX_MESSAGE_SIZE
from briar import timing
from briar.media import VideoIterator, ImageIterator, ImageGenerator, MediaSetIterator, frame_iter
from briar.media import enroll_frames_iter as enroll_frames_iter_media
from briar.media import enroll_frames_iter_async as enroll_frames_iter_media_async
from briar.media_converters import *
from briar.media import ThreadedVideoIterator
from tqdm import tqdm

# Each worker process initializes a single channel after forking.
# It's regrettable, but to ensure that each subprocess only has to instantiate
# a single channel to be reused across all RPCs, we use globals.
_worker_channel_singleton = None
_worker_stub_singleton = None
_worker_thread_position_singleton = None
_worker_proccess_position_singleton = None
_client_identifier_singleton = None
class BriarClient(object):
    """!
    Provide a client to a BRIAR service. It defines and sends the messages which are sent to the connected server
    """
    DEFAULT_PORT = "0.0.0.0:50051"

    def __init__(self, options=None,reused_channel=None,reused_stub=None):
        """!
        Initialize the client and connect it to the specified server. Attempts a connection to localhost by default

        @param options optparse.Values: Options which define the connection being established
        """
        self.options = options

        if options and options.port:
            port = options.port
        else:
            port = self.DEFAULT_PORT
        self.port = port
        if options and options.max_message_size:
            max_message_size = options.max_message_size
        else:
            max_message_size = DEFAULT_MAX_MESSAGE_SIZE

        # TODO: Do we need a reference to the channel for any reason
        # TODO: Update the options

        if reused_channel is not None:
            self.channel = reused_channel
        if reused_stub is not None:
            self.stub = reused_stub

        if reused_channel is None and reused_stub is None:
            channel_options = [("grpc.max_send_message_length", max_message_size),#2000000000 * 1.5),
                               ("grpc.max_receive_message_length", max_message_size),#2000000000 * 1.5)
                               ("grpc.so_reuseport", 1), ]

            self.channel = grpc.insecure_channel(port, options=channel_options)
            self.stub = srvc_pb2_grpc.BRIARServiceStub(self.channel)

    ##################################################
    ## Service Functions
    ##################################################
    def get_status(self, options=None):
        """!
        Get the status of the connected BRIAR service.

        @param options optparse.Values: Additional options for the status request.

        @return: 5 element Tuple of str containing developer name, dev short, service name, version, api version, and status.
        """
        reply = self.stub.status(srvc_pb2.StatusRequest())
        reply: srvc_pb2.StatusReply
        return reply.developer_name, reply.dev_short, reply.service_name, reply.version, reply.api_version, reply.status

    ##################################################
    ## Detection functions
    ##################################################

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
            # print('duration: ',durations.total_duration)
            # self.print_verbose("Detected {} detections in {} seconds"
            #                    "".format(len(detect_reply.detections),
            #                              timing.timeElapsed(detect_reply.durations.total_duration)))
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
            # self.print_verbose("Enhanced {} media in {} seconds"
            #                    "".format(1,
            #                              timing.timeElapsed(enhance_reply.durations.total_duration)))
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

    def iter_over_async(self, ait, loop):
        """!
        Iterate over an asynchronous iterator in a synchronous manner.

        @param ait AsyncIterator: The asynchronous iterator to iterate over.
        @param loop asyncio.AbstractEventLoop: The event loop to run the asynchronous iterator in.

        yield: The next item from the asynchronous iterator.
        """
        ait = ait.__aiter__()

        async def get_next():
            try:
                obj = await ait.__anext__()
                return False, obj
            except StopAsyncIteration:
                return True, None

        while True:
            done, obj = loop.run_until_complete(get_next())
            if done:
                break
            yield obj

    def sync_enroll_frames_iter(self, database_name, video, detect_options=None, extract_options=None,
                                enroll_options=None,
                                det_list_list=None, whole_image=False, request_start=-1):
        """!
        Synchronously enroll frames from a video.

        @param database_name str: Name of the database to enroll into.
        @param video str: Path to the video file.
        @param detect_options briar_pb2.DetectionOptions: Options for detection.
        @param extract_options briar_pb2.ExtractOptions: Options for extraction.
        @param enroll_options briar_pb2.EnrollOptions: Options for enrollment.
        @param det_list_list list: List of detection lists.
        @param whole_image bool: Whether to use the whole image for enrollment.
        @param request_start int: Start time of the request.

        yield: briar_service_pb2.EnrollRequest
        """
        loop = asyncio.get_event_loop()
        async_gen = self.enroll_frames_iter_async(database_name, video, detect_options, extract_options, enroll_options,
                                                  det_list_list, whole_image, request_start, yieldextra=True)
        sync_gen = self.iter_over_async(async_gen, loop)
        return sync_gen

    def enroll_frames_iter(self, database_name, video, clientoptions=None, detect_options=None, extract_options=None,
                           enroll_options=None,
                           det_list_list=None, whole_image=False, request_start=-1, as_async=True, constructor=None):
        """!
        Enroll frames from a video.

        @param database_name str: Name of the database to enroll into.
        @param video str: Path to the video file.
        @param clientoptions optparse.Values: Client options.
        @param detect_options briar_pb2.DetectionOptions: Options for detection.
        @param extract_options briar_pb2.ExtractOptions: Options for extraction.
        @param enroll_options briar_pb2.EnrollOptions: Options for enrollment.
        @param det_list_list list: List of detection lists.
        @param whole_image bool: Whether to use the whole image for enrollment.
        @param request_start int: Start time of the request.
        @param as_async bool: Whether to use asynchronous enrollment.
        @param constructor callable: Constructor for the enrollment requests.

        yield: briar_service_pb2.EnrollRequest
        """
        options_dict = {'detect_options': detect_options, 'extract_options': extract_options,
                        'enroll_options': enroll_options}
        if as_async:
            sync_gen = self.sync_enroll_frames_iter(database_name, video, detect_options, extract_options,
                                                    enroll_options,
                                                    det_list_list, whole_image, request_start)
            yield from sync_gen
        else:
            yield from frame_iter(video, clientoptions, options_dict, database_name, det_list_list, whole_image,
                                  request_start, constructor)
            # yield from  enroll_frames_iter_media(database_name, video, detect_options, extract_options, enroll_options,
            #                det_list_list, whole_image, request_start)

    async def enroll_frames_iter_async(self, database_name, video, detect_options=None, extract_options=None,
                                       enroll_options=None,
                                       det_list_list=None, whole_image=False, request_start=-1, yieldextra=False):
        """!
        Asynchronously enroll frames from a video.

        @param database_name str: Name of the database to enroll into.
        @param video str: Path to the video file.
        @param detect_options briar_pb2.DetectionOptions: Options for detection.
        @param extract_options briar_pb2.ExtractOptions: Options for extraction.
        @param enroll_options briar_pb2.EnrollOptions: Options for enrollment.
        @param det_list_list list: List of detection lists.
        @param whole_image bool: Whether to use the whole image for enrollment.
        @param request_start int: Start time of the request.
        @param yieldextra bool: Whether to yield extra information.

        yield: briar_service_pb2.EnrollRequest
        """
        if yieldextra:
            yield srvc_pb2.EnrollRequest()
        async for v in enroll_frames_iter_media_async(database_name, video, detect_options, extract_options,
                                                      enroll_options,
                                                      det_list_list, whole_image, request_start):
            yield v

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

    def verify_files(self, reference_file, verify_file,client_options, detect_options=None, extract_options=None, verify_options=None,
                     verify_templates=None, det_list_list=None, whole_image=False, request_start=-1):
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
        verify_iter = self.verify_file_iter(reference_file, verify_file,client_options, detect_options, extract_options,
                                            verify_options, verify_templates, det_list_list, whole_image,
                                            request_start=request_start)

        return self.stub.verify(verify_iter)  # TODO:change this to the built in verify client function
        # return self.verify(verify_iter)

    def verify_file_iter(self, reference_media_file, verify_media_file,client_options, detect_options=None, extract_options=None,
                         verify_options=None, verify_templates=None, det_list_list=None, whole_image=False,
                         request_start=-1):
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

        for media_file, role in zip((reference_media_file, verify_media_file), (
        srvc_pb2.VerifyRequest.VerifyRole.reference, srvc_pb2.VerifyRequest.VerifyRole.verify)):
            # print('MAKING A REQUEST FOR',media_file,role)
            media_ext = os.path.splitext(media_file)[-1]
            if client_options.progress:
                prog = tqdm(total=1)
                prog.update()
            if media_ext.lower() in briar_media.BriarMedia.IMAGE_FORMATS:
                # Create an enroll request for an image
                frame = cv2.imread(media_file)
                media = image_cv2proto(frame)
                media.source = os.path.abspath(media_file)
                media.frame_count = 1
                durations = briar_pb2.BriarDurations()
                durations.client_duration_file_level.start = request_start
                req = srvc_pb2.VerifyRequest(media=media,
                                             detect_options=detect_options,
                                             extract_options=extract_options,
                                             verify_options=verify_options,
                                             durations=durations,
                                             role=role
                                             )
                req.detect_options.tracking_options.tracking_disable.value = True
                it_end = time.time()
                req.durations.client_duration_file_level.end = it_end
                req.durations.grpc_outbound_transfer_duration.start = it_end

                req.media.description = "final_frame"
                yield req

            elif media_ext.lower() in briar_media.BriarMedia.VIDEO_FORMATS:
                # Create an enroll request for a video
                # video = pv.Video(media_file)
                video = ThreadedVideoIterator(media_file, options=client_options)
                file_level_client_time_end = time.time()
                if client_options.progress:
                    it = tqdm(enumerate(video), total=len(video),desc=os.path.basename(media_file))
                else:
                    it = enumerate(video)

                for frame_num, frame in it:
                    # print('frame_num',frame_num)

                    durations = briar_pb2.BriarDurations()
                    if frame_num == 0:  # if this is the first frame, include the durations for the file-level operations of the BRIAR client API
                        durations.client_duration_file_level.start = request_start
                        durations.client_duration_file_level.end = file_level_client_time_end
                    durations.client_duration_frame_level.start = time.time()
                    im = frame
                    media = image_cv2proto(im)

                    media.frame_count = int(len(video))  # NOTE len(video) raises an error
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
                    if frame_num >= len(video) - 1 or (
                            client_options.max_frames > 0 and frame_num >= client_options.max_frames):
                        req.media.description = "final_frame"
                    if video.stream.Q.qsize() == 0 and video.stream.stopped:
                        print('got final frame!')
                        req.media.description = "final_frame"
                    yield req

    ##################################################
    ## Search Functions
    ##################################################
    def search(self,
               search_iter):  # database_name, media=None,detect_options=briar_pb2.DetectionOptions(),extract_options=briar_pb2.ExtractOptions(),search_options=briar_pb2.SearchOptions(), search_templates=None, detections=None):
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

    ##################################################
    ## Database functions
    ##################################################
    def get_database_names(self):
        """!
        Gets a list of names from the service representing the databases human readable names

        @return: List of str
        """

        names_reply = self.stub.database_list(srvc_pb2.DatabaseListRequest())
        return list(names_reply.database_names)

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
        create_req = srvc_pb2.DatabaseCreateRequest()
        create_req.database.name = database_name
        create_reply = self.stub.database_create(create_req)
        return create_reply.durations
    def database_refresh(self):
        req = srvc_pb2.Empty()
        return self.stub.database_refresh(req)

    ##################################################
    ## Utility Functions:
    ##################################################

    def get_service_configuration(self):
        reply = self.stub.get_service_configuration(srvc_pb2.BriarServiceConfigurationRequest())
        return reply
    def print_verbose(self, *args):
        """!
        Simple helper function to print only when the verbose client is given the verbose flag

        @param args tuple(object): Arguments to get passed to print

        @return: None - outputs to screen
        """
        if self.options and self.options.verbose:
            print(*args)

_worker_channel_singleton = None
_worker_stub_singleton = None
_worker_port_singleton = None

def _shutdown_worker():
    print("Shutting worker process down.")
    if _worker_channel_singleton is not None:
        _worker_channel_singleton.close()

def _initialize_worker(server_address,proc_number,thread_number,count_q):
    global _worker_channel_singleton  # pylint: disable=global-statement
    global _worker_stub_singleton  # pylint: disable=global-statement
    global _worker_port_singleton
    global _worker_thread_position_singleton
    global _worker_proccess_position_singleton

    global _singleton_pool
    global _client_identifier_singleton
    _worker_port_singleton = server_address
    _worker_channel_singleton = grpc.insecure_channel(server_address)
    _worker_stub_singleton = srvc_pb2_grpc.BRIARServiceStub(
        _worker_channel_singleton
    )
    _worker_thread_position_singleton = thread_number
    _worker_proccess_position_singleton = proc_number

    _client_identifier_singleton = count_q.get()
    # print("Initializing worker process.", server_address, _client_identifier_singleton)
    print('initializing child worker on server address',server_address)
    atexit.register(_shutdown_worker)

