import sys
import os
import optparse

import briar
import briar.briar_client as briar_client
from briar.cli.connection import addConnectionOptions

def statusParseOptions(inputCommand=None):
    """!
    Generate options for getting status and parse command line arguments into them.

    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively
    """
    # Parse command line arguments.
    args = ['']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description =   "Check the server status and display algorithm and version information. " + \
                    "This is a good first check to ensure that a connection is established " + \
                    "and that the service is ready to accept commands."
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s status [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog,conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

    parser.add_option("-o", "--output", type="str", dest="output_file", default=None,
                      help="Save status information to a file.")

    parser.add_option("-l", "--label", action="store_true", dest="output_label", default=False,
                      help="Print out an algorithm label to stdout and exit.")

    

    addConnectionOptions(parser)
    # Here are some templates for standard option formats.
    # parser.add_option("-q", "--quiet", action="store_false", dest="verbose", default=True,
    #                 help="Decrease the verbosity of the program")

    # parser.add_option("-b", "--bool", action="store_true", dest="my_bool", default=False,
    #                  help="don't print status messages to stdout")

    # parser.add_option( "-c","--choice", type="choice", choices=['c1','c2','c3'], dest="my_choice", default="c1",
    #                  help="Choose an option.")

    # parser.add_option( "-f","--float", type="float", dest="my_float", default=0.0,
    #                  help="A floating point value.")

    # parser.add_option( "-i","--int", type="int", dest="my_int", default=0,
    #                  help="An integer value.")

    # parser.add_option( "-s","--str", type="str", dest="my_str", default="default",
    #                  help="A string value.")

    # parser.add_option( "--enroll", type="str", dest="enroll_database", default=None,
    #                  help="Enroll detected faces into a database.")

    # parser.add_option( "--search", type="str", dest="search_database", default=None,
    #                  help="Search images for faces from a database.")

    # parser.add_option( "--name", type="str", dest="subject_name", default=None,
    #                  help="Enroll detected faces into a database.")

    # parser.add_option( "--subject-id", type="str", dest="subject_id", default=None,
    #                  help="Enroll detected faces into a database.")

    # parser.add_option( "--search-log", type="str", dest="search_log", default=None,
    #                  help="Enroll detected faces into a database.")

    # parser.add_option( "-m","--match-log", type="str", dest="match_log", default=None,
    #                  help="A directory to store matching faces.")

    # parser.add_option( "--same-person", type="str", dest="same_person", default=None,
    #                  help="Specifies a python function that returns true if the filenames indicate a match.  Example: lambda x,y: x[:5] == y[:5]")

    # parser.add_option( "-s","--scores-csv", type="str", dest="scores_csv", default=None,
    #                  help="Save similarity scores to this file.")

    # Parse the arguments and return the results.
    if inputCommand is not None:
        import shlex
        inp = shlex.split(inputCommand)
        (options, args) = parser.parse_args(inp)
    else:
        (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.print_help()
        print("\n"
              "Please supply exactly {} arguments.\n"
              "\n".format(0))
        exit(-1)

    return options, args


def status(options=None, args=None):
    """!
    Conects to the server and gets status information. Print results.

    @return: None - results are printed
    """
    options,args = statusParseOptions()
    client = briar_client.BriarClient(options)
    developer_name, service_name, version, api_version, status = client.get_status(options)
    client_side_version = briar.__version__
    status = ['UNKNOWN', 'READY', 'ERROR', 'BUSY'][status]

    if not options.output_label:
        print("\n"
            "===================== STATUS =====================\n"
            "  Developer:   {}\n"
            "  Name:        {}\n"
            "  Alg Version: {}.{}.{}\n"
            "  Server-Side API Version: {}.{}.{}\n"
            "  Client-Side API Version: {}\n"
            "  Status:      {}\n"
            "==================================================\n"
            "\n".format(developer_name, service_name, version.major, version.minor, version.patch, api_version.major, api_version.minor, api_version.patch,client_side_version,
                        status))
    else:
        print("{}.v{}.{}.{}".format(service_name,version.major, version.minor, version.patch))

    if options.output_file is not None:
        import json
        #from google.protobuf.json_format import MessageToJson

        message = { 'developer':developer_name, 
                    'service_name':service_name, 
                    'version_major':version.major, 
                    'version_minor':version.minor, 
                    'version_patch':version.patch, 
                    'api_version_major':api_version.major, 
                    'api_version_minor':api_version.minor, 
                    'api_version_patch':api_version.patch,
                    'status':status,
                    }

        with open(options.output_file, 'w') as jsfile:
            json.dump(message, jsfile,check_circular=True,indent=4)            
            #json.dump(MessageToJson(item), jsfile)







