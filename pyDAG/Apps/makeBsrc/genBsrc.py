#!/usr/bin/env python
"""Generate c and h source files from Beacon7 netlists specified in argument list
    -h / --help
        Print this message and exit
    -d / --debug  <e.g. 0>
        Use this verbosity level to debug program
    -f / --fullbuild
        Use all .net files in folder
    -V, --version
        Print version and quit \n

Tests:
>>>python getrdg.py
"""
#import cProfile
import getopt
from string import replace
from string import atoi
import sys
import os
import shutil
import subprocess

verbose = 0

# Exceptions
class Error(Exception):
    """Base class for exceptions in this module."""
    pass
class InputError(Error):
    """Exception raised for errors in the input.
    Attributes:
        message -- explanation of the error
    """
    def __init__(self, message, usage=0):
        self.message    = message
        self.usage      = usage
    def __str__(self):
        if self.usage:
            return repr(self.message) + '\n\n%(doc)s' %{'doc':  __doc__}
        else:
            return repr(self.message)

def usage(code, msg=''):
    "Usage description"
    print >> sys.stderr, __doc__
    if msg:
        print >> sys.stderr, msg
    sys.exit(code)

# Directory listing sorted by time, latest last
def lslrt(path):
    flist=[]
    for x in os.listdir(path):
        if not os.path.isdir(x):
            flist.append((os.stat(x).st_mtime, x))
    flist.sort()
    dList = [x[1] for x in flist]
    return dList

# Directory listing sorted alphabetically
def lsl(path):
    flist=[]
    for x in os.listdir(path):
        if not os.path.isdir(x):
            flist.append(x)
    flist.sort()
    return flist

# Replace string in file
def fReplace(stext, rtext, iFile):
    inf  = open(iFile)
    output = open('.temp', 'w')
    count  = 0
    for s in inf.xreadlines():
        count += s.count(stext)
        output.write(s.replace(stext, rtext))
    inf.close()
    output.close()
    shutil.move('.temp', iFile)
    return count

# Cat two files to dest, return success as 0
def cat(file1, file2, oFile):
    inf1  = open(file1)
    inf2  = open(file2)
    output  = open(oFile, 'w')
    for s in inf1.xreadlines():
        output.write(s)
    for s in inf2.xreadlines():
        output.write(s)
    inf1.close()
    inf2.close()
    output.close()

# Copy file to dest, return success as 0
def copy(file1, oFile):
    inf1  = open(file1)
    output  = open(oFile, 'w')
    for s in inf1.xreadlines():
        output.write(s)
    inf1.close()
    output.close()

def main(argv):
    "Get readings"

    # Initialize static variables.
    global verbose
    PATH    = os.getcwd()

    # Initialize
    monF  = 'code_report'
    FULLBUILD = 0

    # Options
    try:
        options, remainder = getopt.getopt(argv, 'd:fhV', ['debug=', 'fullbuild', 'help', 'version',])
    except getopt.GetoptError:
        usage(2)
    for opt, arg in options:
        if   opt in ('-h', '--help'):
            print usage(1)
        elif opt in ('-d', '--debug'):
            verbose = atoi(arg)
        elif opt in ('-f', '--fullbuild'):
            FULLBUILD = 1
        elif opt in ('-V', '--version'):
            print 'genBsrc.py Version 0.0.  DA Gutz 7/14/2010'
            exit(0)
        else: print usage(1)
    if len(remainder) < 1:
        print usage(1)
        exit(1)
    if len(remainder) > 0 and FULLBUILD:
        print usage(1)
        print 'inconsistent FULLBUILD option and file list provided'
        exit(1)

    print 'genBsrc: generating c/h source files from .net in %(PATH)s' %{'PATH': PATH}

    # Alphabetical directory listing
    dListAlpha = lsl('.')

    # .net listings
    if FULLBUILD:
        nList = []
        for myFile in dListAlpha:
            (head, sep, ext) = myFile.rpartition('.')
            if len(ext)==3 and ext.count('net'):
                nList.append(myFile)
    else:
        nList = []
        for myFile in remainder:
            (head, sep, ext) = myFile.rpartition('.')
            if len(ext)==3 and ext.count('net'):
                nList.append(myFile)

    monFp = open(monF, 'w')
    subprocess.PIPE = monFp
    for myFile in nList:

        # remove old ones
        (root, sep, ext) = myFile.rpartition('.')
        hfile = "%(FILE)s" %{'FILE': root+'.h'}
        cfile = "%(FILE)s" %{'FILE': root+'.c'}
        if os.path.isfile(hfile):
            os.remove(hfile)
        if os.path.isfile(cfile):
            os.remove(cfile)
        if sys.platform == 'darwin':
            cmd1 = "touch %(FILE).c; touch %(FILE).h;"
        else:
            cmd1 = "/afs/ae.ge.com/apps/beacon7/bin/codegen %(FILE)s -list_var -options_file=$HOME/Beacon.config -language=C" %{'FILE': myFile}
        cmd2 = "sed -n '/--%/p'"
        cmd3 = "sed -n '/The DISCUS and HONEYWELL options require the global precision/,/Internal flag reset to SINGLE/!p'"
        try:
            p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
            p2 = subprocess.Popen(cmd2, stdin=p1.stdout, stdout=subprocess.PIPE, shell=True)
            p3 = subprocess.Popen(cmd3, stdin=p2.stdout, stdout=subprocess.PIPE, shell=True)
            (output3, cgStat) = p3.communicate()
            if cgStat:
                print >>sys.stderr, "Child was terminated by signal", cgStat
            else:
                print ("%(FILE)s: %(OUTPUT)s" %{'FILE': myFile, 'OUTPUT': output3})
                monFp.write("%(FILE)s: %(OUTPUT)s\n" %{'FILE': myFile, 'OUTPUT': output3})
        except OSError, e:
            print >>sys.stderr, "Execution failed:", e

    # Cleanup and quit
    monFp.close()
    print "genBsrc:  done."


if __name__=='__main__':
    #sys.exit(cProfile.run("main(sys.argv[1:])"))
    sys.exit(main(sys.argv[1:]))
 
