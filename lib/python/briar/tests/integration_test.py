import unittest
import os
import numpy as np
import warnings
import briar
import briar.briar_grpc.briar_pb2 as briar_pb2
import briar.briar_grpc.briar_service_pb2 as srvc_pb2
# import green
import inspect
from briar.tests import test_warn
from briar.media_converters import modality_proto2string

warnings.filterwarnings("ignore", category=ResourceWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
# from unittest_prettify.colorize import (
#     colorize,
#     GREEN,
# )
unittest.TestLoader.sortTestMethodsUsing = None

args_string = " --progress "
media_args = " --no-save "
def setUpModule():
    warnings.filterwarnings("ignore", category=ResourceWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    print('setting up test module')
    # args_string = " --progress "
    pass

def setUpClass_main(cls) -> None:
    warnings.filterwarnings("ignore", category=ResourceWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    import cv2
    cls.workingdir = os.path.dirname(os.path.realpath(__file__))
    cls.imagepathsingle = os.path.join(cls.workingdir, 'test_media', 'halle.jpg')
    cls.imagepathsingle2 = os.path.join(cls.workingdir, 'test_media', 'hanks.jpeg')
    cls.imagepathsingle3 = os.path.join(cls.workingdir, 'test_media', 'leo.jpeg')
    cls.imagepathsingle4 = os.path.join(cls.workingdir, 'test_media', 'morgan.jpeg')
    cls.imagepathsingle5 = os.path.join(cls.workingdir, 'test_media', 'halle2.jpeg')

    cls.imagepathsingle6 = os.path.join(cls.workingdir, 'test_media', 'smith.jpeg')
    cls.imagepathsingle7 = os.path.join(cls.workingdir, 'test_media', 'cage.jpeg')
    cls.imagepathsingle6_2 = os.path.join(cls.workingdir, 'test_media', 'smith2.jpeg')
    cls.imagepathsingle7_2 = os.path.join(cls.workingdir, 'test_media', 'cage2.jpeg')

    cls.imagepathmultiple = os.path.join(cls.workingdir, 'test_media', 'david_and_morgan.jpg') #for use with probe tests
    cls.videopathsingle = os.path.join(cls.workingdir, 'test_media', 'hanks.mov')
    cls.videopathmultiple = os.path.join(cls.workingdir, 'test_media', 'walking.mov') # for use with probe tests
    cap = cv2.VideoCapture(cls.videopathmultiple)
    ret,cls.videoMultiple = cap.read()
    cap.release()
    cap = cv2.VideoCapture(cls.videopathsingle)
    ret, cls.videoSingle = cap.read()
    cap.release()
    cls.imagesingle = cv2.imread(cls.imagepathsingle)
    cls.imagesingle2 = cv2.imread(cls.imagepathsingle2)
    cls.imagesingle3 = cv2.imread(cls.imagepathsingle3)
    cls.imagesingle4 = cv2.imread(cls.imagepathsingle4)
    cls.imagesingle5 = cv2.imread(cls.imagepathsingle5)
    cls.imagemultiple = cv2.imread(cls.imagepathmultiple)


class Test001Status(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from briar.cli.status import status
        setUpClass_main(cls)
        cls.status_reply = status(input_command='status' + args_string, ret=True)
    def setUp(self) -> None:
        self.status_reply: srvc_pb2.StatusReply
        self.currentVersion = briar.__version__
        self.currentVersionMajor,self.currentVersionMinor,self.currentVersionPatch = self.currentVersion.split('.')
    def test_01_sdk_version(self):
        """Testing SDK Version"""
        server_api_version = self.status_reply[4]
        self.assertEqual(int(server_api_version.major),int(self.currentVersionMajor))
        self.assertEqual(int(server_api_version.minor), int(self.currentVersionMinor))
        test_warn(self.assertEqual,int(server_api_version.patch), int(self.currentVersionPatch),'SDK patch Version does not correspond with API patch version')

    def test_02_dev_name(self):
        """Testing Developer Name"""
        self.assertGreater(len(self.status_reply[0]), 0) #check there is something there
        self.assertGreater(len(self.status_reply[1]), 0) #check there is something there
    def test_03_dev_short_name(self):
        """Testing Developer Short Name"""
        self.assertNotIn(self.status_reply[1], ' ') #make sure no spaces in short name
        self.assertTrue(self.status_reply[1].isupper())
    def test_04_alg_version(self):
        """Testing Algorithm Version"""
        server_alg_version = self.status_reply[3]
        self.assertGreaterEqual(server_alg_version.major,1)
        self.assertGreaterEqual(server_alg_version.minor, 0)
        self.assertGreaterEqual(server_alg_version.major, 0)
    def test_05_alg_name(self):
        """Testing Algorithm Name"""
        self.assertGreater(len(self.status_reply[2]),0) #make sure there is something there

# class Test_002_Protobufs(unittest.TestCase):
#     def setUpClass(cls) -> None:
#         import briar.briar_client as briar_client
#         from briar.cli.status import get_service_configuration
#         setUpClass_main(cls)
#         cls.client, cls.config_reply = get_service_configuration(input_command='status' + args_string,ret=True)
#         cls.client : briar_client.BriarClient
#
#     def test_status_proto(self):
#         self.client.get_status(srvc_pb2.StatusRequest())
#     def test_status_proto(self):
#         self.client.get_status(srvc_pb2.StatusRequest())
#     def test_status_proto(self):
#         self.client.get_status(srvc_pb2.StatusRequest())


class Test003Configuration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from briar.cli.status import get_service_configuration
        setUpClass_main(cls)
        cls.config_reply = get_service_configuration(input_command='status' + args_string)

    def test_01_config_portlist(self):
        """Testing configuration port list"""
        self.config_reply : srvc_pb2.BriarServiceConfigurationReply
        self.assertGreater(len(self.config_reply.port_list),0)
        for port in self.config_reply.port_list:
            self.assertIn(':',port)
            self.assertGreaterEqual(len(port.split(':')),2)
        self.assertEqual(self.config_reply.base_port,self.config_reply.port_list[0])

    def test_02_port_connections(self):
        """Testing port connections"""
        from briar.cli.status import status

        for port in self.config_reply.port_list:
            success = False
            try:
                print('checking port ',port)
                status_reply = status(input_command='status'+ args_string, ret=True)
                success = True
            except Exception as e:
                print('Could not connect to ',port,':',e)
            self.assertTrue(success)

    def test_03_num_service_ports(self):
        """Testing number of ports variable"""
        self.assertGreaterEqual(self.config_reply.number_of_service_ports, 1)
        self.assertEqual(self.config_reply.number_of_service_ports,len(self.config_reply.port_list))
    def test_04_num_procs_per_port(self):
        self.assertGreaterEqual(self.config_reply.number_of_processes_per_port, 1)
        self.assertTrue((briar.PLATFORM == 'darwin' and self.config_reply.number_of_processes_per_port == 1) or briar.PLATFORM != 'darwin')
    def test_05_num_threads_per_port(self):
        self.assertGreaterEqual(self.config_reply.number_of_threads_per_process, 1)




class Test004Detect(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def runmedia(self,path,media,ideal_entries = 0):
        import numpy as np
        from briar.cli.detect import detect
        replies = []
        for reply in detect(input_command='detect ' + args_string +media_args + path,ret=True):
            replies.append(reply)
        test_warn(self.assertGreaterEqual,len(replies),ideal_entries,'your detector may be finding too few detections!')
        test_warn(self.assertLess,len(replies), ideal_entries+3,'your detector may be finding too many detections!')

        totaldets = 0
        for reply in replies:
            reply : srvc_pb2.DetectReply
            try:
                if ideal_entries > 0:
                    self.assertGreater(len(reply.detections), 0)
            except Exception as e:
                curframe = inspect.currentframe()
                calframe = inspect.getouterframes(curframe, 2)
                stack_i = 1
                print('exception from stack trace:')
                funcs = []
                while stack_i < 6 and True:
                    func_name = calframe[stack_i][3]
                    funcs.append(func_name)
                    if 'test' in func_name:
                        break
                    stack_i += 1
                print('Function:', '->'.join(funcs))
                print("Exception:",e)
            for det in reply.detections:
                totaldets+=1
                self.assertGreaterEqual(det.location.x,0)
                self.assertGreaterEqual(det.location.y, 0)
                if isinstance(media,np.ndarray):

                    test_warn(self.assertLess,det.location.x+det.location.width,media.shape[1])
                    test_warn(self.assertLess,det.location.y + det.location.height, media.shape[0])
                self.assertGreater(det.location.width,0)
                self.assertGreater(det.location.height, 0)
                self.assertGreaterEqual(det.confidence,0)
                self.assertIsNotNone(det.media)
                try:
                    self.assertIsNotNone(det.detection_id)
                except Exception as e:
                    curframe = inspect.currentframe()
                    calframe = inspect.getouterframes(curframe, 2)
                    stack_i = 1
                    print('exception from stack trace:')
                    funcs = []
                    while stack_i < 6 and True:
                        func_name = calframe[stack_i][3]
                        funcs.append(func_name)
                        if 'test' in func_name:
                            break
                        stack_i += 1
                    print('Function:', '->'.join(funcs))
                    print('Exception:',e)
                try:
                    self.assertIsNotNone(det.detection_class)
                except Exception as e:
                    curframe = inspect.currentframe()
                    calframe = inspect.getouterframes(curframe, 2)
                    stack_i = 1
                    print('exception from stack trace:')
                    funcs = []
                    while stack_i < 6 and True:
                        func_name = calframe[stack_i][3]
                        funcs.append(func_name)
                        if 'test' in func_name:
                            break
                        stack_i += 1
                    print('Function:', '->'.join(funcs))
                    print('Exception:',e)
        test_warn(self.assertGreaterEqual,totaldets,ideal_entries,'your detector may be finding too few detections!')
        test_warn(self.assertLessEqual,totaldets,ideal_entries+3,'your detector may be finding too many detections!')


    def test_01_detection_image_single(self):
        self.runmedia(self.imagepathsingle,self.imagesingle,1)

    def test_02_detection_image_multiple(self):
        self.runmedia(self.imagepathmultiple, self.imagemultiple, 1)
    def test_03_detection_video_multiple(self):
        self.runmedia(self.videopathmultiple, self.videoMultiple, )



class Test005Enhance(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)

    def runmedia(self,path,media,cropped):
        from briar.cli.enhance import enhance
        from briar.media_converters import image_proto2cv
        for reply in enhance(input_command= 'enhance ' + cropped + ' ' + args_string +media_args+ path,ret = True):

            reply : srvc_pb2.EnhanceReply
            cvoutput = image_proto2cv(reply.media)
            if isinstance(media,np.ndarray):
                # print(media.shape,cvoutput.shape)
                self.assertGreater(cvoutput.shape[1],0)
                self.assertGreater(cvoutput.shape[0], 0)
                if cropped == '--cropped':
                    test_warn(self.assertLessEqual,cvoutput.shape[1],media.shape[1])
                    test_warn(self.assertLessEqual,cvoutput.shape[0],media.shape[0])
                else:
                    test_warn(self.assertGreaterEqual,cvoutput.shape[1],media.shape[1])
                    test_warn(self.assertGreaterEqual,cvoutput.shape[0],media.shape[0])

    def test_01_image_single_cropped(self):
        self.runmedia(self.imagepathsingle,self.imagesingle,cropped = '--cropped')
    def test_02_image_single_full(self):
        self.runmedia(self.imagepathsingle,self.imagesingle,cropped = '')
    def test_03_image_multiple_cropped(self):
        self.runmedia(self.imagepathmultiple, self.imagesingle, cropped='--cropped')

    def test_04_image_multiple_full(self):
        self.runmedia(self.imagepathmultiple, self.videoMultiple, cropped='')

    def test_05_video_multiple_cropped(self):
        self.runmedia(self.videopathmultiple,self.videoMultiple,cropped = '--cropped')







class Test006Extract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)


    def runmedia(self,path,media,ideal_templates=0):
        from briar.cli.extract import extract
        from briar.media_converters import vector_proto2np
        total_templates = 0
        total_replies = 0
        for reply in extract(inputCommand= 'extract ' + args_string +media_args + path,ret = True):

            reply : srvc_pb2.ExtractReply
            total_replies+=1

            if reply.progress_only_reply:
                self.assertEquals(len(reply.templates),0,'If you return a progress only reply it should not contain templates')
            else:
                test_warn(self.assertGreater, len(reply.templates), 0)
            for template in reply.templates:
                template: briar_pb2.Template
                self.assertIsNotNone(template.data)
                vect = vector_proto2np(template.data)
                buff = template.buffer
                self.assertTrue(len(vect) > 1 or len(buff) > 0)

                total_templates +=1

        test_warn(self.assertLessEqual,total_templates,ideal_templates,'Your algorithm may be extracting too many templates')
        self.assertGreaterEqual(total_replies,0)

    def test_01_extraction_image_singe(self):
        self.runmedia(self.imagepathsingle,self.imagesingle,1)

    def test_02_extraction_image_multiple(self):
        self.runmedia(self.imagepathmultiple,self.imagemultiple,2)
    def test_03_extraction_video_multiple(self):
        self.runmedia(self.videopathmultiple,self.videoMultiple,)






class Test007DatabaseFunctions(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)
        cls.testdb_name = "integration_tests_db"
    def test_01_create_database(self):
        from briar.cli.database.create import database_create
        from briar.cli.database.delete import  database_delete
        from briar.cli.database.list import  database_list
        # testdb_name = "integration_tests_db"
        del_reply = database_delete(input_command="database delete " + args_string + self.testdb_name,ret=True)
        self.assertTrue(del_reply is not None)
        reply = database_create(input_command="database create " + args_string + self.testdb_name,ret=True)
        self.assertTrue(reply is not None)

        database_list = database_list(ret=True,input_command="database list" + args_string)
        # print('database list:',database_list)
        #
        self.assertIn(self.testdb_name,database_list)
    def test_02_database_info(self):
        from briar.cli.database.info import database_info

        info_reply = database_info(input_command="database info " + args_string + self.testdb_name,ret=True)
        db_info = info_reply.info
        entries = db_info.entry_count
        templates = db_info.template_count
        failed = db_info.failed_enrollment_count
        dbsize = db_info.total_database_size
        avgsize = db_info.average_entry_size
        entry_list = list(db_info.entry_ids)
        entry_sizes = list(db_info.entry_sizes)
        modalities = [modality_proto2string(m) for m in db_info.modalities]
        self.assertEqual(entries,0)
        self.assertEqual(templates,0)
        self.assertEqual(len(entry_list),0)

    def test_03_rename_database(self):
        from briar.cli.database.create import database_create
        from briar.cli.database.delete import database_delete
        from briar.cli.database.list import database_list
        from briar.cli.database.rename import database_rename
        from briar.cli.database.refresh import database_refresh
        # testdb_name = "integration_tests_db"

        del_reply = database_delete(input_command="database delete " + args_string + self.testdb_name,ret=True)
        self.assertTrue(del_reply is not None)
        reply = database_create(input_command="database create " + args_string + self.testdb_name,ret=True)
        self.assertTrue(reply is not None)

        database_list_temp = database_list(ret=True,input_command="database list" + args_string)
        # print('database list:',database_list)
        #
        self.assertIn(self.testdb_name,database_list_temp)

        database_rename(input_command='database rename ' + self.testdb_name + ' renamed_database' +args_string)
        refresh_reply = database_refresh(ret=True,input_command="database refresh " + args_string)
        database_list_temp = database_list(ret=True, input_command="database list" + args_string)
        self.assertNotIn(self.testdb_name, database_list_temp)
        self.assertIn('renamed_database', database_list_temp)
        database_rename(input_command='database rename ' + ' renamed_database '+self.testdb_name+args_string)
        refresh_reply = database_refresh(ret=True, input_command="database refresh " + args_string)
    def test_04_delete_database(self):
        from briar.cli.database.create import database_create
        from briar.cli.database.delete import database_delete
        from briar.cli.database.list import database_list

        # del_reply = database_delete(input_command="database delete " + args_string + self.testdb_name,ret=True)
        # self.assertTrue(del_reply is not None)
        reply = database_create(input_command="database create " + args_string + self.testdb_name,ret=True)
        self.assertTrue(reply is not None)

        dblist = database_list(ret=True,input_command="database list"+ args_string)
        # print('database list:',database_list)
        #
        self.assertIn(self.testdb_name,dblist)

        del_reply = database_delete(input_command="database delete "+ args_string + self.testdb_name,ret=True)
        self.assertTrue(del_reply is not None)
        dblist = database_list(ret=True, input_command="database list"+ args_string)
        self.assertNotIn(self.testdb_name, dblist)

    def test_05_refresh_database(self):
        from briar.cli.database.refresh import database_refresh
        refresh_reply = database_refresh(input_command="database refresh "+args_string,ret=True)
        self.assertIsNone(refresh_reply)


class Test008Enroll(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)
        cls.testdb_name = "integration_tests_db"
    def runmedia(self,path,entry_type,testdb_name ,subject_id = 'G001',media_id=None):
        if media_id is None:
            media_id = subject_id
        from briar.cli.enroll import enroll
        from briar.cli.database.create import database_create
        from briar.cli.database.list import database_list
        total_templates = 0
        total_replies = 0

        # del_reply = database_delete(input_command="database delete "+ args_string + testdb_name, ret=True)
        # self.assertTrue(del_reply is not None)
        database_list = database_list(input_command="database list" + args_string,ret=True)
        if testdb_name not in database_list:
            reply = database_create(input_command="database create "+ args_string + testdb_name, ret=True)
            self.assertTrue(reply is not None)


        for reply in enroll(input_command= 'enroll --database ' + testdb_name + media_args + args_string+ ' --subject-id '+ subject_id +' --media-id ' + media_id +' --entry-type ' + entry_type + ' ' + path,ret = True):

            reply : srvc_pb2.EnrollReply

            total_replies+=1
            self.assertTrue(reply is not None)
    def test_01_enroll_image_gallery(self):
            self.runmedia(self.imagepathsingle,'gallery',self.testdb_name+"_gallery1",subject_id= 'G001')
    def test_02_enroll_image_gallery2(self):
            self.runmedia(self.imagepathsingle2,'gallery',self.testdb_name+"_gallery1",subject_id= 'G002',media_id='G002_0')
    def test_03_enroll_video_gallery(self): #tests additional video enrollment to G002
            self.runmedia(self.videopathsingle,'gallery',self.testdb_name+"_gallery1",subject_id= 'G002',media_id='G002_1')
    def test_04_database_checkpoint_subject(self):
        from briar.cli.database.checkpoint_subject import database_checkpoint_subject
        checkpoint_reply = database_checkpoint_subject(
            input_command="database checkpoint-subject " + args_string + ' G002 ' + self.testdb_name + "_gallery1", ret=True)
    def test_05_enroll_image_gallery3(self):
        self.runmedia(self.imagepathsingle3, 'gallery', self.testdb_name + "_gallery1", subject_id='G003')
    def test_06_enroll_image_gallery4(self):
        self.runmedia(self.imagepathsingle4,'gallery',self.testdb_name+"_gallery1",subject_id= 'G004')

    def test_07_enroll_image_gallery6(self):
        self.runmedia(self.imagepathsingle6,'gallery',self.testdb_name+"_gallery2",subject_id= 'G006')
    def test_08_enroll_image_gallery7(self):
        self.runmedia(self.imagepathsingle7,'gallery',self.testdb_name+"_gallery2",subject_id= 'G007')


    def test_09_enroll_image_probe(self):
            self.runmedia(self.imagepathsingle,'probe',self.testdb_name+"_probe1",subject_id= 'p001')
    def test_10_enroll_image_probe2(self):
            self.runmedia(self.imagepathsingle5,'probe',self.testdb_name+"_probe1",subject_id= 'p002')
    def test_11_enroll_video_multiple_probe(self):
            self.runmedia(self.videopathmultiple,'probe',self.testdb_name+"_probe1",subject_id= 'p003')

    def test_12_enroll_image_probe3(self):
            self.runmedia(self.imagepathsingle6_2,'probe',self.testdb_name+"_probe2",subject_id= 'p004')

    def test_13_enroll_image_probe4(self):
        self.runmedia(self.imagepathsingle7_2, 'probe', self.testdb_name + "_probe2", subject_id='p005')



class Test009DatabaseFunctionsAfterEnroll(unittest.TestCase): #should only be called after running TestEnroll
    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)
        cls.testdb_name = "integration_tests_db"

    def test_01_database_checkpoint_gallery1(self):
        from briar.cli.database.checkpoint import database_checkpoint

        checkpoint_reply = database_checkpoint(input_command="database checkpoint " + args_string + self.testdb_name+"_gallery1", ret=True)
    def test_02_database_checkpoint_gallery2(self):
        from briar.cli.database.checkpoint import database_checkpoint

        checkpoint_reply = database_checkpoint(input_command="database checkpoint " + args_string + self.testdb_name+"_gallery2", ret=True)
    def test_03_database_checkpoint_probe1(self):
        from briar.cli.database.checkpoint import database_checkpoint
        checkpoint_reply = database_checkpoint(input_command="database checkpoint " + args_string + self.testdb_name+"_probe1", ret=True)
    def test_04_database_checkpoint_probe2(self):
        from briar.cli.database.checkpoint import database_checkpoint
        checkpoint_reply = database_checkpoint(input_command="database checkpoint " + args_string + self.testdb_name+"_probe2", ret=True)

    def test_05_database_finalize_gallery1(self):
        from briar.cli.database.finalize import database_finalize

        checkpoint_reply = database_finalize(
            input_command="finalize " + args_string + self.testdb_name + "_gallery1", ret=True)

    def test_06_database_finalize_gallery2(self):
        from briar.cli.database.finalize import database_finalize

        checkpoint_reply = database_finalize(
            input_command="finalize " + args_string + self.testdb_name + "_gallery2", ret=True)

    def test_07_database_merge_probe1_probe2(self):
        from briar.cli.database.merge import database_merge
        from briar.cli.database.list import database_list
        self.getInfo(self.testdb_name + "_probe1", 3, 3, ['p001', 'p002', 'p003'])
        self.getInfo(self.testdb_name + "_probe2", 2, 2, ['p004', 'p005'])
        merge_reply = database_merge(input_command="database merge --regex " + self.testdb_name +'_probe --output-database merged_' + self.testdb_name + "_probe " + args_string)

        self.getInfo("merged_"+self.testdb_name + "_probe", 5, 5, ['p001', 'p002', 'p003','p004', 'p005'])
        database_list = database_list(ret=True, input_command="database list" + args_string)
        self.assertIn('merged_' + self.testdb_name + "_probe", database_list)
    def test_08_database_merge_probe_checkpoint(self):
        from briar.cli.database.checkpoint import database_checkpoint
        checkpoint_reply = database_checkpoint(
            input_command="database checkpoint " + args_string + 'merged_' + self.testdb_name + "_probe", ret=True)

    def getInfo(self,db_name,entry_len=0,template_len=0,true_entry_list=[]):
        from briar.cli.database.info import database_info

        info_reply = database_info(input_command="database info " + args_string + db_name, ret=True)
        db_info = info_reply.info
        entries = db_info.entry_count
        templates = db_info.template_count
        failed = db_info.failed_enrollment_count
        dbsize = db_info.total_database_size
        avgsize = db_info.average_entry_size
        entry_list = list(db_info.entry_ids)
        entry_sizes = list(db_info.entry_sizes)
        modalities = [modality_proto2string(m) for m in db_info.modalities]
        self.assertEqual(entries, entry_len)
        self.assertGreaterEqual(templates, template_len)
        self.assertEqual(len(entry_list), entry_len)
        for entry in entry_list:
            self.assertIn(entry, true_entry_list)
    def test_09_database_info_probe1(self):
        self.getInfo(self.testdb_name+"_probe1",3,3,['p001','p002', 'p003'])
    def test_10_database_info_probe2(self):
        self.getInfo(self.testdb_name+"_probe2",2,2,['p004','p005'])
    def test_11_database_info_gallery1(self):
        self.getInfo(self.testdb_name+"_gallery1",4,4,['G001', 'G002', 'G003', 'G004'])
    def test_12_database_info_gallery2(self):
        self.getInfo(self.testdb_name+"_gallery2",2,2,['G006', 'G007'])


class Test010Verify(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)
        cls.pos_scores = []
        cls.neg_scores = []
    def test_01_verify_image_to_image_negative(self):
        from briar.cli.verify import verify
        verify_reply = verify(
            input_command="verify " + args_string + media_args+ self.imagepathsingle + " " + self.imagepathsingle3, ret=True)
        listlen = len(verify_reply.similarities.match_list)
        self.assertGreater(listlen,0,msg="Verification length should be greater that 0")
        test_warn(self.assertLessEqual,listlen,1,"Verification is possibly returning too many scores")
        scores  = []
        for match in verify_reply.similarities.match_list:
            self.assertLessEqual(match.score,match.theoretical_max,'verification score should be under the defined max')
            self.assertGreaterEqual(match.score, match.theoretical_min,'verification score should be over the defined min')
            self.neg_scores.append(match.score)


    def test_02_verify_image_to_image_positive(self):
        from briar.cli.verify import verify
        verify_reply = verify(
            input_command="verify " + args_string + media_args + self.imagepathsingle + " " + self.imagepathsingle5, ret=True)
        listlen = len(verify_reply.similarities.match_list)
        self.assertGreater(listlen, 0, msg="Verification length should be greater that 0")
        test_warn(self.assertLessEqual, listlen, 1, "Verification is possibly returning too many scores")
        scores = []
        for match in verify_reply.similarities.match_list:
            self.assertLessEqual(match.score, match.theoretical_max,
                                 'verification score should be under the defined max')
            self.assertGreaterEqual(match.score, match.theoretical_min,
                                    'verification score should be over the defined min')
            self.pos_scores.append(match.score)

    def test_03_verify_score_coherence(self):
        self.assertGreater(len(self.pos_scores), 0)
        self.assertGreater(len(self.neg_scores), 0)
        self.assertLessEqual(max(self.neg_scores), max(self.pos_scores),
                             'the negative verification example should score lower than the positive verification example')

    def test_04_verify_image_to_video_positive(self):
        from briar.cli.verify import verify
        verify_reply = verify(input_command="verify " + args_string+ media_args + self.imagepathsingle2 + " " + self.videopathsingle, ret=True)
        listlen = len(verify_reply.similarities.match_list)
        self.assertGreater(listlen, 0, msg="Verification length should be greater that 0")
        test_warn(self.assertLessEqual, listlen, 1, "Verification is possibly returning too many scores for video matching")
        scores = []
        for match in verify_reply.similarities.match_list:
            self.assertLessEqual(match.score, match.theoretical_max,
                                 'verification score should be under the defined max')
            self.assertGreaterEqual(match.score, match.theoretical_min,
                                    'verification score should be over the defined min')
            self.pos_scores.append(match.score)







class Test011Search(unittest.TestCase):
    # print('running test status')
    @classmethod
    def setUpClass(cls) -> None:
        setUpClass_main(cls)
        cls.pos_scores = []
        cls.neg_scores = []
        cls.testdb_name = "integration_tests_db_gallery1"

    def test_01_search_image_single(self):
        self.runmedia(self.imagepathsingle5,'G001',ideal_results_size=1)
    def runmedia(self,mediapath,subject_id,returnK = -1,ideal_results_size=1):
        from briar.cli.search import search

        replies = search(input_command="search " + args_string + media_args + "--database " + self.testdb_name + " --max-results " + str(returnK) + " " + mediapath,ret=True)
        total_replies = 0
        total_similarity_lists = 0

        from briar.cli.database.info import database_info

        info_reply = database_info(input_command="database info " + args_string + self.testdb_name, ret=True)
        db_info = info_reply.info
        entries = db_info.entry_count
        templates = db_info.template_count
        failed = db_info.failed_enrollment_count
        dbsize = db_info.total_database_size
        avgsize = db_info.average_entry_size
        entry_list = list(db_info.entry_ids)
        entry_sizes = list(db_info.entry_sizes)
        modalities = [modality_proto2string(m) for m in db_info.modalities]
        self.assertEquals(entries, 4) #there should be 4 entries in total for the gallery
        self.assertGreaterEqual(templates,entries)
        for s in entry_sizes:
            self.assertGreater(s,0,'your algorithm should be returning a non-zero storage size for database entries')
        # self.assertEqual(templates, 0)
        # self.assertEqual(len(entry_list), 0)


        for reply in replies:
            if reply is not None:
                total_replies += 1
                self.assertGreater(len(reply.similarities),0)
                test_warn(self.assertLess,len(reply.similarities),ideal_results_size,"Your search results are returning too many!")
                for searchmatchlist in reply.similarities:
                    result_list = searchmatchlist.match_list
                    total_similarity_lists+=1
                    scores = np.array([match.score for match in result_list])
                    self.assertTrue(np.all(np.diff(scores) <= 0),'Search results are not sorted in descending order')
                    if not subject_id == -1:
                        test_warn(self.assertEquals,result_list[0].subject_id_gallery,subject_id,'Your search using an image of Halle is not returning Halle as the first result') #the search results should show up with Halle as first

                    if returnK > 0:
                        self.assertEquals(len(result_list),returnK,'Your algorithm should provide the amount of results defined by the --max-results flag')
                    for match in result_list:
                        self.assertLessEqual(match.score, match.theoretical_max)
                        self.assertGreaterEqual(match.score, match.theoretical_min)
                        self.assertIsNotNone(match.subject_id_gallery)
                        self.assertGreaterEqual(len(match.subject_id_gallery),0)

            else:
                self.assertIsNotNone(reply, "No reply found")
                print('repy')
        self.assertGreater(total_similarity_lists,0)
        self.assertGreater(total_replies, 0)
        test_warn(self.assertLess,total_similarity_lists,ideal_results_size, 'Your algorithm may be returning too many sets of search results')
        test_warn(self.assertLess, total_replies, ideal_results_size, 'Your algorithm may be returning too many sets of search results')
    def test_02_search_video_single(self):
        self.runmedia(self.videopathsingle,'G002',ideal_results_size=1)
    def test_03_search_video_multiple(self):
        self.runmedia(self.videopathmultiple, 'unknown', returnK=-1, ideal_results_size=2)
def tearDownModule():
    print('tearing down test module')
    pass

def runall():
    unittest.main()



if __name__ == '__main__':
    import sys
    print(sys.argv)
    # if len(sys.argv) > 1:
    #     if sys.argv[1] == '-v':
    # main(module=briar.tests.integration_test)
    # green.main()
    unittest.main()