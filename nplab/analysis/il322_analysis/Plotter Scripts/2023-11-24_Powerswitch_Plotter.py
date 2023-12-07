# -*- coding: utf-8 -*-
"""
Created on Wed Apr 26 18:32:45 2023

@author: il322

Plotter for M-TAPP-SMe single scan 633nm powerswitching 2023-11-20_633nm_Powerswitch_20x_MLAgg.h5


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


my_h5 = h5py.File(r"C:\Users\ishaa\OneDrive\Desktop\Offline Data\2023-11-20_633nm_Powerswitch_20x_MLAgg.h5")


#%% Spectral calibration

# Spectral calibration

## Get default literature BPT spectrum & peaks
lit_spectrum, lit_wn = cal.process_default_lit_spectrum()

## Load BPT ref spectrum
#my_h5 = h5py.File(r"C:\Users\il322\Desktop\Offline Data\2023-09-18_Co-TAPP-SMe_80nm_NPoM_Track_DF_633nm_Powerseries.h5")
coarse_shift = 60 # coarse shift to ref spectrum
notch_range = [0+coarse_shift, 300+coarse_shift]
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
ref_wn = cal.find_ref_peaks(bpt_ref_no_notch, lit_spectrum = lit_spectrum, lit_wn = lit_wn, threshold = 0.035, distance = 15)

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
notch = SERS.SERS_Spectrum(white_ref.x[np.where(white_ref.x < (notch_range[1]-140))], white_ref.y[np.where(white_ref.x < (notch_range[1] - 140))], name = 'White Scatterer Notch') 
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


#%% Dark counts power switch - MLAgg

particle = my_h5['PT_lab']


# Add all SERS spectra to powerseries list in order

keys = list(particle.keys())
keys = natsort.natsorted(keys)
powerseries = []
for key in keys:
    if 'glass_dark' in key:
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

# Add jump back to min powers to dark powerseries

for spec in dark_powerseries:
    print(spec.laser_power)


#%% Plot single powerswitch as timescan and avg high/low power spec for single MLAgg spot

'''
Just plotting un-smoothed lowest power spectra to find damage threshold
''' 


particle = my_h5['ParticleScannerScan_0']['Particle_4']


# Add all SERS spectra to powerseries list in order

keys = list(particle.keys())
keys = natsort.natsorted(keys)
powerseries = []


low_power_avg = np.zeros(len(spectrum.y))
high_power_avg = np.zeros(len(spectrum.y)) 

for key in keys:
    if 'SERS' in key:
        powerseries.append(particle[key])


for i, spectrum in enumerate(powerseries):
    
    ## x-axis truncation, calibration
    spectrum = SERS.SERS_Spectrum(spectrum)
    spectrum.x = spt.wl_to_wn(spectrum.x, 632.8)
    spectrum.x = spectrum.x + coarse_shift
    spectrum.truncate(start_x = notch_range[1], end_x = None)
    spectrum.x = wn_cal
    if spectrum.laser_power < 0.1:
        dark_counts = dark_powerseries[0].y
        color = 'black'
        offset = 0
    else:
        dark_counts = dark_powerseries[1].y
        color = 'red'
        offset = 0.1
    spectrum.calibrate_intensity(R_setup = R_setup,
                                  dark_counts = dark_counts,
                                  exposure = spectrum.cycle_time)
    
    spectrum.y = spt.remove_cosmic_rays(spectrum.y)
    #spectrum.truncate(1100, 1700)
    #spectrum.y_baselined = spt.baseline_als(spectrum.y, 1e0, 1e-1, niter = 10)
    #baseline = np.polyfit(spectrum.x, spectrum.y, 1)
    #spectrum.y_baselined = spectrum.y - (spectrum.x * baseline[0] + baseline[1])
    #spectrum.y_smooth = spt.butter_lowpass_filt_filt(spectrum.y_baselined,cutoff = 3000, fs = 20000, order = 2)
    spectrum.normalise(norm_y = spectrum.y)
    
    powerseries[i] = spectrum
    
    
    # Avg of high & low power spectra
    if spectrum.laser_power < 0.1:
        low_power_avg += spectrum.y 
    else:
        high_power_avg += spectrum.y
        
# Plot average high and low power spec
fig, ax = plt.subplots(1,1,figsize=[12,9])
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('Normalized SERS Intensity (a.u.)')

low_power_avg = SERS.SERS_Spectrum(x = wn_cal, y = low_power_avg/len(powerseries))
high_power_avg = SERS.SERS_Spectrum(x = wn_cal, y = high_power_avg/len(powerseries))    

low_power_avg.normalise()
high_power_avg.normalise()

low_power_avg.plot(ax = ax, plot_y = low_power_avg.y_norm, linewidth = 1, label = np.round(powerseries[0].laser_power * 1000, 0), color = 'black')
high_power_avg.plot(ax = ax, plot_y = high_power_avg.y_norm, title = '633nm Powerswitch - Avg 1uW to Avg 700uW', linewidth = 1, label = np.round(powerseries[1].laser_power * 1000, 0), color = 'red')
ax.legend()
ax.get_legend().set_title('Laser power ($\mu$W)')
plt.tight_layout(pad = 0.8)

# Plot normalized powerswitch as timescan
powerseries_y = powerseries
for i, spectrum in enumerate(powerseries):
    powerseries_y[i] = spectrum.y

powerseries_y = np.array(powerseries_y)

powerseries = SERS.SERS_Timescan(x = wn_cal, y = powerseries_y, exposure = 1)
powerseries.normalise(norm_individual = True)
powerseries.plot_timescan(plot_y = powerseries.Y_norm, v_min = -0.4, v_max = 1.4, x_min = 750, y_min = 1800, title = '633nm Powerswitch - 1uW to 700uW')
#%% Same as above but for each MLAgg spot across scan

'''
Just plotting normalized un-smoothed lowest power spectra to find damage threshold

Take average of un-smoothed lowest power spectra across all MLAgg spots
''' 
avg_scan = np.zeros((20, 965))
avg_low = np.zeros(len(dark_powerseries[0].y))
avg_high = np.zeros(len(dark_powerseries[0].y))

scan_list = ['ParticleScannerScan_1']#, 'ParticleScannerScan_0']
#avg_powerseries = np.zeros([19, len(spectrum.y)])

# Loop over particles in particle scan        

for particle_scan in scan_list:
    print(particle_scan)
    particle_list = []
    particle_list = natsort.natsorted(list(my_h5[particle_scan].keys()))
    
    ## Loop over particles in particle scan
    for particle in particle_list:
        if 'Particle' not in particle:
            particle_list.remove(particle)
            print('remove')
        if 'Particle_30' in particle:
            particle_list.remove(particle)

    # Loop over particles in particle scan
    for particle in particle_list:
        particle_name = 'MLAgg_' + str(particle_scan) + '_' + particle
        particle = my_h5[particle_scan][particle]
        print(particle_name)

        # Add all SERS spectra to powerseries list in order
        
        keys = list(particle.keys())
        keys = natsort.natsorted(keys)
        powerseries = []
        
        
        low_power_avg = np.zeros(len(spectrum.y))
        high_power_avg = np.zeros(len(spectrum.y)) 
        
        for key in keys:
            if 'SERS' in key:
                powerseries.append(particle[key])
        
        
        for i, spectrum in enumerate(powerseries):
            
            ## x-axis truncation, calibration
            spectrum = SERS.SERS_Spectrum(spectrum)
            spectrum.x = spt.wl_to_wn(spectrum.x, 632.8)
            spectrum.x = spectrum.x + coarse_shift
            spectrum.truncate(start_x = notch_range[1], end_x = None)
            spectrum.x = wn_cal
            if spectrum.laser_power < 0.1:
                dark_counts = dark_powerseries[0].y
                color = 'black'
                offset = 0
            else:
                dark_counts = dark_powerseries[1].y
                color = 'red'
                offset = 0.1
            spectrum.calibrate_intensity(R_setup = R_setup,
                                          dark_counts = dark_counts,
                                          exposure = spectrum.cycle_time)
            
            spectrum.y = spt.remove_cosmic_rays(spectrum.y)
            #spectrum.truncate(1100, 1700)
            #spectrum.y_baselined = spt.baseline_als(spectrum.y, 1e0, 1e-1, niter = 10)
            #baseline = np.polyfit(spectrum.x, spectrum.y, 1)
            #spectrum.y_baselined = spectrum.y - (spectrum.x * baseline[0] + baseline[1])
            #spectrum.y_smooth = spt.butter_lowpass_filt_filt(spectrum.y_baselined,cutoff = 3000, fs = 20000, order = 2)
            spectrum.normalise(norm_y = spectrum.y)
            
            powerseries[i] = spectrum
            avg_scan[i] += spectrum.y
            
            
            # Avg of high & low power spectra
            if spectrum.laser_power < 0.1:
                low_power_avg += spectrum.y 
            else:
                high_power_avg += spectrum.y
                
        # Plot average high and low power spec
        # fig, ax = plt.subplots(1,1,figsize=[12,9])
        # ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
        # ax.set_ylabel('Normalized SERS Intensity (a.u.)')
        # fig.suptitle(particle_name)
        
        low_power_avg = SERS.SERS_Spectrum(x = wn_cal, y = low_power_avg/len(powerseries))
        high_power_avg = SERS.SERS_Spectrum(x = wn_cal, y = high_power_avg/len(powerseries))    
        
        avg_low += low_power_avg.y
        avg_high += high_power_avg.y
        
        low_power_avg.normalise()
        high_power_avg.normalise()
        
      #  low_power_avg.plot(ax = ax, plot_y = low_power_avg.y_norm, linewidth = 1, label = np.round(dark_powerseries[0].laser_power * 1000, 0), color = 'black')
       # high_power_avg.plot(ax = ax, plot_y = high_power_avg.y_norm, title = '633nm Powerswitch - Avg 1uW to Avg 700uW', linewidth = 1, label = np.round(dark_powerseries[1].laser_power * 1000, 0), color = 'red')
        ax.legend()
        ax.get_legend().set_title('Laser power ($\mu$W)')
        plt.tight_layout(pad = 0.8)
        save_dir = r'C:\Users\ishaa\OneDrive\Desktop\Offline Data\2023-11-20_633nm_Powerswitch_MLAgg Plots\_'
        # plt.savefig(save_dir + particle_name + '_Avg_Powerswitch' + '.svg', format = 'svg')
        # plt.close(fig)
        
        # Plot normalized powerswitch as timescan
        powerseries_y = powerseries
        for i, spectrum in enumerate(powerseries):
            powerseries_y[i] = spectrum.y
        
        powerseries_y = np.array(powerseries_y)
        
        powerseries = SERS.SERS_Timescan(x = wn_cal, y = powerseries_y, exposure = 1)
        powerseries.normalise(norm_individual = True)
        #powerseries.plot_timescan(plot_y = powerseries.Y_norm, v_min = -0.4, v_max = 1.4, x_min = 750, y_min = 1800, title = particle_name + '\n633nm Powerswitch - 1uW to 700uW')
        # plt.savefig(save_dir + particle_name + '_Powerswitch_Scan' + '.svg', format = 'svg')
        # plt.close(fig)
        
        print(particle_name)
                
#%% Plot averages across all MLAgg spots

fig, ax = plt.subplots(1,1,figsize=[12,9])
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('Normalized SERS Intensity (a.u.)')
fig.suptitle('MLAgg Average')

avg_high = SERS.SERS_Spectrum(x = wn_cal, y = avg_high)
avg_low = SERS.SERS_Spectrum(x = wn_cal, y = avg_low)

avg_low.normalise()
avg_high.normalise()  

avg_low.plot(ax = ax, plot_y = avg_low.y_norm, linewidth = 1, label = np.round(dark_powerseries[0].laser_power * 1000, 0), color = 'black')
avg_high.plot(ax = ax, plot_y = avg_high.y_norm, title = '633nm Powerswitch - Avg 1uW to Avg 700uW', linewidth = 1, label = np.round(dark_powerseries[1].laser_power * 1000, 0), color = 'red')
ax.legend()
ax.get_legend().set_title('Laser power ($\mu$W)')
plt.tight_layout(pad = 0.8)
plt.savefig(save_dir + 'MLAgg_Avg' + '_Avg_Powerswitch' + '.svg', format = 'svg')
plt.close(fig)
        


# Plot normalized powerswitch as timescan
# powerseries_y = avg_scan
# for i, spectrum in enumerate(avg_scan):
#     powerseries_y[i] = spectrum.y

# powerseries_y = np.array(powerseries_y)

avg_scan = SERS.SERS_Timescan(x = wn_cal, y = avg_scan, exposure = 1)
avg_scan.normalise(norm_individual = True)
avg_scan.plot_timescan(plot_y = avg_scan.Y_norm, v_min = -0.4, v_max = 1.4, x_min = 750, y_min = 1800, title = 'MLAgg Average' + '\n633nm Powerswitch - 1uW to 700uW')
plt.savefig(save_dir + 'MLAgg_Avg' + '_Powerswitch_Scan' + '.svg', format = 'svg')
plt.close(fig)
        

