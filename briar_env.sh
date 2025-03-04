# BRIAR API environment variables, if you want to import the API in-place without setup.py or pip
export PYTHONPATH=${PYTHONPATH}:${BRIAR_DIR}stubs/python
export PYTHONPATH=${PYTHONPATH}:${BRIAR_DIR}lib/python

export BRIAR_EVAL_REPOSITORY_DIR=/Users/2r6/Projects/briar/briar-evaluation #where the briar-evaluation repository lives on your system
export BRIAR_EVAL_API_OUTPUT_DIR=/Users/2r6/Projects/briar/briar-evaluation #where you would like the API to write its output score files
#The following env variables are used only in the validation_test suite and integration_test suite
#briar.tests.integration_test
#briar.tests.validation_test
export BRIAR_EVAL_PHASE=phase2
export BRIAR_EVAL_PHASE_MINOR=final
export BRIAR_VALIDATION_PROTOCOL=briar_validation_v4.2.0
export BRIAR_MULTISUBJECT_EVAL_PROTOCOL=briar_evaluation_v4.0.0
export BRIAR_EVAL_PROTOCOL=briar_evaluation_v5.0.0

export BRIAR_MULTISUBJECT_EVAL_SIGSET=Probe_BTS3_multi.xml #this will be changed for a more full multisubject evaluation that adheres to a protocol naming convention

export BRIAR_VALIDATION_DIR=$BRIAR_EVAL_REPOSITORY_DIR/evaluation/$BRIAR_EVAL_PHASE/$BRIAR_VALIDATION_PROTOCOL/
export BRIAR_VALIDATION_OUTPUT_DIR=$BRIAR_EVAL_API_OUTPUT_DIR/evaluation/$BRIAR_EVAL_PHASE/briar_${BRIAR_EVAL_PHASE}_deliverable/all_test_results/scores
export BRIAR_REPORT_OUTPUT_DIR=$BRIAR_EVAL_API_OUTPUT_DIR/evaluation/$BRIAR_EVAL_PHASE/briar_${BRIAR_EVAL_PHASE}_deliverable/all_test_results/reports/
export BRIAR_DATASET_DIR=/Users/2r6/briarrd/

#The following env variables are used only in the evaluation suite
export BRIAR_EVALUATION_DIR=$BRIAR_EVAL_REPOSITORY_DIR/evaluation/$BRIAR_EVAL_PHASE/BRIAR_EVAL_PROTOCOL/
export BRIAR_MULTISUBJECT_EVALUATION_DIR=$BRIAR_EVAL_REPOSITORY_DIR/evaluation/$BRIAR_EVAL_PHASE/BRIAR_MULTISUBJECT_EVAL_PROTOCOL/
export BRIAR_EVALUATION_OUTPUT_DIR=$BRIAR_EVAL_API_OUTPUT_DIR/evaluation/$BRIAR_EVAL_PHASE/briar_${BRIAR_EVAL_PHASE}_deliverable/self_evaluation_results/

export BRIAR_USE_SINGLE_SUBJECT=false #this will ensure that the --single-subject flag is not called during the evaluation scoring.

############## THE FOLLOWING SHOULD BE USED IN service_env.sh WITHIN THE DELIVERABLE STRUCTURE, NOT HERE. ##############

#The following are service configuration options that the API will use to configure how it interacts with your application
#export BRIAR_USE_FRONTEND_MERGING=true #if you don't set this variable, it will default to true.  Set it to false if your algorithm does not require database merging
#to use frontend_merging, you MUST also specify BRIAR_DATABASE_SUFFIX_FLAG below

#export BRIAR_DATABASE_SUFFIX_FLAG=ADDRESS,SERVICE # if BRIAR_USE_FRONTEND_MERGING=true, set BRIAR_DATABASE_SUFFIX_FLAG according to --database-suffix flag choices in sigset-enroll.
#options are: ADDRESS,SERVICE  | this tells the BRIAR API to append both the address and the unique service identifier to the end of  sub-databases to make them unique.
#             ADDRESS          | this tells the BRIAR API to append only the address to the end of a sub-database to make it unique
#             SERVICE          | this tells the BRIAR API to append only the unique service identifier to the end of a sub-database to make it unique
#Example 1: python service.py --services-per-port 2 --threads-per-service 1 --port-range 2 with BRIAR_DATABASE_SUFFIX_FLAG=ADDRESS,SERVICE
# will create 4 unique databases during enrollment:
# <database_base_name>_<ADDRESS1:PORT1>_proc0000
# <database_base_name>_<ADDRESS1:PORT1>_proc0001
# <database_base_name>_<ADDRESS2:PORT2>_proc0002
# <database_base_name>_<ADDRESS2:PORT2>_proc0003

#Example 2: python service.py --services-per-port 2 --threads-per-service 1 --port-range 2 with BRIAR_DATABASE_SUFFIX_FLAG=ADDRESS
# will create 2 unique databases during enrollment:
# <database_base_name>_<ADDRESS1:PORT1>
# <database_base_name>_<ADDRESS2:PORT2>

#These databases will automatically be re-merged at the end of the sigset-enroll call by the API and validation test suite /  run suite

