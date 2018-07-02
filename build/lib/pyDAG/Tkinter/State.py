#!/usr/bin/env python
"""State:  GUI state machine class
	-d [level] / --debug [level]
	    Use this verbosity level to debug program  [0]
	-h / --help
		Print this message and exit
	-V, --version
		Print version and quit \n"
Tests:
>>>python State.py
"""

import Tkinter as Tk
import Tkconstants as Tkc


class State:
    """Organized memory of button/internal states for callbacks

    State dictionary
    entry format = State(stype, (row, col),['depend1', ...], presentState,
                    butName, callback, description))
    
    """
    def __init__(self, stype, rowcol, depends, stateBoolean,
                 buttonName, callback, description):
        self.__stype = stype
        self.__loc = rowcol
        self.__depends = depends
        self.__state = stateBoolean
        if stype == 'checkbutton':
            self.stateInt = Tk.IntVar()
            if stateBoolean:
                self.stateInt.set(0)
            else:
                self.stateInt.set(1)
        self.__buttonName = buttonName
        self.__callback = callback
        self.__desc = description
        self.__widget = Tk.Button()

    def flattenButt(self):
        """Flatten the Tkbutton"""
        self.__widget['relief'] = Tkc.FLAT

    def flat(self):
        """Query if flat"""
        if self.__stype == 'button' and self.__widget['relief'] == \
                Tkc.FLAT:
            return True
        else:
            return False

    def raiseButt(self):
        """Raise the Tkbutton"""
        self.__widget['relief'] = Tkc.RAISED

    def raised(self):
        """Query if raised"""
        if self.__stype == 'button' and self.__widget['relief'] == \
                Tkc.RAISED:
            return True
        else:
            return False

    def grooveButt(self):
        """Groove the Tkbutton"""
        self.__widget['relief'] = Tkc.GROOVE

    def grooved(self):
        """Query if grooved"""
        if self.__stype == 'button' and self.__widget['relief'] == \
                Tkc.GROOVE:
            return True
        else:
            return False

    def ridgeButt(self):
        """Make button ridged"""
        self.__widget['relief'] = Tkc.RIDGE

    def ridged(self):
        """Query ridged"""
        if self.__stype == 'button' and self.__widget['relief'] == \
                Tkc.RIDGE:
            return True
        else:
            return False

    def disabButt(self):
        """Make button disabled"""
        self.__widget['state'] = Tkc.DISABLED

    def disabled(self):
        """Query disabled"""
        if self.__stype == 'button' and self.__widget['state'] == \
                Tkc.DISABLED:
            return True
        else:
            return False

    def enabButt(self):
        """Make button enabled"""
        self.__widget['state'] = Tkc.NORMAL

    def enabled(self):
        """Query enabled"""
        if self.__stype == 'button' and self.__widget['state'] == \
                Tkc.NORMAL:
            return True
        else:
            return False

    def sinkButt(self):
        """Make button sunken"""
        self.__widget['relief'] = Tkc.SUNKEN

    def sunken(self):
        """Query sunken"""
        if self.__stype == 'button' and self.__widget['relief'] == \
                Tkc.SUNKEN:
            return True
        else:
            return False

    def stype(self, newType=None):
        """Assign/query stype"""
        if newType:
            self.__stype = newType
        return self.__stype

    def widget(self, newObj=None):
        """Assign/query widget"""
        if newObj and self.__stype == 'button':
            self.__widget = newObj
        return self.__widget

    def row(self, newRow=None):
        """Assign/query row"""
        if newRow:
            self.__loc = (newRow, self.col())
        return self.__loc[0]

    def col(self, newCol=None):
        """Assign/query column"""
        if newCol:
            self.__loc = (self.row(), newCol)
        return self.__loc[1]

    def depends(self, newDepends=None):
        """Assign/query depends"""
        if newDepends:
            self.__depends = newDepends
        return self.__depends

    def permitted(self, newPermitted=None):
        """Assign/query permitter"""
        if newPermitted != None:
            if self.__stype == 'checkbutton':
                self.stateInt.set(newPermitted)
            self.__state = newPermitted
        else:
            if self.__stype == 'checkbutton':
                self.__state = self.stateInt.get()
        return self.__state

    def buttonName(self, newButtonName=None):
        """Assign/query name"""
        if newButtonName:
            self.__buttonName = newButtonName
        return self.__buttonName

    def callback(self, newCallback=None):
        """Assign/query callback"""
        if newCallback:
            self.__callback = newCallback
        return self.__callback

#------------------------------------------------------------------------
# Name: StateMachine
# Desc: Organize memory of button/internal states for callbacks
#------------------------------------------------------------------------
class StateMachine:
    """Organize memor of button/internal states for callbacks"""

    def __init__(self, stateD, verboseIn):
        self.__verbose = verboseIn
        self.__stateD = stateD
        self.len = len(stateD)
        self.__total = 0
        self.__totalize()

    def stateD(self, key):
        """Query state from dictionary"""
        return self.__stateD[key]

    def verbose(self, newVerbose=None):
        """Query/assign verbose"""
        if newVerbose:
            self.__verbose = newVerbose
        return self.__verbose

    def update(self, buttDone=None):
        """Query/assign update"""
        totalPast = -1
        total = self.__totalize()
        if buttDone and self.__stateD[buttDone].stype()!='checkbutton':
            self.__stateD[buttDone].permitted(True)
        count = 0
        while (totalPast != total) and count < 20:
            totalPast = total
            for (key, state) in self.__stateD.items():
                statePast = self.__stateD[key].permitted()
                if self.__verbose > 4:
                    print key, '=', self.__stateD[key].permitted(), '::',
                if len(state.depends()):
                    self.__stateD[key].permitted(True)
                else:
                    self.__stateD[key].permitted(statePast)
                for dep in state.depends():
                    if self.__verbose > 4:
                        print dep, '=', \
                            self.__stateD[dep].permitted(), ',',
                    if not self.__stateD[dep].permitted():
                        self.__stateD[key].permitted(False)
                if self.__verbose > 4:
                    print '::', key, '=', self.__stateD[key].permitted()
                if self.__verbose > -1:
                    if not statePast and self.__stateD[key].permitted():
                        print 'set=', key
                    if statePast and not self.__stateD[key].permitted():
                        print 'unset=', key
            total = self.__totalize()
            count += 1
        if self.__verbose > -1:
            print 'total=', self.__total, ' count=', count
        return self.__stateD.items()

    def __totalize(self):
        """Add up total state number"""
        self.__total = 0
        istate = 0
        for (key, state) in self.__stateD.items():
            self.__total += state.permitted() * 2**istate
            istate += 1
            if self.__verbose > 0:
                print key, '=', state.permitted(), ',',
        return self.__total

# Main
def main(argv):
    """"Main for running tests on the class"""
    import getopt

    verbose = 0

    # Initialize static variables.
    def usage(code, msg=''):
        "Usage description"
        print >> sys.stderr, __doc__
        if msg:
            print >> sys.stderr, msg
        if code >= 0:
            sys.exit(code)


    # Options
    try:
        options, remainder = getopt.getopt(argv, \
               'd:hV', ['debug=', 'help', 'version'])
    except getopt.GetoptError:
        usage(2)
    for opt, arg in options:
        if opt in ('-d', '--debug'):
            verbose = int(arg)
        elif   opt in ('-h', '--help'):
            print usage(1)
        elif opt in ('-V', '--version'):
            print 'State.py Version 1.0.  DA Gutz 8/26/10'
            exit(0)
        else: print usage(1)
    if len(remainder) >0:
        print usage(1)

    # gui
    class _MyUserInterfaceClass:
        """Local gui creator class"""
        def __init__( self, master, ar, xy, stateD ):
            # States
            self.__stateDict = stateD
            self.__stateMach = StateMachine(stateD, verbose)
            
            # Initialize main menu bar
            self.__menubar = Tk.Menu( master )
            self.__frame = Tk.Toplevel( relief = 'ridge',
                                             borderwidth = 2,
                                             menu = self.__menubar ) 
            self.__frame.geometry( ar + xy )
            master.config( menu=self.__menubar )
            filemenu = Tk.Menu( self.__menubar, tearoff=0 ) # dropdown
            self.__menubar.add_cascade( label = 'File', underline = 0,
                                        menu = filemenu )
            master.withdraw() # Suppress unwanted window
            # Initialize buttons in main window
            b0 =  Tk.Button(self.__frame, text='FILESYS',
                         command=self.__SMcallback('FILESYS'),
                         relief=Tkc.RAISED)
            b0.grid(row=self.__stateRow('FILESYS'),
                    column=self.__stateCol('FILESYS'))
            b1 =  Tk.Button(self.__frame, text='BASELINE',
                         command=self.__SMcallback('BASELINE'),
                         relief=Tkc.RAISED)
            b1.grid(row=self.__stateRow('BASELINE'),
                    column=self.__stateCol('BASELINE'))
            b2 =  Tk.Button(self.__frame, text='BUILDSAR',
                         command=self.__SMcallback('BUILDSAR'),
                         relief=Tkc.RAISED)
            b2.grid(row=self.__stateRow('BUILDSAR'),
                    column=self.__stateCol('BUILDSAR'))

        def stateMach(self):
            """stateMach query"""
            return self.__stateMach

        def __SMcallback(self, key):
            """State lookup and call"""
            return self.__stateMach.stateD(key).callback()

        def __stateRow(self, key):
            """State row query"""
            return self.__stateMach.stateD(key).row()

        def __stateCol(self, key):
            """State column query"""
            return self.__stateMach.stateD(key).col()

    def checkCreateFileSys():
        """File system build callback"""
        print 'FILESYS'
        muic.stateMach().update('FILESYS')

    def importBuildBaseline():
        """Build Baseline callback"""
        print 'BASELINE'
        muic.stateMach().update('BASELINE')

    def buildSAR():
        """Build SAR callback"""
        print 'buildSAR'
        muic.stateMach().update('BUILDSAR')




    # State dictionary
    # entry format = (key,
    #                 State(stype, (locRow, locCol), ('depends1', ...),
    #                 presentState, butName, callback, description))
    states = [('FILESYS',
               State('button',  (0, 0), [], False,
                     'Setup File Sys', checkCreateFileSys,
                     'Check and create folder structure vs. settings')),
              ('SARSPRESENT',
               State('internal',(None, None), ['FILESYS'], False,
                     'SARs Present', None,
                     'SARS are available for processing')),
              ('BASELINE',
               State('button', (0, 1), ['FILESYS'], False,
                     'Build Baseline', importBuildBaseline,
                     'Make a complete build from totally raw library')),
              ('BUILDSAR',
               State('button', (0, 2), ['FILESYS', 'SARSPRESENT'], False,
                     'Build Review Pkg', buildSAR,
                     'Run buildsar tool to make review package')),
              ('GENCODE',
               State('button', (0, 3), ['FILESYS', 'SARSPRESENT'], False,
                     'Generate Code', None,
                     'Consolidate SARS and generate code')),
              ('BUILDTBL',
               State('button', (0, 4), ['GENCODE'], False,
                     'Generate TBL', None,
                     'Process the .tbl table trims')),
              ('BUILDADJ',
               State('button',  (0, 5), ['GENCODE'], False,
                     'Generate ADJ', None,
                     'Process the .adj adjustment trims')),
              ('DBGEN',
               State('button',  (0, 6), ['BUILDTBL', 'BUILDADJ'], False,
                     'Generate BDB', None,
                     'Generate Beacon Database')),
              ('DBCHECK',
               State('button',  (1, 0), ['DBGEN'], False,
                     'Check BDB', None,
                     'Check the Beacon Database')),
              ('BSRC',
               State('button',  (2, 0), ['DBCHECK'], False,
                     'Build the BSRC folder', None,
                     'Consolidate files for move to Simulink'))
              ]
    
    # load settings and make them global
    root = Tk.Tk()
    root.title('State')
    root.withdraw()

    root2 = Tk.Toplevel()
    muic = _MyUserInterfaceClass( root2,     # Set up the main GUI 
                           '400x200', # Width & Height
                          '+20+20',  # Initial X/Y screen loc
                          dict(states)) # state machine def
    root.mainloop() # Outer event loop



if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:]))
