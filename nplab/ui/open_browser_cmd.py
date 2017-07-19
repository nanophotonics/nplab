# -*- coding: utf-8 -*-
"""
Created on Mon Dec 05 17:41:32 2016

@author: Will

A Python file that allows you to run the databrowser from cmd line on a h5 file
"""

import qtpy
import sys
import nplab.datafile as df
import h5py



file_path = sys.argv[1] #Take the file location from sys.argv list

data_file = h5py.File(file_path, mode = 'r') #Open the file using h5py
data_file = df.DataFile(data_file) #convert the file to nplab.datafile type
data_file.show_gui() #Show data browser
