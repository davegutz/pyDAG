#!/usr/bin/env python
"""Generate stress test vectors from FTS file inputs
Usage: genGorilla <baseProfile.def> <monteCarloFile>
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
        
<baseProfile.def
is the FTS standard .def file defining the time varying inputs (see FTS)

<monteCarloFile>
is the local Monte Carlo definitions file with contents:

    NAME        UPDATE  TYPE    min max RISE_TYPE   min max FALL_TYPE   min     max HOLD_TYPE   min max absoluteMin absoluteMax
    plaslider   1       normal  -10 10  uniform     2   420 uniform     -240    -2  uniform     3   4   15          132

    NAME    UPDATE  switch  HOLD_TYPE   min max initialValue
    swwow   1       switch  uniform     1   5   1

    NAME        UPDATE  oneswitch   HOLD_TYPE   min max offTime
    MASTER_SWx  1       oneswitch   uniform     1   5   10

    NAME    normalconstant  min max absMin  absMax
    dtamb   normalconstant  -20 20  -119    44

    NAME uniformconstant min    max     absMin  absMax
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

from random import Random
import cProfile
import getopt
import array
import time
import math
import sys
import os

from pyDAG import InFile
from pyDAG import StringSet

CONSTANTSIZE = 6  # Length of a constant line in random file
MAXBRK = 50000  # Maximum intern temp parameter curve size
MAXDEFCURVES = 15  # Maximum number time vars in .def file.
MAXFILES = 25  # Maximum number of files allowed.
MAXRIGBRK = 200  # Maximum number of breakpoints autotv.
MAXRIGTIME = 3600  # Maximum allowed length of a rig reading.
MAXVAR = 75  # Local array size limit.
ONESWITCHSIZE = 7  # Length of a oneswitch line in random file
REGULARSIZE = 16  # Length of a regular line in random file
SWITCHSIZE = 7  # Length of a switch line in random file
TIMEPAD = 5.  # Flats at beginning and end of files.
TIMERES = 1e-5  # Resolution time= test.


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
        self.message = message
        self.usage = usage

    def __str__(self):
        if self.usage:
            return repr(self.message) + '\n\n%(doc)s' % {'doc': __doc__}
        else:
            return repr(self.message)


def usage(code, msg=''):
    "Usage description"
    print >> sys.stderr, __doc__
    if msg:
        print >> sys.stderr, msg
    sys.exit(code)


def VARDELAY(input, update, tfdelay, ftdelay, icval, state):
    "Variable delay function"
    tf = tfdelay / update
    ft = ftdelay / update
    global INITAS
    if INITAS:
        output = icval
        if icval:
            state = long(tf)
        else:
            state = -long(ft + 1.0)
        return output, state
    if state >= 0:
        if input:
            state = long(tf)
        else:
            state = state - 1
            if state < 0:   state = -long(ft + 1.0)
    else:
        if input:
            state = state + 1
            if state >= 0:  state = long(tf)
        else:
            state = -long(ft + 1.0)
    output = state >= 0
    return output, state


class ICvalue:
    "Keep track of initial value for a parameter"

    def __init__(self, name, val):
        "Instantiate"
        self.name = name
        self.val = val

    def __repr__(self):
        "Print the class"
        cout = '%(name)12s %(val)13.4f\n' % {'name': self.name, 'val': self.val}
        return cout


class Parameter:
    "Keep track of a single parameter"

    def __init__(self, name, type):
        self.name = name
        self.num = 0
        self.curveType = type
        self.time = array.array('d')
        self.val = array.array('d')
        self.__marked = array.array('i')

    def __repr__(self):
        "Print the class"
        cout = '%(name)-12s %(type)2d %(num)4d' % {'name': self.name, 'type': self.curveType, 'num': self.num}
        slist = ['\n%(t)-7.2f %(v)-13.4f' % {'t': self.time[i], 'v': self.val[i]} for i in range(self.num)]
        cout += "".join(slist)
        return cout

    def checkOrder(self):
        "Check time monotonically increasing"
        badOne = 0;
        for i in range(self.num - 1):
            if self.time[i] >= self.time[i + 1]:
                print 'ERROR(genGorilla.py):  Variable', self.name, \
                    'time value not monotonically increasing at', i, \
                    'place, time approximately', self.time[i], '.'
                badOne += 1
        if badOne:
            return -1
        else:
            return 0

    def insertVal(self, t, v, mark, i):
        "Insert a breakpoint after i"
        if self.num >= MAXBRK:
            raise InputError('Too many breakpoints added into %(name)s by consolidation' % {'name': self.name})
        self.num += 1
        self.time.insert(i + 1, t)
        self.val.insert(i + 1, v)
        self.__marked.insert(i + 1, mark)

    def appendVal(self, t, v, mark):
        "Append a breakpoint"
        if self.num >= MAXBRK:
            raise InputError('Too many breakpoints added into %(name)s by consolidation' % {'name': self.name})
        self.num += 1
        self.time.append(t)
        self.val.append(v)
        self.__marked.append(mark)

    def consolidate(self, newCurve, absMin, absMax):
        "Consolidate newCurve with present."
        newNum = newCurve.num
        if self.time[self.num - 1] < newCurve.time[newNum - 1]:
            self.appendVal(newCurve.time[newNum - 1], self.val[self.num - 1], 0)
        elif self.time[self.num - 1] > newCurve.time[newNum - 1]:
            newCurve.appendVal(self.time[self.num - 1], newCurve.val[newNum - 1], 0)
        # Add extra breakpoints to curve random
        for i in range(newNum):
            newTime = newCurve.time[i]
            newPlace = self.findPlace(newTime)
            if newPlace < 0:
                raise InputError('Table %(newCurvename)s does not overlap %(name)s' % {'newCurvename': newCurve.name,
                                                                                       'name': self.name})
            if math.fabs(newTime - self.time[newPlace]) >= TIMERES:
                betweenVal = self.interpolate(newTime, newPlace)
                self.insertVal(newTime, betweenVal, 0, newPlace)

    def findPlace(self, time):
        "Find element location"
        for i in range((self.num - 1), 0, -1):
            if self.time[i] <= time + TIMERES: break
        if i == self.num:
            return -1
        else:
            return i

    def interpolate(self, time, place):
        "Interpolate curve value"
        if place < 0:
            value = self.val[0]
        elif place < self.num - 1:
            value = (time - self.time[place]) / (self.time[place + 1] - self.time[place]) * \
                    (self.val[place + 1] - self.val[place]) + self.val[place]
        else:
            value = self.val[self.num - 1]
        return value

    def partialOut(self, begin, end):
        "Stream out the parameter to streams defOut and initOut.  Return number of points streamed"
        #  Find begin, end.  Print header.  Tare the time.
        time = 0.0
        jbegin = self.findPlace(begin)
        jend = max(self.findPlace(end), jbegin)
        numPts = jend - jbegin + 3
        value = self.val[jbegin]
        initOut = '%(name)-17s %(val)13.4f\n' % {'name': self.name, 'val': value}
        defOut = ""
        # If constant through transient, return right away.
        curveIsConstant = 1
        for k in range(jbegin + 1, jend):
            if not self.val[k] == self.val[k - 1]:
                curveIsConstant = 0
                break
        if curveIsConstant: return 0, defOut, initOut
        #  Otherwise print title and first point.
        numOut = 0
        defOut = '$INPUT %(name)s  %(curveType)-2i %(numPts)-4i\n' % {'name': self.name, 'curveType': self.curveType,
                                                                      'numPts': numPts}
        value = self.val[jbegin]
        defOut += ' %(time)7.2f  %(value)13.4f\n' % {'time': time, 'value': value}
        numOut += 1
        # Hold the beginning
        time = TIMEPAD
        defOut += ' %(time)7.2f  %(value)13.4f\n' % {'time': time, 'value': value}
        numOut += 1
        # Body of points
        for k in range(jbegin + 1, jend + 1):
            time = self.time[k] - begin + TIMEPAD
            value = self.val[k]
            defOut += ' %(time)7.2f  %(value)13.4f\n' % {'time': time, 'value': value}
            numOut += 1
        # Hold the end
        time = end - begin + 4 * TIMEPAD
        defOut += ' %(time)7.2f  %(value)13.4f\n' % {'time': time, 'value': value}
        numOut += 1
        # Done
        return numOut, defOut, initOut


class Base:
    "Keep track of multiple parameters"

    def __repr__(self):
        "Print the class"
        cout = '%(name)s \nftime=%(ftime)f\n' % {'name': self.name, 'ftime': self.ftime}
        slist = ['%(curve)s\n' % {'curve': self.curve[i]} for i in range(self.num)]
        cout += "".join(slist)
        return cout
        #  for ( int i=0; i<base.numIC_; i++ )
        #   {
        #     out << *base.init(i);
        #   }
        return cout

    def __init__(self, defInput, intInput):
        "Instantiate"
        self.ftime = 0.0
        self.name = 'temp'
        self.name = defInput.programName
        self.num = 0
        self.numIC = 0
        self.curve = []
        # Find FTIME
        i = 0
        while not (defInput.LineS(i)[1] == "$FTIME") and i < defInput.numLines:  i += 1
        if i >= defInput.numLines:
            raise InputError('$FTIME line not found')
        else:
            if len(defInput.LineS(i)) == 4:
                self.ftime = float(defInput.LineS(i)[2])
            else:
                raise InputError('In %(line)s, 2 fields needed' % {'line': defInput.LineS(i).str})
        # Find curves
        i = 0
        while True:
            i = defInput.findStr("$INPUT", i)
            if i >= defInput.numLines - 1: break
            curvename = defInput.LineS(i)[2]
            if len(defInput.LineS(i)) < 5:
                raise InputError('Need type spec for input %(cn)s' % {'cn': curvename})
            curveType = int(defInput.LineS(i)[3])
            if self.num >= MAXVAR:
                raise InputError('%(cn)s is too long' % {'cn': curvename})
            self.curve.append(Parameter(defInput.LineS(i)[2], curveType))
            i += 1
            while (defInput.LineS(i)[1][0].isdigit() or defInput.LineS(i)[1][0] == '.') and i < defInput.numLines:
                self.curve[self.num].appendVal(float(defInput.LineS(i)[1]), float(defInput.LineS(i)[2]), 1)
                i += 1
            self.num = len(self.curve)

    def checkOrder(self):
        "Make sure time monotonically increasing"
        badOrder = 0
        for i in range(self.num):
            if -1 == self.curve[i].checkOrder(): badOrder = 1
        if badOrder:
            raise InputError('Time is not monotonically increasing in a curve input')


class RandomAll():
    "Randomized container for entire program"

    def __init__(self, mtcInput):
        "Instantiate"
        self.name = mtcInput.programName
        self.num = 0
        self.ranObj = []
        i = 0
        while i < mtcInput.numLines:
            # Range check
            if self.num > MAXVAR:
                raise InputError('Too many variables in %(cn)s' % {'cn': mtcInput.name()})
            size = len(mtcInput.LineS(i))
            tok002 = mtcInput.LineS(i)[2]
            tok003 = mtcInput.LineS(i)[3]
            if not (size == REGULARSIZE + 2 or \
                    (size == SWITCHSIZE + 2 and tok003 == 'SWITCH') or \
                    (size == ONESWITCHSIZE + 2 and tok003 == 'ONESWITCH') or \
                    (size == CONSTANTSIZE + 2 and tok002 == 'UNIFORMCONSTANT') or \
                    (size == CONSTANTSIZE + 2 and tok002 == 'NORMALCONSTANT')):
                raise InputError('Improper format in %(pn)s at:%(line)s' % {'pn': mtcInput.programName,
                                                                            'line': mtcInput.LineS(i).str}, 1)
            self.ranObj.append(RanDeltaVar(mtcInput.LineS(i)))
            i += 1
        self.num = len(self.ranObj)

    def __repr__(self):
        "Print the class"
        cout = self.name
        slist = ['\n%(ranObj)s' % {'ranObj': self.ranObj[i]} for i in range(self.num)]
        cout += "".join(slist)
        return cout


class RandomVariable():
    "Random variable"
    firstRanSeed = None  # first of seeds
    ranSeed = None  # state of seed, incremented each  new instance and remembered

    def __init__(self, name, min, max=100000):
        "Instantiate"
        self.name = name
        self.min = min
        self.max = max
        if self.min > self.max:
            print 'WARNING(genGorilla.py):  min/max disagree for variable', self.name
        if not RandomVariable.firstRanSeed: RandomVariable.firstRanSeed = os.getpid()
        if not RandomVariable.ranSeed:
            RandomVariable.ranSeed = RandomVariable.firstRanSeed
        else:
            RandomVariable.ranSeed += 1
        self.ranSeed = RandomVariable.ranSeed
        self.rand = Random(self.ranSeed)

    def getValue(self):
        "Value at time"
        return 0.0

    def getValueFromPast(self, past):
        "Value at time from past"
        global INITAS
        #  if ( INITAS ) return past;
        if past == self.max:
            return self.min
        else:
            return self.max

    def __repr__(self):
        "Print the class"
        cout = 'RandomVariable %(name)-6s min = %(min)-6.4g  max = %(max)-6.4g seed = %(seed)-6i' % {'name': self.name,
                                                                                                     'min': self.min,
                                                                                                     'max': self.max,
                                                                                                     'seed': self.ranSeed}
        return cout

        #  // element access


class RanDeltaVar():
    "Random delta variable, adder on nominal curves"

    def __init__(self, LineS):
        "Instantiate"
        self.update = 0.0
        self.__rise = 0.0
        self.__input = 0.0
        self.__hold = 0.0
        self.__fall = 0.0
        self.__istate1 = 0
        self.__state2 = 0.0
        self.__bstate3 = True
        self.__state4 = 0.0
        self.__state5 = 0.0
        self.__state6 = 0.0
        self.__state7 = 0.0
        self.min = 0.0
        self.max = 0.0
        self.absMin = 0.0
        self.absMax = 0.0
        self.__output = 0.0
        self.__limited = False
        self.__initialValue = 0.0
        self.__offTime = 0.0
        self.name = None
        self.__type = None
        self.__inputV = None
        self.__riseV = None
        self.__fallV = None
        self.__holdV = None
        size = len(LineS)
        if size == REGULARSIZE + 2:
            self.__type = LineS[3]
            self.name = LineS[1]
            self.update = float(LineS[2])
            inputType = LineS[3]
            inputMin = float(LineS[4])
            inputMax = float(LineS[5])
            riseType = LineS[6]
            riseMin = float(LineS[7])
            riseMax = float(LineS[8])
            fallType = LineS[9]
            fallMin = float(LineS[10])
            fallMax = float(LineS[11])
            holdType = LineS[12]
            holdMin = float(LineS[13])
            holdMax = float(LineS[14])
            absMin = float(LineS[15])
            absMax = float(LineS[16])
            self.min = inputMin
            self.max = inputMax
            self.absMin = absMin
            self.absMax = absMax
        elif size == SWITCHSIZE + 2 and LineS[3] == "SWITCH":
            self.__type = LineS[3]
            self.name = LineS[1]
            self.update = float(LineS[2])
            inputType = LineS[3]
            inputMin = -1.0
            inputMax = 1.0
            riseType = 'CONSTANT'
            riseMin = (1.0 / self.update + 1.0)
            riseMax = (1.0 / self.update + 1.0)  # TODO dirty hack
            fallType = 'CONSTANT'
            fallMin = -(1.0 / self.update + 1.0)
            fallMax = -(1.0 / self.update + 1.0)
            holdType = LineS[4]
            holdMin = float(LineS[5])
            holdMax = float(LineS[6])
            self.min = inputMin
            self.max = inputMax
            self.absMin = 0.0
            self.absMax = 1.0
            self.__initialValue = int(LineS[7])
        elif size == ONESWITCHSIZE + 2 and LineS[3] == "ONESWITCH":
            self.__type = LineS[3]
            self.name = LineS[1]
            self.update = float(LineS[2])
            inputType = LineS[3]
            inputMin = -1.0
            inputMax = 1.0
            riseType = 'CONSTANT'
            riseMin = (1.0 / self.update + 1.0)
            riseMax = (1.0 / self.update + 1.0)  # TODO dirty hack
            fallType = 'CONSTANT'
            fallMin = -(1.0 / self.update + 1.0)
            fallMax = -(1.0 / self.update + 1.0)
            holdType = LineS[4]
            holdMin = float(LineS[5])
            holdMax = float(LineS[6])
            self.min = float(LineS[7]);
            self.max = inputMax
            self.absMin = 0.0
            self.absMax = 1.0
            self.__initialValue = int(LineS[7]);
        elif size == CONSTANTSIZE + 2 and (LineS[2] == "NORMALCONSTANT" or LineS[2] == "UNIFORMCONSTANT"):
            self.__type = LineS[2]
            self.name = LineS[1]
            self.update = 1
            inputType = LineS[2]
            inputMin = float(LineS[3])
            inputMax = float(LineS[4])
            riseType = 'CONSTANT'
            riseMin = 1
            riseMax = 1
            fallType = 'CONSTANT'
            fallMin = -1
            fallMax = -1
            holdType = "CONSTANT"
            holdMin = 0
            holdMax = -1
            absMin = float(LineS[5])
            absMax = float(LineS[6])
            self.min = inputMin
            self.max = inputMax
            self.absMin = absMin
            self.absMax = absMax
        else:
            raise InputError('Unknown type at %(line)s' % {'line': LineS.str})
        if self.update <= 0.0:
            raise InputError('Bad update at %(line)s' % {'line': LineS.str})
        self.__inputV = self.makeRanVar('INPUT', inputType, inputMin, inputMax)
        self.__riseV = self.makeRanVar('RISE', riseType, riseMin, riseMax)
        self.__fallV = self.makeRanVar('FALL', fallType, fallMin, fallMax)
        self.__holdV = self.makeRanVar('HOLD', holdType, holdMin, holdMax)

    def __repr__(self):
        "Print the class"
        cout = '%(name)-12s\n  inputV= %(inputV)s\n  riseV = %(riseV)s\n  fallV = %(fallV)s\n  holdV = %(holdV)s' \
               % {'name': self.name, 'inputV': self.__inputV, 'riseV': self.__riseV, 'fallV': self.__fallV,
                  'holdV': self.__holdV}
        return cout

    def makeRanVar(self, name, type, min, max):
        "Make random variable from input"
        if type == 'UNIFORM':
            return UniformRandomVariable(name, min, max)
        elif type == 'NORMAL':
            return NormalRandomVariable(name, min, max)
        elif type == 'SWITCH':
            return SwitchVariable(name, min, max, self.__initialValue)
        elif type == 'ONESWITCH':
            return OneSwitchVariable(name, min, max, self.__offTime)
        elif type == 'CONSTANT':
            return ConstantVariable(name, min)
        elif type == 'UNIFORMCONSTANT':
            return UniformConstantVariable(name, min, max)
        elif type == 'NORMALCONSTANT':
            return NormalConstantVariable(name, min, max)
        else:
            print 'WARNING(genGorilla.py):  variable type', type, 'not supported for variable', \
                name, '.  Assuming UNIFORM'
            return UniformRandomVariable(name, min, max)

    def updateVar(self, update, time):
        "Generate Monte-Carlo"
        self.__rise = self.__riseV.getValue()
        self.__hold = self.__holdV.getValue()
        self.__fall = self.__fallV.getValue()
        global INITAS
        if self.__type == "SWITCH":
            if INITAS:  self.__output = self.__initialValue
            self.__input = self.__inputV.getValueFromPast(self.__output)
        elif self.__type == "ONESWITCH":
            if INITAS:  self.__output = 0;
            if 0 == self.__output:
                self.__input = self.__inputV.getValueFromPast(self.__output)
        else:
            self.__input = self.__inputV.getValue()

        if self.__type == "NORMALCONSTANT" or self.__type == "UNIFORMCONSTANT":
            self.__input = self.__inputV.getValue()
            self.__output = self.__input
        else:
            self.__output = self.MONTECARLO(update)
            global verbose
            if verbose > 1:
                if INITAS:  print '\ntype=', self.__type, '\ntime   input  rise   hold   fall   update  istate1  state2  limited bstate3 state4  state5  output'
                print '%(ti)-7.1f%(in)-7.2f%(ri)-7.2f%(ho)-7.2f%(fa)-7.2f%(up)-7.2f %(hi1)-8i %(hs2)-7.2f %(li)-7.0f %(hb3)-7.2f %(hs4)-7.2f %(hs5)-7.2f %(ou)-7.2f' \
                      % {'ti': time, 'in': self.__input, 'ri': self.__rise, 'ho': self.__hold, 'fa': self.__fall,
                         'up': update, \
                         'hi1': self.__istate1, 'hs2': self.__state2, 'li': self.__limited, 'hb3': self.__bstate3,
                         'hs4': self.__state4, 'hs5': self.__state5, 'ou': self.__output}

        if self.__type == "ONESWITCH":
            if time > self.__offTime: self.__output = 0

        return self.__output

    def MONTECARLO(self, update):
        "Generate waveform.  See the Gorilla documentation."
        global INITAS
        if INITAS: self.__state6 = self.__input

        (heldOutput, heldFrozen) = self.HOLDER(self.__input, update)
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
        outputMax = self.update * state4 + self.__state6
        outputMin = self.update * state5 + self.__state6
        if output > outputMax:
            output = outputMax
            self.__limited = True
        elif output < outputMin:
            output = outputMin
            self.__limited = True
        self.__state6 = output
        return output

    def HOLDER(self, input, update):
        "Control update action of the MONTECARLO function.  See the Gorilla documentation"
        global INITAS
        if INITAS:
            self.__state2 = input
            self.__bstate3 = True
        if self.__bstate3:
            output = self.__state2
        else:
            output = input
        varInput = (not self.__bstate3 and not output == self.__state2) or self.__limited
        (varOutput, self.__istate1) = VARDELAY(varInput, update, self.__hold, 0.0, True, self.__istate1)
        frozen = self.__bstate3
        self.__state2 = output
        self.__bstate3 = varOutput
        return output, frozen


class UniformRandomVariable(RandomVariable):
    "Uniform distribution"

    def __init__(self, name, min, max):
        "Instantiate"
        RandomVariable.__init__(self, name, min, max)

    def getValue(self):
        "Get value of variable at time"
        global INITAS
        if INITAS and self.min <= 0: return 0.0
        random = self.rand.uniform(0, 1)
        return random * (self.max - self.min) + self.min


class NormalRandomVariable(RandomVariable):
    "Normal distribution"

    def __init__(self, name, min, max):
        "Instantiate"
        RandomVariable.__init__(self, name, min, max)

    def getValue(self):
        "Get value of variable at time"
        global INITAS
        if INITAS and self.min <= 0: return 0.0
        random = math.sqrt(-2.0 * math.log10(self.rand.uniform(0, 1))) * cos(2.0 * 3.1415926 * self.rand.uniform(0, 1))
        return random * (self.max - self.min) + self.min


class SwitchVariable(RandomVariable):
    "Random two-level"

    def __init__(self, name, min, max, initialValue):
        "Instantiate"
        RandomVariable.__init__(self, name, min, max)
        self.__initialValue = initialValue

    def __repr__(self):
        cout = '%(parent)s initialValue= %(initialValue)-12.4g' % {'parent': RandomVariable.__repr__(self),
                                                                   'initialValue': self.__initialValue}
        return cout


class OneSwitchVariable(RandomVariable):
    "Random on/off"

    def __init__(self, name, min, max, offTime):
        "Instantiate"
        RandomVariable.__init__(self, name, min, max)
        self.__offTime = offTime

    def __repr__(self):
        cout = '%(parent)s offTime = %(offTime)-6.4g' % {'parent': RandomVariable.__repr__(self),
                                                         'offTime': self.__offTime}
        return cout


class ConstantVariable(RandomVariable):
    "Constant"

    def __init__(self, name, val):
        "Instantiate"
        RandomVariable.__init__(self, name, val)
        self.__value = val

    def __repr__(self):
        cout = '%(parent)s value = %(value)-6.4g' % {'parent': RandomVariable.__repr__(self), 'value': self.__value}
        return cout

    def getValue(self):
        "Get value of variable at time"
        return self.__value


class UniformConstantVariable(RandomVariable):
    "Initialize to a uniformly random value"

    def __init_(self, name, min, max):
        "Instantiate"
        RandomVariable.__init__(self, name, min, max)
        random = self.rand.uniform(0, 1)
        self.__value = random * (self.max - self.min) + self.min

    def __repr__(self):
        cout = '%(parent)s value = %(value)-6.4g' % {'parent': RandomVariable.__repr__(self), 'value': self.__value}
        return cout

    def getValue(self):
        "Get value of variable at time"
        return self.__value


class NormalConstantVariable(RandomVariable):
    "Initialize to a normal random value"

    def __init__(self, name, min, max):
        "Instantiate"
        RandomVariable.__init__(self, name, min, max)
        random = math.sqrt(-2.0 * math.log10(self.rand.uniform(0, 1))) * math.cos(
            2.0 * 3.1415926 * self.rand.uniform(0, 1))
        self.__value = random * (self.max - self.min) + self.min

    def __repr__(self):
        cout = '%(parent)s value = %(value)-6.4g' % {'parent': RandomVariable.__repr__(self), 'value': self.__value}
        return cout

    def getValue(self):
        "Get value of variable at time"
        return self.__value


def loadData(baseProfileData, baseProfileIntData, randProfileData):
    # Load
    if baseProfileData.load() == 0 or baseProfileIntData.load() == 0 or randProfileData.load() == 0:
        raise InputError('Trouble loading')
    # Change case to all caps in arrays
    baseProfileData.upcase()
    baseProfileIntData.upcase()
    randProfileData.upcase()
    # Strip comment lines from arrays
    baseProfileData.stripComments("#")
    baseProfileIntData.stripComments("#")
    randProfileData.stripComments("#")
    # Strip blank lines from arrays
    baseProfileData.stripBlankLines()
    baseProfileIntData.stripBlankLines()
    randProfileData.stripBlankLines()
    # Tokenize, creating separate internal token array.
    baseProfileData.tokenize(" \t\n\r,")
    baseProfileIntData.tokenize(" \t\n\r,")
    randProfileData.tokenize(" \t\n\r,")
    return


class Composite():
    "Combine vectors into final"

    def __init__(self, base, rand):
        "Instantiate"
        self.base = base;
        self.rand = rand;
        self.ftime = 0;
        self.comp = [];
        self.num = 0;
        self.ftime = base.ftime
        # Form individual comp_ objects
        # First form non-random by direct assignment
        for i in range(self.base.num):
            baseName = self.base.curve[i].name
            jrand = self.findRandName(baseName)
            if jrand < 0:
                # found a non-random variable
                self.comp.append(self.base.curve[i])
                # Add last point
                jlast = self.base.curve[i].num - 1
                ftime = max(self.comp[self.num].time[jlast], self.base.ftime) + 10
                lastval = self.comp[self.num].val[jlast]
                self.comp[self.num].appendVal(ftime, lastval, 1)
                self.num = len(self.comp)
        # Now form random
        for i in range(self.rand.num):
            randName = self.rand.ranObj[i].name
            jbase = self.findBaseName(randName)
            if jbase < 0:
                raise InputError('Random variable %(name)s not found in Baseline' % {'name': self.rand.ranObj[i].name})
            self.comp.append(Parameter(randName, self.base.curve[jbase].curveType))
            # Time calculations
            update = self.rand.ranObj[i].update
            itime = 0
            time = 0.0
            global INITAS
            while time < self.ftime:
                if itime == 0:
                    INITAS = True
                else:
                    INITAS = False
                time = update * itime
                itime += 1
                value = rand.ranObj[i].updateVar(update, time)
                self.comp[self.num].appendVal(time, value, 0)
            # Consolidate with base
            absMax = self.rand.ranObj[i].absMax
            absMin = self.rand.ranObj[i].absMin
            self.comp[self.num].consolidate(self.base.curve[jbase], absMin, absMax)
            self.num += 1

    def findBaseName(self, randName):
        "Find index of random name in base variables.  Return -1 if fail."
        i = 0
        while not randName == self.base.curve[i].name:
            i += 1
            if i == self.base.num: return -1
            return i

    def findRandName(self, baseName):
        "Find index of base name in random variables.  Return -1 if fail."
        i = 0
        while not baseName == self.rand.ranObj[i].name:
            i += 1
            if i == self.rand.num: return -1
            return i

    def findLongest(self, j, n):
        "Find longest variable and number of time points."
        j = 0
        n = 0
        for i in range(self.num):
            if self.comp[i].num > n:
                n = self.comp[i].num
                j = i
        return (j, n)

    def getNextTime(self, tbegin):
        "Find next time break that meets rig constraints"
        tmax = tbegin + MAXRIGTIME - 4 * TIMEPAD  # Max time
        tnext = tbegin  # Chosen time returned
        tlim = tmax  # Time limit based on num brkpts
        tend = 0  # Time limit based on max time
        for i in range(self.num):
            jbegin = self.comp[i].findPlace(tbegin)
            jend = self.comp[i].findPlace(tmax)
            tend = tnext
            if not jend - jbegin == 0:
                tend = min(self.comp[i].time[jend], tmax)
            if jend - jbegin > MAXRIGBRK - 3:
                jend = jbegin + MAXRIGBRK - 3
                tend = self.comp[i].time[jend]
                tlim = min(tlim, tend)
            tnext = min(max(tnext, tend), tlim)
        if tnext == tbegin:
            return 0
        else:
            return tnext

    def genFiles(self, tod, seed):
        "Generate output files"
        # Determine number of files needed and which variable is pacing item.
        global firstSeed
        tbegin = array.array('d')
        tend = array.array('d')
        ftime = array.array('d')
        #  Use last 4 digits of time (autotv on rig doesn't like more)
        timeofday = tod
        # Determine file breaks
        numFiles = 0
        finalTime = 0
        tbegin.append(0.0)
        tend.append(self.getNextTime(0))
        while finalTime < self.ftime and tend[numFiles] > 0:
            tend[numFiles] = min(tend[numFiles], self.ftime)
            ftime.append(tend[numFiles] - tbegin[numFiles] + 4 * TIMEPAD)
            numFiles += 1
            if numFiles >= MAXFILES:
                raise InputError('Too many files (%(nf)) requested, there are too many breakpoints for some reason' % {
                    'nf': numFiles})
            tbegin.append(tend[numFiles - 1])
            finalTime = tend[numFiles - 1]
            tend.append(self.getNextTime(tbegin[numFiles]))
        # Write the files
        for i in range(numFiles):
            rootName = 'g%(tod)s%(i)i' % {'tod': timeofday, 'i': i}
            defName = rootName + '.def'
            intName = rootName + '.int'
            scdName = rootName + '.scd'
            crvName = rootName + '.mtp'
            deff = file(defName, 'w')
            intf = file(intName, 'w')
            scdf = file(scdName, 'w')
            crvf = file(crvName, 'w')
            deff.write(
                '# %(defName)s generated by genGorilla.py\n# from %(baseN)s and %(randN)s.\n# seed= %(seed)i\n' % {
                    'defName': defName, 'baseN': self.base.name, 'randN': self.rand.name,
                    'seed': RandomVariable.firstRanSeed})
            intf.write(
                '# %(intName)s generated by genGorilla.py\n# from %(baseN)s and %(randN)s.\n' % {'intName': intName,
                                                                                                 'baseN': self.base.name,
                                                                                                 'randN': self.rand.name})
            scdf.write(
                '# %(scdName)s generated by genGorilla.py\n# from %(baseN)s and %(randN)s.\n' % {'scdName': scdName,
                                                                                                 'baseN': self.base.name,
                                                                                                 'randN': self.rand.name})
            crvf.write(
                '# %(crvName)s generated by genGorilla.py\n# from %(baseN)s and %(randN)s.\nTITLE1=\'%(baseN)s\',\nTITLE2=\'%(crvName)s\',\n' % {
                    'crvName': crvName, 'baseN': self.base.name, 'randN': self.rand.name})
            # Stream out the scd file
            scdf.write('START_TIME %(srt)8.3f\nSTOP_TIME  %(spt)8.3f' % {'srt': 2.0, 'spt': ftime[i] - TIMEPAD})
            # Stream out the def, init, and crv file
            deff.write('$FTIME  %(ft)7.2f\n' % {'ft': ftime[i]})
            numDefCurves = 0
            for k in range(self.num):
                num, defAdd, initAdd = self.comp[k].partialOut(tbegin[i], tend[i])
                if 0 < num: numDefCurves += 1
                deff.write(defAdd)
                intf.write(initAdd)
                crvf.write('$INPUT T=\'%(cn)s\',\n X= ' % {'cn': self.comp[k].name})
                for ll in range(self.comp[k].num):
                    crvf.write('%(time)8.3f,' % {'time': self.comp[k].time[ll]})
                    if (ll + 1) % 9 < 1e-8:  crvf.write('\n ')
                crvf.write('\n Z=')
                for ll in range(self.comp[k].num):
                    crvf.write('%(val)7.5g,' % {'val': self.comp[k].val[ll]})
                    if (ll + 1) % 9 < 1e-8:  crvf.write('\n ')
                crvf.write('\n$\n')
            if MAXDEFCURVES < numDefCurves:
                print 'WARNING(genGorilla.py):  too many curves in', defName, 'for autotv on rig'
            deff.close();
            print ('MESSAGE(genGorilla.py):  %(defName)s generated from %(baseN)s and %(randN)s' % {'defName': defName,
                                                                                                    'baseN': self.base.name,
                                                                                                    'randN': self.rand.name})
            intf.close();
            print ('MESSAGE(genGorilla.py):  %(intName)s generated from %(baseN)s and %(randN)s' % {'intName': intName,
                                                                                                    'baseN': self.base.name,
                                                                                                    'randN': self.rand.name})
            scdf.close();
            print ('MESSAGE(genGorilla.py):  %(scdName)s generated from %(baseN)s and %(randN)s' % {'scdName': intName,
                                                                                                    'baseN': self.base.name,
                                                                                                    'randN': self.rand.name})
            crvf.close();
            print ('MESSAGE(genGorilla.py):  %(crvName)s generated from %(baseN)s and %(randN)s' % {'crvName': intName,
                                                                                                    'baseN': self.base.name,
                                                                                                    'randN': self.rand.name})
        if not numFiles: print 'WARNING(genGorilla.py):  no files generated'

    def __repr__(self):
        "Print the class"
        slist = ['COMPOSITE=\n%(comp)s\n' % {'comp': self.comp[i]} for i in range(self.num)]
        cout += "".join(slist)
        return cout


def main(argv):
    "Generate stress test vectors from FTS file inputs"
    programName = 'genGorilla.py 0.0 23-Dec-2007 davegutz'
    version = 0.0
    calibrating = False

    # Initialize static variables.
    global verbose
    verbose = 0
    # MAXFILELINES   = 15000     # Maximum file length, arbitrary.
    # MAXLINE            = 255       # Maximum line length, arbitrary.
    # MAXCURVEPTS        = 1000      # Maximum points allowed in input array.
    # MAXAUTOTVPTS   = 350       # Maximum points allowed by autotv on rig.
    try:
        options, remainder = getopt.getopt(argv, 'c:ho:Vv:',
                                           ['calibrating=', 'help', 'output=', 'version', 'verbose=', ])
    except getopt.GetoptError:
        usage(2)
    for opt, arg in options:
        if opt in ('-c', '--calibrating'):
            RandomVariable.firstRanSeed = int(arg)
            firstSeed = int(arg)
            calibrating = True
        elif opt in ('-h', '--help'):
            print usage(1)
        elif opt in ('-o', '--output'):
            outputFilename = arg
        elif opt in ('-v', '--verbose'):
            verbose = int(arg)
        elif opt in ('-V', '--version'):
            version = arg
        else:
            print usage(1)
        if len(remainder) < 2:
            print usage(1)

    # Load input files
    baseProfileData = InFile(remainder[0], remainder[0])
    intStrSet = StringSet.StringSet(remainder[0], ".")
    intStrSet.gsub('def', 'int')
    baseProfileIntData = InFile(intStrSet.reconstruct(), intStrSet.reconstruct())
    randProfileData = InFile(remainder[1], remainder[1])
    loadData(baseProfileData, baseProfileIntData, randProfileData)

    # Create profile definitions with curves from data.
    baseProfile = Base(baseProfileData, baseProfileIntData)
    baseProfile.checkOrder()
    randProfile = RandomAll(randProfileData)
    compProfile = Composite(baseProfile, randProfile)

    # Generate output
    tod = time.time()
    if calibrating:
        compProfile.genFiles(firstSeed, firstSeed)
    else:
        compProfile.genFiles(tod, firstSeed)

    print 'Done'


if __name__ == '__main__':
    # sys.exit(cProfile.run("main(sys.argv[1:])"))
    sys.exit(main(sys.argv[1:]))
