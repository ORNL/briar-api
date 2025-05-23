import unittest
import sys
import os

import numpy as np
import warnings
import briar
from briar.tests import finalize_db, checkpoint_db
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as srvc_pb2
import briar.evaluation.full_evaluation
warnings.filterwarnings("ignore", category=ResourceWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
from briar.media_converters import modality_proto2string
from briar.tests import test_warn

unittest.TestLoader.sortTestMethodsUsing = None
USES_FRONTEND_MERGING = os.getenv('BRIAR_USE_FRONTEND_MERGING')
DATABASE_SUFFIX_FLAG = os.getenv('BRIAR_DATABASE_SUFFIX_FLAG')
USE_SINGLE_SUBJECT = os.getenv('BRIAR_USE_SINGLE_SUBJECT')
if USE_SINGLE_SUBJECT is None:
    USE_SINGLE_SUBJECT = ' '
else:
    if USE_SINGLE_SUBJECT.lower() == 'false' or USE_SINGLE_SUBJECT.lower() == '0':
        USE_SINGLE_SUBJECT = ' '
    else:
        USE_SINGLE_SUBJECT = ' --single-subject '

RUN_STAGES = os.getenv('RUN_STAGES', None)

if RUN_STAGES is None:
    RUN_STAGES = ','.join([str(n) for n in list(range(1, 4))])
if RUN_STAGES is not None:
    stages_temp = []
    for s in RUN_STAGES.split(','):
        stages_temp.append(float(s))
    RUN_STAGES = stages_temp

if 1 in RUN_STAGES:  # add all of stage 1 substages (these are for probe enrollment)
    RUN_STAGES.extend([1.1, 1.2, 1.3, 1.4])
if 2 in RUN_STAGES:  # add all of stage 2 substages (these are for gallery enrollment)
    RUN_STAGES.extend([2.1, 2.2, 2.3, 2.4])

if 3 in RUN_STAGES:  # Add all of stage 3 substages (these are for scoring)
    RUN_STAGES.extend([3.01, 3.02, 3.03, 3.04, 3.05, 3.06, 3.07, 3.08, 3.09, 3.10, 3.11, 3.12, 3.13, 3.14, 3.15, 3.16])

print('RUNNING STAGES:', RUN_STAGES)

if USES_FRONTEND_MERGING is None:
    USES_FRONTEND_MERGING = False
elif USES_FRONTEND_MERGING.lower() == 'true':
    USES_FRONTEND_MERGING = True
else:
    USES_FRONTEND_MERGING = False

if USES_FRONTEND_MERGING:
    if DATABASE_SUFFIX_FLAG is None:
        print('environment variable BRIAR_DATABASE_SUFFIX_FLAG is not set. Defaulting to ADDRESS,SERVICE')
        DATABASE_SUFFIX_FLAG = 'ADDRESS,SERVICE'
    else:
        print('environment variable BRIAR_DATABASE_SUFFIX_FLAG is set to', DATABASE_SUFFIX_FLAG)
else:
    DATABASE_SUFFIX_FLAG = 'NONE'

args_string = " --progress "
media_args = " --no-save "
enroll_args = " --auto-create-database "

# Make sure to set these environment variables in the briar_env.sh file if you are running these on your own
EVALUATION_DIR = os.getenv('BRIAR_EVALUATION_DIR')
EVALUATION_MULTISUBJECT_DIR = os.getenv('BRIAR_MULTISUBJECT_EVALUATION_DIR')
DATASET_DIR = os.getenv('BRIAR_DATASET_DIR')
OUTPUT_DIR = os.getenv('BRIAR_EVALUATION_OUTPUT_DIR')
EVAL_PHASE = os.getenv('BRIAR_EVAL_PHASE')

probe_filename = "sigsets_main/Probe_BTS_briar-rd_ALL.xml"
multisubject_probe_filename = "sigsets_multiperson/Probe_BTS_briar-rd_multi.xml"
gallery_1_filename = "sigsets_gallery/Gallery_1.xml"
gallery_2_filename = "sigsets_gallery/Gallery_2.xml"

blended_gallery_1_filename = "sigsets_gallery/Blended_Gallery_1.xml"
blended_gallery_2_filename = "sigsets_gallery/Blended_Gallery_2.xml"

database_blended_gallery_1_name = 'db_eval_phase2_blended_gallery_1'
database_blended_gallery_2_name = 'db_eval_phase2_blended_gallery_2'

database_gallery_1_name = 'db_eval_phase2_gallery_1'
database_gallery_2_name = 'db_eval_phase2_gallery_2'

database_probe_name = 'db_eval_phase2_probe'
database_multi_probe_name = 'db_eval_phase2_multisubject_probe'
port_list = []

face_modality_string = 'face'
wb_modality_string = 'wholebody'
gait_modality_string = 'gait'

requires_database_merge = False
number_of_partitions = 1


def setUpModule():
    """!
    Set up the evaluation module.

    This function sets up the evaluation module by ignoring specific warnings and printing a setup message.
    """
    warnings.filterwarnings("ignore", category=ResourceWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    print('setting up evaluation module')
    pass


def setUpClass_main(cls) -> None:
    """!
    Set up the main class for evaluation.

    This function sets up the main class for evaluation by parsing sigsets and setting up paths for various files.
    It also determines whether to run a multisubject evaluation based on the existence of specific files.

    @param cls: The class to set up.
    """
    warnings.filterwarnings("ignore", category=ResourceWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    from briar.sigset import parse
    try:
        cls.gallery_1_sigset_path = os.path.join(EVALUATION_DIR, gallery_1_filename)
        cls.gallery_2_sigset_path = os.path.join(EVALUATION_DIR, gallery_2_filename)
        cls.gallery_1_blended_sigset_path = os.path.join(EVALUATION_DIR, blended_gallery_1_filename)
        cls.gallery_2_blended_sigset_path = os.path.join(EVALUATION_DIR, blended_gallery_2_filename)

        cls.probe_sigset_path = os.path.join(EVALUATION_DIR, probe_filename)
        cls.probe_multisubject_sigset_path = os.path.join(EVALUATION_MULTISUBJECT_DIR, multisubject_probe_filename)
        if not os.path.exists(cls.probe_multisubject_sigset_path):
            cls.run_multisubject_evaluation = False
            if 1.3 in RUN_STAGES:
                RUN_STAGES.remove(1.3)
            if 1.4 in RUN_STAGES:
                RUN_STAGES.remove(1.4)
        else:
            cls.run_multisubject_evaluation = True
            cls.probe_multisubject_sigset = parse.parseBriarSigset(cls.probe_multisubject_sigset_path)

        cls.probe_sigset = parse.parseBriarSigset(cls.probe_sigset_path)
        cls.gallery1_sigset = parse.parseBriarSigset(cls.gallery_1_sigset_path)
        cls.gallery2_sigset = parse.parseBriarSigset(cls.gallery_2_sigset_path)
        cls.gallery1_blended_sigset = parse.parseBriarSigset(cls.gallery_1_blended_sigset_path)
        cls.gallery2_blended_sigset = parse.parseBriarSigset(cls.gallery_2_blended_sigset_path)

    except Exception as e:
        print("Could not run tests:", e)


class Test000InitialConfig(unittest.TestCase):
    """!
    Test initial configuration for the evaluation.

    This class contains tests to check the initial configuration for the evaluation, including environment variables
    and service configuration.
    """

    @classmethod
    def setUpClass(cls) -> None:
        from briar.cli.status import get_service_configuration
        setUpClass_main(cls)
        cls.config_reply = get_service_configuration(input_command='status' + args_string)

    def testValidationDir(self):
        """!
        Test if the validation directory is set.
        """
        if EVALUATION_DIR is None:
            print('You must set the environment variable VALIDATION_DIR')
        self.assertIsNotNone(EVALUATION_DIR)

    def testDatasetDir(self):
        """!
        Test if the dataset directory is set.
        """
        if DATASET_DIR is None:
            print('You must set the environment variable DATASET_DIR')
        self.assertIsNotNone(DATASET_DIR)

    def testOutDir(self):
        """!
        Test if the output directory is set.
        """
        if OUTPUT_DIR is None:
            print('You must set the environment variable OUTDIR')
        self.assertIsNotNone(OUTPUT_DIR)

    def test_01_config_portlist(self):
        """!
        Test the configuration port list.
        """
        self.config_reply: srvc_pb2.BriarServiceConfigurationReply
        self.assertGreater(len(self.config_reply.port_list), 0)
        global port_list
        port_list = self.config_reply.port_list

        for port in self.config_reply.port_list:
            self.assertIn(':', port)
            self.assertGreaterEqual(len(port.split(':')), 2)
        self.assertEqual(self.config_reply.base_port, self.config_reply.port_list[0])

    def test_02_port_connections(self):
        """!
        Test port connections.
        """
        from briar.cli.status import status

        for port in self.config_reply.port_list:
            success = False
            try:
                print('checking port ', port)
                status_reply = status(input_command='status' + args_string, ret=True)
                success = True
            except Exception as e:
                print('Could not connect to ', port, ':', e)
            self.assertTrue(success)

    def test_03_num_service_ports(self):
        """!
        Test the number of service ports.
        """
        self.assertGreaterEqual(self.config_reply.number_of_service_ports, 1)
        self.assertEqual(self.config_reply.number_of_service_ports, len(self.config_reply.port_list))
        if self.config_reply.number_of_service_ports > 1 and USES_FRONTEND_MERGING:
            global requires_database_merge
            requires_database_merge = True

    def test_04_num_procs_per_port(self):
        """!
        Test the number of processes per port.
        """
        self.assertGreaterEqual(self.config_reply.number_of_processes_per_port, 1)
        self.assertTrue((briar.PLATFORM == 'darwin' and self.config_reply.number_of_processes_per_port == 1) or briar.PLATFORM != 'darwin',
                        'MacOS platform not supported for running multiple processes on a single port, as SO_REUSE_PORT does not load balance')
        if self.config_reply.number_of_processes_per_port > 1 and USES_FRONTEND_MERGING:
            global requires_database_merge
            requires_database_merge = True

    def test_05_num_threads_per_port(self):
        """!
        Test the number of threads per port.
        """
        self.assertGreaterEqual(self.config_reply.number_of_threads_per_process, 1)
        if self.config_reply.number_of_threads_per_process > 1 and USES_FRONTEND_MERGING:
            global requires_database_merge
            requires_database_merge = True
        global DATABASE_SUFFIX_FLAG
        if self.config_reply.number_of_processes_per_port == 1 and self.config_reply.number_of_processes_per_port == 1 and self.config_reply.number_of_service_ports == 1:
            DATABASE_SUFFIX_FLAG = 'NONE'
        elif self.config_reply.number_of_processes_per_port == 1 and self.config_reply.number_of_processes_per_port == 1 and (DATABASE_SUFFIX_FLAG.upper() == 'S' or DATABASE_SUFFIX_FLAG.upper() == 'SERVICE'):
            DATABASE_SUFFIX_FLAG = 'NONE'
        elif self.config_reply.number_of_service_ports == 1 and (DATABASE_SUFFIX_FLAG.upper() == 'A' or DATABASE_SUFFIX_FLAG.upper() == 'ADDRESS'):
            DATABASE_SUFFIX_FLAG = 'NONE'

        global number_of_partitions
        number_of_partitions = self.config_reply.number_of_processes_per_port * self.config_reply.number_of_service_ports * self.config_reply.number_of_threads_per_process

        if not DATABASE_SUFFIX_FLAG == "NONE" and DATABASE_SUFFIX_FLAG is not None:
            global enroll_args
            enroll_args += " --database-suffix " + DATABASE_SUFFIX_FLAG + " "

    def test_06_correct_database_creation(self):
        """!
        Test if the database creation is correct.
        """
        message = 'Your service creates unique databases for each unique service running on non-unique ports. The Briar API can only call checkpoint and finalize on a service port, but not a unique service running within that port.'

        self.assertFalse(self.config_reply.number_of_processes_per_port > 1 and USES_FRONTEND_MERGING and DATABASE_SUFFIX_FLAG.upper() == "SERVICE", message)
        self.assertFalse(self.config_reply.number_of_processes_per_port > 1 and USES_FRONTEND_MERGING and DATABASE_SUFFIX_FLAG.upper() == "S", message)
        self.assertFalse(requires_database_merge and DATABASE_SUFFIX_FLAG.upper() == "NONE",
                         'Your service currently requires front-end merging (either only 1 process is running or you specified BRIAR_USE_FRONT_END_MERGING, but you are not specifying how the API should create a suffix for your databases to keep them unique.')
        self.assertFalse(not requires_database_merge and DATABASE_SUFFIX_FLAG is not None and not DATABASE_SUFFIX_FLAG.upper() == "NONE",
                         'Your service currently does not need front-end merging, but you are specifying a suffix for the api to use on your database with environment variable BRIAR_DATABASE_SUFFIX_FLAG.  This could lead to errors so we are setting the suffix to NONE')
        test_warn(self.assertFalse, self.config_reply.number_of_processes_per_port > 1 and USES_FRONTEND_MERGING and DATABASE_SUFFIX_FLAG.upper() == "ADDRESS+SERVICE", message)
        test_warn(self.assertFalse, self.config_reply.number_of_processes_per_port > 1 and USES_FRONTEND_MERGING and DATABASE_SUFFIX_FLAG.upper() == "ADDRESS,SERVICE", message)
        test_warn(self.assertFalse, self.config_reply.number_of_processes_per_port > 1 and USES_FRONTEND_MERGING and DATABASE_SUFFIX_FLAG.upper() == "AS", message)

        self.assertFalse(self.config_reply.number_of_threads_per_process > 1 and USES_FRONTEND_MERGING and DATABASE_SUFFIX_FLAG.upper() == "SERVICE", message)
        self.assertFalse(self.config_reply.number_of_threads_per_process > 1 and USES_FRONTEND_MERGING and DATABASE_SUFFIX_FLAG.upper() == "S", message)
        test_warn(self.assertFalse, self.config_reply.number_of_threads_per_process > 1 and USES_FRONTEND_MERGING and DATABASE_SUFFIX_FLAG.upper() == "ADDRESS+SERVICE", message)
        test_warn(self.assertFalse, self.config_reply.number_of_threads_per_process > 1 and USES_FRONTEND_MERGING and DATABASE_SUFFIX_FLAG.upper() == "ADDRESS,SERVICE", message)
        test_warn(self.assertFalse, self.config_reply.number_of_threads_per_process > 1 and USES_FRONTEND_MERGING and DATABASE_SUFFIX_FLAG.upper() == "AS", message)


def run_on_multi(self, base_db_name, mapped_function):
    """!
    Run a function on multiple databases.

    This function runs a specified function on multiple databases by refreshing the database list and iterating over
    the databases that match the base database name.

    @param self: The test case instance.
    @param base_db_name str: The base name of the database.
    @param mapped_function function: The function to run on each database.
    """
    from briar.cli.database.refresh import database_refresh
    from briar.cli.database.list import database_list

    database_refresh(input_command='database refresh' + args_string)
    database_list_base = database_list(ret=True, input_command="database list" + args_string)
    total_database_partitions = []
    for database_name in database_list_base:
        if base_db_name + '_' in database_name:
            total_database_partitions.append(database_name)

    test_warn(self.assertEqual, len(total_database_partitions), number_of_partitions, "The number of created sub-databases does not match the number of partitions your algorithm ran")

    for port in port_list:
        dblist_local = database_list(ret=True, input_command="database list" + args_string + ' -p ' + port)
        dbfound = 0
        for database_name in total_database_partitions:
            removed_base = database_name.replace(base_db_name + '_', '')

            database_name_parts = removed_base.split('_')
            service_address = None
            if DATABASE_SUFFIX_FLAG is not None:
                if DATABASE_SUFFIX_FLAG.upper() == 'ADDRESS,SERVICE' or DATABASE_SUFFIX_FLAG.upper() == 'AS' or DATABASE_SUFFIX_FLAG.upper() == 'ADDRESS+SERVICE':
                    test_warn(self.assertIsNot, DATABASE_SUFFIX_FLAG.upper(), 'ADDRESS,SERVICE', 'Your service creates unique databases for each unique service running on non-unique ports. The Briar API can only call checkpoint and finalize on a service port, but not a unique service running within that port.')
                    test_warn(self.assertIsNot, DATABASE_SUFFIX_FLAG.upper(), 'AS', 'Your service creates unique databases for each unique service running on non-unique ports. The Briar API can only call checkpoint and finalize on a service port, but not a unique service running within that port.')

                    self.assertGreaterEqual(len(database_name_parts), 2, 'incorrect format of ' + str(database_name_parts) + 'from full database name ' + database_name)
                    service_identifier = database_name_parts[-1]
                    service_address = removed_base.replace('_' + service_identifier, '')
                elif DATABASE_SUFFIX_FLAG.upper() == 'ADDRESS' or DATABASE_SUFFIX_FLAG.upper() == 'A':
                    service_address = removed_base
                elif DATABASE_SUFFIX_FLAG.upper() == 'SERVICE' or DATABASE_SUFFIX_FLAG.upper() == 'S':
                    self.assertNotEquals(DATABASE_SUFFIX_FLAG.upper(), 'SERVICE', 'Your algorithm is set to only produce sub-databases with service identifiers, which cannot be directly called to checkpoint or finalize by the API')
                    self.assertNotEquals(DATABASE_SUFFIX_FLAG.upper(), 'S', 'Your algorithm is set to only produce sub-databases with service identifiers, which cannot be directly called to checkpoint or finalize by the API')
                else:
                    self.assertFalse(True, 'DATABASE_SUFFIX_FLAG is ' + DATABASE_SUFFIX_FLAG + ' and cannot be parsed to determine correct database naming operation: ' + DATABASE_SUFFIX_FLAG)

            if service_address is not None:
                service_port = service_address.split('_')[-1]
                if service_port in port and service_address == port.replace(':', '_').replace('.', '-') and database_name in dblist_local:
                    from briar.cli.database.info import database_info
                    r = database_info(input_command='database info -p ' + port + ' ' + database_name)
                    mapped_function(args_string + ' -p ' + port + ' ', database_name)
                    print('Matched database', database_name, ' to service on port', port)
                    dbfound += 1
            elif database_name in dblist_local:
                mapped_function(args_string + ' -p ' + port + ' ', database_name)

                test_warn(self.assertTrue, False, 'We have found a database match but cannot guarantee that it is the correct match, since we cannot link port numbers and addresses')
                print('Matched database', database_name, ' to service on port', port)
                dbfound += 1
        print('db local list for', port, dblist_local)
        self.assertGreaterEqual(dbfound, 1, 'None of the databases ' + str(total_database_partitions) + 'located the local configured service ' + port)


def get_info(self, db_name):
    """!
    Get information about a database.

    This function retrieves information about a database, including the number of entries, templates, and failed enrollments.

    @param self: The test case instance.
    @param db_name str: The name of the database.
    @return: A tuple containing the number of entries, templates, and failed enrollments.
    """
    from briar.cli.database.info import database_info

    info_reply = database_info(input_command="database info " + args_string + db_name, ret=True)
    db_info = info_reply.info
    entries = db_info.entry_count
    templates = db_info.template_count
    failed = db_info.failed_enrollment_count
    return entries, templates, failed


def get_multi_info(self, base_db_name):
    """!
    Get information about multiple databases.

    This function retrieves information about multiple databases by refreshing the database list and iterating over
    the databases that match the base database name.

    @param self: The test case instance.
    @param base_db_name str: The base name of the database.
    @return: A tuple containing the total number of entries, templates, and failed enrollments across all databases.
    """
    from briar.cli.database.refresh import database_refresh
    from briar.cli.database.list import database_list

    database_refresh(input_command='database refresh' + args_string)
    database_list = database_list(ret=True, input_command="database list" + args_string)
    total_database_partitions = []
    for database_name in database_list:
        if base_db_name + '_' in database_name:
            total_database_partitions.append(database_name)

    test_warn(self.assertEqual, len(total_database_partitions), number_of_partitions, "The number of created sub-databases does not match the number of partitions your algorithm ran")
    total_templates = 0
    total_entries = 0
    total_failed = 0
    for database_name in total_database_partitions:
        entries, templates, failed = get_info(self, database_name)
        total_templates += templates
        total_entries += entries
        total_failed += failed

    return total_entries, total_templates, total_failed


def merge_dbs(self, db_name):
    """!
    Merge multiple databases into a single database.

    This function merges multiple databases into a single database by refreshing the database list, retrieving information
    about the databases, and performing the merge operation.

    @param self: The test case instance.
    @param db_name str: The base name of the database.
    @return: A tuple containing the merged database information, total number of entries, templates, and failed enrollments.
    """
    if requires_database_merge:
        from briar.cli.database.refresh import database_refresh
        from briar.cli.database.list import database_list
        from briar.cli.database.info import database_info
        from briar.cli.database.merge import database_merge

        refresh_reply = database_refresh(input_command='database refresh' + args_string)
        avail_database_list = database_list(ret=True, input_command="database list" + args_string)
        total_entries, total_templates, total_failed = get_multi_info(self, db_name)
        database_merge(input_command='database merge --regex ' + db_name + '_* --output-database merged_' + db_name)
        avail_database_list = database_list(ret=True, input_command="database list" + args_string)
        self.assertIn('merged_' + db_name, avail_database_list)
        merged_dbinfo = get_info(self, 'merged_' + db_name)
        self.assertEqual(merged_dbinfo[0], total_entries, 'the number of entries in the merged database ' + 'merged_' + db_name + ' does not match the sum of the entries in the unmerged databases')
        self.assertEqual(merged_dbinfo[1], total_templates, 'the number of templates in the merged database ' + 'merged_' + db_name + ' does not match the sum of the templates in the unmerged databases')
        self.assertEqual(merged_dbinfo[2], total_failed, 'the number of failure cases in the merged database ' + 'merged_' + db_name + ' does not match the sum of the failures in the unmerged databases')
        return merged_dbinfo, total_entries, total_templates, total_failed


@unittest.skipIf(1.1 not in RUN_STAGES, 'Test 001 is not in the requested run stages')
class Test001SigsetEnrollProbe(unittest.TestCase):
    """!
    Test probe enrollment using sigsets.

    This class contains tests to enroll probes using sigsets and checkpoint the databases.
    """

    @classmethod
    def setUpClass(cls) -> None:
        if requires_database_merge:
            print('The Test Suite has determined that your service will require auto-generation of partitioned databases while running enrollment tests')
            global enroll_args
            enroll_args += " --auto-create-database --database-suffix AS "
        else:
            print('The Test Suite has determined that your service will NOT require auto-generation of partitioned databases while running enrollment tests')

        setUpClass_main(cls)

    def test_01_sigset_enroll_probe(self):
        """!
        Test probe enrollment using sigsets.
        """
        print('Testing Probe Enrollment')

        from briar.cli.sigset import sigset_enroll
        from briar.cli.database.create import database_create
        try:
            input_command_create = "database create " + args_string + database_probe_name
            print('Running test command:', input_command_create)
            reply = database_create(input_command=input_command_create, ret=True)
        except Exception as e:
            print('WARNING: database already exists, you may want to delete the databases and rerun the test from scratch', database_gallery_1_name)
        input_command = 'sigset-enroll' + args_string + media_args + enroll_args + ' --entry-type probe --database ' + database_probe_name + ' ' + self.probe_sigset_path + ' ' + DATASET_DIR
        print('Running test command:', input_command)
        enroll_reply = sigset_enroll(input_command=input_command)

    def test_02_probe_checkpoint(self):
        """!
        Test checkpointing the probe database.
        """
        checkpoint_db(args_string, database_probe_name)
        if requires_database_merge:
            run_on_multi(self, database_probe_name, checkpoint_db)


@unittest.skipIf(1.2 not in RUN_STAGES, 'Test 002 is not in the requested run stages')
class Test002ProbeDatabaseMerge(unittest.TestCase):
    """!
    Test merging probe databases.

    This class contains tests to merge probe databases and checkpoint the merged database.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_02_merge_probe_dbs(self):
        """!
        Test merging probe databases.
        """
        if requires_database_merge:
            merged_dbinfo, total_entries, total_templates, total_failed = merge_dbs(self, database_probe_name)

            self.merged_dbinfo = merged_dbinfo
            self.total_entries = total_entries
            self.total_templates = total_templates
            self.total_failed = total_failed
            print('Merged database info:', self.merged_dbinfo, self.total_entries, self.total_templates, self.total_failed)

            self.assertEqual(self.total_entries, len(self.probe_sigset), 'the number of entries in the set of sub partition databases different than the number of entries in the probe sigset')
            self.assertEqual(self.merged_dbinfo[0], len(self.probe_sigset), 'the number of entries in the merged database is different than the number of entries in the probe sigset')

        else:
            from briar.cli.database.rename import database_rename
            database_rename(input_command='database rename ' + args_string + database_probe_name + ' merged_' + database_probe_name)
        entries, templates, failed = get_info(self, ' merged_' + database_probe_name)
        self.assertEqual(entries, len(self.probe_sigset), 'the number of entries in the database is different than the number of entries in the probe sigset')

    def test_03_checkpoint_merged_probe_db(self):
        """!
        Test checkpointing the merged probe database.
        """
        from briar.cli.database.checkpoint import database_checkpoint
        database_checkpoint(input_command='database checkpoint ' + args_string + ' merged_' + database_probe_name)


@unittest.skipIf(1.3 not in RUN_STAGES, 'Test 001 is not in the requested run stages')
class Test003SigsetEnrollMultiProbe(unittest.TestCase):
    """!
    Test multisubject probe enrollment using sigsets.

    This class contains tests to enroll multisubject probes using sigsets and checkpoint the databases.
    """

    @classmethod
    def setUpClass(cls) -> None:
        if requires_database_merge:
            print('The Test Suite has determined that your service will require auto-generation of partitioned databases while running enrollment tests')
            global enroll_args
            enroll_args += " --auto-create-database --database-suffix AS "
        else:
            print('The Test Suite has determined that your service will NOT require auto-generation of partitioned databases while running enrollment tests')

        setUpClass_main(cls)

    def test_01_sigset_enroll_probe(self):
        """!
        Test multisubject probe enrollment using sigsets.
        """
        print('Testing Probe Enrollment')

        from briar.cli.sigset import sigset_enroll
        from briar.cli.database.create import database_create
        try:
            input_command_create = "database create " + args_string + database_multi_probe_name
            print('Running test command:', input_command_create)
            reply = database_create(input_command=input_command_create, ret=True)
        except Exception as e:
            print('WARNING: database already exists, you may want to delete the databases and rerun the test from scratch', database_gallery_1_name)
        input_command = 'sigset-enroll' + args_string + media_args + enroll_args + ' --entry-type probe --database ' + database_multi_probe_name + ' ' + self.probe_multisubject_sigset_path + ' ' + DATASET_DIR
        print('Running test command:', input_command)
        enroll_reply = sigset_enroll(input_command=input_command)

    def test_02_probe_checkpoint(self):
        """!
        Test checkpointing the multisubject probe database.
        """
        checkpoint_db(args_string, database_multi_probe_name)
        if requires_database_merge:
            run_on_multi(self, database_multi_probe_name, checkpoint_db)


@unittest.skipIf(1.4 not in RUN_STAGES, 'Test 002 is not in the requested run stages')
class Test004MultiProbeDatabaseMerge(unittest.TestCase):
    """!
    Test merging multisubject probe databases.

    This class contains tests to merge multisubject probe databases and checkpoint the merged database.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_02_merge_probe_dbs(self):
        """!
        Test merging multisubject probe databases.
        """
        if requires_database_merge:
            merged_dbinfo, total_entries, total_templates, total_failed = merge_dbs(self, database_multi_probe_name)

            self.merged_dbinfo = merged_dbinfo
            self.total_entries = total_entries
            self.total_templates = total_templates
            self.total_failed = total_failed
            print('Merged database info:', self.merged_dbinfo, self.total_entries, self.total_templates, self.total_failed)

            self.assertEqual(self.total_entries, len(self.probe_multisubject_sigset), 'the number of entries in the set of sub partition databases different than the number of entries in the probe sigset')
            self.assertEqual(self.merged_dbinfo[0], len(self.probe_multisubject_sigset), 'the number of entries in the merged database is different than the number of entries in the probe sigset')

        else:
            from briar.cli.database.rename import database_rename
            database_rename(input_command='database rename ' + args_string + database_multi_probe_name + ' merged_' + database_multi_probe_name)
        entries, templates, failed = get_info(self, ' merged_' + database_multi_probe_name)
        self.assertEqual(entries, len(self.probe_multisubject_sigset), 'the number of entries in the database is different than the number of entries in the probe sigset')

    def test_03_checkpoint_merged_probe_db(self):
        """!
        Test checkpointing the merged multisubject probe database.
        """
        from briar.cli.database.checkpoint import database_checkpoint
        database_checkpoint(input_command='database checkpoint ' + args_string + ' merged_' + database_multi_probe_name)


@unittest.skipIf(2 not in RUN_STAGES and 2.1 not in RUN_STAGES and 2.2 not in RUN_STAGES and 2.3 not in RUN_STAGES and 2.4 not in RUN_STAGES, 'Test 003 is not in the requested run stages')
class Test005SigsetEnrollGalleries(unittest.TestCase):
    """!
    Test gallery enrollment using sigsets.

    This class contains tests to enroll galleries using sigsets and checkpoint the databases.
    """

    @classmethod
    def setUpClass(cls) -> None:
        if requires_database_merge:
            print('The Test Suite has determined that your service will require auto-generation of partitioned databases while running enrollment tests')
            global enroll_args
            enroll_args += " --auto-create-database --database-suffix AS "
        else:
            print('The Test Suite has determined that your service will NOT require auto-generation of partitioned databases while running enrollment tests')

        setUpClass_main(cls)

    def runGallery(self, gal_name, sigset_path):
        """!
        Run gallery enrollment using sigsets.

        This function enrolls a gallery using a specified sigset and database name.

        @param gal_name str: The name of the gallery database.
        @param sigset_path str: The path to the sigset file.
        """
        from briar.cli.sigset import sigset_enroll
        from briar.cli.database.create import database_create
        try:
            reply = database_create(input_command="database create " + args_string + gal_name, ret=True)
        except Exception as e:
            print('WARNING: database already exists, you may want to delete the databases and rerun the test from scratch', database_gallery_1_name)
        enroll_reply = sigset_enroll(input_command='sigset-enroll' + args_string + media_args + enroll_args + ' --entry-type gallery --batch-total 1 --database ' + gal_name + ' ' + sigset_path + ' ' + DATASET_DIR)

    @unittest.skipIf(2.1 not in RUN_STAGES, 'Not running Gallery1 enroll')
    def test_01_sigset_enroll_gallery1(self):
        """!
        Test gallery 1 enrollment using sigsets.
        """
        print('Testing Gallery 1 Enrollment')
        self.runGallery(database_gallery_1_name, self.gallery_1_sigset_path)

    @unittest.skipIf(2.1 not in RUN_STAGES, 'Not running Gallery1 enroll')
    def test_02_gallery1_partitioned_checkpoint(self):
        """!
        Test checkpointing the partitioned gallery 1 database.
        """
        if requires_database_merge:
            checkpoint_db(args_string, database_gallery_1_name)
            run_on_multi(self, database_gallery_1_name, checkpoint_db)
        else:
            finalize_db(args_string, database_gallery_1_name)

    @unittest.skipIf(2.2 not in RUN_STAGES, 'Not running Gallery1 enroll')
    def test_03_sigset_enroll_gallery2(self):
        """!
        Test gallery 2 enrollment using sigsets.
        """
        print('Testing Gallery 2 Enrollment')
        self.runGallery(database_gallery_2_name, self.gallery_2_sigset_path)

    @unittest.skipIf(2.2 not in RUN_STAGES, 'Not running Gallery1 enroll')
    def test_04_gallery2_partitioned_checkpoint(self):
        """!
        Test checkpointing the partitioned gallery 2 database.
        """
        if requires_database_merge:
            checkpoint_db(args_string, database_gallery_2_name)
            run_on_multi(self, database_gallery_2_name, checkpoint_db)
        else:
            finalize_db(args_string, database_gallery_2_name)

    @unittest.skipIf(2.3 not in RUN_STAGES, 'Not running Gallery1 enroll')
    def test_05_sigset_enroll_gallery1(self):
        """!
        Test blended gallery 1 enrollment using sigsets.
        """
        print('Testing Blended Gallery 1 Enrollment')
        self.runGallery(database_blended_gallery_1_name, self.gallery_1_blended_sigset_path)

    @unittest.skipIf(2.3 not in RUN_STAGES, 'Not running Gallery1 enroll')
    def test_06_gallery1_partitioned_checkpoint(self):
        """!
        Test checkpointing the partitioned blended gallery 1 database.
        """
        if requires_database_merge:
            checkpoint_db(args_string, database_blended_gallery_1_name)
            run_on_multi(self, database_blended_gallery_1_name, checkpoint_db)
        else:
            finalize_db(args_string, database_blended_gallery_1_name)

    @unittest.skipIf(2.4 not in RUN_STAGES, 'Not running Gallery1 enroll')
    def test_07_sigset_enroll_gallery2(self):
        """!
        Test blended gallery 2 enrollment using sigsets.
        """
        print('Testing Blended Gallery 2 Enrollment')
        self.runGallery(database_blended_gallery_2_name, self.gallery_2_blended_sigset_path)

    @unittest.skipIf(2.4 not in RUN_STAGES, 'Not running Gallery1 enroll')
    def test_08_gallery2_partitioned_checkpoint(self):
        """!
        Test checkpointing the partitioned blended gallery 2 database.
        """
        if requires_database_merge:
            checkpoint_db(args_string, database_blended_gallery_2_name)
            run_on_multi(self, database_blended_gallery_2_name, checkpoint_db)
        else:
            finalize_db(args_string, database_blended_gallery_2_name)


@unittest.skipIf(2 not in RUN_STAGES and 2.1 not in RUN_STAGES and 2.2 not in RUN_STAGES and 2.3 not in RUN_STAGES and 2.4 not in RUN_STAGES, 'Test 004 is not in the requested run stages')
class Test006GalleryDatabaseMerge(unittest.TestCase):
    """!
    Test merging gallery databases.

    This class contains tests to merge gallery databases and finalize the merged databases.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def merge_db_func(self, gallery_sigset, gallery_db_base_name):
        """!
        Merge gallery databases.

        This function merges gallery databases and checks the number of entries in the merged database.

        @param gallery_sigset: The sigset for the gallery.
        @param gallery_db_base_name: The base name of the gallery database.
        """
        unique_subjects = np.unique([s[0] for s in gallery_sigset['subjectId']])
        if requires_database_merge:
            merged_dbinfo, total_entries, total_templates, total_failed = merge_dbs(self, gallery_db_base_name)
            self.assertEqual(total_entries, len(unique_subjects), 'the number of entries in the set of sub partition databases different than the number of entries in the gallery1 sigset')
            self.assertEqual(merged_dbinfo[0], len(unique_subjects), 'the number of entries in the merged database is different than the number of entries in the gallery1 sigset')
        else:
            from briar.cli.database.rename import database_rename
            database_rename(input_command='database rename ' + args_string + gallery_db_base_name + ' merged_' + gallery_db_base_name)
        entries, templates, failed = get_info(self, ' merged_' + gallery_db_base_name)
        self.assertEqual(entries, len(unique_subjects), 'the number of entries in the database is different than the number of entries in the gallery1 sigset')

    @unittest.skipIf(2.1 not in RUN_STAGES, 'Not running Gallery1 merge')
    def test_01_merge_gallery1_dbs(self):
        """!
        Test merging gallery 1 databases.
        """
        self.merge_db_func(self.gallery1_sigset, database_gallery_1_name)

    @unittest.skipIf(2.2 not in RUN_STAGES, 'Not running Gallery2 merge')
    def test_02_merge_gallery2_dbs(self):
        """!
        Test merging gallery 2 databases.
        """
        self.merge_db_func(self.gallery2_sigset, database_gallery_2_name)

    @unittest.skipIf(2.3 not in RUN_STAGES, 'Not running Gallery2 merge')
    def test_03_merge_blended_gallery2_dbs(self):
        """!
        Test merging blended gallery 1 databases.
        """
        self.merge_db_func(self.gallery1_blended_sigset, database_blended_gallery_1_name)

    @unittest.skipIf(2.4 not in RUN_STAGES, 'Not running Gallery2 merge')
    def test_04_merge_blended_gallery2_dbs(self):
        """!
        Test merging blended gallery 2 databases.
        """
        self.merge_db_func(self.gallery2_blended_sigset, database_blended_gallery_2_name)

    @unittest.skipIf(2.1 not in RUN_STAGES, 'Not running Gallery1 finalize')
    def test_05_finalized_merged_gallery1_db(self):
        """!
        Test finalizing the merged gallery 1 database.
        """
        finalize_db(args_string, 'merged_' + database_gallery_1_name)

    @unittest.skipIf(2.2 not in RUN_STAGES, 'Not running Gallery2 finalize')
    def test_06_finalized_merged_gallery1_db(self):
        """!
        Test finalizing the merged gallery 2 database.
        """
        finalize_db(args_string, 'merged_' + database_gallery_2_name)

    @unittest.skipIf(2.3 not in RUN_STAGES, 'Not running Gallery1 finalize')
    def test_07_finalized_merged_gallery1_db(self):
        """!
        Test finalizing the merged blended gallery 1 database.
        """
        finalize_db(args_string, 'merged_' + database_blended_gallery_1_name)

    @unittest.skipIf(2.4 not in RUN_STAGES, 'Not running Gallery2 finalize')
    def test_08_finalized_merged_gallery1_db(self):
        """!
        Test finalizing the merged blended gallery 2 database.
        """
        finalize_db(args_string, 'merged_' + database_blended_gallery_2_name)


def compute_search(probe_db_name, gal_db_name, probe_sigset_path, output_path, modality=None, blended=False):
    """!
    Compute search scores for a probe database against a gallery database.

    This function computes search scores for a probe database against a gallery database and saves the results to a file.

    @param probe_db_name str: The name of the probe database.
    @param gal_db_name str: The name of the gallery database.
    @param probe_sigset_path str: The path to the probe sigset file.
    @param output_path str: The path to save the output file.
    @param modality str: The modality to use for the search (optional).
    @param blended bool: Whether to use blended galleries (optional).
    """
    from briar.cli.database.compute_search import database_compute_search
    if blended:
        outdir = os.path.join(OUTPUT_DIR, 'blended')
    else:
        outdir = os.path.join(OUTPUT_DIR, 'simple')
    os.makedirs(outdir, exist_ok=True)
    modality_arg = ""
    if modality is not None:
        modality_arg = " --modality " + modality + " "
    command = 'compute-search --return-entry-id ' + USE_SINGLE_SUBJECT + ' --search-database ' + 'merged_' + gal_db_name + ' --probe-database ' + 'merged_' + probe_db_name + ' --output-type pickle -o ' + os.path.join(outdir, output_path) + ' --probe-order-list ' + probe_sigset_path + ' ' + media_args + modality_arg + args_string
    search_reply = database_compute_search(input_command=command)


def compute_verify(probe_db_name, gal_db_name, probe_sigset_path, gal_sigset_path, output_path, csv_path, modality=None, blended=False):
    """!
    Compute verification scores for a probe database against a gallery database.

    This function computes verification scores for a probe database against a gallery database and saves the results to a file.

    @param probe_db_name str: The name of the probe database.
    @param gal_db_name str: The name of the gallery database.
    @param probe_sigset_path str: The path to the probe sigset file.
    @param gal_sigset_path str: The path to the gallery sigset file.
    @param output_path str: The path to save the output file.
    @param csv_path str: The path to save the CSV file.
    @param modality str: The modality to use for verification (optional).
    @param blended bool: Whether to use blended galleries (optional).
    """
    from briar.cli.database.compute_scores import database_compute_verify
    if blended:
        outdir = os.path.join(OUTPUT_DIR, 'blended')
    else:
        outdir = os.path.join(OUTPUT_DIR, 'simple')
    os.makedirs(outdir, exist_ok=True)
    modality_arg = ""
    if modality is not None:
        modality_arg = " --modality " + modality + " "
    command = 'compute-verify ' + USE_SINGLE_SUBJECT + ' --reference-database ' + 'merged_' + gal_db_name + ' --verify-database ' + 'merged_' + probe_db_name + ' --output-type pickle -o ' + os.path.join(outdir, output_path) + ' --gallery-data-filename ' + os.path.join(outdir, csv_path) + ' ' + media_args + args_string + modality_arg + ' --verify-order-list ' + probe_sigset_path + ' --reference-order-list ' + gal_sigset_path + ' ./'
    verify_reply = database_compute_verify(input_command=command)


@unittest.skipIf(3.01 not in RUN_STAGES, 'Test 005 is not in the requested run stages')
class Test007SigsetScoreG1(unittest.TestCase):
    """!
    Test scoring for gallery 1 using sigsets.

    This class contains tests to compute verification and search scores for gallery 1 using sigsets.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_probe_gallery1(self):
        """!
        Test verification scoring for gallery 1 using sigsets.
        """
        compute_verify(database_probe_name, database_gallery_1_name, self.probe_sigset_path, self.gallery_1_sigset_path, 'evaluation_all_scores_g1.pkl', 'gallery_data_g1.csv')

    def test_02_sigset_search_probe_gallery1(self):
        """!
        Test search scoring for gallery 1 using sigsets.
        """
        compute_search(database_probe_name, database_gallery_1_name, self.probe_sigset_path, 'evaluation_all_search_g1.pkl')


@unittest.skipIf(3.02 not in RUN_STAGES, 'Test 007 is not in the requested run stages')
class Test008SigsetScoreGaitG1(unittest.TestCase):
    """!
    Test gait scoring for gallery 1 using sigsets.

    This class contains tests to compute verification and search scores for gallery 1 using gait modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_gait_probe_gallery1(self):
        """!
        Test gait verification scoring for gallery 1 using sigsets.
        """
        compute_verify(database_probe_name, database_gallery_1_name, self.probe_sigset_path, self.gallery_1_sigset_path, 'evaluation_gait_scores_g1.pkl', 'gallery_gait_data_g1.csv', modality='gait')

    def test_02_sigset_search_gait_probe_gallery1(self):
        """!
        Test gait search scoring for gallery 1 using sigsets.
        """
        compute_search(database_probe_name, database_gallery_1_name, self.probe_sigset_path, 'evaluation_gait_search_g1.pkl', modality='gait')


@unittest.skipIf(3.03 not in RUN_STAGES, 'Test 010 is not in the requested run stages')
class Test009SigsetScoreFaceG1(unittest.TestCase):
    """!
    Test face scoring for gallery 1 using sigsets.

    This class contains tests to compute verification and search scores for gallery 1 using face modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_face_probe_gallery1(self):
        """!
        Test face verification scoring for gallery 1 using sigsets.
        """
        compute_verify(database_probe_name, database_gallery_1_name, self.probe_sigset_path, self.gallery_1_sigset_path, 'evaluation_face_scores_g1.pkl', 'gallery_face_data_g1.csv', modality='face')

    def test_02_sigset_search_face_probe_gallery1(self):
        """!
        Test face search scoring for gallery 1 using sigsets.
        """
        compute_search(database_probe_name, database_gallery_1_name, self.probe_sigset_path, 'evaluation_face_search_g1.pkl', modality='face')


@unittest.skipIf(3.04 not in RUN_STAGES, 'Test 011 is not in the requested run stages')
class Test010SigsetScoreWholeBodyG1(unittest.TestCase):
    """!
    Test whole body scoring for gallery 1 using sigsets.

    This class contains tests to compute verification and search scores for gallery 1 using whole body modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_WB_probe_gallery1(self):
        """!
        Test whole body verification scoring for gallery 1 using sigsets.
        """
        compute_verify(database_probe_name, database_gallery_1_name, self.probe_sigset_path, self.gallery_1_sigset_path, 'evaluation_wholebody_scores_g1.pkl', 'gallery_wholebody_data_g1.csv', modality='whole_body')

    def test_02_sigset_search_WB_probe_gallery1(self):
        """!
        Test whole body search scoring for gallery 1 using sigsets.
        """
        compute_search(database_probe_name, database_gallery_1_name, self.probe_sigset_path, 'evaluation_wholebody_search_g1.pkl', modality='whole_body')


@unittest.skipIf(3.05 not in RUN_STAGES, 'Test 006 is not in the requested run stages')
class Test011SigsetScoreG2(unittest.TestCase):
    """!
    Test scoring for gallery 2 using sigsets.

    This class contains tests to compute verification and search scores for gallery 2 using sigsets.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_probe_gallery2(self):
        """!
        Test verification scoring for gallery 2 using sigsets.
        """
        compute_verify(database_probe_name, database_gallery_2_name, self.probe_sigset_path, self.gallery_2_sigset_path, 'evaluation_all_scores_g2.pkl', 'gallery_data_g2.csv')

    def test_02_sigset_search_probe_gallery2(self):
        """!
        Test search scoring for gallery 2 using sigsets.
        """
        compute_search(database_probe_name, database_gallery_2_name, self.probe_sigset_path, 'evaluation_all_search_g2.pkl')


@unittest.skipIf(3.06 not in RUN_STAGES, 'Test 008 is not in the requested run stages')
class Test012SigsetScoreGaitG2(unittest.TestCase):
    """!
    Test gait scoring for gallery 2 using sigsets.

    This class contains tests to compute verification and search scores for gallery 2 using gait modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_gait_probe_gallery2(self):
        """!
        Test gait verification scoring for gallery 2 using sigsets.
        """
        compute_verify(database_probe_name, database_gallery_2_name, self.probe_sigset_path, self.gallery_2_sigset_path, 'evaluation_gait_scores_g2.pkl', 'gallery_gait_data_g2.csv', modality='gait')

    def test_02_sigset_search_gait_probe_gallery2(self):
        """!
        Test gait search scoring for gallery 2 using sigsets.
        """
        compute_search(database_probe_name, database_gallery_2_name, self.probe_sigset_path, 'evaluation_gait_search_g2.pkl', modality='gait')


@unittest.skipIf(3.07 not in RUN_STAGES, 'Test 009 is not in the requested run stages')
class Test013SigsetScoreFaceG2(unittest.TestCase):
    """!
    Test face scoring for gallery 2 using sigsets.

    This class contains tests to compute verification and search scores for gallery 2 using face modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_face_probe_gallery2(self):
        """!
        Test face verification scoring for gallery 2 using sigsets.
        """
        compute_verify(database_probe_name, database_gallery_2_name, self.probe_sigset_path, self.gallery_2_sigset_path, 'evaluation_face_scores_g2.pkl', 'gallery_face_data_g2.csv', modality='face')

    def test_02_sigset_search_face_probe_gallery2(self):
        """!
        Test face search scoring for gallery 2 using sigsets.
        """
        compute_search(database_probe_name, database_gallery_2_name, self.probe_sigset_path, 'evaluation_face_search_g2.pkl', modality='face')


@unittest.skipIf(3.08 not in RUN_STAGES, 'Test 012 is not in the requested run stages')
class Test014SigsetScoreWholeBodyG2(unittest.TestCase):
    """!
    Test whole body scoring for gallery 2 using sigsets.

    This class contains tests to compute verification and search scores for gallery 2 using whole body modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_WB_probe_gallery2(self):
        """!
        Test whole body verification scoring for gallery 2 using sigsets.
        """
        compute_verify(database_probe_name, database_gallery_2_name, self.probe_sigset_path, self.gallery_2_sigset_path, 'evaluation_wholebody_scores_g2.pkl', 'gallery_wholebody_data_g2.csv', modality='whole_body')

    def test_02_sigset_search_WB_probe_gallery2(self):
        """!
        Test whole body search scoring for gallery 2 using sigsets.
        """
        compute_search(database_probe_name, database_gallery_2_name, self.probe_sigset_path, 'evaluation_wholebody_search_g2.pkl', modality='whole_body')


@unittest.skipIf(3.09 not in RUN_STAGES, 'Test 005 is not in the requested run stages')
class Test015SigsetBlendedScoreG1(unittest.TestCase):
    """!
    Test scoring for blended gallery 1 using sigsets.

    This class contains tests to compute verification and search scores for blended gallery 1 using sigsets.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_probe_blended_gallery1(self):
        """!
        Test verification scoring for blended gallery 1 using sigsets.
        """
        compute_verify(database_probe_name, database_blended_gallery_1_name, self.probe_sigset_path, self.gallery_1_blended_sigset_path, 'evaluation_all_scores_g1.pkl', 'gallery_data_g1.csv', blended=True)

    def test_02_sigset_search_probe_blended_gallery1(self):
        """!
        Test search scoring for blended gallery 1 using sigsets.
        """
        compute_search(database_probe_name, database_blended_gallery_1_name, self.probe_sigset_path, 'evaluation_all_search_g1.pkl', blended=True)


@unittest.skipIf(3.1 not in RUN_STAGES, 'Test 008 is not in the requested run stages')
class Test016SigsetScoreBlendedGaitG1(unittest.TestCase):
    """!
    Test gait scoring for blended gallery 1 using sigsets.

    This class contains tests to compute verification and search scores for blended gallery 1 using gait modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_gait_probe_blended_gallery1(self):
        """!
        Test gait verification scoring for blended gallery 1 using sigsets.
        """
        compute_verify(database_probe_name, database_blended_gallery_1_name, self.probe_sigset_path, self.gallery_1_blended_sigset_path, 'evaluation_gait_scores_g1.pkl', 'gallery_gait_data_g1.csv', modality='gait', blended=True)

    def test_02_sigset_search_gait_probe_blended_gallery1(self):
        """!
        Test gait search scoring for blended gallery 1 using sigsets.
        """
        compute_search(database_probe_name, database_blended_gallery_1_name, self.probe_sigset_path, 'evaluation_gait_search_g1.pkl', modality='gait', blended=True)


@unittest.skipIf(3.11 not in RUN_STAGES, 'Test 009 is not in the requested run stages')
class Test017SigsetScoreBlendedFaceG1(unittest.TestCase):
    """!
    Test face scoring for blended gallery 1 using sigsets.

    This class contains tests to compute verification and search scores for blended gallery 1 using face modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_face_probe_blended_gallery1(self):
        """!
        Test face verification scoring for blended gallery 1 using sigsets.
        """
        compute_verify(database_probe_name, database_blended_gallery_1_name, self.probe_sigset_path, self.gallery_1_blended_sigset_path, 'evaluation_face_scores_g1.pkl', 'gallery_face_data_g1.csv', modality='face', blended=True)

    def test_02_sigset_search_face_probe_blended_gallery1(self):
        """!
        Test face search scoring for blended gallery 1 using sigsets.
        """
        compute_search(database_probe_name, database_blended_gallery_1_name, self.probe_sigset_path, 'evaluation_face_search_g1.pkl', modality='face', blended=True)


@unittest.skipIf(3.12 not in RUN_STAGES, 'Test 011 is not in the requested run stages')
class Test018SigsetScoreBlendedWholeBodyG1(unittest.TestCase):
    """!
    Test whole body scoring for blended gallery 1 using sigsets.

    This class contains tests to compute verification and search scores for blended gallery 1 using whole body modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_WB_probe_blended_gallery1(self):
        """!
        Test whole body verification scoring for blended gallery 1 using sigsets.
        """
        compute_verify(database_probe_name, database_blended_gallery_1_name, self.probe_sigset_path, self.gallery_1_blended_sigset_path, 'evaluation_wholebody_scores_g1.pkl', 'gallery_wholebody_data_g1.csv', modality='whole_body', blended=True)

    def test_02_sigset_search_WB_probe_blended_gallery1(self):
        """!
        Test whole body search scoring for blended gallery 1 using sigsets.
        """
        compute_search(database_probe_name, database_blended_gallery_1_name, self.probe_sigset_path, 'evaluation_wholebody_search_g1.pkl', modality='whole_body', blended=True)


@unittest.skipIf(3.13 not in RUN_STAGES, 'Test 006 is not in the requested run stages')
class Test019SigsetBlendedScoreG2(unittest.TestCase):
    """!
    Test scoring for blended gallery 2 using sigsets.

    This class contains tests to compute verification and search scores for blended gallery 2 using sigsets.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_probe_blended_gallery2(self):
        """!
        Test verification scoring for blended gallery 2 using sigsets.
        """
        compute_verify(database_probe_name, database_blended_gallery_2_name, self.probe_sigset_path, self.gallery_2_blended_sigset_path, 'evaluation_all_scores_g2.pkl', 'gallery_data_g2.csv', blended=True)

    def test_02_sigset_search_probe_blended_gallery2(self):
        """!
        Test search scoring for blended gallery 2 using sigsets.
        """
        compute_search(database_probe_name, database_blended_gallery_2_name, self.probe_sigset_path, 'evaluation_all_search_g2.pkl', blended=True)


@unittest.skipIf(3.14 not in RUN_STAGES, 'Test 007 is not in the requested run stages')
class Test020SigsetScoreBlendedGaitG2(unittest.TestCase):
    """!
    Test gait scoring for blended gallery 2 using sigsets.

    This class contains tests to compute verification and search scores for blended gallery 2 using gait modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_gait_probe_blended_gallery2(self):
        """!
        Test gait verification scoring for blended gallery 2 using sigsets.
        """
        compute_verify(database_probe_name, database_blended_gallery_2_name, self.probe_sigset_path, self.gallery_2_blended_sigset_path, 'evaluation_gait_scores_g2.pkl', 'gallery_gait_data_g2.csv', modality='gait', blended=True)

    def test_02_sigset_search_gait_probe_blended_gallery2(self):
        """!
        Test gait search scoring for blended gallery 2 using sigsets.
        """
        compute_search(database_probe_name, database_blended_gallery_2_name, self.probe_sigset_path, 'evaluation_gait_search_g2.pkl', modality='gait', blended=True)


@unittest.skipIf(3.15 not in RUN_STAGES, 'Test 010 is not in the requested run stages')
class Test021SigsetScoreBlendedFaceG2(unittest.TestCase):
    """!
    Test face scoring for blended gallery 2 using sigsets.

    This class contains tests to compute verification and search scores for blended gallery 2 using face modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_face_probe_blended_gallery2(self):
        """!
        Test face verification scoring for blended gallery 2 using sigsets.
        """
        compute_verify(database_probe_name, database_blended_gallery_2_name, self.probe_sigset_path, self.gallery_2_blended_sigset_path, 'evaluation_face_scores_g2.pkl', 'gallery_face_data_g2.csv', modality='face', blended=True)

    def test_02_sigset_search_face_probe_blended_gallery2(self):
        """!
        Test face search scoring for blended gallery 2 using sigsets.
        """
        compute_search(database_probe_name, database_blended_gallery_2_name, self.probe_sigset_path, 'evaluation_face_search_g2.pkl', modality='face', blended=True)


@unittest.skipIf(3.16 not in RUN_STAGES, 'Test 012 is not in the requested run stages')
class Test022SigsetScoreBlendedWholeBodyG2(unittest.TestCase):
    """!
    Test whole body scoring for blended gallery 2 using sigsets.

    This class contains tests to compute verification and search scores for blended gallery 2 using whole body modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_WB_probe_blended_gallery2(self):
        """!
        Test whole body verification scoring for blended gallery 2 using sigsets.
        """
        compute_verify(database_probe_name, database_blended_gallery_2_name, self.probe_sigset_path, self.gallery_2_blended_sigset_path, 'evaluation_wholebody_scores_g2.pkl', 'gallery_wholebody_data_g2.csv', modality='whole_body', blended=True)

    def test_02_sigset_search_WB_probe_blended_gallery2(self):
        """!
        Test whole body search scoring for blended gallery 2 using sigsets.
        """
        compute_search(database_probe_name, database_blended_gallery_2_name, self.probe_sigset_path, 'evaluation_wholebody_search_g2.pkl', modality='whole_body', blended=True)


@unittest.skipIf(3.17 not in RUN_STAGES, 'Test 005 is not in the requested run stages')
class Test023MultiSigsetScoreG1(unittest.TestCase):
    """!
    Test scoring for multisubject gallery 1 using sigsets.

    This class contains tests to compute verification and search scores for multisubject gallery 1 using sigsets.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_multiprobe_gallery1(self):
        """!
        Test verification scoring for multisubject gallery 1 using sigsets.
        """
        compute_verify(database_multi_probe_name, database_gallery_1_name, self.probe_multisubject_sigset_path, self.gallery_1_sigset_path, 'evaluation_multi_all_scores_g1.pkl', 'gallery_data_g1.csv')

    def test_02_sigset_search_multiprobe_gallery1(self):
        """!
        Test search scoring for multisubject gallery 1 using sigsets.
        """
        compute_search(database_multi_probe_name, database_gallery_1_name, self.probe_multisubject_sigset_path, 'evaluation_multi_all_search_g1.pkl')


@unittest.skipIf(3.18 not in RUN_STAGES, 'Test 007 is not in the requested run stages')
class Test024MultiSigsetScoreGaitG1(unittest.TestCase):
    """!
    Test gait scoring for multisubject gallery 1 using sigsets.

    This class contains tests to compute verification and search scores for multisubject gallery 1 using gait modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_gait_multiprobe_gallery1(self):
        """!
        Test gait verification scoring for multisubject gallery 1 using sigsets.
        """
        compute_verify(database_multi_probe_name, database_gallery_1_name, self.probe_multisubject_sigset_path, self.gallery_1_sigset_path, 'evaluation_multi_gait_scores_g1.pkl', 'gallery_gait_data_g1.csv', modality='gait')

    def test_02_sigset_search_gait_multiprobe_gallery1(self):
        """!
        Test gait search scoring for multisubject gallery 1 using sigsets.
        """
        compute_search(database_multi_probe_name, database_gallery_1_name, self.probe_multisubject_sigset_path, 'evaluation_multi_gait_search_g1.pkl', modality='gait')


@unittest.skipIf(3.19 not in RUN_STAGES, 'Test 010 is not in the requested run stages')
class Test025MultiSigsetScoreFaceG1(unittest.TestCase):
    """!
    Test face scoring for multisubject gallery 1 using sigsets.

    This class contains tests to compute verification and search scores for multisubject gallery 1 using face modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_face_multiprobe_gallery1(self):
        """!
        Test face verification scoring for multisubject gallery 1 using sigsets.
        """
        compute_verify(database_multi_probe_name, database_gallery_1_name, self.probe_multisubject_sigset_path, self.gallery_1_sigset_path, 'evaluation_multi_face_scores_g1.pkl', 'gallery_face_data_g1.csv', modality='face')

    def test_02_sigset_search_face_multiprobe_gallery1(self):
        """!
        Test face search scoring for multisubject gallery 1 using sigsets.
        """
        compute_search(database_multi_probe_name, database_gallery_1_name, self.probe_multisubject_sigset_path, 'evaluation_multi_face_search_g1.pkl', modality='face')


@unittest.skipIf(3.2 not in RUN_STAGES, 'Test 011 is not in the requested run stages')
class Test026MultiSigsetScoreWholeBodyG1(unittest.TestCase):
    """!
    Test whole body scoring for multisubject gallery 1 using sigsets.

    This class contains tests to compute verification and search scores for multisubject gallery 1 using whole body modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_WB_multiprobe_gallery1(self):
        """!
        Test whole body verification scoring for multisubject gallery 1 using sigsets.
        """
        compute_verify(database_multi_probe_name, database_gallery_1_name, self.probe_multisubject_sigset_path, self.gallery_1_sigset_path, 'evaluation_multi_wholebody_scores_g1.pkl', 'gallery_wholebody_data_g1.csv', modality='whole_body')

    def test_02_sigset_search_WB_multiprobe_gallery1(self):
        """!
        Test whole body search scoring for multisubject gallery 1 using sigsets.
        """
        compute_search(database_multi_probe_name, database_gallery_1_name, self.probe_multisubject_sigset_path, 'evaluation_multi_wholebody_search_g1.pkl', modality='whole_body')


@unittest.skipIf(3.21 not in RUN_STAGES, 'Test 006 is not in the requested run stages')
class Test027MultiSigsetScoreG2(unittest.TestCase):
    """!
    Test scoring for multisubject gallery 2 using sigsets.

    This class contains tests to compute verification and search scores for multisubject gallery 2 using sigsets.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_multiprobe_gallery2(self):
        """!
        Test verification scoring for multisubject gallery 2 using sigsets.
        """
        compute_verify(database_multi_probe_name, database_gallery_2_name, self.probe_multisubject_sigset_path, self.gallery_2_sigset_path, 'evaluation_multi_all_scores_g2.pkl', 'gallery_data_g2.csv')

    def test_02_sigset_search_multiprobe_gallery2(self):
        """!
        Test search scoring for multisubject gallery 2 using sigsets.
        """
        compute_search(database_multi_probe_name, database_gallery_2_name, self.probe_multisubject_sigset_path, 'evaluation_multi_all_search_g2.pkl')


@unittest.skipIf(3.22 not in RUN_STAGES, 'Test 008 is not in the requested run stages')
class Test028MultiSigsetScoreGaitG2(unittest.TestCase):
    """!
    Test gait scoring for multisubject gallery 2 using sigsets.

    This class contains tests to compute verification and search scores for multisubject gallery 2 using gait modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_gait_multiprobe_gallery2(self):
        """!
        Test gait verification scoring for multisubject gallery 2 using sigsets.
        """
        compute_verify(database_multi_probe_name, database_gallery_2_name, self.probe_multisubject_sigset_path, self.gallery_2_sigset_path, 'evaluation_multi_gait_scores_g2.pkl', 'gallery_gait_data_g2.csv', modality='gait')

    def test_02_sigset_search_gait_multiprobe_gallery2(self):
        """!
        Test gait search scoring for multisubject gallery 2 using sigsets.
        """
        compute_search(database_multi_probe_name, database_gallery_2_name, self.probe_multisubject_sigset_path, 'evaluation_multi_gait_search_g2.pkl', modality='gait')


@unittest.skipIf(3.23 not in RUN_STAGES, 'Test 009 is not in the requested run stages')
class Test029MultiSigsetScoreFaceG2(unittest.TestCase):
    """!
    Test face scoring for multisubject gallery 2 using sigsets.

    This class contains tests to compute verification and search scores for multisubject gallery 2 using face modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_face_multiprobe_gallery2(self):
        """!
        Test face verification scoring for multisubject gallery 2 using sigsets.
        """
        compute_verify(database_multi_probe_name, database_gallery_2_name, self.probe_multisubject_sigset_path, self.gallery_2_sigset_path, 'evaluation_multi_face_scores_g2.pkl', 'gallery_face_data_g2.csv', modality='face')

    def test_02_sigset_search_face_multiprobe_gallery2(self):
        """!
        Test face search scoring for multisubject gallery 2 using sigsets.
        """
        compute_search(database_multi_probe_name, database_gallery_2_name, self.probe_multisubject_sigset_path, 'evaluation_multi_face_search_g2.pkl', modality='face')


@unittest.skipIf(3.24 not in RUN_STAGES, 'Test 012 is not in the requested run stages')
class Test030MultiSigsetScoreWholeBodyG2(unittest.TestCase):
    """!
    Test whole body scoring for multisubject gallery 2 using sigsets.

    This class contains tests to compute verification and search scores for multisubject gallery 2 using whole body modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_WB_multiprobe_gallery2(self):
        """!
        Test whole body verification scoring for multisubject gallery 2 using sigsets.
        """
        compute_verify(database_multi_probe_name, database_gallery_2_name, self.probe_multisubject_sigset_path, self.gallery_2_sigset_path, 'evaluation_multi_wholebody_scores_g2.pkl', 'gallery_wholebody_data_g2.csv', modality='whole_body')

    def test_02_sigset_search_WB_multiprobe_gallery2(self):
        """!
        Test whole body search scoring for multisubject gallery 2 using sigsets.
        """
        compute_search(database_multi_probe_name, database_gallery_2_name, self.probe_multisubject_sigset_path, 'evaluation_multi_wholebody_search_g2.pkl', modality='whole_body')


@unittest.skipIf(3.25 not in RUN_STAGES, 'Test 005 is not in the requested run stages')
class Test031MultiSigsetBlendedScoreG1(unittest.TestCase):
    """!
    Test scoring for multisubject blended gallery 1 using sigsets.

    This class contains tests to compute verification and search scores for multisubject blended gallery 1 using sigsets.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_multiprobe_blended_gallery1(self):
        """!
        Test verification scoring for multisubject blended gallery 1 using sigsets.
        """
        compute_verify(database_multi_probe_name, database_blended_gallery_1_name, self.probe_multisubject_sigset_path, self.gallery_1_blended_sigset_path, 'evaluation_multi_all_scores_g1.pkl', 'gallery_data_g1.csv', blended=True)

    def test_02_sigset_search_multiprobe_blended_gallery1(self):
        """!
        Test search scoring for multisubject blended gallery 1 using sigsets.
        """
        compute_search(database_multi_probe_name, database_blended_gallery_1_name, self.probe_multisubject_sigset_path, 'evaluation_multi_all_search_g1.pkl', blended=True)


@unittest.skipIf(3.26 not in RUN_STAGES, 'Test 008 is not in the requested run stages')
class Test032MultiSigsetScoreBlendedGaitG1(unittest.TestCase):
    """!
    Test gait scoring for multisubject blended gallery 1 using sigsets.

    This class contains tests to compute verification and search scores for multisubject blended gallery 1 using gait modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_gait_multiprobe_blended_gallery1(self):
        """!
        Test gait verification scoring for multisubject blended gallery 1 using sigsets.
        """
        compute_verify(database_multi_probe_name, database_blended_gallery_1_name, self.probe_multisubject_sigset_path, self.gallery_1_blended_sigset_path, 'evaluation_multi_gait_scores_g1.pkl', 'gallery_gait_data_g1.csv', modality='gait', blended=True)

    def test_02_sigset_search_gait_multiprobe_blended_gallery1(self):
        """!
        Test gait search scoring for multisubject blended gallery 1 using sigsets.
        """
        compute_search(database_multi_probe_name, database_blended_gallery_1_name, self.probe_multisubject_sigset_path, 'evaluation_multi_gait_search_g1.pkl', modality='gait', blended=True)


@unittest.skipIf(3.27 not in RUN_STAGES, 'Test 009 is not in the requested run stages')
class Test033MultiSigsetScoreBlendedFaceG1(unittest.TestCase):
    """!
    Test face scoring for multisubject blended gallery 1 using sigsets.

    This class contains tests to compute verification and search scores for multisubject blended gallery 1 using face modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_face_multiprobe_blended_gallery1(self):
        """!
        Test face verification scoring for multisubject blended gallery 1 using sigsets.
        """
        compute_verify(database_multi_probe_name, database_blended_gallery_1_name, self.probe_multisubject_sigset_path, self.gallery_1_blended_sigset_path, 'evaluation_multi_face_scores_g1.pkl', 'gallery_face_data_g1.csv', modality='face', blended=True)

    def test_02_sigset_search_face_multiprobe_blended_gallery1(self):
        """!
        Test face search scoring for multisubject blended gallery 1 using sigsets.
        """
        compute_search(database_multi_probe_name, database_blended_gallery_1_name, self.probe_multisubject_sigset_path, 'evaluation_multi_face_search_g1.pkl', modality='face', blended=True)


@unittest.skipIf(3.28 not in RUN_STAGES, 'Test 011 is not in the requested run stages')
class Test034MultiSigsetScoreBlendedWholeBodyG1(unittest.TestCase):
    """!
    Test whole body scoring for multisubject blended gallery 1 using sigsets.

    This class contains tests to compute verification and search scores for multisubject blended gallery 1 using whole body modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_WB_multiprobe_blended_gallery1(self):
        """!
        Test whole body verification scoring for multisubject blended gallery 1 using sigsets.
        """
        compute_verify(database_multi_probe_name, database_blended_gallery_1_name, self.probe_multisubject_sigset_path, self.gallery_1_blended_sigset_path, 'evaluation_multi_wholebody_scores_g1.pkl', 'gallery_wholebody_data_g1.csv', modality='whole_body', blended=True)

    def test_02_sigset_search_WB_multiprobe_blended_gallery1(self):
        """!
        Test whole body search scoring for multisubject blended gallery 1 using sigsets.
        """
        compute_search(database_multi_probe_name, database_blended_gallery_1_name, self.probe_multisubject_sigset_path, 'evaluation_multi_wholebody_search_g1.pkl', modality='whole_body', blended=True)


@unittest.skipIf(3.29 not in RUN_STAGES, 'Test 006 is not in the requested run stages')
class Test035MultiSigsetBlendedScoreG2(unittest.TestCase):
    """!
    Test scoring for multisubject blended gallery 2 using sigsets.

    This class contains tests to compute verification and search scores for multisubject blended gallery 2 using sigsets.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_multiprobe_blended_gallery2(self):
        """!
        Test verification scoring for multisubject blended gallery 2 using sigsets.
        """
        compute_verify(database_multi_probe_name, database_blended_gallery_2_name, self.probe_multisubject_sigset_path, self.gallery_2_blended_sigset_path, 'evaluation_multi_all_scores_g2.pkl', 'gallery_data_g2.csv', blended=True)

    def test_02_sigset_search_multiprobe_blended_gallery2(self):
        """!
        Test search scoring for multisubject blended gallery 2 using sigsets.
        """
        compute_search(database_multi_probe_name, database_blended_gallery_2_name, self.probe_multisubject_sigset_path, 'evaluation_multi_all_search_g2.pkl', blended=True)


@unittest.skipIf(3.3 not in RUN_STAGES, 'Test 007 is not in the requested run stages')
class Test036MultiSigsetScoreBlendedGaitG2(unittest.TestCase):
    """!
    Test gait scoring for multisubject blended gallery 2 using sigsets.

    This class contains tests to compute verification and search scores for multisubject blended gallery 2 using gait modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_gait_multiprobe_blended_gallery2(self):
        """!
        Test gait verification scoring for multisubject blended gallery 2 using sigsets.
        """
        compute_verify(database_multi_probe_name, database_blended_gallery_2_name, self.probe_multisubject_sigset_path, self.gallery_2_blended_sigset_path, 'evaluation_multi_gait_scores_g2.pkl', 'gallery_gait_data_g2.csv', modality='gait', blended=True)

    def test_02_sigset_search_gait_multiprobe_blended_gallery2(self):
        """!
        Test gait search scoring for multisubject blended gallery 2 using sigsets.
        """
        compute_search(database_multi_probe_name, database_blended_gallery_2_name, self.probe_multisubject_sigset_path, 'evaluation_multi_gait_search_g2.pkl', modality='gait', blended=True)


@unittest.skipIf(3.31 not in RUN_STAGES, 'Test 010 is not in the requested run stages')
class Test037MultiSigsetScoreBlendedFaceG2(unittest.TestCase):
    """!
    Test face scoring for multisubject blended gallery 2 using sigsets.

    This class contains tests to compute verification and search scores for multisubject blended gallery 2 using face modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_face_multiprobe_blended_gallery2(self):
        """!
        Test face verification scoring for multisubject blended gallery 2 using sigsets.
        """
        compute_verify(database_multi_probe_name, database_blended_gallery_2_name, self.probe_multisubject_sigset_path, self.gallery_2_blended_sigset_path, 'evaluation_multi_face_scores_g2.pkl', 'gallery_face_data_g2.csv', modality='face', blended=True)

    def test_02_sigset_search_face_multiprobe_blended_gallery2(self):
        """!
        Test face search scoring for multisubject blended gallery 2 using sigsets.
        """
        compute_search(database_multi_probe_name, database_blended_gallery_2_name, self.probe_multisubject_sigset_path, 'evaluation_multi_face_search_g2.pkl', modality='face', blended=True)


@unittest.skipIf(3.32 not in RUN_STAGES, 'Test 012 is not in the requested run stages')
class Test038MultiSigsetScoreBlendedWholeBodyG2(unittest.TestCase):
    """!
    Test whole body scoring for multisubject blended gallery 2 using sigsets.

    This class contains tests to compute verification and search scores for multisubject blended gallery 2 using whole body modality.
    """

    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def test_01_sigset_verify_WB_multiprobe_blended_gallery2(self):
        """!
        Test whole body verification scoring for multisubject blended gallery 2 using sigsets.
        """
        compute_verify(database_multi_probe_name, database_blended_gallery_2_name, self.probe_multisubject_sigset_path, self.gallery_2_blended_sigset_path, 'evaluation_multi_wholebody_scores_g2.pkl', 'gallery_wholebody_data_g2.csv', modality='whole_body', blended=True)

    def test_02_sigset_search_WB_multiprobe_blended_gallery2(self):
        """!
        Test whole body search scoring for multisubject blended gallery 2 using sigsets.
        """
        compute_search(database_multi_probe_name, database_blended_gallery_2_name, self.probe_multisubject_sigset_path, 'evaluation_multi_wholebody_search_g2.pkl', modality='whole_body', blended=True)


@unittest.skipIf(3 not in RUN_STAGES, 'Test 013 is not in the requested run stages')
class Test023SigsetSearchOutputFormatting(unittest.TestCase):
    """!
    Test output formatting for search results.

    This class contains tests to check the output formatting of search results for various modalities and galleries.
    """

    @unittest.skipIf(3.01 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_01_sigset_search_pickle_fileG1(self):
        """!
        Test search output formatting for gallery 1.
        """
        self.search_file_check(blended=False, galnumber=1)

    @unittest.skipIf(3.02 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_02_sigset_search_gait_pickle_fileG1(self):
        """!
        Test search output formatting for gallery 1 using gait modality.
        """
        self.search_file_check('gait', blended=False, galnumber=1)

    @unittest.skipIf(3.03 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_03_sigset_search_face_pickle_fileG1(self):
        """!
        Test search output formatting for gallery 1 using face modality.
        """
        self.search_file_check('face', blended=False, galnumber=1)

    @unittest.skipIf(3.04 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_04_sigset_search_wb_pickle_fileG1(self):
        """!
        Test search output formatting for gallery 1 using whole body modality.
        """
        self.search_file_check('wholebody', blended=False, galnumber=1)

    @unittest.skipIf(3.05 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_05_sigset_search_pickle_fileG2(self):
        """!
        Test search output formatting for gallery 2.
        """
        self.search_file_check(blended=False, galnumber=2)

    @unittest.skipIf(3.06 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_06_sigset_search_gait_pickle_fileG2(self):
        """!
        Test search output formatting for gallery 2 using gait modality.
        """
        self.search_file_check('gait', blended=False, galnumber=2)

    @unittest.skipIf(3.07 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_07_sigset_search_face_pickle_fileG2(self):
        """!
        Test search output formatting for gallery 2 using face modality.
        """
        self.search_file_check('face', blended=False, galnumber=2)

    @unittest.skipIf(3.08 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_08_sigset_search_wb_pickle_fileG2(self):
        """!
        Test search output formatting for gallery 2 using whole body modality.
        """
        self.search_file_check('wholebody', blended=False, galnumber=2)

    @unittest.skipIf(3.09 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_09_sigset_blended_search_pickle_fileG1(self):
        """!
        Test search output formatting for blended gallery 1.
        """
        self.search_file_check(blended=True, galnumber=1)

    @unittest.skipIf(3.1 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_10_sigset_blended_search_gait_pickle_fileG1(self):
        """!
        Test search output formatting for blended gallery 1 using gait modality.
        """
        self.search_file_check('gait', blended=True, galnumber=1)

    @unittest.skipIf(3.11 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_11_sigset_blended_search_face_pickle_fileG1(self):
        """!
        Test search output formatting for blended gallery 1 using face modality.
        """
        self.search_file_check('face', blended=True, galnumber=1)

    @unittest.skipIf(3.12 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_12_sigset_blended_search_wb_pickle_fileG1(self):
        """!
        Test search output formatting for blended gallery 1 using whole body modality.
        """
        self.search_file_check('wholebody', blended=True, galnumber=1)

    @unittest.skipIf(3.13 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_13_sigset_blended_search_pickle_fileG2(self):
        """!
        Test search output formatting for blended gallery 2.
        """
        self.search_file_check(blended=True, galnumber=2)

    @unittest.skipIf(3.14 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_14_sigset_blended_search_gait_pickle_fileG2(self):
        """!
        Test search output formatting for blended gallery 2 using gait modality.
        """
        self.search_file_check('gait', blended=True, galnumber=2)

    @unittest.skipIf(3.15 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_15_sigset_blended_search_face_pickle_fileG2(self):
        """!
        Test search output formatting for blended gallery 2 using face modality.
        """
        self.search_file_check('face', blended=True, galnumber=2)

    @unittest.skipIf(3.16 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_16_sigset_blended_search_wb_pickle_fileG2(self):
        """!
        Test search output formatting for blended gallery 2 using whole body modality.
        """
        self.search_file_check('wholebody', blended=True, galnumber=2)

    def search_file_check(self, modality='', blended=False, galnumber=1):
        """!
        Check the output formatting of search results.

        This function checks the output formatting of search results for a specified modality and gallery.

        @param modality str: The modality to check (optional).
        @param blended bool: Whether to check blended galleries (optional).
        @param galnumber int: The gallery number to check.
        """
        if len(modality) > 0:
            modality = '_' + modality
        else:
            modality = '_all'
        if blended:
            outdir = os.path.join(OUTPUT_DIR, 'blended')
        else:
            outdir = os.path.join(OUTPUT_DIR, 'simple')
        search_file1 = os.path.join(outdir, 'evaluation' + modality + '_search_g' + str(galnumber) + '.pkl')
        self.assertTrue(os.path.exists(search_file1), search_file1 + ' does not exist')
        self.assertTrue(os.path.isfile(search_file1), search_file1 + ' is not a file')


@unittest.skipIf(3 not in RUN_STAGES, 'Test 014 is not in the requested run stages')
class Test024SigsetVerifyOutputFormatting(unittest.TestCase):
    """!
    Test output formatting for verification results.

    This class contains tests to check the output formatting of verification results for various modalities and galleries.
    """

    @unittest.skipIf(3.01 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_01_sigset_verify_pickle_fileG1(self):
        """!
        Test verification output formatting for gallery 1.
        """
        self.score_file_check(blended=False, galnumber=1)

    @unittest.skipIf(3.02 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_02_sigset_verify_gait_pickle_fileG1(self):
        """!
        Test verification output formatting for gallery 1 using gait modality.
        """
        self.score_file_check('gait', blended=False, galnumber=1)

    @unittest.skipIf(3.03 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_03_sigset_verify_face_pickle_fileG1(self):
        """!
        Test verification output formatting for gallery 1 using face modality.
        """
        self.score_file_check('face', blended=False, galnumber=1)

    @unittest.skipIf(3.04 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_04_sigset_verify_wb_pickle_fileG1(self):
        """!
        Test verification output formatting for gallery 1 using whole body modality.
        """
        self.score_file_check('wholebody', blended=False, galnumber=1)

    @unittest.skipIf(3.05 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_05_sigset_verify_pickle_fileG2(self):
        """!
        Test verification output formatting for gallery 2.
        """
        self.score_file_check(blended=False, galnumber=2)

    @unittest.skipIf(3.06 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_06_sigset_verify_gait_pickle_fileG2(self):
        """!
        Test verification output formatting for gallery 2 using gait modality.
        """
        self.score_file_check('gait', blended=False, galnumber=2)

    @unittest.skipIf(3.07 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_07_sigset_verify_face_pickle_fileG2(self):
        """!
        Test verification output formatting for gallery 2 using face modality.
        """
        self.score_file_check('face', blended=False, galnumber=2)

    @unittest.skipIf(3.08 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_08_sigset_verify_wb_pickle_fileG2(self):
        """!
        Test verification output formatting for gallery 2 using whole body modality.
        """
        self.score_file_check('wholebody', blended=False, galnumber=2)

    @unittest.skipIf(3.09 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_09_sigset_blended_verify_pickle_fileG1(self):
        """!
        Test verification output formatting for blended gallery 1.
        """
        self.score_file_check(blended=True, galnumber=1)

    @unittest.skipIf(3.1 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_10_sigset_blended_verify_gait_pickle_fileG1(self):
        """!
        Test verification output formatting for blended gallery 1 using gait modality.
        """
        self.score_file_check('gait', blended=True, galnumber=1)

    @unittest.skipIf(3.11 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_11_sigset_blended_verify_face_pickle_fileG1(self):
        """!
        Test verification output formatting for blended gallery 1 using face modality.
        """
        self.score_file_check('face', blended=True, galnumber=1)

    @unittest.skipIf(3.12 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_12_sigset_blended_verify_wb_pickle_fileG1(self):
        """!
        Test verification output formatting for blended gallery 1 using whole body modality.
        """
        self.score_file_check('wholebody', blended=True, galnumber=1)

    @unittest.skipIf(3.13 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_13_sigset_blended_verify_pickle_fileG2(self):
        """!
        Test verification output formatting for blended gallery 2.
        """
        self.score_file_check(blended=True, galnumber=2)

    @unittest.skipIf(3.14 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_14_sigset_blended_verify_gait_pickle_fileG2(self):
        """!
        Test verification output formatting for blended gallery 2 using gait modality.
        """
        self.score_file_check('gait', blended=True, galnumber=2)

    @unittest.skipIf(3.15 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_15_sigset_blended_verify_face_pickle_fileG2(self):
        """!
        Test verification output formatting for blended gallery 2 using face modality.
        """
        self.score_file_check('face', blended=True, galnumber=2)

    @unittest.skipIf(3.16 not in RUN_STAGES, 'Test is not in the requested run stages')
    def test_16_sigset_blended_verify_wb_pickle_fileG2(self):
        """!
        Test verification output formatting for blended gallery 2 using whole body modality.
        """
        self.score_file_check('wholebody', blended=True, galnumber=2)

    def score_file_check(self, modality='', blended=False, galnumber=1):
        """!
        Check the output formatting of verification results.

        This function checks the output formatting of verification results for a specified modality and gallery.

        @param modality str: The modality to check (optional).
        @param blended bool: Whether to check blended galleries (optional).
        @param galnumber int: The gallery number to check.
        """
        if len(modality) > 0:
            modality = '_' + modality
        else:
            modality = '_all'
        if blended:
            outdir = os.path.join(OUTPUT_DIR, 'blended')
        else:
            outdir = os.path.join(OUTPUT_DIR, 'simple')
        score_file1 = os.path.join(outdir, 'evaluation' + modality + '_scores_g' + str(galnumber) + '.pkl')
        self.assertTrue(os.path.exists(score_file1), score_file1 + ' does not exist')
        self.assertTrue(os.path.isfile(score_file1), score_file1 + ' is not a file')


def runall():
    """!
    Run all tests.
    """
    unittest.main()


if __name__ == '__main__':
    import sys
    print(sys.argv)
    generate_report = os.environ.get('REPORT', False)

    if generate_report:
        from briar.tests.ReportGenerator import main
        main(module=briar.evaluation.full_evaluation)
    else:
        unittest.main()
