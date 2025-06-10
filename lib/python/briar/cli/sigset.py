import asyncio
import threading

import briar
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as srvc_pb2
import json
import math
import numpy as np
import optparse
import os
import pandas
import sys
import time
from briar import media_converters
from briar import timing
from briar.cli.connection import addConnectionOptions
from briar.cli.detect import addDetectorOptions, detect_options2proto, save_detections, get_detection_path
from briar.cli.enroll import addEnrollOptions, enroll_options2proto, save_tracklets, enrollRequestConstructor
from briar.cli.extract import addExtractOptions, extract_options2proto, save_extractions
from briar.cli.track import get_tracklet_path
from briar.cli.media import addMediaOptions
from briar.media import BriarProgress
from briar.media_converters import modality_string2proto, pathmap_str2dict, pathmap_path2remotepath
from briar.sigset.parse import parseBriarSigset, parseBriarFolder
from tqdm import tqdm
import multiprocessing as mp
from multiprocessing import Manager
from concurrent import futures
from briar.briar_client import BriarClient, _initialize_worker, _worker_channel_singleton, _worker_stub_singleton, _worker_port_singleton, _worker_proccess_position_singleton, _worker_thread_position_singleton, _client_identifier_singleton
from briar.media import VideoIterator, ImageIterator, ImageGenerator, MediaSetIterator
# from threading import Thread
# from multiprocessing.pool import ThreadPool

my_pool = None
proc_number = None
service_address_number = None

def parseSigsetStatsOptions(inputCommand=None):
    """
    Parse command line arguments for the sigset-stats command.

    This function sets up an optparse.OptionParser instance with various options for parsing sigset statistics,
    including verbosity and filtering options. It then parses the command line arguments into these options.

    @param inputCommand str: A string containing the command line input to parse. If None, the function will parse sys.argv.
    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively.
    """
    args = ['<input>.xml']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = "Convert a sigset to a csv file. This function reads in an " + \
                  "xml sigset and converts it to a csv file. Statistics may also " + \
                  "be reported for informational purposes."
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s sigset-stats [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog, conflict_handler="resolve")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")
    parser.add_option("--filter-contains", type="str", dest="filter_contains", default=None,
                      help="Filter out any sigset entries that do not contain this string in the filepath")
    # parser.add_option( "-o","--output-csv", type="str", dest="csv_path", default=None,
    #                   help="Save the sigset info to a csv file.")

    # Parse the arguments and return the results.
    if inputCommand is not None:
        import shlex
        inp = shlex.split(inputCommand)
        (options, args) = parser.parse_args(inp)
    else:
        (options, args) = parser.parse_args()

    if len(args) != n_args + 1:
        parser.print_help()
        print("\n"
              "Please supply exactly {} arguments.\n"
              "\n".format(n_args))
        exit(-1)

    return options, args


def parseSigsetEnrollOptions(inputCommand=None):
    """
    Parse command line arguments for the sigset-enroll command.

    This function sets up an optparse.OptionParser instance with various options for enrolling sigsets,
    including connection options, detector options, extract options, enroll options, and media options.
    It then parses the command line arguments into these options.

    @param inputCommand str: A string containing the command line input to parse. If None, the function will parse sys.argv.
    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively.
    """
    args = ['<input>.xml', 'dataset_dir']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = "Reads a sigset and then enrolls the media into a specified database. " + \
                  "This is the primary interface for enrolling data for experiments. " + \
                  "Experiments are typically run by enrolling a probe set and a gallery " + \
                  "set. Then search or verify queries are called."
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s sigset-enroll [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog, conflict_handler="resolve")

    parser.add_option("--skip-done", action="store_true", dest="skip_done", default=False,
                      help="Will skip files it has already had returned results for, based on the return output directory")

    parser.add_option("--no-dataset", action="store_true", dest="no_dataset", default=False,
                      help="For debugging purposes only, prevents checking if dataset directory exists")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")
    parser.add_option("--drop-duplicates", action="store_true", dest="drop_duplicates", default=False,
                      help="When flag is used, all duplicate entries (conditioned by entry_id) will be dropped from the sigset")
    # parser.add_option( "-o","--output-csv", type="str", dest="csv_path", default=None,
    #                   help="Save the sigset info to a csv file.")
    parser.add_option("-o", "--out-dir", type="str", dest="out_dir", default=None,
                      help="Output Directory: defaults to media_directory.")

    parser.add_option("--batch-total", type="int", dest="batch_total", default=1,
                      help="Total batches being run for this sigset (for partitioning)")
    parser.add_option("--auto-create-database", action="store_true", dest="auto_create_database", default=False,
                      help="Set this flag to auto create a database if they do not already exist")
    parser.add_option("--ignore-fisheye", action="store_true", dest="ignore_fisheye", default=False,
                      help="Ignores fisheye lens camera media, with 'M3057-PLVE' in the name")
    parser.add_option("--enroll-retry", type="int", dest="enroll_retry", default=3,
                      help="Number of times to retry an enrollment if client-side IO fails out")

    # parser.add_option("--bulk-enroll", action="store_true", dest="bulk_enroll", default=False,
    #                   help="Sends across the entire signature set in a single message and waits for enrollment replies. This allows systems to bulk-enroll on server side.")

    parser.add_option("--batch-number", type="int", dest="batch_number", default=0,
                      help="Batch and/or job number of this API call for the sigset (for partitioning)")
    parser.add_option("--minibatch-size", type="int", dest="minibatch_size", default=-1,
                      help="Explicitly defines the size of a media minibatch (how many pieces of media to send to a single service port at once). Default = number_of_service_ports*number_of_services_per_port")


    parser.add_option("--database-suffix", type="choice", choices=['ADDRESS', 'SERVICE', 'A', 'S', 'AS', 'ADDRESS,SERVICE', 'ADDRESS+SERVICE'],
                      dest="database_suffix", default=None,
                      help="Set if the service requires unique database names (achieved via a suffix) for each service running on an address, process, or thread. These suffixes will be determined using <briar.get_process_number>. If not set, the service will not utilize unique database names. Default=None")
    # parser.add_option("--database-suffix", type="str", dest="database_suffix", default=None,
    #                   help="Provides a suffix for each database followed by process number generated by <briar.get_process_number()>")
    parser.add_option("--by-subject", action="store_true", dest="by_subject", default=False,
                      help="DEPRECATED. FOR USE WITH LEGACY SYSTEMS ONLY. Does sigset enrollment by subject, and passes only source-only media objects.")
    parser.add_option("--allow-context", action="store_true", dest="allow_context", default=False,
                      help="Toggles if the evaluation enrollment system will provide context information to the server about controlled or uncontrolled collection conditions. Default: False, in which all data is considered 'Uncontrolled'")
    parser.add_option("--integer-id", action="store_true", dest="integer_id", default=False,
                      help="DEPRECATED. FOR USE WITH LEGACY SYSTEMS ONLY. Indicates that subject ID's will be sent and stored as integers")
    parser.add_option("--no-sigset", action="store_true", dest="no_sigset", default=False,
                      help="If flag is set a sigset .xml file will not be required for the enrollment process or as an argument, and instead will enroll all found media files in the dataset specified dataset folder")
    parser.add_option("--enrollment-structure", type="choice", choices=['per-folder', 'per-file', 'custom'],
                      dest="enrollment_structure", default="per-folder",
                      help="if per-folder, system will enroll each folder found as its own subject.  if per-file, each file will be its own subject")
    addConnectionOptions(parser)
    addDetectorOptions(parser)
    addExtractOptions(parser)
    addEnrollOptions(parser)
    addMediaOptions(parser)

    # Parse the arguments and return the results.
    if inputCommand is not None:
        import shlex
        inp = shlex.split(inputCommand)
        (options, args) = parser.parse_args(inp)
    else:
        (options, args) = parser.parse_args()

    if hasattr(options, "path_map"):
        if isinstance(options.path_map, str):
            options.path_map = pathmap_str2dict(options.path_map)

    if options.database is None:
        print('ERROR: the --database argument is required.')
        exit(-1)
    if options.no_sigset:
        if len(args) == n_args:
            args.append(None)

    if len(args) != n_args + 1:
        parser.print_help()
        print("\n"
              "Please supply exactly {} arguments.\n"
              "\n".format(n_args))
        exit(-1)
    return options, args


def sigset_stats(options=None, args=None):
    """
    Parse a sigset file and print out some statistics about the contents.

    This function reads in an XML sigset file, converts it to a pandas DataFrame, and prints out various statistics
    about the contents, such as the number of unique names, media count, image count, video count, and subject count.

    @param options optparse.Values: Parsed command line options.
    @param args list: List of command line arguments.
    @return: None
    """
    if options is None and args is None:
        options, args = parseSigsetStatsOptions()

    command, sigset_path = args

    csv_name = 'out.csv'

    print("Reading sigset: {}".format(sigset_path))
    df = parseBriarSigset(sigset_path)
    print('DONE PARSING!')
    if options.filter_contains is not None:
        df = df[df.filepath.str.contains(options.filter_contains)].reset_index()
    unique_names = len(set(df['entryId']))
    media_count = len(df)
    image_count = len(df[df['media'] == 'digitalStill'])
    video_count = len(df[df['media'] == 'digitalVideo'])
    subject_count = len(np.unique(df['subjectId']))
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
    print('Unique Names:', unique_names)
    print('Media Count:', media_count)
    print('Image Count:', image_count)
    print('Video Count:', video_count)
    print('Subject Count:', subject_count)
    print("=================================")
    print('Unfiltered Videos:', unfiltered_videos)
    print('Selected Video Frames:', video_time)
    print('Selected Video Seconds:', video_frames)
    print("=================================")
    print()
    # if options.csv_path is not None:
    #     print("Saving {} items to: {}".format(len(df), options.csv_path))
    #
    #     df.to_csv(options.csv_path, index=False)


def sigset_enroll(input_command=None):
    """
    Enroll a signature set into the Briar system.

    This function reads a sigset file, parses it, and enrolls the media into a specified database.
    It supports various options for configuring the enrollment process, including connection options,
    detector options, extract options, enroll options, and media options.

    @param input_command str: A string containing the command line input to parse. If None, the function will parse sys.argv.
    @return: None
    """
    try:
        mp.set_start_method('spawn')
        print("spawned")
    except RuntimeError as E:
        print("Warning: Spawn method not set, using default", E)
        pass

    async_iterator = False  # this flags the enroll_frames_iter to use asyncio (but only on the client side)

    options, args = parseSigsetEnrollOptions(input_command)
    # assert options.by_subject and (options.entry_type == "probe" or options.entry_type == "media")

    command, sigset_path, dataset_dir = args
    # print("args",args)
    detect_options = detect_options2proto(options)  # overall session options for detection
    extract_options = extract_options2proto(options)  # overall session options for extraction
    enroll_options = enroll_options2proto(options)  # overall session options for enrollment

    print("Reading sigset: {}".format(sigset_path))
    csvname = sigset_path + '.csv'
    subject_level_enrollment = True

    if options.no_sigset:
        df = parseBriarFolder(sigset_path, options)
    else:
        df = parseBriarSigset(sigset_path)
    if not os.path.exists(csvname):
        df.to_csv(sigset_path + '.csv')
    if options.drop_duplicates:
        df = df.drop_duplicates(subset='name', keep='first', ignore_index='True')
    # We want to split up the full dataframe into a list of list of dataframes. This way, each service running on a different port will
    # get a list of dataframes

    base_client = client = BriarClient(options)
    # client = BriarClient(options)

    print(base_client.get_status())
    # print()

    # Get the server configuration
    server_configuration = base_client.get_service_configuration()
    server_configuration: briar.briar_grpc.briar_service_pb2.BriarServiceConfigurationReply

    df_full = df
    dfs_per_subject = []
    if options.by_subject or (
            (options.entry_type == "gallery" or options.entry_type == "subject") and options.batch_total >= 1):
        # Partition the sigset by subjects (may not split up as nicely)
        subject_level_enrollment = True
        allsubjects = np.unique(df_full["subjectId"])
        multi_subject_formatting = False
        if isinstance(allsubjects[0], list):
            multi_subject_formatting = True
            allsubjects = [a[0] for a in allsubjects]

        for subid in allsubjects:
            if not multi_subject_formatting:
                df_per_sub = df.loc[df['subjectId'] == subid].copy()
            elif multi_subject_formatting:
                # print('multisub',df['subjectId'])
                df_per_sub = df.loc[np.array([s[0] for s in df['subjectId'].values]) == subid]
            df_per_sub.reset_index()
            dfs_per_subject.append(df_per_sub)

        partitionsize = math.ceil(len(dfs_per_subject) / options.batch_total)
        start = options.batch_number * partitionsize
        stop = min(len(dfs_per_subject), start + partitionsize)
        subject_partition = allsubjects[start:stop]
        print('Total sigset subject size:', len(dfs_per_subject))
        print('Iterating over subject partition ', str(options.batch_number), ' from indexes', str(start), ' to ',
              str(stop))
        if options.batch_total > 1:
            print('Iterating over Subject IDs', ', '.join(subject_partition))

        list_of_dataframes = dfs_per_subject
    else:
        # For partitioned probe sigset-enroll calls, we can partition on a per-entry basis instead of per-subject basis
        subject_level_enrollment = False
        partitionsize = math.ceil(len(df_full) / options.batch_total)
        start = options.batch_number * partitionsize
        stop = min(len(df_full), start + partitionsize)
        print('Total sigset size:', len(df_full))
        print('Iterating over partition ', str(options.batch_number), ' from indexes', str(start), ' to ', str(stop))
        df = df_full[start:stop]
        # Chunk the dataframes into batches the size of how many pieces of media each can take
        dataframe_chunk_i = 0
        list_of_dataframes = []

        if options.minibatch_size > 0:
            chunk_size = options.minibatch_size
        else:
            chunk_size = server_configuration.number_of_processes_per_port * server_configuration.number_of_threads_per_process
        while dataframe_chunk_i <= len(df):
            dataframe_minibatch = df[dataframe_chunk_i:dataframe_chunk_i + chunk_size]
            list_of_dataframes.append(dataframe_minibatch)
            # print('Dataframe batch ',dataframe_chunk_i,':')
            # print(list(dataframe_minibatch['entryId']))
            dataframe_chunk_i += chunk_size

    starttime = time.time()
    frametimes = []
    mediatimes = []
    alltimes = {}
    durations = {}

    database_name_base = options.database
    available_databases = base_client.get_database_names()
    required_databases = []
    if options.database_suffix is None:
        required_databases.append(database_name_base)
    elif options.database_suffix == 'ADDRESS' or options.database_suffix == 'A':
        address_parts = options.port.split(':')
        base_address = address_parts[0]
        base_port = address_parts[1]
        for service_port in server_configuration.port_list:
            address = base_address + ':' + service_port

        # we must create unique databases for each

    if database_name_base not in available_databases:
        if options.auto_create_database:
            print('Database', database_name_base, 'Does not exist on base service.')
            print('Creating Database', database_name_base)
            try:
                client.database_create(database_name=database_name_base)
            except Exception as e:
                print('Exception creating database', e)
                pass
            # Check to see if the database was successfully created
            client.database_refresh()
            available_databases = client.get_database_names()
            if database_name_base not in available_databases:
                print('Error: Base database ', database_name_base, 'has not been created, database auto-creation failed.')
                raise FileNotFoundError
        # if server_configuration.number_of_processes_per_port > 1 or server_configuration.number_of_threads_per_process > 1 or server_configuration.number_of_service_ports > 1:
        else:
            print('Error: ', database_name_base, 'has not been created')
            raise FileNotFoundError
    # Perform an enorllment by just passing the sigset across to the service algorithm
    bulk_enroll = False
    if bulk_enroll:  # Bulk enroll is no longer supported
        pass
    else:  # we are not doing bulk enroll - bulk enroll will not be allowed for phase 2 evaluations

        print('Service has requested ', len(server_configuration.port_list), 'ports')

        batch_manager = Manager()
        batch_queue = batch_manager.Queue()
        progress_queue = batch_manager.Queue()
        id_queues = []
        consumers = []
        print('Deploying parent pool of', len(server_configuration.port_list), 'processes')

        for i, port in enumerate(server_configuration.port_list):
            id_queue = batch_manager.Queue()
            consumers.append(mp.Process(target=df_batch_consumer, args=(batch_queue, i, port, server_configuration, id_queue, progress_queue)))
            id_queues.append(id_queue)

        total_progress_position = server_configuration.number_of_processes_per_port * server_configuration.number_of_threads_per_process * len(
            server_configuration.port_list) + 1
        producer = mp.Process(target=df_batch_producer, args=(batch_queue, 1, total_progress_position, list_of_dataframes, start, dataset_dir, detect_options, extract_options, enroll_options,
                               options))
        progress_worker = mp.Process(target=progress_consumer, args=(progress_queue, total_progress_position, sum([len(d) for d in list_of_dataframes]), options))

        print('starting the pool consumers!')
        for consumer in consumers:
            consumer.start()
        producer.start()
        progress_worker.start()
        producer.join()
        for consumer in consumers:
            consumer.join()
        progress_worker.join()

        # print('Starting the batch loading!')
        # time.sleep(5)
        #
        # for batch in tqdm(df_batch_generator(list_of_dataframes,start,dataset_dir,detect_options,extract_options,enroll_options,options)):
        #     batch_queue.put(batch)
        # batch_queue.put(None)
        #
        # time.sleep(1)
        #
        # total_progress_possition = server_configuration.number_of_processes_per_port*server_configuration.number_of_threads_per_process*len(server_configuration.port_list)+1

        # for output in tqdm(pool_of_pools.imap_unordered(inner_pool_mapper,df_batch_generator(list_of_dataframes,start,dataset_dir,detect_options,extract_options,enroll_options,options)),position=total_progress_possition,desc='Total Batch Progress'+str(total_progress_possition),total=len(list_of_dataframes),leave=True):
        #     pass
        # time.sleep(100)
        # pool_of_pools.join()
        # pool_of_pools.close()
        # for i, row in rowiter:
        #     # Process each row in the sigset table
        #     pool.map(enroll_call_threaded(row,i+start,dataset_dir,detect_options,extract_options,enroll_options,options))
        #     # proc_output = enroll_call_threaded(row,i+start,dataset_dir,detect_options,extract_options,enroll_options,options)
        #     durations[enroll_options.media_id] = proc_output[0]
        #     alltime = proc_output[1]

    # endtime = time.time()
    # alltimes['total'] = endtime - starttime
    #
    # if not options.out_dir:
    #     out_dir = os.path.dirname(path)
    # else:
    #     out_dir = options.out_dir
    # timepath = os.path.join(out_dir, 'timings_part' + str(options.batch_number) + '.json')
    # if os.path.exists(os.path.dirname(timepath)):
    #     with open(timepath, 'w') as fp:
    #         json.dump(alltimes, fp)


def progress_consumer(progress_queue, progress_position, total_len, options):
    """
    The progress_consumer function is a consumer for the progress_queue.
    It takes in a queue, and an integer representing the position of the progress bar on screen.
    The function then creates a BriarProgress object with that position, and starts consuming from 
    the queue until it receives None as an item in the queue (which indicates that all items have been consumed). 
    For each item received from the queue, it increments its counter by 1.

    @param progress_queue: Communicate with the progress_consumer function
    @param progress_position: Determine where the progress bar should be placed on the screen
    @param total_len: Set the maximum value of the progress bar
    @param options: Pass the options to the progress bar
    @return: A function that takes a progress queue,
    @doc-author: Joel Brogan
    """
    pbar = BriarProgress(options, desc="Total Progress", name="TotalProgress", position=progress_position, leave=True)
    i = 0
    while True:
        obj = progress_queue.get()
        if obj is None:
            break
        i += 1
        pbar.update(i, total_len)
        # pbar.refresh()
    pbar.close()


def df_batch_producer(batch_queue, identifier, progress_position, list_of_dataframes, start, dataset_dir, detect_options, extract_options, enroll_options,
                      options):
    """
    The df_batch_producer function is a generator that takes in a list of dataframes and yields batches of images.
    The function will yield batches until the end of the list_of_dataframes is reached.

    @param batch_queue: Pass the batches to the main process
    @param identifier: Identify the thread
    @param progress_position: Keep track of the progress of the batch_producer function
    @param list_of_dataframes: Store the list of dataframes that are to be processed
    @param start: Determine the starting index of the dataframe
    @param dataset_dir: Specify the directory where the dataset is located
    @param detect_options: Specify the detection options
    @param extract_options: Specify the extraction options
    @param enroll_options: Specify the enrollment options
    @param options: Pass the options for each of the functions
    @return: A batch of dataframes
    @doc-author: Joel Brogan
    """
    i = 0
    for batch in df_batch_generator(list_of_dataframes, start, dataset_dir, detect_options, extract_options, enroll_options,
                                    options):
        batch_queue.put(batch)
        i += 1
    batch_queue.put(None)


def df_batch_consumer(batch_queue, identifier, port, server_configuration, id_queue, progress_queue):
    """
    The df_batch_consumer function is a function that takes in a batch of dataframe objects, and processes them using the 
    Briar API. The function uses the multiprocessing library to create multiple worker processes, each with their own 
    connection to the Briar server. Each process then creates multiple threads which are used for processing images.

    @param batch_queue: Pass in the queue of batches to be processed
    @param identifier: Identify the process
    @param port: Determine which port to connect to
    @param server_configuration: Specify the number of processes and threads per process
    @param id_queue: Pass the connection id to the worker process
    @param progress_queue: Send progress information to the main process
    @return: A list of results
    @doc-author: Joel Brogan
    """
    local_pool = None
    print('Started pool process ', identifier, ' for port ', port)
    while True:
        batch_obj = batch_queue.get()
        if batch_obj is None:
            batch_queue.put(batch_obj)
            progress_queue.put(None)
            break
        df_batch = batch_obj[0]
        start = batch_obj[1]
        dataset_dir = batch_obj[2]
        detect_options = batch_obj[3]
        extract_options = batch_obj[4]
        enroll_options = batch_obj[5]
        options = batch_obj[6]

        connections_per_port = server_configuration.number_of_processes_per_port * server_configuration.number_of_threads_per_process
        if local_pool is None:
            # initialize the pool
            proc_number = briar.get_process_number()
            thread_number = briar.get_thread_number()

            for i in range(connections_per_port):
                id_queue.put(i + (identifier * connections_per_port))
            local_pool = mp.Pool(connections_per_port, initializer=_initialize_worker,
                                 initargs=(port, proc_number, thread_number, id_queue,))

        time.sleep(5)
        results = inner_pool_mapper(batch_obj, local_pool, progress_queue, port)
    print('all done!')


def df_batch_generator(list_of_dfs, start, dataset_dir, detect_options, extract_options, enroll_options, options):
    """
    The df_batch_generator function is a generator that yields batches of dataframes to be processed by the
    multiprocessing pool. The function takes in a list of dataframes, and returns each one as an element in the 
    generator. This allows for parallel processing using multiple cores on your machine.

    @param list_of_dfs: Pass in the list of dataframes that are to be processed
    @param start: Keep track of the current index in the list_of_dfs
    @param dataset_dir: Specify the directory where the images are stored
    @param detect_options: Specify the type of detection algorithm to use
    @param extract_options: Specify the extraction algorithm to be used
    @param enroll_options: Specify the enrollment options for each batch
    @param options: Pass in the number of processes to use
    @return: A generator that yields a tuple of the following form:
    @doc-author: Joel Brogan
    """
    for i, df_batch in enumerate(list_of_dfs):
        yield (df_batch, start, dataset_dir, detect_options, extract_options, enroll_options, options)


def df_row_generator(rowiter, start, dataset_dir, detect_options, extract_options, enroll_options, options):
    """
    The df_row_generator function is a generator that yields the row of the dataframe,
    the index of the row, and all other arguments passed to it. This allows us to use
    multiprocessing.Pool's map function with multiple arguments.

    @param rowiter: Iterate over the rows of a dataframe
    @param start: Keep track of the row number
    @param dataset_dir: Specify the directory where the dataset is located
    @param detect_options: Set the detection options
    @param extract_options: Pass the extract_options to the worker function
    @param enroll_options: Pass the enroll_options to the function
    @param options: Pass the options to the enroll_options function
    @return: A generator that yields a list of arguments
    @doc-author: Joel Brogan
    """
    for i, row in rowiter:
        yield [row, i + start, dataset_dir, detect_options, extract_options, enroll_options, options]


def inner_pool_mapper(batch_obj, local_pool, progress_queue, port):
    """
    The inner_pool_mapper function is a function that takes in a batch of data, and then maps the enroll_call_threaded function over it.
    The inner pool mapper is used to map the enroll call threaded function over batches of data. The inner pool mapper also handles progress reporting for each batch.

    @param batch_obj: Pass the following parameters to the inner_pool_mapper function:
    @param local_pool: Specify the number of threads to use for processing
    @param progress_queue: Communicate progress back to the main process
    @return: A list of results
    @doc-author: Joel Brogan
    """
    df_batch = batch_obj[0]
    start = batch_obj[1]
    dataset_dir = batch_obj[2]
    detect_options = batch_obj[3]
    extract_options = batch_obj[4]
    enroll_options = batch_obj[5]
    options = batch_obj[6]

    try:
        procnum = int(mp.current_process().name.split('-')[-1])
    except:
        procnum = 0
    if not options.progress:
        it = range(len(df_batch))
        rowiter = list(enumerate(df_batch.iterrows()))
    else:
        it = range(len(df_batch))  # , position=0, desc="Total progress", leave=True)
        rowiter = list(enumerate(df_batch.iterrows()))  # , desc="Total progress", leave=True)

    results = []
    for result in local_pool.imap(enroll_call_threaded, df_row_generator(rowiter, start, dataset_dir, detect_options, extract_options, enroll_options, options)):  # , desc="Batch progress", position=procnum, leave=False)
        progress_queue.put(1)
        results.append(result)
    # if options.by_subject or options.entry_type == "gallery" or options.entry_type == "subject": TODO: Re-implement end-of-media message through enrollments to take place of checkpoint_subject
    # sid = np.unique(df_batch['subjectId'])[0][0]
    # client = BriarClient(options)
    # print('checkpointing subject',sid)
    # req = srvc_pb2.DatabaseCheckpointSubjectRequest(subject_id=sid)
    # local_pool :mp.Pool
    # local_pool.apply(checkpoint_subject_threaded,[[req,options]])
    # client.stub.database_checkpoint_subject(req)
    return results
    # print('we joined!')
    # my_pool.join()
    # my_pool.close()


def checkpoint_subject_threaded(obj):
    req = obj[0]
    options = obj[1]
    client = BriarClient(options, reused_channel=_worker_channel_singleton, reused_stub=_worker_stub_singleton)
    # print('threaded checkpoint', req.subject_id)
    client.stub.database_checkpoint_subject(req)


def enroll_call_threaded(input):  # row,i, dataset_dir,detect_options,extract_options,enroll_options,options):
    """
    Enroll the given input data into the Briar database.

    Parameters:
        input (tuple): A tuple containing the following elements:
            - row (dict): A dictionary containing the information about the input data.
            - i (int): Index of the input data.
            - dataset_dir (str): Directory path of the dataset.
            - detect_options (briar_pb2.FrameDetectOptions): Detection options for the enrollment process.
            - extract_options (briar_pb2.TemplateExtractOptions): Template extraction options for the enrollment process.
            - enroll_options (briar_pb2.TemplateEnrollOptions): Template enrollment options for the enrollment process.
            - options (argparse.Namespace): Command-line options for the enrollment process.

    Returns:
        None
    """
    from ..briar_client import BriarClient, _initialize_worker, _worker_channel_singleton, _worker_stub_singleton, \
        _worker_port_singleton, _worker_proccess_position_singleton, _worker_thread_position_singleton, \
        _client_identifier_singleton
    TIMING_OUTPUT_DIR = os.getenv('BRIAR_EVALUATION_OUTPUT_DIR')
    if TIMING_OUTPUT_DIR is None:
        TIMING_OUTPUT_DIR = './'
    io_failure_dir = os.path.join(TIMING_OUTPUT_DIR, 'IO_failures')
    os.makedirs(io_failure_dir, exist_ok=True)

    row = input[0]
    i = input[1]
    dataset_dir = input[2]
    detect_options = input[3]
    extract_options = input[4]
    enroll_options = input[5]
    options = input[6]

    startmediatime = time.time()
    options.port = _worker_port_singleton
    client = BriarClient(options, reused_channel=_worker_channel_singleton, reused_stub=_worker_stub_singleton)
    stats_vtime = -1
    stats_ptime = -1
    stats_frames = -1
    # i = i + start
    row = row[1]
    async_iterator = False
    if 'name' in row.keys():
        name = row['name']
    elif 'entryId' in row.keys():
        name = row['entryId']
    modalitystr = row['modality']
    modality = briar.media_converters.modality_string2proto(modalitystr)
    # modality_option = options.modality

    exstr = "row_" + str(i).zfill(5) + "_" + options.modality
    fixedpath = row['filepath']
    if not options.no_sigset:
        fixedpath = pathmap_path2remotepath(fixedpath, options.path_map)
    path = os.path.join(dataset_dir, fixedpath)
    subject_ids = row['subjectId']  # row['subjectId'] contains a list as of v1.9.0
    enroll_options.subject_ids
    del enroll_options.subject_ids[:]
    enroll_options.subject_ids.MergeFrom(subject_ids)
    enroll_options.media_id = name
    detpath = get_detection_path(path, options, i, modality=exstr, media_id=enroll_options.media_id)
    trackletpath = get_tracklet_path(path, options, i, modality=exstr, media_id=enroll_options.media_id)

    try:
        retry_count = options.enroll_retry
        while retry_count >= 0:  # we will retry this enrollment the number of retry counts specified if it fails due to client-side IO errors
            try:
                procnum = int(mp.current_process().name.split('-')[-1])
            except:
                procnum = 0
            # print('ENROLLCALL IN PROC NUM ', procnum)

            if (os.path.exists(detpath) or os.path.exists(trackletpath)) and options.skip_done:
                print('skipping ', path)
                return None
            modalitystr = options.modality
            modality = briar.media_converters.modality_string2proto(modalitystr)
            detect_options.return_media.value = detect_options.tracking_options.return_media.value = extract_options.return_media.value = False
            # modality = briar.media_converters.modality_string2proto(modalitystr)
            detect_options.tracking_options.modality = detect_options.modality = extract_options.modality = enroll_options.modality = modality
            # Check the file path

            if not os.path.exists(path) and not options.no_dataset:
                print('ERROR: {} path does not exist'.format(path))
                return None
            if (options.entry_type == "gallery" or options.entry_type == "subject") and options.allow_context:
                if "controlled" in row['filepath']:  # Only allow context to be set to controlled
                    options.context = 'controlled'
                else:
                    options.context = 'uncontrolled'
            else:
                options.context = 'uncontrolled'  # in non-gallery-enrollment scenarios we will only specify video as uncontrolled, and in scenarios there is no context or context is not allowed, default to 'uncontrolled'
            if row['media'] == 'digitalVideo':
                fstart = row['start']
                fstop = row['stop']
                if options.max_frames > 0:
                    fstop = min(int(fstop), int(fstart) + int(options.max_frames))
                has_data = True
                if not os.path.exists(path):
                    has_data = False

                if has_data:
                    media_iterator = VideoIterator(path, fstart, fstop, row['unit'], options=options, debug_empty=not has_data)
                else:
                    media_iterator = VideoIterator(path, fstart, fstop, row['unit'], debug_empty=not has_data)
            elif row['media'] == 'digitalStill':
                # print('Enrolling a Still ',modalitystr)
                # return None
                media_iterator = ImageIterator(path, row['start'], row['stop'], row['unit'],
                                               debug_empty=options.no_dataset)
            else:
                raise ValueError("Unknown media type: " + row['media'])
            if media_iterator.isOpened:
                # Enroll here
                count = 0

                database_name_base = options.database
                address_database_suffix = options.port.replace(':', '_').replace('.', '-')
                if options.database_suffix is None:
                    database_name = database_name_base
                elif options.database_suffix == 'ADDRESS' or options.database_suffix == 'A':
                    database_name = database_name_base + "_" + address_database_suffix
                elif options.database_suffix == 'SERVICE' or options.database_suffix == 'S':
                    database_name = database_name_base + '_proc' + str(_client_identifier_singleton).zfill(4)
                elif options.database_suffix == 'ADDRESS+SERVICE' or options.database_suffix == 'ADDRESS,SERVICE' or options.database_suffix == 'AS':
                    database_name = database_name_base + "_" + address_database_suffix + '_proc' + str(_client_identifier_singleton).zfill(4)

                # perform a database manifest refresh to ensure we have the latest, most up-to-date list of instantiated databases
                client.database_refresh()
                available_databases = client.get_database_names()
                if database_name not in available_databases:
                    if options.auto_create_database:
                        print('Database', database_name, 'Does not exist on service', _worker_port_singleton, '')
                        print('Creating Database', database_name)
                        try:
                            client.database_create(database_name=database_name)
                        except Exception as e:
                            print('Exception creating database', e)
                            pass
                        # Check to see if the database was successfully created
                        client.database_refresh()
                        available_databases = client.get_database_names()
                        if database_name not in available_databases:
                            print('Error: ', database_name, 'has not been created, database auto-creation failed.')
                            raise FileNotFoundError
                    else:
                        print('Error: ', database_name, 'has not been created yet. Either create it using `briar database create <database_name> or call this function using --auto-create-database')
                        raise FileNotFoundError

                run_async = async_iterator and row['media'] == 'digitalVideo'  # only use async if the input is a video
                enroll_iter = client.enroll_frames_iter(database_name, media_iterator, options,
                                                        detect_options=detect_options, extract_options=extract_options,
                                                        enroll_options=enroll_options, request_start=startmediatime,
                                                        as_async=run_async, constructor=enrollRequestConstructor)
                if run_async:  # if the interator is asyncronous, we need to run a single iteration to correctly initialize the async-to-sync functionality.  Don't worry, the iterator is coded to provide an empty throw-away request message to begin.
                    for req in enroll_iter:
                        break
                server_configuration = client.get_service_configuration()
                if options.minibatch_size > 0:
                    chunk_size = options.minibatch_size
                else:
                    chunk_size = server_configuration.number_of_processes_per_port * server_configuration.number_of_threads_per_process
                pbar = BriarProgress(options, desc='port ' + client.port + '_' + str(procnum) + ' | ' + str(_client_identifier_singleton) + ' | ' + enroll_options.media_id, position=_client_identifier_singleton, leave=False)
                frametimes = []
                perfile_durations = []
                if not options.progress:
                    print('Enrolling ', path)

                i = 0
                io_failure = False
                try:
                    for i, reply in enumerate(client.stub.enroll(enroll_iter)):
                        try:
                            if options.max_frames > 0 and i >= options.max_frames:
                                break
                            reply.durations: briar_pb2.BriarDurations
                            startframetime = reply.durations.grpc_inbound_transfer_duration.end = time.time()
                            length = reply.progress.totalSteps
                            if len(media_iterator) <= 1:
                                pbar.update(total=len(media_iterator), current=reply.progress.currentStep + 1)
                            else:
                                pbar.update(total=len(media_iterator), current=reply.progress.currentStep)

                            templates = reply.extract_reply.templates
                            detections = reply.extract_reply.detect_reply.detections
                            tracklets = reply.extract_reply.track_reply.tracklets
                            if reply.durations.service_duration.start or reply.durations.service_duration.end:
                                perfile_durations.append(reply.durations)
                            if not reply.progress_only_reply:

                                if not options.no_save:
                                    save_detections(path, reply.extract_reply.detect_reply, options, i, modality=exstr,
                                                    media_id=enroll_options.media_id)
                                    save_tracklets(path, tracklets, options, i, modality=exstr, media_id=enroll_options.media_id)
                                    save_extractions(path, templates, options, i, modality=exstr, media_id=enroll_options.media_id)
                            endframetime = time.time()
                            frametimes.append(endframetime - startframetime)
                        except Exception as e:
                            print('inner loop exception', e)
                            print(path)
                except Exception as e:
                    # Delete the request if we have experienced an error in file reading from the iterator during enrollment
                    io_failure = True
                    print('Outer loop exception. The iterator failed prematurely at ', i, 'of', len(media_iterator), 'for media', enroll_options.media_id)
                    if options.verbose:
                        print(e)
                    delete_req = srvc_pb2.DatabaseInsertRequest(ids=briar_pb2.TemplateIds(ids=['cmd_delete_errored', enroll_options.media_id]), database=briar_pb2.BriarDatabase(name=database_name))
                    client.stub.database_insert(delete_req)
                    failure_file = os.path.join(io_failure_dir, enroll_options.media_id + "_" + str(options.enroll_retry - retry_count))
                    with open(failure_file, 'w') as fp:
                        fp.write("1")

                    retry_count -= 1
                    if retry_count >= 0:
                        print('Retrying media', enroll_options.media_id)
                    continue

                # Perform final timing and briar durations saving
                if not io_failure:
                    if len(perfile_durations) > 0:
                        perfile_durations_first: briar_pb2.BriarDurations = perfile_durations[0]
                    else:
                        perfile_durations_first = briar_pb2.BriarDurations()
                    perfile_durations_first.total_duration.start = startmediatime
                    perfile_durations_first.total_duration.end = time.time()
                    perfile_durations.append(perfile_durations_first)

                    if options.save_durations:
                        timing.save_durations(path, perfile_durations, options, "sigset-enroll" + enroll_options.media_id)

            endmediatime = time.time()
            return None
            # alltimes[path] = {'mediatime': endmediatime - startmediatime, 'frametimes': frametimes}
            return [perfile_durations, {'mediatime': endmediatime - startmediatime, 'frametimes': frametimes}]
    except Exception as e:
        print('Error in the thread!', e, path)
