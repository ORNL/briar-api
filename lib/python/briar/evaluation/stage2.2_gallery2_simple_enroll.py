import unittest
import os
from briar.evaluation import runStages
main = unittest.TestProgram

if __name__ == '__main__':
    generate_report = os.environ.get('REPORT', False)
    runStages([0,2.2],generate_report)