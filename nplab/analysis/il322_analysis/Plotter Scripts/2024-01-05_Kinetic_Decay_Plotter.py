# -*- coding: utf-8 -*-
"""
Created on Thu Jan 18 02:50:33 2024

@author: il322

Plotter for Co-TAPP-SMe 633nm SERS Powerswitch w/ varying dark wait time:
    - Background v. powerswitch scan #
    - Peak intensity v. powerswitch scan # (1337, 1360, 1621, ratio 1337/1360)
    - Peak intensity recovery v. dark time (1337, 1360, 1621, ratio 1337/1360, background)
        - Exponential recovery fit


Data: 2024-01-05_633nm_SERS_Powerseries_LongKinetic.h5


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

from lmfit.models import GaussianModel

#%% Load h5


my_h5_ref = h5py.File(r"C:\Users\il322\Desktop\Offline Data\2023-12-19_633nm_SERS_400Grating_Powerswitch_VariedDarkTime.h5")
my_h5 = h5py.File(r"C:\Users\il322\Desktop\Offline Data\2024-01-05_633nm_SERS_Powerseries_LongKinetic.h5")


#%%

# Spectral calibration

## Get default literature BPT spectrum & peaks
lit_spectrum, lit_wn = cal.process_default_lit_spectrum()

## Load BPT ref spectrum
bpt_ref = my_h5_ref['ref_meas']['BPT_633nm']
bpt_ref = SERS.SERS_Spectrum(bpt_ref)

## Coarse adjustments to miscalibrated spectra
coarse_shift = 70 # coarse shift to ref spectrum
coarse_stretch = 1 # coarse stretch to ref spectrum
notch_range = [(130 + coarse_shift) * coarse_stretch, (180 + coarse_shift) * coarse_stretch] # Define notch range as region in wavenumbers
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
                                                        cutoff=1000,
                                                        fs = 11000,
                                                        order=2)
bpt_ref_no_notch.normalise(norm_y = bpt_ref_no_notch.y_smooth)

## Find BPT ref peaks
ref_wn = cal.find_ref_peaks(bpt_ref_no_notch, lit_spectrum = lit_spectrum, lit_wn = lit_wn, threshold = 0.06, distance = 1)

## Find calibrated wavenumbers
wn_cal = cal.calibrate_spectrum(bpt_ref_no_notch, ref_wn, lit_spectrum = lit_spectrum, lit_wn = lit_wn, linewidth = 1, deg = 2)
bpt_ref.x = wn_cal


#%% Spectral efficiency white light calibration

white_ref = my_h5_ref['ref_meas']['white_ref']
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

#%% Quick function to get directory based on particle scan & particle number (one folder per particle) or make one if it doesn't exist

def get_directory(particle_name):
        
    directory_path = r'C:\Users\il322\Desktop\Offline Data\2024-01-05 Analysis\_' + particle_name + '\\'
    
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"Directory '{directory_path}' created.")

    return directory_path


#%% Translated Bart's iterative polynomial background subtraction fit

def find_background4(w, n, m, b, tol, pol):
    """
    Find background using iterative polynomial curve fitting.

    Parameters:
    - w (numpy.ndarray): Input wave (data to be fitted and subtracted).
    - n (int): Start index for the mask initialization.
    - m (int): Stop index for the mask initialization.
    - b (int): Number of iterations for the curve fitting.
    - tol (float): Tolerance for identifying outliers during each iteration.
    - pol (numpy.ndarray): Coefficients of the polynomial to fit.

    Returns:
    - ww (numpy.ndarray): Background-subtracted wave.
    """

    # Duplicate the input wave
    bkg_data = np.copy(w)
    mask = np.ones_like(w)
    w_fit = np.nan
    subtract = np.zeros_like(w)

    # Initialize mask
    mask[0:n] = 0
    mask[m:-1] = 0

    # Perform iterative curve fitting
    ii = 0
    while ii < b:
        w_fit = np.polyval(pol, bkg_data)
        indx = np.where((w - w_fit) > tol)[0]
        mask[indx] = 0
        ii += 1

    # Calculate coefficients and subtract from the original wave
    w_coef = np.polyfit(np.arange(len(w)), bkg_data, len(pol) - 1)
    for i in range(len(w_coef)):
        subtract += w_coef[i] * np.arange(len(w))**i

    # Create the background-subtracted wave
    ww = w - subtract

    return ww

# Example usage:
# Assume 'w' is a NumPy array, 'n', 'm', 'b', 'tol', and 'pol' are variables.
# You can replace these with your actual data.
# result_wave = find_background4(w, n, m, b, tol, pol)


#%%

def timescan_chunk(timescan, chunk_size):
    
    assert timescan.Y.shape[0]%chunk_size == 0
    
    new_timescan = np.zeros((int(timescan.Y.shape[0]/chunk_size), timescan.Y.shape[1]))
    
    for i, scan in enumerate(new_timescan):
        this_scan = np.zeros(new_timescan.shape[1])
        for j in range(0,chunk_size):
            this_scan += timescan.Y[(i*chunk_size)+j]
        new_timescan[i] = this_scan
        
    return new_timescan
        
#%% Testing background subtraction


particle = my_h5['ParticleScannerScan_0']['Particle_96']


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
    spectrum.x = (spectrum.x + coarse_shift) * coarse_stretch
    spectrum.truncate(start_x = truncate_range[0], end_x = truncate_range[1])
    spectrum.x = wn_cal
    spectrum.calibrate_intensity(R_setup = R_setup,
                                  dark_counts = notch_cts,
                                  exposure = spectrum.cycle_time)
    
    ## Baseline
    spectrum.baseline = spt.baseline_als(spectrum.y[0], 1e3, 1e-2, niter = 10)
    spectrum.y_baselined = spectrum.y[0] - spectrum.baseline
    
    ## Plot raw, baseline, baseline subtracted
    spectrum.plot(ax = ax, plot_y = spectrum.y[0], title = '633nm Powerswitch', linewidth = 1, color = 'black', label = i, zorder = 30-i)
    spectrum.plot(ax = ax, plot_y = spectrum.y_baselined , title = '633nm Powerswitch', linewidth = 1, color = 'purple', label = i, zorder = 30-i)
    spectrum.plot(ax = ax, plot_y = spectrum.baseline, color = 'darkred', linewidth = 1)    
    
    ## Labeling & plotting
    # ax.legend(fontsize = 18, ncol = 5, loc = 'upper center')
    # ax.get_legend().set_title('Scan No.')
    # for line in ax.get_legend().get_lines():
    #     line.set_linewidth(4.0)
    fig.suptitle('MLAgg')
    powerseries[i] = spectrum
    
    # ax.set_xlim(1200, 1700)
    # ax.set_ylim(0, powerseries[].y_baselined.max() * 1.5)
    plt.tight_layout(pad = 0.8)


#%% Testing peak fitting - triple Gaussian region


particle = my_h5['ParticleScannerScan_0']['Particle_80']

keys = list(particle.keys())
keys = natsort.natsorted(keys)


# Get timescan
for key in keys:
    if 'SERS' in key:
        timescan = particle[key]
        
        timescan = SERS.SERS_Timescan(timescan)
        laser_power = timescan.laser_power
        print(laser_power)
        
        ## Add timescan chunks to improve S/N
        chunk_size = 1
        new_y = timescan_chunk(timescan, chunk_size)
        timescan = SERS.SERS_Timescan(x = timescan.x, y = new_y, exposure = timescan.cycle_time * chunk_size)
        timescan.laser_power = laser_power
        
        ## Process timescan
        timescan.x = spt.wl_to_wn(timescan.x, 632.8)
        timescan.x = (timescan.x + coarse_shift) * coarse_stretch
        timescan.truncate(start_x = truncate_range[0], end_x = truncate_range[1])
        timescan.x = wn_cal
        timescan.calibrate_intensity(R_setup = R_setup,
                                      dark_counts = notch_cts,
                                      exposure = timescan.exposure,
                                      laser_power = timescan.laser_power)
        for i, spectrum in enumerate(timescan.Y[0:10]):
            spectrum_baseline = spt.baseline_als(spectrum, 1e3, 1e-2, niter = 10)
            spectrum_baselined = spectrum - spectrum_baseline
            timescan.Y[i] = spectrum_baselined
            
        timescan.truncate(1350,1450)


        ## Triple Gaussian fit
        for i, spectrum in enumerate(timescan.Y[0:10]):
            
            fig, ax = plt.subplots(1,1,figsize=[12,9])
            ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
            ax.set_ylabel('SERS Intensity (cts/mW/s)')
            
            x = timescan.x
            y = spectrum
            
            max_amp = y.max()*5/0.3
            g2_amp = y[25]*5/0.28
            
            # build a model as a sum of 3 Gaussians
            model = (GaussianModel(prefix='g1_') + GaussianModel(prefix='g2_') + 
                     GaussianModel(prefix='g3_'))
            
            amplitude_tol = 0.05
            center_tol = 5
            sigma_tol = 3
            
            g1_amplitude = max_amp * 1
            g1_center = 1422
            g1_sigma = 5
            
            g2_amplitude = g2_amp
            g2_center = 1410
            g2_sigma = 5
            
            g3_amplitude = max_amp * 0.2
            g3_center = 1385
            g3_sigma = 5
            
            
            # build Parameters with initial values
            params = model.make_params(g1_amplitude = g1_amplitude,
                                       g1_center = g1_center,
                                       g1_sigma = g1_sigma,
                                       g2_amplitude = g2_amplitude,
                                       g2_center = g2_center,
                                       g2_sigma = g2_sigma,
                                       g3_amplitude = g3_amplitude,
                                       g3_center = g3_center,
                                       g3_sigma = g3_sigma)
                                      
            # optionally, set bound / constraints on Parameters:
            
            params['g1_amplitude'].min = g1_amplitude - (amplitude_tol * g1_amplitude) 
            params['g1_amplitude'].max = g1_amplitude + (amplitude_tol * g1_amplitude) 
            
            params['g2_amplitude'].min = g2_amplitude - (amplitude_tol/2 * g2_amp) 
            params['g2_amplitude'].max = g2_amplitude + (amplitude_tol/2 * g2_amp) 
            
            # params['g3_amplitude'].min = g3_amplitude - (amplitude_tol * max_amp) 
            # params['g3_amplitude'].max = g3_amplitude + (amplitude_tol * max_amp) 
                
            params['g1_center'].min = g1_center - center_tol
            params['g1_center'].max = g1_center + center_tol
            
            params['g2_center'].min = g2_center - (center_tol*1)
            params['g2_center'].max = g2_center + (center_tol*1)
            
            params['g3_center'].min = g3_center - (center_tol*5)
            params['g3_center'].max = g3_center + (center_tol*5)
            
            params['g1_sigma'].min = g1_sigma - sigma_tol
            params['g1_sigma'].max = g1_sigma + sigma_tol
            
            params['g2_sigma'].min = g2_sigma - sigma_tol
            params['g2_sigma'].max = g2_sigma + sigma_tol
            
            params['g3_sigma'].min = g3_sigma - (sigma_tol*3)
            params['g3_sigma'].max = g3_sigma + (sigma_tol*3)
            
            
            # perform the actual fit
            result = model.fit(y, params, x=x)
            
            # print fit statistics and values and uncertainties for variables
            # print(result.fit_report())
            
            # evaluate the model components ('g1_', 'g2_', and 'g3_')
            comps = result.eval_components(result.params, x=x)
            
            # plot the results
            ax.plot(x, y, label='data')
            ax.plot(x, result.best_fit, label='best fit')
            
            ax.plot(x, comps['g1_'], label='gaussian1')
            ax.plot(x, comps['g2_'], label='gaussian2')
            ax.plot(x, comps['g3_'], label='gaussian3')
            ax.legend()
            
            print(result.rsquared)
        

#%% Testing peak fitting - single Gaussian region


particle = my_h5['ParticleScannerScan_0']['Particle_96']

keys = list(particle.keys())
keys = natsort.natsorted(keys)


# Get timescan
for key in keys:
    if 'SERS' in key:
        timescan = particle[key]
        
        timescan = SERS.SERS_Timescan(timescan)
        laser_power = timescan.laser_power
        
        ## Add timescan chunks to improve S/N
        chunk_size = 1
        new_y = timescan_chunk(timescan, chunk_size)
        timescan = SERS.SERS_Timescan(x = timescan.x, y = new_y, exposure = timescan.cycle_time * chunk_size)
        timescan.laser_power = laser_power
        
        ## Process timescan
        timescan.x = spt.wl_to_wn(timescan.x, 632.8)
        timescan.x = (timescan.x + coarse_shift) * coarse_stretch
        timescan.truncate(start_x = truncate_range[0], end_x = truncate_range[1])
        timescan.x = wn_cal
        timescan.calibrate_intensity(R_setup = R_setup,
                                      dark_counts = notch_cts,
                                      exposure = timescan.exposure,
                                      laser_power = timescan.laser_power)

        for i, spectrum in enumerate(timescan.Y[0:3]):
            spectrum_baseline = spt.baseline_als(spectrum, 1e3, 1e-2, niter = 10)
            spectrum_baselined = spectrum - spectrum_baseline
            timescan.Y[i] = spectrum_baselined
        
        timescan.truncate(1600,1650)
        
       
        for i, spectrum in enumerate(timescan.Y[0:3]):
            
            ### perform the fit with optimized parameters
            x = timescan.x
            y = spectrum
            max_amp = y.max()*5/0.3
            model = (GaussianModel(prefix='g4_'))
            amplitude_tol = 0.1
            center_tol = 5
            sigma_tol = 5
            g4_amplitude = max_amp * 1
            g4_center = 1625
            g4_sigma = 5
            params = model.make_params(g4_amplitude = g4_amplitude,
                                       g4_center = g4_center,
                                       g4_sigma = g4_sigma)
            # params['g4_amplitude'].min = g4_amplitude - (amplitude_tol * g4_amplitude) 
            # params['g4_amplitude'].max = g4_amplitude + (amplitude_tol * g4_amplitude) 
            params['g4_center'].min = g4_center - center_tol
            params['g4_center'].max = g4_center + center_tol
            params['g4_sigma'].min = g4_sigma - sigma_tol
            params['g4_sigma'].max = g4_sigma + sigma_tol
            result = model.fit(y, params, x=x)
           
            ### Plot single Gaussian fit 
            fig, ax = plt.subplots(1,1,figsize=[12,9])
            ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
            ax.set_ylabel('SERS Intensity (cts/mW/s)')
            comps = result.eval_components(result.params, x=x)
            ax.plot(x, y, label='data')
            ax.plot(x, result.best_fit, label='best fit')
            ax.plot(x, comps['g4_'], label='gaussian1')
            ax.legend()
            fig.suptitle('633nm Powerswitch - Single Gaussian Fit')
           # #### Save plot
           # save_dir = get_directory(particle_name + r'\Peak Fit')
           # plt.savefig(save_dir + particle_name + '_' + str(i) + ' Single Gauss' + '.svg', format = 'svg')
           # plt.close(fig)
           
           ### return g4 amplitude value
       #     if result.rsquared < 0.95:
       #         print('\nFIT ERROR: ' + particle_name + '\n')
       #         this_particle.peaks[i][3] = 0
       #     else:
       #         this_particle.peaks[i][3] = result.params['g4_amplitude'].value
       #     powerseries[i] = spectrum
       # print('Single Gaussian')

#%% Plot timescan for each MLAgg spot across scan


scan_list = ['ParticleScannerScan_0']


# Loop over particles in particle scan
laser_powers = []
for particle_scan in scan_list:
    particle_list = []
    particle_list = natsort.natsorted(list(my_h5[particle_scan].keys()))
    
    ## Loop over particles in particle scan
    for particle in particle_list:
        if 'Particle' not in particle:
            particle_list.remove(particle)
    
    # Loop over particles in particle scan
    
    for particle in particle_list:
        particle_name = 'MLAgg_' + str(particle_scan) + '_' + particle
        particle = my_h5[particle_scan][particle]
        
        if particle_name == 'MLAgg_ParticleScannerScan_0_Particle_97':
            continue

        ## Get timescan
        keys = list(particle.keys())
        keys = natsort.natsorted(keys)
        for key in keys:
            if 'SERS' in key:
                timescan = particle[key]
                
                timescan = SERS.SERS_Timescan(timescan)
                laser_power = timescan.laser_power
                if laser_power not in laser_powers:                
                    laser_powers.append(laser_power)
                
                ## Add timescan chunks to improve S/N
                if laser_power < 0.002:
                    chunk_size = 10
                elif laser_power < 0.009:
                    chunk_size = 5
                else:
                    chunk_size = 1
                new_y = timescan_chunk(timescan, chunk_size)
                timescan = SERS.SERS_Timescan(x = timescan.x, y = new_y, exposure = timescan.cycle_time * chunk_size)
                timescan.laser_power = laser_power
                
                ## Process timescan
                timescan.x = spt.wl_to_wn(timescan.x, 632.8)
                timescan.x = (timescan.x + coarse_shift) * coarse_stretch
                timescan.truncate(start_x = truncate_range[0], end_x = truncate_range[1])
                timescan.x = wn_cal
                timescan.calibrate_intensity(R_setup = R_setup,
                                              dark_counts = notch_cts,
                                              exposure = timescan.exposure,
                                              laser_power = timescan.laser_power)
                for i, spectrum in enumerate(timescan.Y):
                    spectrum_baseline = spt.baseline_als(spectrum, 1e3, 1e-2, niter = 10)
                    spectrum_baselined = spectrum - spectrum_baseline
                    timescan.Y[i] = spectrum_baselined
        
        
        # Plot timescan
        
        fig, (ax) = plt.subplots(1, 1, figsize=[12,16])
        t_plot = np.linspace(0,len(timescan.Y)*timescan.exposure,len(timescan.Y))
        v_min = timescan.Y.min()
        v_max = np.percentile(timescan.Y, 99.9)
        cmap = plt.get_cmap('inferno')
        ax.set_yticklabels([])
        ax.set_xlabel('Raman Shifts (cm$^{-1}$)', fontsize = 'large')
        ax.set_xlim(460,1800)
        ax.set_ylabel('Time (s)', fontsize = 'large')
        ax.set_yticks(np.linspace(0,len(timescan.Y)*timescan.exposure,11))
        ax.set_yticklabels(np.linspace(0,len(timescan.Y)*timescan.exposure,11).astype('int'))
        ax.set_title('633nm Timescan - Laser Power: ' + str(laser_power*1000) + '$\mu$W\n' + str(particle_name), fontsize = 'x-large', pad = 10)
        pcm = ax.pcolormesh(timescan.x, t_plot, timescan.Y, vmin = v_min, vmax = v_max, cmap = cmap, rasterized = 'True')
        clb = fig.colorbar(pcm, ax=ax)
        clb.set_label(label = 'SERS Intensity', size = 'large', rotation = 270, labelpad=30)
        print(particle_name)
        
        ## Save plot
        save_dir = get_directory(particle_name)
        plt.savefig(save_dir + particle_name + ' Powerswitch Timescan' + '.svg', format = 'svg')
        plt.close(fig)
        print('Timescan powerswitch')
      
        
#%%
        
# Calculate & plot average over MLAgg spots for each dark_time

for j in range(0, len(avg_powerseries)):
    
    avg_powerseries[j] = avg_powerseries[j]/avg_counter[j]
    powerseries = avg_powerseries[j]
    dark_time = j*900
    particle_name = 'MLAgg_Avg_' + str(dark_time)
    print(particle_name)
        
    
    # # Plot powerswitch as stacked spectra
    
    # fig, ax = plt.subplots(1,1,figsize=[12,9])
    # ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
    # ax.set_ylabel('SERS Intensity')
    # for i, spectrum in enumerate(powerseries):
    #     spectrum = SERS.SERS_Spectrum(x = wn_cal, y = spectrum)
    #     my_cmap = plt.get_cmap('inferno')
    #     color = my_cmap(i/20)
    #     if i % 2 == 0:
    #         spectrum.plot(ax = ax, plot_y = spectrum.y, title = '', linewidth = 1, color = color, label = i, zorder = 30-i, linestyle = '-')
    #     else:
    #         spectrum.plot(ax = ax, plot_y = spectrum.y, title = '633nm Powerswitch - 1$\mu$W/100$\mu$W - Dark Time ' + str(dark_time) + 's', linewidth = 1, color = color, label = i, zorder = 30-i, linestyle = '--')
    # ax.plot(0,0, linestyle = '-', color = 'black', label = '1$\mu$W')
    # ax.plot(0,0, linestyle = '--', color = 'black', label = '100$\mu$W')
    # ax.legend(fontsize = 16, ncol = 7, loc = 'upper center')
    # ax.get_legend().set_title('Scan No.')
    # for line in ax.get_legend().get_lines():
    #     line.set_linewidth(3.0)
    # fig.suptitle(particle_name)
    # ax.set_xlim(460, 1800)
    # ax.set_ylim(0, avg_powerseries[j].max() * 1.4)
    # plt.tight_layout(pad = 0.8)
    
    # ## Save plot
    # save_dir = get_directory(particle_name)
    # plt.savefig(save_dir + particle_name + ' Powerswitch Stack' + '.svg', format = 'svg')
    # plt.close(fig)
    # print('Stacked powerswitch')
    
    
    # # Plot powerswitch as timescan
    
    # powerseries_y = powerseries
    # for i, spectrum in enumerate(powerseries):
    #     powerseries_y[i] = spectrum
    # powerseries_y = np.array(powerseries_y)
    # powerseries_y = np.insert(powerseries_y, 10, np.zeros(937), axis = 0)
    # powerseries = SERS.SERS_Timescan(x = wn_cal, y = powerseries_y, exposure = 1)
    # fig, (ax) = plt.subplots(1, 1, figsize=[12,16])
    # t_plot = np.linspace(0,20,21)
    # v_min = powerseries_y.min()
    # v_max = np.percentile(powerseries_y, 99.9)
    # cmap = plt.get_cmap('inferno')
    # ax.set_yticklabels([])
    # ax.set_xlabel('Raman Shifts (cm$^{-1}$)', fontsize = 'large')
    # ax.set_xlim(460,1800)
    # ax.text(x=750,y=9.8,s='Dark recovery time: ' + str(dark_time) + 's', color = 'white', size='x-large')
    # ax.set_title('633nm Powerswitch - Dark Time: ' + str(dark_time) + 's\n' + str(particle_name), fontsize = 'x-large', pad = 10)
    # pcm = ax.pcolormesh(powerseries.x, t_plot, powerseries_y, vmin = v_min, vmax = v_max, cmap = cmap, rasterized = 'True')
    # clb = fig.colorbar(pcm, ax=ax)
    # clb.set_label(label = 'SERS Intensity', size = 'large', rotation = 270, labelpad=30)
    
    # ## Save plot
    # save_dir = get_directory(particle_name)
    # plt.savefig(save_dir + particle_name + ' Powerswitch Timescan' + '.svg', format = 'svg')
    # plt.close(fig)
    # print('Timescan powerswitch')
    
    

#%% Fit target peaks in powerswitch scans of all MLAgg spots


class Particle(): 
    def __init__(self):
        self.peaks = np.zeros((20,5)) 



particle_list_final = []

scan_list = ['ParticleScannerScan_0', 'ParticleScannerScan_4']


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
        particle_name = 'MLAgg_' + str(particle_scan) + '_' + particle
        particle = my_h5[particle_scan][particle]
        
        if particle_name == 'MLAgg_ParticleScannerScan_0_Particle_66':
            continue

        ## Add all SERS spectra to powerseries list in order
        dark_time = 0
        keys = list(particle.keys())
        keys = sorted(keys, key=lambda x: particle[x].attrs['creation_timestamp'], reverse=False)           
        powerseries = []
        for key in keys:
            if 'SERS' in key:
                powerseries.append(particle[key])
            if 'dark' in key:
                dark_time = float(np.array(particle[key]))
        print(particle_name)
        
        this_particle = Particle()
        this_particle.dark_time = dark_time
        this_particle.particle_name = particle_name
        
        
        # Fit target peaks
        
        '''
        g1 = 1425 1/cm peak (triplet tall)
        g2 = 1405 1/cm peak (triplet middle)
        g3 = 1380 1/cm peak (triplet short)
        g4 = 1610 1/cm peak (lone peak)
        '''
        
        # Triple Guassian fit
        for i, spectrum in enumerate(powerseries):
        
            ### x-axis truncation, calibration
            spectrum = SERS.SERS_Spectrum(spectrum)
            spectrum.x = spt.wl_to_wn(spectrum.x, 632.8)
            spectrum.x = (spectrum.x + coarse_shift) * coarse_stretch
            spectrum.truncate(start_x = truncate_range[0], end_x = truncate_range[1])
            spectrum.x = wn_cal
            spectrum.calibrate_intensity(R_setup = R_setup,
                                          dark_counts = notch_cts,
                                          exposure = spectrum.cycle_time)
            spectrum.truncate(1350,1450)
            spectrum.y_baselined = spectrum.y - spt.baseline_als(spectrum.y, 1e4, 1e-3, niter = 10)
            
            ### perform the fit with optimized parameters
            x = spectrum.x
            y = spectrum.y_baselined
            
            max_amp = spectrum.y_baselined.max()*5/0.3
            g2_amp = spectrum.y_baselined[25]*5/0.28
            
            # build a model as a sum of 3 Gaussians
            model = (GaussianModel(prefix='g1_') + GaussianModel(prefix='g2_') + 
                     GaussianModel(prefix='g3_'))
            
            amplitude_tol = 0.05
            center_tol = 5
            sigma_tol = 3
            
            g1_amplitude = max_amp * 1
            g1_center = 1422
            g1_sigma = 5
            
            g2_amplitude = g2_amp
            g2_center = 1410
            g2_sigma = 5
            
            g3_amplitude = max_amp * 0.2
            g3_center = 1385
            g3_sigma = 5
            
            
            # build Parameters with initial values
            params = model.make_params(g1_amplitude = g1_amplitude,
                                       g1_center = g1_center,
                                       g1_sigma = g1_sigma,
                                       g2_amplitude = g2_amplitude,
                                       g2_center = g2_center,
                                       g2_sigma = g2_sigma,
                                       g3_amplitude = g3_amplitude,
                                       g3_center = g3_center,
                                       g3_sigma = g3_sigma)
                                      
            # optionally, set bound / constraints on Parameters:
            
            params['g1_amplitude'].min = g1_amplitude - (amplitude_tol * g1_amplitude) 
            params['g1_amplitude'].max = g1_amplitude + (amplitude_tol * g1_amplitude) 
            
            params['g2_amplitude'].min = g2_amplitude - (amplitude_tol/2 * g2_amp) 
            params['g2_amplitude'].max = g2_amplitude + (amplitude_tol/2 * g2_amp) 
            
            # params['g3_amplitude'].min = g3_amplitude - (amplitude_tol * max_amp) 
            # params['g3_amplitude'].max = g3_amplitude + (amplitude_tol * max_amp) 
                
            params['g1_center'].min = g1_center - center_tol
            params['g1_center'].max = g1_center + center_tol
            
            params['g2_center'].min = g2_center - (center_tol*1)
            params['g2_center'].max = g2_center + (center_tol*1)
            
            params['g3_center'].min = g3_center - (center_tol*5)
            params['g3_center'].max = g3_center + (center_tol*5)
            
            params['g1_sigma'].min = g1_sigma - sigma_tol
            params['g1_sigma'].max = g1_sigma + sigma_tol
            
            params['g2_sigma'].min = g2_sigma - sigma_tol
            params['g2_sigma'].max = g2_sigma + sigma_tol
            
            params['g3_sigma'].min = g3_sigma - (sigma_tol*3)
            params['g3_sigma'].max = g3_sigma + (sigma_tol*3)
            
            
            # perform the actual fit
            result = model.fit(y, params, x=x)
            
            # ### Plot triple Gaussian fit 
            # fig, ax = plt.subplots(1,1,figsize=[12,9])
            # ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
            # ax.set_ylabel('SERS Intensity (cts/mW/s)')
            # comps = result.eval_components(result.params, x=x)
            # ax.plot(x, y, label='data')
            # ax.plot(x, result.best_fit, label='best fit')
            # ax.plot(x, comps['g1_'], label='gaussian1')
            # ax.plot(x, comps['g2_'], label='gaussian2')
            # ax.plot(x, comps['g3_'], label='gaussian3')
            # ax.legend()
            # ax.set_title(particle_name + ' - Scan No: ' + str(i))
            # fig.suptitle('633nm Powerswitch - Triple Gaussian Fit')
            # #### Save plot
            # save_dir = get_directory(particle_name + r'\Peak Fit')
            # plt.savefig(save_dir + particle_name + '_' + str(i) + ' Triple Gauss' + '.svg', format = 'svg')
            # plt.close(fig)
            
            ### return g1-3 amplitude values
            if result.rsquared < 0.90:
                print('\nFIT ERROR: ' + particle_name + '\n')
                this_particle.peaks[i][0] = 0
                this_particle.peaks[i][1] = 0
                this_particle.peaks[i][2] = 0
                this_particle.peaks[i][4] = 0
            else:
                this_particle.peaks[i][0] = result.params['g1_amplitude'].value
                this_particle.peaks[i][1] = result.params['g2_amplitude'].value
                this_particle.peaks[i][2] = result.params['g3_amplitude'].value
                this_particle.peaks[i][4] = this_particle.peaks[i][0]/this_particle.peaks[i][1] 
            powerseries[i] = spectrum
        print('Triple Gaussian')
        
        ## Single Guassian fit
        powerseries = []
        for key in keys:
            if 'SERS' in key:
                powerseries.append(particle[key])
        for i, spectrum in enumerate(powerseries):
        
            ### x-axis truncation, calibration
            spectrum = SERS.SERS_Spectrum(spectrum)
            spectrum.x = spt.wl_to_wn(spectrum.x, 632.8)
            spectrum.x = (spectrum.x + coarse_shift) * coarse_stretch
            spectrum.truncate(start_x = truncate_range[0], end_x = truncate_range[1])
            spectrum.x = wn_cal
            spectrum.calibrate_intensity(R_setup = R_setup,
                                          dark_counts = notch_cts,
                                          exposure = spectrum.cycle_time)
            spectrum.truncate(1600,1650)
            spectrum.y_baselined = spectrum.y - spt.baseline_als(spectrum.y, 1e4, 1e-3, niter = 10)
            
            ### perform the fit with optimized parameters
            x = spectrum.x
            y = spectrum.y_baselined
            max_amp = spectrum.y_baselined.max()*5/0.3
            model = (GaussianModel(prefix='g4_'))
            amplitude_tol = 0.1
            center_tol = 5
            sigma_tol = 5
            g4_amplitude = max_amp * 1
            g4_center = 1625
            g4_sigma = 5
            params = model.make_params(g4_amplitude = g4_amplitude,
                                       g4_center = g4_center,
                                       g4_sigma = g4_sigma)
            # params['g4_amplitude'].min = g4_amplitude - (amplitude_tol * g4_amplitude) 
            # params['g4_amplitude'].max = g4_amplitude + (amplitude_tol * g4_amplitude) 
            params['g4_center'].min = g4_center - center_tol
            params['g4_center'].max = g4_center + center_tol
            params['g4_sigma'].min = g4_sigma - sigma_tol
            params['g4_sigma'].max = g4_sigma + sigma_tol
            result = model.fit(y, params, x=x)
            
            ### Plot single Gaussian fit 
            # fig, ax = plt.subplots(1,1,figsize=[12,9])
            # ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
            # ax.set_ylabel('SERS Intensity (cts/mW/s)')
            # comps = result.eval_components(result.params, x=x)
            # ax.plot(x, y, label='data')
            # ax.plot(x, result.best_fit, label='best fit')
            # ax.plot(x, comps['g4_'], label='gaussian1')
            # ax.legend()
            # ax.set_title(particle_name + ' - Scan No: ' + str(i))
            # fig.suptitle('633nm Powerswitch - Sing;e Gaussian Fit')
            # #### Save plot
            # save_dir = get_directory(particle_name + r'\Peak Fit')
            # plt.savefig(save_dir + particle_name + '_' + str(i) + ' Single Gauss' + '.svg', format = 'svg')
            # plt.close(fig)
            
            ### return g4 amplitude value
            if result.rsquared < 0.95:
                print('\nFIT ERROR: ' + particle_name + '\n')
                this_particle.peaks[i][3] = 0
            else:
                this_particle.peaks[i][3] = result.params['g4_amplitude'].value
            powerseries[i] = spectrum
        print('Single Gaussian')
        
        particle_list_final.append(this_particle)

#%% Loop over saved MLAgg peak spot data - plot peak amplitudes v. powerswitch        
      
    
'''
0 = 1425 1/cm peak (triplet tall)
1 = 1405 1/cm peak (triplet middle)
2 = 1380 1/cm peak (triplet short)
3 = 1610 1/cm peak (lone peak)
4 = 1425/1405 ratio
'''

# Calculate average peak stats

# ## [dark_times, scan nos, peaks]
# avg_peaks = np.zeros([11, 1, 20, 5])
# avg_counter = 0

# for i, particle in enumerate(particle_list_final):
    
#     print(particle.particle_name)
    
#     if 0 in particle.peaks:
#         print('Skipping particle with poor fit')
#         continue
    
#     index = int(particle.dark_time/900)
    
#     print(avg_peaks[index].shape)
    
#     x = np.vstack([avg_peaks[index,i], particle.peaks])
    
    
avg_peaks = np.zeros([11,20,5])
avg_counter = np.zeros(11)
for i, particle in enumerate(particle_list_final):
    
    print(particle.particle_name)
    
    if 0 in particle.peaks:
        print('Skipping particle with poor fit')
        continue
    
    index = int(particle.dark_time/900)
    
    avg_peaks[index] += particle.peaks
    avg_counter[index] += 1

for i in range(0,10):
    avg_peaks[i] = avg_peaks[i]/avg_counter[i]
#%%

# Plot peak amplitude avg v. powerswitch for each dark time

# for i in range(0,10):
#     dark_time = i * 900
#     particle_name = 'MLAgg_Avg_' + str(dark_time)
    
#     print(particle_name)
    
#     # Peak amplitude v. powerswitch
#     fig, ax = plt.subplots(1,1,figsize=[12,9])
#     ax.set_xlabel('Scan No.', size = 'large')
#     ax.set_ylabel('Peak Intensity', size = 'large')
#     ax2 = ax.twinx() 
#     ax2.set_ylabel('Peak Ratio 1425/1405', size = 'large', rotation = 270, labelpad = 30)
#     ax.set_xticks(np.linspace(0,18,10))
#     scan = np.linspace(0,19,20)
#     ax.plot(scan, avg_peaks[i,:,0], marker = 'o', markersize = 6, color = 'black', linewidth = 1, label = '1425 cm$^{-1}$', zorder = 2)          
#     ax.plot(scan, avg_peaks[i,:,1], marker = 'o', markersize = 6, color = 'red', linewidth = 1, label = '1405 cm$^{-1}$')
#     ax.plot(scan, avg_peaks[i,:,3], marker = 'o', markersize = 6, color = 'blue', linewidth = 1, label = '1610 cm$^{-1}$')   
#     ax.plot(scan, avg_peaks[i,:,0], marker = 'o', markersize = 6, color = 'purple', linewidth = 1, label = '1425/1405', zorder = 1)
#     ax2.plot(scan, avg_peaks[i,:,4], marker = 'o', markersize = 6, color = 'purple', linewidth = 1, label = '1425/1405')   
#     ax.legend()
#     fig.suptitle('633nm Powerswitch - Peak Amplitude', fontsize = 'large')
#     ax.set_title('MLAgg_Avg - Dark Time: ' + str(dark_time) + 's')
#     ymin = ax2.get_ylim()[0]
#     ymax = ax2.get_ylim()[1]
#     ax2.vlines(9.5, ymin = ymin, ymax = ymax, color = 'grey', linewidth = 8)
#     ax2.text(s = 'Dark time: ' + str(dark_time) + 's', x = 9.8, y = ymax-0.3)
#     ax2.set_ylim(ymin, ymax)
#     ## Save plot
#     save_dir = get_directory(particle_name)
#     plt.savefig(save_dir + particle_name + 'Peak Amplitude' + '.svg', format = 'svg')
#     plt.close(fig)
    
#     ## Peak amplitude v. powerswitch - low powers only
#     fig, ax = plt.subplots(1,1,figsize=[12,9])
#     ax.set_xlabel('Scan No.', size = 'large')
#     ax.set_ylabel('Peak Intensity', size = 'large')
#     ax2 = ax.twinx() 
#     ax2.set_ylabel('Peak Ratio 1425/1405', size = 'large', rotation = 270, labelpad = 30)
#     ax.set_xticks(np.linspace(0,18,10))
#     scan = np.linspace(0,18,10, dtype = int)
#     ax.plot(scan, avg_peaks[i,scan,0], marker = 'o', markersize = 6, color = 'black', linewidth = 1, label = '1425 cm$^{-1}$', zorder = 2)          
#     ax.plot(scan, avg_peaks[i,scan,1], marker = 'o', markersize = 6, color = 'red', linewidth = 1, label = '1405 cm$^{-1}$')
#     ax.plot(scan, avg_peaks[i,scan,3], marker = 'o', markersize = 6, color = 'blue', linewidth = 1, label = '1610 cm$^{-1}$')   
#     ax.plot(scan, avg_peaks[i,scan,0], marker = 'o', markersize = 6, color = 'purple', linewidth = 1, label = '1425/1405', zorder = 1)
#     ax2.plot(scan, avg_peaks[i,scan,4], marker = 'o', markersize = 6, color = 'purple', linewidth = 1, label = '1425/1405')   
#     ax.legend()
#     fig.suptitle('633nm Powerswitch - Peak Amplitude - 1$\mu$W Spectra', fontsize = 'large')
#     ax.set_title('MLAgg_Avg - Dark Time: ' + str(dark_time) + 's')
#     ymin = ax2.get_ylim()[0]
#     ymax = ax2.get_ylim()[1]
#     ax2.vlines(9.5, ymin = ymin, ymax = ymax, color = 'grey', linewidth = 8)
#     ax2.text(s = 'Dark time: ' + str(dark_time) + 's', x = 9.8, y = ymax-0.3)
#     ax2.set_ylim(ymin, ymax)
#     ## Save plot
#     save_dir = get_directory(particle_name)
#     plt.savefig(save_dir + particle_name + 'Peak Amplitude Low Power' + '.svg', format = 'svg')
#     plt.close(fig)
    
# Plot recovery v. dark time
fig, ax = plt.subplots(1,1,figsize=[12,9])
ax.set_xlabel('Dark Recovery Time (s)', size = 'large')
ax.set_ylabel('Peak Intensity Recovery (Scan 11/Scan 0)', size = 'large')
times = np.linspace(0,9000,11, dtype = int)
ax.plot(times, avg_peaks[:,10,0]/avg_peaks[:,0,0], marker = 'o', markersize = 6, color = 'black', linewidth = 1, label = '1425 cm$^{-1}$', zorder = 2)          
ax.plot(times, avg_peaks[:,10,1]/avg_peaks[:,0,1], marker = 'o', markersize = 6, color = 'red', linewidth = 1, label = '1405 cm$^{-1}$')
ax.plot(times, avg_peaks[:,10,3]/avg_peaks[:,0,3], marker = 'o', markersize = 6, color = 'blue', linewidth = 1, label = '1610 cm$^{-1}$')   
ax.plot(times, avg_peaks[:,10,4]/avg_peaks[:,0,4], marker = 'o', markersize = 6, color = 'purple', linewidth = 1, label = '1425/1405')   
ax.legend(loc = 'upper left', ncols = 2)
# ax.set_ylim(0.5,1.1)
fig.suptitle('633nm Powerswitch - Peak Recovery v. Recovery Time', fontsize = 'large')
ax.set_title('MLAgg_Avg')
## Save plot
save_dir = r'C:\Users\il322\Desktop\Offline Data\2023-12-19 Analysis\\'
plt.savefig(save_dir + 'Peak Recovery v Dark Time' + '.svg', format = 'svg')
plt.close(fig)
    
    
        



# # Plot peak amplitude v. power for each particle

# for i, particle in enumerate(particle_list_final):
    
#     print(particle.particle_name)
    
#     if 0 in particle.peaks:
#         print('Skipping particle with poor fit')
#         continue
    
#     fig, ax = plt.subplots(1,1,figsize=[12,9])
#     ax.set_xlabel('Scan No.', size = 'large')
#     ax.set_ylabel('Peak Intensity', size = 'large')
#     ax2 = ax.twinx() 
#     ax2.set_ylabel('Peak Ratio 1425/1405', size = 'large', rotation = 270, labelpad = 30)
#     ax.set_xticks(np.linspace(0,18,10))
#     scan = np.linspace(0,19,20)
#     ax.plot(scan, particle.peaks[:,0], marker = 'o', markersize = 6, color = 'black', linewidth = 1, label = '1425 cm$^{-1}$', zorder = 2)          
#     ax.plot(scan, particle.peaks[:,1], marker = 'o', markersize = 6, color = 'red', linewidth = 1, label = '1405 cm$^{-1}$')
#     ax.plot(scan, particle.peaks[:,3], marker = 'o', markersize = 6, color = 'blue', linewidth = 1, label = '1610 cm$^{-1}$')   
#     ax.plot(scan, particle.peaks[:,0], marker = 'o', markersize = 6, color = 'purple', linewidth = 1, label = '1425/1405', zorder = 1)
#     ax2.plot(scan, particle.peaks[:,0]/particle.peaks[:,1], marker = 'o', markersize = 6, color = 'purple', linewidth = 1, label = '1425/1405')   
#     ax.legend()
#     fig.suptitle('633nm Powerswitch - Peak Amplitude', fontsize = 'large')
#     ax.set_title(particle.particle_name)
#     ymin = ax2.get_ylim()[0]
#     ymax = ax2.get_ylim()[1]
#     ax2.vlines(9.5, ymin = ymin, ymax = ymax, color = 'grey', linewidth = 8)
#     ax2.text(s = 'Dark time: ' + str(particle.dark_time) + 's', x = 9.8, y = ymax-0.3)
#     ax2.set_ylim(ymin, ymax)
#     ## Save plot
#     save_dir = get_directory(particle.particle_name)
#     plt.savefig(save_dir + particle.particle_name + 'Peak Amplitude' + '.svg', format = 'svg')
#     plt.close(fig)
    
    
# # Plot peak amplitude v. power for each particle - low power scans only

# for i, particle in enumerate(particle_list_final):
    
#     print(particle.particle_name)
    
#     if 0 in particle.peaks:
#         print('Skipping particle with poor fit')
#         continue
    
#     fig, ax = plt.subplots(1,1,figsize=[12,9])
#     ax.set_xlabel('Scan No.', size = 'large')
#     ax.set_ylabel('Peak Intensity', size = 'large')
#     ax2 = ax.twinx() 
#     ax2.set_ylabel('Peak Ratio 1425/1405', size = 'large', rotation = 270, labelpad = 30)
#     ax.set_xticks(np.linspace(0,18,10))
#     scan = np.linspace(0,19,20)   
#     scan = np.linspace(0,18,10, dtype = int)
#     ax.plot(scan, particle.peaks[scan,0], marker = 'o', markersize = 6, color = 'black', linewidth = 1, label = '1425 cm$^{-1}$', zorder = 2)          
#     ax.plot(scan, particle.peaks[scan,1], marker = 'o', markersize = 6, color = 'red', linewidth = 1, label = '1405 cm$^{-1}$')
#     ax.plot(scan, particle.peaks[scan,3], marker = 'o', markersize = 6, color = 'blue', linewidth = 1, label = '1610 cm$^{-1}$')   
#     ax.plot(scan, particle.peaks[scan,0], marker = 'o', markersize = 6, color = 'purple', linewidth = 1, label = '1425/1405', zorder = 1)
#     ax2.plot(scan, particle.peaks[scan,0]/particle.peaks[scan,1], marker = 'o', markersize = 6, color = 'purple', linewidth = 1, label = '1425/1405')   
#     ax.legend()
#     fig.suptitle('633nm Powerswitch - Peak Amplitude - 1$\mu$W Spectra', fontsize = 'large')
#     ax.set_title(particle.particle_name)
#     ymin = ax2.get_ylim()[0]
#     ymax = ax2.get_ylim()[1]
#     ax2.vlines(9.5, ymin = ymin, ymax = ymax, color = 'grey', linewidth = 8)
#     ax2.text(s = 'Dark time: ' + str(particle.dark_time) + 's', x = 9.8, y = ymax-0.3)
#     ax2.set_ylim(ymin, ymax)
#     ## Save plot
#     save_dir = get_directory(particle.particle_name)
#     plt.savefig(save_dir + particle.particle_name + 'Peak Amplitude Low Power' + '.svg', format = 'svg')
#     plt.close(fig)
    
    
     
    
    
 # Decay fit with Peak amplitude v. powerswitch - low powers only
 
 ## perform the fit
 scan = np.linspace(0,18,10, dtype = int)
 times = 
 xs = scan
 ys = avg_peaks[scan,0]
 p0 = (ys[0], 5, ys[len(ys)-1]) # start with values near those we expect
 params, cv = scipy.optimize.curve_fit(monoExp, xs, ys, p0)
 m, t, b = params
 sampleRate = 10000000 # Hz
 tauSec = (1 / t) / sampleRate
 
 ## determine quality of the fit
 squaredDiffs = np.square(ys - monoExp(xs, m, t, b))
 squaredDiffsFromMean = np.square(ys - np.mean(ys))
 rSquared = 1 - np.sum(squaredDiffs) / np.sum(squaredDiffsFromMean)
 print(f"R² = {rSquared}")
 
 ## plot the results
 plt.plot(xs, ys, '.', label="data")
 plt.plot(xs, monoExp(xs, m, t, b), '--', label="fitted")
 plt.title("Fitted Exponential Curve")
 
 ## inspect the parameters
 print(f"Y = {m} * e^(-{t} * x) + {b}")
 print(f"Tau = {tauSec * 1e6} µs")
 #%%
 fig, ax = plt.subplots(1,1,figsize=[12,9])
 ax.set_xlabel('Scan No.', size = 'large')
 ax.set_ylabel('Peak Intensity', size = 'large')
 ax2 = ax.twinx() 
 ax2.set_ylabel('Peak Ratio 1425/1405', size = 'large', rotation = 270, labelpad = 30)
 ax.set_xticks(np.linspace(0,18,10))
 ax.errorbar(scan, avg_peaks[scan,0], yerr = sem_peaks[scan,0], marker = 'o', markersize = 9, color = 'black', linewidth = 0, label = '1425 cm$^{-1}$', zorder = 2, markerfacecolor = 'none', markeredgewidth = 2, capsize = 5, elinewidth = 2)          
 ax.errorbar(scan, avg_peaks[scan,1], yerr = sem_peaks[scan,1], marker = 'o', markersize = 9, color = 'red', linewidth = 0, label = '1405 cm$^{-1}$', markerfacecolor = 'none', markeredgewidth = 2, capsize = 5, elinewidth = 2)
 ax.errorbar(scan, avg_peaks[scan,3], yerr = sem_peaks[scan,3], marker = 'o', markersize = 9, color = 'blue', linewidth = 0, label = '1610 cm$^{-1}$', markerfacecolor = 'none', markeredgewidth = 2, capsize = 5, elinewidth = 2)   
 ax.errorbar(scan, avg_peaks[scan,0], yerr = sem_peaks[scan,0], marker = 'o', markersize = 9, color = 'purple', linewidth = 0, label = '1425/1405', zorder = 1, markerfacecolor = 'none', markeredgewidth = 2, capsize = 5, elinewidth = 2)
 ax2.errorbar(scan, avg_peaks[scan,4], yerr = sem_peaks[scan,4], marker = 'o', markersize = 9, color = 'purple', linewidth = 0, label = '1425/1405', markerfacecolor = 'none', markeredgewidth = 2, capsize = 5, elinewidth = 2)   
 ax.legend()
 fig.suptitle('633nm Powerswitch - Peak Amplitude - 1$\mu$W Spectra', fontsize = 'large')
 ax.set_title('MLAgg_Avg - Dark Time: ' + str(dark_time) + 's')
 ymin = ax2.get_ylim()[0]
 ymax = ax2.get_ylim()[1]
 ax2.vlines(9.5, ymin = ymin, ymax = ymax, color = 'grey', linewidth = 8)
 ax2.text(s = 'Dark time: ' + str(dark_time) + 's', x = 9.8, y = ymax-0.3)
 ax2.set_ylim(ymin, ymax)
 ## Save plot
 # save_dir = get_directory(particle_name)
 # plt.savefig(save_dir + particle_name + 'Decay Fit Peak Amplitude Low Power' + '.svg', format = 'svg')
 # plt.close(fig)
            
            
            