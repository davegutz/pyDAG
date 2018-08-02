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

names_str = f.readline()
delimiters = ' \t()\n'
reg_ex = re.compile("[" + re.escape(delimiters) + "]*")
names_token = reg_ex.split(names_str)
names_key = names_token[0]
num_names = string.atoi(names_token[1])
name_format = names_token[2]
loc_a = string.find(name_format, 'A')
names_per_line = string.atoi(name_format[:loc_a])
num_name_lines = num_names / names_per_line
if num_names % names_per_line != 0:
    num_name_lines = num_name_lines + 1
names = []
[names.extend([nm for nm in f.readline().split()]) for i in range(num_name_lines)]
print names

frequencies_str = f.readline()
delimiters = ' \t()\n'
reg_ex = re.compile("[" + re.escape(delimiters) + "]*")
frequencies_token = reg_ex.split(frequencies_str)
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

par_str_next = f.readline().split()
data = []
for j in range(num_names):
    data.append([])
    par_str = par_str_next
    data_str = f.readline()
    loc_next = string.find(data_str, '*VALUEB')
    par_str_next = data_str[loc_next:]
    data_str = data_str[:loc_next]
    num_data = len(data_str) / 4
    i_data = []
    for i in range(num_data):
        temp = data_str[4 * i:4 * i + 4]
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
