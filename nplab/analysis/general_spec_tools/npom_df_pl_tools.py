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

class NPoM_Z_Scan(spt.Timescan):
    '''
    Object for handling NPoM DF z-scan measurements
    Contains functions for:
        Checking centering/focus of particles and/or collection path alignment
        Condensing z-stack into 1D spectrum, corrected for chromatic aberration
    '''
    def __init__(self, *args, dz = None, z_min = -3, z_max = 3, **kwargs):
        super().__init__(*args, **kwargs)

        if dz is None:
            dz = np.linspace(self.z_min, self.z_max, len(self.t_raw))

        self.dz = dz
        self.z_min = z_min
        self.z_max = z_max

    def check_centering(self, **kwargs):
        Y_T = self.Y.T #Transpose to look at scan at each wavelength

        start_index = abs(self.x - 500).argmin()
        end_index = abs(self.x - 820).argmin()

        scan_maxima = np.max(Y_T[start_index:end_index], axis = 1) #Find max intensity of each scan in region 500 - 820 nm; too much noise at longer wavelengths
        print(scan_maxima.shape, self.x.shape)

        fs = 50000
        scan_maxima_smooth = spt.butter_lowpass_filt_filt(scanMaxs, **kwargs) #Smoothes the 'spectrum'
        maxWlIndices = detectMinima(-scanMaxsSmooth) + startDex #finds indices of main spectral 'peaks'

        while len(maxWlIndices) > 4:
            #unrealistic, so have another go with stronger smoothing
            fs += 3000
            scanMaxsSmooth = butterLowpassFiltFilt(scanMaxs, cutoff = 1500, fs = fs)
            maxWlIndices = detectMinima(-scanMaxsSmooth) + startDex

        maxWlIndices = np.array([np.arange(i - 2, i + 3) for i in maxWlIndices]).flatten()
        #adds a few either side of each peak for luck

        brightScans = np.array([scan for scan in zScanTransposed[maxWlIndices]])
        #List of corresponding z-stacks
        testFactor = 0
        dZInterp = np.linspace(-3, 3, 41)

        for z in brightScans:
            z[0] = z[1]
            z -= z.min()
            z = np.interp(dZInterp, dz, z)     

            iEdge = np.trapz(z[:10]) + np.trapz(z[-(10):])
            iMid = np.trapz(z[10:-10])
            testFactor += iMid/iEdge

        testFactor /= len(maxWlIndices)
        
        if testFactor > 3.6:      
            #print(f'Aligned ({testFactor:.2f})')
            return True
        else:      
            #print(f'Misaligned ({testFactor:.2f})')
            return False


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

