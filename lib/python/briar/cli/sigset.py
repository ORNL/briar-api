import pandas
from briar.sigset.parse import parseBriarSigset
import briar
import optparse
import sys
import os
from tqdm import tqdm
from ..media import VideoIterator, ImageIterator, ImageGenerator
import json
from ..briar_client import BriarClient
import time
import briar.briar_grpc.briar_pb2 as briar_pb2
from briar.media_converters import modality_string2proto
from briar.cli.connection import addConnectionOptions
from briar.cli.detect import addDetectorOptions, detect_options2proto,save_detections,get_detection_path
from briar.cli.track import get_tracklet_path
from briar.cli.extract import addExtractOptions, extract_options2proto,save_extractions
from briar.cli.enroll import addEnrollOptions, enroll_options2proto,save_tracklets
from briar.media import BriarProgress
from briar import timing

def parseSigsetStatsOptions(inputCommand=None):
    """
    Parse command line arguments.
    """
    args = ['<input>.xml']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description =   "Convert a sigset to a csv file.  This function reads in an " + \
                    "xml sigset and converts it to a csv file.  Statistics may also " + \
                    "be reported for informational purposes."
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s sigset-stats [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog,conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

    parser.add_option( "-o","--output-csv", type="str", dest="csv_path", default=None,
                      help="Save the sigset info to a csv file.")

    parser.add_option( "-m","--database-mode", type="str", dest="database_mode", default='subject',
                      help="Save the sigset info to a csv file.")


    #addDetectorOptions(parser)
    #addConnectionOptions(parser)

    # Parse the arguments and return the results.
    if inputCommand is not None:
        import shlex
        inp = shlex.split(inputCommand)
        (options, args) = parser.parse_args(inp)
    else:
        (options, args) = parser.parse_args()

    if len(args) != n_args+1:
        parser.print_help()
        print("\n"
              "Please supply exactly {} arguments.\n"
              "\n".format(n_args))
        exit(-1)

    return options, args

def parseSigsetEnrollOptions(inputCommand = None):
    """
    Parse command line arguments.
    """
    args = ['<input>.xml','dataset_dir']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description =   "Reads a sigset and then enrolls the media into a specified database. " + \
                    "This is the primary interface for enrolling data for experiments. " + \
                    "Experiments are typically run by enrolling a probe set and a gallery " + \
                    "set. Then search or verify queries are called."
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s sigset-enroll [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog,conflict_handler="resolve")

    parser.add_option("--skip-done", action="store_true", dest="skip_done", default=False,
                      help="will skip files it has already had returned results for, based on the return output directorty")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

    parser.add_option( "-o","--output-csv", type="str", dest="csv_path", default=None,
                      help="Save the sigset info to a csv file.")
    parser.add_option("-o", "--out-dir", type="str", dest="out_dir", default=None,
                      help="Output Directory: defaults to media_directory.")

    parser.add_option("--batch-total", type="int", dest="batch_total", default=1,
                      help="Total batches being run for this sigset (for partitioning)")

    parser.add_option("--batch-number", type="int", dest="batch_number", default=0,
                      help="Batch and/or job number of this API call for the sigset (for partitioning)")
    parser.add_option("--max-frames", type="int", dest="max_frames", default=-1,
                      help="Maximum frames to extract from a video (leave unset or -1 to use all given frames)")

    #parser.add_option("-D", "--database", type="str", dest="database_name", default=None,
    #                        help="Select the database to enroll into.")

    #parser.add_option( "-T","--entry-type", type="choice", choices=['subject','media'], dest="entry_type", default="subject",
    #                  help="Choose an enrollment mode: subject or media. Default=subject")

    # parser.add_option("-N", "--name", type="str", dest="subject_name", default=None,
    #                   help="Enroll detected faces into a database.")


    addConnectionOptions(parser)
    addDetectorOptions(parser)
    addExtractOptions(parser)
    addEnrollOptions(parser)

    # Parse the arguments and return the results.
    if inputCommand is not None:
        import shlex
        inp = shlex.split(inputCommand)
        (options, args) = parser.parse_args(inp)
    else:
        (options, args) = parser.parse_args()

    if options.database == None:
        print('ERROR: the --database argument is required.')
        exit(-1)

    if len(args) != n_args+1:
        parser.print_help()
        print("\n"
              "Please supply exactly {} arguments.\n"
              "\n".format(n_args))
        exit(-1)

    return options, args

def sigset_stats(options=None,args=None):
    if options is None and args is None:
        options, args = parseSigsetStatsOptions()

    command, sigset_path = args

    sigset_name = "media/gallery-videos-and-still-face.xml"
    csv_name = 'out.csv'

    print("Reading sigset: {}".format(sigset_path))
    df = parseBriarSigset(sigset_path)
    print('DONE PARSING!')
    # print()
    # print(df)

    unique_names = len(set(df['name']))
    media_count = len(df)
    image_count = len(df[df['media'] == 'digitalStill'])
    video_count = len(df[df['media'] == 'digitalVideo'])

    videos = df[df['media'] == 'digitalVideo']

    unfiltered_videos = len(videos[videos['unit'] == 'NA'])
        
    frame_videos = videos[videos['unit'] == 'frame']
    video_frames = frame_videos['stop'].apply(int).sum() - frame_videos['start'].apply(int).sum()

    time_videos = videos[videos['unit'] == 'second']
    video_time = time_videos['stop'].apply(float).sum() - time_videos['start'].apply(float).sum()


    if options.verbose:
        print('Sigset Fields:')
        print(list(df.columns))
    print("============= Stats =============")
    print('Unique Names:',unique_names)
    print('Media Count:',media_count)
    print('Image Count:',image_count)
    print('Video Count:',video_count)
    print("=================================")
    print('Unfiltered Videos:',unfiltered_videos)
    print('Selected Video Frames:',video_time)
    print('Selected Video Seconds:',video_frames)
    print("=================================")
    print()

    if options.csv_path is not None:
        print("Saving {} items to: {}".format(len(df),options.csv_path))

        df.to_csv(options.csv_path,index=False)

    print()
    

def sigset_enroll():
    import cv2 

    options, args = parseSigsetEnrollOptions()

    command, sigset_path, dataset_dir = args

    detect_options = detect_options2proto(options)
    extract_options = extract_options2proto(options)
    enroll_options = enroll_options2proto(options)

    database_name_base = options.database
    all_database_names = []

    print("Reading sigset: {}".format(sigset_path))
    csvname = sigset_path+'.csv'
    if os.path.exists(csvname):
        df = pandas.read_csv(csvname)
    else:
        df = parseBriarSigset(sigset_path)
        df.to_csv(sigset_path+'.csv')
    # print()
    # print(df)
    df_full = df
    partitionsize = int(len(df_full)/options.batch_total)
    start = options.batch_number*partitionsize
    stop = min(len(df_full), start+partitionsize)
    print('Total sigset size:', len(df_full))
    print('Iterating over partition ', str(options.batch_number),' from indexes', str(start),' to ', str(stop))
    df = df_full[start:stop]
    client = BriarClient(options)

    print(client.get_status())
    print()
    starttime = time.time()
    frametimes = []
    mediatimes = []
    alltimes = {}
    durations = {}
    for i in tqdm(range(len(df)),position=1,desc="Total progress",leave=True):
        # Process each row in the sigset table
        startmediatime=time.time()
        
        stats_vtime = -1
        stats_ptime = -1
        stats_frames = -1
        i = i+start
        row = df.loc[i]

        name = row['name']
        modalitystr = row['modality']
        modality = briar.media_converters.modality_string2proto(modalitystr)
        # modality_option = options.modality
        if not modalitystr == 'wholeBody':
            #print('not whole face')
            #continue
            pass
        exstr = "row_" + str(i).zfill(5) + "_" + options.modality
        path = os.path.join(dataset_dir, row['filepath'])
        enroll_options.subject_id = row['subjectId']
        enroll_options.media_id = row['name']
        detpath = get_detection_path(path, options, i, modality=exstr,media_id=enroll_options.media_id)
        trackletpath = get_tracklet_path(path, options,i,modality=exstr,media_id=enroll_options.media_id)
        # print('trackletpath: ',trackletpath,os.path.exists(trackletpath))
        # print('to skip:',options.skip_done)
        if (os.path.exists(detpath) or os.path.exists(trackletpath)) and options.skip_done:
            print('skipping ',path)
            continue
        for oneiter in ["face"]:
            modalitystr = options.modality
            modality = briar.media_converters.modality_string2proto(modalitystr)
            detect_options.return_media.value = detect_options.tracking_options.return_media.value = extract_options.return_media.value = False
            # modality = briar.media_converters.modality_string2proto(modalitystr)
            detect_options.tracking_options.modality = detect_options.modality = extract_options.modality = enroll_options.modality = modality
            #Check the file path

            if not os.path.exists(path):
                print('ERROR: {} path does not exist'.format(path))
                continue
                # exit(0)

            if row['media'] == 'digitalVideo':
                # print('Enrolling a Video ',modalitystr)
                fstart = row['start']
                fstop  = row['stop']
                if options.max_frames > 0:
                    fstop = min(fstop,fstart+options.max_frames)
                video = VideoIterator(path,fstart,fstop,row['unit'])

            elif row['media'] == 'digitalStill':
                # print('Enrolling a Still', modalitystr)
                video = ImageIterator(path,row['start'],row['stop'],row['unit'])

            else:
                raise ValueError("Unknown media type: "+row['media'])

            if video.isOpened:
                # Enroll here
                count = 0

                # print("Enrolling:",path)
                # if "probe" in database_name_base:
                #     print('ENROLLING PROBE MEDIA!! NOT GALLERY!')
                #     enroll_options.entry_type = briar_pb2.ENTRY_TYPE_MEDIA
                # else:
                #     enroll_options.entry_type = briar_pb2.ENTRY_TYPE_SUBJECT
                # else:
                enroll_options.subject_id = row['subjectId']
                enroll_options.media_id = row['name']

                # enroll_options.entry_name = row['name']

                database_name = database_name_base+modalitystr
                if database_name not in all_database_names:
                    all_database_names.append(database_name)
                enroll_iter = client.enroll_frames_iter(database_name, video, detect_options=detect_options, extract_options=extract_options, enroll_options=enroll_options,request_start=startmediatime)
                pbar = BriarProgress(options, desc='Enrolling '+briar.media_converters.modality_proto2string(modality) + ' | '+os.path.basename(path),position=0,leave=False)
                frametimes = []
                perfile_durations = []
                for reply in client.stub.enroll(enroll_iter):
                    startframetime=time.time()
                    length = reply.progress.totalSteps
                    pbar.update(total=len(video), current=reply.progress.currentStep)
                    templates = reply.extract_reply.templates
                    detections = reply.extract_reply.detect_reply.detections
                    tracklets = reply.extract_reply.track_reply.tracklets
                    perfile_durations.append(reply.durations)



                    save_detections(path, reply.extract_reply.detect_reply, options, i,modality=exstr,media_id=enroll_options.media_id)
                    save_tracklets(path, tracklets, options, i,modality=exstr,media_id=enroll_options.media_id)
                    save_extractions(path, templates, options, i,modality=exstr,media_id=enroll_options.media_id)
                    endframetime=time.time()
                    frametimes.append(endframetime-startframetime)
                    #print('reply!!!')
                durations[enroll_options.media_id] = perfile_durations
                if options.save_durations:
                    timing.save_durations(path,perfile_durations, options, "sigset-enroll"+enroll_options.media_id)
            endmediatime=time.time()
            alltimes[path]={'mediatime':endmediatime-startmediatime,'frametimes':frametimes}

    for db in all_database_names:
        client.finalize(db)
    endtime = time.time()
    alltimes['total']=endtime-starttime

    if not options.out_dir:
        out_dir = os.path.dirname(path)
    else:
        out_dir = options.out_dir
    timepath = os.path.join(out_dir,'timings_part'+str(options.batch_number)+'.json')
    if os.path.exists(os.path.dirname(timepath)):
        with open(timepath,'w') as fp:
            json.dump(alltimes,fp)
