# -*- coding: utf-8 -*-
"""
Created on Sat Jun 10 10:38:55 2023

@author: il322

Plotter for Renishaw M-TAPP Solution Aggregate Concentration series data

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

H2_h5 = h5py.File(r"C:\Users\il322\Desktop\Offline Data\2023-03-11_M-TAPP-SMe_60nm Solution Aggregates\2023-03-11_H2-TAPP-SMe_60nm Solution Aggregates Raman Data.h5")
Co_h5 = h5py.File(r"C:\Users\il322\Desktop\Offline Data\2023-03-11_M-TAPP-SMe_60nm Solution Aggregates\2023-02-23_Co-TAPP-SMe_60nm Solution Aggregates Raman Data.h5")
Ni_h5 = h5py.File(r"C:\Users\il322\Desktop\Offline Data\2023-03-11_M-TAPP-SMe_60nm Solution Aggregates\2023-03-11_Ni-TAPP-SMe_60nm Solution Aggregates Raman Data.h5")
Zn_h5 = h5py.File(r"C:\Users\il322\Desktop\Offline Data\2023-03-11_M-TAPP-SMe_60nm Solution Aggregates\2023-03-11_Zn-TAPP-SMe_60nm Solution Aggregates Raman Data.h5")


#%% Renishaw doesn't need spec or efficiency calibration


#%% Plotting

# Concentration in uM

conc_dict = {0 : 19.9809705,
             1 : 9.990485252,
             2 : 3.996194101,
             3 : 1.99809705,
             4 : 0.999048525,
             5 : 0.39961941,
             6 : 0.199809705,
             7 : 0.099904853,
             8 : 0.039961941,
             9 : 0.019980971,
             10 : 0.009990485,
             11 : 0.003996194,
             12 : 0.001998097,
             13 : 0.000999049}

def concentration_series(my_h5, wavelength = 633, molecule_name = 'M-TAPP-SMe', conc_range = [0, 201], offset = 100):
    
    '''
    Quick function to plot & process concentration series
    '''


    # Get spectra to plot

    ## Get list of names & sort
    spectra = []
    for spectrum in my_h5['All Raw'].keys():
        if str(wavelength) in spectrum:
            spectra.append(spectrum)        
    spectra_sorted = natsort.natsorted(spectra)
    
    ## Get list of data objects
    spectra = []
    for spectrum in spectra_sorted:
        spectra.append(my_h5['All Raw'][spectrum])

    # Plotting
    
    fig, ax = plt.subplots(1, 1, figsize=[8,6])
    ax.set_ylabel('Intensity (cts/mW/s)')
    ax.set_xlabel('Raman shifts (cm$^{-1})$')
    fig.suptitle(str(wavelength) + 'nm SERS Concentration Series\n' + molecule_name + ' 60nm Solution Aggregates', fontsize='medium')
    norm = mpl.colors.LogNorm(vmin = 10e-4, vmax = max(conc_dict.values()))
    cmap = mpl.cm.ScalarMappable(norm = norm, cmap = mpl.cm.jet)
    #cmap.set_array([])
    cbar = plt.colorbar(cmap, location = 'right', pad = 0)
    cbar.ax.tick_params(labelsize='small')
    cbar.set_label('Concentration ($\mu$M)', rotation=270, labelpad = 20, fontsize='medium')

    ## Loop over spectra & plot
    spectra_processed = []
    for i, spectrum in enumerate(spectra):
        conc = np.round(conc_dict[i], 3)
        spectrum = SERS.SERS_Spectrum(spectrum)
        spectrum.y = spectrum.y / (spectrum.dset.attrs['Laser Power (uW)'] * spectrum.dset.attrs['Accumulations'] /1000)
        color = cmap.to_rgba(conc_dict[i])
        spectrum.y_baselined = spectrum.y - spt.baseline_als(spectrum.y, lam = 1e3, p = 1e-4)
        spectrum.y_smooth = spt.butter_lowpass_filt_filt(spectrum.y_baselined)
        if conc <= conc_range[1] and conc >= conc_range[0]:
            ax.plot(spectrum.x, spectrum.y_baselined + (len(spectra) - i) * offset, color = color)
        ax.set_xlim(600,1750)
        spectra_processed.append(spectrum)
    
    ## Save
    #save_name = molecule_name + ' ' + str(wavelength) + 'nm Concentration Series.svg'
#    plt.savefig(save_name, format = 'svg')
    
    # Return processed spectra
    
    return spectra_processed


H2_633_spectra = concentration_series(H2_h5, wavelength = 633, molecule_name = 'H2-TAPP-SMe', conc_range = [0, 3], offset = 4)
Co_633_spectra = concentration_series(Co_h5, wavelength = 633, molecule_name = 'Co-TAPP-SMe', conc_range = [0, 20], offset = 60)
Ni_633_spectra = concentration_series(Ni_h5, wavelength = 633, molecule_name = 'Ni-TAPP-SMe', conc_range = [0, 20], offset = 15)
Zn_633_spectra = concentration_series(Zn_h5, wavelength = 633, molecule_name = 'Zn-TAPP-SMe', conc_range = [0, 2], offset = 20)
    
H2_785_spectra = concentration_series(H2_h5, wavelength = 785, molecule_name = 'H2-TAPP-SMe', conc_range = [0, 20], offset = 4)
Co_785_spectra = concentration_series(Co_h5, wavelength = 785, molecule_name = 'Co-TAPP-SMe', conc_range = [0, 20], offset = 60)
Ni_785_spectra = concentration_series(Ni_h5, wavelength = 785, molecule_name = 'Ni-TAPP-SMe', conc_range = [0, 20], offset = 15)
Zn_785_spectra = concentration_series(Zn_h5, wavelength = 785, molecule_name = 'Zn-TAPP-SMe', conc_range = [0, 20], offset = 20)

 
#%%


conc_range = [0, 3]

def get_concentration_series_area(spectra_list, conc_range):
    '''
    Quick function to get max peak area of concentration series
    '''
    
    areas = []
    
    for i, spectrum in enumerate(spectra_list):
        conc = conc_dict[i]
        spectrum.y_smooth = spt.butter_lowpass_filt_filt(spectrum.y_baselined, cutoff = 1200, fs = 12000)
        if conc >= conc_range[0] and conc <= conc_range[1]:
            peaks = spt.approx_peak_gausses(spectrum.x, spectrum.y_smooth, smooth_first = False, plot = False, threshold = 0.97, height_frac = 0.13)
            peak = max(peaks)
            width = peak[2]
            if peak[2] > 200:
                width = 80
            area = peak[0] *(np.pi * 2)**0.5 * width
    
    
        else:
            area = 0
            
        areas.append(area)
        
    return(areas)


#%% 633 max peak intensity v concentration
   
my_cmap = plt.get_cmap('Set1')

H2_633_areas = get_concentration_series_area(H2_633_spectra, [0,3]) 
Co_633_areas = get_concentration_series_area(Co_633_spectra, [0,20])
Ni_633_areas = get_concentration_series_area(Ni_633_spectra, [0,20])
Zn_633_areas = get_concentration_series_area(Zn_633_spectra, [0,2])

fig, ax = plt.subplots(1,1, figsize = [10,6])
ax.plot(conc_dict.values(), H2_633_areas/max(H2_633_areas), '-o', linewidth = 2, color = my_cmap(3), label = 'H2-TAPP-SMe', zorder = 4)
ax.plot(conc_dict.values(), Co_633_areas/max(Co_633_areas), '-o', linewidth = 2, color = my_cmap(1), label = 'Co-TAPP-SMe', zorder = 2)
ax.plot(conc_dict.values(), Ni_633_areas/max(Ni_633_areas), '-o', linewidth = 2, color = my_cmap(6), label = 'Ni-TAPP-SMe', zorder = 3)
ax.plot(conc_dict.values(), Zn_633_areas/max(Zn_633_areas), '-o', linewidth = 2, color = my_cmap(2), label = 'Zn-TAPP-SMe', zorder = 1)
ax.set_xlabel('Concentration ($\mu$M)')
ax.set_ylabel('Normalized Max SERS Peak Intensity (a.u.)')
ax.set_xscale('log')
ax.legend()
fig.suptitle('633nm SERS Intensity v. 60nm Solution Aggregate Concentration', fontsize = 'medium')

#plt.savefig('633nm Intensity v. Concentration.svg', format = 'svg')

#%% 785 max peak intensity v concentration
   
my_cmap = plt.get_cmap('Set1')

H2_785_areas = get_concentration_series_area(H2_785_spectra, [0,20]) 
Co_785_areas = get_concentration_series_area(Co_785_spectra, [0,20])
Ni_785_areas = get_concentration_series_area(Ni_785_spectra, [0,20])
Zn_785_areas = get_concentration_series_area(Zn_785_spectra, [0,20])

fig, ax = plt.subplots(1,1, figsize = [10,6])
ax.plot(conc_dict.values(), H2_785_areas/max(H2_785_areas), '-o', linewidth = 2, color = my_cmap(3), label = 'H2-TAPP-SMe', zorder = 4)
ax.plot(conc_dict.values(), Co_785_areas/max(Co_785_areas), '-o', linewidth = 2, color = my_cmap(1), label = 'Co-TAPP-SMe', zorder = 2)
ax.plot(conc_dict.values(), Ni_785_areas/max(Ni_785_areas), '-o', linewidth = 2, color = my_cmap(6), label = 'Ni-TAPP-SMe', zorder = 3)
ax.plot(conc_dict.values(), Zn_785_areas/max(Zn_785_areas), '-o', linewidth = 2, color = my_cmap(2), label = 'Zn-TAPP-SMe', zorder = 1)
ax.set_xlabel('Concentration ($\mu$M)')
ax.set_ylabel('Normalized Max SERS Peak Intensity (a.u.)')
ax.set_xscale('log')
ax.legend()
fig.suptitle('785nm SERS Intensity v. 60nm Solution Aggregate Concentration', fontsize = 'medium')

#plt.savefig('785nm Intensity v. Concentration.svg', format = 'svg')

#%% Plot 633 max SERS spectra 

fig, ax = plt.subplots(1,1, figsize = [10,6])
ax.plot(H2_633_spectra[7].x, H2_633_spectra[7].y_baselined, linewidth = 3, color = my_cmap(3), label = 'H2-TAPP-SMe', zorder = 4)
ax.plot(Co_633_spectra[7].x, Co_633_spectra[7].y_baselined, linewidth = 3, color = my_cmap(1), label = 'Co-TAPP-SMe', zorder = 2)
ax.plot(Ni_633_spectra[9].x, Ni_633_spectra[9].y_baselined, linewidth = 3, color = my_cmap(6), label = 'Ni-TAPP-SMe', zorder = 3)
ax.plot(Zn_633_spectra[7].x, Zn_633_spectra[7].y_baselined, linewidth = 3, color = my_cmap(2), label = 'Zn-TAPP-SMe', zorder = 1)
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('SERS Intensity (a.u.)')
ax.set_xlim(500, 2000)
ax.legend()
fig.suptitle('633nm SERS M-TAPP-SMe 60nm Solution Aggregates', fontsize = 'medium')

#plt.savefig('633nm SERS M-TAPP-SMe Solution Aggregates.svg', format = 'svg')


#%% Plot 633 max SERS spectra normalized

fig, ax = plt.subplots(1,1, figsize = [10,6])
ax.plot(H2_633_spectra[7].x, H2_633_spectra[7].y_baselined/max(H2_633_spectra[7].y_baselined), linewidth = 3, color = my_cmap(3), label = 'H2-TAPP-SMe', zorder = 4)
ax.plot(Co_633_spectra[7].x, Co_633_spectra[7].y_baselined/max(Co_633_spectra[7].y_baselined)+ 0.4, linewidth = 3, color = my_cmap(1), label = 'Co-TAPP-SMe', zorder = 2)
ax.plot(Ni_633_spectra[9].x, Ni_633_spectra[9].y_baselined/max(Ni_633_spectra[9].y_baselined)+ 0.8, linewidth = 3, color = my_cmap(6), label = 'Ni-TAPP-SMe', zorder = 3)
ax.plot(Zn_633_spectra[7].x, Zn_633_spectra[7].y_baselined/max(Zn_633_spectra[7].y_baselined)+ 1.2, linewidth = 3, color = my_cmap(2), label = 'Zn-TAPP-SMe', zorder = 1)
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('Normalized SERS Intensity (a.u.)')
ax.set_xlim(500, 2000)
ax.legend()
fig.suptitle('633nm SERS M-TAPP-SMe 60nm Solution Aggregates', fontsize = 'medium')

#plt.savefig('Normalized 633nm SERS M-TAPP-SMe Solution Aggregates.svg', format = 'svg')


#%% Plot 785 max SERS spectra 

fig, ax = plt.subplots(1,1, figsize = [10,6])
ax.plot(H2_785_spectra[6].x, H2_785_spectra[6].y_baselined, linewidth = 3, color = my_cmap(3), label = 'H2-TAPP-SMe', zorder = 4)
ax.plot(Co_785_spectra[7].x, Co_785_spectra[7].y_baselined, linewidth = 3, color = my_cmap(1), label = 'Co-TAPP-SMe', zorder = 2)
ax.plot(Ni_785_spectra[8].x, Ni_785_spectra[8].y_baselined, linewidth = 3, color = my_cmap(6), label = 'Ni-TAPP-SMe', zorder = 3)
ax.plot(Zn_785_spectra[7].x, Zn_785_spectra[7].y_baselined, linewidth = 3, color = my_cmap(2), label = 'Zn-TAPP-SMe', zorder = 1)
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('SERS Intensity (a.u.)')
ax.set_xlim(600, 1750)
ax.legend()
fig.suptitle('785nm SERS M-TAPP-SMe 60nm Solution Aggregates', fontsize = 'medium')

#plt.savefig('785nm SERS M-TAPP-SMe Solution Aggregates.svg', format = 'svg')


#%% Plot 785 max SERS spectra normalized

fig, ax = plt.subplots(1,1, figsize = [10,6])
ax.plot(H2_785_spectra[6].x, H2_785_spectra[6].y_baselined/max(H2_785_spectra[6].y_baselined), linewidth = 3, color = my_cmap(3), label = 'H2-TAPP-SMe', zorder = 4)
ax.plot(Co_785_spectra[7].x, Co_785_spectra[7].y_baselined/max(Co_785_spectra[7].y_baselined)+ 0.4, linewidth = 3, color = my_cmap(1), label = 'Co-TAPP-SMe', zorder = 2)
ax.plot(Ni_785_spectra[8].x, Ni_785_spectra[8].y_baselined/max(Ni_785_spectra[8].y_baselined)+ 0.8, linewidth = 3, color = my_cmap(6), label = 'Ni-TAPP-SMe', zorder = 3)
ax.plot(Zn_785_spectra[7].x, Zn_785_spectra[7].y_baselined/max(Zn_785_spectra[7].y_baselined)+ 1.2, linewidth = 3, color = my_cmap(2), label = 'Zn-TAPP-SMe', zorder = 1)
ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
ax.set_ylabel('Normalized SERS Intensity (a.u.)')
ax.set_xlim(600, 1750)
ax.legend()
fig.suptitle('785nm SERS M-TAPP-SMe 60nm Solution Aggregates', fontsize = 'medium')


#plt.savefig('Normalized 785nm SERS M-TAPP-SMe Solution Aggregates.svg', format = 'svg')


#%% Getting UV Vis data

my_h5 = h5py.File(r"C:\Users\il322\Desktop\Offline Data\car72 M-TAPP UV-Vis\2021-04-05 All MTPP UV-Vis PL.h5")
my_csv = r"C:\Users\il322\Desktop\Offline Data\car72 M-TAPP UV-Vis\Co-TAPP Abs_processed.csv"

Co = np.genfromtxt(my_csv, delimiter=',')
Co = Co.transpose()
Co_abs = spt.Spectrum(Co[0], Co[1])
Co_abs.x = np.round(Co_abs.x, 0)

H2 = my_h5['H2-MTPP MeOH MeCN UV-Vis']
Ni = my_h5['Ni-MTPP MeOH MeCN UV-Vis']
Zn = my_h5['Zn-MTPP MeOH MeCN UV-Vis']

H2_abs = spt.Spectrum(x = H2.attrs['wavelengths'], y = H2.attrs['yRaw'])
Ni_abs = spt.Spectrum(x = Ni.attrs['wavelengths'], y = Ni.attrs['yRaw'])
Zn_abs = spt.Spectrum(x = Zn.attrs['wavelengths'], y = Zn.attrs['yRaw'])


#%% Plotting 633nm Max SERS Peak Area v. Absorption

fig, ax = plt.subplots(1,1, figsize = [10,6])

ax.scatter(H2_abs.y[np.where(H2_abs.x == 633)], max(H2_633_areas), color = my_cmap(3), label = 'H2-TAPP-SMe', zorder = 1)
ax.scatter(Co_abs.y[np.where(Co_abs.x == 633)], max(Co_633_areas), color = my_cmap(1), label = 'Co-TAPP-SMe', zorder = 1)
ax.scatter(Ni_abs.y[np.where(Ni_abs.x == 633)], max(Ni_633_areas), color = my_cmap(6), label = 'Ni-TAPP-SMe', zorder = 1)
ax.scatter(Zn_abs.y[np.where(Zn_abs.x == 633)], max(Zn_633_areas), color = my_cmap(2), label = 'Zn-TAPP-SMe', zorder = 1)

deg = 1
M_abs = [H2_abs.y[np.where(H2_abs.x == 633)], Co_abs.y[np.where(Co_abs.x == 633)], Ni_abs.y[np.where(Ni_abs.x == 633)], Zn_abs.y[np.where(Zn_abs.x == 633)]]
for i in range(0, len(M_abs)):
    M_abs[i] = float(M_abs[i])
M_areas = [max(H2_633_areas), max(Co_633_areas), max(Ni_633_areas), max(Zn_633_areas)]

a = np.polyfit((M_abs), np.log(M_areas), deg = 1)
b = np.polyfit((M_abs), (M_areas), deg = 1)
c = np.polyfit((M_abs), (M_areas), deg = 2)
abs_x = np.linspace(0, 0.05, 100)
exp_fit = exp(a[1]) * exp(a[0] * abs_x)
lin_fit = b[1] + b[0] * abs_x
quad_fit = c[2] + c[1] * abs_x + c[0] * abs_x**2

#ax.plot(abs_x, exp_fit, linestyle = 'dashed', color = 'grey', zorder = 0, label = 'exp')
#ax.plot(abs_x, lin_fit, linestyle = 'dashed', color = 'black', zorder = 0, label = 'lin')
ax.plot(abs_x, lin_fit, linestyle = 'dashed', color = 'grey', zorder = 0)

ax.set_xlabel('Absorbance at 633nm')
ax.set_ylabel('Max Peak SERS Intensity (a.u.)')
ax.legend()
ax.set_title('M-TAPP-SMe 633nm SERS Intensity v. Absorbance', fontsize = 'medium', pad = 20)
ax.ticklabel_format(axis = 'y', style = 'sci', scilimits = (0,0))
#plt.tight_layout()
#plt.savefig('Test 633nm Max SERS v. Absorbance.svg', format = 'svg')

#%% Plotting 785m, Max SERS Peak Area v. Absorption

fig, ax = plt.subplots(1,1, figsize = [8,6])

ax.scatter(H2_abs.y[np.where(H2_abs.x == 785)], max(H2_785_areas), color = my_cmap(3), label = 'H2-TAPP-SMe')
ax.scatter(Co_abs.y[np.where(Co_abs.x == 785)], max(Co_785_areas), color = my_cmap(1), label = 'Co-TAPP-SMe')
ax.scatter(Ni_abs.y[np.where(Ni_abs.x == 785)], max(Ni_785_areas), color = my_cmap(6), label = 'Ni-TAPP-SMe')
ax.scatter(Zn_abs.y[np.where(Zn_abs.x == 785)], max(Zn_785_areas), color = my_cmap(2), label = 'Zn-TAPP-SMe')

deg = 1
M_abs = [H2_abs.y[np.where(H2_abs.x == 785)], Co_abs.y[np.where(Co_abs.x == 785)], Ni_abs.y[np.where(Ni_abs.x == 785)], Zn_abs.y[np.where(Zn_abs.x == 785)]]
for i in range(0, len(M_abs)):
    M_abs[i] = float(M_abs[i])
M_areas = [max(H2_785_areas), max(Co_785_areas), max(Ni_785_areas), max(Zn_785_areas)]

a = np.polyfit((M_abs), np.log(M_areas), deg = 1)
b = np.polyfit((M_abs), (M_areas), deg = 1)
c = np.polyfit((M_abs), (M_areas), deg = 2)
abs_x = np.linspace(-0.002, 0.002, 100)
exp_fit = exp(a[1]) * exp(a[0] * abs_x)
lin_fit = b[1] + b[0] * abs_x
quad_fit = c[2] + c[1] * abs_x + c[0] * abs_x**2

#ax.plot(abs_x, exp_fit, linestyle = 'dashed', color = 'grey', zorder = 0, label = 'exp')
#ax.plot(abs_x, lin_fit, linestyle = 'dashed', color = 'black', zorder = 0, label = 'lin')
#ax.plot(abs_x, lin_fit, linestyle = 'dashed', color = 'grey', zorder = 0)


ax.set_xlabel('Absorbance at 785nm')
ax.set_ylabel('Max Peak SERS Intensity (a.u.)')
ax.legend()
fig.suptitle('M-TAPP-SMe 785nm SERS Intensity v. Absorbance', fontsize = 'medium')

#plt.savefig('785nm Max SERS v. Absorbance.svg', format = 'svg')
