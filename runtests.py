#!/usr/bin/python2.5
import os
import sys
import unittest
sys.path.append('code')

from strongbox import *
from clerks import *
from weblib import *
from handy import *
from storage import *
from pytypes import *

# from zebra import *   # depends on obsolete xmllib


__name__ = "runtests"   # to prevent other unittests from running first
spies = []
for filename in os.listdir('specs'):
    if filename.endswith("_spec.py"):
        # pass in filename so it shows up in tracebacks:
        path = os.path.join('specs', filename)
        exec(compile(open(path).read(), path, 'exec'))
        
unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout))
