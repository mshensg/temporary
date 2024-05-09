#!/bin/python

import os
import time
import json

SPLUNK_HOME=os.environ['SPLUNK_HOME'] if 'SPLUNK_HOME' in os.environ else "/opt/splunkforwarder" if os.path.isdir("/opt/splunkforwarder") else "/opt/splunk"

splunk_configuration_folder="etc/apps"
splunk_system_local_folder="etc/system/local"

app_folder=os.path.join(SPLUNK_HOME, splunk_configuration_folder)
sys_folder=os.path.join(SPLUNK_HOME, splunk_system_local_folder)

exclusion_apps=["introspection_generator_addon",
"journald_input",
"learned",
"search",
"SplunkUniversalForwarder",
"splunk_httpinput",
"splunk_internal_metrics"]

splunk_applications=[os.path.join(app_folder,f) for f in os.listdir(app_folder) if os.path.isdir(os.path.join(app_folder,f)) and f not in exclusion_apps]
splunk_applications.append(sys_folder)

t=time.strftime("%Y-%m-%d %H:%M:%S %z")

for p in splunk_applications:
    filelist=[]
    filecontent=[]
    for folder, dirs, files in os.walk(p):
        for file in files:
            if file.endswith(".conf"):
                filelist.append(os.path.join(folder,file))
    for fl in filelist:
        with open(fl,"r") as f:
            content="".join(f.readlines())
        filecontent.append({fl:content})
    result={"_timestamp":t,
            "application":p,
            "filelist":filelist,
            "filecontent":filecontent}
    print(json.dumps(result,sort_keys=True))
