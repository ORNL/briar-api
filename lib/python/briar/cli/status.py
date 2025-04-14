import asyncio
import briar
import briar.briar_client as briar_client
import optparse
import os
import sys
from briar.cli.connection import addConnectionOptions


def statusParseOptions(inputCommand=None):
    """!
    Generate options for getting status and parse command line arguments into them.

    This function sets up an optparse.OptionParser instance with various options for checking the server status,
    including verbosity and output options. It then parses the command line arguments into these options.

    @param inputCommand str: A string containing the command line input to parse. If None, the function will parse sys.argv.
    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively.
    """
    # Parse command line arguments.
    args = ['']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = "Check the server status and display algorithm and version information. " + \
                  "This is a good first check to ensure that a connection is established " + \
                  "and that the service is ready to accept commands."
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s status [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog, conflict_handler="resolve")

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")

    parser.add_option("-o", "--output", type="str", dest="output_file", default=None,
                      help="Save status information to a file.")

    parser.add_option("-l", "--label", action="store_true", dest="output_label", default=False,
                      help="Print out an algorithm label to stdout and exit.")

    addConnectionOptions(parser)

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


def status(options=None, args=None,input_command=None,ret=False):
    """!
    Conects to the server and gets status information. Print results.

    @return: None - results are printed
    """
    options, args = statusParseOptions(input_command)
    client = briar_client.BriarClient(options)
    developer_name, dev_short, service_name, version, api_version, status = client.get_status(options)
    client_side_version = briar.__version__
    status = ['UNKNOWN', 'READY', 'ERROR', 'BUSY'][status]

    if not options.output_label and not ret:
        print("\n"
              "===================== STATUS =====================\n"
              "  Developer:   {}\n"
              "  Developer Short:   {}\n"
              "  Name:        {}\n"
              "  Alg Version: {}.{}.{}\n"
              "  Server-Side API Version: {}.{}.{}\n"
              "  Client-Side API Version: {}\n"
              "  Status:      {}\n"
              "==================================================\n"
              "\n".format(developer_name, dev_short, service_name, version.major, version.minor, version.patch,
                          api_version.major, api_version.minor, api_version.patch, client_side_version,
                          status))
    else:
        if not ret:
            print("{}.v{}.{}.{}".format(service_name, version.major, version.minor, version.patch))

    if options.output_file is not None:
        import json
        # from google.protobuf.json_format import MessageToJson

        message = {'developer': developer_name,
                   'dev_short': dev_short,
                   'service_name': service_name,
                   'version_major': version.major,
                   'version_minor': version.minor,
                   'version_patch': version.patch,
                   'api_version_major': api_version.major,
                   'api_version_minor': api_version.minor,
                   'api_version_patch': api_version.patch,
                   'status': status,
                   }

        with open(options.output_file, 'w') as jsfile:
            json.dump(message, jsfile, check_circular=True, indent=4)
    if ret:
        return client.get_status(options)


def get_service_configuration(options=None, args=None,input_command=None,ret=False):
    options, args = statusParseOptions(input_command)
    client = briar_client.BriarClient(options)
    reply = client.get_service_configuration()
    if ret:
        return client,reply
    return reply

def print_service_configuration(options=None, args=None):
    reply = get_service_configuration(options,args)
    print('Service configuration:')
    print(reply)