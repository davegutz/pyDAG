#!/usr/bin/env python
r""" Input file module, parse and manipulate input files

Tests:
>>> import InFile
>>> tf=open('temp', 'wb')
>>> tf.write("This is the first line.\n\nThis is the third line.\nThis is the fourth line.\nThis is also a third line.\n")
>>> tf.close()
>>> infile=InFile.InFile('temp','asTemp')
>>> infile.load()

>>> infile
asTemp (5 lines):
0:This is the first line.
1:
2:This is the third line.
3:This is the fourth line.
4:This is also a third line.
<BLANKLINE>

Properties of the infile
>>> len(infile.lines)
5
>>> infile.numLines
5
>>> infile.Line(1600)
'This is also a third line.\n'

Modify it
>>> infile.stripBlankLines()
1
>>> infile.numLines
4
>>> infile
asTemp (4 lines):
0:This is the first line.
1:This is the third line.
2:This is the fourth line.
3:This is also a third line.
<BLANKLINE>
>>> infile.loadVars()
17
>>> infile.nVars
17
>>> infile.tokenize(";[]{}()!@#$%^&*-+_=`~/<>,.:'")
12
>>> infile.LineS(1600)
<000>|<001>This is also a third line|.<002>
|
>>> infile.Line(infile.numLines/3)
'This is the third line.\n'
>>> infile.LineS(infile.numLines/3)
<000>|<001>This is the third line|.<002>
|
>>> firstThird=infile.findStr('third')
>>> infile.Line(firstThird)
'This is the third line.\n'
>>> firstThird=infile.findStr('third', firstThird+1)
>>> infile.Line(firstThird)
'This is also a third line.\n'
>>> infile.token(firstThird, 1)
'This is also a third line'
>>> infile.maxLineLength()
3
>>> infile.gsub('third', 'fourth', firstThird)
1
>>> infile
asTemp (4 lines):
0:<000>|<001>This is the first line|.<002>
|
1:<000>|<001>This is the third line|.<002>
|
2:<000>|<001>This is the fourth line|.<002>
|
3:<000>|<001>This is also a fourth line|.<002>
|
<BLANKLINE>

>>> infile.reconstruct()
>>> infile
asTemp (4 lines):
0:This is the first line.
1:This is the third line.
2:This is the fourth line.
3:This is also a fourth line.
<BLANKLINE>

>>> infile.upcase(0,3)
>>> infile
asTemp (4 lines):
0:THIS IS THE FIRST LINE.
1:THIS IS THE THIRD LINE.
2:THIS IS THE FOURTH LINE.
3:This is also a fourth line.
<BLANKLINE>

>>> infile.gsub('This is also', '#This is also')
1
>>> infile.stripComments('#', 1, 5)
1
>>> infile.tokenize(";[]{}()!@#$%^&*-+_=`~/<>,.:'")
9
>>> infile.addLine(1, 'This line was inserted, no line feed in input string')
>>> infile.addLine(1, 'This line was inserted, line feed in input string\n')
>>> infile.sort()
>>> infile
asTemp (6 lines):
0:1:THIS IS THE FIRST LINE.
2:THIS IS THE FOURTH LINE.
3:THIS IS THE THIRD LINE.
4:This line was inserted, line feed in input string
5:This line was inserted, no line feed in input string
<BLANKLINE>

>>> import os
>>> os.remove('temp')

"""
from StringSet import StringSet as StrSet

# Exceptions
class Error(Exception):
    """Base class for exceptions in this module."""
    pass
class InputError(Error):
    """Exception raised for errors in the input.
    
    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message
    def __str__(self):
        return repr(self.expression)

class TransitionError(Error):
    """Raised when an operation attempts a state transition that's not
    allowed.

    Attributes:
    previous -- state at beginning of transition
    next -- attempted new state
    message -- explanation of why the specific transition is not allowed
    """
    def __init__(self, previous, next, message):
        self.previous = previous
        self.next = next
        self.message = message

class InFile:
    """Load, parse, and manipulate input files.  Supports gzip automatically

    Test of throughput exercising StrSet and InFile:
    time python testInfile.py       time extrag rdg100Large
    real   11    1.7
    user   8.6   1.5
    sys    2.0   0.03
    """
    def __init__(self, srcFile="user input", pname="", maxFileLines=64000, maxLine=1028):
        # Check the inputs
        if __debug__:
            if maxLine < 2:
                raise InputError("", "maxLine must be 2 or more")
            if not srcFile:
                raise InputError("", "no source file specified")
        # Process the inputs
        self.vS = None         # list of StrSet
        self.inFile = srcFile  # the source file
        self.f = None          # filename pointer
        self.lines = None      # list of line strings
        self.numLines = 0      # Number of lines in the file
        self.tokenDelims = None \
            # string of token delimiters for tokenization
        self.fileExtension = None # part of filename after last "."
        self.fileRoot = None   # part of filename before first "."
        self.programName = pname \
                # the name of this object, usually file name
        self.Vars = None \
                # list of variables found in file by loadVars
        self.nVars = 0   \
                # the number of variables found in file by loadVars
        self.reconstructed = 0   \
                # whether tokenized then reconstructed
        self.tokenized = 0      # whether tokenized
        self.maxLineTokens = 0 \
            # stored value of maximum line length, in tokens
        self.counted = 0  # whether maximum line length is counted
        self.loaded = 0   # whether readlines already run on self.f

    def __repr__(self):
        "Print the class"
        cout =  '%(name)s (%(numLines)d lines):\n' \
            %{'name': self.programName, 'numLines': self.numLines}
        if self.tokenized:
            slist = ['%(i)d:%(line)s\n' \
                         %{'i': i, 'line': self.vS[i]} \
                         for i in range(self.numLines)]
        else:
            slist = ['%(i)d:%(line)s' \
                         %{'i': i, 'line': self.lines[i]} \
                         for i in range(self.numLines)]
        cout += "".join(slist)
        return cout

    def Line(self, i):
        "Return the line string demanded but always in-range"
        limitedIndex = max(min(i, len(self.lines)-1), 0)
        return '%(line)s' %{'line': self.lines[ limitedIndex ]}

    def LineS(self, i):
        "Return the tokenized representation of line i, always in range"
        # Check input
        if __debug__:
            if not self.tokenized:
                raise InputError("", \
          "must run InFile.tokenize before look in InFile.LineS")
        limitedIndex = max(min(i, len(self.vS)-1), 0)
        return self.vS[ limitedIndex ]

    def addLine(self, L, Sl):
        "Insert line of string Sl after line L"
        if not Sl[len(Sl)-1]=='\n': Sl += '\n'
        self.lines[(L+1):(L+1)] = [Sl]
        if self.tokenized:
            VS = StrSet(Sl, self.tokenDelims)
            self.vS[(L+1):(L+1)] = [VS]
        self.numLines = len(self.lines)

    def closeFile(self):
        self.f.close()

    def deleteLine(self, L):
        "Delete line and readjust internal arrays"
        del self.vS[L]
        del self.lines[L]
        self.numLines = len(self.lines)

    def downcase(self, startline=0, endline=None):
        "Downcase all the text lines in specified line range"
        if endline: endline = max( min( endline, self.numLines-1 ), 0 )
        startline = max( min( startline, endline ), 0 )
        for i in range(startline, endline):
            self.lines[i] = self.lines[i].lower()
        self.reconstructed = 0

    def findStr(self, target, startLine=0):
        "Number of line containing first 'target' in lines after 'startLine'"
        offset = -1
        for line in self.lines[max(min(startLine, self.numLines), 0):]:
            offset += 1
            if line.count(target): break
        return startLine + offset

    def getLine(self, f):
        "Get a line at a time from the unloaded file and return it's string"
        if __debug__:
            if self.loaded:
                raise InputError("", "do not run load() before getLine()")
        newLine = f.readline()
        if not newLine:
            return ""
        if not self.lines:
            self.lines = [newLine]
        else:
            self.lines += [newLine]
        self.numLines = len(self.lines)
        return newLine

    def gsub(self, target, replace, startline=0, endline=None):
        "Global substitution in lines or StrSets(if tokenized); return total number of replacements"
        if endline:
            endline = max( min( endline, self.numLines ), 0 )
        else:
            endline = self.numLines
        startline = max( min( startline, endline ), 0 )
        count = 0
        if not self.tokenized:
            if not target==replace:
                for i in range(startline, endline):
                    count += self.lines[i].count(target)
                    self.lines[i] = self.lines[i].replace(target, replace)
        else:
            if not target==replace:
                for i in range(startline, endline):
                    count += self.vS[i].gsub(target, replace)
        return count

    def gsubDelims(self, target, replace, startline=0, endline=None):
        "Globally substitute target with replace in the specified range of tokenized file memory; return total number of replacements"
        if __debug__:
            if not self.tokenized:
                raise InputError("", "must be tokenized")
        if endline:
            endline = max( min( endline, self.numLines ), 0 )
        else:
            endline = self.numLines
        count = 0
        if not target==replace:
            for i in range(startline, endline):
                count += self.vS[i].gsubDelims(target, replace)
        return count

    def load(self, quiet=True):
        """Load the file"""
        inFileS = StrSet(self.inFile, "/.");
        if len(inFileS)>2:
            self.fileExtension = inFileS[len(inFileS)-1]
        self.fileRoot = inFileS[1]
        if self.fileExtension=='gz':
            import gzip
            self.f = gzip.open(self.inFile)
        else:
            self.f = open(self.inFile, 'r')
        self.lines = self.f.readlines()
        self.numLines = len(self.lines)
        self.loaded = 1
        if not quiet:
            print 'loaded', self.inFile, 'root=', self.fileRoot, \
                'numLines=', self.numLines, ' extension=', self.fileExtension

    def loadVars(self):
        """Load variable vector data, using text (isnum) as delimiter.
        Useful for reading general input data files
        """
        if __debug__:
            if self.tokenized:
                raise InputError("", "must not be tokenized yet")
        self.tokenize(" =!\t\n\a\b\r\f\v;%<>/,&^?#|$@*():{}\\\'[]\"")
        loadingVar = 0
        # Strip out the data vectors
        locV = []            # local storage of data coordinates
        self.Vars = []
        name = ""
        n = self.numLines
        for i in range(n):
            m = len(self.vS[i])
            for j in range(m):
                token = self.vS[i][j]
                # skip if haven't found a new alphanumeric variable name
                if not loadingVar and not token.isalnum():
                    continue
                if not token.isalnum():
                    locV.append([i,j])
                # flag last token
                lastTok = (n==i+1) and (m==j+1)
                # new data is available, or end
                if token.isalnum() or lastTok:                      
                    # save previous data
                    self.Vars.append([[name] , [len(locV)], [locV]])
                    # Start processing new data
                    loadingVar = 0
                    if not lastTok:     # found a new one
                        self.nVars += 1
                        name = token    # new data vector name
                        loadingVar = 1  # flag to process
                        locV = []       # make room for new data
        return self.nVars

    def maxLineLength(self):
        """Determine length of longest line, in tokens"""
        if self.counted:  #TODO:  warnings in exception class?
            print 'WARNING(InFile):  maxLineLength : already counted.  Returning stored value'
            return self.maxLineTokens
        elif not self.tokenized:  return 1
        else:
            self.counted = 1
            for vS in self.vS:
                self.maxLineTokens = max(self.maxLineTokens, len(vS))
        return self.maxLineTokens

    def reconstruct(self):
        "Reconstruct the tokenized memory back into the lines"
        if __debug__:
            if not self.tokenized:
                raise InputError("", "must be tokenized")
            if self.reconstructed:
                raise InputError("", "reconstructed already")
        for i in range(self.numLines):
            # Dangling initial delimiter
            if self.vS[i].sized and not self.vS[i].size:
                self.lines[i] = self.vS[i].delim(0)
            else:
                self.lines[i] = ""
            # Some tokens exist
            #print 'i=', i, 'vS=', self.vS[i], 'size=', self.vS[i].size, 'sized=', self.vS[i].sized
            #print 'tokens=', self.vS[i].tokens, '\ndelims=', self.vS[i].delims, '\nstr=', self.vS[i].str, '\ndelimiters', self.vS[i].delimiters
            self.lines[i] += self.vS[i].reconstruct()
        self.reconstructed = 1
        self.tokenized = 0

    def shortenDelim(self, L, i):
        "Delete last char of i'th delimiter in tokenized line L"
        if __debug__:
            if not self.tokenized:
                raise InputError("", "must be tokenized")
            if L>=self.numLines:
                raise InputError("", "line number out of range")
        self.vS[L].shortenDelim(i)
        self.reconstructed = 0

    def sort(self):
        """Sort"""
        self.lines.sort()
        self.vS = []
        # whether tokenized then reconstructed
        self.reconstructed = 0 
        self.tokenized = 0    # whether tokenized
        # stored value of maximum line length, in tokens
        self.maxLineTokens = 0
        self.counted = 0   # whether maximum line length is counted
        self.loaded = 0    # whether readlines already run on self.f

    def sout(self):
        "Stream the class"
        if self.tokenized:
            slist = ['%(line)s\n' %{'line': self.vS[i].reconstruct()} for i in range(self.numLines)]
            cout = "".join(slist)
        else:
            slist = ['%(line)s\n' %{'line': self.lines[i]} for i in range(self.numLines)]
            cout = "".join(slist)
        return cout

    def stripBlankLines(self, startline=0, endline=None):
        "Strip lines containing only white, in specified line range; return number of lines remaining"
        # Check input
        if __debug__:
            if self.tokenized:
                raise InputError("", "run before tokenizing")
        if endline:
            endline = max( min( endline, self.numLines ), 0 )
        else:
            endline = self.numLines
        startline = max( min( startline, endline ), 0 )
        numBlankLines = 0
        i = 0
        while i<endline:
            if not len(self.lines[i].strip()):
                self.lines.pop(i)
                numBlankLines += 1
                i = i - 1
                self.numLines -= 1
                endline = max( min( endline, self.numLines ), 0 )
            i += 1
        if self.numLines==0:
            print 'WARNING(InFile):  stripBlankLines : ', self.inFile, 'is empty after stripping white space'
        return numBlankLines

    def stripComments(self, commentDelim, startline=0, endline=None):
        "Strip comments from delimiter to end of line, in specified line range; return number of comments stripped"
        if endline:
            endline = max( min( endline, self.numLines-1 ), 0 )
        startline = max( min( startline, endline ), 0 )
        numComS = 0
        for i in range(self.numLines):
            if self.lines[i].find(commentDelim)>-1:
                numComS += 1
                self.lines[i] = self.lines[i].split(commentDelim)[0]
        return numComS

    def token(self, i, j):
        """Return token at specified location"""
        if 0>i or 0>j:
            return "";
        else:
            return self.LineS(i)[j]

    def tokenize(self, delimiters):
        "Tokenize each line of file into a StringSet.  Return total number of tokens"
        self.vS = [];
        numTokens = 0
        self.tokenDelims = delimiters
        if self.numLines: self.reconstructed = 0
        for i in range(self.numLines):
            self.vS.append(StrSet(self.lines[i], delimiters))
            numTokens += len( self.vS[ len(self.vS)-1 ] )
        self.tokenized = 1
        self.reconstructed = 0
        return numTokens

    def upcase(self, startline=0, endline=None):
        "Upcase all the text lines in specified line range"
        if endline:
            endline = max( min( endline, self.numLines-1 ), 0 )
        else:
            endline = self.numLines
        startline = max( min( startline, endline ), 0 )
        for i in range(startline, endline):
            self.lines[i] = self.lines[i].upper()
        self.reconstructed = 0

if __name__ == '__main__':
    import doctest
    doctest.testmod(verbose=True)
