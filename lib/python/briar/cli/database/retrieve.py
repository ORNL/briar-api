import briar
import briar.briar_client as briar_client
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as briar_service_pb2
import briar.grpc_json

import optparse

from briar.cli.connection import addConnectionOptions

def parseDatabaseRetrieveOptions(inputCommand=None):
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
                                   version=version, description=description, epilog=epilog, conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

    parser.add_option("-o", "--out-csv", type="str", dest="csv_path", default=None,
                      help="Output a csv listing here.")

    parser.add_option("-D", "--database-name", type="str", dest="database", default=None,
                      help="Output a csv listing here.")

    addConnectionOptions(parser)

    # Parse the arguments and return the results.
    if inputCommand is not None:
        import shlex
        inp = shlex.split(inputCommand)
        (options, args) = parser.parse_args(inp)
    else:
        (options, args) = parser.parse_args()

    if options.database is None and len(args) < 3:
        print('len', len(args))
        print("ERROR: --database option needs to be defined")
        exit(-1)

    if len(args) != n_args + 2:
        parser.print_help()
        print("\n"
              "Please supply exactly {} arguments.\n"
              "\n".format(n_args))
        exit(-1)

    return options, args


def database_retrieve(options=None, args=None,input_command=None,ret = False):
    ''' list the entries in a database '''

    # // REQUIRED Clients can retrieve templates with metadata from a database for client side storage, processing, backup, or for database management.
    # rpc database_retrieve(stream DatabaseRetrieveRequest) returns (stream DatabaseRetrieveReply){};

    options, args = parseDatabaseRetrieveOptions(inputCommand=input_command)

    client = briar_client.BriarClient(options)

    request = briar_service_pb2.DatabaseRetrieveRequest(database=briar_pb2.BriarDatabase(name=options.database))
    # request.database.name = options.database

    print(options.database, len(options.database))
    print(request)
    reply = client.stub.database_list_templates(request)

    print(reply)

    print("Database '{}' contains {} entries.".format(args[1], len(reply.template_ids.ids)))
    for each in reply.template_ids.ids:
        print('   ', each)

    if options.csv_path is not None:
        f = open(options.csv_path, 'w')
        for each in reply.template_ids.ids:
            f.write(each + '\n')


