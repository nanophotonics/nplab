__author__ = 'alansanders'
import re
from functools import cached_property
from pathlib import Path

import h5py
import numpy as np
from scipy.ndimage import gaussian_filter

H5_TEMPLATE = r'\S*(\d{4})-(\d{2})-(\d{2})\S*.h5' 
# allow somestuff1_2021-01-05_someotherstuff.h5

def load_h5(location='.'):
    '''return the latest h5 in a given directory. If location is left blank,
    loads the latest file in the current directory.'''
    path = Path(location)
    candidates_dates = [(f, [int(m) for m in match.groups()]) for f in path.iterdir()\
                        if (match := re.match(H5_TEMPLATE, f.name))]
    if candidates_dates:
        return h5py.File(path / max(candidates_dates, key=lambda cd: cd[1])[0], 'r') 
    else:
        raise ValueError('No suitable h5 file found')
    
def latest_scan(file):
    '''returns the last ParticleScannerScan in a file'''
    return file[max(file, key=lambda x: int(x.split('_')[-1])
                    if x.startswith('ParticleScannerScan') else -1)]

class Spectrum(np.ndarray):
    '''acts a an ndarray, but has a wavelengths attribute,
    and several useful methods for spectra. Can be 1 or 2d (time series/z-scan)'''
    
    def __new__(cls, spectrum, wavelengths, *args, **kwargs):
        '''boilerplate numpy subclassing'''
        assert len(wavelengths) == np.shape(spectrum)[-1]

        obj = np.asarray(spectrum).view(cls)
        obj.wavelengths = np.asarray(wavelengths)
        return obj

    def __array_finalize__(self, obj):
        '''boilerplate numpy subclassing'''
        if obj is None:
            return
        if not obj.shape:
            return np.array(obj)
        self.wavelengths = getattr(
            obj, 'wavelengths', np.arange(obj.shape[-1]))

    @classmethod
    def from_h5(cls, dataset):
        '''create instance using a h5 dataset.
        will background-subtract and reference the spectrum if these
        attributes are saved'''    
        attrs = dataset.attrs
        ref = attrs.get('reference', 1)
        bg = attrs.get('background', 0)
        return cls((dataset[()]-bg)/(ref-bg), dataset.attrs['wavelengths'])

    @property
    def wl(self):
        '''convenient for accessing wavelengths'''
        return self.wavelengths

    @wl.setter
    def wl(self, value):
        '''convenient for accessing wavelengths'''
        self.wavelengths = np.array(value)

    @property
    def x(self):
        '''abstraction of x axis for using shifts or wavelengths'''
        return self.wavelengths # wavelengths unless subclassed

    def split(self, lower=-np.inf, upper=np.inf):
        '''returns the spectrum between the upper and lower bounds'''
        if upper < lower:
            upper, lower = lower, upper
        condition = (lower <= self.x) & (self.x < upper)  
        # '<=' allows recombination of an array into the original
        return self.__class__(self.T[condition].T, self.x[condition])

    def norm(self):
        '''return an spectrum divided by its largest value'''
        return self.__class__(self/self.ravel().max(), self.x)
    
    def squash(self):
        '''condense a time_series into one spectrum'''
        return self.__class__(self.sum(axis=0), self.x)
    
    def smooth(self, sigma):
        '''smooth using scipy.ndimage.guassian_smooth'''
        return self.__class__(gaussian_filter(self, sigma), self.x)
    
    def remove_cosmic_ray(self,
                          thresh=5,
                          smooth=30,
                          max_iterations=10):
        '''wrapper around remove_cosmic_ray to allow 2d or 1d spectra
        to be passed'''
        func = lambda s: remove_cosmic_ray(s,
                                           thresh=thresh,
                                           smooth=smooth,
                                           max_iterations=max_iterations)
        if len(self.shape) == 2:
            return self.__class__([func(s) for s in self], 
                                  self.x,)
        return self.__class__(func(self), self.x)

class RamanSpectrum(Spectrum):
    '''
    Uses shifts as its x axis. These are the values used in split() etc. 
    When creating, either supply shifts directly, or they'll be calculated
    the first time they're accessed using wavelengths and laser_wavelength.
    
    To use with a different laser wavelength, change the class attribute 
    after importing:
    >>> RamanSpectrum.laser_wavelength = 785.
    
    if you frequently use two wavelengths in the same analysis, create a 
    subclass:
    >>> class RamanSpectrum785(RamanSpectrum):
            laser_wavelength = 785.
        class RamanSpectrum532(RamanSpectrum):
            laser_wavelength = 532.
        
    '''
    
    laser_wavelength = 632.8
    def __new__(cls, 
                spectrum,
                shifts=None,
                wavelengths=None,
                *args, **kwargs):
        assert not (shifts is None and wavelengths is None),\
        'must supply shifts or wavelengths'
        obj = np.asarray(spectrum).view(cls)
        if wavelengths is not None:
            wavelengths = np.asarray(wavelengths)
        obj.wavelengths = wavelengths
        if shifts is not None:
            shifts = np.asarray(shifts)
        obj._shifts = shifts
        
        obj.laser_wavelength = cls.laser_wavelength 
        # stops existing instances' laser_wavelength being changed by changing
        # the class attribute 
        return obj

    def __array_finalize__(self, obj):

        if obj is None:
            return
        if not obj.shape:
            return np.array(obj)
        self.wavelengths = getattr(obj,
                                   'wavelengths',
                                   np.arange(obj.shape[-1]))
        self._shifts = getattr(obj, '_shifts', None)
        
    @classmethod
    def from_h5(cls, dataset):
        '''create instance using a h5 dataset.
        will background-subtract and reference the spectrum if these
        attributes are saved'''    
        attrs = dataset.attrs
        ref = attrs.get('reference', 1)
        bg = attrs.get('background', 0)
        return cls((dataset[()]-bg)/(ref-bg), wavelengths=dataset.attrs['wavelengths'])
    
    @cached_property # only ever calculated once per instance
    def shifts(self):
        if self._shifts is None:
            return (1./(self.laser_wavelength*1e-9) - 1./(self.wl*1e-9))/100.
        return self._shifts
    
    @property
    def x(self):
        return self.shifts

def remove_cosmic_ray(spectrum, thresh=5, smooth=30, max_iterations=10):
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
    _len = len(spectrum)
    cleaned = np.copy(spectrum) # prevent modification in place
    
    for i in range(max_iterations): 
        noise_spectrum = cleaned/gaussian_filter(cleaned, smooth)
        # ^ should be a flat, noisy line, with a large spike where there's
        # a cosmic ray.
        noise_level = np.sqrt(np.var(noise_spectrum)) 
        # average deviation of a datapoint from the mean
        mean_noise = noise_spectrum.mean() # should be == 1
        spikes = np.arange(_len)[noise_spectrum > mean_noise+(thresh*noise_level)]
        # the indices of the datapoints that are above the threshold
       
        # now we add all data points to either side of the spike that are 
        # above the noise level (but not necessarily the thresh*noise_level)
        rays = set()
        for spike in spikes:
            for side in (-1, 1): # left and right
                step = 0
                while 0 <= (coord := spike+(side*step)) <= _len-1:
                    # staying in the spectrum
                    
                    if noise_spectrum[coord] > mean_noise + noise_level:
                        rays.add(coord)
                        step += 1
                    else:
                        break
        rays = list(rays) # convert to list for indexing
        if rays: # if there are any cosmic rays
            cleaned[rays] = gaussian_filter(cleaned, smooth)[rays]
            # replace the regions with the smooothed spectrum
            continue # and repeat, as the smoothed spectrum will still be 
                     # quite affected by the cosmic ray. 
                     
        # until no cosmic rays are found
        return cleaned
    return cleaned

if __name__ ==  '__main__':
    import matplotlib.pyplot as plt
    wls = np.linspace(633, 750, 1600)
    spec = np.random.randint(300, 600, size=1600)
    
    rspec = RamanSpectrum(spec, wavelengths=wls)
    
    RamanSpectrum.laser_wavelength = 700
    plt.figure()
    plt.plot(rspec.shifts, rspec, label='shifts')
    rspec2 = RamanSpectrum(spec, wavelengths=wls)
    plt.plot(rspec2.shifts, rspec2, label='center of 700')
    plt.legend()
    