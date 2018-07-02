#!C:\Python27\python.exe
"""Makes .cmd PMAT trim files from ingredients in folder such as
09_ET_01.adj and 09_ET_01.tbl.
   - makes engine test trim file from $engSARs files.
   - makes dry rig test trim file from $dryRigSARs files.
   - makes multiple individual trim files from $testSARs files.
Convert .adj and .tbl source files into target .cmd trim files for FADEC load
done using the PDAP software.   Desired target trim files are 'rig',
'engine',  and 'test'.

Normally all the files in a folder are converted depending on
file name.    Therefore the user must organize source .adj and .tbl
files in folders that match the usage.   Alternatively you can list the
desired files in a .shm file to create a 'shop mod' trim.   Files in the .shm
may have any name.  The program still runs as though the files are
organized in the same folder so it will throw errors if files are not
named per convention.

The naming convention for source .adj and .tbl goes
    YY-AS-000.adj/.tbl:    application software change planned.  Included
                           into all rig and engine trims.
    YY-ET-000.adj/.tbl:    engine test only.  Included only in engine trims.
    YY-DR-000.adj/.tbl:    dry rig only.   Included only in rig trims.
    YY-XX-000.adj/.tbl:    test only.  Included only in XX test trims.

Any one of these appearing in a .shm file gets put into the shop
mod trim regardless of name.

Options:

    -h / --help
        Print this message and exit
    -d / --debug  <e.g. 0>
        Use this verbosity level to debug program
    -f / --force
        Force rebuild of all trims
    -p / --program <e.g. "ge38">
    -V, --version
        Print version and quit \n"
    -v, --SW_Version    <e.g. "v0.00">
        Use this software version string
Tests:
>>>makeCMD.py -d 0
"""
"""
Rev        Author        Date    Description
1.3.    DA Gutz        11/7/10    Add shop mod'
1.4        DG Rindner    7/22/11    Update shop mod creation
1.5        DG Rindner    9/28/11    Added recursive inclusion of shopmod lists.
1.6        DG Rindner    11/9/11    Update shopmod creation, added update_as_(adj,tbl) option (currently disabled)
1.7        DG Rindner   9/6/12      Fixed path errors that prevented it from running in windows cygwin installation
"""
MYVERSION=1.7
#import cProfile
import getopt
import datetime
import sys
import os
import shutil
import glob
import time
import pdb
import subprocess
from pyDAG import InFile
from fnmatch import filter

# Initialize static variables.
enableUpdateASfiles=0
verbose = 0
PGM = "ge38"
ENG = "engine"
RIG = "dryrig"
#FML00 = "fmlist72_governors.cmd"
FML00="fmlist38_esn003_v2_02.cmd"
USINGFML00 = True
FORCE = False
today = datetime.date.today()
DATE = "%(Y)4i%(M)02i%(D)02i" \
    % {'Y': today.year, 'M': today.month, 'D': today.day}
SWVER = "0.0"
PERLOUT = "000.cmd"
VERN = "00"


# Exceptions
class Error(Exception):
    """Base class for exceptions in this module."""
    pass
class InputError(Error):
    """Exception raised for errors in the input.
    Attributes:
        message -- explanation of the error
    """
    def __init__(self, message, use=0):
        Error.__init__()
        self.message = message
        self.usage = use
    def __str__(self):
        if self.usage:
            return repr(self.message) + '\n\n%(doc)s' % {'doc':  __doc__}
        else:
            return repr(self.message)

def usage(code, msg=''):
    """Usage description"""
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

def lslrt(path):
    """Directory listing sorted by time, latest last"""
    flist = []
    for x in os.listdir(path):
        if not os.path.isdir(x) and os.path.isfile(x):
            flist.append((os.stat(x).st_mtime, x))
    flist.sort()
    dList = [x[1] for x in flist]
    return dList

def lsl(path):
    """Directory listing sorted alphabetically"""
    flist = []
    for x in os.listdir(path):
        if not os.path.isdir(x) and os.path.isfile(x):
            flist.append((os.stat(x).st_mtime, x))
    dListAlpha = [x[1] for x in flist]
    return dListAlpha

def fReplace(stext, rtext, iFile):
    """Replace string in file"""
    inf = open(iFile)
    outf = open('.temp', 'w')
    count = 0
    for s in inf.xreadlines():
        count += s.count(stext)
        outf.write(s.replace(stext, rtext))
    inf.close()
    outf.close()
    shutil.move('.temp', iFile)
    return count

def cat(file1, file2, oFile):
    """Cat two files to dest, return success as 0"""
    input1 = open(file1)
    input2 = open(file2)
    outf = open(oFile, 'w')
    for s in input1.xreadlines():
        outf.write(s)
    for s in input2.xreadlines():
        outf.write(s)
    input1.close()
    input2.close()
    outf.close()

def copy(file1, oFile):
    """Copy file to dest, return success as 0"""
    input1 = open(file1)
    outf = open(oFile, 'w')
    for s in input1.xreadlines():
        outf.write(s)
    input1.close()
    outf.close()

def adjtblList(locSARs):
    """Make .adj .tbl listing"""
    aList = []
    tList = []
    # Alphabetical directory listing, a-z
    dListAlpha = lsl('.')
    for ifile in dListAlpha:
        if ifile.count('.adj'):
            for tsType in locSARs:
                if ifile.count('_%(TS)s_' % {'TS': tsType}):
                    aList.append(ifile)
        elif ifile.count('.tbl'):
            for tsType in locSARs:
                if ifile.count('_%(TS)s_' % {'TS': tsType}):
                    tList.append(ifile)
    return (aList, tList)


def makeTest(testSARs):
    """Make test SAR trims, one at a time"""
    echoed00 = False
    dList = lslrt('.')
    (aList, tList) = adjtblList(testSARs)
    if aList.__len__() | tList.__len__():
        trimListTestSARs = aList + tList
        for i in trimListTestSARs:
            haveOther = False
            other = ""
            ROOT = i.replace('.adj', '').replace('.tbl', '')
            if i.count('.adj'):
                TYPE = "adj"
                OTYPE = "tbl"
                if trimListTestSARs.count(ROOT+'.'+OTYPE):
                    haveOther = 1
                    other = ROOT+'.'+OTYPE
            else:
                TYPE = "tbl"
                OTYPE = "adj"
                if trimListTestSARs.count(ROOT+'.'+OTYPE):
                    continue
            if haveOther:
                rOutFile = PGM+'v'+VERN+'_'+ROOT+'_adjtbl_'+DATE+'.cmd'
                pOutRoot = PGM+'v'+VERN+'_'+ROOT+'_adjtbl_'
                # Last occurence of root will be the latest
                pOutFile = rOutFile
                for ifile in dList:
                    if ifile.count(pOutRoot):
                        pOutFile = ifile
                    if verbose > 3:
                        print 'file=', i, 'rOutFile=', rOutFile, \
                            'pOutFile=', pOutFile
            else:
                rOutFile = PGM+'v'+VERN+'_'+ROOT+'_'+TYPE+'_'+DATE+'.cmd'
                pOutRoot = PGM+'v'+VERN+'_'+ROOT+'_'+TYPE+'_'
                # Last occurence of root will be the latest
                pOutFile = rOutFile
                for ifile in dList:
                    if ifile.count(pOutRoot):
                        pOutFile = ifile
                if verbose > 3:
                    print 'file=', i, 'rOutFile=', rOutFile, \
                        'pOutFile=', pOutFile

            makingNewOther = False
            if haveOther:
                if dList.count(pOutFile) > 0:
                    if os.stat(other).st_mtime > os.stat(pOutFile).st_mtime:
                        makingNewOther = True
                        print other, " changed..."
                else:
                    makingNewOther = True

            makingNew = False
            if dList.count(pOutFile) > 0:
                if verbose > 3:
                    print 'pOutFile=', pOutFile, 'pstat=', \
                        os.stat(pOutFile).st_mtime, \
                        'i=', i, 'istat=', os.stat(i).st_mtime
                if os.stat(i).st_mtime > os.stat(pOutFile).st_mtime:
                    makingNew = True
                    print i, " changed"
            else:
                makingNew = True
                print i, " changed"

            if FORCE:
                makingNewOther = True
                makingNew = True
                if (not echoed00):
                    print "Forcing rebuild of all..."
                    echoed00 = True

            # Create the new file
            if (not makingNew) & (not makingNewOther):
                print pOutFile, " up to date..."
                continue
            else:
                iFile = ""
                oFile = ""
           #     plStat = os.system("sar2trim -d -p %(PG)s -v %(VE)s %(FL)s" \
           #                   % {'PG': PGM, 'VE': VERN, 'FL': i})
                sar2trimPath=findPath('sar2trim')
              #  print sar2trimPath
                plStat=subprocess.Popen(['perl',sar2trimPath, '-d', '-p',PGM,'-v',VERN,i],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                plStat.communicate()[0]
                plerr=plStat.stderr.read()
                if not plerr:
#                    print "No errors"
                    targ = "v%(VE)s" % {'VE': VERN}
                    repl = "v%(VE)s_%(RT)s" % {'VE': VERN, 'RT': ROOT}
                    iFile = PERLOUT.replace(targ, repl).replace('scr', \
                                             "_%(TY)s_" % {'TY': TYPE})
                    fReplace(PERLOUT, iFile, PERLOUT)
                    shutil.move(PERLOUT, iFile)
                    if USINGFML00:
                        fReplace("SET VA AS_ADJ_STORE_REQ", \
                                     "!SET VA AS_ADJ_STORE_REQ", iFile)
                    if (not haveOther):
                        print 'made ', iFile
                        time.sleep(1)

            if haveOther:  # this must be a .tbl file given sorting done earlier
                plCmd = "sar2trim -d -p %(PG)s -v %(VE)s %(FI)s" \
                    % {'PG': PGM, 'VE': VERN, 'FI': other}
                if verbose > 3:
                    print plCmd
                sar2trimPath=findPath('sar2trim')
                print sar2trimPath
                plStat=subprocess.Popen(['perl',sar2trimPath, '-d', '-p',PGM,'-v',VERN,i],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                plStat.communicate()[0]
                plerr=plStat.stderr.read()
                if not plerr:
                    targ = "v%(VE)s" % {'VE': VERN}
                    repl = "v%(VE)s_%(RT)s" % {'VE': VERN, 'RT': ROOT}
                    oFile = PERLOUT.replace(targ, repl).replace('scr', \
                                             "_%(OTY)s_" % {'OTY': OTYPE})
                    fReplace(PERLOUT, oFile, PERLOUT)
                    shutil.move(PERLOUT, oFile)
                    if USINGFML00:
                        fReplace("SET VA AS_ADJ_STORE_REQ", \
                                     "!SET VA AS_ADJ_STORE_REQ", \
                                     oFile)
                    cat(iFile, oFile, rOutFile)
                    os.remove(iFile)
                    os.remove(oFile)
                    print 'made ', rOutFile
                    time.sleep(1)
        else:
            print "No more test SARs... continuing\n"

def listShm(shmFile):
    """Recursively list shm file and extract lists"""
    shmF = InFile(shmFile)
    shmF.load()
    shmF.gsub('#include', 'INCLUDE')
    shmF.stripComments('#')
    shmF.stripComments('%')
    shmF.stripComments('!')
    shmF.stripBlankLines()
    shmF.tokenize('. \r\n')
    rawlist = []
    fullList= []
    shmList = []
    for i in range(shmF.numLines):
       # if len(shmF.vS[i]) != 4:
       #     print shmF.vS[i]
       #     print "\nERROR(makeCMD.py/loadShm):  bad input in", shmFile, \
       #         "at", shmF.Line(i)
       #     exit(1)
       #Added ability to recursively #INCLUDE additional shopmods (.shm) lists
 #       print "Line is "+shmF.Line(i)
        if shmF.token(i,1).startswith('INCLUDE') :
            includeShmName= shmF.token(i, 2) + '.shm'
            shmList.append(includeShmName)
            includeShmFile=os.path.join(os.getcwd(), includeShmName)
            if os.path.isfile(includeShmFile):
                #Recursive call to listShm
                [recList,recFullList,recShmList] = listShm(includeShmFile)
                fullList=fullList+recFullList
                shmList=shmList+recShmList
#            pdb.set_trace
        else:
            filename = os.path.join(os.getcwd(), \
                            shmF.token(i, 1) + '.' + shmF.token(i, 2))
            if os.path.isfile(filename):
                rawlist.append(filename)
                fullList.append(filename)
            else:
                print("Could not find "+os.path.basename(filename))
    # cull repeats
    cleanlist = []
    for i in range(len(rawlist)):
        if not cleanlist.__contains__(rawlist[i]):
            cleanlist.append(rawlist[i])
    return cleanlist, fullList, shmList

def makeShmFolder(pOutFolder, loclist):
    """Copy files to working folder"""
    print 'processing', os.path.basename(pOutFolder)
    if os.path.isfile('as.adj'):
        shutil.copy('as.adj', os.path.join(pOutFolder, 'as.adj'))
    if os.path.isfile('as.tbl'):
        shutil.copy('as.tbl', os.path.join(pOutFolder, 'as.tbl'))
    #if os.path.isfile('sar2trim'):
   #     shutil.copy('sar2trim', os.path.join(pOutFolder, 'sar2trim'))    
   # pdb.set_trace()
#    if os.path.isfile(FML00):
#       print 'I found the fml00'
#       shutil.copy(FML00, os.path.join(pOutFolder, FML00))
    adjList = []
    adjSarDict = {}
    tblList = []
    tblSarDict = {}
    for ifile in reversed(loclist):
        if ifile.count('.adj'):
            outfname = os.path.join(pOutFolder, os.path.basename(ifile))
            outf = open(outfname, 'w')
            adjF = InFile(ifile)
            adjF.load()
            adjF.tokenize(' \n\t')
            for i in range(adjF.numLines):
                if adjF.Line(i).startswith('!') or adjF.Line(i).startswith('#') or adjF.Line(i).startswith('\n'):
                    outf.write(adjF.Line(i))
                else: #if len(adjF.LineS(i)) == 4:
                    name = adjF.token(i, 1)
                    if adjList.count(name) == 0:
                        adjList.append(name)
                        adjSarDict[name]=os.path.basename(ifile)
                        outf.write(adjF.Line(i))
                    else:
                        outf.write(' '.join(['!obsolete: overwritten by',adjSarDict[name], adjF.Line(i)]))
            outf.close()
        elif ifile.count('.tbl'):
            outfname = os.path.join(pOutFolder, os.path.basename(ifile))
            outf = open(outfname, 'w')
            tblF = InFile(ifile)
            tblF.load()
            tblF.tokenize(' \n\t\',')
            commenting = False
            for i in range(tblF.numLines):
                if tblF.Line(i).startswith('!'):
                    outf.write(tblF.Line(i))
                else:
                    if tblF.Line(i).count('#ADJUSTABLE'):
                        continue
                    if tblF.Line(i).count('$INPUT'):
                        name = tblF.token(i, 3)
                        if tblList.count(name) == 0:
                            tblList.append(name)
                            tblSarDict[name]=os.path.basename(ifile)
                            commenting = False
                            outf.write(tblF.Line(i-1))
                            outf.write(tblF.Line(i))
                        else:
                            commenting = True
                            outf.write(' '.join(['!obsolete:', tblF.Line(i-1)]))
                            outf.write(' '.join(['!obsolete: overwritten by', tblSarDict[name],tblF.Line(i)]))
                    elif commenting:
                       outf.write(''.join(['!obsolete:', tblF.Line(i)]))
                    else:
                        outf.write(tblF.Line(i))
            outf.close()
        elif ifile.count('.fml'):
            shutil.copy(ifile, os.path.join(pOutFolder, os.path.basename(ifile)))
        else:
            print os.path.basename(ifile)," not found"

def makeShm(shmFile):
    """Make shop mod from list in file"""
    pOutRoot = os.path.basename(shmFile).rpartition('.')[0]
    rOutFile = pOutRoot+'.cmd'
    home = os.getcwd()
    pOutFolder = os.path.join(home, pOutRoot)
    # load shm file and extract lists
    [loclist,fullList,shmList] = listShm(shmFile)
    

    # make folder to work the files
    recreateShm = 0
    if os.path.isfile(pOutRoot):
        print 'ERROR(makeCMD.py/makeShm): ', home, 'is already a file...quitting'
        exit(1)
    if not os.path.isdir(pOutRoot):
        os.mkdir(pOutRoot)
        recreateShm = 1
    else:
        if os.stat(shmFile).st_mtime > os.stat(pOutRoot).st_mtime:
            print "".join([pOutRoot,".shm is more recent than ",pOutRoot," folder"])
            recreateShm = 1
        else:
            for i in loclist:
    #note: only compares time stamps of  SARs explicitly included in this .shm file,
    #      does not check files recursively to determine whether to rebuild
                if os.stat(os.path.basename(i)).st_mtime > os.stat(pOutRoot).st_mtime:
                    print os.path.basename(i)," is more recent than ",pOutRoot," folder"
                    recreateShm = 1

    if recreateShm or FORCE:
        print "\ncleaning out", os.path.basename(pOutFolder)
        for ifile in glob.iglob(os.path.join(pOutFolder, '*')):
            if not os.path.basename(ifile) == 'CVS':
                try:
                    os.remove(ifile)
                except OSError:
                    shutil.rmtree(ifile,ignore_errors=True)
        
        locDlist = []
        locNameList =[]
        for i in loclist:
            locDlist.append(os.path.join(pOutFolder, os.path.basename(i)))
            locNameList.append(os.path.basename(i))
        # copy all files, including recursive, to working folder and go there
        makeShmFolder(pOutFolder, fullList)
       # print os.getcwd()
        os.chdir(pOutFolder)
      #  print os.getcwd()
       # pdb.set_trace()
        # Time sorted directory listing, newest last
        dList = lslrt('.')

        # Last occurence of root will be the latest
        pOutFile = rOutFile
        for ifile in dList:
            if ifile.count(pOutRoot) and ifile.count('.cmd'):
                pOutFile = ifile
        if verbose > 3:
            print "\n\n", "rOutFile=", rOutFile, "pOutFile=", pOutFile

        # Output file
        outFile = PERLOUT.replace(PGM, pOutRoot).replace('v'+VERN, '')
        outFile = outFile.replace('scr', '_')

        # Generate the file
        newFile, success = makeLocFiles(locDlist, dList, outFile, pOutFile)
        
        fullDlist = []
        fullNameList = []
        if not fullList==loclist:
            print 'Recursively included '+', '.join(shmList)
            for i in fullList:
                fullDlist.append(os.path.join(pOutFolder, os.path.basename(i)))
                fullNameList.append(os.path.basename(i))
            fullOutFile=outFile.replace('.cmd','_full.cmd')
            newFullFile, successFull = makeLocFiles(fullDlist,dList,fullOutFile, pOutFile)
            if successFull:
                print 'Created full trim file to go from baseline software v'+VERN
            if enableUpdateASfiles:
                updateASfiles(fullNameList,pOutRoot)
            deltaList=list(set(fullNameList).difference(set(locNameList)))
            #pdb.set_trace()
            os.mkdir(os.path.join(pOutFolder,'backup'))
            for i in deltaList:
                shutil.move(os.path.join(pOutFolder,i),os.path.join(pOutFolder,'backup',i))
        else:
            if enableUpdateASfiles:
                updateASfiles(locNameList,pOutRoot)
        
        
        newFileBase = os.path.basename(newFile)
        topFile = os.path.join(home, newFileBase)
        if success:
            shutil.copy(newFile, topFile)
        os.chdir(home)
    else:
        print pOutRoot," up to date"

def makeLoc(locSARs, loc):
    """Make SARs for defined location"""
    rOutFile = PGM+loc+'v'+VERN+'_'+DATE+'.cmd'
    pOutRoot = PGM+loc+'v'+VERN+'_'

    # Time sorted directory listing, newest last
    dList = lslrt('.')

    # Last occurence of root will be the latest
    pOutFile = rOutFile
    for ifile in dList:
        if ifile.count(pOutRoot):
            pOutFile = ifile
    if verbose > 3:
        print '\n\n', loc, 'rOutFile=', rOutFile, 'pOutFile=', pOutFile

    # .adj and .tbl listings
    (aList, tList) = adjtblList(locSARs)
    loclist = aList
    [loclist.append(i) for i in tList]

    # Output file
    outFile = PERLOUT.replace(PGM, PGM+loc).replace('scr', '_')

    # Generate the file
    makeLocFiles(loclist, dList, outFile, pOutFile)

def makeLocFiles(loclist, dList, outFile, pOutFile):
    """Make SAR out of loclist"""
    global USINGFML00
    echoed00 = False
    makingNew = False
    success = False
    for i in loclist:
        if dList.count(pOutFile) > 0:
            if verbose > 3:
                print 'pOutFile=', pOutFile, 'pstat=', \
                    os.stat(pOutFile).st_mtime, \
                    'i=', i, 'istat=', os.stat(i).st_mtime
            if os.stat(i).st_mtime > os.stat(pOutFile).st_mtime:
                makingNew = True
                print i, "changed"
        else:
            makingNew = True
    if dList.count(FML00) > 0:
        USINGFML00 = True
        if dList.count(pOutFile) > 0:
            if os.stat(FML00).st_mtime > os.stat(pOutFile).st_mtime:
                makingNew = True
                print FML00, "changed"
        else:
            makingNew = True
    else:
        print FML00, ' does not exist - assuming not needed...'
        USINGFML00 = False
    # Forcing
    if FORCE:
        makingNew = True
        if (not echoed00):
            print "Forcing rebuild of all..."
            echoed00 = True
    # Making new
    if makingNew:
        loclistStr = ""
        for i in loclist:
            loclistStr += (i + " ")
        if verbose > 3:
            print plCmd
        sar2trimPath=findPath('sar2trim')
        perlPath=findPath('perl')
      #  print perlPath
     #   print sar2trimPath
      #  print os.getcwd()
      #  pdb.set_trace()
        tester=" ".join([perlPath,sar2trimPath, '-d', '-p',PGM,'-v',VERN,loclistStr])
#       plStat=subprocess.Popen(['perl',sar2trimPath, '-d', '-p',PGM,'-v',VERN,loclistStr],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        plStat=subprocess.Popen(tester,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
#        cmdtest=subprocess.Popen(['perl',sar2trimPath,'-d','-p',PGM,'-v',VERN, '10_XX_070.tbl, 10_XX_071.tbl'],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        [output,plerr]=plStat.communicate()
        warnList = filter([plerr[:]], "Warning")
        errList = filter([plerr[:]], "Error")
 #       plerr=plStat.stderr.read()
        if errList:
            print >> sys.stderr, "Child was terminated:\n", errList
            print "failed", outFile, "continuing...\n"
            success = False
                #print plerr
                
        else:  # success
            if warnList:
                print "Warnings found in ", outFile,"\n"
                print warnList
                print "continuing...\n"
            if USINGFML00:
                fReplace("SET VA AS_ADJ_STORE_REQ", \
                             "!SET VA AS_ADJ_STORE_REQ", \
                             PERLOUT)
            fReplace(PERLOUT, outFile, PERLOUT)
            if USINGFML00:
                cat(PERLOUT, FML00, outFile)
            else:
                copy(PERLOUT, outFile)
            os.remove(PERLOUT)
            print 'made', outFile
            time.sleep(1)
            success = True
    else:
        print pOutFile, ' up to date...'
    return outFile, success
    # End loc SARS

def updateASfiles(nameList,pOutRoot):
 #   pdb.set_trace()
    #Sub function to run the BDB tools to generate updated AS files for given shopmod
    adjDlist = filter(nameList, "*.adj")
    tblDlist = filter(nameList, "*.tbl")
    print "Updating as.adj and as.tbl in "+pOutRoot+" folder"
    updateAdjArgs=['update_as_adj_win','-n','-f', pOutRoot]+adjDlist[:]
   # pdb.set_trace()
    statusAdj = subprocess.call(updateAdjArgs)
    #print "This is current: "+statusAdj.poll()
    #except OSError:
    #    print "Unable to update as.adj"
    #try:
    updateTblArgs=['update_as_tbl_win','-n','-f', pOutRoot]+tblDlist[:]
    statusTbl = subprocess.call(updateTblArgs)
    #statusTbl.wait()
   # pdb.set_trace()
    if os.path.exists(pOutRoot+"tbl.log"):
        print "Converting as.tbl to tables_def.h for PLM"
        statusCtblmkr=subprocess.Popen(['ctblmkr_GEneric_win','as.tbl']).communicate()[0]
#    except OSError:
#        print "Unable to update as.tbl or create tables_def.h"

def findPath(targetFunction):
        whichProc = subprocess.Popen(["which", targetFunction],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        [funcPathC, stdoutTemp] = whichProc.communicate()
       
        if funcPathC:
            cygpathProc = subprocess.Popen(["cygpath", "-w", funcPathC.rstrip()],stdout=subprocess.PIPE)
            [funcPathW, stdoutTemp] = cygpathProc.communicate()
        else:
            raise Exception("Unable to find "+targetFunction+", please check it exists in $PATH")
        return funcPathW.rstrip()


def main(argv):
    """Convert .adj/.tbl to .cmd"""
    global verbose, PGM, VERN, FORCE, PERLOUT, SWVER

    # Default _XX_ correspondence between file names and usage
    engSARs = ['AS', 'ET']
    dryRigSARs = ['AS', 'ET', 'DR']
    testSARs = ['XX']

    # Initialize

    # Options
    try:
        options, remainder = getopt.getopt(argv, \
          'd:fhp:Vv:', \
          ['debug=', 'force', 'help', 'program=', 'version', 'SW_Version=',])
    except getopt.GetoptError:
        usage(2)
    for opt, arg in options:
        if   opt in ('-h', '--help'):
            print usage(1)
        elif opt in ('-d', '--debug'):
            verbose = int(arg)
        elif opt in ('-f', '--force'):
            FORCE = True
        elif opt in ('-p', '--program'):
            PGM = arg
        elif opt in ('-v', '--SW_Version'):
            SWVER = arg
        elif opt in ('-V', '--version'):
            print 'makeCMD.py Version ',MYVERSION,' DG Rindner 10/04/11 Update shop mod function'
            exit(0)
        else: print usage(1)
        if remainder:
            print 'ERROR(makeCMD.py):  too many arguments:', remainder
            exit(1)

    # Assign static variables
    #SWVER = os.getcwd().rpartition('/')[2].strip()
    VERN = SWVER.replace('.', '').replace('v', '')
    print 'makeCMD.py:  making PDAP script cmd files for ',
    print 'program=%(PG)s, version=%(SWVER)s...' \
        % {'PG': PGM, 'SWVER': SWVER}
    PERLOUT = "%(PG)sv%(VE)sscr%(DATE)s.cmd" \
        % {'PG': PGM, 'VE': VERN, 'DATE': DATE}

    # Misc Test XX SARs
    makeTest(testSARs)

    # Engine SARs
    makeLoc(engSARs, ENG)
    time.sleep(0.5)

    # Dry Rig SARs
    makeLoc(dryRigSARs, RIG)
    time.sleep(0.5)

    # Shop Mods
    for shmFile in glob.iglob(os.path.join(os.getcwd(), '*.shm')):
        makeShm(shmFile)
        time.sleep(0.5)

    # Cleanup and quit
    if lsl('.').count('.temp'):
        os.remove('.temp')
    print "\nmakeCMD.py:  done."




if __name__ == '__main__':
    #sys.exit(cProfile.run("main(sys.argv[1:])"))
    sys.exit(main(sys.argv[1:]))


