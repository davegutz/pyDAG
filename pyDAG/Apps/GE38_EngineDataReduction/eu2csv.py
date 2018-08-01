#!/usr/bin/env python
import os
import string
import re
import struct

os.getcwd()
os.listdir('.')
f = open('c005r9951.eu', 'rb')

hdrKey = f.readline()

hdrStr = f.readline()
q1, q2, q3, loc, cell, dateStr, q4, q5, q6 = hdrStr.split()
print q1, q2, q3, loc, cell, dateStr, q4, q5

namesStr = f.readline()
delimiters = ' \t()\n'
regEx = re.compile("[" + re.escape(delimiters) + "]*")
namesTok = regEx.split(namesStr)
namesKey = namesTok[0]
numNames = string.atoi(namesTok[1])
nameFmt = namesTok[2]
locA = string.find(nameFmt, 'A')
namesPerLine = string.atoi(nameFmt[:locA])
numNameLines = numNames / namesPerLine
if numNames % namesPerLine != 0:
    numNameLines = numNameLines + 1
names = []
[names.extend([nm for nm in f.readline().split()]) for i in range(numNameLines)]
print names

frequencies_str = f.readline()
delimiters = ' \t()\n'
regEx = re.compile("[" + re.escape(delimiters) + "]*")
frequencies_token = regEx.split(frequencies_str)
frequenciesKey = frequencies_token[0]
num_frequencies = string.atoi(frequencies_token[1])
frequencies_format = frequencies_token[2]
locF = string.find(frequencies_format, 'F')
frequenciesPerLine = string.atoi(frequencies_format[:locF])
numFreqLines = num_frequencies / frequenciesPerLine
if num_frequencies % frequenciesPerLine != 0:
    numFreqLines = numFreqLines + 1
frequencies = []
[frequencies.extend([string.atof(fs) for fs in f.readline().split()]) for i in range(numFreqLines)]
print frequencies

parStrNext = f.readline().split()
data = []
for j in range(numNames):
    data.append([])
    parStr = parStrNext
    dataStr = f.readline()
    locNext = string.find(dataStr, '*VALUEB')
    parStrNext = dataStr[locNext:]
    dataStr = dataStr[:locNext]
    num_data = len(dataStr) / 4
    i_data = []
    for i in range(num_data):
        temp = dataStr[4 * i:4 * i + 4]
        packed = struct.pack('4c', temp[0], temp[1], temp[2], temp[3])
        data[j].append(struct.unpack('f', packed))

print 'size data=', len(data)
for k in range(len(data)):
    print len(data[k]),
print ''
for j in range(len(names)):
    print names[j], ',',
print ''
for i in range(num_data):
    for j in range(len(names)):
        print data[j][i], ',',
    print ''

f.close()
