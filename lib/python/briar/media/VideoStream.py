from threading import Thread
import sys
import cv2
import time
from queue import Queue
import imageio

class FileVideoStream_cv2:
    def __init__(self, path, transform=None, queue_size=60*3,options=None):
        # initialize the file video stream along with the boolean
        # used to indicate if the thread should be stopped or not
        self.stream = cv2.VideoCapture(path)
        self.stopped = False
        self.transform = transform
        self.options = options
        # initialize the queue used to store frames read from
        # the video file
        self.Q = Queue(maxsize=queue_size)
        # intialize thread
        self.thread = Thread(target=self.update, args=())
        self.thread.daemon = True

    def start(self):
        # start a thread to read frames from the file video stream
        self.thread.start()
        return self

    def update(self):
        # keep looping infinitely
        while True:
            # if the thread indicator variable is set, stop the
            # thread
            if self.stopped:
                break

            # otherwise, ensure the queue has room in it
            if not self.Q.full():
                # read the next frame from the file
                (grabbed, frame) = self.stream.read()

                # if the `grabbed` boolean is `False`, then we have
                # reached the end of the video file
                if not grabbed:
                    self.stopped = True

                # if there are transforms to be done, might as well
                # do them on producer thread before handing back to
                # consumer thread. ie. Usually the producer is so far
                # ahead of consumer that we have time to spare.
                #
                # Python is not parallel but the transform operations
                # are usually OpenCV native so release the GIL.
                #
                # Really just trying to avoid spinning up additional
                # native threads and overheads of additional
                # producer/consumer queues since this one was generally
                # idle grabbing frames.
                if self.transform:
                    frame = self.transform(frame)

                # add the frame to the queue
                self.Q.put(frame)
            else:
                time.sleep(0.1)  # Rest for 10ms, we have a full queue

        self.stream.release()

    def read(self):
        # return next frame in the queue
        return self.Q.get()
    def scrub_to(self, index):
        self.stream.set(cv2.CAP_PROP_POS_FRAMES, index)
    def get_position(self):
        return self.stream.get(cv2.CAP_PROP_POS_FRAMES)
    def get_width(self):
        return int(self.stream.get(cv2.CAP_PROP_FRAME_WIDTH))
    def get_height(self):
        return int(self.stream.get(cv2.CAP_PROP_FRAME_HEIGHT))
    def get_length(self):
        return int(self.stream.get(cv2.CAP_PROP_FRAME_COUNT))
    def get_fps(self):
        return float(self.stream.get(cv2.CAP_PROP_FPS))
    def is_open(self):
        return self.stream.isOpened()
    # Insufficient to have consumer use while(more()) which does
    # not take into account if the producer has reached end of
    # file stream.
    def running(self):
        return self.more() or not self.stopped

    def more(self):
        # return True if there are still frames in the queue. If stream is not stopped, try to wait a moment
        tries = 0
        # changing retry count and sleep time to equivalent of a 60 second timeout
        while self.Q.qsize() == 0 and not self.stopped and tries < 60:
            time.sleep(1)
            print('retry', tries)
            tries += 1

        return self.Q.qsize() > 0

    def stop(self):
        # indicate that the thread should be stopped
        self.stopped = True
        # wait until stream resources are released (producer thread might be still grabbing frame)
        self.thread.join()


class FileVideoStream_imageio:
    def __init__(self, path, transform=None, queue_size=60 * 3, options=None):
        # initialize the file video stream along with the boolean
        # used to indicate if the thread should be stopped or not
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

        # initialize the queue used to store frames read from
        # the video file
        self.Q = Queue(maxsize=queue_size)
        # intialize thread
        self.thread = Thread(target=self.update, args=())
        self.thread.daemon = True

    def start(self):
        # start a thread to read frames from the file video stream
        self.thread.start()
        self.stopped = False
        return self

    def update(self):
        # keep looping infinitely
        i = 0
        while True:
            # if the thread indicator variable is set, stop the
            # thread
            if self.stopped:
                break

            # otherwise, ensure the queue has room in it
            if not self.Q.full():
                # read the next frame from the file
                try:
                    frame = self.stream.get_next_data()
                    # Convert to BGR since all the downstream code assumes
                    # a cv2 reader loaded the imagery
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    # print('frame sum:',frame.sum(),'frame num: ',i)
                    # cv2.imwrite('frame_'+str(i)+'.jpg',frame)
                    # if the `grabbed` boolean is `False`, then we have
                    # reached the end of the video file
                    if frame is None:
                        self.stopped = True
                    else:
                        # if there are transforms to be done, might as well
                        # do them on producer thread before handing back to
                        # consumer thread. ie. Usually the producer is so far
                        # ahead of consumer that we have time to spare.
                        #
                        # Python is not parallel but the transform operations
                        # are usually OpenCV native so release the GIL.
                        #
                        # Really just trying to avoid spinning up additional
                        # native threads and overheads of additional
                        # producer/consumer queues since this one was generally
                        # idle grabbing frames.
                        if self.transform:
                            frame = self.transform(frame)

                        # add the frame to the queue
                        self.Q.put((frame, i))
                    i += 1
                except Exception as e:
                    # if self.options is not None and self.options.verbose:
                    #     print("Video stream terminated")
                    self.stopped = True
            else:
                time.sleep(0.1)  # Rest for 10ms, we have a full queue

        # self.stream.release()
        self.stream.close()

    def read(self):
        # return next frame in the queue
        obj = self.Q.get()
        # print('got i',obj[1],obj[0].sum())
        return obj[0]

    def scrub_to(self, index):
        self.stream.set_image_index(index)

    def get_position(self):
        return self.stream._pos

    def get_width(self):
        return self.stream.get_meta_data()['size'][0]

    def get_height(self):
        return self.stream.get_meta_data()['size'][1]

    def get_length(self):
        return self.stream.count_frames()

    def is_open(self):
        return self.stream is not None

    def get_fps(self):
        return self.stream.get_meta_data()['fps']

    # Insufficient to have consumer use while(more()) which does
    # not take into account if the producer has reached end of
    # file stream.
    def running(self):
        return self.more() or not self.stopped

    def more(self):
        # return True if there are still frames in the queue. If stream is not stopped, try to wait a moment
        tries = 0
        # Increase timeout to 60s.  10s is insufficient when system is under load
        while self.Q.qsize() == 0 and not self.stopped and tries < 60:
            time.sleep(1)
            tries += 1

        return self.Q.qsize() > 0

    def stop(self):
        # indicate that the thread should be stopped
        self.stopped = True
        # wait until stream resources are released (producer thread might be still grabbing frame)
        self.thread.join()
