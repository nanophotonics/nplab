# -*- coding: utf-8 -*-
"""
Created on Sun May 14 14:22:50 2023

@author: il322

Module with specific functions for processing and analysing DF spectra
Inherits spectral classes from spectrum_tools.py


To do:
    make function for plotting histogram
    add manual screening to plot screening df
    add rejection filter to particle scan loop
    think about global rc params
    
    Separately, make class for particle to store all types of data
"""

import h5py
import os
import math
from math import log10, floor
import natsort
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from scipy.stats import norm
from importlib import reload

from nplab.analysis.general_spec_tools import spectrum_tools as spt
from nplab.analysis.general_spec_tools import npom_df_pl_tools as df
from nplab.analysis.general_spec_tools import all_rc_params as arp
df_rc_params = arp.master_param_dict['DF Spectrum']
plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)

class Z_Scan(df.NPoM_DF_Z_Scan):
    
    '''
    Object for handling NPoM DF z-scan datasets
    Inherits from df.NPoM_DF_Z_Scan class
    Contains functions for:
        Checking centering/focus of particles and/or collection path alignment
        Condensing z-stack into 1D spectrum, corrected for chromatic aberration
    '''
    
    def __init__(self, *args, dz = None, z_min = -3, z_max = 3, z_trim = 2, 
                 particle_name = None, avg_scan = False, **kwargs):
        super().__init__(*args, **kwargs)

        self.particle_name = particle_name

        if 'dz' not in self.__dict__.keys():  
            if dz is None:
                self.z_min = z_min
                self.z_max = z_max
                dz = np.linspace(self.z_min, self.z_max, len(self.t_raw))

            self.dz = dz

        self.dz = self.dz[z_trim:]
        self.t_raw = self.t_raw[z_trim:]

        self.z_min = self.dz.min()
        self.z_max = self.dz.max()

        self.Y = self.Y[z_trim:]  

        self.check_centering(**kwargs)

        self.avg_scan = avg_scan
        
    
    def plot_z_scan(self, ax = None, y_label = None, rc_params = None, x_lim = None, 
                    cmap = 'inferno', title = None, **kwargs):
        '''
        !!! needs docstring
        '''

        old_rc_params = plt.rcParams.copy()#saves initial rcParams before overwriting them

        if ax is None:
            if self.rc_params is not None:
                plt.rcParams.update(self.rc_params)#use rc params specified with object
            if rc_params is not None:
                plt.rcParams.update(rc_params)#unless overridden when calling the function

            fig, ax = plt.subplots()#if no axes provided, create some
            external_ax = False

        else:
            external_ax = True

        x = self.x
        z = self.dz

        y_label = 'Focal Height ($\mathrm{\mu}$m)'

        if y_label == False:
            y_label = ''        

        Y = np.vstack(self.Y)

        self.determine_v_lims(**kwargs)

        ax.pcolormesh(x, z, Y, cmap = cmap, shading = 'auto', 
                      norm = mpl.colors.LogNorm(vmin = self.v_min, vmax = self.v_max), rasterized = True)

        if x_lim is None:
            x_lim = self.x_lim

        if x_lim is not None and x_lim is not False:
            ax.set_xlim(x_lim)
            
        ax.set_ylim(z.min(), z.max())
        ax.set_ylabel(y_label)

        if title is not None:
            ax.set_title(title)

        if external_ax == False:
            plt.show()
            plt.rcParams.update(old_rc_params)#put rcParams back to normal when done

        
   
        
#%%     

class DF_Spectrum(df.NPoM_DF_Spectrum):
    
    '''
    Object containing xy data and functions for NPoM DF spectral analysis
    Inherits from "df.NPoM_DF_Spectrum" data class
    args can be y data, x and y data, h5 dataset or h5 dataset and its name
    '''
    
    def __init__(self, *args, rc_params = df_rc_params, particle_name = None, np_size = 80, lower_cutoff = None,
                 pl = False, doubles_threshold = 2, **kwargs):
        super().__init__(*args, rc_params = rc_params, **kwargs)

        self.particle_name = particle_name

        centre_trough_wl_dict = {80: 680, 70 : 630, 60 : 580, 50 : 550, 40 : 540}
        cm_min_wl_dict = {80: 580, 70 : 560, 60 : 540, 50 : 520, 40 : 500}
        self.centre_trough_wl = centre_trough_wl_dict[np_size]
        self.cm_min_wl = cm_min_wl_dict[np_size]
        self.np_size = np_size

        if lower_cutoff is not None:
            self.cm_min_wl = lower_cutoff

        self.pl = pl

        if self.y_smooth is None:
            self.y_smooth = spt.butter_lowpass_filt_filt(self.y, **kwargs)

        self.find_maxima(**kwargs)
        
        
    def find_critical_wln(self):
        
        '''
        Find critical wavelength from list of maxima (takes global maximum)
        '''
        crit_wln = 0
        global_max = 0
        for maximum in self.maxima:
            if self.y_smooth[maximum] > global_max:
                global_max = self.y_smooth[maximum]
                crit_wln = self.x[maximum]
                self.crit_maximum = maximum
                
        self.crit_wln = crit_wln
                

#%%

def df_screening(z_scan, df_spectrum, image = None, tinder = False, plot = False, title = None, save_file = None, **kwargs):
    
    '''
    Function to screen NPoMs based on DF data
    Can plot NPoM CWL.image, z_scan, and df_spectrum with maxima
    
    Parameters:
        z_scan: (Z_Scan)
        df_spectrum: (DF_Spectrum)
        image: (HDF5 image = None)
        tinder: (boolean = False) Set True for manual NPoM screening
        plot: (boolean = False) plot z_scan, df_spectrum with maxima, and CWL.image
        title: (string = None) title for plotting
        save_file: (string = None) path for saving figure. If none, does not save
        
    Output:
        df_spectrum: (DF_Spectrum) Return df_spectrum with updated .is_npom and .not_npom_because attributes
    '''
    
    # Plotting
    
    if plot == True:
        plt.rc('font', size=18, family='sans-serif')
        plt.rc('lines', linewidth=3)
        plt.figure(figsize=[7,16])    
        ax1=plt.subplot(3,1,1)
        ax2=plt.subplot(3,1,2, sharex=ax1)
        ax3 = plt.subplot(3,1,3)
        #ax1.get_xaxis().set_visible(False)
        ax1.set_title('Z-Scan')
        ax2.set_title('Stacked Dark-field Spectrum')
        ax3.set_title('Image')
        if title is not None:
            plt.suptitle(title)
        plt.tight_layout(pad = 1.2)
    
        ## Plot z-scan
        z_scan.plot_z_scan(ax=ax1, x_lim = (z_scan.x_lim))
    
        ## Plot df spectrum (raw & smoothed) w/ maxima & crit wln
        df_spectrum.plot_df(ax=ax2, x_lim = z_scan.x_lim)
        if len(df_spectrum.maxima) > 0:
            for maximum in df_spectrum.maxima:
                ax2.scatter(df_spectrum.x[maximum], df_spectrum.y_smooth[maximum], marker='x', s=250, color='black', zorder = 10)
            ax2.scatter(df_spectrum.crit_wln, np.max(df_spectrum.y_smooth[df_spectrum.maxima]), marker = '*', s = 400, color = 'purple', zorder = 20)
        ax2.set_yticks(np.round(np.linspace(0, df_spectrum.y.max(), 2), 3))       

        ## Plot CWL image
        if image is not None:
            ax3.imshow(image, zorder = 500)
        
    
    # Run NPoM tests & print reasons why NPoM rejected
        
    ## Test if z-scan centred correctly
    if z_scan.aligned == False:
        df_spectrum.is_npom = False
        df_spectrum.not_npom_because = 'Centering failed'
        if plot == True: 
            ax2.text(s='Centering Failed', x = z_scan.x_lim[0] + 50, y=(df_spectrum.y.max() + df_spectrum.y.min())/2, fontsize = 40)
    
    ## Test df spectrum via test_if_npom() 
    else:
        try:
            if df_spectrum.is_npom == False:
                if plot == True: ax2.text(s='NPoM Test failed: ' + df_spectrum.not_npom_because, x = z_scan.x_lim[0] + 50, y=(df_spectrum.y.max() + df_spectrum.y.min())/2, fontsize = 20, zorder=20)
        except:
            df_spectrum.test_if_npom()
            if df_spectrum.is_npom == False:
                if plot == True: ax2.text(s='NPoM Test failed: ' + df_spectrum.not_npom_because, x = z_scan.x_lim[0] + 50, y=(df_spectrum.y.max() + df_spectrum.y.min())/2, fontsize = 20, zorder=20)
    
    if plot == True and save_file == None:
        plt.show()
    
    elif plot == True and save_file is not None:
        plt.savefig(save_file, format = 'svg')
    
    
    ## Manual rejection
    if tinder == True:        
        ar = input('a/d = accept/decline: ').strip().lower()
        if ar == 'a':
            df_spectrum.is_npom = True
        if ar == 'd':
            ### If not already rejected by automatic screening
            if df_spectrum.is_npom == True:
                df_spectrum.is_npom = False
                df_spectrum.not_npom_because = 'Manually rejected'
    
    
    return df_spectrum


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
    ax.bar(bins, hist, width = ((max(bins)-min(bins))/(num_bins)), color=my_cmap(colors), align = 'edge', zorder=2)
    
    
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
    ax.text(s = 'FWHM:\n' + str(np.round(FWHM)) + 'nm', x = 470, y = ax.get_ylim()[1] * 0.8)
    
#%% Template of how to analyze your DF data (run this from your script)


# # Get particle scan & list of particles from h5
# my_h5 = h5py.File(r'C:\Users\il322\Desktop\Offline Data\2023-05-10_M-TAPP-SMe_NPoM\2023-05-22_M-TAPP-SME_80nm_NPoM_Track_DF_633nmPowerseries.h5')
# particle_scan = 'ParticleScannerScan_2'
# particle_list = natsort.natsorted(list(my_h5[particle_scan].keys()))
# for particle in particle_list:
#     if 'Particle' not in particle:
#         particle_list.remove(particle)


# # Set lists for critical wavelength hist & rejected particles
# crit_wln_list = []
# df_spectra_list = []
# rejected = []


# # Loop over particles in particle scan

# for particle in particle_list:
#     particle_name = particle_scan + ': ' + particle
#     particle = my_h5[particle_scan][particle]
    
#     ## Get z_scan, df_spectrum, crit_wln of particle
#     try:
#         z_scan = particle['lab.z_scan_0']
#     except:
#         print(particle_name + ': Z-Scan not found')
#         continue
#     z_scan = Z_Scan(z_scan)
#     z_scan.condense_z_scan() # Condense z-scan into single df-spectrum
#     ### Smoothing necessary for finding maxima
#     z_scan.df_spectrum = DF_Spectrum(x = z_scan.x,
#                                       y = z_scan.df_spectrum, 
#                                       y_smooth = spt.butter_lowpass_filt_filt(z_scan.df_spectrum, cutoff = 1600, fs = 200000))
#     z_scan.df_spectrum.test_if_npom()
#     z_scan.df_spectrum.find_critical_wln()
        
#     ## Run DF screening of particle
#     image = particle['CWL.thumb_image_0']
#     z_scan.df_spectrum = df_screening(z_scan = z_scan,
#                                       df_spectrum = z_scan.df_spectrum,
#                                       image = image,
#                                       tinder = False,
#                                       plot = False,
#                                       title = particle_name)

#     ## Add crit_wln & df_spectrum to list for binning or reject
#     if z_scan.aligned == True and z_scan.df_spectrum.is_npom == True:
#         crit_wln_list.append(z_scan.df_spectrum.crit_wln)
#         df_spectra_list.append(z_scan.df_spectrum.y_smooth)
        
#     else:
#         rejected.append(particle_name + ' - ' + z_scan.df_spectrum.not_npom_because)

# ## Plot histogram
# crit_wln_list = np.array(crit_wln_list)
# df_spectra_list = np.array(df_spectra_list)   
# bin_range = (crit_wln_list.min(), crit_wln_list.max())
# plot_df_histogram(crit_wln_list, 
#                   df_spectra_list, 
#                   z_scan.df_spectrum.x, 
#                   num_bins = int(np.ceil((len(crit_wln_list)**0.5))), 
#                   bin_range = (500,900), 
#                   df_avg_threshold = 2,
#                   title = 'Co-TAPP-SMe')


