#!/usr/bin/env python
"""Move Google Photos Takeout data into target folder, checking to make sure no overwrite
    -h / --help
        Print this message and exit
    -d / --debug  <e.g. 0>
        Use this verbosity level to debug program
    -i / --input
        Use this source folder
    -o / --output
        Use this destination folder
    -r / --reversing
        Reverse input folder date location
    -t / --testing
        Testing without writing
    -V, --version
        Print version and quit \n"

Run for 2016-2018 with folders names yyyy-
  saveGooglePhotosTakeout.py -i "C:\Users\Dave\Downloads\takeout-20180907T151536Z\Takeout\Google Photos" \
  -o "D:\Pictures\Saved Pictures\KPGUTZ_2016" -d1

Run for r2015 with folder named -yyyy, first to extract from folders in output
  saveGooglePhotosTakeout.py -i "D:\Pictures\Saved Pictures\KPGUTZ_2015" \
  -o "D:\Pictures\Saved Pictures\KPGUTZ_2015" -d1 -r
then
  saveGooglePhotosTakeout.py -i "C:\Users\Dave\Downloads\takeout-20180907T151536Z\Takeout\Google Photos" \
  -o "D:\Pictures\Saved Pictures\KPGUTZ_2015" -d1

Tests:
"""
# import cProfile
import getopt
import sys
# import pyexif
import os
import shutil


def usage(msg=''):
    """Usage description"""
    code = sys.stderr
    print(code, __doc__)
    if msg:
        print(code, msg)
    sys.exit(code)


def touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)


def main(argv):
    """desc here"""

    # Initialize static variables.
    global verbose
    verbose = 1
    testing = False
    reversing = False

    # Initialize
    folder_in = ''
    folder_out = ''

    # Options
    options = ""
    try:
        options, remainder = getopt.getopt(argv, 'd:hi:o:rtV:', ['debug=', 'help', 'input=', 'output=', 'reversing',
                                                                'testing', 'version='])
    except getopt.GetoptError:
        usage('ERR')
    for opt, arg in options:
        if opt in ('-h', '--help'):
            print(usage('help'))
        elif opt in ('-d', '--debug'):
            verbose = int(arg)
        elif opt in ('-t', '--testing'):
            testing = True
        elif opt in ('-r', '--reversing'):
            reversing = True
        elif opt in ('-V', '--version'):
            print('saveGooglePhotosTakeout Version 1.0.  DA Gutz 9/8/2018')
            exit(0)
        elif opt in ('-i', '--input'):
            folder_in = arg
        elif opt in ('-o', '--output'):
            folder_out = arg
        else:
            print(usage('OK'))

    # Check inputs
    print("input=", folder_in, "\noutput=", folder_out)

    # Get information about output:  only input files of same date will be copied
    out_date = folder_out[-4:]
    o_files = os.listdir(folder_out)
    print o_files
    for o_file in o_files:
        file_path = folder_out + "\\" + o_file
        statinfo = os.stat(file_path)
        if verbose > 2:
            print "ofile=", file_path, "size=", statinfo.st_size, "date=", out_date
            print(statinfo)

    # Process input folders
    folders_in = os.listdir(folder_in)
    for folder in folders_in:
        if reversing:
            in_date = folder[-4:]
        else:
            in_date = folder[:4]
        if in_date != out_date:
            continue
        i_files = os.listdir(folder_in + "\\" + folder)
        if verbose > 1:
            print "i_files=", i_files
        for i_file in i_files:
            if i_file[-4:] == 'json' or i_file[-3:] == 'ini' or i_file[-2:] == 'db':
                continue
            i_file_path = folder_in + "\\" + folder + "\\" + i_file
            statinfo = os.stat(i_file_path)
            if verbose > 2:
                print "ifile=", i_file_path, "size=", statinfo.st_size, "date=", in_date
            tack = 0
            counter = 0
            while o_files.count(i_file) and counter < 5:
                counter += 1
                if verbose > 1:
                    print "exists=", i_file, "counter=", counter, "count=", o_files.count(i_file)
                o_file_path = folder_out + "\\" + i_file
                if testing:
                    o_statinfo = statinfo
                else:
                    o_statinfo = os.stat(o_file_path)
                if not testing and statinfo.st_size == o_statinfo.st_size:
                    if verbose > 1:
                        print "skipping ", i_file
                    break
                else:
                    tack += 1
                    i_file, found, ext = i_file.partition(".")
                    if found:
                        i_file += "_" + str(tack) + "." + ext
                        if verbose > 0:
                            if testing:
                                print "testing:  may need to append=", i_file, "size=",\
                                    statinfo.st_size, "date=", in_date
                            else:
                                print "appending=", i_file, "size=", statinfo.st_size, "date=", in_date
                    else:
                        print "error(saveGooglePhotosTakeout.py):  file doesn't have a '.' in it"
            # Copy the file
            o_file_path = folder_out + "\\" + i_file
            if verbose > 1:
                print "source=", i_file_path, "----->", o_file_path
            if not testing:
                # touch(o_file_path)
                shutil.copy(i_file_path, o_file_path)
            o_files.append(i_file)


if __name__ == '__main__':
    # sys.exit(cProfile.run("main(sys.argv[1:])"))
    sys.exit(main(sys.argv[1:]))
