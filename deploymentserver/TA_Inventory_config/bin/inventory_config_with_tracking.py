#!/bin/python

import os
import hashlib
import time
import json

def get_file_hash(filename):
    sha256_hash = hashlib.sha256()
    md5_hash = hashlib.md5()
    with open(filename,"rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096),b""):
            sha256_hash.update(byte_block)
            md5_hash.update(byte_block)
    return sha256_hash.hexdigest(),md5_hash.hexdigest()

SPLUNK_HOME=os.environ['SPLUNK_HOME'] if 'SPLUNK_HOME' in os.environ else "/opt/splunk"

manifest=os.path.join(SPLUNK_HOME,max([i for i in os.listdir(SPLUNK_HOME) if i[-8:]=="manifest"]))

splunk_configuration_folder="etc/deployment-apps"
trackerfolder=os.path.join(SPLUNK_HOME,"var/lib/splunk/modinputs/deployment_apps_config_tracker/")
if not os.path.exists(trackerfolder):
    os.mkdir(trackerfolder)
trackerfile=os.path.join(trackerfolder,"tracker.json")
target_folder=os.path.join(SPLUNK_HOME, splunk_configuration_folder)

files_to_check=[]

for folder, dirs, files in os.walk(target_folder):
    for file in files:
        if file.endswith(".conf"):
            files_to_check.append(os.path.join(folder,file))

t=time.strftime("%Y-%m-%d %H:%M:%S %z")

try:
    with open(trackerfile,"r") as f:
        content="\n".join(f.readlines())
    tracker=json.loads(content)
except:
    tracker={}
finally:
    pass

if type(tracker) is not dict:
    tracker={}

for file in files_to_check:
    hashsha256,hashmd5 = get_file_hash(file)
    checksum = hashmd5[0:16]
    #print('{"checktime":"'+t+'","filename":"'+file+'","sha256hash":"'+hashsha256+'","md5hash":"'+hashmd5+'","checksum":"0x'+checksum+'"}')
    event={"checktime":t,
           "filename":file,
           "sha256hash":hashsha256,
           "md5hash":hashmd5,
           "checksum":"0x"+checksum}
    if not file in tracker.keys() or tracker[file]["sha256hash"] != hashsha256 or time.time()-tracker[file]["checkepoch"]>86400:
        print(json.dumps(event))
        tracker[file]={"sha256hash":hashsha256,
            "md5hash":hashmd5,
            "checkepoch":time.time()}

with open(trackerfile,"w") as f:
    f.writelines([json.dumps(tracker)])
