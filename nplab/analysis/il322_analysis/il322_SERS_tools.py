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


#%% E-Chem plotting functions - can be moved to their own script maybe

def plot_ca(ca_data, ax, t_min = None, t_max = None):

    '''
    Plot chronoamperometry data
    
    Parameters:
        ca_data
        ax: (mpl.ax) axis to be plotted on
        t_min: (float) Time minimum for plotting
        t_max: (float) Time maximum for plotting
    '''
    
    
    # Extract current (uA) and time (s)
    
    current = ca_data[:,1]*10**3
    time = ca_data[:,0]
    
    
    # Plot current v. time
    
    ax.plot(current, time)
    ax.set_ylabel('Time (s)', fontsize='large')
    ax.set_xlabel('Current ($\mu$A)', fontsize='large')
    ax.set_ylim(t_min, t_max)


def plot_cv(cv_data, ax, t_min = None, t_max = None):
    
    '''
    Plot Cyclic Voltammetry data
    
    Parameters:
        cv_data
        attrs: h5 dataset attributes
        ax: (mpl.ax) axis to be plotted on
        t_min: (float) Time minimum for plotting
        t_max: (float) Time maximum for plotting
    '''
    
    
    # Extract current (uA), voltage (V), time (s)
    
    current = cv_data[:,2]*10**6
    time = cv_data[:,0]
    voltage = cv_data[:,1]


    # Time limits

    if t_min is None:
        t_min = time.min()
        
    if t_max is None:
        t_max = time.max()


    # Plot current v. time

    ax.plot(current, time)
    ax.set_ylabel('Voltage (V)', fontsize='large')
    ax.set_xlabel('Current ($\mu$A)', fontsize='large')
    
    ## Get voltage tick values from time tick values 
    n_ticks = 12
    time_ticks = time[::int(len(time)/n_ticks)]
    volt_ticks = np.round(voltage[time.searchsorted(time_ticks)],1)
    ax.set_yticks(time_ticks, volt_ticks)
    ax.set_ylim(t_min, t_max)
   
    
#%% SERS_Spectrum class

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

    '''
    popt_gauss, pcov_gauss = scipy.optimize.curve_fit(spt.lorentzian, spectrum.x[460:500], spectrum.y[460:500], p0=[2.4e6, 1550, 20])
    perr_gauss = np.sqrt(np.diag(pcov_gauss))

    plt.plot(spectrum.x, spt.lorentzian(x=spectrum.x, height = popt_gauss[0], center = popt_gauss[1], fwhm=popt_gauss[2]))
    plt.plot(spectrum.x, spectrum.y)
    
    '''


#%% SERS_Timescan class
        
class SERS_Timescan(spt.Timescan):
    
    '''
    Object containing x, y, t data for SERS timescan
    Inherits from spt.Timescan class
    args can be y data, x and y data, h5 dataset or h5 dataset and its name
    
    Optional parameters:
        raman_excitation (float): excitation wavelength for converting wavelength to wavenumber
        name: (str = '')
        spec_calibrated (boolean): set True if input x is already calibrated
        intensity_calibrated (boolean): set True if input y is already calibrated and in cts/mW/s
        
    '''
    
    def __init__(self, *args, raman_excitation = None, name = '',
                 spec_calibrated = False, intensity_calibrated = False, echem_mode = '', echem_data = None, **kwargs):

        super().__init__(*args, raman_excitation = raman_excitation, **kwargs)

        self.name = name
        self.spec_calibrated = spec_calibrated
        self.intensity_calibrated = intensity_calibrated
        self.echem_mode = echem_mode.upper()
        self.echem_data = echem_data
        
        self.t = self.t_raw * self.dset.attrs['Exposure']
    


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
    
            
    def plot_timescan(self, plot_type = 'cmap', 
                      v_min = None, v_max = None,
                      x_min = None, x_max = None,
                      t_min = None, t_max = None, t_offset = 0,
                      cmap = 'inferno', avg_chunks = None, avg_color = 'white', 
                      stack_offset = None, stack_color = 'black', 
                      plot_echem = False):
        
        '''
        Function for plotting a single timescan, either as a colormap or as a stack of single spectra
        Can optionally plot echem data (a CV curve or chronoamperometry data) alongside timescan
        
        Parameters:
            plot_type: (string = 'cmap') Determines type of plot. 'cmap' for colormap or 'stack' for stack of single spectra
            v_min: (float = None) Minimum value for colormap normalization
            v_max: (float = None) Maximum value for colormap normalization
            x_min: (float = None) x minimum for plotting
            x_max: (float = None) x maximum for plotting
            t_min: (float = None) Time minimum for plotting
            t_max: (float = None) Time maximum for plotting
            t_offset: (float = 0) Offset timescan in time axis so it matches echem data
            cmap: (string = 'inferno') Colormap for plotting
            avg_chunks: (int = None) Number of spectra to calculate for average spectra in colormap
            avg_color: (string = 'white') Color for avergae chunk plotting on colormap
            stack_offset: (float = None) y-offset value for stacked spectra
            stack_color: (string = 'black') Color for stacked spectra
            plot_echem: (boolean = False) Choose if plotting echem alongside timescan. Must have specified echem data in class initialization
        '''
        
        
        assert plot_type == 'cmap' or plot_type == 'stack', 'Error: invalid plot type. Please specify either "cmap" or "stack"'
        
        
        # Set v, x, and t limits
        
        if v_min is None:
            v_min = self.Y.min()
        
        if v_max is None:
            v_max = np.percentile(self.Y, 95) # Take 95th percentile for v_max -> good for removing effect of cosmic rays on cmap
            print(v_max)
        if x_min is None:
            x_min = self.x.min()
            
        if x_max is None:
            x_max = self.x.max()
            
        if t_min is None:
            t_min = self.t.min()
            
        if t_max is None:
            t_max = self.t.max()
        
        
        # Plot E-Chem
        
        if plot_echem == True:
            assert self.echem_mode == 'CA' or self.echem_mode == 'CV', 'Error: please specify E-Chem mode as either "CA" or "CV"'
            assert self.echem_data is not None, 'Error: No echem data provided'
                        
            ## Plot CA
            if self.echem_mode == 'CA':
                
                ### Define figure with 2 subplots - ax2 for echem & ax1 for timescan
                fig, (ax2, ax1) = plt.subplots(1, 2, figsize=[12,16], gridspec_kw={'width_ratios': [1, 3]}, sharey=False)
                
                plot_ca(ca_data = self.echem_data, ax = ax2, t_min = t_min, t_max = t_max)
            
                ### Set title
                try:
                    fig.suptitle('SERS Timescan + Chronoamperometry ' + str(self.dset.attrs['Level 1']) + 'V to ' + str(self.dset.attrs['Level 2']) + 'V\n' + self.dset.attrs['sample'] + '\n' + self.name, fontsize='x-large')
                except:
                    fig.suptitle('SERS Timescan + Chronomperometry\n' + self.dset.attrs['sample'] + '\n' + self.name, fontsize='x-large')


            ## Plot CV
            elif self.echem_mode == 'CV':
                
                ### Define figure with 2 subplots - ax2 for echem & ax1 for timescan
                fig, (ax2, ax1) = plt.subplots(1, 2, figsize=[12,16], gridspec_kw={'width_ratios': [1, 3]}, sharey=False)
                plot_cv(cv_data = self.echem_data, ax = ax2, t_min = t_min, t_max = t_max)
                
                ### Set time axis label
                ax1.set_ylabel(r'Time (s)', fontsize = 'large')
                
                ### Set title
                try:
                    fig.suptitle('SERS Timescan + Cyclic Voltammetry ' + str(self.dset.attrs['Vertex 1']) + 'V to ' + str(self.dset.attrs['Vertex 2']) + 'V\n' + self.dset.attrs['sample'] + '\n' + self.name, fontsize='x-large')
                except:
                    fig.suptitle('SERS Timescan + Cyclic Voltammetry\n' + self.dset.attrs['sample'] + '\n' + self.name, fontsize='x-large')
        
      
        else:
            ## If not plotting e_chem, define figure with 1 subplots - ax1 for timescan, set axis label & title
            fig, (ax1) = plt.subplots(1, 1, figsize=[12,16])
            ax1.set_ylabel(r'Time (s)', fontsize = 'large')
            fig.suptitle('SERS Timescan\n' + self.dset.attrs['sample'] + '\n' + self.name, fontsize='x-large')
        
        
        # Plot SERS timescan
        
        ax1.set_xlabel(r'Raman shift (cm$^{-1}$)', fontsize='large')
        ax1.set_xlim(x_min, x_max)
        
        ## Plot as colormap
        if plot_type == 'cmap':    
            cmap = plt.get_cmap(cmap)
            pcm = ax1.pcolormesh(self.x, self.t + t_offset, self.Y, vmin = v_min, vmax = v_max, cmap = cmap)
            ax1.set_ylim(t_min, t_max)
            clb = fig.colorbar(pcm, ax=ax1)
            clb.set_label(label = 'SERS Intensity (cts/mW/s)', size = 'large', rotation = 270, labelpad=30)
            
            ### Plot average chunks
            if avg_chunks is not None:
                Y_arr = np.split(self.Y, len(self.Y)/avg_chunks) # Split self.Y into arrays of avg_chunk size
                time_inc = len(self.t) * self.dset.attrs['Exposure']/(len(self.Y)/avg_chunks)
                for n, Y_i in enumerate(Y_arr):
                    y_i = np.sum(Y_i, axis = 0)
                    y_i = y_i - y_i.min()
                    y_i = y_i/y_i.max()
                    y_i *= time_inc*0.95
                    y_i += n*time_inc + t_offset    
                    ax1.plot(self.x, y_i, color = 'black', lw = 6) # Plot black border around avg spectrum
                    ax1.plot(self.x, y_i, color = avg_color, alpha = 0.85) # Plot avg spectrum
            
        ## Plot as stacked spectra
        elif plot_type == 'stack':
            
            ### Set stack offset
            if stack_offset is None:
                stack_offset = np.percentile(self.Y, 5)

            ### Loop through individual spectra in given time range
            for i, spectrum in enumerate(self.Y[int(t_min/self.dset.attrs['Exposure']) : int(t_max/self.dset.attrs['Exposure'])]): # Converting t_min/t_max to indicies
                spectrum = spectrum - spectrum[0] # Subtract so first spectrum starts at 0
                spectrum = spectrum + (i*stack_offset) # Offset spectrum
                ax1.plot(self.x, spectrum, color = 'black') # Plot individual spectrum
        
            ### Adjust ticks & labels -> y-axis for time and intensity
            
            #### Intensity axis
            y_ticks = np.arange(0, spectrum.max(), np.round(spectrum.max()/10, -5)) # Intensity ticks (10 evenly spaced from 0 to max of top spectrum)
            ax1.set_yticks(y_ticks, y_ticks)
            ax1.set_ylabel('SERS Intensity (cts/mW/s)', fontsize='large', rotation = 270, labelpad = 30)
            ax1.yaxis.set_label_position('right')               
            ax1.yaxis.tick_right()
            
            #### Time axis -> only when not plotting CA
            if plot_echem == False or (plot_echem == True and self.echem_mode == 'CV'):
                timeax = ax1.secondary_yaxis('left') # Secondary axis for time
                timeax.set_ylabel('Time (s)', fontsize = 'large')
                timeax.set_ticks(y_ticks, np.round(np.linspace(t_min, t_max, len(y_ticks)))) # Time tick labels at same location as intensity ticks
            ax1.set_ylim(y_ticks.min(), y_ticks.max())
            
        plt.tight_layout()


#%% SERS_Powerseries class
        
class SERS_Powerseries():
    
    '''
    Object containing SERS powerseries
    Arg should be h5 group containing individual SERS timescans (each at diff laser power), 
    or list of timescans
    '''
    
    def __init__(self, *args, raman_excitation = 632.8, particle_name = 'Particle_', **kwargs):

        super().__init__(*args, raman_excitation = raman_excitation, **kwargs)

        self.particle_name = particle_name
    