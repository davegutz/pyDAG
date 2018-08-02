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
import shutil
import subprocess
import glob

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
        self.message = message
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
        
def usage(code, msg=None):
    """Usage description"""
    print >> sys.stderr, __doc__
    if msg is not None:
        print >> sys.stderr, msg
    if code >= 0:
        print '****makeBsrc.py:  bad input string on command line'
        sys.exit(code)


#------------------------------------------------------------------------
# Name: MyUserInterfaceClass
# Desc: Tkinter based user interface class.
#------------------------------------------------------------------------
class _MyUserInterfaceClass(Tk.Frame): # pylint: disable=R0904
    """Class to drive Tkinter interface"""

    def __init__(self, master, emaster, geometry, structureInputs  ):

        (settingL, stateD) = structureInputs

        # Folder names
        self.veroDir = None
        self.bsbuildDir = None
        self.badjDir = None
        self.pgmDir = None
        self.beaconConfig = None
        self.bfsilDir = None
        self.blineDir = None
        self.blinebsrcDir = None
        self.blinelbsrcDir = None
        self.bsbuildBuildDir = None
        self.sdalibDir = None
        self.btblDir = None
        self.bdiagDir = None
        self.buildNameDir = None
        self.modDir = None
        self.bmodDir = None

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
        userHome = os.getenv('USERPROFILE') or  os.getenv('HOME')
        self.__dotFile = os.path.join(userHome, '.makeBsrc')
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
                                   variable=state.stateInt,
                                   onvalue=0, offvalue=1,
                                   anchor=Tkc.W)
                state.widget(b)
                stateRow = state.row()+startRow
                stateCol = state.col()
                b.grid(row=stateRow, column=stateCol, \
                      sticky=Tkc.N+Tkc.E+Tkc.W)
                b.bind("<ButtonRelease-1>", state.callback())
            elif state.stype() == 'internal':
                pass
            else:
                print 'ERROR(makeBsrc.py/loadDispMain):  UNKNOWN state stype=',
                print state.stype()
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
        entryWidth = 14  # width of entry boxes
        browseWidth = 8  # width of left column containing browse buttons
        descrWidth = 60  # width of right column containing descriptions
        i = 0
        for (name, (value, desc)) in settingL:
            self.__setLabeler.append(Tk.Label(self.__setFrame,
                                              width=browseWidth,
                                              anchor=Tkc.E, text=name))
            if name == 'MYHOME':
                bhome = Tk.Button(self.__setFrame, text='Browse',
                                  relief=Tkc.RAISED,
                                  command=self.__changeHome, 
                                  anchor=Tkc.E)
                bhome.grid(row=i, column=0)
            elif name == 'SDAROOT':
                broot = Tk.Button(self.__setFrame, text='Browse',
                                  relief=Tkc.RAISED,
                                  command=self.__changeRoot, 
                                  anchor=Tkc.E)
                broot.grid(row=i, column=0)
            else:
                self.__setLabeler[i].grid(row=i, column=0)
            self.__entry.append(Tk.StringVar())
            self.__setEditor.append(Tk.Entry(self.__setFrame,
                                             width=entryWidth,
                                             textvariable=self.__entry[i]))
            self.__setEditor[i].insert(0, value)
            self.__setEditor[i].grid(row=i, column=1)
            self.__setDescer.append(Tk.Label(self.__setFrame,
                                             width=descrWidth,
                                             anchor=Tkc.W,
                                             text=desc))
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
        setFile = None
        if self.__dotFile and os.path.isfile(self.__dotFile):
            dotFileObj = InFile(self.__dotFile)
            dotFileObj.load()
            dotFileObj.stripComments('#')
            dotFileObj.stripComments('%')
            dotFileObj.stripComments('!')
            dotFileObj.stripBlankLines()
            if dotFileObj.numLines > 0:
                dotFileObj.tokenize(' =\t\n')
                for i in range(dotFileObj.numLines):
                    (variable, value) = (dotFileObj.token(i, 1), \
                                             dotFileObj.token(i, 2))
                    if variable == 'setFile':
                        setFile = value
                    else:
                        print 'UNKNOWN', dotFileObj.token(i, 1), '=', value
            dotFileObj.closeFile()
        if not setFile:
            setFile = tkF.askopenfilename(defaultextension='.mbs',
                                      filetypes=[('MakeBsrc Project', '.mbs')],
                                      title='Open .mbs configuration file')
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
            settingFile.closeFile()
            dotFile = open(self.__dotFile, 'w')
            dotFile.write("setFile=%(setFile)s\n" % { 'setFile': setFile})
            dotFile.close()
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
        homeReq = tkF.askdirectory(initialdir=self.myhome())
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

    def __changeRoot(self):
        """Change root SDA folder"""
        entriesChanged = 0
        #rootReq = tkF.askdirectory(initialdir=os.path.dirname(self.sdaroot()))
        rootReq = tkF.askdirectory(initialdir=self.sdaroot())
        if rootReq and os.path.isdir(rootReq):
            for i in range(self.__numEntries):  # find SDAROOT entry
                iHome = i
                name = self.__setLabeler[i]['text']
                if name == 'SDAROOT':
                    break
            oldDesc = self.__setDic[name][1]
            self.__setDic[name] = (rootReq, oldDesc)
            oldValue = self.__setEditor[iHome].get()
            if oldValue != rootReq:
                entriesChanged += 1
                self.__entry[iHome].set(rootReq)
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
                g = open(self.__dotFile, 'w')
                g.write("setFile=%(setFile)s\n" % { 'setFile': setFile})
                g.close()
                print 'done.'
            else:
                print 'MakeBsrc:  settings unchanged'
        else:
            print 'MakeBsrc:  settings unchanged'

    def makeNames(self):
        """Make folder names"""
        # myhome
        myhome = self.myhome()
        self.beaconConfig = ''.join([myhome, '/Beacon.config'])

        # pgm
        pgm = self.pgm()
        self.pgmDir = os.path.join(myhome, pgm)

       # vero
        vero = self.vero()
        self.veroDir = os.path.join(self.pgmDir, vero)

        # bfsil
        self.bfsilDir = os.path.join(self.veroDir, 'buildForSimulink')

        # bsrc
        self.blineDir = os.path.join(self.bfsilDir, 'bline')
        self.blinebsrcDir = os.path.join(self.blineDir, 'bsrc')
        self.blinelbsrcDir = os.path.join(self.blineDir, 'lbsrc')

        # bdiag
        self.bdiagDir = os.path.join(self.veroDir, 'diagrams')
        self.badjDir = os.path.join(self.veroDir, 'adjustments')
        self.btblDir = os.path.join(self.veroDir, 'schedules')
        self.modDir = os.path.join(self.veroDir, 'mods')
        self.bmodDir = os.path.join(self.veroDir, 'mods_bline')

        # bsbuild
        self.bsbuildDir = os.path.join(self.bfsilDir, 'bsbuild')
        self.bsbuildBuildDir = os.path.join(self.bfsilDir, 'bsbuild', 'build')

        build = self.build()
        self.buildNameDir = os.path.join(self.bfsilDir, build)

        # sdalib
        self.sdalibDir = os.path.join(self.sdaroot(), \
                                     ''.join([self.sdaname(), 'sda_lib']), \
                                     'srs', self.verlib())

    def checkAndCreate(self):
        """Check and create folders"""
        checkAndMake(self.pgmDir)
        checkAndMake(self.veroDir)
        checkAndMake(self.bfsilDir)
        checkAndMake(self.blineDir)
        checkAndMake(self.blinebsrcDir)
        checkAndMake(self.blinelbsrcDir)
        checkAndMake(self.bdiagDir)
        checkAndMake(self.badjDir)
        checkAndMake(self.btblDir)
        checkAndMake(self.modDir)
        checkAndMake(self.bmodDir)
        checkAndMake(self.bsbuildDir)
        checkAndMake(self.bsbuildBuildDir)
        checkAndMake(self.buildNameDir)
        checkBeaconConfig(self.beaconConfig)

    def baselineGetFiles(self):
        """Baseline: get files"""
        print 'baselineGetFiles:  removing compressed files: ',
        print removeCompressed(self.bdiagDir), 'file(s)'
        (cp, cz, sk, sz) = batchCopy(self.sdalibDir, self.bdiagDir, '.net') 
        print "baselineGetFiles:  copied %(CP)s .net, copied %(CZ)s .net.gz"\
            % {'CP': cp, 'CZ': cz}
        print "                     skip %(SK)s .net, skip %(SZ)s .net.gz"\
            % {'SK': sk, 'SZ': sz}
        (cp, cz, sk, sz) = batchCopy(self.sdalibDir, self.badjDir,  '.adj') 
        print "baselineGetFiles:  copied %(CP)s, skipped %(SK)s .adj" \
            % {'CP': cp, 'SK': sk}
        (cp, cz, sk, sz) = batchCopy(self.sdalibDir, self.btblDir,  '.tbl') 
        print "baselineGetFiles:  copied %(CP)s, skipped %(SK)s .tbl" \
            % {'CP': cp, 'SK': sk}

        # Compress .net
        count = 0 
        print "baselineGetFiles:  in bdiagDir compressing..."
        for candFile in osu.lsl(self.bdiagDir):
            ext = candFile.rpartition('.')[2]
            if ext == 'net':
                sourceFile = os.path.join(self.bdiagDir, candFile)
                targetFile = ''.join([sourceFile, '.gz'])
                f_in = open(sourceFile)
                f_out = gzip.open(targetFile, 'wb')
                f_out.writelines(f_in)
                f_out.close()
                f_in.close()
                os.remove(sourceFile)
                count += 1
                sys.stdout.write(".")
                sys.stdout.flush()
        if count:
            print ""
        print "baselineGetFiles:  compressed", count, ".net files"
   
    def emptyOutBfsilDir(self):
        """Empty out bfsilDir"""
        print "emptyOutBfsilDir:  cleaning", self.bfsilDir, '...',
        count = 0
        for candFile in osu.lsl(self.bfsilDir):
            if os.path.isfile(candFile):
                os.remove(candFile)
                count += 1
        print "removed", count, "file(s)"

    def copyInTheFiles(self):
        """Copy in the files"""
        (cp, cz, sk, sz) = batchCopy(self.bdiagDir, self.bfsilDir, '.net') 
        print "copyInTheFiles:  copied %(CP)s .net, copied %(CZ)s .net.gz,"\
            % {'CP': cp, 'CZ': cz}
        print "                     skip %(SK)s .net, skip %(SZ)s .net.gz" \
            % {'SK': sk, 'SZ': sz}
        (cp, cz, sk, sz) = batchCopy(self.badjDir,  self.bfsilDir, '.adj') 
        print "copyInTheFiles:  copied %(CP)s, skipped %(SK)s .adj" \
            % {'CP': cp, 'SK': sk}
        (cp, cz, sk, sz) = batchCopy(self.btblDir,  self.bfsilDir, '.tbl') 
        print "copyInTheFiles:  copied %(CP)s, skipped %(SK)s .tbl" \
            % {'CP': cp, 'SK': sk}

    def uncompressForFullBuild(self):
        """Uncompress for full build"""
        if SM.stateD('FULLBUILD').stateInt.get():
            print 'uncompressForFullBuild:  uncompressing for full build...'
            count = 0
            for candFile in osu.lsl(self.bfsilDir):
                ext = candFile.rpartition('.')[2]
                root = candFile.rpartition('.')[0]
                if ext == 'gz':
                    ext = root.rpartition('.')[2]
                    root = root.rpartition('.')[0]
                    if ext == 'net':
                        targetFile = os.path.join(self.bfsilDir, \
                                                      ''.join([root, '.net']))
                        sourceFile = ''.join([targetFile, '.gz'])
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
            print 'uncompressForFullBuild:  uncompressed', count, \
                '.net.gz files'

    def copyTheFilesToBsrc(self):
        """Copy the files over to BSRC for distribution"""
        count = 0
        for candFile in glob.iglob(os.path.join(self.bfsilDir, '*.c')):
            targetFile = os.path.join(self.blinebsrcDir, os.path.basename(candFile))
            shutil.copyfile(candFile, targetFile)
            count += 1
        for candFile in glob.iglob(os.path.join(self.bfsilDir, '*.h')):
            if candFile == 'tables_def.h':
                targetFile = os.path.join(self.blinelbsrcDir, os.path.basename(candFile))
                shutil.copyfile(candFile, targetFile)
            else:
                targetFile = os.path.join(self.blinebsrcDir, os.path.basename(candFile))
                shutil.copyfile(candFile, targetFile)
            count += 1
        print 'copyTheFilesToBsrc: ', count, 'files'
            
# Copy to pc
#cd $BFSIL
#rm -rf $BSRC $LBSRC $FSRC
#>/dev/null mkdir $BSRC  2>&1
#>/dev/null mkdir $LBSRC 2>&1
#>/dev/null mkdir $FSRC  2>&1
#if test " $FULLBUILD" -eq " 1" 
#then
#    >/dev/null compress $BFSIL/*.net 2>&1 3>&1
#fi
#>/dev/null mv *.c $BSRC
#>/dev/null mv *.h $BSRC
#>/dev/null mv $BSRC/tables_def.h $LBSRC/.
#>/dev/null mv *.f $FSRC
#cp csci*.dat $BSRC
#cp as.adj $BSRC    #as.tbl not needed; tables_def.h used instead



    def genBsrc(self):
        """Generate .h and .c files from .net"""
        monF = 'code_report'
        count = 0
        nList = []
        for candFile in osu.lsl(self.bfsilDir):
            ext = candFile.rpartition('.')[2]
            root = candFile.rpartition('.')[0]
            if ext == 'net':
                nList.append(candFile)
        monFp = open(monF, 'w')
        subprocess.PIPE = monFp
        for myFile in nList:
            nFile = os.path.join(self.bfsilDir, myFile)
            dnFile = osu.get_stamp(nFile)
            # remove old ones
            making = 0
            ext = myFile.rpartition('.')[2]
            root = myFile.rpartition('.')[0]
            hFile = os.path.join(self.bfsilDir, ''.join([root, '.h']))
            cFile = os.path.join(self.bfsilDir, ''.join([root, '.c']))
            if os.path.isfile(hFile):
                dhFile = osu.get_stamp(hFile)
                if dnFile > dhFile:
                    os.remove(hFile)
                    making = 1
            if os.path.isfile(cFile):
                dcFile = osu.get_stamp(cFile)
                if dnFile > dcFile:
                    os.remove(cFile)
                    making = 1
            if making:
                cmd3 = "sed -n '/The DISCUS and HONEYWELL options require the global precision/,/Internal flag reset to SINGLE/!p'"
                if sys.platform == 'darwin':
                    cmd1 = "touch %(HFILE)s; touch %(CFILE)s;" \
                        %{'HFILE': hFile, 'CFILE': cFile}
                    cmd2 = "sed -n '//p'"
                else:
                    cmd1 = "/afs/ae.ge.com/apps/beacon7/bin/codegen %(FILE)s -list_var -options_file=$HOME/Beacon.config -language=C" %{'FILE': myFile}
                    cmd2 = "sed -n '/--%/p'"
                try:
                    p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
                    p2 = subprocess.Popen(cmd2, stdin=p1.stdout,
                                          stdout=subprocess.PIPE, shell=True)
                    p3 = subprocess.Popen(cmd3, stdin=p2.stdout,
                                          stdout=subprocess.PIPE, shell=True)
                    (output3, cgStat) = p3.communicate()
                    if cgStat:
                        print >>sys.stderr, "Child was terminated by signal", cgStat
                    else:
                        print ("%(FILE)s: %(OUTPUT)s" \
                                   %{'FILE': myFile, 'OUTPUT': output3})
                        monFp.write("%(FILE)s: %(OUTPUT)s\n" \
                                        %{'FILE': myFile, 'OUTPUT': output3})
                        count += 2
                except OSError, e:
                    print >>sys.stderr, "Execution failed:", e

        # Cleanup and quit
        monFp.close()
        print 'genBsrc: ', count, 'files'

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
        print 'ERROR(makeBsrc.py/checkBeaconConfig):',
        print lfile, 'missing.   Quitting.'
        exit(1)
    else:
        print 'checkBeaconConfig: ', lfile, 'exists...permit'
        SM.stateD('BEACONCONFIG').permitted(True)

def batchCopy(libDir, targetDir, sext):
    """Copy in the files having extension sext"""

    copied = 0
    copiedZ = 0
    skipped = 0
    skippedZ = 0
    for candFile in osu.lsl(libDir):
        ext = candFile.rpartition('.')[2]
        root = candFile.rpartition('.')[0]
        if ext == 'gz':
            ext = root.rpartition('.')[2]
            root = root.rpartition('.')[0]
        if ''.join(['.', ext]) == sext:
            sourceFile = os.path.join(libDir, ''.join([root, sext]))
            sourceFileGz = ''.join([sourceFile, '.gz'])
            targetFile = os.path.join(targetDir, ''.join([root, sext]))
            targetFileGz = ''.join([targetFile, '.gz'])
            dSourceFile = osu.get_stamp(sourceFile)
            dSourceFileGz = osu.get_stamp(sourceFileGz)
            dTargetFile = osu.get_stamp(targetFile)
            dTargetFileGz = osu.get_stamp(targetFileGz)
            if   dTargetFile >=  max(dSourceFile, dSourceFileGz):
                skipped += 1
            elif dTargetFileGz >= max(dSourceFile, dSourceFileGz):
                skippedZ += 1
            elif dSourceFile > dTargetFile:
                shutil.copyfile(sourceFile, targetFile)
                print 'copying', os.path.basename(sourceFile)
                copied += 1
            elif dSourceFileGz > dTargetFileGz:
                shutil.copyfile(sourceFileGz, targetFileGz)
                print 'copying', os.path.basename(sourceFileGz)
                copiedZ += 1
            elif dSourceFileGz > dTargetFile:
                print 'WARNING(MakeBsrc.py/batchCopy): ', sourceFileGz, \
                    'newer than', targetFile
            else:
                pass
    return (copied, copiedZ, skipped, skippedZ)
        
def checkAndMake(ldir):
    """Make folders"""
    if not os.path.isdir(ldir):
        os.mkdir(ldir)
        print 'made', ldir
    else:
        print ldir, 'exists...skip'

def removeCompressed(ldir):
    """Remove all compressed files in directory given"""
    count = 0
    for candFile in osu.lsl(ldir):
        root = candFile.rpartition('.')[0]
        #ext = candFile.rpartition('.')[2]
        Zfile = ''.join([root, '.Z'])
        if os.path.isfile(Zfile):
            os.remove(Zfile)
            count += 1
            print 'removeCompressed:  removing', Zfile
        gzfile = ''.join([root, '.gz'])
        if os.path.isfile(gzfile):
            os.remove(gzfile)
            count += 1
            print 'removeCompressed:  removing', gzfile
    return count

def checkCreateFileSys(event=None):
    """Create folders and/or check them"""
    #if event:
    #    print event
    key = 'FILESYS'
    state = SM.stateD(key)

    if state.permitted() and state.raised():
        # Create
        MUIC.makeNames()
        MUIC.checkAndCreate()

        # temp code
        ans = tkM.askokcancel(message='Succeed with files?')
        if ans:
            state.disabButt()
            state.sinkButt()
            update(key)
        else:
            state.enabButt()

def importBuildBaseline(event=None):
    """Go get the baseline software from library and build"""
    #if event:
     #   print event
    key = 'BASELINE'
    state = SM.stateD(key)

    if state.permitted() and state.raised():
        MUIC.baselineGetFiles()
        MUIC.emptyOutBfsilDir()
        MUIC.copyInTheFiles()
        MUIC.uncompressForFullBuild()
        MUIC.genBsrc()
        MUIC.copyTheFilesToBsrc()

        # temp code
        ans = tkM.askokcancel(message= \
                             'Succeed with import build baseline?')
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
SETTINGLIST = [('MYHOME', ('~/beacon', 'Path of personal beacon folder')),
               ('PGM',  ('advanced', 
   'Program name in sdalib.  UNIX higher level folder name above VERO')),
               ('ITPGM',  ('advanced', 'Program name used by it-tools')),
               ('VERO', ('v0.0', 'Baseline of this build.')),
               ('BUILD',('v00a', 'Name of build in Simulink.')),
               ('VERN', ('v0.1', 'Expected new version (for reports)')), 
               ('SDAROOT',('/afs/ae.ge.com','Path of sdalib folder')),
               ('SDANAME',('advanced', 'Program folder in sdalib')),
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
TKROOT.title('MakeBsrc Root')
ROOT3 = Tk.Toplevel()
MUIC = _MyUserInterfaceClass(TKROOT,    # Set up the main GUI 
                              ROOT3,     # editor
                              ('400x360',# MakeBsrc Width & Height
                              '+20+20',  # Initial X/Y screen loc
                              '740x360', # settings Width & Height
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
    if remainder:
        print usage(1)

    SM.verbose(verbose)
    
    TKROOT.withdraw()
    if not usingIDLE:   # Avoid IDLE or other Tkinter based IDEs
        TKROOT.mainloop() # Outer event loop



if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
