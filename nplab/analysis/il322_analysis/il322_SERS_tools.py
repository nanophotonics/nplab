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
from math import log10, floor
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from importlib import reload

from nplab.analysis.general_spec_tools import spectrum_tools as spt
from nplab.analysis.general_spec_tools import npom_sers_tools as nst


#%% E-Chem plotting functions - can be moved to their own script maybe


def plot_ca(ca_data, ax, t_min = None, t_max = None, t_offset = 0):

    '''
    Plot chronoamperometry data
    
    Parameters:
        ca_data
        ax: (mpl.ax) axis to be plotted on
        t_min: (float) Time minimum for plotting
        t_max: (float) Time maximum for plotting
        t_offset: (float = None) Time offset
    '''
    
    
    # Only use t_offset if > 0 (negative t_offset moves SERS intead)
    
    if t_offset < 0:
        t_offset = 0
    
    
    # Extract current (uA) and time (s)
    
    current = ca_data[:,1]*10**3
    time = ca_data[:,0]
    
    
    # Plot current v. time
    
    ax.plot(current, time - t_offset)
    ax.set_ylabel('Time (s)', fontsize='large')
    ax.set_xlabel('Current ($\mu$A)', fontsize='large')
    ax.set_ylim(t_min, t_max)


def plot_cv(cv_data, ax, t_min = None, t_max = None, t_offset = 0):
    
    '''
    Plot Cyclic Voltammetry data
    
    Parameters:
        cv_data
        attrs: h5 dataset attributes
        ax: (mpl.ax) axis to be plotted on
        t_min: (float) Time minimum for plotting
        t_max: (float) Time maximum for plotting
        t_offset: (float = None) Time offset
    '''
    
    
    # Only use t_offset if > 0 (negative t_offset moves SERS intead)
    
    if t_offset < 0:
        t_offset = 0

    
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
                exposure = self.exposure
            except:
                print('Error: Exposure not found')
                return
            
        self.y = (self.y - dark_counts) / (R_setup * laser_power * exposure)
        
        
    def normalise(self, norm_range = (0, 1), norm_y = None):
        
        '''
        Function for normalizing spectra in timescan
        
        Parameters:
            norm_range: (tuple = (0, 1)) Normalization range
            norm_y: (None) Which y to normalize (self.y_smooth, self.y_baselined, etc). Default is just self.y
        '''
        
        if norm_y is None:
            self.y_norm = self.y.copy()
        else:
            self.y_norm = norm_y.copy()
        self.y_norm = self.y_norm.astype('float64')
        
        ## Normalize
        self.y_norm = self.y_norm - self.y_norm.min()
        self.y_norm = (self.y_norm / self.y_norm.max()) * (norm_range[1] - norm_range[0])
        self.y_norm = self.y_norm + norm_range[0]
        
        
    def plot(self, ax = None, plot_y = None, title = None, **kwargs):
        
        '''
        Plotting function
        requires docstring
        '''
        
        if ax is None:
            fig, ax = plt.subplots(1,1,figsize=[8,6])
            ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
            ax.set_ylabel('SERS Intensity (a.u.)')
            
        if plot_y is None:
            y_plot = self.y.copy()
        else:
            y_plot = plot_y.copy()
            
        if title is None:
            ax.set_title(self.name)
        else:
            ax.set_title(title)
            
        ax.plot(self.x, y_plot, **kwargs)

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
                 spec_calibrated = False, intensity_calibrated = False, echem_mode = '', echem_data = None,
                 exposure = 1, **kwargs):

        super().__init__(*args, raman_excitation = raman_excitation, **kwargs)

        self.name = name
        self.spec_calibrated = spec_calibrated
        self.intensity_calibrated = intensity_calibrated
        self.echem_mode = echem_mode.upper()
        self.echem_data = echem_data
        
<<<<<<< Updated upstream
        try:
            self.exposure = np.round(self.dset.attrs['Exposure'], 4)
        except:
            exposure = input('Please specify exposure (s): ')
            self.exposure = float(exposure)
=======
        self.exposure = exposure  
        
        # try:
        #     self.exposure = np.round(self.dset.attrs['cycle_time'], 4)
        # except:
        #     try:
        #         self.exposure = np.round(self.dset.attrs['Exposure'], 4)
        #         print('Could not find cycle time - using "Exposure" attribute!')
        #     except:
        #         self.exposure = 1
        #         print('Could not find exposure - using 1s exposure!!!')
>>>>>>> Stashed changes
            
        self.t = np.round(self.t_raw * self.exposure, 4)    
        self.Y_raw = self.Y.copy()
    

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
                exposure = self.exposure
            except:
                print('Error: Exposure not found')
                return
            
        self.Y = (self.Y - dark_counts)
        if self.Y.min() < 0:
            self.Y -= self.Y.min()
        self.Y = self.Y / (R_setup * laser_power * exposure)
        self.Y = self.Y.astype('float64')
        self.y = np.average(self.Y, axis = 0)

    
    def extract_nanocavity(self, timescan_y = None, plot = False):
        
        '''
        Extracts a stable nanocavity spectrum from a timescan that contains flares or picocavities
        Calculates flat baseline value for each pixel (wln or wn) across a timescan
        The flat baseline value is the y-value (intensity) of the nanocavity at that x-value
        
        Parameters:
            timescan: (nst.Timescan class = self) - best if already x & y-calibrated
            timescan_y: (nst.Timescan.Y attribute = None): choose which y (Y_smooth, Y_raw, etc) to use. Default uses self.Y
            use_raw: (boolean = False) extracts nanocavity from Y_raw if True
            plot: (boolean) plots nanocavity spectrum
            
        Returns:
            nanocavity_spectrum: (SERS_Spectrum class) extracted nanocavity spectrum
        '''
        
        
        # Choose which self.Y attribute to use
        
        if timescan_y is None:
            timescan_y = self.Y.copy()
        else:
            timescan_y = timescan_y.copy()
        

        # Get flat baseline value of each pixel (x-value) across each scan of time scan
        
        pixel_baseline = np.zeros(len(self.x))
        for pixel in range(0,len(self.x)):
            pixel_baseline[pixel] = np.polyfit(self.t, timescan_y[:,pixel], 0)
        
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
    
    
    def normalise(self, norm_range = (0, 1), norm_individual = True,
                  t_min = None, t_max = None):
        
        '''
        Function for normalizing spectra in timescan
        
        Parameters:
            norm_range: (tuple = (0, 1)) Normalization range
            norm_individual: (boolean = True) If True, normalizes each spectrum in timescan individually to norm_range
                                              If False, normalizes the whole together timescan to norm_range
            t_min: (float = None) Time minimum for normalization
            t_max: (float = None) Time maximum for normalization
        '''
        
        self.Y_norm = self.Y.copy()
        self.Y_norm = self.Y_norm.astype('float64')
                
        if t_min is None:
            t_min = self.t.min()
            
        if t_max is None:
            t_max = self.t.max()        

        t_min_idx = int(t_min / self.exposure)
        t_max_idx = int(t_max / self.exposure)
        
        
        # Normalize each spectrum individually
        
        if norm_individual == True:
            
            ## Loop over each spectrum
            for i in range(t_min_idx, t_max_idx+1):
                
                self.Y_norm[i] = self.Y_norm[i] - self.Y_norm[i].min() + norm_range[0]
                self.Y_norm[i] = self.Y_norm[i] / np.max(self.Y_norm[i]) * (norm_range[1] - norm_range[0])
                self.Y_norm[i] = self.Y_norm[i] + norm_range[0]
  
    
        # Normalize the timescan as a whole
        
        else:
            
            self.Y_norm[t_min_idx : t_max_idx+1] = (self.Y_norm[t_min_idx : t_max_idx+1] - self.Y_norm[t_min_idx : t_max_idx+1].min())
            self.Y_norm[t_min_idx : t_max_idx+1] = (self.Y_norm[t_min_idx : t_max_idx+1] / self.Y_norm[t_min_idx : t_max_idx+1].max()) * (norm_range[1] - norm_range[0])
            self.Y_norm[t_min_idx : t_max_idx+1] = self.Y_norm[t_min_idx : t_max_idx+1] + norm_range[0]
        
            
    def plot_timescan(self, plot_type = 'cmap', plot_y = None, 
                      v_min = None, v_max = None,
                      x_min = None, x_max = None,
                      t_min = None, t_max = None, t_offset = 0,
                      cmap = 'inferno', avg_chunks = None, avg_color = 'white', 
                      stack_offset = None, stack_color = 'black', 
                      plot_echem = False, title = None, **kwargs):

        
        '''
        Function for plotting a single timescan, either as a colormap or as a stack of single spectra
        Can optionally plot echem data (a CV curve or chronoamperometry data) alongside timescan
        
        Parameters:
            plot_type: (string = 'cmap') Determines type of plot. 'cmap' for colormap or 'stack' for stack of single spectra
            plot_y: (None) which y you want to plot (self.Y, self.Y_norm, self.Y_smooth, etc)
            v_min: (float = None) Minimum value for colormap normalization
            v_max: (float = None) Maximum value for colormap normalization
            x_min: (float = None) x minimum for plotting
            x_max: (float = None) x maximum for plotting
            t_min: (float = None) Time minimum for plotting
            t_max: (float = None) Time maximum for plotting
            t_offset: (float = 0) Offset timescan in time axis so it matches echem data
            cmap: (string = 'inferno') Colormap for plotting
            avg_chunks: (int = None) Number of averages to calculate for average spectra in colormap
            avg_color: (string = 'white') Color for avergae chunk plotting on colormap
            stack_offset: (float = None) y-offset value for stacked spectra
            stack_color: (string = 'black') Color for stacked spectra
            plot_echem: (boolean = False) Choose if plotting echem alongside timescan. Must have specified echem data in class initialization
            title: (str = None) Title for plot. If None, tries to set automatically from sample & echem metadata
        '''
        
        assert plot_type == 'cmap' or plot_type == 'stack', 'Error: invalid plot type. Please specify either "cmap" or "stack"'
        
        if plot_y is None:
            Y_plot = self.Y.copy()
        else:
            Y_plot = plot_y.copy()
        
        
        # Set v, x, and t limits
        
        if v_min is None:
            v_min = Y_plot.min()
        
        if v_max is None:
            v_max = np.percentile(Y_plot, 99.5) # Take 95th percentile for v_max -> good for removing effect of cosmic rays on cmap
            
        if x_min is None:
            x_min = self.x.min()
            
        if x_max is None:
            x_max = self.x.max()
            
        if t_min is None:
            t_min = self.t.min()
            
        if t_max is None:
            t_max = self.t.max()
           
            
        # Managing t_offset
        
        if t_offset < 0:
            t_plot = self.t + t_offset
            t_max_idx = int(math.ceil((t_max - t_offset) / self.exposure)) + 1
            t_min_idx = int(math.ceil((t_min - t_offset) / self.exposure))
        else:
            t_plot = self.t
            t_max_idx = int(math.ceil((t_max) / self.exposure)) + 1
            
            t_min_idx = int(math.ceil((t_min) / self.exposure))

        Y_plot = Y_plot[t_min_idx : t_max_idx]
        t_plot = t_plot[t_min_idx : t_max_idx]
        
        print(t_plot)
        
        # Plot E-Chem
        
        if plot_echem == True:
            assert self.echem_mode == 'CA' or self.echem_mode == 'CV', 'Error: please specify E-Chem mode as either "CA" or "CV"'
            assert self.echem_data is not None, 'Error: No echem data provided'
                        
            ## Plot CA
            if self.echem_mode == 'CA':
                
                ### Define figure with 2 subplots - ax2 for echem & ax1 for timescan
                fig, (ax2, ax1) = plt.subplots(1, 2, figsize=[12,16], gridspec_kw={'width_ratios': [1, 3]}, sharey=False)
                plot_ca(ca_data = self.echem_data, ax = ax2, t_min = t_min, t_max = t_max, t_offset = t_offset)
            
                ### Set title
                try:
                    fig.suptitle('SERS Timescan + Chronoamperometry ' + str(self.dset.attrs['Level 1']) + 'V to ' + str(self.dset.attrs['Level 2']) + 'V\n' + self.dset.attrs['sample'] + '\n' + self.name, fontsize='x-large')
                except:
                    fig.suptitle('SERS Timescan + Chronomperometry\n' + self.dset.attrs['sample'] + '\n' + self.name, fontsize='x-large')


            ## Plot CV
            elif self.echem_mode == 'CV':
                
                ### Define figure with 2 subplots - ax2 for echem & ax1 for timescan
                fig, (ax2, ax1) = plt.subplots(1, 2, figsize=[12,16], gridspec_kw={'width_ratios': [1, 3]}, sharey=False)
                plot_cv(cv_data = self.echem_data, ax = ax2, t_min = t_min, t_max = t_max, t_offset = t_offset)
                
                ### Set time axis label
                ax1.set_ylabel(r'Time (s)', fontsize = 'large')
                
                ### Set title
                if title is None:
                    try:
                        fig.suptitle('SERS Timescan + Cyclic Voltammetry ' + str(self.dset.attrs['Vertex 1']) + 'V to ' + str(self.dset.attrs['Vertex 2']) + 'V\n' + self.dset.attrs['sample'] + '\n' + self.name, fontsize='x-large')
                    except:
                        fig.suptitle('SERS Timescan + Cyclic Voltammetry\n' + self.dset.attrs['sample'] + '\n' + self.name, fontsize='x-large')
                else:
                    fig.suptitle(title, fontsize = 'x-large')

        else:
            ## If not plotting e_chem, define figure with 1 subplots - ax1 for timescan, set axis label & title
            fig, (ax1) = plt.subplots(1, 1, figsize=[12,16])
            ax1.set_ylabel(r'Time (s)', fontsize = 'large')

            if title is None:
                try:
                    fig.suptitle('SERS Timescan\n' + self.dset.attrs['sample'] + '\n' + self.name, fontsize='x-large')
                except:
                    pass
            else:
                fig.suptitle(title, fontsize = 'x-large')
                
        
        # Plot SERS timescan
        
        ax1.set_xlabel(r'Raman shift (cm$^{-1}$)', fontsize='large')
        ax1.set_xlim(x_min, x_max)
        
        ## Plot as colormap
        if plot_type == 'cmap':    
            cmap = plt.get_cmap(cmap)
            pcm = ax1.pcolormesh(self.x, t_plot, Y_plot, vmin = v_min, vmax = v_max, cmap = cmap, rasterized = 'True')
            ax1.set_ylim(t_min, t_max)
            clb = fig.colorbar(pcm, ax=ax1)
            clb.set_label(label = 'SERS Intensity (cts/mW/s)', size = 'large', rotation = 270, labelpad=30)
            
            ### Plot average chunks
            if avg_chunks is not None:
                Y_arr = np.array_split(Y_plot, (avg_chunks)) # Split Y_plot into avg_chunks # of arrays
                time_inc = len(t_plot) * self.exposure/(avg_chunks)
                for n, Y_i in enumerate(Y_arr):
                    y_i = np.sum(Y_i, axis = 0)
                    y_i = y_i - y_i.min() # Normalize min to 0
                    y_i = y_i/y_i.max() * (len(Y_i)*self.exposure) # Normalize max to max time in chunk
                    y_i += n * time_inc # Shift by time
                    y_i += t_plot.min() # Shift to match min time
                    ## Squish avg chunk if it goes above plot
                    if y_i.max() > t_max: 
                        y_i *= (t_max/y_i.max()) 
                    ax1.plot(self.x, y_i, color = 'black', lw = 6) # Plot black border around avg spectrum
                    ax1.plot(self.x, y_i, color = avg_color, alpha = 0.85) # Plot avg spectrum
            
        ## Plot as stacked spectra
        elif plot_type == 'stack':
            
            ### Set stack offset
            if stack_offset is None:
                stack_offset = np.percentile(Y_plot, 5)

            ### Loop through individual spectra in given time range
            for i, spectrum in enumerate(Y_plot[int(t_min/self.exposure) : int(t_max/self.exposure)]): # Converting t_min/t_max to indicies
                spectrum = spectrum - spectrum[0] # Subtract so first spectrum starts at 0
                spectrum = spectrum + (i*stack_offset) # Offset spectrum
                ax1.plot(self.x, spectrum, color = 'black') # Plot individual spectrum
        
            ### Adjust ticks & labels -> y-axis for time and intensity
            
            #### Intensity axis
            y_ticks = np.arange(0, spectrum.max(), np.round(spectrum.max()/10, 1-int(floor(log10(abs(spectrum.max()))))))
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
        

#%% Testing
# h5_MLAgg = h5py.File(r'C:\Users\il322\Desktop\Offline Data\2023-03-17_M-TAPP-SMe_60nm-MLAgg\2023-04-20_Lab8_EChem_Co-TAPP-SMe_60nm_MLAgg.h5')
# timescan = SERS_Timescan(h5_MLAgg['Co-TAPP-SMe_60nm_MLAgg_on_Au_1']['633nm_CA-0to-1.2V_20cycles_0.1sx800scans'], name = 'MLAgg')
# ca_data = np.loadtxt(r'C:\Users\il322\Desktop\Offline Data\2023-03-17_M-TAPP-SMe_60nm-MLAgg\2023-03-17_Co-TAPP-SMe_60nm_MLAgg_on_SAM_on_Au\ca_-1.2.txt',
#                       skiprows=1)

# ## Plot
# timescan.echem_data = ca_data
# timescan.echem_mode = 'CA'

# timescan.plot_timescan(t_min = 0, t_max = 10, t_offset = -1,  v_min = 300, v_max = np.percentile(timescan.Y, 99) + 500, plot_echem = True, plot_type='stack', stack_offset = np.percentile(timescan.Y, 1), avg_chunks = 10)

