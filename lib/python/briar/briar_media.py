"""!
Defines a media class which acts as a wrapper for image and video files.
"""

import briar.briar_grpc.briar_pb2
import briar.briar_grpc.briar_pb2_grpc
import cv2
import numpy as np
import os
from briar.media_converters import *


class MediaStream:
    def __init__(self, briar_media):
        if isinstance(briar_media, briar_pb2.BriarMedia) or isinstance(briar_media, BriarMedia):
            buf = [briar_media]
        elif isinstance(briar_media, list()):
            buf = briar_media
        self._media_list = briar_media

    def __iter__(self, request_type):
        for briar_media in self._media_list:
            yield request_type(briar_media=briar_media)


# class BriarMedia(briar_pb2.BriarMedia): # TypeError: A Message class can only inherit from Message
class BriarMedia():
    IMAGE_FORMATS = ['.bmp', 'dib', '.jpeg', '.jpg', '.jpe', '.jp2', '.png',
                     '.webp', '.pbm', '.pgm', '.ppm', '.pxm', '.pnm', '.sr',
                     '.ras', '.tiff', '.tif', '.exr', '.hdr', '.pic']
    VIDEO_FORMATS = ['.avi', '.mp4', '.mov', '.m4v', '.ts']
    DATA_TYPES = dict(UINT8=0, UINT16=1, FLOAT32=2, URL=3, PNG=4, JPG=5, MJPG=6,
                      H264=7, H265=8)

    def __init__(self, media_input="", description="", datetime=None, metadata=None):

        if media_input:
            # input media is a filepath
            self.source = media_input

            if os.path.splitext(self.source)[-1] in self.IMAGE_FORMATS:
                data_iterator = [self.source]
                width, height, channels = data_iterator[0].shape
                fps = None
                len = 1
            elif os.path.isdir(self.source):
                data_iterator = list()
                for root, dirs, files in os.walk(self.source):
                    for file in files:
                        data_iterator.append(os.path.join(root, file))
                width, height, channels = data_iterator[0].shape
                fps = None
                len = len(data_iterator)
            elif os.path.splitext(self.source)[-1] in self.VIDEO_FORMATS:
                data_iterator = cv2.VideoCapture(self.source)
                width = data_iterator.get(cv2.CAP_PROP_FRAME_WIDTH)
                height = data_iterator.get(cv2.CAP_PROP_FRAME_HEIGHT)
                channels = data_iterator.get(cv2.CAP_PROP_CHANNEL)
                fps = data_iterator.get(cv2.CAP_PROP_FPS)
                len = data_iterator.get(cv2.CAP_PROP_FRAME_COUNT)

            self.width = width
            self.height = height
            self.channels = channels
            self.fps = fps
            self.len = len

            self.source = media_input
            self.description = description
            self.datetime = datetime
            self.metadata = metadata


def briar_media_from_pb2(pb2_object):
    media = BriarMedia()
    media.source = pb2_object.source
    media.width = pb2_object.width
    media.height = pb2_object.height
    media.channels = pb2_object.channels
    media.frame_cnt = pb2_object.frame_cnt
    media.segment_id = pb2_object.segment_id
    media.segment_total = pb2_object.segment_total
    media.data_type = pb2_object.data_type
    media.data = pb2_object.data
    media.description = pb2_object.description
    media.datetime = pb2_object.datetime
    media.metadata = pb2_object.metadata
    return media


def briar_media_to_pb2(media):
    pb2_object = briar_pb2.BriarMedia()
    pb2_object.source = media.source
    pb2_object.width = media.width
    pb2_object.height = media.height
    pb2_object.channels = media.channels
    pb2_object.frame_cnt = media.frame_cnt
    pb2_object.segment_id = media.segment_id
    pb2_object.segment_total = media.segment_total
    pb2_object.data_type = media.data_type
    pb2_object.data = media.data
    pb2_object.description = media.description
    pb2_object.datetime = media.datetime
    pb2_object.metadata = media.metadata
    return pb2_object


def load_media_from_image(image_path):
    raise NotImplementedError


def load_media_from_folder(folder_path, recursive=False):
    raise NotImplementedError


def load_media_from_numpy(numpy_array):
    raise NotImplementedError
