import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.grpc_json
import json
import os
import time
from datetime import timedelta
from google.protobuf.json_format import MessageToJson, Parse

DURATION_FILE_EXT = ".durations"


def print_durations(durations):
    print_duration("client-side time", durations.client_duration_file_level)
    print_duration("client-side frame time", durations.client_duration_frame_level)
    print_duration("server-side time", durations.service_duration)
    print_duration("request transfer time", durations.grpc_outbound_transfer_duration)
    print_duration("reply transfer time", durations.grpc_inbound_transfer_duration)
    print_duration("Total time:", durations.total_duration)


def print_duration(name, duration):
    dur = duration.end - duration.start
    print(name + ": ", dur, " Seconds")


def start_duration(request, reply):
    reply.durations.CopyFrom(request.durations)
    frame_process_duration_start = time.time()  # this should record when the request was received
    reply.durations.grpc_outbound_transfer_duration.end = frame_process_duration_start
    reply.durations.service_duration.start = frame_process_duration_start


def end_duration(reply):
    reply.durations.service_duration.end = reply.durations.grpc_inbound_transfer_duration.start = time.time()


def generate_progress(frame_id, media):
    # this generates the progress object that the API can use to display an incrementing progress bar
    progress_reply = briar_pb2.BriarProgress()
    progress_reply.currentStep = frame_id
    if isinstance(media, briar_pb2.BriarMedia):
        progress_reply.totalSteps = media.frame_count
    else:
        progress_reply.totalSteps = media
    return progress_reply


def timestamp():
    return time.strftime('%Y/%m/%d-%H:%M:%S%z')


def timeElapsed(duration):
    return duration.end - duration.start


def save_durations(media_file, durations_list, options, operation, modality=None):
    if not options.out_dir:
        out_dir = os.path.dirname(media_file)
    else:
        out_dir = os.path.join(options.out_dir, 'durations')

    os.makedirs(out_dir, exist_ok=True)
    if modality is None:
        modality = ""
    else:
        modality = "_" + modality
    dur_name = os.path.splitext(os.path.basename(media_file))[0] + "_" + operation + modality + DURATION_FILE_EXT
    dur_path = os.path.join(out_dir, dur_name)
    # print('saved durations at ', dur_path)
    durlist_proto = briar_pb2.BriarDurationsList(durations_list=durations_list)
    message_json = MessageToJson(durlist_proto)
    with open(dur_path, 'w') as fp:
        json.dump(message_json, fp)
    # briar.grpc_json.save(durlist_proto,dur_path)


def loadDurationsFolder(durations_directory):
    file_list = os.listdir(durations_directory)
    durations_dictionary = {}
    for fname in file_list:
        path = os.path.join(durations_directory, fname)
        with open(path, 'r') as fp:
            js = json.load(fp)
            durations_list_proto: briar_pb2.BriarDurationsList = Parse(js, briar_pb2.BriarDurationsList())
        # durations_list_proto :briar_pb2.BriarDurationsList = briar.grpc_json.load(path)
        durations_list = list(durations_list_proto.durations_list)
        media_id = fname.replace(DURATION_FILE_EXT, '')
        durations_dictionary[media_id] = durations_list


def parseDurations(durationsperfile_dictionary):
    for media_id in durationsperfile_dictionary:
        perfile_durations = durationsperfile_dictionary[media_id]
        client_filetime_dur = None

        client_time_durs_forfile = []
        performer_time_durs_forfile = []
        grpc_outbound_time_durs_forfile = []
        grpc_inbound_time_durs_forfile = []

        for d in perfile_durations:
            d: briar_pb2.BriarDurations
            client_frametime = d.client_duration_frame_level
            client_to_service = d.grpc_outbound_transfer_duration
            service_to_client = d.grpc_inbound_transfer_duration
            service_time = d.service_duration

            client_file_time = d.client_duration_file_level
            if client_file_time.start > 0 and client_file_time.end > 0:
                if client_filetime_dur is not None:
                    client_filetime_dur = timeElapsed(d.client_duration_file_level)
            client_time_durs_forfile.append(timeElapsed(client_frametime))
            performer_time_durs_forfile.append(timeElapsed(service_time))
            grpc_outbound_time_durs_forfile.append(timeElapsed(client_to_service))
            grpc_inbound_time_durs_forfile.append(timeElapsed(service_to_client))
