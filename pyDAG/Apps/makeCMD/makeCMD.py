#!/usr/bin/env python
# import cProfile
import getopt
import datetime
import sys
import os
import shutil
import glob
import time
import subprocess
from pyDAG import InFile
import fnmatch

"""Makes .cmd PMAT trim files from ingredients in folder such as
09_ET_01.adj and 09_ET_01.tbl.
   - makes engine test trim file from $engSARs files.
   - makes dry rig test trim file from $dryRigSARs files.
   - makes multiple individual trim files from $testSARs files.
Convert .adj and .tbl source files into target .cmd trim files for FADEC load
done using the PDAP software.   Desired target trim files are 'rig',
'engine',  and 'test'.

Normally all the files in a folder are converted depending on
file name.    Therefore the user must organize source .adj and .tbl
files in folders that match the usage.   Alternatively you can list the
desired files in a .shm file to create a 'shop mod' trim.   Files in the .shm
may have any name.  The program still runs as though the files are
organized in the same folder so it will throw errors if files are not
named per convention.

The naming convention for source .adj and .tbl goes
    YY-AS-000.adj/.tbl:    application software change planned.  Included
                           into all rig and engine trims.
    YY-ET-000.adj/.tbl:    engine test only.  Included only in engine trims.
    YY-DR-000.adj/.tbl:    dry rig only.   Included only in rig trims.
    YY-XX-000.adj/.tbl:    test only.  Included only in XX test trims.

Any one of these appearing in a .shm file gets put into the shop
mod trim regardless of name.

Options:

    -h / --help
        Print this message and exit
    -d / --debug  <e.g. 0>
        Use this verbosity level to debug program
    -f / --force
        Force rebuild of all trims
    -p / --program <e.g. "ge38">
    -V, --version
        Print version and quit \n"
    -v, --SW_Version    <e.g. "v0.00">
        Use this software version string
Tests:
>>>makeCMD.py -d 0
"""
"""
Rev        Author        Date    Description
1.3.    DA Gutz        11/7/10    Add shop mod'
1.4        DG Rindner    7/22/11    Update shop mod creation
1.5        DG Rindner    9/28/11    Added recursive inclusion of shopmod lists.
1.6        DG Rindner    11/9/11    Update shopmod creation, added update_as_(adj,tbl) option (currently disabled)
1.7        DG Rindner   9/6/12      Fixed path errors that prevented it from running in windows cygwin installation
"""
MY_VERSION = 1.7

# Initialize static variables.
enable_update_AS_files = 0
verbose = 0
PGM = "ge38"
ENG = "engine"
RIG = "dryrig"
# FML00 = "fmlist72_governors.cmd"
FML00 = "fmlist38_esn003_v2_02.cmd"
USING_FML00 = True
FORCE = False
today = datetime.date.today()
DATE = "%(Y)4i%(M)02i%(D)02i" \
       % {'Y': today.year, 'M': today.month, 'D': today.day}
SW_VER = "0.0"
PERL_OUT = "000.cmd"
VERN = "00"


# Exceptions
class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class InputError(Error):
    """Exception raised for errors in the input.
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


def find_executable(executable, path=None):
    """Try to find 'executable' in the directories listed in 'path' (a
    string listing directories separated by 'os.pathsep'; defaults to
    os.environ['PATH']).  Returns the complete filename or None if not
    found
    """
    if path is None:
        path = os.environ['PATH']
    paths = path.split(os.pathsep)
    external_list = ['']

    if os.name == 'os2':
        (base, ext) = os.path.splitext(executable)
        # executable files on OS/2 can have an arbitrary extension, but
        # .exe is automatically appended if no dot is present in the name
        if not ext:
            executable = executable + ".exe"
    elif sys.platform == 'win32':
        path_external = os.environ['PATHEXT'].lower().split(os.pathsep)
        (base, ext) = os.path.splitext(executable)
        if ext.lower() not in path_external:
            external_list = path_external
        print 'path_external=', path_external, ', base=', base, ', ext=', ext, \
            'external_list=', external_list
    for ext in external_list:
        executable_name = executable + ext
        if os.path.isfile(executable_name):
            return executable_name
        else:
            for p in paths:
                f = os.path.join(p, executable_name)
                if os.path.isfile(f):
                    return f
    else:
        return None


def list_time(path):
    """Directory listing sorted by time, latest last"""
    file_list = []
    for x in os.listdir(path):
        if not os.path.isdir(x) and os.path.isfile(x):
            file_list.append((os.stat(x).st_mtime, x))
    file_list.sort()
    calculated_list = [x[1] for x in file_list]
    return calculated_list


def list_alpha(path):
    """Directory listing sorted alphabetically"""
    file_list = []
    for x in os.listdir(path):
        if not os.path.isdir(x) and os.path.isfile(x):
            file_list.append((os.stat(x).st_mtime, x))
    directory_list_alpha = [x[1] for x in file_list]
    return directory_list_alpha


def replace_str_in_file(s_text, r_text, index_file):
    """Replace string in file"""
    inf = open(index_file)
    out_file = open('.temp', 'w')
    count = 0
    for s in inf.xreadlines():
        count += s.count(s_text)
        out_file.write(s.replace(s_text, r_text))
    inf.close()
    out_file.close()
    shutil.move('.temp', index_file)
    return count


def cat(file1, file2, out_file):
    """Cat two files to destination, return success as 0"""
    input1 = open(file1)
    input2 = open(file2)
    out_file = open(out_file, 'w')
    for s in input1.xreadlines():
        out_file.write(s)
    for s in input2.xreadlines():
        out_file.write(s)
    input1.close()
    input2.close()
    out_file.close()


def copy(file1, out_file):
    """Copy file to , return success as 0"""
    input1 = open(file1)
    out_file = open(out_file, 'w')
    for s in input1.xreadlines():
        out_file.write(s)
    input1.close()
    out_file.close()


def adjust_table_list(location_sars):
    """Make .adj .tbl listing"""
    adj_list = []
    tbl_list = []
    # Alphabetical directory listing, a-z
    directory_list_alpha = list_alpha('.')
    for check_file in directory_list_alpha:
        if check_file.count('.adj'):
            for tsType in location_sars:
                if check_file.count('_%(TS)s_' % {'TS': tsType}):
                    adj_list.append(check_file)
        elif check_file.count('.tbl'):
            for tsType in location_sars:
                if check_file.count('_%(TS)s_' % {'TS': tsType}):
                    tbl_list.append(check_file)
    return adj_list, tbl_list


def make_test(test_sars):
    """Make test SAR trims, one at a time"""
    echoed00 = False
    calculated_list = list_time('.')
    (adj_list, tbl_list) = adjust_table_list(test_sars)
    if adj_list.__len__() | tbl_list.__len__():
        trim_list_test_sars = adj_list + tbl_list
        for i in trim_list_test_sars:
            have_other = False
            other = ""
            root = i.replace('.adj', '').replace('.tbl', '')
            if i.count('.adj'):
                parameter_type = "adj"
                other_type = "tbl"
                if trim_list_test_sars.count(root + '.' + other_type):
                    have_other = 1
                    other = root + '.' + other_type
            else:
                parameter_type = "tbl"
                other_type = "adj"
                if trim_list_test_sars.count(root + '.' + other_type):
                    continue
            if have_other:
                r_out_file = PGM + 'v' + VERN + '_' + root + '_adjtbl_' + DATE + '.cmd'
                # p_out_file = PGM+'v' + VERN + '_' + root + '_adjtbl_'
                # Last occurrence of root will be the latest
                p_out_file = r_out_file
                for check_file in calculated_list:
                    if check_file.count(p_out_file):
                        p_out_file = check_file
                    if verbose > 3:
                        print 'file=', i, 'r_out_file=', r_out_file, \
                            'p_out_file=', p_out_file
            else:
                r_out_file = PGM + 'v' + VERN + '_' + root + '_' + parameter_type + '_' + DATE + '.cmd'
                # p_out_file = PGM + 'v' + VERN + '_' + root + '_' + parameter_type + '_'
                # Last occurrence of root will be the latest
                p_out_file = r_out_file
                for check_file in calculated_list:
                    if check_file.count(p_out_file):
                        p_out_file = check_file
                if verbose > 3:
                    print 'file=', i, 'r_out_file=', r_out_file, \
                        'p_out_file=', p_out_file

            making_new_other = False
            if have_other:
                if calculated_list.count(p_out_file) > 0:
                    if os.stat(other).st_mtime > os.stat(p_out_file).st_mtime:
                        making_new_other = True
                        print other, " changed..."
                else:
                    making_new_other = True

            making_new = False
            if calculated_list.count(p_out_file) > 0:
                if verbose > 3:
                    print 'p_out_file=', p_out_file, 'p_stat=', \
                        os.stat(p_out_file).st_mtime, \
                        'i=', i, 'i_stat=', os.stat(i).st_mtime
                if os.stat(i).st_mtime > os.stat(p_out_file).st_mtime:
                    making_new = True
                    print i, " changed"
            else:
                making_new = True
                print i, " changed"

            if FORCE:
                making_new_other = True
                making_new = True
                if not echoed00:
                    print "Forcing rebuild of all..."
                    echoed00 = True

            # Create the new file
            if (not making_new) & (not making_new_other):
                print p_out_file, " up to date..."
                continue
            else:
                index_file = ""
                # out_file = ""
                sar_2_trim_path = find_path('sar2trim')
                perl_status = subprocess.Popen(['perl', sar_2_trim_path, '-d', '-p', PGM, '-v', VERN, i],
                                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                # perl_status.communicate()[0] = perl_status.stderr.read()
                perl_error = perl_status.stderr.read()
                if not perl_error:
                    target_str = "v%(VE)s" % {'VE': VERN}
                    replace_str = "v%(VE)s_%(RT)s" % {'VE': VERN, 'RT': root}
                    index_file = PERL_OUT.replace(target_str, replace_str).replace('scr',
                                                                                   "_%(TY)s_" % {'TY': parameter_type})
                    replace_str_in_file(PERL_OUT, index_file, PERL_OUT)
                    shutil.move(PERL_OUT, index_file)
                    if USING_FML00:
                        replace_str_in_file("SET VA AS_ADJ_STORE_REQ",
                                            "!SET VA AS_ADJ_STORE_REQ", index_file)
                    if not have_other:
                        print 'made ', index_file
                        time.sleep(1)

            if have_other:  # this must be a .tbl file given sorting done earlier
                perl_command = "sar2trim -d -p %(PG)s -v %(VE)s %(FI)s" \
                        % {'PG': PGM, 'VE': VERN, 'FI': other}
                if verbose > 3:
                    print perl_command
                sar_2_trim_path = find_path('sar2trim')
                print sar_2_trim_path
                perl_status = subprocess.Popen(['perl', sar_2_trim_path, '-d', '-p', PGM, '-v', VERN, i],
                                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                perl_status.communicate()[0] = perl_status.stderr.read()
                if not perl_error:
                    target_str = "v%(VE)s" % {'VE': VERN}
                    replace_str = "v%(VE)s_%(RT)s" % {'VE': VERN, 'RT': root}
                    out_file = PERL_OUT.replace(target_str, replace_str).replace('scr',
                                                                                 "_%(OTY)s_" % {'OTY': other_type})
                    replace_str_in_file(PERL_OUT, out_file, PERL_OUT)
                    shutil.move(PERL_OUT, out_file)
                    if USING_FML00:
                        replace_str_in_file("SET VA AS_ADJ_STORE_REQ",
                                            "!SET VA AS_ADJ_STORE_REQ",
                                            out_file)
                    cat(index_file, out_file, r_out_file)
                    os.remove(index_file)
                    os.remove(out_file)
                    print 'made ', r_out_file
                    time.sleep(1)
        else:
            print "No more test SARs... continuing\n"


def list_shm(shm_file):
    """Recursively list shm file and extract lists"""
    shm_in_file = InFile(shm_file)
    shm_in_file.load()
    shm_in_file.gsub('#include', 'INCLUDE')
    shm_in_file.stripComments('#')
    shm_in_file.stripComments('%')
    shm_in_file.stripComments('!')
    shm_in_file.stripBlankLines()
    shm_in_file.tokenize('. \r\n')
    raw_list = []
    full_list = []
    shm_list = []
    for i in range(shm_in_file.numLines):
        # Added ability to recursively #INCLUDE additional shopmods (.shm) lists
        if shm_in_file.token(i, 1).startswith('INCLUDE'):
            include_shm_name = shm_in_file.token(i, 2) + '.shm'
            shm_list.append(include_shm_name)
            include_shm_file = os.path.join(os.getcwd(), include_shm_name)
            if os.path.isfile(include_shm_file):
                # Recursive call to list_shm
                [recursive_list, recursive_full_list, recursive_shm_list] = list_shm(include_shm_file)
                full_list = full_list + recursive_full_list
                shm_list = shm_list + recursive_shm_list
        #            pdb.set_trace
        else:
            filename = os.path.join(os.getcwd(),
                                    shm_in_file.token(i, 1) + '.' + shm_in_file.token(i, 2))
            if os.path.isfile(filename):
                raw_list.append(filename)
                full_list.append(filename)
            else:
                print("Could not find " + os.path.basename(filename))
    # cull repeats
    clean_list = []
    for i in range(len(raw_list)):
        if not clean_list.__contains__(raw_list[i]):
            clean_list.append(raw_list[i])
    return clean_list, full_list, shm_list


def make_shm_folder(print_out_folder, location_list):
    """Copy files to working folder"""
    print 'processing', os.path.basename(print_out_folder)
    if os.path.isfile('as.adj'):
        shutil.copy('as.adj', os.path.join(print_out_folder, 'as.adj'))
    if os.path.isfile('as.tbl'):
        shutil.copy('as.tbl', os.path.join(print_out_folder, 'as.tbl'))
    adj_list = []
    adj_sar_dict = {}
    tbl_list = []
    tbl_sar_dict = {}
    for check_file in reversed(location_list):
        if check_file.count('.adj'):
            out_file_name = os.path.join(print_out_folder, os.path.basename(check_file))
            out_file = open(out_file_name, 'w')
            adj_in_file = InFile(check_file)
            adj_in_file.load()
            adj_in_file.tokenize(' \n\t')
            for i in range(adj_in_file.numLines):
                if adj_in_file.Line(i).startswith('!') or adj_in_file.Line(i).startswith('#')\
                        or adj_in_file.Line(i).startswith('\n'):
                    out_file.write(adj_in_file.Line(i))
                else:  # if len(adj_in_file.LineS(i)) == 4:
                    name = adj_in_file.token(i, 1)
                    if adj_list.count(name) == 0:
                        adj_list.append(name)
                        adj_sar_dict[name] = os.path.basename(check_file)
                        out_file.write(adj_in_file.Line(i))
                    else:
                        out_file.write(' '.join(['!obsolete: overwritten by', adj_sar_dict[name], adj_in_file.Line(i)]))
            out_file.close()
        elif check_file.count('.tbl'):
            out_file_name = os.path.join(print_out_folder, os.path.basename(check_file))
            out_file = open(out_file_name, 'w')
            tbl_in_file = InFile(check_file)
            tbl_in_file.load()
            tbl_in_file.tokenize(' \n\t\',')
            commenting = False
            for i in range(tbl_in_file.numLines):
                if tbl_in_file.Line(i).startswith('!'):
                    out_file.write(tbl_in_file.Line(i))
                else:
                    if tbl_in_file.Line(i).count('#ADJUSTABLE'):
                        continue
                    if tbl_in_file.Line(i).count('$INPUT'):
                        name = tbl_in_file.token(i, 3)
                        if tbl_list.count(name) == 0:
                            tbl_list.append(name)
                            tbl_sar_dict[name] = os.path.basename(check_file)
                            commenting = False
                            out_file.write(tbl_in_file.Line(i - 1))
                            out_file.write(tbl_in_file.Line(i))
                        else:
                            commenting = True
                            out_file.write(' '.join(['!obsolete:', tbl_in_file.Line(i - 1)]))
                            out_file.write(' '.join(['!obsolete: overwritten by', tbl_sar_dict[name],
                                                     tbl_in_file.Line(i)]))
                    elif commenting:
                        out_file.write(''.join(['!obsolete:', tbl_in_file.Line(i)]))
                    else:
                        out_file.write(tbl_in_file.Line(i))
            out_file.close()
        elif check_file.count('.fml'):
            shutil.copy(check_file, os.path.join(print_out_folder, os.path.basename(check_file)))
        else:
            print os.path.basename(check_file), " not found"


def make_shm(shm_file):
    """Make shop mod from list in file"""
    p_out_file = os.path.basename(shm_file).rpartition('.')[0]
    r_out_file = p_out_file + '.cmd'
    home = os.getcwd()
    print_out_folder = os.path.join(home, p_out_file)
    # load shm file and extract lists
    [location_list, full_list, shm_list] = list_shm(shm_file)

    # make folder to work the files
    recreate_shm = 0
    if os.path.isfile(p_out_file):
        print 'ERROR(makeCMD.py/make_shm): ', home, 'is already a file...quitting'
        exit(1)
    if not os.path.isdir(p_out_file):
        os.mkdir(p_out_file)
        recreate_shm = 1
    else:
        if os.stat(shm_file).st_mtime > os.stat(p_out_file).st_mtime:
            print "".join([p_out_file, ".shm is more recent than ", p_out_file, " folder"])
            recreate_shm = 1
        else:
            for i in location_list:
                # note: only compares time stamps of  SARs explicitly included in this .shm file,
                #      does not check files recursively to determine whether to rebuild
                if os.stat(os.path.basename(i)).st_mtime > os.stat(p_out_file).st_mtime:
                    print os.path.basename(i), " is more recent than ", p_out_file, " folder"
                    recreate_shm = 1

    if recreate_shm or FORCE:
        print "\ncleaning out", os.path.basename(print_out_folder)
        for check_file in glob.iglob(os.path.join(print_out_folder, '*')):
            if not os.path.basename(check_file) == 'CVS':
                try:
                    os.remove(check_file)
                except OSError:
                    shutil.rmtree(check_file, ignore_errors=True)

        local_directory_list = []
        local_name_list = []
        for i in location_list:
            local_directory_list.append(os.path.join(print_out_folder, os.path.basename(i)))
            local_name_list.append(os.path.basename(i))
        # copy all files, including recursive, to working folder and go there
        make_shm_folder(print_out_folder, full_list)
        os.chdir(print_out_folder)
        # Time sorted directory listing, newest last
        calculated_list = list_time('.')

        # Last occurrence of root will be the latest
        p_out_file = r_out_file
        for check_file in calculated_list:
            if check_file.count(p_out_file) and check_file.count('.cmd'):
                p_out_file = check_file
        if verbose > 3:
            print "\n\n", "r_out_file=", r_out_file, "p_out_file=", p_out_file

        # Output file
        out_file = PERL_OUT.replace(PGM, p_out_file).replace('v' + VERN, '')
        out_file = out_file.replace('scr', '_')

        # Generate the file
        new_file, success = make_location_files(local_directory_list, calculated_list, out_file, p_out_file)

        full_directory_list = []
        full_name_list = []
        if not full_list == location_list:
            print 'Recursively included ' + ', '.join(shm_list)
            for i in full_list:
                full_directory_list.append(os.path.join(print_out_folder, os.path.basename(i)))
                full_name_list.append(os.path.basename(i))
            full_out_file = out_file.replace('.cmd', '_full.cmd')
            new_full_file, success_full = make_location_files(full_directory_list, calculated_list, full_out_file,
                                                              p_out_file)
            if success_full:
                print 'Created full trim file to go from baseline software v' + VERN
            if enable_update_AS_files:
                # update_as_files(full_name_list, p_out_file)
                update_as_files(p_out_file)
            delta_list = list(set(full_name_list).difference(set(local_name_list)))
            os.mkdir(os.path.join(print_out_folder, 'backup'))
            for i in delta_list:
                shutil.move(os.path.join(print_out_folder, i), os.path.join(print_out_folder, 'backup', i))
        else:
            if enable_update_AS_files:
                # update_as_files(local_name_list, p_out_file)
                update_as_files(p_out_file)

        new_file_base = os.path.basename(new_file)
        top_file = os.path.join(home, new_file_base)
        if success:
            shutil.copy(new_file, top_file)
        os.chdir(home)
    else:
        print p_out_file, " up to date"


def make_location(location_sars, loc):
    """Make SARs for defined location"""
    r_out_file = PGM + loc + 'v' + VERN + '_' + DATE + '.cmd'
    # p_out_file = PGM + loc + 'v' + VERN + '_'

    # Time sorted directory listing, newest last
    calculated_list = list_time('.')

    # Last occurrence of root will be the latest
    p_out_file = r_out_file
    for check_file in calculated_list:
        if check_file.count(p_out_file):
            p_out_file = check_file
    if verbose > 3:
        print '\n\n', loc, 'r_out_file=', r_out_file, 'p_out_file=', p_out_file

    # .adj and .tbl listings
    (adj_list, tbl_list) = adjust_table_list(location_sars)
    location_list = adj_list
    [location_list.append(i) for i in tbl_list]

    # Output file
    out_file = PERL_OUT.replace(PGM, PGM + loc).replace('scr', '_')

    # Generate the file
    make_location_files(location_list, calculated_list, out_file, p_out_file)


def make_location_files(location_list, calculated_list, out_file, p_out_file):
    """Make SAR out of location_list"""
    global USING_FML00
    echoed00 = False
    making_new = False
    success = False
    for i in location_list:
        if calculated_list.count(p_out_file) > 0:
            if verbose > 3:
                print 'p_out_file=', p_out_file, 'p_stat=', \
                    os.stat(p_out_file).st_mtime, \
                    'i=', i, 'i_stat=', os.stat(i).st_mtime
            if os.stat(i).st_mtime > os.stat(p_out_file).st_mtime:
                making_new = True
                print i, "changed"
        else:
            making_new = True
    if calculated_list.count(FML00) > 0:
        USING_FML00 = True
        if calculated_list.count(p_out_file) > 0:
            if os.stat(FML00).st_mtime > os.stat(p_out_file).st_mtime:
                making_new = True
                print FML00, "changed"
        else:
            making_new = True
    else:
        print FML00, ' does not exist - assuming not needed...'
        USING_FML00 = False
    # Forcing
    if FORCE:
        making_new = True
        if not echoed00:
            print "Forcing rebuild of all..."
            #  echoed00 = True
    # Making new
    if making_new:
        location_list_str = ""
        for i in location_list:
            location_list_str += (i + " ")
        sar_2_trim_path = find_path('sar2trim')
        perl_path = find_path('perl')
        #  print perl_path
        #   print sar_2_trim_path
        #  print os.getcwd()
        #  pdb.set_trace()
        tester = " ".join([perl_path, sar_2_trim_path, '-d', '-p', PGM, '-v', VERN, location_list_str])
        perl_status = subprocess.Popen(tester, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        [output, perl_error] = perl_status.communicate()
        warn_list = fnmatch.filter([perl_error[:]], "Warning")
        err_list = fnmatch.filter([perl_error[:]], "Error")
        #       perl_error=perl_status.stderr.read()
        if err_list:
            print >> sys.stderr, "Child was terminated:\n", err_list
            print "failed", out_file, "continuing...\n"
            success = False
            # print perl_error

        else:  # success
            if warn_list:
                print "Warnings found in ", out_file, "\n"
                print warn_list
                print "continuing...\n"
            if USING_FML00:
                replace_str_in_file("SET VA AS_ADJ_STORE_REQ",
                                    "!SET VA AS_ADJ_STORE_REQ",
                                    PERL_OUT)
            replace_str_in_file(PERL_OUT, out_file, PERL_OUT)
            if USING_FML00:
                cat(PERL_OUT, FML00, out_file)
            else:
                copy(PERL_OUT, out_file)
            os.remove(PERL_OUT)
            print 'made', out_file
            time.sleep(1)
            success = True
    else:
        print p_out_file, ' up to date...'
    return out_file, success
    # End location SARs


# def update_as_files(name_list, p_out_file):
def update_as_files(p_out_file):

    #   pdb.set_trace()
    # Sub function to run the BDB tools to generate updated AS files for given shopmod
    # adj_change_list = fnmatch.filter(name_list, "*.adj")
    # tbl_change_list = fnmatch.filter(name_list, "*.tbl")
    print "Updating as.adj and as.tbl in " + p_out_file + " folder"
    # update_adj_arg = ['update_as_adj_win', '-n', '-f', p_out_file] + adj_change_list[:]
    # status_adj = subprocess.call(update_adj_arg)
    # print "This is current: "+status_adj.poll()
    # except OSError:
    #    print "Unable to update as.adj"
    # try:
    # update_tbl_args = ['update_as_tbl_win', '-n', '-f', p_out_file] + tbl_change_list[:]
    # status_tbl = subprocess.call(update_tbl_args)
    if os.path.exists(p_out_file + "tbl.log"):
        print "Converting as.tbl to tables_def.h for PLM"
        # status_c_tbl_maker = subprocess.Popen(['ctblmkr_GEneric_win', 'as.tbl']).communicate()[0]


def find_path(target_function):
    which_process = subprocess.Popen(["which", target_function], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    [func_path_c, stdout_temp] = which_process.communicate()

    if func_path_c:
        cyg_path_process = subprocess.Popen(["cygpath", "-w", func_path_c.rstrip()], stdout=subprocess.PIPE)
        [func_path_w, stdout_temp] = cyg_path_process.communicate()
    else:
        raise Exception("Unable to find " + target_function + ", please check it exists in $PATH")
    return func_path_w.rstrip()


def main(argv):
    """Convert .adj/.tbl to .cmd"""
    global verbose, PGM, VERN, FORCE, PERL_OUT, SW_VER

    # Default _XX_ correspondence between file names and usage
    eng_sars = ['AS', 'ET']
    dry_rig_sars = ['AS', 'ET', 'DR']
    test_sars = ['XX']

    # Initialize

    # Options
    options = ""
    remainder = ""
    try:
        options, remainder = getopt.getopt(argv,
                                           'd:fhp:Vv:',
                                           ['debug=', 'force', 'help', 'program=', 'version', 'SW_Version=', ])
    except getopt.GetoptError:
        usage(2)
    for opt, arg in options:
        if opt in ('-h', '--help'):
            print usage(1)
        elif opt in ('-d', '--debug'):
            verbose = int(arg)
        elif opt in ('-f', '--force'):
            FORCE = True
        elif opt in ('-p', '--program'):
            PGM = arg
        elif opt in ('-v', '--SW_Version'):
            SW_VER = arg
        elif opt in ('-V', '--version'):
            print 'makeCMD.py Version ', MY_VERSION, ' DG Rindner 10/04/11 Update shop mod function'
            exit(0)
        else:
            print usage(1)
        if remainder:
            print 'ERROR(makeCMD.py):  too many arguments:', remainder
            exit(1)

    # Assign static variables
    VERN = SW_VER.replace('.', '').replace('v', '')
    print 'makeCMD.py:  making PDAP script cmd files for ',
    print 'program=%(PG)s, version=%(SW_VER)s...' \
          % {'PG': PGM, 'SW_VER': SW_VER}
    PERL_OUT = "%(PG)sv%(VE)sscr%(DATE)s.cmd" \
               % {'PG': PGM, 'VE': VERN, 'DATE': DATE}

    # Misc Test XX SARs
    make_test(test_sars)

    # Engine SARs
    make_location(eng_sars, ENG)
    time.sleep(0.5)

    # Dry Rig SARs
    make_location(dry_rig_sars, RIG)
    time.sleep(0.5)

    # Shop Mods
    for shm_file in glob.iglob(os.path.join(os.getcwd(), '*.shm')):
        make_shm(shm_file)
        time.sleep(0.5)

    # Cleanup and quit
    if list_alpha('.').count('.temp'):
        os.remove('.temp')
    print "\nmakeCMD.py:  done."


if __name__ == '__main__':
    # sys.exit(cProfile.run("main(sys.argv[1:])"))
    sys.exit(main(sys.argv[1:]))
