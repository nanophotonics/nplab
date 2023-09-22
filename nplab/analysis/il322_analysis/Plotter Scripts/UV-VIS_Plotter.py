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

my_h5 = h5py.File(r"C:\Users\il322\Desktop\Offline Data\car72 M-TAPP UV-Vis\2021-04-05 All MTPP UV-Vis PL.h5")
my_csv = r"C:\Users\il322\Desktop\Offline Data\car72 M-TAPP UV-Vis\Co-TAPP Abs_processed.csv"

Co = np.genfromtxt(my_csv, delimiter=',')
Co = Co.transpose()
Co = spt.Spectrum(Co[0], Co[1])

H2 = my_h5['H2-MTPP MeOH MeCN UV-Vis']
Ni = my_h5['Ni-MTPP MeOH MeCN UV-Vis']
Zn = my_h5['Zn-MTPP MeOH MeCN UV-Vis']

H2 = spt.Spectrum(x = H2.attrs['wavelengths'], y = H2.attrs['yRaw'])
Ni = spt.Spectrum(x = Ni.attrs['wavelengths'], y = Ni.attrs['yRaw'])
Zn = spt.Spectrum(x = Zn.attrs['wavelengths'], y = Zn.attrs['yRaw'])

#%%
plot_start = 300
fig, ax = plt.subplots(1,1, figsize = (8,6))
my_cmap = plt.get_cmap('Set1')
ax.plot(H2.x[300:], H2.y[300:], label = 'H2-TAPP', color = my_cmap(3), zorder = 4)
ax.plot(Co.x[:400], Co.y[:400], label = 'Co-TAPP', color = my_cmap(1), zorder = 2)
ax.plot(Ni.x[300:], Ni.y[300:], label = 'Ni-TAPP', color = my_cmap(6), zorder = 3)
ax.plot(Zn.x[300:], Zn.y[300:], label = 'Zn-TAPP', color = my_cmap(2), zorder = 1)

ax.plot(H2.x[280:300], H2.y[280:300], linestyle = 'dashed', color = my_cmap(3), zorder = 1)
ax.plot(Co.x[:420], Co.y[:420], linestyle = 'dashed', color = my_cmap(1), zorder = 1)
ax.plot(Ni.x[280:300], Ni.y[280:300], linestyle = 'dashed', color = my_cmap(6), zorder = 1)
ax.plot(Zn.x[280:300], Zn.y[280:300], linestyle = 'dashed', color = my_cmap(2), zorder = 1)

#ax.text(s = '633nm Raman\n   Excitation', x = 645, y = 0.12, fontsize = 'small', color = 'red')
ax.text(s = '785nm Raman\n   Excitation', x = 745, y = 0.01, fontsize = 'small', color = 'darkorange')

ax.vlines(x = 632.8, ymin = 0, ymax = 0.25, color = 'red', linewidth = 10, zorder = 0)
ax.vlines(x = 785, ymin = -1, ymax = 0.25, color = 'darkorange', linewidth = 10, zorder = 0)

ax.set_xlim(720,850)
ax.set_ylim(-0.004,0.015)
ax.set_xlabel('Wavelength (nm)', fontsize = 'large')
ax.set_ylabel('Absorption', fontsize = 'large')
ax.legend()
fig.suptitle('UV-Vis: 1$\mu$M M-TAPP in 1:1 MeOH:MeCN')

plt.savefig('785 inset M-TAPP UV-Vis.svg', format = 'svg')