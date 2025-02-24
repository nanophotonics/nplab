# -*- coding: utf-8 -*-
"""
Created on Fri Nov  3 17:02:07 2023

@author: smrs3, il322
"""

import numpy as np
from nplab import datafile as df
from nplab.utils.array_with_attrs import ArrayWithAttrs
from nplab.instrument import Instrument
import time
from pyvium import Pyvium
from pyvium.pyvium_verifiers import PyviumVerifiers



class Ivium(Instrument, Pyvium):
    
    
    '''
    Class handling Ivium Potentiostat
    Uses pyvium library (pip install pyvium -> from pyvium import Pyvium as iv)
    
                
    Notes/Improvements:
        
        Create GUI & GUI class
        
        CA: default method file only supports 2 levels, how to add more without chanign method?
        
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
               e_step : float = 0.01,
               n_scans : int = 1,
               scanrate : float = 0.1,
               current_range : str = '10mA',
               auto_cr : bool = True,
               auto_cr_max : str = '1A',
               auto_cr_min : str = '1nA',
               pre_ranging : bool = True,
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
            e_step (float = 0.01): Potential step size in V
            n_scans (int = 1): Number of CV scans
            scanrate (float = 0.1): CV scan rate in V/s
            current_range (str = '10mA'): Current dynamic range. Dropdown option: must be in valid_current_range (see below)
            auto_cr (bool = True): Enable/disable auto current ranging during measurement. If False, current signal may saturate
                auto_cr_max (str = '1A'): Max current dynamic range for autoranging. Dropdown option: must be in valid_current_range (see below)
                auto_cr_min (str = '1nA'): Min current dynamic range for autoranging. Dropdown option: must be in valid_current_range (see below)
                pre_ranging (bool = True): Enable/disable pre-determination of current dynamic range, if using auto ranging.   
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
        if str(auto_cr_max) not in valid_current_range:
            raise ValueError('\nInvalid auto current range limit. Current range must be:\n' + str(valid_current_range))
            return
        if str(auto_cr_min) not in valid_current_range:
            raise ValueError('\nInvalid auto current range limit. Current range must be:\n' + str(valid_current_range))
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
        self.set_method_parameter('AutoCR', str(auto_cr).lower())
        if auto_cr:
            self.set_method_parameter('AutoCR.Max range', str(auto_cr_max))
            self.set_method_parameter('AutoCR.Min range', str(auto_cr_min))
            self.set_method_parameter('AutoCR.Pre ranging', str(pre_ranging).lower())
            
            
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
                    'AutoCR' : str(auto_cr),
                    'AutoCR Max Range' : str(auto_cr_max),
                    'AutoCR Min Range' : str(auto_cr_min),
                    'AutoCR Pre Ranging' : str(pre_ranging),
                    'start_time' : start_time,
                    'stop_time' : stop_time}
        
        ## Return/save data
        if save == True:
            self.save(name = title, data = ArrayWithAttrs(data_VI, data_attrs))
        return ArrayWithAttrs(data_VI, data_attrs)
        
    
    def run_lsv(self, 
               title : str = 'LSV_%d',
               mode : str = 'Standard',
               e_start : float = 0,
               e_end : float = 1.0,
               e_step : float = 0.01,
               scanrate : float = 0.1,
               current_range : str = '10mA',
               auto_cr : bool = True,
               auto_cr_max : str = '1A',
               auto_cr_min : str = '1nA',
               pre_ranging : bool = True,
               method_file_path : str = r"C:\Users\HERA\Documents\GitHub\nplab\nplab\instrument\potentiostat\LSV_Standard.imf",
               save : bool = True):
        
        
        '''
        Function for setting LSV parameters, running LSV, and returning data w/ attributes
        
        
        Parameters:
            
            self (Ivium class)
            title (str = 'LSV_%d')
            mode (str = 'Standard') LSV mode. Dropdown option: must be 'Standard' or 'HiSpeed'
            e_start (float = 0): Starting potential in V
            e_end (float = 1.0): Ending potential in V
            e_step (float = 0.01): Potential step size in V
            scanrate (float = 0.1): LSV scan rate in V/s
            current_range (str = '10mA'): Current dynamic range. Dropdown option: must be in valid_current_range (see below)
            auto_cr (bool = True): Enable/disable auto current ranging during measurement. If False, current signal may saturate
                auto_cr_max (str = '1A'): Max current dynamic range for autoranging. Dropdown option: must be in valid_current_range (see below)
                auto_cr_min (str = '1nA'): Min current dynamic range for autoranging. Dropdown option: must be in valid_current_range (see below)
                pre_ranging (bool = True): Enable/disable pre-determination of current dynamic range, if using auto ranging.   
            method_file_path (str): Method file path. Must be LSV .imf file
            save (bool = True): If true, saves data automatically to h5 file    
        '''
        
        
        # Load LSV method
        
        self.load_method(method_file_path)
        
        
        # Assert dropdown parameters are valid
        
        ## Mode
        if str(mode) != 'Standard' and str(mode) != 'HiSpeed':
            raise ValueError('\nInvalid LSV mode. LSV mode must be "Standard" or "HiSpeed"')
            return
        
        ## Current range
        valid_current_range = ['1A', '100mA', '10mA', '1mA', '100uA', '10uA', '1uA', '100nA', '10nA', '1nA', '100pA']
        if str(current_range) not in valid_current_range:
            raise ValueError('\nInvalid current range. Current range must be:\n' + str(valid_current_range))
            return
        if str(auto_cr_max) not in valid_current_range:
            raise ValueError('\nInvalid auto current range limit. Current range must be:\n' + str(valid_current_range))
            return
        if str(auto_cr_min) not in valid_current_range:
            raise ValueError('\nInvalid auto current range limit. Current range must be:\n' + str(valid_current_range))
            return
        
        
        # Set all parameters
        
        self.set_method_parameter('Title', str(title))
        self.set_method_parameter('Mode', str(mode))
        self.set_method_parameter('E start', str(e_start))      
        self.set_method_parameter('E end', str(e_end))      
        self.set_method_parameter('E step', str(e_step))
        self.set_method_parameter('Scanrate', str(scanrate))
        self.set_method_parameter('Current range', str(current_range))
        self.set_method_parameter('AutoCR', str(auto_cr).lower())
        if auto_cr:
            self.set_method_parameter('AutoCR.Max range', str(auto_cr_max))
            self.set_method_parameter('AutoCR.Min range', str(auto_cr_min))
            self.set_method_parameter('AutoCR.Pre ranging', str(pre_ranging).lower())        


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
        
        ## Get attributes
        data_attrs={'Potential (V)' : data_V,
                    'Time (s)' : data_t,
                    'Title' : str(title),
                    'Mode' : str(mode),
                    'E start (V)' : e_start,
                    'E end (V)' : e_end,
                    'E step (V)' : e_step,
                    'Scanrate (V/s)' : scanrate,
                    'Current range' : str(current_range),
                    'AutoCR' : str(auto_cr),
                    'AutoCR Max Range' : str(auto_cr_max),
                    'AutoCR Min Range' : str(auto_cr_min),
                    'AutoCR Pre Ranging' : str(pre_ranging),
                    'start_time' : start_time,
                    'stop_time' : stop_time}
        
        ## Return/save data
        if save == True:
            self.save(name = title, data = ArrayWithAttrs(data_VI, data_attrs))
        return ArrayWithAttrs(data_VI, data_attrs)
        
    
    def run_ca(self, 
               title : str = 'CA_%d',
               mode : str = 'Standard',
               levels_v : list = [0, 1.0],
               levels_t : list = [1, 1],
               cycles : int = 5,
               interval_time : float = 0.1,
               current_range : str = '10mA',
               auto_cr : bool = True,
               auto_cr_max : str = '1A',
               auto_cr_min : str = '1nA',
               pre_ranging : bool = True,
               method_file_path : str = r"C:\Users\HERA\Documents\GitHub\nplab\nplab\instrument\potentiostat\CA_Standard.imf",
               save : bool = True):
        
        
        '''
        Function for setting ChronoAmperometry parameters, running CA, and returning/saving data w/ metadata
        
        Note: Using more than 2 levels requires creating a new .imf file with the desired number of levels as method_file_path
        
        Parameters:
            
            self (Ivium class)
            title (str = 'CA_%d')
            mode (str = 'Standard') CA mode. Dropdown option: must be 'Standard' or 'HiSpeed'
            levels_v (list = [0, 1.0]): CA level potentials in V
            levels_t (list = [1, 1]): CA level times in s
            cycles (int = 5): Number of CA cycles
            interval_time (float = 0.1): CA data point step size in s
            current_range (str = '10mA'): Current dynamic range. Dropdown option: must be in valid_current_range (see below)
            auto_cr (bool = True): Enable/disable auto current ranging during measurement. If False, current signal may saturate
                auto_cr_max (str = '1A'): Max current dynamic range for autoranging. Dropdown option: must be in valid_current_range (see below)
                auto_cr_min (str = '1nA'): Min current dynamic range for autoranging. Dropdown option: must be in valid_current_range (see below)
                pre_ranging (bool = True): Enable/disable pre-determination of current dynamic range, if using auto ranging.   
            method_file_path (str): Method file path. Must be CA .imf file. Default file is for 2 levels.     
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
        if str(auto_cr_max) not in valid_current_range:
            raise ValueError('\nInvalid auto current range limit. Current range must be:\n' + str(valid_current_range))
            return
        if str(auto_cr_min) not in valid_current_range:
            raise ValueError('\nInvalid auto current range limit. Current range must be:\n' + str(valid_current_range))
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
        self.set_method_parameter('AutoCR', str(auto_cr).lower())
        if auto_cr:
            self.set_method_parameter('AutoCR.Max range', str(auto_cr_max))
            self.set_method_parameter('AutoCR.Min range', str(auto_cr_min))
            self.set_method_parameter('AutoCR.Pre ranging', str(pre_ranging).lower())        


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
            t,I,V = self.get_data_point(point_index)
            data_t.append(t)
            data_V.append(V)
            data_I.append(I)
        data_t = np.array(data_t)
        data_V = np.array(data_V)
        data_I = np.array(data_I)
        data_tI = np.array([data_t, data_I])
        
        ## Get attributes
        data_attrs={
                    # 'Potential (V)' : data_V,
                    # 'Time (s)' : data_t,
                    'Title' : str(title),
                    'Mode' : str(mode),
                    'N_levels' : len(levels_v),
                    'Levels_v (V)' : levels_v,
                    'Levels_t (s)' : levels_t,
                    'Cycles' : cycles,
                    'Interval time (s)' : interval_time,
                    'Current range' : str(current_range),
                    'AutoCR' : str(auto_cr),
                    'AutoCR Max Range' : str(auto_cr_max),
                    'AutoCR Min Range' : str(auto_cr_min),
                    'AutoCR Pre Ranging' : str(pre_ranging),
                    'start_time' : start_time,
                    'stop_time' : stop_time}
        
        ## Return/save data
        if save == True:
            self.save(name = title, data = ArrayWithAttrs(data_tI, data_attrs))
        return ArrayWithAttrs(data_tI, data_attrs)        
    
    
    def run_ocp_trace(self, 
               title : str = 'OCP_%d',
               interval_time : float = 0.1,
               run_time : float = 10,
               current_range : str = '10mA',
               auto_cr : bool = True,
               auto_cr_max : str = '1A',
               auto_cr_min : str = '1nA',
               pre_ranging : bool = True,
               potential_range : str = '4V',
               method_file_path : str = r"C:\Users\HERA\Documents\GitHub\nplab\nplab\instrument\potentiostat\ECN_Standard.imf",
               save : bool = True):
        
        
        '''
        Function for measuring OCP (current and potential), aka Electrochemical Noise method
        
        
        Parameters:
            
            self (Ivium class)
            title (str = 'CA_%d')
            interval_time (float = 0.1): Data point step size in s
            run_time (float = 10): Total scan time in s
            current_range (str = '10mA'): Current dynamic range. Dropdown option: must be in valid_current_range (see below)
                auto_cr_max (str = '1A'): Max current dynamic range for autoranging. Dropdown option: must be in valid_current_range (see below)
                auto_cr_min (str = '1nA'): Min current dynamic range for autoranging. Dropdown option: must be in valid_current_range (see below)
                pre_ranging (bool = True): Enable/disable pre-determination of current dynamic range, if using auto ranging.  
            potential_range (str = '4V'): Potential dynamic range. Dropdown option: must be in valid_potential_range (see below)
            method_file_path (str): Method file path. Must be CA .imf file. Default file is for 2 levels.     
            save (bool = True):             
        '''
        
        
        # Load electrochemical noise method
        
        self.load_method(method_file_path)
        
        
        # Assert dropdown parameters are valid
        
        
        ## Current range
        valid_current_range = ['1A', '100mA', '10mA', '1mA', '100uA', '10uA', '1uA', '100nA', '10nA', '1nA', '100pA']
        if str(current_range) not in valid_current_range:
            raise ValueError('\nInvalid current range. Current range must be:\n' + str(valid_current_range))
            return
        if str(auto_cr_max) not in valid_current_range:
            raise ValueError('\nInvalid auto current range limit. Current range must be:\n' + str(valid_current_range))
            return
        if str(auto_cr_min) not in valid_current_range:
            raise ValueError('\nInvalid auto current range limit. Current range must be:\n' + str(valid_current_range))
            return
       
        ## Potential range
        ## Current range
        valid_potential_range = ['10V', '4V', '1V', '400mV', '100mV', '40mV', '10mV', '1mV']
        if str(potential_range) not in valid_potential_range:
            raise ValueError('\nInvalid potential range. Potential range must be:\n' + str(valid_potential_range))
            return

                   
        # Set all parameters
        
        self.set_method_parameter('Title', str(title))
        self.set_method_parameter('Interval time', str(interval_time))
        self.set_method_parameter('Run time', str(run_time))
        self.set_method_parameter('Potential range', str(potential_range))
        self.set_method_parameter('Current range', str(current_range))
        self.set_method_parameter('AutoCR', str(auto_cr).lower())
        if auto_cr:
            self.set_method_parameter('AutoCR.Max range', str(auto_cr_max))
            self.set_method_parameter('AutoCR.Min range', str(auto_cr_min))
            self.set_method_parameter('AutoCR.Pre ranging', str(pre_ranging).lower())        


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
            t,I,V = self.get_data_point(point_index)
            data_t.append(t)
            data_V.append(V)
            data_I.append(I)
        data_t = np.array(data_t)
        data_V = np.array(data_V)
        data_I = np.array(data_I)
        data_tI = np.array([data_t, data_I])
        data_tV = np.array([data_t, data_V])
        
        ## Get attributes
        data_attrs={
                    # 'Potential (V)' : data_V,
                    # 'Time (s)' : data_t,
                    'Title' : str(title),
                    'Interval time (s)' : interval_time,
                    'Potential range' : str(potential_range),
                    'Current range' : str(current_range),
                    'AutoCR' : str(auto_cr),
                    'AutoCR Max Range' : str(auto_cr_max),
                    'AutoCR Min Range' : str(auto_cr_min),
                    'AutoCR Pre Ranging' : str(pre_ranging),
                    'start_time' : start_time,
                    'stop_time' : stop_time}
        
        ## Return/save data
        if save == True:
            self.save(name = title + '_currents', data = ArrayWithAttrs(data_tI, data_attrs))
            self.save(name = title + '_voltages', data = ArrayWithAttrs(data_tV, data_attrs))
        return ArrayWithAttrs(data_tI, data_attrs)        
                                                                                                                                                                                
                   
#%% Main    

if __name__ == "__main__":

    ivium = Ivium()
    
    from nplab.ui.data_group_creator import DataGroupCreator
    from nplab import datafile
    from nplab.utils.gui_generator import GuiGenerator
    dgc = DataGroupCreator()
    data_file = datafile.current()      
    GuiGenerator({'data_group_creator': dgc})
    
    
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
