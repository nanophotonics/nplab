# -*- coding: utf-8 -*-
"""
Created on Sun May 14 14:22:50 2023

@author: il322

Module with specific functions for processing and analysing SERS spectra
Inherits spectral classes from spectrum_tools.py
"""

import h5py
import os
import math
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from importlib import reload

from nplab.analysis.general_spec_tools import spectrum_tools as spt
from nplab.analysis.general_spec_tools import npom_sers_tools as nst



class SERS_Spectrum(spt.Spectrum):
    
    '''
    Object containing xy data and functions for NPoM SERS spectral analysis and plotting
    Inherits from "Spectrum" object class in spectrum_tools module
    args can be y data, x and y data, h5 dataset or h5 dataset and its name
    '''
    
    def __init__(self, *args, raman_excitation = None, particle_name = 'Particle_',
                 spec_calibrated = False, intensity_calibrated = False, **kwargs):

        super().__init__(*args, raman_excitation = raman_excitation, **kwargs)

        self.particle_name = particle_name
        self.spec_calibrated = spec_calibrated
        self.intensity_calibrated = intensity_calibrated

        self.x_min = self.x.min()
        self.x_max = self.x.max()
        
    def calibrate_intensity(self, R_setup = 1, dark_counts = 0, laser_power = None, exposure = None):
        
        '''
        Function to convert raw counts into cts/mW/s & apply spectral efficiency calibration
        
        Parameters:
            R_setup: (array of floats) White light efficiency correction array
            dark_counts: (SERS_Spectrum) Dark count spectrum
            laser_power: (float) If not given, will try to take from dset.attrs
            exposure: (float) If not given, will try to take from dset.attrs
        '''
        if laser_power is None:
            try:
                laser_power = self.dset.attrs['laser_power']
            except:
                print('Error: Laser power not found')
                return
            
        if exposure is None:
            try:
                exposure = self.dset.attrs['Exposure']
            except:
                print('Error: Exposure not found')
                return
            
        self.y = (self.y - dark_counts) / (R_setup * laser_power * exposure)


        
class SERS_Timescan(spt.Timescan):
    
    '''
    Object containing x, y, t data for SERS timescan
    Inherits from spt.Timescan class
    args can be y data, x and y data, h5 dataset or h5 dataset and its name
    
    Optional parameters:
        raman_excitation (float): excitation wavelength for converting wavelength to wavenumber
        particle_name
        spec_calibrated (boolean): set True if input x is already calibrated
        intensity_calibrated (boolean): set True if input y is already calibrated and in cts/mW/s
        
    '''
    
    def __init__(self, *args, raman_excitation = None, particle_name = 'Particle_',
                 spec_calibrated = False, intensity_calibrated = False, **kwargs):

        super().__init__(*args, raman_excitation = raman_excitation, **kwargs)

        self.particle_name = particle_name
        self.spec_calibrated = spec_calibrated
        self.intensity_calibrated = intensity_calibrated

        self.x_min = self.x.min()
        self.x_max = self.x.max()


    def calibrate_intensity(self, R_setup = 1, dark_counts = 0, laser_power = None, exposure = None):
        
        '''
        Function to convert raw counts into cts/mW/s & apply spectral efficiency calibration
        
        Parameters:
            R_setup: (array of floats) White light efficiency correction array
            dark_counts: (SERS_Spectrum) Dark count spectrum
            laser_power: (float) If not given, will try to take from dset.attrs
            exposure: (float) If not given, will try to take from dset.attrs
        '''
        if laser_power is None:
            try:
                laser_power = self.dset.attrs['laser_power']
            except:
                print('Error: Laser power not found')
                return
            
        if exposure is None:
            try:
                exposure = self.dset.attrs['Exposure']
            except:
                print('Error: Exposure not found')
                return
            
        self.Y = (self.Y - dark_counts) / (R_setup * laser_power * exposure)
        self.y = np.average(self.Y, axis = 0)

    
    def extract_nanocavity(self, plot=False):
        
        '''
        Extracts a stable nanocavity spectrum from a timescan that contains flares or picocavities
        Calculates flat baseline value for each pixel (wln or wn) across a timescan
        The flat baseline value is the y-value (intensity) of the nanocavity at that x-value
        
        Parameters:
            timescan: (nst.Timescan class) - best if already x & y-calibrated
            plot: (boolean) plots nanocavity spectrum
            
        Returns:
            nanocavity_spectrum: (SERS_Spectrum class) extracted nanocavity spectrum
        '''
        
        # Get flat baseline value of each pixel (x-value) across each scan of time scan
        
        pixel_baseline = np.zeros(len(self.x))
        for pixel in range(0,len(self.x)):
            pixel_baseline[pixel] = np.polyfit(self.t, self.Y[:,pixel], 0)
        self.nanocavity_spectrum = SERS_Spectrum(self.x, pixel_baseline)
        
        # Plot extracted nanocavity spectrum
        if plot == True:
            self.nanocavity_spectrum.plot()
            

    def integrate_timescan(self, plot=False):
        
        '''
        Adds together all scans in timescan into single SERS spectrum!
        '''
        
        self.y_int = np.sum(self.Y, axis = 0)
        self.integrated_spectrum = SERS_Spectrum(self.x, self.y_int)
        
        # Plot integrated spectrum
        if plot == True:
            self.integrated_spectrum.plot()
            
   
        
class SERS_Powerseries():
    
    '''
    Object containing SERS powerseries
    Arg should be h5 group containing individual SERS timescans (each at diff laser power), 
    or list of timescans
    '''
    
    def __init__(self, *args, raman_excitation = 632.8, particle_name = 'Particle_', **kwargs):

        super().__init__(*args, raman_excitation = raman_excitation, **kwargs)

        self.particle_name = particle_name
    
    
    
    