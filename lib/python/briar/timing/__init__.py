import os
import briar.briar_grpc.briar_pb2 as briar_pb2
import time
from datetime import timedelta
import briar.grpc_json

DURATION_FILE_EXT = ".durations"

def print_durations(durations):
    print_duration("client-side time", durations.client_duration_file_level)
    print_duration("client-side frame time", durations.client_duration_frame_level)
    print_duration("server-side time", durations.service_duration)
    print_duration("request transfer time", durations.grpc_outbound_transfer_duration)
    print_duration("reply transfer time", durations.grpc_inbound_transfer_duration)
def print_duration(name,duration):
    dur = duration.end-duration.start
    print(name+": ",dur," Seconds")

def start_duration(request,reply):
    reply.durations.CopyFrom(request.durations)
    frame_process_duration_start = time.time()  # this should record when the request was received
    reply.durations.grpc_outbound_transfer_duration.end = frame_process_duration_start
    reply.durations.service_duration.start = frame_process_duration_start

def end_duration(reply):
    reply.durations.service_duration.end = reply.durations.grpc_inbound_transfer_duration.start = time.time()

def generate_progress(frame_id, media):
    #this generates the progress object that the API can use to display an incrementing progress bar
    progress_reply = briar_pb2.BriarProgress()
    progress_reply.currentStep = frame_id
    progress_reply.totalSteps = media.frame_count
    return progress_reply

def timestamp():
    return time.strftime('%Y/%m/%d-%H:%M:%S%z')

def timeElapsed(duration):
    return duration.end-duration.start

def save_durations(media_file,durations_list,options,operation,modality=None):
    if not options.out_dir:
        out_dir = os.path.dirname(media_file)
    else:
        out_dir = options.out_dir

    os.makedirs(out_dir,exist_ok=True)
    if modality is None:
        modality = ""
    else:
        modality = "_"+modality
    dur_name = os.path.splitext(os.path.basename(media_file))[0] + "_" +operation +modality + DURATION_FILE_EXT
    dur_path = os.path.join(out_dir,dur_name)
    print('saved durations at ', dur_path)
    briar.grpc_json.save(durations_list,dur_path)