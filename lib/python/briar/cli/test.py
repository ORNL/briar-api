import os.path
import sys

import briar.grpc_json
from  briar import dyn_import
from colorama import Fore, Back, Style
import cv2
import numpy as np
from briar.briar_grpc import briar_pb2
from briar import timing
class BriarTestResult:
    def __init__(self,name,passed,reason=None,level = 0):
        self.name = name
        self.passed = passed
        self.reason = reason
        self.level = level

class BriarTest:


    def __init__(self):
        if "BRIAR_TESTDATA_DIR" in os.environ:
            self.testdata_folder = os.environ["BRIAR_TESTDATA_DIR"]
            # testdata_folder = "/Users/2r6/Projects/briar/briar-testdata/"
        else:
            print("ERROR: environment variable BRIAR_TESTDATA_DIR not set.  Please set this variable to run API integration tests")
            exit(1)
            # assert "BRIAR_TESTDATA_DIR" in sys.path

    def run(self):
        return True
    def test(self):
        functions = dir(self)
        test_functions = []
        test_order = []
        for f in functions:
            if f.startswith("test_"):
                testname = type(self).__name__.replace('test_','')
                order = int(f.split('_')[1])
                test_order.append(order)
                test_functions.append({"func": getattr(type(self),f),'name':testname,'obj':self})
                # print(testname)
        test_order = np.array(test_order,dtype=np.int).argsort()
        test_functions = np.array(test_functions)[test_order]

        reportcard = []
        for funcs in test_functions:
            print('Performing test: ',funcs['name'])
            output = funcs['func'](funcs['obj'])
            funcname = funcs['func'].__name__
            print(funcname)
            if output is None or output is False:
                print(Fore.RED + 'Fail' + Fore.RESET)



            for subtestName in output:
                result = output[subtestName]
                isinstance(result,dict)
                if result is None or (isinstance(result,dict) and result['result'] is None) or (isinstance(result,dict) and result['result'] is False):
                    print(subtestName + ": " + Fore.RED + 'Fail:'+Fore.RESET)
                    if isinstance(result,dict) and 'reason' in result:
                        print(result['reason'])
                    reportcard.append([funcs['name'],funcname,subtestName,False])
                elif  isinstance(result['result'],str) and result['result'].lower() == 'warning':
                    reportcard.append([funcs['name'], funcname, subtestName, 'warning'])
                    print(subtestName + ": " + Fore.YELLOW + 'Warning' + Fore.RESET)
                    if isinstance(result, dict) and 'reason' in result:
                        print(result['reason'])
                elif result['result'] is True:
                    reportcard.append([funcs['name'],funcname,subtestName, True])
                    print(subtestName + ": " + Fore.GREEN + 'Success' + Fore.RESET)
                    if isinstance(result, dict) and 'reason' in result:
                        print(result['reason'])
        print(Fore.RESET)

        print('A Summary of all ',type(self).__name__,": ")
        testfuncname = None
        for r in reportcard:
            curfuncname = r[1]
            if not curfuncname == testfuncname:
                print(curfuncname,":")
                testfuncname = curfuncname

            if isinstance(r[3],str) and r[3].lower() == 'warning':
                print("\t"+r[2] + ": " + Fore.YELLOW + 'Passed with warning' + Fore.RESET)
            elif r[3] is True:
                print("\t"+r[2]+": " + Fore.GREEN + 'Passed' + Fore.RESET)
            else:
                print("\t"+r[2]+": " + Fore.RED + 'Failed' + Fore.RESET)
    def description(self):
        return 'A Generic Test'

class DetectTest(BriarTest):
    testim_path = "testdata/BTS1/distractors/G00038/controlled/images_jpg/face/G00038_set2_face0_03_45_662fb70a.jpg"
    output_path = "./briar-integration-test-results"

    def description(self):
        return 'Unit tests for Detection Functions'
    def test_1_detection_image(self,testim_path=None,output_path=None,return_media=False):
        subtests = {}
        import briar.cli.detect as cli_detect
        if testim_path is None:
            testim_path = self.testim_path
        if output_path is None:
            output_path = self.output_path

        self.detection_file_path = os.path.join(output_path, os.path.basename(testim_path).split('.')[
            0] + cli_detect.DETECTION_FILE_EXT)
        opstring = "detect -o " + output_path +" "+ os.path.join(self.testdata_folder,testim_path)
        if return_media:
            opstring = "detect -o " + output_path + " --return-media " + os.path.join(self.testdata_folder, testim_path)
        options,args = cli_detect.detectParseOptions(opstring)
        try:
            cli_detect.detect(options,args)
            subtests['Completed API Call'] = {'result':True}
        except Exception as e:
            subtests['Completed API Call'] = {'result':False, 'reason':e}

        subtests['Output Directory Exists'] = {'result':os.path.exists(output_path),'reason':""}
        subtests['Output Detection File Exists'] = {'result':os.path.exists(self.detection_file_path),'reason':""}
        subtests['Output Detection File Size < 512KB'] = {'result':os.path.getsize(self.detection_file_path) < 512*1024,'reason':"Detection file size is " + str(os.path.getsize(self.detection_file_path)/1024) + " KB"}
        return subtests

    def test_2_detection_image_output(self,testim_path=None,output_path=None,return_media=False):
        if testim_path is None:
            testim_path = self.testim_path
        if output_path is None:
            output_path = self.output_path
        testimage = cv2.imread(os.path.join(self.testdata_folder,testim_path))
        subtests = {}
        detection_obj = None
        try:
            detection_obj_loaded = briar.grpc_json.load(self.detection_file_path)
            detection_obj = detection_obj_loaded.detections
            # BriarTestResult(name = 'Loaded Detection file',passed=True
            subtests['Loaded Detection file'] = {'result': True}
        except Exception as e:
            subtests['Loaded Detection file'] = {'result': False, 'reason': e}
            return subtests
        if detection_obj is not None:
            subtests.update(detection_output_tests(detection_obj_loaded,testimage,return_media,))
        return subtests
    def test_3_detection_image_withreturn(self):
        return self.test_1_detection_image(return_media=True)
    def test_4_detection_image_output_withreturn(self):
        return self.test_2_detection_image_output(return_media=True)
    # Test detection on corrupt video
    # Test detection on corrupt image
    # Test detection on image with no face
    # Test detection on video with no face
    # Test detection on video returns bounding box
    # Test detection on video with trackingreturns track
    # Test detection output for correct data
    # Test detection on each modality
    # Check each modality for correct return modality flag

def detection_output_tests(detection_obj_loaded,testimage,return_media):
    try:
        detection_obj = detection_obj_loaded.detections
    except:
        subtests['Detection exits'] = {'result': False}
    subtests = {}
    if detection_obj is not None:
        subtests['Detection exits'] = {'result': detection_obj is not None}
        if len(detection_obj) == 1:
            subtests['Number of detections = 1'] = {'result': True}
        elif len(detection_obj) > 1:
            subtests['Number of detections = 1'] = {'result': 'Warning', 'reason': 'The algorithm returned' + str(
                len(detection_obj)) + ' faces'}
        else:
            subtests['Number of detections = 1'] = {'result': False,
                                                    'reason': 'The algorithm returned 0 faces'}

        subtests['Detection Confidence is Non-Negative'] = {'result': detection_obj[0].confidence >= 0,
                                                            'reason': 'Confidence: ' + str(detection_obj[0].confidence)}

        subtests['Detection x Location is Non-Negative'] = {'result': detection_obj[0].location.x >= 0,
                                                            'reason': 'X coord: ' + str(detection_obj[0].location.x)}
        subtests['Detection Y Location is Non-Negative'] = {'result': detection_obj[0].location.y >= 0,
                                                            'reason': 'Y Coord: ' + str(
                                                                detection_obj[0].location.y)}
        subtests['Detection Width is > 0'] = {'result': detection_obj[0].location.width > 0,
                                              'reason': 'width: ' + str(
                                                  detection_obj[0].location.width)}
        subtests['Detection Height is > 0'] = {'result': detection_obj[0].location.height > 0,
                                               'reason': 'height: ' + str(
                                                   detection_obj[0].location.height)}

        subtests['Detection Width is < Image Width'] = {'result': detection_obj[0].location.width < testimage.shape[1]}
        subtests['Detection Height is < Image Height'] = {
            'result': detection_obj[0].location.height < testimage.shape[0]}
        subtests['Detection Height is < Image Height'] = {
            'result': detection_obj[0].location.height < testimage.shape[0]}
        if not return_media:
            subtests['Detection should not contain media bytes'] = {
                'result': len(detection_obj[0].media.data) == 0}
        else:
            subtests['Detection should contain media bytes'] = {
                'result': len(detection_obj[0].media.data) > 0,
                'reason': "Media data is length " + str(len(detection_obj[0].media.data))}
        if not return_media:
            subtests['Detection media be of correct type SOURCE_ONLY'] = {
                'result': detection_obj[0].media.type == briar_pb2.BriarMedia.SOURCE_ONLY,
                'reason': 'Media output is of type ' + str(detection_obj[0].media.type)}
        else:
            subtests['Detection media be of Not SOURCE_ONLY'] = {
                'result': not detection_obj[0].media.type == briar_pb2.BriarMedia.SOURCE_ONLY,
                'reason': 'Media output is of type ' + str(detection_obj[0].media.type)}
        subtests['Detection media contains a source path'] = {
            'result': len(detection_obj[0].media.source) > 0}
        subtests['Detection media source path exists'] = {
            'result': os.path.exists(detection_obj[0].media.source),
            'reason': "source path: " + detection_obj[0].media.source}
        subtests['Detection media source path exists'] = {
            'result': os.path.exists(detection_obj[0].media.source),
            'reason': "source path: " + detection_obj[0].media.source}
        subtests['Total duration is > 0'] = {'result': timing.timeElapsed(detection_obj_loaded.durations.total_duration) > 0,
                                             'reason': 'Total duration is ' + str(
                                                 timing.timeElapsed(detection_obj_loaded.durations.total_duration)) + " seconds"}

        totaldur = []
        for dkey in detection_obj_loaded.durations.durations:
            totaldur.append(detection_obj_loaded.durations.durations[dkey])
        totaldur = np.array(totaldur)
        subtests['Duration parts > 0'] = {'result': totaldur.sum() > 0,
                                          'reason': 'Total duration is ' + str(totaldur.sum()) + " seconds"}
        durdif = float(abs(totaldur.sum() - timing.timeElapsed(detection_obj_loaded.durations.total_duration)))
        if len(totaldur) > 0:
            subtests['More than 0 Duration parts'] = {'result': True,
                                                      'reason': str(
                                                          len(totaldur)) + ' Duration parts returned by algorithm (Briardurations.durations)'}
        else:
            subtests['More than 0 Duration parts'] = {'result': 'Warning',
                                                      'reason': 'No duration parts returned by algorithm (Briardurations.durations)'}
        if durdif < .1:
            subtests['Duration parts == total_duration'] = {'result': True,
                                                            'reason': 'Difference between duration parts and total duration is ' + str(
                                                                durdif) + " seconds"}
        elif durdif < .5:
            subtests['Duration parts == total_duration'] = {'result': "Warning",
                                                            'reason': 'Difference between duration parts and total duration is ' + str(
                                                                durdif) + " seconds"}
        else:
            subtests['Duration parts == total_duration'] = {'result': False,
                                                            'reason': 'Difference between duration parts and total duration is ' + str(
                                                                durdif) + " seconds"}

        subtests['gRPC transfere Duration < .05s'] = {
            'result': 'api_transfer' in detection_obj_loaded.durations.durations and
                      detection_obj_loaded.durations.durations['api_transfer'],
            'reason': 'Difference between duration parts and total duration is ' + str(durdif) + " seconds"}
    return subtests

def extraction_output_tests(template_obj_loaded,testimage,return_media):
    subtests = {}
    templatesize = sys.getsizeof(template_obj_loaded[0])
    if templatesize > 0:
        subtests['Template > 0 memory size'] = {'result': True}
    else:
        subtests['Template > 0 memory size'] = {'result': False, 'reason': "sys.getsizeof(template) = " + str(templatesize)}

    return subtests
class ExtractTest(BriarTest):
    testim_path = "testdata/BTS1/distractors/G00038/controlled/images_jpg/face/G00038_set2_face0_03_45_662fb70a.jpg"
    output_path = "./briar-integration-test-results"
    def description(self):
        return 'Unit tests for Template Extraction Functions'
    def test_1_extraction_image(self,testim_path=None,output_path=None,return_media=False):
        subtests = {}
        import briar.cli.extract as cli_extract
        import briar.cli.detect as cli_detect
        if testim_path is None:
            testim_path = self.testim_path
        if output_path is None:
            output_path = self.output_path

        self.template_file_path = os.path.join(output_path, os.path.basename(testim_path).split('.')[
            0] + cli_extract.TEMPLATE_FILE_EXT)
        self.detection_file_path = os.path.join(output_path, os.path.basename(testim_path).split('.')[
            0] + cli_detect.DETECTION_FILE_EXT)
        opstring = "extract -o " + output_path +" "+ os.path.join(self.testdata_folder,testim_path)
        if return_media:
            opstring = "extract -o " + output_path + " --return-media " + os.path.join(self.testdata_folder, testim_path)
        options,args = cli_extract.extractParseOptions(opstring)
        try:
            cli_extract.extract(options,args)
            subtests['Completed API Call'] = {'result':True}
        except Exception as e:
            subtests['Completed API Call'] = {'result':False, 'reason':e}
            return subtests

        subtests['Output Directory Exists'] = {'result':os.path.exists(output_path),'reason':""}
        subtests['Output Detection File Exists'] = {'result':os.path.exists(self.template_file_path),'reason':""}
        subtests['Output Detection File Size < 512KB'] = {'result':os.path.getsize(self.template_file_path) < 512*1024,'reason':"Detection file size is " + str(os.path.getsize(self.template_file_path)/1024) + " KB"}

        return subtests

    def test_2_extraction_image_output(self, testim_path=None, output_path=None, return_media=False):
        if testim_path is None:
            testim_path = self.testim_path
        if output_path is None:
            output_path = self.output_path
        testimage = cv2.imread(os.path.join(self.testdata_folder, testim_path))
        subtests = {}
        detection_obj = None
        extraction_obj = None
        try:
            detection_obj_loaded = briar.grpc_json.load(self.detection_file_path)
            detection_obj = detection_obj_loaded.detections
            # BriarTestResult(name = 'Loaded Detection file',passed=True
            subtests['Loaded Detection file'] = {'result': True}
        except Exception as e:
            subtests['Loaded Detection file'] = {'result': False, 'reason': e}
            return subtests
        if detection_obj is not None:
            subtests.update(detection_output_tests(detection_obj_loaded, testimage, return_media, ))

        try:
            template_obj_loaded = briar.grpc_json.load(self.template_file_path)
            template_obj = template_obj_loaded[0]
            # BriarTestResult(name = 'Loaded Detection file',passed=True
            subtests['Loaded Template file'] = {'result': True}
        except Exception as e:
            subtests['Loaded Template file'] = {'result': False, 'reason': e}
            return subtests
        if template_obj_loaded is not None and len(template_obj_loaded) > 0:
            subtests.update(extraction_output_tests(template_obj_loaded, testimage, return_media, ))
        return subtests

    # def test_2_extraction_image_subdetection(self):
    #     return

    # Test extraction on corrupt video
    # Test extraction on corrupt image
    # Test extraction on image with no face
    # Test extraction on video with no face
    # Test extraction on image with provided bounding box
    # Test extraction on video with provided bounding box
    # Test extraction on video with tracking returns track
    # Test extraction output for correct data
    # Test extraction on each modality
    # Check eac modality for correct return modality flag

class EnrollTest(BriarTest):
    def test(self):
        pass
    # Test enroll on corrupt video
    # Test enroll on corrupt image
    # Test enroll on image with no face
    # Test enroll on video with no face
    # Test extraction on image returns bounding box
    # Test extraction on video returns bounding box
    # Test extraction on video with trackingreturns track
    # Test extraction output for correct data
    # Test extraction on each modality
    # Check eac modality for correct return modality flag

class DatabaseTest(BriarTest):
    def test(self):
        pass
    # Check that database enrollment numbers are consistent after enroll and delete
    # Check merging correctly merges
    # Check for correct subject amounts
    # Check for correct template amounts