# -*- coding: utf-8 -*-
"""
Created on Fri Jun 13 09:01:53 2014

@author: alansanders
"""
from __future__ import print_function

from future import standard_library
standard_library.install_aliases()
from builtins import range
from builtins import object
import numpy as np
from io import StringIO

class IviumDataFile(object):
    def __init__(self, data_file):
        self.params = {}
        self.parse_data(data_file)

    def parse_data(self, data_file):
        with open(data_file, 'r') as f:
            lines = [l.strip() for l in f.readlines()]
            for line in lines:
                if '=' in line:
                    param, value = line.split('=')
                    self.params[param] = value
                if 'primary_data' in line:
                    i = lines.index(line)
                    #for j in range(i, i+6): print j, lines[j]
                    self.data = np.genfromtxt(data_file, skip_header=i+4, skip_footer=2,
                                           usecols=(0,1,2),
                                           names=('x', 'y', 'z'),
                                           #missing_values = 'x',
                                           #filling_values = 0,
                                           autostrip=True, unpack=True,
                                           )

class IviumDataFileStr(object):
    def __init__(self, data_file_str):
        self.params = {}
        self.parse_data(data_file_str)

    def parse_data(self, data_file_str):
        s = StringIO(data_file_str)
        lines = [l.strip() for l in s.readlines()]
        print(len(lines))
        for line in lines:
            if '=' in line:
                param, value = line.split('=')
                self.params[param] = value
            if 'primary_data' in line:
                i = lines.index(line)
                print('starting from line {0:d}/{1:d}'.format(i, len(lines)), lines[i])
                #print lines
                #for j in range(i, i+6): print j, lines[j]
                self.data = np.genfromtxt(StringIO(data_file_str), skip_header=i+4, skip_footer=3,
                                       usecols=(0,1,2),
                                       names=('x', 'y', 'z'),
                                       #missing_values = 'x',
                                       #filling_values = 0,
                                       autostrip=True, unpack=True,
                                       )

class IviumDataSet(object):
    def __init__(self, data_set):
        self.sets = []
        self.parse_set2(data_set)

    def parse_set(self, data_set):
        with open(data_set, 'r') as f:
            data_set = f.read()
        data = [s.strip() for s in data_set.split('QR') if s.strip() != '' and s.strip() != '=']
        print(len(data))
        print(data)

    def parse_set2(self, data_set):
        with open(data_set, 'r') as f:
            lines = f.readlines()
            indices = [i for i in range(len(lines)) if 'QR=QR' in lines[i]]
            print(indices)
            #for i in indices: print lines[i]
            sets = [lines[indices[n]:indices[n+1]] for n in range(len(indices)-1)]
            sets.append(lines[indices[-1]:])
            self.sets = [IviumDataFileStr(''.join(x)) for x in sets[1:]]

if __name__ == '__main__':
    from pylab import *

    data_file = '/Volumes/NPHome/as2180/0 - data/Data/2014/Jul/01/Electrochemistry/140701-ivium/3v.idf'

#    data_file = '/Users/alansanders/Desktop/Electrochemistry/cv3.idf'
    idf = IviumDataFile(data_file)
#    plot(idf.data['x'], idf.data['y'])
    plot(idf.data['x'], idf.data['y'])
    print('method 1 works')
#
#    with open(data_file, 'r') as f:
#        s = f.read()
#    ds = IviumDataFileStr(s)
#    plot(ds.data['voltage'], ds.data['current'])
#    print 'method 2 works'
#
#    data_set = '/Users/alansanders/Desktop/Electrochemistry/to minus3point2-cv.ids'
#    ids = IviumDataSet(data_set)
#    for ds in ids.sets[1:]:
#        plot(ds.data['voltage'], ds.data['current'])
    show()
