# -*- coding: utf-8 -*-
"""
Created on Wed May 23 16:51:45 2018

@author: wmd22

A few functions for quick calculation ofs MPE's
"""
from __future__ import division

from past.utils import old_div
import matplotlib
#%matplotlib inline
import matplotlib.pyplot as plt
import numpy as np

#,average_power, rep_rate = 80E6,
def single_pulse_MPE(wavelength,pulse_width = 100E-15,divergence = 1.1):
    """ A single pulse MPE calculator for pulsed systems, units are nm,t, and mrad
    Currently only works for 100fs to 10 ps pulses or ms->seconds of exposure"""
    if wavelength>400 and wavelength<450:
        c3 = 1
    elif wavelength > 450 and wavelength<600:
        c3 = 10.0**(0.02*(wavelength-450))
    elif wavelength>700 and wavelength<1050:
        c4 = 10.0**(0.002*(wavelength-700))
    elif wavelength>1050 and wavelength<1400:
        c4 = 5
    if wavelength>400 and wavelength<1400:
        if divergence<1.5:
            c6 = 1
            T2 = 10
        elif divergence>1.5 and divergence<100:
            c6 = divergence/1.5
            T2 = 10*10**((divergence-1.5)/98.5)
        elif divergence>100.0:
            c6 = 100.0/1.5
            T2 = 100.0 
    if wavelength>1050 and wavelength<=1150:
        c7 = 1
    if wavelength>1150 and wavelength<=1200:
        c7 = 10.0**(0.018*(wavelength-1150))
    if wavelength>1200 and wavelength <=1400:
        c7 = 8
        
    if pulse_width>99E-15 and pulse_width<10E-11:
        if wavelength>400 and wavelength<=700:
            return 1.5E-4*c6
        if wavelength>700 and wavelength<=1050:
            return 1.5E-4*c4*c6
        if wavelength>1050 and wavelength<=1400:
            return 1.5E-3*c6*c7
        if wavelength>1400 and wavelength<=1500:
            return 1E12*pulse_width
        if wavelength>1500 and wavelength<=1800:
            return 1E13*pulse_width
        if wavelength>1800 and wavelength<=2600:
            return 1E12*pulse_width
        if wavelength>2600:
            return 1E11*pulse_width
    if pulse_width>=1E-3 and pulse_width<=10:
        if wavelength>400 and wavelength<=700:
            return 18*pulse_width**0.75*c6
        if wavelength>700 and wavelength<=1050:
            return 18*pulse_width**0.75*c6*c4
        if wavelength>1050 and wavelength<=1400:
            return 90.0*pulse_width**0.75*c6*c7
        if wavelength>1400 and wavelength<=1500:
            return 5600*pulse_width**0.25
        if wavelength>1500 and wavelength<=1800:
            return 10**4
        if wavelength>1800 and wavelength<=2600:
            return 5600*pulse_width**0.25   
        if wavelength>2600:
            return 5600*pulse_width**0.25          
        
def power_at_dist(power,distance):
    '''power at a distance from a scattering point '''
    surface_area = 2.0*np.pi*distance**2
    return old_div(power,surface_area)

def calculate_MPEs(wavelength,pulse_width = 100E-15,divergence = 1.1,frequency = 80E6):
    '''Calculate the Three different MPE's required for pulsed lasers'''
    mpe_single = single_pulse_MPE(wavelength,pulse_width,divergence)
    if wavelength>=400 and wavelength<=700:
        mpe_average = single_pulse_MPE(wavelength,0.25,divergence)
        num_pulses = (0.25*frequency)
        mpe_average=old_div(mpe_average,num_pulses)
    else:
        mpe_average = single_pulse_MPE(wavelength,10.0,divergence)
        num_pulses= (10*frequency)
        mpe_average = old_div(mpe_average,num_pulses)
    mpe_train = mpe_single*num_pulses**(-0.25)
    return np.array((mpe_single, mpe_average, mpe_train))*frequency
           
        
            
    