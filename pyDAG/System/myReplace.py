#!/usr/bin/env python
"""Replace string in file"""


def replace_in_file(s_text, r_text, input_file_name):
    """Replace s_text with r_text in input_file_name"""
    input_file = open(input_file_name)
    output_file = open('.temp', 'w')
    count = 0
    for s in input_file.xreadlines():
        count += s.count(s_text)
        output_file.write(s.replace(s_text, r_text))
    input_file.close()
    output_file.close()
    if count > 0:
        shutil.move('.temp', input_file_name)
    else:
        os.remove('.temp')
    return count


# Testing
def main(args):
    """Replace string in file"""
    usage = "usage: %s search_text replace_text [infile [outfile]]" \
            % os.path.basename(sys.argv[0])

    if len(sys.argv) < 3:
        print usage
    else:
        s_text = sys.argv[1]
        r_text = sys.argv[2]
        input_file = sys.argv[3]
        count = replace_in_file(s_text, r_text, input_file)
        print 'replace:  replaced ', count, ' occurrences'


if __name__ == '__main__':
    import os
    import sys
    import shutil
    sys.exit(main(sys.argv[1:]))
