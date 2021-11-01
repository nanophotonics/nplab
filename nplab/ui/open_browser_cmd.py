# -*- coding: utf-8 -*-
"""
Created on Mon Dec 05 17:41:32 2016

@author: Will

A Python file that allows you to run the databrowser from cmd line on a h5 file
"""

import sys

import h5py

import nplab.datafile as df

file_path = sys.argv[1] #Take the file location from sys.argv list

data_file = df.DataFile(file_path, mode = 'r')
data_file.show_gui() #Show data browser
