import asyncio
import briar
import briar.briar_client as briar_client
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.grpc_json as grpc_json
import numpy as np
import optparse
import os
import pyvision as pv
import sys
import time
from briar.cli.connection import addConnectionOptions
from briar.cli.detect import addDetectorOptions
from briar.cli.detect import detectParseOptions, detect_options2proto
from briar.cli.media import addMediaOptions
from briar.cli.media import collect_files
from briar.cli.search import DETECTION_FILE_EXT, MATCHES_FILE_EXT
from briar.cli.track import TRACKLET_FILE_EXT
from briar.media import BriarProgress
from briar.media import visualize
from briar.media_converters import image_proto2cv


def viz():
    """!
    Using the options specified in the command line, runs visualization on the specified files.

    @return: No return - Function writes results to disk
    """
    options, args = vizParseOptions()
    visfiles = {}
    visfiles['detection'] = collect_files(args[1:], options, extension=DETECTION_FILE_EXT)
    visfiles['tracklet'] = collect_files(args[1:], options, extension=TRACKLET_FILE_EXT)
    visfiles['matches'] = collect_files(args[1:], options, extension=MATCHES_FILE_EXT)

    if options.type == "auto":
        keys = list(visfiles.keys())
        bestlistkey = keys[np.array([len(visfiles[k]) for k in keys]).argmax()]
        options.type = bestlistkey
    else:
        bestlistkey = options.type
    if options.type == "detection":
        for media_file in visfiles[bestlistkey]:
            visualize.visualize_detection(media_file)
    elif options.type == "tracklet":
        for media_file in visfiles[bestlistkey]:
            visualize.visualize_track(media_file, options)
    elif options.type == "matches":
        print('in')
        for media_file in visfiles[bestlistkey]:
            visualize.visualize_matches(media_file)

    # print(detectionslist,trackletlist,matcheslist)


def vizParseOptions():
    """!
    Generate options for running detections and parse command line arguments into them.

    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively
    """
    args = ['[.detection file] [.matches file] [.tracklet file] [...]']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = "Visualize detections, tracklets, and matches as saved output from BRIAR API commands  " + \
                  "Results can be saved as image files in the output directory."
    epilog = '''Created by Joel Brogan - broganjr@ornl.gov'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s command [OPTIONS] %s' % (sys.argv[0], args),
                                   version=version, description=description, epilog=epilog, conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

    parser.add_option("-o", "--out-dir", type="str", dest="out_dir", default=None,
                      help="Output Directory: defaults to media_directory.")

    parser.add_option("--type", type="choice", choices=['detection', 'tracklet', 'matches', 'auto'], dest="type",
                      default="auto",
                      help="Choose an enrollment mode: subject or media. Default=auto")

    # Parse the arguments and return the results.
    (options, args) = parser.parse_args()

    if len(args) < 1:
        parser.print_help()
        print("\n"
              "Please supply exactly {} arguments.\n"
              "\n".format(n_args))
        exit(-1)

    return options, args
