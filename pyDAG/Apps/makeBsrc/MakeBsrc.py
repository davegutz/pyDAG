#!/usr/bin/env python
"""MakeBsrc:  Administer generation of Beacon source for Simulink
	-d [level] / --debug [level]
	    Use this verbosity level to debug program  [0]
	-h / --help
		Print this message and exit
	-V, --version
		Print version and quit \n"
Tests:
>>>python MakeBsrc.py -d 0
"""

# Settings
DATE = 'None'
usingIDLE = 0   # set to 1 for idle
verbose = 0

import termios
import sys
import os
import gzip
import getopt
import time
#import datetime

import Tkinter as Tk
import Tkconstants as Tkc
import tkMessageBox as tkM
import tkFileDialog as tkF

from pyDAG import InFile
from pyDAG import State as St
from pyDAG import mySystem as osu

TERMIOS = termios

# Exceptions
class Error(Exception):
    """Base class for exceptions in this module."""
    def __init__(self):
        Exception.__init__()

class InputError(Error):
    """Exception raised for errors in the input.
    Attributes:
    message -- explanation of the error
    """
    def __init__(self, message, usagev=0):
        Error.__init__()
        self.message 	= message
        self.usagev = usagev
    def __str__(self):
        """Generate message string"""
        if self.usagev:
            return repr(self.message) + \
                '\n\n%(doc)s' % {'doc':  __doc__}
        else:
            return repr(self.message)

def usagecb():
    """Display usage hint as callback"""
    usage(-1, 'Here''s how!')

def displayManual():
    """Display users manual callback"""
    usage(-1, 'write the f manual!')
        
def usage(code, msg=''):
    """Usage description"""
    print >> sys.stderr, __doc__
    if msg:
        print >> sys.stderr, msg
    if code >= 0:
        sys.exit(code)


#------------------------------------------------------------------------
# Name: MyUserInterfaceClass
# Desc: Tkinter based user interface class.
#------------------------------------------------------------------------
class _MyUserInterfaceClass(Tk.Frame): # pylint: disable=R0904
    """Class to drive Tkinter interface"""

    def __init__(self, master, emaster, geometry, structureInputs  ):

        (settingL, stateD) = structureInputs

        Tk.Frame.__init__(self, master)

        # state dictionary
        self.__stateD = stateD

        # main menu bar
        self.__menubar, self.__frame = \
            self.__initMainMenuBar(master, geometry)

       # Initialize buttons in main window
        self.__loadDispMain()

        # Initialize settings editor menu
        self.__setDic = dict(iter(settingL))

        # Create edit settings bar
        self.__editbar, self.__setFrame , self.__eframe = \
            self.__initEditSettingsBar(emaster, geometry)

        # Load and display settings window
        self.__loadSettingsFromFile()
        self.__entry = []
        self.__setEditor = []
        self.__setLabeler = []
        self.__setDescer = []
        self.__numEntries = self.__loadDispSet(settingL)
        self.__entriesChanged = 0
        self.__forceSave = 0
        self.__applySettings()

        if not usingIDLE: # Set window exit protocol, if needed.
            self.__eframe.protocol('WM_DELETE_WINDOW',
                                   self.__eframe.quit)
            self.__frame.protocol('WM_DELETE_WINDOW', self.__frame.quit)

    def __initMainMenuBar(self, master, geometry):
        """Initialize main menu bar"""

        (ar, xy) = geometry[:2]

        mb = Tk.Menu(master)
        frame = Tk.Toplevel(relief='ridge', borderwidth=2, menu=mb) 
        frame.geometry(ar + xy)
        master.config(menu=mb)

        # File
        fm = Tk.Menu(mb, tearoff=0) # dropdown
        mb.add_cascade(label='File', underline=0, menu=fm)
        # open
        fm.add_command(label='Open Settings', underline=0,
                              command=self.__loadApplySettings)
        # save
        fm.add_command(label='Save Settings', underline=0,
                              command=self.__saveSettings)
        # save as
        fm.add_command(label='Save Settings As', underline=0,
                              command=self.__saveSettingsAs)
        # exit
        fm.add_command(label='Exit', underline=0,
                              command=self.__exit)

        # Edit
        em = Tk.Menu(mb, tearoff=0) # dropdown
        mb.add_cascade(label='Edit', underline=0, menu=em)
        # settings
        em.add_command(label='Settings', underline=0,
                              command=self.__editSettings)

        # Help
        hm = Tk.Menu(mb, tearoff=0) # dropdown
        mb.add_cascade(label='Help', underline=0, menu=hm)
        # manual
        hm.add_command(label='Manual', underline=0,
                              command=displayManual)
        # about
        hm.add_command(label='About', underline=0,
                              command=usagecb)

        return (mb, frame)

    def __loadDispMain(self):
        """Initialize buttons in main window"""
        startRow = 0
        for (key, state) in self.__stateD.items():
            bname = state.buttonName()
            if verbose > 3:
                print 'name=', bname, 'key=', key, 'stype=', \
                    state.stype(), 'state=', state.permitted()
            if state.stype() == 'button':
                if state.permitted():
                    initialRelief = Tkc.RAISED
                else:
                    initialRelief = Tkc.FLAT
                b = Tk.Button(self.__frame, text=bname, \
                             relief=initialRelief, anchor=Tkc.W)
                state.widget(b)
                stateRow = state.row()+startRow
                stateCol = state.col()
                b.grid(row=stateRow, column=stateCol, \
                      sticky=Tkc.N+Tkc.E+Tkc.W)
                b.bind("<Double-Button-1>", state.callback())
            elif state.stype() == 'checkbutton':
                b = Tk.Checkbutton(self.__frame, text=bname,
                                      variable=state.stateInt, \
                                             anchor=Tkc.W)
                stateRow = state.row()+startRow
                stateCol = state.col()
                b.grid(row=stateRow, column=stateCol, \
                      sticky=Tkc.N+Tkc.E+Tkc.W)
                b.bind("<ButtonRelease-1>", state.callback())
            elif state.stype() == 'internal':
                pass
            else:
                print 'UNKNOWN state stype=', state.stype()
                exit(1)

    def __initEditSettingsBar(self, emaster, geometry):
        """Create the settings editor window"""

        (ar, xy, are, xye, flex) = geometry

        emaster.title('MakeBsrc Menu/Buttons')
        emaster.withdraw() # Suppress unwanted window
        eb = Tk.Menu(emaster)
        sf = Tk.Toplevel(relief='ridge', borderwidth=2, menu=eb)
        sf.geometry(are + xye)
        sf.resizable(flex, flex)
        sf.title('MakeBsrc Settings')
        ef = Tk.Toplevel(relief='ridge', borderwidth=2, menu=eb)
        ef.geometry(ar + xy)
        ef.resizable(flex, flex)

        # Setting editor menu bar
        emaster.config(menu=eb)
        efm = Tk.Menu(eb, tearoff=0) # dropdown

        # File
        eb.add_cascade(label='File', underline=0,  menu=efm)
        # open
        efm.add_command(label='Open Settings', underline=0,
                              command=self.__loadApplySettings)
        # save
        efm.add_command(label='Save Settings', underline=0,
                              command=self.__saveSettings)
        # save as
        efm.add_command(label='Save Settings As', underline=0,
                              command=self.__saveSettingsAs)
        # exit
        efm.add_command(label='Exit', underline=0,
                              command=self.__exit)

        # Help
        hpm = Tk.Menu(eb, tearoff=0) # dropdown
        eb.add_cascade(label='Help', underline=0, menu=hpm)
        # manual
        hpm.add_command(label='Manual', underline=0,
                            command=displayManual)
        # about
        hpm.add_command(label='About', underline=0,
                              command=usagecb)

        return (eb, sf, ef)

    def __loadDispSet(self, settingL):
        """Instantiate; load and display settings"""

        entryWidth = 18  # width of entry boxes

        i = 0
        self.__entry.append(Tk.StringVar())
        (value, desc) = self.__setDic['MYHOME']
        self.__setEditor.append(Tk.Entry(self.__setFrame,
            width=entryWidth, textvariable=self.__entry[i]))
        self.__setEditor[i].insert(0, value)
        self.__setEditor[i].grid(row=i, column=1)
        self.__setLabeler.append(Tk.Label(self.__setFrame,
                       width=12, anchor=Tkc.E, text='MYHOME'))
        bhome = Tk.Button(self.__setFrame, text='Browse',
                relief=Tkc.RAISED, command=self.__changeHome, 
                               anchor=Tkc.W)
        bhome.grid(row=i, column=0)

        self.__setDescer.append(Tk.Label(self.__setFrame,
                        width=48, anchor=Tkc.W, text=desc))
        self.__setDescer[i].grid(row=i, column=2)
        i += 1
        for (name, (value, desc)) in settingL:
            if name == 'MYHOME':
                continue
            self.__entry.append(Tk.StringVar())
            self.__setEditor.append(Tk.Entry(self.__setFrame,
                      width=entryWidth,textvariable=self.__entry[i]))
            self.__setEditor[i].insert(0, value)
            self.__setEditor[i].grid(row=i, column=1)
            self.__setLabeler.append(Tk.Label(self.__setFrame,
                      width=12, anchor=Tkc.E, text=name))
            self.__setLabeler[i].grid(row=i, column=0)
            self.__setDescer.append(Tk.Label(self.__setFrame,
                      width=48, anchor=Tkc.W, text=desc))
            self.__setDescer[i].grid(row=i, column=2)
            i = i+1
        return i

    def __loadApplySettings(self):
        """Load settings from file then apply to internal parameters"""
        if self.__loadSettingsFromFile():
            self.__applySettings()

    def __loadSettingsFromFile(self):
        """Load settings from chosen file; default from
        SETTINGLIST if cancelled"""
        setFile = tkF.askopenfilename(defaultextension='.mbs',
                             filetypes=[('MakeBsrc Project', '.mbs')])
        settingChanged = 0
        if setFile and os.path.isfile(setFile) and \
                os.path.getsize(setFile) > 0:
            settingFile = InFile(setFile)
            settingFile.load()
            settingFile.stripComments('#')
            settingFile.stripComments('%')
            settingFile.stripComments('!')
            settingFile.stripBlankLines()
            if settingFile.numLines > 0:
                settingFile.tokenize(' =\t\n')
                for i in range(settingFile.numLines):
                    (candidate, value) = (settingFile.token(i, 1),
                                          settingFile.token(i, 2))
                    if self.__setDic.has_key(candidate):
                        (oldValue, oldDesc) = \
                            self.__setDic[candidate]
                        if oldValue != value:
                            settingChanged += 1
                            self.__setDic[candidate] = \
                                (value, oldDesc)
                    else:
                        print 'UNKNOWN', settingFile.token(i, 1), \
                            '=', value
#                        exit(1)
            settingFile.closeFile()
            return settingChanged

    def __applySettings(self):
        """Apply settings to internal parameters for use"""
        entriesChanged = 0
        for i in range(self.__numEntries):
            name = self.__setLabeler[i]['text']
            oldValue = self.__setEditor[i].get()
            value = self.__setDic[name][0]
            if oldValue != value:
                entriesChanged += 1
                self.__entry[i].set(value)
        return entriesChanged

    def myhome(self):
        """Retrieve myhome parameter from dictionary"""
        myhome = self.__setDic['MYHOME'][0]
        return myhome

    def pgm(self):
        """Retrieve pgm parameter from dictionary"""
        pgm = self.__setDic['PGM'][0]
        return pgm

    def itpgm(self):
        """Retrieve itpgm parameter from dictionary"""
        itpgm = self.__setDic['ITPGM'][0]
        return itpgm

    def vero(self):
        """Retrieve vero parameter from dictionary"""
        vero = self.__setDic['VERO'][0]
        return vero

    def build(self):
        """Retrieve build parameter from dictionary"""
        build = self.__setDic['BUILD'][0]
        return build

    def vern(self):
        """Retrieve vern parameter from dictionary"""
        vern = self.__setDic['VERN'][0]
        return vern

    def sdaroot(self):
        """Retrieve sdaroot parameter from dictionary"""
        sdaroot = self.__setDic['SDAROOT'][0]
        return sdaroot

    def sdaname(self):
        """Retrieve sdaname parameter from dictionary"""
        sdaname = self.__setDic['SDANAME'][0]
        return sdaname

    def verlib(self):
        """Retrieve verlib parameter from dictionary"""
        verlib = self.__setDic['VERLIB'][0]
        return verlib

    def user(self):
        """Retrieve user parameter from dictionary"""
        user = self.__setDic['USER'][0]
        return user

    def dbgen(self):
        """Retrieve dbgen parameter from dictionary"""
        dbgen = self.__setDic['DBGEN'][0]
        return dbgen

    def dbcheck(self):
        """Retrieve dbcheck parameter from dictionary"""
        dbcheck = self.__setDic['DBCHECK'][0]
        return dbcheck

    def __changeHome(self):
        """Change home Beacon folder"""
        entriesChanged = 0
        homeReq = tkF.askdirectory()
        if homeReq and os.path.isdir(homeReq):
            for ihome in range(self.__numEntries):  # find MYHOME entry
                iHome = ihome
                name = self.__setLabeler[ihome]['text']
                if name == 'MYHOME':
                    break
            oldDesc = self.__setDic[name][1]
            self.__setDic[name] = (homeReq, oldDesc)
            os.chdir(homeReq)
            oldValue = self.__setEditor[iHome].get()
            if oldValue != homeReq:
                entriesChanged += 1
                self.__entry[iHome].set(homeReq)
        return entriesChanged

    def __editSettings(self):
        """Raise settings menu for editting"""
        self.__setFrame.deiconify()
        self.__setFrame.lift()

    def __exit(self):
        """Exit from class"""
        if self.__getEntries():
            ans = tkM.askyesnocancel(message='Save Settings?')
            if ans:
                self.__saveSettingsAs()
            elif ans == None:
                return
        else:
            print 'entries unchanged'
        print 'quitting...'
        self.__menubar.quit()

    def __getEntries(self):
        """Get current entries settings menu and return number changed"""
        self.__entriesChanged = 0
        for i in range(self.__numEntries):
            name = self.__setLabeler[i]['text']
            value = self.__setEditor[i].get()
            (oldValue, oldDesc) = self.__setDic[name]
            if oldValue != value:
                print 'changed:', name, ' from ', oldValue, ' to ', value
                self.__entriesChanged += 1
                self.__setDic[name] = (value, oldDesc)
        return self.__entriesChanged

    def __saveSettingsAs(self):
        """Save settings to file-as"""
        self.__forceSave = 1
        self.__saveSettings()
   
    def __saveSettings(self):
        """Save to file"""
        if self.__getEntries() or self.__forceSave:
            print 'MakeBsrc:  settings saving...',
            TIME = "%(hr)02i:%(mn)02i:%(sc)02i" \
                % {'hr': time.localtime().tm_hour, \
                      'mn': time.localtime().tm_min, \
                      'sc': time.localtime().tm_sec}
            setFile = tkF.asksaveasfilename(defaultextension='.mbs', \
                      filetypes=[('MakeBsrc Settings', '.mbs')])
            if setFile:
                f = open(setFile, 'w')
                f.write("# %(date)s at %(time)s\n"
                        % { 'date': DATE, 'time': TIME})
                f.write("# You may edit this file...at your peril\n")
                for (name, valdesc) in self.__setDic.items():
                    f.write("%(name)s=%(value)s"
                             % {'name':name, 'value':valdesc[0]})
                    f.write("\n")
                f.close()
                print 'done.'
            else:
                print 'MakeBsrc:  settings unchanged'
        else:
            print 'MakeBsrc:  settings unchanged'
   
    def __quit(self):
        """Self destruct"""
        if usingIDLE:
            self.__frame.destroy()
        else:
            self.__frame.quit()

def update(key):
    """General callbacks"""
    status = SM.update(key)
    for (skey, state) in status:
        if key != skey and state.stype() == 'button' and \
                state.enabled():
            if state.permitted():
                if (state.flat() or state.sunken()):
                    state.raiseButt()
            else:
                state.disabButt()

def checkBeaconConfig(lfile):
    """Check for Beacon configuration file"""
    if not os.path.isfile(lfile):
        SM.stateD('BEACONCONFIG').permitted(False)
        print 'MakeBsrc.py: ', lfile, 'missing.   Quitting.'
        exit(1)
    else:
        print 'MakeBsrc.py: ', lfile, 'exists...permit'
        SM.stateD('BEACONCONFIG').permitted(True)

def batchCopy(libDir, targetDir, sext):
    """Copy in the files having extension sext"""
    copied = 0
    copiedZ = 0
    skipped = 0
    skippedZ = 0
    for candFile in osu.lsl(libDir):
        #(root, sep, ext) = candFile.rpartition('.')
        root = candFile.rpartition('.')[0]
        ext = candFile.rpartition('.')[2]
        if ext == 'gz':
            root = root.rpartition('.')[0]
            ext = root.rpartition('.')[2]
        if '.'+ext == sext:
            sourceFile = libDir     + '/' + root + sext
            sourceFileGz = sourceFile + '.gz'
            targetFile = targetDir  + '/' + root + sext
            targetFileGz = targetFile + '.gz'
            dSourceFile = osu.getStamp(sourceFile)
            dSourceFileGz = osu.getStamp(sourceFileGz)
            dTargetFile = osu.getStamp(targetFile)
            dTargetFileGz = osu.getStamp(targetFileGz)
            if   dTargetFile >=  max(dSourceFile, dSourceFileGz):
                skipped += 1
            elif dTargetFileGz >= max(dSourceFile, dSourceFileGz):
                skippedZ += 1
            elif dSourceFile > dTargetFile:
                osu.copy(sourceFile, targetFile)
                print 'MakeBsrc.py:  copying', sourceFile
                copied += 1
            elif dSourceFileGz > dTargetFileGz:
                osu.copy(sourceFileGz, targetFileGz)
                print 'MakeBsrc.py:  copying', sourceFileGz
                copiedZ += 1
            elif dSourceFileGz > dTargetFile:
                print 'WARNING(MakeBsrc.py): ', sourceFileGz, \
                    'newer than', targetFile
            else:
                pass
    return (copied, copiedZ, skipped, skippedZ)

def checkCreateFileSys(event):
    """Create folders and/or check them"""
    if event:
        print event
    key = 'FILESYS'
    state = SM.stateD(key)
    if state.permitted() and state.raised():

        # myhome
        myhome = MUIC.myhome()
        beaconConfig = myhome + '/Beacon.config'

        # pgm
        pgm = MUIC.pgm()
        pgmDir = myhome + '/' + pgm

       # vero
        vero = MUIC.vero()
        veroDir = pgmDir + '/' + vero

        # bfsil
        bfsilDir = veroDir + '/buildForSimulink'

        # bdiag
        bdiagDir = veroDir + '/diagrams'
        badjDir = veroDir + '/adjustments'
        btblDir = veroDir + '/schedules'

        # bsbuild
        bsbuildDir = bfsilDir + '/bsbuild'
        bsbuildBuildDir = bfsilDir + '/bsbuild/build'
        build = MUIC.build()
        buildNameDir = bfsilDir + '/' + build

        # sdalib
        sdalibDir = MUIC.sdaroot() + '/' + MUIC.sdaname() + \
            'sda_lib/srs/' + MUIC.verlib()

        def checkAndMake(ldir):
            """Make folders"""
            if not os.path.isdir(ldir):
                os.mkdir(ldir)
                print 'MakeBsrc.py: made', ldir
            else:
                print 'MakeBsrc.py: ', ldir, 'exists...skip'

        checkAndMake(pgmDir)
        checkAndMake(veroDir)
        checkAndMake(bfsilDir)
        checkAndMake(bdiagDir)
        checkAndMake(badjDir)
        checkAndMake(btblDir)
        checkAndMake(bsbuildDir)
        checkAndMake(bsbuildBuildDir)
        checkAndMake(buildNameDir)

        # Check
        checkBeaconConfig(beaconConfig)

        # Baseline: get files
        # Baseline:  rm *.Z
        print 'MakeBsrc.py:  cleaning .Z files: ',
        count = 0
        for candFile in osu.lsl(bdiagDir):
            root = candFile.rpartition('.')[0]
            ext = candFile.rpartition('.')[2]
            Zfile = root + '.Z'
            if os.path.isfile(Zfile):
                os.remove(Zfile)
                count += 1
                print 'MakeBsrc.py:  removing', Zfile
        print count, 'file(s)'
        (cp, cz, sk, sz) = batchCopy(sdalibDir, bdiagDir, '.net') 
        print "MakeBsrc.py:  copied %(CP)s .net, copied %(CZ)s .net.gz"\
            % {'CP': cp, 'CZ': cz}
        print "              skip %(SK)s .net, skip %(SZ)s .net.gz"\
            % {'SK': sk, 'SZ': sz}
        (cp, cz, sk, sz) = batchCopy(sdalibDir, badjDir,  '.adj') 
        print "MakeBsrc.py:  copied %(CP)s, skipped %(SK)s .adj" \
            % {'CP': cp, 'SK': sk}
        (cp, cz, sk, sz) = batchCopy(sdalibDir, btblDir,  '.tbl') 
        print "MakeBsrc.py:  copied %(CP)s, skipped %(SK)s .tbl" \
            % {'CP': cp, 'SK': sk}

        # Compress .net
        count = 0 
        print "MakeBsrc.py:  compressing..."
        for candFile in osu.lsl(bdiagDir):
            root = candFile.rpartition('.')[0]
            ext = candFile.rpartition('.')[2]
            if ext == 'net':
                sourceFile = bdiagDir   + '/' + candFile
                targetFile = sourceFile + '.gz'
                f_in = open(sourceFile)
                f_out = gzip.open(targetFile, 'wb')
                f_out.writelines(f_in)
                f_out.close()
                f_in.close()
                os.remove(sourceFile)
                count += 1
                print ".",
                sys.stdout.flush()
        if count:
            print ""
        print "MakeBsrc.py:  compressed", count, ".net files"

        # Empty out bfsilDir
        print "MakeBsrc.py:  cleaning", bfsilDir, '...',
        count = 0
        for candFile in osu.lsl(bfsilDir):
            if os.path.isfile(candFile):
                os.remove(candFile)
                count += 1
        print "removed", count, "file(s)"
        
        # Copy in the files
        (cp, cz, sk, sz) = batchCopy(bdiagDir, bfsilDir, '.net') 
        print "MakeBsrc.py:  copied %(CP)s .net, copied %(CZ)s .net.gz,"\
            % {'CP': cp, 'CZ': cz}
        print "              skip %(SK)s .net, skip %(SZ)s .net.gz" \
            % {'SK': sk, 'SZ': sz}
        (cp, cz, sk, sz) = batchCopy(badjDir,  bfsilDir, '.adj') 
        print "MakeBsrc.py:  copied %(CP)s, skipped %(SK)s .adj" \
            % {'CP': cp, 'SK': sk}
        (cp, cz, sk, sz) = batchCopy(btblDir,  bfsilDir, '.tbl') 
        print "MakeBsrc.py:  copied %(CP)s, skipped %(SK)s .tbl" \
            % {'CP': cp, 'SK': sk}



        # Uncompress for full build
        if SM.stateD('FULLBUILD').stateInt.get():
            print 'MakeBsrc.py:  uncompressing...'
            count = 0
            for candFile in osu.lsl(bfsilDir):
                root = candFile.rpartition('.')[0]
                ext = candFile.rpartition('.')[2]
                if ext == 'gz':
                    root = root.rpartition('.')[0]
                    ext = root.rpartition('.')[2]
                    if ext == 'net':
                        targetFile = bfsilDir   + '/' + root + '.net'
                        sourceFile = targetFile + '.gz'
                        f_in = gzip.open(sourceFile, 'rb')
                        f_out = open(targetFile, 'wb')
                        f_out.write(f_in.read())
                        f_out.close()
                        f_in.close()
                        os.remove(sourceFile)
                        count += 1
                        print '.',
                        sys.stdout.flush()
            if count:
                print ''
            print 'MakeBsrc.py:  uncompressed', count, '.net.gz files'


        # temp code
        ans = tkM.askokcancel(message='Succeed with files?')
        if ans:
            state.disabButt()
            state.sinkButt()
            update(key)
        else:
            state.enabButt()

def importBuildBaseline(event):
    """Go get the baseline software from library"""
    if event:
        print event
    key = 'BASELINE'
    state = SM.stateD(key)
    if state.permitted() and state.raised():
        ans = tkM.askokcancel(message= \
                             'Succeed with import baseline?')
        if ans:
            state.disabButt()
            state.sinkButt()
            update(key)
        else:
            state.enabButt()

def buildSAR(event):
    """Perform the build sar sequence for a SAR report .pdf generation"""
    if event:
        print event
    key = 'BUILDSAR'
    state = SM.stateD(key)
    if state.permitted() and state.raised():
        ans = tkM.askokcancel(message= \
                             'Succeed with building SAR review package?')
        if ans:
            state.disabButt()
            state.sinkButt()
            update(key)
        else:
            state.enabButt()


def buildSACSAR(event):
    """Set checkbox to do a SAC style SAR report"""
    if SM.stateD('SACBUILDSAR').stateInt.get():
        print 'setSACBUILDSAR', event.type
    else:
        print 'unsetSACBUILDSAR'
    update('SACBUILDSAR')

def setFullBuild(event):
    """Set full build checkbox callback to do a complete build"""
    if SM.stateD('FULLBUILD').stateInt.get():
        print 'setFullBuild', event.type
        SM.stateD('FILESYS').raiseButt()
        SM.stateD('FILESYS').enabButt()
    else:
        print 'unsetFullBuild'
    update('FULLBUILD')

def setAutoPutit(event):
    """Set auto putit checkbox callback to automatically put to drop"""
    if SM.stateD('AUTOPUTIT').stateInt.get():
        print 'setAutoPutit', event.type
    else:
        print 'unsetAutoPutit'
    update('AUTOPUTIT')

def setPrinting(event):
    """Set printing checkbox callback"""
    if SM.stateD('PRINTING').stateInt.get():
        print 'setPrinting', event.type
    else:
        print 'unsetPrinting'
    update('PRINTING')

def checkSarsPresent(event):
    """Check for SARS present, callback"""
    if event:
        print event
    key = 'SARSPRESENT'
    state = SM.stateD(key)
    update(key)
    print key, '=', state.permitted()

def genCode(event):
    """Generate code callback"""
    if event:
        print event
    key = 'GENCODE'
    state = SM.stateD(key)
    if state.permitted() and state.raised():
        ans = tkM.askokcancel(message='Succeed with code?')
        if ans:
            state.disabButt()
            state.sinkButt()
            update(key)
        else:
            state.enabButt()

def buildTbl(event):
    """Build from .tbl files"""
    if event:
        print event
    key = 'BUILDTBL'
    state = SM.stateD(key)
    if state.permitted() and state.raised():
        ans = tkM.askokcancel(message='Succeed with tables?')
        if ans:
            state.disabButt()
            state.sinkButt()
            update(key)
        else:
            state.enabButt()

def buildAdj(event):
    """Build from .adj files"""
    if event:
        print event
    key = 'BUILDADJ'
    state = SM.stateD(key)
    if state.permitted() and state.raised():
        ans = tkM.askokcancel(message='Succeed with adjusts?')
        if ans:
            state.disabButt()
            state.sinkButt()
            update(key)
        else:
            state.enabButt()

def dbGen(event):
    """Generate Beacon data base files"""
    if event:
        print event
    key = 'DBGEN'
    state = SM.stateD(key)
    if state.permitted() and state.raised():
        ans = tkM.askokcancel(message='Succeed with dbGen?')
        if ans:
            state.disabButt()
            state.sinkButt()
            update(key)
        else:
            state.enabButt()

def dbCheck(event):
    """Check Beacon data base files"""
    if event:
        print event
    key = 'DBCHECK'
    state = SM.stateD(key)
    if state.permitted() and state.raised():
        ans = tkM.askokcancel(message='Succeed with dbCheck?')
        if ans:
            state.disabButt()
            state.sinkButt()
            update(key)
        else:
            state.enabButt()

def buildBsrc(event):
    """Build the Beacon source files .c and .h"""
    if event:
        print event
    key = 'BSRC'
    state = SM.stateD(key)
    if state.permitted() and state.raised():
        ans = tkM.askokcancel(message='Succeed with building bsrc?')
        if ans:
            state.disabButt()
            state.sinkButt()
            update(key)
        else:
            state.enabButt()

#  root needs to be here so State.py knows to get Tkinter stuff
TKROOT = Tk.Tk()

# Application setting menu dictionary
# entry format = (key, (defaultValue, description))
SETTINGLIST = [('MYHOME', ('~/beacon',
                           'Home folder for Beacon (containing PGMs)')),
               ('PGM',  ('advanced', 
   'Program name in sdalib.  UNIX higher level folder name above VERO')),
               ('ITPGM',  ('advanced', 'Program name used by it-tools')),
               ('VERO', ('v0.0', 'Baseline of this build.')),
               ('BUILD',('v00a', 'Name of build in Simulink.')),
               ('VERN', ('v0.1', 'Expected new version (for reports)')), 
               ('SDAROOT',('/afs/ae.ge.com','Location of sdalib')),
               ('SDANAME',('advanced', 'Name of sdalib')),
               ('VERLIB', ('v0.0', 'Version of library in sdalib')),
               ('USER',   ('aw0000t', 'Your UNIX user name')),
               ('DBGEN',  ('dbGen5', 'Name dbGen for your program')),
               ('DBCHECK',('dbCheck5', 'Name dbCheck for your program'))]


#------------------------------------------------------------------------
# State dictionary
# entry format = (key, State(stype, ('depends1', ...), presentState,
#                            butName, callback,
#                            description))
stateList = [('FILESYS',    
           St.State('button',  (0, 0), [], True,
                 'Setup File Sys', checkCreateFileSys,
                 'Check and create folder structure vs. settings')),
          ('BEACONCONFIG',    
           St.State('internal',  (None, None), ['FILESYS'], False,
                 'Beacon configuration present', checkBeaconConfig,
                 'Beacon.config file available in right place')),
          ('SARSPRESENT',    
           St.State('internal',  (None, None), ['FILESYS'], False,
                 'SARs Present', checkSarsPresent,
                 'SARS are available for processing')),
          ('BASELINE',
           St.State('button',  (1, 0), ['FILESYS'], False,
                 'Build Baseline', importBuildBaseline,
                 'Make a complete build from totally raw library')),
          ('FULLBUILD',
           St.State('checkbutton',  (0, 1), [], False,
                 'Generate complete build', setFullBuild,
                 'Use all nets and all SARs to make all .c/.h/.f')),
          ('AUTOPUTIT',
           St.State('checkbutton',  (1, 1), [], False,
                 'Automatically put changes', setAutoPutit,
                 'Run the it-tools putit command on SARs')),
          ('PRINTING',
           St.State('checkbutton',  (2, 1), [], False,
                 'Print all .pdf', setPrinting,
                 'Print all the .pdf each .net file processed')),
          ('BUILDSAR',
           St.State('button',  (2, 0), ['FILESYS', 'SARSPRESENT'], False,
                 'Build Review Pkg', buildSAR,
                 'Run buildsar tool to make review package')),
          ('SACBUILDSAR',
           St.State('checkbutton',  (3, 1), [], False,
                 'Build SAC Review Pkg', buildSACSAR,
                 'Run buildsar tool for SAC-specific SAR package')),
          ('GENCODE',
           St.State('button',  (3, 0),
                 ['BEACONCONFIG', 'FILESYS', 'SARSPRESENT'], False,
                 'Generate Code', genCode,
                 'Consolidate SARS and generate code')),
          ('BUILDTBL',
           St.State('button',  (4, 0), ['GENCODE'], False,
                 'Generate TBL', buildTbl,
                 'Process the .tbl table trims')),
          ('BUILDADJ',
           St.State('button',  (5, 0), ['GENCODE'], False,
                 'Generate ADJ', buildAdj,
                 'Process the .adj adjustment trims')),
          ('DBGEN',
           St.State('button',  (6, 0), ['BUILDTBL', 'BUILDADJ'], False,
                 'Generate BDB', dbGen,
                 'Generate Beacon Database')),
          ('DBCHECK',
           St.State('button',  (7, 0), ['DBGEN'], False,
                 'Check BDB', dbCheck,
                 'Check the Beacon Database')),
          ('BSRC',
           St.State('button',  (8, 0), ['DBCHECK'], False,
                 'Build the BSRC folder', buildBsrc,
                 'Consolidate files for move to Simulink'))
          ]
STATEDICTIONARY = dict(stateList)
SM = St.StateMachine(STATEDICTIONARY, verbose)
# load settings and make them global
#    root = Tk.Tk()
TKROOT.title('MakeBsrc Root')

#root2 = Tk.Toplevel()
#root2.title('MakeBsrc MAIN')
ROOT3 = Tk.Toplevel()
MUIC = _MyUserInterfaceClass(TKROOT,    # Set up the main GUI 
                              ROOT3,     # editor
                              ('400x400',# MakeBsrc Width & Height
                              '+20+20',  # Initial X/Y screen loc
                              '640x280', # settings Width & Height
                              '+420+220',# Edit X/Y screen loc
                              1),        # Resizing turned off
                              (SETTINGLIST, 
                              STATEDICTIONARY))



# Main
def main(argv):
    """Main"""

    # Initialize static variables.
    global verbose  # pylint: disable=W0603

    # Initialize
    #today = datetime.date.today()
    #DATE = "Automatically generated by MakeBsrc:  \
        #%(Y)04i-%(M)02i-%(D)02i" \
        # % {'Y': today.year, 'M': today.month, 'D': today.day}

    # Options
    try:
        options, remainder = getopt.getopt(argv, 'd:hV', \
                                ['debug=', 'help', 'version'])
    except getopt.GetoptError:
        usage(2)
    for opt, arg in options:
        if opt in ('-d', '--debug'):
            verbose = int(arg)
            print 'mainBsrc verbose=', verbose
        elif   opt in ('-h', '--help'):
            print usage(1)
        elif opt in ('-V', '--version'):
            print 'MakeBsrc.py Version 1.0.  DA Gutz 8/5/09'
            exit(0)
        else: print usage(1)
    if len(remainder) > 0:
        print usage(1)

    SM.verbose(verbose)
    
    #path = os.getenv('PATH')

    TKROOT.withdraw()
    if not usingIDLE:   # Avoid IDLE or other Tkinter based IDEs
        TKROOT.mainloop() # Outer event loop



if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
