#!/usr/bin/env python
r"""Various system utilities

>>> import mySystem as ms
>>> import os

Copy file
>>> ms.copy('mySystem.py', '.temp')


Time stamp
>>> ms.getStamp('mySystem.py')
1285894621.0

Sorted reverse time
>>> ms.lslrt('.')
['__init__.pyc', 'myReplace.pyc', '__init__.py', 'myReplace.py', 'mySystem.py', '.temp', 'mySystem.pyc']

Sorted alphabetically
>>> ms.lslrt('.')
['__init__.pyc', 'myReplace.pyc', '__init__.py', 'myReplace.py', 'mySystem.py', '.temp', 'mySystem.pyc']

>>> ms.freplace('freplace', 'fREPLACE', './.temp')
3

>>> ms.cat('./.temp', './.temp', './.temp1')
368

>>> os.remove('./.temp')
>>> os.remove('./.temp1')

"""

#import cProfile
import sys
import os
import shutil

# Exceptions
class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class InputError(Error):
    """Exception raised for errors in the input.
    Attributes:
    message -- explanation of the error
    """
    def __init__(self, message, usage_=0):
        Error.__init__()
        self.message    = message
        self.usage      = usage_

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

def find_executable(executable, path=None):
    """Try to find 'executable' in the directories listed in 'path' (a
    string listing directories separated by 'os.pathsep'; defaults to
    os.environ['PATH']).  Returns the complete filename or None if not
    found
    """
    if path is None:
        path = os.environ['PATH']
    paths = path.split(os.pathsep)
    extlist = ['']

    if os.name == 'os2':
        (base, ext) = os.path.splitext(executable)
        # executable files on OS/2 can have an arbitrary extension, but
        # .exe is automatically appended if no dot is present in the name
        if not ext:
            executable = executable + ".exe"
    elif sys.platform == 'win32':
        pathext = os.environ['PATHEXT'].lower().split(os.pathsep)
        (base, ext) = os.path.splitext(executable)
        if ext.lower() not in pathext:
            extlist = pathext
        print 'pathext=', pathext, ', base=', base, ', ext=', ext, \
            'extlist=', extlist
    for ext in extlist:
        execname = executable + ext
        if os.path.isfile(execname):
            return execname
        else:
            for p in paths:
                f = os.path.join(p, execname)
                if os.path.isfile(f):
                    return f
    else:
        return None


def copy(file1, oFile):
    """Copy file to dest, return total lines copied"""
    shutil.copy(file1, oFile)
    #inf1  = open(file1)
    #output  = open(oFile, 'w')
    #count = 0
    #for s in inf1.xreadlines():
    #    count += 1
    #    output.write(s)
    #inf1.close()
    #output.close()
    #return count

def getStamp(lfile):
    """Time stamp of file"""
    ifile = os.path.isfile(lfile)
    if ifile:
        dfile = os.path.getmtime(lfile)
    else:
        dfile = 0
    return dfile

def lslrt(path):
    """Directory listing sorted by time, latest last"""
    flist = []
    for x in os.listdir(path):
        if not os.path.isdir(x):
            flist.append((os.stat(x).st_mtime, x))
    flist.sort()
    dList = [x[1] for x in flist]
    return dList

def lsl(path):
    """Directory listing sorted alphabetically"""
    flist = []
    for x in os.listdir(path):
        if not os.path.isdir(x):
            flist.append(x)
    flist.sort()
    return flist

def freplace(stext, rtext, iFile):
    """Replace string in file"""
    inputf = open(iFile)
    output = open('.rtemp', 'w')
    count  = 0
    for s in inputf.xreadlines():
        count += s.count(stext)
        output.write(s.replace(stext, rtext))
    inputf.close()
    output.close()
    shutil.move('.rtemp', iFile)
    return count

def cat(file1, file2, oFile):
    """Cat two files to dest, return total lines catted"""
    input1 = open(file1)
    input2 = open(file2)
    output = open(oFile, 'w')
    count = 0
    for s in input1.xreadlines():
        count += 1
        output.write(s)
    for s in input2.xreadlines():
        count += 1
        output.write(s)
    input1.close()
    input2.close()
    output.close()
    return count


if __name__ == '__main__':
    import doctest
    doctest.testmod(verbose=True)

