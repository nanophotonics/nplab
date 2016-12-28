# -*- coding: utf-8 -*-
"""
Created on Fri Dec 23 14:29:47 2016

@author: Will
"""

import fileinput
import sys
import os
import fnmatch


from qtpy import QtGui,QtWidgets

import nplab.utils.gui




def Convert_Pyqt_to_qtpy(path,avoid_files = None):
    '''A function for converting pyqt based python scripts to use qtpy 
    ( a wrapper that allows any qt version to be used)
    
    Be very careful when using this functions, Always Create backups!!!!!
    
    N.B. The fileinput modulue forces the print function to write to file (Very annoying), so do not use any print statements  
    '''
    
    if avoid_files == None:
        avoid_files = ['PyQtToQtpy.py','utils\\gui.py']
        
        
    file_locations = [os.path.join(dirpath, f)
    for dirpath, dirnames, files in os.walk(path)
        for f in fnmatch.filter(files, '*.py')]

    
    
    for filename in file_locations:
        found_bad_file = False
        for avoid_file in avoid_files:
            if avoid_file in filename:
                found_bad_file = True
                continue
        if found_bad_file == True:
            continue
        i=0
        for line in fileinput.input(filename):
            i+=1
        if i == 1:
            f = open(filename,mode = 'r')
            text = f.read()
            f.close()
            text = text.replace('\r','\n')
            f = open(filename,mode='w')
            f.write(text)
            f.close()
                
        for line in fileinput.input(filename, inplace=True):
            if ('import' in line) and ('QtGui' in line):
                if 'QtWidgets' in line:
                    nplab_import_line = 'from nplab.utils.gui import '
                else:
                    nplab_import_line = 'from nplab.utils.gui import QtWidgets, '
                for attribute in dir(nplab.utils.gui): 
                    if attribute in line.replace(',',' ').split('\n')[0].split(' '):               
                        nplab_import_line = nplab_import_line +attribute+', '
                        
                nplab_import_line = nplab_import_line[:-2] + '\n'
                sys.stdout.write(line.split('import')[0].split('from')[0]+nplab_import_line) # added line split on import and from to correct for white space for indented imports
                continue
            for command in line.split(' '):
                if 'QtGui' in command:
                    
                    if len(command.split('.'))>1:
                        func = command.split('QtGui.')[1].split(' ')[0].split(',')[0].split(')')[0].split('(')[0]
                    else:
                        continue
                    if hasattr(QtGui,func):
                        continue
                    else:
                        if hasattr(QtWidgets,func):
                            line = line.replace("QtGui", "QtWidgets")
                        else:
                            continue
                      #      print func,'Could not be found in qtpy. From file ',filename
                       #     print func
            sys.stdout.write(line)
            
        fileinput.close()