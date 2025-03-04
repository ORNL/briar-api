import asyncio
import briar
import briar.briar_client as briar_client
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as srvc_pb2
import briar.grpc_json as grpc_json
import optparse
import os
import pyvision as pv
import sys
import time
from briar import timing
from briar.cli.connection import addConnectionOptions
from briar.cli.detect import addDetectorOptions
from briar.cli.detect import detectParseOptions, detect_options2proto
from briar.cli.media import addMediaOptions
from briar.cli.media import collect_files
from briar.media import BriarProgress, file_iter
from briar.media_converters import image_cv2proto, pathmap_str2dict, pathmap_path2remotepath
from briar.media_converters import image_proto2cv

TRACKLET_FILE_EXT = ".tracklet"


def track(options=None, args=None,input_command=None,ret = False):
    """!
    Using the options specified in the command line, runs a detection on the specified files. Writes results to disk
    to a location specified by the cmd arguments

    @return: No return - Function writes results to disk
    """
    api_start = time.time()
    if options is None and args is None:
        options, args = detectParseOptions(input_command)

    client = briar_client.BriarClient(options)

    detect_options = detect_options2proto(options)
    # # Check the status
    # print("*"*35,'STATUS',"*"*35)
    # print(client.get_status())
    # print("*"*78)

    # Get images from the cmd line arguments
    image_list, video_list = collect_files(args[1:], options)
    media_list = image_list + video_list

    results = []
    if len(image_list) > 0:
        print('Cannot run tracking on images, {} image files will be skipped.'.format(len(image_list)))
        return

    if len(video_list) > 0:
        if options.verbose:
            print("Running Tracking on {} Videos".format(len(video_list)))
        if options.out_dir:
            out_dir = options.out_dir
            os.makedirs(out_dir, exist_ok=True)

        i = 0
        startime = time.time()
        for media_file in video_list:
            request_start = time.time()
            media_ext = os.path.splitext(media_file)[-1]
            durations = []
            pbar = BriarProgress(options, name='Tracking')
            it = file_iter([media_file], options, {"detect_options": detect_options}, request_start=request_start,
                           requestConstructor=trackRequestConstructor)
            for i, reply in enumerate(client.track(it)):
                if options.max_frames > 0 and i >= options.max_frames:
                    break
                reply.durations.grpc_inbound_transfer_duration.end = time.time()
                durs = reply.durations
                durations.append(durs)
                length = reply.progress.totalSteps
                pbar.update(current=reply.progress.currentStep, total=length)
                durs.total_duration.end = time.time()
                if not reply.progress_only_reply:
                    if len(reply.tracklets) > 0:
                        if options.verbose:
                            print("Tracked {} in {}s".format(len(reply.tracklets),
                                                             timing.timeElapsed(durs.total_duration)))
                        if not options.no_save:
                            save_tracklets(media_file, reply.tracklets, options, i, verbose=options.verbose)
                    if ret:
                        yield reply
            if options.save_durations:
                timing.save_durations(media_file, durations, options, "enhance")

        if options.verbose:
            print("Finished {} files in {} seconds".format(len(media_list),
                                                           time.time() - startime))
    else:
        print("Error. No image or video media found.")


def get_tracklet_path(media_file, options, i, modality=None, media_id=None):
    if modality is not None:
        modality = "_" + modality
    else:
        modality = ""
    if media_id is not None:
        media_id = "_" + media_id
    else:
        media_id = ""
    if not (options and options.out_dir):
        out_dir = os.path.dirname(media_file)
    elif options.out_dir is not None:
        out_dir = options.out_dir
    tracklet_filename = os.path.splitext(os.path.basename(media_file))[0] + modality + media_id + TRACKLET_FILE_EXT

    out_dir = os.path.join(out_dir, tracklet_filename + 's')
    if not os.path.exists(out_dir) and not options.no_save:
        os.makedirs(out_dir)
    tracklet_filename = os.path.splitext(os.path.basename(media_file))[0] + "_" + str(i).zfill(
        6) + modality + TRACKLET_FILE_EXT
    out_path = os.path.join(out_dir, tracklet_filename)
    return out_path


def save_tracklets(media_file, tracklets, options, i, verbose=False, modality=None, media_id=None):
    if len(tracklets) > 0:
        if modality is not None:
            modality = "_" + modality
        else:
            modality = ""
        if media_id is not None:
            media_id = "_" + media_id
        else:
            media_id = ""
        if not (options and options.out_dir):
            out_dir = os.path.dirname(media_file)
        elif options.out_dir is not None:
            out_dir = options.out_dir
        tracklet_filename = os.path.splitext(os.path.basename(media_file))[0] + modality + media_id + TRACKLET_FILE_EXT

        out_dir = os.path.join(out_dir, tracklet_filename + 's')
        if not os.path.exists(out_dir) and not options.no_save:
            os.makedirs(out_dir)
        tracklet_filename = os.path.splitext(os.path.basename(media_file))[0] + "_" + str(i).zfill(
            6) + modality + TRACKLET_FILE_EXT
        out_path = os.path.join(out_dir, tracklet_filename)
        if not os.path.exists(os.path.dirname(out_path)):
            os.makedirs(os.path.dirname(out_path))
        if verbose:
            print("Writing {} tracks to '{}'".format(len(tracklets), out_path))

        grpc_json.save(tracklets, out_path)


def trackRequestConstructor(media: briar_pb2.BriarMedia, durations: briar_pb2.BriarDurations, options_dict={},
                            det_list_list=None, database_name: str = None):
    detect_options = options_dict['detect_options']
    req = srvc_pb2.TrackRequest(media=media,
                                detect_options=detect_options,
                                durations=durations)
    return req
