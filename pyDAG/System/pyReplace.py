"""Replaces strings in file lists.
Normally call with target and replace strings then file listing.   Optionally
provide a file with file list.

Example:
    pyReplace targetStr sourceStr file

Options:

    -h / --help
        Print this message and exit
    -d / --debug  <e.g. 0>
        Use this verbosity level to debug program
    -l / --list <e.g. "pyReplace.list" a file listing to operate on>
        example:   pyReplace -l file.lst  targetStr sourceStr
    -V, --# import cProfile
        version
        Print version and quit \n"

Tests:

>>> import mySystem as mS
>>> import os
>>> mS.copy('mySystem.dic', 'tests/.temp')

# python pyReplace lslrt lslrt_replaced tests/.temp
>>> main(['lslrt', 'lslrt_replaced', 'tests/.temp'])
1

>>> os.remove('tests/.temp')
"""

"""
Rev		Author		Date	Description
1.0.		DA Gutz		8/31/11	Release
"""

# import cProfile
import getopt
# import time
import sys
import mySystem as mS


# Initialize static variables.
MY_VERSION = 1.0
verbose = 0


# Exceptions
class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class InputError(Error):
    """Exception raised for errors in the input_file.
    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message, use=0):
        Error.__init__(self)
        self.message = message
        self.usage = use

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


# noinspection SpellCheckingInspection
def main(argv):
    """Replace text in files"""
    global verbose

    # Initialize
    list_file = ""
    arg_list = []

    # Options
    options = ""
    remainder = ""
    try:
        options, remainder = getopt.getopt(argv,
                                           'd:hl:V',
                                           ['debug=', 'help', 'list=', 'version'])
    except getopt.GetoptError:
        usage(2, 'getopt error')
    for opt, arg in options:
        if opt in ('-h', '--help'):
            print 'here'
            usage(1)
        elif opt in ('-d', '--debug'):
            verbose = int(arg)
        elif opt in ('-l', '--list'):
            list_file = arg
        elif opt in ('-V', '--version'):
            print 'pyReplace Version ', MY_VERSION, ' DA Gutz 8/31/2011 add file list option'
            exit(0)
        else:
            usage(1, 'uknown')

    if len(remainder) != 3:
        if verbose:
            print 'remainder=', remainder
        usage(1, 'number of string arguments supplied not 2')

    if verbose:
        print 'list_file=', list_file

    if list_file:
        s_text = remainder[0]
        r_text = remainder[1]
        f = open(list_file)
        for line in f:
            arg_list.append(line.strip())
    else:
        s_text = remainder[0]
        r_text = remainder[1]
        arg_list = remainder
        del arg_list[0:2]
        if verbose:
            print 'arg_list=', arg_list

    count = 0
    for file_name in arg_list:
        count_file = mS.replace_in_file(s_text, r_text, file_name)
        count += count_file
        if verbose:
            print 'target=', s_text, ', replacement=', r_text, ', file=', file_name, ', count=', count_file
    print count


if __name__ == '__main__':
    # sys.exit(cProfile.run("main(sys.argv[1:])"))
    sys.exit(main(sys.argv[1:]))
