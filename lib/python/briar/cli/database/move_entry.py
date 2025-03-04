import briar
import briar.briar_client as briar_client
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as briar_service_pb2
import briar.grpc_json
import optparse
import re
from briar.cli.connection import addConnectionOptions

def parseDatabaseMoveEntryOptions(inputCommand=None):
    """!
    Generate options for moving database entries and parse command line arguments into the API call.

    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively
    """
    args = ['database_from_name', 'database_to_name', 'entry_id']  # Add the names of arguments here.
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

    parser.add_option("--copy", action="store_true", dest="regex", default=False,
                      help="Specify if you are copying the entry or just moving it.  Default is False")
    # parser.add_option("-D", "--database", type="str", dest="database", default=None,
    #                  help="Output a csv listing here.")

    addConnectionOptions(parser)

    # Parse the arguments and return the results.
    if inputCommand is not None:
        import shlex
        inp = shlex.split(inputCommand)
        (options, args) = parser.parse_args(inp)
    else:
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


    return options, args


def database_move_entry(options=None, args=None,input_command=None,ret=False,client = None):
    ''' Merge a set of databases '''

    # // REQUIRED Clients can retrieve templates with metadata from a database for client side storage, processing, backup, or for database management.
    # rpc database_retrieve(stream DatabaseRetrieveRequest) returns (stream DatabaseRetrieveReply){};

    options, args = parseDatabaseMoveEntryOptions(input_command)

    if not client:
        client = briar_client.BriarClient(options)


    database_from_name = args[1]
    database_to_name = args[2]
    entry_id = args[3]

    request = briar_service_pb2.DatabaseMoveEntryRequest(from_database=briar_pb2.BriarDatabase(
                                                             name=database_from_name),
                                                         to_database=briar_pb2.BriarDatabase(
                                                             name=database_to_name),entry_id=entry_id)

    available_database_list = database_list(ret=True, input_command="database list")

    # has_entry_reply = client.stub.database_has_entry(briar_service_pb2.DatabaseHasEntryRequest)

    request = briar_service_pb2.DatabaseMergeRequest(
        output_database=briar_pb2.BriarDatabase(name=options.output_database))
    if options.verbose:
        print('Moving databases: ')
        print(' '.join(database_name_list))
    briardatabases = []
    for db_name in database_name_list:
        db = request.database_list.add()
        db.name = db_name

    if options.verbose:
        print('Sending database move entry request')
        # output = str(request)
        # print(output[:250])

    reply = client.stub.database_merge(request)

    if options.verbose:
        print('Recieved Reply:')
        output = str(reply)
        print(output[:250])

    print("Merged {} databases with {} entries into one database named {}".format(len(database_name_list),
                                                                                 reply.entry_count,
                                                                                 options.output_database))

