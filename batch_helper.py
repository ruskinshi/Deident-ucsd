import os
import os.path
import pydicom

def createBatchDictionary(path):

    #Store each of these locations in a list
    mygenerator = absoluteFilePaths(path)
    locations = []
    for i in mygenerator:
        locations.append(i)

    #Group each Location by MR number
    d = {}
    for i in locations:
        ds = pydicom.dcmread(i)
        patientid = ds.PatientID
        print(patientid)
        if patientid  not in d:
            d[patientid] = list()
        d[patientid].append(os.path.dirname(i))

    return d

#Obtain the absolute file paths of each unique folder
def absoluteFilePaths(path):
    for dirpath,_,filenames in os.walk(path):
        for f in filenames:
            if  ('.dcm' in f) or ('.' not in f):
                yield os.path.abspath(os.path.join(dirpath,f))
                break

    
        
