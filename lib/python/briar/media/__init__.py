import cv2
import numpy as np
import os
import briar.briar_grpc.briar_pb2 as briar_pb2

# OpenCV Capture Properties
#CAP_PROP_FPS
#CAP_PROP_FRAME_COUNT
#CAP_PROP_FRAME_HEIGHT
#CAP_PROP_FRAME_WIDTH
#CAP_PROP_IMAGES_BASE
#CAP_PROP_IMAGES_LAST
#CAP_PROP_POS_AVI_RATIO
#CAP_PROP_POS_FRAMES
#CAP_PROP_POS_MSEC
#CAP_PROP_FPS
#CAP_PROP_FORMAT
#CAP_PROP_MODE

class VideoIterator(object):

    def __init__(self, filepath, start=None, stop=None, unit=None):
        self.filepath = filepath
        self.isOpened = False
        self.cap = cv2.VideoCapture(self.filepath)
        # Check if camera opened successfully
        if (self.cap.isOpened() == False):
            print('Could not read file: ',self.filepath)
            self.isOpened = False
            # raise FileError("Could not open file: " + self.filepath)
        else:
            self.frame_width  = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.frame_count  = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps          = float(self.cap.get(cv2.CAP_PROP_FPS))
            if self.fps is not None and self.fps > 0:
                self.length   = self.frame_count/self.fps
            else:
                self.length   = self.frame_count
            self.pos          = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            self.msec         = int(self.cap.get(cv2.CAP_PROP_POS_MSEC))

            # Figure out the range of frames [start_frame, end_frame)
            if unit == 'NA' or unit is None:
                start_frame = 0
                stop_frame = self.frame_count
            elif unit == 'frame':
                start_frame = int(start)
                stop_frame = int(stop)
            elif unit == 'second':
                start_frame = int(self.fps*float(start))
                stop_frame = int(self.fps*float(stop))
            else:
                raise NotImplementedError("Unsupported Unit Type: " + unit)

            # self.start_frame = start_frame
            if stop_frame > self.frame_count:
                print('WARNING: stop frame', stop_frame, 'is greater than frames in video: ', self.frame_count)
            self.stop_frame = min(stop_frame,self.frame_count)
            self.start_frame = start_frame
            if self.start_frame >= self.stop_frame:
                print("WARNING: stop frame", self.stop_frame, 'is smaller than start frame ', self.start_frame,' from video with total frames ', self.frame_count)
                self.start_frame = max(0,self.stop_frame-1)

            assert self.start_frame >= 0
            assert self.stop_frame <= self.frame_count
            assert self.start_frame < self.stop_frame
            self.i = self.start_frame
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)
            self.processed = 0
            self.isOpened = True
    def __len__(self):
        try:
            subset = self.stop_frame-self.start_frame
            if subset > 0:
                return subset
        except Exception as e:
            print('Iterator length error:', e)
        return self.frame_count

    def __iter__(self):
        # Scan to the start frame
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)
        self.i = self.start_frame
        self.processed = 0
        return self


    def __next__(self):
        # Read until video is completed
        if not self.cap.isOpened():
            # End of file
            raise StopIteration

        if self.i == self.stop_frame:
            raise StopIteration   
        
        # Capture frame-by-frame
        ret, frame = self.cap.read()
        self.processed += 1
        self.i += 1
        #frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        # Return as bgr
        return frame



class ImageIterator(object):

    def __init__(self, filepath, start=None, stop=None, unit=None):
        self.filepath = filepath

        self.frame = cv2.imread(self.filepath)
        if self.frame is not None and min(self.frame.shape) > 0:
            self.isOpened = True
            self.frame_width  = self.frame.shape[1]
            self.frame_height  = self.frame.shape[0]
            self.frame_count  = 1
            self.fps          = 30.0
            self.length       = self.frame_count/self.fps
            self.pos          = 0
            self.msec         = 0

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
        return 1



    def __iter__(self):
        # Scan to the start frame
        self.i = self.start_frame
        self.processed = 0
        return self


    def __next__(self):
        # Read until video is completed
        if self.i == self.stop_frame:
            raise StopIteration   
        
        # Capture frame-by-frame
        frame = self.frame
        self.processed += 1
        self.i += 1
        #frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)

        return frame



def ImageGenerator(filepath, start=None, stop=None, unit=None):
    print("ImageGenerator Started")
    filepath = filepath

    frame = cv2.imread(filepath)

    frame_width  = frame.shape[1]
    frame_height  = frame.shape[0]
    frame_count  = 1
    fps          = 30.0
    length       = frame_count/fps
    pos          = 0
    msec         = 0

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
    #frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)

    print("ImageGenerator Yield")

    yield frame

class BriarProgress:
    def __init__(self,options,desc=None,name=None,leave=True,position=None):
        self.tqdm = None
        self.pbar = None
        self.name = name
        self.desc = desc
        self.leave = leave
        self.position = position
        self.enabled = options.progress
        self.prevstep = 0
        if self.enabled:
            try:
                from tqdm import tqdm
                self.tqdm = tqdm
            except Exception as e:
                if options.verbose:
                    print("Warning: could not load tqdm module for progress")
    def update(self,current=1,total=-1):
        if self.enabled and self.tqdm is not None:
            if self.pbar is None:
                if self.position is not None:
                    self.pbar = self.tqdm(total=total, leave=self.leave,position=self.position,desc=self.desc)
                else:
                    self.pbar = self.tqdm(total = total,leave=self.leave,desc=self.desc)
            else:
                self.pbar.update(current-self.prevstep)
                self.prevstep = current

def decodeMedia(media_pb,newsource=None):
    """!
    Convert protobuf media into a numpy array

    @param media_pb: briar_pb2.BriarMedia

    return: numpy.array
    """
    if newsource:
        media_pb.source = newsource
    if media_pb.data and not newsource:
        # decode media
        img = np.frombuffer(media_pb.data,dtype=np.uint8)
        img.resize(media_pb.height,media_pb.width,media_pb.channels)
        img = img[:,:,::-1] #convert from rgb to bgr . There is a reordering from bgr to RGB internally in the detector code.
    elif media_pb.source or newsource is not None:
        # print('decode media src', media_pb.source)
        if os.path.exists(media_pb.source):
            img = cv2.imread(media_pb.source)
    return img