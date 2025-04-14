import asyncio
import briar
import briar.briar_client as briar_client
import optparse
import os
import pyvision as pv
import sys
from briar.cli.connection import addConnectionOptions


def finalizeParseOptions(inputCommand=None):
    """!
    Generate options for running 'finalize' (saving the loaded databases) and parse command line arguments into them.

    This function sets up an optparse.OptionParser instance with various options for finalizing a database,
    including the database name and connection options. It then parses the command line arguments into these options.

    @param inputCommand str: A string containing the command line input to parse. If None, the function will parse sys.argv.
    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively.
    """
    args = ['[database_name]']
    n_args = len(args)
    description = "Finalize the given database and save to disk. This could " + \
                  "take a long time and may build complex data structures. " + \
                  "After a database is finalized it will not be modified."
    epilog = "Created by Joel Brogan - broganjr@ornl.gov"
    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage="{} finalize [OPTIONS] {}".format('python -m briar', args),
                                   version=version, description=description, epilog=epilog, conflict_handler="resolve")
    parser.add_option("-D", "--database", type="str", dest="database", default=None,
                      help="Select the database to finalize.")
    addConnectionOptions(parser)

    # Parse the arguments and return the results
    if inputCommand is not None:
        import shlex
        inp = shlex.split(inputCommand)
        (options, args) = parser.parse_args(inp)
    else:
        (options, args) = parser.parse_args()

    if options.database is None:
        parser.print_help()
        print("\nError: The --database argument is required.\n")
        exit(-1)

    if len(args) < 1:
        parser.print_help()
        print("\nError: Please supply at least one database name.\n")
        exit(-1)

    return options, args


def database_finalize(options=None, args=None, input_command=None, ret=False):
    """!
    Parses the command line options and saves the database to disk.

    This function initializes a BriarClient, sets up the finalize options, and processes the specified database.
    It runs the finalize process on the database and optionally returns the results.

    @param options optparse.Values: Parsed command line options.
    @param args list: List of command line arguments.
    @param input_command str: A string containing the command line input to parse. If None, the function will parse sys.argv.
    @param ret bool: If True, the function will return the finalize results. Otherwise, it writes results to disk.
    @return: If ret is True, returns the finalize reply.
    """
    if options is None and args is None:
        options, args = finalizeParseOptions(input_command)
    client = briar_client.BriarClient(options)

    reply = client.finalize(args[-1])
    if ret:
        return reply
    print('Database finalize complete.')
