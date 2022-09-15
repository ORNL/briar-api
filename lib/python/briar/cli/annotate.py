import sys
import os
import optparse

import pyvision as pv

import briar
import briar.briar_client as briar_client
from briar.cli.connection import addConnectionOptions

from .media import addMediaOptions


def annotate():
    options, args = detectParseOptions()

    assert args[-1].lower().endswith('.csv') # Last argument needs to be a csv file

    csv_path = args[-1]

    tmp_path = csv_path[:-4] + ".tmp.csv"

    #print(tmp_path,csv_path)

    #exit(1)

    client = briar_client.BriarClient(options=options)

    # Check the status
    print("*"*35,'STATUS',"*"*35)
    print(client.get_status())
    print("*"*78)

    # get the media names
    media_names = args[1:-1]
    print("Selected Media:",media_names)
    print("Output File:", csv_path)

    face_csv_file = open(tmp_path,'w')
    face_csv_writer = csv.writer(face_csv_file)
    face_csv_header = ['path','frame_id','tracklet_id','face_x','face_y','face_w','face_h','confidence','expression','pose','keypoints_shape','keypoints_values','landmarks_shape','landmarks_values','face_center','face_scale','face_orientation','yaw','pitch','roll','head_center','head_x','head_y','head_w','head_h']
    face_csv_writer.writerow(face_csv_header)
    total_videos = 0

    for path in media_names:
        print("Processing",path)
        assert os.path.isfile(path) # check that the file exists
        assert os.access(path,os.R_OK) # check that the file is readable

        if pv.isVideo(path): # check for supported media types
            # Load the video
            video = pv.Video(path)
        elif pv.isImage(path): # check for supported media types
            # Load the video
            video = [pv.Image(path)]
        else:
            raise ValueError("Unknown file extension: %s"%(path,))

        # Load the frames
        start_time = time.time()
    
        # Run the detector
        frame_count = 0
        for reply in client.detect_frames(video):
            frame_count += 1
            print('Frame:',reply.frame_id)
            for detection in reply.detections:
                print('    tracklet:',detection.tracklet_id,'loc:',detection.location.x,detection.location.y,detection.location.width,detection.location.height,'  score:',detection.confidence)
                
                # Defaults for output
                frame_id = reply.frame_id
                tracklet_id = detection.tracklet_id
                face_x = "UNLABELED"
                face_y = "UNLABELED"
                face_w = "UNLABELED"
                face_h = "UNLABELED"
                confidence = "UNLABELED"
                expression = "UNLABELED"
                pose = "UNLABELED"
                keypoints_shape = "UNLABELED"
                keypoints_values = "UNLABELED"
                landmarks_shape = "UNLABELED"
                landmarks_values = "UNLABELED"
                face_center_values = "UNLABELED"
                face_scale = "UNLABELED"
                face_orientation = "UNLABELED"

                face_x = detection.location.x
                face_y = detection.location.y
                face_w = detection.location.width
                face_h = detection.location.height

                head_x = "UNLABELED"
                head_y = "UNLABELED"
                head_w = "UNLABELED"
                head_h = "UNLABELED"

                head_center = "UNLABELED"

                yaw = "UNLABELED"
                pitch = "UNLABELED"
                roll = "UNLABELED"

                confidence = detection.confidence

                for each in detection.attributes:
                    if each.key == 'keypoints':
                        mat = briar_client.matrix_proto2np(each.matrix)
                        keypoints_shape = "|".join(["%d"%value for value in mat.shape])
                        keypoints_values = "|".join(["%0.1f"%value for value in mat.flatten()])
                    if each.key == 'landmarks':
                        mat = briar_client.matrix_proto2np(each.matrix)
                        landmarks_shape = "|".join(["%d"%value for value in mat.shape])
                        landmarks_values = "|".join(["%0.1f"%value for value in mat.flatten()])

                    if each.key == 'face_center':
                        mat = briar_client.vector_proto2np(each.vector)
                        face_center = "|".join(["%0.1f"%value for value in mat.flatten()])
                    
                    if each.key == 'head_center':
                        mat = briar_client.vector_proto2np(each.vector)
                        head_center = "|".join(["%0.1f"%value for value in mat.flatten()])
                    
                    if each.key == 'head_box':
                        head_x, head_y, head_w, head_h = briar_client.vector_proto2np(each.vector)
                    
                    if each.key == 'yaw_pitch_roll':
                        yaw,pitch,roll = briar_client.vector_proto2np(each.vector)
                    
                    if each.key == 'face_scale':
                        face_scale = each.fvalue

                    if each.key == 'face_orientation':
                        mat = briar_client.matrix_proto2np(each.matrix)
                        face_orientation = "|".join(["%0.4f"%value for value in mat.flatten()])

                face_csv_writer.writerow([path,frame_id,tracklet_id,face_x,face_y,face_w,face_h,confidence,expression,pose,keypoints_shape,keypoints_values,landmarks_shape,landmarks_values,face_center,face_scale,face_orientation,yaw,pitch,roll,head_center,head_x,head_y,head_w,head_h])
                    

    face_csv_file.close() 

    if frame_count > 0:
        os.rename(tmp_path,csv_path) 
    else:
        try:
            os.remove(tmp_path)  
        except:
            pass   

    print('done')

