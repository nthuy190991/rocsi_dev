# -*- coding: utf-8 -*-
"""
Created on Fri Jun 03 05:22:08 2016

@author: thnguyen
"""

#import numpy as np
import os, sys
import time
import face_api
#import emotion_api
from binascii import a2b_base64, b2a_base64
import requests
import calendar
from datetime import datetime, timedelta

_username   = 'thanhhuynguyenorange'
_password   = 'GGQN0871abc'
_url_github = 'https://api.github.com/repos/nthuy190991/facial_recognition_on_Bluemix/contents/'

def put_image_to_github(image_path, data):

    headers = {
        'Content-Type': 'application/json'
    }
    json = {
        "message": "bluemix",
        "committer": {
            "name": "thanhhuynguyenorange",
            "email": "thanhhuy.nguyen@orange.com"
        },
        "content": b2a_base64(data)
    }
    url = _url_github + image_path

    response = requests.put(url, headers=headers, json=json, auth=(_username, _password))
    result   = response.json() if response.content else None
    return result

def get_image_from_github(image_path):
    url = _url_github + image_path
    response = requests.get(url, auth=(_username, _password))

    # result = response.json() if response.content else None
    if (response.content):
        result = response.json()
        data_read = result['content']
    else:
        data_read =  None

    binary_data = a2b_base64(data_read)
    return binary_data

def delete_image_on_github(image_path):
    url = _url_github + image_path
    response = requests.get(url, auth=(_username, _password))
    result   = response.json() if response.content else None
    sha_img  = result['sha']

    headers = {
        'Content-Type': 'application/json'
    }
    json = {
        "message": "bluemix",
        "committer": {
            "name": "thanhhuynguyenorange",
            "email": "thanhhuy.nguyen@orange.com"
        },
        "sha": sha_img
    }
    response = requests.delete(url, headers=headers, json=json, auth=(_username, _password))
    result   = response.json() if response.content else None
    return result



def utc_to_local(utc_dt):
    # get integer timestamp to avoid precision lost
    timestamp = calendar.timegm(utc_dt.timetuple())
    local_dt = datetime.fromtimestamp(timestamp)
    assert utc_dt.resolution >= timedelta(microseconds=1)
    return local_dt.replace(microsecond=utc_dt.microsecond)

def aslocaltime(utc_dt):
    dt = utc_to_local(utc_dt)
    yyyy = dt.year
    mm = dt.month
    dd = dt.day
    h = dt.hour
    m = dt.minute
    s = dt.second
    return yyyy, mm, dd, h, m, s

"""
Convert date and time
"""
def convert_datetime(str_datetime): # Format "mm/dd/yyyy hh:mm:ss AM"
    mm, dd         = str_datetime.split('/')[0:2]
    yyyy, tt, ampm = str_datetime.split('/')[2].split(' ')
    h, m, s        = tt.split(':')

    if (((ampm=='pm') or (ampm=='PM')) and (h!=12)):
        h=h+12

    # Convert from UTC time to Local
    yyyy, mm, dd, h, m, s = aslocaltime(datetime(int(yyyy),  int(mm), int(dd), int(h), int(m), int(s)))
    print 'Created on ', datetime(yyyy, mm, dd, h, m, s)
    return yyyy, mm, dd, h, m, s


"""
==============================================================================
Create PersonGroup, Add images and Train PersonGroup
==============================================================================
"""
def create_group_add_person(groupId, groupName):

    # Create PersonGroup
    result = face_api.createPersonGroup(groupId, groupName, "")
    flag_reuse_person_group = False

    if ('error' in result):
        result = eval(result)

        if (result["error"]["code"] == "PersonGroupExists"):

            res_train_status      = face_api.getPersonGroupTrainingStatus(groupId)
            res_train_status      = res_train_status.replace('null','None')
            res_train_status_dict = eval(res_train_status)
            print res_train_status

            if 'error' not in res_train_status_dict:
                createdDateTime = res_train_status_dict['createdDateTime']
                year, month, day, hour, mi, sec = convert_datetime(createdDateTime)

                structTime = time.localtime()
                dt_now = datetime(*structTime[:6])
                print dt_now

                # Compare if the PersonGroup has expired or not (valid during 24 hours)
                if (dt_now.year==year):
                    if (dt_now.month==month):
                        if (dt_now.day==day):
                            del_person_group = False
                        elif (dt_now.day-1==day):
                            if (dt_now.hour<hour):
                                del_person_group = False
                            else:
                                del_person_group = True
                        else:
                            del_person_group = True
                    else:
                        del_person_group = True
            else:
                del_person_group = True

            if (del_person_group):
                print 'PersonGroup exists, deleting...'

                res_del = face_api.deletePersonGroup(groupId)
                print ('Deleting PersonGroup succeeded' if res_del=='' else 'Deleting PersonGroup failed')

                result = face_api.createPersonGroup(groupId, groupName, "")
                print ('Re-create PersonGroup succeeded' if res_del=='' else 'Re-create PersonGroup failed')

                flag_reuse_person_group = False

            elif (not del_person_group):
                # Get PersonGroup training status
                training_status = res_train_status_dict['status']
                if (training_status=='succeeded'):
                    flag_reuse_person_group = True

        elif (result["error"]["code"] == "RateLimitExceeded"):
            print 'RateLimitExceeded, please retry after 30 seconds'
            sys.exit()



    if not flag_reuse_person_group:
        # Create person and add person image
        image_paths = [os.path.join(imgPath, f) for f in os.listdir(imgPath)]
        nbr = 0

        for image_path in image_paths:
            nom = os.path.split(image_path)[1].split(".")[0]
            if nom not in list_nom:
                # Create a Person in PersonGroup
                personName = nom
                personId   = face_api.createPerson(groupId, personName, "")

                list_nom.append(nom)
                list_personId.append(personId)
                nbr += 1
            else:
                personId = list_personId[nbr-1]

            # Add image
            image_data = get_image_from_github(image_path)
            face_api.addPersonFace(groupId, personId, None, None, image_data)
            print "Add image...", nom, '\t', image_path
            time.sleep(0.25)


def train_person_group(groupId):
    # Train PersonGroup
    face_api.trainPersonGroup(groupId)

    # Get training status
    res      = face_api.getPersonGroupTrainingStatus(groupId)
    res      = res.replace('null','None')
    res_dict = eval(res)
    training_status = res_dict['status']
    print training_status

    while (training_status=='running'):
        time.sleep(0.25)
        res = face_api.getPersonGroupTrainingStatus(groupId)
        res = res.replace('null','None')
        res_dict = eval(res)
        training_status = res_dict['status']
        print training_status

    return training_status


"""
==============================================================================
    MAIN PROGRAM
==============================================================================
"""
try:
    if (sys.argv[1] == '-h') or (sys.argv[1] == '--help'):
        print 'mdl_recognition_msoxford.py <path_to_database> <path_to_image_test/video>'
        sys.exit()

    groupId = sys.argv[1]
    groupName = sys.argv[2]

except IndexError:
    print "Set parameters as default"
    groupId     = "PersonGroup"
    groupName   = "Employeurs"

# Parameters
imgPath = "face_database_for_oxford/" # path to database of faces
maxNbOfCandidates = 1 # Maximum number of candidates for the identification

list_nom = []
list_personId = []
nbr = 0

# Train database
create_group_add_person(groupId, groupName)
result = train_person_group(groupId)

# Begin run program
if (result=='succeeded'):
    print('Database' + str(groupId) + ' is ready for recognition...')

# END OF PROGRAM
