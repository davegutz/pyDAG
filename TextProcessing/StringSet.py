#!/usr/bin/env python
r"""StringSet:  string tokenizer class

Tests:

>>> import StringSet
>>> SS=StringSet.StringSet

>>> testStrSet = SS("Mary had a little lamb; it's was white as snow.")
>>> otherStrSet = SS("Mary had a little lamb; it's was white as snow.")

Basic attributes:
>>> len(testStrSet)
47
>>> otherStrSet == testStrSet
True
>>> testStrSet.tokenize(",;.'")
>>> len(testStrSet)
5
>>> len(otherStrSet)
47
>>> otherStrSet==testStrSet
False

Replacing:
>>> numRepl = testStrSet.gsub('white', 'black')
>>> print numRepl
1
>>> print testStrSet
<000>|<001>Mary had a little lamb|;<002> it|'<003>s was black as snow|.<004>|
>>> otherStrSet.tokenize(".")
>>> otherStrSet.gsubDelims(".", "!")
1
>>> print otherStrSet
<000>|<001>Mary had a little lamb; it's was white as snow|!<002>|

Token details:
>>> ss =SS('class Error(Exception):\n', ';[]{}()!@#$%^&*-+_=`~/<>,.:\'') 
>>> ss.str
'class Error(Exception):\n'
>>> ss
<000>|<001>class Error|(<002>Exception|):<003>
|
>>> ss.size
4
>>> ss.sized
4
>>> ss.tokens
['', 'class Error', 'Exception', '\n']
>>> ss.delims
['', '(', '):', '']
>>> ss.reconstruct()
'class Error(Exception):\n'
>>> ss =SS('[class Error(Exception):\n', ';[]{}()!@#$%^&*-+_=`~/<>,.:\'') 
>>> ss.str
'[class Error(Exception):\n'
>>> ss
<000>|[<001>class Error|(<002>Exception|):<003>
|
>>> ss.size
4
>>> ss.sized
4
>>> ss.tokens
['', 'class Error', 'Exception', '\n']
>>> ss.delims
['[', '(', '):', '']
>>> ss.reconstruct()
'[class Error(Exception):\n'
>>> ss = SS('./rdg100Small.txt', "./")
>>> ss.str
'./rdg100Small.txt'
>>> ss
<000>|./<001>rdg100Small|.<002>txt|
>>> ss.size
3
>>> ss.sized
3
>>> ss.tokens
['', 'rdg100Small', 'txt']
>>> ss.tokens
['', 'rdg100Small', 'txt']
>>> ss.reconstruct()
'./rdg100Small.txt'
"""

import re

class StringSet:
    """Create string sets from lines for easy file text manipulation"""

    def __eq__(self, other):
        """== special class method"""
        if isinstance(other, StringSet):
            if      other.str == self.str and \
                    other.size == self.size and \
                    other.sized == self.sized and \
                    other.tokenized == self.tokenized and \
                    other.delims == self.delims and \
                    other.tokens == self.tokens:
                result = True
            else:
                result = False
        else:
            result = False
        return result

    def __init__(self, srcStr=None, delimiters=None):
        self.str = srcStr
        self.tokens = []
        self.size = 0
        self.delims = []
        self.sized = 0
        self.tokenized = 0
        self.delimiters = ''
        if delimiters:
            self.delimiters = delimiters
            self.tokenize(delimiters)
            self.tokenized = 1

    def __len__(self):
        """String length if not tokenized, otherwise number tokens."""
        if self.tokenized:
            return self.size
        else:
            return len(self.str)

    def __ne__(self, other):
        """!= special class method"""
        if isinstance(other, StringSet):
            if      other.str != self.str or \
                    other.size != self.size or \
                    other.sized != self.sized or \
                    other.tokenized != self.tokenized or \
                    other.delims != self.delims or \
                    other.tokens != self.tokens:
                result = True
            else:
                result = False
        else:
            result = True
        return result

    def __repr__(self):
        """Print the class"""
        if self.sized:
            if not self.size:
                cout = '<000> %(d0)s' % {'d0': self.delims[0]}
            else:
                cout = ''
            slist = ['<%(i)03d>%(ti)s|%(di)s' \
                         % {'i':i, 'di':self.delims[i],'ti':self.tokens[i]} \
                         for i in range(self.sized)]
            cout = cout.join(slist)
            if self.size and self.sized > self.size:
                cout = cout.join('<%(ss1)03d>%(dss1)s' \
                         % {'ss1':self.sized-1, \
                               'dss1': self.delims[self.sized-1]})
        else:
            slist = ['<%(i)03d>%(ti)s' \
                         % {'i':i, 'ti':self.tokens[i]} \
                         for i in range(self.size)]
            cout = ''.join(slist)
        return cout

    def gsub(self, target, replacement):
        """Global token replace, return number of replacements"""
        changed = 0
        if target != replacement:
            for i in range(self.size):
                changed += self.tokens[i].count(target)
                self.tokens[i] = self.tokens[i].replace(target, \
                                                      replacement)
                changed -= self.tokens[i].count(target)
        return changed

    def gsubDelims(self, target, replacement):
        """Global delimiter replace, return number of replacements"""
        changed = 0
        if target != replacement:
            for i in range(self.sized):
                changed += self.delims[i].count(target)
                self.delims[i] = self.delims[i].replace(target, replacement)
                changed -= self.delims[i].count(target)
        return changed

    def reconstruct(self):
        """Reconstruct the tokenized version and return it"""
        if self.sized:
            if not self.size:
                cout = '%(d0)s'% {'d0': self.delims[0]}
            else:
                cout = ''
            slist = ['%(ti)s%(di)s' \
                         % {'di':self.delims[i], 'ti':self.tokens[i]} \
                         for i in range(self.sized)]
            cout = cout.join(slist)
            if self.size and self.sized > self.size:
                cout = cout.join('%(dlast)s' \
                                % {'dlast': self.delims[self.sized-1]})
        else:
            slist = ['%(ti)s ' % {'ti':self.tokens[i]} \
                         for i in range(self.size)]
            cout = "".join(slist)
        return cout

    def shortenDelim(self, i):
        """Shorten delimiter by one character at end"""
        self.delims[i] = self.delims[i][:len(self.delims[i])-1]

    def token(self, i, verbose=True):
        """Use __getitem__ instead"""
        if verbose:
            print "Deprecated.   Use ''[]'' instead"
        return self.tokens[i]

    def __getitem__(self, i):
        """Return an element"""
        return self.tokens[i]

    def tokenize(self, delimiters, saveDelims=True):
        """Find tokens of self.str separated by one or more delimiters;
        save tokens and delimiters"""
        # Initialize
        self.delimiters = delimiters
        if self.tokenized:
            self.tokens = []
            self.size = 0
            self.delims = []
            self.sized = 0
            self.tokenized = 0
        if not self.str:
            return
        regEx = re.compile("[" + re.escape(delimiters) + "]*")
        self.tokens = regEx.split(self.str)
        self.tokenized = 1
        if saveDelims:
            if self.tokens[0] == '':
                self.delims = []
            else:
                self.delims = ['']
            rawDelims = regEx.findall(self.str)
            for strg in rawDelims:
                if strg:
                    self.delims.append(strg)
            if rawDelims[0] == '':
                self.tokens.insert(0,'')
        self.size = len(self.tokens)
        while len(self.delims) < self.size:
            self.delims.append('')
        self.sized = len(self.delims)

if __name__ == '__main__':
    import doctest
    doctest.testmod(verbose=True)
