"""!
Contained in this are functions for converting numpy arrays into various protobuf objects and back again
since numpy arrays cannot be sent directly over gRPC.
"""
import cv2
import numpy as np
import urllib

import briar.briar_grpc.briar_pb2 as briar_pb2

modalityDict = {'whole_body':briar_pb2.WHOLE_BODY,
                'wholeBody':briar_pb2.WHOLE_BODY,
                'wholebody':briar_pb2.WHOLE_BODY,
                    'face':briar_pb2.FACE,
                    'gait':briar_pb2.GAIT,
                    'unspecified':briar_pb2.UNSPECIFIED}

reverseModalityDict = {modalityDict[k]:k for k in modalityDict}

def image_cv2proto(im, compression='uint8', quality=99):
    """!
    Convert a cv2 numpy array to a protobuf format.

    @param img numpy.array: array containing the image to convert to BriarMedia

    @param compression str: What compression to use. Can be 'uint8', 'png', 'jpg'

    @param quality int: 0-100 How much do you want to mutilate the image in the name of saving memory?

    return: briar_pb2.BriarMedia
    """
    assert im.dtype == np.uint8  # Currently only uint8 supported
    assert quality >= 0 and quality <= 100

    result = briar_pb2.BriarMedia()
    result.width = im.shape[1]
    result.height = im.shape[0]
    result.channels = im.shape[2]
    if compression == 'uint8':
        if result.channels == 1:
            result.type = briar_pb2.BriarMedia.MONO8
        elif result.channels == 3:
            result.type = briar_pb2.BriarMedia.RGB8

        result.data = im.tostring()
        pass
    elif compression in ('jpg', 'png'):
        buf = cv2.imencode('.' + compression, im, [int(cv2.IMWRITE_JPEG_QUALITY), quality])[1].tobytes()
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


def image_np2proto(im,compression='uint8',quality=99):
    """!
    Convert a numpy array to a protobuf format.

    @param img numpy.array: array containing the image to convert to BriarMedia

    @param compression str: What compression to use. Can be 'uint8', 'png', 'jpg'

    @param quality int: 0-100 How much do you want to mutilate the image in the name of saving memory?

    return: briar_pb2.BriarMedia
    """
    if len(im.shape) > 2:
        im = im[:,:,::-1] # RGB to BGR

    return image_cv2proto(im, compression=compression, quality=quality)


def image_proto2cv(pb_data):
    """!
    Convert a protobuf BriarMedia image to a cv2 numpy array

    @param pb_data briar_pb2.BriarMedia: Protobuf object containing image data
    @return: numpy.array cv2 formatted np array containing image
    """
    shape = pb_data.height, pb_data.width, pb_data.channels
    if min(shape) > 0:
        if pb_data.type == briar_pb2.BriarMedia.MONO8 or pb_data.type == briar_pb2.BriarMedia.RGB8:
            data = np.fromstring(pb_data.data, dtype=np.uint8)
            data = data[:(shape[0]*shape[1]*shape[2])]
            data.shape = shape
            data = data[:, :, ::-1]
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
            print('SOURCE ONLY',source)
        else:
            raise ValueError("BriarMediaType not supported: " + repr(pb_data.type))
    else:
        import inspect
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        print("Warning: size 0 array decoded,caller name:", [cf[3] for cf in calframe])
        # print()
        return np.array([])
    return data


def image_proto2np(pb_data):
    """!
    Convert a protobuf image to a numpy array.

    @param pb_data briar_pb2.BriarMedia: Protobuf object containing image data

    @return: np.array
    """
    data = image_proto2cv(pb_data)
    data = data[:, :, ::-1]  # Convert BGR to RGB
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

attribute_type_name_map = {'int':'ivalue','float':'fvalue'}

def attribute_retrieve(attribute: briar_pb2.Attribute,return_type = False):
    att_type = attribute.type
    att_type_name = briar_pb2.BriarDataType.Name(att_type)
    if att_type_name.lower() in attribute_type_name_map:
        att_type_name = attribute_type_name_map[att_type_name.lower()]
    if not att_type_name == "EMPTY":
        proto_val = getattr(attribute,att_type_name)
        if return_type:
            return proto_val,att_type
        return proto_val
    return None

def attribute_proto2val(attribute: briar_pb2.Attribute):
    proto_val,att_type = attribute_retrieve(attribute,return_type=True)
    if isinstance(proto_val,briar_pb2.BriarVector):
        return vector_proto2np(proto_val)
    elif isinstance(proto_val,briar_pb2.BriarMatrix):
        return matrix_proto2np(proto_val)
    elif isinstance(proto_val,briar_pb2.BriarMedia):
        return image_proto2cv(proto_val)
    elif isinstance(proto_val,briar_pb2.BriarPoint2D):
        return (proto_val.x,proto_val.y)
    elif isinstance(proto_val,briar_pb2.BriarRect):
        return (proto_val.x,proto_val.y,proto_val.width,proto_val.height)
    elif isinstance(proto_val,bytes) or isinstance(proto_val,bytearray):
        return proto_val
    return proto_val
        # if briar_pb2.BriarDataType.Name(att_type):
def attribute_val2proto(key,val,override_type :briar_pb2.BriarDataType = None):
    att = briar_pb2.Attribute(key=key)
    dtype = None
    if override_type:
        att.type = override_type
        if dypte == briar_pb2.BriarDataType.PICKLE:
            att.pickle = val
        elif dtype == briar_pb2.BriarDataType.XML:
            att.xml = val
        elif dtype == briar_pb2.BriarDataType.JSON:
            att.json = val
    if isinstance(val,str):
        att.type = briar_pb2.BriarDataType.STRING
        att.text = val
    elif isinstance(val,int):
        att.type = briar_pb2.BriarDataType.INT
        att.ivalue = val
    elif isinstance(val,float):
        att.type = briar_pb2.BriarDataType.FLOAT
        att.fvalue = val
    elif isinstance(val,briar_pb2.BriarMatrix):
        att.type = briar_pb2.BriarDataType.MATRIX
        att.matrix = val
    elif isinstance(val,briar_pb2.BriarVector):
        att.type = briar_pb2.BriarDataType.VECTOR
        att.vector = val
    elif isinstance(val,briar_pb2.BriarPoint2D):
        att.type = briar_pb2.BriarDataType.POINT
        att.point = val
    elif isinstance(val,briar_pb2.BriarMedia):
        att.type = briar_pb2.BriarDataType.MEDIA
        att.media = val
    elif isinstance(val,briar_pb2.BriarRect):
        att.type = briar_pb2.BriarDataType.RECT
        att.rect = val
    elif isinstance(val,bytes) or isinstance(val,bytearray):
        att.type = briar_pb2.BriarDataType.BUFFER
        att.buffer = val
    return att


def modality_string2proto(modality):
    key = modality.lower()
    if key not in modalityDict:
        assert KeyError
        return modalityDict['unspecified']
    return modalityDict[modality]

def modality_proto2string(modality):
    if modality not in reverseModalityDict:
        assert KeyError
    return reverseModalityDict[modality]

def tracklet_list2proto(track_list):
    tracklet = briar_pb2.Tracklet()
    detlist = []
    for t in track_list:
        det = briar_pb2.Detection()

        if 'x'in t: det.location.x = t['x']
        if 'y'in t: det.location.y = t['y']
        if 'width'in t: det.location.width = t['width']
        if 'height'in t: det.location.height = t['height']
        if 'tracklet_id'in t: tracklet.tracklet_id = t['tracklet_id']
        if 'tracklet_id'in t: det.tracklet_id = t['tracklet_id']
        if 'frame'in t: det.frame = t['frame']
        if 'confidence'in t: det.confidence = t['confidence']
        detlist.append(det)
    tracklet.detections.MergeFrom(detlist)
    return tracklet