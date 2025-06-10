import briar
import optparse
import os
import sys

DEFAULT_MAX_MESSAGE_SIZE = 64 * 1024 * 1024 * 8  # 512MB
DEFAULT_MAX_ASYNC = 8  # The maximum number of async client calls at a time.


# def connectToBriarClient(options):
#     """!
#     Connect to the servicer specified by the options.
#
#     @param options optparse.Values: Options to configure the connection with
#
#     @return: A gRPC stub representing a connection to the running server.
#     """
#     channel = grpc.insecure_channel('localhost:50051')
#     briar_stub = srvc_pb2_grpc.BRIARServiceStub(channel)
#     return briar_stub


def addConnectionOptions(parser):
    """!
    Accumulatively add options for connecting to the Briar API service. Modifies the parser in place.

    This function adds a group of connection-related options to the provided optparse.OptionParser instance.
    These options allow the user to configure various aspects of the connection to the BRIAR service, such as
    the maximum message size, the port to use, and whether to display progress.

    @param parser optparse.OptionParser: A parser to modify in place by adding connection options.
    """
    connection_group = optparse.OptionGroup(parser, "Connection Options",
                                            "Control the connection to the BRIAR service.")

    # TODO implement the commented out arguments
    # connection_group.add_option("--max-async", type="int", dest="max_async", default=DEFAULT_MAX_ASYNC,
    #                             help="The maximum number of asynchronous calls to make at a time. Default=%d" % DEFAULT_MAX_ASYNC)
    #
    # connection_group.add_option("--compression", type="choice", choices=['uint8', 'jpg', 'png'], dest="compression", default="uint8",
    #                             help="Choose a compression format for data transmissions [uint8, jpg, png]. Default=uint8")
    #
    # connection_group.add_option("--quality", type="int", dest="quality", default=95,
    #                             help="Compression quality level [0-100]. Default=95")
    #
    connection_group.add_option("--max-message-size", type="int", dest="max_message_size",
                                default=DEFAULT_MAX_MESSAGE_SIZE,
                                help="Maximum gRPC message size. Set to -1 for unlimited. Default=%d" % (
                                    DEFAULT_MAX_MESSAGE_SIZE))
    connection_group.add_option("-p", "--port", type="str", dest="port", default=briar.DEFAULT_PORT,
                                help="The port used for the recognition service.\n"
                                     "Default={}".format(briar.DEFAULT_PORT))
    connection_group.add_option("--progress", action="store_true", dest="progress", default=False,
                                help="Display progress of the job in the form of a progress bar")
    connection_group.add_option("--bgr", action="store_true", dest="bgr", default=False,
                                help="When set, supplies BGR formatted images, instead of RGB")
    connection_group.add_option("--path-map", type="str", dest="path_map",
                                default="./BTS1/:BGC1/BTS1,./BTS2/:BGC2/BTS2,./BTS3/:BGC3/BTS3,./BTS1.1/:BGC1.1/BTS1.1,./BTS4/:BGC4/BTS4,./BTS5/:BGC5/BTS5",
                                help="If a shared directory is mounted remotely on the server, this provides an alias mapping from file paths on the client to file paths on the server. Map is comma separated, key:value coded. E.g. dir1:dir1,dir2:dir2r")
    connection_group.add_option("--save-durations", action="store_true", dest="save_durations", default=False,
                                help="Save separate durations files for each media file input")
    connection_group.add_option("--chop-frames", type="int", dest="chop_frames", default=-1,
                            help="Sets the number fo frames to chop a video or stream in to. Default=-1 (no chopping).")
    
    connection_group.add_option("--scale", type="float", dest="scale", default=1,
                            help="number with which to scale the input stream to before sending to the server. Default=1 (no scaling). Greater than 1 denotes upscaling, less than 1 denotes downscaling. This is useful for reducing the size of the input stream to reduce bandwidth usage.")
    connection_group.add_option("--max-stream-cycles", type="int", dest="max_stream_cycles", default=-1,
                            help="Sets the maximum number of times to run a stream (chopped by --chop-frames). Default=-1 (runs indefinitely).")
    connection_group.add_option("--skip-frames", type="int", dest="skip_frames", default=0,
                            help="Determines how many frames to skip in between each computed frame.  Set this value larger will speed up computation, but lose accuracy. Default=0 (runs on all frames, skips 0 frames).")

    parser.add_option_group(connection_group)
