"""!
"""
from concurrent import futures

import os
import grpc
import briar.briar_grpc.briar_service_pb2_grpc as srvc_pb2_grpc
import time

__version__ = '1.3.0'

DEFAULT_PORT = "0.0.0.0:50051"
DEFAULT_SERVE_PORT = '[::]:50051'
DEFAULT_MAX_MESSAGE_SIZE = 64*1024*1024 # 64MB

class Rect:
    """
    Basic rectangle for storing ROIs without needing to mess with the gRPC BriarRect
    """
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

try:
    BRIAR_DIR = os.environ["BRIAR_DIR"]
except Exception as e:
    raise EnvironmentError("The Briar root directory environment variable (BRIAR_DIR) is not set "
                           "in your environment")

def dyn_import(name):
    components = name.split('.')
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

def serve(serviceClass,options=None,serve_port=None):
    """!
    Initialize and run the BRIARService. Runs until killed

    @return:
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10),
                         options=[('grpc.max_send_message_length', 64*1024*1024*8),
                                  ('grpc.max_receive_message_length', 64*1024*1024*8)])
    srvc_pb2_grpc.add_BRIARServiceServicer_to_server(serviceClass(options=options), server)
    if serve_port is None:
        serve_port = DEFAULT_SERVE_PORT
    server.add_insecure_port(serve_port)
    server.start()
    # server.wait_for_termination()

    print("Service Started.  ")
    while True:
        time.sleep(0.1)