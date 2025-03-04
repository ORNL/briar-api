import asyncio
import briar
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as srvc_pb2
import cv2
import multiprocessing as mp
import numpy as np
import os
import time
from briar import briar_media
from briar import media_converters
from briar.media_converters import image_cv2proto, pathmap_path2remotepath
from briar.media.VideoStream import FileVideoStream_cv2,FileVideoStream_imageio

# OpenCV Capture Properties
# CAP_PROP_FPS
# CAP_PROP_FRAME_COUNT
# CAP_PROP_FRAME_HEIGHT
# CAP_PROP_FRAME_WIDTH
# CAP_PROP_IMAGES_BASE
# CAP_PROP_IMAGES_LAST
# CAP_PROP_POS_AVI_RATIO
# CAP_PROP_POS_FRAMES
# CAP_PROP_POS_MSEC
# CAP_PROP_FPS
# CAP_PROP_FORMAT
# CAP_PROP_MODE

class BriarVideoIterator():

    def __init__(self, filepath, start=None, stop=None, unit=None, debug_empty=False,options=None):

        """
    The __init__ function is called when the class is instantiated.
    It sets up the instance of the class, and defines all its attributes.
    The __init__ function takes in arguments that are passed to it by whoever creates an instance of this class,
    and assigns these arguments to self variables so they can be used throughout this object.

    :param self: Represent the instance of the class
    :param filepath: Specify the path to the video file
    :param start: Specify the start frame of the video
    :param stop: Set the last frame to be read from the video
    :param unit: Specify the unit of start and stop, choices: frame, time in seconds, NA (defaults to full video)
    :param debug_empty: specified for creating a debug video iterator object that passes empty frames for testing purposes
    :return: Nothing
    :doc-author: Joel Brogan, BRIAR team, Trelent
    """
        pass

    def __len__(self):
        """
    The __len__ function is used to determine the length of an object.
    For example, if you have a list with 5 items in it, calling len(my_list) will return 5.
    The __len__ function is called when using the built-in len() function.

    :param self: Allow an object to refer to itself
    :return: The length of the iterator
    :doc-author: Joel Brogan, BRIAR team, Trelent
    """
        pass

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
        pass

    def __aiter__(self):
        """
    The __aiter__ function is used to define an asynchronous iterator.

    :param self: Refer to the current instance of a class
    :return: The __iter__ function
    :doc-author: Joel Brogan, BRIAR team, Trelent
    """
        pass

    def __next__(self):
        # Read until video is completed
        """
    The __next__ function is called by the for loop to get each item from the iterator.
    The __next__ function should raise a StopIteration exception when there are no more items in the container.


    :param self: Represent the instance of the class
    :return: A frame from the video
    :doc-author: Joel Brogan, BRIAR team, Trelent
    """

        pass

    async def __anext__(self):
        # Read until video is completed
        """
    The __anext__ function is the asynchronous iterator protocol.
    It allows you to use async for loops, which are a lot more efficient than regular for loops.
    The __anext__ function should return an awaitable object that resolves to the next item in your sequence.

    :param self: Represent the instance of the class
    :return: A frame, which is a numpy array
    :doc-author: Joel Brogan, BRIAR team, Trelent
    """
        pass

class VideoIterator(BriarVideoIterator):

    def __init__(self, filepath, start=None, stop=None, unit=None, debug_empty=False,options=None):

        """
    The __init__ function is called when the class is instantiated.
    It sets up the instance of the class, and defines all its attributes.
    The __init__ function takes in arguments that are passed to it by whoever creates an instance of this class,
    and assigns these arguments to self variables so they can be used throughout this object.

    :param self: Represent the instance of the class
    :param filepath: Specify the path to the video file
    :param start: Specify the start frame of the video
    :param stop: Set the last frame to be read from the video
    :param unit: Specify the unit of start and stop, choices: frame, time in seconds, NA (defaults to full video)
    :param debug_empty: specified for creating a debug video iterator object that passes empty frames for testing purposes
    :return: Nothing
    :doc-author: Joel Brogan, BRIAR team, Trelent
    """
        self.debug_empty = debug_empty  #
        self.filepath = filepath
        self.isOpened = False
        self.cap = None
        if not self.debug_empty:
            self.cap = cv2.VideoCapture(self.filepath)
        # Check if camera opened successfully
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
                self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.fps = float(self.cap.get(cv2.CAP_PROP_FPS))
                if self.fps is not None and self.fps > 0:
                    self.length = self.frame_count / self.fps
                else:
                    self.length = self.frame_count
                self.pos =  0#int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                self.msec =  0#int(self.cap.get(cv2.CAP_PROP_POS_MSEC))

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
            if not self.debug_empty:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)
            self.processed = 0
            self.isOpened = True

    def __len__(self):
        """
        Calculates the length of the iterator.

        Returns:
            The length of the iterator.

        Raises:
            Exception: If there is an error in calculating the length.
        """
        try:
            subset = self.stop_frame - self.start_frame
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
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)
        self.i = self.start_frame
        self.processed = 0
        return self

    def __aiter__(self):
        """
    The __aiter__ function is used to define an asynchronous iterator.

    :param self: Refer to the current instance of a class
    :return: The __iter__ function
    :doc-author: Joel Brogan, BRIAR team, Trelent
    """
        return self.__iter__()

    def __next__(self):
        # Read until video is completed
        """
    The __next__ function is called by the for loop to get each item from the iterator.
    The __next__ function should raise a StopIteration exception when there are no more items in the container.


    :param self: Represent the instance of the class
    :return: A frame from the video
    :doc-author: Joel Brogan, BRIAR team, Trelent
    """

        if  not self.debug_empty and not self.cap.isOpened() :
            # End of file
            print('end of file')
            raise StopIteration

        if self.i >= self.stop_frame:
            raise StopIteration

            # Capture frame-by-frame
        if not self.debug_empty:
            ret, frame = self.cap.read()  # reads in in BGR format. If BGR is set to true, these channels should not get flipped down-stream before being sent to the server.
            if frame is None or ret is False:
                if self.i < len(self):
                    print('Warning: iterator only made it through', self.i, 'frames of', len(self))
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
        # Read until video is completed
        """
    The __anext__ function is the asynchronous iterator protocol.
    It allows you to use async for loops, which are a lot more efficient than regular for loops.
    The __anext__ function should return an awaitable object that resolves to the next item in your sequence.

    :param self: Represent the instance of the class
    :return: A frame, which is a numpy array
    :doc-author: Joel Brogan, BRIAR team, Trelent
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

    def __init__(self, filepath, start=None, stop=None, unit=None, debug_empty=False,options=None):

        """
    The __init__ function is called when the class is instantiated.
    It sets up the instance of the class, and defines all its attributes.
    The __init__ function takes in arguments that are passed to it by whoever creates an instance of this class,
    and assigns these arguments to self variables so they can be used throughout this object.

    :param self: Represent the instance of the class
    :param filepath: Specify the path to the video file
    :param start: Specify the start frame of the video
    :param stop: Set the last frame to be read from the video
    :param unit: Specify the unit of start and stop, choices: frame, time in seconds, NA (defaults to full video)
    :param debug_empty: specified for creating a debug video iterator object that passes empty frames for testing purposes
    :return: Nothing
    :doc-author: Joel Brogan, BRIAR team, Trelent
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
    The __len__ function is used to determine the length of an object.
    For example, if you have a list with 5 items in it, calling len(my_list) will return 5.
    The __len__ function is called when using the built-in len() function.

    :param self: Allow an object to refer to itself
    :return: The length of the iterator
    :doc-author: Joel Brogan, BRIAR team, Trelent
    """
        try:
            subset = self.stop_frame - self.start_frame
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
        self.stream.scrub_to(self.start_frame)
        self.i = self.start_frame
        self.processed = 0
        if not self.isStarted:
            self.stream.start()
            self.isStarted = True
        return self

    def stop_iteration(self, exception_type):
        self.stream.stop()
        raise exception_type

    def __aiter__(self):
        """
    The __aiter__ function is used to define an asynchronous iterator.

    :param self: Refer to the current instance of a class
    :return: The __iter__ function
    :doc-author: Joel Brogan, BRIAR team, Trelent
    """
        return self.__iter__()

    def __next__(self):
        # Read until video is completed
        """
    The __next__ function is called by the for loop to get each item from the iterator.
    The __next__ function should raise a StopIteration exception when there are no more items in the container.


    :param self: Represent the instance of the class
    :return: A frame from the video
    :doc-author: Joel Brogan, BRIAR team, Trelent
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
        # Read until video is completed
        """
    The __anext__ function is the asynchronous iterator protocol.
    It allows you to use async for loops, which are a lot more efficient than regular for loops.
    The __anext__ function should return an awaitable object that resolves to the next item in your sequence.

    :param self: Represent the instance of the class
    :return: A frame, which is a numpy array
    :doc-author: Joel Brogan, BRIAR team, Trelent
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


class ImageIterator(object):

    def __init__(self, filepath, start=None, stop=None, unit=None, debug_empty=False,options=None):
        """
    The __init__ function is called when the class is instantiated.
    It sets up the object with all of its initial values.


    :param self: Represent the instance of the class
    :param filepath: Specify the path to the image file
    :param start: Set the start frame of the video
    :param stop: Specify the last frame to be read
    :param unit: Specify the unit of time for the start and stop parameters
    :return: The following:
    :doc-author: Joel Brogan, BRIAR team, Trelent
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
    The __len__ function is used to determine the length of an object.
    For example, len(s) returns the number of items in s.
    The built-in function len() calls s.__len__().


    :param self: Refer to the instance of the class
    :return: The length of the list
    :doc-author: Joel Brogan, BRIAR team, Trelent
    """
        return 1

    def __iter__(self):
        # Scan to the start frame
        """
    The __iter__ function is called when an iterator object is created for the class.
    This function should return a new iterator object that can iterate over all the objects in the class.
    For example, list, tuple or string classes have this method defined that allows them to be iterated over with a for loop.

    :param self: Access the attributes and methods of the class
    :return: The object itself
    :doc-author: Joel Brogan, BRIAR team, Trelent
    """
        self.i = self.start_frame
        self.processed = 0
        return self

    def __next__(self):
        # Read until video is completed
        """
    The __next__ function is called by the Python interpreter to fetch the next value from an iterator.
    It should raise StopIteration when there are no more values to fetch.

    :param self: Represent the instance of the class
    :return: The next frame in the video
    :doc-author: Joel Brogan, BRIAR team, Trelent
    """
        if self.i == self.stop_frame:
            raise StopIteration

            # Capture frame-by-frame
        frame = self.frame
        self.processed += 1
        self.i += 1
        # frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)

        return frame


class MediaSetIterator(object):

    def __init__(self, filepaths, start_frames, stop_frames, unit=None, path_map={},options=None):
        """
    The __init__ function is called when the class is instantiated.
    It sets up the object with all of its initial values and does any other setup that needs to be done.


    :param self: Refer to the object itself
    :param filepaths: Store the filepaths of all the media files that are to be processed
    :param start_frames: Specify the starting frame of each video
    :param stop_frames: Set the last frame to be read from a video file
    :param unit: Specify the unit of the start and stop frames
    :param path_map: Map the filepaths to a new location
    :return: Nothing
    :doc-author: Joel Brogan, BRIAR team, Trelent
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
    The __len__ function is a special function that returns the length of an object.
    In this case, it's returning the number of media objects in the set.

    :param self: Refer to the class itself
    :return: The length of the media_set list
    :doc-author: Joel Brogan, BRIAR team, Trelent
    """
        return len(self.media_set)

    def __iter__(self):
        # Scan to the start frame
        # self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)
        # self.i = self.start_frame
        """
    The __iter__ function is called when an iterator object is created for the class.
    This function should return an object (usually just self) that has a next() method defined.
    The next() method should return the next value for the iterable, or raise StopIteration if there are no more values.

    :param self: Represent the instance of the class
    :return: The object itself
    :doc-author: Joel Brogan, BRIAR team, Trelent
    """
        self.processed = 0
        return self

    def __next__(self):
        # Read until video is completed
        """
    The __next__ function is called by the for loop to get the next item in
    the iterable. It should raise StopIteration when there are no more items
    to return.

    :param self: Represent the instance of the class
    :return: The next item in the sequence
    :doc-author: Joel Brogan, BRIAR team, Trelent
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


def ImageGenerator(filepath, start=None, stop=None, unit=None,options=None):
    """
The ImageGenerator function is a generator that yields frames from an image file.

:param filepath: Specify the location of the image
:param start: Set the starting frame of the video
:param stop: Stop the generator at a certain frame
:param unit: Determine the unit of time that is used for the start and stop parameters
:return: A single frame, so we need to wrap it in a loop
:doc-author: Joel Brogan, BRIAR team, Trelent
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
    # generate the BriarMedia
    """
The single_frame_generate function is used to generate a single frame of BriarMedia.
It takes in the following parameters:
    - frame: The image or video frame that will be converted into BriarMedia.
    - ittype: The type of iterator being used (ImageIterator, VideoIterator, MediaSetIterator).  This is needed because the function needs to know whether it's dealing with an image or a video file.  If you're using MediaSetIterators, then this parameter should be set to &quot;None&quot;.
    - filepath: A string containing the path and filename for the media being processed by BRIAR.

:param frame: Pass in the frame to be processed
:param frame_num: Keep track of the frame number
:param ittype: Determine the type of iterator used to generate frames
:param filepath: Indicate the path to the file that is being processed
:param start_frame: Indicate the starting frame of a video, and stop_frame is used to indicate the ending frame
:param stop_frame: Determine the last frame to be processed
:param video_length: Set the frame_count in the briarmedia
:param clientoptions: Pass the options to the client
:param options_dict : dict: Pass the options dictionary to the server
:param database_name: Specify the database to which the request should be sent
:param det_list_list: Pass the detection list from one frame to another
:param whole_image: Determine if the whole image is sent to briar or just a cropped version
:param request_start: Record the time at which the client api was called
:param file_level_client_time_end: Record the time at which the file-level operations of the briar client api have completed
:param requestConstructor: Create a request object
:return: A request object, which is a briarrequest message
:doc-author: Joel Brogan, BRIAR team, Trelent
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
    Iterates the paths in the media file list, loading them one by one and yielding grpc requests generated by <requestConstructor>.

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
        media_file = pathmap_path2remotepath(media_file, path_map)
        media_ext = os.path.splitext(media_file)[-1]

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
        yield from frame_iter(media_iterator, clientoptions, options_dict, database_name, request_start=request_start,
                              requestConstructor=requestConstructor)


def frame_iter(media_iterator, clientoptions=None, options_dict: dict = {}, database_name=None, det_list_list=None,
               whole_image=False, request_start=-1, requestConstructor=None):
    """
    The frame_iter function is a generator that takes in an iterator of frames, and returns a request object for each frame.
    The request object contains the following information:
        - The frame number (int)
        - The type of media_iterator (str)
        - The filepath to the video/image sequence (str)
        - A list containing all detections from previous iterations, if applicable. If not applicable, this will be None.

    :param media_iterator: Iterate through the frames of a video
    :param clientoptions: Pass the client options to the request
    :param options_dict : dict: Pass in the options dictionary from the client
    :param database_name: Specify the database name
    :param det_list_list: Pass in a list of detection lists
    :param whole_image: Determine whether or not to send the whole image
    :param request_start: Keep track of when the request was begun
    :param requestConstructor: Create a request object
    :return: A generator that yields a single frame request
    :doc-author: Joel Brogan, BRIAR team, Trelent
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
        # iterationtime1 = time.time()
        # total_iteration_time = iterationtime1 - iterationtime0
        # iterationtime0 = iterationtime1
        # frame_load_time_start = time.time()
        send_start = time.time()

        if frame_num >= len(media_iterator)-1 or (clientoptions.max_frames > 0 and frame_num >= clientoptions.max_frames):
            req.media.description = "final_frame"
        if hasattr(media_iterator,'stream'):
            if media_iterator.stream.Q.qsize() == 0 and media_iterator.stream.stopped:
                req.media.description = "final_frame"
        yield req


def enroll_frames_iter(database_name, video, detect_options=None, extract_options=None, enroll_options=None,
                       det_list_list=None, whole_image=False, request_start=-1):
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

    @type request_start: int
    @param: timestamp of when the request started

    @yield: briar_service_pb2.EnrollRequest
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
    """Asynchronously enumerate an async iterator from a given start value"""
    n = start
    async for elem in asequence:
        yield n, elem
        n += 1


async def enroll_frames_iter_async(database_name, video, detect_options=None, extract_options=None, enroll_options=None,
                                   det_list_list=None, whole_image=False, request_start=-1):
    """!
    Asyncronously Iterates the paths in the media file list, loading them one by one and yielding grpc enroll requests.
    This method should provide better video load performance and better request generation performance.

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

    @type request_start: int
    @param: timestamp of when the request started

    @yield: briar_service_pb2.EnrollRequest
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
    The __init__ function is called when the class is instantiated.
    It sets up the progress bar and initializes some variables.


    :param self: Represent the instance of the class
    :param options: Determine if progress bars are enabled
    :param desc: Set the description of the progress bar
    :param name: Name the progress bar
    :param leave: Determine whether the progress bar should be left on screen after completion
    :param position: Set the position of the progress bar
    :return: Nothing
    :doc-author: Joel Brogan, BRIAR team, Trelent
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
        if self.pbar is not None:
            self.pbar.refresh()
    def close(self):
        if self.pbar is not None:
            self.pbar.close()

def decodeMedia(media_pb, newsource=None):
    """!
    Convert protobuf media into a numpy array

    @param media_pb: briar_pb2.BriarMedia

    return: numpy.array
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