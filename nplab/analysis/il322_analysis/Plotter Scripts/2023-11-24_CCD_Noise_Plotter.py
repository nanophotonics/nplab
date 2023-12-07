# -*- coding: utf-8 -*-
"""
Created on Wed Apr 26 18:32:45 2023

@author: il322

Plotter for CCD Noise data testing cooler from 2023-11-17_CCD_Cooler_Test.h5


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

my_h5 = h5py.File(r"C:\Users\ishaa\OneDrive\Desktop\Offline Data\2023-11-17_CCD_Cooler_Test.h5")




#%% Plotting

particle = my_h5['CCD_Cooler']


# Add all SERS spectra to powerseries list in order

keys = list(particle.keys())
keys = natsort.natsorted(keys)
powerseries = []
for key in keys:
    if 'CCD' in key:
        powerseries.append(particle[key])
        
for i, spectrum in enumerate(powerseries):
    
    ## x-axis truncation, calibration
    spectrum = SERS.SERS_Spectrum(spectrum)
    #spectrum.x = spt.wl_to_wn(spectrum.x, 785)
    #spectrum.x = spectrum.x + coarse_shift
    #spectrum.x = spectrum.x * coarse_stretch
    #spectrum.truncate(start_x = notch_range[1], end_x = None)
    #spectrum.x = wn_cal
    spectrum.y = spt.remove_cosmic_rays(spectrum.y)
    powerseries[i] = spectrum
    

fig, ax = plt.subplots(1,1,figsize=[12,9])
ax.set_xlabel('Wavelength (nm)')
ax.set_ylabel('Normalized SERS Intensity (a.u.)')

for spectrum in powerseries:
    if '1s' in spectrum.name:
        label = '1s'
    elif '10s' in spectrum.name:
        label = '10s'
    elif '100s' in spectrum.name:
        label = '100s'
    elif '1000s' in spectrum.name:
        label = '1000s'
        
    if '-60' in spectrum.name:
        spectrum.plot(ax = ax, label = label)

ax.legend()
ax.set_title('Newton CCD Cooler Noise Test -60C')

save_dir = r'C:\Users\ishaa\OneDrive\Desktop\Offline Data\2023-11-17_CCD_Cooler_Test Plots\_'
plt.savefig(save_dir + 'CCD_Cooler_Noise_Test_-60C' + '.svg', format = 'svg')
plt.close(fig)
