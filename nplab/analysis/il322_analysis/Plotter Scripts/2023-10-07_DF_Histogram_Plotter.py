# -*- coding: utf-8 -*-
"""
Created on Fri Sep 22 16:26:43 2023

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
from nplab.analysis.il322_analysis import il322_DF_tools as df


plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)

#%%

my_h5 = h5py.File(r"C:\Users\il322\Desktop\Offline Data\2023-10-03_BPT_60nm_NPoM_DF_Track.h5")


#%%


# Set lists for critical wavelength hist & rejected particles

crit_wln_list = []
df_spectra_list = []
rejected = []
scan_list = ['ParticleScannerScan_0', 'ParticleScannerScan_1', 'ParticleScannerScan_2']


# Loop over particle scans        

for particle_scan in scan_list:
    particle_list = natsort.natsorted(list(my_h5[particle_scan].keys()))
    
    ## Loop over particles in particle scan
    for particle in particle_list:
        if 'Particle' not in particle:
            particle_list.remove(particle)
    
    
    # Loop over particles in particle scan
    
    for particle in particle_list:
        particle_name = str(particle_scan) + ': ' + particle
        particle = my_h5[particle_scan][particle]
        
        ## Get z_scan, df_spectrum, crit_wln of particle
        z_scan = None
        image = None

        for key in particle.keys():
            if 'image' in key:
                image = particle[key]
                break
            
        for key in particle.keys():
            if 'z_scan' in key:
                z_scan = particle[key]
                z_scan = df.Z_Scan(z_scan, brightness_threshold = 0.01)
                
                ## Processing z-scan (x-lim,background, reference, truncate, min to 0)
                z_scan.x_lim = (450, 900)
                z_scan.Y -= z_scan.background
                z_scan.reference
                z_scan.reference -= z_scan.background
                with np.errstate(divide='ignore', invalid='ignore'):
                    z_scan.Y = np.divide(z_scan.Y, z_scan.reference)
                z_scan.Y = np.nan_to_num(z_scan.Y, posinf = 0, neginf = 0)
                z_scan.truncate(z_scan.x_lim[0], z_scan.x_lim[1])
                z_scan.Y -= z_scan.Y.min()
                        
                z_scan.condense_z_scan() # Condense z-scan into single df-spectrum
                ### Smoothing necessary for finding maxima
                z_scan.df_spectrum = df.DF_Spectrum(x = z_scan.x,
                                                  y = z_scan.df_spectrum, 
                                                  y_smooth = spt.butter_lowpass_filt_filt(z_scan.df_spectrum, cutoff = 1000, fs = 50000),
                                                  lower_threshold = -1,
                                                  upper_threshold = -0.005)
                z_scan.df_spectrum.test_if_npom()
                z_scan.df_spectrum.find_critical_wln()
                z_scan.df_spectrum = df.df_screening(z_scan = z_scan,
                                                  df_spectrum = z_scan.df_spectrum,
                                                  image = image,
                                                  tinder = True,
                                                  plot = True,
                                                  title = particle_name + ' ' + key)
                
                if z_scan.aligned == True and z_scan.df_spectrum.is_npom == True:
                    crit_wln_list.append(z_scan.df_spectrum.crit_wln)
                    df_spectra_list.append(z_scan.df_spectrum.y_smooth)
                    
                else:
                    rejected.append(particle_name + ' - ' + z_scan.df_spectrum.not_npom_because)


#%%



        
    
    