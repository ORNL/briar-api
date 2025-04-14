import unittest
import os
import sys
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as srvc_pb2
class TestDurations(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workingdir = os.path.dirname(os.path.realpath(__file__))
        cls.imagepathsingle = os.path.join(cls.workingdir, 'test_media', 'halle.jpg')

    def test_duration_image(self):
        from briar.cli.detect import detect
        replies = []
        for reply in detect(input_command='detect ' + self.imagepathsingle, ret=True):
            replies.append(reply)
            reply : srvc_pb2.DetectReply
            fduration = reply.durations.client_duration_file_level
            service_duration = reply.durations.service_duration
            self.assertLess(fduration.start,fduration.end)
            self.assertLess(service_duration.start, service_duration.end)