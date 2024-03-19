# -*- coding: utf-8 -*-
"""
Created on Thu Jan 18 02:50:33 2024

@author: il322

Plotter for Lab 9 UV-Vis spectra on 2023-12_Stratchlyde AuNPs

Data S:/il322/PhD Data/Other Samples/2023-12_Stratchlyde_AuNPs/2024-02-08_Strathclyde_AuNPs_UVVis.h5

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


#%% Previous data for 20nm BBI stock

filename = r"S:\il322\PhD Data\M-TAPP-SMe\2023-10-13_Co-TAPP-SMe_20nm_Solution_Agg\2023-10-13 UV-Vis\SB109_UV1.csv"
data = np.genfromtxt(filename, delimiter = ',', skip_header = 2, skip_footer = 197, dtype = float)
water = spt.Spectrum(x = data[:,0], y = data[:,1])
BBI_20nm = spt.Spectrum(x = data[:,10], y = data[:,11])
# control.y = control.y/water.y

#%% Load h5


my_h5 = h5py.File(r"S:\il322\PhD Data\Other Samples\2023-12_Stratchlyde_AuNPs\2024-02-08_Strathclyde_AuNPs_UVVis.h5")
save_dir = r"C:\Users\il322\Desktop\Offline Data\2024-02-08 AuNP Analysis\_"

#%%

group = my_h5['OceanOpticsSpectrometer']

blank = group['water_2000ms_0']
blank = spt.Spectrum(blank)

white = group['whitelight_50ms_1']
white = spt.Spectrum(white)
white.normalise()

dark = group['dark_2000ms_0']
dark = spt.Spectrum(dark)

#%% Plot U-Vis spectra of all relevant samples

mpl.rcParams['lines.linewidth'] = 0.2
plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)
fig, (ax) = plt.subplots(1, 1, figsize=[12,10])
fig.suptitle('UV-Vis Strathclyde AuNPs', )
ax.set_xlabel('Wavelength (nm)')
ax.set_ylabel('Absorbance (a.u.)')
offset = 0.0
my_cmap = plt.get_cmap('jet')
ax.plot(1, 1, color = 'black', linestyle = '-', label = 'Centrifuged')
ax.plot(1, 1, color = 'black', linestyle = '--', label = 'Not Centrifuged')
name_list = []


# Plot Stratchlyde spectra
for i, spectrum in enumerate(list(group.keys())):
     
    if '_1_' in spectrum:
        linetype = '-'
    elif'_0_' in spectrum:
        linetype = '--'
    else:
        continue

    if 'BBI' in spectrum:
        continue
    else:
        name = 'Strath_' + spectrum[0]   
                
    if name not in name_list:
        name_list.append(name)
        
    # if '3_' not in spectrum or '4_' not in spectrum:
    #     continue

    color = my_cmap(int(np.floor(i/2)*40))
    
    spectrum = group[spectrum]
    spectrum = spt.Spectrum(spectrum)
    spectrum.y = spectrum.y-dark.y
    spectrum.y = spectrum.y/(blank.y-dark.y)
    spectrum.truncate(420,900)
    # spectrum.y = (spectrum.y * -1) + 1
    abso = -np.log10(spectrum.y)    

    if i % 2 != 0:    
        ax.plot(spectrum.x, abso + (int(np.floor(i/2))*offset), label = name, linestyle = linetype, color = color)
    else:
        ax.plot(spectrum.x, abso + (int(np.floor(i/2))*offset), linestyle = linetype, color = color)



# Plot BBI spectra
ax.plot(BBI_20nm.x, BBI_20nm.y + (int(np.floor(i/2))*offset), label = 'BBI_20nm', linestyle = '--', color = (0,0,0.5,0.5))
my_cmap = plt.get_cmap('jet')
for i, spectrum in enumerate(list(group.keys())):
     
    if '_1_' in spectrum:
        linetype = '-'
    elif'_0_' in spectrum:
        linetype = '--'
    else:
        continue

    if 'BBI' not in spectrum:
        continue

    name = spectrum[0:8]
                
    if name not in name_list:
        name_list.append(name)
    
    color = my_cmap(int((np.floor(i/2)-5) * 60))
    color_x = []
    for j in range(0,4):
        color_x.append(color[j])
    color_x[3] = 0.5
    
    color = color_x
    
    spectrum = group[spectrum]
    spectrum = spt.Spectrum(spectrum)
    spectrum.y = spectrum.y-dark.y
    spectrum.y = spectrum.y/(blank.y-dark.y)   
    spectrum.truncate(420,900)
    # spectrum.y = (spectrum.y * -1) + 1
    abso = -np.log10(spectrum.y)  

    if linetype == '-':
        ax.plot(spectrum.x, abso + (int(np.floor(i/2))*offset), label = name, linestyle = linetype, color = color)
    else:
        ax.plot(spectrum.x, abso + (int(np.floor(i/2))*offset), linestyle = linetype, color = color)
        
    print((np.floor(i/2)-6) * 30)
    
    
ax.legend(ncol = 4, loc = 'upper center', fontsize = 'medium')
ax.set_xlim(420,900)
# ax.set_ylim(0, 1 + (offset * 10))
plt.tight_layout(pad = 0.5)
# plt.savefig(save_dir + 'AuNP_UV-Vis' + '.svg', format = 'svg')

#%% Plot LSPR position for each NP batch

mpl.rcParams['lines.linewidth'] = 0.2
plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)
fig, (ax) = plt.subplots(1, 1, figsize=[14,10])
fig.suptitle('LSPR Position - Strathclyde AuNPs', )
ax.set_xlabel('Estimated NP Size (Increasing)')
ax.set_ylabel('LSPR Peak Position (nm)')
offset = 0.0
my_cmap = plt.get_cmap('jet')
ax.plot(1, 1, color = 'black', linestyle = '-', label = 'Centrifuged')
ax.plot(1, 1, color = 'black', linestyle = '--', label = 'Not Centrifuged')
spectrum_list = ['1_1_2000ms_0',
                 '20nm',
                 '2_1_2000ms_0',
                 'BBI_40nm_1_2000ms_0',
                 '3_1_2000ms_0',
                 '4_1_2000ms_0',
                 'BBI_60nm_1_2000ms_0',
                 '5_1_2000ms_0',
                 'BBI_80nm_1_2000ms_0',
                 '6_1_2000ms_0']

    
# Plot Strathclyde LSPR position - centrifuged only
for i, spectrum in enumerate(spectrum_list):
     
    
    if 'BBI' in spectrum or '20nm' in spectrum:
        name = spectrum[0:8]
        color = 'red'
    elif '_1' in spectrum:
        name = 'Strath_' + spectrum[0]   
        color = 'black'
    else:
        continue
         
    if spectrum != '20nm':
        spectrum = group[spectrum]
        spectrum = spt.Spectrum(spectrum)
        spectrum.y = spectrum.y-dark.y
        spectrum.y = spectrum.y/(blank.y-dark.y)
        spectrum.y = (spectrum.y * -1) + 1
    else:
        spectrum = BBI_20nm
        name = 'BBI_20nm'
        color = 'red'        
        
    spectrum.truncate(420,800)
    lspr = spectrum.x[np.nanargmax(spectrum.y)]

    ax.scatter(name, lspr, color = color, s = 100)



# ax.set_xlim(420,900)
ax.set_ylim(500, 560)
plt.tight_layout(pad = 0.5)
# plt.savefig(save_dir + 'AuNP_UV-Vis_LSPR' + '.svg', format = 'svg')


#%% Plot absorbance at 520nm for each batch

mpl.rcParams['lines.linewidth'] = 0.2
plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)
fig, (ax) = plt.subplots(1, 1, figsize=[14,10])
fig.suptitle('Absorbance @ 520nm - Strathclyde AuNPs', )
ax.set_xlabel('Estimated NP Size (Increasing)')
ax.set_ylabel('Absorbance at 520nm (a.u.)')
offset = 0.0
my_cmap = plt.get_cmap('jet')
ax.plot(1, 1, color = 'black', linestyle = '-', label = 'Centrifuged')
ax.plot(1, 1, color = 'black', linestyle = '--', label = 'Not Centrifuged')
spectrum_list = ['1_1_2000ms_0',
                 '20nm',
                 '2_1_2000ms_0',
                 'BBI_40nm_0_2000ms_0',
                 '3_1_2000ms_0',
                 '4_1_2000ms_0',
                 'BBI_60nm_0_2000ms_0',
                 '5_1_2000ms_0',
                 'BBI_80nm_0_2000ms_0',
                 '6_1_2000ms_0']

    
# Plot Strathclyde LSPR position - centrifuged only
for i, spectrum in enumerate(spectrum_list):
     
    
    if 'BBI' in spectrum or '20nm' in spectrum:
        name = spectrum[0:8]
        color = 'red'
    elif '_1' in spectrum:
        name = 'Strath_' + spectrum[0]   
        color = 'black'
    else:
        continue
         
    if spectrum != '20nm':
        spectrum = group[spectrum]
        spectrum = spt.Spectrum(spectrum)
        spectrum.y = spectrum.y-dark.y
        spectrum.y = spectrum.y/(blank.y-dark.y)
        # spectrum.y = (spectrum.y * -1) + 1
    else:
        spectrum = BBI_20nm
        name = 'BBI_20nm'
        color = 'red'        
        
    spectrum.truncate(420,800)
    x = np.where(np.logical_and(spectrum.x>519.5, spectrum.x<520.5))
    abso = -np.log10(spectrum.y)[x]
    
    if name == 'BBI_20nm':
        abso = 0.59
    ax.scatter(name, abso, color = color, s = 100)



# ax.set_xlim(420,900)
ax.set_ylim(0, 1)
plt.tight_layout(pad = 0.5)
# plt.savefig(save_dir + 'AuNP_UV-Vis_Abs520' + '.svg', format = 'svg')

#%% Plot absorbance at 520nm in ODU
''' Dvide absorbance by path length in cm'''

mpl.rcParams['lines.linewidth'] = 0.2
plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)
fig, (ax) = plt.subplots(1, 1, figsize=[14,10])
fig.suptitle('Absorbance @ 520nm - Strathclyde AuNPs', )
ax.set_xlabel('Estimated NP Size (Increasing)')
ax.set_ylabel('Absorbance at 520nm (OD/cm)')
offset = 0.0
my_cmap = plt.get_cmap('jet')
ax.plot(1, 1, color = 'black', linestyle = '-', label = 'Centrifuged')
ax.plot(1, 1, color = 'black', linestyle = '--', label = 'Not Centrifuged')
spectrum_list = ['1_1_2000ms_0',
                 '20nm',
                 '2_1_2000ms_0',
                 'BBI_40nm_0_2000ms_0',
                 '3_1_2000ms_0',
                 '4_1_2000ms_0',
                 'BBI_60nm_0_2000ms_0',
                 '5_1_2000ms_0',
                 'BBI_80nm_0_2000ms_0',
                 '6_1_2000ms_0']

    
# Plot Strathclyde LSPR position - centrifuged only
for i, spectrum in enumerate(spectrum_list):
     
    
    if 'BBI' in spectrum or '20nm' in spectrum:
        name = spectrum[0:8]
        color = 'red'
    elif '_1' in spectrum:
        name = 'Strath_' + spectrum[0]   
        color = 'black'
    else:
        continue
         
    if spectrum != '20nm':
        spectrum = group[spectrum]
        spectrum = spt.Spectrum(spectrum)
        spectrum.y = spectrum.y-dark.y
        spectrum.y = spectrum.y/(blank.y-dark.y)
        # spectrum.y = (spectrum.y * -1) + 1
    else:
        spectrum = BBI_20nm
        name = 'BBI_20nm'
        color = 'red'        
        
    spectrum.truncate(420,800)
    x = np.where(np.logical_and(spectrum.x>519.5, spectrum.x<520.5))
    abso = -np.log10(spectrum.y)[x]/0.5
    
    if name == 'BBI_20nm':
        abso = 0.59/0.5

    ax.scatter(name, abso, color = color, s = 100)
    
    print(name)
    print(abso)



# ax.set_xlim(420,900)
# ax.set_ylim(0, 1.5)
plt.tight_layout(pad = 0.5)
# plt.savefig(save_dir + 'AuNP_UV-Vis_Abs520_ODU' + '.svg', format = 'svg')


