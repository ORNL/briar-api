import briar
import briar.briar_client as briar_client
import briar.briar_grpc.briar_service_pb2 as briar_service_pb2
import briar.grpc_json
import optparse
import re
from briar.cli.connection import addConnectionOptions


def parseDatabaseListOptions(inputCommand = None):
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
                                   version=version, description=description, epilog=epilog, conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

    parser.add_option("-o", "--out-csv", type="str", dest="csv_path", default=None,
                      help="Output a csv listing here.")

    parser.add_option("--regex", action="store_true", dest="regex", default=None,
                      help="define if you are providing a regex argument")
    addConnectionOptions(parser)

    # Parse the arguments and return the results.
    if inputCommand is not None:
        import shlex
        inp = shlex.split(inputCommand)
        (options, args) = parser.parse_args(inp)
    else:
        (options, args) = parser.parse_args()

    if len(args) < 1:
        parser.print_help()
        print("\n"
              "Please supply exactly {} arguments.\n"
              "\n".format(n_args))
        exit(-1)

    return options, args

def database_list(options=None, args=None,input_command=None,ret = False):
    ''' list the names of the databases '''

    # // REQUIRED List the names of the galleries on this service.
    # rpc database_names(DatabaseNamesRequest) returns (DatabaseNamesReply){};

    options, args = parseDatabaseListOptions(input_command)
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
    name_output = []
    for name in reply.database_names:
        if reg is not None:
            search = reg.search(name)
            if search is not None:
                name_output.append(name)
        else:
            name_output.append(name)
    print("Service contains '{}' databases.".format(len(name_output)))

    db_names = []
    for each in name_output:
        db_names.append(each)
        if not ret:
            print(each)

    if options.csv_path is not None:
        f = open(options.csv_path, 'w')
        for each in reply.database_names:

            f.write(each + '\n')
    if ret:
        return db_names