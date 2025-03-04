import briar
import briar.briar_client as briar_client
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as briar_service_pb2
import briar.grpc_json
import optparse
import re
from briar.cli.connection import addConnectionOptions

def parseDatabaseMergeOptions(inputCommand=None):
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
    elif len(args) > n_args + 2 and options.regex:
        print("\n"
              "Please supply at only 1 argument when using the --regex flag.\n"
              "\n".format(n_args))
        exit(-1)

    return options, args


def database_merge(options=None, args=None,input_command=None,ret=False):
    ''' Merge a set of databases '''

    # // REQUIRED Clients can retrieve templates with metadata from a database for client side storage, processing, backup, or for database management.
    # rpc database_retrieve(stream DatabaseRetrieveRequest) returns (stream DatabaseRetrieveReply){};

    options, args = parseDatabaseMergeOptions(input_command)

    client = briar_client.BriarClient(options)
    request = briar_service_pb2.DatabaseMergeRequest(
        output_database=briar_pb2.BriarDatabase(name=options.output_database))

    if len(args) == 3 and not options.regex:
        database_name_list = args[2].split(',')
    elif len(args) > 3 and not options.regex:
        database_name_list = args[2:]
    elif options.regex:
        listrequest = briar_service_pb2.DatabaseListRequest()
        reply = client.stub.database_list(listrequest)
        database_name_list = []
        r = args[-1]
        if r.endswith('*'):
            r = r[:-1]
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
        print('Sending database merge request')
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

