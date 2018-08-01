#!/usr/bin/env python
"""Generate stress test vectors from FTS file inputs
Usage: genGorilla <base_profile.def> <monteCarloFile>
Options:/
    -c, --calibrating  <seed value>
        Run with specified seed
    -h / --help
        Print this message and exit
    -o / --output <filename>
        Print to this output file basename
    -V, --version
        Print version and quit \n"
    -v, --verbose   <level>
        Print diagnostics to stdout
        
<base_profile.def
is the FTS standard .def file defining the time varying inputs (see FTS)

<monteCarloFile>
is the local Monte Carlo definitions file with contents:

    NAME   UPDATE  TYPE    min max RISE_TYPE min max FALL_TYPE   min     max HOLD_TYPE   min max absoluteMin absoluteMax
    plaslider   1  normal  -10 10  uniform   2   420 uniform     -240    -2  uniform     3   4   15          132

    NAME    UPDATE  switch  HOLD_TYPE   min max initial_value
    swwow   1       switch  uniform     1   5   1

    NAME        UPDATE  oneswitch   HOLD_TYPE   min max off_time
    MASTER_SWx  1       oneswitch   uniform     1   5   10

    NAME    normalconstant  min max abs_min  abs_max
    dtamb   normalconstant  -20 20  -119    44

    NAME uniformconstant min    max     abs_min  abs_max
    xm   uniformconstant -0.1   0.1     0.1     0.4
    alt  uniformconstant -10000 10000   -2000   60000

Tests:
python genGorilla.py -c11 g1000.def airstart.mtc
>>> main(['-c11', 'g1000.def','airstart.mtc'])
MESSAGE(genGorilla.py):  g110.def generated from g1000.def and airstart.mtc
MESSAGE(genGorilla.py):  g110.int generated from g1000.def and airstart.mtc
MESSAGE(genGorilla.py):  g110.int generated from g1000.def and airstart.mtc
MESSAGE(genGorilla.py):  g110.int generated from g1000.def and airstart.mtc
MESSAGE(genGorilla.py):  g111.def generated from g1000.def and airstart.mtc
MESSAGE(genGorilla.py):  g111.int generated from g1000.def and airstart.mtc
MESSAGE(genGorilla.py):  g111.int generated from g1000.def and airstart.mtc
MESSAGE(genGorilla.py):  g111.int generated from g1000.def and airstart.mtc
Done

"""

# import cProfile
import random as rn
import getopt
import array
import time
import math
import sys
import os

from pyDAG import InFile
from pyDAG import StringSet

INITAS = 0
CONSTANT_SIZE = 6  # Length of a constant line in random file
MAX_BREAK = 50000  # Maximum intern temp parameter curve size
MAX_DEFINE_CURVES = 15  # Maximum number time vars in .def file.
MAX_FILES = 25  # Maximum number of files allowed.
MAX_RIG_BREAKS = 200  # Maximum number of breakpoints autotv.
MAX_RIG_TIME = 3600  # Maximum allowed length of a rig reading.
MAX_VARIABLE_ARRAY_SIZE = 75  # Local array size limit.
ONE_SWITCH_SIZE = 7  # Length of a oneswitch line in random file
REGULAR_SIZE = 16  # Length of a regular line in random file
SWITCH_SIZE = 7  # Length of a switch line in random file
TIME_PAD = 5.  # Flats at beginning and end of files.
TIME_RESOLUTION = 1e-5  # Resolution time= test.


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
        self.message = message
        self.usage = usage_

    def __str__(self):
        if self.usage:
            return repr(self.message) + '\n\n%(doc)s' % {'doc': __doc__}
        else:
            return repr(self.message)


def usage(code, msg=''):
    """Usage description"""
    print >> sys.stderr, __doc__
    if msg:
        print >> sys.stderr, msg
    sys.exit(code)


def var_delay(input_, update, tf_delay, ft_delay, ic_val, state):
    """Variable delay function"""
    tf = tf_delay / update
    ft = ft_delay / update
    global INITAS
    if INITAS:
        output = ic_val
        if ic_val:
            state = long(tf)
        else:
            state = -long(ft + 1.0)
        return output, state
    if state >= 0:
        if input_:
            state = long(tf)
        else:
            state = state - 1
            if state < 0:
                state = -long(ft + 1.0)
    else:
        if input_:
            state = state + 1
            if state >= 0:
                state = long(tf)
        else:
            state = -long(ft + 1.0)
    output = state >= 0
    return output, state


class IcValue:
    """Keep track of initial value for a parameter"""

    def __init__(self, name, val):
        """Instantiate"""
        self.name = name
        self.val = val

    def __repr__(self):
        """Print the class"""
        c_out = '%(name)12s %(val)13.4f\n' % {'name': self.name, 'val': self.val}
        return c_out


class Parameter:
    """Keep track of a single parameter"""

    def __init__(self, name, type_):
        self.name = name
        self.num = 0
        self.curve_type = type_
        self.time = array.array('d')
        self.val = array.array('d')
        self.__marked = array.array('i')

    def __repr__(self):
        """Print the class"""
        c_out = '%(name)-12s %(type)2d %(num)4d' % {'name': self.name, 'type': self.curve_type, 'num': self.num}
        s_list = ['\n%(t)-7.2f %(v)-13.4f' % {'t': self.time[i], 'v': self.val[i]} for i in range(self.num)]
        c_out += "".join(s_list)
        return c_out

    def check_order(self):
        """Check time monotonically increasing"""
        bad_one = 0
        for i in range(self.num - 1):
            if self.time[i] >= self.time[i + 1]:
                print 'ERROR(genGorilla.py):  Variable', self.name, \
                  'time value not monotonically increasing at', i, \
                  'place, time approximately', self.time[i], '.'
                bad_one += 1
        if bad_one:
            return -1
        else:
            return 0

    def insert_val(self, t, v, mark, i):
        """Insert a breakpoint after i"""
        if self.num >= MAX_BREAK:
            raise InputError('Too many breakpoints added into %(name)s by consolidation' % {'name': self.name})
        self.num += 1
        self.time.insert(i + 1, t)
        self.val.insert(i + 1, v)
        self.__marked.insert(i + 1, mark)

    def append_val(self, t, v, mark):
        """Append a breakpoint"""
        if self.num >= MAX_BREAK:
            raise InputError('Too many breakpoints added into %(name)s by consolidation' % {'name': self.name})
        self.num += 1
        self.time.append(t)
        self.val.append(v)
        self.__marked.append(mark)

    def consolidate(self, new_curve):
        """Consolidate new_curve with present."""
        new_num = new_curve.num
        if self.time[self.num - 1] < new_curve.time[new_num - 1]:
            self.append_val(new_curve.time[new_num - 1], self.val[self.num - 1], 0)
        elif self.time[self.num - 1] > new_curve.time[new_num - 1]:
            new_curve.append_val(self.time[self.num - 1], new_curve.val[new_num - 1], 0)
        # Add extra breakpoints to curve random
        for i in range(new_num):
            new_time = new_curve.time[i]
            new_place = self.find_place(new_time)
            if new_place < 0:
                raise InputError('Table %(new_curve_name)s does not overlap %(name)s'
                                 % {'new_curve_name': new_curve.name, 'name': self.name})
            if math.fabs(new_time - self.time[new_place]) >= TIME_RESOLUTION:
                between_val = self.interpolate(new_time, new_place)
                self.insert_val(new_time, between_val, 0, new_place)

    def find_place(self, time_):
        """Find element location"""
        i = 0
        for i in range((self.num - 1), 0, -1):
            if self.time[i] <= time_ + TIME_RESOLUTION:
                break
        if i == self.num:
            return -1
        else:
            return i

    def interpolate(self, time_, place):
        """Interpolate curve value"""
        if place < 0:
            value = self.val[0]
        elif place < self.num - 1:
            value = (time_ - self.time[place]) / (self.time[place + 1] - self.time[place]) * \
                    (self.val[place + 1] - self.val[place]) + self.val[place]
        else:
            value = self.val[self.num - 1]
        return value

    def partial_out(self, begin, end):
        """Stream out the parameter to streams def_out and init_out.  Return number of points streamed"""
        #  Find begin, end.  Print header.  Tare the time.
        time_ = 0.0
        j_begin = self.find_place(begin)
        j_end = max(self.find_place(end), j_begin)
        num_pts = j_end - j_begin + 3
        value = self.val[j_begin]
        init_out = '%(name)-17s %(val)13.4f\n' % {'name': self.name, 'val': value}
        def_out = ""
        # If constant through transient, return right away.
        curve_is_constant = 1
        for k in range(j_begin + 1, j_end):
            if not self.val[k] == self.val[k - 1]:
                curve_is_constant = 0
                break
        if curve_is_constant:
            return 0, def_out, init_out
        #  Otherwise print title and first point.
        num_out = 0
        def_out = '$INPUT %(name)s  %(curve_type)-2i %(num_pts)-4i\n'\
                  % {'name': self.name, 'curve_type': self.curve_type, 'num_pts': num_pts}
        value = self.val[j_begin]
        def_out += ' %(time)7.2f  %(value)13.4f\n' % {'time': time_, 'value': value}
        num_out += 1
        # Hold the beginning
        time_ = TIME_PAD
        def_out += ' %(time)7.2f  %(value)13.4f\n' % {'time': time_, 'value': value}
        num_out += 1
        # Body of points
        for k in range(j_begin + 1, j_end + 1):
            time_ = self.time[k] - begin + TIME_PAD
            value = self.val[k]
            def_out += ' %(time)7.2f  %(value)13.4f\n' % {'time': time_, 'value': value}
            num_out += 1
        # Hold the end
        time_ = end - begin + 4 * TIME_PAD
        def_out += ' %(time)7.2f  %(value)13.4f\n' % {'time': time_, 'value': value}
        num_out += 1
        # Done
        return num_out, def_out, init_out


class Base:
    """Keep track of multiple parameters"""

    def __repr__(self):
        """Print the class"""
        c_out = '%(name)s \nf_time=%(f_time)f\n' % {'name': self.name, 'f_time': self.f_time}
        s_list = ['%(curve)s\n' % {'curve': self.curve[i]} for i in range(self.num)]
        c_out += "".join(s_list)
        return c_out

    def __init__(self, def_input):
        """Instantiate"""
        self.f_time = 0.0
        self.name = 'temp'
        self.name = def_input.programName
        self.num = 0
        self.numIC = 0
        self.curve = []
        # Find FTIME
        i = 0
        while not (def_input.LineS(i)[1] == "$FTIME") and i < def_input.numLines:
            i += 1
        if i >= def_input.numLines:
            raise InputError('$FTIME line not found')
        else:
            if len(def_input.LineS(i)) == 4:
                self.f_time = float(def_input.LineS(i)[2])
            else:
                raise InputError('In %(line)s, 2 fields needed' % {'line': def_input.LineS(i).str})
        # Find curves
        i = 0
        while True:
            i = def_input.findStr("$INPUT", i)
            if i >= def_input.numLines - 1:
                break
            curve_name = def_input.LineS(i)[2]
            if len(def_input.LineS(i)) < 5:
                raise InputError('Need type spec for input %(cn)s' % {'cn': curve_name})
            curve_type = int(def_input.LineS(i)[3])
            if self.num >= MAX_VARIABLE_ARRAY_SIZE:
                raise InputError('%(cn)s is too long' % {'cn': curve_name})
            self.curve.append(Parameter(def_input.LineS(i)[2], curve_type))
            i += 1
            while (def_input.LineS(i)[1][0].isdigit() or def_input.LineS(i)[1][0] == '.') and i < def_input.numLines:
                self.curve[self.num].append_val(float(def_input.LineS(i)[1]), float(def_input.LineS(i)[2]), 1)
                i += 1
            self.num = len(self.curve)

    def check_order(self):
        """Make sure time monotonically increasing"""
        bad_order = 0
        for i in range(self.num):
            if -1 == self.curve[i].check_order():
                bad_order = 1
        if bad_order:
            raise InputError('Time is not monotonically increasing in a curve input')


class RandomAll:
    """Randomized container for entire program"""

    def __init__(self, mtc_input):
        """Instantiate"""
        self.name = mtc_input.programName
        self.num = 0
        self.ranObj = []
        i = 0
        while i < mtc_input.numLines:
            # Range check
            if self.num > MAX_VARIABLE_ARRAY_SIZE:
                raise InputError('Too many variables in %(cn)s' % {'cn': mtc_input.name()})
            size = len(mtc_input.LineS(i))
            tok002 = mtc_input.LineS(i)[2]
            tok003 = mtc_input.LineS(i)[3]
            if not (size == REGULAR_SIZE + 2 or
                    (size == SWITCH_SIZE + 2 and tok003 == 'SWITCH') or
                    (size == ONE_SWITCH_SIZE + 2 and tok003 == 'ONESWITCH') or
                    (size == CONSTANT_SIZE + 2 and tok002 == 'UNIFORMCONSTANT') or
                    (size == CONSTANT_SIZE + 2 and tok002 == 'NORMALCONSTANT')):
                raise InputError('Improper format in %(pn)s at:%(line)s' % {'pn': mtc_input.program_name,
                                                                            'line': mtc_input.LineS(i).str}, 1)
            self.ranObj.append(RanDeltaVar(mtc_input.LineS(i)))
            i += 1
        self.num = len(self.ranObj)

    def __repr__(self):
        """Print the class"""
        c_out = self.name
        s_list = ['\n%(ran_obj)s' % {'ran_obj': self.ranObj[i]} for i in range(self.num)]
        c_out += "".join(s_list)
        return c_out


class RandomVariable:
    """Random variable"""
    firstRanSeed = None  # first of seeds
    ranSeed = None  # state of seed, incremented each  new instance and remembered

    def __init__(self, name, min_, max_=100000):
        """Instantiate"""
        self.name = name
        self.min = min_
        self.max = max_
        if self.min > self.max:
            print 'WARNING(genGorilla.py):' \
                  'min/max disagree for variable', self.name
        if not RandomVariable.firstRanSeed:
            RandomVariable.firstRanSeed = os.getpid()
        if not RandomVariable.ranSeed:
            RandomVariable.ranSeed = RandomVariable.firstRanSeed
        else:
            RandomVariable.ranSeed += 1
        self.ranSeed = RandomVariable.ranSeed
        self.rand = rn.Random(self.ranSeed)

    def get_value(self):
        """Value at time"""
        return 0.0

    def get_value_from_past(self, past):
        """Value at time from past"""
        # global INITAS
        #  if ( INITAS ) return past
        if past == self.max:
            return self.min
        else:
            return self.max

    def __repr__(self):
        """Print the class"""
        c_out = 'RandomVariable %(name)-6s min = %(min)-6.4g  max = %(max)-6.4g seed = %(seed)-6i'\
                % {'name': self.name, 'min': self.min, 'max': self.max, 'seed': self.ranSeed}
        return c_out

        #  // element access


class RanDeltaVar:
    """Random delta variable, adder on nominal curves"""

    def __init__(self, line_s):
        """Instantiate"""
        self.update = 0.0
        self.__rise = 0.0
        self.__input = 0.0
        self.__hold = 0.0
        self.__fall = 0.0
        self.__i_state1 = 0
        self.__state2 = 0.0
        self.__b_state3 = True
        self.__state4 = 0.0
        self.__state5 = 0.0
        self.__state6 = 0.0
        self.__state7 = 0.0
        self.min = 0.0
        self.max = 0.0
        self.abs_min = 0.0
        self.abs_max = 0.0
        self.__output = 0.0
        self.__limited = False
        self.__initial_value = 0.0
        self.__off_time = 0.0
        self.name = None
        self.__type = None
        self.__input_v = None
        self.__rise_v = None
        self.__fall_v = None
        self.__hold_v = None
        size = len(line_s)
        if size == REGULAR_SIZE + 2:
            self.__type = line_s[3]
            self.name = line_s[1]
            self.update = float(line_s[2])
            input_type = line_s[3]
            input_min = float(line_s[4])
            input_max = float(line_s[5])
            rise_type = line_s[6]
            rise_min = float(line_s[7])
            rise_max = float(line_s[8])
            fall_type = line_s[9]
            fall_min = float(line_s[10])
            fall_max = float(line_s[11])
            hold_type = line_s[12]
            hold_min = float(line_s[13])
            hold_max = float(line_s[14])
            abs_min = float(line_s[15])
            abs_max = float(line_s[16])
            self.min = input_min
            self.max = input_max
            self.abs_min = abs_min
            self.abs_max = abs_max
        elif size == SWITCH_SIZE + 2 and line_s[3] == "SWITCH":
            self.__type = line_s[3]
            self.name = line_s[1]
            self.update = float(line_s[2])
            input_type = line_s[3]
            input_min = -1.0
            input_max = 1.0
            rise_type = 'CONSTANT'
            rise_min = (1.0 / self.update + 1.0)
            rise_max = (1.0 / self.update + 1.0)
            fall_type = 'CONSTANT'
            fall_min = -(1.0 / self.update + 1.0)
            fall_max = -(1.0 / self.update + 1.0)
            hold_type = line_s[4]
            hold_min = float(line_s[5])
            hold_max = float(line_s[6])
            self.min = input_min
            self.max = input_max
            self.abs_min = 0.0
            self.abs_max = 1.0
            self.__initial_value = int(line_s[7])
        elif size == ONE_SWITCH_SIZE + 2 and line_s[3] == "ONESWITCH":
            self.__type = line_s[3]
            self.name = line_s[1]
            self.update = float(line_s[2])
            input_type = line_s[3]
            input_min = -1.0
            input_max = 1.0
            rise_type = 'CONSTANT'
            rise_min = (1.0 / self.update + 1.0)
            rise_max = (1.0 / self.update + 1.0)
            fall_type = 'CONSTANT'
            fall_min = -(1.0 / self.update + 1.0)
            fall_max = -(1.0 / self.update + 1.0)
            hold_type = line_s[4]
            hold_min = float(line_s[5])
            hold_max = float(line_s[6])
            self.min = float(line_s[7])
            self.max = input_max
            self.abs_min = 0.0
            self.abs_max = 1.0
            self.__initial_value = int(line_s[7])
        elif size == CONSTANT_SIZE + 2 and (line_s[2] == "NORMALCONSTANT"
                                            or line_s[2] == "UNIFORMCONSTANT"):
            self.__type = line_s[2]
            self.name = line_s[1]
            self.update = 1
            input_type = line_s[2]
            input_min = float(line_s[3])
            input_max = float(line_s[4])
            rise_type = 'CONSTANT'
            rise_min = 1
            rise_max = 1
            fall_type = 'CONSTANT'
            fall_min = -1
            fall_max = -1
            hold_type = "CONSTANT"
            hold_min = 0
            hold_max = -1
            abs_min = float(line_s[5])
            abs_max = float(line_s[6])
            self.min = input_min
            self.max = input_max
            self.abs_min = abs_min
            self.abs_max = abs_max
        else:
            raise InputError('Unknown type at %(line)s' % {'line': line_s.str})
        if self.update <= 0.0:
            raise InputError('Bad update at %(line)s' % {'line': line_s.str})
        self.__input_v = self.make_ran_var('INPUT', input_type, input_min, input_max)
        self.__rise_v = self.make_ran_var('RISE', rise_type, rise_min, rise_max)
        self.__fall_v = self.make_ran_var('FALL', fall_type, fall_min, fall_max)
        self.__hold_v = self.make_ran_var('HOLD', hold_type, hold_min, hold_max)

    def __repr__(self):
        """Print the class"""
        c_out = '%(name)-12s\n  input_v= %(input_v)s\n  rise_v = %(rise_v)s\n  fall_v = %(fall_v)s\n' \
                '  hold_v = %(hold_v)s' \
                % {'name': self.name, 'input_v': self.__input_v, 'rise_v': self.__rise_v, 'fall_v': self.__fall_v,
                    'hold_v': self.__hold_v}
        return c_out

    def make_ran_var(self, name, type_, min_, max_):
        """Make random variable from input"""
        if type_ == 'UNIFORM':
            return UniformRandomVariable(name, min_, max_)
        elif type_ == 'NORMAL':
            return NormalRandomVariable(name, min_, max_)
        elif type_ == 'SWITCH':
            return SwitchVariable(name, min_, max_, self.__initial_value)
        elif type_ == 'ONESWITCH':
            return OneSwitchVariable(name, min_, max_, self.__off_time)
        elif type_ == 'CONSTANT':
            return ConstantVariable(name, min_)
        elif type_ == 'UNIFORMCONSTANT':
            return UniformConstantVariable(name, min_, max_)
        elif type_ == 'NORMALCONSTANT':
            return NormalConstantVariable(name, min_, max_)
        else:
            print 'WARNING(genGorilla.py):  variable type', type_, 'not supported for variable', \
                name, '.  Assuming UNIFORM'
            return UniformRandomVariable(name, min_, max_)

    def update_var(self, update, time_):
        """Generate Monte-Carlo"""
        self.__rise = self.__rise_v.get_value()
        self.__hold = self.__hold_v.get_value()
        self.__fall = self.__fall_v.get_value()
        # global INITAS
        if self.__type == "SWITCH":
            if INITAS:
                self.__output = self.__initial_value
            self.__input = self.__input_v.get_value_from_past(self.__output)
        elif self.__type == "ONESWITCH":
            if INITAS:
                self.__output = 0
            if 0 == self.__output:
                self.__input = self.__input_v.get_value_from_past(self.__output)
        else:
            self.__input = self.__input_v.get_value()

        if self.__type == "NORMALCONSTANT" or self.__type == "UNIFORMCONSTANT":
            self.__input = self.__input_v.get_value()
            self.__output = self.__input
        else:
            self.__output = self.monte_carlo(update)
            # global verbose
            if verbose > 1:
                if INITAS:
                    print '\ntype=', self.__type, \
                          '\ntime_   input  rise   hold   fall   update  i_state1', \
                          '  state2  limited b_state3 state4  state5  output'
                print '%(ti)-7.1f%(in)-7.2f%(ri)-7.2f%(ho)-7.2f%(fa)-7.2f%(up)-7.2f %(hi1)-8i %(hs2)-7.2f %(li)-7.0f' \
                      ' %(hb3)-7.2f %(hs4)-7.2f %(hs5)-7.2f %(ou)-7.2f' \
                      % {'ti': time_, 'in': self.__input, 'ri': self.__rise, 'ho': self.__hold, 'fa': self.__fall,
                         'up': update,
                         'hi1': self.__i_state1, 'hs2': self.__state2, 'li': self.__limited, 'hb3': self.__b_state3,
                         'hs4': self.__state4, 'hs5': self.__state5, 'ou': self.__output}

        if self.__type == "ONESWITCH":
            if time_ > self.__off_time:
                self.__output = 0

        return self.__output

    def monte_carlo(self, update):
        """Generate waveform.  See the Gorilla documentation."""
        # global INITAS
        if INITAS:
            self.__state6 = self.__input

        (heldOutput, heldFrozen) = self.holder(self.__input, update)
        if not heldFrozen:
            state4 = self.__rise
        else:
            state4 = self.__state4
        self.__state4 = state4
        if not heldFrozen:
            state5 = self.__fall
        else:
            state5 = self.__state5
        self.__state5 = state5
        output = heldOutput
        self.__limited = False
        output_max = self.update * state4 + self.__state6
        output_min = self.update * state5 + self.__state6
        if output > output_max:
            output = output_max
            self.__limited = True
        elif output < output_min:
            output = output_min
            self.__limited = True
        self.__state6 = output
        return output

    def holder(self, input_, update):
        """Control update action of the monte_carlo function.  See the Gorilla documentation"""
        # global INITAS
        if INITAS:
            self.__state2 = input_
            self.__b_state3 = True
        if self.__b_state3:
            output = self.__state2
        else:
            output = input_
        var_input = (not self.__b_state3 and not output == self.__state2) or self.__limited
        (varOutput, self.__i_state1) = var_delay(var_input, update, self.__hold, 0.0, True, self.__i_state1)
        frozen = self.__b_state3
        self.__state2 = output
        self.__b_state3 = varOutput
        return output, frozen


class UniformRandomVariable(RandomVariable):
    """Uniform distribution"""

    def __init__(self, name, min_, max_):
        """Instantiate"""
        RandomVariable.__init__(self, name, min_, max_)

    def get_value(self):
        """Get value of variable at time"""
        # global INITAS
        if INITAS and self.min <= 0:
            return 0.0
        random = self.rand.uniform(0, 1)
        return random * (self.max - self.min) + self.min


class NormalRandomVariable(RandomVariable):
    """Normal distribution"""

    def __init__(self, name, min_, max_):
        """Instantiate"""
        RandomVariable.__init__(self, name, min_, max_)

    def get_value(self):
        """Get value of variable at time"""
        global INITAS
        if INITAS and self.min <= 0:
            return 0.0
        random = math.sqrt(-2.0 * math.log10(self.rand.uniform(0, 1)))\
            * math.cos(2.0 * 3.1415926 * self.rand.uniform(0, 1))
        return random * (self.max - self.min) + self.min


class SwitchVariable(RandomVariable):
    """Random two-level"""

    def __init__(self, name, min_, max_, initial_value):
        """Instantiate"""
        RandomVariable.__init__(self, name, min_, max_)
        self.__initial_value = initial_value

    def __repr__(self):
        c_out = '%(parent)s initial_value= %(initial_value)-12.4g'\
                % {'parent': RandomVariable.__repr__(self), 'initial_value': self.__initial_value}
        return c_out


class OneSwitchVariable(RandomVariable):
    """Random on/off"""

    def __init__(self, name, min_, max_, off_time):
        """Instantiate"""
        RandomVariable.__init__(self, name, min_, max_)
        self.__off_time = off_time

    def __repr__(self):
        c_out = '%(parent)s off_time = %(off_time)-6.4g'\
                % {'parent': RandomVariable.__repr__(self), 'off_time': self.__off_time}
        return c_out


class ConstantVariable(RandomVariable):
    """Constant"""

    def __init__(self, name, val):
        """Instantiate"""
        RandomVariable.__init__(self, name, val)
        self.__value = val

    def __repr__(self):
        c_out = '%(parent)s value = %(value)-6.4g' % {'parent': RandomVariable.__repr__(self), 'value': self.__value}
        return c_out

    def get_value(self):
        """Get value of variable at time"""
        return self.__value


class UniformConstantVariable(RandomVariable):
    """Initialize to a uniformly random value"""

    def __init_(self, name, min_, max_):
        """Instantiate"""
        RandomVariable.__init__(self, name, min_, max_)
        random = self.rand.uniform(0, 1)
        self.__value = random * (self.max - self.min) + self.min

    def __repr__(self):
        c_out = '%(parent)s value = %(value)-6.4g' % {'parent': RandomVariable.__repr__(self), 'value': self.__value}
        return c_out

    def get_value(self):
        """Get value of variable at time"""
        return self.__value


class NormalConstantVariable(RandomVariable):
    """Initialize to a normal random value"""

    def __init__(self, name, min_, max_):
        """Instantiate"""
        RandomVariable.__init__(self, name, min_, max_)
        random = math.sqrt(-2.0 * math.log10(self.rand.uniform(0, 1))) * math.cos(
            2.0 * 3.1415926 * self.rand.uniform(0, 1))
        self.__value = random * (self.max - self.min) + self.min

    def __repr__(self):
        c_out = '%(parent)s value = %(value)-6.4g' % {'parent': RandomVariable.__repr__(self), 'value': self.__value}
        return c_out

    def get_value(self):
        """Get value of variable at time"""
        return self.__value


def load_data(base_profile_data, base_profile_int_data, rand_profile_data):
    # Load
    if base_profile_data.load() == 0 or base_profile_int_data.load() == 0 or rand_profile_data.load() == 0:
        raise InputError('Trouble loading')
    # Change case to all caps in arrays
    base_profile_data.upcase()
    base_profile_int_data.upcase()
    rand_profile_data.upcase()
    # Strip comment lines from arrays
    base_profile_data.stripComments("#")
    base_profile_int_data.stripComments("#")
    rand_profile_data.stripComments("#")
    # Strip blank lines from arrays
    base_profile_data.stripBlankLines()
    base_profile_int_data.stripBlankLines()
    rand_profile_data.stripBlankLines()
    # Tokenize, creating separate internal token array.
    base_profile_data.tokenize(" \t\n\r,")
    base_profile_int_data.tokenize(" \t\n\r,")
    rand_profile_data.tokenize(" \t\n\r,")
    return


class Composite:
    """Combine vectors into final"""

    def __init__(self, base, rand):
        """Instantiate"""
        self.base = base
        self.rand = rand
        self.f_time = 0
        self.comp = []
        self.num = 0
        self.f_time = base.f_time
        # Form individual comp_ objects
        # First form non-random by direct assignment
        for i in range(self.base.num):
            base_name = self.base.curve[i].name
            j_rand = self.find_rand_name(base_name)
            if j_rand < 0:
                # found a non-random variable
                self.comp.append(self.base.curve[i])
                # Add last point
                j_last = self.base.curve[i].num - 1
                f_time = max(self.comp[self.num].time[j_last], self.base.f_time) + 10
                last_val = self.comp[self.num].val[j_last]
                self.comp[self.num].append_val(f_time, last_val, 1)
                self.num = len(self.comp)
        # Now form random
        for i in range(self.rand.num):
            rand_name = self.rand.ranObj[i].name
            j_base = self.find_base_name(rand_name)
            if j_base < 0:
                raise InputError('Random variable %(name)s not found in Baseline' % {'name': self.rand.ranObj[i].name})
            self.comp.append(Parameter(rand_name, self.base.curve[j_base].curve_type))
            # Time calculations
            update = self.rand.ranObj[i].update
            i_time = 0
            time_ = 0.0
            global INITAS
            while time_ < self.f_time:
                if i_time == 0:
                    INITAS = True
                else:
                    INITAS = False
                time_ = update * i_time
                i_time += 1
                value = rand.ranObj[i].update_var(update, time_)
                self.comp[self.num].append_val(time_, value, 0)
            # Consolidate with base
            self.comp[self.num].consolidate(self.base.curve[j_base])
            self.num += 1

    def find_base_name(self, rand_name):
        """Find index of random name in base variables.  Return -1 if fail."""
        i = 0
        while not rand_name == self.base.curve[i].name:
            i += 1
            if i == self.base.num:
                return -1
            return i

    def find_rand_name(self, base_name):
        """Find index of base name in random variables.  Return -1 if fail."""
        i = 0
        while not base_name == self.rand.ranObj[i].name:
            i += 1
            if i == self.rand.num:
                return -1
            return i

    def find_longest(self):
        """Find longest variable and number of time points."""
        j = 0
        n = 0
        for i in range(self.num):
            if self.comp[i].num > n:
                n = self.comp[i].num
                j = i
        return j, n

    def get_next_time(self, t_begin):
        """Find next time break that meets rig constraints"""
        t_max = t_begin + MAX_RIG_TIME - 4 * TIME_PAD  # Max time
        t_next = t_begin  # Chosen time returned
        t_lim = t_max  # Time limit based on num break points
        # t_end = 0  # Time limit based on max time
        for i in range(self.num):
            j_begin = self.comp[i].find_place(t_begin)
            j_end = self.comp[i].find_place(t_max)
            t_end = t_next
            if not j_end - j_begin == 0:
                t_end = min(self.comp[i].time[j_end], t_max)
            if j_end - j_begin > MAX_RIG_BREAKS - 3:
                j_end = j_begin + MAX_RIG_BREAKS - 3
                t_end = self.comp[i].time[j_end]
                t_lim = min(t_lim, t_end)
            t_next = min(max(t_next, t_end), t_lim)
        if t_next == t_begin:
            return 0
        else:
            return t_next

    def gen_files(self, tod):
        """Generate output files"""
        # Determine number of files needed and which variable is pacing item.
        t_begin = array.array('d')
        t_end = array.array('d')
        f_time = array.array('d')
        #  Use last 4 digits of time (autotv on rig doesn't like more)
        time_of_day = tod
        # Determine file breaks
        num_files = 0
        final_time = 0
        t_begin.append(0.0)
        t_end.append(self.get_next_time(0))
        while final_time < self.f_time and t_end[num_files] > 0:
            t_end[num_files] = min(t_end[num_files], self.f_time)
            f_time.append(t_end[num_files] - t_begin[num_files] + 4 * TIME_PAD)
            num_files += 1
            if num_files >= MAX_FILES:
                raise InputError('Too many files %(nf) requested, there are too many breakpoints for some reason' % {
                    'nf': num_files})
            t_begin.append(t_end[num_files - 1])
            final_time = t_end[num_files - 1]
            t_end.append(self.get_next_time(t_begin[num_files]))
        # Write the files
        for i in range(num_files):
            root_name = 'g%(tod)s%(i)i' % {'tod': time_of_day, 'i': i}
            def_name = root_name + '.def'
            int_name = root_name + '.int'
            scd_name = root_name + '.scd'
            crv_name = root_name + '.mtp'
            def_f = file(def_name, 'w')
            int_f = file(int_name, 'w')
            scd_f = file(scd_name, 'w')
            crv_f = file(crv_name, 'w')
            def_f.write(
                '# %(def_name)s generated by genGorilla.py\n# from %(baseN)s and %(randN)s.\n# seed= %(seed)i\n' % {
                    'def_name': def_name, 'baseN': self.base.name, 'randN': self.rand.name,
                    'seed': RandomVariable.firstRanSeed})
            int_f.write(
                '# %(int_name)s generated by genGorilla.py\n# from %(baseN)s and %(randN)s.\n'
                % {'int_name': int_name, 'baseN': self.base.name, 'randN': self.rand.name})
            scd_f.write(
                '# %(scd_name)s generated by genGorilla.py\n# from %(baseN)s and %(randN)s.\n'
                % {'scd_name': scd_name, 'baseN': self.base.name, 'randN': self.rand.name})
            crv_f.write(
                '# %(crv_name)s generated by genGorilla.py\n# from %(baseN)s and %(randN)s.\nTITLE1=\'%(baseN)s\','
                '\nTITLE2=\'%(crv_name)s\',\n'
                % {'crv_name': crv_name, 'baseN': self.base.name, 'randN': self.rand.name})
            # Stream out the scd file
            scd_f.write('START_TIME %(srt)8.3f\nSTOP_TIME  %(spt)8.3f' % {'srt': 2.0, 'spt': f_time[i] - TIME_PAD})
            # Stream out the def, init, and crv file
            def_f.write('$FTIME  %(ft)7.2f\n' % {'ft': f_time[i]})
            num_def_curves = 0
            for k in range(self.num):
                num, def_add, init_add = self.comp[k].partial_out(t_begin[i], t_end[i])
                if 0 < num:
                    num_def_curves += 1
                def_f.write(def_add)
                int_f.write(init_add)
                crv_f.write('$INPUT T=\'%(cn)s\',\n X= ' % {'cn': self.comp[k].name})
                for ll in range(self.comp[k].num):
                    crv_f.write('%(time)8.3f,' % {'time': self.comp[k].time[ll]})
                    if (ll + 1) % 9 < 1e-8:
                        crv_f.write('\n ')
                crv_f.write('\n Z=')
                for ll in range(self.comp[k].num):
                    crv_f.write('%(val)7.5g,' % {'val': self.comp[k].val[ll]})
                    if (ll + 1) % 9 < 1e-8:
                        crv_f.write('\n ')
                crv_f.write('\n$\n')
            if MAX_DEFINE_CURVES < num_def_curves:
                print 'WARNING(genGorilla.py):  too many curves in', def_name, 'for autotv on rig'
            def_f.close()
            print ('MESSAGE(genGorilla.py):  %(def_name)s generated from '
                   '%(baseN)s and %(randN)s' %
                   {'def_name': def_name, 'baseN': self.base.name, 'randN': self.rand.name})
            int_f.close()
            print ('MESSAGE(genGorilla.py):  %(int_name)s generated from %(baseN)s and %(randN)s' %
                   {'int_name': int_name, 'baseN': self.base.name, 'randN': self.rand.name})
            scd_f.close()
            print ('MESSAGE(genGorilla.py):  %(scd_name)s generated from %(baseN)s and %(randN)s' %
                   {'scd_name': int_name, 'baseN': self.base.name, 'randN': self.rand.name})
            crv_f.close()
            print ('MESSAGE(genGorilla.py):  %(crv_name)s generated from %(baseN)s and %(randN)s' %
                   {'crv_name': int_name, 'baseN': self.base.name, 'randN': self.rand.name})
        if not num_files:
            print 'WARNING(genGorilla.py): no files generated'

    def __repr__(self):
        """Print the class"""
        c_out = ""
        s_list = ['COMPOSITE=\n%(comp)s\n' % {'comp': self.comp[i]} for i in range(self.num)]
        c_out += "".join(s_list)
        return c_out


def main(argv):
    """Generate stress test vectors from FTS file inputs"""
    # program_name = 'genGorilla.py 0.0 23-Dec-2007 davegutz'
    # version = 0.0
    calibrating = False

    # Initialize static variables.
    global verbose
    verbose = 0
    # MAX_FILE_LINES   = 15000     # Maximum file length, arbitrary.
    # MAX_LINE            = 255       # Maximum line length, arbitrary.
    # MAX_CURVE_PTS        = 1000      # Maximum points allowed in input array.
    # MAX_AUTOTV_PTS   = 350       # Maximum points allowed by autotv on rig.
    options = ""
    remainder = ""
    try:
        options, remainder = getopt.getopt(argv, 'c:ho:Vv:',
                                           ['calibrating=', 'help', 'output=', 'version', 'verbose=', ])
    except getopt.GetoptError:
        usage(2)
    for opt, arg in options:
        if opt in ('-c', '--calibrating'):
            RandomVariable.firstRanSeed = int(arg)
            global first_seed
            first_seed = int(arg)
            calibrating = True
        elif opt in ('-h', '--help'):
            print usage(1)
        elif opt in ('-v', '--verbose'):
            verbose = int(arg)
        else:
            print usage(1)
        if len(remainder) < 2:
            print usage(1)

    # Load input files
    base_profile_data = InFile(remainder[0], remainder[0])
    int_str_set = StringSet.StringSet(remainder[0], ".")
    int_str_set.gsub('def', 'int')
    base_profile_int_data = InFile(int_str_set.reconstruct(), int_str_set.reconstruct())
    rand_profile_data = InFile(remainder[1], remainder[1])
    load_data(base_profile_data, base_profile_int_data, rand_profile_data)

    # Create profile definitions with curves from data.
    base_profile = Base(base_profile_data)
    base_profile.check_order()
    rand_profile = RandomAll(rand_profile_data)
    comp_profile = Composite(base_profile, rand_profile)

    # Generate output
    tod = time.time()
    if calibrating:
        comp_profile.gen_files(first_seed)
    else:
        comp_profile.gen_files(tod)

    print 'Done'


if __name__ == '__main__':
    # sys.exit(cProfile.run("main(sys.argv[1:])"))
    sys.exit(main(sys.argv[1:]))
