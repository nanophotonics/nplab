# -*- coding: utf-8 -*-
"""
Created on Fri Apr 14 01:25:21 2023

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
from nplab.analysis.general_spec_tools import npom_sers_tools as nst
from nplab.analysis.general_spec_tools import agg_sers_tools as ast
from nplab.analysis.general_spec_tools import npom_df_pl_tools as df
from nplab.analysis.SERS_Fitting import Auto_Fit_Raman as afr
#from nplab.analysis.il322_NPoM_DF_Powerseries_Plotter import normalise 
#from nplab.analysis.SERS_Fitting import Iterative_Raman_Fitting as irf

#%%

wn_cal_633nm = np.loadtxt(r'S:\il322\PhD Data\M-TAPP-SMe\2023-03-17_M-TAPP-SMe_60nm-NPoM\2022-03-25_M-TAPP-SMe_60nm_NPoM Processed Data\2023-03-25_Calibrated_Wavenumbers_633nm.txt')
laser_powers = np.loadtxt(r'S:\il322\PhD Data\M-TAPP-SMe\2023-03-17_M-TAPP-SMe_60nm-NPoM\2022-03-25_M-TAPP-SMe_60nm_NPoM Processed Data\2023-03-25_Laser_Powers_633nm.txt')
R_setup_633nm = np.loadtxt(r'S:\il322\PhD Data\M-TAPP-SMe\2023-03-17_M-TAPP-SMe_60nm-NPoM\2022-03-25_M-TAPP-SMe_60nm_NPoM Processed Data\2023-03-25_R_Setup_633nm.txt')
H2_nanocavity = np.loadtxt(r'S:\il322\PhD Data\M-TAPP-SMe\2023-03-17_M-TAPP-SMe_60nm-NPoM\2022-03-25_M-TAPP-SMe_60nm_NPoM Processed Data\2023-03-25_Processed_H2-TAPP-SMe-60nm_NPoM_Average-Nanocavity-Timescan_633nm.txt', delimiter = ',')
Co_nanocavity = np.loadtxt(r'S:\il322\PhD Data\M-TAPP-SMe\2023-03-17_M-TAPP-SMe_60nm-NPoM\2022-03-25_M-TAPP-SMe_60nm_NPoM Processed Data\2023-03-25_Processed_Co-TAPP-SMe-60nm_NPoM_Average-Nanocavity-Timescan_633nm.txt', delimiter = ',')
Ni_nanocavity = np.loadtxt(r'S:\il322\PhD Data\M-TAPP-SMe\2023-03-17_M-TAPP-SMe_60nm-NPoM\2022-03-25_M-TAPP-SMe_60nm_NPoM Processed Data\2023-03-25_Processed_Ni-TAPP-SMe-60nm_NPoM_Average-Nanocavity-Timescan_633nm.txt', delimiter = ',')
Zn_nanocavity = np.loadtxt(r'S:\il322\PhD Data\M-TAPP-SMe\2023-03-17_M-TAPP-SMe_60nm-NPoM\2022-03-25_M-TAPP-SMe_60nm_NPoM Processed Data\2023-03-25_Processed_Zn-TAPP-SMe-60nm_NPoM_Average-Nanocavity-Timescan_633nm.txt', delimiter = ',')


#%%            

fig,ax=plt.subplots(4,1,figsize=[7,16], dpi=1000) 
ax1 = ax[0]
ax2 = ax[1]
ax3 = ax[2]
ax4 = ax[3]
fig.suptitle('633nm SERS Powerseries - Average Nanocavity', fontsize='x-large',x=0.45, y=0.92)#, labelpad=0)


ax1.set_title('H2-TAPP-SMe 60nm NPoM - 633nm SERS Powerseries', color='black')
ax1.set_ylabel('SERS Intensity (cts/mW/s)')
#ax1.set_xlabel('Raman shifts (cm$^{-1}$)')
norm = mpl.colors.LogNorm(vmin=0.003, vmax=laser_powers.max())
cmap = mpl.cm.ScalarMappable(norm=norm, cmap=mpl.cm.Greys)
cmap.set_array([])
for i in range(5,len(H2_nanocavity)):
    ax1.plot(wn_cal_633nm, H2_nanocavity[i]+((i-7)*700), c=cmap.to_rgba(laser_powers[i]))
cbar = fig.colorbar(cmap, location = 'right',ax=ax1, pad = 0)
cbar.ax.tick_params(labelsize='small')
cbar.set_label('Laser Power (mW)', rotation=270, labelpad = 22, fontsize='medium')


ax2.set_title('Co-TAPP-SMe 60nm NPoM - 633nm SERS Powerseries', color='blue')
ax2.set_ylabel('SERS Intensity (cts/mW/s)')
#ax2.set_xlabel('Raman shifts (cm$^{-1}$)')
norm = mpl.colors.LogNorm(vmin=0.003, vmax=laser_powers.max())
cmap = mpl.cm.ScalarMappable(norm=norm, cmap=mpl.cm.Blues)
cmap.set_array([])
for i in range(5,len(Co_nanocavity)):
    ax2.plot(wn_cal_633nm, Co_nanocavity[i]+((i-7)*500), c=cmap.to_rgba(laser_powers[i]))
cbar = fig.colorbar(cmap, location = 'right',ax=ax2, pad = 0)
cbar.ax.tick_params(labelsize='small')
cbar.set_label('Laser Power (mW)', rotation=270, labelpad = 22, fontsize='medium')


ax3.set_title('Ni-TAPP-SMe 60nm NPoM - 633nm SERS Powerseries', color='red')
ax3.set_ylabel('SERS Intensity (cts/mW/s)')
#ax2.set_xlabel('Raman shifts (cm$^{-1}$)')
norm = mpl.colors.LogNorm(vmin=0.003, vmax=laser_powers.max())
cmap = mpl.cm.ScalarMappable(norm=norm, cmap=mpl.cm.Reds)
cmap.set_array([])
for i in range(5,len(Ni_nanocavity)):
    ax3.plot(wn_cal_633nm, Ni_nanocavity[i]+((i-7)*300), c=cmap.to_rgba(laser_powers[i]))
cbar = fig.colorbar(cmap, location = 'right',ax=ax3, pad = 0)
cbar.ax.tick_params(labelsize='small')
cbar.set_label('Laser Power (mW)', rotation=270, labelpad = 22, fontsize='medium')


ax4.set_title('Zn-TAPP-SMe 60nm NPoM - 633nm SERS Powerseries', color='green')
ax4.set_ylabel('SERS Intensity (cts/mW/s)')
#ax2.set_xlabel('Raman shifts (cm$^{-1}$)')
norm = mpl.colors.LogNorm(vmin=0.003, vmax=laser_powers.max())
cmap = mpl.cm.ScalarMappable(norm=norm, cmap=mpl.cm.Greens)
cmap.set_array([])
for i in range(5,len(Zn_nanocavity)):
    ax4.plot(wn_cal_633nm, Zn_nanocavity[i]+((i-7)*700), c=cmap.to_rgba(laser_powers[i]))
cbar = fig.colorbar(cmap, location = 'right',ax=ax4, pad = 0)
cbar.ax.tick_params(labelsize='small')
cbar.set_label('Laser Power (mW)', rotation=270, labelpad = 22, fontsize='medium')
ax4.set_xlabel('Raman shifts (cm$^{-1}$)')

plt.show();

#%%

fig,ax=plt.subplots(2,1,figsize=[10,16], dpi=1000) 
ax1 = ax[0]
ax2 = ax[1]

fig.suptitle('M-TAPP-SMe 60nm NPoM - Average Nanocavity SERS\n633nm - 36$\mu$W on Sample', fontsize='x-large',x=0.5, y=0.94)


ax1.set_ylabel('SERS Intensity (cts/mW/s)', fontsize='large')
ax1.plot(wn_cal_633nm, H2_nanocavity[8], color='black', label = 'H2-TAPP-SMe')
ax1.plot(wn_cal_633nm, Co_nanocavity[8], color='blue', label = 'Co-TAPP-SMe')
ax1.plot(wn_cal_633nm, Ni_nanocavity[8], color='red', label = 'Ni-TAPP-SMe')
ax1.plot(wn_cal_633nm, Zn_nanocavity[8], color='green', label = 'Zn-TAPP-SMe')


ax2.set_ylabel('Normalized SERS Intensity (a.u.)', fontsize='large')
ax2.set_xlabel('Raman shifts (cm$^{-1}$)', fontsize='large')
ax2.plot(wn_cal_633nm, normalise(H2_nanocavity[8]), color='black', label = 'H2-TAPP-SMe')
ax2.plot(wn_cal_633nm, normalise(Co_nanocavity[8]), color='blue', label = 'Co-TAPP-SMe')
ax2.plot(wn_cal_633nm, normalise(Ni_nanocavity[8]), color='red', label = 'Ni-TAPP-SMe')
ax2.plot(wn_cal_633nm, normalise(Zn_nanocavity[8]), color='green', label = 'Zn-TAPP-SMe')
ax2.set_ylim(0,1.1)
ax2.legend()

