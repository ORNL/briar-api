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
from briar.cli.database.compute_scores import parseDatabaseComputeScoreOptions, addDatabaseComputeScore_options2proto

def database_compute_search(options=None, args=None,input_command=None,ret=False):
    """!
    Using the options specified in the command line, runs a search within the specified database using specified
    probe database. Writes results to disk to a location specified by the cmd arguments

    @return: No return - Function writes results to disk
    """
    api_start = time.time()

    if options is None and args is None:
        options, args = parseDatabaseComputeScoreOptions(inputCommand=input_command)
    client = briar_client.BriarClient(options)

    # Check the status
    # print("*" * 35, 'STATUS', "*" * 35)
    # print(client.get_status())
    # print("*" * 78)

    search_options = addDatabaseComputeScore_options2proto(options)

    if options.verbose:
        print("Scanning directories for images and videos.")
    image_list = None
    video_list = None
    search_database_flag = False
    if options.search_database:
        database = options.search_database
        search_database_flag = True
    else:
        options.search_database = args[2]
        database = args[2]

    image_count = 0

    if options.probe_database is not None:
        probe_database = options.probe_database
    elif len(args) > 2:
        options.probe_database = args[3]
        probe_database = args[3]
    if options.probe_database is not None:
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
        searchRequest = briar_service_pb2.SearchDatabaseRequest(database=briar_pb2.BriarDatabase(name=database),
                                                                search_options=search_options,
                                                                probe_database=briar_pb2.BriarDatabase(
                                                                    name=probe_database))
        all_search_replies_matchlists = []
        all_search_durations = []
        all_search_probe_media_ids = []
        for streamed_searchReply in tqdm(client.stub.database_compute_search(searchRequest)):
            all_search_replies_matchlists.extend(streamed_searchReply.similarities)
            all_search_durations.append(streamed_searchReply.durations)
            all_search_probe_media_ids.extend([])
        searchReply = briar_service_pb2.SearchDatabaseReply(similarities=all_search_replies_matchlists)

        # searchReply = client.stub.database_compute_search(searchRequest)
        if filename is None:
            filename = database + "_" + probe_database

        # print(searchReply)
        if options.output_type == 'pickle' or options.output_type == 'pkl':
            # matches_name = os.path.splitext(os.path.basename(filename))[0] #+ '_search.pkl'
            matches_name = os.path.basename(filename)
            matches_path = os.path.join(out_dir, matches_name)
            outputlist = []
            probe_counts_withid = {}
            if options.order_list is not None:
                outputlist = {}
            for matchlist in searchReply.similarities:
                output_subids = []
                output_scores = []
                subject_id_probe = None
                entry_id_probe = None
                for matchInfo in matchlist.match_list:
                    subject_id_probe = matchInfo.subject_id_probe
                    entry_id_probe = matchInfo.entry_id_probe
                    entry_id_gallery = matchInfo.entry_id_gallery

                    if matchInfo.uses_integer_subject_id_gallery:
                        subject_id_gallery = subjectID_int2str(matchInfo.integer_subject_id_gallery)
                    else:
                        subject_id_gallery = matchInfo.subject_id_gallery
                    output_subids.append(subject_id_gallery)
                    output_scores.append(matchInfo.score)
                output_scores = np.array(output_scores)
                if entry_id_probe not in probe_counts_withid:
                    probe_counts_withid[entry_id_probe] = 0
                probe_counts_withid[entry_id_probe] += 1
                if isinstance(outputlist, list):
                    if options.return_entry_id:
                        outputlist.append([entry_id_probe, output_subids, output_scores])
                    else:
                        outputlist.append([subject_id_probe, output_subids, output_scores])
                elif isinstance(outputlist, dict):
                    if entry_id_probe not in outputlist:
                        outputlist[
                            entry_id_probe] = []  # because multiple search outputs for mulitple subjects within a probe can be generated, we store a list of match results per probe entry_id
                    if options.return_entry_id:
                        outputlist[entry_id_probe].append([entry_id_probe, output_subids, output_scores])
                    else:
                        outputlist[entry_id_probe].append([subject_id_probe, output_subids, output_scores])
            probe_counts = []
            if options.order_list:
                new_outputlist = []
                print("parsing Sigset XML", os.path.basename(options.order_list), ' for result ordering...')
                from briar.sigset import parse
                import pandas
                csvname = options.order_list + '.csv'
                # if os.path.exists(csvname):
                #     probe_sigset = pandas.read_csv(csvname)
                # else:
                probe_sigset = parseBriarSigset(options.order_list)
                probe_order = list(probe_sigset['entryId'])
                # probe_order_subject = list(probe_sigset['subjectId'])
                bad_probes = []
                output_entry_ids_list = []

                for entry_id in probe_order:
                    if entry_id in outputlist:
                        if options.single_subject: #We want to keep the results with only the highest scores, to conform to the single-subject output required by phase 0 and phase 1 scores.
                            if len(outputlist[entry_id]) > 1:
                                all_gal_results = []
                                all_gal_result_scores = []
                                #this will take all search results for a single probe and concatenate them, then reduce them down to a single set of results.
                                for r in outputlist[entry_id]:
                                    all_gal_results.extend(r[1])
                                    all_gal_result_scores.extend(r[2])
                                all_gal_result_scores = np.array(all_gal_result_scores)
                                all_gal_results = np.array(all_gal_results)

                                all_gall_results_sorted_inds = np.argsort(all_gal_result_scores)[::-1]
                                all_gall_results_sorted = all_gal_results[all_gall_results_sorted_inds]
                                all_gal_result_scores_sorted = all_gal_result_scores[all_gall_results_sorted_inds]
                                unq,inds = np.unique(all_gall_results_sorted,return_index=True)
                                all_gall_results_sorted_reduced = all_gall_results_sorted[sorted(inds)]
                                all_gal_result_scores_sorted_reduced = all_gal_result_scores_sorted[sorted(inds)]
                                new_outputlist.append([r[0],all_gall_results_sorted_reduced,all_gal_result_scores_sorted_reduced])

                                # max_result_ind = np.nanargmax(np.array([max(r[2]) for r in outputlist[entry_id]]))
                                # new_outputlist.append(outputlist[entry_id][max_result_ind])
                            # elif len(outputlist[entry_id]) == 1:
                            #     new_outputlist.append([outputlist[entry_id][0][0], outputlist[entry_id]])
                            else:
                                new_outputlist.append(outputlist[entry_id][0])
                            output_entry_ids_list.append(entry_id)
                        else:
                            new_outputlist.extend(outputlist[entry_id])
                            output_entry_ids_list.extend([entry_id]*len(outputlist[entry_id]))
                        probe_counts.append(len(outputlist[entry_id]))
                    else:
                        if options.return_entry_id:
                            new_outputlist.append([entry_id, [], []])
                        else:
                            new_outputlist.append([subjectId, [], []])
                        probe_counts.append(0)
                        output_entry_ids_list.append(entry_id)
                        bad_probes.append(entry_id)
                if len(bad_probes) > 0:
                    print('WARNING: The probe database used for database search did not contain', len(bad_probes),
                          ' probes')
                    # print('To see them, enable verbose mode with -v')
                    if options.verbose:
                        print('bad probes:')
                        print(bad_probes)
                outputlist = new_outputlist
            print('writing pkl file to', matches_path)
            with open(matches_path, 'wb') as fp:
                pkl.dump(outputlist, fp)
            mpath_root,mpath_ext = os.path.splitext(matches_path)
            if options.order_list:
                with open(mpath_root+'_probe_counts.csv', 'w') as fp:
                    fp.write('\n'.join([str(p) for p in probe_counts]))
            else:
                with open(mpath_root + '_probe_counts.csv', 'w') as fp:
                    fp.write('entryId,returned result count')
                    fp.write('\n'.join([str(k) +','+ str(probe_counts_withid[k]) for k in probe_counts_withid]))

            # with open(mpath_root+'_entry_id_order.csv', 'w') as fp:
            #     fp.write('\n'.join(output_entry_ids_list))
        if options.output_type == "briar":
            matches_name = os.path.splitext(os.path.basename(filename))[0] + MATCHES_FILE_EXT
            matches_path = os.path.join(out_dir, matches_name)
            briar.grpc_json.save(searchReply, matches_path)
