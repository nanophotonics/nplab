# -*- coding: utf-8 -*-
"""
Created on Wed Apr 26 18:32:45 2023

@author: il322

Plotter for Co-TAPP-SMe 633nm SERS w/ 400l/mm grating 2023-12-19_633nm_SERS_400Grating_Powerswitch_VariedDarkTime.h5


(samples:
     2023-11-28_Co-TAPP-SMe_60nm_MLAgg_b)

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


my_h5 = h5py.File(r"C:\Users\il322\Desktop\Offline Data\2023-12-19_633nm_SERS_400Grating_Powerswitch_VariedDarkTime.h5")


#%%

# Spectral calibration

## Get default literature BPT spectrum & peaks
lit_spectrum, lit_wn = cal.process_default_lit_spectrum()

## Load BPT ref spectrum
bpt_ref = my_h5['400_grating']['BPT_633nm_400grating']
bpt_ref = SERS.SERS_Spectrum(bpt_ref)

## Coarse adjustments to miscalibrated spectra
coarse_shift = 150 # coarse shift to ref spectrum
coarse_stretch = .92 # coarse stretch to ref spectrum
notch_range = [(110 + coarse_shift) * coarse_stretch, (170 + coarse_shift) * coarse_stretch] # Define notch range as region in wavenumbers
truncate_range = [notch_range[1] + 200, None] # Truncate range for all spectra on this calibration - Add 50 to take out notch slope

## Convert to wn
bpt_ref.x = spt.wl_to_wn(bpt_ref.x, 632.8)
bpt_ref.x = bpt_ref.x + coarse_shift
bpt_ref.x = bpt_ref.x * coarse_stretch

## No notch spectrum (use this truncation for all spectra!)
bpt_ref_no_notch = bpt_ref
bpt_ref_no_notch.truncate(start_x = truncate_range[0], end_x = truncate_range[1])

# Baseline, smooth, and normalize no notch ref for peak finding
bpt_ref_no_notch.y_baselined = bpt_ref_no_notch.y -  spt.baseline_als(y=bpt_ref_no_notch.y,lam=1e1,p=1e-4,niter=1000)
bpt_ref_no_notch.y_smooth = spt.butter_lowpass_filt_filt(bpt_ref_no_notch.y_baselined,
                                                        cutoff=2000,
                                                        fs = 10000,
                                                        order=2)
bpt_ref_no_notch.normalise(norm_y = bpt_ref_no_notch.y_smooth)

## Find BPT ref peaks
ref_wn = cal.find_ref_peaks(bpt_ref_no_notch, lit_spectrum = lit_spectrum, lit_wn = lit_wn, threshold = 0.05, distance = 10)

## Find calibrated wavenumbers
wn_cal = cal.calibrate_spectrum(bpt_ref_no_notch, ref_wn, lit_spectrum = lit_spectrum, lit_wn = lit_wn, linewidth = 1, deg = 2)
bpt_ref.x = wn_cal


#%% Spectral efficiency white light calibration

white_ref = my_h5['400_grating']['white_ref_633nm_400grating']
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
white_ref.truncate(start_x = truncate_range[0], end_x = truncate_range[1])


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


#%% Plot 633nm SERS of various samples


fig, ax = plt.subplots(1,1,figsize=[12,9])
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('SERS Intensity (cts/mW/s)')


# BPT

spectrum = my_h5['400_grating']['BPT_633nm_400grating']
## x-axis truncation, calibration
spectrum = SERS.SERS_Spectrum(spectrum)
spectrum.x = spt.wl_to_wn(spectrum.x, 632.8)
spectrum.x = (spectrum.x + coarse_shift) * coarse_stretch
print(spectrum.y.shape) 
spectrum.truncate(start_x = truncate_range[0], end_x = truncate_range[1])
spectrum.x = wn_cal
print(spectrum.y.shape)
spectrum.calibrate_intensity(R_setup = R_setup,
                              dark_counts = notch_cts,
                              exposure = spectrum.cycle_time)
spectrum.normalise(norm_y = spectrum.y)
spectrum.plot(ax = ax, plot_y = spectrum.y_norm, title = '633nm SERS - 400l/mm Grating', linewidth = 2, label = 'BPT Ref')


# Si

spectrum = my_h5['400_grating']['Si_633nm_400grating']
## x-axis truncation, calibration
spectrum = SERS.SERS_Spectrum(spectrum)
spectrum.x = spt.wl_to_wn(spectrum.x, 632.8)
spectrum.x = (spectrum.x + coarse_shift) * coarse_stretch
print(spectrum.y.shape) 
spectrum.truncate(start_x = truncate_range[0], end_x = truncate_range[1])
spectrum.x = wn_cal
print(spectrum.y.shape)
spectrum.calibrate_intensity(R_setup = R_setup,
                              dark_counts = notch_cts,
                              exposure = spectrum.cycle_time)
spectrum.normalise(norm_y = spectrum.y)
spectrum.plot(ax = ax, plot_y = spectrum.y_norm - 0.32, title = '633nm SERS - 400l/mm Grating', linewidth = 2, label = 'Si Ref')


# Co-TAPP-SMe MLAgg Avg x15

particle = my_h5['400_grating']

## Avg all Co-TAPP-SMe kinetic scans

keys = list(particle.keys())
keys = natsort.natsorted(keys)
spectrum_avg = np.zeros(spectrum.y.shape)
counter = 0

for key in keys:
    if '633nm_20uW' in key:
        ## x-axis truncation, calibration
        spectrum = particle[key]
        spectrum = SERS.SERS_Timescan(spectrum)
        spectrum.x = spt.wl_to_wn(spectrum.x, 632.8)
        spectrum.x = (spectrum.x + coarse_shift) * coarse_stretch
        spectrum.truncate(start_x = truncate_range[0], end_x = None)
        spectrum.x = wn_cal
        spectrum.calibrate_intensity(R_setup = R_setup,
                                      dark_counts = notch_cts,
                                      exposure = spectrum.cycle_time)
        spectrum_avg += spectrum.y
        counter += 1
        
spectrum_avg = spectrum_avg/counter
       
## Plot

spectrum = SERS.SERS_Spectrum(x = wn_cal, y = spectrum_avg)
spectrum.normalise()
spectrum.plot(ax = ax, plot_y = spectrum.y_norm, title = '633nm SERS - 400l/mm Grating', linewidth = 2, label = 'Co-TAPP-SMe MLAgg')


# Labeling & plotting

ax.legend()
ax.set_ylim(-0.1, 1.1)
plt.tight_layout(pad = 0.8)


# Save

# save_dir = r'C:\Users\il322\Desktop\Offline Data\_'
# plt.savefig(save_dir + 'CH_Stretch_Norm' + '.svg', format = 'svg')
# plt.close(fig)


#%% Plot same as above but uncalibrated


fig, ax = plt.subplots(1,1,figsize=[12,9])
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('SERS Intensity (cts/mW/s)')


# BPT

spectrum = my_h5['400_grating']['BPT_633nm_400grating']
## x-axis truncation, calibration
spectrum = SERS.SERS_Spectrum(spectrum)
spectrum.x = spt.wl_to_wn(spectrum.x, 632.8)
spectrum.normalise(norm_y = spectrum.y)
spectrum.plot(ax = ax, plot_y = spectrum.y_norm, title = '633nm SERS - 400l/mm Grating Uncalibrated', linewidth = 2, label = 'BPT Ref')


# Si

spectrum = my_h5['400_grating']['Si_633nm_400grating']
## x-axis truncation, calibration
spectrum = SERS.SERS_Spectrum(spectrum)
spectrum.x = spt.wl_to_wn(spectrum.x, 632.8)
spectrum.normalise(norm_y = spectrum.y)
spectrum.plot(ax = ax, plot_y = spectrum.y_norm, title = '633nm SERS - 400l/mm Grating Uncalibrated', linewidth = 2, label = 'Si Ref')


# Co-TAPP-SMe MLAgg Avg x15

particle = my_h5['400_grating']

## Avg all Co-TAPP-SMe kinetic scans

keys = list(particle.keys())
keys = natsort.natsorted(keys)
spectrum_avg = np.zeros(spectrum.y.shape)
counter = 0

for key in keys:
    if '633nm_20uW' in key:
        ## x-axis truncation, calibration
        spectrum = particle[key]
        spectrum = SERS.SERS_Timescan(spectrum)
        spectrum.x = spt.wl_to_wn(spectrum.x, 632.8)
        spectrum_avg += spectrum.y
        counter += 1
        
spectrum_avg = spectrum_avg/counter
       
## Plot

spectrum = SERS.SERS_Spectrum(x = spectrum.x, y = spectrum_avg)
spectrum.normalise()
spectrum.plot(ax = ax, plot_y = spectrum.y_norm, title = '633nm SERS - 400l/mm Grating Uncalibrated', linewidth = 2, label = 'Co-TAPP-SMe MLAgg')


# Labeling & plotting

ax.legend()
ax.set_ylim(-0.1, 1.1)
plt.tight_layout(pad = 0.8)


# Save

# save_dir = r'C:\Users\il322\Desktop\Offline Data\_'
# plt.savefig(save_dir + 'CH_Stretch_Norm_Uncalibrated' + '.svg', format = 'svg')
# plt.close(fig)

