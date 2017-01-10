# -*- coding: utf-8 -*-
"""
Created on Fri Dec 23 14:29:47 2016

@author: Will
"""

import fileinput
import sys
import os
import fnmatch
import re


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
        
        
    file_locations = [os.path.join(dirpath, f) #Create a list of file paths from the top level path
    for dirpath, dirnames, files in os.walk(path)
        for f in fnmatch.filter(files, '*.py')]

    
    
    for filename in file_locations:
        found_bad_file = False
        for avoid_file in avoid_files: # skip requested files
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
            if ('import ' in line) and (('QtCore' in line) or ('QtGui' in line) or ('uic' in line)):
                if '*' in line:
                    nplab_import_line = line.replace('PyQt4','nplab.utils.gui')
                if ('QtWidgets' not in line) and ('QtGui' in line):
                    nplab_import_line = 'from nplab.utils.gui import QtWidgets, '
                else:
                    nplab_import_line = 'from nplab.utils.gui import '                    
                for attribute in dir(nplab.utils.gui): 
                    if attribute in line.replace(',',' ').split('\n')[0].split(' '):               
                        nplab_import_line = nplab_import_line +attribute+', '
                if nplab_import_line == 'from nplab.utils.gui import ':
                    sys.stdout.write(line) 
                    continue
                else:
                    nplab_import_line = nplab_import_line[:-2] + '\n'
                    sys.stdout.write(line.split('import')[0].split('from')[0]+nplab_import_line) # added line split on import and from to correct for white space for indented imports
                    continue
            for command in line.split(' '):
                if 'QtGui.' in command:
                    func = re.search(r"QtGui\.([0-9a-zA-Z_]+)", command).group(1)
                    if hasattr(QtGui,func):
                        continue
                    else:
                        if hasattr(QtWidgets,func):
                            line = line.replace("QtGui", "QtWidgets")
                        else:
                            continue

                if 'QtCore.' in command:
                    
                    try:
                        func = re.search(r"QtCore\.([0-9a-zA-Z_]+)", command).group(1)
                    except IndexError: 
                        continue
                    if func == 'pyqtSignal':
                        line = line.replace('pyqtSignal','Signal')
                        continue
                            
            sys.stdout.write(line)
            
        fileinput.close()