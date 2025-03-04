import briar
import briar.briar_client as briar_client
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as briar_service_pb2
import briar.grpc_json
import optparse
from briar.cli.connection import addConnectionOptions



def parseDatabaseCheckpointSubjectOptions(inputCommand = None):
    """!
    Generate options for getting information about a pre-existing database and parse command line arguments into an API call.

    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively
    """
    args = ['main_call ', 'database_name','subject_id']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = "Checkpoint the media for a specific subject that has been enrolled into a database. This can be called when it is believed there is no more media pertaining to that subject."
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s database list [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog, conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

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






def database_checkpoint_subject(options=None, args=None,input_command=None,ret = False):
    options, args = parseDatabaseCheckpointSubjectOptions(inputCommand=input_command)
    client = briar_client.BriarClient(options)
    if  hasattr(options,'database') and options.database:
        database = options.database
    else:
        options.database = args[2]
        database = args[2]
    subject_id = args[1]
    request = briar_service_pb2.DatabaseCheckpointSubjectRequest(database=briar_pb2.BriarDatabase(name=database),subject_id=subject_id,)
    print('Checkpointing subject', subject_id, 'in database', database)
    reply = client.stub.database_checkpoint_subject(request)
    print('Subject ',subject_id,' succesfully checkpointed!')


