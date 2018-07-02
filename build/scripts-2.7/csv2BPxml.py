#!C:\Python27\python.exe
from pyDAG import InFile
import sys
import cProfile
from pyDAG import StringSet
import getopt
import string
import array
import time
import math
import sys
import os

def main(argv):
    "Process .csv FTS config file to .xml"

# Initialize static variables.
    global verbose
    verbose         = 0
    try:
        options, remainder = getopt.getopt(argv, 'ho:Vv:', ['help', 'output=', 'version', 'verbose=',])
    except getopt.GetoptError:
        usage(2)
    for opt, arg in options:
        if opt in ('-h', '--help'):
            print usage(1)
        elif opt in ('-o', '--output'):
            outputFilename = arg
        elif opt in ('-v', '--verbose'):
            verbose = string.atoi(arg)
        elif opt in ('-V', '--version'):
            version = arg
        else: print usage(1)
        if len(remainder) < 1:
            print "Input a file name for csv"

    # Load input files
    infile = InFile(remainder[0])
    infStrSet = StringSet.StringSet(remainder[0], ".")
    infStrSet.gsub('csv', 'xml')
    infile.load()

    print infile.numLines, 'lines.   Making substitutions...',
    infile.tokenize("\n\r\t,")
    infile.gsubDelims('\n', '')
    infile.gsubDelims(',', '')
    infile.gsub('\"<', '<')
    infile.gsub('\"\"\"', '\"')
    infile.gsub('\"\"', '\"')
    infile.gsub('<NODE ', '\t<NODE ')
    infile.gsub('<HSDL>', '\t\t<HSDL>')
    infile.gsub('<PARAMETERS ', '\t\t\t<PARAMETERS ')
    infile.gsub('<PARAMETER ', '\t\t\t\t<PARAMETER ')
    infile.gsub('</PARAMETERS>', '\t\t\t</PARAMETERS>')
    infile.gsub('</HSDL>', '\t\t</HSDL>')
    infile.gsub('<COMMON>', '\t\t<COMMON>')
    infile.gsub('</COMMON>', '\t\t</COMMON>')
    infile.gsub('<LOCAL>', '\t\t<LOCAL>')
    infile.gsub('</LOCAL>', '\t\t</LOCAL>')
    infile.gsub('</NODE>', '\t</NODE>')
    infile.gsub('>\"', '>')
    print 'done\nWriting output file', infStrSet.reconstruct()
    file(infStrSet.reconstruct(), 'wb').write(infile.sout())
    print 'done'

if __name__=='__main__':
        #sys.exit(cProfile.run("main(sys.argv[1:])"))
    sys.exit(main(sys.argv[1:]))
