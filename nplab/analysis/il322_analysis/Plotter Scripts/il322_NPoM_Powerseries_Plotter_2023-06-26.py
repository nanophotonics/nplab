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
from nplab.analysis.il322_analysis import il322_SERS_tools as SERS
from nplab.analysis.il322_analysis import il322_calibrate_spectrum as cal



plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)


#%% Loading h5

#my_h5 = h5py.File(r'S:\il322\PhD Data\M-TAPP-SMe\2023-03-17_M-TAPP-SMe_60nm-NPoM\2023-03-25_M-TAPP-SME_60nm_NPoM_Track_DF_Powerseries.h5')
my_h5 = h5py.File(r"C:\Users\il322\Desktop\Offline Data\2023-05-12_M-TAPP-SMe_80nm_NPoM_Track_DF_633nmPowerseries.h5")



#%% Get wn_cal

bpt_ref_633nm = my_h5['ref_meas']['BPT-NPoM_633nm_Grating4_690cnwln_1s']
bpt_ref_633nm = spt.Spectrum(bpt_ref_633nm)

## Convert to wn
bpt_ref_633nm.x = spt.wl_to_wn(bpt_ref_633nm.x, 632.8)
truncate_range = [210, 2400]

## Truncate out notch (use this truncation for all spectra!)
bpt_ref_633nm.truncate(truncate_range[0], truncate_range[1])
bpt_ref_633nm.plot()

## Have to adjust ref_wn because peak fitting is not yet robust
ref_wn_633nm = [ 276.74390496,  396.21252815,  468.08976025, 679.43472478,  816.85574808,  986.17656368,
 1067.96658448, 1179.79270908, 1271.98782961, 1467.40917881, 1570.24171155]

## Get calibrated wavenumbers
wn_cal_633 = cal.run_spectral_calibration(bpt_ref_633nm, ref_wn = ref_wn_633nm, ref_threshold=0.07, deg = 2, plot=True)


#%% Get R_setup

white_ref_633nm = my_h5['ref_meas']['whitescatt_Grating4_690cnwln_0.005sx10scans']
white_ref_633nm = spt.Spectrum(white_ref_633nm.attrs['wavelengths'], white_ref_633nm[5])

## Convert to wn
white_ref_633nm.x = spt.wl_to_wn(white_ref_633nm.x, 632.8)

## Truncate out notch (same range as BPT ref above)
white_ref_633nm.truncate(truncate_range[0], truncate_range[1])

## Convert back to wl for efficiency calibration
white_ref_633nm.x = spt.wn_to_wl(white_ref_633nm.x, 632.8)

## Get white background counts in notch
notch_range = [0,90]
notch = spt.Spectrum(white_ref_633nm.x_raw[notch_range[0]:notch_range[1]], white_ref_633nm.y_raw[notch_range[0]:notch_range[1]]) 
notch_cts = notch.y.mean()
notch.plot()


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
def plot_powerseries(powerseries, powerseries_powers, particle_name):
    
    #fig, (ax1, ax2) = plt.subplots(1, 2, figsize=[10,(n_spectra/250)], gridspec_kw={'width_ratios': [1, 3]}, sharey=True)
    #fig.suptitle('Co-TAPP-SMe 60nm MLAgg CV 0V to ' + str(vertex) + 'V', fontsize='x-large')
        
    fig, (ax) = plt.subplots(len(powerseries), 1, figsize=[16,48], sharex=True, sharey=True)
    fig.suptitle('H2-TAPP-SMe 80nm NPoM: ' + particle_name +'\n 633nm Powerseries', fontsize=44, y=0.91)
    #fig.suptitle(particle_name, fontsize=36, y=0.89)
    #ax0 = plt.subplot(len(powerseries)-1,1,len(powerseries)-1)
    
    # get global vmax for plotting
    v_max = 0
    for i, timescan in enumerate(powerseries):
        timescan_max = timescan.Y.max()
        if timescan_max > v_max:
            v_max = timescan_max
    
    for i, timescan in enumerate(powerseries):
        #ax[i]=plt.subplot(len(powerseries[5:8]),1,i+1, sharex=ax0)
    
        ## SERS timescan plotting
        j = len(powerseries)-1 - i
        cmap = plt.get_cmap('inferno')
        #pcm = ax[i].pcolormesh(timescan.x, timescan.t, timescan.Y, vmin = 500, vmax = 50000, cmap = cmap)
        pcm = ax[j].pcolormesh(timescan.x, timescan.t, timescan.Y, vmin = 1000, vmax = np.percentile(timescan.Y,90) + 3000, cmap = cmap)
        ax[j].set_xlabel(r'Raman shift (cm$^{-1}$)', fontsize=40)
        ax[j].tick_params(axis='x', which='major', labelsize=30)
        ax[j].tick_params(axis='y', which='major', labelsize=20)
        ax[int(len(ax)/2)].set_ylabel(r'Time (s)', fontsize = 40)
        ax[j].text(x = 2450, y = 30, s = str(powerseries_powers[i]) + 'mW', fontsize = 30)
        #ax[j].plot(timescan.x, timescan.Y[150], color='white')
        #fig.colorbar(pcm, ax = ax[i])#, label = 'SERS Intensity (cts/mW/s)')


    # ## Plot average chunks
    # chunk_size = int(2400/n_ticks) # number of spectra to average together
    # avg_chunks = np.arange(0,len(timescan.t_raw)+1,chunk_size)
    # for i in range(0,len(avg_chunks)-1):
    #     timescan_chunk = timescan.Y[avg_chunks[i]:avg_chunks[i+1]]
    #     timescan_avg = np.mean(timescan_chunk, axis=0)
    #     #plt.plot(timescan.x, timescan_avg)
    #     #plt.show()
    #     timescan_avg = spt.Spectrum(timescan.x, timescan_avg)
    #     timescan_avg.normalise([avg_chunks[i]*exposure,avg_chunks[i+1]*exposure])    
    #     ax2.plot(timescan.x, timescan_avg.y_norm, color = 'white',linewidth=1)

    fig.subplots_adjust(wspace=0)
    fig.subplots_adjust(hspace=0)
    #plt.tight_layout(pad=0,h_pad=0,w_pad=0)
    plt.show()



# #%%
# particle_names = ['Particle_0', 'Particle_1', 'Particle_6', 'Particle_9']
# for particle_name in particle_names:

#     #particle_name = 'Particle_35'
#     particle_group = my_h5['ParticleScannerScan_2'][particle_name]
    
#     ## Process each timescan in powerseries then add to powerseries list
#     items = natsort.natsorted(list(particle_group.items()))
#     powerseries = []
#     powerseries_powers = []
#     for item in items:
#         if 'Powerseries' in str(item):
#             timescan = particle_group[str(item[0])]
#             exposure = np.around(timescan.attrs['Exposure'],2)
#             power = timescan.attrs['laser_power']
#             timescan = spt.Timescan(timescan)
#             n_spectra = len(timescan.t_raw)
#             ## Convert to wn
#             timescan.x = spt.wl_to_wn(timescan.x, 632.8)
            
#             ## Truncate out notch (use this truncation for all spectra!)
#             timescan.x, timescan.Y = spt.truncate_spectrum(timescan.x, timescan.Y, start_wl=truncate_range[0], end_wl=truncate_range[1])
            
#             ## Using wn_cal
#             timescan.x = wn_cal_633
            
#             ## Get notch counts
#             notch_cts = 325
            
#             ## Correct intensity
#             timescan.Y = (timescan.Y-notch_cts)/(R_setup_633nm*power*exposure)
            
#             ## Correct time
#             timescan.t = np.around(timescan.t_raw * exposure, 4)
            
#             powerseries.append(timescan)
#             powerseries_powers.append(power)
            
#     plot_powerseries(powerseries, powerseries_powers, particle_name) 
        

#%% Getting timescans in powerseries for this particle

particle_name = 'Particle_3'
particle_group = my_h5['ParticleScannerScan_2'][particle_name]

dark_counts = particle_group['kinetic_SERS_633nm_0.2sx300scans_Powerseries']
#dark_counts = particle_group[str(item[0])]
dark_counts = SERS.SERS_Timescan(dark_counts)
## Convert to wn
dark_counts.x = spt.wl_to_wn(dark_counts.x, 632.8)

dark_counts.truncate(truncate_range[0], truncate_range[1])
dark_counts.x = wn_cal_633
dark_counts = dark_counts.Y[0]

#dark_counts = 350

#%%
dark_counts = 330
particle_names = ['Particle_3']
for particle_name in particle_names:
    particle_group = my_h5['ParticleScannerScan_2'][particle_name]
    ## Process each timescan in powerseries then add to powerseries list
    items = natsort.natsorted(list(particle_group.items()))
    powerseries = []
    powerseries_powers = []
    for item in items:
        if 'Powerseries' in str(item):
            timescan = particle_group[str(item[0])]
            timescan = SERS.SERS_Timescan(timescan)
            
            ## Convert to wn
            timescan.x = spt.wl_to_wn(timescan.x, 632.8)
            
            timescan.truncate(truncate_range[0], truncate_range[1])
            timescan.x = wn_cal_633
            laser_power = timescan.dset.attrs['laser_power']
            timescan.name = 'Dark Subtraction: ' + str(dark_counts)
            timescan.calibrate_intensity(R_setup = R_setup_633nm, dark_counts = 0, laser_power = laser_power)
            
            powerseries.append(timescan)
            powerseries_powers.append(laser_power)
#%%
fig, (ax1) = plt.subplots(1, 1, figsize=[16,16])
fig.suptitle('SERS Powerseries (633nm)  \n' + 'Co-TAPP-SMe 80nm NPoM\n' + particle_name, fontsize='x-large')

#ax1.plot(powerseries[0].x, powerseries[0].Y_norm[0], label = '0V', color = 'black')
ax1.set_xlabel(r'Raman shifts cm$^{-1}$', fontsize = 'large')
ax1.set_ylabel(r'Normalized Integrated SERS Intensity (a.u.)', fontsize = 'large')

for i , timescan in enumerate(powerseries[0:10]):
    timescan.integrate_timescan(plot=False)
    spec = timescan.integrated_spectrum
    spec.normalise()
    ax1.plot(timescan.x, spec.y_norm + (i/10), label = str(timescan.dset.attrs['laser_power']) + ' mW')
    ax1.text(x=2500, y = spec.y_norm[871] + (i/10), s= str(timescan.dset.attrs['laser_power']) + ' mW')
    #ax1.plot(timescan.x, spec.y + (i*1e7), label = str(timescan.dset.attrs['laser_power']) + ' mW')
    #ax1.set_xlim(1400,1410)
#plt.ylim(0)
plt.legend()
plt.show()    
powerseries[2].plot_timescan()

#%%

powerseries[4].plot_timescan()
#%%

plt.plot(powerseries[0].x, powerseries[0].Y[0])
plt.show()
powerseries[15].integrate_timescan()
plt.plot(powerseries[0].x, powerseries[0].integrated_spectrum.y)