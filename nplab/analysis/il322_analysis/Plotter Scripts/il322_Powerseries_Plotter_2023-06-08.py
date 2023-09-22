# -*- coding: utf-8 -*-
"""
Created on Wed Apr 26 18:32:45 2023

@author: il322

Plotter for M-TAPP-SMe kinetic powerseries from 


This does a lot:
    - Plots kinetic powerseries of M-TAPP-SMe NPoMs -> plots split into 4 for better cmap scaling across large range of powers


Need to work on:
    - Spectral calibration:
        improved using scipy find_peaks()
        Need better way to calibrate anti-Stokes
        Re-implement in calibraation module
        
    - Timescan functions:
        extract nanocavity should have Y_raw option
        normalisation functions should be able to accept y_baselined, y_smooth, etc
        add baselining and smoothing functions to sers module
        extracr std function can be incorporated into extract nanocavity
            also need Y_raw option
            extracting std is not great at low powers because of noise
                can try smooth & subtract before but then we lose flare deviation
        
            
    - powerseries class
        add plotting functions from here to class in sers tools module
        
    Loop over all particles and save plots!
        powerseries kinetix timescan
        extracted nanocavity powerseries + integrated std per power
            power normalized & raw power
        dark field screening
    

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
my_h5 = h5py.File(r"C:\Users\il322\Desktop\Offline Data\2023-05-22_M-TAPP-SME_80nm_NPoM_Track_DF_633nmPowerseries.h5")
h5_785 = h5py.File(r"C:\Users\il322\Desktop\Offline Data\2023-05-29_M-TAPP_SMe_100nm_NPoM_Track_DF_785nmPowerseries.h5")
#truncate_range = [185]
notch_range = [337, 389]

#%% Get wn_cal

'''
Made progress with this by doing the following:
    
    - find peaks on separate no notch spectrum (BPT ref Stokes)
    - find peaks using scipy.signal.find_peaks
    - careful with peak assignment - first2 low wavenumber peaks are quite small in measured spectra (after notch artefact)
'''

bpt_ref_633nm = my_h5['ref_meas']['BPT_NPoM_633nm_1s_690cnwln_Grating2']
bpt_ref_no_notch = SERS.SERS_Spectrum(bpt_ref_633nm) # No notch spectrum for finding peaks
bpt_ref_633nm = SERS.SERS_Spectrum(bpt_ref_633nm)

## Convert to wn
bpt_ref_633nm.x = spt.wl_to_wn(bpt_ref_633nm.x, 632.8)
bpt_ref_no_notch.x = spt.wl_to_wn(bpt_ref_no_notch.x, 632.8)
bpt_ref_no_notch.truncate(start_x = 200, end_x = None)

## Truncate out notch (use this truncation for all spectra!)
#bpt_ref_633nm.truncate(truncate_range[0], None)

# bpt_ref_633nm.y_smooth = spt.butter_lowpass_filt_filt(bpt_ref_633nm.y,
#                                                         cutoff=2000,
#                                                         fs = 40000,
#                                                         order=2)

## Smooth no notch ref for peak finding
bpt_ref_no_notch.y_baselined = bpt_ref_no_notch.y -  spt.baseline_als(y=bpt_ref_no_notch.y,lam=1e1,p=1e-4,niter=1000)
bpt_ref_no_notch.y_smooth = spt.butter_lowpass_filt_filt(bpt_ref_no_notch.y_baselined,
                                                        cutoff=2000,
                                                        fs = 40000,
                                                        order=2)

# plt.plot(bpt_ref_633nm.x, bpt_ref_633nm.y)
# plt.plot(bpt_ref_no_notch.x, bpt_ref_no_notch.y, linestyle = 'dashed')
# plt.plot(bpt_ref_no_notch.x, bpt_ref_no_notch.y_baselined)
# plt.plot(bpt_ref_no_notch.x, bpt_ref_no_notch.y_smooth)
# plt.show()

'''
This still needs work. Either get neon or BPT working
scipy.signal.find_peaks is much more robust - try to incorporate into calibration tools
'''

## Find peaks in no notch smoothed spectrum
ref_peaks = find_peaks(bpt_ref_no_notch.y_smooth, height = bpt_ref_no_notch.y.max() * 0.013, distance = 10)
ref_wn = bpt_ref_no_notch.x[ref_peaks[0]]
print(ref_wn)
plt.plot(bpt_ref_no_notch.x, bpt_ref_no_notch.y_smooth)
for wn in ref_wn:
    plt.scatter(wn, bpt_ref_no_notch.y_smooth[(np.where(np.round(bpt_ref_no_notch.x, 8) == np.round(wn,8)))])
plt.xlim(0,)
plt.show()

# ref_wn_633nm = [200.82171233, 259.786324, 464.73913479, 638.40365652,
#                 866.39766658, 973.6162754, 1050.9464265, 1135.431746,
#                 1258.29258901, 1455.74357538, 1557.99121454]

# ref_wn_633nm = [250.74671053, 380.77518622,  460.34406507,  685.43919579,  799.60053094,
#                 866.39766658, 1050.9464265,  1139.42891279, 
#                 1254.3651391, 1459.55929794, 1557.99121454]

# ref_wn_633nm_bpt_no_notch = [255.2685689, 380.77518622, 460.34406507, 638.40365652,
#                 866.39766658, 969.52147062, 1050.9464265,
#                 1135.431746,  1258.29258901, 1455.74357538,
#                 1557.99121454]

ref_wn_633nm_bpt_no_notch = [380.77518622, 460.34406507, 638.40365652, 799.60053094,
                866.39766658, 969.52147062, 1050.9464265,
                1135.431746,  1258.29258901, 1455.74357538,
                1557.99121454]

## Get calibrated wavenumbers
wn_cal_633 = cal.run_spectral_calibration(bpt_ref_633nm, ref_wn = ref_wn_633nm_bpt_no_notch, deg=2, ref_threshold=0.1)

#%% Testing neon calibration

'''
Kinda works, but doesn't match with nanocavity.csv
'''

# def neon_calibration(wls_meas, neon_spec_meas, threshold = 0.03, distance = 10, deg = 2):
    
#     # Neon wavelengths taken from http://www.astrosurf.com/buil/us/spe2/calib2/neon1.gif
#     neon_wls = np.array([585.249, 588.189, 594.483, 597.553, 603, 607.434, 609.616, 614.306, 616.359, 621.728, 626.649, 630.479, 633.443, 638.299, 640.225, 650.653, 653.288, 659.895, 667.828, 671.704, 692.947, 703.241, 717.394, 724.517, 743.89])

#     # find peaks in measured neon spectrum
#     neon_peaks_meas = find_peaks(neon_spec_meas, height = threshold*np.max(neon_spec_meas), distance = distance)
#     wls_neon_peaks_meas = wls_meas[neon_peaks_meas[0]]
    
#     plt.plot(wls_meas, neon_spec_meas)
    
#     neon_wls_list = np.zeros(len(wls_neon_peaks_meas))
#     #print(wls_neon_peaks_meas)
#     for i, meas_wl in enumerate(wls_neon_peaks_meas):
#         #print(meas_wl)
#         neon_wls_list[i] = neon_wls[np.argmin(np.abs(neon_wls - meas_wl))]
#         plt.scatter(meas_wl, neon_spec_meas[np.where(np.round(wls_meas,8) == np.round(meas_wl,8))])
#     #print('measured wls: ' + str(np.round(wls_neon_peaks_meas,2)))
#     #print('literature wls: ' + str(np.round(neon_wls_list,2)))
    
#     #print(np.where(np.round(wls_meas, 8) == np.round(meas_wl, 8)))
#     plt.show()
    
    
    
#     # fit neon wavelengths (linear)
#     slope_offset, wl_offset = np.polyfit(neon_wls_list, wls_neon_peaks_meas, 1, rcond=None, full=False, w=None, cov=False)

#     # Calculate coefficienct of determination for neon fit    
#     corr_matrix = np.corrcoef(wls_neon_peaks_meas, slope_offset*neon_wls_list + wl_offset)
#     corr = corr_matrix[0,1]
#     R_sq = corr**2
    
#     # plt.figure(figsize=(8,6), dpi=300)
#     # plt.plot(neon_wls_list, wls_neon_peaks_meas, '.')
#     # plt.plot(neon_wls_list, slope_offset*neon_wls_list + wl_offset, '-')
#     # plt.xlabel('Neon wavelengths - Literature')
#     # plt.ylabel('Neon wavelengths - Measured')
#     # plt.figtext(0.5,0.3,'R$^{2}$: ' + str(R_sq))
#     # plt.tight_layout()
#     # plt.show()    
    


#     print(wls_neon_peaks_meas)
#     print(neon_wls_list)
        
#     # Fit literature peak positions to measured peak positions
#     a = np.polyfit(wls_neon_peaks_meas, neon_wls_list, deg=deg)
    
#     # Calculate the calibrated wavenumbers using the fitted coefficients
#     wl_cal = 0
#     for i in range(0, len(a)):
#         wl_cal = wl_cal + a[i] * wls_meas**(deg-i)
    
#     plt.figure(figsize=[10,6], dpi=1000) 
#     plt.plot(wls_neon_peaks_meas, neon_wls_list, '.')
#     cal_peak = 0
#     for i in range(0, len(a)):
#         cal_peak = cal_peak + a[i] * wls_neon_peaks_meas**(deg-i)
#     plt.plot(wls_neon_peaks_meas, cal_peak, '-')
#     plt.xlabel('Peak Positions (cm$^{-1}$) - Measured')
#     plt.ylabel('Peak Positions (cm$^{-1}$) - Literature')
#     #plt.tight_layout()
#     plt.show() 
    
#     #return R_sq
#     #return (wls_meas - wl_offset)/slope_offset
#     return wl_cal
    
# neon_spec = my_h5['ref_meas']['neon_lamp_0.2sx10scans']
# neon_spec = SERS.SERS_Spectrum(neon_spec.attrs['wavelengths'], neon_spec[5])

# wl_cal_633nm = neon_calibration(neon_spec.x, neon_spec.y, threshold = 0.1, distance = 40, deg = 3)

# #plt.plot(neon_spec.x, neon_spec.y/neon_spec.y_smooth)

# wn_cal_633nm = spt.wl_to_wn(wl_cal_633nm, 632.8)
# bpt_ref_633nm.normalise()
# plt.plot(wn_cal_633nm, bpt_ref_633nm.y_norm)

# data_dir = r'C:\Users\il322\Desktop\Offline Data'
# file_name = r'nanocavity_spectrum_BPT.csv'
# os.chdir(data_dir)
# lit_spectrum = np.loadtxt(file_name,skiprows=1,delimiter=',')
# lit_spectrum = spt.Spectrum(x=lit_spectrum[:,1], y=lit_spectrum[:,0])

# #lit_spectrum.x = spt.wn_to_wl(lit_spectrum.x, 632.8)

# plt.plot(lit_spectrum.x, lit_spectrum.y)
# plt.xlim(0,1600)
#%% Get R_setup

white_ref_633nm = my_h5['ref_meas']['white_scatt_0.0005sx10scans_690cnwln_Grating2']
white_ref_633nm = SERS.SERS_Spectrum(white_ref_633nm.attrs['wavelengths'], white_ref_633nm[5], title = 'White Scatterer')

## Convert to wn
#white_ref_633nm.x = spt.wl_to_wn(white_ref_633nm.x, 632.8)

## Truncate out notch (same range as BPT ref above)
#white_ref_633nm.truncate(truncate_range[0], truncate_range[1])

## Convert back to wl for efficiency calibration
white_ref_633nm.x = spt.wn_to_wl(white_ref_633nm.x, 632.8)
# white_ref_633nm.plot()

## Get white background counts in notch
notch = SERS.SERS_Spectrum(white_ref_633nm.x_raw[notch_range[0]:notch_range[1]], white_ref_633nm.y_raw[notch_range[0]:notch_range[1]], name = 'White Scatterer Notch') 
# notch.plot()
notch_cts = notch.y.mean()

## Calculate R_setup
R_setup_633nm = cal.white_scatter_calibration(wl = white_ref_633nm.x,
                                              white_scatter = white_ref_633nm.y,
                                              white_bkg = notch_cts,
                                              plot=False,
                                              start_notch = notch_range[0]-20,
                                              end_notch = notch_range[1]+20)

## Get dark counts
dark_cts = my_h5['ref_meas']['dark_spectrum_0.2sx10scans_690cnwln_Grating2']
dark_cts = SERS.SERS_Spectrum(wn_cal_633, dark_cts[5], title = 'Dark Counts')
# dark_cts.plot()
plt.show()

## Test R_setup with BPT reference
# plt.plot(bpt_ref_633nm.x, bpt_ref_633nm.y - dark_cts.y, color = (0.8,0.1,0.1,0.7), label = 'Raw spectrum')
# plt.plot(bpt_ref_633nm.x, (bpt_ref_633nm.y - dark_cts.y)/R_setup_633nm, color = (0,0.6,0.2,0.5), label = 'Efficiency-corrected')
# plt.legend(fontsize='x-small')
# plt.show()
        

#%% Spectral calibration 785nm
truncate_range_785 = [-2000, 2300]

bpt_ref = h5_785['ref_meas']['BPT_785nm_ref_1s_1']
bpt_ref_no_notch = SERS.SERS_Spectrum(bpt_ref) # No notch spectrum for finding peaks
bpt_ref = SERS.SERS_Spectrum(bpt_ref)

## Convert to wn
bpt_ref.x = spt.wl_to_wn(bpt_ref.x, 785)
bpt_ref_no_notch.x = spt.wl_to_wn(bpt_ref_no_notch.x, 785)
bpt_ref_no_notch.truncate(start_x = 200, end_x = None)

## Truncate out notch (use this truncation for all spectra!)
bpt_ref.truncate(truncate_range_785[0], truncate_range_785[1])

# bpt_ref.y_smooth = spt.butter_lowpass_filt_filt(bpt_ref.y,
#                                                         cutoff=2000,
#                                                         fs = 40000,
#                                                         order=2)

## Smooth no notch ref for peak finding
bpt_ref_no_notch.y_baselined = bpt_ref_no_notch.y -  spt.baseline_als(y=bpt_ref_no_notch.y,lam=1e1,p=1e-4,niter=1000)
# bpt_ref_no_notch.y_smooth = spt.butter_lowpass_filt_filt(bpt_ref_no_notch.y_baselined,
#                                                         cutoff=2000,
#                                                         fs = 40000,
#                                                         order=2)

# plt.plot(bpt_ref.x, bpt_ref.y)
# plt.plot(bpt_ref_no_notch.x, bpt_ref_no_notch.y, linestyle = 'dashed')
# plt.plot(bpt_ref_no_notch.x, bpt_ref_no_notch.y_baselined)
# #plt.plot(bpt_ref_no_notch.x, bpt_ref_no_notch.y_smooth)
# plt.show()

'''
This still needs work. Either get neon or BPT working
scipy.signal.find_peaks is much more robust - try to incorporate into calibration tools
'''

## Find peaks in no notch smoothed spectrum
ref_peaks = find_peaks(bpt_ref_no_notch.y_baselined, height = bpt_ref_no_notch.y.max() * 0.01, distance = 9)
ref_wn = bpt_ref_no_notch.x[ref_peaks[0]]
print(ref_wn)
plt.plot(bpt_ref_no_notch.x, bpt_ref_no_notch.y_baselined)
for wn in ref_wn:
    plt.scatter(wn, bpt_ref_no_notch.y_baselined[(np.where(np.round(bpt_ref_no_notch.x, 8) == np.round(wn,8)))])
plt.xlim(0,)
plt.show()

ref_wn_785 = [369.40221262,  439.14233319, 508.08493853, 717.62264771,
              790.69468573,  962.42311146, 1046.41098591, 1156.51227542,
              1244.42080332, 1442.17333713, 1551.17382617]

## Get calibrated wavenumbers
wn_cal_785 = cal.run_spectral_calibration(bpt_ref, ref_wn = ref_wn_785, deg=2, ref_threshold=0.1)


#%% R_setup 785nm

white_ref_785 = h5_785['ref_meas']['white_scatt_785nmcnwln_0.001sx10scans']
white_ref_785 = SERS.SERS_Spectrum(white_ref_785.attrs['wavelengths'], white_ref_785[5], title = 'White Scatterer')

## Convert to wn
white_ref_785.x = spt.wl_to_wn(white_ref_785.x, 785)

## Truncate out notch (same range as BPT ref above)
white_ref_785.truncate(truncate_range_785[0], truncate_range_785[1])

## Convert back to wl for efficiency calibration
white_ref_785.x = spt.wn_to_wl(white_ref_785.x, 785)
# white_ref_785.plot()

## Get white background counts in notch
notch_range = [205, 219]
notch = SERS.SERS_Spectrum(white_ref_785.x_raw[notch_range[0]:notch_range[1]], white_ref_785.y_raw[notch_range[0]:notch_range[1]], name = 'White Scatterer Notch') 
# notch.plot()
notch_cts = notch.y.mean()

## Calculate R_setup
R_setup_785 = cal.white_scatter_calibration(wl = white_ref_785.x,
                                              white_scatter = white_ref_785.y,
                                              white_bkg = notch_cts,
                                              plot=False,
                                              start_notch = notch_range[0]-20,
                                              end_notch = notch_range[1]+5)

## Get dark counts
dark_cts_785 = h5_785['ref_meas']['dark_spectrum_0.2sx10scans']
dark_cts_785 = SERS.SERS_Spectrum(dark_cts_785.attrs['wavelengths'], dark_cts_785[5], title = 'Dark Counts')
dark_cts_785.x = spt.wl_to_wn(dark_cts_785.x, 785)
dark_cts_785.truncate(truncate_range_785[0], truncate_range_785[1])
dark_cts.x = wn_cal_785
# dark_cts_785.plot()
# plt.show()

## Test R_setup with BPT reference
# plt.plot(bpt_ref.x, bpt_ref.y - dark_cts_785.y, color = (0.8,0.1,0.1,0.7), label = 'Raw spectrum')
# plt.plot(bpt_ref.x, (bpt_ref.y - dark_cts_785.y)/R_setup_785, color = (0,0.6,0.2,0.5), label = 'Efficiency-corrected')
# plt.legend(fontsize='x-small')
# plt.show()


#%% Get wn_cal Stokes 633nm

'''
Made progress with this by doing the following:
    
    - find peaks on separate no notch spectrum (BPT ref Stokes)
    - find peaks using scipy.signal.find_peaks
    - careful with peak assignment - first2 low wavenumber peaks are quite small in measured spectra (after notch artefact)
'''

bpt_ref_633nm = my_h5['ref_meas']['BPT_NPoM_633nm_1s_690cnwln_Grating2']
bpt_ref_stokes = SERS.SERS_Spectrum(bpt_ref_633nm) # No notch spectrum for finding peaks
bpt_ref_633nm = SERS.SERS_Spectrum(bpt_ref_633nm)

## Convert to wn
bpt_ref_633nm.x = spt.wl_to_wn(bpt_ref_633nm.x, 632.8)
bpt_ref_stokes.x = spt.wl_to_wn(bpt_ref_stokes.x, 632.8)
bpt_ref_stokes.truncate(start_x = 300, end_x = None)

## Truncate out notch (use this truncation for all spectra!)
#bpt_ref_633nm.truncate(truncate_range[0], None)

# bpt_ref_633nm.y_smooth = spt.butter_lowpass_filt_filt(bpt_ref_633nm.y,
#                                                         cutoff=2000,
#                                                         fs = 40000,
#                                                         order=2)

## Smooth no notch ref for peak finding
bpt_ref_stokes.y_baselined = bpt_ref_stokes.y -  spt.baseline_als(y=bpt_ref_stokes.y,lam=1e1,p=1e-4,niter=1000)
bpt_ref_stokes.y_smooth = spt.butter_lowpass_filt_filt(bpt_ref_stokes.y_baselined,
                                                        cutoff=3000,
                                                        fs = 40000,
                                                        order=2)

# plt.plot(bpt_ref_633nm.x, bpt_ref_633nm.y)
# plt.plot(bpt_ref_stokes.x, bpt_ref_stokes.y, linestyle = 'dashed')
# plt.plot(bpt_ref_stokes.x, bpt_ref_stokes.y_baselined)
# plt.plot(bpt_ref_stokes.x, bpt_ref_stokes.y_smooth)
# plt.show()

'''
This still needs work. Either get neon or BPT working
scipy.signal.find_peaks is much more robust - try to incorporate into calibration tools
'''

## Find peaks in no notch smoothed spectrum
ref_peaks = find_peaks(bpt_ref_stokes.y_smooth, height = bpt_ref_stokes.y.max() * 0.000001, distance = 1)
ref_wn = bpt_ref_stokes.x[ref_peaks[0]]
print(ref_wn)
plt.plot(bpt_ref_stokes.x, bpt_ref_stokes.y_smooth)
for wn in ref_wn:
    plt.scatter(wn, bpt_ref_stokes.y_smooth[(np.where(np.round(bpt_ref_stokes.x, 8) == np.round(wn,8)))])
plt.xlim(0,)
plt.show()

# ref_wn_633nm = [200.82171233, 259.786324, 464.73913479, 638.40365652,
#                 866.39766658, 973.6162754, 1050.9464265, 1135.431746,
#                 1258.29258901, 1455.74357538, 1557.99121454]

# ref_wn_633nm = [250.74671053, 380.77518622,  460.34406507,  685.43919579,  799.60053094,
#                 866.39766658, 1050.9464265,  1139.42891279, 
#                 1254.3651391, 1459.55929794, 1557.99121454]

# ref_wn_633nm_bpt_no_notch = [255.2685689, 380.77518622, 460.34406507, 638.40365652,
#                 866.39766658, 969.52147062, 1050.9464265,
#                 1135.431746,  1258.29258901, 1455.74357538,
#                 1557.99121454]

ref_wn_633nm_bpt_no_notch = [380.77518622, 464.73913479, 521.63534533, 638.40365652,
                866.39766658, 969.52147062, 1050.9464265,
                1135.431746,  1258.29258901, 1455.74357538,
                1557.99121454]

## Get calibrated wavenumbers
wn_cal_633_stokes = cal.run_spectral_calibration(bpt_ref_stokes, ref_wn = ref_wn_633nm_bpt_no_notch, deg=2, ref_threshold=0.1)
     

#%% Standardize the names of calibration variables

h5_633 = my_h5
wn_cal_633 = wn_cal_633
dark_cts_633 = dark_cts
R_setup_633 = R_setup_633nm
truncate_range_633 = None

h5_785 = h5_785
wn_cal_785 = wn_cal_785
dark_cts_785 = dark_cts_785
R_setup_785 = R_setup_785
truncate_range_785 = [-2000, 2300]
#%%

def baseline_timescan(timescan, timescan_y = None, lam = 1e4, p = 1e-4, niter = 10):
    
    
    if timescan_y is None:
        timescan_y = timescan.Y.copy()
    else:
        timescan_y = timescan_y.copy()
    
    timescan.Y_baselined = timescan_y.copy()
    timescan.Y_background = timescan_y.copy()
    
    for i, spectrum in enumerate(timescan_y):
        timescan.Y_background[i] = spt.baseline_als(spectrum, lam, p, niter)
        timescan.Y_baselined[i] = spectrum - timescan.Y_background[i]
        
    return timescan
    

#%%    
def smooth_timescan(timescan, timescan_y = None, cutoff = 1000, fs = 30000, order = 1):
    
    
    if timescan_y is None:
        timescan_y = timescan.Y.copy()
    else:
        timescan_y = timescan_y.copy()
    
    timescan.Y_smooth = timescan_y.copy()
    
    for i, spectrum in enumerate(timescan_y):
        spectrum_smooth = spt.butter_lowpass_filt_filt(spectrum, cutoff = cutoff, fs = fs, order = order)
        timescan.Y_smooth[i] = spectrum_smooth
        
    return timescan

#%% Function to get std per pixel in timescan - can move to SERS_Timescan class

def std_per_pixel(timescan, timescan_y = None, x_range = [None, None]):
    
    '''
    Needs docstring
    Needs option for using Y_raw
    Add to sers tools module
    '''
    
    
    # Get y axis to use
    
    if timescan_y is None:
        timescan_y = timescan.Y.copy()
    else:
        timescan_y = timescan_y.copy()
    
    
    # Calculate standard deviation per pixel across timescan
    
    pixel_std = np.zeros(len(timescan.x))
    for pixel in range(0, len(timescan.x)):
        
        pixel_std[pixel] = np.std(timescan_y[:,pixel])
    
    
    ## Integrate standard deviation of spectrum
    
    timescan.int_std = np.sum(pixel_std[x_range[0]: x_range[1]])
    
    timescan.avg_std = timescan.int_std / len(pixel_std[x_range[0]: x_range[1]]) # Average std per pixel
    print(len(pixel_std[x_range[0]: x_range[1]]))
    timescan.std_spectrum = SERS.SERS_Spectrum(timescan.x, pixel_std)
    
    return timescan


#%%

def process_powerseries(my_h5, particle_scan_name, particle_name, laser_wln,
                        sample_name, wn_cal, R_setup, dark_counts, truncate_range = None):
    
    '''
    Needs docstring
    Pre-processing powerseries from h5 data
    '''
    
    # Get particle
    
    particle = my_h5[particle_scan_name][particle_name]
    
    
    # Process powerseries (list of timescans)
    
    powerseries = []
    
    ## Loop over timescans in particle, add to powerseris
    for item in natsort.natsorted(particle.keys()):
       
        if 'Powerseries' in item:
            
            ### Process timescan (x-cal, y-cal), add to powerseries
            timescan = SERS.SERS_Timescan(particle[item])
            if truncate_range is not None:
                timescan.x = spt.wl_to_wn(timescan.x, laser_wln)
                timescan.truncate(truncate_range[0], truncate_range[1])
                timescan.Y_raw = timescan.Y.copy()
            timescan.x = wn_cal
            timescan.calibrate_intensity(R_setup = R_setup, dark_counts = dark_counts.y)
            timescan = smooth_timescan(timescan)
            powerseries.append(timescan)
            
    return powerseries


#%%%

def plot_kinetic_powerseries(powerseries, particle_scan_name, particle_name, 
                             laser_wln, sample_name, n_plots = 4, 
                             v_mins = None, v_maxs = None, save_dir = None):
    
    '''
    Needs docstring
    Plot kinetic powerseries on 1 x n_plots plots
    '''
    
    ## Create powerseries_Y (stitch together all timescan.Y)
    for i, timescan in enumerate(powerseries):
        if i == 0:    
            powerseries_Y = powerseries[0].Y
        else:
            powerseries_Y = np.append(powerseries_Y, powerseries[i].Y, axis = 0) 
    
    
    # Plot kinetic powerseries in 1 x 4 plot
           
    fig, ax = plt.subplots(1, n_plots, figsize=[20*4,30])
    cmap = plt.get_cmap('inferno')
    
    ## Plot labeling
    fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + str(sample_name) + '\n' + str(particle_scan_name) + ': ' + str(particle_name), fontsize = 80, y = 1)
    
    if n_plots == 4:
        ''' Need to generalize this part'''
        if laser_wln == 633:
            ax[0].set_title('~0.1 - 1 $\mu$W', fontsize = 70)
            ax[1].set_title('~1 - 10 $\mu$W', fontsize = 70)
            ax[2].set_title('~10- 100$\mu$W', fontsize = 70)
            ax[3].set_title('~100$\mu$W - 1mW', fontsize = 70)
            
        elif laser_wln == 785:
            ax[0].set_title('~0.1 - 1 $\mu$W', fontsize = 70)
            ax[1].set_title('~1 - 10 $\mu$W', fontsize = 70)
            ax[2].set_title('~10$\mu$W', fontsize = 70)
            ax[3].set_title('~10 - 100$\mu$W', fontsize = 70)
    
    ## Split powerseries_Y into n_plots and get vlims
    split = np.split(powerseries_Y, n_plots)
    if v_mins is None:
        v_mins = [None] * n_plots
        for i, series in enumerate(split):
            v_mins[i] = np.percentile(split, 1)
    if v_maxs is None:
        v_maxs = [None] * n_plots
        for i, series in enumerate(split):
            v_maxs[i] = np.percentile(series, 96.5)
    
    ## Loop over each axis
    plot_per_ax = len(powerseries)/len(ax)
    for ax_i, ax in enumerate(ax):
        
        ### Loop over timescans that go on each axis
        for i, timescan in enumerate(powerseries[int(ax_i * plot_per_ax) : int((ax_i * plot_per_ax) + plot_per_ax)]):
            
            #### Plot timescan & label laser power
            pcm = ax.pcolormesh(timescan.x, timescan.t + (i*timescan.t.max()), timescan.Y, vmin = v_mins[ax_i], vmax = v_maxs[ax_i], cmap = cmap, rasterized = True)
            ax.text(x = (timescan.x.min() - 860), y = (timescan.t.max() * (i + 0.5)) , s = str(timescan.laser_power) + 'mW', fontsize = 30)
            
        ### Axis labeling 
        ax.set_xlabel(r'Raman shifts (cm$^{-1}$)', fontsize=40)
        ax.tick_params(axis='x', which='major', labelsize=30)   
        ax.text(x = (timescan.x.min() - 1260), y = (timescan.t.max() * plot_per_ax - 8) , s = 'Laser power', fontsize = 40)
        ax.get_yaxis().set_visible(False)
        clb = fig.colorbar(pcm, ax = ax, pad = 0, format='%.0e')
        clb.ax.tick_params(labelsize = 30)
        clb.set_label(label = 'SERS Intensity (a.u.)', size = '40', rotation = 270, labelpad=50)
    
    plt.tight_layout()
    
    if save_dir is None:
        plt.show()
    else:
        plt.savefig(save_dir + '/Kinetic SERS Powerseries ' + particle_scan_name + ' ' + particle_name + '.svg', format = 'svg')


#%%

def process_powerseries_nanocavity(powerseries, timescan_y_str, laser_wln, calibrate_power = False):

    
    # Process nanocavity powerseries
    
    ## Loop over each timescan in powerseries
    for i, timescan in enumerate(powerseries):
    
        ### Get timescan_y to use for processing 
        timescan_y = getattr(timescan, timescan_y_str)
    
        ### Extract timescan nanocavity using raw y-data
        timescan.extract_nanocavity(timescan_y = timescan_y)
        
        ### Take Stokes of nanocavity_spectrum, baseline, smooth, set min to 0
        if laser_wln == 633:
            timescan.nanocavity_spectrum.truncate(1200, 1700)
        else:
            timescan.nanocavity_spectrum.truncate(500, 2000)
        timescan.nanocavity_spectrum.y_baselined = timescan.nanocavity_spectrum.y - spt.baseline_als(timescan.nanocavity_spectrum.y, 1e3, 1e-3, niter = 10)
        if timescan.laser_power < 0.001:
            fs = 20000
        else:
            fs = 10000
        timescan.nanocavity_spectrum.y_smooth = spt.butter_lowpass_filt_filt(timescan.nanocavity_spectrum.y_baselined, 2000, fs, 1)        
        timescan.nanocavity_spectrum.y_smooth -= timescan.nanocavity_spectrum.y_smooth[20:480].min()
        ## Optional power calibration
        if calibrate_power == True:
            timescan.nanocavity_spectrum.y_smooth /= (timescan.laser_power * timescan.exposure)
        
        ### Process spectral deviation (raw)
        timescan = std_per_pixel(timescan, timescan_y = timescan_y)
        

    return powerseries


#%%

def plot_nanocavity_powerseries(powerseries, ax = None, save_dir = None, 
                                int_std = False, ax_std = None,
                                laser_wln = '', offset = 0,
                                particle_scan_name = '', particle_name = '',
                                powerseries_range = [0,20], y_label = 'raw'):
    
    
    if ax is None:
        if int_std == False:
            fig, ax = plt.subplots(1, 1, figsize=[8,6])
        else:
            fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
            ax_std = ax[1]
            ax = ax[0]
        fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)        
    my_cmap = plt.get_cmap('plasma')
    

    # Plot nanocavity powerseries + spectral deviation
    
    ## Plot nanocavity powerseries
    for i, timescan in enumerate(powerseries[powerseries_range[0]: powerseries_range[1]]):
        color = my_cmap((powerseries_range[0]+i)/20)
        ax.plot(timescan.nanocavity_spectrum.x, timescan.nanocavity_spectrum.y_smooth + offset*i, linewidth = '1', zorder = (20/(i+1)), color = color, label = str(timescan.laser_power) + 'mW')
    
    ## Plot labeling
    ax.legend(fontsize = 11, ncol = 4, loc = 'upper left')
    ax.set_xlim(1200, 1700)
    if y_label == 'raw':
        ax.set_ylabel('SERS Intensity (raw counts)')
    elif y_label == 'power-norm':
        ax.set_ylabel('Power-Normalized SERS Intensity (a.u.)')
    else:
        ax.set_ylabel('Normalized SERS Intensity (a.u.)')
    ax.set_xlabel(r'Raman shifts (cm$^{-1}$)')
    ax.set_title('Extracted Nanocavity', fontsize = 'medium')
    ax.set_ylim(0,2.6)   
    
    if int_std == False:
        
        plt.tight_layout(pad = 1) 
        
        if save_dir is None:
            plt.show()
        else:
            if y_label == 'raw':
                plt.savefig(save_dir + '/Raw Nanocavity SERS Powerseries ' + particle_scan_name + ' ' + particle_name + '.svg', format = 'svg')
            elif y_label == 'power-norm':
                plt.savefig(save_dir + '/Power-Normalized Nanocavity SERS Powerseries ' + particle_scan_name + ' ' + particle_name + '.svg', format = 'svg')
            else:
                plt.savefig(save_dir + '/Normalized Nanocavity SERS Powerseries ' + particle_scan_name + ' ' + particle_name + '.svg', format = 'svg')

            
    # Plot integrated std v power (raw)

    else:     
            
        ax_std.set_xlim(1e-4, 2)
        if y_label == 'raw':
            ax_std.set_ylabel(r'$\Sigma$ $\sigma _{Raw}$ $_{SERS}$ $_{Intensity}$', rotation = 270, labelpad = 30, fontsize = 'large')
        else:
            ax_std.set_ylabel(r'$\Sigma$ $\sigma _{SERS}$ $_{Intensity}$', rotation = 270, labelpad = 30, fontsize = 'large')

        ax_std.set_xlabel(r'Laser Power (mW)')
        ax_std.set_title('Spectral Deviation', fontsize = 'medium')
        for i, timescan in enumerate(powerseries[powerseries_range[0]: powerseries_range[1]]):
            color = my_cmap((powerseries_range[0]+i)/20)
            ax_std.scatter(timescan.laser_power, timescan.int_std/timescan.laser_power, color = color)
        ax_std.set_xscale('log')
        ax_std.set_yscale('log')
        ax_std.yaxis.tick_right()
        ax_std.yaxis.set_label_position("right")
        
        plt.tight_layout(pad = 1) 
        
        if save_dir is None:
            plt.show()
        else:
            if y_label == 'raw':
                plt.savefig(save_dir + '/Raw Nanocavity SERS Powerseries ' + particle_scan_name + ' ' + particle_name + '.svg', format = 'svg')
            else:
                plt.savefig(save_dir + '/Power-Normalized Nanocavity SERS Powerseries ' + particle_scan_name + ' ' + particle_name + '.svg', format = 'svg')


#%%

def process_DF_screening(my_h5, particle_scan_name, particle_name, save_dir):

    
    # DF Screening

    particle = my_h5[particle_scan_name][particle_name]    

    z_scan = None
    image = None
    
    for key in particle.keys():
        if 'z_scan' in key:
            z_scan = particle[key]
        if 'image' in key:
            image = particle[key]
    
    if z_scan is None:
        print(particle_name + ': Z-Scan not found')
        return
    
    z_scan = df.Z_Scan(z_scan)
    z_scan.condense_z_scan() # Condense z-scan into single df-spectrum
    ### Smoothing necessary for finding maxima
    z_scan.df_spectrum = df.DF_Spectrum(x = z_scan.x,
                                      y = z_scan.df_spectrum, 
                                      y_smooth = spt.butter_lowpass_filt_filt(z_scan.df_spectrum, cutoff = 1600, fs = 200000))
    z_scan.df_spectrum.test_if_npom()
    z_scan.df_spectrum.find_critical_wln()
        
    ## Run DF screening of particle
    #image = particle['CWL.thumb_image_0']
    z_scan.df_spectrum = df.df_screening(z_scan = z_scan,
                                      df_spectrum = z_scan.df_spectrum,
                                      image = image,
                                      tinder = False,
                                      plot = True,
                                      title = particle_name,
                                      save_file = save_dir + '/Darkfield Data ' + particle_scan_name + ' ' + particle_name + '.svg')

          
#%% Running above functions for multiple M-TAPP particle tracks

'''
Particle Scans for h5_633
0: 2023-05-10_H2-TAPP-SMe_80nm_NPoM
1-2: 2023-05-10_Co-TAPP-SMe_80nm_NPoM
3: 2023-03-23_Ni-TAPP-SMe_80nm_NPoM 
4- 5: 2023-03-23_Zn-TAPP-SMe_80nm_NPoM 
'''

'''
Particle Scans for h5_785
1: 2023-05-10_H2-TAPP-SMe
2: 2023-05-10_Co-TAPP-SMe
3-4: 2023-03-23_Ni-TAPP-SMe
5-10: 2023-03-23_Zn-TAPP-SMe_100nm_NPoM
'''


#%% Set variables for 633

my_h5 = h5_633
laser_wln = 633
wn_cal = wn_cal_633
R_setup = R_setup_633
dark_cts = dark_cts_633
truncate_range = truncate_range_633


#%% H2 633

# save_dir = r"C:\Users\il322\Desktop\Offline Data\2023-05-10_M-TAPP-SMe_NPoM\2023-05-12_M-TAPP-SMe_80nm_NPoM Powerseries_DF\633nm H2-TAPP-SMe 80nm NPoM"
# scan_list = ['ParticleScannerScan_0']
# sample_name = 'H2-TAPP-SMe 80nm NPoM'
# print('633nm H2')

# ## Loop over scan lists
# for particle_scan_name in scan_list:
#     print(particle_scan_name)
#     particle_scan = my_h5[particle_scan_name]
#     particle_list = natsort.natsorted(list(particle_scan.keys()))
    
#     ## Loop over particles in particle scan
#     for particle in particle_list:
#         if 'Particle' not in particle:
#             particle_list.remove(particle)
    
#     ## Loop over filtered particles in particle scan
#     for particle_name in particle_list:
#         print(particle_name)
        
#         ### Process powerseries
#         powerseries = process_powerseries(my_h5, particle_scan_name, 
#                                           particle_name, laser_wln,
#                                           sample_name, wn_cal, R_setup,
#                                           dark_cts, truncate_range)          
        
#         ### Plot kinetic powerseries
#         plot_kinetic_powerseries(powerseries, 
#                                  particle_scan_name, 
#                                  particle_name, 
#                                  laser_wln, 
#                                  sample_name, 
#                                  n_plots = 4, 
#                                  v_mins = None, 
#                                  v_maxs = None, 
#                                  save_dir = save_dir)

#         ### Raw Nanocavity & Deviation
#         powerseries_raw = process_powerseries_nanocavity(powerseries, 'Y_raw', laser_wln)
#         fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
#         fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)
#         plot_nanocavity_powerseries(powerseries_raw,
#                                     ax = ax[0],
#                                     save_dir = save_dir, 
#                                     int_std = True, 
#                                     ax_std = ax[1],
#                                     laser_wln = laser_wln,
#                                     particle_scan_name = particle_scan_name,
#                                     particle_name = particle_name,
#                                     y_label = 'raw')
        
#         ### Power norm Nanocavity & Deviation
#         powerseries_power_norm = process_powerseries_nanocavity(powerseries, 'Y', laser_wln, calibrate_power = True)
#         fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
#         fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)
#         plot_nanocavity_powerseries(powerseries_power_norm,
#                                     ax = ax[0],
#                                     save_dir = save_dir, 
#                                     int_std = True, 
#                                     ax_std = ax[1],
#                                     laser_wln = laser_wln,
#                                     particle_scan_name = particle_scan_name,
#                                     particle_name = particle_name,
#                                     y_label = 'power_norm')
        
#         ### DF Data
#         process_DF_screening(my_h5, particle_scan_name, particle_name, save_dir)
        
#         ### Cleanup
#         plt.close('all')
#         gc.collect() 

#%% Co 633

# save_dir = r"C:\Users\il322\Desktop\Offline Data\2023-05-10_M-TAPP-SMe_NPoM\2023-05-12_M-TAPP-SMe_80nm_NPoM Powerseries_DF\633nm Co-TAPP-SMe 80nm NPoM"
# scan_list = ['ParticleScannerScan_1', 'ParticleScannerScan_2']
# sample_name = 'Co-TAPP-SMe 80nm NPoM'
# print('633nm Co')

# ## Loop over scan lists
# for particle_scan_name in scan_list:
#     print(particle_scan_name)
#     particle_scan = my_h5[particle_scan_name]
#     particle_list = natsort.natsorted(list(particle_scan.keys()))
    
#     ## Loop over particles in particle scan
#     for particle in particle_list:
#         if 'Particle' not in particle:
#             particle_list.remove(particle)
    
#     ## Loop over filtered particles in particle scan
#     for particle_name in particle_list:
#         print(particle_name)
        
#         ### Process powerseries
#         powerseries = process_powerseries(my_h5, particle_scan_name, 
#                                           particle_name, laser_wln,
#                                           sample_name, wn_cal, R_setup,
#                                           dark_cts, truncate_range)          
        
#         ### Plot kinetic powerseries
#         plot_kinetic_powerseries(powerseries, 
#                                  particle_scan_name, 
#                                  particle_name, 
#                                  laser_wln, 
#                                  sample_name, 
#                                  n_plots = 4, 
#                                  v_mins = None, 
#                                  v_maxs = None, 
#                                  save_dir = save_dir)

#         ### Raw Nanocavity & Deviation
#         powerseries_raw = process_powerseries_nanocavity(powerseries, 'Y_raw', laser_wln)
#         fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
#         fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)
#         plot_nanocavity_powerseries(powerseries_raw,
#                                     ax = ax[0],
#                                     save_dir = save_dir, 
#                                     int_std = True, 
#                                     ax_std = ax[1],
#                                     laser_wln = laser_wln,
#                                     particle_scan_name = particle_scan_name,
#                                     particle_name = particle_name,
#                                     y_label = 'raw')
        
#         ### Power norm Nanocavity & Deviation
#         powerseries_power_norm = process_powerseries_nanocavity(powerseries, 'Y', laser_wln, calibrate_power = True)
#         fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
#         fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)
#         plot_nanocavity_powerseries(powerseries_power_norm,
#                                     ax = ax[0],
#                                     save_dir = save_dir, 
#                                     int_std = True, 
#                                     ax_std = ax[1],
#                                     laser_wln = laser_wln,
#                                     particle_scan_name = particle_scan_name,
#                                     particle_name = particle_name,
#                                     y_label = 'power_norm')
        
#         ### DF Data
#         process_DF_screening(my_h5, particle_scan_name, particle_name, save_dir)
        
#         ### Cleanup
#         plt.close('all')
#         gc.collect()
        
        
#%% Ni 633

# save_dir = r"C:\Users\il322\Desktop\Offline Data\2023-05-10_M-TAPP-SMe_NPoM\2023-05-12_M-TAPP-SMe_80nm_NPoM Powerseries_DF\633nm Ni-TAPP-SMe 80nm NPoM"
# scan_list = ['ParticleScannerScan_3']
# sample_name = 'Ni-TAPP-SMe 80nm NPoM'
# print('633nm Ni')

# ## Loop over scan lists
# for particle_scan_name in scan_list:
#     print(particle_scan_name)
#     particle_scan = my_h5[particle_scan_name]
#     particle_list = natsort.natsorted(list(particle_scan.keys()))
    
#     ## Loop over particles in particle scan
#     for particle in particle_list:
#         if 'Particle' not in particle:
#             particle_list.remove(particle)
    
#     ## Loop over filtered particles in particle scan
#     for particle_name in particle_list:
#         print(particle_name)
        
#         ### Process powerseries
#         powerseries = process_powerseries(my_h5, particle_scan_name, 
#                                           particle_name, laser_wln,
#                                           sample_name, wn_cal, R_setup,
#                                           dark_cts, truncate_range)          
        
#         ### Plot kinetic powerseries
#         plot_kinetic_powerseries(powerseries, 
#                                  particle_scan_name, 
#                                  particle_name, 
#                                  laser_wln, 
#                                  sample_name, 
#                                  n_plots = 4, 
#                                  v_mins = None, 
#                                  v_maxs = None, 
#                                  save_dir = save_dir)

#         ### Raw Nanocavity & Deviation
#         powerseries_raw = process_powerseries_nanocavity(powerseries, 'Y_raw', laser_wln)
#         fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
#         fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)
#         plot_nanocavity_powerseries(powerseries_raw,
#                                     ax = ax[0],
#                                     save_dir = save_dir, 
#                                     int_std = True, 
#                                     ax_std = ax[1],
#                                     laser_wln = laser_wln,
#                                     particle_scan_name = particle_scan_name,
#                                     particle_name = particle_name,
#                                     y_label = 'raw')
        
#         ### Power norm Nanocavity & Deviation
#         powerseries_power_norm = process_powerseries_nanocavity(powerseries, 'Y', laser_wln, calibrate_power = True)
#         fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
#         fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)
#         plot_nanocavity_powerseries(powerseries_power_norm,
#                                     ax = ax[0],
#                                     save_dir = save_dir, 
#                                     int_std = True, 
#                                     ax_std = ax[1],
#                                     laser_wln = laser_wln,
#                                     particle_scan_name = particle_scan_name,
#                                     particle_name = particle_name,
#                                     y_label = 'power_norm')
        
#         ### DF Data
#         process_DF_screening(my_h5, particle_scan_name, particle_name, save_dir)
        
#         ### Cleanup
#         plt.close('all')
#         gc.collect() 
        

#%% Zn 633

# save_dir = r"C:\Users\il322\Desktop\Offline Data\2023-05-10_M-TAPP-SMe_NPoM\2023-05-12_M-TAPP-SMe_80nm_NPoM Powerseries_DF\633nm Zn-TAPP-SMe 80nm NPoM"
# scan_list = ['ParticleScannerScan_4', 'ParticleScannerScan_5']
# sample_name = 'Zn-TAPP-SMe 80nm NPoM'
# print('633nm Zn')

# ## Loop over scan lists
# for particle_scan_name in scan_list:
#     print(particle_scan_name)
#     particle_scan = my_h5[particle_scan_name]
#     particle_list = natsort.natsorted(list(particle_scan.keys()))
    
#     ## Loop over particles in particle scan
#     for particle in particle_list:
#         if 'Particle' not in particle:
#             particle_list.remove(particle)
    
#     ## Loop over filtered particles in particle scan
#     for particle_name in particle_list:
#         print(particle_name)
        
#         ### Process powerseries
#         powerseries = process_powerseries(my_h5, particle_scan_name, 
#                                           particle_name, laser_wln,
#                                           sample_name, wn_cal, R_setup,
#                                           dark_cts, truncate_range)          
        
#         ### Plot kinetic powerseries
#         plot_kinetic_powerseries(powerseries, 
#                                  particle_scan_name, 
#                                  particle_name, 
#                                  laser_wln, 
#                                  sample_name, 
#                                  n_plots = 4, 
#                                  v_mins = None, 
#                                  v_maxs = None, 
#                                  save_dir = save_dir)

#         ### Raw Nanocavity & Deviation
#         powerseries_raw = process_powerseries_nanocavity(powerseries, 'Y_raw', laser_wln)
#         fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
#         fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)
#         plot_nanocavity_powerseries(powerseries_raw,
#                                     ax = ax[0],
#                                     save_dir = save_dir, 
#                                     int_std = True, 
#                                     ax_std = ax[1],
#                                     laser_wln = laser_wln,
#                                     particle_scan_name = particle_scan_name,
#                                     particle_name = particle_name,
#                                     y_label = 'raw')
        
#         ### Power norm Nanocavity & Deviation
#         powerseries_power_norm = process_powerseries_nanocavity(powerseries, 'Y', laser_wln, calibrate_power = True)
#         fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
#         fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)
#         plot_nanocavity_powerseries(powerseries_power_norm,
#                                     ax = ax[0],
#                                     save_dir = save_dir, 
#                                     int_std = True, 
#                                     ax_std = ax[1],
#                                     laser_wln = laser_wln,
#                                     particle_scan_name = particle_scan_name,
#                                     particle_name = particle_name,
#                                     y_label = 'power_norm')
        
#         ### DF Data
#         process_DF_screening(my_h5, particle_scan_name, particle_name, save_dir)
        
#         ### Cleanup
#         plt.close('all')
#         gc.collect() 


#%% Set variables for 785

my_h5 = h5_785
laser_wln = 785
wn_cal = wn_cal_785
R_setup = R_setup_785
dark_cts = dark_cts_785
truncate_range = truncate_range_785


#%% H2 785

# save_dir = r"C:\Users\il322\Desktop\Offline Data\2023-05-10_M-TAPP-SMe_NPoM\2023-05-12_M-TAPP-SMe_80nm_NPoM Powerseries_DF\785nm H2-TAPP-SMe 100nm NPoM"
# scan_list = ['ParticleScannerScan_1']
# sample_name = 'H2-TAPP-SMe 100nm NPoM'
# print('785nm H2')

# ## Loop over scan lists
# for particle_scan_name in scan_list:
#     print(particle_scan_name)
#     particle_scan = my_h5[particle_scan_name]
#     particle_list = natsort.natsorted(list(particle_scan.keys()))
    
#     ## Loop over particles in particle scan
#     for particle in particle_list:
#         if 'Particle' not in particle:
#             particle_list.remove(particle)
    
#     ## Loop over filtered particles in particle scan
#     for particle_name in particle_list:
#         print(particle_name)
        
#         ### Process powerseries
#         powerseries = process_powerseries(my_h5, particle_scan_name, 
#                                           particle_name, laser_wln,
#                                           sample_name, wn_cal, R_setup,
#                                           dark_cts, truncate_range)          
        
#         ### Plot kinetic powerseries
#         plot_kinetic_powerseries(powerseries, 
#                                  particle_scan_name, 
#                                  particle_name, 
#                                  laser_wln, 
#                                  sample_name, 
#                                  n_plots = 4, 
#                                  v_mins = None, 
#                                  v_maxs = None, 
#                                  save_dir = save_dir)

#         ### Raw Nanocavity & Deviation
#         powerseries_raw = process_powerseries_nanocavity(powerseries, 'Y_raw', laser_wln)
#         fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
#         fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)
#         plot_nanocavity_powerseries(powerseries_raw,
#                                     ax = ax[0],
#                                     save_dir = save_dir, 
#                                     int_std = True, 
#                                     ax_std = ax[1],
#                                     laser_wln = laser_wln,
#                                     particle_scan_name = particle_scan_name,
#                                     particle_name = particle_name,
#                                     y_label = 'raw')
        
#         ### Power norm Nanocavity & Deviation
#         powerseries_power_norm = process_powerseries_nanocavity(powerseries, 'Y', laser_wln, calibrate_power = True)
#         fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
#         fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)
#         plot_nanocavity_powerseries(powerseries_power_norm,
#                                     ax = ax[0],
#                                     save_dir = save_dir, 
#                                     int_std = True, 
#                                     ax_std = ax[1],
#                                     laser_wln = laser_wln,
#                                     particle_scan_name = particle_scan_name,
#                                     particle_name = particle_name,
#                                     y_label = 'power_norm')
        
#         ### DF Data
#         process_DF_screening(my_h5, particle_scan_name, particle_name, save_dir)
        
#         ### Cleanup
#         plt.close('all')
#         gc.collect() 
        
        
#%% Co 785

# save_dir = r"C:\Users\il322\Desktop\Offline Data\2023-05-10_M-TAPP-SMe_NPoM\2023-05-12_M-TAPP-SMe_80nm_NPoM Powerseries_DF\785nm Co-TAPP-SMe 100nm NPoM"
# scan_list = ['ParticleScannerScan_2']
# sample_name = 'Co-TAPP-SMe 100nm NPoM'
# print('785nm Co')

# ## Loop over scan lists
# for particle_scan_name in scan_list:
#     print(particle_scan_name)
#     particle_scan = my_h5[particle_scan_name]
#     particle_list = natsort.natsorted(list(particle_scan.keys()))
    
#     ## Loop over particles in particle scan
#     for particle in particle_list:
#         if 'Particle' not in particle:
#             particle_list.remove(particle)
    
#     ## Loop over filtered particles in particle scan
#     for particle_name in particle_list:
#         print(particle_name)
        
#         ### Process powerseries
#         powerseries = process_powerseries(my_h5, particle_scan_name, 
#                                           particle_name, laser_wln,
#                                           sample_name, wn_cal, R_setup,
#                                           dark_cts, truncate_range)          
        
#         ### Plot kinetic powerseries
#         plot_kinetic_powerseries(powerseries, 
#                                  particle_scan_name, 
#                                  particle_name, 
#                                  laser_wln, 
#                                  sample_name, 
#                                  n_plots = 4, 
#                                  v_mins = None, 
#                                  v_maxs = None, 
#                                  save_dir = save_dir)

#         ### Raw Nanocavity & Deviation
#         powerseries_raw = process_powerseries_nanocavity(powerseries, 'Y_raw', laser_wln)
#         fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
#         fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)
#         plot_nanocavity_powerseries(powerseries_raw,
#                                     ax = ax[0],
#                                     save_dir = save_dir, 
#                                     int_std = True, 
#                                     ax_std = ax[1],
#                                     laser_wln = laser_wln,
#                                     particle_scan_name = particle_scan_name,
#                                     particle_name = particle_name,
#                                     y_label = 'raw')
        
#         ### Power norm Nanocavity & Deviation
#         powerseries_power_norm = process_powerseries_nanocavity(powerseries, 'Y', laser_wln, calibrate_power = True)
#         fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
#         fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)
#         plot_nanocavity_powerseries(powerseries_power_norm,
#                                     ax = ax[0],
#                                     save_dir = save_dir, 
#                                     int_std = True, 
#                                     ax_std = ax[1],
#                                     laser_wln = laser_wln,
#                                     particle_scan_name = particle_scan_name,
#                                     particle_name = particle_name,
#                                     y_label = 'power_norm')
        
#         ### DF Data
#         process_DF_screening(my_h5, particle_scan_name, particle_name, save_dir)
        
#         ### Cleanup
#         plt.close('all')
#         gc.collect() 
        
        
#%% Ni 785

# save_dir = r"C:\Users\il322\Desktop\Offline Data\2023-05-10_M-TAPP-SMe_NPoM\2023-05-12_M-TAPP-SMe_80nm_NPoM Powerseries_DF\785nm Ni-TAPP-SMe 100nm NPoM"
# scan_list = ['ParticleScannerScan_3', 'ParticleScannerScan_4']
# sample_name = 'Ni-TAPP-SMe 100nm NPoM'
# print('785nm Ni')

# ## Loop over scan lists
# for particle_scan_name in scan_list:
#     print(particle_scan_name)
#     particle_scan = my_h5[particle_scan_name]
#     particle_list = natsort.natsorted(list(particle_scan.keys()))
    
#     ## Loop over particles in particle scan
#     for particle in particle_list:
#         if 'Particle' not in particle:
#             particle_list.remove(particle)
    
#     ## Loop over filtered particles in particle scan
#     for particle_name in particle_list:
#         print(particle_name)
        
#         ### Process powerseries
#         powerseries = process_powerseries(my_h5, particle_scan_name, 
#                                           particle_name, laser_wln,
#                                           sample_name, wn_cal, R_setup,
#                                           dark_cts, truncate_range)          
        
#         ### Plot kinetic powerseries
#         plot_kinetic_powerseries(powerseries, 
#                                  particle_scan_name, 
#                                  particle_name, 
#                                  laser_wln, 
#                                  sample_name, 
#                                  n_plots = 4, 
#                                  v_mins = None, 
#                                  v_maxs = None, 
#                                  save_dir = save_dir)

#         ### Raw Nanocavity & Deviation
#         powerseries_raw = process_powerseries_nanocavity(powerseries, 'Y_raw', laser_wln)
#         fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
#         fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)
#         plot_nanocavity_powerseries(powerseries_raw,
#                                     ax = ax[0],
#                                     save_dir = save_dir, 
#                                     int_std = True, 
#                                     ax_std = ax[1],
#                                     laser_wln = laser_wln,
#                                     particle_scan_name = particle_scan_name,
#                                     particle_name = particle_name,
#                                     y_label = 'raw')
        
#         ### Power norm Nanocavity & Deviation
#         powerseries_power_norm = process_powerseries_nanocavity(powerseries, 'Y', laser_wln, calibrate_power = True)
#         fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
#         fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)
#         plot_nanocavity_powerseries(powerseries_power_norm,
#                                     ax = ax[0],
#                                     save_dir = save_dir, 
#                                     int_std = True, 
#                                     ax_std = ax[1],
#                                     laser_wln = laser_wln,
#                                     particle_scan_name = particle_scan_name,
#                                     particle_name = particle_name,
#                                     y_label = 'power_norm')
        
#         ### DF Data
#         process_DF_screening(my_h5, particle_scan_name, particle_name, save_dir)
        
#         ### Cleanup
#         plt.close('all')
#         gc.collect() 
        
        
#%% Zn 785

# save_dir = r"C:\Users\il322\Desktop\Offline Data\2023-05-10_M-TAPP-SMe_NPoM\2023-05-12_M-TAPP-SMe_80nm_NPoM Powerseries_DF\785nm Zn-TAPP-SMe 100nm NPoM"
# scan_list = ['ParticleScannerScan_5', 'ParticleScannerScan_6',
#              'ParticleScannerScan_7', 'ParticleScannerScan_8',
#              'ParticleScannerScan_9', 'ParticleScannerScan_10']
# sample_name = 'Zn-TAPP-SMe 100nm NPoM'
# print('785nm Zn')

# ## Loop over scan lists
# for particle_scan_name in scan_list:
#     print(particle_scan_name)
#     particle_scan = my_h5[particle_scan_name]
#     particle_list = natsort.natsorted(list(particle_scan.keys()))
    
#     ## Loop over particles in particle scan
#     for particle in particle_list:
#         if 'Particle' not in particle:
#             particle_list.remove(particle)
    
#     ## Loop over filtered particles in particle scan
#     for particle_name in particle_list:
#         print(particle_name)
        
#         ### Process powerseries
#         powerseries = process_powerseries(my_h5, particle_scan_name, 
#                                           particle_name, laser_wln,
#                                           sample_name, wn_cal, R_setup,
#                                           dark_cts, truncate_range)          
        
#         ### Plot kinetic powerseries
#         plot_kinetic_powerseries(powerseries, 
#                                  particle_scan_name, 
#                                  particle_name, 
#                                  laser_wln, 
#                                  sample_name, 
#                                  n_plots = 4, 
#                                  v_mins = None, 
#                                  v_maxs = None, 
#                                  save_dir = save_dir)

#         ### Raw Nanocavity & Deviation
#         powerseries_raw = process_powerseries_nanocavity(powerseries, 'Y_raw', laser_wln)
#         fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
#         fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)
#         plot_nanocavity_powerseries(powerseries_raw,
#                                     ax = ax[0],
#                                     save_dir = save_dir, 
#                                     int_std = True, 
#                                     ax_std = ax[1],
#                                     laser_wln = laser_wln,
#                                     particle_scan_name = particle_scan_name,
#                                     particle_name = particle_name,
#                                     y_label = 'raw')
        
#         ### Power norm Nanocavity & Deviation
#         powerseries_power_norm = process_powerseries_nanocavity(powerseries, 'Y', laser_wln, calibrate_power = True)
#         fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
#         fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)
#         plot_nanocavity_powerseries(powerseries_power_norm,
#                                     ax = ax[0],
#                                     save_dir = save_dir, 
#                                     int_std = True, 
#                                     ax_std = ax[1],
#                                     laser_wln = laser_wln,
#                                     particle_scan_name = particle_scan_name,
#                                     particle_name = particle_name,
#                                     y_label = 'power_norm')
        
#         ### DF Data
#         process_DF_screening(my_h5, particle_scan_name, particle_name, save_dir)
        
#         ### Cleanup
#         plt.close('all')
#         gc.collect() 


#%% Co 633 - Particle ScannerScan 1 Particle 17

my_h5 = h5_633
laser_wln = 633
wn_cal = wn_cal_633
R_setup = R_setup_633
dark_cts = dark_cts_633
truncate_range = truncate_range_633
#save_dir = r"C:\Users\il322\Desktop\Offline Data\2023-05-10_M-TAPP-SMe_NPoM\2023-05-12_M-TAPP-SMe_80nm_NPoM Powerseries_DF\633nm Co-TAPP-SMe 80nm NPoM"
save_dir = None
sample_name = 'Co-TAPP-SMe 80nm NPoM'
print('633nm Co')

particle_scan_name = 'ParticleScannerScan_1'
particle_name = 'Particle_17'

### Process powerseries
powerseries = process_powerseries(my_h5, particle_scan_name, 
                                  particle_name, laser_wln,
                                  sample_name, wn_cal, R_setup,
                                  dark_cts, truncate_range)          

## Plot kinetic powerseries
plot_kinetic_powerseries(powerseries, 
                          particle_scan_name, 
                          particle_name, 
                          laser_wln, 
                          sample_name, 
                          n_plots = 4, 
                          v_mins = None, 
                          v_maxs = None, 
                          save_dir = save_dir)

### Raw Nanocavity & Deviation
powerseries_raw = process_powerseries_nanocavity(powerseries, 'Y_raw', laser_wln)
# fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
# fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)
# plot_nanocavity_powerseries(powerseries_raw,
#                             ax = ax[0],
#                             save_dir = save_dir, 
#                             int_std = True, 
#                             ax_std = ax[1],
#                             laser_wln = laser_wln,
#                             particle_scan_name = particle_scan_name,
#                             particle_name = particle_name,
#                             y_label = 'raw')

### Power norm Nanocavity & Deviation
powerseries_power_norm = process_powerseries_nanocavity(powerseries, 'Y', laser_wln, calibrate_power = True)
# fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
# fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)
# plot_nanocavity_powerseries(powerseries_power_norm,
#                             ax = ax[0],
#                             save_dir = save_dir, 
#                             int_std = True, 
#                             ax_std = ax[1],
#                             laser_wln = laser_wln,
#                             particle_scan_name = particle_scan_name,
#                             particle_name = particle_name,
#                             y_label = 'power_norm')

### DF Data
#process_DF_screening(my_h5, particle_scan_name, particle_name, save_dir)

### Cleanup
plt.close('all')
gc.collect()


#%% Plot Co-TAPP-SMe 633 v BPT 633 timescans at same power

# Co_timescan = powerseries[18]
# Co_timescan.plot_timescan(v_min = 500, v_max = 8000, x_min = 500)

# BPT_h5 = h5py.File(r"C:\Users\il322\Downloads\BPT_Dataset_For_Kent.h5")
# BPT_particle = BPT_h5['Particle_2']
# BPT_x = BPT_particle.attrs['wavenumber_axis']
# BPT_y = np.array(BPT_particle)
# BPT_timescan = SERS.SERS_Timescan(x = BPT_x, y = BPT_y)
# BPT_timescan.calibrate_intensity(laser_power = .709, exposure = .03487)
# BPT_timescan.plot_timescan(x_min = 500, v_min = 12000, v_max = 14500)

#%%
# Co_timescan.truncate(500, 2490)
# BPT_timescan.truncate(500, 1600)

# Co_timescan.plot_timescan(v_min = 500, v_max = 8000, title = '633nm SERS 712$\mu$W\nCo-TAPP-SMe 80nm NPoM')
# plt.savefig('Co-TAPP 633nm Timescan 700uW.svg', format = 'svg')
# BPT_timescan.plot_timescan(v_min = 12350, v_max = 13500, title = '633nm SERS 709$\mu$W\nBPT 80nm NPoM')
# plt.savefig('BPT 633nm Timescan 700uW.svg', format = 'svg')

# Co_timescan = std_per_pixel(Co_timescan)
# BPT_timescan = std_per_pixel(BPT_timescan)

# Co_std = Co_timescan.int_std / (2490 - 500)
# BPT_std = BPT_timescan.int_std / (1600 - 500)

# print(Co_std)
# print(BPT_std)

#%% Co 633nm stokes for plotting with mlagg echem

my_h5 = h5_633
laser_wln = 633
wn_cal = wn_cal_633_stokes
R_setup = R_setup_633[431:]
dark_cts_y = dark_cts_633.y[431:]
dark_cts_x = wn_cal_633_stokes
dark_cts = SERS.SERS_Spectrum(dark_cts_x, dark_cts_y)
truncate_range = [295, None]
#save_dir = r"C:\Users\il322\Desktop\Offline Data\2023-05-10_M-TAPP-SMe_NPoM\2023-05-12_M-TAPP-SMe_80nm_NPoM Powerseries_DF\633nm Co-TAPP-SMe 80nm NPoM"
save_dir = None
sample_name = 'Co-TAPP-SMe 80nm NPoM'
print('633nm Co')

particle_scan_name = 'ParticleScannerScan_1'
particle_name = 'Particle_17'

### Process powerseries
powerseries = process_powerseries(my_h5, particle_scan_name, 
                                  particle_name, laser_wln,
                                  sample_name, wn_cal, R_setup,
                                  dark_cts, truncate_range)          

## Plot kinetic powerseries
plot_kinetic_powerseries(powerseries, 
                          particle_scan_name, 
                          particle_name, 
                          laser_wln, 
                          sample_name, 
                          n_plots = 4, 
                          v_mins = None, 
                          v_maxs = None, 
                          save_dir = save_dir)

### Raw Nanocavity & Deviation
powerseries_raw = process_powerseries_nanocavity(powerseries, 'Y_raw', laser_wln)
# fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
# fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)
# plot_nanocavity_powerseries(powerseries_raw,
#                             ax = ax[0],
#                             save_dir = save_dir, 
#                             int_std = True, 
#                             ax_std = ax[1],
#                             laser_wln = laser_wln,
#                             particle_scan_name = particle_scan_name,
#                             particle_name = particle_name,
#                             y_label = 'raw')

### Power norm Nanocavity & Deviation
powerseries_power_norm = process_powerseries_nanocavity(powerseries, 'Y', laser_wln, calibrate_power = True)
# fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
# fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)
# plot_nanocavity_powerseries(powerseries_power_norm,
#                             ax = ax[0],
#                             save_dir = save_dir, 
#                             int_std = True, 
#                             ax_std = ax[1],
#                             laser_wln = laser_wln,
#                             particle_scan_name = particle_scan_name,
#                             particle_name = particle_name,
#                             y_label = 'power_norm')

### DF Data
#process_DF_screening(my_h5, particle_scan_name, particle_name, save_dir)

### Cleanup
plt.close('all')
gc.collect()


#%%
fig, ax = plt.subplots(1, 1, figsize=[8,6])
fig.suptitle('633nm SERS Powerseries Co-TAPP-SMe 80nm NPoM\n& SERS-EChem Co-TAPP-SMe MLAgg', fontsize = 'medium', y = 0.95)
powerseries_norm = powerseries_raw
for timescan in powerseries_norm:
    fs = 10000
    cutoff = 500
   # timescan.nanocavity_spectrum.truncate(600,2050)
    timescan.nanocavity_spectrum.y_smooth = timescan.nanocavity_spectrum.y_baselined
    timescan.nanocavity_spectrum.y_smooth = spt.butter_lowpass_filt_filt(timescan.nanocavity_spectrum.y_baselined, cutoff, fs, 1)
    timescan.nanocavity_spectrum.y_norm = timescan.nanocavity_spectrum.y_smooth - timescan.nanocavity_spectrum.y_smooth.min()
    timescan.nanocavity_spectrum.y_norm = timescan.nanocavity_spectrum.y_norm/timescan.nanocavity_spectrum.y_norm.max()
## Impoart echem spectra
spec_x = np.loadtxt(r"C:\Users\il322\Desktop\Offline Data\Normalized CA Wavenumbers.txt")
spec0 = np.loadtxt(r"C:\Users\il322\Desktop\Offline Data\Normalized CA  0.0V.txt")
spec2 = np.loadtxt(r"C:\Users\il322\Desktop\Offline Data\Normalized CA -0.2V.txt")
spec4 = np.loadtxt(r"C:\Users\il322\Desktop\Offline Data\Normalized CA -0.4V.txt")
spec6 = np.loadtxt(r"C:\Users\il322\Desktop\Offline Data\Normalized CA -0.6V.txt")
spec8 = np.loadtxt(r"C:\Users\il322\Desktop\Offline Data\Normalized CA -0.8V.txt")
spec10 = np.loadtxt(r"C:\Users\il322\Desktop\Offline Data\Normalized CA -1.0V.txt")
spec12 = np.loadtxt(r"C:\Users\il322\Desktop\Offline Data\Normalized CA -1.2V.txt")
spec16 = np.loadtxt(r"C:\Users\il322\Desktop\Offline Data\Normalized CA -1.6V.txt")
spec_x = spec_x[299:551]
spec_list = [spec0, spec2, spec4, spec6, spec8, spec10, spec12]
spec_list = [spec0, spec8, spec12] 
voltage_list = [0.0, -0.8, -1.2]

## Plot
my_cmap = plt.get_cmap("viridis")
for i, spec in enumerate(spec_list):
    spec = spec[299:551]
    spec_baselined = spec - spt.baseline_als(spec, 1e3, 1e-3)
    spec_baselined = spec_baselined/spec_baselined.max()
    spec_voltage = voltage_list[i]
    color = my_cmap(i/(len(spec_list)+0.5))
    color = (color[0], color[1], color[2],1)
    ax.plot(spec_x, spec_baselined + 0.65, label = 'MLAgg '  + str(spec_voltage) + 'V', color = color)
    #ax.text(s=spec_voltage, x = 1950, y = spec.min() + (i*0.15), fontsize = 'small', color = my_cmap(i/(len(spec_list)+0.5)))
    print(my_cmap(i/(len(spec_list)+0.5)))

save_dir = r"C:\Users\il322\Desktop\Offline Data"

plot_nanocavity_powerseries(powerseries_norm,
                            ax = ax,
                            save_dir = save_dir, 
                            laser_wln = laser_wln,
                            offset = 0,
                            particle_scan_name = particle_scan_name,
                            particle_name = particle_name,
                            y_label = None, powerseries_range=[2,20])

#plt.savefig('633nm nanocav echem compare.svg', format = 'svg')
#ax.set_ylabel = 'Normalized SERS Intensity (a.u.)'


#%%
#%% Co 785nm for plotting with mlagg echem


#save_dir = r"C:\Users\il322\Desktop\Offline Data\2023-05-10_M-TAPP-SMe_NPoM\2023-05-12_M-TAPP-SMe_80nm_NPoM Powerseries_DF\633nm Co-TAPP-SMe 80nm NPoM"


h5_785 = h5_785
wn_cal_785 = wn_cal_785
dark_cts_785 = dark_cts_785
R_setup_785 = R_setup_785
truncate_range_785 = [-2000, 2300]

sample_name = 'Co-TAPP-SMe 100nm NPoM'
my_h5 = h5_785
laser_wln = 785
wn_cal = wn_cal_785
R_setup = R_setup_785
dark_cts = dark_cts_785
truncate_range = truncate_range_785
print('Co 785nm')

particle_scan_name = 'ParticleScannerScan_2'
particle_name = 'Particle_6'

### Process powerseries
powerseries = process_powerseries(my_h5, particle_scan_name, 
                                  particle_name, laser_wln,
                                  sample_name, wn_cal, R_setup,
                                  dark_cts, truncate_range)          

## Plot kinetic powerseries
# plot_kinetic_powerseries(powerseries, 
#                           particle_scan_name, 
#                           particle_name, 
#                           laser_wln, 
#                           sample_name, 
#                           n_plots = 4, 
#                           v_mins = None, 
#                           v_maxs = None, 
#                           save_dir = save_dir)

### Raw Nanocavity & Deviation
powerseries_raw = process_powerseries_nanocavity(powerseries, 'Y_raw', laser_wln)
# fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
# fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)
# plot_nanocavity_powerseries(powerseries_raw,
#                             ax = ax[0],
#                             save_dir = None, 
#                             int_std = True, 
#                             ax_std = ax[1],
#                             laser_wln = laser_wln,
#                             particle_scan_name = particle_scan_name,
#                             particle_name = particle_name,
#                             y_label = 'raw')

### Power norm Nanocavity & Deviation
powerseries_power_norm = process_powerseries_nanocavity(powerseries, 'Y', laser_wln, calibrate_power = True)
# fig, ax = plt.subplots(1, 2, figsize=[12,6], gridspec_kw={'width_ratios': [3, 1]}, sharey=False)
# fig.suptitle(str(laser_wln) + 'nm SERS Powerseries: ' + sample_name + '\n' + particle_scan_name + ': ' + particle_name)
# plot_nanocavity_powerseries(powerseries_power_norm,
#                             ax = ax[0],
#                             save_dir = save_dir, 
#                             int_std = True, 
#                             ax_std = ax[1],
#                             laser_wln = laser_wln,
#                             particle_scan_name = particle_scan_name,
#                             particle_name = particle_name,
#                             y_label = 'power_norm')

### DF Data
#process_DF_screening(my_h5, particle_scan_name, particle_name, save_dir)

### Cleanup
plt.close('all')
gc.collect()

# Plot 785 nanocav & echem
powerseries_norm = powerseries_raw
for timescan in powerseries_norm:
    fs = 10000
    cutoff = 500
   # timescan.nanocavity_spectrum.truncate(600,2050)
    timescan.nanocavity_spectrum.y_smooth = timescan.nanocavity_spectrum.y
    timescan.nanocavity_spectrum.y_smooth = timescan.nanocavity_spectrum.y_baselined
    timescan.nanocavity_spectrum.y_smooth = spt.butter_lowpass_filt_filt(timescan.nanocavity_spectrum.y_baselined, cutoff, fs, 1)

    timescan.nanocavity_spectrum.y_smooth = timescan.nanocavity_spectrum.y_smooth[95:191]
    timescan.nanocavity_spectrum.x = timescan.nanocavity_spectrum.x[95:191]
 
    for i in range(0, len(timescan.nanocavity_spectrum.x)-1):
        timescan.nanocavity_spectrum.x[i] += 1 + (i/len(timescan.nanocavity_spectrum.x))
        
    
    #timescan.nanocavity_spectrum.y_smooth = timescan.nanocavity_spectrum.y_smooth[50:250]
    #timescan.nanocavity_spectrum.x = timescan.nanocavity_spectrum.x[50:250]

    timescan.nanocavity_spectrum.y_norm = timescan.nanocavity_spectrum.y_smooth - timescan.nanocavity_spectrum.y_smooth.min()
    timescan.nanocavity_spectrum.y_norm = timescan.nanocavity_spectrum.y_norm/timescan.nanocavity_spectrum.y_norm.max()
    timescan.nanocavity_spectrum.y_smooth = timescan.nanocavity_spectrum.y_norm
## Impoart echem spectra
spec_x = np.loadtxt(r"C:\Users\il322\Desktop\Offline Data\Normalized CA Wavenumbers.txt")
spec0 = np.loadtxt(r"C:\Users\il322\Desktop\Offline Data\Normalized CA  0.0V.txt")
spec2 = np.loadtxt(r"C:\Users\il322\Desktop\Offline Data\Normalized CA -0.2V.txt")
spec4 = np.loadtxt(r"C:\Users\il322\Desktop\Offline Data\Normalized CA -0.4V.txt")
spec6 = np.loadtxt(r"C:\Users\il322\Desktop\Offline Data\Normalized CA -0.6V.txt")
spec8 = np.loadtxt(r"C:\Users\il322\Desktop\Offline Data\Normalized CA -0.8V.txt")
spec10 = np.loadtxt(r"C:\Users\il322\Desktop\Offline Data\Normalized CA -1.0V.txt")
spec12 = np.loadtxt(r"C:\Users\il322\Desktop\Offline Data\Normalized CA -1.2V.txt")
spec16 = np.loadtxt(r"C:\Users\il322\Desktop\Offline Data\Normalized CA -1.6V.txt")
spec_x = spec_x[299:551]
spec_list = [spec0, spec2, spec4, spec6, spec8, spec10, spec12]
spec_list = [spec0, spec8, spec12] 
voltage_list = [0.0, -0.8, -1.2]


#%%
## Plot

fig, ax = plt.subplots(1, 1, figsize=[8,6])
fig.suptitle('785nm SERS Powerseries Co-TAPP-SMe 100nm NPoM\n& SERS-EChem Co-TAPP-SMe MLAgg', fontsize = 'medium', y = 0.95)


my_cmap = plt.get_cmap("viridis")
for i, spec in enumerate(spec_list):
    spec = spec[299:551]
    spec_baselined = spec - spt.baseline_als(spec, 1e3, 1e-3)
    spec_baselined = spec_baselined/spec_baselined.max()
    spec_voltage = voltage_list[i]
    color = my_cmap(i/(len(spec_list)+0.5))
    color = (color[0], color[1], color[2],1)
    ax.plot(spec_x, spec_baselined + 0.6, label = 'MLAgg '  + str(spec_voltage) + 'V', color = color)
    #ax.text(s=spec_voltage, x = 1950, y = spec.min() + (i*0.15), fontsize = 'small', color = my_cmap(i/(len(spec_list)+0.5)))
    print(my_cmap(i/(len(spec_list)+0.5)))

save_dir = r"C:\Users\il322\Desktop\Offline Data"

plot_nanocavity_powerseries(powerseries_raw,
                            ax = ax,
                            save_dir = save_dir, 
                            laser_wln = laser_wln,
                            offset = 0,
                            particle_scan_name = particle_scan_name,
                            particle_name = particle_name,
                            y_label = None, powerseries_range=[0,20])
