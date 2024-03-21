# -*- coding: utf-8 -*-
"""
Created on Mon Aug 07 17:52:45 2023

@author: il322

Plotter for gas chromatography spectra exported from Agilent

Using on data for 2024-02-14_Co-TAPP-SMe_20nm_Solution_Agg HER experiments

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
from nplab.analysis.il322_analysis import il322_GC_tools as gc



#%% Load GC files


filename = r"S:\il322\PhD Data\M-TAPP-SMe\2024-02-14_Co-TAPP-SMe_20nm_Solution_Agg\2024-02-14_CHEM_HER\ishaan_compiled_2.xlsx"
import pandas as pd
WS = pd.read_excel(filename)
data = np.array(WS)

a = spt.Spectrum(data[:,0], data[:,1])
b = spt.Spectrum(data[:,2], data[:,3])
c = spt.Spectrum(data[:,4], data[:,5])
d = spt.Spectrum(data[:,6], data[:,7])
e = spt.Spectrum(data[:,8], data[:,9])
cal = spt.Spectrum(data[:,10], data[:,11])

#%% Plotting GC Spectra
mpl.rcParams['lines.linewidth'] = 0.2
plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)
fig, (ax) = plt.subplots(1, 1, figsize=[12,8], )

fig.suptitle('20nm AuNP@Co-TAPP-SMe Solution Aggregates')

ax.set_xlabel('Retention Time (min)')
ax.set_ylabel('Intensity')
ax.set_xlim(0.5,2)
#ax.set_ylim(-1000,100000)


#no_inj.plot(ax = ax)
#air.plot(ax = ax, color = 'black')
a.plot(ax = ax, color = 'black', label = '0 min')
b.plot(ax = ax, color = 'brown', label = '30 min')
c.plot(ax = ax, color = 'darkorange', label = '60 min')
# c2.plot(ax = ax, color = 'darkorange')
d.plot(ax = ax, color = 'red', label = '90 min')
e.plot(ax = ax, color = 'purple', label = '120 min')
cal.plot(ax = ax, color = 'grey', linestyle = '--', label = 'Calibration Gas')
ax.legend(title = 'Illumination Time')
ax.set_title('HER Experiment - GC')
# ax.set_xlim(1.2,1.7)

# plt.savefig('GC_H2_zoom.svg', format = 'svg')
