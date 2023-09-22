# -*- coding: utf-8 -*-
"""
Created on Wed Apr 26 18:32:45 2023

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
from nplab.analysis.il322_analysis import il322_calibrate_spectrum as cal

#%% Load h5
h5_MLAgg = h5py.File(r'C:\Users\il322\Desktop\Offline Data\2023-03-17_M-TAPP-SMe_60nm-MLAgg\2023-04-20.h5')
truncate_range = [185,1350]

#%% Get wn_cal

bpt_ref_633nm = h5_MLAgg['ref_meas']['BPT_ref_633nm_5s']
bpt_ref_633nm = spt.Spectrum(bpt_ref_633nm)

## Coarse wl shift because Lab 8 is crazy
bpt_ref_633nm.x_raw = bpt_ref_633nm.x_raw - 63
bpt_ref_633nm.x = bpt_ref_633nm.x - 63

## Convert to wn
bpt_ref_633nm.x = spt.wl_to_wn(bpt_ref_633nm.x, 632.8)

## Truncate out notch (use this truncation for all spectra!)
bpt_ref_633nm.truncate(truncate_range[0], truncate_range[1])

## Have to adjust ref_wn because peak fitting is not yet robust
ref_wn_633nm = [ 189.96242575,  256.60661727,  304.85947153,  416.21397689,  518.96110313,
  635.5749669,  688.10709404,  760.32610816,  818.56620529,  951.50031667, 1021.03800555]

## Get calibrated wavenumbers
wn_cal_633 = cal.run_spectral_calibration(bpt_ref_633nm, ref_wn = ref_wn_633nm)


#%% Get R_setup

white_ref_633nm = h5_MLAgg['ref_meas']['white_scatt_633nm_0.02sx10scans']
white_ref_633nm = spt.Spectrum(white_ref_633nm.attrs['wavelengths'], white_ref_633nm[5])

## Coarse wl shift because Lab 8 is crazy
white_ref_633nm.x_raw = white_ref_633nm.x_raw - 63
white_ref_633nm.x = white_ref_633nm.x - 63

## Convert to wn
white_ref_633nm.x = spt.wl_to_wn(white_ref_633nm.x, 632.8)

## Truncate out notch (same range as BPT ref above)
white_ref_633nm.truncate(truncate_range[0], truncate_range[1])

## Convert back to wl for efficiency calibration
white_ref_633nm.x = spt.wn_to_wl(white_ref_633nm.x, 632.8)

## Get white background counts in notch
notch_range = [70,125]
notch = spt.Spectrum(white_ref_633nm.x_raw[notch_range[0]:notch_range[1]], white_ref_633nm.y_raw[notch_range[0]:notch_range[1]]) 
notch_cts = notch.y.mean()


## Calculate R_setup
R_setup_633nm = cal.white_scatter_calibration(wl = white_ref_633nm.x, white_scatter = white_ref_633nm.y, white_bkg = notch_cts, plot=True)

## Test R_setup with BPT reference
notch = spt.Spectrum(bpt_ref_633nm.x_raw[notch_range[0]:notch_range[1]], bpt_ref_633nm.y_raw[notch_range[0]:notch_range[1]]) 
notch_cts = notch.y.mean()
plt.plot(bpt_ref_633nm.x, bpt_ref_633nm.y-notch_cts, color = (0.8,0.1,0.1,0.7), label = 'Raw spectrum')
plt.plot(bpt_ref_633nm.x, (bpt_ref_633nm.y-notch_cts)/R_setup_633nm, color = (0,0.6,0.2,0.5), label = 'Efficiency-corrected')
plt.legend(fontsize='x-small')
plt.show()



#%%

def plot_cv(timescan, cv_data):
    
    '''
    Plot single timescan side-by-side with CV data
    
    Parameters:
        timescan (h5 object): SERS timescan
        cv_data
    '''
    
    # Load timescan & process
    
    ## Get necessary attributes
    power = timescan.attrs['power']
    exposure = round(timescan.attrs['Exposure'],4)
    n_scans = timescan.attrs['N scans']
    scan_rate = timescan.attrs['Scan rate (mV/s)']/1000
    vertex = timescan.attrs['Vertex 2']

    ## Load time scan
    timescan = spt.Timescan(timescan)
    n_spectra = len(timescan.t_raw)
    scan_period = n_spectra/n_scans
    timescan.t = np.around(timescan.t_raw * exposure, 4)

    ## Coarse wl shift because Lab 8 is crazy
    timescan.x_raw = timescan.x_raw - 63
    timescan.x = timescan.x - 63

    ## Convert to wn
    timescan.x = spt.wl_to_wn(timescan.x, 632.8)

    ## Truncate out notch (use this truncation for all spectra!)
    timescan.x, timescan.Y = spt.truncate_spectrum(timescan.x, timescan.Y, start_wl=truncate_range[0], end_wl=truncate_range[1])

    ## Using wn_cal
    timescan.x = wn_cal_633

    ## Get notch counts
    notch_cts = 300

    ## Correct intensity
    timescan.Y = (timescan.Y-notch_cts)/(R_setup_633nm*power*exposure)

    ## Find CV voltage associated with time
    cv_period = n_spectra*exposure/n_scans
    timescan.v = ((abs(mod(timescan.t,cv_period)-cv_period/2) * (scan_rate)))
    timescan.v = timescan.v + vertex
    

    # Plot CV + SERS
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=[10,(n_spectra/250)], gridspec_kw={'width_ratios': [1, 3]}, sharey=True)
    fig.suptitle('Co-TAPP-SMe 60nm MLAgg CV 0V to ' + str(vertex) + 'V', fontsize='x-large')
    
    ## SERS timescan plotting
    cmap = plt.get_cmap('inferno')
    pcm = ax2.pcolormesh(timescan.x, timescan.t, timescan.Y, vmin = timescan.Y.min(), vmax = timescan.Y.max(), cmap = cmap)
    ax2.set_xlabel(r'Raman shift (cm$^{-1}$)', fontsize='large')
    ax2.set_ylabel(r'Time (s)', fontsize = 'large')
    fig.colorbar(pcm, ax=ax2, label = 'SERS Intensity (cts/mW/s)')

    ## CV curve plotting
    ax1.plot(cv_data[:,2]*10**6, cv_data[:,0])
    ax1.set_ylim(timescan.t.min(),timescan.t.max())
    n_ticks = 13
    time_ticks = np.linspace(cv_data[:,0].min(), cv_data[:,0].max(),n_ticks)
    volt_ticks = np.around(((abs(mod(time_ticks,cv_period)-cv_period/2) * (scan_rate))) + vertex,2)
    ax1.set_yticks(time_ticks, volt_ticks, fontsize = 'medium')
    ax1.set_ylabel('Voltage (V)', fontsize='large')
    ax1.set_xlabel('Current ($\mu$A)', fontsize='large')

    ## Plot average chunks
    chunk_size = int(2400/n_ticks) # number of spectra to average together
    avg_chunks = np.arange(0,len(timescan.t_raw)+1,chunk_size)
    for i in range(0,len(avg_chunks)-1):
        timescan_chunk = timescan.Y[avg_chunks[i]:avg_chunks[i+1]]
        timescan_avg = np.mean(timescan_chunk, axis=0)
        #plt.plot(timescan.x, timescan_avg)
        #plt.show()
        timescan_avg = spt.Spectrum(timescan.x, timescan_avg)
        timescan_avg.normalise([avg_chunks[i]*exposure,avg_chunks[i+1]*exposure])    
        ax2.plot(timescan.x, timescan_avg.y_norm, color = 'white',linewidth=1)
        
#%%

def plot_ca(timescan, ca_data):
    
    '''
    Plot single timescan side-by-side with CA data
    Need to add h-lines, avg_chunks, colorbar
    
    Parameters:
        timescan (h5 object): SERS timescan
        ca_data
        
    currently just plots timescan - need to extract ca from Ivium
    '''
    
    # Load timescan & process
    
    ## Get necessary attributes
    power = timescan.attrs['power']
    exposure = round(timescan.attrs['Exposure'],4)
    n_cycles = timescan.attrs['N_Cycles']
    cycle_time = timescan.attrs['Time per level'] * 2
    vertex = timescan.attrs['Level 2']
    ## Load time scan
    timescan = spt.Timescan(timescan)
    n_spectra = len(timescan.t_raw)
    print(n_spectra)
    cycle_period = n_spectra/n_cycles
    timescan.t = np.around(timescan.t_raw * exposure, 4)

    ## Coarse wl shift because Lab 8 is crazy
    timescan.x_raw = timescan.x_raw - 63
    timescan.x = timescan.x - 63

    ## Convert to wn
    timescan.x = spt.wl_to_wn(timescan.x, 632.8)

    ## Truncate out notch (use this truncation for all spectra!)
    timescan.x, timescan.Y = spt.truncate_spectrum(timescan.x, timescan.Y, start_wl=truncate_range[0], end_wl=truncate_range[1])

    ## Using wn_cal
    timescan.x = wn_cal_633

    ## Get notch counts
    notch_cts = 300

    ## Correct intensity
    timescan.Y = (timescan.Y-notch_cts)/(R_setup_633nm*power*exposure)
    
    
    ## Find CA voltage associated with time
    timescan.v = np.zeros(np.shape(timescan.t))
    cycle_period = n_spectra*exposure/n_cycles
    for i in range(0,len(timescan.t)):
        if mod(timescan.t[i],cycle_time) < cycle_time/2:
            timescan.v[i] = 0
        else:
            timescan.v[i] = vertex
    

    # Plot CA + SERS
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=[10,16], gridspec_kw={'width_ratios': [1, 3]}, sharey=True)
    #fig, ax2 = plt.subplots(1,1,figsize = [7, 10])
    fig.suptitle('Co-TAPP-SMe 60nm MLAgg CA 0V to ' + str(vertex) + 'V', fontsize='x-large', y = 0.92)
    
    ## SERS timescan plotting
    cmap = plt.get_cmap('inferno')
    pcm = ax2.pcolormesh(timescan.x, timescan.t, timescan.Y, vmin = timescan.Y.min(), vmax = timescan.Y.max(), cmap = cmap)
    ax2.set_xlabel(r'Raman shift (cm$^{-1}$)', fontsize='large')
    #ax2.set_ylabel(r'Time (s)', fontsize = 'large')
    fig.colorbar(pcm, ax=ax2, label = 'SERS Intensity (cts/mW/s)')
    
    
    n_ticks = n_cycles
    time_ticks = np.linspace(timescan.t.min(), timescan.t.max(), n_ticks)
    #ax2.set_yticks(time_ticks, time_ticks, fontsize = 'medium')
    
    ax1.plot(ca_data[:,1]*10**3, ca_data[:,0])
    ax1.set_ylim(timescan.t.min(),timescan.t.max())
    time_ticks = np.around(np.linspace(ca_data[:,0].min(), ca_data[:,0].max(),13),0)
    
    ax1.set_yticks(time_ticks, time_ticks, fontsize = 'medium')
    ax1.set_ylabel('Time (s)', fontsize='large')
    ax1.set_xlabel('Current ($\mu$A)', fontsize='large')
    ax1.set_ylim(0,20)
    #ax2.set_ylim(1,21.5)
    #ax2.get_yaxis().set_visible(False)
    
    
    ## Plot average chunks
    chunk_size = int(n_spectra/(n_cycles*4)) # number of spectra to average together
    avg_chunks = np.arange(0,len(timescan.t_raw)+1,chunk_size)
    for i in range(0,len(avg_chunks)-1):
        timescan_chunk = timescan.Y[avg_chunks[i]:avg_chunks[i+1]]
        timescan_avg = np.mean(timescan_chunk, axis=0)
        #plt.plot(timescan.x, timescan_avg)
        #plt.show()
        timescan_avg = spt.Spectrum(timescan.x, timescan_avg)
        timescan_avg.normalise([avg_chunks[i]*exposure,avg_chunks[i+1]*exposure])    
        ax2.plot(timescan.x, timescan_avg.y_norm, color = 'white',linewidth=1)
    
        
#%% Run CV SERS plotting

data_group = h5_MLAgg['Co-TAPP-SMe_60nm_MLAgg_on_Au_1']
particle_items = data_group.items()
for item in list(particle_items):
    
    if 'CV' in str(item):
        print(item[0])
        timescan = item[0]
        timescan = data_group[timescan]
        vertex = timescan.attrs['Vertex 2']

        cv_data = np.loadtxt(r'C:\Users\il322\Desktop\Offline Data\2023-03-17_M-TAPP-SMe_60nm-MLAgg\2023-03-17_Co-TAPP-SMe_60nm_MLAgg_on_SAM_on_Au\cv_'+str(vertex)+'.txt_1',
                              skiprows=1)
        cv_data2 = np.loadtxt(r'C:\Users\il322\Desktop\Offline Data\2023-03-17_M-TAPP-SMe_60nm-MLAgg\2023-03-17_Co-TAPP-SMe_60nm_MLAgg_on_SAM_on_Au\cv_'+str(vertex)+'.txt_2',
                              skiprows=1)
        cv_data2[:,0] = cv_data2[:,0] + float(cv_data2[len(cv_data)-1,0])
        cv_data = np.concatenate([cv_data, cv_data2])    
        plot_cv(timescan, cv_data)
        

#%% 

data_group = h5_MLAgg['Co-TAPP-SMe_60nm_MLAgg_on_Au_1']
particle_items = data_group.items()
for item in list(particle_items):
    
    if 'CA' in str(item):
        print(item[0])
        timescan = item[0]
        timescan = data_group[timescan]    
        vertex = timescan.attrs['Level 2']
        
        ca_data = np.loadtxt(r'C:\Users\il322\Desktop\Offline Data\2023-03-17_M-TAPP-SMe_60nm-MLAgg\2023-03-17_Co-TAPP-SMe_60nm_MLAgg_on_SAM_on_Au\ca_'+str(vertex)+'.txt',
                              skiprows=1)
        plot_ca(timescan, ca_data)