"""!
Created on 2021 at Oak Ridge National Laboratory

The Briar Command Line Interface (Briar CLI) provides a universal method to interface with different gRPC
created with the compiled protobuf stubs. It provides a series of common functions to run detection and
identification on faces, whole bodies, and walking gaits, as well as various database enrollment and search
functions. Briar does not implement these detect, extract, enroll, etc functions itself, but rather acts as a
means for connecting with servers (outlined with service.py)

@author: Joel Brogan
"""

# import briar.tests.integration_test

import briar.cli.test
import sys
from briar import dyn_import
from briar.cli.database.list_entries import database_list_entries
from briar.cli.database.list import database_list
from briar.cli.database.info import database_info
from briar.cli.database.merge import database_merge
from briar.cli.database.compute_scores import database_compute_verify
from briar.cli.database.compute_search import database_compute_search
from briar.cli.database.rename import database_rename
from briar.cli.database.load import database_load
from briar.cli.database.delete import database_delete
from briar.cli.database.checkpoint import database_checkpoint
from briar.cli.database.checkpoint_subject import database_checkpoint_subject
from briar.cli.database.create import database_create
from briar.cli.database.refresh import database_refresh
from briar.cli.detect import detect
from briar.cli.enhance import enhance
from briar.cli.enroll import enroll
from briar.cli.extract import extract
from briar.cli.database.finalize import database_finalize
from briar.cli.search import search
from briar.cli.sigset import sigset_stats, sigset_enroll
# External commands
from briar.cli.status import status,print_service_configuration
from briar.cli.track import track
from briar.cli.verify import verify
from briar.cli.viz import viz

FACE_COUNT = 0
DETECTION_FILE_EXT = ".detection"
TEMPLATE_FILE_EXT = '.template'
MATCHES_FILE_EXT = '.matches'


def incomplete():
    """
The incomplete function is a placeholder for functions that have not yet been implemented.
It raises a NotImplementedError exception to indicate that the function has not yet been implemented.

:return: A notimplementederror
:doc-author: Joel Brogan
"""
    print("This function is not yet implemented.")
    raise NotImplementedError()


def briar_database_command_line():
    """!
        Entry point for the Database CLI - switches on the second command line argument (such as 'delete', 'merge', etc) and
        builds the parser and help messages based upon the callback defined in COMMANDS. Each 'command' should be
        treated as a 'switch' which defines additional command line arguments.

        @return:
        """
    if len(sys.argv) < 3 or sys.argv[2] not in DATABASE_COMMANDS:
        # Display a basic help message if no command is specified
        print()
        print(
            "ERROR: You must a select a database command.  For more help run python -m briar database <command> --help.\n\nCommands:")
        print("    Commands marked ! are not yet implemented.")
        print("")
        for each in DATABASE_COMMANDS:
            print("    %s - %s" % (each, DATABASE_COMMANDS[each][0]))
        print()
        exit(-1)

    # Jump to the entry point for the command.
    DATABASE_COMMANDS[sys.argv[2]][1]()


def briar_test_command_line():
    """!
        Entry point for the Test CLI - switches on the second command line argument (such as 'delete', 'merge', etc) and
        builds the parser and help messages based upon the callback defined in COMMANDS. Each 'command' should be
        treated as a 'switch' which defines additional command line arguments.

        @return:
        """

    all_test_elements_tmp = dir(briar.cli.test)
    TEST_COMMANDS = {'integration':['All integration tests',briar.tests.integration_test.runall()]}
    for elem in all_test_elements_tmp:
        if elem.endswith('Test'):
            testname = elem.replace('Test', '').lower()
            if testname in COMMANDS:
                testobj = dyn_import('briar.cli.test.' + elem)()
                test_desc = testobj.description()
                TEST_COMMANDS[testname] = [test_desc, testobj.test]

    if len(sys.argv) < 3 or sys.argv[2] not in TEST_COMMANDS:
        # Display a basic help message if no command is specified
        print()
        print(
            "ERROR: You must select an integration test command.  For more help run python -m briar test <command> --help.\n\nCommands:")
        print("    Commands marked ! are not yet implemented.")
        print("")
        for each in TEST_COMMANDS:
            print("    %s - %s" % (each, TEST_COMMANDS[each][0]))
        print()
        exit(-1)

    # Jump to the entry point for the command.
    TEST_COMMANDS[sys.argv[2]][1]()


COMMANDS = {
    'detect': ['Run detection on media files.', detect],
    'track': ['Run tracking on media files (videos only).', track],
    'enhance': ['Run tracking on media files (videos only).', enhance],
    'extract': ['Run feature extraction to generate templates or embeddings.', extract],
    'enroll': ['Scan media files and enroll templates into a database.', enroll],
    'verify': ['Verify a given peice of media against a reference media.', verify],
    'finalize': ['Finalize a database.', database_finalize],
    'search': ['Search a database for an example identity.', search],
    'sigset-stats': ['Convert a sigset to a csv file and compute statistics.', sigset_stats],
    'sigset-enroll': ['Process a sigset and enroll in a database.', sigset_enroll],
    'status': ['Connects to the server and displays version and status information.', status],
    'service-configuration': ['Returns configuration settings from the service', print_service_configuration],
    'database': ['Base call for database-related functions', briar_database_command_line],
    'vis': ['Visualize saved results output from API Calls', viz],
    'test': ['Base call for API test functions', briar_test_command_line]
}

DATABASE_COMMANDS = {
    'create': ['Create and initialize a new database.', database_create],
    'delete': ['Delete a database from the service.', database_delete],
    'rename': ['Rename a database from the service.', database_rename],
    '!insert': ['Insert templates directly into a database.', incomplete],
    'load': ['Load database onto the server.', database_load],
    'list': ['List the names of the databases on this service.', database_list],
    'ls': ['List the names of the databases on this service.', database_list],
    'info': ['List information about a given database.', database_info],
    'list-entries': ['List the entries contained within a database stored on this service.', database_list_entries],
    'finalize': ['Finalize a database.', database_finalize],
    'checkpoint': ['Checkpoint a database to save progress, without finalizing', database_checkpoint],
    'checkpoint-subject': ['Checkpoint a database subject to save progress, without finalizing', database_checkpoint_subject],
    'compute-search': ['Searches a probe database against a gallery database', database_compute_search],
    'compute-verify': ['Performs batch verification ', database_compute_verify],
    'refresh':  ['Performs a refresh of the list of databases to keep them coherent between services',database_refresh],
    '!remove-entries': ['Remove entries from the database', incomplete],
    'merge': ['Merge a list of existing databases together', database_merge],
}


def briar_command_line():
    """!
    Entry point for the CLI - switches on the first command line argument (such as 'status', 'detect', etc) and
    builds the parser and help messages based upon the callback defined in COMMANDS. Each 'command' should be
    treated as a 'switch' which defines additional command line arguments.

    @return:
    """
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        # Display a basic help message if no command is specified
        print()
        print("ERROR: You must a select a command.  For more help run python -m briar <command> --help.\n\nCommands:")
        print("    Commands marked ! are not yet implemented.")
        print("")
        for each in COMMANDS:
            print("    %s - %s" % (each, COMMANDS[each][0]))
        print()
        exit(-1)
    # Jump to the entry point for the command.
    gen = COMMANDS[sys.argv[1]][1]()
    import types
    if isinstance(gen,types.GeneratorType):
        output = [o for o in gen] #this runs the function if it is a generator

if __name__ == '__main__':
    briar_command_line()
