# -*- coding: utf-8 -*-
"""
Created on Mon Apr 17 10:50:52 2023

@author: il322

Script to plot DF histogram of 12 samples (4 M-TAPP-SMe Molecules x 3 NP sizes)

What I'm plotting and from where

60nm:
    
    Sample: 2023-03-17_M-TAPP-SMe_60nm_NPoM: 
        h5: "S:\il322\PhD Data\M-TAPP-SMe\2023-03-17_M-TAPP-SMe_60nm-NPoM\2023-03-25_M-TAPP-SME_60nm_NPoM_Track_DF_Powerseries.h5"
            Scan 2 = 60nm Co-TAPP-SMe
            Scan 3 = 60nm Ni-TAPP-SMe
            Scan 4 = 60nm Zn-TAPP-SMe
            Scan 5 = 60nm H2-TAPP-SMe
        
80nm:
    
    Sample: 2023-03-27_M-TAPP-SMe_80nm_NPoM
        h5: "S:\il322\PhD Data\M-TAPP-SMe\2023-03-27_M-TAPP-SMe_80nm-NPoM\2023-03-31_M-TAPP-SME_80nm_NPoM_Track_DF_Powerseries.h5"
            ParticleScannerScan_1 & 2: H2-TAPP
            ParticleScannerScan_3-9: Co-TAPP
            ParticleScannerScan_10-11: Ni-TAPP
        
        h5: "S:\il322\PhD Data\M-TAPP-SMe\2023-05-10_M-TAPP-SMe_NPoM\2023-05-22_M-TAPP-SME_80nm_NPoM_Track_DF_633nmPowerseries.h5"
			Scan 3: 2023-03-23_Ni-TAPP-SMe_80nm_NPoM 
            Scans 4- 5: 2023-03-23_Zn-TAPP-SMe_80nm_NPoM
        

    Sample: 2023-05-10_M-TAPP-SMe_80nm_NPoM
        h5: "S:\il322\PhD Data\M-TAPP-SMe\2023-05-10_M-TAPP-SMe_NPoM\2023-05-12_M-TAPP-SMe_80nm_NPoM_Track_DF_633nmPowerseries.h5"
            ParticleScannerScan_1: 80nm Co-TAPP-SMe
            ParticleScannerScan_2: 80nm H2-TAPP-SMe (good DF, bad SERS)
            
        h5: "S:\il322\PhD Data\M-TAPP-SMe\2023-05-10_M-TAPP-SMe_NPoM\2023-05-15_M-TAPP-SMe_80nm_NPoM_Track_DF_633nmPowerseries.h5"
            Scans 1-5: 2023-05-10 H2-TAPP-SME_80nm_NPoM
            Scans 6-9: 2023-05-10 Ni-TAPP-SME_80nm_NPoM
            
        h5: "S:\il322\PhD Data\M-TAPP-SMe\2023-05-10_M-TAPP-SMe_NPoM\2023-05-22_M-TAPP-SME_80nm_NPoM_Track_DF_633nmPowerseries.h5"
			Scan 0: 2023-05-10_H2-TAPP-SMe_80nm_NPoM
            Scans 1-2: 2023-05-10_Co-TAPP-SMe_80nm_NPoM
            
100nm:
    
    Sample: 2023-03-27_M-TAPP-SMe_100nm_NPoM
        h5: "S:\il322\PhD Data\M-TAPP-SMe\2023-05-10_M-TAPP-SMe_NPoM\2023-05-29_M-TAPP_SMe_100nm_NPoM_Track_DF_785nmPowerseries.h5"
    		Scans 3-4: 2023-03-23_Ni-TAPP-SMe_100nm_NPoM
            Scans 5-: 2023-03-23_Zn-TAPP-SMe_100nm_NPoM
    
    Sample: 2023-05-10_M-TAPP-SMe_100nm_NPoM
        h5: "S:\il322\PhD Data\M-TAPP-SMe\2023-05-10_M-TAPP-SMe_NPoM\2023-05-29_M-TAPP_SMe_100nm_NPoM_Track_DF_785nmPowerseries.h5"
            Scan 1: 2023-05-10_H2-TAPP-SMe_100nm_NPoM
            Scan 2: 2023-05-10_Co-TAPP-SMe_100nm_NPoM

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
from nplab.analysis.il322_analysis import il322_DF_tools as df


plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)

       
#%% h5 Files
    
h5_03_25 = h5py.File(r'C:\Users\il322\Desktop\Offline Data\2023-03-25_M-TAPP-SME_60nm_NPoM_Track_DF_Powerseries.h5')
h5_03_31 = h5py.File(r'C:\Users\il322\Desktop\Offline Data\2023-03-31_M-TAPP-SME_80nm_NPoM_Track_DF_Powerseries.h5')
h5_05_12 = h5py.File(r'C:\Users\il322\Desktop\Offline Data\2023-05-12_M-TAPP-SMe_80nm_NPoM_Track_DF_633nmPowerseries.h5')
h5_05_15 = h5py.File(r'C:\Users\il322\Desktop\Offline Data\2023-05-15_M-TAPP-SMe_80nm_NPoM_Track_DF_633nmPowerseries.h5')
h5_05_22 = h5py.File(r'C:\Users\il322\Desktop\Offline Data\2023-05-22_M-TAPP-SME_80nm_NPoM_Track_DF_633nmPowerseries.h5')
h5_05_29 = h5py.File(r'C:\Users\il322\Desktop\Offline Data\2023-05-29_M-TAPP_SMe_100nm_NPoM_Track_DF_785nmPowerseries.h5')


#%% Getting particle scan lists for each molecule + NP size

H2_60nm = [h5_03_25['ParticleScannerScan_5']]

Co_60nm = [h5_03_25['ParticleScannerScan_2']]

Ni_60nm = [h5_03_25['ParticleScannerScan_3']]

Zn_60nm = [h5_03_25['ParticleScannerScan_4']]


H2_80nm = [h5_03_31['ParticleScannerScan_1'], 
          h5_03_31['ParticleScannerScan_2'], 
          h5_05_12['ParticleScannerScan_2'],
          h5_05_15['ParticleScannerScan_1'],
          h5_05_15['ParticleScannerScan_2'],
          h5_05_15['ParticleScannerScan_3'],
          h5_05_15['ParticleScannerScan_4'],
          h5_05_15['ParticleScannerScan_5'],
          h5_05_22['ParticleScannerScan_0']]

Co_80nm = [h5_03_31['ParticleScannerScan_3'],
          h5_03_31['ParticleScannerScan_4'],
          h5_03_31['ParticleScannerScan_5'],
          h5_03_31['ParticleScannerScan_6'],
          h5_03_31['ParticleScannerScan_7'],
          h5_03_31['ParticleScannerScan_8'],
          h5_03_31['ParticleScannerScan_9'],
          h5_05_12['ParticleScannerScan_1'],
          h5_05_22['ParticleScannerScan_1'],
          h5_05_22['ParticleScannerScan_2']]

Ni_80nm = [h5_03_31['ParticleScannerScan_10'],
          h5_03_31['ParticleScannerScan_11'],
          h5_05_22['ParticleScannerScan_3'],
          h5_05_15['ParticleScannerScan_6'],
          h5_05_15['ParticleScannerScan_7'],
          h5_05_15['ParticleScannerScan_8'],
          h5_05_15['ParticleScannerScan_9']]
          
Zn_80nm = [h5_05_22['ParticleScannerScan_4'],
          h5_05_22['ParticleScannerScan_5']]


H2_100nm = [h5_05_29['ParticleScannerScan_1']]

Co_100nm = [h5_05_29['ParticleScannerScan_2']]

Ni_100nm = [h5_05_29['ParticleScannerScan_3'],
           h5_05_29['ParticleScannerScan_4']]

Zn_100nm = [h5_05_29['ParticleScannerScan_5'],
           h5_05_29['ParticleScannerScan_6']]


#%% Define histogram (4x3)

fig,ax=plt.subplots(4,3,figsize=[20,20], dpi=1000) 
fig.suptitle('M-TAPP-SMe NPoM $\lambda_c$ Histogram', fontsize='x-large',x=0.5, y=0.92)#, labelpad=0)

# 60nm
ax1 = ax[0,0] # H2
ax2 = ax[1,0] # Co
ax3 = ax[2,0] # Ni
ax4 = ax[3,0] # Zn

ax1.set_ylabel('H2-TAPP-SMe\n'+'$\lambda_c$ Frequency', size= 'medium')
ax1.set_title('60nm NPoM')

ax2.set_ylabel('Co-TAPP-SMe\n'+'$\lambda_c$ Frequency', size= 'medium')

ax3.set_ylabel('Ni-TAPP-SMe\n'+'$\lambda_c$ Frequency', size= 'medium')

ax4.set_xlabel('Wavelength (nm)', size='medium')
ax4.set_ylabel('Zn-TAPP-SMe\n'+'$\lambda_c$ Frequency', size= 'medium')


# 80nm

bx1 = ax[0,1]
bx2 = ax[1,1]
bx3 = ax[2,1]
bx4 = ax[3,1]

bx1.set_title('80nm NPoM')
bx4.set_xlabel('Wavelength (nm)', size='medium')


# 100nm

cx1 = ax[0,2]
cx2 = ax[1,2]
cx3 = ax[2,2]
cx4 = ax[3,2]

cx1.set_title('100nm NPoM')
cx4.set_xlabel('Wavelength (nm)', size='medium')

#%% Processing DF data

def scan_to_crit_wln(scan_list):
    
    '''
    Function for this plotter script
    Takes particle scan list and returns crit_wln_list and df_spectra_list
    '''


    # Set lists for critical wavelength hist & rejected particles
    
    crit_wln_list = []
    df_spectra_list = []
    rejected = []


    # Loop over particles in particle scan        

    for particle_scan in scan_list:
        particle_list = natsort.natsorted(list(particle_scan.keys()))
        
        ## Loop over particles in particle scan
        for particle in particle_list:
            if 'Particle' not in particle:
                particle_list.remove(particle)
        
        
        # Loop over particles in particle scan
        
        for particle in particle_list:
            particle_name = str(particle_scan) + ': ' + particle
            particle = particle_scan[particle]
            
            ## Get z_scan, df_spectrum, crit_wln of particle
            z_scan = None
            image = None
            
            for key in particle.keys():
                if 'z_scan' in key:
                    z_scan = particle[key]
                if 'image' in key:
                    image = particle[key]
            
            if z_scan is None:
                print(particle_name + ': Z-Scan not found')
                continue
            
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
                                              plot = False,
                                              title = particle_name)
        
            
        
            ## Add crit_wln & df_spectrum to list for binning or reject
            if z_scan.aligned == True and z_scan.df_spectrum.is_npom == True:
                crit_wln_list.append(z_scan.df_spectrum.crit_wln)
                df_spectra_list.append(z_scan.df_spectrum.y_smooth)
            else:
                rejected.append(particle_name + ' - ' + z_scan.df_spectrum.not_npom_because)
                
    return crit_wln_list, df_spectra_list, rejected

#%% Send data to 4x3 histogram

## Getting single z-scan for x-axis for plotting
z_scan = h5_05_29['ParticleScannerScan_0']['Particle_0']['lab.z_scan_0']
z_scan = z_scan = df.Z_Scan(z_scan)
z_scan.condense_z_scan()
z_scan.df_spectrum = df.DF_Spectrum(x = z_scan.x,
                                  y = z_scan.df_spectrum, 
                                  y_smooth = spt.butter_lowpass_filt_filt(z_scan.df_spectrum, cutoff = 1600, fs = 200000))

## H2 60nm
crit_wln_list, df_spectra_list, rejected = scan_to_crit_wln(H2_60nm)
crit_wln_list.remove(830.0250582532867)
crit_wln_list = np.array(crit_wln_list)
df_spectra_list = np.array(df_spectra_list)   
num_bins = int(np.ceil(sqrt(len(crit_wln_list))))  
df.plot_df_histogram(crit_wln_list, 
                  df_spectra_list, 
                  z_scan.df_spectrum.x, 
                  num_bins = num_bins, 
                  bin_range = (crit_wln_list.min(), crit_wln_list.max()), 
                  df_avg_threshold = 3,
                  ax = ax1)

## Co 60nm
crit_wln_list, df_spectra_list, rejected = scan_to_crit_wln(Co_60nm)
crit_wln_list.remove(843.3752265852869)
crit_wln_list = np.array(crit_wln_list)
df_spectra_list = np.array(df_spectra_list)   
num_bins = int(np.ceil(sqrt(len(crit_wln_list))))  
df.plot_df_histogram(crit_wln_list, 
                  df_spectra_list, 
                  z_scan.df_spectrum.x, 
                  num_bins = num_bins, 
                  bin_range = (crit_wln_list.min(), crit_wln_list.max()), 
                  df_avg_threshold = 3,
                  ax = ax2)

## Ni 60nm
crit_wln_list, df_spectra_list, rejected = scan_to_crit_wln(Ni_60nm)
crit_wln_list = np.array(crit_wln_list)
df_spectra_list = np.array(df_spectra_list)   
num_bins = int(np.ceil(sqrt(len(crit_wln_list))))  
df.plot_df_histogram(crit_wln_list, 
                  df_spectra_list, 
                  z_scan.df_spectrum.x, 
                  num_bins = num_bins, 
                  bin_range = (crit_wln_list.min(), crit_wln_list.max()), 
                  df_avg_threshold = 3,
                  ax = ax3)

## Zn 60nm
crit_wln_list, df_spectra_list, rejected = scan_to_crit_wln(Zn_60nm)
crit_wln_list = np.array(crit_wln_list)
df_spectra_list = np.array(df_spectra_list)   
num_bins = int(np.ceil(sqrt(len(crit_wln_list))))  
df.plot_df_histogram(crit_wln_list, 
                  df_spectra_list, 
                  z_scan.df_spectrum.x, 
                  num_bins = num_bins, 
                  bin_range = (crit_wln_list.min(), crit_wln_list.max()), 
                  df_avg_threshold = 3,
                  ax = ax4)

## H2 80nm
crit_wln_list, df_spectra_list, rejected = scan_to_crit_wln(H2_80nm)
crit_wln_list = np.array(crit_wln_list)
df_spectra_list = np.array(df_spectra_list)   
num_bins = int(np.ceil(sqrt(len(crit_wln_list))))  
df.plot_df_histogram(crit_wln_list, 
                  df_spectra_list, 
                  z_scan.df_spectrum.x, 
                  num_bins = num_bins, 
                  bin_range = (crit_wln_list.min(), crit_wln_list.max()), 
                  df_avg_threshold = 3,
                  ax = bx1)

## Co 80nm
crit_wln_list, df_spectra_list, rejected = scan_to_crit_wln(Co_80nm)
crit_wln_list = np.array(crit_wln_list)
df_spectra_list = np.array(df_spectra_list)   
num_bins = int(np.ceil(sqrt(len(crit_wln_list))))  
df.plot_df_histogram(crit_wln_list, 
                  df_spectra_list, 
                  z_scan.df_spectrum.x, 
                  num_bins = num_bins, 
                  bin_range = (crit_wln_list.min(), crit_wln_list.max()), 
                  df_avg_threshold = 3,
                  ax = bx2)

## Ni 80nm
crit_wln_list, df_spectra_list, rejected = scan_to_crit_wln(Ni_80nm)
crit_wln_list = np.array(crit_wln_list)
df_spectra_list = np.array(df_spectra_list)   
num_bins = int(np.ceil(sqrt(len(crit_wln_list))))  
df.plot_df_histogram(crit_wln_list, 
                  df_spectra_list, 
                  z_scan.df_spectrum.x, 
                  num_bins = num_bins, 
                  bin_range = (crit_wln_list.min(), crit_wln_list.max()), 
                  df_avg_threshold = 3,
                  ax = bx3)

## Zn 80nm
crit_wln_list, df_spectra_list, rejected = scan_to_crit_wln(Zn_80nm)
crit_wln_list = np.array(crit_wln_list)
df_spectra_list = np.array(df_spectra_list)   
num_bins = int(np.ceil(sqrt(len(crit_wln_list))))  
df.plot_df_histogram(crit_wln_list, 
                  df_spectra_list, 
                  z_scan.df_spectrum.x, 
                  num_bins = num_bins, 
                  bin_range = (crit_wln_list.min(), crit_wln_list.max()), 
                  df_avg_threshold = 3,
                  ax = bx4)

## H2 100nm
crit_wln_list, df_spectra_list, rejected = scan_to_crit_wln(H2_100nm)
crit_wln_list.remove(555.4845843478499)
crit_wln_list = np.array(crit_wln_list)
df_spectra_list = np.array(df_spectra_list)   
num_bins = int(np.ceil(sqrt(len(crit_wln_list))))  
df.plot_df_histogram(crit_wln_list, 
                  df_spectra_list, 
                  z_scan.df_spectrum.x, 
                  num_bins = num_bins, 
                  bin_range = (crit_wln_list.min(), crit_wln_list.max()), 
                  df_avg_threshold = 3,
                  ax = cx1,
                  ax_df_label = 'Normalized Intensity')

## Co 100nm
crit_wln_list, df_spectra_list, rejected = scan_to_crit_wln(Co_100nm)
crit_wln_list = np.array(crit_wln_list)
crit_wln_list[np.where(crit_wln_list == 562.2646980910698)[0]] = 772.44582837 # Co 100nm
crit_wln_list[np.where(crit_wln_list == 563.3938756320938)[0]] = 791.89779684 # Co 100nm
crit_wln_list[np.where(crit_wln_list == 566.2157671695327)[0]] = 788.12177201 # Co 100nm
df_spectra_list = np.array(df_spectra_list)   
num_bins = int(np.ceil(sqrt(len(crit_wln_list))))  
df.plot_df_histogram(crit_wln_list, 
                  df_spectra_list, 
                  z_scan.df_spectrum.x, 
                  num_bins = num_bins, 
                  bin_range = (crit_wln_list.min(), crit_wln_list.max()), 
                  df_avg_threshold = 3,
                  ax = cx2,
                  ax_df_label = 'Normalized Intensity')

## Ni 100nm
crit_wln_list, df_spectra_list, rejected = scan_to_crit_wln(Ni_100nm)
crit_wln_list.remove(580.8653480560398) # Ni 100nm
crit_wln_list.remove(630.1456718583972) # Ni 100nm
crit_wln_list = np.array(crit_wln_list)
df_spectra_list = np.array(df_spectra_list)   
num_bins = int(np.ceil(sqrt(len(crit_wln_list))))  
df.plot_df_histogram(crit_wln_list, 
                  df_spectra_list, 
                  z_scan.df_spectrum.x, 
                  num_bins = num_bins, 
                  bin_range = (crit_wln_list.min(), crit_wln_list.max()), 
                  df_avg_threshold = 3,
                  ax = cx3,
                  ax_df_label = 'Normalized Intensity')

## Zn 100nm
crit_wln_list, df_spectra_list, rejected = scan_to_crit_wln(Zn_100nm)
crit_wln_list = np.array(crit_wln_list)
df_spectra_list = np.array(df_spectra_list)   
num_bins = int(np.ceil(sqrt(len(crit_wln_list))))  
df.plot_df_histogram(crit_wln_list, 
                  df_spectra_list, 
                  z_scan.df_spectrum.x, 
                  num_bins = num_bins, 
                  bin_range = (crit_wln_list.min(), crit_wln_list.max()), 
                  df_avg_threshold = 3,
                  ax = cx4,
                  ax_df_label = 'Normalized Intensity')

plt.savefig('M-TAPP-SMe Compiled DF Histogram.svg')


