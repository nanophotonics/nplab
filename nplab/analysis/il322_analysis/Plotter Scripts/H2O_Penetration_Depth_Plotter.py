# -*- coding: utf-8 -*-
"""
Created on Fri Jun  9 03:21:47 2023

@author: il322

Plotter for M-TAPP-SMe UV-VIS Data

"""

import h5py
import os
import math
from math import log10, floor
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from importlib import reload

from nplab.analysis.general_spec_tools import spectrum_tools as spt


plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)


#%%

my_csv = r"C:\Users\il322\Desktop\Offline Data\Hale water pen depth.csv"

depth = np.genfromtxt(my_csv, delimiter=',')
depth = depth.transpose()
depth = spt.Spectrum(depth[0]*10**3, depth[3])

#%%

fig, ax = plt.subplots(1,1, figsize = (8,6))
my_cmap = plt.get_cmap('Set1')

ax.plot(depth.x, depth.y, label = 'H2-TAPP', color = 'blue', zorder = 4)

#ax.text(s = '633nm Raman\n   Excitation', x = 645, y = 0.12, fontsize = 'small', color = 'red')
#ax.text(s = '785nm Raman\n   Excitation', x = 745, y = 0.01, fontsize = 'small', color = 'darkorange')

#ax.vlines(x = 632.8, ymin = 0, ymax = 0.25, color = 'red', linewidth = 10, zorder = 0)
#ax.vlines(x = 785, ymin = -1, ymax = 0.25, color = 'darkorange', linewidth = 10, zorder = 0)


ax.set_xlim(600,1200)
ax.set_ylim(1, 1000)
#ax.set_yscale('log')
ax.set_xlabel('Wavelength (nm)', fontsize = 'large')
ax.set_ylabel('Penetration Depth (mm)', fontsize = 'large')
#ax.legend()
fig.suptitle('Light Penetration Depth in Pure Water')

#plt.savefig('785 inset M-TAPP UV-Vis.svg', format = 'svg')