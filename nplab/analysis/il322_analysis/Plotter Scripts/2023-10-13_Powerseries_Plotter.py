# -*- coding: utf-8 -*-
"""
Created on Wed Apr 26 18:32:45 2023

@author: il322

Plotter for M-TAPP-SMe kinetic powerseries from 2023-10-04_633nm_Powerseries_DF_Track_NPoM_MLAgg.h5
(samples:
     2023-07-31-b_Co-TAPP-SMe_80nm_NPoM
     2023-07-31_Co-TAPP-SMe_60nm_MLAgg_on_Glass_b)

"""

import gc
import numpy as np
import scipy as sp
from matplotlib import pyplot as plt
import matplotlib as mpl
import tkinter as tk
from tkinter import filedialog
import statistics
from scipy.stats import linregress
from scipy.interpolate import interp1d
from scipy.signal import find_peaks
from scipy.signal import find_peaks_cwt
from scipy.signal import savgol_filter
from pylab import *
import nplab
import h5py
import natsort
import os

from nplab.analysis.general_spec_tools import spectrum_tools as spt
from nplab.analysis.general_spec_tools import npom_sers_tools as nst
from nplab.analysis.general_spec_tools import agg_sers_tools as ast
from nplab.analysis.SERS_Fitting import Auto_Fit_Raman as afr
from nplab.analysis.il322_analysis import il322_calibrate_spectrum as cal
from nplab.analysis.il322_analysis import il322_SERS_tools as SERS
from nplab.analysis.il322_analysis import il322_DF_tools as df

#%% Load h5

my_h5 = h5py.File(r"C:\Users\il322\Desktop\Offline Data\2023-10-04_633nm_Powerseries_DF_Track_NPoM_MLAgg.h5")


#%% Spectral calibration

'''
New and improved
'''

# Spectral calibration

## Get default literature BPT spectrum & peaks
lit_spectrum, lit_wn = cal.process_default_lit_spectrum()

## Load BPT ref spectrum
#my_h5 = h5py.File(r"C:\Users\il322\Desktop\Offline Data\2023-09-18_Co-TAPP-SMe_80nm_NPoM_Track_DF_633nm_Powerseries.h5")
coarse_shift = 90 # coarse shift to ref spectrum
notch_range = [0+coarse_shift, 230+coarse_shift]
bpt_ref_633nm = my_h5['PT_lab']['BPT_633nm_0']
bpt_ref_633nm = SERS.SERS_Spectrum(bpt_ref_633nm)

## Convert to wn
bpt_ref_633nm.x = spt.wl_to_wn(bpt_ref_633nm.x, 632.8)
bpt_ref_633nm.x = bpt_ref_633nm.x + coarse_shift

## No notch spectrum (use this truncation for all spectra!)
bpt_ref_no_notch = bpt_ref_633nm
bpt_ref_no_notch.truncate(start_x = notch_range[1], end_x = None)

## Baseline, smooth, and normalize no notch ref for peak finding
bpt_ref_no_notch.y_baselined = bpt_ref_no_notch.y -  spt.baseline_als(y=bpt_ref_no_notch.y,lam=1e1,p=1e-4,niter=1000)
bpt_ref_no_notch.y_smooth = spt.butter_lowpass_filt_filt(bpt_ref_no_notch.y_baselined,
                                                        cutoff=2000,
                                                        fs = 10000,
                                                        order=2)
bpt_ref_no_notch.normalise(norm_y = bpt_ref_no_notch.y_smooth)

## Find BPT ref peaks
ref_wn = cal.find_ref_peaks(bpt_ref_no_notch, lit_spectrum = lit_spectrum, lit_wn = lit_wn, threshold = 0.05)

## Find calibrated wavenumbers
wn_cal = cal.calibrate_spectrum(bpt_ref_no_notch, ref_wn, lit_spectrum = lit_spectrum, lit_wn = lit_wn, linewidth = 1)
bpt_ref_no_notch.x = wn_cal


#%% Efficiency calibration

# White light efficiency calibration

## Load white scatter with 

white_ref = my_h5['PT_lab']['white_scatt_x5']
white_ref = SERS.SERS_Spectrum(white_ref.attrs['wavelengths'], white_ref[2], title = 'White Scatterer')

## Convert to wn
white_ref.x = spt.wl_to_wn(white_ref.x, 632.8)
white_ref.x = white_ref.x + coarse_shift

## Get white bkg (counts in notch region)
notch = SERS.SERS_Spectrum(white_ref.x[np.where(white_ref.x < (notch_range[1]-50))], white_ref.y[np.where(white_ref.x < (notch_range[1] - 50))], name = 'White Scatterer Notch') 
notch_cts = notch.y.mean()
notch.plot()

# ## Truncate out notch (same as BPT ref), assign wn_cal
white_ref.truncate(start_x = notch_range[1], end_x = None)


## Convert back to wl for efficiency calibration
white_ref.x = spt.wn_to_wl(white_ref.x, 632.8)

# Calculate R_setup
R_setup = cal.white_scatter_calibration(wl = white_ref.x,
                                              white_scatter = white_ref.y,
                                              white_bkg = notch_cts,
                                              plot = True,
                                              start_notch = notch_range[0]-40,
                                              end_notch = notch_range[1]-40)

## Get dark counts - skip for now as using powerseries
# dark_cts = my_h5['PT_lab']['whire_ref_x5']
# dark_cts = SERS.SERS_Spectrum(wn_cal_633, dark_cts[5], title = 'Dark Counts')
# # dark_cts.plot()
# plt.show()

# Test R_setup with BPT reference
''' Add this plotting part to function'''
plt.plot(bpt_ref_633nm.x, bpt_ref_633nm.y, color = (0.8,0.1,0.1,0.7), label = 'Raw spectrum')
plt.plot(bpt_ref_633nm.x, (bpt_ref_633nm.y)/R_setup, color = (0,0.6,0.2,0.5), label = 'Efficiency-corrected')
plt.legend(fontsize='x-small')
plt.show()


#%% Dark counts power series

particle = my_h5['PT_lab']


# Add all SERS spectra to powerseries list in order

keys = list(particle.keys())
keys = natsort.natsorted(keys)
powerseries = []
for key in keys:
    if 'Au_mirror' in key:
        powerseries.append(particle[key])
        
for i, spectrum in enumerate(powerseries):
    
    ## x-axis truncation, calibration
    spectrum = SERS.SERS_Spectrum(spectrum)
    spectrum.x = spt.wl_to_wn(spectrum.x, 632.8)
    spectrum.x = spectrum.x + coarse_shift
    spectrum.truncate(start_x = notch_range[1], end_x = None)
    spectrum.x = wn_cal
    spectrum.y = spt.remove_cosmic_rays(spectrum.y)
    powerseries[i] = spectrum
    
dark_powerseries = powerseries

#%% List of powers used, for colormaps

powers_list = []
colors_list = np.linspace(0,10,10)

for spectrum in dark_powerseries:
    powers_list.append(spectrum.laser_power)
    



#%% Plot single powerseries for single particle


particle = my_h5['ParticleScannerScan_3']['Particle_4']


# Add all SERS spectra to powerseries list in order

keys = list(particle.keys())
keys = natsort.natsorted(keys)
powerseries = []
for key in keys:
    if 'SERS' in key:
        powerseries.append(particle[key])


#

fig, ax = plt.subplots(1,1,figsize=[8,6])
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('SERS Intensity (a.u.)')

for i, spectrum in enumerate(powerseries):
    
    ## x-axis truncation, calibration
    spectrum = SERS.SERS_Spectrum(spectrum)
    spectrum.x = spt.wl_to_wn(spectrum.x, 632.8)
    spectrum.x = spectrum.x + coarse_shift
    spectrum.truncate(start_x = notch_range[1], end_x = None)
    spectrum.x = wn_cal
    spectrum.calibrate_intensity(R_setup = R_setup,
                                 dark_counts = dark_powerseries[i].y,
                                 exposure = spectrum.cycle_time)
    
    spectrum.y = spt.remove_cosmic_rays(spectrum.y)
    spectrum.truncate(1100, 1700)
    spectrum.y_baselined = spt.baseline_als(spectrum.y, 1e0, 1e-1, niter = 10)
    #baseline = np.polyfit(spectrum.x, spectrum.y, 1)
    #spectrum.y_baselined = spectrum.y - (spectrum.x * baseline[0] + baseline[1])
    spectrum.y_smooth = spt.butter_lowpass_filt_filt(spectrum.y_baselined,cutoff = 3000, fs = 20000, order = 2)
    
    spectrum.normalise(norm_y = spectrum.y_smooth)
    
    ## Plot
    my_cmap = plt.get_cmap('inferno')
    if i <= 10:
        j = i
    else:
        j = 20-i
    color = my_cmap(j/20)
    spectrum.plot(ax = ax, plot_y = spectrum.y_norm + i/10, title = 'Particle', linewidth = 1, color = color)
    #ax.set_xlim(600, 1700)

    powerseries[i] = spectrum
    
    
#%% Same as above but for each particle in multiple scans


scan_list = ['ParticleScannerScan_3']
min_power_before = []
min_power_after = []

# Loop over particles in particle scan        

for particle_scan in scan_list:
    particle_list = []
    particle_list = natsort.natsorted(list(my_h5[particle_scan].keys()))
    
    ## Loop over particles in particle scan
    for particle in particle_list:
        if 'Particle' not in particle:
            particle_list.remove(particle)
    
    
    # Loop over particles in particle scan
    
    for particle in particle_list:
        particle_name = str(particle_scan) + '_' + particle
        particle = my_h5[particle_scan][particle]
        

        ## Add all SERS spectra to powerseries list in order
        
        keys = list(particle.keys())
        keys = natsort.natsorted(keys)
        powerseries = []
        for key in keys:
            if 'SERS' in key:
                powerseries.append(particle[key])
        
        ## Plotting
        fig, ax = plt.subplots(1,1,figsize=[8,6])
        ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
        ax.set_ylabel('SERS Intensity (a.u.)')
        
        ## Loop over each spectrum in powerseries
        for i, spectrum in enumerate(powerseries):
            
            ### Process spectrum
            spectrum = SERS.SERS_Spectrum(spectrum)
            spectrum.x = spt.wl_to_wn(spectrum.x, 632.8)
            spectrum.x = spectrum.x + coarse_shift
            spectrum.truncate(start_x = notch_range[1], end_x = None)
            spectrum.x = wn_cal
            
            spectrum.calibrate_intensity(R_setup = R_setup,
                                         dark_counts = dark_powerseries[i].y,
                                         exposure = spectrum.cycle_time)
            
            spectrum.y = spt.remove_cosmic_rays(spectrum.y)
            spectrum.truncate(1100, 1700)
            spectrum.y_baselined = spt.baseline_als(spectrum.y, 1e0, 1e-1, niter = 10)
            #baseline = np.polyfit(spectrum.x, spectrum.y, 1)
            #spectrum.y_baselined = spectrum.y - (spectrum.x * baseline[0] + baseline[1])
            spectrum.y_smooth = spt.butter_lowpass_filt_filt(spectrum.y_baselined,cutoff = 2500, fs = 20000, order = 2)
            spectrum.normalise(norm_y = spectrum.y_smooth)
            
            if i == 0:
                min_power_before.append(spectrum.y_smooth)
            elif i == 18:
                min_power_after.append(spectrum.y_smooth)
            
            ### Plot
            my_cmap = plt.get_cmap('inferno')
            if i <= 10:
                j = i
            else:
                j = 20-i
            color = my_cmap(j/20)
            spectrum.plot(ax = ax, plot_y = spectrum.y_norm + i/10, title = particle_name, linewidth = 1, color = color, label = str(np.round(spectrum.laser_power, 4)) + 'mW')
            powerseries[i] = spectrum
    
        ax.legend(fontsize = 11, ncol = 4, loc = 'upper left')
        ax.set_ylim(0,4)
        save_dir = r'C:\Users\il322\Desktop\Offline Data\2023-10-04_NPoM\_'
        plt.savefig(save_dir + particle_name + '.svg', format = 'svg')
        plt.close(fig)
        print(particle_name)
        
#%%
fig, ax = plt.subplots(1,1,figsize=[8,6])
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('SERS Intensity (a.u.)')
x = spectrum.x        
avg_min_before = np.mean(min_power_before, axis = 0)
avg_min_after = np.mean(min_power_after, axis = 0)

avg_min_before = SERS.SERS_Spectrum(x, avg_min_before)
avg_min_after = SERS.SERS_Spectrum(x, avg_min_after)

avg_min_before.normalise()
avg_min_after.normalise()

ax.plot(x,avg_min_before.y_norm, label = 'min power before', color = 'blue')
ax.plot(x,avg_min_after.y_norm, label = 'min power after', color = 'purple')
ax.legend()

#%%
#%% Same as above but for each particle in multiple scans - MLAGG


scan_list = ['ParticleScannerScan_4']
min_power_before = []
min_power_after = []

# Loop over particles in particle scan        

for particle_scan in scan_list:
    particle_list = []
    particle_list = natsort.natsorted(list(my_h5[particle_scan].keys()))
    
    ## Loop over particles in particle scan
    for particle in particle_list:
        if 'Particle' not in particle:
            particle_list.remove(particle)
    
    
    # Loop over particles in particle scan
    
    for particle in particle_list:
        particle_name = str(particle_scan) + '_' + particle
        particle = my_h5[particle_scan][particle]
        

        ## Add all SERS spectra to powerseries list in order
        
        keys = list(particle.keys())
        keys = natsort.natsorted(keys)
        powerseries = []
        for key in keys:
            if 'SERS' in key:
                powerseries.append(particle[key])
        
        ## Plotting
        fig, ax = plt.subplots(1,1,figsize=[8,6])
        ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
        ax.set_ylabel('SERS Intensity (a.u.)')
        
        ## Loop over each spectrum in powerseries
        for i, spectrum in enumerate(powerseries):
            
            ### Process spectrum
            spectrum = SERS.SERS_Spectrum(spectrum)
            spectrum.x = spt.wl_to_wn(spectrum.x, 632.8)
            spectrum.x = spectrum.x + coarse_shift
            spectrum.truncate(start_x = notch_range[1], end_x = None)
            spectrum.x = wn_cal
            
            spectrum.calibrate_intensity(R_setup = R_setup,
                                         dark_counts = 0,
                                         exposure = spectrum.cycle_time)
            
            spectrum.y = spt.remove_cosmic_rays(spectrum.y)
            spectrum.truncate(1100, 1700)
            #spectrum.y_baselined = spt.baseline_als(spectrum.y, 1e0, 1e-1, niter = 100)
            baseline = np.polyfit(spectrum.x, spectrum.y, 1)
            spectrum.y_baselined = spectrum.y - (spectrum.x * baseline[0] + baseline[1])
            spectrum.y_smooth = spt.butter_lowpass_filt_filt(spectrum.y_baselined,cutoff = 4000, fs = 20000, order = 2)
            spectrum.normalise(norm_y = spectrum.y_smooth)
            
            if i == 0:
                min_power_before.append(spectrum.y_smooth)
            elif i == 18:
                min_power_after.append(spectrum.y_smooth)
            
            ### Plot
            my_cmap = plt.get_cmap('inferno')
            if i <= 10:
                j = i
            else:
                j = 20-i
            color = my_cmap(j/20)
            spectrum.plot(ax = ax, plot_y = spectrum.y_norm + i/10, title = particle_name, linewidth = 1, color = color, label = str(np.round(spectrum.laser_power, 4)) + 'mW')
            powerseries[i] = spectrum
    
        ax.legend(fontsize = 11, ncol = 4, loc = 'upper left')
        ax.set_ylim(0,4)
        save_dir = r'C:\Users\il322\Desktop\Offline Data\2023-10-04_MLAgg\_'
        plt.savefig(save_dir + particle_name + '.svg', format = 'svg')
        plt.close(fig)
        print(particle_name)
        
#%%
fig, ax = plt.subplots(1,1,figsize=[8,6])
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('SERS Intensity (a.u.)')
x = spectrum.x        
avg_min_before = np.mean(min_power_before, axis = 0)
avg_min_after = np.mean(min_power_after, axis = 0)

avg_min_before = SERS.SERS_Spectrum(x, avg_min_before)
avg_min_after = SERS.SERS_Spectrum(x, avg_min_after)

avg_min_before.normalise()
avg_min_after.normalise()

ax.plot(x,avg_min_before.y_norm, label = 'min power before', color = 'blue')
ax.plot(x,avg_min_after.y_norm, label = 'min power after', color = 'purple')
ax.legend()

