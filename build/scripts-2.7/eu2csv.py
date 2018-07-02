#!C:\Python27\python.exe
import os
import string
import re
import struct
import array

#os.chdir('/home/davegutz/Desktop')
os.getcwd()
os.listdir('.')
f=open('c005r9951.eu', 'rb')

hdrKey	= f.readline()

hdrStr	= f.readline()
q1, q2, q3, loc, cell, dateStr, q4, q5, q6 = hdrStr.split()
print q1,q2,q3,loc,cell,dateStr,q4,q5

namesStr	= f.readline()
delimiters	=' \t()\n'
regEx 		= re.compile("[" + re.escape(delimiters) + "]*")
namesTok	= regEx.split(namesStr)
namesKey	= namesTok[0]
numNames	= string.atoi(namesTok[1])
nameFmt 	= namesTok[2]
locA 		= string.find(nameFmt, 'A')
namesPerLine 	= string.atoi(nameFmt[:locA])
numNameLines 	= numNames/namesPerLine
if numNames%namesPerLine != 0:
	numNameLines = numNameLines+1
names	= []
[names.extend([nm for nm in f.readline().split()]) for i in range(numNameLines)]
print names

freqsStr	= f.readline()
delimiters=' \t()\n'
regEx 	= re.compile("[" + re.escape(delimiters) + "]*")
freqsTok	= regEx.split(freqsStr)
freqsKey	= freqsTok[0]
numfreqs	= string.atoi(freqsTok[1])
freqFmt 	= freqsTok[2]
locF 	= string.find(freqFmt, 'F')
freqsPerLine 	= string.atoi(freqFmt[:locF])
numFreqLines 	= numfreqs/freqsPerLine
if numfreqs%freqsPerLine != 0:
	numFreqLines = numFreqLines+1
freqs	= []
[freqs.extend([string.atof(fs) for fs in f.readline().split()]) for i in range(numFreqLines)]
print freqs

parStrNext	= f.readline().split()
data 	= []
for j in range(numNames):
	data.append([])
	parStr 		= parStrNext
	dataStr 	= f.readline()
	locNext		= string.find(dataStr, '*VALUEB')
	parStrNext 	= dataStr[locNext:]
	dataStr 	= dataStr[:locNext]
	numData		= len(dataStr)/4
	#len(dataStr)%4 == 0
	idata = []
	for i in range(numData):
		temp	= dataStr[4*i:4*i+4]
		packed	= struct.pack('4c', temp[0], temp[1], temp[2], temp[3])
		#idata.append(struct.unpack('f', packed))
		data[j].append(struct.unpack('f', packed))
	#data.append(idata)

print 'size data=',len(data)
for k in range(len(data)):
	print len(data[k]),
print ''
for j in range(len(names)):
	print names[j],',',
print ''
#cout	=  '%(name)-12s %(type)2d %(num)4d' %{'name': self.name, 'type': self.curveType, 'num': self.num}
for i in range(numData):
	for j in range(len(names)):
		print data[j][i],',',
		#print '%(val)13.8g,' %{'val': data[j][i]}
	print ''

#		left16, right16 = struct.unpack('hh', packed)
#		all32 = struct.unpack('i', packed)
#		float32 = struct.unpack('f', packed)
#		print 'packed string:', repr(packed), ', as two 16-bit integers:', left16, right16,
#		print ',  as a single 32-bit integer', all32[0], ', as a 32-bit float', float32[0]
#		print ''
f.close()

