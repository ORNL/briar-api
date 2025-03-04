import briar
import briar.briar_client as briar_client
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as briar_service_pb2
import briar.grpc_json
import optparse
from briar.cli.connection import addConnectionOptions
from briar.cli.database.retrieve import parseDatabaseRetrieveOptions

def parseDatabaseRenameOptions(inputCommand=None):
    """!
    Generate options for Renaming a pre-existing database to a new name and parse command line arguments into API call.

    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively
    """
    args = ['current_database_name', 'new_database_name']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = '''Rename a database.'''
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s database rename [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog, conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

    parser.add_option("-o", "--out-csv", type="str", dest="csv_path", default=None,
                      help="Output a csv listing here.")
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
    # request.database.name = options.database

    reply = client.stub.database_load(request)

    # print(reply)

    print("Database '{}' has been Loaded".format(options.database, ))


def database_rename(options=None, args=None,input_command=None,ret = False):
    ''' rename a database '''

    # // REQUIRED Clients can rename a database for database management.
    # rpc database_rename(stream DatabaseRenameRequest) returns (stream DatabaseRenameReply){};

    options, args = parseDatabaseRenameOptions(input_command)

    client = briar_client.BriarClient(options)
    request = briar_service_pb2.DatabaseRenameRequest(database=briar_pb2.BriarDatabase(name=args[-2]),
                                                      database_new=briar_pb2.BriarDatabase(name=args[-1]))
    list_request = briar_service_pb2.DatabaseListRequest()
    list_reply = client.stub.database_list(list_request)
    if request.database_new.name in list_reply.database_names:
        raise FileExistsError("ERROR: Database '{}' already exists".format(request.database_new.name))

    if options.verbose:
        print('Sending database rename request:')
        output = str(request)
        print(output[:250])

    reply = client.stub.database_rename(request)

    if options.verbose:
        print('Recieved Reply:')
        output = str(reply)
        print(output[:250])
    if reply.exists:
        print("Renamed database {} to {}.".format(args[-2], args[-1]))
    else:
        print("No such database named '{}'.".format(args[-1]))

    # if options.csv_path is not None:
    #    f = open(options.csv_path,'w')
    #    for each in reply.template_ids.ids:
    #        f.write(each+'\n')
