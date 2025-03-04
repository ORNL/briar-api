import briar
import briar.briar_client as briar_client
import briar.briar_grpc.briar_service_pb2 as briar_service_pb2
import briar.grpc_json
import json
import optparse
from briar.cli.connection import addConnectionOptions
from briar.media_converters import modality_proto2string, subjectID_int2str, subjectList_string2list,subjectList_list2string
from briar.cli.database.common import db_no_exist
def parseDatabaseInfoOptions(inputCommand = None):
    """!
    Generate options for getting information about a pre-existing database and parse command line arguments into an API call.

    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively
    """
    args = ['main_call ', 'database_name']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = "List Information about a database.  This will contain information about failure to enroll,acquire, " + \
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


def database_info(options=None, args=None,input_command=None,ret = False):
    ''' list the information pertaining to a database '''

    # // REQUIRED List the enrollments and associated metadata in the database.
    # rpc database_list_templates(DatabaseListRequest) returns (DatabaseListReply){};

    options, args = parseDatabaseInfoOptions(inputCommand=input_command)

    client = briar_client.BriarClient(options)

    request = briar_service_pb2.DatabaseInfoRequest(database_name=args[1])

    reply = client.stub.database_info(request)
    if reply.exists:
        print("Database '{}' Information:".format(args[1], ))
        db_info = reply.info

        entries = db_info.entry_count
        templates = db_info.template_count
        failed = db_info.failed_enrollment_count
        dbsize = db_info.total_database_size
        avgsize = db_info.average_entry_size
        entry_list = list(db_info.entry_ids)
        entry_sizes = list(db_info.entry_sizes)
        modalities = [modality_proto2string(m) for m in db_info.modalities]

        if options.csv_path:
            outjson = {
                "total_entries": entries,
                "total_templates": templates,
                "failed": failed,
                "database_size": dbsize,
                "average_entry_size": avgsize,
                "entry_list": entry_list,
                "entry_size_list": entry_sizes,
                "entry_modalities": modalities
            }
            with open(options.csv_path, 'w') as fp:
                json.dump(outjson, fp)

        print('Utilized Modalities:', modalities)
        print('Total entries:', entries)
        print('Total templates:', templates)
        print('Total failed enrollments:', failed)
        print('Database Size (KB):', dbsize)
        print('Average entry size (KB):', avgsize)
        if options.verbose:
            print('\n'.join(entry_list))
        # print('Entry Sizes (KB):', entry_sizes)
        # TODO: Make a save out function
        # if options.csv_path is not None:
        #     f = open(options.csv_path,'w')
        #     for each in reply.template_ids.ids:
        #         f.write(each+'\n')
    else:
        db_no_exist(args[1])
    if ret:
        return reply
