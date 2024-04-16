# -*- coding: utf-8 -*-
"""
Created on Fri Nov  3 17:02:07 2023

@author: smrs3, il322
"""

import numpy as np
from nplab import datafile as df
from nplab.utils.array_with_attrs import ArrayWithAttrs
from nplab.instrument import Instrument
import ctypes
import glob
import os.path
import pandas as pd
import time
import pyvium
from pyvium import Pyvium
from pyvium.pyvium_verifiers import PyviumVerifiers



class Ivium(Instrument, Pyvium):
    
    
    '''
    Class handling Ivium Potentiostat
    Uses pyvium library (pip install pyvium -> from pyvium import Pyvium as iv)
    
                
    Notes/Improvements:
        
        Create GUI & GUI class
        
        run_method functions:
            
            Parameters must be set in function arguments:
                Parameters set in IviumSoft will not be saved to .h5 metadata
                No way to read updated parameters set in IviumSoft
    
            Does not check that parameter inputs are valid:
                If invalid, will run method on default parameters from method_file_path without warning!
    
            Current system requires hard-coding of individual method parameters:
                - Have to hard code any methods you want to set
                - Have to hard code valid options for dropdown parameters
    
            Further advanced method parameters can be added (AutoCR, PreRanging, etc.)
    '''


    def __init__(self):
        
        Instrument.__init__(self)
        
        
        # Open Ivium dll & connect device
        
        self.open_driver()
        self.connect_device()


        # Check Ivium status
        
        self.status = self.get_device_status()
        assert self.status[0] == 1, 'Check Ivium status'
        print('Ivium connected!')

        
        # Create h5 datafile if none
        
        self.data_file = df.current()
        
    
    def save(self, name, data):
        
        '''
        Function to save Ivium data to h5 file 
        '''
        
        if self.data_file is None:
            self.data_file = df.current()
    
        ## Get current group or make 'Potentiostat' group
        if df._use_current_group == True and df._current_group is not None:
            group = df._current_group
        elif 'Potentiostat' in list(self.data_file.keys()):
            group = self.data_file['Potentiostat']
        else:
            group = self.data_file.create_group('Potentiostat')

        ## Save to group
        group.create_dataset(name = name, data = data)
    
    
    def run_cv(self, 
               title : str = 'CV_%d',
               mode : str = 'Standard',
               e_start : float = 0,
               vertex_1 : float = 1.0,
               vertex_2 : float = -1.0,
               e_step : float = 0.1,
               n_scans : int = 1,
               scanrate : float = 1,
               current_range : str = '1nA',
               method_file_path : str = r"C:\Users\HERA\Documents\GitHub\nplab\nplab\instrument\potentiostat\CV_Standard.imf",
               save : bool = True):
        
        
        '''
        Function for setting CV parameters, running CV, and returning data w/ attributes
        
        
        Parameters:
            
            self (Ivium class)
            title (str = 'CV_%d')
            mode (str = 'Standard') CV mode. Dropdown option: must be 'Standard' or 'HiSpeed'
            e_start (float = 0): Starting potential in V
            vertex_1 (float = 1.0): Vertex 1 potential in V
            vertex_2 (float = -1.0): Vertex 2 potential in V
            e_step (float = 0.1): Potential step size in V
            n_scans (int = 1): Number of CV scans
            scanrate (float = 0.01): CV scan rate in V/s
            current_range (str = '1nA'): Current dynamic range. Dropdown option: must be in valid_current_range (see below)
            method_file_path (str): Method file path. Must be CV .imf file
            save (bool = True): If true, saves data automatically to h5 file    
        '''
        
        
        # Load CV method
        
        self.load_method(method_file_path)
        
        
        # Assert dropdown parameters are valid
        
        ## Mode
        if str(mode) != 'Standard' and str(mode) != 'HiSpeed':
            raise ValueError('\nInvalid CV mode. CV mode must be "Standard" or "HiSpeed"')
            return
        
        ## Current range
        valid_current_range = ['1A', '100mA', '10mA', '1mA', '100uA', '10uA', '1uA', '100nA', '10nA', '1nA', '100pA']
        if str(current_range) not in valid_current_range:
            raise ValueError('\nInvalid current range. Current range must be:\n' + str(valid_current_range))
            return
        
        
        # Set all parameters
        
        self.set_method_parameter('Title', str(title))
        self.set_method_parameter('Mode', str(mode))
        self.set_method_parameter('E start', str(e_start))      
        self.set_method_parameter('Vertex 1', str(vertex_1))
        self.set_method_parameter('Vertex 2', str(vertex_2))
        self.set_method_parameter('E step', str(e_step))
        self.set_method_parameter('N scans', str(n_scans)) 
        self.set_method_parameter('Scanrate', str(scanrate))
        self.set_method_parameter('Current range', str(current_range))
        

        # Run method
        
        ## Start method
        start_time = time.time()
        self.start_method()
        
        ## Wait for method to finish
        while self.get_device_status()[0] == 2:
            time.sleep(0.1)
        stop_time = time.time()
        print('Ivium method finished!')
        
        
        # Return data

        ## Get data
        total_points = self.get_available_data_points_number()
        data_t = []
        data_V = []
        data_I = []
        for scan_index in range(1, n_scans+1):
            for point_index in range(1,total_points+1):
                V_x,I,V = self.get_data_point_from_scan(point_index, scan_index)
                t = point_index * (e_step/scanrate)
                data_t.append(t)
                data_V.append(V)
                data_I.append(I)
        data_t = np.array(data_t)
        data_V = np.array(data_V)
        data_I = np.array(data_I)
        data_VI = np.array([data_V, data_I])
        
        ## Get attributes
        data_attrs={'Potential (V)' : data_V,
                    'Time (s)' : data_t,
                    'Title' : str(title),
                    'Mode' : str(mode),
                    'E start (V)' : e_start,
                    'Vertex 1 (V)' : vertex_1,
                    'Verttex 2 (V)' : vertex_2,
                    'E step (V)' : e_step,
                    'N scans' : n_scans,
                    'Scanrate (V/s)' : scanrate,
                    'Current range' : str(current_range),
                    'start_time' : start_time,
                    'stop_time' : stop_time}
        
        ## Return/save data
        if save == True:
            self.save(name = title, data = ArrayWithAttrs(data_VI, data_attrs))
        return ArrayWithAttrs(data_VI, data_attrs)
        
        
    def run_ca(self, 
               title : str = 'CA_%d',
               mode : str = 'Standard',
               levels_v : list = [0, 0.5, 1.0],
               levels_t : list = [1, 1, 1],
               cycles : int = 5,
               interval_time : float = 0.1,
               current_range : str = '1nA',
               method_file_path : str = r"C:\Users\HERA\Documents\GitHub\nplab\nplab\instrument\potentiostat\CA_Standard.imf",
               save : bool = True):
        
        
        '''
        Function for setting ChronoAmperometry parameters, running CA, and returning/saving data w/ metadata
        
        
        Parameters:
            
            self (Ivium class)
            title (str = 'CA_%d')
            mode (str = 'Standard') CA mode. Dropdown option: must be 'Standard' or 'HiSpeed'
            levels_v (list = [0, 0.5, 1.0]): CA level potentials in V
            levels_t (list = [1, 1, 1]): CA level times in s
            cycles (int = 5): Number of CA cycles
            interval_time (float = 0.1): CA data point step size in s
            current_range (str = '1nA'): Current dynamic range. Dropdown option: must be in valid_current_range (see below)
            method_file_path (str): Method file path. Must be CA .imf file     
            save (bool = True):             
        '''
        
        
        # Load CA method
        
        self.load_method(method_file_path)
        
        
        # Assert dropdown parameters are valid
        
        ## Mode
        if str(mode) != 'Standard' and str(mode) != 'HiSpeed':
            raise ValueError('\nInvalid CA mode. CA mode must be "Standard" or "HiSpeed"')
            return
        
        ## Current range
        valid_current_range = ['1A', '100mA', '10mA', '1mA', '100uA', '10uA', '1uA', '100nA', '10nA', '1nA', '100pA']
        if str(current_range) not in valid_current_range:
            raise ValueError('\nInvalid current range. Current range must be:\n' + str(valid_current_range))
            return
       
        
        # Handle levels
       
        ## Assert number of level voltages and level times are the same
        if len(levels_v) != len(levels_t):
           raise ValueError('\nInvalid CA levels. Number of voltages and times must be equal (len(levels_v) == len(levels_t)):\n')
           print(len(levels_v) + ' voltage levels specified.\n')
           print(len(levels_t) + ' time levels specified.\n')
           return
       
        ## Assert 0 < number of levels <= 25
        if len(levels_v) < 1:
            raise ValueError('\nInvalid CA levels. Must specify at least 1 level:\n')
            return
        if len(levels_v) > 25:
            raise ValueError('\nInvalid CA levels. Cannot specify more than 25 levels:\n')
            return
        
        ## Set level parameters
        self.set_method_parameter('Levels', str(len(levels_v)))
        for i in range(0, len(levels_v)):
            level_i = i + 1
            self.set_method_parameter(f'Levels.E[{level_i}]', str(levels_v[i]))
            self.set_method_parameter(f'Levels.time[{level_i}]', str(levels_t[i]))           
      
                   
        # Set all parameters
        
        self.set_method_parameter('Title', str(title))
        self.set_method_parameter('Mode', str(mode))
        self.set_method_parameter('Cycles', str(cycles))
        self.set_method_parameter('Interval time', str(interval_time))
        self.set_method_parameter('Current range', str(current_range))
        

        # Run method
        
        ## Start method
        start_time = time.time()
        self.start_method()
        
        ## Wait for method to finish
        while self.get_device_status()[0] == 2:
            time.sleep(0.1)
        stop_time = time.time()
        print('Ivium method finished!')
        
        
        # Return data

        ## Get data
        total_points = self.get_available_data_points_number()
        data_t = []
        data_V = []
        data_I = []
        for point_index in range(1,total_points+1):
            print(self.get_data_point(point_index))
            t,I,V = self.get_data_point(point_index)
            data_t.append(t)
            data_V.append(V)
            data_I.append(I)
        data_t = np.array(data_t)
        data_V = np.array(data_V)
        data_I = np.array(data_I)
        data_tI = np.array([data_t, data_I])
        
        ## Get attributes
        data_attrs={'Potential (V)' : data_V,
                    'Time (s)' : data_t,
                    'Title' : str(title),
                    'Mode' : str(mode),
                    'N_levels' : len(levels_v),
                    'Levels_v (V)' : levels_v,
                    'Levels_t (s)' : levels_t,
                    'Cycles' : cycles,
                    'Interval time (s)' : interval_time,
                    'Current range' : str(current_range),
                    'start_time' : start_time,
                    'stop_time' : stop_time}
        
        ## Return/save data
        if save == True:
            self.save(name = title, data = ArrayWithAttrs(data_tI, data_attrs))
        return ArrayWithAttrs(data_tI, data_attrs)        

#%% Main    

if __name__ == "__main__":

    ivium = Ivium()        
    
    
#%% How to run from other scripts (e.g., as part of particle track)

'''
open Ivium Soft & connect Ivium

from nplab.instruments.potentiostat.ivium import Ivium
ivium = Ivium()
# Put ivium object in lab equipment_dict

cv_data = ivium.run_cv() # Here specify the method/parameters you want to use from python (if you change parameters in Ivium soft, data will not be saved correctly)
lab.get_group().create_dataset(name = 'CV_%d', data = cv_data) # Use this line if you specify save = False in run_method() functions

#%%  Simultaneous (threaded) CV + SERS 

thread_cv = threading.Thread(target = ivium.run_cv, kwargs={'title': 'CV_test_%d'})
thread_SERS = threading.Thread(target = SERS_with_name, kwargs={'name': 'SERS_%d', 'laser_power': 0}) # Your SERS function here
thread_cv.start()
thread_SERS.start()
'''
