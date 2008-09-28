#!/bin/env python
"""
Pack an individual workshop module for distribution on PyPI, etc.
"""
import os
import sys
from subprocess import call
from shutil import copy

def resetDotPackDirectory():
    if not 'pack.py' in os.listdir('.'):
        print "please run this from workshop/trunk."
        sys.exit()

    if os.path.exists(".pack"):
        os.system('rm -rf .pack')
    os.mkdir(".pack")


def checkModuleExists(module):
    path = 'code/%s.py' % module
    if not os.path.exists(path):
        print "error:", path, "not found!"
        print 'doing nothing.'
        sys.exit()


def pack(module, setup_args):
    print 'packing', module
    print '-------------------------------------------'
    resetDotPackDirectory()

    filesToCopy = [
        'code/%s.py' % module,
        'ez_setup.py',
        'common_setup.py']

    for f in filesToCopy:
        print 'copying %s -> .pack' % f
        copy(f, '.pack')

    os.chdir('.pack')

    setup = open('setup.py', 'w')
    setup.write('from common_setup import *\n')
    setup.write('common_setup("%s")\n' % (module))
    setup.close()

    manifest = open('MANIFEST.in', 'w')
    manifest.write('include ez_setup.py common_setup.py')
    manifest.close()

    
    call(['python', 'setup.py'] + list(setup_args))
    os.chdir('..')


def main(module, *setup_args):
    checkModuleExists(module)
    pack(module, setup_args)

if __name__ == '__main__':

    if len(sys.argv) < 3:
        print "usage: pack.py module [setup.py commands]"

    main(*sys.argv[1:])
