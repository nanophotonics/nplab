# -*- coding: utf-8 -*-
"""
Created on Wed Apr 26 18:32:45 2023

@author: il322

Plotter for M-TAPP-SMe 633nm SERS before/after plasma cleaning


(samples:
     2023-11-28_Co-TAPP-SMe_60nm_MLAgg_on_Glass_a)

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


my_h5 = h5py.File(r"C:\Users\ishaa\OneDrive\Desktop\Offline Data\2023-11-29_633nm_20x_MLAgg_PlasmaClean_SERS.h5")


#%%

# Spectral calibration

## Get default literature BPT spectrum & peaks
lit_spectrum, lit_wn = cal.process_default_lit_spectrum()

## Load BPT ref spectrum
bpt_ref = my_h5['ref_meas']['BPT_633nm']
bpt_ref = SERS.SERS_Spectrum(bpt_ref)

## Coarse adjustments to miscalibrated spectra
coarse_shift = 100 # coarse shift to ref spectrum
coarse_stretch = 1 # coarse stretch to ref spectrum
notch_range = [(127 + coarse_shift) * coarse_stretch, (177 + coarse_shift) * coarse_stretch] # Define notch range as region in wavenumbers
truncate_range = [notch_range[1] + 50] # Truncate range for all spectra on this calibration - Add 50 to take out notch slope

## Convert to wn
bpt_ref.x = spt.wl_to_wn(bpt_ref.x, 632.8)
bpt_ref.x = bpt_ref.x + coarse_shift
bpt_ref.x = bpt_ref.x * coarse_stretch

## No notch spectrum (use this truncation for all spectra!)
bpt_ref_no_notch = bpt_ref
bpt_ref_no_notch.truncate(start_x = truncate_range[0], end_x = None)

# Baseline, smooth, and normalize no notch ref for peak finding
bpt_ref_no_notch.y_baselined = bpt_ref_no_notch.y -  spt.baseline_als(y=bpt_ref_no_notch.y,lam=1e1,p=1e-4,niter=1000)
bpt_ref_no_notch.y_smooth = spt.butter_lowpass_filt_filt(bpt_ref_no_notch.y_baselined,
                                                        cutoff=2000,
                                                        fs = 10000,
                                                        order=2)
bpt_ref_no_notch.normalise(norm_y = bpt_ref_no_notch.y_smooth)

## Find BPT ref peaks
ref_wn = cal.find_ref_peaks(bpt_ref_no_notch, lit_spectrum = lit_spectrum, lit_wn = lit_wn, threshold = 0.06, distance = 20)

## Find calibrated wavenumbers
wn_cal = cal.calibrate_spectrum(bpt_ref_no_notch, ref_wn, lit_spectrum = lit_spectrum, lit_wn = lit_wn, linewidth = 1, deg = 2)
bpt_ref.x = wn_cal


#%% Spectral efficiency white light calibration

white_ref = my_h5['ref_meas']['white_ref_x5']
white_ref = SERS.SERS_Spectrum(white_ref.attrs['wavelengths'], white_ref[2], title = 'White Scatterer')

## Convert to wn
white_ref.x = spt.wl_to_wn(white_ref.x, 632.8)
white_ref.x = white_ref.x + coarse_shift
white_ref.x = white_ref.x * coarse_stretch

## Get white bkg (counts in notch region)
#notch = SERS.SERS_Spectrum(white_ref.x[np.where(white_ref.x < (notch_range[1]-50))], white_ref.y[np.where(white_ref.x < (notch_range[1] - 50))], name = 'White Scatterer Notch') 
# notch = SERS.SERS_Spectrum(x = spt.truncate_spectrum(white_ref.x, white_ref.y, notch_range[0], notch_range[1] - 100)[0], 
#                             y = spt.truncate_spectrum(white_ref.x, white_ref.y, notch_range[0], notch_range[1] - 100)[1], 
#                             name = 'White Scatterer Notch')
notch = SERS.SERS_Spectrum(white_ref.x, white_ref.y, title = 'Notch')
notch.truncate(notch_range[0], notch_range[1])
notch_cts = notch.y.mean()
notch.plot(title = 'White Scatter Notch')

# ## Truncate out notch (same as BPT ref), assign wn_cal
white_ref.truncate(start_x = truncate_range[0], end_x = None)


## Convert back to wl for efficiency calibration
white_ref.x = spt.wn_to_wl(white_ref.x, 632.8)


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


#%% Before & after PC plotting


#%% Dark counts spectrum - MLAgg

particle = my_h5['ref_meas']


# Add all SERS spectra to powerseries list in order

spectrum = particle['dark_counts_glass_x12']
spectrum = SERS.SERS_Spectrum(x = spectrum.attrs['wavelengths'], y = spectrum[5], title = 'dark spectrum')
spectrum.x = spt.wl_to_wn(spectrum.x, 632.8)
spectrum.x = spectrum.x + coarse_shift
spectrum.truncate(start_x = truncate_range[0], end_x = None)
spectrum.x = wn_cal
# spectrum.y = spt.remove_cosmic_rays(spectrum.y, threshold = 2, cutoff = 200)
dark_spectrum = spectrum
dark_spectrum.plot()

#%% Plot single before & after PC spectra


fig, ax = plt.subplots(1,1,figsize=[12,9])
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('SERS Intensity (cts/mW/s)')



particle_list = natsort.natsorted(list(my_h5.keys()))

## Loop over particles in particle scan
for particle in particle_list:
    # print(particle)
    if 'before' not in particle and 'after' not in particle:
        particle_list.remove(particle)
particle_list.remove('ref_meas')
        
        
for particle in particle_list:

    
    if 'before' in particle:
        color = 'black'
        linetype = 'solid'
        label = 'Before PC'
        
    elif 'after_45min' in particle:
        color = 'red'
        linetype = 'solid'
        label = 'After 45min PC'
        
    elif 'after_30min' in particle:
        color = 'blue'
        linetype = 'solid'
        label = 'After 30min 1mM reconstitution'
        
    elif 'after_120min' in particle:
        color = 'green'
        linetype = 'solid'
        label = 'After 120min 1mM reconstitution'
        
    particle = my_h5[particle]
                    
    spectrum = particle['633nm_SERS_20uW_5s_x12']
    wlns = spectrum.attrs['wavelengths']
    spectrum = np.array(spectrum)
    spectrum = spectrum.mean(axis = 0)
    spectrum = SERS.SERS_Spectrum(x = wlns, y = spectrum)
    spectrum.x = spt.wl_to_wn(spectrum.x, 632.8)
    spectrum.x = spectrum.x + coarse_shift
    spectrum.truncate(start_x = truncate_range[0], end_x = None)
    spectrum.x = wn_cal
    spectrum.calibrate_intensity(R_setup = R_setup,
                                  dark_counts = dark_spectrum.y,
                                  exposure = 5.091790199279785,
                                  laser_power = 0.0188)
    ax.plot(spectrum.x, spectrum.y, color = color, label = label)
    ax.set_title('633nm SERS - Plasma Clean & Reconstitute')
    
## Labeling

handles, labels = ax.get_legend_handles_labels()
handle_list, label_list = [], []
for handle, label in zip(handles, labels):
    if label not in label_list:
        handle_list.append(handle)
        label_list.append(label)

order = [3,1,0,2]
plt.legend([handle_list[idx] for idx in order],[label_list[idx] for idx in order])



fig.suptitle('Co-TAPP-SMe 60nm MLAgg')

ax.set_xlim(400, 1900)
plt.tight_layout(pad = 0.8)
# ax.set_yscale('log')

save_dir = r'C:\Users\ishaa\OneDrive\Desktop\Offline Data\_'
# plt.savefig(save_dir + 'Before_After_PC' + '.svg', format = 'svg')
# plt.close(fig)

#%% Plot single before & after PC spectra - zoomed


fig, ax = plt.subplots(1,1,figsize=[12,9])
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('SERS Intensity (cts/mW/s)')



particle_list = natsort.natsorted(list(my_h5.keys()))

## Loop over particles in particle scan
for particle in particle_list:
    # print(particle)
    if 'before' not in particle and 'after' not in particle:
        particle_list.remove(particle)
particle_list.remove('ref_meas')
        
        
for particle in particle_list:

    
    if 'before' in particle:
        color = 'black'
        linetype = 'solid'
        label = 'Before PC'
        continue
        
    elif 'after_45min' in particle:
        color = 'red'
        linetype = 'solid'
        label = 'After 45min PC'
        
    elif 'after_30min' in particle:
        color = 'blue'
        linetype = 'solid'
        label = 'After 30min 1mM reconstitution'
        
    elif 'after_120min' in particle:
        color = 'green'
        linetype = 'solid'
        label = 'After 120min 1mM reconstitution'
        continue
        
    particle = my_h5[particle]
                    
    spectrum = particle['633nm_SERS_20uW_5s_x12']
    wlns = spectrum.attrs['wavelengths']
    spectrum = np.array(spectrum)
    spectrum = spectrum.mean(axis = 0)
    spectrum = SERS.SERS_Spectrum(x = wlns, y = spectrum)
    spectrum.x = spt.wl_to_wn(spectrum.x, 632.8)
    spectrum.x = spectrum.x + coarse_shift
    spectrum.truncate(start_x = truncate_range[0], end_x = None)
    spectrum.x = wn_cal
    spectrum.calibrate_intensity(R_setup = R_setup,
                                  dark_counts = dark_spectrum.y,
                                  exposure = 5.091790199279785,
                                  laser_power = 0.0188)
    ax.plot(spectrum.x, spectrum.y, color = color, label = label)
    ax.set_title('633nm SERS - Plasma Clean & Reconstitute')
    
## Labeling

handles, labels = ax.get_legend_handles_labels()
handle_list, label_list = [], []
for handle, label in zip(handles, labels):
    if label not in label_list:
        handle_list.append(handle)
        label_list.append(label)

order = [0,1]
plt.legend([handle_list[idx] for idx in order],[label_list[idx] for idx in order])



fig.suptitle('Co-TAPP-SMe 60nm MLAgg')

ax.set_xlim(400, 1900)
plt.tight_layout(pad = 0.8)
ax.set_ylim(0,34000)

save_dir = r'C:\Users\ishaa\OneDrive\Desktop\Offline Data\_'
# plt.savefig(save_dir + 'Before_After_PC_zoom' + '.svg', format = 'svg')
# plt.close(fig)