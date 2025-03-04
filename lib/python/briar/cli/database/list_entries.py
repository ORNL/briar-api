import briar
import briar.briar_client as briar_client
import briar.briar_grpc.briar_service_pb2 as briar_service_pb2
import briar.grpc_json
import optparse
from briar.cli.connection import addConnectionOptions
from briar.cli.database.common import db_no_exist


def parseDatabaseListEntriesOptions(inputCommand = None):
    """!
    Generate options for Listing entries within a pre-existing database and parse command line arguments into an API call.

    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively
    """
    args = ['main_call ', 'database_name']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = "List the entries in a database.  This will contain entry names " + \
                  "and any additional metadata associated with the media or the " + \
                  " subject."
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


def database_list_entries(options=None, args=None,input_command=None,ret = False):
    ''' list the entries in a database '''

    # // REQUIRED List the enrollments and associated metadata in the database.
    # rpc database_list_templates(DatabaseListRequest) returns (DatabaseListReply){};

    options, args = parseDatabaseListEntriesOptions(inputCommand=input_command)

    client = briar_client.BriarClient(options)

    request = briar_service_pb2.DatabaseListEntriesRequest(database_name=args[1])

    reply = client.stub.database_list_entries(request)
    if reply.exists:
        print("Database '{}' contains {} entries.".format(args[1], len(reply.entry_ids)))
        for id, attributes in zip(reply.entry_ids, reply.entry_attributes):
            print('Entry:', id)
            for att in attributes.attributes:
                if att.description in dir(att):
                    val = getattr(att, att.description)
                else:
                    val = att
                print(att.key, ":", val)
        # TODO: make a csv save out function
        # if options.csv_path is not None:
        #     f = open(options.csv_path,'w')
        #     for each in reply.template_ids.ids:
        #         f.write(each+'\n')
    else:
        db_no_exist(args[1])