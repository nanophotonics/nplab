# -*- coding: utf-8 -*-
'''
Created on 2023-01-27
@author: car72

Module with basic functions for processing and analysing spectra
Many of these functions are copied from NPoM_DF_Analysis.DF_Multipeakfit
    but have been reformatted and repurposed as part of the upcoming overhaul
Still a work in progress, so check back for updates!

Useful functions include:

Smoothing: butter_lowpass_filt_filt()
Numerical differentiation: cent_diff()
Detection of minima (or maxima): detect_minima()

'''

import numpy as np
import scipy as sp
import h5py
#from scipy.signal import butter, filtfilt #for smoothing function
import matplotlib as mpl
import matplotlib.pyplot as plt
import os

from nplab.analysis.general_spec_tools import all_rc_params as arp

#pyplot rcParams to make pretty Timescans:
timescan_params = arp.master_param_dict['NPoM SERS Timescan']

def approx_peak_gausses(x, y, smooth_first = True, threshold = 0.1, reverse = False, plot = False, height_frac = 0.5, **kwargs):
    '''
    Estimates FW{height_frac}M, center and height of peaks in a dataset
        height_frac defaults to 0.5 (i.e. FWHM), but can be raised or lowered to suit the spectral shape

    smooth: smooth spectrum before analysis; default = True (good for NPoM DF, Aggregate Extinction etc)
    reverse: optionally reverses the x and y arrays before analysis
    '''
    #y_raw = y.copy()
    #y = y/y.max()#normalise before analysis
    
    if smooth_first == True:#smooth spectrum before analysing; default = True
        y = butter_lowpass_filt_filt(y)
        
    if reverse == True:#optionally reverse spectrum before analysing
        x = x[::-1]
        y = y[::-1]
        if peak_index is not None:#flip peak index position accordingly
            peak_index = -peak_index

    y_temp = y.copy()
    approx_gausses = []

    n = 0
    while True:
        maxima = detect_maxima(y_temp, lower_threshold = threshold*y.max(), edges = True)

        if len(maxima) == 0:
            break

        maxima = np.array(sorted(maxima, key = lambda i: x[i]))
        residuals = []
        temp_gausses = []

        for peak_index in maxima:
            #peak_index = maxima[-1]
            height = y_temp[peak_index]
            center = x[peak_index] #corresponding x and y locations of maximum
            width_height = height*height_frac
            
            y_sub = y_temp - width_height #difference between y and half max
            
            y_diff_mins = detect_minima(abs(y_sub), upper_threshold = y.max()*1e-2)#find where y_sub crosses 0

            diff_mins_left = y_diff_mins[y_diff_mins < peak_index]
            diff_mins_right = y_diff_mins[y_diff_mins > peak_index]

            if len(diff_mins_left) > 0:
                windex_left = diff_mins_left[-1]
                width_left = abs(center - x[windex_left])
                y_left = y_temp[windex_left:peak_index]
                x_left = x[windex_left:peak_index]
                g_left = gaussian(x_left, height, center, width_left*2, height_frac)
                residual_left = np.std(g_left - y_left)/height

                if plot == True:
                    plt.plot(x[windex_left], y_temp[windex_left], 'r.', zorder = 100)

            else:
                width_left = np.inf
                residual_left = np.inf

            if len(diff_mins_right) > 0:
                windex_right = diff_mins_right[0]
                width_right = abs(center - x[windex_right])
                y_right = y_temp[peak_index:windex_right]
                x_right = x[peak_index:windex_right]
                g_right = gaussian(x_right, height, center, width_right*2, height_frac)
                residual_right = np.std(g_right - y_right)/height

                if plot == True:
                    plt.plot(x[windex_right], y_temp[windex_right], 'r.', zorder = 100)

            else:
                width_right = np.inf
                residual_right = np.inf

            residual = min([residual_left, residual_right])
            width = min([width_left, width_right])*2

            if plot == True:
                plt.plot(x, y_temp)
                plt.plot(x, abs(y_sub), 'k--', alpha = 0.6)
                plt.plot(center, height, 'o')

                #if np.isfinite(fwhm):
                gauss_approx = gaussian(x, height, center, width, height_frac)
                ls = '--'

                plt.plot(x, gauss_approx, ls)

                #plt.plot(x, abs(y_sub))
                plt.plot(x[y_diff_mins], y_temp[y_diff_mins], 'ko')
                plt.title(f'Iteration {n}; {center:.2f}; {residual:.2e}')
                #plt.legend(title = 'center & residual', loc = 'center left', bbox_to_anchor = (1, 0.5))
                plt.show()

            residuals.append(residual)
            temp_gausses.append((height, center, width, height_frac))

        min_residual, chosen_gauss_params = sorted(zip(residuals, temp_gausses), key = lambda r_g: r_g[0])[0]
        height, center, width, height_frac = chosen_gauss_params
    
        if plot == True:
            plt.plot(x, y_temp)
            plt.plot(center, height, 'ko')

            for peak_index, residual, gauss_params in zip(maxima, residuals, temp_gausses):
                gauss_approx = gaussian(x, *gauss_params)
                ls = '--'
                if gauss_params == chosen_gauss_params:
                    ls = 'k--'
                plt.plot(x, gauss_approx, ls, label = f'{x[peak_index]:.1f}; {residual:.2e}')

            #plt.plot(x, abs(y_sub))
            plt.title(f'Iteration {n}')
            plt.legend(title = 'center & residual', loc = 'center left', bbox_to_anchor = (1, 0.5))
            plt.show()

        approx_gausses.append(chosen_gauss_params)

        gauss_approx = gaussian(x, *chosen_gauss_params)
        y_temp -= gauss_approx
        n += 1

    if plot == True:
        print(f'{len(approx_gausses)} peaks found')
        plt.plot(x, y)
        for g_n, (height, center, width, height_frac) in enumerate(approx_gausses):
            gauss_approx = gaussian(x, height, center, width, height_frac)
            plt.plot(x, gauss_approx, '--', label = f'g_{g_n}')

        plt.title('Final')
        plt.show()

    return approx_gausses

def baseline_als(y, lam, p, niter=10):
    '''
    Calculates spectral baseline using iterative asymmetric least-squares fitting

    Parameters:
        y: signal to be baselined; 1D array_like
        lam: (aka lambda) large number determining smoothness; typically 10^2 - 10^9
        p: small number (between 0 and 1); determines asymmetry; typically 10^-1 to 10^-3
            generally lam = 10^n and p = 10^-m; higher values of m or n increase "roughness" of baseline
        niter: number of iterations

    Returns:
        z: baseline of signal; 1D numpy array with same length as y
    '''

    assert 0 < p < 1, 'p must be between 0 and 1 for baseline_als'

    y = np.array(y)
    
    L = len(y)
    D = sp.sparse.diags([1,-2,1],[0,-1,-2], shape=(L,L-2))
    D = sp.sparse.csc_matrix(np.diff(np.eye(L), 2)) 
    w = np.ones(L)

    for i in range(niter):
        W = sp.sparse.spdiags(w, 0, L, L)
        Z = W + lam * D.dot(D.transpose())
        z = sp.sparse.linalg.spsolve(Z, w*y)
        w = p * (y > z) + (1-p) * (y < z)

    return z

def boltzmann_dist(x, a, A):
    '''
    !!! needs docstring !!!
    '''
    return A*np.sqrt(2/np.pi)*(x**2*np.exp(-x**2/(2*a**2)))/a**3

def butter_lowpass_filt_filt(y, cutoff = 1500, fs = 60000, order=5, **kwargs):
    '''
    Smoothes y data without shifting it
    Play with values of cutoff and fs to control amount of wibbly wobbly in output
    !!! find out what order does and add info to docstring !!!
    '''
    y = np.array(y)

    if len(y.shape) == 2:#if y is 2D array (ca. list of 1D spectra), each spectrum is smoothed individually through recursive calling
        return np.array([butter_lowpass_filt_filt(yi, cutoff, fs, order) for yi in y])

    padded = False

    if len(y) < 18:# len(y) must be >= 18 for function to work
        padded = True
        pad = 18 - len(y)//2
        start_pad = np.array([y[0]] * (int(pad) + 1))
        end_pad = np.array([y[0]] * (int(pad) + 1))
        y = np.concatenate((start_pad, y, end_pad))

    '''
    No idea what the next bit actually does
    I stole it off the internet and have been using it since 2016; it's very robust
    '''
    nyq = 0.5 * fs
    normal_cutoff = cutoff/nyq
    b, a = sp.signal.butter(order, normal_cutoff, btype = 'low', analog = False)
    y_filtered = sp.signal.filtfilt(b, a, y)

    if padded == True:
        y_filtered = y_filtered[len(start_pad):-len(end_pad)]

    return y_filtered

def calc_noise(y, y_smooth = None, window_size = 5, **kwargs):
    '''
    Calculates noise using moving window to compare raw and smoothed spectrum
    Smoothed spectrum can be specified or calculated in-situ
    window size must be int
    '''

    if y_smooth is None:
        y_smooth = butter_lowpass_filt_filt(y, **kwargs)

    if window_size % 2 != 0:
        window_size += 1

    noise = y - y_smooth
    new_noise = np.concatenate((noise[:window_size/2][::-1], noise, noise[-window_size/2:][::-1]))
    noise_level = np.array([np.std(new_noise[n:n + window_size]) for n, i in enumerate(noise)])

    return noise_level

def cent_diff(x, y):

    '''Numerically calculates dy/dx using central difference method'''

    x1 = np.concatenate((x[:2][::-1], x))
    x2 = np.concatenate((x, x[-2:][::-1]))
    dx = x2 - x1
    dx = dx[1:-1]

    y1 = np.concatenate((y[:2][::-1], y))
    y2 = np.concatenate((y, y[-2:][::-1]))
    dy = y2 - y1
    dy = dy[1:-1]

    if 0 in dx:
        dx = remove_nans(np.where(dx == 0, dx, np.nan))

    d = dy/dx
    d /= 2

    return d

def detect_maxima(y, upper_threshold = np.inf, lower_threshold = -np.inf, edges = False):
    maxdices = detect_minima(-y)

    if edges == True:
        x = np.arange(len(y))
        d1 = cent_diff(x, y)
        if d1[0] < 0 and lower_threshold < y[0] < upper_threshold:
            maxdices = np.insert(maxdices, 0, 0)
        if d1[-1] > 0 and lower_threshold < y[-1] < upper_threshold:
            maxdices = np.append(maxdices, len(y) - 1)

    if len(maxdices) > 0:
        maxdices = maxdices[lower_threshold < y[maxdices]]
        maxdices = maxdices[y[maxdices] < upper_threshold]

    return maxdices

def detect_minima(y, upper_threshold = np.inf, lower_threshold = -np.inf):
    '''
    Returns indices of any minima in the input
    to identify maxima, just use -y instead of y
    
    Args: 
        y: array_like; 1D
        upper_threshold: threshold above which minima are ignored
        lower_threshold: as above, but below

    Returns: np.array

    '''
    mindices = []
    y = np.array(y)

    if (len(y) < 3):#
        return False if return_bool == True else mindices

    neutral, rising, falling = np.arange(3)

    def get_state(a, b):
        if a < b: return rising
        if a > b: return falling
        return neutral

    ps = get_state(y[0], y[1])
    begin = 1

    for i in np.arange(2, len(y)):
        s = get_state(y[i - 1], y[i])

        if s != neutral:
            if ps != neutral and ps != s:
                if s != falling:
                    mindices.append((begin + i - 1)//2)

            begin = i
            ps = s

    mindices = np.array(mindices)

    if len(mindices) > 0:
        mindices = mindices[lower_threshold < y[mindices]]
        mindices = mindices[y[mindices] < upper_threshold]

    return mindices

def evToNm(eV):
    '''
    converts eV to nm
    '''
    e = 1.60217662e-19
    joules = eV * e
    c = 299792458
    h = 6.62607015e-34
    wavelength = h*c/joules
    nm = wavelength * 1e9
    return nm

def nmToEv(nm):
    '''
    converts nm to eV
    '''
    wavelength = nm*1e-9
    c = 299792458
    h = 6.62607015e-34
    joules = h*c/wavelength
    e = 1.60217662e-19
    eV = joules / e
    return eV

def find_d2_minima(x, y, smoothed = False, threshold = 0.1, max_n_peaks = 5, plot = False, title = None, **kwargs):    
    if smoothed == False:
        y_smooth = butter_lowpass_filt_filt(y, **kwargs)
    else:
        y_smooth = y

    d1 = cent_diff(x, y_smooth)
    d2 = cent_diff(x, d1)
    d2 /= d2.max()
    
    d2_mins = detect_minima(d2)
    d2_mins = d2_mins[d2[d2_mins] < -threshold]# d2 minima that are negative and greater in magnitude than certain threshold
    d2_mins = sorted(d2_mins, key = lambda i: d2[i])[:max_n_peaks]#keep only the most negative ones    
    
    y_maxs = detect_minima(-y_smooth)

    if plot == True:    
        fig, (ax_d2, ax_d1, ax) = plt.subplots(3, sharex = True, figsize = (8, 12))
        
        ax_d2.plot(x, d2, color = plt.cm.Dark2(2))
        ax_d2.plot(x[d2_mins], d2[d2_mins], 'ro')
        ax_d2.plot(x, np.zeros(len(x)), 'k--', lw = 1)
        
        ax_d2.set_yticks([])
        ax_d2.set_ylabel('y"', rotation = 0, ha = 'right')

        ax_d1.plot(x, d1, color = plt.cm.Dark2(1))
        ax_d1.set_yticks([])
        ax_d1.set_ylabel('y\'', rotation = 0, ha = 'right')
        
        ax.plot(x, y)
        ax.plot(x, y_smooth)
        ax.plot(x[y_maxs], y_smooth[y_maxs], 'ko')
        ax.plot(x[d2_mins], y_smooth[d2_mins], 'ro')
        
        ax.set_yticks([])
        ax.set_ylabel('Intensity')
        
        ax.set_xlabel('Wavelength (nm)')
        ax.set_xlim(x.min(), x.max())

        if title is not None:
            ax_d2.set_title(title)

        plt.subplots_adjust(hspace = 0)
        plt.show()

    return d2_mins, y_maxs

def gauss_area(height, fwhm):
    '''
    Calculates area of gaussian based on height and FWHM only
    Assumes no y-offset
    '''
    h = height
    c = fwhm
    area = h*np.sqrt((np.pi*c**2)/(4*np.log(2)))

    return area

def gaussian(x, height, center, width, width_height_frac = 0.5):
    a = height
    b = center
    c = width/(2*np.sqrt(2*np.log(1/width_height_frac)))
    
    return a*np.exp(-(((x - b)**2)/(2*c**2)))

def gaussian_old(x, height, center, fwhm, offset = 0):
    '''Gaussian as a function of height, centre, fwhm and offset'''
    a = height
    b = center
    c = fwhm

    N = 4*np.log(2)*(x - b)**2
    D = c**2
    F = -(N/D)
    E = np.exp(F)
    y = a*E
    y += offset

    return y

def linear_interp(a, b, frac):
    '''
    interpolate fractionally between two values (a and b)
    frac is between 0 and 1
    '''
    m = b - a
    return (m * frac) + a

def lorentzian(x, height, center, fwhm):
    I = height
    x0 = center
    gamma = fwhm/2
    numerator = gamma**2
    denominator = (x - x0)**2 + gamma**2
    quot = numerator/denominator
    
    y = I*quot
    return y

def remove_nans(data, noisy_data = False, **kwargs):
    '''
    Interpolates across gaps left by NaN values in n-dimensional array
    if too_noisy == True: (use for very noisy data)
        replaces NaNs with values from smoothed array
    else: (better for clean data)
        replaces NaNs with linear interpolation between adjacent points

    Input = array-like
    Output = copy of same array/list with no NaNs
    Array size/shape is preserved

    !!! add option to call calc_noise function and allow auto-detection of too_noisy !!!
    '''

    y = np.array(data)

    if len(np.shape(y)) > 1:#if array dimensionality > 1, recursively performs remove_nans on each 1D sub array
        y = np.array([remove_nans(y_sub) for y_sub in y])

    if np.count_nonzero(np.isnan(data)) == 0:#returns original array if no nans detected
        return y

    elif np.count_nonzero(~np.isnan(data)) == 0:#returns original array if all elements are NaN
        print('WARNING: Entire array is NaNs')
        return y
    
    '''
    performs linear interpolation across "gaps" caused by NaN values
    '''
    x = np.arange(0, len(y))#keeps track of original array length
    y_trunc = np.delete(y, np.where(np.isnan(y)))#deletes all NaNs and truncates array
    x_trunc = np.delete(x, np.where(np.isnan(y)))#repeats with x
    y_interp = np.interp(x, x_trunc, y_trunc)#interpolates using x and x_trunc as a reference

    if noisy_data == True:
        '''
        smoothes data and replaces NaNs with values from smoothed data
        good for very noisy data, but can generate artifacts in clean data
        '''
        y_smooth_interp = butter_lowpass_filt_filt(y_interp, **kwargs)#include cutoff and fs values in kwargs, if needed
        y_interp = np.where(np.isnan(y), y_smooth_interp, y)

    return y_interp

def truncate_spectrum(x, y, start_wl = 450, end_wl = 900, buffer = False):
    '''
    Truncates x, y data according to given x values. 
    Useful for isolating a section of a spectrum.
    x: 1D array
    y: 1D or 2D array; if 2D, y.shape[1] must be equal to len(x)
    
    Default start & end wavelength are 450, 900 - common useful data range for Lab 3 darkfield spectra.
    '''
    x = np.array(x)
    y = np.array(y)

    if len(y.shape) == 2:#if y is 2D, recursively performs truncate_spectrum on each 1D sub array
        Y = np.array([truncate_spectrum(x, y_sub, start_wl, end_wl, buffer)[1] for y_sub in y])
        x = truncate_spectrum(x, y[0], start_wl, end_wl, buffer)[0]
        return x, Y

    assert len(x) == len(y), f'x and y must be the same length. Currently len(x) = {len(x)}; len(y) = {len(y)}'

    reverse = False
    if x[0] > x[-1]:
        reverse = True
        x = x[::-1]
        y = y[::-1]

    if end_wl == 0 or end_wl is None:
        end_wl = x.max()
        
    if start_wl < x.min() or end_wl > x.max():
        '''
        If start or end wl lie outside x range, x and y will be increased in length
        new y data can be specified by "buffer", otherwise defaults to NaN
        '''
        x_extrap = np.arange(min(start_wl, x.min()), max(end_wl, x.max()), abs(x[1] - x[0]))
        x = np.concatenate(([x_extrap[0]], x, [x_extrap[-1]]))

        if type(buffer) in (int, float):
            if buffer == 0:
                buffer = y.min()
            y = np.concatenate(([buffer], y, [buffer]))

        elif buffer == True:
            y = np.concatenate(([y[0]], y, [y[-1]]))

        else:
            y = np.concatenate(([np.nan], y, [np.nan]))
        
        y_extrap = np.interp(x_extrap, x, y)
    
        x, y = x_extrap, y_extrap
    
    y_trunc = y[np.where(x >= start_wl)]
    x_trunc = x[np.where(x >= start_wl)]
    y_trunc = y_trunc[np.where(x_trunc <= end_wl)]
    x_trunc = x_trunc[np.where(x_trunc <= end_wl)]
    
    if reverse == True:
        x_trunc = x_trunc[::-1]
        y_trunc = y_trunc[::-1]
        
    return x_trunc, y_trunc

def wl_to_wn(wl, laser_wl = 633):
    '''
    Converts measured wavelength (in nm) to Raman shift (in cm^-1), given laser excitation
    Parameters:
        wl: wavelength in nm (int, float or numpy array)
        laser_wl: wavelength of excitation laser (int or float)
    '''
    wl_energy = (1/(wl*1e-9))/100 #converts nm to cm-1
    laser_wl_energy = (1/(laser_wl*1e-9))/100
    wn = laser_wl_energy - wl_energy
    return wn

def wn_to_wl(wn, laser_wl = 633):
    '''
    Converts Raman shift (in cm^-1) to measured wavelength (in nm), given laser excitation
    Parameters:
        wn: Raman shift in wavenumbers (int, float or numpy array)
        laser_wl: wavelength of excitation laser (int or float)
    '''
    laser_wl_energy = (1/(laser_wl*1e-9))/100#calculate laser energy in cm^-1
    wl_energy = laser_wl_energy - wn#calculate absolute energy (in cm^-1) of Raman-shifted photon
    
    wl = 1e9/(wl_energy*100) #converts absolute energy (cm-1) to wavelength (nm)
    
    return wl

def remove_cosmic_rays(y, threshold = 3, cutoff = 1500, fs = 60000, max_iterations = 10, **kwargs):
    '''
    a way of removing cosmic rays from spectra. Mainly tested with Dark-Field
    spectra, as the spikiness of Raman makes it very difficult to do simply.
    
    thresh: the height above the noise level a given data point should be 
            to be considered a cosmic ray. Lower values will remove smaller cosmic rays,
            but may start to remove higher parts of the noise if too low.
    smooth: the 'sigma' value used to smooth the spectrum,
            see scipy.ndimage.gaussian_filter. Should be high enough to
            so that the shape of the spectrum is conserved, but the cosmic ray
            is almost gone. 
    max_iterations: 
        maximum iterations. Shouldn't matter how high it is as most spectra
        are done in 1-3.
    
    '''
    _len = len(y)
    y_clean = np.copy(y) # prevent modification in place
    
    for i in range(max_iterations): 
        #noise_spectrum = y_clean/sp.ndimage.gaussian_filter(y_clean, smoothing_factor)
        y_noise = y_clean/butter_lowpass_filt_filt(y, cutoff, fs, **kwargs)
        # ^ should be a flat, noisy line, with a large spike where there's
        # a cosmic ray.
        noise_level = np.sqrt(np.var(y_noise))
        # average deviation of a datapoint from the mean
        mean_noise = y_noise.mean() # should be == 1
        spikes = np.arange(_len)[y_noise > mean_noise + (threshold*noise_level)]
        # the indices of the datapoints that are above the threshold
       
        # now we add all data points to either side of the spike that are 
        # above the noise level (but not necessarily the thresh*noise_level)
        ray_indices = set()

        for spike in spikes:
            for side in (-1, 1): # left and right
                step = 0

                while 0 <= (coord := spike + (side*step)) <= _len - 1:
                    # staying in the spectrum
                    
                    if y_noise[coord] > mean_noise + noise_level:
                        ray_indices.add(coord)
                        step += 1
                    else:
                        break

        ray_indices = list(ray_indices) # convert to list for indexing

        if len(ray_indices) > 0: # if there are any cosmic rays
            #y_clean[ray_indices] = sp.ndimage.gaussian_filter(y_clean, smoothing_factor)[ray_indices]
            y_clean[ray_indices] = butter_lowpass_filt_filt(y_clean, cutoff, fs, **kwargs)[ray_indices]
            # replace the regions with the smooothed spectrum
            continue # and repeat, as the smoothed spectrum will still be 
                     # quite affected by the cosmic ray. 
                     
        # until no cosmic rays are found
        return y_clean
    return y_clean

class Spectrum:
    '''
    Object containing xy data and functions for general spectral analysis
    args can be:
        y data (n-dimensional list or array)
        x and y data (lists and/or arrays of equal length; x must be 1D and specified first; y can be n-dimensional)
        h5 dataset object (must be open)
        open h5 dataset (open h5 dataset object) and its name (str)
    these can also be specified explicitly as keyword arguments
    additional keyword args:
        y_smooth: smoothed y spectrum
        rc_params: plot style parameters with which to update plt.rcParams, if desired
        raman_excitation: excitation wavelength with which to convert wavelength to wavenumber
            NB: leave raman_excitation = None if x input is already in wavenumbers
        x_min, x_max: x-axis values between which to truncate the spectrum (both x and y), if desired
            self.x, self.y will be the truncated spectra
            original x, y are copied and saved as self.x_raw and self.y_raw
    '''
    def __init__(self, *args, x = None, y = None, y_smooth = None, dset = None, name = None, rc_params = None, 
                 x_lim = None, x_min = None, x_max = None, attrs = None, raman_excitation = None, referenced = True, 
                 **kwargs):
        
        self.x = x
        self.y = y
        self.y_smooth = y_smooth
        self.dset = dset
        self.name = name
        self.raman_excitation = raman_excitation
        
        if rc_params is None:
            self.rc_params = plt.rcParams

        else:
            self.rc_params = rc_params

        '''
        Next few blocks auto-identify which combination of possible args (x, y, dset, name) has bee provided
        Useful for quick, lazy creation of Spectrum object
        '''

        if len(args) == 1:
            if type(args[0]) in [list, np.ndarray]:#if only y data provided
                self.y = args[0]
            
            elif type(args[0]) == h5py._hl.dataset.Dataset:#if only open h5 dataset provided
                self.dset = args[0]
                self.name = self.dset.name.split('/')[-1]#extract name from dataset

            elif type(args[0]) == h5py._hl.group.Group:#if h5 group provided by mistake
                assert type(args[0]) == h5py._hl.dataset.Dataset, f'{args[0].name} is an h5 group, not a dataset; please provide a dataset instead'
            
        elif len(args) == 2:
            if all([type(arg) in [list, np.ndarray] for arg in args]):#if x and y data provided
                self.x, self.y = args
                
            else:#if h5 dset and spectrum are provided
                for arg in args:
                    if type(arg) == h5py._hl.dataset.Dataset:
                        self.dset = arg
                        
                    elif type(arg) == str:
                        self.name = arg

        '''
        !!! In future, modify to auto-identify/distinguish x and y and allow specifying x, y, name as non-keyword args
        !!! Also add auto-detection for rc_params as non keyword arg
        '''

        if self.dset is not None:
            dset_attrs = self.dset.attrs

            if attrs is not None:
                dset_attrs.update(attrs)
            
            attrs = dset_attrs
        
            if self.y is None:
                self.y = self.dset[()]
        
            if self.x is None:
                self.x = attrs.get('wavelengths', None)
        
        assert (self.y is not None), 'Please specify some data'
        assert (self.x is not None), 'Please specify an x axis'

        if self.raman_excitation is not None:
            self.x_wl = self.x.copy()
            self.x = wl_to_wn(self.x_wl, self.raman_excitation)

        if attrs is not None and attrs is not False:#if attrs is False, do not copy h5 dataset attrs
            for key, attr in attrs.items():
                attr_name = '_'.join(key.split())#in case attr name contains whitespace
                attr_name = attr_name.lower()#de-capitalise everything
                setattr(self, attr_name, attr)#update object attrs with additonal metadata, if any

        if x_lim is None:
            x_lim = [self.x.min(), self.x.max()]

        if x_min is not None:
            x_lim[0] = x_min

        if x_max is not None:
            x_lim[1] = x_max

        self.x_lim = x_lim

        if referenced == False:
            self.bg_and_ref()

        self.x_raw = self.x.copy()
        self.y_raw = self.y.copy()

        self.x, self.y = truncate_spectrum(self.x, self.y, *self.x_lim)


    def bg_and_ref(self, background = None, reference = None):
        if background is None:
            if 'background' in self.__dict__.keys():
                background = self.background
            assert background is not None, 'background not found; please specify'

        if reference is None:
            if 'reference' in self.__dict__.keys():
                reference = self.reference
            assert reference is not None, 'reference not found; please specify'

        self.y = (self.y - background)/(reference - background)

        if 'Y' in self.__dict__.keys():
            #in case spectrum is 2D
            self.Y = (self.Y - background)/(reference - background)

    def normalise(self, norm_range=[0,1]):
        norm_diff = norm_range[1] - norm_range[0]
        self.y_norm = self.y - self.y.min()
        self.y_norm = (self.y_norm/self.y_norm.max()) * norm_diff
        self.y_norm = self.y_norm + norm_range[0]


    def plot(self, ax = None, y_ticks = True, y_label = 'Intensity', x_label = 'Wavelength (nm)', 
             rc_params = None, title = False, **kwargs):

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

        x, y = self.x, self.y
        ax.plot(x, y, **kwargs)

        if y_ticks == False:
            ax.set_yticks([])

        ax.set_ylabel(y_label)
        ax.set_xlabel(x_label)
        ax.set_xlim(x.min(), x.max())

        if title == True:
            ax.set_title(self.name)

        if external_ax == False:#if no axes were provided, show plot
            plt.show()
            plt.rcParams.update(old_rc_params)

    def scale_x(self, x_scale, x_shift):
        self.x *= x_scale
        self.x += x_shift

    def truncate(self, start_x, end_x, buffer=False):
        if start_x is None:
            start_x = self.x.min()
        if end_x is None:
            end_x = self.x.max()
        self.x, self.y = truncate_spectrum(self.x, self.y, start_wl = start_x, end_wl = end_x, buffer=False)


class Timescan(Spectrum):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.Y = self.y.copy()
        assert len(self.Y.shape) == 2, f'Input data should be a 2D array; current array shape is {self.Y.shape}'

        self.y = np.average(self.Y, axis = 0)# average of Y data, for 1D plotting
        self.t_raw = np.arange(self.Y.shape[0])

    def determine_v_lims(self, min_std = 0.5, max_std = 4, ignore_vlims = False, **kwargs):
        '''
        Calculates appropriate intensity limits for 2D plot of timescan, based on frequency distribution of intensities.
        !!! add more comments
        '''

        Y_flat = self.Y.flatten()

        if ignore_vlims == True:
            v_min = Y_flat.min()
            v_max = Y_flat.max()

        frequencies, bins = np.histogram(Y_flat, bins = 1000, range = (0, Y_flat.max()), density = False)
        bin_centres = np.linspace(np.average([bins[0], bins[1]]), np.average([bins[-2], bins[-1]]), len(frequencies))
        
        mode = bin_centres[frequencies.argmax()]
        std = np.std(Y_flat)
        
        if max_std == 0 or max_std is None:
            v_max = Y_flat.max()
        else:
            v_max = mode + max_std*std

        if min_std == 0 or min_std is None:
            v_min = 0
        else:
            v_min = max(mode - min_std*std, mode)


        print(v_min, v_max)

        
        self.v_min = v_min
        self.v_max = v_max


    def plot_timescan(self, ax = None, y_label = None, rc_params = timescan_params, x_lim = None, title = None,
                      x_scale = 1, x_shift = 0, x_label = 'Wavelength (nm)', figsize = None, save_fig = False, 
                      img_name = None,
                      plot_averages = False, avg_chunks = 10, avg_color = 'white', show = True, cmap = 'inferno', 
                      **kwargs):
        '''
        !!! needs docstring
        '''

        old_rc_params = plt.rcParams.copy()#saves initial rcParams before overwriting them

        
        if ax is None:
            if self.rc_params is not None:
                plt.rcParams.update(self.rc_params)#use rc params specified with object
            if rc_params is not None:
                plt.rcParams.update(rc_params)#unless overridden when calling the function

            if figsize is None:
                figsize = plt.rcParams['figure.figsize']

            fig, ax = plt.subplots()#if no axes provided, create some
            external_ax = False

        else:
            external_ax = True

        x = self.x
        x = x*x_scale + x_shift

        t = self.t_raw

        if y_label == False:

            y_label = ''

        if 'exposure' in self.__dict__.keys():
            if y_label is None:
                y_label = 'Time (s)'

        else:
            self.exposure = 1
            if y_label is None:
                y_label = 'Spectrum Number'

        t = t*self.exposure
        self.t = t

        Y = np.vstack(self.Y)

        self.determine_v_lims(**kwargs)

        if 'v_min' in kwargs.keys():
            self.v_min = kwargs['v_min']

        if 'v_max' in kwargs.keys():
            self.v_max = kwargs['v_max']

        ax.pcolormesh(x, t, Y, cmap = cmap, shading = 'auto', 
                      norm = mpl.colors.LogNorm(vmin = self.v_min, vmax = self.v_max))

        if x_lim is None:
            x_lim = self.x_lim

        if x_lim is not None and x_lim is not False:
            ax.set_xlim(*x_lim)

        if plot_averages == True:
            Y_arr = np.split(self.Y, avg_chunks)
            time_inc = len(t)*self.exposure/avg_chunks
            
            for n, Y_i in enumerate(Y_arr):
                y_i = np.sum(Y_i, axis = 0)
                y_i = y_i - y_i.min()
                y_i = y_i/y_i.max()
                y_i *= time_inc*0.95
                y_i += n*time_inc
            
                ax.plot(x, y_i, color = 'k', lw = 3, alpha = 0.5)
                ax.plot(x, y_i, color = avg_color, alpha = 0.85)
                ax.set_yticks(np.arange(t.min(), t.max(), time_inc))

        ax.set_ylim(t.min(), t.max())
        ax.set_ylabel(y_label)

        if title is not None:
            ax.set_title(title)

        if external_ax == False:
            if self.raman_excitation is not None and x_label == 'Wavelength (nm)':
                x_label = 'Raman Shift (cm$^{-1}$)'
                
            ax.set_xlabel(x_label)            

            if save_fig == True:
                if img_name is None:
                    img_name = 'timescan.png'

                fig.savefig(img_name, bbox_inches = 'tight')

            if show == True:
                plt.show()
            else:
                plt.close('all')
                
            plt.rcParams.update(old_rc_params)#put rcParams back to normal when done

        def truncate(self, start_x, end_x, buffer=False):
            self.x, self.Y = truncate_spectrum(self.x, self.Y, start_wl = start_x, end_wl = end_x, buffer=False)
            self.y = np.average(self.Y, axis = 0)

