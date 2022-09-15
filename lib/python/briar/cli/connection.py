import sys
import os
import optparse

import briar

DEFAULT_MAX_MESSAGE_SIZE = 64*1024*1024*8 # 512MB
DEFAULT_MAX_ASYNC = 8 # The maximum number of async client calls at a time.

# def connectToBriarClient(options):
#     """!
#     Connect to the servicer specified by the options.

#     @param options optparse.Values: Options to configure the connection with

#     @return: A gRPC stub representing a connection to the running server.
#     """
#     channel = grpc.insecure_channel('localhost:50051')
#     briar_stub = srvc_pb2_grpc.BRIARServiceStub(channel)
#     return briar_stub


def addConnectionOptions(parser):
    """!
    Accumulatively add options for connecting to the Briar API service. Modifiers the parser in plase

    @param parser optparse.OptionParser: A parser to modify in place by adding connection options
    """
    connection_group = optparse.OptionGroup(parser, "Connection Options",
                                            "Control the connection to the BRIAR service.")

    # TODO implement the commented out arguments
    # connection_group.add_option("--max-async", type="int", dest="max_async", default=DEFAULT_MAX_ASYNC,
    #                             help="The maximum number of asyncronous call to make at a time. Default=%d" % DEFAULT_MAX_ASYNC)
    #
    # connection_group.add_option( "--compression", type="choice", choices=['uint8','jpg','png'], dest="compression", default="uint8",
    #                             help="Choose a compression format for data transmissions [uint8, jpg, png]. Default=uint8")
    #
    # connection_group.add_option( "--quality", type="int", dest="quality", default=95,
    #                             help="Compression quality level [0-100]. Default=95")
    #
    connection_group.add_option("--max-message-size", type="int", dest="max_message_size",
                                default=DEFAULT_MAX_MESSAGE_SIZE,
                                help="Maximum gRPC message size. Set to -1 for unlimited. Default=%d" % (
                                    DEFAULT_MAX_MESSAGE_SIZE))
    connection_group.add_option("-p", "--port", type="str", dest="port", default=briar.DEFAULT_PORT,
                                help="The port used for the recognition service.\n"
                                     "Default={}".format(briar.DEFAULT_PORT))
    connection_group.add_option("--progress", action="store_true", dest="progress", default=None,
                              help="Display progress of the job in the form of a progress bar")
    connection_group.add_option("--save-durations", action="store_true", dest="save_durations", default=False,
                                help="Save separate durations files for each media file input")
    parser.add_option_group(connection_group)


