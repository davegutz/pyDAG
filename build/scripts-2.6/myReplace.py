#!/usr/bin/python
"""Replace string in file"""

def myReplace(stext, rtext, iFile):
    """Replace stext with rtext in iFile"""
    inputf  = open(iFile)
    outputf = open('.temp', 'w')
    count = 0
    for s in inputf.xreadlines():
        count += s.count(stext)
        outputf.write(s.replace(stext, rtext))
    inputf.close()
    outputf.close()
    if count > 0:
        shutil.move('.temp', iFile)
    else:
    	os.remove('.temp')
    return count


# Testing
def main(args):
    """Replace string in file"""
    usage = "usage: %s search_text replace_text [infile [outfile]]" \
        %         os.path.basename(sys.argv[0])

    if len(sys.argv) < 3:
        print usage
    else:
        stext = sys.argv[1]
        rtext = sys.argv[2]
        inputf = sys.argv[3]
        count = myReplace(stext, rtext, inputf)
        print 'replace:  replaced ', count, ' occurrences'
    
if __name__ == '__main__':
    import os, sys, shutil
    sys.exit(main(sys.argv[1:]))
