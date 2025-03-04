"""!
Contained in this are functions for converting numpy arrays into various protobuf objects and back again
since numpy arrays cannot be sent directly over gRPC.
"""
import warnings

import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as srvc_pb2
import cv2
import numpy as np
import os
import urllib
from typing import List

modalityDict = {'whole_body': briar_pb2.WHOLE_BODY,
                'wholeBody': briar_pb2.WHOLE_BODY,
                'wholebody': briar_pb2.WHOLE_BODY,
                'face': briar_pb2.FACE,
                'gait': briar_pb2.GAIT,
                'unspecified': briar_pb2.UNSPECIFIED}

reverseModalityDict = {modalityDict[k]: k for k in modalityDict}


def video_file2proto(vidfile, start, end, path_map={}):
    """
The video_file2proto function takes in a video file, start frame, end frame and path_map.
The path_map is used to map the local paths of the video files to their server side paths.
This function returns a BriarMedia proto object with all of its fields filled out.

:param vidfile: Get the video file name
:param start: Specify the frame number of the first frame in a video
:param end: Determine the last frame of a video
:param path_map: Map the local path to the server path
:return: A briar_pb2
:doc-author: Joel Brogan, BRIAR team, Trelent
"""
    vidfile_server = vidfile + ''
    for key in path_map:
        vidfile_server = vidfile_server.replace(key, path_map[key])
    result = briar_pb2.BriarMedia()
    result.source = vidfile
    result.serverside_source = vidfile_server
    result.type = briar_pb2.BriarMedia.DataType.SOURCE_ONLY
    result.source_type = briar_pb2.BriarMedia.DataType.GENERIC_VIDEO  # TODO maybe dont only have this as the video type
    result.frame_start = int(start)
    result.frame_end = int(end)
    return result


def subjectID_str2int(subjectid):  # This function is for legacy systems that utilize only numbers as gallery entries.
    """
The subjectID_str2int function is for legacy systems that utilize only numbers as gallery entries.
    This function takes a string of the form &quot;G####&quot; and returns an integer of the form ####.

:param subjectid: Create a subjectid that is only numbers
:return: An integer value of the subjectid
:doc-author: Joel Brogan, BRIAR team, Trelent
"""
    return int(subjectid.replace("G", ''))


def subjectID_int2str(subjectid):
    """
The subjectID_int2str function takes an integer subject ID and converts it to a string.
The function is used in the process of creating a new subject ID for each participant.
It ensures that all IDs are 5 digits long, with leading zeros if necessary.

:param subjectid: Convert the subjectid from an integer to a string
:return: A string of the subject id with a g in front and zeros to fill out the rest
:doc-author: Joel Brogan, BRIAR team, Trelent
"""
    idlen = 5
    snum = str(subjectid)
    snum = snum.zfill(idlen)
    return "G" + snum


def image_file2proto(imfile, path_map={}):
    imfile_server = imfile + ''
    imfile_server = pathmap_path2remotepath(imfile_server, path_map)

    result = briar_pb2.BriarMedia()
    result.type = briar_pb2.BriarMedia.SOURCE_ONLY
    result.source = imfile
    result.serverside_source = imfile_server
    result.source_type = briar_pb2.BriarMedia.DataType.GENERIC_IMAGE
    return result


def image_cv2proto(im, compression='uint8', quality=99,
                   flip_channels=True):  # flip channels is by default set to true. If this is coming from the default media_iterator (which provides BGR images), this means cv2proto will return an RGB image.
    """!
    Convert a cv2 numpy array to a protobuf format.

    @param img numpy.array: array containing the image to convert to BriarMedia

    @param compression str: What compression to use. Can be 'uint8', 'png', 'jpg'

    @param quality int: 0-100 How much do you want to mutilate the image in the name of saving memory?

    @param flip_channels boolean : Flips the channels dimension of a cv2-type numpy image.  This could translate an image from RGB->BGR or vice-versa.  Default is True.

    return: briar_pb2.BriarMedia
    """
    assert im.dtype == np.uint8  # Currently only uint8 supported
    assert quality >= 0 and quality <= 100

    result = briar_pb2.BriarMedia()
    result.width = im.shape[1]
    result.height = im.shape[0]
    result.channels = im.shape[2]

    imdata = im
    if flip_channels:
        if len(im.shape) > 2:
            imdata = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)

    if compression == 'uint8':
        if result.channels == 1:
            result.type = briar_pb2.BriarMedia.MONO8
        elif result.channels == 3:
            result.type = briar_pb2.BriarMedia.RGB8

        result.data = imdata.tobytes()
        pass
    elif compression in ('jpg', 'png'):
        buf = cv2.imencode('.' + compression, imdata, [int(cv2.IMWRITE_JPEG_QUALITY), quality])[1].tobytes()
        if compression == 'jpg':
            result.type = briar_pb2.BriarMedia.JPG
        elif compression == 'png':
            result.type = briar_pb2.BriarMedia.PNG
        else:
            raise ValueError("Unknown type:" + compression)
        result.data = buf

    # Check compression info:
    # print("BriarMedia Size:",result.width,result.height,result.channels,"   Compression:",compression,quality, "   Rate:",len(result.SerializeToString()),len(result.SerializeToString())/(result.width*result.height*result.channels))

    return result


def image_np2proto(im, compression='uint8', quality=99, flip_channels=True):
    """!
    Convert a numpy array to a protobuf format.

    @param img numpy.array: array containing the image to convert to BriarMedia

    @param compression str: What compression to use. Can be 'uint8', 'png', 'jpg'

    @param quality int: 0-100 How much do you want to mutilate the image in the name of saving memory?

    @param flip_channels boolean : Flips the channels dimension of a cv2-type numpy image.  This could translate an image from RGB->BGR or vice-versa.  Default is True.

    return: briar_pb2.BriarMedia
    """
    # if len(im.shape) > 2:
    #     im = im[:,:,::-1] # RGB to BGR

    return image_cv2proto(im, compression=compression, quality=quality, flip_channels=flip_channels)


def image_proto2cv(pb_data, flip_channels=False):
    """!
    Convert a protobuf BriarMedia image to a cv2 numpy array

    @param pb_data briar_pb2.BriarMedia: Protobuf object containing image data
    @param flip_channels boolean : Flips the channels dimension of a cv2-type numpy image.  This could translate an image from RGB->BGR or vice-versa.  Default is False.
    @return: numpy.array cv2 formatted np array containing image
    """
    shape = pb_data.height, pb_data.width, pb_data.channels
    if min(shape) > 0:
        if pb_data.type == briar_pb2.BriarMedia.MONO8 or pb_data.type == briar_pb2.BriarMedia.RGB8:
            data = np.frombuffer(pb_data.data, dtype=np.uint8).reshape(shape)
        elif pb_data.type in (briar_pb2.BriarMedia.PNG, briar_pb2.BriarMedia.JPG):
            tmp = np.fromstring(pb_data.data, dtype='uint8')
            data = cv2.imdecode(tmp, cv2.IMREAD_COLOR)
        elif pb_data.type in [briar_pb2.BriarMedia.URL]:
            link = pb_data.data
            f = urllib.urlopen(link)
            tmp = f.read()
            data = cv2.imdecode(tmp, cv2.IMREAD_COLOR)
        elif pb_data.type in [briar_pb2.BriarMedia.SOURCE_ONLY]:
            source = pb_data.source
            data = cv2.imread(source)
            print('SOURCE ONLY', source)
        else:
            raise ValueError("BriarMediaType not supported: " + repr(pb_data.type))
        if flip_channels:
            if len(data.shape) > 2:
                data = cv2.cvtColor(data, cv2.COLOR_BGR2RGB)

    else:
        import inspect
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        print("Warning: size 0 array decoded,caller name:", [cf[3] for cf in calframe])
        # print()
        return np.array([])
    return data


def image_proto2np(pb_data, flip_channels=True):
    """!
    Convert a protobuf image to a numpy array.

    @param pb_data briar_pb2.BriarMedia: Protobuf object containing image data

    @return: np.array
    """
    data = image_proto2cv(pb_data, flip_channels=flip_channels)
    # data = data[:, :, ::-1]  # Convert BGR to RGB
    return data


def vector_np2proto(vec):
    """!
    Convert a 1 dimensional np array into a BriarVector

    @param vec numpy.array: Numpy array contaiing vector data

    @return: briar_pb2.BriarVector
    """
    protovec = briar_pb2.BriarVector()
    assert len(vec.shape) == 1
    protovec.data.extend(vec)
    return protovec


def vector_proto2np(protovec):
    """!
    Convert a protobuf vector into a numpy array

    @param protovec briar_pb2.BriarVector: Protobuf object containing vector info

    @return: numpy.array
    """
    vec = np.array(protovec.data, dtype=np.float32)
    return vec


def matrix_np2proto(mat):
    """!
    Convert a numpy matrix into a BriarMatrix

    @param mat numpy.array: Matrix to convert

    @return: briar_pb2.BriarMatrix
    """
    result = briar_pb2.BriarMatrix()
    for row in mat:
        result.rows.add().CopyFrom(vector_np2proto(row))
    return result


def matrix_proto2np(protomat):
    """!
    Convert a protobuf matrix into a numpy matrix

    @param protomat briar_pb2.BriarMatrix: Protobuf matrix to convert

    @return: numpy.array
    """
    mat = []
    for row in protomat.rows:
        vec = vector_proto2np(row)
        mat.append(vec)
    mat = np.array(mat, dtype=np.float32)
    return mat


attribute_type_name_map = {'int': 'ivalue', 'float': 'fvalue','string':'text'}

def attribute_find(key,attributes : List[briar_pb2.Attribute]):
    """
    Find an attribute by its key in a list of attributes.

    Parameters:
        key (Any): The key of the attribute to find.
        attributes (list[briar_pb2.Attribute]): The list of attributes to search through.

    Returns:
        Any: The value of the attribute if found, otherwise None.

    """
    for attribute in attributes:
        if attribute.key == key:
            return attribute_proto2val(attribute)
    warnings.warn('No attribute found named' ,key)
    return None

def attribute_retrieve(attribute: briar_pb2.Attribute, return_type=False):
    """
The attribute_retrieve function takes in a briar_pb2.Attribute object and returns the value of that attribute
    as a python object. The function also has an optional parameter, return_type, which if set to True will return
    both the value of the attribute and its type as a tuple.

:param attribute: briar_pb2.Attribute: Specify the attribute to retrieve
:param return_type: Determine if the type of the attribute should be returned as well
:return: A tuple of the attribute value and type
:doc-author: Joel Brogan, BRIAR team, Trelent
"""
    att_type = attribute.type
    att_type_name = briar_pb2.BriarDataType.Name(att_type)
    if att_type_name.lower() in attribute_type_name_map:
        att_type_name = attribute_type_name_map[att_type_name.lower()]
    if not att_type_name == "EMPTY":

        proto_val = getattr(attribute, att_type_name)
        if return_type:
            return proto_val, att_type
        return proto_val
    return None


def attribute_proto2val(attribute: briar_pb2.Attribute):
    """
The attribute_proto2val function takes a briar_pb2.Attribute object and returns the value of that attribute in its native type.

:param attribute: briar_pb2.Attribute: Store the attribute
:return: The value of the attribute
:doc-author: Joel Brogan, BRIAR team, Trelent
"""
    proto_val, att_type = attribute_retrieve(attribute, return_type=True)
    if isinstance(proto_val, briar_pb2.BriarVector):
        return vector_proto2np(proto_val)
    elif isinstance(proto_val, briar_pb2.BriarMatrix):
        return matrix_proto2np(proto_val)
    elif isinstance(proto_val, briar_pb2.BriarMedia):
        return image_proto2cv(proto_val)
    elif isinstance(proto_val, briar_pb2.BriarPoint2D):
        return (proto_val.x, proto_val.y)
    elif isinstance(proto_val, briar_pb2.BriarRect):
        return (proto_val.x, proto_val.y, proto_val.width, proto_val.height)
    elif isinstance(proto_val, bytes) or isinstance(proto_val, bytearray):
        return proto_val
    return proto_val
    # if briar_pb2.BriarDataType.Name(att_type):


def attribute_val2proto(key, val, override_type: briar_pb2.BriarDataType = None):
    """
The attribute_val2proto function takes a key, value pair and converts it to a BriarAttribute protobuf.
The function will attempt to determine the type of the value automatically, but you can override this by passing in an override_type parameter.
If you pass in an override_type parameter, then the val must be of that type or else it will raise an exception.

:param key: Identify the attribute
:param val: Set the value of the attribute
:param override_type :briar_pb2.BriarDataType: Force the type of the attribute
:return: A briar_pb2
:doc-author: Joel Brogan, BRIAR team, Trelent
"""
    att = briar_pb2.Attribute(key=key)
    dtype = None
    if override_type:
        att.type = override_type
        if dtype == briar_pb2.BriarDataType.PICKLE:
            att.pickle = val
        elif dtype == briar_pb2.BriarDataType.XML:
            att.xml = val
        elif dtype == briar_pb2.BriarDataType.JSON:
            att.json = val
    if isinstance(val, str):
        att.type = briar_pb2.BriarDataType.STRING
        att.text = val
    elif isinstance(val, int):
        att.type = briar_pb2.BriarDataType.INT
        att.ivalue = val
    elif isinstance(val, float):
        att.type = briar_pb2.BriarDataType.FLOAT
        att.fvalue = val
    elif isinstance(val, briar_pb2.BriarMatrix):
        att.type = briar_pb2.BriarDataType.MATRIX
        att.matrix = val
    elif isinstance(val, briar_pb2.BriarVector):
        att.type = briar_pb2.BriarDataType.VECTOR
        att.vector = val
    elif isinstance(val, briar_pb2.BriarPoint2D):
        att.type = briar_pb2.BriarDataType.POINT
        att.point = val
    elif isinstance(val, briar_pb2.BriarMedia):
        att.type = briar_pb2.BriarDataType.MEDIA
        att.media = val
    elif isinstance(val, briar_pb2.BriarRect):
        att.type = briar_pb2.BriarDataType.RECT
        att.rect = val
    elif isinstance(val, bytes) or isinstance(val, bytearray):
        att.type = briar_pb2.BriarDataType.BUFFER
        att.buffer = val
    return att


def modality_string2proto(modality):
    """
The modality_string2proto function takes a string and returns the corresponding modality enum value.

:param modality: Determine the type of data that is being used
:return: The modality of the image
:doc-author: Joel Brogan, BRIAR team, Trelent
"""
    key = modality.lower()
    if key not in modalityDict:
        assert KeyError
        return modalityDict['unspecified']
    return modalityDict[modality]


def modality_proto2string(modality):
    """
The modality_proto2string function takes a modality and returns the string representation of that modality.

:param modality: Determine which modality the data is from
:return: The string representation of the modality
:doc-author: Joel Brogan, BRIAR team, Trelent
"""
    if modality not in reverseModalityDict:
        assert KeyError
    return reverseModalityDict[modality]


def tracklet_list2proto(track_list):
    """
The tracklet_list2proto function takes a list of dictionaries and converts them into a tracklet proto.
The dictionary must have the following keys:
    x, y, width, height (all floats)
    frame (int)
    confidence (float)

:param track_list: Create a tracklet proto
:return: A protobuf object
:doc-author: Joel Brogan, BRIAR team, Trelent
"""
    tracklet = briar_pb2.Tracklet()
    detlist = []
    for t in track_list:
        det = briar_pb2.Detection()

        if 'x' in t: det.location.x = t['x']
        if 'y' in t: det.location.y = t['y']
        if 'width' in t: det.location.width = t['width']
        if 'height' in t: det.location.height = t['height']
        if 'tracklet_id' in t: tracklet.tracklet_id = t['tracklet_id']
        if 'tracklet_id' in t: det.tracklet_id = t['tracklet_id']
        if 'frame' in t: det.frame = t['frame']
        if 'confidence' in t: det.confidence = t['confidence']
        detlist.append(det)
    tracklet.detections.MergeFrom(detlist)
    return tracklet


def pathmap_str2dict(path_map):
    """
The pathmap_str2dict function takes a string of the form
    'key:value,key2:value2'
and returns a dictionary with keys and values as follows:
    { key : value, key2 : value2 }.

:param path_map: Map the path of a file to another path
:return: A dictionary mapping the paths in the
:doc-author: Joel Brogan, BRIAR team, Trelent
"""
    pathmap = {}
    parts = path_map.split(',')
    for p in parts:
        kv = p.split(":")
        key = os.path.normpath(kv[0])
        val = os.path.normpath(kv[1])
        if not val.endswith('/'):
            val = val + '/'
        pathmap[key] = val
    return pathmap

def subjectList_list2string(subject_list_str,chomp = True):
    """
    Convert a list of subjects to a string representation.

    Parameters:
    subject_list_str (list): A list containing the subjects as strings.

    Returns:
    str: A string representation of the list of subjects, where each subject is separated by a comma.

    Example:
    >>> subjects = ['Math', 'Science', 'English']
    >>> subjectList_list2string(subjects)
    'Math,Science,English'
    """
    subject_list_str = str(subject_list_str)
    if chomp:
        subject_str = subject_list_str.replace('[','').replace(']','').replace('"','').replace("'",'')

    #return ','.join(subject_list_str)
    return subject_str


def subjectList_string2list(subject_list):
    """
    Convert a comma-separated string of subjects to a list of strings.

    Parameters:
        subject_list (str): A comma-separated string of subjects.

    Returns:
        List[str]: A list of subjects.

    Example:
        >>> subject_string2list("Math,Science,English")
        ['Math', 'Science', 'English']
    """
    return subject_list.split(',')
def pathmap_path2remotepath(path, path_map,exclude_cases_containing_folder = ['mugshots']):
    """
    Maps a local file path to a remote file path based on a given path map and excludes specific folders.

    Args:
        path (str): The local file path to be mapped.
        path_map (dict): A dictionary containing mappings from local folders to remote folders.
        exclude_cases_containing_folder (list, optional): A list of folder names. If any of these folder names are found in the path, the path is excluded from mapping. Defaults to ['mug
    *shots'].

    Returns:
        str: The mapped remote file path.

    Raises:
        None

    Example:
        path = '/Users/johndoe/Documents/pictures/mugshots/2020/abc.jpg'
        path_map = {
            'pictures': 'photo',
            'mugshots': 'headshots'
        }
        exclude_cases_containing_folder = ['mugshots']

        remote_path = pathmap_path2remotepath(path, path_map, exclude_cases_containing_folder)
        print(remote_path)
        # Output: '/Users/johndoe/Documents/photo/headshots/2020/abc.jpg'
    """
    filename = os.path.basename(path)  # We separate the file name out as to not make replacements on it
    pathparts = os.path.normpath(os.path.dirname(path)).split(
        os.sep)  # We split the path into parts based on the os separator
    for exclusion_folder in exclude_cases_containing_folder:
        if exclusion_folder in pathparts:
            return path
    newpathparts = pathparts.copy()

    for m in path_map:  # we loop through the keys of the folder name we want to replace
        m_orig = m
        m = os.path.normpath(m)
        for j, ppart in enumerate(pathparts):

            ppart = os.path.normpath(ppart)
            if m == ppart:
                newpathparts[j] = os.path.normpath(path_map[m_orig])
    fixedpath = os.path.join(*newpathparts, filename)
    if path.startswith('/'):
        fixedpath = "/" + fixedpath
    return fixedpath


def check_if_delete_request(request : srvc_pb2.DatabaseInsertRequest):
    """
    Checks if the delete request is valid.

    Parameters:
    request (srvc_pb2.DatabaseInsertRequest): The request containing the ids.

    Returns:
    bool: True if the delete request is valid, False otherwise.
    """
    ids = request.ids.ids
    if len(ids) > 0:
        if ids[0].startswith('cmd_delete'):
            return True
        return False
    else:
        return False

def check_if_delete_request_due_to_error(request : srvc_pb2.DatabaseInsertRequest):
    """
    Check if a delete request is due to an error.

    Args:
        request (srvc_pb2.DatabaseInsertRequest): The delete request to be checked.

    Returns:
        bool: True if the delete request is due to an error, False otherwise.
    """
    ids = request.ids.ids
    if len(ids) > 0:
        print('ids:',ids[0])
        if ids[0] == 'cmd_delete_errored':
            return True
        return False
    else:
        return False

def get_entry_id_list(request : srvc_pb2.DatabaseInsertRequest):
    """

        Get Entry ID List

        This method accepts a request object of type srvc_pb2.DatabaseInsertRequest and
        returns a list of entry IDs.

        Parameters:
            request (srvc_pb2.DatabaseInsertRequest): The request object containing entry IDs

        Returns:
            list: A list of entry IDs

    """
    ids = request.ids.ids
    if len(ids) > 0:
        if ids[0].startswith('cmd_delete'):
            if len(ids) == 1:
                return []
            elif len(ids) > 1:
                return ids[1:]

    return request.ids.ids
