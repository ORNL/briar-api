from threading import Thread
import cv2
import time
from queue import Queue
import imageio
import numpy as np

class FileVideoStream_cv2:
    def __init__(self, path, transform=None, queue_size=60*3, options=None):
        """
        Initialize the file video stream using OpenCV.

        Args:
            path (str): Path to the video file.
            transform (callable, optional): Transformation function to apply to each frame.
            queue_size (int, optional): Maximum size of the frame queue.
            options (dict, optional): Additional options for the video stream.
        """
        self.stream = cv2.VideoCapture(path)
        self.stopped = False
        self.transform = transform
        self.options = options
        self.Q = Queue(maxsize=queue_size)
        self.thread = Thread(target=self.update, args=())
        self.thread.daemon = True

    def start(self):
        """
        Start the thread to read frames from the file video stream.

        Returns:
            FileVideoStream_cv2: The instance of the video stream.
        """
        self.thread.start()
        return self

    def update(self):
        """
        Keep looping infinitely to read frames from the video file and add them to the queue.
        """
        while True:
            if self.stopped:
                break

            if not self.Q.full():
                grabbed, frame = self.stream.read()
                if not grabbed:
                    self.stopped = True
                if self.transform:
                    frame = self.transform(frame)
                self.Q.put(frame)
            else:
                time.sleep(0.1)

        self.stream.release()

    def read(self):
        """
        Return the next frame in the queue.

        Returns:
            numpy.ndarray: The next frame in the queue.
        """
        return self.Q.get()

    def scrub_to(self, index):
        """
        Scrub to a specific frame index in the video.

        Args:
            index (int): The frame index to scrub to.
        """
        self.stream.set(cv2.CAP_PROP_POS_FRAMES, 0)
        for i in range(0, index):
            ret = self.stream.grab()
            if ret:
                pass
            else:
                break
        pos_frame = self.stream.get(cv2.CAP_PROP_POS_FRAMES)
        assert int(pos_frame) == index, f"Video Iterator start could not be set to {index}"

    def get_position(self):
        """
        Get the current frame position in the video.

        Returns:
            int: The current frame position.
        """
        return self.stream.get(cv2.CAP_PROP_POS_FRAMES)

    def get_width(self):
        """
        Get the width of the video frames.

        Returns:
            int: The width of the video frames.
        """
        return int(self.stream.get(cv2.CAP_PROP_FRAME_WIDTH))

    def get_height(self):
        """
        Get the height of the video frames.

        Returns:
            int: The height of the video frames.
        """
        return int(self.stream.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def get_length(self):
        """
        Get the total number of frames in the video.

        Returns:
            int: The total number of frames.
        """
        return int(self.stream.get(cv2.CAP_PROP_FRAME_COUNT))

    def get_fps(self):
        """
        Get the frames per second (FPS) of the video.

        Returns:
            float: The FPS of the video.
        """
        return float(self.stream.get(cv2.CAP_PROP_FPS))

    def is_open(self):
        """
        Check if the video stream is open.

        Returns:
            bool: True if the stream is open, False otherwise.
        """
        return self.stream.isOpened()

    def running(self):
        """
        Check if the video stream is still running.

        Returns:
            bool: True if the stream is running, False otherwise.
        """
        return self.more() or not self.stopped

    def more(self):
        """
        Check if there are more frames in the queue.

        Returns:
            bool: True if there are more frames, False otherwise.
        """
        tries = 0
        while self.Q.qsize() == 0 and not self.stopped and tries < 60:
            time.sleep(1)
            print('retry', tries)
            tries += 1

        return self.Q.qsize() > 0

    def stop(self):
        """
        Indicate that the thread should be stopped and wait until stream resources are released.
        """
        self.stopped = True
        self.thread.join()


class FileVideoStream_imageio:
    def __init__(self, path, transform=None, queue_size=60 * 3, options=None):
        """
        Initialize the file video stream using imageio.

        Args:
            path (str): Path to the video file.
            transform (callable, optional): Transformation function to apply to each frame.
            queue_size (int, optional): Maximum size of the frame queue.
            options (dict, optional): Additional options for the video stream.
        """
        self.options = options
        self.stream = None
        self.backend = None
        self.fps = 30
        try:
            metadata = imageio.v3.immeta(path, exclude_applied=False)
            self.fps = metadata['fps']
        except:
            print('Could not read video metadata')

        try:
            self.stream = imageio.get_reader(path, "ffmpeg", fps=self.fps)
            self.backend = 'ffmpeg'
        except:
            print('Could not load reader with ffmpeg, falling back to default imageio reader')
            pass
        if self.stream is None:
            try:
                self.stream = imageio.get_reader(path, fps=self.fps)
                self.backend = 'pyav'
            except:
                print('could not load file with pyav:', path)
        self.stopped = False
        self.transform = transform
        self.Q = Queue(maxsize=queue_size)
        self.thread = Thread(target=self.update, args=())
        self.thread.daemon = True

    def start(self):
        """
        Start the thread to read frames from the file video stream.

        Returns:
            FileVideoStream_imageio: The instance of the video stream.
        """
        self.thread.start()
        self.stopped = False
        return self

    def update(self):
        """
        Keep looping infinitely to read frames from the video file and add them to the queue.
        """
        i = 0
        while True:
            if self.stopped:
                break

            if not self.Q.full():
                try:
                    frame = self.stream.get_next_data()
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    if frame is None:
                        self.stopped = True
                    else:
                        if self.transform:
                            frame = self.transform(frame)
                        self.Q.put((frame, i))
                    i += 1
                except Exception as e:
                    self.stopped = True
            else:
                time.sleep(0.1)

        self.stream.close()

    def read(self):
        """
        Return the next frame in the queue.

        Returns:
            numpy.ndarray: The next frame in the queue.
        """
        obj = self.Q.get()
        return obj[0]

    def scrub_to(self, index):
        """
        Scrub to a specific frame index in the video.

        Args:
            index (int): The frame index to scrub to.
        """
        self.stream.set_image_index(index)

    def get_position(self):
        """
        Get the current frame position in the video.

        Returns:
            int: The current frame position.
        """
        return self.stream._pos

    def get_width(self):
        """
        Get the width of the video frames.

        Returns:
            int: The width of the video frames.
        """
        return self.stream.get_meta_data()['size'][0]

    def get_height(self):
        """
        Get the height of the video frames.

        Returns:
            int: The height of the video frames.
        """
        return self.stream.get_meta_data()['size'][1]

    def get_length(self):
        """
        Get the total number of frames in the video.

        Returns:
            int: The total number of frames.
        """
        return self.stream.count_frames()

    def is_open(self):
        """
        Check if the video stream is open.

        Returns:
            bool: True if the stream is open, False otherwise.
        """
        return self.stream is not None

    def get_fps(self):
        """
        Get the frames per second (FPS) of the video.

        Returns:
            float: The FPS of the video.
        """
        return self.stream.get_meta_data()['fps']

    def running(self):
        """
        Check if the video stream is still running.

        Returns:
            bool: True if the stream is running, False otherwise.
        """
        return self.more() or not self.stopped

    def more(self):
        """
        Check if there are more frames in the queue.

        Returns:
            bool: True if there are more frames, False otherwise.
        """
        tries = 0
        while self.Q.qsize() == 0 and not self.stopped and tries < 60:
            time.sleep(1)
            tries += 1

        return self.Q.qsize() > 0

    def stop(self):
        """
        Indicate that the thread should be stopped and wait until stream resources are released.
        """
        self.stopped = True
        self.thread.join()
