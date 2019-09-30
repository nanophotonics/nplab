# -*- coding: utf-8 -*-
"""
Created on Mon Jul 15 11:50:45 2019

@author: Eoin Elliott
"""


import re
import os
import h5py
import numpy as np
import scipy 
import conversions as cnv
from lmfit import Minimizer
from nplab.analysis import Adaptive_Polynomial as AP
from nplab.analysis import Auto_Fit_Raman as AFR
import matplotlib.pyplot as plt
from nplab.analysis import smoothing as sm





def findH5File(rootDir, mostRecent = True, nameFormat = 'date'):
    '''
    Finds either oldest or most recent .h5 file in a folder containing specified string
    '''

    os.chdir(rootDir)

    if mostRecent == True:
        n = -1

    else:
        n = 0

    if nameFormat == 'date':

        if mostRecent == True:
            print 'Searching for most recent instance of yyyy-mm-dd.h5 or similar...'

        else:
            print 'Searching for oldest instance of yyyy-mm-dd.h5 or similar...'

        h5File = sorted([i for i in os.listdir('.') if re.match('\d\d\d\d-[01]\d-[0123]\d', i[:10])
                         and (i.endswith('.h5') or i.endswith('.hdf5'))],
                        key = lambda i: os.path.getmtime(i))[n]

    else:

        if mostRecent == True:
            print 'Searching for most recent instance of %s.h5 or similar...' % nameFormat

        else:
            print 'Searching for oldest instance of %s.h5 or similar...' % nameFormat

        h5File = sorted([i for i in os.listdir('.') if i.startswith(nameFormat)
                         and (i.endswith('.h5') or i.endswith('.hdf5'))],
                        key = lambda i: os.path.getmtime(i))[n]

    print '\tH5 file %s found\n' % h5File

    return h5File

def truncate(counts, wavelengths, lower_cutoff, upper_cutoff, return_indices_only = False):
    l = 0
    for index, wl in enumerate(wavelengths):
        if wl>=lower_cutoff:
            
            l = index
            break
        
    u = False
    for index, wl in enumerate(wavelengths[l:]):
        if wl>= upper_cutoff:
            u=index+l
            break
    if return_indices_only == False:
        if u == False:
            return counts[l:], wavelengths[l:]
        else:
            return counts[l:u], wavelengths[l:u]
    else:
        return l,u
def find_closest(value_to_match, array):
    '''Taking an input value and array, it searches for the value and index in the array which is closest to the input value '''
    residual = []
    for value in array:
        residual.append(np.absolute(value-value_to_match))
        
    return array[np.argmin(residual)], np.argmin(residual), min(residual) # value, index, residual
def stokesratio(Stokes_counts, antiStokes_counts, shift, laser_wavelength = 785.):#returns T, shift is in cm-1
    #omega is the raman shift in omega. 
    omega = cnv.cm_to_omega(shift)
    
    omega_AS = omega +cnv.simple_wavelength_to_omega(laser_wavelength)
    omega_S = cnv.simple_wavelength_to_omega(laser_wavelength)-omega
    logarg = (np.array(Stokes_counts)/np.array(antiStokes_counts))*(omega_AS/omega_S)**4
    T = scipy.constants.hbar*omega/(scipy.constants.k*np.log(logarg))
    return T        
            
def condenseZscan(zScan, normalised = True):    
    #
    bg = zScan.attrs['background']
    ref = zScan.attrs['reference']
    refdsubdzscan = np.zeros(np.shape(zScan))
    for index,z in enumerate(zScan):
        refdsubdzscan[index] = np.true_divide(z-bg,ref-bg)
    output = np.array([scan.max() for scan in np.transpose(refdsubdzscan)])
    if normalised == True: output = output/(float(max(output[len(output)/3:2*len(output)/3])))
    return output
 
def remove_cosmic_rays_from_Raman(counts, threshold = 2):
    removed_ray = False
    Range = range(len(counts))
    del Range[0]
    del Range[0]
    del Range[0]
    
    del Range[-1]
    del Range[-1]
    del Range[-1]
    
    
    
    for i in Range:
        if counts[i]>threshold*np.mean([counts[i-2], counts[i-3], counts[i+2],counts[i+3]]):
            counts[i] = np.mean([counts[i-2], counts[i-3], counts[i+2],counts[i+3]])
            
            removed_ray = True
    return counts, removed_ray    
class exponential: # work in omega, simple exponential
    def __init__(self, input_params):
        self.initial_params = input_params
    def function(self, params, omega): 
        A = params['A']
        T = params['T']
        bg = params['bg']
        return A*np.exp((-scipy.constants.hbar/scipy.constants.k)*omega/T)+bg
    def objective(self, params, omega, counts): 
        return counts - self.function(params, omega)
    def fit_to_spectrum(self, counts, omega):
        minner = Minimizer(self.objective, self.initial_params, fcn_args=(omega, counts))
        result = minner.minimize()
        self.fitted_params = result.params

class exponential2: # work in omega, more complicated exponential
    def __init__(self, input_params):
        self.initial_params = input_params
    def function(self, params, omega): 
        A = params['A']
        T = params['T']
        bg = params['bg']
        return A*(np.exp((scipy.constants.hbar/scipy.constants.k)*omega/T) -1)**-1 +bg
    def objective(self, params, omega, counts): 
        return counts - self.function(params, omega)
    def fit_to_spectrum(self, counts, omega):
        minner = Minimizer(self.objective, self.initial_params, fcn_args=(omega, counts))
        result = minner.minimize()
        self.fitted_params = result.params
        #self.errors = {'A':result.params['A'].stderr, 'T':result.params['T'].stderr, 'bg':result.params['bg'].stderr}

class exponential3: # work in omega, more complicated exponential
    def __init__(self, input_params):
        self.initial_params = input_params
    def function(self, params, omega): 
        A = params['A']
        T = params['T']
        bg = params['bg']
        return A*((np.exp((scipy.constants.hbar/scipy.constants.k)*omega/T) -1)**-1 + (np.exp((scipy.constants.hbar/scipy.constants.k)*omega/292) -1)**-1)+bg
    def objective(self, params, omega, counts): 
        return counts - self.function(params, omega)
    def fit_to_spectrum(self, counts, omega):
        minner = Minimizer(self.objective, self.initial_params, fcn_args=(omega, counts))
        result = minner.minimize()
        self.fitted_params = result.params
        #self.errors = {'A':result.params['A'].stderr, 'T':result.params['T'].stderr, 'bg':result.params['bg'].stderr



def get_laser_power_from_leak(power_series, shifts):
    extracted_powers = []
    for spectrum in power_series:
        cut = truncate(spectrum, shifts, -15, 15)[0]
        cut =  AP.Run(cut, 1, Auto_Remove = True)
        extracted_powers.append(np.sum(cut))
    return extracted_powers
def get_peak_heights(counts, wavelengths, shift, Range=4., return_wavelength = False, antiStokes = True, inputcm = False): # shift is in cm-1, range is in nm
    
    if inputcm==False:    
        S_nm = cnv.cm_to_wavelength(-shift, centre_wl = 785.)
        S_group, S_group_wl = truncate(counts, wavelengths, S_nm-(Range/2), S_nm+(Range)/2)
    else:
        S_group, S_group_wl = truncate(counts, wavelengths, shift-(Range/2), shift+(Range)/2)
    
    S = max(S_group)
    s = np.argmax(S_group)
    S_wl = S_group_wl[s] # wl may also be shift if the input is shift
    
    if antiStokes ==True:
        if inputcm==False: 
            
            AS_nm = cnv.cm_to_wavelength(shift, centre_wl = 785.)
            AS_group, AS_group_wl = truncate(counts, wavelengths, AS_nm-Range/2, AS_nm+Range/2)
        else:
            AS_group, AS_group_wl = truncate(counts, wavelengths, -shift-Range/2, -shift+Range/2)
    
    
        AS = max(AS_group)
        a_s = np.argmax(AS_group)
        AS_wl = AS_group_wl[a_s]
        if return_wavelength == True:
            return S, AS, S_wl, AS_wl
        else:
            return S, AS
    else:
        if return_wavelength ==True:
            return S, S_wl
        else:
            return S


def calibrate_Si(counts, wavelengths, shift=520, centre_wl = 785.):
    try:
        os.remove("Si_calibration.txt")
    except:
        Dump = 1
    S_wl, AS_wl = get_peak_heights(counts, wavelengths, shift, Range = 50, return_wavelength = True)[2:4]
    S_factor = (cnv.cm_to_wavelength(-shift, centre_wl = centre_wl)-centre_wl)/(S_wl-centre_wl)
    AS_factor = (cnv.cm_to_wavelength(shift, centre_wl = centre_wl)-centre_wl)/(AS_wl-centre_wl)    
    doc= open("Si_calibration.txt","w+")
    doc.write(str(S_factor))
    doc.write('\t')
    doc.write(str(AS_factor))
    doc.close()
    S = truncate(counts, wavelengths, centre_wl, 1000)[1]
    AS = truncate(counts, wavelengths, 0 , centre_wl)[1]
    S_new = np.add(S, -centre_wl)*S_factor + centre_wl
    AS_new = np.add(AS, -centre_wl)*AS_factor +centre_wl
    new_wavelengths = np.append(AS_new, S_new)
    if len(new_wavelengths)!= len(wavelengths):
        print 'error'
        print len(new_wavelengths), len(wavelengths)
        
    return new_wavelengths  

def transmission_function(S_fit, AS_fit):
  
    print r'C:\Users\Eoin Elliott\Documents\GitHub\nplab\nplab\calibration\Lab 5' 
    OO_wl = np.transpose(np.loadtxt(r'C:\Users\Eoin Elliott\Documents\GitHub\nplab\nplab\calibration\Lab 5\Ocean_Optics_halogen_and_xenon.txt' ))[0]
    OO_halogen = np.transpose(np.loadtxt(r'C:\Users\Eoin Elliott\Documents\GitHub\nplab\nplab\calibration\Lab 5\Ocean_Optics_halogen_and_xenon.txt' ))[1]
    OO_xenon = np.transpose(np.loadtxt(r'C:\Users\Eoin Elliott\Documents\GitHub\nplab\nplab\calibration\Lab 5\Ocean_Optics_halogen_and_xenon.txt' ))[2]
    xenon_reference = np.transpose(np.loadtxt(r'C:\Users\Eoin Elliott\Documents\GitHub\nplab\nplab\calibration\Lab 5\Ocean_Optics_halogen_and_xenon.txt' ))[1]
    xenon_wl = np.transpose(np.loadtxt(r'C:\Users\Eoin Elliott\Documents\GitHub\nplab\nplab\calibration\Lab 5\Ocean_Optics_halogen_and_xenon.txt' ))[0]
    OO_halogen = sm.convex_smooth(OO_halogen,10, normalise = False)[0]
    OO_xenon = sm.convex_smooth(OO_xenon,10, normalise = False)[0]
    andor_wl = np.transpose(np.loadtxt(r'C:\Users\Eoin Elliott\Documents\GitHub\nplab\nplab\calibration\Lab 5\100x_09_NA_600lmm_800nm_5050bs.txt' ))[0][::-1]
    andor_halogen = np.transpose(np.loadtxt(r'C:\Users\Eoin Elliott\Documents\GitHub\nplab\nplab\calibration\Lab 5\100x_09_NA_600lmm_800nm_5050bs.txt' ))[1][::-1]
    
    andor_halogen = sm.convex_smooth(andor_halogen,10, normalise = True)[0]

    
    andor_wl = -cnv.wavelength_to_cm(andor_wl, centre_wl = 785)
    
    S_andor_halogen, S_andor_wl = truncate(andor_halogen, andor_wl, 0, np.inf)
    AS_andor_halogen, AS_andor_wl = truncate(andor_halogen, andor_wl, -np.inf, 0)
    andor_halogen = np.append(AS_andor_halogen, S_andor_halogen)
    
    S_andor_wl = np.polyval(S_fit, S_andor_wl)
    AS_andor_wl = np.polyval(AS_fit, AS_andor_wl)
    andor_cm = np.append(AS_andor_wl, S_andor_wl)
    andor_wl = cnv.cm_to_wavelength(-andor_cm, centre_wl = 785)
    

    OO_halogen = scipy.interpolate.interp1d(OO_wl, OO_halogen)(andor_wl)
    OO_xenon = scipy.interpolate.interp1d(OO_wl, OO_xenon)(andor_wl)
    xenon_reference = scipy.interpolate.interp1d(xenon_wl, xenon_reference)(andor_wl)
    T = OO_xenon*andor_halogen/OO_halogen*xenon_reference
    
    
    
    plt.figure('Transmission_functions')
    plt.plot(andor_wl, OO_xenon/float(max(OO_xenon)), label = 'OO_xenon')
    plt.plot(andor_wl, andor_halogen/float(max(andor_halogen)), label = 'andor_halogen')
    plt.plot(andor_wl, OO_halogen/float(max(OO_halogen)), label = 'OO_halogen')
    plt.plot(andor_wl, xenon_reference/float(max(xenon_reference)), label = 'xenon_reference')
    plt.plot(andor_wl, T/float(max(T)), label = 'transmission')
    plt.legend()
    plt.savefig(r'C:\Users\Eoin Elliott\Documents\GitHub\nplab\nplab\calibration\Lab 5\Transmission_function')
    T_tuple = np.append([andor_wl], [T], axis = 0)
    np.savetxt(r'C:\Users\Eoin Elliott\Documents\GitHub\nplab\nplab\calibration\Lab 5\Transmission_function_100x_09_NA_600lmm_800nm_5050bs.txt',T_tuple)
    return T/max(T), andor_cm       





if __name__ =='__main__':
    os.chdir(r'R:\ee306\Experimental data\2019.08.04 Two temperature measurements with 785nm')
    File = h5py.File(findH5File(os.getcwd()), mode = 'r')
    power_series = spec = File['Particle_4']['Power_Series']
    spec = power_series[-1]
    wavelengths = power_series.attrs['wavelengths']
    notch = 230.

    