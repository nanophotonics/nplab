# -*- coding: utf-8 -*-
"""
Created on Thu Feb 01 13:21:40 2018

@author: Charlie Readman
"""
if __name__ == '__main__':   
    print 'Importing modules...'

import h5py
import numpy as np
import os
import matplotlib.pyplot as plt
from scipy import sparse
import scipy.sparse.linalg as splu
from scipy.signal import butter, filtfilt
from lmfit.models import GaussianModel
import time
from PIL import Image
from scipy.stats.kde import gaussian_kde

if __name__ == '__main__':
    absolute_start_time = time.time()
    print 'Modules imported\n'
    print 'Initialising functions...'

class DF_Spectrum(object):
    
    def __init__(self, intensities, fit_params, is_NPoM, is_double, cm_peakpos, metadata):
        self.intensities = intensities #y data (1D array)
        self.fit_params = fit_params #parameters that describe the multiple gaussians that make up each spectrum (dictionary)
        self.is_NPoM = is_NPoM #Whether or not the spectrum describes an NPoM (bool)
        self.is_double = is_double #Whether or not the spectrum contains a double coupled mode (bool)
        self.cm_peakpos = cm_peakpos #What it says on the tin (float)
        self.metadata = metadata #All other relevant info (dictionary)

def find_key(input_dict, value):
    return next((k for k, v in input_dict.items() if v == value), None)

def remove_NaNs(spectrum):  
    #Identifies NaN values and sets the corresponding data point as an average of the two either side
    #If multiple sequential NaN values are encountered a straight line is made between the two closest data points
    #Input = 1D array
    #Works like list.sort() rather than sorted(list), i.e. manipulates array directly rather than returning a new one
      
    i = -1
    
    if not np.isfinite(spectrum[i]) == True:

        while not np.isfinite(spectrum[i]) == True:
            i -= 1

        for j in range(len(spectrum[i:])):
            spectrum[i+j] = spectrum[i]

    for i in range(len(spectrum)):

        if not np.isfinite(spectrum[i]) == True:

            if i == 0:
                j = i

                while not np.isfinite(spectrum[j]) == True:
                    j += 1
    
                for k in range(len(spectrum[i:j])):
                    spectrum[i+k] = spectrum[j]

            elif i != len(spectrum) - 1:
                j = i

                while not np.isfinite(spectrum[j]) == True:
                    j += 1

                start = spectrum[i-1]
                end = spectrum[j]
                diff = end - start

                for k in range(len(spectrum[i:j])):
                    spectrum[i+k] = float(start) + float(k)*float(diff)/(len(spectrum[i:j]))

def correct_spectrum(spectrum, reference): 
    #Removes any NaNs from all spectra in list and divides each by a 1D array of the same length (designed for referencing)
    #spectra = list of arrays, 2D array with size (n, 1)
    #reference = 1D array
    
    for n in range(len(reference)):
        
        if reference[n] == 0.:
            reference[n] = np.nan
    
    remove_NaNs(reference)
    return spectrum/reference

def truncate_spectrum(wavelengths, spectrum, start_wl = 450, finish_wl = 900):
    #Truncates spectra to remove high and low end noise

    for n, wl in enumerate(wavelengths):
        
        if n == 0 and wl > start_wl:
            start_index = n
                    
        if int(np.round(wl)) == int(np.round(start_wl)):
            start_index = n
            
        elif int(np.round(wl)) == int(np.round(finish_wl)):
            finish_index = n
        
        elif n == len(wavelengths) - 1 and wl < finish_wl:
            finish_index = n

    wavelengths_trunc = np.array(wavelengths[start_index:finish_index])
    spectrum_trunc = np.array(spectrum[start_index:finish_index])
    return np.array([wavelengths_trunc, spectrum_trunc])

def baseline_als(y, lambd, p, iterations = 10):#Calculates baseline for data
    L = y.size
    D = sparse.csc_matrix(np.diff(np.eye(L), 2))
    w = np.ones(L)
    for i in xrange(iterations):
        W = sparse.spdiags(w, 0, L, L)
        Z = W + lambd * D.dot(D.transpose())
        z = splu.spsolve(Z, w*y)
        w = p * (y > z) + (1-p) * (y < z)
    return z

#def butter_lowpass(cutoff, fs, order=5):
#    nyq = 0.5 * fs
#    normal_cutoff = cutoff / nyq
#    b, a = butter(order, normal_cutoff, btype='low', analog=False)
#    return b, a

def butter_lowpass_filtfilt(data, cutoff = 1500, fs = 60000, order=5):#Smooths data without shifting it
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    y_filtered = filtfilt(b, a, data)
    return y_filtered

def detect_minima(y, neg_only = True, threshold = 0):
    ind = False
    #Finds and returns list of minima in a data set
    y_sign = np.sign(y + threshold)
    #print 'y sign:'
    #print y_sign
    dy = np.zeros(len(y))
    #print 'len(y)', len(y)
    dy[1:] = np.diff(y)
    #print 'len(np.diff(y))', len(np.diff(y))
    #print 'len(dy)', len(dy)
    
    if len(dy) > 1:
        dy[0] = dy[1]
        dy = np.sign(dy)
        #print 'dy:'
        #print dy
        d2y = np.zeros(len(y))
        d2y[1:] = np.diff(dy)
        d2y[0] = d2y[1]
        d2y = np.sign(d2y)
        #print 'd2y:'
        #print d2y
    
        if neg_only == True: #Finds only minima that exist below zero
            ind = np.nonzero((-y_sign + dy + d2y) == 3)
            ind = ind[0]
            ind = [int(i) for i in ind]

        elif neg_only == False:#Finds all minima
            ind = np.nonzero((dy + d2y) == 2)
            ind = ind[0]
            ind = [int(i) for i in ind]

        return ind

def test_if_NPoM(y, lower = 0.1, upper = 2, NPoM_threshold = 1.5): 
    #Filters out spectra that are obviously not from NPoMs

    if np.sum(y) > lower and np.sum(y) < upper:
        #If sum of all intensities lies outside a given range, it's probably not an NPoM
        #Can adjust range to suit system
        first_half = y[:int(len(y)/2)]
        second_half = y[int(len(y)/2):]
    
        #print np.sum(y)

        if np.sum(first_half) < np.sum(second_half) * NPoM_threshold:
            #NPoM spectra generally have greater total signal at longer wavelengths due to coupled mode
            is_NPoM = True

        else:
            is_NPoM = False
    else:
        is_NPoM = False
    
    #print np.sum(first_half), np.sum(second_half)
    return is_NPoM
  
def take_derivs(y, x):
    #numerically differentiates y wrt x twice and returns both derivatives
    #y, x = 1D array
    
    dy = np.diff(y)
    dx = np.diff(x)
    first_derivative = dy/dx
        
    d_dy_dx = np.diff(first_derivative)
    
    second_derivative = d_dy_dx/dx[:-1]
    
    return first_derivative, second_derivative

def remove_baseline(x, y, cutoff = 1500, fs = 60000, lambd = 10**6.7, p = 0.003, return_trunc = False):
    x_raw = x
    y_raw = y
        
    x_trunc1, y_trunc1 = truncate_spectrum(x_raw, y_raw, start_wl = 450, finish_wl = 1000) #Truncate to remove low-end noise
    y_trunc1_smooth = butter_lowpass_filtfilt(y_trunc1, cutoff, fs) #Smooth truncated data
    y_trunc1_minima = detect_minima(y_trunc1_smooth, neg_only = False) #Finds indices of minima in smoothed data
    
    init_min_index = y_trunc1_minima[0] #Index of first minimum in truncated spectrum
    init_wl = x_trunc1[init_min_index] #Wavelength corresponding to this minimum
    init_min_index = np.where(x_raw == init_wl)[0][0] #Corresponding index in full spectrum
    
    x_trunc2, y_trunc2 = truncate_spectrum(x_raw, y_raw, start_wl = 800, finish_wl = 1000) #Truncate to only probe data after CM peak        
    y_trunc2_smooth = butter_lowpass_filtfilt(y_trunc2, cutoff, fs) #Smooth truncated data
    y_trunc2_minima = detect_minima(y_trunc2_smooth, neg_only = False) #Finds indices of minima in smoothed data

    final_min_index = y_trunc2_minima[0] #Index of first minimum after CM peak
    final_wl = x_trunc2[final_min_index] #Wavelength corresponding to this minimum
    final_min_index = np.where(x_raw == final_wl)[0][0] #Corresponding index in full spectrum
    
    '''These two minima are taken as the start and end points of the "real" spectrum'''

    x_trunc3, y_trunc3 = truncate_spectrum(x_raw, y_raw, start_wl = init_wl, finish_wl = final_wl) #Truncate spectrum between two minima
    y_trunc3_baseline = baseline_als(y_trunc3, lambd, p) #Take baseline of this data
    y_trunc3_subtracted = y_trunc3 - y_trunc3_baseline
    
    '''Baseline extrapolated with straight line at each end so it can be subtracted from the raw spectrum'''

    y_baseline_1 = [y_trunc3_baseline[0]] * init_min_index
    y_baseline_2 = [i for i in y_trunc3_baseline]
    y_baseline_3 = [y_trunc3_baseline[-1]] * (len(y_raw) - final_min_index)

    y_full_baseline = y_baseline_1 + y_baseline_2 + y_baseline_3

    '''Due to rounding errors when truncating, extrapolated baseline may have different length to raw data '''
    
    len_diff = len(y_raw) - len(y_full_baseline) #Calculate this difference

    if len_diff < 0:
        y_full_baseline = y_full_baseline[:len_diff] #Remove data point(s) from end if necessary

    elif len_diff > 0:

        for j in range(len_diff):
            y_full_baseline.append(y_trunc3_baseline[-1]) #Add data point(s) to end if necessary

    y_full_baseline = np.array(y_full_baseline)
    y_subtracted = y_raw - y_full_baseline #Subtract baseline from raw data

    '''Baseline calculation isn't perfect, so this subtraction sometimes leads to unrealistically negative y-values'''
    '''Data truncated and smoothed once more, and minimum subtracted from data'''
    
    subtracted_trunc = truncate_spectrum(x_raw, y_subtracted, start_wl = 450, finish_wl = 850)
    x_sub_trunc, y_sub_trunc = subtracted_trunc[0], subtracted_trunc[1]
    y_sub_trunc_smooth = butter_lowpass_filtfilt(y_sub_trunc, cutoff, fs)

    y_subtracted -= y_sub_trunc_smooth.min()

    if return_trunc == True:
        return y_subtracted, x_trunc3, y_trunc3_subtracted
    
    else:  
        return y_subtracted

def norm_to_trans(x, y, cutoff = 1500, fs = 60000, lambd = 10**6.7, p = 0.003, plot = False, monitor_progress = False, baseline = True, return_peakpos = True):

    x_raw = x
    y_raw = y
    
    if baseline == True:
        y_subtracted, x_trunc, y_trunc = remove_baseline(x_raw, y_raw, lambd = lambd, p = p, return_trunc = True)

    else:
        x_trunc, y_trunc = truncate_spectrum(x_raw, y_raw, start_wl = 450, finish_wl = 900)
    
    y_trunc_smooth = butter_lowpass_filtfilt(y_trunc, cutoff = cutoff, fs = fs)
    first_deriv, second_deriv = take_derivs(y_trunc_smooth, x_trunc)
    
    peak_indices = detect_minima(second_deriv, neg_only = False)
    
    x_peaks = [x_trunc[index] for index in peak_indices]
    
    for n, peak_wl in enumerate(x_peaks):
        
        if peak_wl > 500:
            trans_index = peak_indices[n]
            break

    trans_wl = x_trunc[trans_index]
    trans_height = y_trunc_smooth[trans_index]

    if baseline == False:
        y_subtracted = y_raw - min(y_trunc_smooth)
        y_trunc = y_trunc - min(y_trunc_smooth)
    
    y_norm = y_subtracted / trans_height
    y_trunc_norm = y_trunc / trans_height

    if return_peakpos == True:
        return y_norm, trans_wl, x_trunc, y_trunc_norm   
    
    else:
        return y_norm, x_trunc, y_trunc_norm

def test_if_double(x, best_fit, final_params, doubles_threshold = 0.5, min_dist = 30, monitor_progress = False, plot = False, return_heights_and_centers = True):

    '''Decides if DF spectrum contains two coupled modes. Requires fitting beforehand. Sloppy but gets the job done.
    May tidy up later'''
    
    #x = 1D array
    #best_fit = final result of curve fitting
    #final_params = dictionary of parameters that describe the multiple gaussians that make up each spectrum, as returned by find_fit_peaks (see below)
    #doubles_threshold = minimum size ratio required to classify a double resonance
    
    is_double = False #Innocent until proven guilty
    heights = [] #List to be populated with peak heights
    centers = [] #List to be populated with peak positions
    component_numbers = []

    for n in range(len(final_params)):

        if final_params['g%s' % (n)]['center'] > 600: #Excludes tranverse peak
            heights.append(final_params['g%s' % (n)]['height']) #Populates list of heights
            centers.append(final_params['g%s' % (n)]['center'])
            component_numbers.append(n)

    heights_sorted = sorted(heights)
    #print 'heights_sorted', heights_sorted
    centers_sorted = [c for _,c in sorted(zip(heights, centers))]
    #print 'centers_sorted', centers_sorted
    component_numbers_sorted = [index_i for _,index_i in sorted(zip(heights, component_numbers))]

    #fitted_data = out.best_fit
    #main_peak_position = np.argmax(out.best_fit)

    peak_1_index = 0
    peak_2_index = 0

    if len(centers_sorted) > 1:
        #Only performs the analysis if more than 1 peak exists
        #print [x[n] for n in range(len(x))]
        #print [abc for abc in centers_sorted]

        for n in range(len(x)):

            if int(x[n]) == int(centers_sorted[-1]):
                #print 'int(x[n])', int(x[n])
                #print 'int(centers_sorted[-1])', int(centers_sorted[-1])
                #print 'n =', n
                peak_1_index = n

            if int(x[n]) == int(centers_sorted[-2]):
                peak_2_index = n

            if peak_1_index != 0 and peak_2_index != 0:
                break

        if peak_1_index == 0 or peak_1_index == 0:
            is_NPoM = False

        else:
            is_NPoM = True

        if peak_1_index > peak_2_index:
            x_CM = x[peak_2_index:peak_1_index]
            y_CM = best_fit[peak_2_index:peak_1_index]

        else:
            x_CM = x[peak_1_index:peak_2_index]
            y_CM = best_fit[peak_1_index:peak_2_index]

        if monitor_progress == True and plot == 'all':
            print 'Region between maxima:'
            plt.plot(x_CM, y_CM)
            plt.show()

        #else:
        #    split_peak = False

        if len(heights) > 1:

            if heights_sorted[-1] * doubles_threshold < heights_sorted[-2]:
                #if height of second largest peak > largest peak x chosen threshold,
                
                if monitor_progress == True:
                    print '\tSecond peak is bigger than %s times the size of the largest' % doubles_threshold
                
                if abs(centers_sorted[-1] - centers_sorted[-2]) > min_dist:
                    #AND peaks are more than a certain distance apart,
                                        
                    #snip_length = int(np.round(len(y_CM))/7)
                     
                    #x_CM = x_CM[snip_length : -snip_length]
                    #y_CM = y_CM[snip_length : -snip_length]
                    
                    CM_minima_indices = detect_minima(y_CM, neg_only = False)
                        
                    
                    if monitor_progress == True:
                        print '\t peaks are further than %s nm apart' % min_dist
                        print 'Region between maxima:'
                        
                        plt.plot(x_CM, y_CM)
                        plt.show()                        
                    
                    if len(CM_minima_indices) > 0:# and best_fit.max() * doubles_threshold < best_fit[peak_2_index]:
                        #AND a minimum exists between them
                        
                        x_mins = [x_CM[index] for index in CM_minima_indices]
                        y_mins = [y_CM[index] for index in CM_minima_indices]
                        
                        if monitor_progress == True:
                            print 'Minimum exists between peaks'
                            
                            plt.plot(x_CM, y_CM)
                            plt.plot(x_mins, y_mins, 'o')
                            plt.show() 
                        
                        is_double = True #it counts as a double peak
                    
                    else:
                        
                        if monitor_progress == True:
                            print 'No minumum between peaks'
                            is_double = False                    
                    
            else:
                is_double = False

    else:
        is_double = False
            
    if return_heights_and_centers == True:
        return is_double, heights, centers
    
    else:
        return is_double

def find_fit_peaks(x, y, cutoff = 1500, fs = 60000, lambd = 10**6.7, baseline_p = 0.003, detection_threshold = 0, doubles_threshold = 0.5, doubles_dist = 30, constrain_peakpos = False, print_report = False, plot = False, monitor_progress = False):   
    
    y_raw = np.array(y)
    x_raw = np.array(x)
    
    all_metadata_keys = ['NPoM?',
                      'double_peak?',
                      'transverse_mode_position_(init)',
                      'transverse_mode_intensity_(init)',
                      'transverse_mode_position',
                      'transverse_mode_intensity',
                      'coupled_mode_resonance_(fit)',
                      'coupled_mode_intensity_(fit)',
                      'coupled_mode_resonance_(spectrum)',
                      'coupled_mode_height_(spectrum)',
                      'intensity_ratio_2',
                      'intensity_ratio_1',
                      'raw_data',
                      'normalised_spectrum',
                      'full_wavelengths',
                      'full_wavelengths',
                      'truncated_spectrum',
                      'smoothed_spectrum',
                      'initial_guess',
                      'best_fit',
                      'residuals',
                      'final_components',
                      'final_params',                      
                      'truncated_wavelengths',
                      'truncated_wavelengths',
                      'second_derivative']
    
    metadata = {key : 'N/A' for key in all_metadata_keys}
    metadata['raw_data'] = y_raw
    metadata['full_wavelengths'] = x_raw
    
    is_NPoM_start = time.time()
            
    is_NPoM = test_if_NPoM(y_raw)
    
    is_NPoM_end = time.time()
    is_NPoM_time = is_NPoM_end - is_NPoM_start
    
    if monitor_progress == 'time' or monitor_progress == True:
        print 'Tested if NPoM in %s seconds' % is_NPoM_time
    
    if plot == 'raw' or plot == 'all':
        plt.figure(figsize = (10,7))
        y_max = y_raw[67:661].max()
        y_lim_frac = y_max/10
        plt.ylim(-y_lim_frac, y_max + y_lim_frac)
        
        if is_NPoM == True:
            plt.plot(x_raw, y_raw, 'g', label = 'Raw Data')
        
        else:
            plt.plot(x_raw, y_raw, 'r', label = 'Raw Data')
        
        plt.xlim(x_raw.min(), x_raw.max())
        plt.xlabel('Wavelength (nm)')
        plt.ylabel('Scattering Intensity')
        plt.title('Raw Data\nNPoM = %s' % is_NPoM)
        plt.show() 
        
    if monitor_progress == True:
        print 'NPoM:', is_NPoM

    metadata['NPoM?'] = is_NPoM

    if is_NPoM == True:
        
        norm_to_trans_start = time.time()

        y_raw_norm, trans_peakpos, x_trunc, y_trunc = norm_to_trans(x, y, cutoff = cutoff, fs = fs, lambd = lambd, p = baseline_p, plot = False, monitor_progress = False, baseline = True)
        
        norm_to_trans_end = time.time()
        norm_to_trans_time = norm_to_trans_end - norm_to_trans_start
        
        if monitor_progress == 'time' or monitor_progress == True:
            print 'Normalised in %s seconds' % norm_to_trans_time
        
        #print len(y_trunc), len(x_trunc)
        
        trunc_start = time.time()
        
        x_trunc, y_trunc = truncate_spectrum(x_trunc, y_trunc, start_wl = x_trunc[0], finish_wl = 850)
        
        trunc_end = time.time()
        trunc_time = trunc_end - trunc_start
        
        if monitor_progress == 'time' or monitor_progress == True:
            print 'Truncated in %s seconds' % trunc_time
        
        metadata['transverse_mode_position_(init)'] = trans_peakpos
        metadata['normalised_spectrum'] = y_raw_norm
        
        if monitor_progress == True:
            print '\nData baseline subtracted and normalised'
        
        if plot == 'all':
            plt.figure(figsize = (10,7))
            y_max = y_raw_norm[67:661].max()
            y_lim_frac = y_max/10
            plt.ylim(-0.02, y_max + y_lim_frac)
            plt.plot(x_raw, y_raw_norm, 'purple')
            plt.xlim(x_raw.min(), x_raw.max())
            plt.xlabel('Wavelength (nm)')
            plt.ylabel('Scattering Intensity')
            plt.title('Baselined/Normalised Data')
            plt.show()
        
        y_smooth = butter_lowpass_filtfilt(y_trunc, cutoff = cutoff, fs = fs)
        y = y_trunc
        x = x_trunc
        
        metadata['smoothed_spectrum'] = y_smooth
        metadata['truncated_spectrum'] = y_trunc
        metadata['truncated_wavelengths'] = x_trunc
        
        if monitor_progress == True:
            print '\nData smoothed'

        #Differentiation
        
        deriv_start = time.time()

        first_derivative, second_derivative = take_derivs(y_smooth, x)
        
        deriv_end = time.time()
        deriv_time = deriv_end - deriv_start
        
        if monitor_progress == 'time' or monitor_progress == True:
            print 'Differentiated in %s seconds' % deriv_time

        metadata['second_derivative'] = second_derivative

        if monitor_progress == True:
            print 'Derivatives taken'

        #Peak detection in 2nd derivative:
            
        detect_minima_start = time.time()

        indices = detect_minima(second_derivative, neg_only = True, threshold = second_derivative.max()*detection_threshold)
        
        detect_minima_end = time.time()
        
        detect_minima_time = detect_minima_end - detect_minima_start
        
        if monitor_progress == 'time' or monitor_progress == True:
            print 'Minima detected in %s seconds' % detect_minima_time
        
        if monitor_progress == True:
            print '%s peaks detected' % (len(indices))

        if plot == 'derivatives' or plot == 'both' or plot == 'all':
            y_smooth_norm = np.array((y_smooth-y_smooth.min())/y_smooth.max() - 0.5)
            first_derivative_norm = np.array(first_derivative)
            #first_derivative_norm -= first_derivative_norm.min()
            first_derivative_norm /= first_derivative_norm.max()
            #first_derivative_norm -= 0.5
            second_derivative_norm = np.array(second_derivative)
            second_derivative_norm /= second_derivative_norm.max()

            plt.figure(figsize = (10, 7))
            #plt.plot(x, y0, 'k--', label = 'y=0')
            #plt.plot(x, y0 + 1, 'k--')
            #plt.plot(x, y0 + 2, 'k--')
            #plt.plot(x, y0 + 3, 'k--')
            plt.plot(x, y_smooth_norm, label = 'Smoothed Data')
            plt.plot(x[:-1], first_derivative_norm + 1, label = 'First Derivative')
            plt.plot(x[1:-1], second_derivative_norm + 2, label = 'Second Derivative')
            plt.plot(x[indices], second_derivative_norm[indices] + 2, 'ko')
            plt.xlim(450, 900)
            plt.legend(loc = 0)
            plt.tick_params(axis = 'y', labelleft = 'off')
            plt.show()

        '''Next bit performs the actual fitting'''
    
        if len(indices) != 0: #If peaks exist
            
            fit_start = time.time() 
              
            if monitor_progress == True:
                print '\n%s peaks about to be fitted' % (len(indices))
            
            model_elements = [] #Empty list to be populated with components of model
            component = GaussianModel(prefix = 'g0_')
            component.set_param_hint('amplitude', min = 0)
            component.set_param_hint('center', min = x.min(), max = 850) #Above 850 is v. noisy, so NO PEAKS ALLOWED
            model_elements.append(component) #One gaussian added for starters

            if len(indices) == 1: #If only one peak detected
                pars = model_elements[0].guess(y_smooth, x = x) #initial parameter guess based on entire spectrum
                gauss_model = model_elements[0] #total model set equal to gaussian component

            else: #If more than one peak detected
                #Sets initial guess data range for first peak
                peak_end = int((indices[0] + indices[1])/2) #Midpoint between 1st and 2nd peak taken as end of data range for 1st peak
                pars = model_elements[0].guess(y_smooth[:peak_end], x[:peak_end]) #initial guess performed within this range
                gauss_model = model_elements[0] #total model initially set equal to first gaussian component

                if constrain_peakpos == True:
                    model_elements[0].set_param_hint('center', max = x[peak_end])

                for i in range(len(indices))[1:]:
                    component = GaussianModel(prefix = 'g%s_' % (i))
                    component.set_param_hint('amplitude', min = 0)
                    component.set_param_hint('center', min = x.min(), max = 850) #Above 850 is v. noisy, so NO PEAKS ALLOWED
                    model_elements.append(component) #Components list populated with appropriate number of gaussians to be calculated

                    if i > 0 and i != len(indices) - 1: #Sets initial guess data range for subsequent peaks
                        peak_start = int((indices[i - 1] + indices[i])/2)
                        peak_end = int((indices[i] + indices[i + 1])/2)

                    elif i > 0 and i == len(indices) - 1: #Sets initial guess data range for final peak
                        peak_start = int((indices[i - 1] + indices[i])/2)
                        peak_end = len(x)

                    if constrain_peakpos == True:
                        model_elements[i].set_param_hint('center', min = x[peak_start + 1], max = x[peak_end - 1])

                    pars.update(model_elements[i].guess(y_smooth[peak_start:peak_end], x[peak_start:peak_end]))#List of parameters updated with initial guesses for each peak
                    gauss_model += model_elements[i]#Total model updated to include each subsequent peak

            if monitor_progress == True:
                print 'Initial guesses made for %s gaussians' % (len(indices))

            init = gauss_model.eval(pars, x=x)#Function formed from initial guesses
            
            metadata['initial_guess'] = init
            
            y_float16 = np.float16(y)
            x_float16 = np.float16(x)
                                      
            out = gauss_model.fit(y_float16, pars, x=x_float16)#Performs the fit, based on initial guesses
            #out = gauss_model.fit(y_smooth, pars, x=x)#Fit to smoothed data
            comps = out.eval_components(x=x_float16)
            metadata['final_components'] = comps
            
            fit_end = time.time()
            fit_time = fit_end - fit_start
            
            if monitor_progress == 'time' or monitor_progress == True:
                print '\n\nFit performed in %s seconds' % fit_time
            
            if monitor_progress == True:
                print '%s components' % len(comps)
                print '\nFit performed'
            
            final_params = {}
            component_param_names = ['sigma', 'center', 'amplitude', 'fwhm', 'height']
            
            for prefix in [model.prefix for model in model_elements]:
                final_params[prefix[:-1]] = {}

                for name in component_param_names:
                    #print 'Name = ' + name
                    final_params[prefix[:-1]][name] = out.params[prefix + name].value
            
            metadata['lmfit_output'] = out
            metadata['best_fit'] = out.best_fit
            metadata['final_params'] = final_params
            metadata['residuals'] = out.residual
            
            is_double_start = time.time()       
                    
            is_double, heights, centers = test_if_double(x, out.best_fit, final_params, doubles_threshold = doubles_threshold, min_dist = doubles_dist, monitor_progress = monitor_progress)            
            
            is_double_end = time.time()
            is_double_time = is_double_end - is_double_start
            
            if monitor_progress == 'time' or monitor_progress == True:
                print 'Tested if double peak in %s seconds\n\n' % is_double_time
            
            if monitor_progress == True:
                
                if is_double == True:
                    print '\nDouble peak'
                
                elif is_double == False:
                    print '\nSingle peak'
                
                else:
                    print '\nSomething else'
                
                #print 'Peak positions:', centers
                print 'Fitting complete'
            
            cm_peakpos = centers[np.array(heights).argmax()]
            metadata['double_peak?'] = is_double
            metadata['coupled_mode_resonance_(fit)'] = cm_peakpos
            metadata['coupled_mode_intensity_(fit)'] = max(heights)
            
            if print_report == True:
                print 'Fit report:\n'
                print out.fit_report()

            if plot == 'basic' or plot == 'both':
                plt.figure(figsize = (10,7))
                plt.plot(x_raw, y_raw_norm, label = 'raw')
                plt.plot(x, out.best_fit, 'r-', label = 'fit')
                plt.legend(loc = 0)
                plt.xlabel('Wavelength (nm)')
                plt.tick_params(axis = 'y', labelleft = 'off')
                #plt.ylabel('Intensity')
                plt.xlim(450, 1050)
                plt.show()

            elif plot == 'full' or plot == 'all':

                plt.figure(figsize = (10,7))
                
                if monitor_progress == True:
                    
                    if is_double == True:
                        plt.title('Double Peak')
                    
                    elif is_double == False:
                        plt.title('Single Peak')
                        
                plt.plot(x_raw, y_raw_norm, label = 'raw', linewidth = 0.7)
                plt.plot(x, y_smooth, label = 'smoothed', linewidth = 0.5)
                plt.plot(x, init, 'k-', label = 'initial guess', linewidth = 0.3)

                for i in range(len(indices)):
                    plt.plot(x, comps['g%s_' % (i)], '--', label = 'Component %s' % (i), linewidth = 0.3)

                plt.plot(x, out.best_fit, 'r-', label = 'fit')
                plt.legend(loc = 0, ncol = 2, fontsize = 9)
                plt.xlabel('Wavelength (nm)')
                #plt.tick_params(axis = 'y', labelleft = 'off')
                plt.ylabel('Intensity')
                lim_frac = y_smooth.max()/10
                plt.ylim(-lim_frac/2, y_smooth.max() + lim_frac)
                plt.xlim(450, 900)
                plt.yticks([])
                plt.show()
                
                plt.figure(figsize = (10, 4))
                plt.title('Residuals')
                plt.plot(x, out.residual)
                plt.xlabel('Wavelength (nm)')
                plt.ylabel('Residuals')
                plt.yticks([])
                plt.xlim(450, 900)
                plt.show()
            
            if is_double == False:               
                
                trans_index = np.where(np.round(x) - np.round(trans_peakpos) == 0)[0][0]
                trans_height = y_smooth[trans_index]
                cm_full_height = y_smooth.max()
                cm_full_peakpos = x[y_smooth.argmax()]
                
                for prefix in [model.prefix for model in model_elements]:
                    comp = final_params[prefix[:-1]]
                    
                    if comp['center'] > 500:
                        trans_comp_peakpos = comp['center']                        
                        trans_comp_height = comp['height']
                        
                        if trans_comp_height < trans_height/3.5:
                            continue
                            
                        elif comp['center'] > 550:
                            trans_comp_peakpos = trans_peakpos
                            trans_comp_height = trans_height
                            break
                        
                        else:
                            break
                
                try:
                    cm_index = np.where(np.round(x) - np.round(cm_peakpos) == 0)[0][0]
                    cm_height = y_smooth[cm_index]
                
                except:
                    cm_height = cm_full_height
                    cm_peakpos = cm_full_peakpos
                    
                    if monitor_progress == True:
                        print 'CM peak position out of range. CM height/peak position assigned to spectral maximum'
                             
                intensity_ratio_1 = cm_full_height/trans_height
                intensity_ratio_2 = cm_full_height/trans_comp_height
                
                metadata['intensity_ratio_1'] = intensity_ratio_1
                metadata['intensity_ratio_2'] = intensity_ratio_2
                metadata['transverse_mode_position'] = trans_comp_peakpos
                metadata['transverse_mode_intensity_(init)'] = trans_height
                metadata['transverse_mode_intensity'] = trans_comp_height
                metadata['coupled_mode_resonance_(spectrum)'] = cm_full_peakpos
                metadata['coupled_mode_height_(spectrum)'] = cm_full_height
                metadata['final_components'] = comps
                
                #y_raw_norm /= trans_comp_height
                #y /= trans_comp_height
                #y_smooth/= trans_comp_height
                
                #metadata['normalised_spectrum'] = y_raw_norm
                #metadata['smoothed_spectrum'] = y_smooth
                #metadata['truncated_spectrum'] = y
                
                if plot == 'all':
                    lim_frac = y_smooth.max()/10
                                        
                    plt.plot(x_raw, y_raw_norm, lw = 0.5)
                    plt.plot(x, y)
                    plt.plot(x, y_smooth)
                    plt.plot(x, [0] * len(x), '--')
                    plt.plot([trans_peakpos] * 10, np.linspace(trans_height, cm_full_height, 10), 'k--')
                    plt.plot(x, [cm_full_height] * len(x))
                    plt.plot(x, [trans_height] * len(x))
                    plt.title('Intensity Ratio 1: %s' % (intensity_ratio_1))
                    plt.xlabel('Wavelength(nm)')
                    plt.ylabel('Intensity')
                    plt.ylim(-lim_frac/2, y_smooth.max() + lim_frac)
                    plt.xlim(450, 900)
                    plt.show()
                    
                    plt.plot(x_raw, y_raw_norm/trans_comp_height, lw = 0.5)
                    plt.plot(x, y/trans_comp_height)
                    plt.plot(x, y_smooth/trans_comp_height)
                    plt.plot(x, [0] * len(x), '--')
                    plt.plot([trans_comp_peakpos] * 10, np.linspace(trans_comp_height, cm_full_height/trans_comp_height, 10), 'k--')
                    plt.plot(x, [cm_full_height/trans_comp_height] * len(x))
                    plt.plot(x, [trans_comp_height/trans_comp_height] * len(x))
                    plt.plot([cm_peakpos] * 10, np.linspace(0, cm_full_height, 10)/trans_comp_height, 'r--')
                    plt.plot([cm_full_peakpos] * 10, np.linspace(0, cm_full_height, 10)/trans_comp_height, 'g--')
                    
                    for i in range(len(indices)):
                        plt.plot(x, comps['g%s_' % (i)]/trans_comp_height, '--', linewidth = 0.4)
                    
                    plt.title('Intensity Ratio 2: %s' % (intensity_ratio_2))
                    plt.xlabel('Wavelength(nm)')
                    plt.ylabel('Intensity')
                    plt.ylim(-lim_frac/2, (y_smooth/trans_comp_height).max() + lim_frac)
                    plt.xlim(450, 900)
                    plt.show()
              
                if abs(cm_full_peakpos - cm_peakpos) < 50:
                    cm_peakpos = cm_full_peakpos
            
            metadata['NPoM?'] = is_NPoM
            return DF_Spectrum(y, final_params, is_NPoM, is_double, cm_peakpos, metadata)
        
        else:
            is_NPoM = False
            
            if monitor_progress == True:
                print 'Not a NPoM'
            
            metadata['NPoM?'] = is_NPoM
            return DF_Spectrum(y, 'N/A', is_NPoM, 'N/A', 'N/A', metadata)
            
    else:
        
        if monitor_progress == True:
            print 'Not a NPoM'
        
        metadata['NPoM?'] = is_NPoM       
        return DF_Spectrum(y, 'N/A', is_NPoM, 'N/A', 'N/A', metadata)
    
def reduce_noise(y, factor = 10):
    y_smooth = butter_lowpass_filtfilt(y)
    y_noise = y - y_smooth
    y_noise /= factor
    y = y_smooth + y_noise
    return y

def make_histogram(spectra, start_wl = 450, end_wl = 900, no_of_bins = 80, plot = True, min_bin_factor = 4):
    
    bin_size = (end_wl - start_wl) / no_of_bins
    bins = np.linspace(start_wl, end_wl, num = no_of_bins)
    frequencies = np.zeros(len(bins))
    spectra_binned = [[] for f in frequencies]
    x = spectra['Spectrum 0/Raw/Raw data'].attrs['wavelengths'][()]
    
    start_index = np.where(np.round(x) == np.round(start_wl))[0][0]
    end_index = np.where(np.round(x) == np.round(end_wl))[0][0]
    
    ydata_binned = [np.zeros(len(x)) for f in frequencies]
    
    for n, spectrum in enumerate(spectra):
        
        for nn, bin_start in enumerate(bins):
            
            cm_peakpos = spectra[spectrum].attrs['Coupled mode wavelength (from spectrum)']
            #print cm_peakpos
            ydata = spectra[spectrum]['Raw/Raw data (normalised)']

            if cm_peakpos != 'N/A' and cm_peakpos > bin_start and cm_peakpos < bin_start + bin_size and 600 < cm_peakpos < 849:
                frequencies[nn] += 1
                ydata_binned[nn] += ydata

    for n, ydata_sum in enumerate(ydata_binned):
        ydata_binned[n] /= frequencies[n]
    
    min_bin = max(frequencies)/min_bin_factor
    
    fig = plt.figure(figsize = (8, 6))
    
    if plot == True:
        fig = plt.figure(figsize = (8, 6))

        cmap = plt.get_cmap('jet')

        ax1 = fig.add_subplot(111)
        ax1.set_zorder(1)
        ax2 = ax1.twinx()
        ax2.set_zorder(0)
        ax1.patch.set_visible(False)

        ymax = 0

        ydata_plot = [i for n, i in enumerate(ydata_binned) if frequencies[n] > min_bin]

        for n, ydata_sum in enumerate(ydata_plot):

            color = cmap(256 - n*(256/len(ydata_plot)))
            current_ymax = ydata_sum[start_index:end_index].max()

            y_smooth = reduce_noise(ydata_sum, factor = 7)
            ax1.plot(x, y_smooth, lw = 0.7, color = color)

            if current_ymax > ymax:
                ymax = current_ymax

        ax1.set_ylim(-0.1, ymax*1.2)
        ax1.set_ylabel('Normalised Intensity', fontsize = 18)
        ax1.tick_params(labelsize = 15)
        ax1.set_xlabel('Coupled Mode Peak Position (nm)', fontsize = 18)
        #ax1.set_xticks(range(500, 900, 50))

        ax2.bar(bins, frequencies, width = 0.8*bin_size, color = 'grey', alpha = 0.9, linewidth = 0)
        ax2.set_xlim(start_wl, end_wl)
        ax2.set_ylim(0, max(frequencies)*1.05)
        ax2.set_ylabel('Frequency', fontsize = 18, rotation = 270)
        ax2.yaxis.set_label_coords(1.11, 0.5)
        ax2.set_yticks([int(tick) for tick in ax2.get_yticks() if tick > 0][:-1])
        ax2.tick_params(labelsize = 15)

        fig.tight_layout()
        fig.savefig('Histogram.png')

        img = Image.open('Histogram.png')
        img = np.array(img)
        img = img.transpose((1, 0, 2))

    return frequencies, bins, ydata_binned, img

def histyfit(frequencies, bins):
    
    gauss_model = GaussianModel()
    pars = gauss_model.guess(frequencies, x = bins)
    out = gauss_model.fit(frequencies, pars, x=bins)#Performs the fit, based on initial guesses
    print '\nAverage peakpos:', out.params['center'].value, '+/-', out.params['center'].stderr, 'nm'
    print 'FWHM:', out.params['fwhm'].value, 'nm'
    #print out.fit_report()
    
    resonance = out.params['center'].value
    stderr = out.params['center'].stderr
    fwhm = out.params['fwhm'].value

    return resonance, stderr, fwhm

def peakfit_for_threading(data):
    try:
        return find_fit_peaks(data[0], data[1])
    except:
        return 'Failed'
        
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def collect_intensity_ratios(all_spectra, plot = True):
    
    ir_1 = [all_spectra[spectrum].attrs['Intensity ratio 1 (rough)'] for spectrum in all_spectra]
    ir_2 = [all_spectra[spectrum].attrs['Intensity ratio 2 (realistic)'] for spectrum in all_spectra]
    cm_peakposes = [all_spectra[spectrum].attrs['Coupled mode wavelength (from spectrum)'] for spectrum in all_spectra]
    
    for n, ir in enumerate(ir_1):
        
        if is_number(ir) == False:
            ir_1[n] = 'N/A'
            ir_2[n] = 'N/A'
            cm_peakposes[n] = 'N/A'
    
    for n, ir in enumerate(ir_2):
        
        if is_number(ir) == False:
            ir_1[n] = 'N/A'
            ir_2[n] = 'N/A'
            cm_peakposes[n] = 'N/A'
            
    for n, cm_peakpos in enumerate(cm_peakposes):
        
        if is_number(cm_peakpos) == False:
            ir_1[n] = 'N/A'
            ir_2[n] = 'N/A'
            cm_peakposes[n] = 'N/A'
    
    ir_1 = np.array([a for a in ir_1 if a != 'N/A'])
    ir_2 = np.array([a for a in ir_2 if a != 'N/A'])
    cm_peakposes = np.array([a for a in cm_peakposes if a != 'N/A'])
    
    if plot == True:
        
        imgs = {}
        
        for ir_ind, y in enumerate([ir_1, ir_2]):
            x = cm_peakposes
            nbins=300

            k = gaussian_kde([x,y])
            xi, yi = np.mgrid[x.min():x.max():nbins*1j, y.min():y.max():nbins*1j]
            zi = k(np.vstack([xi.flatten(), yi.flatten()]))
            
            zi_ordered = np.array(sorted(zi)[::-1])
            zi_cum = np.cumsum(zi_ordered)
            zi_total = sum(zi)
            
            index_50 = np.where(zi_cum > zi_total*0.9)[0][0]
            
            zi_50 = []
            
            for n, z_val in enumerate(zi):
                
                if z_val < zi_ordered[index_50]:
                    zi_50.append(0)
                
                else:
                    zi_50.append(1)
                
            zi_50 = np.array(zi_50)
            zi_50[zi.argmax()] = 5
                
            fig = plt.figure(figsize = (7, 7))
            plt.contour(xi, yi, zi.reshape(xi.shape))#, colors = ('w', 'w', 'b', 'w', 'w', 'w', 'w'))
            plt.contour(xi, yi, zi_50.reshape(xi.shape))#, colors = 'b', levels = [])
            plt.xlim(600, 900)
            plt.ylim(1, 7)
            plt.xlabel('Coupled Mode Resonance (nm)', fontsize = 18)
            plt.ylabel('Intensity Ratio', fontsize = 18)
            plt.xticks(fontsize = 18)
            plt.yticks(fontsize = 18)
            
            fig.tight_layout()
            fig.savefig('Intensity Ratios %s.png' % (ir_ind + 1))
            
            img = Image.open('Intensity Ratios %s.png' % (ir_ind + 1))
            img = np.array(img)
            img = img.transpose((1, 0, 2))
            
            imgs['ir_%s' % (ir_ind + 1)] = img
            
    return ir_1, ir_2, cm_peakposes, imgs
        
if __name__ == '__main__':
    
    print 'Functions initialised\n'
    print 'Retrieving data...'
    
    prep_start = time.time()
    
    start_spec = 0
    finish_spec = 0
    
    '''Retrieve data from summary file, remove NaN values and reference'''
    
    if 'summary.h5' in os.listdir('.'):
        h5_filename = 'summary.h5'
    
    elif 'summary.hdf5' in os.listdir('.'):
        h5_filename = 'summary.hdf5'
    
    else:
        print 'Summary file not found'
        exit
    
    summary_file = h5py.File(h5_filename, 'r') 
    all_scans = summary_file['particleScanSummaries/'] 
    scan_number = np.array([len(all_scans[scan]['spectra']) for scan in all_scans]).argmax()
    
    if finish_spec == 0:
        spectra = summary_file['particleScanSummaries/scan%s/spectra' % scan_number][()][start_spec:]
    
    else:
        spectra = summary_file['particleScanSummaries/scan%s/spectra' % scan_number][()][start_spec:finish_spec]
    
    wavelengths = summary_file['particleScanSummaries/scan%s/spectra' % scan_number].attrs[u'wavelengths'][()]
    background = summary_file['particleScanSummaries/scan%s/spectra' % scan_number].attrs[u'background'][()]
    reference = summary_file['particleScanSummaries/scan%s/spectra' % scan_number].attrs[u'reference'][()]
    
    print 'Data retrieved from particleScanSummaries/scan%s\n' % scan_number
    print 'Preparing data...'
    
    remove_NaNs(wavelengths)
    
    for spectrum in spectra:
        remove_NaNs(spectrum)
    
    spectra_referenced = [correct_spectrum(spectrum, reference) for spectrum in spectra]
    
    x_full = wavelengths
    y_full = spectra_referenced
    
    summary_file.close()
    
    prep_end = time.time()
    prep_time = prep_end - prep_start
    
    print 'All spectra cleared of NaNs and referenced in %s seconds\n' % prep_time
    
    '''Set initial fit parameters'''
    
    print 'Creating output file...'
    
    x = x_full
    doubles_threshold = 0.4
    detection_threshold = 0
    doubles_dist = 50
    
    '''Create/open new hdf5 file ready for population'''
    
    output_file = 'Multipeakfit_output.h5'
    
    if output_file in os.listdir('.'):
        print '\n%s already exists' % output_file
        n = 0
        output_file = 'Multipeakfit_output_%s.h5' % n
        
        while output_file in os.listdir('.'):
            print '%s already exists' % output_file
            n += 1
            output_file = 'Multipeakfit_output_%s.h5' % n
    
    print '\nOutput file %s created' % output_file

    '''Start peak fit "for" loop'''
    
    print '\nBeginning fit procedure...'
    
    if len(y_full) > 2500:
        print 'About to fit %s spectra. This may take a while...' % len(y_full)
    
    fitted_spectra = []
    failed_spectra = []
    
    nummers = range(5, 101, 5)
    
    total_fit_start = time.time()
    
    print '\n0% complete'
            
    with h5py.File(output_file, 'a') as f:
    
        for n, y in enumerate(y_full[:]):
            
            nn = n
            n += start_spec
            #print n
            
            if int(100 * nn / len(y_full[:])) in nummers:
                current_time = time.time() - total_fit_start
                mins = int(current_time / 60)
                secs = (np.round((current_time % 60)*100))/100
                print '%s%% complete in %s min %s sec' % (nummers[0], mins, secs)
                nummers = nummers[1:]
            
            start_fit = time.time()
        
            try:
                fitted_spectrum = find_fit_peaks(x, y, detection_threshold = detection_threshold, doubles_threshold = doubles_threshold, doubles_dist = doubles_dist)#, monitor_progress = 'time')
                fitted_spectra.append(fitted_spectrum)
            
            except:
                failed_spectra.append(y)
                print 'Spectrum %s fitting failed' % n
            
            end_fit = time.time()
            
            single_fit_time = end_fit - start_fit
            
            #print 'Spectrum %s fitted in %s seconds' % (n, single_fit_time)
        
            '''Iterate through list of fitted spectra and populate HDF5 file'''
            
            group_time_start = time.time()

            g = f.create_group('Fitted spectra/Spectrum %s/' % n)
            g.attrs['NPoM?'] = fitted_spectrum.metadata['NPoM?']
            g.attrs['Double Peak?'] = fitted_spectrum.metadata['double_peak?']
            g.attrs['Transverse mode intensity (from spectrum)'] = fitted_spectrum.metadata['transverse_mode_intensity_(init)']
            g.attrs['Transverse mode wavelength (from spectrum)'] = fitted_spectrum.metadata['transverse_mode_position_(init)']
            g.attrs['Transverse mode intensity (from fit)'] = fitted_spectrum.metadata['transverse_mode_intensity']
            g.attrs['Transverse mode wavelength (from fit)'] = fitted_spectrum.metadata['transverse_mode_position']
            g.attrs['Coupled mode intensity (from spectrum)'] = fitted_spectrum.metadata['coupled_mode_height_(spectrum)']
            g.attrs['Coupled mode wavelength (from spectrum)'] = fitted_spectrum.metadata['coupled_mode_resonance_(spectrum)']
            g.attrs['Coupled mode intensity (from fit)'] = fitted_spectrum.metadata['coupled_mode_intensity_(fit)']
            g.attrs['Coupled mode wavelength (from fit)'] = fitted_spectrum.metadata['coupled_mode_resonance_(fit)']            
            g.attrs['Intensity ratio 1 (rough)'] = fitted_spectrum.metadata['intensity_ratio_1']
            g.attrs['Intensity ratio 2 (realistic)'] = fitted_spectrum.metadata['intensity_ratio_2']
            
            g_raw = g.create_group('Raw/')
            
            d_raw = g_raw.create_dataset('Raw data', data = fitted_spectrum.metadata['raw_data'])
            d_raw.attrs['wavelengths'] = fitted_spectrum.metadata['full_wavelengths']
            
            d_raw_norm = g_raw.create_dataset('Raw data (normalised)', data = fitted_spectrum.metadata['normalised_spectrum'])
            d_raw_norm.attrs['wavelengths'] = d_raw.attrs['wavelengths']
            
            g_fit = g.create_group('Fit/')
            
            d_raw_trunc = g_fit.create_dataset('Raw data (truncated, normalised)', data = fitted_spectrum.metadata['truncated_spectrum'])
            d_raw_trunc.attrs['wavelengths'] = fitted_spectrum.metadata['truncated_wavelengths']
            
            d_smooth = g_fit.create_dataset('Smoothed data', data = fitted_spectrum.metadata['smoothed_spectrum'])
            d_smooth.attrs['wavelengths'] = d_raw_trunc.attrs['wavelengths']
            d_smooth.attrs['second_derivative'] = fitted_spectrum.metadata['second_derivative']
            
            d_best_fit = g_fit.create_dataset('Best fit', data = fitted_spectrum.metadata['best_fit'])
            d_best_fit.attrs['wavelengths'] = d_raw_trunc.attrs['wavelengths']
            d_best_fit.attrs['Initial guess'] = fitted_spectrum.metadata['initial_guess']
            d_best_fit.attrs['Residuals'] = fitted_spectrum.metadata['residuals']
            
            g_comps = g_fit.create_group('Final components/')
            
            comps = fitted_spectrum.metadata['final_components']
                        
            if comps != 'N/A':
                
                for i in range(len(comps.keys())):
                    component = g_comps.create_dataset(str(i), data = comps['g%s_' % i])
            
                    component_params = fitted_spectrum.metadata['final_params']['g%s' % i]
                    component.attrs['center'] = component_params['center']
                    component.attrs['height'] = component_params['height']
                    component.attrs['amplitude'] = component_params['amplitude']
                    component.attrs['sigma'] = component_params['sigma']
                    component.attrs['fwhm'] = component_params['fwhm']
    
        x = x_full
        
        print '100% complete'
        total_fit_end = time.time()
        time_elapsed = total_fit_end - total_fit_start
    
        mins = int(time_elapsed / 60)
        secs = int(np.round(time_elapsed % 60))
        
        print '\n%s spectra fitted in %s min %s sec' % (nn + 1, mins, secs)
        print '\nCombining spectra and plotting histogram...'
        frequencies, bins, ydata_binned, img = make_histogram(f['Fitted spectra'])
        
        avg_resonance, stderr, fwhm = histyfit(frequencies, bins)
        
        stats_g = f.create_group('Statistics/Histogram/')
        stats_g.attrs['Average resonance'] = avg_resonance
        stats_g.attrs['Error'] = stderr
        stats_g.attrs['FWHM'] = fwhm 
                     
        d_bins = stats_g.create_dataset('Bins', data = bins)
        d_freq = stats_g.create_dataset('Frequencies', data = frequencies)
        d_freq.attrs['wavelengths'] = d_bins
        stats_g.create_dataset('Histogram', data = img)
        g_ydata_binned = stats_g.create_group('Binned y data/')
        
        for n, y_datum in enumerate(ydata_binned):
            g_ydata_binned.create_dataset('Bin %s data, peakpos = %s' % (n, bins[n]), data = y_datum)
        
        import seaborn as sns
        sns.set_style('white')
        
        print 'Plotting intensity ratios...'
        
        ir_1, ir_2, cm_peakposes, imgs = collect_intensity_ratios(f['Fitted spectra'], plot = True)
        
        ir_g = f.create_group('Statistics/Intensity ratios')
        d_cm_peakposes = ir_g.create_dataset('CM peak positions', data = cm_peakposes)
        
        ir_g_1 = ir_g.create_group('1')
        d_ir_1 = ir_g_1.create_dataset('Intensity ratios 1', data = ir_1)
        d_ir_1.attrs['wavelengths'] = d_cm_peakposes
        ir_g_1.create_dataset('Density map', data = imgs['ir_1'])
        #ir_g_1.create_dataset('Density map (50%)', data = imgs['ir_1_50'])
        
        ir_g_2 = ir_g.create_group('2')            
        d_ir_2 = ir_g_2.create_dataset('Intensity ratios 2', data = ir_2)
        d_ir_2.attrs['wavelengths'] = d_cm_peakposes
        ir_g_2.create_dataset('Density map', data = imgs['ir_2'])
        #ir_g_2.create_dataset('Density map (50%)', data = imgs['ir_2_50'])
    
    absolute_end_time = time.time()
    time_elapsed = absolute_end_time - absolute_start_time
    
    mins = int(time_elapsed / 60)
    secs = int(np.round(time_elapsed % 60))
    
    if len(failed_spectra) == 0:
        print '\nFinished in %s min %s sec. Smooth sailing.' % (mins, secs)
    
    elif len(failed_spectra) == 1:
        print '\nPhew... finished in %s min %s sec with only %s failure' % (mins, secs, len(failed_spectra))
    
    elif len(failed_spectra) > len(fitted_spectra):
        print '\nHmmm... finished in %s min %s sec but with %s failures and only %s successful fits' % (mins, secs, len(failed_spectra), len(fitted_spectra))
    
    elif len(fitted_spectra) > 5000:
        print '\nM8 that took ages. How long was your experiment?? %s min %s sec' % (mins, secs)
    
    else:
        print '\nPhew... finished in %s min %s sec with only %s failures' % (mins, secs, len(failed_spectra))