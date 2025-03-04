import uuid
import pyvision as pv
import os
def new_uuid():
    """!
    Create and return a new, 36 character unique id

    @return: str
    """
    return str(uuid.uuid4())

def collect_files(args, options, extension=None):
    if options.verbose:
        if extension is None:
            print('Scanning for videos and images...')
        else:
            print('Scanning for ', extension, ' files')
    image_list = []
    video_list = []
    csv_list = []
    for each in args:
        if os.path.isdir(each):
            for path, dirs, files in os.walk(each):
                for filename in files:
                    if pv.isImage(filename):
                        image_list.append(os.path.join(path, filename))
                    elif pv.isVideo(filename):
                        video_list.append(os.path.join(path, filename))
                    elif extension is not None and filename.endswith(extension):
                        csv_list.append(os.path.join(path, filename))

        elif os.path.isfile(each):
            if pv.isImage(each):
                image_list.append(each)
            elif pv.isVideo(each):
                video_list.append(each)
            elif extension is not None and each.endswith(extension):
                csv_list.append(each)
            else:
                raise ValueError("The file <%s> is not in a supported image or video type." % (each))
        else:
            raise ValueError("The path <%s> is not found." % (each))

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