# -*- coding: utf-8 -*-
"""
Created on Tue Jul 25 16:06:25 2017

@author: wmd22
"""
from __future__ import division
from past.utils import old_div
import nplab.datafile as df
import numpy as np
def process_datafile_spectrum(h5object):
    """Process a spectrum for a h5file dataset"""
    Data = np.array(h5object)
    if 'variable_int_enabled' in list(h5object.attrs.keys()):
        variable_int = h5object.attrs['variable_int_enabled']
    else:
        variable_int =False
    if 'averaging_enabled' in list(h5object.attrs.keys()):
        if h5object.attrs['averaging_enabled']:
            Data = np.mean(Data,axis = 0)
    if ((variable_int == True) and #Check for variable integration time and that the background_int and reference_int are not none
                ((h5object.attrs['background_int'] != h5object.attrs['integration_time'] 
                    and (h5object.attrs['background_int'] != None))
                or (h5object.attrs['reference_int'] != h5object.attrs['integration_time'] 
                    and (h5object.attrs['reference_int'] != None)))):
        if h5object.attrs['background_int'] != None:
            if h5object.attrs['reference_int'] != None:
                Data = (old_div((Data-(h5object.attrs['background_constant']+h5object.attrs['background_gradient']*h5object.attrs['integration_time'])), 
                                (old_div((h5object.attrs['reference']-(h5object.attrs['background_constant']+h5object.attrs['background_gradient']*h5object.attrs['reference_int']))
                                *h5object.attrs['integration_time'],h5object.attrs['reference_int']))))
            else:
                Data = Data-(h5object.attrs['background_constant']+h5object.attrs['background_gradient']*h5object.attrs['integration_time'])
    else:
        if 'background' in list(h5object.attrs.keys()):
            if len(Data) == len(np.array(h5object.attrs['background'])):
                Data = Data - np.array(h5object.attrs['background'])
            if 'reference' in list(h5object.attrs.keys()):
                if len(Data) == len(np.array(h5object.attrs['reference'])):
                    Data = old_div(Data,(np.array(h5object.attrs['reference']) - np.array(h5object.attrs['background'])))
    if 'absorption_enabled' in list(h5object.attrs.keys()):
        if h5object.attrs['absorption_enabled']:
            Data = np.log10(old_div(1,np.array(Data)))
    return Data

def wavelength2wavenumber(wavelengths,laser_wavelength):
    """Input in nm output in cm^-1 """
    return 1.0/(laser_wavelength*1E-7)-(1.0/(wavelengths*1E-7))
def wavenumber2wavelength(wavenumbers,laser_wavelength):
    """Input in nm and cm^-1 output in nm """
    return 1.0/(1.0/(laser_wavelength)-(wavenumbers*1E-7))