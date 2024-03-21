# -*- coding: utf-8 -*-
"""
Created on Mon May 22 15:05:48 2023

@author: il322
"""

import numpy as np
import scipy as sp
from matplotlib import pyplot as plt
import matplotlib as mpl


''' Quick plotter for laser safety stuff in Lab 1 BX-60 rig
    Plots MPE v exposure time for 633nm, 785nm, & 852nm
    Plots Actual Laser Irradiance v Laser Output Power
    Plots Nominal Optical Hazard Distance v Laser Output Power
    Refer to OneNote O:\0-Shared\Labs\LabNotes\Lab%201\BX60\Safety.one for MPE values & formulas
    
'''

plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)


#%% Plot MPE v. exposure time

exposure = np.linspace(0, 100, 2001)

# MPE for 3 wlns in W/m2
MPE_633 = 6.36/exposure
MPE_785 = 149.7166/exposure
MPE_852 = 203.8296/exposure

# Plotting
fig = plt.figure(figsize=(8,6))
plt.plot(exposure, MPE_633, label = 'MPE_633nm', color='red')
plt.plot(exposure, MPE_785, label = 'MPE_785nm', color = 'orange')
plt.plot(exposure, MPE_852, label = 'MPE_852nm', color='purple')
plt.title('Maximum Permissible Exposure v. Exposure Time',pad=10)
plt.xlabel('Exposure Time (s)')
plt.ylabel('MPE (Wm$^{-2}$)')
plt.legend(loc=1)
plt.show()

#%% Plot irradiance v laser output power with MPE hlines

# Calculate actual laser irradiance in W/m2
power = np.linspace(0, 100, 1001)
I = (power/1000)/(3.85*(10**-5))

# Plotting
fig = plt.figure(figsize=(8,6))
plt.plot(power, I, label = 'Laser Irradiance')
plt.title('Laser Irradiance v. Output Power')
plt.xlabel('Laser Output Power (mW)')
plt.ylabel('Laser Irradiance (Wm$^{-2}$)')
## Plot MPE h_lines for MPE_633 (0.25s) and MPE_785 & MPE_852 (10s)
plt.hlines(MPE_633[np.where(exposure == 0.25)], 0, power.max(), color = 'red', linestyles='dashed', label = 'MPE 633nm, 0.25s')
plt.hlines(MPE_785[np.where(exposure == 10)], 0, power.max(), color = 'orange', linestyles='dashed', label = 'MPE 785nm, 10s')
plt.hlines(MPE_852[np.where(exposure == 10)], 0, power.max(), color = 'purple', linestyles='dashed', label = 'MPE 852nm, 10s')
plt.legend(loc=2)
plt.show()

#%% Plot scattering NOHD v laser output power

# Calculate NOHD (cm) using 100s exposure and 2 rad divergence
NOHD_633 = (((4 * power / 1000)/(np.pi * MPE_633[np.where(exposure == 100)]))**(1/2) - (0.7/1000)) / 2 * 100
NOHD_785 = (((4 * power / 1000)/(np.pi * MPE_785[np.where(exposure == 100)]))**(1/2) - (0.5/1000000)) / 2 * 100
NOHD_852 = (((4 * power / 1000)/(np.pi * MPE_852[np.where(exposure == 100)]))**(1/2) - (0.5/1000000)) / 2 * 100

# Plotting
fig = plt.figure(figsize=(8,6))
plt.plot(power[0:230], NOHD_633[0:230], color='red', label = 'HeNe 633nm, 100s')
plt.plot(power[0:720], NOHD_785[0:720], color='orange', label = 'FPV 785nm, 100s')
plt.plot(power[0:260], NOHD_852[0:260], color='purple', label = 'FPV 852nm, 100s')
plt.title('Scattered Light NOHD v. Output Power')
plt.xlabel('Laser Output Power (mW)')
plt.ylabel('Nominal Ocular Hazard Distance (cm)')
plt.legend(loc=1)
plt.show()