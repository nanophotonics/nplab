# -*- coding: utf-8 -*-
"""
Created on Thu Mar 30 17:06:38 2023

@author: il322
"""

import numpy as np
import scipy as sp
from matplotlib import pyplot as plt
import matplotlib as mpl
from scipy.signal import find_peaks
from scipy.signal import find_peaks_cwt
from scipy.stats import linregress
from scipy.interpolate import interp1d
from scipy.signal import savgol_filter
from pylab import *
import nplab
import h5py
import natsort
import os

from nplab.analysis.general_spec_tools import spectrum_tools as spt
from nplab.analysis.general_spec_tools import npom_sers_tools as nst
from nplab.analysis.general_spec_tools import agg_sers_tools as ast
from nplab.analysis.general_spec_tools import npom_df_pl_tools as df
from nplab.analysis.SERS_Fitting import Auto_Fit_Raman as afr
from nplab.analysis.il322_analysis import il322_SERS_tools as SERS


plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)


#%% Spectral efficiency correction using white light

def white_scatter_calibration(wl, white_scatter, white_bkg, start_notch=None, end_notch=None, plot=False):

    '''
    Calculates 1D array to correct for spectral efficiency from white scatter reference measurement,
    using known lamp emission

    Parameters:
        wl: (x) 1D array of calibrated wavelengths
        white_scatter: (y) 1D array of white scatter ref measurement intensities
        white_bkg: dark counts (can be taken from notch filter region)
        notch_range: [min_wln : max_wln] wavelength range of notch filter (optional)
        plot: (boolean) plots literature lamp emission over corrected measured white scatter
        
    Returns:
        R_setup: normalized 1D array - divide your spectra by this to correct for efficiency
    '''


    print('Calibrating spectral efficiency from white scatter reference')
    

    # Load measured white scatter
    ''' Need to fix background'''
    S_whitescatter = np.array(white_scatter) - white_bkg

    
    # Load literature lamp emission
    try:
        S_dkfd = np.loadtxt(r'C:\Users\il322\Desktop\Offline Data\S_dkdf.txt',delimiter=',')
    except:
        S_dkfd = np.loadtxt(r"C:\Users\ishaa\OneDrive\Desktop\Offline Data\S_dkdf.txt",delimiter=',')
    
    ## Interpolate literature lamp emission
    spline = sp.interpolate.splrep(S_dkfd[...,0],S_dkfd[...,1], s=0)
    
    ## Interpolate literature lamp emission in target wln range
    S_dkfd_spline = sp.interpolate.splev(wl, spline, der=0)
    S_dkfd_spline = np.array(S_dkfd_spline)
    
    ## Calculate R_setup
    R_setup = S_whitescatter/S_dkfd_spline
    R_setup = R_setup/R_setup.max()
    
    ## Set R_setup values in notch range to 1
    if start_notch != None and end_notch != None:
        R_setup[start_notch:end_notch] = 1
    
    
    # Plot literature lamp emission & corrected measured white scatter
    if plot == True:
        plt.figure(figsize=[10,6], dpi=1000)
        white_cal = np.array(S_whitescatter/R_setup)
        if start_notch != None and end_notch != None:
            white_cal_no_notch = np.concatenate((white_cal[0:start_notch], white_cal[end_notch:len(white_cal)-1]))
            white_cal = (white_cal - white_cal_no_notch.min())/(white_cal_no_notch.max()-white_cal_no_notch.min())
            plt.plot(wl, white_cal, label='Calibrated white scatter', color = 'grey')
        else:
            plt.plot(wl, (white_cal-white_cal.min())/white_cal.max(), label='Calibrated white scatter', color = 'grey')
        plt.plot(wl, (S_dkfd_spline-S_dkfd_spline.min())/(S_dkfd_spline.max() - S_dkfd_spline.min()),  '--', label='Literature lamp emission',color = 'black')
        plt.xlabel('Wavelength (nm)')
        plt.ylabel('Normalized Intensity (a.u.)')
        plt.title('633nm - Spectral Efficiency Calibration - White Scatter')
        plt.legend()
        plt.show()


    # Return R_setup
    print('   Done\n')
    return R_setup


#%% Get default literature BPT peaks

def process_default_lit_spectrum(plot = True, **kwargs):

    '''
    Processing of lit BPT spectra, used if no other literature spectrum provided
    '''
    
    ## Get file & spectrum
    file_name = r'nanocavity_spectrum_BPT.csv'
    try:
        data_dir = r'C:\Users\il322\Desktop\Offline Data'
        os.chdir(data_dir)
    except:
        data_dir = r'C:\Users\ishaa\OneDrive\Desktop\Offline Data'
        os.chdir(data_dir)
    lit_spectrum = np.loadtxt(file_name,skiprows=1,delimiter=',')
    lit_spectrum = SERS.SERS_Spectrum(x=lit_spectrum[:,1], y=lit_spectrum[:,0])
    
    ## Truncate, baseline, smooth
    lit_spectrum.truncate(start_x=450, end_x = lit_spectrum.x.max())
    lit_spectrum.y_baselined = lit_spectrum.y -  spt.baseline_als(y=lit_spectrum.y,lam=1e1,p=1e-4,niter=1000)
    lit_spectrum.y_smooth = spt.butter_lowpass_filt_filt(lit_spectrum.y_baselined,
                                                          cutoff = 3000,
                                                          fs = 40000,
                                                          order=1)
    lit_spectrum.normalise(norm_y = lit_spectrum.y_smooth)
    
    ## Find peaks
    lit_peaks = find_peaks(lit_spectrum.y_baselined, height = lit_spectrum.y.max() * 0.05, distance = 10)
    lit_wn = lit_spectrum.x[lit_peaks[0]]    
    print('Default BPT Literature Peaks (1/cm):')
    print(lit_wn)
    
    ## Plot with peak positions
    if plot == True:
        cmap = plt.get_cmap('tab10')
        fig, ax = plt.subplots(1,1,figsize=[8,6])
        ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
        ax.set_ylabel('SERS Intensity (a.u.)')
        lit_spectrum.plot(plot_y = lit_spectrum.y_baselined, ax = ax, title = 'Literature BPT Spectrum', color = 'orange')
        for i,wn in enumerate(lit_wn):
            plt.scatter(wn, lit_spectrum.y_baselined[(np.where(lit_spectrum.x == wn))], zorder = 2, color = cmap(i))
        ax.set_xlim(300,2000)
        plt.show()
        
    return lit_spectrum, lit_wn

#%% Function to compare ref & lit peaks and pick closest

def find_closest_matches(a, b):
    
    
    print('Choosing closest ref peaks')
    
    # Initialize an empty array to store the closest matches
    c = []

    # Iterate through each element in array 'a'
    for x in a:
        # Calculate the average absolute differences between x and all elements in 'b'
        avg_differences = [np.abs(x - y) for y in b]
        
        # Find the index of the 'b' value with the lowest average difference
        closest_index = np.argmin(avg_differences)
        
        # Get the closest match from 'b'
        closest_match = b[closest_index]
        
        # Check if the closest match is not already in 'c', then append it
        if closest_match not in c:
            c.append(closest_match)
    
    return c



#%% Find reference peaks

def find_ref_peaks(ref_spectrum, lit_spectrum = None, lit_wn = None, threshold = 0.05, distance = 10, plot = True, **kwargs):
    
    '''
    Finds peaks in reference spectrum using scipy.find_peaks, plots with lit peaks
    
    Parameters:
        ref_spectrum (SERS_Spectrum): ref spectrum, needs y_norm if plotting
        lit_spectrum (SERS_Spectrum = None): literature spectrum  
        lit_wn (1D array/list = None): list of lit peak positions in wavenumber, if None uses default BPT
        deg: (int) order of polynomial fit between measured & lit peaks
        plot: (boolean) plot ployfit and literature v calibrated spectra
    '''
    
    
    # Find peaks in wavenumbers
    
    ref_peaks = find_peaks(ref_spectrum.y_smooth, height = ref_spectrum.y_smooth.max() * threshold, distance = distance, **kwargs)
    ref_wn = ref_spectrum.x[ref_peaks[0]]
    
    print('\nReference Peaks (1/cm):')
    print(ref_wn)

    
    # Plotting
    
    if plot == True:
        cmap = plt.get_cmap('tab10')
        
        ## Plot ref_spectrum & all ref peaks
        fig, ax = plt.subplots(1,1,figsize=[8,6])
        ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
        ax.set_ylabel('SERS Intensity (a.u.)')
        ref_spectrum.plot(plot_y = ref_spectrum.y_norm, ax = ax, label = 'Ref', zorder = 1)
        for i, wn in enumerate(ref_wn):
            ax.scatter(wn, ref_spectrum.y_norm[(np.where(np.round(ref_spectrum.x, 8) == np.round(wn,8)))], color = cmap(i), zorder = 2, marker = 'x')
    
        ## Plot lit_spectrum & peaks
        if lit_spectrum is not None:
            lit_spectrum.plot(ax = ax, plot_y = lit_spectrum.y_norm + 0.5, color = 'orange', label = 'Lit', zorder = 0, **kwargs)
        if lit_wn is not None:
            for i, wn in enumerate(lit_wn):
                ax.scatter(wn, lit_spectrum.y_norm[(np.where(lit_spectrum.x == wn))] + 0.5, color = cmap(i), zorder = 2)
        
            ### Find closest ref peaks and plot
            assert len(ref_wn) >= len(lit_wn), 'Error: Not enough reference peaks'
            if len(ref_wn) > len(lit_wn):
                ref_wn = find_closest_matches(lit_wn, ref_wn)
            for i, wn in enumerate(ref_wn):
                ax.scatter(wn, ref_spectrum.y_norm[(np.where(np.round(ref_spectrum.x, 8) == np.round(wn,8)))], color = cmap(i), zorder = 2)
        
        ax.set_title('Reference Spectrum')
        ax.set_xlim(300,2000)
        ax.legend()
        plt.show()
        
        
    return ref_wn        
        
    

#%% Get calibrated wavenumbers

def calibrate_spectrum(ref_spectrum, ref_wn, lit_spectrum = None, lit_wn = None, deg = 2, plot = True, **kwargs):
    
    ''' 
    Calibrates spectrum in wavenumbers of measured spectrum to literature peak positions.
    Need to input processed spectra with y_norm and found ref wavenumbers
    
    Parameters:
        ref_spectrum (SERS_Spectrum): ref spectrum, needs y_norm if plotting
        ref_wn (1D array/list): list of reference peak positions in wavenumber
        lit_spectrum (SERS_Spectrum = None): literature spectrum, if None uses default BPT
        lit_wn (1D array/list = None): list of lit peak positions in wavenumber, if None uses default BPT
        deg: (int) order of polynomial fit between measured & lit peaks
        plot: (boolean) plot ployfit and literature v calibrated spectra
    
    Returns:
        wn_cal: calibrated wavenumbers, 1D numpy array with same length as ref_spectrum.x    
    '''
    
    
    print('Calibrating spectrometer from reference\n')
    
    
    # Use default literature bpt spectrum if none other provided
    
    if lit_spectrum is None or lit_wn is None:
        print('No literature spectrum provided, using default BPT nanocavity\n')
        lit_spectrum, lit_wn = process_default_lit_spectrum(plot = plot, **kwargs)
    
    
    # Get closest ref peaks
    
    assert len(ref_wn) >= len(lit_wn), 'Error: Not enough reference peaks'
    if len(ref_wn) > len(lit_wn):
        ref_wn = find_closest_matches(lit_wn, ref_wn)
    
        
    # Run calibration
    
    ref_wn = np.array(ref_wn)
    lit_wn = np.array(lit_wn)
    
    ## Fit literature peak positions to ref peak positions
    a = np.polyfit(ref_wn, lit_wn, deg=deg)
    
    ## Calculate the calibrated wavenumbers using the fitted coefficients
    wn_cal = 0
    for i in range(0, len(a)):
        wn_cal = wn_cal + a[i] * ref_spectrum.x**(deg-i)
        
    
    # Plotting

    if plot == True:
    
        ## Plot ref & lit spectra w/ fitted peak positions
        fig, ax = plt.subplots(1,1,figsize=[8,6])
        ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
        ax.set_ylabel('SERS Intensity (a.u.)')
        
        ### Normalize spectra
        ref_spectrum.normalise(norm_y = ref_spectrum.y_smooth)
        
        ### Plot
        cmap = plt.get_cmap('tab10')
        ref_spectrum.plot(ax = ax, plot_y = ref_spectrum.y_norm, color = 'blue', label = 'Ref', **kwargs)
        for i, wn in enumerate(ref_wn):
            ax.scatter(wn, ref_spectrum.y_norm[(np.where(np.round(ref_spectrum.x, 8) == np.round(wn,8)))], color = cmap(i), zorder = 2)
        lit_spectrum.plot(ax = ax, plot_y = lit_spectrum.y_norm, color = 'orange', label = 'Lit', **kwargs)
        for i, wn in enumerate(lit_wn):
            ax.scatter(wn, lit_spectrum.y_norm[(np.where(lit_spectrum.x == wn))], color = cmap(i), zorder = 2)
        ax.set_title('Spectral Calibration')
        ax.legend()
        plt.show()
            
        ## Plot ref v lit peak positions & fit    
        fig, ax = plt.subplots(1,1,figsize=[8,6]) 
        ax.plot(ref_wn, lit_wn, '.')
        cal_peak = 0
        for i in range(0, len(a)):
            cal_peak = cal_peak + a[i] * ref_wn**(deg-i)
        ax.plot(ref_wn, cal_peak, '-')
        ax.set_xlabel('Peak Positions (cm$^{-1}$) - Measured')
        ax.set_ylabel('Peak Positions (cm$^{-1}$) - Literature')
        ax.set_title('Literature v. Measured Peak Positions & Fit')
        plt.tight_layout()
        plt.show()  
        
        ## Plot lit & ref spectra w/ calibrated wavenumbers
        x_original = ref_spectrum.x
        ref_spectrum.x = wn_cal
        fig, ax = plt.subplots(1,1,figsize=[8,6])
        ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
        ax.set_ylabel('SERS Intensity (a.u.)')
        ref_spectrum.plot(ax = ax, plot_y = ref_spectrum.y_norm, color = 'blue', label = 'Ref', **kwargs)
        lit_spectrum.plot(ax = ax, plot_y = lit_spectrum.y_norm, color = 'orange', label = 'Lit', **kwargs)
        ax.set_title('Calibrated Spectra')
        ax.legend()
        ref_spectrum.x = x_original
        plt.show()
        
        
        # Return calibrated wavenumbers
        
        print('\nDone\n')
        
    return wn_cal


#%% How to run

# # Spectral calibration

# ## Get default literature BPT spectrum & peaks
# lit_spectrum, lit_wn = process_default_lit_spectrum()

# ## Load BPT ref spectrum
# my_h5 = h5py.File(r"C:\Users\il322\Desktop\Offline Data\2023-09-18_Co-TAPP-SMe_80nm_NPoM_Track_DF_633nm_Powerseries.h5")
# coarse_shift = 90 # coarse shift to ref spectrum
# notch_range = [0+coarse_shift, 230+coarse_shift]
# bpt_ref_633nm = my_h5['PT_lab']['BPT_633nm']
# bpt_ref_633nm = SERS.SERS_Spectrum(bpt_ref_633nm)

# ## Convert to wn
# bpt_ref_633nm.x = spt.wl_to_wn(bpt_ref_633nm.x, 632.8)
# bpt_ref_633nm.x = bpt_ref_633nm.x + coarse_shift

# ## No notch spectrum (use this truncation for all spectra!)
# bpt_ref_no_notch = bpt_ref_633nm
# bpt_ref_no_notch.truncate(start_x = notch_range[1], end_x = None)

# ## Baseline, smooth, and normalize no notch ref for peak finding
# bpt_ref_no_notch.y_baselined = bpt_ref_no_notch.y -  spt.baseline_als(y=bpt_ref_no_notch.y,lam=1e1,p=1e-4,niter=1000)
# bpt_ref_no_notch.y_smooth = spt.butter_lowpass_filt_filt(bpt_ref_no_notch.y_baselined,
#                                                         cutoff=2000,
#                                                         fs = 10000,
#                                                         order=2)
# bpt_ref_no_notch.normalise(norm_y = bpt_ref_no_notch.y_smooth)

# ## Find BPT ref peaks
# ref_wn = find_ref_peaks(bpt_ref_no_notch, lit_spectrum = lit_spectrum, lit_wn = lit_wn, threshold = 0.05)

# ## Find calibrated wavenumbers
# wn_cal = calibrate_spectrum(bpt_ref_no_notch, ref_wn, lit_spectrum = lit_spectrum, lit_wn = lit_wn, linewidth = 1)
# bpt_ref_no_notch.x = wn_cal

#%%
# # White light efficiency calibration

# ## Load white scatter with 

# white_ref = my_h5['PT_lab']['white_ref_x5']
# white_ref = SERS.SERS_Spectrum(white_ref.attrs['wavelengths'], white_ref[2], title = 'White Scatterer')

# ## Convert to wn
# white_ref.x = spt.wl_to_wn(white_ref.x, 632.8)
# white_ref.x = white_ref.x + coarse_shift

# ## Get white bkg (counts in notch region)
# notch = SERS.SERS_Spectrum(white_ref.x[np.where(white_ref.x < (notch_range[1]-50))], white_ref.y[np.where(white_ref.x < (notch_range[1] - 50))], name = 'White Scatterer Notch') 
# notch_cts = notch.y.mean()
# notch.plot()

# # ## Truncate out notch (same as BPT ref), assign wn_cal
# white_ref.truncate(start_x = notch_range[1], end_x = None)


# ## Convert back to wl for efficiency calibration
# white_ref.x = spt.wn_to_wl(white_ref.x, 632.8)

# # Calculate R_setup
# R_setup_633nm = white_scatter_calibration(wl = white_ref.x,
#                                               white_scatter = white_ref.y,
#                                               white_bkg = notch_cts,
#                                               plot = True,
#                                               start_notch = notch_range[0]-40,
#                                               end_notch = notch_range[1]-40)

# ## Get dark counts
# # dark_cts = my_h5['PT_lab']['whire_ref_x5']
# # dark_cts = SERS.SERS_Spectrum(wn_cal_633, dark_cts[5], title = 'Dark Counts')
# # # dark_cts.plot()
# # plt.show()

# # Test R_setup with BPT reference
''' Add this plotting part to function'''
# plt.plot(bpt_ref_633nm.x, bpt_ref_633nm.y, color = (0.8,0.1,0.1,0.7), label = 'Raw spectrum')
# plt.plot(bpt_ref_633nm.x, (bpt_ref_633nm.y)/R_setup_633nm, color = (0,0.6,0.2,0.5), label = 'Efficiency-corrected')
# plt.legend(fontsize='x-small')
# plt.show()