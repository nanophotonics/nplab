# -*- coding: utf-8 -*-
"""
Created on Fri Sep 22 16:26:43 2023

@author: il322

Plotter for Matthew's polarization z-scans (2023-09-14_mrc79_Track_DF.h5)

Screens NPoMs from control & aggregate samples, using 0deg polarization z-scans (criteria is significantly relaxed for these experiments)
Plots df-spectra w/ averages for each polarization angle

Can include some of this in il322_DF_tools module
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
from nplab.analysis.il322_analysis import il322_DF_tools as df


plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)

#%%

my_h5 = h5py.File(r"C:\Users\il322\Desktop\Offline Data\2023-09-14_mrc79_Track_DF.h5")


#%% Screening NPoMs at 0deg polarization

# Set lists for critical wavelength hist & rejected particles

crit_wln_list = []
df_spectra_list = []
rejected = []
scan_list = ['ParticleScannerScan_3', 'ParticleScannerScan_4']

# Loop over particles in particle scan        

for particle_scan in scan_list:
    particle_list = natsort.natsorted(list(my_h5[particle_scan].keys()))
    
    ## Loop over particles in particle scan
    for particle in particle_list:
        if 'Particle' not in particle:
            particle_list.remove(particle)
    
    
    # Loop over particles in particle scan
    
    for particle in particle_list:
        particle_name = str(particle_scan) + ': ' + particle
        particle = my_h5[particle_scan][particle]
        
        ## Get z_scan, df_spectrum, crit_wln of particle
        z_scan = None
        image = None

        for key in particle.keys():
            if 'image' in key:
                image = particle[key]
                break
            
        for key in particle.keys():
            if 'z_scan_0' in key: # Only 0deg polarization z_scan
                z_scan = particle[key]
                z_scan = df.Z_Scan(z_scan, brightness_threshold = 0.01)
                
                ## Processing z-scan (x-lim,background, reference, truncate, min to 0)
                z_scan.x_lim = (450, 900)
                z_scan.Y -= z_scan.background
                z_scan.reference
                z_scan.reference -= z_scan.background
                with np.errstate(divide='ignore', invalid='ignore'):
                    z_scan.Y = np.divide(z_scan.Y, z_scan.reference)
                z_scan.Y = np.nan_to_num(z_scan.Y, posinf = 0, neginf = 0)
                z_scan.truncate(z_scan.x_lim[0], z_scan.x_lim[1])
                z_scan.Y -= z_scan.Y.min()
                        
                z_scan.condense_z_scan() # Condense z-scan into single df-spectrum
                ### Smoothing necessary for finding maxima
                z_scan.df_spectrum = df.DF_Spectrum(x = z_scan.x,
                                                  y = z_scan.df_spectrum, 
                                                  y_smooth = spt.butter_lowpass_filt_filt(z_scan.df_spectrum, cutoff = 1000, fs = 50000),
                                                  lower_threshold = -1,
                                                  upper_threshold = -0.005)
                z_scan.df_spectrum.test_if_npom()
                z_scan.df_spectrum.find_critical_wln()
                z_scan.df_spectrum = df.df_screening(z_scan = z_scan,
                                                  df_spectrum = z_scan.df_spectrum,
                                                  image = image,
                                                  tinder = False,
                                                  plot = False,
                                                  title = particle_name + ' ' + key)
                
                if z_scan.aligned == True and z_scan.df_spectrum.is_npom == True:
                    crit_wln_list.append(z_scan.df_spectrum.crit_wln)
                    df_spectra_list.append(z_scan.df_spectrum.y_smooth)
                    
                else:
                    rejected.append(particle_name + ' - ' + z_scan.df_spectrum.not_npom_because)
        
        
#%% DF Plots at each polarization angle


# Plot for control (scan 3)

fig = plt.figure(figsize = (8,20))
ax = fig.add_subplot()
cmap = plt.get_cmap('tab10')
       
## Subplot per scan

scan_list = ['ParticleScannerScan_3']

## Loop over polarization angles

pol_angles = np.linspace(0,90,10)

for pol_angle in pol_angles:    
    crit_wln_list = []
    df_spectra_list = []
    color = cmap(pol_angle/100)

    ## Select correct reference spectrum
    ref_string = 'white_ref_pol_' + str(int(pol_angle)) + '_0'
    try:
        reference = my_h5['OceanOpticsSpectrometer'][ref_string]
    except:
        reference = my_h5['OceanOpticsSpectrometer']['white_ref_pol_0_0']
    
    
    # Loop over particles in particle scan        
    
    for i,particle_scan in enumerate(scan_list):
        particle_list = natsort.natsorted(list(my_h5[particle_scan].keys()))
        
        ## Loop over particles in particle scan
        for particle in particle_list:
            if 'Particle' not in particle:
                particle_list.remove(particle)
        
        
        # Loop over particles in particle scan
        
        for particle in particle_list:
            particle_name = str(particle_scan) + ': ' + particle
            particle = my_h5[particle_scan][particle]
            
            ## Skip rejected particles
            if particle_name in rejected:
                break
            
            ## Get z_scan, df_spectrum, crit_wln of particle
            z_scan = None
            image = None
    
            for key in particle.keys():
                if 'image' in key:
                    image = particle[key]
                    break
                
            for key in particle.keys():
                if 'z_scan' in key: 
                    z_scan = particle[key]
                    z_scan = df.Z_Scan(z_scan, brightness_threshold = 0.01)
                    
                    ## Skip if wrong polarization angle
                    if z_scan.polarization_angle != pol_angle:
                        continue
                    
                    ## Processing z-scan (x-lim,background, reference, truncate, min to 0)
                    z_scan.x_lim = (450, 900)
                    z_scan.Y -= z_scan.background
                    z_scan.reference = reference
                    z_scan.reference -= z_scan.background
                    with np.errstate(divide='ignore', invalid='ignore'):
                        z_scan.Y = np.divide(z_scan.Y, z_scan.reference)
                    z_scan.Y = np.nan_to_num(z_scan.Y, posinf = 0, neginf = 0)
                    z_scan.truncate(z_scan.x_lim[0], z_scan.x_lim[1])
                    z_scan.Y -= z_scan.Y.min()
                            
                    z_scan.condense_z_scan() # Condense z-scan into single df-spectrum
                    ### Smoothing necessary for finding maxima
                    z_scan.df_spectrum = df.DF_Spectrum(x = z_scan.x,
                                                      y = z_scan.df_spectrum, 
                                                      y_smooth = spt.butter_lowpass_filt_filt(z_scan.df_spectrum, cutoff = 1000, fs = 50000),
                                                      lower_threshold = -1,
                                                      upper_threshold = -0.005)
                    # z_scan.df_spectrum.test_if_npom()
                    z_scan.df_spectrum.find_critical_wln()
                    # z_scan.df_spectrum = df.df_screening(z_scan = z_scan,
                    #                                   df_spectrum = z_scan.df_spectrum,
                    #                                   image = image,
                    #                                   tinder = True,
                    #                                   plot = True,
                    #                                   title = particle_name + ' ' + key)
                    
                    # if z_scan.aligned == True and z_scan.df_spectrum.is_npom == True:
                    #     crit_wln_list.append(z_scan.df_spectrum.crit_wln)
                    df_spectra_list.append(z_scan.df_spectrum.y_smooth)
                    df_spectrum_x = z_scan.df_spectrum.x
                        
                    # else:
                    #     rejected.append(particle_name + ' - ' + z_scan.df_spectrum.not_npom_because)
                    
    for spectrum in df_spectra_list:
        color = (color[0], color[1], color[2], 0.8)
        ax.plot(df_spectrum_x, spectrum + pol_angle/200, color = color, zorder = 0, linewidth = 1)

    ax.text(s = str(pol_angle) + u'\N{DEGREE SIGN}', x = 905, y = 0 + (pol_angle/200), color = color)
    color = 'black'
    ax.plot(df_spectrum_x, np.average(df_spectra_list, axis = 0) + pol_angle/200, color = color, zorder = 2, linewidth = 3)

ax.text(s = '$\lambda$/2 Angle', x = 870, y = 0.05+(pol_angle/200))    
ax.set_xlabel('Wavelength (nm)')
ax.set_xlim(550, 950)
ax.set_title('GEIO PBS (Control) NPoM DF Spectra')
#plt.savefig('GEIO PBS (Control) NPoM DF Spectra.png')

#%%
# Plot for aggregate (scan 4)

fig = plt.figure(figsize = (8,20))
ax = fig.add_subplot()
cmap = plt.get_cmap('tab10')
       
## Subplot per scan
scan_list = ['ParticleScannerScan_4']
rejected = ['ParticleScannerScan_4: Particle_162']

## Loop over polarization angles
agg_full_df_spectra_list = []
pol_angles = np.linspace(0,90,10)


for pol_angle in pol_angles:    
    crit_wln_list = []
    df_spectra_list = []
    color = cmap(pol_angle/100)

    ## Select correct reference spectrum
    ref_string = 'white_ref_pol_' + str(int(pol_angle)) + '_0'
    try:
        reference = my_h5['OceanOpticsSpectrometer'][ref_string]
    except:
        reference = my_h5['OceanOpticsSpectrometer']['white_ref_pol_0_0']
    
    
    # Loop over particles in particle scan        
    
    for i,particle_scan in enumerate(scan_list):
        particle_list = natsort.natsorted(list(my_h5[particle_scan].keys()))
        
        ## Loop over particles in particle scan
        for particle in particle_list:
            if 'Particle' not in particle:
                particle_list.remove(particle)
        
        
        # Loop over particles in particle scan
        
        for particle in particle_list:
            particle_name = str(particle_scan) + ': ' + particle
            particle = my_h5[particle_scan][particle]
            
            ## Skip rejected particles
            if particle_name in rejected:
                break
            
            ## Get z_scan, df_spectrum, crit_wln of particle
            z_scan = None
            image = None
    
            for key in particle.keys():
                if 'image' in key:
                    image = particle[key]
                    break
                
            for key in particle.keys():
                if 'z_scan' in key: 
                    z_scan = particle[key]
                    z_scan = df.Z_Scan(z_scan, brightness_threshold = 0.01)
                    
                    ## Skip if wrong polarization angle
                    if z_scan.polarization_angle != pol_angle:
                        continue
                    
                    ## Processing z-scan (x-lim,background, reference, truncate, min to 0)
                    z_scan.x_lim = (450, 900)
                    z_scan.Y -= z_scan.background
                    z_scan.reference = reference
                    z_scan.reference -= z_scan.background
                    with np.errstate(divide='ignore', invalid='ignore'):
                        z_scan.Y = np.divide(z_scan.Y, z_scan.reference)
                    z_scan.Y = np.nan_to_num(z_scan.Y, posinf = 0, neginf = 0)
                    z_scan.truncate(z_scan.x_lim[0], z_scan.x_lim[1])
                    z_scan.Y -= z_scan.Y.min()
                            
                    z_scan.condense_z_scan() # Condense z-scan into single df-spectrum
                    ### Smoothing necessary for finding maxima
                    z_scan.df_spectrum = df.DF_Spectrum(x = z_scan.x,
                                                      y = z_scan.df_spectrum, 
                                                      y_smooth = spt.butter_lowpass_filt_filt(z_scan.df_spectrum, cutoff = 1000, fs = 50000),
                                                      lower_threshold = -1,
                                                      upper_threshold = -0.005)
                    # z_scan.df_spectrum.test_if_npom()
                    z_scan.df_spectrum.find_critical_wln()
                    # z_scan.df_spectrum = df.df_screening(z_scan = z_scan,
                    #                                   df_spectrum = z_scan.df_spectrum,
                    #                                   image = image,
                    #                                   tinder = True,
                    #                                   plot = True,
                    #                                   title = particle_name + ' ' + key)
                    
                    # if z_scan.aligned == True and z_scan.df_spectrum.is_npom == True:
                    #     crit_wln_list.append(z_scan.df_spectrum.crit_wln)
                    df_spectra_list.append(z_scan.df_spectrum.y_smooth)
                    df_spectrum_x = z_scan.df_spectrum.x
                        
                    # else:
                    #     rejected.append(particle_name + ' - ' + z_scan.df_spectrum.not_npom_because)
                    
    #for spectrum in df_spectra_list:
        #color = (color[0], color[1], color[2], 0.8)
        #ax.plot(df_spectrum_x, spectrum + pol_angle/200, color = color, zorder = 0, linewidth = 1)
    print(shape(df_spectra_list))
    agg_full_df_spectra_list.append(df_spectra_list)

#     ax.text(s = str(pol_angle) + u'\N{DEGREE SIGN}', x = 905, y = 0 + (pol_angle/200), color = color)
#     color = 'black'
#     ax.plot(df_spectrum_x, np.average(df_spectra_list, axis = 0) + pol_angle/200, color = color, zorder = 2, linewidth = 3)

# ax.text(s = '$\lambda$/2 Angle', x = 870, y = 0.05+(pol_angle/200))    
# ax.set_xlabel('Wavelength (nm)')
# ax.set_xlim(550, 950)
# ax.set_title('GEIO IwS 40nm (Aggregate) NPoM DF Spectra')
#plt.savefig('GEIO IwS 40nm (Aggregate) NPoM DF Spectra.png')


#%% DF Plots at each polarization angle


# Plot for control (scan 3)

# fig = plt.figure(figsize = (8,20))
# ax = fig.add_subplot()
# cmap = plt.get_cmap('tab10')
       
## Subplot per scan

scan_list = ['ParticleScannerScan_3']

## Loop over polarization angles

pol_angles = np.linspace(0,90,10)
control_full_df_spectra_list = []


for pol_angle in pol_angles:    
    crit_wln_list = []
    df_spectra_list = []
    color = cmap(pol_angle/100)

    ## Select correct reference spectrum
    ref_string = 'white_ref_pol_' + str(int(pol_angle)) + '_0'
    try:
        reference = my_h5['OceanOpticsSpectrometer'][ref_string]
    except:
        reference = my_h5['OceanOpticsSpectrometer']['white_ref_pol_0_0']
    
    
    # Loop over particles in particle scan        
    
    for i,particle_scan in enumerate(scan_list):
        particle_list = natsort.natsorted(list(my_h5[particle_scan].keys()))
        
        ## Loop over particles in particle scan
        for particle in particle_list:
            if 'Particle' not in particle:
                particle_list.remove(particle)
        
        
        # Loop over particles in particle scan
        
        for particle in particle_list:
            particle_name = str(particle_scan) + ': ' + particle
            particle = my_h5[particle_scan][particle]
            
            ## Skip rejected particles
            if particle_name in rejected:
                break
            
            ## Get z_scan, df_spectrum, crit_wln of particle
            z_scan = None
            image = None
    
            for key in particle.keys():
                if 'image' in key:
                    image = particle[key]
                    break
                
            for key in particle.keys():
                if 'z_scan' in key: 
                    z_scan = particle[key]
                    z_scan = df.Z_Scan(z_scan, brightness_threshold = 0.01)
                    
                    ## Skip if wrong polarization angle
                    if z_scan.polarization_angle != pol_angle:
                        continue
                    
                    ## Processing z-scan (x-lim,background, reference, truncate, min to 0)
                    z_scan.x_lim = (450, 900)
                    z_scan.Y -= z_scan.background
                    z_scan.reference = reference
                    z_scan.reference -= z_scan.background
                    with np.errstate(divide='ignore', invalid='ignore'):
                        z_scan.Y = np.divide(z_scan.Y, z_scan.reference)
                    z_scan.Y = np.nan_to_num(z_scan.Y, posinf = 0, neginf = 0)
                    z_scan.truncate(z_scan.x_lim[0], z_scan.x_lim[1])
                    z_scan.Y -= z_scan.Y.min()
                            
                    z_scan.condense_z_scan() # Condense z-scan into single df-spectrum
                    ### Smoothing necessary for finding maxima
                    z_scan.df_spectrum = df.DF_Spectrum(x = z_scan.x,
                                                      y = z_scan.df_spectrum, 
                                                      y_smooth = spt.butter_lowpass_filt_filt(z_scan.df_spectrum, cutoff = 1000, fs = 50000),
                                                      lower_threshold = -1,
                                                      upper_threshold = -0.005)
                    # z_scan.df_spectrum.test_if_npom()
                    z_scan.df_spectrum.find_critical_wln()
                    # z_scan.df_spectrum = df.df_screening(z_scan = z_scan,
                    #                                   df_spectrum = z_scan.df_spectrum,
                    #                                   image = image,
                    #                                   tinder = True,
                    #                                   plot = True,
                    #                                   title = particle_name + ' ' + key)
                    
                    # if z_scan.aligned == True and z_scan.df_spectrum.is_npom == True:
                    #     crit_wln_list.append(z_scan.df_spectrum.crit_wln)
                    df_spectra_list.append(z_scan.df_spectrum.y_smooth)
                    df_spectrum_x = z_scan.df_spectrum.x
                    
                        
                    # else:
                    #     rejected.append(particle_name + ' - ' + z_scan.df_spectrum.not_npom_because)
                    
    for spectrum in df_spectra_list:
        color = (color[0], color[1], color[2], 0.8)
        #ax.plot(df_spectrum_x, spectrum + pol_angle/200, color = color, zorder = 0, linewidth = 1)

    control_full_df_spectra_list.append(df_spectra_list)


#%%
def plot_df_histogram(crit_wln_list, 
                      df_spectra_list = None, 
                      df_spectrum_x = None, 
                      num_bins = 31, 
                      bin_range = (550, 850),
                      df_avg_threshold = 1,
                      ax = None,
                      title = None,
                      ax_df_label = None,
                      **kwargs):

    '''
    Function for plotting darkfield critical wavelength histogram with avg df spectra
    
    Parameters:
        crit_wln_list: (1DArray float) array of critical wavelengths
        df_spectra_list: (2DArray float = None) array of dark field spectra, axis 0 corresponds to particles in crit_wln_list
        df_spectrum_x: (1D Array float = None) array of dark field x-axis for plotting
        num_bins: (int = 31) number of bins for histogram
        bin_range: (tuple = (550,850)) wavelength range for histogram
        df_avg_threshold: (int = 1) Number of counts in bin required to plot df average for that bin
        ax: (plt ax = None) axis for plotting. If None will create figure
        title: (str = None) title for histogram
        ax_df_label: (str = None) Label for secondary y-axis
        
    Need to add:
        Fitting histogram
        Title
        Saving
        RC Params
    '''
    
    
    # Binning data
    
    crit_wln_list = np.array(crit_wln_list)
    df_spectra_list = np.array(df_spectra_list)
    
    ## Set bins
    bins = np.linspace(bin_range[0], bin_range[1], num_bins)
    
    ## Find bin index for each crit_wln
    inds = np.digitize(crit_wln_list, bins[:-1], right = False) - 1
    
    ## Find counts in each bin
    hist = np.histogram(bins[inds], bins = bins)[0]
    bins = bins[:-1]
    
    
    # Plot histogram
    
    if ax is None:
        plt.rc('font', size=18, family='sans-serif')
        plt.rc('lines', linewidth=3)
        fig = plt.figure(figsize = (8,6))
        ax = fig.add_subplot()
        ax.set_xlabel('Wavelength (nm)')
        ax.set_ylabel('Frequency')
        if title is not None:
            fig.suptitle(title, fontsize = 'large')
        else:
            fig.suptitle('NPoM $\lambda_c$ Histogram', fontsize = 'large')
   
    else:
        if title is not None:
            plt.title(title, fontsize = 'large', pad = 1)
        else:
            plt.title('NPoM $\lambda_c$ Histogram', fontsize = 'large', pad = 1)
    
    my_cmap = plt.get_cmap("hsv")
    colors = (-bins + 800)/320 # Rainbow colormap where 550nm = violet and 800nm = ref
#    ax.bar(bins, hist, width = ((max(bins)-min(bins))/(num_bins)), color=my_cmap(colors), align = 'edge', zorder=2)
    ax.bar(bins, hist, width = ((max(bins)-min(bins))/(num_bins)), align = 'edge', zorder=2, **kwargs)   
    
    # Average df spectrum per bin
    
    if df_spectra_list is not None and df_spectrum_x is not None:
    
        bin_avg = np.zeros((len(hist), len(df_spectra_list[0])))     
        
        ## Secondary axis for df_spectrum
        ax_df = ax.twinx()
        if ax_df_label is not None:
            ax_df.set_ylabel(ax_df_label, rotation = 270, labelpad = 25)
            ax_df.yaxis.set_label_position("right")
        
        ## Loop over each bin
        for i in range(0, len(hist)):
            ### If bin frequency meets threshold 
            if hist[i] >= df_avg_threshold:
                #### Avg df_spectrum in bin
                bin_avg[i] = np.sum(df_spectra_list[np.where(inds == i)], axis = 0) / len(df_spectra_list[np.where(inds == i)])
                #### Plot normalized avg df spectrum
                ax_df.plot(df_spectrum_x, (bin_avg[i] - bin_avg[i].min())/(bin_avg[i].max() - bin_avg[i].min()), color=my_cmap(colors[i]))
    
        ax_df.set_ylim(0, 1.2)
        ax_df.set_yticks([])
        ax.set_zorder(ax_df.get_zorder() + 1)
        ax.patch.set_visible(False)
        
    ax.set_xlim(bin_range)
    
    
    # Fit & plot normal distribution
    
    mu, std = norm.fit(crit_wln_list)
    FWHM = 2.3548 * std
    x = np.linspace(ax.get_xlim()[0], ax.get_xlim()[1], 500)
    p = norm.pdf(x, mu, std)
    ax.plot(x, p/p.max() * hist[np.where(bins < mu)[0].max()], color = 'black', linewidth = 2, linestyle = 'dashed')
    #ax.text(s = 'FWHM:\n' + str(np.round(FWHM)) + 'nm', x = 470, y = ax.get_ylim()[1] * 0.8)
    #ax.set_xlim(bin_range)
#%%

plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)
fig = plt.figure(figsize = (8,6))
ax = fig.add_subplot()
ax.set_xlabel('DF Intensity STD')
ax.set_ylabel('Frequency')
fig.suptitle('Polarized DF Intensity Deviation', fontsize = 'large')

full_df_array = control_full_df_spectra_list
num_particles = len(full_df_array[0])

pixel_std = np.std(full_df_array, axis = 0) # std per pixel across 10 polarizations
particle_std = np.sum(pixel_std, axis = 1) # particle std across 10 polarizations

# fig = plt.figure(figsize = (8,8))
# ax = fig.add_subplot()

# for i in range(0, num_particles):
#     ax.scatter(i, particle_std[i])

## Plot histogram
crit_wln_list = np.array(particle_std)
plot_df_histogram(crit_wln_list,  
                  num_bins = 35, 
                  bin_range = (0,10), 
                  df_avg_threshold = 2,
                  #title = 'Co-TAPP-SMe',
                  ax = ax,
                  color = (1,0,0,0.5))


full_df_array = agg_full_df_spectra_list
num_particles = len(full_df_array[0])

pixel_std = np.std(full_df_array, axis = 0) # std per pixel across 10 polarizations
particle_std = np.sum(pixel_std, axis = 1) # particle std across 10 polarizations

# fig = plt.figure(figsize = (8,8))
# ax = fig.add_subplot()

# for i in range(0, num_particles):
#     ax.scatter(i, particle_std[i])

## Plot histogram
crit_wln_list = np.array(particle_std)
plot_df_histogram(crit_wln_list,  
                  num_bins = 35, 
                  bin_range = (0,10), 
                  df_avg_threshold = 2,
                  title = '',
                  ax = ax,
                  color = (0,0,1,0.5))

ax.set_xlim(0,7)

        
    
    