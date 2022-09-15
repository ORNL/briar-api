import sys
import os
import optparse

import pyvision as pv

import briar
import briar.briar_client as briar_client
from briar.cli.connection import addConnectionOptions



def finalizeParseOptions(inputCommand=None):
    """!
    Generate options for running 'finalize' (saving the loaded databases) and parse command line arguments into
    them.

    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively
    """
    args = ['[database_name]']
    n_args = len(args)
    description =   "Finalize the given database and save to disk.  This could " + \
                    "take a long time and may build complex data structures.  " + \
                    "After a database is finalized it will not be modified"
    epilog = "Created by Joel Brogan - broganjr@ornl.gov"
    version = briar.__version__

    parser = optparse.OptionParser(usage="{} finalize [OPTIONS] {}".format('python -m briar', args),
                                   version=version, description=description, epilog=epilog,conflict_handler="resolve")
    parser.add_option("-D", "--database", type="str", dest="database", default=None,
                      help="Select the database to enroll into.")
    addConnectionOptions(parser)

    # Parse the arguments and return the results
    if inputCommand is not None:
        import shlex
        inp = shlex.split(inputCommand)
        (options, args) = parser.parse_args(inp)
    else:
        (options, args) = parser.parse_args()

    # if options.database == None:
    #     print('ERROR: the --database argument is required.')
    #     exit(-1)

    if len(args) < 2:
        parser.print_help()
        print()
        print(("Error: Please supply at least one database name."))
        print()
        exit(-1)

    return options, args



def database_finalize(options=None,args=None):
    """!
    Parses the command line options and saves the database to disk
    @return: None - results are written to disk to a location specified by options
    """
    if options is None and args is None:
       options, args = finalizeParseOptions()
    client = briar_client.BriarClient(options)

    client.finalize(args[-1])
    print('Database finalize complete.')

