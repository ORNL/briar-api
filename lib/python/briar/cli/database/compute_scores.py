import asyncio
import briar
import briar.briar_client as briar_client
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as briar_service_pb2
import briar.grpc_json
import json
import numpy as np
import optparse
import os
import pickle as pkl
import re
import sys
import time
from briar.cli.connection import addConnectionOptions
from briar.cli.search import MATCHES_FILE_EXT
from briar.cli.media import addMediaOptions
from briar.cli.verify import verifyParseOptions, verify_options2proto, addVerifyOptions, VERIFICATION_FILE_EXT
from briar.media_converters import modality_proto2string, subjectID_int2str, subjectList_string2list,subjectList_list2string
from briar.sigset.parse import parseBriarSigset
from tqdm import tqdm

def addDatabaseComputeScoreOptions(parser):
    """!
    Add options for search of a database using a database.

    @param parser optparse.OptionParser: A parser to modify in place by adding options
    """

    search_group = optparse.OptionGroup(parser, "Search Databases Options",
                                        "Configuration for database-against-database search.")

    search_group.add_option("-o", "--out-dir", type="str", dest="out_dir", default=None,
                            help="Save the search results.")
    output_type_choices = ['pickle', 'briar', 'numpy', 'pandas', 'xml']
    search_group.add_option("--output-type", type="choice", choices=output_type_choices, dest="output_type",
                            default="briar",
                            help="Choose an output type for saving results. Options: " + ",".join(
                                output_type_choices) + " Default=briar")

    search_group.add_option("--search-database", type="str", dest="search_database", default=None,
                            help="Select the database to search.")
    search_group.add_option("--probe-database", type="str", dest="probe_database", default=None,
                            help="Database to use as a probe set")
    search_group.add_option("--max-results", type="int", dest="max_results", default=-1,
                            help="Set the maximum number of search results returned for each face. If negative, search will return search scores for ALL gallery entries")

    search_group.add_option("--return-media", action="store_true", dest="return_media", default=False,
                            help="Enables returning of media from workers to the client - will significantly increase output file sizes!")
    search_group.add_option("-m", "--modality", type="choice", choices=['unspecified', 'whole_body', 'face', 'gait','all'],
                            dest="modality",
                            default="all",
                            help="Choose a biometric modality. Default=face")


    parser.add_option_group(search_group)


def addDatabaseComputeScore_options2proto(options):
    '''
    Parse command line options and populate a proto object for grpc
    '''

    search_options = briar_pb2.SearchOptions()
    val = options.out_dir
    if val is not None:
        search_options.out_dir.value = options.out_dir
    val = options.output_type
    if val is not None:
        search_options.output_type.value = options.output_type
    val = options.search_database
    if val is not None:
        search_options.search_database.value = options.search_database
    val = options.probe_database
    if val is not None:
        search_options.probe_database.value = options.probe_database
    val = options.modality
    if val is not None:
        val = briar.media_converters.modality_string2proto(val)
        search_options.modality = val
    # val = options.probe_database
    # if val is not None:
    #     search_options.search_database.value = options.search_database
    val = options.max_results
    if val is not None:
        search_options.max_results.value = val
    val = options.return_media
    if val is not None:
        search_options.return_media.value = val
    search_options.full.value = False
    return search_options

def parseDatabaseComputeScoreOptions(inputCommand=None):
    """!
    Generate options for matching databases against other databases, and parse command line arguments into the API call.

    @return: 2 element Tuple of (optparse.Values, list) containing the parsed options and parameters respectively
    """
    args = ['gallery_database_name', 'probe_database_name']  # Add the names of arguments here.
    n_args = len(args)
    args = " ".join(args)
    description = "Run a 1:N search against a database. Input a probe entry" + \
                  " and finds the top matches in a gallery database."
    epilog = '''Created by David Bolme (bolmeds@ornl.gov) and Joel Brogan (broganjr@ornl.gov)'''

    version = briar.__version__

    # Setup the parser
    parser = optparse.OptionParser(usage='%s search [OPTIONS] %s' % ('python -m briar', args),
                                   version=version, description=description, epilog=epilog, conflict_handler="resolve")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Print out more program information.")
    parser.add_option("--no-save", action="store_true", dest="no_save", default=False,
                      help="Disables saving of results on the client-side")
    parser.add_option("--single-subject", action="store_true", dest="single_subject", default=False,
                      help="Ensures single-subject ouptuts are pickled. Must be set to True for compatibility with Phase 1 report card")
    parser.add_option("--return-entry-id", action="store_true", dest="return_entry_id", default=False,
                      help="Makes the API return full probe entry IDs instead of just subject IDs for each probe. Must be unset or set to False to when requiring compatibility with Phase 1 report cards")
    parser.add_option("--probe-order-list", type="str", dest="order_list", default=None,
                      help="Sigset XML file to use as the ordering of result output")


    addDatabaseComputeScoreOptions(parser)
    addConnectionOptions(parser)
    addMediaOptions(parser)
    # if options.database is None:
    #    print("ERROR: --database option needs to be defined")
    #    exit(-1)

    # Parse the arguments and return the results.
    if inputCommand is not None:
        import shlex
        inp = shlex.split(inputCommand)
        (options, args) = parser.parse_args(inp)
    else:
        (options, args) = parser.parse_args()

    if len(args) < n_args + 2:
        if options.probe_database is None and options.search_database is None:
            parser.print_help()
            print("\n"
                  "Please supply at least {} arguments.\n"
                  "\n".format(n_args))
            exit(-1)

    return options, args




def database_compute_verify(options=None, args=None,input_command=None,ret=False):
    """!
    Using the options specified in the command line, runs a batch verification betweeen the specified databases using specified
    probe database. Writes results to disk to a location specified by the cmd arguments

    @return: No return - Function writes results to disk
    """
    api_start = time.time()
    if options is None and args is None:
        options, args = verifyParseOptions(inputCommand=input_command)
    client = briar_client.BriarClient(options)

    # Check the status
    # print("*" * 35, 'STATUS', "*" * 35)
    # print(client.get_status())
    # print("*" * 78)

    verify_options = verify_options2proto(options)

    if options.verbose:
        print("Scanning directories for images and videos.")
    image_list = None
    video_list = None
    search_database_flag = False
    if options.reference_database:
        database = options.reference_database
        search_database_flag = True
    else:
        options.reference_database = args[2]
        database = args[3]

    image_count = 0

    if options.verify_database is not None:
        verify_database = options.verify_database
    elif len(args) > 2:
        options.verify_database = args[3]
        verify_database = args[3]

    if options.verify_database is not None:
        filename = None

        if not options.out_dir:
            out_dir = './'
        else:
            out_dir = options.out_dir
            out_dir_fname = os.path.basename(out_dir)
            if not out_dir_fname == '':
                if '.' in out_dir_fname:
                    filename = out_dir_fname
                    out_dir = os.path.dirname(out_dir)
                    if out_dir == '':
                        out_dir = './'
            os.makedirs(out_dir, exist_ok=True)
        verifyRequest = briar_service_pb2.VerifyDatabaseRequest(
            reference_database=briar_pb2.BriarDatabase(name=database), verify_options=verify_options,
            verify_database=briar_pb2.BriarDatabase(name=verify_database))
        verifyReply = client.stub.database_compute_verify(verifyRequest)
        if filename is None:
            filename = database + "_" + verify_database
        if options.plot:
            from briar.media import visualize
            match_visualizer = visualize.match_matrix_visualizer(verifyReply, options.verify_database,
                                                                 options.reference_database)
            match_visualizer.showmat_interactive()

        if options.output_type == 'pickle' or options.output_type == 'pkl':

            # matches_name = os.path.splitext(os.path.basename(filename))[0] + '_verification.pkl'
            matches_name = os.path.basename(filename)

            matches_path = os.path.join(out_dir, matches_name)
            outputlist = []
            matrix = briar.media_converters.matrix_proto2np(verifyReply.match_matrix)
            matrix_width = matrix.shape[1]
            probe_counts = []
            if options.verify_order_list:
                print("parsing Sigset XML", os.path.basename(options.verify_order_list),
                      ' for probe result ordering...')
                from briar.sigset import parse
                import pandas
                csvname = options.verify_order_list + '.csv'
                # if os.path.exists(csvname):
                #     probe_sigset = pandas.read_csv(csvname)
                # else:
                probe_sigset = parseBriarSigset(options.verify_order_list)
                probe_order =  probe_sigset['entryId']
                newmatrix_sortedprobes = []
                matrix_probe_order = list(verifyReply.match_matrix.row_headers)
                missing_probes = []
                # print('probe order:',probe_order)
                # print('matrix_probe_order:',matrix_probe_order)
                for probeid in probe_order:
                    if probeid in matrix_probe_order:
                        index = -1
                        # loop through the matrix_probe_order to find all indexes pertaining to the probeid
                        probe_bin = []
                        while True:
                            try:
                                index = matrix_probe_order.index(probeid, index + 1)
                                probe_bin.append(matrix[index])
                            except ValueError:
                                break
                        if len(probe_bin) > 0:
                            if len(probe_bin) > 1:
                                probe_bin_np = np.vstack(probe_bin)
                                if options.single_subject:
                                    newmatrix_sortedprobes.append(np.nanmax(probe_bin_np,axis=0)) #taking the column-wise max of all rows for a given probe

                                else:
                                    newmatrix_sortedprobes.extend(probe_bin)
                            else:
                                newmatrix_sortedprobes.append(probe_bin[0])
                            probe_counts.append(len(probe_bin))
                        else:
                            emptyrow = np.empty(matrix_width)
                            emptyrow[:] = np.nan
                            newmatrix_sortedprobes.append(emptyrow)
                            missing_probes.append(probeid)
                            probe_counts.append(0)
                        # newmatrix_sortedprobes.append(matrix[matrix_probe_order.index(probeid)])
                    else:
                        emptyrow = np.empty(matrix_width)
                        emptyrow[:] = np.nan
                        newmatrix_sortedprobes.append(emptyrow)
                        missing_probes.append(probeid)
                        probe_counts.append(0)
                matrix = np.vstack(newmatrix_sortedprobes)

                if len(missing_probes) > 0:
                    print('WARNING: Verification database', verify_database, ' did not contain ', len(missing_probes),
                          'entries indicated by the sigset.')
                    print('To see them, run with the -v flag')
                    if options.verbose:
                        print('Missing Probe Entries:')
                        print(missing_probes)
            gallery_order = None
            if options.reference_order_list:
                print("parsing Sigset XML", os.path.basename(options.reference_order_list),
                      ' for reference result ordering...')
                from briar.sigset import parse
                # import pandas
                # csvname = options.reference_order_list + '.csv'
                # if os.path.exists(csvname):
                #     gallery_sigset = pandas.read_csv(csvname)
                # else:
                gallery_sigset = parseBriarSigset(options.reference_order_list)
                gallery_order_all = [subjectList_list2string(sl) for sl in list(gallery_sigset['subjectId'])]
                gallery_subids, gallery_subid_indexes = np.unique(gallery_order_all, return_index=True)
                gallery_order = gallery_subids[
                    gallery_subid_indexes.argsort()]  # this returns the unique subject ids that the gallery should be ordered in
                newmatrix_sortedgallery = []
                matrix_gallery_order = list(verifyReply.match_matrix.column_headers)

                if verifyReply.uses_integer_subject_id_gallery:
                    integer_matrix_gallery_order = list(verifyReply.match_matrix.column_headers_integer)
                    matrix_gallery_order = []
                    for gid in integer_matrix_gallery_order:
                        matrix_gallery_order.append(subjectID_int2str(gid))

                # output_subids.append(subject_id_gallery)
                missing_gallery = []
                missing_probes = []
                for gallid in gallery_order:
                    if gallid in matrix_gallery_order:
                        newmatrix_sortedgallery.append(matrix.T[matrix_gallery_order.index(gallid)])
                    else:
                        missing_gallery.append(gallid)
                matrix = np.vstack(newmatrix_sortedgallery).T

                if len(missing_gallery) > 0:
                    print('WARNING: Reference database', database, ' did not contain ', len(missing_gallery),
                          'entries indicated by the sigset.')
                    print('To see them, run with the -v flag')
                    if options.verbose:
                        print('Missing Reference Entries:')
                        print(missing_gallery)

            print('writing pkl file to', matches_path)
            with open(matches_path, 'wb') as fp:
                pkl.dump(matrix, fp)
            mpath_root,mpath_ext = os.path.splitext(matches_path)
            with open(mpath_root+'_probe_counts.csv', 'w') as fp:
                fp.write('\n'.join([str(p) for p in probe_counts]))
            if options.gallery_data_filename is not None and gallery_order is not None:
                gallerycsv_filepath = os.path.join(out_dir, options.gallery_data_filename)
                gallerycsv = "gallery_id,sub_id\n"
                gallerycsv = gallerycsv + "\n".join([",".join(s) for s in zip(gallery_order, gallery_order)])
                with open(gallerycsv_filepath, 'w') as fp:
                    fp.write(gallerycsv)
        if options.output_type == "briar":
            matches_name = os.path.splitext(os.path.basename(filename))[0] + MATCHES_FILE_EXT
            matches_path = os.path.join(out_dir, matches_name)
            briar.grpc_json.save(verifyReply, matches_path)
