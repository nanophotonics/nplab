# -*- coding: utf-8 -*-
'''
Created on 2023-03-23
author: Charlie Readman, car72

Module for extracting data from .spc files
Most useful for keeping track of Renishaw spectral metadata

This is an overhaul of the much older spc_to_h5 module
'''

import os
import datetime
import numpy as np
import h5py
from nplab.analysis.general_spec_tools.renishaw_laser_powers import all_laser_powers

try:
    import spc
except Exception as e:
    print('spc module not installed!')
    print('spc is not available via pip; instead, clone from https://github.com/rohanisaac/spc and install')
    raise e

from nplab.analysis.general_spec_tools import particle_track_analysis as pta

class Renishaw_SPC_Datafile:
    '''
    wrapper for .spc files from the Renishaw 
    extracts xy (or xY for timescans) data

    also extracts metadata and stores as object attributes:
        laser wavelength
            nm
        laser power
            %
            this gets converted to mW using latest power calibration data
        accumulations
            int
        exposure time
            ms
        whether cosmic rays were removed
            True/False
        laser focus mode
            pinhole, linefocus etc
        grating details
            lines per mm
        scan type
            timescan or single
        measurement type
            static or extended
    '''
    def __init__(self, filename, power_dict = None, **kwargs):
        '''
        args:
            filename: str
                name of spc file
                (must end in .spc, obviously)
            power_dict: dict
                dictionary containing values for converting % laser power to actual power
                must be in the format {laser power : {percent power : absolute power (mW)}}
        '''
        self.filename = filename
        
        timestamp = os.path.getmtime(filename)
        timestamp = datetime.datetime.fromtimestamp(timestamp)
        self.timestamp = str(timestamp).replace(' ', 'T')
                        
        metadata_keys = [b'Exposure_time', b'Accumulations', b'Cosmic_ray_removal', b'Focus_mode', b'Grating_grooves', 
                         b'Laser', b'Laser_power', b'Measurement_type', b'Scan_type']
        metadata_dict = {}
        
        F = spc.File(filename)
            
        for key in metadata_keys:
            value = F.log_dict[key]
            
            if type(key) == bytes:
                key = key.decode()
            
            try:
                if type(value) == bytes:
                    value = value.decode()
                
            except Exception as e:
                value = str(value)
                print(f'Encountered an error when parsing {filename}:')
                print(f'spc.File("{filename}").log_dict["{key}"] = {value}')
                print(f'Could not decode value {value} because {e}')
                
            metadata_dict[key] = value        
        
        self.exposure = float(metadata_dict['Exposure_time'].split(': ')[-1])
        self.accumulations = int(metadata_dict['Accumulations'].split(': ')[-1])
        self.cosmic_rays_removed = bool(int(metadata_dict['Cosmic_ray_removal'].split(': ')[-1]))
        self.focus_mode = metadata_dict['Focus_mode']
        self.grating = metadata_dict['Grating_grooves'].split(': ')[-1]
        self.laser_wavelength = int(metadata_dict['Laser'].split(': ')[-1].split(' ')[0])
        self.percent_laser_power = float(metadata_dict['Laser_power'].split(': ')[-1].strip('%'))

        if power_dict is not None:
            for laser_wavelength, powers in power_dict.items():
                all_laser_powers[laser_wavelength].update(powers)

        try:
            self.laser_power = all_laser_powers[self.laser_wavelength][self.percent_laser_power]
        except KeyError:
            print(f'{self.filename}: absolute laser power not known for {self.laser_wavelength} at {self.percent_laser_power}%')
            self.laser_power = 1

        self.scan_type = metadata_dict['Scan_type']
        self.measurement_type = metadata_dict['Measurement_type']
        
        self.x = F.x
        self.y = np.array([sub_file.y for sub_file in F.sub])
        
        if len(self.y) == 1:
            self.y = self.y[0]
        else:
            self.Y = self.y.copy()
            self.y = np.sum(self.Y, axis = 0)
    
    def add_to_h5(self, h5_group, dset_name = None, **kwargs):
        '''
        creates new h5 dataset containing xy data (if single scan) or xY data (if timescan)
        updates dataset attributes with object metadata
        args:
            h5_group: open h5 file or group object
                file/group in which to create the new dataset
            dset name: str (optional)
                new name for the dataset
                if not specified, defaults to the spc filename (without the .spc extension)
        '''
        if dset_name is None:
            dset_name = self.filename[:-4]
        
        data = self.__dict__.get('Y', self.y)
        dset = h5_group.create_dataset(dset_name, data = data)
        
        for key, value in self.__dict__.items():
            if key not in ['Y', 'y', 'x']:
                dset.attrs[key] = value
        
        dset.attrs['wavelengths'] = self.x
        return dset

def extract_all_spc(data_dir = None, h5_filename = None, h5_group_name = None, filenames = None, dset_names = None, 
                    overwrite_h5 = False, overwrite_dsets = False,
                    **kwargs):
    '''
    Converts a collection of spc_files into .h5 format
        Extracts and stores both xy data and metadata (see Renishaw_SPC_Datafile class for more details)

    kwargs: (all optional)
        h5_filename: str (optional)
            name of h5 file to transfer the data to
            new file will be created if it doesn't exist yet
            if not specified, name of the parent folder will be used
        h5_group: str (optional)
            if specified, put data in h5 group instead of the main file root
            group will be created if it doesnt exist yet
        data_dir: str (optional)
            directory in which the .spc files are located
            if not specified, current working directory will be used
        filenames: iterable (optional)
            list of filenames from which to extract data
            if not specified, all spc files in the folder will be extracted
        dset_names: iterable (optional)
            list of names with which to rename the spc data when creating the h5 datasets
            if not specified, defaults to filenames (above)
            if specified, must be the same length as filenames

    **kwargs:
        power_dict: dict
            see Renishaw_SPC_Datafile docstring
            
    '''
    if data_dir is not None:
        os.chdir(data_dir)

    if filenames is None:
        filenames = [filename for filename in os.listdir() if filename.endswith('.spc')]

    if dset_names is None:
        dset_names = [filename[:-4] for filename in filenames]

    else:
        assert len(dset_names) == len(filenames), 'Please specify the correct number of dataset names'

    spc_files = [Renishaw_SPC_Datafile(filename, **kwargs) for filename in filenames]

    if h5_filename is None:
        h5_filename = os.path.split(os.getcwd())[-1]

    if not h5_filename.endswith('.h5'):
        h5_filename = f'{h5_filename}.h5'

    if overwrite_h5 == True:
        if h5_filename in os.listdir():
            os.remove(h5_filename)

    with h5py.File(h5_filename, 'a') as F:
        data_group = F
        if h5_group_name is not None:
            data_group = F.get(h5_group_name, F.create_group(h5_group_name))
        
        for spc_file, dset_name in zip(spc_files, dset_names):
            if dset_name in data_group.keys() and overwrite_dsets == True:
                del data_group[dset_name]
            dset = spc_file.add_to_h5(data_group, dset_name = dset_name, **kwargs)