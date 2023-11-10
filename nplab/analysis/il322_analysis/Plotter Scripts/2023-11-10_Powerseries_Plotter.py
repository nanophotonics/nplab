# -*- coding: utf-8 -*-
"""
Created on Wed Apr 26 18:32:45 2023

@author: il322

Plotter for M-TAPP-SMe single scan 633nm powerseries from 2023-10-21_633nm_Powerseries_Track_NPoM_MLAgg.h5 & 2023-10-30_633nm_Powerseries_20x_MLAgg.h5

'Back to min' powerseries- plots min power spectra after each new power in powerseries, and averages (trying to find damage threshold)


(samples:
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

'''
First data file - 100x
'''


my_h5 = h5py.File(r"C:\Users\ishaa\OneDrive\Desktop\Offline Data\2023-10-21_633nm_Powerseries_Track_NPoM_MLAgg.h5")


#%% Spectral calibration

# Spectral calibration

## Get default literature BPT spectrum & peaks
lit_spectrum, lit_wn = cal.process_default_lit_spectrum()

## Load BPT ref spectrum
#my_h5 = h5py.File(r"C:\Users\il322\Desktop\Offline Data\2023-09-18_Co-TAPP-SMe_80nm_NPoM_Track_DF_633nm_Powerseries.h5")
coarse_shift = 60 # coarse shift to ref spectrum
notch_range = [0+coarse_shift, 210+coarse_shift]
bpt_ref_633nm = my_h5['PT_lab']['BPT_633nm']
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

white_ref = my_h5['PT_lab']['white_ref_x5']
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


#%% Dark counts power series - MLAgg

particle = my_h5['PT_lab']


# Add all SERS spectra to powerseries list in order

keys = list(particle.keys())
keys = natsort.natsorted(keys)
powerseries = []
for key in keys:
    if 'Glass_dark' in key:
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


# List of powers used, for colormaps

powers_list = []
colors_list = np.linspace(0,10,10)

for spectrum in dark_powerseries:
    powers_list.append(spectrum.laser_power)
    

# Add jump back to min powers to dark powerseries

dark_powerseries = np.insert(dark_powerseries, np.linspace(2,len(dark_powerseries),9).astype(int), dark_powerseries[0])
for spec in dark_powerseries:
    print(spec.laser_power)


#%% Plot single powerseries for single MLAgg spot

'''
Just plotting un-smoothed lowest power spectra to find damage threshold
''' 


particle = my_h5['ParticleScannerScan_1']['Particle_4']


# Add all SERS spectra to powerseries list in order

keys = list(particle.keys())
keys = natsort.natsorted(keys)
powerseries = []

for key in keys:
    if 'SERS' in key:
        powerseries.append(particle[key])


fig, ax = plt.subplots(1,1,figsize=[12,9])
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('SERS Intensity (cts/mW/s)')

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
    #spectrum.truncate(1100, 1700)
    spectrum.y_baselined = spt.baseline_als(spectrum.y, 1e0, 1e-1, niter = 10)
    #baseline = np.polyfit(spectrum.x, spectrum.y, 1)
    #spectrum.y_baselined = spectrum.y - (spectrum.x * baseline[0] + baseline[1])
    #spectrum.y_smooth = spt.butter_lowpass_filt_filt(spectrum.y_baselined,cutoff = 3000, fs = 20000, order = 2)
    #spectrum.normalise(norm_y = spectrum.y)
    
    ## Color = color of previous power in powerseries
    my_cmap = plt.get_cmap('inferno')
    color = my_cmap(i/20)
    if i == 0:
        spectrum.plot(ax = ax, plot_y = spectrum.y, title = '633nm Powerseries - 500nW Spectra', linewidth = 1, color = color, label = 0.0)
    elif spectrum.laser_power < 0.0006:
        spectrum.plot(ax = ax, plot_y = spectrum.y, title = '633nm Powerseries - 500nW Spectra', linewidth = 1, color = color, label = powerseries[i-1].laser_power * 1000)

    ## Labeling & plotting
    ax.legend(fontsize = 18, ncol = 5, loc = 'upper center')
    ax.get_legend().set_title('Previous laser power ($\mu$W)')
    for line in ax.get_legend().get_lines():
        line.set_linewidth(4.0)
    fig.suptitle('MLAgg')
    powerseries[i] = spectrum
    
    ax.set_xlim(250, 1900)
    ax.set_ylim(0, powerseries[0].y.max() * 1.4)
    plt.tight_layout(pad = 0.8)
    
    
#%% Same as above but for each MLAgg spot across scan

'''
Just plotting normalized un-smoothed lowest power spectra to find damage threshold

Take average of un-smoothed lowest power spectra across all MLAgg spots
''' 

scan_list = ['ParticleScannerScan_1']
avg_powerseries = np.zeros([19, len(spectrum.y)])

# Loop over particles in particle scan        

for particle_scan in scan_list:
    particle_list = []
    particle_list = natsort.natsorted(list(my_h5[particle_scan].keys()))
    
    ## Loop over particles in particle scan
    for particle in particle_list:
        if 'Particle' not in particle:
            particle_list.remove(particle)
    
    particle_list.remove('Particle_25')
    
    # Loop over particles in particle scan
    
    for particle in particle_list:
        particle_name = 'MLAgg_' + str(particle_scan) + '_' + particle
        particle = my_h5[particle_scan][particle]
        

        ## Add all SERS spectra to powerseries list in order
        
        keys = list(particle.keys())
        keys = natsort.natsorted(keys)
        powerseries = []

        for key in keys:
            if 'SERS' in key:
                powerseries.append(particle[key])

        ## Plot un-smoothed lowest power spectra only
        fig, ax = plt.subplots(1,1,figsize=[12,9])
        ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
        ax.set_ylabel('SERS Intensity (cts/mW/s)')

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
            #spectrum.truncate(1100, 1700)
            #spectrum.y_baselined = spt.baseline_als(spectrum.y, 1e0, 1e-1, niter = 10)
            #baseline = np.polyfit(spectrum.x, spectrum.y, 1)
            #spectrum.y_baselined = spectrum.y - (spectrum.x * baseline[0] + baseline[1])
            #spectrum.y_smooth = spt.butter_lowpass_filt_filt(spectrum.y_baselined,cutoff = 3000, fs = 20000, order = 2)
            spectrum.normalise(norm_y = spectrum.y)
            
            ## Color = color of previous power in powerseries, add to avg_powerseries
            my_cmap = plt.get_cmap('inferno')
            color = my_cmap(i/20)
            offset = 0.03
            if i == 0:
                spectrum.plot(ax = ax, plot_y = spectrum.y_norm, title = '633nm Powerseries - 500nW Spectra - 100x MLAgg', linewidth = 1, color = color, label = 0.0)
                avg_powerseries[i] += (spectrum.y_norm)
            elif spectrum.laser_power < 0.0006:
                spectrum.plot(ax = ax, plot_y = spectrum.y_norm + (i*offset), title = '633nm Powerseries - 500nW Spectra - 100x MLAgg', linewidth = 1, color = color, label = powerseries[i-1].laser_power * 1000)
                avg_powerseries[i] += (spectrum.y_norm)

            ## Label & plot
            ax.legend(fontsize = 18, ncol = 5, loc = 'upper center')
            ax.get_legend().set_title('Previous laser power ($\mu$W)')
            for line in ax.get_legend().get_lines():
                line.set_linewidth(4.0)
            fig.suptitle(particle_name)
            powerseries[i] = spectrum
            ax.set_xlim(250, 1900)
            ax.set_ylim(0, 2)
            ax.set_ylabel('Normalized SERS Intensity (a.u.)')
            plt.tight_layout(pad = 0.8)


        # save_dir = r'C:\Users\ishaa\OneDrive\Desktop\Offline Data\2023-10-21_MLAgg\Normalized\_'
        # plt.savefig(save_dir + particle_name + '.svg', format = 'svg')
        # plt.close(fig)
        print(particle_name)
        
## Calculate average
for i in range(0, len(avg_powerseries)):
    avg_powerseries[i] = avg_powerseries[i]/len(particle_list)
        
#%% Plot min power spectrum powerseries avg across MLAgg spots


# Plotting

fig, ax = plt.subplots(1,1,figsize=[12,9])
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('SERS Intensity (cts/mW/s)')
x = spectrum.x        

for i in range(0, len(avg_powerseries)):
    
    ## Color = color of previous power in powerseries
    my_cmap = plt.get_cmap('inferno')
    color = my_cmap(i/20)
    offset = 0.03
    if i == 0:
        ax.plot(x, avg_powerseries[i], linewidth = 1, color = color, label = 0.0)
    elif i % 2 == 0:
        ax.plot(x, avg_powerseries[i] + (i*offset), linewidth = 1, color = color, label = powerseries[i-1].laser_power * 1000)

## Label & plot
ax.legend(fontsize = 18, ncol = 5, loc = 'upper center')
ax.get_legend().set_title('Previous laser power ($\mu$W)')
for line in ax.get_legend().get_lines():
    line.set_linewidth(4.0)
fig.suptitle('633nm Powerseries - 500nW Spectra - 100x MLAgg Average')
ax.set_xlim(250, 1900)
ax.set_ylim(0, 2)
ax.set_ylabel('Normalized SERS Intensity (a.u.)')
plt.tight_layout(pad = 0.8)

# plt.savefig(save_dir + 'MLAgg Avg' + '.svg', format = 'svg')
# plt.close(fig)



#%% Plot powerseries spectra without mins

'''
Just plotting normalized un-smoothed powerseries
''' 


particle = my_h5['ParticleScannerScan_1']['Particle_4']


# Add all SERS spectra to powerseries list in order

keys = list(particle.keys())
keys = natsort.natsorted(keys)
powerseries = []

for key in keys:
    if 'SERS' in key:
        powerseries.append(particle[key])


fig, ax = plt.subplots(1,1,figsize=[12,9])
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('SERS Intensity (cts/mW/s)')

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
    #spectrum.truncate(1100, 1700)
    spectrum.y_baselined = spt.baseline_als(spectrum.y, 1e0, 1e-1, niter = 10)
    #baseline = np.polyfit(spectrum.x, spectrum.y, 1)
    #spectrum.y_baselined = spectrum.y - (spectrum.x * baseline[0] + baseline[1])
    #spectrum.y_smooth = spt.butter_lowpass_filt_filt(spectrum.y_baselined,cutoff = 3000, fs = 20000, order = 2)
    spectrum.normalise(norm_y = spectrum.y)
    
    ## Color = color of previous power in powerseries
    my_cmap = plt.get_cmap('inferno')
    color = my_cmap(i/20)
    offset = 0.03
    if i == 0:
        spectrum.plot(ax = ax, plot_y = spectrum.y_norm, title = '633nm Powerseries - 100x MLAgg', linewidth = 1, color = color, label = 0)
    elif spectrum.laser_power >= 0.0006:
        spectrum.plot(ax = ax, plot_y = spectrum.y_norm + (i*offset), title = '633nm Powerseries - 100x MLAgg', linewidth = 1, color = color, label = spectrum.laser_power * 1000)

    ## Labeling & plotting
    ax.legend(fontsize = 18, ncol = 5, loc = 'upper center')
    ax.get_legend().set_title('Laser power ($\mu$W)')
    for line in ax.get_legend().get_lines():
        line.set_linewidth(4.0)
    fig.suptitle('MLAgg')
    powerseries[i] = spectrum
    
    ax.set_xlim(250, 1900)
    ax.set_ylim(0, 2)
    plt.tight_layout(pad = 0.8)


#%% Same as above but for each MLAgg spot across scan

'''
Just plotting normalized un-smoothed powerseries

Take average of un-smoothed powerseries across all MLAgg spots
''' 

scan_list = ['ParticleScannerScan_1']
avg_powerseries = np.zeros([19, len(spectrum.y)])

# Loop over particles in particle scan        

for particle_scan in scan_list:
    particle_list = []
    particle_list = natsort.natsorted(list(my_h5[particle_scan].keys()))
    
    ## Loop over particles in particle scan
    for particle in particle_list:
        if 'Particle' not in particle:
            particle_list.remove(particle)
    
    particle_list.remove('Particle_25')
    
    # Loop over particles in particle scan
    
    for particle in particle_list:
        particle_name = 'MLAgg_' + str(particle_scan) + '_' + particle
        particle = my_h5[particle_scan][particle]
        

        ## Add all SERS spectra to powerseries list in order
        
        keys = list(particle.keys())
        keys = natsort.natsorted(keys)
        powerseries = []

        for key in keys:
            if 'SERS' in key:
                powerseries.append(particle[key])

        ## Plot un-smoothed lowest power spectra only
        fig, ax = plt.subplots(1,1,figsize=[12,9])
        ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
        ax.set_ylabel('Normalized SERS Intensity (a.u.)')

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
            #spectrum.truncate(1100, 1700)
            #spectrum.y_baselined = spt.baseline_als(spectrum.y, 1e0, 1e-1, niter = 10)
            #baseline = np.polyfit(spectrum.x, spectrum.y, 1)
            #spectrum.y_baselined = spectrum.y - (spectrum.x * baseline[0] + baseline[1])
            #spectrum.y_smooth = spt.butter_lowpass_filt_filt(spectrum.y_baselined,cutoff = 3000, fs = 20000, order = 2)
            spectrum.normalise(norm_y = spectrum.y)
            
            ## Color = color of previous power in powerseries, add to avg_powerseries
            my_cmap = plt.get_cmap('inferno')
            color = my_cmap(i/20)
            offset = 0.03
            if i == 0:
                spectrum.plot(ax = ax, plot_y = spectrum.y_norm, title = '633nm Powerseries - 100x MLAgg', linewidth = 1, color = color, label = spectrum.laser_power * 1000)
                avg_powerseries[i] += (spectrum.y_norm)
            elif spectrum.laser_power >= 0.0006:
                spectrum.plot(ax = ax, plot_y = spectrum.y_norm + (i*offset), title = '633nm Powerseries - 100x MLAgg', linewidth = 1, color = color, label = spectrum.laser_power * 1000)
                avg_powerseries[i] += (spectrum.y_norm)

            ## Label & plot
            ax.legend(fontsize = 18, ncol = 5, loc = 'upper center')
            ax.get_legend().set_title('Laser power ($\mu$W)')
            for line in ax.get_legend().get_lines():
                line.set_linewidth(4.0)
            fig.suptitle(particle_name)
            powerseries[i] = spectrum
            ax.set_xlim(250, 1900)
            ax.set_ylim(0, 2)
            ax.set_ylabel('Normalized SERS Intensity (a.u.)')
            plt.tight_layout(pad = 0.8)


        # save_dir = r'C:\Users\ishaa\OneDrive\Desktop\Offline Data\2023-10-21_MLAgg\100x\Direct Powerseries Normalized\_'
        # plt.savefig(save_dir + particle_name + '.svg', format = 'svg')
        # plt.close(fig)
        print(particle_name)
        
## Calculate average
for i in range(0, len(avg_powerseries)):
    avg_powerseries[i] = avg_powerseries[i]/len(particle_list)

#%% Plot min power spectrum powerseries avg across MLAgg spots


# Plotting

fig, ax = plt.subplots(1,1,figsize=[12,9])
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('Normalized SERS Intensity (a.u.)')
x = spectrum.x        

for i in range(0, len(avg_powerseries)):
    
    ## Color = color of previous power in powerseries
    my_cmap = plt.get_cmap('inferno')
    color = my_cmap(i/20)
    offset = 0.03
    if i == 0:
        ax.plot(x, avg_powerseries[i], linewidth = 1, color = color, label = powerseries[i].laser_power * 1000)
    elif i % 2 != 0:
        ax.plot(x, avg_powerseries[i] + (i*offset), linewidth = 1, color = color, label = powerseries[i].laser_power * 1000)

## Label & plot
ax.legend(fontsize = 18, ncol = 5, loc = 'upper center')
ax.get_legend().set_title('Laser power ($\mu$W)')
for line in ax.get_legend().get_lines():
    line.set_linewidth(4.0)
fig.suptitle('633nm Powerseries - 100x MLAgg Average')
ax.set_xlim(250, 1900)
ax.set_ylim(0, 2)
plt.tight_layout(pad = 0.8)

# plt.savefig(save_dir + 'MLAgg Avg' + '.svg', format = 'svg')
# plt.close(fig)


#%%

'''
Now for 20x data file
'''

my_h5 = h5py.File(r"C:\Users\ishaa\OneDrive\Desktop\Offline Data\2023-10-30_633nm_Powerseries_20x_MLAgg.h5")


#%% Spectral calibration

# Spectral calibration

## Get default literature BPT spectrum & peaks
lit_spectrum, lit_wn = cal.process_default_lit_spectrum()

## Load BPT ref spectrum
#my_h5 = h5py.File(r"C:\Users\il322\Desktop\Offline Data\2023-09-18_Co-TAPP-SMe_80nm_NPoM_Track_DF_633nm_Powerseries.h5")
coarse_shift = 60 # coarse shift to ref spectrum
notch_range = [0+coarse_shift, 210+coarse_shift]
bpt_ref_633nm = my_h5['PT_lab']['BPT_ref']
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
ref_wn = cal.find_ref_peaks(bpt_ref_no_notch, lit_spectrum = lit_spectrum, lit_wn = lit_wn, threshold = 0.06)

## Find calibrated wavenumbers
wn_cal = cal.calibrate_spectrum(bpt_ref_no_notch, ref_wn, lit_spectrum = lit_spectrum, lit_wn = lit_wn, linewidth = 1)
bpt_ref_no_notch.x = wn_cal


#%% Efficiency calibration

# White light efficiency calibration

## Load white scatter with 

white_ref = my_h5['PT_lab']['white_ref_x5']
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


#%% Dark counts power series - MLAgg

particle = my_h5['PT_lab']


# Add all SERS spectra to powerseries list in order

keys = list(particle.keys())
keys = natsort.natsorted(keys)
powerseries = []
for key in keys:
    if 'glass_dark_2' in key:
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


# List of powers used, for colormaps

powers_list = []
colors_list = np.linspace(0,10,10)

for spectrum in dark_powerseries:
    powers_list.append(spectrum.laser_power)
    

# Add jump back to min powers to dark powerseries

dark_powerseries = np.insert(dark_powerseries, np.linspace(2,len(dark_powerseries),9).astype(int), dark_powerseries[0])
for spec in dark_powerseries:
    print(spec.laser_power)


#%% Plot single powerseries for single MLAgg spot

'''
Just plotting un-smoothed lowest power spectra to find damage threshold
''' 


particle = my_h5['ParticleScannerScan_1']['Particle_4']


# Add all SERS spectra to powerseries list in order

keys = list(particle.keys())
keys = natsort.natsorted(keys)
powerseries = []

for key in keys:
    if 'SERS' in key:
        powerseries.append(particle[key])


fig, ax = plt.subplots(1,1,figsize=[12,9])
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('SERS Intensity (cts/mW/s)')

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
    #spectrum.truncate(1100, 1700)
    spectrum.y_baselined = spt.baseline_als(spectrum.y, 1e0, 1e-1, niter = 10)
    #baseline = np.polyfit(spectrum.x, spectrum.y, 1)
    #spectrum.y_baselined = spectrum.y - (spectrum.x * baseline[0] + baseline[1])
    #spectrum.y_smooth = spt.butter_lowpass_filt_filt(spectrum.y_baselined,cutoff = 3000, fs = 20000, order = 2)
    #spectrum.normalise(norm_y = spectrum.y)
    
    ## Color = color of previous power in powerseries
    my_cmap = plt.get_cmap('inferno')
    color = my_cmap(i/20)
    if i == 0:
        spectrum.plot(ax = ax, plot_y = spectrum.y, title = '633nm Powerseries - 500nW Spectra', linewidth = 1, color = color, label = 0.0)
    elif spectrum.laser_power < 0.0006:
        spectrum.plot(ax = ax, plot_y = spectrum.y, title = '633nm Powerseries - 500nW Spectra', linewidth = 1, color = color, label = powerseries[i-1].laser_power * 1000)

    ## Labeling & plotting
    ax.legend(fontsize = 18, ncol = 5, loc = 'upper center')
    ax.get_legend().set_title('Previous laser power ($\mu$W)')
    for line in ax.get_legend().get_lines():
        line.set_linewidth(4.0)
    fig.suptitle('MLAgg')
    powerseries[i] = spectrum
    
    ax.set_xlim(250, 1900)
    ax.set_ylim(0, powerseries[0].y.max() * 1.4)
    plt.tight_layout(pad = 0.8)
    
    
#%% Same as above but for each MLAgg spot across scan

'''
Just plotting normalized un-smoothed lowest power spectra to find damage threshold

Take average of un-smoothed lowest power spectra across all MLAgg spots
''' 

scan_list = ['ParticleScannerScan_1']
avg_powerseries = np.zeros([19, len(spectrum.y)])

# Loop over particles in particle scan        

for particle_scan in scan_list:
    particle_list = []
    particle_list = natsort.natsorted(list(my_h5[particle_scan].keys()))
    
    ## Loop over particles in particle scan
    for particle in particle_list:
        if 'Particle' not in particle:
            particle_list.remove(particle)
    
    particle_list.remove('Particle_25')
    
    # Loop over particles in particle scan
    
    for particle in particle_list:
        particle_name = 'MLAgg_' + str(particle_scan) + '_' + particle
        particle = my_h5[particle_scan][particle]
        

        ## Add all SERS spectra to powerseries list in order
        
        keys = list(particle.keys())
        keys = natsort.natsorted(keys)
        powerseries = []

        for key in keys:
            if 'SERS' in key:
                powerseries.append(particle[key])

        ## Plot un-smoothed lowest power spectra only
        fig, ax = plt.subplots(1,1,figsize=[12,9])
        ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
        ax.set_ylabel('SERS Intensity (cts/mW/s)')

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
            #spectrum.truncate(1100, 1700)
            #spectrum.y_baselined = spt.baseline_als(spectrum.y, 1e0, 1e-1, niter = 10)
            #baseline = np.polyfit(spectrum.x, spectrum.y, 1)
            #spectrum.y_baselined = spectrum.y - (spectrum.x * baseline[0] + baseline[1])
            #spectrum.y_smooth = spt.butter_lowpass_filt_filt(spectrum.y_baselined,cutoff = 3000, fs = 20000, order = 2)
            spectrum.normalise(norm_y = spectrum.y)
            
            ## Color = color of previous power in powerseries, add to avg_powerseries
            my_cmap = plt.get_cmap('inferno')
            color = my_cmap(i/20)
            offset = 0.03
            if i == 0:
                spectrum.plot(ax = ax, plot_y = spectrum.y_norm, title = '633nm Powerseries - 500nW Spectra - 100x MLAgg', linewidth = 1, color = color, label = 0.0)
                avg_powerseries[i] += (spectrum.y_norm)
            elif spectrum.laser_power < 0.0006:
                spectrum.plot(ax = ax, plot_y = spectrum.y_norm + (i*offset), title = '633nm Powerseries - 500nW Spectra - 100x MLAgg', linewidth = 1, color = color, label = powerseries[i-1].laser_power * 1000)
                avg_powerseries[i] += (spectrum.y_norm)

            ## Label & plot
            ax.legend(fontsize = 18, ncol = 5, loc = 'upper center')
            ax.get_legend().set_title('Previous laser power ($\mu$W)')
            for line in ax.get_legend().get_lines():
                line.set_linewidth(4.0)
            fig.suptitle(particle_name)
            powerseries[i] = spectrum
            ax.set_xlim(250, 1900)
            ax.set_ylim(0, 2)
            ax.set_ylabel('Normalized SERS Intensity (a.u.)')
            plt.tight_layout(pad = 0.8)


        # save_dir = r'C:\Users\ishaa\OneDrive\Desktop\Offline Data\2023-10-21_MLAgg\Normalized\_'
        # plt.savefig(save_dir + particle_name + '.svg', format = 'svg')
        # plt.close(fig)
        print(particle_name)
        
## Calculate average
for i in range(0, len(avg_powerseries)):
    avg_powerseries[i] = avg_powerseries[i]/len(particle_list)
        
#%% Plot min power spectrum powerseries avg across MLAgg spots


# Plotting

fig, ax = plt.subplots(1,1,figsize=[12,9])
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('SERS Intensity (cts/mW/s)')
x = spectrum.x        

for i in range(0, len(avg_powerseries)):
    
    ## Color = color of previous power in powerseries
    my_cmap = plt.get_cmap('inferno')
    color = my_cmap(i/20)
    offset = 0.03
    if i == 0:
        ax.plot(x, avg_powerseries[i], linewidth = 1, color = color, label = 0.0)
    elif i % 2 == 0:
        ax.plot(x, avg_powerseries[i] + (i*offset), linewidth = 1, color = color, label = powerseries[i-1].laser_power * 1000)

## Label & plot
ax.legend(fontsize = 18, ncol = 5, loc = 'upper center')
ax.get_legend().set_title('Previous laser power ($\mu$W)')
for line in ax.get_legend().get_lines():
    line.set_linewidth(4.0)
fig.suptitle('633nm Powerseries - 500nW Spectra - 100x MLAgg Average')
ax.set_xlim(250, 1900)
ax.set_ylim(0, 2)
ax.set_ylabel('Normalized SERS Intensity (a.u.)')
plt.tight_layout(pad = 0.8)

# plt.savefig(save_dir + 'MLAgg Avg' + '.svg', format = 'svg')
# plt.close(fig)



#%% Plot powerseries spectra without mins

'''
Just plotting normalized un-smoothed powerseries
''' 


particle = my_h5['ParticleScannerScan_1']['Particle_4']


# Add all SERS spectra to powerseries list in order

keys = list(particle.keys())
keys = natsort.natsorted(keys)
powerseries = []

for key in keys:
    if 'SERS' in key:
        powerseries.append(particle[key])


fig, ax = plt.subplots(1,1,figsize=[12,9])
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('SERS Intensity (cts/mW/s)')

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
    #spectrum.truncate(1100, 1700)
    spectrum.y_baselined = spt.baseline_als(spectrum.y, 1e0, 1e-1, niter = 10)
    #baseline = np.polyfit(spectrum.x, spectrum.y, 1)
    #spectrum.y_baselined = spectrum.y - (spectrum.x * baseline[0] + baseline[1])
    #spectrum.y_smooth = spt.butter_lowpass_filt_filt(spectrum.y_baselined,cutoff = 3000, fs = 20000, order = 2)
    spectrum.normalise(norm_y = spectrum.y)
    
    ## Color = color of previous power in powerseries
    my_cmap = plt.get_cmap('inferno')
    color = my_cmap(i/20)
    offset = 0.03
    if i == 0:
        spectrum.plot(ax = ax, plot_y = spectrum.y_norm, title = '633nm Powerseries - 100x MLAgg', linewidth = 1, color = color, label = 0)
    elif spectrum.laser_power >= 0.0006:
        spectrum.plot(ax = ax, plot_y = spectrum.y_norm + (i*offset), title = '633nm Powerseries - 100x MLAgg', linewidth = 1, color = color, label = spectrum.laser_power * 1000)

    ## Labeling & plotting
    ax.legend(fontsize = 18, ncol = 5, loc = 'upper center')
    ax.get_legend().set_title('Laser power ($\mu$W)')
    for line in ax.get_legend().get_lines():
        line.set_linewidth(4.0)
    fig.suptitle('MLAgg')
    powerseries[i] = spectrum
    
    ax.set_xlim(250, 1900)
    ax.set_ylim(0, 2)
    plt.tight_layout(pad = 0.8)


#%% Same as above but for each MLAgg spot across scan

'''
Just plotting normalized un-smoothed powerseries

Take average of un-smoothed powerseries across all MLAgg spots
''' 

scan_list = ['ParticleScannerScan_1']
avg_powerseries = np.zeros([19, len(spectrum.y)])

# Loop over particles in particle scan        

for particle_scan in scan_list:
    particle_list = []
    particle_list = natsort.natsorted(list(my_h5[particle_scan].keys()))
    
    ## Loop over particles in particle scan
    for particle in particle_list:
        if 'Particle' not in particle:
            particle_list.remove(particle)
    
    particle_list.remove('Particle_25')
    
    # Loop over particles in particle scan
    
    for particle in particle_list:
        particle_name = 'MLAgg_' + str(particle_scan) + '_' + particle
        particle = my_h5[particle_scan][particle]
        

        ## Add all SERS spectra to powerseries list in order
        
        keys = list(particle.keys())
        keys = natsort.natsorted(keys)
        powerseries = []

        for key in keys:
            if 'SERS' in key:
                powerseries.append(particle[key])

        ## Plot un-smoothed lowest power spectra only
        fig, ax = plt.subplots(1,1,figsize=[12,9])
        ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
        ax.set_ylabel('Normalized SERS Intensity (a.u.)')

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
            #spectrum.truncate(1100, 1700)
            #spectrum.y_baselined = spt.baseline_als(spectrum.y, 1e0, 1e-1, niter = 10)
            #baseline = np.polyfit(spectrum.x, spectrum.y, 1)
            #spectrum.y_baselined = spectrum.y - (spectrum.x * baseline[0] + baseline[1])
            #spectrum.y_smooth = spt.butter_lowpass_filt_filt(spectrum.y_baselined,cutoff = 3000, fs = 20000, order = 2)
            spectrum.normalise(norm_y = spectrum.y)
            
            ## Color = color of previous power in powerseries, add to avg_powerseries
            my_cmap = plt.get_cmap('inferno')
            color = my_cmap(i/20)
            offset = 0.03
            if i == 0:
                spectrum.plot(ax = ax, plot_y = spectrum.y_norm, title = '633nm Powerseries - 100x MLAgg', linewidth = 1, color = color, label = spectrum.laser_power * 1000)
                avg_powerseries[i] += (spectrum.y_norm)
            elif spectrum.laser_power >= 0.0006:
                spectrum.plot(ax = ax, plot_y = spectrum.y_norm + (i*offset), title = '633nm Powerseries - 100x MLAgg', linewidth = 1, color = color, label = spectrum.laser_power * 1000)
                avg_powerseries[i] += (spectrum.y_norm)

            ## Label & plot
            ax.legend(fontsize = 18, ncol = 5, loc = 'upper center')
            ax.get_legend().set_title('Laser power ($\mu$W)')
            for line in ax.get_legend().get_lines():
                line.set_linewidth(4.0)
            fig.suptitle(particle_name)
            powerseries[i] = spectrum
            ax.set_xlim(250, 1900)
            ax.set_ylim(0, 2)
            ax.set_ylabel('Normalized SERS Intensity (a.u.)')
            plt.tight_layout(pad = 0.8)


        # save_dir = r'C:\Users\ishaa\OneDrive\Desktop\Offline Data\2023-10-21_MLAgg\100x\Direct Powerseries Normalized\_'
        # plt.savefig(save_dir + particle_name + '.svg', format = 'svg')
        # plt.close(fig)
        print(particle_name)
        
## Calculate average
for i in range(0, len(avg_powerseries)):
    avg_powerseries[i] = avg_powerseries[i]/len(particle_list)

#%% Plot min power spectrum powerseries avg across MLAgg spots


# Plotting

fig, ax = plt.subplots(1,1,figsize=[12,9])
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('Normalized SERS Intensity (a.u.)')
x = spectrum.x        

for i in range(0, len(avg_powerseries)):
    
    ## Color = color of previous power in powerseries
    my_cmap = plt.get_cmap('inferno')
    color = my_cmap(i/20)
    offset = 0.03
    if i == 0:
        ax.plot(x, avg_powerseries[i], linewidth = 1, color = color, label = powerseries[i].laser_power * 1000)
    elif i % 2 != 0:
        ax.plot(x, avg_powerseries[i] + (i*offset), linewidth = 1, color = color, label = powerseries[i].laser_power * 1000)

## Label & plot
ax.legend(fontsize = 18, ncol = 5, loc = 'upper center')
ax.get_legend().set_title('Laser power ($\mu$W)')
for line in ax.get_legend().get_lines():
    line.set_linewidth(4.0)
fig.suptitle('633nm Powerseries - 100x MLAgg Average')
ax.set_xlim(250, 1900)
ax.set_ylim(0, 2)
plt.tight_layout(pad = 0.8)

# plt.savefig(save_dir + 'MLAgg Avg' + '.svg', format = 'svg')
# plt.close(fig)