#!C:\Python27\python.exe
import os
import fnmatch
import subprocess
from fnmatch import filter
import pdb
import getopt
from optparse import OptionParser
import sys
#from string import Template
# 01-Sep-2011	DG Rindner	V1.0 Converted makeTBLADJ shell wrapper to python for improved performance
#         gmcTemplate = Template(gmcData)    newfile = gmcTemplate.substitute(
#                           inputFileName    = dataFile,
#                           outputFileName   = psFileName,
#                           SHP_Calculations = calcs,
#                           titleLine = '"' + currentTest['titleline'] + '"')

mapList = []
insList = []
mapdir=[]
insdir=[]
lsdir = os.listdir(".")
mapdir = filter(lsdir, "*_map.inp")
insdir = filter(lsdir, "*_ins.inp")

usage ='''usage: %prog [-f][-h]
       Wrapper to create .adj and .tbl files from npss format files
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
if not mapdir:
    print "No map.inp files found in current directory"
else:    
    if force:
        mapList = mapdir
    else:
        for mapX in mapdir:
            tblX = (mapX.replace('-','_')).replace('_map.inp','.tbl')
            try:
                tbl_mtime=os.stat(tblX).st_mtime
            except OSError:
                tbl_mtime=0
            if os.stat(mapX).st_mtime > tbl_mtime:
                 mapList.append(mapX)
    if mapList:
        print("Converting following _map.inp files: ")
        print(", ".join(mapList))
        map2tblArgs=mapList[:]
        map2tblArgs.insert(0,'as.tbl')
        map2tblArgs.insert(0,'map2tbl')
        p1 = subprocess.Popen(map2tblArgs, stdout=subprocess.PIPE).communicate()[0]
        for mapI in mapList:
            tblI = (mapI.replace('-','_')).replace('_map.inp','.tbl')
            try:
                tblI_mtime=os.stat(tblI).st_mtime
                if tblI_mtime > os.stat(mapI).st_mtime:
                    print tblI+": conversion success"
                else:
                    print tblI+": conversion failed, check error messages"
            except OSError:
                print tblI+": not found, check error messages"
    else:
         print "All map.inp files up to date, use force option to remake all"

if not insdir:
    print "No ins.inp files found in current directory"
else:  
    if force:
        insList = insdir
    else:
        for insX in insdir:
            adjX = (insX.replace('-','_')).replace('_ins.inp','.adj')
            try:
                adj_mtime=os.stat(adjX).st_mtime
            except OSError:
                adj_mtime=0
            if os.stat(insX).st_mtime > adj_mtime:
                insList.append(insX)

    if insList:
        print("Converting following _ins.inp files: ")
        print(", ".join(insList))
        ins2adjArgs=insList[:]
        ins2adjArgs.insert(0,'as.adj')
        ins2adjArgs.insert(0,'ins2adj')
        p2 = subprocess.Popen(ins2adjArgs, stdout=subprocess.PIPE).communicate()[0] 
        for insI in insList:
            adjI = (insI.replace('-','_')).replace('_ins.inp','.adj')
            try:
                adjI_mtime=os.stat(adjI).st_mtime
                if adjI_mtime > os.stat(insI).st_mtime:
                    print adjI+": conversion success"
                else:
                    print adjI+": conversion failed, check error messages"
            except OSError:
                print adjI+": not found, check error messages"        
    else:
         print "All ins.inp files up to date, use force option to remake all"
    