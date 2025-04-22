import asyncio
import briar
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as srvc_pb2
import cv2
import multiprocessing as mp
import numpy as np
import os
import time
import re
from briar import briar_media
from briar import media_converters
from briar.media_converters import image_cv2proto, pathmap_path2remotepath
from briar.media.VideoStream import FileVideoStream_cv2, FileVideoStream_imageio
import numpy as np
import time
import math

DEFAULT_STREAMING_FRAME_CHOP = 480  # about 20 seconds @ 24 fps

def is_streaming_url(media_file):
    """
    Check if the given media_file string is a streaming URL.

    Args:
        media_file (str): The media file string to check.

    Returns:
        bool: True if it's a streaming URL, False otherwise.
    """
    streaming_url_pattern = re.compile(r'^(http|https|rtsp|rtmp)://')
    return bool(streaming_url_pattern.match(media_file))

class BriarVideoIterator:
    def __init__(self, filepath, start=None, stop=None, unit=None, debug_empty=False, options=None):
        """
        Initialize the video iterator.

        Args:
            filepath (str): Path to the video file.
            start (int, optional): Start frame of the video.
            stop (int, optional): Stop frame of the video.
            unit (str, optional): Unit of start and stop, choices: frame, second, NA.
            debug_empty (bool, optional): Create a debug video iterator object that passes empty frames for testing purposes.
            options (dict, optional): Additional options for the video iterator.
        """
        pass

    def __len__(self):
        """
        Determine the length of the iterator.

        Returns:
            int: The length of the iterator.
        """
        pass

    def __iter__(self):
        """
        Create an iterator object.

        Returns:
            BriarVideoIterator: The iterator object.
        """
        pass

    def __aiter__(self):
        """
        Define an asynchronous iterator.

        Returns:
            BriarVideoIterator: The iterator object.
        """
        pass

    def __next__(self):
        """
        Get the next item from the iterator.

        Returns:
            numpy.ndarray: A frame from the video.
        """
        pass

    async def __anext__(self):
        """
        Get the next item from the asynchronous iterator.

        Returns:
            numpy.ndarray: A frame from the video.
        """
        pass

    def is_opened():
        return False


class VideoIterator(BriarVideoIterator):
    def __init__(self, filepath, start=None, stop=None, unit=None, debug_empty=False, options=None,cap=None):
        """
        Initialize the video iterator.

        Args:
            filepath (str): Path to the video file.
            start (int, optional): Start frame of the video.
            stop (int, optional): Stop frame of the video.
            unit (str, optional): Unit of start and stop, choices: frame, second, NA.
            debug_empty (bool, optional): Create a debug video iterator object that passes empty frames for testing purposes.
            options (dict, optional): Additional options for the video iterator.
        """
        self.debug_empty = debug_empty  #
        self.cap = None
        self.filepath = filepath
        self.is_stream = is_streaming_url(filepath)
        self.cap_reused = False
        if cap is not None:
            # if options.verbose:
            print('Using cv2.VideoCapture object as input')
            self.cap = cap
            self.is_stream = True
            self.cap_reused = True
        self.isOpened = False
        self.options = options
        self.skip_length = options.skip_frames
        self.maintainCapture = False
        self.no_more_frames = False
        if not self.debug_empty and self.cap is None:
            print('setting capture')
            self.cap = cv2.VideoCapture(self.filepath)
        # Check if camera opened successfully
        self.isOpened = self.is_opened()
        if not self.debug_empty and self.cap.isOpened() == False:

            print('Could not read file: ', self.filepath)
            self.isOpened = False
            # raise FileError("Could not open file: " + self.filepath)

        else:
            if self.debug_empty:
                self.isOpened = True
                self.frame_width = 128
                self.frame_height = 128
                self.frame_count = int(stop) + 1
                self.fps = 30
            else:
                self.get_capture_attributes()

            # Figure out the range of frames [start_frame, end_frame)
            if unit == 'NA' or unit is None:
                start_frame = 0
                stop_frame = self.frame_count
            elif unit == 'frame':
                start_frame = int(start)
                stop_frame = int(stop)
            elif unit == 'second':
                start_frame = int(self.fps * float(start))
                stop_frame = int(self.fps * float(stop))
            else:
                raise NotImplementedError("Unsupported Unit Type: " + unit)

            # self.start_frame = start_frame
            if stop_frame > self.frame_count:
                print('WARNING: stop frame', stop_frame, 'is greater than frames in video: ', self.frame_count)
            self.stop_frame = min(stop_frame, self.frame_count)
            self.start_frame = start_frame
            if self.start_frame >= self.stop_frame:
                print("WARNING: stop frame", self.stop_frame, 'is smaller than start frame ', self.start_frame,
                      ' from video with total frames ', self.frame_count)
                self.start_frame = max(0, self.stop_frame - 1)

            assert self.start_frame >= 0
            assert self.stop_frame <= self.frame_count
            assert self.start_frame < self.stop_frame
            self.i = self.start_frame
            
            self.processed = 0
            self.isOpened = True
            if self.skip_length > 0:    
                self.frame_count = self.length = int(math.floor(self.frame_count / (self.skip_length+1)))
                self.fps = int(self.fps / (self.skip_length+1))
    def get_capture_attributes(self):
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if not self.is_stream:
            self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        else:
            if self.options.chop_frames > 0:
                self.frame_count = self.options.chop_frames
            else:
                self.frame_count = DEFAULT_STREAMING_FRAME_CHOP
        self.fps = float(self.cap.get(cv2.CAP_PROP_FPS))
        if self.fps is not None and self.fps > 0:
            self.length = self.frame_count / self.fps
        else:
            self.length = self.frame_count
        self.pos =  0#int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        self.msec =  0#int(self.cap.get(cv2.CAP_PROP_POS_MSEC))
    def get_total_frames(self):
        return int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    def insert_opened_capture(self,cap):
        self.cap = cap
        self.isOpened = self.is_opened()
        self.get_capture_attributes()

    def is_opened(self):
        return self.cap.isOpened()

    def __len__(self):
        """
        Determine the length of the iterator.

        Returns:
            int: The length of the iterator.
        """
        try:
            subset = self.stop_frame - self.start_frame
            subset = int(math.floor(subset / (self.skip_length+1)))
            if subset > 0:
                return subset
        except Exception as e:
            print('Iterator length error:', e)
        return self.frame_count

    def __iter__(self):
        # Scan to the start frame
        """
        The __iter__ function is called when an iterator is required for a container.
        This function should return a new iterator object that can iterate over all the objects in the container.
        For mappings, it should iterate over the keys of the container, and should also be made available as the method __iter__().

        :param self: Represent the instance of the class
        :return: Self
        :doc-author: Joel Brogan, BRIAR team, Trelent
        """        

        if not self.debug_empty:
            if not self.cap_reused:
                for i in range(0, self.start_frame):
                    ret = self.cap.grab()
                    if ret:
                        pass
                    else:
                        break
                pos_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
                assert int(pos_frame) == self.start_frame, f"Video Iterator start could not be set to {self.start_frame}"
        self.i = self.start_frame
        self.processed = 0
        return self

    def __aiter__(self):
        """
        Define an asynchronous iterator.

        Returns:
            VideoIterator: The iterator object.
        """
        return self.__iter__()

    def __next__(self):
        """
        Get the next item from the iterator.

        Returns:
            numpy.ndarray: A frame from the video.
        """
        if  not self.debug_empty and not self.cap.isOpened() :
            # End of file
            raise StopIteration
        # print('getting next frame',self.i,self.stop_frame)
        if self.i >= self.stop_frame:
            raise StopIteration

            # Capture frame-by-frame
        if not self.debug_empty:
            for s in range(self.skip_length):
                ret = self.cap.grab()
                if ret is False:
                    print('bad grab!')
                    raise StopIteration
                self.i += 1
            ret, frame = self.cap.read()  # reads in in BGR format. If BGR is set to true, these channels should not get flipped down-stream before being sent to the server.
            if frame is None or ret is False:
                if self.i < self.start_frame + len(self):
                    print('Warning: iterator only made it through', self.i, 'frames of', len(self))
                if self.options is not None and self.options.verbose:
                    print('end of file3',ret, type(frame))
                self.no_more_frames = True
                raise StopIteration
        else:
            # if we are sending debug dummy video (for throughput testing), send over just gaussian noise
            gaussianr = np.random.random((self.frame_height, self.frame_width, 1))
            gaussiang = np.random.random((self.frame_height, self.frame_width, 1))
            gaussianb = np.random.random((self.frame_height, self.frame_width, 1))
            frame = (np.concatenate((gaussianr, gaussiang, gaussianb), axis=2) * 255).astype(np.uint8)
        self.processed += 1
        self.i += 1
        # frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        # Return as bgr
        return frame

    async def __anext__(self):
        """
        Get the next item from the asynchronous iterator.

        Returns:
            numpy.ndarray: A frame from the video.
        """
        if not self.cap.isOpened():
            # End of file
            raise StopAsyncIteration

        if self.i >= self.stop_frame:
            raise StopAsyncIteration

            # Capture frame-by-frame
        ret, frame = self.cap.read()
        if frame is None or ret is False:
            raise StopAsyncIteration
        self.processed += 1
        self.i += 1
        # frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        # Return as bgr
        return frame

class ThreadedVideoIterator(BriarVideoIterator):
    def __init__(self, filepath, start=None, stop=None, unit=None, debug_empty=False, options=None):
        """
        Initialize the threaded video iterator.

        Args:
            filepath (str): Path to the video file.
            start (int, optional): Start frame of the video.
            stop (int, optional): Stop frame of the video.
            unit (str, optional): Unit of start and stop, choices: frame, second, NA.
            debug_empty (bool, optional): Create a debug video iterator object that passes empty frames for testing purposes.
            options (dict, optional): Additional options for the video iterator.
        """
        self.debug_empty = debug_empty  #
        self.filepath = filepath
        self.isOpened = False
        self.options = options
        self.cap = None
        if not self.debug_empty:
            self.stream = FileVideoStream_imageio(filepath,options=options)
            self.cap = self.stream.stream
        # Check if camera opened successfully
        if not self.debug_empty and (self.stream.is_open() == False):

            print('Could not read file: ', self.filepath)
            self.isOpened = False
            # raise FileError("Could not open file: " + self.filepath)

        else:

            self.frame_width = self.stream.get_width()
            self.frame_height = self.stream.get_height()
            self.frame_count = self.stream.get_length()
            self.fps = self.stream.get_fps()
            if self.fps is not None and self.fps > 0:
                self.length = self.frame_count / self.fps
            else:
                self.length = self.frame_count
            self.pos = 0#int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            self.msec = 0#int(self.cap.get(cv2.CAP_PROP_POS_MSEC))

            # Figure out the range of frames [start_frame, end_frame)
            if unit == 'NA' or unit is None:
                start_frame = 0
                stop_frame = self.frame_count
            elif unit == 'frame':
                start_frame = int(start)
                stop_frame = int(stop)
            elif unit == 'second':
                start_frame = int(self.fps * float(start))
                stop_frame = int(self.fps * float(stop))
            else:
                raise NotImplementedError("Unsupported Unit Type: " + unit)
            if options.max_frames > 0:
                stop_frame = start_frame + options.max_frames
            # self.start_frame = start_frame
            if stop_frame > self.frame_count:
                print('WARNING: stop frame', stop_frame, 'is greater than frames in video: ', self.frame_count)
            self.stop_frame = min(stop_frame, self.frame_count)
            self.start_frame = start_frame
            if self.start_frame >= self.stop_frame:
                print("WARNING: stop frame", self.stop_frame, 'is smaller than start frame ', self.start_frame,
                      ' from video with total frames ', self.frame_count)
                self.start_frame = max(0, self.stop_frame - 1)

            assert self.start_frame >= 0
            assert self.stop_frame <= self.frame_count
            assert self.start_frame < self.stop_frame
            self.i = self.start_frame
            if not self.debug_empty:
                self.stream.scrub_to(self.start_frame)
            self.processed = 0

            self.isStarted = False
            self.isOpened = True

    def __len__(self):
        """
        Determine the length of the iterator.

        Returns:
            int: The length of the iterator.
        """
        try:
            subset = self.stop_frame - self.start_frame
            if subset > 0:
                return subset
        except Exception as e:
            print('Iterator length error:', e)
        return self.frame_count

    def __iter__(self):
        """
        Create an iterator object.

        Returns:
            ThreadedVideoIterator: The iterator object.
        """
        self.stream.scrub_to(self.start_frame)
        self.i = self.start_frame
        self.processed = 0
        if not self.isStarted:
            self.stream.start()
            self.isStarted = True
        return self

    def stop_iteration(self, exception_type):
        """
        Stop the iteration and raise the specified exception.

        Args:
            exception_type (Exception): The exception to raise.
        """
        self.stream.stop()
        raise exception_type

    def __aiter__(self):
        """
        Define an asynchronous iterator.

        Returns:
            ThreadedVideoIterator: The iterator object.
        """
        return self.__iter__()

    def __next__(self):
        """
        Get the next item from the iterator.

        Returns:
            numpy.ndarray: A frame from the video.
        """
        if not self.debug_empty and not self.stream.more():
            # End of file
            # if self.options is not None and self.options.verbose:
            print('end of file')
            self.stop_iteration(StopIteration)

        if self.i >= self.stop_frame:
            self.stop_iteration(StopIteration)

            # Capture frame-by-frame
        if self.stream.running():
            frame = self.stream.read()  # reads in in BGR format. If BGR is set to true, these channels should not get flipped down-stream before being sent to the server.
            if frame is None:
                if self.i < len(self):
                    print('Warning: iterator only made it through', self.i, 'frames of', len(self))
                self.stop_iteration(StopIteration)
        else:
            self.stop_iteration(StopIteration)

        self.processed += 1
        self.i += 1
        # frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        # Return as bgr

        return frame

    async def __anext__(self):
        """
        Get the next item from the asynchronous iterator.

        Returns:
            numpy.ndarray: A frame from the video.
        """
        if not self.stream.is_open():
            # End of file
            self.stop_iteration(StopAsyncIteration)

        if self.i >= self.stop_frame:
            self.stop_iteration(StopAsyncIteration)

            # Capture frame-by-frame
        ret, frame = self.cap.read()
        if frame is None or ret is False:
            self.stop_iteration(StopAsyncIteration)
        self.processed += 1
        self.i += 1
        # frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        # Return as bgr
        return frame

class ImageIterator:
    def __init__(self, filepath, start=None, stop=None, unit=None, debug_empty=False, options=None):
        """
        Initialize the image iterator.

        Args:
            filepath (str): Path to the image file.
            start (int, optional): Start frame of the video.
            stop (int, optional): Stop frame of the video.
            unit (str, optional): Unit of start and stop, choices: frame, second, NA.
            debug_empty (bool, optional): Create a debug image iterator object that passes empty frames for testing purposes.
            options (dict, optional): Additional options for the image iterator.
        """
        self.filepath = filepath
        self.debug_empty = debug_empty


        if not self.debug_empty:
            self.frame = cv2.imread(self.filepath)
        else:
            self.frame_height = 1024
            self.frame_width = 512
            self.frame =  np.random.randint(0,255,(self.frame_height,self.frame_width,3)).astype(np.uint8)# np.concatenate((gaussianr, gaussiang, gaussianb), axis=2)
        if self.frame is not None and min(self.frame.shape) > 0:
            self.isOpened = True
            self.frame_width = self.frame.shape[1]
            self.frame_height = self.frame.shape[0]
            self.frame_count = 1
            self.fps = 30.0
            self.length = self.frame_count / self.fps
            self.pos = 0
            self.msec = 0

            start_frame = 0
            stop_frame = 1

            self.start_frame = start_frame
            self.stop_frame = stop_frame

            assert self.start_frame >= 0
            assert self.stop_frame <= self.frame_count
            assert self.start_frame < self.stop_frame
        else:
            self.isOpened = False

    def __len__(self):
        """
        Determine the length of the iterator.

        Returns:
            int: The length of the iterator.
        """
        return 1

    def __iter__(self):
        """
        Create an iterator object.

        Returns:
            ImageIterator: The iterator object.
        """
        self.i = self.start_frame
        self.processed = 0
        return self

    def __next__(self):
        """
        Get the next item from the iterator.

        Returns:
            numpy.ndarray: A frame from the image.
        """
        if self.i == self.stop_frame:
            raise StopIteration

            # Capture frame-by-frame
        frame = self.frame
        self.processed += 1
        self.i += 1
        # frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)

        return frame

class MediaSetIterator:
    def __init__(self, filepaths, start_frames, stop_frames, unit=None, path_map={}, options=None):
        """
        Initialize the media set iterator.

        Args:
            filepaths (list of str): List of file paths.
            start_frames (list of int): List of start frames for each file.
            stop_frames (list of int): List of stop frames for each file.
            unit (str, optional): Unit of start and stop, choices: frame, second, NA.
            path_map (dict, optional): Map of file paths to new locations.
            options (dict, optional): Additional options for the media set iterator.
        """
        if isinstance(filepaths, str):
            self.filepaths = [filepaths]
        else:
            self.filepaths = filepaths
        self.isOpened = False
        self.media_set = []
        self.start_frames = start_frames
        self.stop_frames = stop_frames
        if not isinstance(start_frames, list):
            self.start_frames = [self.start_frames] * len(self.filepaths)
        if not isinstance(stop_frames, list):
            self.stop_frames = [self.stop_frames] * len(self.filepaths)
        assert len(self.start_frames) == len(self.stop_frames)
        assert len(self.stop_frames) == len(self.filepaths)
        self.start_frame = self.start_frames[0]
        self.stop_frame = self.stop_frames[0]
        for i, path in enumerate(self.filepaths):
            media_ext = os.path.splitext(path)[-1]

            if media_ext.lower() in briar_media.BriarMedia.IMAGE_FORMATS:
                media = media_converters.image_file2proto(path, path_map)
                self.start_frames[i] = None
                self.stop_frames[i] = None
            elif media_ext.lower() in briar_media.BriarMedia.VIDEO_FORMATS:
                self.start_frames[i] = int(self.start_frames[i])
                self.stop_frames[i] = int(self.stop_frames[i])
                media = media_converters.video_file2proto(path, start=self.start_frames[i], end=self.stop_frames[i],
                                                          path_map=path_map)
            else:
                print('BAD FILE FORMAT', path, media_ext)
            self.media_set.append(media)

        self.processed = 0
        self.i = 0
        self.isOpened = True

    def __len__(self):
        """
        Determine the length of the iterator.

        Returns:
            int: The length of the iterator.
        """
        return len(self.media_set)

    def __iter__(self):
        """
        Create an iterator object.

        Returns:
            MediaSetIterator: The iterator object.
        """
        self.processed = 0
        return self

    def __next__(self):
        """
        Get the next item from the iterator.

        Returns:
            numpy.ndarray: The next item in the sequence.
        """
        if self.i == len(self.media_set):
            raise StopIteration
        to_return = self.media_set[self.processed]
        self.start_frame = self.start_frames[self.i]
        self.stop_frame = self.stop_frames[self.i]
        self.processed += 1
        self.i += 1
        return to_return
        # frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        # Return as bgr

def ImageGenerator(filepath, start=None, stop=None, unit=None, options=None):
    """
    The ImageGenerator function is a generator that yields frames from an image file.

    Args:
        filepath (str): Path to the image file.
        start (int, optional): Start frame of the video.
        stop (int, optional): Stop frame of the video.
        unit (str, optional): Unit of start and stop, choices: frame, second, NA.
        options (dict, optional): Additional options for the image generator.

    Yields:
        numpy.ndarray: A frame from the image.
    """
    filepath = filepath

    frame = cv2.imread(filepath)

    frame_width = frame.shape[1]
    frame_height = frame.shape[0]
    frame_count = 1
    fps = 30.0
    length = frame_count / fps
    pos = 0
    msec = 0

    start_frame = 0
    stop_frame = 1

    start_frame = start_frame
    stop_frame = stop_frame

    assert start_frame >= 0
    assert stop_frame <= frame_count
    assert start_frame < stop_frame

    # Scan to the start frame
    i = start_frame
    processed = 0

    # Read until video is completed
    if i == stop_frame:
        raise StopIteration

        # Capture frame-by-frame
    frame = frame
    processed += 1
    i += 1
    # frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)

    yield frame

def single_frame_generate(frame, frame_num, ittype, filepath, start_frame, stop_frame, fps, video_length, clientoptions=None,
                          options_dict: dict = {}, database_name=None, det_list_list=None, whole_image=False,
                          request_start=-1,frame_load_time_start=-1, file_level_client_time_end=-1, requestConstructor=None):
    """
    Generate a single frame of BriarMedia.

    Args:
        frame (numpy.ndarray): The image or video frame to be converted into BriarMedia.
        frame_num (int): The frame number.
        ittype (type): The type of iterator being used (ImageIterator, VideoIterator, MediaSetIterator).
        filepath (str): The path and filename for the media being processed by BRIAR.
        start_frame (int): The starting frame of a video.
        stop_frame (int): The ending frame of a video.
        fps (float): The frame rate of the video.
        video_length (int): The length of the video in frames.
        clientoptions (briar_pb2.DetectionOptions, optional): The client options.
        options_dict (dict, optional): Additional options in dictionary format.
        database_name (str, optional): The database name.
        det_list_list (list of list of briar_pb2.Detection, optional): The detection list from one frame to another.
        whole_image (bool, optional): Whether to send the whole image to briar or just a cropped version.
        request_start (int, optional): The time at which the client API was called.
        frame_load_time_start (int, optional): The time at which the frame load started.
        file_level_client_time_end (int, optional): The time at which the file-level operations of the briar client API have completed.
        requestConstructor (callable, optional): The request constructor.

    Returns:
        briar_service_pb2.DetectRequest: The request object.
    """
    if not ittype == MediaSetIterator:
        if clientoptions is not None and clientoptions.bgr:
            media = image_cv2proto(frame,
                                   flip_channels=False)  # we do *not* flip the channels, as the media_iterator provides a BGR image to begin with
        else:
            media = image_cv2proto(frame)
            media.type = briar_pb2.BriarMedia.DataType.RGB8

        media.source = filepath
        media.frame_number = frame_num
        if ittype == VideoIterator:
            media.source_type = briar_pb2.BriarMedia.DataType.GENERIC_VIDEO
        else:
            media.source_type = briar_pb2.BriarMedia.DataType.GENERIC_IMAGE
    else:
        media = frame
    if start_frame is not None and stop_frame is not None:
        media_metadata = briar_pb2.MediaMetadata(
            attributes=[
                briar_pb2.Attribute(key="start_frame", ivalue=start_frame, type=briar_pb2.BriarDataType.INT),
                briar_pb2.Attribute(key="stop_frame", ivalue=stop_frame, type=briar_pb2.BriarDataType.INT)])
        media.metadata.MergeFrom([media_metadata])
        media.frame_start = start_frame
        media.frame_end = stop_frame
    media.frame_rate = fps
    if video_length is not None:
        media.frame_count = video_length
        

    durations = briar_pb2.BriarDurations()
    it_time = time.time()
    if frame_num == 0:  # if this is the first frame, include the durations for the file-level operations of the BRIAR client API
        durations.client_duration_file_level.start = request_start
        durations.client_duration_file_level.end = file_level_client_time_end
    durations.total_duration.start = request_start
    durations.client_duration_frame_level.start = frame_load_time_start

    # durations.client_duration_frame_level.end = it_time
    # durations.grpc_outbound_transfer_duration.start = it_time
    # print('media metadat:', media.metadata)

    req = requestConstructor(media, durations, options_dict, det_list_list, database_name)
    req.durations.client_duration_frame_level.end = time.time()
    req.durations.grpc_outbound_transfer_duration.start = time.time()
    return req

def file_iter(media_files: list[str], clientoptions: briar_pb2.DetectionOptions = None, options_dict: dict = None, database_name: str = None, verbose: bool = False, request_start: int = -1, requestConstructor: callable = None):
    """
    Iterate the paths in the media file list, loading them one by one and yielding grpc requests generated by <requestConstructor>.

    Args:
        media_files (list of str): Paths to the media files to enroll from.
        clientoptions (briar_pb2.DetectionOptions, optional): Command line options in protobuf format which control detection functionality.
        options_dict (dict, optional): Additional options in dictionary format.
        database_name (str, optional): Name of the database.
        verbose (bool, optional): If True, enables verbose output.
        request_start (int, optional): Starting index for the request.
        requestConstructor (callable, optional): Function to construct the request.

    Yields:
        briar_service_pb2.DetectRequest: gRPC request generated by requestConstructor.
    """
    path_map = {}

    media_enum = zip(media_files)

    for i, iteration in enumerate(media_enum):
        # Dynamically break the iteration into individual components

        media_file = iteration[0]
        is_stream = is_streaming_url(media_file)
        if not is_stream:
            media_file = pathmap_path2remotepath(media_file, path_map)
        media_ext = os.path.splitext(media_file)[-1]
        # code that checks if media_file represents a file or a video stream, setting the is_stream flag if so
        if is_stream or (hasattr(clientoptions,'chop_frames') and clientoptions.chop_frames > 0):
            if hasattr(clientoptions,'chop_frames') and clientoptions.chop_frames > 0:
                if clientoptions.verbose:
                    print('Setting frame chopping length to ', clientoptions.chop_frames, 'frames')
                print('Streaming from ', media_file, 'in chunks of', clientoptions.chop_frames,'frames')
            else:
                if clientoptions.verbose:
                    print('Setting frame chopping length to ', DEFAULT_STREAMING_FRAME_CHOP, 'frames')
            frame_batch_counter = i
            should_continue_stream = True
            cached_capture = None
            max_iterations = None
            while should_continue_stream:
                # print('making iterator')
                if cached_capture is None:
                    media_iterator = VideoIterator(media_file,options=clientoptions)
                    cached_capture = media_iterator.cap
                else:
                    media_iterator = VideoIterator(media_file,options=clientoptions,cap=cached_capture)
                # print('made videoiterator!')
                it = frame_iter(media_iterator, frame_batch_counter,clientoptions, options_dict, database_name, request_start=request_start,
                              requestConstructor=requestConstructor,)
                if max_iterations is None and not is_stream:
                    max_iterations = media_iterator.get_total_frames()
                frame_batch_counter+=1
                if max_iterations is not None:
                    if frame_batch_counter >= max_iterations:
                        should_continue_stream = False
                yield it
                
                
                # Check if the stream is still open
                
        else:  
            if media_ext.lower() in briar_media.BriarMedia.IMAGE_FORMATS:
                # Create an enroll request for an image
                media_iterator = ImageIterator(media_file)
            elif media_ext.lower() in briar_media.BriarMedia.VIDEO_FORMATS:
                startframe = stopframe = None
                if clientoptions.start_frame is not None and clientoptions.start_frame > -1:
                    startframe = options.start_frame
                if clientoptions.stop_frame is not None and clientoptions.stop_frame > -1:
                    stop_frame = options.stop_frame
                media_iterator = VideoIterator(media_file,start=startframe,stop=stopframe,options=clientoptions)
            else:
                raise NotImplementedError
        print('yielding frame_iter')
        yield frame_iter(media_iterator, 0,clientoptions, options_dict, database_name, request_start=request_start,
                              requestConstructor=requestConstructor)

def frame_iter(media_iterator, frame_batch_counter,clientoptions=None, options_dict: dict = {}, database_name=None, det_list_list=None,
               whole_image=False, request_start=-1, requestConstructor=None):
    """
    Iterate through the frames of a video and return a request object for each frame.

    Args:
        media_iterator (iterator): The iterator of frames.
        clientoptions (briar_pb2.DetectionOptions, optional): The client options.
        options_dict (dict, optional): Additional options in dictionary format.
        database_name (str, optional): The database name.
        det_list_list (list of list of briar_pb2.Detection, optional): The detection list from one frame to another.
        whole_image (bool, optional): Whether to send the whole image to briar or just a cropped version.
        request_start (int, optional): The time at which the client API was called.
        requestConstructor (callable, optional): The request constructor.

    Yields:
        briar_service_pb2.DetectRequest: The request object.
    """
    file_level_client_time_end = time.time()
    # Create an enroll request for a video
    iterationtime0 = time.time()
    vidlen = None
    try:
        vidlen = len(media_iterator)  # NOTE len(video) raises an error
    except:
        pass
    frame_load_time_start = time.time()
    try:
        fps = media_iterator.fps
    except:
        fps = -1
    send_start = request_start
    for frame_num, frame in enumerate(media_iterator):
        # print('doing frame gen')
        req = single_frame_generate(
            frame,
            frame_num,
            type(media_iterator),
            media_iterator.filepath,
            media_iterator.start_frame,
            media_iterator.stop_frame,
            media_iterator.fps,
            vidlen,
            clientoptions,
            options_dict,
            database_name,
            det_list_list,
            whole_image,
            send_start,
            frame_load_time_start,
            file_level_client_time_end,
            requestConstructor)
        # print('done frame gen')
        # iterationtime1 = time.time()
        # total_iteration_time = iterationtime1 - iterationtime0
        # iterationtime0 = iterationtime1
        # frame_load_time_start = time.time()
        send_start = time.time()
        # print('frame tme',len(media_iterator), frame_num,clientoptions.max_frames, 'time:', send_start - frame_load_time_start)
        if frame_num >= len(media_iterator)-1 or (clientoptions.max_frames > 0 and frame_num >= clientoptions.max_frames):
            req.media.description = "final_frame"
        
        if hasattr(media_iterator,'stream'):
            if media_iterator.stream.Q.qsize() == 0 and media_iterator.stream.stopped:
                print('stream stopped')
                req.media.description = "final_frame"
        if clientoptions.max_frames > 0 and frame_num >= clientoptions.max_frames-1:
            req.media.description = "final_frame"
            break
        # print('sending frame gen')
        yield req

def enroll_frames_iter(database_name, video, detect_options=None, extract_options=None, enroll_options=None,
                       det_list_list=None, whole_image=False, request_start=-1):
    """
    Iterate the paths in the media file list, loading them one by one and yielding grpc enroll requests.

    Args:
        database_name (str): Name of the database to enroll templates in.
        video (iterator): An iterator that generates cv2 frames.
        detect_options (briar_pb2.DetectionOptions, optional): Command line options in protobuf format which control detection functionality.
        extract_options (briar_pb2.ExtractOptions, optional): Command line options in protobuf format which control extraction functionality.
        enroll_options (briar_pb2.EnrollOptions, optional): Command line options in protobuf format which control enrollment functionality.
        det_list_list (list of list of briar_pb2.Detection, optional): If not None, it will contain 1 list of detections per media file.
        whole_image (bool, optional): Ignore detections and run an extract on the whole image.
        request_start (int, optional): Timestamp of when the request started.

    Yields:
        briar_service_pb2.EnrollRequest: The enroll request.
    """
    if detect_options is None:
        detect_options = briar_pb2.DetectionOptions()
    if extract_options is None:
        extract_options = briar_pb2.ExtractOptions()
    if enroll_options is None:
        enroll_options = briar_pb2.EnrollOptions()
    database = briar_pb2.BriarDatabase(name=database_name)
    file_level_client_time_end = time.time()
    # Create an enroll request for a video
    iterationtime0 = time.time()
    for frame_num, frame in enumerate(video):
        if not isinstance(video, MediaSetIterator):
            media = image_cv2proto(frame)
            media.source = video.filepath
            media.frame_number = frame_num
        else:
            media = frame

        durations = briar_pb2.BriarDurations()
        if frame_num == 0:  # if this is the first frame, include the durations for the file-level operations of the BRIAR client API
            durations.client_duration_file_level.start = request_start
            durations.client_duration_file_level.end = file_level_client_time_end

        durations.client_duration_frame_level.start = time.time()
        if video.start_frame is not None and video.stop_frame is not None:
            media_metadata = briar_pb2.MediaMetadata(
                attributes=[
                    briar_pb2.Attribute(key="start_frame", ivalue=video.start_frame, type=briar_pb2.BriarDataType.INT),
                    briar_pb2.Attribute(key="stop_frame", ivalue=video.stop_frame, type=briar_pb2.BriarDataType.INT)])
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
                                     subject_id_integer=enroll_options.subject_id_integer.value,
                                     subject_name=enroll_options.subject_name,
                                     detections=det_list_list,
                                     detect_options=detect_options,
                                     extract_options=extract_options,
                                     durations=durations,
                                     enroll_options=enroll_options)
        if isinstance(video, briar.media.ImageIterator):
            req.detect_options.tracking_options.tracking_disable.value = True
        else:
            req.detect_options.tracking_options.tracking_disable.value = False
        it_time = time.time()
        req.durations.client_duration_frame_level.end = it_time
        req.durations.grpc_outbound_transfer_duration.start = it_time
        iterationtime1 = time.time()
        total_iteration_time = iterationtime1 - iterationtime0
        iterationtime0 = iterationtime1
        yield req

async def aenumerate(asequence, start=0):
    """
    Asynchronously enumerate an async iterator from a given start value.

    Args:
        asequence (async iterator): The async iterator.
        start (int, optional): The starting value.

    Yields:
        tuple: The index and the element from the async iterator.
    """
    n = start
    async for elem in asequence:
        yield n, elem
        n += 1

async def enroll_frames_iter_async(database_name, video, detect_options=None, extract_options=None, enroll_options=None,
                                   det_list_list=None, whole_image=False, request_start=-1):
    """
    Asynchronously iterate the paths in the media file list, loading them one by one and yielding grpc enroll requests.

    Args:
        database_name (str): Name of the database to enroll templates in.
        video (async iterator): An iterator that generates cv2 frames.
        detect_options (briar_pb2.DetectionOptions, optional): Command line options in protobuf format which control detection functionality.
        extract_options (briar_pb2.ExtractOptions, optional): Command line options in protobuf format which control extraction functionality.
        enroll_options (briar_pb2.EnrollOptions, optional): Command line options in protobuf format which control enrollment functionality.
        det_list_list (list of list of briar_pb2.Detection, optional): If not None, it will contain 1 list of detections per media file.
        whole_image (bool, optional): Ignore detections and run an extract on the whole image.
        request_start (int, optional): Timestamp of when the request started.

    Yields:
        briar_service_pb2.EnrollRequest: The enroll request.
    """
    if detect_options is None:
        detect_options = briar_pb2.DetectionOptions()
    if extract_options is None:
        extract_options = briar_pb2.ExtractOptions()
    if enroll_options is None:
        enroll_options = briar_pb2.EnrollOptions()
    database = briar_pb2.BriarDatabase(name=database_name)
    file_level_client_time_end = time.time()
    # Create an enroll request for a video
    iterationtime0 = time.time()
    async for frame_num, frame in aenumerate(video):
        if not isinstance(video, MediaSetIterator):
            media = image_cv2proto(frame)
            media.source = video.filepath
            media.frame_number = frame_num
        else:
            media = frame

        durations = briar_pb2.BriarDurations()
        if frame_num == 0:  # if this is the first frame, include the durations for the file-level operations of the BRIAR client API
            durations.client_duration_file_level.start = request_start
            durations.client_duration_file_level.end = file_level_client_time_end

        durations.client_duration_frame_level.start = time.time()
        if video.start_frame is not None and video.stop_frame is not None:
            media_metadata = briar_pb2.MediaMetadata(
                attributes=[
                    briar_pb2.Attribute(key="start_frame", ivalue=video.start_frame, type=briar_pb2.BriarDataType.INT),
                    briar_pb2.Attribute(key="stop_frame", ivalue=video.stop_frame, type=briar_pb2.BriarDataType.INT)])
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
                                     subject_id_integer=enroll_options.subject_id_integer.value,
                                     subject_name=enroll_options.subject_name,
                                     detections=det_list_list,
                                     detect_options=detect_options,
                                     extract_options=extract_options,
                                     durations=durations,
                                     enroll_options=enroll_options)
        if isinstance(video, briar.media.ImageIterator):
            req.detect_options.tracking_options.tracking_disable.value = True
        else:
            req.detect_options.tracking_options.tracking_disable.value = False
        it_time = time.time()
        req.durations.client_duration_frame_level.end = it_time
        req.durations.grpc_outbound_transfer_duration.start = it_time
        iterationtime1 = time.time()
        total_iteration_time = iterationtime1 - iterationtime0
        iterationtime0 = iterationtime1
        yield req

try:
    from tqdm import tqdm
except:
    tqdm = None
    if options.verbose:
        print("Warning: could not load tqdm module for progress")
class BriarProgress:
    def __init__(self, options, desc=None, name=None, leave=True, position=None):
        """
        Initialize the progress bar.

        Args:
            options (dict): The options for the progress bar.
            desc (str, optional): The description of the progress bar.
            name (str, optional): The name of the progress bar.
            leave (bool, optional): Whether to leave the progress bar on screen after completion.
            position (int, optional): The position of the progress bar.
        """
        self.tqdm = tqdm
        self.pbar = None
        self.name = name
        self.desc = desc
        self.leave = leave
        self.position = position
        self.prevstep = 0
        self.enabled = True
        # if self.enabled:
            # try:
            #     from tqdm import tqdm
            #     self.tqdm = tqdm
            # except Exception as e:

        if not options.progress:
            self.enabled = False

    def update(self, current=1, total=-1):
        """
        Update the progress bar.

        Args:
            current (int, optional): The current progress.
            total (int, optional): The total progress.
        """
        if self.enabled and self.tqdm is not None:
            if self.pbar is None:
                if self.position is not None:
                    self.pbar = self.tqdm(total=total, leave=self.leave, position=self.position,desc=self.desc)
                else:
                    self.pbar = self.tqdm(total=total, leave=self.leave, desc=self.desc)
            else:

                self.pbar.update(current - self.prevstep)
                self.prevstep = current
    def refresh(self):
        """
        Refresh the progress bar.
        """
        if self.pbar is not None:
            self.pbar.refresh()
    def close(self):
        """
        Close the progress bar.
        """
        if self.pbar is not None:
            self.pbar.close()

def decodeMedia(media_pb, newsource=None):
    """
    Convert protobuf media into a numpy array.

    Args:
        media_pb (briar_pb2.BriarMedia): The protobuf media.
        newsource (str, optional): The new source for the media.

    Returns:
        numpy.ndarray: The decoded media.
    """
    if newsource:
        media_pb.source = newsource
    if media_pb.data and not newsource:
        # decode media
        size = media_pb.height, media_pb.width, media_pb.channels
        img = np.frombuffer(media_pb.data, dtype=np.uint8).reshape(size)
        # img.resize(media_pb.height,media_pb.width,media_pb.channels)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) #decode media flips channels
    elif media_pb.source or newsource is not None:
        # print('decode media src', media_pb.source)
        if os.path.exists(media_pb.source):
            img = cv2.imread(media_pb.source)
    return img

def isFinalFrame(request):
    """
    Check if the request is the final frame.

    Args:
        request (briar_pb2.BriarMedia or briar_service_pb2.DetectRequest): The request.

    Returns:
        bool: True if the request is the final frame, False otherwise.
    """
    if isinstance(request,briar_pb2.BriarMedia):
        if request.description == "final_frame":
            return True
        else:
            return False
    else:
        if request.media.description == "final_frame":
            return True
        else:
            return False