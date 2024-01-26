# -*- coding: utf-8 -*-
"""
Created on Fri Nov  3 17:02:07 2023

@author: smrs3, il322
"""

import numpy as np
from nplab import datafile
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


# Dictionary of parameters for Ivium methods
# method_dict = {
#     'CV' : {'Title' : 'CV', 'E start' : 'x', 'Vertex 1', 'Vertex 2', 'E step', 'N scans', 'Scanrate', 'Current Range'},
#     'CA' : ['Title', 'Levels', 'Cycles', 'Interval time', 'Current Range']
#     }



''' Notes about above method dictionary:
    - No warnings given when parameter name or set value are invalid, Ivium will just use the previous value
        - Can always double check parameters are correct when loading parameter in IviumSoft
    - Can be expanded to include additional method types
    - Can be expanded so drop-down parameters only allow you to pick valid options
    - Only includes some parameters for CV and CA
    - Only works with 'Standard' mode (not 'HiSpeed')
'''

class Ivium(Instrument, Pyvium):
    
    '''
    Class handling Ivium Potentiostat
    Uses pyvium library (pip install pyvium -> from pyvium import Pyvium as iv)
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
        
        self.data_file = datafile.current()
        
        
    def run_cv(self, 
               title : str = 'CV',
               mode : str = 'Standard',
               e_start : float = 0,
               vertex_1 : float = 1.0,
               vertex_2 : float = -1.0,
               e_step : float = 0.1,
               n_scans : int = 1,
               scanrate : float = 1,
               current_range : str = '1nA',
               method_file_path : str = r"C:\Users\HERA\Documents\GitHub\nplab\nplab\instrument\potentiostat\CV_Standard.imf"):
        
        
        '''
        Function for setting CV parameters, running CV, and returning data w/ metadata
        
        
        Parameters:
            
            self (Ivium class)
            mode (str = 'Standard') CV mode. Dropdown option: must be 'Standard' or 'HiSpeed'
            title (str = 'CV')
            e_start (float = 0): Starting potential in V
            vertex_1 (float = 1.0): Vertex 1 potential in V
            vertex_2 (float = -1.0): Vertex 2 potential in V
            e_step (float = 0.1): Potential step size in V
            n_scans (int = 1): Number of CV scans
            scanrate (float = 0.01): CV scan rate in V/s
            current_range (str = '1nA'): Current dynamic range. Dropdown option: must be in valid_current_range (see below)
            method_file_path (str): Method file path. Must be CV .imf file
            
            
        Notes/Improvements:
            
            Parameters must be set in function arguments:
                Parameters set in IviumSoft will not be saved to .h5 metadata
                No way to read updated parameters set in IviumSoft

            Does not check that parameter inputs are valid:
                If invalid, will run method on default parameters from method_file_path without warning!

            Current system requires hard-coding of individual method parameters:
                - Have to hard code any methods you want to set
                - Have to hard code valid options for dropdown parameters

            Further advanced CV method parameters can be added (AutoCR, PreRanging, etc.)
                 
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
        for point_index in range(1,total_points+1):
            V_x,I,V = self.get_data_point(point_index)
            t = point_index * (e_step/scanrate)
            data_t.append(t)
            data_V.append(V)
            data_I.append(I)
        data_t = np.array(data_t)
        data_V = np.array(data_V)
        data_I = np.array(data_I)
        data_VI = np.array([data_V, data_I])
        data_VIt = np.array([data_V, data_I, data_t])
        
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
        
        ## Return data
        self.data_file.create_dataset(name = title, data = data_VI, attrs = data_attrs)
        return ArrayWithAttrs(data_VIt, data_attrs)
        

#%%        

if __name__ == "__main__":

    ivium = Ivium()        
    #ivium.load_method(r"C:\Users\HERA\Documents\GitHub\nplab\nplab\instrument\potentiostat\E_step.imf")
    #ivium.run_cv()

    # IV_method=ctypes.create_string_buffer(b"C:\Users\HERA\Documents\GitHub\nplab\nplab\instrument\potentiostat\E_step.imf")
    # ivium.dll.IV_readmethod(ctypes.byref(IV_method))
    # ivium.dll.IV_startmethod()
    # print(ivium.dll.IV_getdevicestatus(None))
    # ivium.get_all_datapoints()

