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

import lmfit
from lmfit.models import LorentzianModel, GaussianModel

from nplab.analysis.general_spec_tools import all_rc_params as arp
df_rc_params = arp.master_param_dict['DF Spectrum']

class NPoM_DF_Z_Scan(spt.Timescan):
    '''
    Object for handling NPoM DF z-scan datasets
    Contains functions for:
        Checking centering/focus of particles and/or collection path alignment
        Condensing z-stack into 1D spectrum, corrected for chromatic aberration
    '''
    def __init__(self, *args, dz = None, z_min = -3, z_max = 3, rc_params = df_rc_params, z_trim = 2, 
                 particle_name = None, avg_scan = False, **kwargs):
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

        self.avg_scan = avg_scan

    def check_centering(self, start_wl = 450, end_wl = 900, dz_interp_steps = 41, brightness_threshold = 3.6, 
                        plot = False, print_progress = True, **kwargs):
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
        self.aligned = relative_brightness > brightness_threshold #bool
        #print(avg_relative_brightness)

        if plot == True:
            title = 'Aligned' if self.aligned == True else 'Not Aligned'
            title = f'{title}\n{relative_brightness:.2f}'
            if self.particle_name is not None:
                title = f'{self.particle_name}\n{title}'

            self.plot_z_scan(title = title)

    def condense_z_scan(self, threshold = 0.01, plot = False, cosmic_ray_removal = True, **kwargs):
        Y_T = self.Y.T

        max_indices = np.array([wl_scan.argmax() for wl_scan in Y_T])#finds index of brightest z position for each wavelength
        max_indices_smooth = spt.butter_lowpass_filt_filt(max_indices, cutoff = 900, fs = 80000)#smooth

        '''
        Z Scan is thresholded and the centroid taken for each wavelength
        Don't ask me how this works - Jack Griffiths wrote it
        '''
        Y_thresh = spt.remove_nans(self.Y, noisy_data = True).astype(np.float64)
        Y_thresh = (Y_thresh - Y_thresh.min(axis = 0))/(Y_thresh.max(axis = 0) - Y_thresh.min(axis = 0))
        Y_thresh -= threshold
        Y_thresh *= (Y_thresh > 0) #Normalise and Threshold array
        ones = np.ones([Y_thresh.shape[1]])
        z_positions = np.array([ones*n for n in np.arange(Y_thresh.shape[0])]).astype(np.float64)

        centroid_indices = np.sum((Y_thresh*z_positions), axis = 0)/np.sum(Y_thresh, axis = 0) #Find Z centroid position for each wavelength
        centroid_indices = spt.remove_nans(centroid_indices)

        assert np.count_nonzero(np.isnan(centroid_indices)) == 0, 'All centroids are NaNs; try changing the threshold when calling condense_z_scan()'

        if plot == True:
            old_rc_params = plt.rcParams.copy()
            plt.rcParams.update(df_rc_params)
                            
            fig = plt.figure(figsize = (7, 12))

            ax_z = plt.subplot2grid((14, 1), (0, 0), rowspan = 8)
            plt.setp(ax_z.get_xticklabels(), visible = False)
            ax_df = plt.subplot2grid((14, 1), (8, 0), rowspan = 6, sharex = ax_z)

            self.plot_z_scan(ax_z, title = f'{self.particle_name}\nAligned = {self.aligned}')
    
        df_spectrum = []
        z_profile = []

        for n, centroid_index in enumerate(centroid_indices):
            #use centroid_index in z (as float) to obtain interpolated spectral intensity

            if 0 < centroid_index < len(self.dz) - 1:#if calculated centroid is within z-range
                lower = int(centroid_index)
                upper = lower + 1
                frac = centroid_index % 1
                yi = spt.linear_interp(Y_T[n][lower], Y_T[n][upper], frac)
                zi = spt.linear_interp(self.dz[lower], self.dz[upper], frac)
                
            else:
                #print('centroid shifted')
                if centroid_index <= 0:
                    yi = Y_T[n][0]     
                    zi = self.dz[0]
                elif centroid_index >= len(self.dz) - 1:
                    yi = Y_T[n][-1]     
                    zi = self.dz[-1]

            df_spectrum.append(yi)
            z_profile.append(zi)

        if cosmic_ray_removal == True:
            df_spectrum = spt.remove_cosmic_rays(df_spectrum, **kwargs)

        df_spectrum = spt.remove_nans(df_spectrum)

        self.df_spectrum = np.array(df_spectrum)
        self.z_profile = np.array(z_profile)

        if plot == True:
            ax_df.plot(self.x, df_spectrum, alpha = 0.6, label = 'Centroid')
            ax_z.plot(self.x, z_profile)

            ax_df.plot(self.x, np.average(self.Y, axis = 0), label = 'Avg')
            ax_df.set_xlim(400, 900)
            ax_df.legend(loc = 0, fontsize = 14, ncol = 2)
            ax_df.set_xlabel('Wavelength (nm)')

            plt.subplots_adjust(hspace = 0)
            plt.show()

            plt.rcParams.update(old_rc_params)
           
    def plot_z_scan(self, ax = None, y_label = None, rc_params = None, x_lim = [400, 900], 
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

    def analyse_df(self, **kwargs):        
        self.test_if_npom(**kwargs)
        self.test_if_double(**kwargs)
    
    '''
    Work in Progress
    '''

    def plot_df(self, ax = None, rc_params = df_rc_params, smooth = True, x_lim = None, y_lim = None, y_ticks = False, 
                **kwargs):
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
        if y_ticks == False:
            ax.set_yticks([])

        if external_ax == False:
            plt.show()
            plt.rcParams.update(old_rc_params)
            return fig, ax

    def find_maxima(self, smooth_first = False, analyse_raw = False, lower_threshold = -np.inf, upper_threshold = np.inf, **kwargs):
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
            
        self.maxima = spt.detect_minima(-y_smooth, upper_threshold, lower_threshold)
        self.minima = spt.detect_minima(y_smooth)

    def test_if_npom(self, min_int_signal = 0.05, max_int_signal = 2.5, npom_threshold = 1.5, plot_is_npom = False, **kwargs):
        '''
        Tests if DF spectrum is from a real NPoM or just random scattering object
        '''
    
        self.is_npom = False #Guilty until proven innocent

        '''To be accepted as an NPoM, you must first pass four trials'''

        '''Trial the first: do you have a reasonable signal?'''
        #If sum of all intensities lies outside a given range, it's probably not an NPoM
        if np.sum(self.y - self.y.min()) < min_int_signal or (self.y_raw.min() < -0.1 and self.x.min() < 500):
            self.not_npom_because = 'signal too low'            
            return

        '''Trial the second: do you slant in the correct direction?'''
        #NPoM spectra generally have greater total signal at longer wavelengths due to coupled mode
        first_half = self.y[:len(self.y)//2]
        second_half = self.y[len(self.y)//2:]
        
        if np.sum(first_half) >= np.sum(second_half) * npom_threshold:
            self.not_npom_because = 'coupled mode region too weak'
            return

        '''Trial the third: are you more than just noise?'''
        #If the sum of the noise after 900 nm is greater than that of the spectrum itself, it's probably crap

        x_upper, y_upper = spt.truncate_spectrum(self.x_raw, self.y_raw, 900, self.x_raw.max())
        if np.sum(self.y)*3 > np.sum(y_upper)/npom_threshold:
            self.not_npom_because = 'just noise'

        '''Trial the fourth: do you have more than one maximum?'''
        #NPoM spectra usually have more than one distinct peak
        #Only require one peak for NP size <= 60nm
        if len(self.maxima) < 2 and self.np_size > 60:
            self.not_npom_because = 'too few peaks'
            return
        elif len(self.maxima) < 1:
            self.not_npom_because = 'too few peaks'
            return

        self.is_npom = True
        self.not_npom_because = 'N/A'

    def test_if_double(self, plot_is_double = False, **kwargs):
        '''
        Tests if DF spectrum has a split coupled mode
        '''
        self.is_double = False

        if len(self.minima) == 0 or len(self.maxima) == 0:
            self.is_npom = False
            self.is_double = 'N/A'
            self.not_npom_because = 'no minima or maxima'
            return

        x_mins = self.x[self.minima]
        y_mins = self.y_smooth[self.minima]

        x_maxs = self.x[self.maxima]
        y_maxs = self.y_smooth[self.maxima]

        y_max = y_maxs.max()
        x_maxs = x_maxs[y_maxs.argmax()]

        maxs_sorted = sorted([i for i in zip(x_maxs, y_maxs) if i[0] > self.cm_min_wl*1.0345],
                             key = lambda i: i[1]) # all maxima of smoothed spectrum within coupled mode region

        '''
        !!! Work in progress
        '''

    def multi_peak_fit(self, peak_height_threshold = 0.1, peak_find_plot = False,
                       peak_fit_plot = False, peak_shape = 'gaussian', peak_find_height_frac = 0.5, **kwargs):
        #print(d2_plot)
        #print(self.x.min())

        approx_gausses = spt.approx_peak_gausses(self.x, self.y_smooth, height_frac = peak_find_height_frac, 
                                                 plot = peak_find_plot,
                                                 threshold = peak_height_threshold, peak_shape = 'gaussian', **kwargs)

        for g_n, (height, center, width, height_frac) in enumerate(approx_gausses):
            g_mod_n = GaussianModel(prefix = f'g{g_n}_')
            #print(height)
            sigma = width/(2*np.sqrt(2*np.log(1/peak_find_height_frac)))
            amplitude = height*(np.sqrt(2*np.pi)*sigma)

            pars_n = g_mod_n.make_params(amplitude = amplitude, center = center, sigma = sigma)
            pars_n[f'g{g_n}_amplitude'].set(min = 0)
            #pars_n[f'g{g_n}_center'].set(center)
            pars_n[f'g{g_n}_sigma'].set(min = sigma*0.5, max = sigma*2)

            if g_n == 0:
                g_mod = g_mod_n
                pars = pars_n
            else:
                g_mod += g_mod_n
                pars.update(pars_n)

        y_init = g_mod.eval(pars, x = self.x)

        g_out = g_mod.fit(self.y_smooth, pars, x = self.x, nan_policy = 'propagate')

        y_fit = g_out.best_fit
        comps = g_out.eval_components(x = self.x)

        for comp_name, gauss in comps.items():
            setattr(self, f'Peak_{comp_name[:-1]}', gauss)

        if peak_fit_plot == True:
            fig, ax = plt.subplots()

            for comp_name, gauss in comps.items():
                ax.plot(self.x, gauss, 'b:', label = comp_name)

            ax.plot(self.x, self.y, label = 'Data', zorder = -3)
            ax.plot(self.x, y_init, 'r-', lw = 1, label = 'initial guess', zorder = -2)
            ax.plot(self.x, y_fit, '--', label = 'Best fit', zorder = -2)

            ax.set_xlabel('Wavelength (nm)')
            ax.set_ylabel('Intensity')

            ax.legend(loc = 'center left', bbox_to_anchor = (1, 0.5))
            plt.title('Fitting')
            plt.show()

        self.y_fit = y_fit
        self.fit_residual = g_out.residual
        
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

