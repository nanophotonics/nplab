# -*- coding: utf-8 -*-
'''
Created on 2023-01-30
@author: car72

Module with specific functions for processing and analysing DF spectra
Inherits from spectrum_tools.Spectrum
!!! Soon to be updated with DF & PL analysis functions from DF_Multipeakfit
'''

from nplab.analysis.general_spec_tools import spectrum_tools as spt
import numpy as np
import h5py
import matplotlib.pyplot as plt
import os
import matplotlib as mpl

from nplab.analysis.general_spec_tools import all_rc_params
df_rc_params = all_rc_params.master_param_dict['DF Spectrum']

class NPoM_Z_Scan(spt.Timescan):
    '''
    Object for handling NPoM DF z-scan datasets
    Contains functions for:
        Checking centering/focus of particles and/or collection path alignment
        Condensing z-stack into 1D spectrum, corrected for chromatic aberration
    '''
    def __init__(self, *args, dz = None, z_min = -3, z_max = 3, rc_params = df_rc_params, z_trim = 2, 
                 particle_name = None, **kwargs):
        super().__init__(*args, rc_params = rc_params, **kwargs)

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

    def check_centering(self, start_wl = 450, end_wl = 900, dz_interp_steps = 41, brightness_threshold = 3.6, 
                        plot = False, **kwargs):
        '''
        Checks whether the particle was correctly focused/centred during measurement
            (important for accuracy of absolute spectral intensities)

        Inspects the average z-profile of spectral intensity
        z-profile has one obvious intensity maximum if the particle is correctly focused/centred, and the collection path aligned
        If the z-profile deviates from this, the particle is flagged as unfocused/misaligned
        '''
        
        z_profile = np.average(self.Y, axis = 1)
        z_profile = z_profile - z_profile.min()

        dz_cont = np.linspace(self.z_min, self.z_max, dz_interp_steps)
        buffer = int(round(dz_interp_steps/4))

        z_profile_cont = np.interp(dz_cont, self.dz, z_profile)

        if plot == True:
            plt.plot(dz_cont, z_profile_cont/z_profile_cont.max(), 'k', lw = 4)
            plt.title('Average Z-Profile')
            plt.show()
            
        i_edge = np.trapz(z_profile_cont[:buffer]) + np.trapz(z_profile_cont[-buffer:])
        i_mid = np.trapz(z_profile_cont[buffer:-buffer])

        relative_brightness = i_mid/i_edge

        #if spectral brightness is significantly brighter than background in centre of z-stack, particle is considered to be aligned
        self.aligned = relative_brightness > brightness_threshold
        #print(avg_relative_brightness)

        if plot == True:
            title = 'Aligned' if self.aligned == True else 'Not Aligned'
            title = f'{title}\n{relative_brightness:.2f}'
            if self.particle_name is not None:
                title = f'{self.particle_name}\n{title}'

            self.plot_z_stack(title = title)

    def plot_z_stack(self, ax = None, y_label = None, rc_params = None, x_lim = [400, 900], 
                     plot_averages = False, avg_chunks = 10, cmap = 'inferno', title = None, **kwargs):
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
                      norm = mpl.colors.LogNorm(vmin = self.v_min, vmax = self.v_max))

        if x_lim is None:
            x_lim = self.x_lim

        if x_lim is not None and x_lim is not False:
            ax.set_xlim(*x_lim)

        ax.set_ylim(z.min(), z.max())
        ax.set_ylabel(y_label)

        if title is not None:
            ax.set_title(title)

        if external_ax == False:
            plt.show()
            plt.rcParams.update(old_rc_params)#put rcParams back to normal when done

class NPoM_DF_Spectrum(spt.Spectrum):
    '''
    Object containing xy data and functions for NPoM DF spectral analysis
    Inherits from "Spectrum" data class
    args can be y data, x and y data, h5 dataset or h5 dataset and its name
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    '''
    Work in Progress
    '''

    def plot_df(self, ax = None, rc_params = df_rc_params, smooth = True, x_lim = None, y_lim = None, **kwargs):
        '''
        Plots DF spectrum using self.x and self.y
        '''
        old_rc_params = plt.rcParams.copy()
        if ax is None:
            if self.rc_params is not None:
                plt.rcParams.update(self.rc_params)#use rc params specified with object unless set to false
            if rc_params is not None:
                plt.rcParams.update(rc_params)# and unless overridden when calling the function

            external_ax = False
            fig, ax = plt.subplots()

        else:
            external_ax = True

        ax.plot(self.x, self.y)
        if smooth == True:
            if self.y_smooth is None:
                self.y_smooth = spt.butter_lowpass_filt_filt(self.y, **kwargs)
            ax.plot(self.x, self.y_smooth)
                
        if x_lim is None:
            ax.set_xlim(self.x.min(), self.x.max())
        else:
            ax.set_xlim(x_lim)
        if y_lim is not None:
            ax.set_ylim(y_lim)

        ax.set_xlabel('Wavelength (nm)')
        ax.set_ylabel('Intensity')
        ax.set_yticks([])

        if external_ax == False:
            plt.show()
            plt.rcParams.update(old_rc_params)

    def find_maxima(self, smooth_first = False, analyse_raw = False, **kwargs):
        '''
        Smoothes spectrum and finds maxima
        Finds maxima in raw data if specified not to

        >>> !!! boolean logic below still needs testing !!! <<<

        '''
        if self.y_smooth is None or smooth_first == True:
            y_smooth = spt.butter_lowpass_filt_filt(self.y, **kwargs)
        elif self.y_smooth is not None:
            y_smooth = self.y_smooth
        elif (self.y_smooth is None and smooth_first == False) or analyse_raw == True:
            y_smooth = self.y

        y_maxs = spt.detect_minima(-y_smooth)

        return y_maxs

    def test_if_npom(self):
        '''
        Tests if DF spectrum is from a real NPoM or just random scattering object
        '''
        pass

    def test_if_double(self):
        '''
        Tests if DF spectrum has a split coupled mode
        '''
        pass
    def normalise(self):
        '''
        Identifies height of transverse mode and pre-TM minimum and normalises spectrum using these
        '''
        pass
    def identify_weird_peak(self):
        '''
        Some NPoM DF spectra have a very bright sharp peak in the quadrupolar region, as well as increased CM intensity
        This function identifies whether the spectrum belongs to this category
        '''
        pass
    def find_main_peaks(self):
        '''
        Identifies position and intensity of TM, CM(s) weird peak, where appropriate
        '''

class NPoM_PL_Spectrum(spt.Spectrum):
    '''
    Object containing xy data and functions for NPoM PL spectral analysis
    Inherits from "Spectrum" data class
    args can be y data, x and y data, h5 dataset or h5 dataset and its name
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

