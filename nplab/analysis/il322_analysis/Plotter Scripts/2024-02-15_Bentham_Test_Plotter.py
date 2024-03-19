# -*- coding: utf-8 -*-
"""
Created on Thu Feb 15 23:42:43 2024

@author: il322

Plotter for Bentham wavelength & power test

Data "S:\il322\PhD Data\Lab 1 BX-60\2024-02-15_Bentham_Installation\2024-02-15_Bentham_Test.h5"

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


#%% Load h5

my_h5 = h5py.File(r"S:\il322\PhD Data\Lab 1 BX-60\2024-02-15_Bentham_Installation\2024-02-15_Bentham_Test.h5")
save_dir = (r"S:\il322\PhD Data\Lab 1 BX-60\2024-02-15_Bentham_Installation\2024-02-15_Bentham_Test_Plots\_")

#%% Plot spectra of each set wavelength

group = my_h5['OceanOpticsSpectrometer']


mpl.rcParams['lines.linewidth'] = 0.2
plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)
fig, (ax) = plt.subplots(1, 1, figsize=[16,10])
fig.suptitle('Bentham Monochromator Test', )
ax.set_xlabel('Wavelength (nm)')
ax.set_ylabel('Normalized Intensity (a.u.)')
offset = 0.0

my_cmap = plt.get_cmap('nipy_spectral')

for i, spectrum in enumerate(list(group.keys())):
     
    if 'Bentham' not in spectrum:
        continue
    
    name = spectrum[20:23]
    
    wln = int(name)
    color = my_cmap((wln-380)/580)
    spectrum = group[spectrum]
    background = np.array(spectrum.attrs['background'])
    spectrum = spt.Spectrum(spectrum)
    spectrum.y = spectrum.y - background
    
    # if spectrum.y.max() < 400:
    #     continue
    
    if wln < 380:
        continue
    
    spectrum.normalise()
    ax.plot(spectrum.x, spectrum.y_norm, color = color, label = name, linewidth = 2)
    print(name)
    
ax.legend(loc = 'upper center', fontsize = 'medium', ncol = 8, title = 'Set Wavelength (nm)')
ax.set_xlim(350,950)
ax.set_ylim(0, 1.3)
plt.tight_layout(pad = 0.5)
# plt.savefig(save_dir + 'Bentham_Spectra' + '.svg', format = 'svg')


#%% Plot peak position v set wavelength


group = my_h5['OceanOpticsSpectrometer']


mpl.rcParams['lines.linewidth'] = 0.2
plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)
fig, (ax) = plt.subplots(1, 1, figsize=[12,10])
fig.suptitle('Bentham Monochromator Test - Wavelength Selection', )
ax.set_xlabel('Set Wavelength (nm)')
ax.set_ylabel('Actual Peak Wavelength (nm)')
wlns = np.linspace(350, 1000, 50)
ax.plot(wlns, wlns, linestyle = '--', color = (0,0,0,0.5), zorder = 1, label = '$\lambda_{meas}=\lambda_{set}$')
ax.scatter(300, 300, color = 'purple', s = 100, zorder = 2, marker = 'o', label = 'Norm. Peak Intensity = 1')
ax.scatter(300, 300, color = 'purple', s = 20, zorder = 2, marker = 'o', label = 'Norm. Peak Intensity = 0.2')
offset = 0.0

my_cmap = plt.get_cmap('nipy_spectral')

for i, spectrum in enumerate(list(group.keys())):
     
    if 'Bentham' not in spectrum:
        continue
    
    name = spectrum[20:23]
    
    wln = int(name)
    color = my_cmap((wln-380)/580)
    spectrum = group[spectrum]
    background = np.array(spectrum.attrs['background'])
    spectrum = spt.Spectrum(spectrum)
    spectrum.y = spectrum.y - background
    peak_x = spectrum.x[spectrum.y.argmax()]
    
    
    if spectrum.y.max() < 400:
        continue
    
    if wln < 300:
        continue
    
    spectrum.normalise()
    spectrum.y_norm_smooth = spt.butter_lowpass_filt_filt(spectrum.y_norm, cutoff = 3000, fs = 40000, order = 2)
    maxima = spt.detect_maxima(spectrum.y_norm_smooth, lower_threshold=0.2)
    
    for maximum in maxima:
        size = 200 * spectrum.y_norm[maximum] 
        ax.scatter(wln, spectrum.x[maximum], color = color, s = size, zorder = 2, marker = 'o')
    
    print(name)
    
ax.legend(loc = 'upper left', fontsize = 'large')
ax.set_xlim(317.5,1032.5)
# ax.set_ylim(0, 1.3)
plt.tight_layout(pad = 0.5)
# plt.savefig(save_dir + 'Bentham_Peaks' + '.svg', format = 'svg')


#%% Plot FWHM & FWQM v set wavelength

# Calculating FWHM as as distance in wavelength between first and last point >= 0.5 norm intensity

group = my_h5['OceanOpticsSpectrometer']


mpl.rcParams['lines.linewidth'] = 0.2
plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)
fig, (ax) = plt.subplots(1, 1, figsize=[12,10])
fig.suptitle('Bentham Monochromator Test - FWHM', )
ax.set_xlabel('Set Wavelength (nm)')
ax.set_ylabel('FWHM - Primary Peak (nm)')
ax2 = ax.twinx()
ax2.set_ylabel('FWQM - Primary Peak (nm)', rotation = 270, labelpad = 30)
wlns = np.linspace(350, 1000, 50)
# ax.plot(wlns, wlns, linestyle = '--', color = (0,0,0,0.5), zorder = 1, label = '$\lambda_{meas}=\lambda_{set}$')
ax.scatter(300, 300, color = 'purple', s = 100, zorder = 2, marker = 'o', label = 'FWHM')
ax.scatter(300, 300, color = 'purple', s = 100, zorder = 2, marker = 'x', label = 'FWQM')
offset = 0.0

my_cmap = plt.get_cmap('nipy_spectral')

for i, spectrum in enumerate(list(group.keys())):
     
    if 'Bentham' not in spectrum:
        continue
    
    name = spectrum[20:23]
    
    wln = int(name)
    color = my_cmap((wln-380)/580)
    spectrum = group[spectrum]
    background = np.array(spectrum.attrs['background'])
    spectrum = spt.Spectrum(spectrum)
    spectrum.y = spectrum.y - background    
    
    if spectrum.y.max() < 400:
        continue
    
    if wln < 300 or wln > 970:
        continue
    
    if wln > 700:
        spectrum.truncate(700, None)
    spectrum.normalise()
    peak_wlns = spectrum.x[np.where(spectrum.y_norm >= 0.5)]
    fwhm = peak_wlns.max() - peak_wlns.min()
    peak_wlns = spectrum.x[np.where(spectrum.y_norm >= 0.25)]
    fwqm = peak_wlns.max() - peak_wlns.min()
    
    # spectrum.y_norm_smooth = spt.butter_lowpass_filt_filt(spectrum.y_norm, cutoff = 3000, fs = 40000, order = 2)
    # maxima = spt.detect_maxima(spectrum.y_norm_smooth, lower_threshold=0.2)        

    # for maximum in maxima:
    #     size = 200 * spectrum.y_norm[maximum] 
    ax.scatter(wln, fwhm, color = color, s = 200, zorder = 2, marker = 'o')
    ax2.scatter(wln, fwqm, color = color, s = 200, zorder = 2, marker = 'x')
    
    print(name)
    
ax.legend(loc = 'upper left', fontsize = 'large')
ax.set_xlim(317.5,1032.5)
ax.set_ylim(0, 55)
ax2.set_ylim(0, 55)
plt.tight_layout(pad = 0.5)
# plt.savefig(save_dir + 'Bentham_FWHM' + '.svg', format = 'svg')

#%% Detect maxima & smoothing test - plot smoothed and maxima for each spectrum individually


group = my_h5['OceanOpticsSpectrometer']


my_cmap = plt.get_cmap('nipy_spectral')

for i, spectrum in enumerate(list(group.keys())):
     
    if 'Bentham' not in spectrum:
        continue
    
    name = spectrum[20:23]
    
    wln = int(name)
    color = my_cmap((wln-380)/580)
    spectrum = group[spectrum]
    background = np.array(spectrum.attrs['background'])
    spectrum = spt.Spectrum(spectrum)
    spectrum.y = spectrum.y - background
    
    if spectrum.y.max() < 400:
        continue
    
    if wln < 380:
        continue
    
    # if abs(wln-peak_x) > 50:
    #     marker = 'x'
    #     spectrum.truncate(800, None)
    #     peak_x2 = spectrum.x[spectrum.y.argmax()]
    #     ax.scatter(wln, peak_x2, color = color, s = 200, zorder = 2, marker = 'o')
    # else:
    #     marker = 'o'
    
    mpl.rcParams['lines.linewidth'] = 0.2
    plt.rc('font', size=18, family='sans-serif')
    plt.rc('lines', linewidth=3)
    fig, (ax) = plt.subplots(1, 1, figsize=[12,10])
    fig.suptitle('Bentham Monochromator Test - Wavelength Selection', )
    ax.set_xlabel('Set Wavelength (nm)')
    ax.set_ylabel('Actual Peak Wavelength (nm)')
    wlns = np.linspace(350, 1000, 50)
    # ax.plot(wlns, wlns, linestyle = '--', color = (0,0,0,0.5), zorder = 1)
    offset = 0.0
    
    spectrum.normalise()
    spectrum.y_norm = spt.butter_lowpass_filt_filt(spectrum.y_norm, cutoff = 3000, fs = 40000, order = 2)
    # ax.scatter(wln, peak_x, color = color, s = 200, zorder = 2, marker = marker)
    maxima = spt.detect_maxima(spectrum.y_norm, lower_threshold=0.1)
    
    # if wln > 700:
        # spectrum.truncate(700, None)
        # spectrum.normalise()
    # peak_wlns = spectrum.x[np.where(spectrum.y_norm >= 0.5)]
    # fwhm = peak_wlns.max() - peak_wlns.min()
    print(name)
    print(maxima)
    
    ax.plot(spectrum.x, spectrum.y_norm, color = color)
    ax.scatter(spectrum.x[maxima], spectrum.y_norm[maxima],s = 100, color = color)
    # ax.vlines(peak_wlns.max(), ymin = 0, ymax = 1, color = (0,0,0,0.5))
    ax.set_title(wln)
    
# ax.legend(loc = 'upper center', fontsize = 'medium', ncol = 8, title = 'Set Wavelength (nm)')
# ax.set_xlim(350,950)
# ax.set_ylim(0, 1.3)
plt.tight_layout(pad = 0.5)
# plt.savefig(save_dir + 'Bentham_Spectra' + '.svg', format = 'svg')


#%% Plot power v wavelength

group = my_h5['ThorlabsPowermeter']


mpl.rcParams['lines.linewidth'] = 0.2
plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)
fig, (ax) = plt.subplots(1, 1, figsize=[14,8])
fig.suptitle('Bentham Monochromator Power', )
ax.set_xlabel('Set Wavelength (nm)')
ax.set_ylabel('Power on Sample ($\mu$W)')

my_cmap = plt.get_cmap('nipy_spectral')

for i, spectrum in enumerate(list(group.keys())):
     
    if 'Bentham' not in spectrum:
        continue
    
    name = spectrum[23:26]
    
    wln = int(name)
    color = my_cmap((wln-380)/580)
    spectrum = group[spectrum]
    power = np.float32(spectrum) * 1000
    
    if wln < 200:
        continue
    
    ax.scatter(wln, power, color = color, s = 200)
    print(name)
    
# ax.legend(loc = 'upper center', fontsize = 'medium', ncol = 8, title = 'Set Wavelength (nm)')
# ax.set_xlim(350,950)
# ax.set_ylim(0, 1.3)
plt.tight_layout(pad = 0.5)
# plt.savefig(save_dir + 'Bentham_Power' + '.svg', format = 'svg')





