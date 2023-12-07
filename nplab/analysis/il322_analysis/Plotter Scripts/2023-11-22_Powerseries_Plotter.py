# -*- coding: utf-8 -*-
"""
Created on Wed Apr 26 18:32:45 2023

@author: il322

Plotter for M-TAPP-SMe single scan 785nm & 830nm powerseries from 2023-11-21_Lab8_MLAgg_785_830_Powerseries.h5

(samples:
     2023-07-31_Co-TAPP-SMe_60nm_MLAgg_on_Glass_c)

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

my_h5 = h5py.File(r"C:\Users\ishaa\OneDrive\Desktop\Offline Data\2023-11-21_Lab8_MLAgg_785_830_Powerseries.h5")


#%% Spectral calibration 785

## Get default literature BPT spectrum & peaks
lit_spectrum, lit_wn = cal.process_default_lit_spectrum()

## Load BPT ref spectrum
bpt_ref = my_h5['WlLab']['BPT_785nm']
bpt_ref = SERS.SERS_Spectrum(bpt_ref)

## Coarse adjustments to miscalibrated spectra
coarse_shift = -1450 # coarse shift to ref spectrum
coarse_stretch = 2 # coarse stretch to ref spectrum
notch_range = [(1420 + coarse_shift) * coarse_stretch, (1650 + coarse_shift) * coarse_stretch]

## Convert to wn
bpt_ref.x = spt.wl_to_wn(bpt_ref.x, 785)
bpt_ref.x = bpt_ref.x + coarse_shift
bpt_ref.x = bpt_ref.x * coarse_stretch

## No notch spectrum (use this truncation for all spectra!)
bpt_ref_no_notch = bpt_ref
bpt_ref_no_notch.truncate(start_x = notch_range[1], end_x = None)

## Baseline, smooth, and normalize no notch ref for peak finding
bpt_ref_no_notch.y_baselined = bpt_ref_no_notch.y -  spt.baseline_als(y=bpt_ref_no_notch.y,lam=1e1,p=1e-4,niter=1000)
bpt_ref_no_notch.y_smooth = spt.butter_lowpass_filt_filt(bpt_ref_no_notch.y_baselined,
                                                        cutoff=2000,
                                                        fs = 10000,
                                                        order=2)
bpt_ref_no_notch.normalise(norm_y = bpt_ref_no_notch.y_smooth)

## Find BPT ref peaks
ref_wn = cal.find_ref_peaks(bpt_ref_no_notch, lit_spectrum = lit_spectrum, lit_wn = lit_wn, threshold = 0.03, distance = 8)

## Find calibrated wavenumbers
wn_cal = cal.calibrate_spectrum(bpt_ref_no_notch, ref_wn, lit_spectrum = lit_spectrum, lit_wn = lit_wn, linewidth = 1, deg = 2)
bpt_ref.x = wn_cal

#%% Spectral efficiency white light calibration 785

white_ref = my_h5['WlLab']['white_scatt_785notch_x5_1']
white_ref = SERS.SERS_Spectrum(white_ref.attrs['wavelengths'], white_ref[2], title = 'White Scatterer')

## Convert to wn
white_ref.x = spt.wl_to_wn(white_ref.x, 785)
white_ref.x = white_ref.x + coarse_shift
white_ref.x = white_ref.x * coarse_stretch

## Get white bkg (counts in notch region)
#notch = SERS.SERS_Spectrum(white_ref.x[np.where(white_ref.x < (notch_range[1]-50))], white_ref.y[np.where(white_ref.x < (notch_range[1] - 50))], name = 'White Scatterer Notch') 
notch = SERS.SERS_Spectrum(x = spt.truncate_spectrum(white_ref.x, white_ref.y, notch_range[0] + 200, notch_range[1] - 200)[0], 
                            y = spt.truncate_spectrum(white_ref.x,white_ref.y, notch_range[0] + 200, notch_range[1] - 200)[1], 
                            name = 'White Scatterer Notch')
notch_cts = notch.y.mean()
notch.plot()

# ## Truncate out notch (same as BPT ref), assign wn_cal
white_ref.truncate(start_x = notch_range[1], end_x = None)


## Convert back to wl for efficiency calibration
white_ref.x = spt.wn_to_wl(white_ref.x, 785)


# Calculate R_setup

R_setup = cal.white_scatter_calibration(wl = white_ref.x,
                                    white_scatter = white_ref.y,
                                    white_bkg = notch_cts,
                                    plot = True,
                                    start_notch = None,
                                    end_notch = None,
                                    bpt_ref = bpt_ref)

## Get dark counts - skip for now as using powerseries
# dark_cts = my_h5['PT_lab']['whire_ref_x5']
# dark_cts = SERS.SERS_Spectrum(wn_cal_633, dark_cts[5], title = 'Dark Counts')
# # dark_cts.plot()
# plt.show()

''' 
Still issue with 'white background' of calculating R_setup
Right now, choosing white background ~400 (near notch counts) causes R_setup to be very low at long wavelengths (>900nm)
This causes very large background past 1560cm-1 BPT peak
Using a white_bkg of -100000 flattens it out...
'''    

#%% 785nm MLAGG dark counts

particle = my_h5['glass_785_0']


# Add all SERS spectra to powerseries list in order

keys = list(particle.keys())
keys = natsort.natsorted(keys)
powerseries = []
for key in keys:
    if 'SERS' in key:
        powerseries.append(particle[key])
        
for i, spectrum in enumerate(powerseries):
    
    ## x-axis truncation, calibration
    spectrum = SERS.SERS_Spectrum(spectrum)
    spectrum.x = spt.wl_to_wn(spectrum.x, 785)
    spectrum.x = spectrum.x + coarse_shift
    spectrum.x = spectrum.x * coarse_stretch
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
    
    
#%% Plot single powerseries for each MLAgg spot 785

particle_list = ['particle_2', 'particle_3', 'particle_4']

avg_powerseries = np.zeros([12, len(spectrum.y)])

for j, particle in enumerate(particle_list):
    particle = my_h5[particle]
    particle_name = 'Particle_' + str(j)
    
    # Add all SERS spectra to powerseries list in order
    
    keys = list(particle.keys())
    keys = natsort.natsorted(keys)
    powerseries = []
    
    for key in keys:
        if 'SERS' in key:
            powerseries.append(particle[key])
    
    
    fig, ax = plt.subplots(1,1,figsize=[12,9])
    ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
    ax.set_ylabel('Normalized SERS Intensity (a.u.)')
    
    for i, spectrum in enumerate(powerseries):
        
        ## x-axis truncation, calibration
        spectrum = SERS.SERS_Spectrum(spectrum)
        spectrum.x = spt.wl_to_wn(spectrum.x, 785)
        spectrum.x = spectrum.x + coarse_shift
        spectrum.x = spectrum.x * coarse_stretch
        spectrum.truncate(start_x = notch_range[1], end_x = None)
        spectrum.x = wn_cal
        spectrum.calibrate_intensity(R_setup = R_setup,
                                      dark_counts = dark_powerseries[i].y,
                                      exposure = spectrum.exposure)
        
        spectrum.y = spt.remove_cosmic_rays(spectrum.y)
        #spectrum.truncate(1100, 1700)
        #spectrum.y_baselined = spt.baseline_als(spectrum.y, 1e0, 1e-1, niter = 10)
        #baseline = np.polyfit(spectrum.x, spectrum.y, 1)
        #spectrum.y_baselined = spectrum.y - (spectrum.x * baseline[0] + baseline[1])
        #spectrum.y_smooth = spt.butter_lowpass_filt_filt(spectrum.y_baselined,cutoff = 3000, fs = 20000, order = 2)
        spectrum.normalise(norm_y = spectrum.y)
        
        ## Plot
        my_cmap = plt.get_cmap('inferno')
        color = my_cmap(i/13)
        offset = 0.00
        spectrum.plot(ax = ax, plot_y = spectrum.y_norm + (i*offset), title = '785nm Powerseries - Co-TAPP-SMe 60nm MLAgg', linewidth = 1, color = color, label = np.round(spectrum.laser_power * 1000, 0), zorder = (19-i))
        avg_powerseries[i] += spectrum.y_norm
    
        ## Labeling & plotting
        ax.legend(fontsize = 18, ncol = 4, loc = 'upper center')
        ax.get_legend().set_title('Laser power ($\mu$W)')
        for line in ax.get_legend().get_lines():
            line.set_linewidth(4.0)
        fig.suptitle(particle.name)
        powerseries[i] = spectrum
        
        ax.set_xlim(250, None)
        ax.set_ylim(0, 1.4)
        plt.tight_layout(pad = 0.8)
        
        # save_dir = r'C:\Users\ishaa\OneDrive\Desktop\Offline Data\2023-11-21_MLAgg\785\Normalized\_'
        # plt.savefig(save_dir + particle_name + '.svg', format = 'svg')
        # plt.close(fig)
        
## Calculate average
for i in range(0, len(avg_powerseries)):
    avg_powerseries[i] = avg_powerseries[i]/len(particle_list)        
    

#%% Plot powerseries avg across MLAgg spots 785

# Plotting

fig, ax = plt.subplots(1,1,figsize=[12,9])
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('Normalized SERS Intensity (a.u.)')
x = spectrum.x        

for i in range(0, len(avg_powerseries)):
    
    ## Color = color of previous power in powerseries
    my_cmap = plt.get_cmap('inferno')
    color = my_cmap(i/13)
    offset = 0
    ax.plot(x, avg_powerseries[i] + (i*offset), linewidth = 1, color = color, label = np.round(powerseries[i].laser_power * 1000,1), zorder = (19-i))

## Label & plot
ax.legend(fontsize = 18, ncol = 4, loc = 'upper center')
ax.get_legend().set_title('Laser power ($\mu$W)')
for line in ax.get_legend().get_lines():
    line.set_linewidth(4.0)
fig.suptitle('785nm Powerseries - MLAgg Average')
ax.set_ylim(0, avg_powerseries.max() * 1.4)
plt.tight_layout(pad = 0.8)

#plt.savefig(save_dir + 'MLAgg Avg' + '.svg', format = 'svg')
# plt.close(fig)


#%%
# Spectral calibration 830nm

## Get default literature BPT spectrum & peaks
lit_spectrum, lit_wn = cal.process_default_lit_spectrum()

## Load BPT ref spectrum
bpt_ref = my_h5['WlLab']['BPT_830nm']
bpt_ref = SERS.SERS_Spectrum(bpt_ref)

## Coarse adjustments to miscalibrated spectra
coarse_shift = -1000 # coarse shift to ref spectrum
coarse_stretch = 1.7 # coarse stretch to ref spectrum
notch_range = [(1000 + coarse_shift) * coarse_stretch, (1300 + coarse_shift) * coarse_stretch]

## Convert to wn
bpt_ref.x = spt.wl_to_wn(bpt_ref.x, 830)
bpt_ref.x = bpt_ref.x + coarse_shift
bpt_ref.x = bpt_ref.x * coarse_stretch

## No notch spectrum (use this truncation for all spectra!)
bpt_ref_no_notch = bpt_ref
bpt_ref_no_notch.truncate(start_x = notch_range[1], end_x = None)

## Baseline, smooth, and normalize no notch ref for peak finding
bpt_ref_no_notch.y_baselined = bpt_ref_no_notch.y -  spt.baseline_als(y=bpt_ref_no_notch.y,lam=1e1,p=1e-4,niter=1000)
bpt_ref_no_notch.y_smooth = spt.butter_lowpass_filt_filt(bpt_ref_no_notch.y_baselined,
                                                        cutoff=2000,
                                                        fs = 10000,
                                                        order=2)
bpt_ref_no_notch.normalise(norm_y = bpt_ref_no_notch.y_smooth)

## Find BPT ref peaks
ref_wn = cal.find_ref_peaks(bpt_ref_no_notch, lit_spectrum = lit_spectrum, lit_wn = lit_wn, threshold = 0.1, distance = 8)

## Find calibrated wavenumbers
wn_cal = cal.calibrate_spectrum(bpt_ref_no_notch, ref_wn, lit_spectrum = lit_spectrum, lit_wn = lit_wn, linewidth = 1, deg = 2)
bpt_ref_no_notch.x = wn_cal


#%% Spectral efficiency white light calibration 830

white_ref = my_h5['WlLab']['white_scatt_830notch_x5']
white_ref = SERS.SERS_Spectrum(white_ref.attrs['wavelengths'], white_ref[2], title = 'White Scatterer')

## Convert to wn
white_ref.x = spt.wl_to_wn(white_ref.x, 830)
white_ref.x = white_ref.x + coarse_shift
white_ref.x = white_ref.x * coarse_stretch

## Get white bkg (counts in notch region)
#notch = SERS.SERS_Spectrum(white_ref.x[np.where(white_ref.x < (notch_range[1]-50))], white_ref.y[np.where(white_ref.x < (notch_range[1] - 50))], name = 'White Scatterer Notch') 
notch = SERS.SERS_Spectrum(x = spt.truncate_spectrum(white_ref.x, white_ref.y, notch_range[0] + 200, notch_range[1] - 200)[0], 
                            y = spt.truncate_spectrum(white_ref.x,white_ref.y, notch_range[0] + 200, notch_range[1] - 200)[1], 
                            name = 'White Scatterer Notch')
notch_cts = notch.y.mean()
notch.plot()

# ## Truncate out notch (same as BPT ref), assign wn_cal
white_ref.truncate(start_x = notch_range[1], end_x = None)


## Convert back to wl for efficiency calibration
white_ref.x = spt.wn_to_wl(white_ref.x, 830)


# Calculate R_setup

R_setup = cal.white_scatter_calibration(wl = white_ref.x,
                                    white_scatter = white_ref.y,
                                    white_bkg = notch_cts,
                                    plot = True,
                                    start_notch = None,
                                    end_notch = None,
                                    bpt_ref = bpt_ref)

## Get dark counts - skip for now as using powerseries
# dark_cts = my_h5['PT_lab']['whire_ref_x5']
# dark_cts = SERS.SERS_Spectrum(wn_cal_633, dark_cts[5], title = 'Dark Counts')
# # dark_cts.plot()
# plt.show()

''' 
Still issue with 'white background' of calculating R_setup
Right now, choosing white background ~400 (near notch counts) causes R_setup to be very low at long wavelengths (>900nm)
This causes very large background past 1560cm-1 BPT peak
Using a white_bkg of -100000 flattens it out...
'''    

#%% 830nm MLAGG dark counts

particle = my_h5['glass_830_0']


# Add all SERS spectra to powerseries list in order

keys = list(particle.keys())
keys = natsort.natsorted(keys)
powerseries = []
for key in keys:
    if 'SERS' in key:
        powerseries.append(particle[key])
        
for i, spectrum in enumerate(powerseries):
    
    ## x-axis truncation, calibration
    spectrum = SERS.SERS_Spectrum(spectrum)
    spectrum.x = spt.wl_to_wn(spectrum.x, 830)
    spectrum.x = spectrum.x + coarse_shift
    spectrum.x = spectrum.x * coarse_stretch
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


#%% Plot single powerseries for each MLAgg spot 830

particle_list = ['particle_5', 'particle_6', 'particle_7']

avg_powerseries = np.zeros([12, len(spectrum.y)])

for j, particle in enumerate(particle_list):
    particle = my_h5[particle]
    particle_name = 'Particle_' + str(j)
    
    # Add all SERS spectra to powerseries list in order
    
    keys = list(particle.keys())
    keys = natsort.natsorted(keys)
    powerseries = []
    
    for key in keys:
        if 'SERS' in key:
            powerseries.append(particle[key])
    
    
    fig, ax = plt.subplots(1,1,figsize=[12,9])
    ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
    ax.set_ylabel('Normalzied SERS Intensity (a.u.)')
    
    for i, spectrum in enumerate(powerseries):
        
        ## x-axis truncation, calibration
        spectrum = SERS.SERS_Spectrum(spectrum)
        spectrum.x = spt.wl_to_wn(spectrum.x, 830)
        spectrum.x = spectrum.x + coarse_shift
        spectrum.x = spectrum.x * coarse_stretch
        spectrum.truncate(start_x = notch_range[1], end_x = None)
        spectrum.x = wn_cal
        spectrum.calibrate_intensity(R_setup = R_setup,
                                      dark_counts = dark_powerseries[i].y,
                                      exposure = spectrum.exposure)
        
        spectrum.y = spt.remove_cosmic_rays(spectrum.y)
        #spectrum.truncate(1100, 1700)
        #spectrum.y_baselined = spt.baseline_als(spectrum.y, 1e0, 1e-1, niter = 10)
        #baseline = np.polyfit(spectrum.x, spectrum.y, 1)
        #spectrum.y_baselined = spectrum.y - (spectrum.x * baseline[0] + baseline[1])
        #spectrum.y_smooth = spt.butter_lowpass_filt_filt(spectrum.y_baselined,cutoff = 3000, fs = 20000, order = 2)
        spectrum.normalise(norm_y = spectrum.y)
        
        ## Plot
        my_cmap = plt.get_cmap('inferno')
        color = my_cmap(i/13)
        spectrum.plot(ax = ax, plot_y = spectrum.y_norm, title = '830nm Powerseries - Co-TAPP-SMe 60nm MLAgg', linewidth = 1, color = color, label = np.round(spectrum.laser_power * 1000, 0), zorder = (19-i))
        avg_powerseries[i] += spectrum.y_norm
    
        ## Labeling & plotting
        ax.legend(fontsize = 18, ncol = 4, loc = 'upper center')
        ax.get_legend().set_title('Laser power ($\mu$W)')
        for line in ax.get_legend().get_lines():
            line.set_linewidth(4.0)
        fig.suptitle(particle.name)
        powerseries[i] = spectrum
        
        ax.set_xlim(250, None)
        ax.set_ylim(0, 1.4)
        plt.tight_layout(pad = 0.8)
        
        save_dir = r'C:\Users\ishaa\OneDrive\Desktop\Offline Data\2023-11-21_MLAgg\830\Normalized\_'
        plt.savefig(save_dir + particle_name + '.svg', format = 'svg')
        #plt.close(fig)
        
## Calculate average
for i in range(0, len(avg_powerseries)):
    avg_powerseries[i] = avg_powerseries[i]/len(particle_list)        
    

#%% Plot powerseries avg across MLAgg spots 830

# Plotting

fig, ax = plt.subplots(1,1,figsize=[12,9])
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('Normalized SERS Intensity (a.u.)')
x = spectrum.x        

for i in range(0, len(avg_powerseries)):
    
    ## Color = color of previous power in powerseries
    my_cmap = plt.get_cmap('inferno')
    color = my_cmap(i/13)
    offset = 0
    ax.plot(x, avg_powerseries[i] + (i*offset), linewidth = 1, color = color, label = np.round(powerseries[i].laser_power * 1000,1), zorder = (19-i))

## Label & plot
ax.legend(fontsize = 18, ncol = 4, loc = 'upper center')
ax.get_legend().set_title('Laser power ($\mu$W)')
for line in ax.get_legend().get_lines():
    line.set_linewidth(4.0)
fig.suptitle('830nm Powerseries - MLAgg Average')
ax.set_ylim(0, avg_powerseries.max() * 1.4)
plt.tight_layout(pad = 0.8)

plt.savefig(save_dir + 'MLAgg Avg' + '.svg', format = 'svg')
# plt.close(fig)