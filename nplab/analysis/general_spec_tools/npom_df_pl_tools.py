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

from nplab.analysis.general_spec_tools import all_rc_params
df_rc_params = all_rc_params.master_param_dict['DF Spectrum']

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
