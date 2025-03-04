import briar
import briar.briar_client as briar_client
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as briar_service_pb2
import briar.grpc_json
from briar.cli.database.retrieve import parseDatabaseRetrieveOptions
import optparse

from briar.cli.connection import addConnectionOptions

def parseDatabaseRefreshOptions(inputCommand = None):
    """!
    Generate options for getting information about a pre-existing database and parse command line arguments into an API call.

    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively
    """
    args = ['main_call ' ]  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = "Refresh the database directory for the service "
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s database list [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog, conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")
    parser.add_option("-a", "--all", action="store_true", dest="verbose", default=False,
                      help="refreshes all databases")
    # parser.add_option("-s","-subject-id", type="str", dest="subject_id", default=None,
    #                   help="subject ID to checkpoint or finalize (can be provided as argument instead")

    addConnectionOptions(parser)

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

    return options, args[1:]
def database_refresh(options=None, args=None,input_command=None,ret = False):
    ''' Refresh the list of databases '''

    options, args = parseDatabaseRefreshOptions(inputCommand=input_command)

    client = briar_client.BriarClient(options)
    print('Refreshing databases...')
    client.stub.database_refresh(briar_service_pb2.Empty())
    print('Refreshed!')
    return None


def database_checkpoint(options=None, args=None,input_command=None,ret = False):
    ''' Checkpoints a database without finalizing it '''
    # rpc database_checkpoint(DatabaseCheckpointRequest) returns(DatabaseCheckpointReply) {};

    options, args = parseDatabaseRetrieveOptions(inputCommand=input_command)

    client = briar_client.BriarClient(options)

    if options.database:
        database = options.database
    else:
        options.database = args[2]
        database = args[2]
    print('Checkpointing database', database)
    request = briar_service_pb2.DatabaseCheckpointRequest(database=briar_pb2.BriarDatabase(name=options.database))
    # request.database.name = options.database

    # print(request)
    reply = client.stub.database_checkpoint(request)

    # print(reply)

    print("Database '{}' has been checkpointed".format(database, ))
