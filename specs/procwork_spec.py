"""
procwork: asynchronous subprocesses for clockwork
"""
import unittest
from narrative import testcase
import procwork
from clockwork import wrap
import time

"""
This is really simple:

We want to invoke a process, wait for
it to finish executing and then work
with the results.

The only catch is that we want to do
other things in the meantime.

"""

@testcase
def testYes(test):
    """
    yes is a command that prints 'y' over
    and over and never terminates on its own.
    """
    p = wrap(procwork.waitfor("yes", secondsToWait=0.05))
    assert p.killed
    assert p.stdout.readline() == 'y\n'

if __name__=="__main__":
    unittest.main()
