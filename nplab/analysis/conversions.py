# -*- coding: utf-8 -*-
"""
Created on Mon Jul 15 11:50:45 2019

@author: Eoin Elliott
"""
import numpy as np
import scipy.constants
      
    
def wavelength_to_omega(wavelengths, centre_wl = 633.): # wl in nm
    omega = 2*np.pi*scipy.constants.c*(1./(wavelengths*1e-9) - 1./(centre_wl*1e-9))
    return omega # Stokes omegas are negative

def omega_to_wavelength(omega, centre_wl = 633):
    wavelengths = 1e9/(omega/(2.*np.pi*scipy.constants.c) + 1./(centre_wl*1e-9))
    return wavelengths # consistant signs
def OD_to_power(P0,OD):
    return P0*10.**(-OD)

def wavelength_to_cm(wavelengths, centre_wl = 633.):
    return (1./(wavelengths*1e-9) - 1./(centre_wl*1e-9))/100
    # Stokes cm are negative
    
def cm_to_wavelength(cm, centre_wl = 633):
    return 1e9/(cm*100 +1./(centre_wl*1e-9))

def simple_wavelength_to_omega(wavelengths):
    omega = 2*np.pi*scipy.constants.c*1./(wavelengths*1e-9)/1.0e-9
    
    return omega
def simple_omega_to_wavelength(omega):
    wavelength =  1e9*(2.*np.pi*scipy.constants.c)/omega
    return wavelength
def cm_to_omega(cm):
    return 2*np.pi*scipy.constants.c*100.*cm