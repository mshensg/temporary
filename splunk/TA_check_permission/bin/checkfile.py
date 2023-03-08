#!/bin/python
import time

file_to_check=['/var/log/secure','/var/log/messages','/var/log/audit/audit.log','/var/log/auth']

for file in file_to_check:
    try:
        with open(file,"r") as f:
            l = f.readline()
    except Exception as err:
        print('{"checktime":"'+time.strftime("%Y-%m-%d %H:%M:%S %z")+'","filename":"'+file+'","result":"'+str(err)+'"}\n')
    else:
        print('{"checktime":"'+time.strftime("%Y-%m-%d %H:%M:%S %z")+'","filename":"'+file+'","result":"successful"}\n')
    finally:
        pass

