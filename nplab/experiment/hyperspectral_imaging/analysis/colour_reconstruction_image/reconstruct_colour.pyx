# -*- coding: utf-8 -*-
"""
Created on Tue May 13 16:08:24 2014

@author: alansanders
"""

import colorpy.ciexyz as cp
import colorpy.colormodels as cpm
import numpy as np
from scipy import interpolate

cimport cython
cimport numpy as np


#np.ndarray[np.uint8_t, ndim=3]
cpdef reconstruct_colour_image(np.ndarray[np.float64_t, ndim=3] data,
                                        np.ndarray[np.float64_t, ndim=1] wavelength,
                                        norm):
    '''Take a hyperspectral image and convert it to an rgb image.'''
    cdef unsigned int n_rows, n_cols, n_pnts
    n_rows, n_cols, n_pnts = (<object> data).shape
    img_array = np.zeros((n_rows, n_cols, 4), 'float32')
    cdef np.ndarray[np.float64_t, ndim=1] spectrum    
    
    for i in range(n_rows):    # for every pixel:
        for j in range(n_cols):
            spectrum = data[i,j,:]
            img_array[i,j] = get_colour_from_spectrum(wavelength, spectrum)
            if norm == True:
                intensity = np.sum(data[i,j,:]) / np.amax(np.sum(data, axis=2))
                img_array[i,j,3] = intensity
    
    img_array = img_array.transpose((1,0,2))
    img = img_array
    return img


cpdef get_colour_from_spectrum(wavelength, spectrum):
    '''Convert a spectrum into an rgb colour vector.'''
    interpolated_spectrum = cp.empty_spectrum()
    f = interpolate.interp1d(wavelength, spectrum, kind='linear', bounds_error=False, fill_value=0.)
    size = interpolated_spectrum.shape[0]
    interpolated_spectrum[:,1] = f(interpolated_spectrum[:,0])
    xyz = cp.xyz_from_spectrum(interpolated_spectrum[0:size,:])
    rgb = cpm.rgb_from_xyz(xyz)
    irgb = cpm.irgb_from_rgb(rgb)
    c = np.concatenate((rgb/rgb.max(), [1.])).astype(np.float32)
    return c