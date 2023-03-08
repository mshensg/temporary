#!/bin/bash

FILE=/bin/python

if test -f "$FILE"; then
    PYTHON=$FILE
else
    PYTHON=/usr/bin/python
fi

$PYTHON $(dirname $BASH_SOURCE)/checkconfig.py
