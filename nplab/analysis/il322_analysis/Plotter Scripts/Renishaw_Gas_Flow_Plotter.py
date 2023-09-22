# -*- coding: utf-8 -*-
"""
Created on Sat Jun 10 10:38:55 2023

@author: il322

Plotter for Renishaw M-TAPP MLAgg CO2 gas flow data

"""

import numpy as np
import scipy as sp
from matplotlib import pyplot as plt
import matplotlib as mpl
import tkinter as tk
from tkinter import filedialog
from lmfit.models import LorentzianModel
import statistics
import scipy
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
from nplab.analysis.general_spec_tools import npom_df_pl_tools as df
from nplab.analysis.SERS_Fitting import Auto_Fit_Raman as afr
from nplab.analysis.il322_analysis import il322_calibrate_spectrum as cal
from nplab.analysis.il322_analysis import il322_SERS_tools as SERS


plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)


#%% Load h5 files

my_h5 = h5py.File(r"C:\Users\il322\Desktop\Offline Data\2023-02-24_Co-TAPP-SMe_60nm Agg_Gas Flow Raman Data.h5")

#%% Renishaw doesn't need spec or efficiency calibration


#%% CO2 Gas Flow

timescan_CO2 = my_h5['Spectra']['43: 7_633nm_CO2_flow_60']['Raman (cts)']
timescan_CO2 = SERS.SERS_Timescan(timescan_CO2)
timescan_CO2.normalise(norm_individual=True)
timescan_CO2.plot_timescan(avg_chunks = 10, plot_y = timescan_CO2.Y_norm)

#%%

spectrum_N2 = my_h5['Spectra']['44: 7_633nm_N2']['Raman (cts)']
spectrum_N2 = SERS.SERS_Spectrum(spectrum_N2)
spectrum_N2.normalise()

#%%

fig, ax = plt.subplots(1,1, figsize = [10,6])

plt.plot(timescan_CO2.x, timescan_CO2.Y_norm[0], color = 'black')
plt.plot(timescan_CO2.x, timescan_CO2.Y_norm[59] + 0.2, color = 'red')
plt.plot(timescan_CO2.x, spectrum_N2.y_norm + 0.4, color = 'blue')

#%%

timescan_CO2 = my_h5['Spectra']['31: 4_1_633nm_CO2_flow_60']['Raman (cts)']
timescan_CO2 = SERS.SERS_Timescan(timescan_CO2)
timescan_CO2.normalise(norm_individual=True)
#timescan_CO2.plot_timescan(avg_chunks = 10, plot_y = timescan_CO2.Y_norm)

timescan_N2 = my_h5['Spectra']['33: 4_1_633nm_N2_flow_60']['Raman (cts)']
timescan_N2 = SERS.SERS_Timescan(timescan_N2)
timescan_N2.normalise(norm_individual=True)
#timescan_N2.plot_timescan(avg_chunks = 10, plot_y = timescan_N2.Y_norm)



timescan = timescan_CO2
timescan.Y_norm = np.append(timescan_CO2.Y_norm, timescan_N2.Y_norm, axis = 0)
timescan.t = np.append(timescan_CO2.t, timescan_N2.t + 60)
#%%
timescan.plot_timescan(avg_chunks = 10, plot_y = timescan.Y_norm, v_max = 1.2)
plt.title('633nm SERS CO$_2$ Gas Flow\nCo-TAPP-SMe MLAgg on Glass', fontsize = 'x-large')
plt.savefig('633nm N2-CO2-N2 Gas Flow Timescan.svg', format = 'svg')


fig, ax = plt.subplots(1,1, figsize = [10,6])
ax.plot(timescan.x, np.sum(timescan.Y_norm[0:5], axis = 0)/5, color = 'black', label = 'N$_2$; t = 0s',zorder=2)
ax.plot(timescan.x, np.sum(timescan.Y_norm[54:59], axis = 0)/5 + 0.1, color = 'purple', label = 'CO$_2$; t = 60s', zorder=1)
ax.plot(timescan.x, np.sum(timescan.Y_norm[114:119], axis = 0)/5  + 0.2, color = 'grey', label = 'N$_2$; t = 120s')
#ax.text(x = 2100, y = timescan.Y_norm[0][len(timescan.Y_norm)], s = 'N$_2$\nt = 0s')
#ax.set_xlim(200,2300)
ax.legend()
ax.set_xlabel('Raman shifts (cm$^{-1})')
ax.set_ylabel('Normalized SERS Intensity (a.u.)')
ax.set_title('633nm SERS CO$_2$ Gas Flow\nCo-TAPP-SMe MLAgg on Glass', fontsize = 'large')
#plt.savefig('633nm N2-CO2-N2 Gas Flow Comparison.svg', format = 'svg')

