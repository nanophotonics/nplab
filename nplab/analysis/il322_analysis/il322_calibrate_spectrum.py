# -*- coding: utf-8 -*-
"""
Created on Thu Mar 30 17:06:38 2023

@author: il322
"""

import numpy as np
import scipy as sp
from matplotlib import pyplot as plt
import matplotlib as mpl
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


#%% Find calibrated wavenumbers from ref & lit BPT spectra    

def spectral_calibration(meas_x, meas_y, meas_wn=None, lit_x=None, lit_y=None, lit_wn=None, deg = 2, plot=True):
    
    '''
    Calibrates spectrum in wavenumbers of measured spectrum to literature peak positions
    
    Parameters:
        meas_x: x-values of measured spectrum in wavenumbers
        meas_y: y-values of measured spectrum
        mean_wn: peak positions of measured spectrum
        lit_x: x-values of literature spectrum in wavenumber (optional: for plot)
        lit_y: y-values of literature spectrum (optional: for plot)
        deg: (int) order of polynomial fit between measured & lit peaks
        plot: (boolean) plot ployfit and literature v calibrated spectra
    
    Returns:
        wn_cal: calibrated wavenumbers, 1D numpy array with same length as meas_x
    '''
    
    
    print('Calibrating spectrometer from reference')
    
    
    # Fit literature peak positions to measured peak positions
    a = np.polyfit(meas_wn, lit_wn, deg=deg)
    
    # Calculate the calibrated wavenumbers using the fitted coefficients
    wn_cal = 0
    for i in range(0, len(a)):
        wn_cal = wn_cal + a[i] * meas_x**(deg-i)
    '''
    
    a2, a1, a0 = np.polyfit(meas_wn, lit_wn, deg=2)
    
    
    # Calculate the calibrated wavenumbers using the fitted coefficients
    wn_cal = a2 * meas_x**2 + a1 * meas_x + a0
    '''
    
    '''
    Advanced code from chatGPT if n_meas != n_lit - still doesn't assign 
    correct peaks to each other because peaks in meas_wn that are not in lit_wn
    are too close to incorrect peaks in lit_wn: spectrometer is too poorly cal
    
    # Assign literature peak positions to measured peak positions
    n_meas = len(meas_wn)
    n_lit = len(lit_wn)
    
    ## Initialize indices of corresponding peaks
    indices = np.zeros(n_lit, dtype=int) - 1
    
    ## Find the closest measured peak to each literature peak
    for i in range(n_lit):
        diff = np.abs(meas_wn - lit_wn[i])
        idx = np.argmin(diff)
        ### Check if the peak has already been assigned
        while idx in indices:
            #### If so, find the next closest measured peak
            diff[idx] = np.inf
            idx = np.argmin(diff)
        ### Assign the peak to the corresponding index
        indices[i] = idx
        
    ## Check if all peaks have been assigned
    if -1 in indices:
        print("Not all peaks could be assigned. Calibration failed.")
        return
    else:
        ### Extract the corresponding measured peak positions
        meas_wn = meas_wn[indices]
        
        ### Perform a linear fit between the corrected measured peak positions and known peak positions
        slope_offset, wn_offset = np.polyfit(meas_wn, lit_wn, deg=1)
        
        ### Calculate the calibrated wavenumbers using the fitted coefficients
        wn_cal = slope_offset * meas_x + wn_offset
    '''
    
    # Plot
    if plot == True:
        plt.figure(figsize=[10,6], dpi=1000) 
        plt.plot(meas_wn, lit_wn, '.')
        cal_peak = 0
        for i in range(0, len(a)):
            cal_peak = cal_peak + a[i] * meas_wn**(deg-i)
        plt.plot(meas_wn, cal_peak, '-')
        plt.xlabel('Peak Positions (cm$^{-1}$) - Measured')
        plt.ylabel('Peak Positions (cm$^{-1}$) - Literature')
        #plt.tight_layout()
        plt.show()  
        
    
        if lit_x.any() != None and lit_y.any() != None:
            lit = spt.Spectrum(lit_x, lit_y)
            lit.normalise()
            meas = spt.Spectrum(meas_x, meas_y)
            meas.normalise()
            plt.figure(figsize=[10,6], dpi=1000) 
            plt.plot(lit.x, lit.y_norm, '-', color='black', label='Literature')
            plt.plot(wn_cal, meas.y_norm, '-', color='blue', label = 'Calibrated')
            plt.xlabel('Raman Shifts (cm$^{-1}$)')
            plt.ylabel('Normalized Intensity (a.u.)')
            plt.title('Spectral Calibration - BPT Nanocavity SERS')
            plt.legend()
            #plt.tight_layout()
            plt.show()        
    
    
    # Return calibrated wavenumbers
    print('   Done\n')
    return wn_cal


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
    S_dkfd = np.loadtxt(r'C:\Users\il322\Desktop\Offline Data\S_dkdf.txt',delimiter=',')
    
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
#%%
def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return array[idx]

#%%

def run_spectral_calibration(ref_spectrum, ref_wn = [], lit_wn = [], ref_threshold = 0.08, deg = 2, baseline_first = True, smooth_first = True, plot = True):

    '''
    Run function to calibrate x-axis of spectrometer via reference spectrum
    Defaults to BPT literature values from nanocavity_spectrum.csv
    
    Parameters:
        ref_spectrum (Spectrum class): reference spectrum, truncated
        ref_wn ([] list): list of ref spectrum peak positions (if empty, extracts from reference spectrum)
        lit_wn ([] list): list of literature spectrum peak positions (if empty, defaults to BPT spectrum)
        ref_threshold(0.08 float): peak fitting threshold for reference spectrum
        deg: (int) order of polynomial fit between measured & lit peaks
        baseline_first (boolean)
        smooth_first (boolean)
        plot (boolean)
    '''
    # Get literature peak positions
    
    ## If no lit peak positions provided, get peak positions from nanocavity_spectrum.csv 
    if len(lit_wn) == 0:
        ### Process literature spectrum
        data_dir = r'C:\Users\il322\Desktop\Offline Data'
        file_name = r'nanocavity_spectrum_BPT.csv'
        os.chdir(data_dir)
        lit_spectrum = np.loadtxt(file_name,skiprows=1,delimiter=',')
        lit_spectrum = spt.Spectrum(x=lit_spectrum[:,1], y=lit_spectrum[:,0])
        lit_spectrum.truncate(start_x=450, end_x = lit_spectrum.x.max())
        lit_spectrum.y_baselined = lit_spectrum.y -  spt.baseline_als(y=lit_spectrum.y,lam=1e1,p=1e-4,niter=1000)
        lit_spectrum.y_smooth = spt.butter_lowpass_filt_filt(lit_spectrum.y_baselined,
                                                              cutoff=1500,
                                                              fs = 40000,
                                                              order=1)
        ### Find peaks
        lit_peaks = spt.approx_peak_gausses(lit_spectrum.x,
                                                lit_spectrum.y_smooth,
                                                plot=False,
                                                threshold=0.045,
                                                smooth_first=False,
                                                height_frac = 0.05)
        ### Store peak positions
        lit_wn = []
        for peak in lit_peaks:
            wn = peak[1]
            lit_wn.append(wn)
        lit_wn.sort()
        lit_wn = np.array(lit_wn)
                
    ## If peak positions provided, use those
    else:
        lit_wn = np.array(lit_wn)
        
        
    # Get reference peak positions
    
    ## Process reference spectrum
    if baseline_first == False:
        ref_spectrum.y_baselined = ref_spectrum.y
    else:
        ref_spectrum.y_baselined = ref_spectrum.y -  spt.baseline_als(y=ref_spectrum.y,lam=1e1,p=1e-4,niter=1000)
    
    if smooth_first == True:  
        ref_spectrum.y_smooth = spt.butter_lowpass_filt_filt(ref_spectrum.y_baselined,
                                                              cutoff=1000,
                                                              fs = 30000,
                                                              order=3)
    
    ## If no ref peak positions provided, get peak positions from ref spectrum
    if len(ref_wn) == 0:        
        ### Find peaks
        ref_peaks = spt.approx_peak_gausses(ref_spectrum.x,
                                                ref_spectrum.y_smooth,
                                                plot=False,
                                                threshold=ref_threshold,
                                                smooth_first=False,
                                                height_frac = 0.05)    
        
        ### Store peak positions
        ref_wn = []
        for peak in ref_peaks:
            wn = peak[1]
            ref_wn.append(wn)
        ref_wn.sort()
        ref_wn = np.array(ref_wn)
        print('Ref wavenumbers: ' + str(ref_wn))
    
    ## If peak positions provided, use those
    else:
        ref_wn = np.array(ref_wn)
    
    
    # Plot ref & lit spectra with peak positions
    
    if plot == True:
        plt.plot(lit_spectrum.x, lit_spectrum.y_smooth/lit_spectrum.y_smooth.max(), color=(0,0,1,0.5), label = 'Literature')
        plt.plot(ref_spectrum.x, ref_spectrum.y_smooth/ref_spectrum.y_smooth.max() + 1, color=(0.3,1,0.2,0.5), label= 'Reference')
        plt.legend(fontsize='x-small')
        plt.xlabel('Raman shifts (cm$^{-1}$)', fontsize='small')
        for peak in lit_wn:
            plt.scatter(peak, lit_spectrum.y_smooth[np.where(lit_spectrum.x == peak)] / lit_spectrum.y_smooth.max(), color='blue')
        for peak in ref_wn:
            plt.scatter(peak, ref_spectrum.y_smooth[(np.where(np.round(ref_spectrum.x, 8) == np.round(peak,8)))] / ref_spectrum.y_smooth.max() + 1, color = 'green')
        plt.title('Literature & Reference Spectra & Peak Positions', fontsize='medium')
        plt.show()
        
    # Cubic fit to get calibrated wavenumbers
    
    wn_cal = spectral_calibration(
             ref_spectrum.x, 
             ref_spectrum.y, 
             meas_wn = ref_wn, 
             lit_x = lit_spectrum.x, 
             lit_y = lit_spectrum.y_smooth, 
             lit_wn = lit_wn,
             deg = deg,
             plot=plot)
        
    return wn_cal

#%% How to run spectral calibration - from your own script

# ## Load h5 & spectrum
# my_h5 = h5py.File(r'C:\Users\il322\Desktop\Offline Data\2023-05-12.h5')
# bpt_ref_633nm = my_h5['ref_meas']['BPT-NPoM_633nm_Grating4_690cnwln_1s']
# bpt_ref_633nm = spt.Spectrum(bpt_ref_633nm)

# ## Convert to wn
# bpt_ref_633nm.x = spt.wl_to_wn(bpt_ref_633nm.x, 632.8)
# truncate_range = [210, 2400]

# ## Truncate out notch (use this truncation for all spectra!)
# bpt_ref_633nm.truncate(truncate_range[0], truncate_range[1])
# bpt_ref_633nm.plot()

# ## Have to adjust ref_wn because peak fitting is not yet robust
# ref_wn_633nm = [ 276.74390496,  396.21252815,  468.08976025, 679.43472478,  816.85574808,  986.17656368,
#  1067.96658448, 1179.79270908, 1271.98782961, 1467.40917881, 1570.24171155]

# ## Get calibrated wavenumbers
# wn_cal_633 = cal.run_spectral_calibration(bpt_ref_633nm, ref_wn = ref_wn_633nm, ref_threshold=0.07, deg = 3, plot=True)

#%% How to run spectral efficiency calibration - from your own script

# ## Load h5 & spectrum
# white_ref_633nm = my_h5['ref_meas']['whitescatt_0.002s_700cnwl']
# white_ref_633nm = spt.Spectrum(white_ref_633nm)

# ## Convert to wn
# white_ref_633nm.x = spt.wl_to_wn(white_ref_633nm.x, 632.8)

# ## Truncate out notch (same range as BPT ref above)
# white_ref_633nm.truncate(450, white_ref_633nm.x.max())

# ## Convert back to wl for efficiency calibration
# white_ref_633nm.x = spt.wn_to_wl(white_ref_633nm.x, 632.8)

# ## Get white background counts in notch
# notch_range = [0,90]
# notch = spt.Spectrum(white_ref_633nm.x_raw[notch_range[0]:notch_range[1]], white_ref_633nm.y_raw[notch_range[0]:notch_range[1]]) 
# notch_cts = notch.y.mean()

# ## Calculate R_setup
# R_setup = white_scatter_calibration(wl = white_ref_633nm.x, white_scatter = white_ref_633nm.y, white_bkg = notch_cts, plot=True)

# ## Test R_setup with BPT reference
# notch_cts = bpt_ref_633nm.y_raw[0:150].mean() # Remember to subtract notch counts from SERS spectra!
# plt.plot(bpt_ref_633nm.x, bpt_ref_633nm.y-notch_cts, color = (0.8,0.1,0.1,0.7), label = 'Raw spectrum')
# plt.plot(bpt_ref_633nm.x, (bpt_ref_633nm.y-notch_cts)*R_setup, color = (0,0.6,0.2,0.5), label = 'Efficiency-corrected')
# plt.legend(fontsize='x-small', borderpad = 0.2)


#%% Testing
# my_h5 = h5py.File(r"C:\Users\il322\Desktop\Offline Data\2023-05-22_M-TAPP-SME_80nm_NPoM_Track_DF_633nmPowerseries.h5")
# bpt_ref_633nm = my_h5['ref_meas']['BPT_NPoM_633nm_1s_690cnwln_Grating2']
# bpt_ref_633nm = SERS.SERS_Spectrum(bpt_ref_633nm)

# ## Convert to wn
# bpt_ref_633nm.x = spt.wl_to_wn(bpt_ref_633nm.x, 632.8)

# ## Truncate out notch (use this truncation for all spectra!)
# #bpt_ref_633nm.truncate(truncate_range[0], truncate_range[1])

# # ref_peaks = spt.approx_peak_gausses(bpt_ref_633nm.x,
# #                                         bpt_ref_633nm.y_smooth,
# #                                         plot=True,
# #                                         threshold=0.1,
# #                                         smooth_first=False,
# #                                         height_frac = 0.05)

# ## Have to adjust ref_wn because peak fitting is not yet robust
# ref_wn_633nm = [ 189.96242575,  256.60661727,  304.85947153,  416.21397689,  518.96110313,
#   635.5749669,  688.10709404,  760.32610816,  818.56620529,  951.50031667, 1021.03800555]

# plt.plot(bpt_ref_633nm.x, bpt_ref_633nm.y)
# bpt_ref_633nm.y_baselined = bpt_ref_633nm.y -  spt.baseline_als(y=bpt_ref_633nm.y,lam=1e1,p=1e-4,niter=1000)
# bpt_ref_633nm.y_smooth = spt.butter_lowpass_filt_filt(bpt_ref_633nm.y_baselined,
#                                                        cutoff=2000,
#                                                        fs = 40000,
#                                                        order=2)

# plt.plot(bpt_ref_633nm.x, bpt_ref_633nm.y_smooth)
# #plt.plot(bpt_ref_633nm.x, ref_spectrum.y_baselined)
# plt.show()

# ## Get calibrated wavenumbers
# wn_cal_633 = run_spectral_calibration(bpt_ref_633nm, deg = 2, ref_threshold = 0.03, baseline_first = False, smooth_first = False)

# Neon wavelengths taken from http://www.astrosurf.com/buil/us/spe2/calib2/neon1.gif
#neon_wls = np.array([585.249, 588.189, 594.483, 597.553, 603, 607.434, 609.616, 614.306, 616.359, 621.728, 626.649, 630.479, 633.443, 638.299, 640.225, 650.653, 653.288, 659.895, 667.828, 671.704, 692.947, 703.241, 717.394, 724.517, 743.89])

### Process literature spectrum
# data_dir = r'C:\Users\il322\Desktop\Offline Data'
# file_name = r'nanocavity_spectrum_BPT.csv'
# os.chdir(data_dir)
# lit_spectrum = np.loadtxt(file_name,skiprows=1,delimiter=',')
# lit_spectrum = spt.Spectrum(x=lit_spectrum[:,1], y=lit_spectrum[:,0])
# lit_spectrum.truncate(start_x=450, end_x = lit_spectrum.x.max())
# lit_spectrum.y_baselined = lit_spectrum.y -  spt.baseline_als(y=lit_spectrum.y,lam=1e1,p=1e-4,niter=1000)
# lit_spectrum.y_smooth = spt.butter_lowpass_filt_filt(lit_spectrum.y_baselined,
#                                                       cutoff=1500,
#                                                       fs = 40000,
#                                                       order=1)
# ### Find peaks
# lit_peaks = spt.approx_peak_gausses(lit_spectrum.x,
#                                         lit_spectrum.y_smooth,
#                                         plot=False,
#                                         threshold=0.045,
#                                         smooth_first=False,
#                                         height_frac = 0.05)

# plt.plot(lit_spectrum.x, lit_spectrum.y_smooth/lit_spectrum.y_baselined.max())
# lit_wn = []
# for peak in lit_peaks:
#     wn = peak[1]
#     lit_wn.append(wn)
# lit_wn.sort()
# lit_wn = np.array(lit_wn)

# for peak in lit_wn:
#     plt.scatter(peak, lit_spectrum.y_smooth[np.where(lit_spectrum.x == peak)] / lit_spectrum.y_baselined.max())