import unittest
import inspect
import warnings
import os
from briar.tests.ReportGenerator import main
def runStages(stages,report = False):
    import sys
    print(sys.argv)

    os.environ["RUN_STAGES"] = ','.join([str(s) for s in stages])
    import briar.evaluation.full_evaluation
    if report:
        main(module=briar.evaluation.full_evaluation)
    else:
        unittest.main(module=briar.evaluation.full_evaluation)