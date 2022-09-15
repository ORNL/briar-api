
#import tqdm.auto
#import numpy as np
import os.path


def parseBriarSigset(filename):
    import xml.etree.cElementTree as ET
    import pandas as pd

    print(filename,os.path.exists(filename))
    tree = ET.parse(filename)

    root = tree.getroot()

    columns = ('name','subjectId','filepath','modality','media','media_format','start','stop','unit')
    #df = pd.DataFrame(columns=columns)
    data_list = []
    rootiter = list(root.iter('{http://www.nist.gov/briar/xml/sigset}signature'))
    #for signature in tqdm.auto.tqdm(rootiter,position=1):
    for signature in rootiter:
        name = signature.find('{http://www.nist.gov/briar/xml/sigset}name').text
        subjectId = signature.find('{http://www.nist.gov/briar/xml/sigset}subjectId').text
        sig=list(signature.iter('{http://www.nist.gov/briar/xml/sigset}sigmember'))
        for sigmember in sig:
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

            #i = len(df)

            data = [name,subjectId,filepath,modality,media,media_format,start,stop,unit]
            # print(columns)
            for field, value in zip(columns,data):
                if value == "ERROR":
                    raise ValueError("Could not determine '{}' for sigmember {} in {}".format(field,i,filename))
            #dft = pd.DataFrame([data], columns=columns)
            # print(dft.shape)
            # df.append(dft)
            # print(df)
            #df.loc[i] = data
            data_list.append(data)
            #print(len(df))

    df = pd.DataFrame(data_list,columns=columns)
    return df

def expandTree(root, level = 0, spaces=3):
    for element in root:
        padding = " "*spaces*level
        print(padding+element.tag,len(padding),level)
        #print(dir(element))
        expandTree(element,level+1,spaces)