###################################################################
# Common media handeling fuctions and classes
###################################################################
import briar
import optparse
import os
import pyvision as pv
import sys

DEFAULT_MAX_SIZE = 1920


def addMediaOptions(parser):
    """!
    Add options for running detections to the parser. Modifiers the parser in plase

    @param parser optparse.OptionParser: A parser to modify in place by adding options
    """
    detector_group = optparse.OptionGroup(parser, "Media Options",
                                          "Common Media Handling Options.")

    parser.add_option("-n", "--max-images", type="int", dest="max_images", default=None,
                      help="Process N images per video and then stop.")

    parser.add_option("--maximum-size", type="int", dest="max_size", default=DEFAULT_MAX_SIZE,
                      help="If too large, images will be scaled to have this maximum size. Default=%d" % (
                          DEFAULT_MAX_SIZE))
    parser.add_option("--max-frames", type="int", dest="max_frames", default=-1,
                            help="Maximum frames to extract from a video (leave unset or -1 to use all given frames)")
    parser.add_option("--start-frame", type="int", dest="start_frame", default=-1,
                            help="Start of frame range to extract from a video (leave unset or -1 to use all given frames)")
    parser.add_option("--stop-frame", type="int", dest="stop_frame", default=-1,
                            help="Stop of frame range to extract from a video (leave unset or -1 to use all given frames)")
    parser.add_option("--context", type="choice", choices=['controlled', 'uncontrolled'],
                      dest="context", default="uncontrolled",
                      help="Provides information on the environment in which the media was collected")


    # TODO implement some/all options below
    # detector_group.add_option("-d", "--detections-csv", type="str", dest="detections_csv", default=None,
    #                           help="Save detection data to the file.")
    #
    # detector_group.add_option("-a", "--attributes-csv", type="str", dest="attributes_csv", default=None,
    #                           help="Save attributes data to the file.")
    #
    # detector_group.add_option("--detect-log", type="str", dest="detect_log", default=None,
    #                           help="A directory for detection images.")
    #
    # detector_group.add_option("--face-log", type="str", dest="face_log", default=None,
    #                           help="A directory for faces.")
    #
    # detector_group.add_option("-b", "--best", action="store_true", dest="best", default=False,
    #                           help="Detect the 'best' highest scoring face in the image.")
    #
    # detector_group.add_option("--detect-thresh", type="float", dest="detect_thresh", default=None,
    #                           help="The threshold for a detection.")
    #
    # detector_group.add_option("--min-size", type="int", dest="min_size", default=64,
    #                           help="Faces with a height less that this will be ignored.")
    #
    # detector_group.add_option("--attribute-filter", type="str", dest="attribute_filter", default=None,
    #                           help="A comma seperated list of filters example: 'Male>0.5'"
    #                           )
    parser.add_option_group(detector_group)


def collect_files(args, options, extension=None):
    """!
    Take the paths specified by 'args' and find all the media files that they define: folders will be searched for
    all media files contained inside.

    @param args list(str): List of paths to add as/search for media files

    @param options optparse.Values: Command line options which dictate collect behavior

    @param extension str: A specific extension which defines the csv files associated with media.

    @return: Return value depends on 'extension'
             If 'extension' is None, Tuple will be two elements (list of str, list of str) representing lists
             of image paths and video paths respectively

             If 'extension' is not None, returns a single list of csv files with extensions matching 'extension'
    """
    if options.verbose:
        if extension is None:
            print('Scanning for videos and images...')
        else:
            print('Scanning for ', extension, ' files')
    image_list = []
    video_list = []
    csv_list = []
    for media in args:
        if os.path.isdir(media):
            for path, dirs, files in os.walk(media):
                for filename in files:
                    if pv.isImage(filename):
                        image_list.append(os.path.join(path, filename))
                    elif pv.isVideo(filename):
                        video_list.append(os.path.join(path, filename))
                    elif extension is not None and hasExtension(filename, extension):
                        csv_list.append(os.path.join(path, filename))

        elif os.path.isfile(media):
            if pv.isImage(media):
                image_list.append(media)
            elif pv.isVideo(media):
                video_list.append(media)
            elif extension is not None and hasExtension(media, extension):
                csv_list.append(media)
            else:
                raise ValueError("The file {} is not in a supported image or video type.".format(media))
        else:
            raise ValueError("The path {} does not exist.".format(media))

    if options.verbose:
        if extension is None:
            print("    Found %d images." % (len(image_list)))
            print("    Found %d videos." % (len(video_list)))
        else:
            print("    Found %d files." % (len(csv_list)))

    if extension is None:
        return image_list, video_list
    else:
        return csv_list


def hasExtension(f, extension):
    if isinstance(extension, list):
        for ext in extension:
            if f.endswith(ext):
                return True
        else:
            return False
    else:
        if f.endswith(extension):
            return True
        return False
