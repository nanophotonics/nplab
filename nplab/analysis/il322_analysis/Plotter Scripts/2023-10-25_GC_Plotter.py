# -*- coding: utf-8 -*-
"""
Created on Mon Aug 07 17:52:45 2023

@author: il322

Plotter for gas chromatography spectra & analysis exported from Shimadzu

Using on data for 2023-10-13_Co-TAPP-SMe_20nm_Solution_Agg HER experiments

Quantifies H2 peak to internal CH4 ref and calculated HER rate per catalyst

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



#%% Load Shimadzu GC .txt files and then into classes


spectrum_data, peak_data = gc.process_file(r"C:\Users\ishaa\OneDrive\Desktop\Offline Data\SB109_NoInjection    _13102023_1724_001.txt")
no_inj = gc.GC_Spectrum(x = spectrum_data[:,0], y = spectrum_data[:,1], peak_data = peak_data)

spectrum_data, peak_data = gc.process_file(r"C:\Users\ishaa\OneDrive\Desktop\Offline Data\SB109_Air    _13102023_1729_001.txt")
air = gc.GC_Spectrum(x = spectrum_data[:,0], y = spectrum_data[:,1], peak_data = peak_data)

spectrum_data, peak_data = gc.process_file(r"C:\Users\ishaa\OneDrive\Desktop\Offline Data\SB109_A 0min    _13102023_1734_001.txt")
a = gc.GC_Spectrum(x = spectrum_data[:,0], y = spectrum_data[:,1], peak_data = peak_data)

spectrum_data, peak_data = gc.process_file(r"C:\Users\ishaa\OneDrive\Desktop\Offline Data\SB109_B_30min    _13102023_1740_001.txt")
b = gc.GC_Spectrum(x = spectrum_data[:,0], y = spectrum_data[:,1], peak_data = peak_data)

spectrum_data, peak_data = gc.process_file(r"C:\Users\ishaa\OneDrive\Desktop\Offline Data\SB109_C_60min    _13102023_1744_001.txt")
c1 = gc.GC_Spectrum(x = spectrum_data[:,0], y = spectrum_data[:,1], peak_data = peak_data)

spectrum_data, peak_data = gc.process_file(r"C:\Users\ishaa\OneDrive\Desktop\Offline Data\SB109_C_60min    _13102023_1754_001.txt")
c2 = gc.GC_Spectrum(x = spectrum_data[:,0], y = spectrum_data[:,1], peak_data = peak_data)

spectrum_data, peak_data = gc.process_file(r"C:\Users\ishaa\OneDrive\Desktop\Offline Data\SB109_D_90min    _13102023_1749_001.txt")
d1 = gc.GC_Spectrum(x = spectrum_data[:,0], y = spectrum_data[:,1], peak_data = peak_data)

spectrum_data, peak_data = gc.process_file(r"C:\Users\ishaa\OneDrive\Desktop\Offline Data\SB109_D_90min    _13102023_1759_001.txt")
d2 = gc.GC_Spectrum(x = spectrum_data[:,0], y = spectrum_data[:,1], peak_data = peak_data)

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
c1.plot(ax = ax, color = 'darkorange', label = '60 min')
c2.plot(ax = ax, color = 'darkorange')
d1.plot(ax = ax, color = 'red', label = '90 min')
d2.plot(ax = ax, color = 'red')
ax.legend(title = 'Illumination Time')
ax.set_title('HER Experiment - H2 GC Peak')

#plt.savefig('GC_H2.svg', format = 'svg')

#%% Quantifying H2 Produced

'''
Can put following into function where just input GC class and get out product moles and catalytic rate
Can go into GC_tools module
'''

AreaH2 = c1.peaks[0][4]
AreaCH4 = c1.peaks[3][4]


AreaH2 = 97.7
AreaCH4 = 140705


# Constants

RfH2 = 0.097 # Shimadzu response factor to H2 normalized to 2% CH4 int standard
RfCO = 0.384 # Shimadzu response factor to CO normalized to 2% CH4 int standard
IS = 0.02 # Percent of internal standard (CH4)
V_vessel = 7.8 # Volume of reactor vessel in mL
V_sol = 2.05 # Volume of reaction solution in mL
V = V_vessel - V_sol # Volume of headspace in mL
MolarGasVol = 22.41 * 1000 # Molar gas volume from ideal gas law in mL/mol


# Calculate moles of H2 produced in reaction

MolH2 = (AreaH2 / AreaCH4) / RfH2
MolH2 = MolH2 * IS * V
MolH2 = (MolH2 / MolarGasVol)



# Calculate HER rate in mmol per gram catalyst per hour

## Find mass of catalyst in reaction solution
ConcCat = 0.1 * 1e-6 # Concentration of Co-TAPP-SMe in Molar
V_sol = 2 # Volume of reaction solution in mL
GFMCat = 1583.58 # Co-TAPP-SMe molecular weight in g/mol
MolCat = ConcCat * (V_sol/1000)
MCat = MolCat * GFMCat # Mass of catalyst in g

## Find HER rate
time = 1 # Illumination time in hours
rate = (MolH2 * 1000)/MCat/time
