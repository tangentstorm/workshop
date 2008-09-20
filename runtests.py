#!/usr/bin/python2.5
from strongbox import *
from clerks import *
from zebra import *
from weblib import *
from handy import *
from storage import *
from pytypes import *


import os,sys


__name__="runtests" # to prevent other unittests from running first
spies = []
for filename in os.listdir('.'):
    if filename.endswith(".spy"):
        # pass in filename so it shows up in tracebacks:
        exec compile(open(filename).read(), filename, 'exec')
        
import unittest
unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout))
