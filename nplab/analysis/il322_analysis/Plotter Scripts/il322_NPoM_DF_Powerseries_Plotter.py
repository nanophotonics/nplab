# -*- coding: utf-8 -*-
"""
Created on Thu Mar 30 17:06:38 2023

@author: il322
"""

import numpy as np
import scipy as sp
from matplotlib import pyplot as plt
import matplotlib as mpl
import tkinter as tk
from tkinter import filedialog
import statistics
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
#from nplab.analysis.SERS_Fitting import Iterative_Raman_Fitting as irf

'''
raw_h5 = [r'2023-03-25_M-TAPP-SME_60nm_NPoM_Track_DF_Powerseries.h5']
data_dir = r'S:\il322\PhD Data\M-TAPP-SMe\2023-03-17_M-TAPP-SMe_60nm-NPoM'
nst.summarise_h5(data_dir = data_dir, 
             h5_files = raw_h5, 
             summary_filename = 'Summary 2023-03-25_M-TAPP-SME_60nm_NPoM_Track_DF_Powerseries.h5',
             scan_format = 'ParticleScannerScan_', 
             scans_to_omit = [0,1], 
             particle_format = 'Particle_', 
             sers_format = 'TAPP', 
             z_scan_format = 'lab.z_scan',
             img_format = 'CWL.thumb_image')
'''
'''Would be good if I could amend this function to add attribue to particle 
group in summary giving pointer to original h5 file & sample info

Currently this only takes one timescan per particle - need to fix that too

Would be good if it could take reference group(s) as well into summary

For now just using original h5 file''' 


plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)


#%% Some spectrum processing functions

def normalise(y):
    
    '''
    Simple 0-1 linear normalisation
    
    Parameters:
        y: 1D numpy array
        
    Returns:
        y_norm: normalized 1D numpy array
    '''
    
    
    y = (y-np.min(y))
    y_norm = y/np.max(y)
    
    
    return y_norm


def truncate_spectrum(spectrum, start_x, end_x, buffer = None):
    
    '''
    Truncates spectrum class & returns -> preserves class unlike spt.truncate_spectrum()
    
    Parameters:
        spectrum: input spectrum (type spt.Spectrum class)
        start_x: start wl or wn
        end_x: end wl or wn
        buffer: y-values if start_x or end_x is outside of spectrum x range, defaults to NaN
        
    Returns:
        spectrum_truncated (spt.Spectrum class)
    '''
    
    spectrum_trunc_x, spectrum_trunc_y = spt.truncate_spectrum(spectrum.x, spectrum.y, start_x, end_x, buffer)
    spectrum_truncated = spt.Spectrum(x = spectrum_trunc_x, y = spectrum_trunc_y)
    
    
    return spectrum_truncated

#%% BPT Spectral Calibration

def get_bpt_literature_peaks(data_dir = r'S:\il322\PhD Data', 
                             file_name = r'nanocavity_spectrum_BPT.csv', 
                             plot = False, 
                             smooth_first = True):
    
    '''
    Gets BPT peak centre wavenumbers from .csv file
    
    Parameters:
        data_dir: Data directory file path
        file_name: BPT spectrum.csv filename
        
    Returns:
        bpt_lit_x: x-values of bpt literature spectrum in wavenumber
        bpt_lit_y: y-values of bpt literature spectrum
        bpt_lit_wn: 1D numpy array of 3 peak positions in wavenumber
    '''
    
    
    # Load spectrum from CSV
    print('Getting literature BPT peak positions')
    os.chdir(data_dir)
    bpt_lit = np.loadtxt(file_name,skiprows=1,delimiter=',')
    bpt_lit = spt.Spectrum(x=bpt_lit[:,1], y=bpt_lit[:,0])
    
    
    # Process BPT spectrum
    
    ## Plot BPT spectrum
    if plot == True:
        bpt_lit.plot()
        
    ## Truncate BPT spectrum to remove notch
    bpt_lit = truncate_spectrum(bpt_lit, start_x = 520, end_x = bpt_lit.x.max())
    #bpt_lit = spt.Spectrum(x = bpt_lit_trunc[0], y = bpt_lit_trunc[1])
    
    ## Background subtract spectrum
    bpt_lit.y = bpt_lit.y -  spt.baseline_als(y=bpt_lit.y,lam=1e3,p=1e-2,niter=10)
    if plot == True:
        bpt_lit.plot()
    
    ## Smooth spectrum
    if smooth_first == True:
        bpt_lit.y = spt.butter_lowpass_filt_filt(bpt_lit.y, order=1)
    
    
    # Find BPT peaks
    bpt_peaks_lit = spt.approx_peak_gausses(bpt_lit.x, bpt_lit.y, plot=plot, threshold=0.08, smooth_first=False, height_frac = 0.1)
    
    ## Record peak wavenumbers
    bpt_lit_wn = []
    for peak in bpt_peaks_lit:
        wn = peak[1]
        bpt_lit_wn.append(wn)
    
    
    # Return BPT peak centre wavenumbers
    bpt_lit_wn.sort()
    bpt_lit_wn = np.array(bpt_lit_wn)
    print('   Done\n')
    return bpt_lit.x, bpt_lit.y, bpt_lit_wn
    

def spectral_calibration(meas_x, meas_y, meas_wn=None, lit_x=None, lit_y=None, lit_wn=None, plot=True):
    
    '''
    Calibrates spectrum in wavenumbers of measured spectrum to literature peak positions
    
    Parameters:
        meas_x: x-values of measured spectrum in wavenumbers
        meas_y: y-values of measured spectrum
        mean_wn: peak positions of measured spectrum
        lit_x: x-values of literature spectrum in wavenumber (optional: for plot)
        lit_y: y-values of literature spectrum (optional: for plot)
        smooth_first: butter_lowpass_filt - need to fix bkg subtraction
        plot: (boolean) plot ployfit and literature v calibrated spectra
    
    Returns:
        wn_cal: calibrated wavenumbers, 1D numpy array with same length as meas_x
    '''
    
    
    print('Calibrating spectrometer from reference')
    

    # BPT peak positions (wavenumber) from nanocavity_spectrum_bpt.csv
    '''
    Fix this so it can tell if bpt_lit_wn is input array or None
    if bpt_lit_wn.any() == None:
    '''
    '''
    lit_wn = np.array([571.32367, 1100.296, 1172.7075, 1273.3427, 1348.0537,
                           1507.6302, 1593.3044])
    meas_wn = np.array([539.66536608, 1228.17568046, 1304.75264495,
           1465.19265942, 1512.07153269, 1669.91014465, 1795.76970808])
    '''
    
    # Linear fit literature peak positions to measured peak positions
    slope_offset, wn_offset = np.polyfit(meas_wn, lit_wn, deg=1)
    
    
    # Calculate the calibrated wavenumbers using the fitted coefficients
    wn_cal = slope_offset * meas_x + wn_offset
    
    
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
        plt.plot(lit_wn, meas_wn, '.')
        plt.plot(lit_wn, (lit_wn - wn_offset)/slope_offset, '-')
        plt.xlabel('Peak Positions (cm$^{-1}$) - Literature')
        plt.ylabel('Peak Positions (cm$^{-1}$) - Measured')
        #plt.tight_layout()
        plt.show()  
        
    
        if lit_x.any() != None and lit_y.any() != None:
            plt.figure(figsize=[10,6], dpi=1000) 
            plt.plot(lit_x, normalise(lit_y), '-', color='black', label='Literature')
            #plt.plot(meas_x, normalise(meas_y), '-', color='darkorange', label = 'Measured')
            plt.plot(wn_cal, normalise(meas_y), '-', color='blue', label = 'Calibrated')
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
    S_whitescatter = np.array(white_scatter.y) - white_bkg
    
    
    # Load literature lamp emission
    S_dkfd = np.loadtxt(r'S:\il322\PhD Data\S_dkdf.txt',delimiter=',')
    
    ## Interpolate literature lamp emission
    spline = sp.interpolate.splrep(S_dkfd[...,0],S_dkfd[...,1], s=0)
    
    ## Interpolate literature lamp emission in target wln range
    S_dkfd_spline = sp.interpolate.splev(wl, spline, der=0)
    
    ## Calculate R_setup
    R_setup = S_whitescatter/np.array(S_dkfd_spline)
    R_setup = R_setup/max(R_setup)
    
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
            plt.plot(wl, normalise(white_cal), label='Calibrated white scatter', color = 'grey')
        plt.plot(wl, normalise(S_dkfd_spline),  '--', label='Literature lamp emission',color = 'black')
        plt.xlabel('Wavelength (nm)')
        plt.ylabel('Normalized Intensity (a.u.)')
        plt.title('633nm - Spectral Efficiency Calibration - White Scatter')
        plt.legend()
        plt.show()


    # Return R_setup
    print('   Done\n')
    return R_setup


#%% Loading h5

#my_h5 = h5py.File(r'S:\il322\PhD Data\M-TAPP-SMe\2023-03-17_M-TAPP-SMe_60nm-NPoM\2023-03-25_M-TAPP-SME_60nm_NPoM_Track_DF_Powerseries.h5')
my_h5 = h5py.File(r'S:\il322\PhD Data\M-TAPP-SMe\2023-03-27_M-TAPP-SMe_80nm-NPoM\2023-03-31_M-TAPP-SME_80nm_NPoM_Track_DF_Powerseries.h5')

#%% Loaf BPT literature spectrum & get peak positions

bpt_lit_x, bpt_lit_y, bpt_lit_wn = get_bpt_literature_peaks(r'S:\il322\PhD Data', r'nanocavity_spectrum_bpt.csv',smooth_first=True,plot=False)


#%% 633nm calibration

# BPT spectral calibration

## Load spectrum
bpt_ref_633nm = my_h5['ref_meas']['BPT_ref_633nm']
bpt_ref_633nm = spt.Spectrum(bpt_ref_633nm)
bpt_ref_633nm.x = spt.wl_to_wn(bpt_ref_633nm.x, 633)

## Calculate dark counts from notch region
notch_start_633nm = bpt_ref_633nm.x.min()
notch_end_633nm = 470
bpt_notch_633nm = truncate_spectrum(bpt_ref_633nm, notch_start_633nm, notch_end_633nm-25)
dark_counts_633nm = bpt_notch_633nm.y.mean()


## Process BPT spectrum
bpt_ref_633nm = truncate_spectrum(bpt_ref_633nm, notch_end_633nm, bpt_ref_633nm.x.max(),buffer=0)
wl_uncal_633nm = spt.wn_to_wl(bpt_ref_633nm.x, 633) # truncated but not calibrated -> can use to truncate other spectra before calibrating them
bpt_ref_633nm.y_clean = bpt_ref_633nm.y -  spt.baseline_als(y=bpt_ref_633nm.y,lam=1e7,p=1e-1,niter=10)
bpt_ref_633nm.y_clean = spt.butter_lowpass_filt_filt(bpt_ref_633nm.y_clean, order=2)
plt.plot(bpt_ref_633nm.x, bpt_ref_633nm.y_clean)


## Get peak positions
bpt_633nm_peaks = spt.approx_peak_gausses(bpt_ref_633nm.x, 
                                          bpt_ref_633nm.y_clean,
                                          threshold=0.08, 
                                          smooth_first=False, 
                                          plot=False, 
                                          height_frac = 0.9)


bpt_633nm_wn = []
forbidden_wn = [696.8737568122979]
for peak in bpt_633nm_peaks:
    wn = peak[1]
    if wn not in forbidden_wn:
        ''' remove when peak matching in spectral_calibration() is fixed'''
        bpt_633nm_wn.append(wn)
bpt_633nm_wn.sort()
bpt_633nm_wn = np.array(bpt_633nm_wn)

print(bpt_633nm_wn)

## Calibrate to literature peak positions
bpt_lit_wn_amended = ([ 571.32367, 1100.296  , 1172.7075 , 1273.3427 , 1348.0537 , 1593.3044 ])
wn_cal_633nm = spectral_calibration(meas_x = bpt_ref_633nm.x, 
                                    meas_y = bpt_ref_633nm.y_clean,
                                    meas_wn = bpt_633nm_wn,
                                    lit_x = bpt_lit_x, 
                                    lit_y = bpt_lit_y,
                                    lit_wn = bpt_lit_wn_amended, 
                                    plot=False)


## Get wavelengths
wl_cal_633nm = spt.wn_to_wl(wn_cal_633nm, 633)
#%%

# White scatter spectral efficiency calibration

## Load white scatter spectrum
white_scatter_633nm = my_h5['ref_meas']['whitescatt_0.002s_700cnwl']
white_scatter_633nm = spt.Spectrum(white_scatter_633nm)
white_scatter_633nm.x = spt.wl_to_wn(white_scatter_633nm.x, 633)

## Calculate dark counts from notch region
white_notch_633nm = truncate_spectrum(white_scatter_633nm, notch_start_633nm, notch_end_633nm-45)
white_bkg_633nm = white_notch_633nm.y.mean()

white_scatter_633nm = truncate_spectrum(white_scatter_633nm, notch_end_633nm, white_scatter_633nm.x.max())

## Calculate spectral efficiency matrix
R_setup_633nm = white_scatter_calibration(wl_cal_633nm, white_scatter_633nm, white_bkg_633nm, plot=True)



#%% 785nm calibration
'''
# BPT spectral calibration

## Load spectrum
bpt_ref_785nm = my_h5['ref_meas']['BPT-NPoM_785nm']
bpt_ref_785nm = spt.Spectrum(bpt_ref_785nm)
bpt_ref_785nm.x = spt.wl_to_wn(bpt_ref_785nm.x, 785)

## Calculate dark counts from notch region
notch_start_785nm = 450
notch_end_785nm = 580
bpt_notch_785nm = truncate_spectrum(bpt_ref_785nm, notch_start_785nm, notch_end_785nm-25)
SERS_bkg_785nm = bpt_notch_785nm.y.mean()

## Process BPT spectrum
bpt_ref_785nm = truncate_spectrum(bpt_ref_785nm, notch_end_785nm, bpt_ref_785nm.x.max(),buffer=0)
wl_uncal_785nm = spt.wn_to_wl(bpt_ref_785nm.x, 785) # truncated but not calibrated -> can use to truncate other spectra before calibrating them
bpt_ref_785nm.y_clean = bpt_ref_785nm.y -  spt.baseline_als(y=bpt_ref_785nm.y,lam=1e4,p=1e-1,niter=10)
bpt_ref_785nm.y_clean = spt.butter_lowpass_filt_filt(bpt_ref_785nm.y_clean, order=2)

## Get peak positions
bpt_785nm_peaks = spt.approx_peak_gausses(bpt_ref_785nm.x, 
                                          bpt_ref_785nm.y_clean,
                                          threshold=0.2, 
                                          smooth_first=False, 
                                          plot=False, 
                                          height_frac = 0.2)
bpt_785nm_wn = []
for peak in bpt_785nm_peaks:
    wn = peak[1]
    bpt_785nm_wn.append(wn)
bpt_785nm_wn.sort()
bpt_785nm_wn = np.array(bpt_785nm_wn)

#remove when peak cal is fixed
lit_wn_785nm = np.array([571.32367, 1100.296, 1172.7075, 1348.0537,
                       1507.6302, 1593.3044])
## Calibrate to literature peak positions
wn_cal_785nm = spectral_calibration(meas_x = bpt_ref_785nm.x, 
                                    meas_y = bpt_ref_785nm.y_clean,
                                    meas_wn = bpt_785nm_wn,
                                    lit_x = bpt_lit_x, 
                                    lit_y = bpt_lit_y,
                                    lit_wn = lit_wn_785nm, 
                                    plot=False)

## Get wavelengths
wl_cal_785nm = spt.wn_to_wl(wn_cal_785nm, 785)


# White scatter spectral efficiency calibration

## Load white scatter spectrum
white_scatter_785nm = my_h5['ref_meas']['whitescatt_0.001s']
white_scatter_785nm = spt.Spectrum(white_scatter_785nm)
white_scatter_785nm.x = spt.wl_to_wn(white_scatter_785nm.x, 785)

## Calculate dark counts from notch region
white_notch_785nm = truncate_spectrum(white_scatter_785nm, notch_start_785nm, notch_end_785nm-45)
white_bkg_785nm = white_notch_785nm.y.mean()

white_scatter_785nm = truncate_spectrum(white_scatter_785nm, notch_end_785nm, white_scatter_785nm.x.max())

## Calculate spectral efficiency matric
R_setup_785nm = white_scatter_calibration(wl_cal_785nm, white_scatter_785nm, white_bkg_785nm, plot=False)

#plt.plot(wn_cal_785nm, bpt_ref_785nm.y/R_setup_785nm)
#plt.plot(wn_cal_785nm, bpt_ref_785nm.y, color='black')
'''



#%% Function to extract nanocavity from single timescan

def extract_nanocavity_spectrum(timescan, plot=False):
    
    '''
    Extracts nanocavity spectrum from a timescan that contains flares or picocavities
    Calculates flat baseline value for each pixel (wln/wn) across a timescan
    The flat baseline value is the y-value (intensity) of the nanocavity at that x-value
    
    Parameters:
        timescan: (nst.Timescan class) - best if already x & y-calibrated
        plot: (boolean) plots nanocavity spectrum
        
    Returns:
        nanocavity_spectrum: (spt.Spectrum class) extracted nanocavity spectrum
    '''
    
    
    # Get flat baseline value of each pixel (x-value) across each scan of time scan
    
    pixel_baseline = np.zeros(len(timescan.x))
    for pixel in range(0,len(timescan.x)):
        pixel_baseline[pixel] = np.polyfit(timescan.t_raw, timescan.Y[:,pixel], 0)
    nanocavity_spectrum = spt.Spectrum(timescan.x, pixel_baseline)
    
    
    # Plot extracted nanocavity spectrum
    
    if plot == True:
        nanocavity_spectrum.plot()
        
    
    # Return extracted nanocavity spectrum
    
    return nanocavity_spectrum



#%% Bring above into function - getting nanocavity powerseries of single NPoM

def get_nanocavity_powerseries(particle_group, plot=False):
    
    '''
    
    '''
    
    
    # Get list of timescans
    
    items = natsort.natsorted(list(particle_group.keys()))
    timescans = []
    for item in items:
        if 'Powerseries' in str(item):
            timescans.append(item)


    # Calculate SERS background spectrum from minimum power time scan

    ## Make single timescan from select min power data, truncate
    min_power_timescan = particle_group['kinetic_SERS_633nm_1sx20scans_Powerseries_0']
    min_power_timescan = nst.NPoM_SERS_Timescan(min_power_timescan, find_dft=False)
    min_power_timescan.x, min_power_timescan.Y = spt.truncate_spectrum(min_power_timescan.x, min_power_timescan.Y, notch_end_633nm, min_power_timescan.x.max())

    ## Make calibrated timescan (x-cal & y-cal)
    min_power_timescan.x = wn_cal_633nm

    ## Extract nanocavity spectrum - SERS background
    min_power_nanocavity = extract_nanocavity_spectrum(min_power_timescan, plot=False)
    SERS_bkg = min_power_nanocavity.y

    
    # NP arrays to store full powerseries (2D) and laser powers (1D) 
    nanocavity_powerseries = np.empty((len(timescans),len(min_power_timescan.x)))
    laser_powers = np.empty(len(timescans)) 

    
    if plot == True:
        fig,ax1=plt.subplots(figsize=[10,6], dpi=1000)
        ax1.set_title('Co-TAPP-SMe 60nm NPoM - 633nm SERS Powerseries')
        ax1.set_ylabel('SERS Intensity (cts/mW/s)')
        ax1.set_xlabel('Raman shifts (cm$^{-1}$)')


    # Loop over each time scan
    
    for i_timescan, this_timescan in enumerate(timescans):
        
        if 'Powerseries' in str(this_timescan):
            ## Create single timescan & attributes
            timescan = particle_group[str(this_timescan)]
            laser_wl = int(timescan.attrs['laser_wavelength'])
            laser_power = float(timescan.attrs['laser_power'])
            laser_powers[i_timescan] = laser_power
            exposure = float(timescan.attrs['Exposure'])
            timescan = nst.NPoM_SERS_Timescan(timescan, find_dft=False)
            
            ## Processing timescan: truncate, x-cal, y-cal
            timescan.x, timescan.Y = spt.truncate_spectrum(timescan.x, timescan.Y, notch_end_633nm, timescan.x.max())
            
            ### Loop over each scan in timescan - white calibration
            for i in range(0, len(timescan.Y)):
                
                scan = timescan.Y[i,:]
                scan = scan - SERS_bkg
                #### Get linear baseline of each scan
                scan_baseline = spt.baseline_als(scan, lam=10**10, p=10**-2)
                #### White scatter calibration
                scan_cal = (scan-scan_baseline)/(laser_power*exposure*R_setup_633nm)
                timescan.Y[i] = scan_cal   

            ### Make calibrated timescan (x-cal & y-cal)
            timescan.x = wn_cal_633nm
            
            ## Extract nanocavity spectrum
            nanocavity_spectrum = extract_nanocavity_spectrum(timescan)
           
            ## Add to final array
            nanocavity_powerseries[i_timescan] = nanocavity_spectrum.y
           
            ## Plot power series
            if plot == True:
                if laser_power > 0.02: 
                    ax1.plot(timescan.x, (nanocavity_spectrum.y + (500*i_timescan)))
    

    return nanocavity_powerseries, laser_powers


#%%
'''
fig,ax1=plt.subplots(figsize=[10,6], dpi=1000) 
for i in range(7, len(nanocavity_powerseries)):
    laser_power = laser_powers[i]
    ax1.plot(timescan.x, nanocavity_powerseries[i] + (500*(i-7)))
    
#%%

get_nanocavity_powerseries(particle_group = particle_group, plot=True)
'''

#%% Expand it to each sample, average all particles from tracks together into one powerseries

current_sample = 'Ni-TAPP-SMe 80nm NPoM'
particle_scan_list = ['ParticleScannerScan_10', 'ParticleScannerScan_11']

print('\n' + current_sample)
particle_counter = 0  
avg_nanocavity_powerseries = np.zeros((18,905)) 

for particle_scan in particle_scan_list:
    print('\n'+ particle_scan)
    particle_scan = my_h5[particle_scan] 
    all_data_groups = natsort.natsorted(list(particle_scan.keys()))
    all_particle_groups = []
    
    for data_group in all_data_groups:
        if 'Particle' in str(data_group):
            all_particle_groups.append(data_group)
                  
    for particle_group in all_particle_groups:
        particle_group = particle_scan[particle_group]
        
        print('\n'+str(particle_group))
        particle_items = str(list(particle_group.items()))
        if '633nm' in particle_items:
            print('Extracting nanocavity powerseries')        
            this_particle_nanocavity_powerseries, this_particle_laser_powers = get_nanocavity_powerseries(particle_group, plot=False)
            avg_nanocavity_powerseries = avg_nanocavity_powerseries + this_particle_nanocavity_powerseries
            particle_counter = particle_counter + 1
            print('Done')
        else:
            print('Skipping: 785nm data')
            

avg_nanocavity_powerseries = avg_nanocavity_powerseries/particle_counter 
print('\nFinished!') 
        
#%%            

fig,ax1=plt.subplots(figsize=[10,8], dpi=1000) 
ax1.set_title('H2-TAPP-SMe 80nm NPoM - 633nm SERS Powerseries', color='black')
fig.suptitle('633nm SERS Powerseries - Average Nanocavity', fontsize='x-large',x=0.45)#, labelpad=0)
ax1.set_ylabel('SERS Intensity (cts/mW/s)')
ax1.set_xlabel('Raman shifts (cm$^{-1}$)')
norm = mpl.colors.LogNorm(vmin=0.003, vmax=laser_powers.max())
cmap = mpl.cm.ScalarMappable(norm=norm, cmap=mpl.cm.Greys)
cmap.set_array([])

laser_power_labels = []
for power in laser_powers:
    laser_power_labels.append(int(power))

for i in range(3,len(avg_nanocavity_powerseries)):
    ax1.plot(wn_cal_633nm, avg_nanocavity_powerseries[i]+((i-7)*1000), c=cmap.to_rgba(laser_powers[i]))
#cbar = fig.colorbar(cmap, pad=0, label ='Laser Power (mW)')
cbar = fig.colorbar(cmap, location = 'right', pad = 0)
cbar.ax.tick_params(labelsize='small')
cbar.set_label('Laser Power (mW)', rotation=270, labelpad = 30, fontsize='medium')

plt.show();
