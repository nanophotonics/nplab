# -*- coding: utf-8 -*-
"""
Created on Fri Jun  9 03:21:47 2023

@author: il322

Plotter for UV-Vis spectra & analysis exported from Reisner group UV-Vis

Using on data for 2023-10-13_Co-TAPP-SMe_20nm_Solution_Agg HER experiments

"""

import h5py
import os
import math
from math import log10, floor
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MultipleLocator
from importlib import reload

from nplab.analysis.general_spec_tools import spectrum_tools as spt


plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)


#%% Import data from csv


filename = r"S:\il322\PhD Data\M-TAPP-SMe\2023-10-13_Co-TAPP-SMe_20nm_Solution_Agg\2023-10-13 UV-Vis\SB109_UV1.csv"
data = np.genfromtxt(filename, delimiter = ',', skip_header = 2, skip_footer = 197, dtype = float)



#%% Split data into spectra

offset = 0.01
water = spt.Spectrum(x = data[:,0], y = data[:,1])
A = spt.Spectrum(x = data[:,2], y = data[:,3] + offset * 1)
B = spt.Spectrum(x = data[:,4], y = data[:,5] + offset * 2)
C = spt.Spectrum(x = data[:,6], y = data[:,7] + offset * 3)
D = spt.Spectrum(x = data[:,8], y = data[:,9] + offset * 4)
control = spt.Spectrum(x = data[:,10], y = data[:,11])
sheng = spt.Spectrum(x = data[:,12], y = data[:,13])
sheng_45 = spt.Spectrum(x = data[:,12], y = data[:,14])

A.normalise()
B.normalise()
C.normalise()
D.normalise()
control.normalise()
sheng.normalise()
sheng_45.normalise()


#%% Plot


mpl.rcParams['lines.linewidth'] = 0.2
plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)
fig, (ax) = plt.subplots(1, 1, figsize=[12,8], )

fig.suptitle('20nm AuNP@Co-TAPP-SMe Solution Aggregates')

ax.set_xlabel('Wavelength (nm)')
ax.set_ylabel('Intensity')
#ax.set_ylim(-1000,100000)


# A.plot(ax = ax, color = 'black', label = '0 min')
# B.plot(ax = ax, color = 'brown', label = '30 min')
# C.plot(ax = ax, color = 'darkorange', label = '60 min')
# D.plot(ax = ax, color = 'red', label = '90 min')
# control.plot(ax = ax, label = '20 nm AuNP Stock')
# sheng.plot(ax = ax, label = 'Sheng et al')


ax.plot(A.x, A.y_norm, color = 'black', label = '0 min')
ax.plot(B.x, B.y_norm, color = 'brown', label = '30 min')
ax.plot(C.x, C.y_norm, color = 'darkorange', label = '60 min')
ax.plot(D.x, D.y_norm, color = 'red', label = '90 min')
ax.plot(control.x, control.y_norm, color = 'pink', label = '20nm AuNP Stock')
ax.plot(sheng.x, sheng.y_norm, label = 'Sheng et al')
ax.plot(sheng_45.x, sheng_45.y_norm, color = 'green', label = 'Sheng et al 45hr')

ax.legend(title = 'Illumination Time')
ax.set_title('HER Experiment - UV-Vis')

plt.savefig('UV-Vis.svg', format = 'svg')