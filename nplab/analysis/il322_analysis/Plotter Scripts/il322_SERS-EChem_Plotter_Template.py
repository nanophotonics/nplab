# -*- coding: utf-8 -*-
"""
Created on Wed Apr 26 18:32:45 2023

@author: il322

Plotter for e-chem SERS timescans from 
"S:\il322\PhD Data\M-TAPP-SMe\2023-03-17_M-TAPP-SMe_60nm-MLAgg\2023-04-20_Lab8_EChem_Co-TAPP-SMe_60nm_MLAgg.h5"
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
from nplab.analysis.general_spec_tools import npom_sers_tools as nst
from nplab.analysis.general_spec_tools import agg_sers_tools as ast
from nplab.analysis.general_spec_tools import npom_df_pl_tools as df
from nplab.analysis.SERS_Fitting import Auto_Fit_Raman as afr
from nplab.analysis.il322_analysis import il322_calibrate_spectrum as cal
from nplab.analysis.il322_analysis import il322_SERS_tools as SERS

#%% Load h5
h5_MLAgg = h5py.File(r"C:\Users\il322\Desktop\Offline Data\2023-03-17_M-TAPP-SMe_60nm-MLAgg\2023-04-20_Lab8_EChem_Co-TAPP-SMe_60nm_MLAgg.h5")
truncate_range = [185,1350]

#%% Get wn_cal

bpt_ref_633nm = h5_MLAgg['ref_meas']['BPT_ref_633nm_5s']
bpt_ref_633nm = SERS.SERS_Spectrum(bpt_ref_633nm)

## Coarse wl shift because Lab 8 is crazy
bpt_ref_633nm.x_raw = bpt_ref_633nm.x_raw - 63
bpt_ref_633nm.x = bpt_ref_633nm.x - 63

## Convert to wn
bpt_ref_633nm.x = spt.wl_to_wn(bpt_ref_633nm.x, 632.8)

## Truncate out notch (use this truncation for all spectra!)
bpt_ref_633nm.truncate(truncate_range[0], truncate_range[1])

## Have to adjust ref_wn because peak fitting is not yet robust
ref_wn_633nm = [ 189.96242575,  256.60661727,  304.85947153,  416.21397689,  518.96110313,
  635.5749669,  688.10709404,  760.32610816,  818.56620529,  951.50031667, 1021.03800555]

## Get calibrated wavenumbers
wn_cal_633 = cal.run_spectral_calibration(bpt_ref_633nm, ref_wn = ref_wn_633nm, deg=2)


#%% Get R_setup

white_ref_633nm = h5_MLAgg['ref_meas']['white_scatt_633nm_0.02sx10scans']
white_ref_633nm = SERS.SERS_Spectrum(white_ref_633nm.attrs['wavelengths'], white_ref_633nm[5], title = 'White Scatterer')

## Coarse wl shift because Lab 8 is crazy
white_ref_633nm.x_raw = white_ref_633nm.x_raw - 63
white_ref_633nm.x = white_ref_633nm.x - 63

## Convert to wn
white_ref_633nm.x = spt.wl_to_wn(white_ref_633nm.x, 632.8)

## Truncate out notch (same range as BPT ref above)
white_ref_633nm.truncate(truncate_range[0], truncate_range[1])

## Convert back to wl for efficiency calibration
white_ref_633nm.x = spt.wn_to_wl(white_ref_633nm.x, 632.8)
white_ref_633nm.plot(title=True)

## Get white background counts in notch
notch_range = [0,120]
notch = SERS.SERS_Spectrum(white_ref_633nm.x_raw[notch_range[0]:notch_range[1]], white_ref_633nm.y_raw[notch_range[0]:notch_range[1]], name = 'White Scatterer Notch') 
notch.plot(title=True)
notch_cts = notch.y.mean()

## Calculate R_setup
R_setup_633nm = cal.white_scatter_calibration(wl = white_ref_633nm.x, white_scatter = white_ref_633nm.y, white_bkg = notch_cts, plot=True)

## Test R_setup with BPT reference
notch_range = [75,120]
notch = SERS.SERS_Spectrum(bpt_ref_633nm.x_raw[notch_range[0]:notch_range[1]], bpt_ref_633nm.y_raw[notch_range[0]:notch_range[1]], name = 'BPT Ref Notch') 
notch.plot(title=True)
notch_cts = notch.y.mean()
plt.plot(bpt_ref_633nm.x, bpt_ref_633nm.y-notch_cts, color = (0.8,0.1,0.1,0.7), label = 'Raw spectrum')
plt.plot(bpt_ref_633nm.x, (bpt_ref_633nm.y-notch_cts)/R_setup_633nm, color = (0,0.6,0.2,0.5), label = 'Efficiency-corrected')
plt.legend(fontsize='x-small')
plt.show()
        
        
#%%

timescan = SERS.SERS_Timescan(h5_MLAgg['Co-TAPP-SMe_60nm_MLAgg_on_Au_1']['633nm_No-e-chem_0.1sx100scans'])
timescan.x_raw = timescan.x_raw - 63
timescan.x = timescan.x - 63
timescan.x = spt.wl_to_wn(timescan.x, 632.8)
timescan.truncate(truncate_range[0], truncate_range[1])
timescan.x = wn_cal_633

laser_power = timescan.dset.attrs['power']

timescan.calibrate_intensity(R_setup = R_setup_633nm, dark_counts = notch_cts, laser_power = laser_power)

ca_data = np.loadtxt(r'C:\Users\il322\Desktop\Offline Data\2023-03-17_M-TAPP-SMe_60nm-MLAgg\2023-03-17_Co-TAPP-SMe_60nm_MLAgg_on_SAM_on_Au\ca_-1.0.txt',
                      skiprows=1)

timescan.echem_data = ca_data
timescan.echem_mode = 'CA'

timescan.plot_timescan(t_min = 0, t_max = 9, t_offset= 0, v_min = 30000, v_max = 350000, plot_echem = False, plot_type='cmap', avg_chunks = None)
save_name = timescan.dset.attrs['sample'] + '.svg'
#plt.savefig(save_name, format = 'svg')
#%%

cv_data = np.loadtxt(r'C:\Users\il322\Desktop\Offline Data\2023-03-17_M-TAPP-SMe_60nm-MLAgg\2023-03-17_Co-TAPP-SMe_60nm_MLAgg_on_SAM_on_Au\cv_-1.0.txt_1',
                     skiprows=1)
cv_data2 = np.loadtxt(r'C:\Users\il322\Desktop\Offline Data\2023-03-17_M-TAPP-SMe_60nm-MLAgg\2023-03-17_Co-TAPP-SMe_60nm_MLAgg_on_SAM_on_Au\cv_-1.0.txt_2',
                      skiprows=1)
cv_data2[:,0] = cv_data2[:,0] + float(cv_data2[len(cv_data)-1,0])
cv_data = np.concatenate([cv_data, cv_data2])

timescan = SERS.SERS_Timescan(h5_MLAgg['Co-TAPP-SMe_60nm_MLAgg_on_Au_1']['633nm_CV-0to-1.0Vx2scans_0.1sx4000scans'], name = 'MLAgg')
timescan.x_raw = timescan.x_raw - 63
timescan.x = timescan.x - 63
timescan.x = spt.wl_to_wn(timescan.x, 632.8)
timescan.truncate(truncate_range[0], truncate_range[1])
timescan.x = wn_cal_633

laser_power = timescan.dset.attrs['power']

timescan.calibrate_intensity(R_setup = R_setup_633nm, dark_counts = notch_cts, laser_power = laser_power)


timescan.echem_data = cv_data
timescan.echem_mode = 'CV'

timescan.plot_timescan(t_min = 0, t_max = 200, plot_echem = True)

#%%
timescan = SERS.SERS_Timescan(h5_MLAgg['Co-TAPP-SMe_60nm_MLAgg_on_Au_1']['633nm_CV-0to-1.0Vx2scans_0.1sx4000scans'], name = 'MLAgg')
timescan.x_raw = timescan.x_raw - 63
timescan.x = timescan.x - 63
timescan.x = spt.wl_to_wn(timescan.x, 632.8)
timescan.truncate(truncate_range[0], truncate_range[1])
timescan.x = wn_cal_633

laser_power = timescan.dset.attrs['power']

timescan.calibrate_intensity(R_setup = R_setup_633nm, dark_counts = notch_cts, laser_power = laser_power)
timescan.normalise(norm_range = (0,1), norm_individual=False, t_min = None, t_max = None)
timescan.plot_timescan(plot_norm = False, plot_type = 'cmap', stack_offset=1000, t_min = 0, t_max = None)
