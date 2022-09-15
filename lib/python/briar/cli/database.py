import sys
import os
import optparse
import briar
import briar.briar_client as briar_client
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as briar_service_pb2
from briar.media_converters import modality_proto2string
from briar.cli.search import MATCHES_FILE_EXT
from briar.cli.verify import verifyParseOptions, verify_options2proto, addVerifyOptions,VERIFICATION_FILE_EXT
import re
import time
import numpy as np
import pickle as pkl
import briar.grpc_json

from briar.cli.connection import addConnectionOptions
    # // REQUIRED Load database by name onto the server running the service.
    # rpc database_load(DatabaseLoadRequest) returns (DatabaseLoadReply){};

    # // REQUIRED Clients can retrieve templates with metadata from a database for client side storage, processing, backup, or for database management.
    # rpc database_retrieve(stream DatabaseRetrieveRequest) returns (stream DatabaseRetrieveReply){};

    # // REQUIRED Clients can insert templates directly into a database for database management purposes.
    # rpc database_insert(DatabaseInsertRequest) returns (DatabaseInsertReply){};

    # // REQUIRED List the names of the galleries on this service.
    # rpc database_names(DatabaseNamesRequest) returns (DatabaseNamesReply){};

    # // REQUIRED List the enrollments and associated metadata in the database.
    # rpc database_list_templates(DatabaseListRequest) returns (DatabaseListReply){};

    # // REQUIRED Templates and associated records are deleted from a database.
    # rpc database_remove_templates(DatabaseRemoveTmplsRequest) returns (DatabaseRemoveTmplsReply) {};

    # // REQUIRED Called after all individuals have been enrolled.  Conduct any analysis
    # // of the database entries as needed or optimize for fast verification or search.
    # rpc database_finalize(DatabaseFinalizeRequest) returns (DatabaseFinalizeReply){};

    # // OPTIONAL Given two database names compute a score matrix of size databaseA X databaseB.
    # // The matrix may be used for testing, analysis, client side clustering, etc.
    # // This may needed to be implemented to support evaluations in the future.
    # rpc database_compute_score_matrix(Empty) returns (BriarMatrix){};


def parseDatabaseListOptions():
    """!
    Generate options for listing all pre-existing databases and parse command line arguments into them.

    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively
    """
    args = ["regex"]  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = '''List the databases that have been created on the service.'''
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s database names [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog,conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

    parser.add_option("-o", "--out-csv", type="str", dest="csv_path", default=None,
                      help="Output a csv listing here.")

    parser.add_option("--regex", action="store_true", dest="regex", default=None,
                      help="define if you are providing a regex argument")
    addConnectionOptions(parser)

    # Parse the arguments and return the results.
    (options, args) = parser.parse_args()

    

    if len(args) < 1:
        parser.print_help()
        print("\n"
              "Please supply exactly {} arguments.\n"
              "\n".format(n_args))
        exit(-1)

    return options, args


def database_list():
    ''' list the names of the databases '''

    # // REQUIRED List the names of the galleries on this service.
    # rpc database_names(DatabaseNamesRequest) returns (DatabaseNamesReply){};

    options, args = parseDatabaseListOptions()
    client = briar_client.BriarClient(options)
    reg = None
    if len(args) == 3:
        try:
            r = args[-1]
            reg = re.compile(r)
        except:
            reg = None
    request = briar_service_pb2.DatabaseListRequest()

    reply = client.stub.database_list(request)
    name_output=[]
    for name in reply.database_names:
        if reg is not None:
            search = reg.search(name)
            if search is not None:
                name_output.append(name)
        else:
            name_output.append(name)
    print("Service contains '{}' databases.".format(len(name_output)))

    for each in name_output:
        print(each)

    if options.csv_path is not None:
        f = open(options.csv_path,'w')
        for each in reply.database_names:
            f.write(each+'\n')




def parseDatabaseListEntriesOptions():
    """!
    Generate options for Listing entries within a pre-existing database and parse command line arguments into an API call.

    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively
    """
    args = ['main_call ','database_name']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = "List the entries in a database.  This will contain entry names " + \
                  "and any additional metadata associated with the media or the " + \
                  " subject."
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s database list [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog,conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

    parser.add_option("-o", "--out-csv", type="str", dest="csv_path", default=None,
                      help="Output a csv listing here.")

    addConnectionOptions(parser)

    # Parse the arguments and return the results.
    (options, args) = parser.parse_args()

    

    if len(args) != n_args+1:
        parser.print_help()
        print("\n"
              "Please supply exactly {} arguments.\n"
              "\n".format(n_args))
        exit(-1)

    return options, args[1:]


def database_list_entries():
    ''' list the entries in a database '''

    # // REQUIRED List the enrollments and associated metadata in the database.
    # rpc database_list_templates(DatabaseListRequest) returns (DatabaseListReply){};


    options, args = parseDatabaseListEntriesOptions()

    client = briar_client.BriarClient(options)

    request = briar_service_pb2.DatabaseListEntriesRequest(database_name = args[1])

    reply = client.stub.database_list_entries(request)
    if reply.exists:
        print("Database '{}' contains {} entries.".format(args[1],len(reply.entry_ids)))
        for id,attributes in zip(reply.entry_ids,reply.entry_attributes):
            print('Entry:' , id)
            for att in attributes.attributes:
                if att.description in dir(att):
                    val = getattr(att,att.description)
                else:
                    val = att
                print(att.key,":", val)
        #TODO: make a csv save out function
        # if options.csv_path is not None:
        #     f = open(options.csv_path,'w')
        #     for each in reply.template_ids.ids:
        #         f.write(each+'\n')
    else:
        db_no_exist(args[1])


def parseDatabaseInfoOptions():
    """!
    Generate options for getting information about a pre-existing database and parse command line arguments into an API call.

    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively
    """
    args = ['main_call ', 'database_name']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = "List Information about a database.  This will contain information about failure to enroll, " + \
                  "and any additional metadata associated with the database "
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s database list [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog, conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

    parser.add_option("-o", "--out-csv", type="str", dest="csv_path", default=None,
                      help="Output a csv listing here.")

    addConnectionOptions(parser)

    # Parse the arguments and return the results.
    (options, args) = parser.parse_args()

    if len(args) != n_args + 1:
        parser.print_help()
        print("\n"
              "Please supply exactly {} arguments.\n"
              "\n".format(n_args))
        exit(-1)

    return options, args[1:]

def database_info():
    ''' list the information pertaining to a database '''

    # // REQUIRED List the enrollments and associated metadata in the database.
    # rpc database_list_templates(DatabaseListRequest) returns (DatabaseListReply){};

    options, args = parseDatabaseInfoOptions()

    client = briar_client.BriarClient(options)

    request = briar_service_pb2.DatabaseInfoRequest(database_name=args[1])

    reply = client.stub.database_info(request)
    if reply.exists:
        print("Database '{}' Information:".format(args[1],))
        db_info = reply.info

        entries = db_info.entry_count
        templates = db_info.template_count
        failed = db_info.failed_enrollment_count
        dbsize = db_info.total_database_size
        avgsize = db_info.average_entry_size
        entry_sizes = list(db_info.entry_sizes)
        modalities = [modality_proto2string(m) for m in db_info.modalities]


        print('Utilized Modalities:', modalities)
        print('Total entries:', entries)
        print('Total templates:', templates)
        print('Total failed enrollments:', failed)
        print('Database Size (KB):', dbsize)
        print('Average entry size (KB):',avgsize)
        print('Entry Sizes (KB):', entry_sizes)
        #TODO: Make a save out function
        # if options.csv_path is not None:
        #     f = open(options.csv_path,'w')
        #     for each in reply.template_ids.ids:
        #         f.write(each+'\n')
    else:
        db_no_exist(args[1])

def db_no_exist(name):
    print('No database exists named \"', name, '\"')

def parseDatabaseRetrieveOptions():
    """!
    Generate options for retrieving a pre-existing database and parse command line arguments API call.

    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively
    """
    args = ['database_name']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = '''Retrieve the entries from a database and store on disk.'''
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s database retrieve [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog,conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

    parser.add_option("-o", "--out-csv", type="str", dest="csv_path", default=None,
                      help="Output a csv listing here.")

    parser.add_option("-D", "--database", type="str", dest="database", default=None,
                      help="Output a csv listing here.")

    addConnectionOptions(parser)

    # Parse the arguments and return the results.
    (options, args) = parser.parse_args()

    
    if options.database is None and len(args) < 3:
        print('len',len(args))
        print("ERROR: --database option needs to be defined")
        exit(-1)

    if len(args) != n_args+2:
        parser.print_help()
        print("\n"
              "Please supply exactly {} arguments.\n"
              "\n".format(n_args))
        exit(-1)

    return options, args


def database_retrieve():
    ''' list the entries in a database '''

    # // REQUIRED Clients can retrieve templates with metadata from a database for client side storage, processing, backup, or for database management.
    # rpc database_retrieve(stream DatabaseRetrieveRequest) returns (stream DatabaseRetrieveReply){};


    options, args = parseDatabaseRetrieveOptions()

    client = briar_client.BriarClient(options)

    request = briar_service_pb2.DatabaseRetrieveRequest(database=briar_pb2.BriarDatabase(name=options.database))
    #request.database.name = options.database

    print(options.database, len(options.database))
    print(request)
    reply = client.stub.database_list_templates(request) 

    print(reply)

    print("Database '{}' contains {} entries.".format(args[1],len(reply.template_ids.ids)))
    for each in reply.template_ids.ids:
        print('   ',each)

    if options.csv_path is not None:
        f = open(options.csv_path,'w')
        for each in reply.template_ids.ids:
            f.write(each+'\n')

def database_checkpoint():
    ''' Checkpoints a database without finalizing it '''
    # rpc database_checkpoint(DatabaseCheckpointRequest) returns(DatabaseCheckpointReply) {};

    options, args = parseDatabaseRetrieveOptions()

    client = briar_client.BriarClient(options)

    if options.database:
        database = options.database
    else:
        options.database = args[2]
        database = args[2]

    request = briar_service_pb2.DatabaseCheckpointRequest(database=briar_pb2.BriarDatabase(name=options.database))
    #request.database.name = options.database

    # print(request)
    reply = client.stub.database_checkpoint(request)

    # print(reply)

    print("Database '{}' has been checkpointed".format(database,))

def database_create():
    ''' Checkpoints a database without finalizing it '''
    # rpc database_checkpoint(DatabaseCheckpointRequest) returns(DatabaseCheckpointReply) {};

    options, args = parseDatabaseRetrieveOptions()

    client = briar_client.BriarClient(options)
    if options.database:
        database = options.database
    else:
        options.database = args[2]
        database = args[2]
    request = briar_service_pb2.DatabaseCreateRequest(database=briar_pb2.BriarDatabase(name=options.database))
    #request.database.name = options.database

    reply = client.stub.database_create(request)

    # print(reply)

    print("Database '{}' has been created".format(options.database,))

def parseDatabaseRenameOptions():
    """!
    Generate options for Renaming a pre-existing database to a new name and parse command line arguments into API call.

    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively
    """
    args = ['database_name','new_database_name']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = '''Rename a database.'''
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s database delete [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog, conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

    parser.add_option("-o", "--out-csv", type="str", dest="csv_path", default=None,
                      help="Output a csv listing here.")
    addConnectionOptions(parser)

    # Parse the arguments and return the results.
    (options, args) = parser.parse_args()

    # if options.database is None:
    #    print("ERROR: --database option needs to be defined")
    #    exit(-1)

    if len(args) != n_args + 2:
        parser.print_help()
        print("\n"
              "Please supply exactly {} arguments.\n"
              "\n".format(n_args))
        exit(-1)

    return options, args

def database_load():
    ''' Loads a database from storage'''
    # rpc database_checkpoint(DatabaseCheckpointRequest) returns(DatabaseCheckpointReply) {};

    options, args = parseDatabaseRetrieveOptions()

    client = briar_client.BriarClient(options)
    if options.database:
        database = options.database
    else:
        options.database = args[2]
        database = args[2]
    request = briar_service_pb2.DatabaseLoadRequest(database=briar_pb2.BriarDatabase(name=options.database))
    #request.database.name = options.database

    reply = client.stub.database_load(request)

    # print(reply)

    print("Database '{}' has been Loaded".format(options.database,))


def database_rename():
    ''' rename a database '''

    # // REQUIRED Clients can rename a database for database management.
    # rpc database_rename(stream DatabaseRenameRequest) returns (stream DatabaseRenameReply){};

    options, args = parseDatabaseRenameOptions()

    client = briar_client.BriarClient(options)
    request = briar_service_pb2.DatabaseRenameRequest(database=briar_pb2.BriarDatabase(name=args[-2]),database_new=briar_pb2.BriarDatabase(name=args[-1]))

    if options.verbose:
        print('Sending database rename request:')
        output = str(request)
        print(output[:250])

    reply = client.stub.database_rename(request)

    if options.verbose:
        print('Recieved Reply:')
        output = str(reply)
        print(output[:250])

    print("Renamed database {} to {}.".format(args[-1], args[-2]))

    # if options.csv_path is not None:
    #    f = open(options.csv_path,'w')
    #    for each in reply.template_ids.ids:
    #        f.write(each+'\n')


def parseDatabaseDeleteOptions():
    """!
    Generate options for Deleting a pre-existing database and parse command line arguments into API call.

    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively
    """
    args = ['database_name']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = '''Delete a database.'''
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s database delete [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog,conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

    parser.add_option("-o", "--out-csv", type="str", dest="csv_path", default=None,
                      help="Output a csv listing here.")

    #parser.add_option("-D", "--database", type="str", dest="database", default=None,
    #                  help="Output a csv listing here.")

    addConnectionOptions(parser)

    # Parse the arguments and return the results.
    (options, args) = parser.parse_args()

    
    #if options.database is None:
    #    print("ERROR: --database option needs to be defined")
    #    exit(-1)

    if len(args) != n_args + 2:
        parser.print_help()
        print("\n"
              "Please supply exactly {} arguments.\n"
              "\n".format(n_args))
        exit(-1)

    return options, args


def database_delete():
    ''' delete a database '''

    # // REQUIRED Clients can retrieve templates with metadata from a database for client side storage, processing, backup, or for database management.
    # rpc database_retrieve(stream DatabaseRetrieveRequest) returns (stream DatabaseRetrieveReply){};


    options, args = parseDatabaseDeleteOptions()

    client = briar_client.BriarClient(options)
    request = briar_service_pb2.DatabaseDeleteRequest(database=briar_pb2.BriarDatabase(name=args[-1]))

    if options.verbose:
        print('Sending database delete request:')
        output = str(request)
        print(output[:250])

    reply = client.stub.database_delete(request) 

    if options.verbose:
        print('Recieved Reply:')
        output = str(reply)
        print(output[:250])

    if reply.exists:
        print("Deleted database {} with {} entries.".format(request.database,reply.entry_count))
    else:
        db_no_exist(request.database.name)


def parseDatabaseMergeOptions():
    """!
    Generate options for merging databases and parse command line arguments into the API call.

    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively
    """
    args = ['database_name']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = '''Merge a list of databases.'''
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''
    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s database merge [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog, conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

    parser.add_option("--output-database", type="str", dest="output_database", default="Default",
                      help="Name of the output merged database")

    parser.add_option("--regex", action="store_true", dest="regex", default=None,
                      help="define if you are providing a regex argument")
    # parser.add_option("-D", "--database", type="str", dest="database", default=None,
    #                  help="Output a csv listing here.")

    addConnectionOptions(parser)

    # Parse the arguments and return the results.
    (options, args) = parser.parse_args()

    # if options.database is None:
    #    print("ERROR: --database option needs to be defined")
    #    exit(-1)
    if len(args) < n_args + 2:
        parser.print_help()
        print("\n"
              "Please supply at least {} arguments.\n"
              "\n".format(n_args))
        exit(-1)
    elif len(args) > n_args+2 and options.regex:
        print("\n"
              "Please supply at only 1 argument when using the --regex flag.\n"
              "\n".format(n_args))
        exit(-1)

    return options, args


def database_merge():
    ''' Merge a set of databases '''

    # // REQUIRED Clients can retrieve templates with metadata from a database for client side storage, processing, backup, or for database management.
    # rpc database_retrieve(stream DatabaseRetrieveRequest) returns (stream DatabaseRetrieveReply){};

    options, args = parseDatabaseMergeOptions()

    client = briar_client.BriarClient(options)
    request = briar_service_pb2.DatabaseMergeRequest(output_database=briar_pb2.BriarDatabase(name=options.output_database))

    if len(args) == 3 and not options.regex:
        database_name_list = args[2].split(',')
    elif len(args) > 3 and not options.regex:
        database_name_list = args[2:]
    elif options.regex:
        listrequest = briar_service_pb2.DatabaseListRequest()
        reply = client.stub.database_list(listrequest)
        database_name_list = []
        r = args[-1]
        reg = None
        try:
            reg = re.compile(r)
        except:
            reg = None
        for name in reply.database_names:
            if reg is not None:
                search = reg.search(name)
                if search is not None:
                    database_name_list.append(name)
            else:
                database_name_list.append(name)

    if options.verbose:
        print('Merging databases: ')
        print(' '.join(database_name_list))
    briardatabases = []
    for db_name in database_name_list:
        db = request.database_list.add()
        db.name = db_name



    if options.verbose:
        print('Sending database merge reques')
        # output = str(request)
        # print(output[:250])

    reply = client.stub.database_merge(request)

    if options.verbose:
        print('Recieved Reply:')
        output = str(reply)
        print(output[:250])

    print("Merged {} database with {} entries into one database named {}".format(len(database_name_list), reply.entry_count,options.output_database))

def addDatabaseComputeScoreOptions(parser):
    """!
    Add options for search of a database using a database.

    @param parser optparse.OptionParser: A parser to modify in place by adding options
    """

    search_group = optparse.OptionGroup(parser, "Search Databases Options",
                                        "Configuration for database-against-database search.")

    search_group.add_option("-o", "--out-dir", type="str", dest="out_dir", default=None,
                            help="Save the search results.")
    output_type_choices = ['pickle','briar','numpy','pandas','xml']
    search_group.add_option("--output-type", type="choice", choices=output_type_choices, dest="output_type",
                      default="briar",
                      help="Choose an output type for saving results. Options: " + ",".join(output_type_choices) + " Default=briar")

    search_group.add_option("--search-database", type="str", dest="search_database", default=None,
                            help="Select the database to search.")
    search_group.add_option("--probe-database", type="str", dest="probe_database", default=None,
                                                    help="Database to use as a probe set")
    search_group.add_option("--max-results", type="int", dest="max_results", default=10,
                            help="Set the maximum number of search results returned for each face. If negative, search will return search scores for ALL gallery entries")

    search_group.add_option("--return-media", action="store_true", dest="return_media", default=False,
                               help="Enables returning of media from workers to the client - will significantly increase output file sizes!")
    search_group.add_option("-m","--modality", type="choice", choices=['unspecified', 'whole_body', 'face', 'gait'], dest="modality",
                                default="face",
                                                            help="Choose a biometric modality. Default=face")
    search_group.add_option("-m", "--modality", type="choice",
                            choices=['unspecified', 'whole_body', 'face', 'gait', 'all'], dest="modality",
                            default="face",
                            help="Choose a biometric modality to detect/extract/enroll. Default=all")

    parser.add_option_group(search_group)

def addDatabaseComputeScore_options2proto(options):
    '''
    Parse command line options and populate a proto object for grpc
    '''

    search_options = briar_pb2.SearchOptions()
    val = options.out_dir
    if val is not None:
        search_options.out_dir.value = options.out_dir
    val = options.output_type
    if val is not None:
        search_options.output_type.value = options.output_type
    val = options.search_database
    if val is not None:
        search_options.search_database.value = options.search_database
    val = options.probe_database
    if val is not None:
        search_options.probe_database.value = options.probe_database
    val = options.modality
    if val is not None:
        val = briar.media_converters.modality_string2proto(val)
        search_options.modality = val
    # val = options.probe_database
    # if val is not None:
    #     search_options.search_database.value = options.search_database
    val = options.max_results
    if val is not None:
        search_options.max_results.value = val
    val = options.return_media
    if val is not None:
        search_options.return_media.value = val
    search_options.full.value = False
    return search_options

def parseDatabaseComputeScoreOptions(inputCommand = None):
    """!
    Generate options for matching databases against other databases, and parse command line arguments into the API call.

    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively
    """
    args = ['gallery_database_name','probe_database_name']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = "Run a 1:N search against a database. Input a probe entry" + \
                  " and finds the top matches in a gallery database."
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s search [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog, conflict_handler="resolve")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")
    parser.add_option("--no-save", action="store_true", dest="no_save", default=False,
                      help="Disables saving of results on the client-side")

    parser.add_option("--probe-order-list", type="str", dest="order_list", default=None,
                            help="Sigset XML file to use as the ordering of result output")

    addDatabaseComputeScoreOptions(parser)
    addConnectionOptions(parser)
    # if options.database is None:
    #    print("ERROR: --database option needs to be defined")
    #    exit(-1)

    # Parse the arguments and return the results.
    if inputCommand is not None:
        import shlex
        inp = shlex.split(inputCommand)
        (options, args) = parser.parse_args(inp)
    else:
        (options, args) = parser.parse_args()

    if len(args) < n_args + 2:
        if options.probe_database is None and options.search_database is None :
            parser.print_help()
            print("\n"
                  "Please supply at least {} arguments.\n"
                  "\n".format(n_args))
            exit(-1)

    return options, args




def database_compute_search(options=None,args=None):
    """!
    Using the options specified in the command line, runs a search within the specified database using specified
    probe database. Writes results to disk to a location specified by the cmd arguments

    @return: No return - Function writes results to disk
    """
    api_start = time.time()

    if options is None and args is None:
        options, args = parseDatabaseComputeScoreOptions()
    client = briar_client.BriarClient(options)


    # Check the status
    # print("*" * 35, 'STATUS', "*" * 35)
    # print(client.get_status())
    # print("*" * 78)

    search_options = addDatabaseComputeScore_options2proto(options)


    if options.verbose:
        print("Scanning directories for images and videos.")
    image_list = None
    video_list = None
    search_database_flag = False
    if options.search_database:
        database = options.search_database
        search_database_flag = True
    else:
        options.search_database = args[2]
        database = args[2]

    image_count = 0

    if options.probe_database is not None:
        probe_database = options.probe_database
    elif len(args) >2:
        options.probe_database = args[3]
        probe_database = args[3]
    if options.probe_database is not None:
        filename = None
        if not options.out_dir:
            out_dir = './'
        else:
            out_dir = options.out_dir
            out_dir_fname = os.path.basename(out_dir)
            if not out_dir_fname == '':
                if '.' in out_dir_fname:
                    filename = out_dir_fname
                    out_dir = os.path.dirname(out_dir)
                    if out_dir == '':
                        out_dir = './'
        os.makedirs(out_dir, exist_ok=True)
        searchRequest = briar_service_pb2.SearchDatabaseRequest(database = briar_pb2.BriarDatabase(name=database),search_options=search_options,probe_database=briar_pb2.BriarDatabase(name=probe_database))
        searchReply = client.stub.database_compute_search(searchRequest)
        if filename is None:
            filename = database+"_"+probe_database

        # print(searchReply)
        if options.output_type == 'pickle' or options.output_type == 'pkl':
            matches_name = os.path.splitext(os.path.basename(filename))[0] + '_search.pkl'
            matches_path = os.path.join(out_dir, matches_name)
            outputlist = []
            if options.order_list is not None:
                outputlist = {}
            for matchlist in searchReply.similarities:
                output_subids = []
                output_scores = []
                subject_id_probe = None
                for matchInfo in matchlist.match_list:
                    subject_id_probe = matchInfo.subject_id_probe
                    entry_id_gallery = matchInfo.entry_id_gallery
                    output_subids.append(matchInfo.subject_id_gallery)
                    output_scores.append(matchInfo.score)
                output_scores = np.array(output_scores)
                if isinstance(outputlist,list):
                    outputlist.append([subject_id_probe,output_subids,output_scores])
                elif isinstance(outputlist,dict):
                    outputlist[subject_id_probe] = [subject_id_probe,output_subids,output_scores]

            if options.order_list:
                new_outputlist = []
                print("parsing Sigset XML", os.path.basename(options.order_list), ' for result ordering...')
                from briar.sigset import parse
                import pandas
                csvname = options.order_list + '.csv'
                if os.path.exists(csvname):
                    probe_sigset = pandas.read_csv(csvname)
                else:
                    probe_sigset = parseBriarSigset(options.order_list)
                probe_order = list(probe_sigset['name'])
                bad_probes = []
                for entry_id in probe_order:
                    if entry_id in outputlist:
                        new_outputlist.append(outputlist[entry_id])
                    else:
                        new_outputlist.append([entry_id,[],[]])
                        bad_probes.append(entry_id)
                if len(bad_probes) > 0:
                    print('WARNING: The probe databse used for database search did not contain', len(bad_probes),' probes')
                    print('To see them, enable verbose mode with -v')
                    if options.verbose:
                        print('bad probes:')
                        print(bad_probes)
                outputlist = new_outputlist
            print('writing pkl file to', matches_path)
            with open(matches_path, 'wb') as fp:
                pkl.dump(outputlist, fp)

        if options.output_type == "briar":
            matches_name = os.path.splitext(os.path.basename(filename))[0] + MATCHES_FILE_EXT
            matches_path = os.path.join(out_dir, matches_name)
            briar.grpc_json.save(searchReply,matches_path)

def database_compute_verify(options=None,args=None):
    """!
    Using the options specified in the command line, runs a batch verification betweeen the specified databases using specified
    probe database. Writes results to disk to a location specified by the cmd arguments

    @return: No return - Function writes results to disk
    """
    api_start = time.time()
    if options is None and args is None:
        options, args = verifyParseOptions()
    client = briar_client.BriarClient(options)


    # Check the status
    # print("*" * 35, 'STATUS', "*" * 35)
    # print(client.get_status())
    # print("*" * 78)

    verify_options = verify_options2proto(options)


    if options.verbose:
        print("Scanning directories for images and videos.")
    image_list = None
    video_list = None
    search_database_flag = False
    if options.reference_database:
        database = options.reference_database
        search_database_flag = True
    else:
        options.reference_database = args[2]
        database = args[3]

    image_count = 0

    if options.verify_database is not None:
        verify_database = options.verify_database
    elif len(args) > 2:
        options.verify_database = args[3]
        verify_database = args[3]

    if options.verify_database is not None:
        filename = None

        if not options.out_dir:
            out_dir = './'
        else:
            out_dir = options.out_dir
            out_dir_fname = os.path.basename(out_dir)
            if not out_dir_fname == '':
                if '.' in out_dir_fname:
                    filename = out_dir_fname
                    out_dir = os.path.dirname(out_dir)
                    if out_dir == '':
                        out_dir = './'
            os.makedirs(out_dir,exist_ok=True)
        verifyRequest = briar_service_pb2.VerifyDatabaseRequest(reference_database = briar_pb2.BriarDatabase(name=database),verify_options=verify_options,verify_database=briar_pb2.BriarDatabase(name=verify_database))
        verifyReply = client.stub.database_compute_verify(verifyRequest)
        if filename is None:
            filename = database + "_" + verify_database
        if options.plot:
            from briar.media import visualize
            match_visualizer = visualize.match_matrix_visualizer(verifyReply,options.verify_database,options.reference_database)
            match_visualizer.showmat_interactive()

        if options.output_type == 'pickle' or options.output_type == 'pkl':
            matches_name = os.path.splitext(os.path.basename(filename))[0] + '_verification.pkl'
            matches_path = os.path.join(out_dir, matches_name)
            outputlist = []
            matrix = briar.media_converters.matrix_proto2np(verifyReply.match_matrix)

            if options.verify_order_list:
                print("parsing Sigset XML", os.path.basename(options.verify_order_list), ' for probe result ordering...')
                from briar.sigset import parse
                import pandas
                csvname = options.verify_order_list + '.csv'
                if os.path.exists(csvname):
                    probe_sigset = pandas.read_csv(csvname)
                else:
                    probe_sigset = parseBriarSigset(options.verify_order_list)
                probe_order = list(probe_sigset['name'])
                newmatrix_sortedprobes = []
                matrix_probe_order = list(verifyReply.match_matrix.row_headers)
                missing_probes = []
                print('probe order:',probe_order)
                print('matrix_probe_order:',matrix_probe_order)
                for probeid in probe_order:
                    if probeid in matrix_probe_order:
                        newmatrix_sortedprobes.append(matrix[matrix_probe_order.index(probeid)])
                    else:
                        missing_probes.append(probeid)
                matrix = np.vstack(newmatrix_sortedprobes)

                if len(missing_probes) > 0:
                    print('WARNING: Verification database',verify_database, ' did not contain ', len(missing_probes), 'entries indicated by the sigset.' )
                    print('To see them, run with the -v flag')
                    if options.verbose:
                        print('Missing Probe Entries:')
                        print(missing_probes)

            if options.reference_order_list:
                print("parsing Sigset XML", os.path.basename(options.reference_order_list), ' for reference result ordering...')
                from briar.sigset import parse
                import pandas
                csvname = options.reference_order_list + '.csv'
                if os.path.exists(csvname):
                    gallery_sigset = pandas.read_csv(csvname)
                else:
                    gallery_sigset = parseBriarSigset(options.reference_order_list)
                gallery_order = list(gallery_sigset['name'])
                newmatrix_sortedgallery = []
                matrix_gallery_order = list(verifyReply.match_matrix.column_headers)
                missing_gallery = []
                for gallid in gallery_order:
                    if gallid in matrix_gallery_order:
                        newmatrix_sortedgallery.append(matrix.T[matrix_gallery_order.index(gallid)])
                    else:
                        missing_gallery.append(gallid)
                matrix = np.vstack(newmatrix_sortedprobes).T

                if len(missing_gallery) > 0:
                    print('WARNING: Reference database', database, ' did not contain ', len(missing_probes),
                          'entries indicated by the sigset.')
                    print('To see them, run with the -v flag')
                    if options.verbose:
                        print('Missing Reference Entries:')
                        print(missing_gallery)


            print('writing pkl file to', matches_path)
            with open(matches_path, 'wb') as fp:
                pkl.dump(matrix, fp)

        if options.output_type == "briar":
            matches_name = os.path.splitext(os.path.basename(filename))[0] + MATCHES_FILE_EXT
            matches_path = os.path.join(out_dir, matches_name)
            briar.grpc_json.save(verifyReply,matches_path)

