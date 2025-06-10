# import tqdm.auto
# import numpy as np
import os.path
import sys
from briar.functions import collect_files,new_uuid


def parseBriarFolder(path,options):
    """
The parseBriarFolder function takes a path to a folder and returns a list of all files in that folder that are supported by Briar.
:param path: Specify the path to the folder
:return: A list of all files in the folder that are supported by Briar

:doc-author: Joel Brogan,
"""
    import pandas as pd
    image_list,video_list = collect_files([path], options)
    columns = ('entryId', 'subjectId', 'filepath', 'modality', 'media', 'media_format', 'start', 'stop', 'unit')
    data_list = []
    media_types = ['digitalStill','digitalVideo']
    for i,medialist in enumerate([image_list,video_list]):
        media_type = media_types[i]
        for mediapath in medialist:
            medianame = os.path.basename(mediapath)
            name_parts = medianame.split('_')
            if hasattr(options,'enrollment_structure'):
                if options.enrollment_structure == 'per-file':
                    subjectId = name_parts[::max(1,len(name_parts)-1)][0]
                elif options.enrollment_structure == 'per-folder':
                    subjectId = os.path.basename(os.path.dirname(mediapath))
            subjectIds = [subjectId]
            
            filepath = mediapath
            modality = 'face'
            media = media_type
            fname, ext = os.path.splitext(medianame)
            entryId = mediapath.replace('/','_')
            media_format = ext[1:]
            # print('media format',media_format)
            start = "NA"
            stop = 'NA'
            unit = 'NA'
            # entryId = new_uuid()
            data = [entryId, subjectIds, filepath, modality, media, media_format, start, stop, unit]
            data_list.append(data)
    df = pd.DataFrame(data_list, columns=columns)
    return df

def parseBriarSigset(filename):
    """
The parseBriarSigset function parses a Briar XML sigset file and returns a pandas dataframe with the following columns:
    name - The name of the signature.
    subjectId - The ID of the subject who signed this signature.
    filepath - The path to where this sigmember is stored on disk. This may be relative or absolute, depending on how it was specified in the sigset file.
    modality - What type of media is used for this sigmember (e.g., 'online', 'offline').  See https://briarsigset-schema-v2_

:param filename: Specify the path to the xml file
:return: A dataframe with the following columns:
:doc-author: Joel Brogan, BRIAR team, Joel Brogan, BRIAR team, Trelent
"""
    import xml.etree.cElementTree as ET
    import pandas as pd

    tree = ET.parse(filename)

    root = tree.getroot()

    columns = ('entryId', 'subjectId', 'filepath', 'modality', 'media', 'media_format', 'start', 'stop', 'unit')
    # df = pd.DataFrame(columns=columns)
    data_list = []
    rootiter = list(root.iter('{http://www.nist.gov/briar/xml/sigset}signature'))


    for signature in rootiter:
        name = signature.find('{http://www.nist.gov/briar/xml/sigset}name').text
        subjectIds = []
        for element in signature.iter('{http://www.nist.gov/briar/xml/sigset}subjectId'):
            subjectIds.append(element.text)

        sig = list(signature.iter('{http://www.nist.gov/briar/xml/sigset}sigmember'))
        for i, sigmember in enumerate(sig):
            filepath = "ERROR"
            modality = 'ERROR'
            media = "ERROR"
            media_format = 'ERROR'
            start = "NA"
            stop = 'NA'
            unit = 'NA'

            for element in sigmember.iter('{http://www.nist.gov/briar/xml/sigset}filePath'):
                filepath = element.text
            for element in sigmember.iter('{http://www.nist.gov/briar/xml/sigset}modality'):
                modality = element.text
            for element in sigmember.iter('{http://www.nist.gov/briar/xml/sigset}media'):
                media = element.text
            for element in sigmember.iter('{http://www.nist.gov/briar/xml/sigset}mediaFormat'):
                media_format = element.text
            for element in sigmember.iter('{http://www.nist.gov/briar/xml/sigset-eval}start'):
                start = element.text
            for element in sigmember.iter('{http://www.nist.gov/briar/xml/sigset-eval}stop'):
                stop = element.text
            for element in sigmember.iter('{http://www.nist.gov/briar/xml/sigset-eval}unit'):
                unit = element.text
            for element in sigmember.iter('{http://www.nist.gov/briar/xml/sigset}id'):
                entryId = element.text
            # i = len(df)

            data = [entryId, subjectIds, filepath, modality, media, media_format, start, stop, unit]
            # print(columns)
            i = 0
            for field, value in zip(columns, data):
                if value == "ERROR":
                    raise ValueError("Could not determine '{}' for sigmember {} in {}".format(field, i, filename))
            i += 1
            data_list.append(data)

    df = pd.DataFrame(data_list, columns=columns)
    return df


def create_test_sigset(sigset_probe_file : str,sigset_gallery_file : str,base_dir : str,output_dir):
    import xml.etree.cElementTree as ET
    # from lxml import etree as ET
    import pandas as pd
    import numpy as np
    from briar.media_converters import pathmap_path2remotepath
    from tqdm import tqdm
    probe_tree = ET.parse(sigset_probe_file)
    print(sigset_gallery_file)
    gallery_tree = ET.parse(sigset_gallery_file)
    gallery_tree2 = ET.parse(sigset_gallery_file)
    gallery_root = gallery_tree.getroot()
    gallery_root2 = gallery_tree2.getroot()
    probe_root = probe_tree.getroot()
    columns = ('entryId', 'subjectId', 'filepath', 'modality', 'media', 'media_format', 'start', 'stop', 'unit')
    path_map = {"./BTS1/":"BGC1/BTS1","./BTS2/":"BGC2/BTS2","./BTS3/":"BGC3/BTS3","./BTS1.1/":"BGC1.1/BTS1.1","./BTS4/":"BGC4/BTS4","./BTS5/":"BGC5/BTS5"}

    # df = pd.DataFrame(columns=columns)
    data_list = []

    total_subjects = 10
    total_gallery_images_per_subject = 5
    total_gallery_videos_per_subject = 2
    total_probes_per_subject = 5
    total_distractor_probes = 5

    all_keep_subject_ids = {}
    gallery_subjects_to_keep = []
    for descriptor in gallery_root.iter('{http://www.nist.gov/briar/xml/sigset}description'):
        descriptor.text = "A miniature test sigset for validation purposes, containing data from BTS1, 1.1, 2, and 3"
    for parent in tqdm(gallery_root.findall('.//{http://www.nist.gov/briar/xml/sigset}signature/..')): #parent is the overaching sigset element element
        for el in parent.findall('{http://www.nist.gov/briar/xml/sigset}signature'): #each el should be a signature that holds sigmembers (for gallery)
            subjectId = el.find('{http://www.nist.gov/briar/xml/sigset}subjectId').text
            num_images = []
            num_videos = []
            for el2 in el.findall('{http://www.nist.gov/briar/xml/sigset}sigmember'):
                filepath = list(el2.iter('{http://www.nist.gov/briar/xml/sigset}filePath'))[0].text
                fixedpath = os.path.join(base_dir,pathmap_path2remotepath(filepath, path_map))
                format = list(el2.iter('{http://www.nist.gov/briar/xml/sigset}mediaFormat'))[0].text
                if os.path.exists(fixedpath) or True:
                    if format == "mp4":
                        num_videos.append(filepath)
                    elif format == "jpg" or format == "jpeg":
                        num_images.append(filepath)
            if len(num_images) >= total_gallery_images_per_subject and len(num_videos) >= total_gallery_videos_per_subject:
                all_keep_subject_ids[subjectId] = (num_images,num_videos)
    gallery_subjects_to_keep = np.array(list(all_keep_subject_ids.keys()))
    gallery_subjects_to_keep1 = gallery_subjects_to_keep[:int(total_subjects/2)]
    gallery_subjects_to_keep2 = gallery_subjects_to_keep[int(total_subjects/2):total_subjects]
    print('len1',gallery_subjects_to_keep)
    print('len2', gallery_subjects_to_keep2)
    for parent in tqdm(gallery_root.findall('.//{http://www.nist.gov/briar/xml/sigset}signature/..')): #parent is the overaching sigset element element
        for el in parent.findall('{http://www.nist.gov/briar/xml/sigset}signature'): #each el should be a signature that holds sigmembers (for gallery)
            subjectId = el.find('{http://www.nist.gov/briar/xml/sigset}subjectId').text
            if subjectId not in gallery_subjects_to_keep1:
                print('removing gallery 1',subjectId)
                parent.remove(el)
            else:
                images_to_keep = all_keep_subject_ids[subjectId][0]
                np.random.shuffle(images_to_keep)
                images_to_keep = images_to_keep[:total_gallery_images_per_subject]
                videos_to_keep = all_keep_subject_ids[subjectId][1]
                np.random.shuffle(videos_to_keep)
                videos_to_keep = videos_to_keep[:total_gallery_videos_per_subject]
                for el2 in el.findall('{http://www.nist.gov/briar/xml/sigset}sigmember'):
                    filepath = list(el2.iter('{http://www.nist.gov/briar/xml/sigset}filePath'))[0].text
                    if filepath not in images_to_keep and filepath not in videos_to_keep:
                        el.remove(el2)


    for parent in tqdm(gallery_root2.findall('.//{http://www.nist.gov/briar/xml/sigset}signature/..')): #parent is the overaching sigset element element
        for el in parent.findall('{http://www.nist.gov/briar/xml/sigset}signature'): #each el should be a signature that holds sigmembers (for gallery)
            subjectId = el.find('{http://www.nist.gov/briar/xml/sigset}subjectId').text
            if subjectId not in gallery_subjects_to_keep2:
                print('removing gallery 2 ',subjectId)
                parent.remove(el)
            else:
                images_to_keep = all_keep_subject_ids[subjectId][0]
                np.random.shuffle(images_to_keep)
                images_to_keep = images_to_keep[:total_gallery_images_per_subject]
                videos_to_keep = all_keep_subject_ids[subjectId][1]
                np.random.shuffle(videos_to_keep)
                videos_to_keep = videos_to_keep[:total_gallery_videos_per_subject]
                for el2 in el.findall('{http://www.nist.gov/briar/xml/sigset}sigmember'):
                    filepath = list(el2.iter('{http://www.nist.gov/briar/xml/sigset}filePath'))[0].text
                    if filepath not in images_to_keep and filepath not in videos_to_keep:
                        el.remove(el2)

    number_of_distractors_kept = 0
    probes_subject_counts = {}
    good_probe_subjects = {}
    for parent in tqdm(probe_root.findall('.//{http://www.nist.gov/briar/xml/sigset}signature/..')): #parent is the overaching sigset element element
        for el in parent.findall('{http://www.nist.gov/briar/xml/sigset}signature'): #each el should be a signature that holds sigmembers (for gallery)

            subjectId = el.find('{http://www.nist.gov/briar/xml/sigset}subjectId').text
            isKept = True
            if subjectId not in probes_subject_counts:
                probes_subject_counts[subjectId] = []
            for el2 in el.findall('{http://www.nist.gov/briar/xml/sigset}sigmember'):
                filepath = list(el2.iter('{http://www.nist.gov/briar/xml/sigset}filePath'))[0].text
                fixedpath = os.path.join(base_dir, pathmap_path2remotepath(filepath, path_map))
                if os.path.exists(fixedpath) or True:
                    probes_subject_counts[subjectId].append(filepath)

    for p in probes_subject_counts:
        if len(probes_subject_counts[p]) >= total_probes_per_subject:
            probes = probes_subject_counts[p]
            np.random.shuffle(probes)
            good_probe_subjects[p] = probes[:total_probes_per_subject]

    kept_distractor_counts = 0

    kept_actor_counts = {}
    for parent in tqdm(probe_root.findall(
            './/{http://www.nist.gov/briar/xml/sigset}signature/..')):  # parent is the overaching sigset element element
        for el in parent.findall(
                '{http://www.nist.gov/briar/xml/sigset}signature'):  # each el should be a signature that holds sigmembers (for gallery)
            subjectId = el.find('{http://www.nist.gov/briar/xml/sigset}subjectId').text
            isKept = True
            if subjectId in good_probe_subjects and subjectId in gallery_subjects_to_keep1:
                for el2 in el.findall('{http://www.nist.gov/briar/xml/sigset}sigmember'):
                    filepath = list(el2.iter('{http://www.nist.gov/briar/xml/sigset}filePath'))[0].text
                    if filepath in good_probe_subjects[subjectId]:
                        pass
                    else:
                        el.remove(el2)
                        parent.remove(el)
            elif kept_distractor_counts < total_distractor_probes and subjectId in good_probe_subjects:
                for el2 in el.findall('{http://www.nist.gov/briar/xml/sigset}sigmember'):
                    filepath = list(el2.iter('{http://www.nist.gov/briar/xml/sigset}filePath'))[0].text
                    kept_distractor_counts +=1
            else:
                parent.remove(el)

    os.makedirs(output_dir,exist_ok=True)
    probe_tree.write(os.path.join(output_dir,'validation_probe.xml'))
    gallery_tree.write(os.path.join(output_dir,'validation_gallery1.xml'))
    gallery_tree2.write(os.path.join(output_dir, 'validation_gallery2.xml'))



def expandTree(root, level=0, spaces=3):
    """
The expandTree function takes a root element and prints out the tag, length of padding, and level for each element in the tree.
The function is recursive, so it will print out all elements in the tree.

:param root: Pass the root of the tree to be expanded
:param level: Keep track of the depth of the tree
:param spaces: Control the number of spaces used for indentation
:return: The name of each tag and the number of spaces between tags
:doc-author: Joel Brogan, BRIAR team, Trelent
"""
    for element in root:
        padding = " " * spaces * level
        print(padding + element.tag, len(padding), level)
        # print(dir(element))
        expandTree(element, level + 1, spaces)


if __name__ == '__main__':
    args = sys.argv
    create_test_sigset(args[1],args[2],args[3],args[4])
    # create_test_sigset('/Users/2r6/Projects/briar/briar-evaluation/evaluation/phase2/briar_evaluation_v4.1.1u1/sigsets_main/Probe_BTS_briar-rd_ALL.xml','/Users/2r6/Projects/briar/briar-evaluation/evaluation/phase2/briar_evaluation_v4.1.1u1/sigsets_gallery/Blended_Gallery_1.xml','/base_dataset/','/Users/2r6/Projects/briar/briar-evaluation/evaluation/phase2/briar_validation_v.1.1u1/')