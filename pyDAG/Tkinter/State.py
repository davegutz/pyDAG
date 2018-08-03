#!/usr/bin/env python
import Tkinter as Tk
import Tkconstants as Tkc

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


class State:
    """Organized memory of button/internal states for callbacks

    State dictionary
    entry format = State(s_type, (row, col),['depend1', ...], presentState,
                    butName, callback, description))
    
    """

    def __init__(self, s_type, row_col, depends, state_boolean,
                 button_name, callback, description):
        self.__s_type = s_type
        self.__loc = row_col
        self.__depends = depends
        self.__state = state_boolean
        if s_type == 'checkbutton':
            self.stateInt = Tk.IntVar()
            if state_boolean:
                self.stateInt.set(0)
            else:
                self.stateInt.set(1)
        self.__buttonName = button_name
        self.__callback = callback
        self.__desc = description
        self.__widget = Tk.Button()

    def flatten_butt(self):
        """Flatten the tk button"""
        self.__widget['relief'] = Tkc.FLAT

    def flat(self):
        """Query if flat"""
        if self.__s_type == 'button' and self.__widget['relief'] == \
                Tkc.FLAT:
            return True
        else:
            return False

    def raise_butt(self):
        """Raise the tk button"""
        self.__widget['relief'] = Tkc.RAISED

    def raised(self):
        """Query if raised"""
        if self.__s_type == 'button' and self.__widget['relief'] == \
                Tkc.RAISED:
            return True
        else:
            return False

    def groove_butt(self):
        """Groove the tk button"""
        self.__widget['relief'] = Tkc.GROOVE

    def grooved(self):
        """Query if grooved"""
        if self.__s_type == 'button' and self.__widget['relief'] == \
                Tkc.GROOVE:
            return True
        else:
            return False

    def ridge_butt(self):
        """Make button ridged"""
        self.__widget['relief'] = Tkc.RIDGE

    def ridged(self):
        """Query ridged"""
        if self.__s_type == 'button' and self.__widget['relief'] == \
                Tkc.RIDGE:
            return True
        else:
            return False

    def disable_butt(self):
        """Make button disabled"""
        self.__widget['state'] = Tkc.DISABLED

    def disabled(self):
        """Query disabled"""
        if self.__s_type == 'button' and self.__widget['state'] == \
                Tkc.DISABLED:
            return True
        else:
            return False

    def enable_butt(self):
        """Make button enabled"""
        self.__widget['state'] = Tkc.NORMAL

    def enabled(self):
        """Query enabled"""
        if self.__s_type == 'button' and self.__widget['state'] == \
                Tkc.NORMAL:
            return True
        else:
            return False

    def sink_butt(self):
        """Make button sunken"""
        self.__widget['relief'] = Tkc.SUNKEN

    def sunken(self):
        """Query sunken"""
        if self.__s_type == 'button' and self.__widget['relief'] == \
                Tkc.SUNKEN:
            return True
        else:
            return False

    def s_type(self, new_type=None):
        """Assign/query s_type"""
        if new_type:
            self.__s_type = new_type
        return self.__s_type

    def widget(self, new_obj=None):
        """Assign/query widget"""
        if new_obj and self.__s_type == 'button':
            self.__widget = new_obj
        return self.__widget

    def row(self, new_row=None):
        """Assign/query row"""
        if new_row:
            self.__loc = (new_row, self.col())
        return self.__loc[0]

    def col(self, new_col=None):
        """Assign/query column"""
        if new_col:
            self.__loc = (self.row(), new_col)
        return self.__loc[1]

    def depends(self, new_depends=None):
        """Assign/query depends"""
        if new_depends:
            self.__depends = new_depends
        return self.__depends

    def permitted(self, new_permitted=None):
        """Assign/query permit"""
        if new_permitted is not None:
            if self.__s_type == 'checkbutton':
                self.stateInt.set(new_permitted)
            self.__state = new_permitted
        else:
            if self.__s_type == 'checkbutton':
                self.__state = self.stateInt.get()
        return self.__state

    def button_name(self, new_button_name=None):
        """Assign/query name"""
        if new_button_name:
            self.__buttonName = new_button_name
        return self.__buttonName

    def callback(self, new_callback=None):
        """Assign/query callback"""
        if new_callback:
            self.__callback = new_callback
        return self.__callback


# ------------------------------------------------------------------------
# Name: StateMachine
# Desc: Organize memory of button/internal states for callbacks
# ------------------------------------------------------------------------
class StateMachine:
    """Organize memory of button/internal states for callbacks"""

    def __init__(self, state_d, verbose_in):
        self.__verbose = verbose_in
        self.__stateD = state_d
        self.len = len(state_d)
        self.__total = 0
        self.__totalize()

    def state_d(self, key):
        """Query state from dictionary"""
        return self.__stateD[key]

    def verbose(self, new_verbose=None):
        """Query/assign verbose"""
        if new_verbose:
            self.__verbose = new_verbose
        return self.__verbose

    def update(self, butt_done=None):
        """Query/assign update"""
        total_past = -1
        total = self.__totalize()
        if butt_done and self.__stateD[butt_done].s_type() != 'checkbutton':
            self.__stateD[butt_done].permitted(True)
        count = 0
        while (total_past != total) and count < 20:
            total_past = total
            for (key, state) in self.__stateD.items():
                state_past = self.__stateD[key].permitted()
                if self.__verbose > 4:
                    print key, '=', self.__stateD[key].permitted(), '::',
                if len(state.depends()):
                    self.__stateD[key].permitted(True)
                else:
                    self.__stateD[key].permitted(state_past)
                for dep in state.depends():
                    if self.__verbose > 4:
                        print dep, '=', \
                            self.__stateD[dep].permitted(), ',',
                    if not self.__stateD[dep].permitted():
                        self.__stateD[key].permitted(False)
                if self.__verbose > 4:
                    print '::', key, '=', self.__stateD[key].permitted()
                if self.__verbose > -1:
                    if not state_past and self.__stateD[key].permitted():
                        print 'set=', key
                    if state_past and not self.__stateD[key].permitted():
                        print 'unset=', key
            total = self.__totalize()
            count += 1
        if self.__verbose > -1:
            print 'total=', self.__total, ' count=', count
        return self.__stateD.items()

    def __totalize(self):
        """Add up total state number"""
        self.__total = 0
        i_state = 0
        for (key, state) in self.__stateD.items():
            self.__total += state.permitted() * 2 ** i_state
            i_state += 1
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
        """Usage description"""
        print >> sys.stderr, __doc__
        if msg:
            print >> sys.stderr, msg
        if code >= 0:
            sys.exit(code)

    # Options
    options = ""
    remainder = ""
    try:
        options, remainder = getopt.getopt(argv,
                                           'd:hV', ['debug=', 'help', 'version'])
    except getopt.GetoptError:
        usage(2)
    for opt, arg in options:
        if opt in ('-d', '--debug'):
            verbose = int(arg)
        elif opt in ('-h', '--help'):
            print usage(1)
        elif opt in ('-V', '--version'):
            print 'State.py Version 1.0.  DA Gutz 8/26/10'
            exit(0)
        else:
            print usage(1)
    if len(remainder) > 0:
        print usage(1)

    # gui
    class _MyUserInterfaceClass:
        """Local gui creator class"""

        def __init__(self, master, ar, xy, state_d):
            # States
            self.__stateDict = state_d
            self.__stateMach = StateMachine(state_d, verbose)

            # Initialize main menu bar
            self.__menu_bar = Tk.Menu(master)
            self.__frame = Tk.Toplevel(relief='ridge',
                                       borderwidth=2,
                                       menu=self.__menu_bar)
            self.__frame.geometry(ar + xy)
            master.config(menu=self.__menu_bar)
            file_menu = Tk.Menu(self.__menu_bar, tearoff=0)  # drop down
            self.__menu_bar.add_cascade(label='File', underline=0,
                                        menu=file_menu)
            master.withdraw()  # Suppress unwanted window
            # Initialize buttons in main window
            b0 = Tk.Button(self.__frame, text='FILESYS',
                           command=self.__sm_callback('FILESYS'),
                           relief=Tkc.RAISED)
            b0.grid(row=self.__state_row('FILESYS'),
                    column=self.__state_col('FILESYS'))
            b1 = Tk.Button(self.__frame, text='BASELINE',
                           command=self.__sm_callback('BASELINE'),
                           relief=Tkc.RAISED)
            b1.grid(row=self.__state_row('BASELINE'),
                    column=self.__state_col('BASELINE'))
            b2 = Tk.Button(self.__frame, text='BUILDSAR',
                           command=self.__sm_callback('BUILDSAR'),
                           relief=Tkc.RAISED)
            b2.grid(row=self.__state_row('BUILDSAR'),
                    column=self.__state_col('BUILDSAR'))

        def state_machine(self):
            """state_machine query"""
            return self.__stateMach

        def __sm_callback(self, key):
            """State lookup and call"""
            return self.__stateMach.state_d(key).callback()

        def __state_row(self, key):
            """State row query"""
            return self.__stateMach.state_d(key).row()

        def __state_col(self, key):
            """State column query"""
            return self.__stateMach.state_d(key).col()

    def check_create_file_sys():
        """File system build callback"""
        print 'FILESYS'
        mu_ic.state_machine().update('FILESYS')

    def import_build_baseline():
        """Build Baseline callback"""
        print 'BASELINE'
        mu_ic.state_machine().update('BASELINE')

    def build_sar():
        """Build SAR callback"""
        print 'build_sar'
        mu_ic.state_machine().update('BUILDSAR')

    # State dictionary
    # entry format = (key,
    #                 State(s_type, (locRow, locCol), ('depends1', ...),
    #                 presentState, butName, callback, description))
    states = [('FILESYS',
               State('button', (0, 0), [], False,
                     'Setup File Sys', check_create_file_sys,
                     'Check and create folder structure vs. settings')),
              ('SARSPRESENT',
               State('internal', (None, None), ['FILESYS'], False,
                     'SARs Present', None,
                     'SARS are available for processing')),
              ('BASELINE',
               State('button', (0, 1), ['FILESYS'], False,
                     'Build Baseline', import_build_baseline,
                     'Make a complete build from totally raw library')),
              ('BUILDSAR',
               State('button', (0, 2), ['FILESYS', 'SARSPRESENT'], False,
                     'Build Review Pkg', build_sar,
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
               State('button', (0, 5), ['GENCODE'], False,
                     'Generate ADJ', None,
                     'Process the .adj adjustment trims')),
              ('DBGEN',
               State('button', (0, 6), ['BUILDTBL', 'BUILDADJ'], False,
                     'Generate BDB', None,
                     'Generate Beacon Database')),
              ('DBCHECK',
               State('button', (1, 0), ['DBGEN'], False,
                     'Check BDB', None,
                     'Check the Beacon Database')),
              ('BSRC',
               State('button', (2, 0), ['DBCHECK'], False,
                     'Build the BSRC folder', None,
                     'Consolidate files for move to Simulink'))
              ]

    # load settings and make them global
    root = Tk.Tk()
    root.title('State')
    root.withdraw()

    root2 = Tk.Toplevel()
    mu_ic = _MyUserInterfaceClass(root2,  # Set up the main GUI 
                                  '400x200',  # Width & Height
                                  '+20+20',  # Initial X/Y screen loc
                                  dict(states))  # state machine def
    root.mainloop()  # Outer event loop


if __name__ == '__main__':
    import sys

    sys.exit(main(sys.argv[1:]))
