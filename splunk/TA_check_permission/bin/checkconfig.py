#!/bin/python

import os
import hashlib
import time

def get_file_hash(filename):
    sha256_hash = hashlib.sha256()
    md5_hash = hashlib.md5()
    with open(filename,"rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096),b""):
            sha256_hash.update(byte_block)
            md5_hash.update(byte_block)
    return sha256_hash.hexdigest(),md5_hash.hexdigest()

SPLUNK_HOME=os.environ['SPLUNK_HOME'] if 'SPLUNK_HOME' in os.environ else "/opt/splunkforwarder"

#manifest=max([i for i in os.listdir(SPLUNK_HOME) if i[-8:]=="manifest"])
manifest=os.path.join(SPLUNK_HOME,max([i for i in os.listdir(SPLUNK_HOME) if i[-8:]=="manifest"]))

hashes={}

omit=SPLUNK_HOME.split("/")[-1]

with open(manifest,"r") as f:
    contents=f.readlines()

for i in contents:
    fields = i.split(" ")
    if len(fields)==6:
        checkfile=fields[4]
        if checkfile[0:len(omit)] == omit:
            checkfile = checkfile[len(omit)+1:]
        filename=os.path.join(SPLUNK_HOME,checkfile)
#        print(filename)
        hashes[filename]=fields[5].strip()

#print(hashes)

#for h in hashes.keys():
#    print(h+"\t"+hashes[h])


splunk_configuration_folder="etc/apps"
target_folder=os.path.join(SPLUNK_HOME, splunk_configuration_folder)

files_to_check=[]

for folder, dirs, files in os.walk(target_folder):
    for file in files:
        if file.endswith(".conf"):
            files_to_check.append(os.path.join(folder,file))

t=time.strftime("%Y-%m-%d %H:%M:%S %z")

for file in files_to_check:
    hashsha256,hashmd5 = get_file_hash(file)
    expected=hashes[file] if file in hashes.keys() else None
    if expected is None:
        result = "added"
    elif expected == hashsha256:
        result = "intact"
    else:
        result = "modified"
    if result!="intact":
        #print('{"checktime":"{}","filename":"{}","hash":"{}"}'.format(t,file,get_hash))
        print('{"checktime":"'+t+'","filename":"'+file+'","sha256hash":"'+hashsha256+'","md5hash":"'+hashmd5+'","type":"'+result+'"}')
