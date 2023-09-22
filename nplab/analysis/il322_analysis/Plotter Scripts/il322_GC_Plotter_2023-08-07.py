# -*- coding: utf-8 -*-
"""
Created on Mon Aug 07 17:52:45 2023

@author: il322

Plotter for gas chromatography spectra & analysis exported from Shimadzu

Using on data for 2023-07-31_Co-TAPP-SMe_60nm_MLAgg_on_Glass(a) sample

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



#%% Load Shimadzu GC .txt files

filename_CoTAPP = r'C:\Users\il322\Desktop\Offline Data\2023-08-02 GC Data\Ishaan 2023-07-31(a) Co-TAPP-SMe MLAgg 10mM NaAsc_02082023_1506_001.txt'
data_CoTAPP = np.genfromtxt(filename_CoTAPP, skip_header = 108)

filename_blank = r'C:\Users\il322\Desktop\Offline Data\2023-08-02 GC Data\Ishaan 10mM NaAsc Blank_02082023_1457_001.txt'
data_blank = np.genfromtxt(filename_blank, skip_header = 108)

filename_air = r'C:\Users\il322\Desktop\Offline Data\2023-08-02 GC Data\Ishaan Blank 2_02082023_1521_001.txt'
data_air = np.genfromtxt(filename_air, skip_header = 108)


#%%
data_CoTAPP[:,1] = data_CoTAPP[:,1] - data_CoTAPP[:,1].min()
data_blank[:,1] = data_blank[:,1] - data_blank[:,1].min()
data_air[:,1] = data_air[:,1] - data_air[:,1].min()

#%% Plot

plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)
fig, (ax) = plt.subplots(1, 1, figsize=[12,8])


fig.suptitle('Gas Chromatography\n')
ax.set_title('Co-TAPP-SMe 60nm MLAgg on Glass in 10 mM NaAsc (aq)\n 1 Red Sun illumination (> 600 nm)')
ax.set_xlabel('Retention Time (min)', fontsize = 'large')
ax.set_ylabel('Intensity (a.u.)', fontsize = 'large')
#ax.set_yscale('log')

ax.plot(data_CoTAPP[:,0], data_CoTAPP[:,1], color = 'blue', label = 'Co-TAPP-SMe MLAgg in 10mM NaAsc')
ax.plot(data_blank[:,0], data_blank[:,1], color = 'magenta', label = '10mM NaAsc Control')
ax.plot(data_air[:,0], data_air[:,1], color = 'grey', label = 'Air Blank')


ax.set_xlim(1,2)
ax.set_ylim(2000,2.5e3)
ax.legend()
plt.tight_layout(pad = 0.4)
#plt.savefig('GC H2 Zoom.svg')

