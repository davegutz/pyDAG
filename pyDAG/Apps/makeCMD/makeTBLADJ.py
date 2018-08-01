#!/usr/bin/env python
import os
import fnmatch
import subprocess
from fnmatch import filter
import pdb
import getopt
from optparse import OptionParser
import sys

# from string import Template
# 01-Sep-2011	DG Rindner	V1.0 Converted makeTBLADJ shell wrapper to python for improved performance
#         gmcTemplate = Template(gmcData)    newfile = gmcTemplate.substitute(
#                           inputFileName    = dataFile,
#                           outputFileName   = psFileName,
#                           SHP_Calculations = calcs,
#                           titleLine = '"' + currentTest['titleline'] + '"')

map_list = []
ins_list = []
map_dir = []
ins_dir = []
ls_dir = os.listdir(".")
map_dir = filter(ls_dir, "*_map.inp")
ins_dir = filter(ls_dir, "*_ins.inp")

usage = '''usage: %prog [-f][-h]
       Wrapper to create .adj and .tbl files from NPSS format files
       using map2tbl and ins2adj scripts. Input files of type:
       09_ET_001_ins.inp and 09_ET_001_map.inp
       Converts all npss files in current directory where tbl/adj files 
       do not exist or map.inp, ins.inp files are more recent'''
parser = OptionParser(usage=usage)
parser.add_option('-f', '--force', action='store_true',
                  default=False, dest='force',
                  help='Force reconvert of all files')

(options, args) = parser.parse_args()
force = options.force
if not map_dir:
    print "No map.inp files found in current directory"
else:
    if force:
        map_list = map_dir
    else:
        for mapX in map_dir:
            tblX = (mapX.replace('-', '_')).replace('_map.inp', '.tbl')
            try:
                tbl_mtime = os.stat(tblX).st_mtime
            except OSError:
                tbl_mtime = 0
            if os.stat(mapX).st_mtime > tbl_mtime:
                map_list.append(mapX)
    if map_list:
        print("Converting following _map.inp files: ")
        print(", ".join(map_list))
        map2tblArgs = map_list[:]
        map2tblArgs.insert(0, 'as.tbl')
        map2tblArgs.insert(0, 'map2tbl')
        p1 = subprocess.Popen(map2tblArgs, stdout=subprocess.PIPE).communicate()[0]
        for mapI in map_list:
            tblI = (mapI.replace('-', '_')).replace('_map.inp', '.tbl')
            try:
                tblI_mtime = os.stat(tblI).st_mtime
                if tblI_mtime > os.stat(mapI).st_mtime:
                    print tblI + ": conversion success"
                else:
                    print tblI + ": conversion failed, check error messages"
            except OSError:
                print tblI + ": not found, check error messages"
    else:
        print "All map.inp files up to date, use force option to remake all"

if not ins_dir:
    print "No ins.inp files found in current directory"
else:
    if force:
        ins_list = ins_dir
    else:
        for insX in ins_dir:
            adjX = (insX.replace('-', '_')).replace('_ins.inp', '.adj')
            try:
                adj_mtime = os.stat(adjX).st_mtime
            except OSError:
                adj_mtime = 0
            if os.stat(insX).st_mtime > adj_mtime:
                ins_list.append(insX)

    if ins_list:
        print("Converting following _ins.inp files: ")
        print(", ".join(ins_list))
        ins2adjArgs = ins_list[:]
        ins2adjArgs.insert(0, 'as.adj')
        ins2adjArgs.insert(0, 'ins2adj')
        p2 = subprocess.Popen(ins2adjArgs, stdout=subprocess.PIPE).communicate()[0]
        for insI in ins_list:
            adjI = (insI.replace('-', '_')).replace('_ins.inp', '.adj')
            try:
                adjI_mtime = os.stat(adjI).st_mtime
                if adjI_mtime > os.stat(insI).st_mtime:
                    print adjI + ": conversion success"
                else:
                    print adjI + ": conversion failed, check error messages"
            except OSError:
                print adjI + ": not found, check error messages"
    else:
        print "All ins.inp files up to date, use force option to remake all"
