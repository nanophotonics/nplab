from __future__ import division
from __future__ import print_function
from builtins import range
from builtins import object
from past.utils import old_div
__author__ = 'alansanders'

import os
import numpy as np
#import numpy.ma as ma
from nputils.data_loader import load_data
from nputils import get_roi, get_nearest
from .colour_reconstruction_image import colour_reconstruction as cr
from np_analysis_methods.centroid_fitting import fit_centroid
from scipy.optimize import curve_fit
from itertools import product

h = 6.63e-34
c = 3e8
e = 1.6e-19


class HyperspectralImage(object):
    '''Applies to both 2D and 3D hyperspectral images, however some methods
    are limited to specific cases and will raise assertion errors when
    miscalled.'''

    def __init__(self, file_location,
                 data_location='hyperspectral scans',
                 scan_id=None):
        super(HyperspectralImage, self).__init__()
        self.f, self.scan = load_data(file_location, data_location, scan_id)
        self._load_data(self.scan)
        self._load_calibrations()

    def __del__(self):
        if self.f is not None:
            self.f.close()

    def _load_data(self, scan):
        # ROI data
        self._rescale = False
        self._x_lims = (-np.inf, np.inf)
        self._x_roi = np.s_[:]
        self._y_lims = (-np.inf, np.inf)
        self._y_roi = np.s_[:]
        self._z_lims = (-np.inf, np.inf)
        self._z_roi = np.s_[:]
        self._wavelength_lims = (-np.inf, np.inf)
        self._wavelength_roi = np.s_[:]
        self._wavelength2_lims = (-np.inf, np.inf)
        self._wavelength2_roi = np.s_[:]
        # Other attributes
        self.attrs = dict(scan.attrs)
        if 'num_spectrometers' not in self.attrs:
            self.attrs['num_spectrometers'] = len([s for s in list(scan.keys()) if 'spectra' in s])

    # ROI properties
    @property
    def x_lims(self):
        return self._x_lims
    @x_lims.setter
    def x_lims(self, value):
        assert len(value) == 2, 'Value must have 2 elements'
        self._x_lims = value
        a = self.scan['x'][()]
        a = (a - (a.min()+a.max())/2.0)
        self._x_roi = get_roi(a, value[0], value[1])
    @property
    def y_lims(self):
        return self._y_lims
    @y_lims.setter
    def y_lims(self, value):
        assert len(value) == 2, 'Value must have 2 elements'
        self._y_lims = value
        a = self.scan['y'][()]
        a = (a - (a.min()+a.max())/2.0)
        self._y_roi = get_roi(a, value[0], value[1])
    @property
    def z_lims(self):
        return self._z_lims
    @z_lims.setter
    def z_lims(self, value):
        assert len(value) == 2, 'Value must have 2 elements'
        if 'z' in self.scan:
            self._z_lims = value
            a = self.scan['z'][()]
            a = (a - (a.min()+a.max())/2.0)
            self._z_roi = get_roi(a, value[0], value[1])
        else:
            print('There is no z dataset')
    @property
    def wavelength_lims(self):
        return self._wavelength_lims
    @wavelength_lims.setter
    def wavelength_lims(self, value):
        assert len(value) == 2, 'Value must have 2 elements'
        self._wavelength_lims = value
        self._wavelength_roi = get_roi(self.scan['wavelength'][()], value[0], value[1])
    @property
    def wavelength2_lims(self):
        return self._wavelength2_lims
    @wavelength2_lims.setter
    def wavelength2_lims(self, value):
        assert len(value) == 2, 'Value must have 2 elements'
        if 'wavelength2' in self.scan:
            self._wavelength2_lims = value
            self._wavelength2_roi = get_roi(self.scan['wavelength2'][()], value[0], value[1])
        else:
            print('There is no wavelength2 dataset')
    # Axes data properties
    @property
    def x(self):
        a = self.scan['x'][()]
        a = (a - (a.min()+a.max())/2.0)
        a = a[self._x_roi]
        if self._rescale:
            a = (a - (a.min()+a.max())/2.0)
        return a
    @property
    def y(self):
        a = self.scan['y'][()]
        a = (a - (a.min()+a.max())/2.0)
        a = a[self._y_roi]
        if self._rescale:
            a = (a - (a.min()+a.max())/2.0)
        return a
    @property
    def z(self):
        if 'z' in self.scan:
            a = self.scan['z'][()]
            a = (a - (a.min()+a.max())/2.0)
            a = a[self._z_roi]
            if self._rescale:
                a = (a - (a.min()+a.max())/2.0)
            return a
        else:
            print('There is no z dataset')
    @property
    def wavelength(self): return self.scan['wavelength'][self._wavelength_roi]
    @property
    def energy(self): return old_div(1e9*(old_div(h*c,self.wavelength)),e)
    @property
    def wavelength2(self):
        if 'wavelength2' in self.scan:
            return self.scan['wavelength2'][self._wavelength2_roi]
        else:
            print('There is no wavelength2 dataset')
    @property
    def energy2(self):
        if 'wavelength2' in self.scan:
            return old_div(1e9*(old_div(h*c,self.wavelength2)),e)
        else:
            print('There is no wavelength2 dataset so cannot return energy2')
    # Data properties
    @property
    def spectra(self):
        ndim = len(self.scan['spectra'].shape)-1
        if ndim == 2:
            roi = np.s_[self._x_roi, self._y_roi, self._wavelength_roi]
        elif ndim == 3:
            roi = np.s_[self._x_roi, self._y_roi, self._z_roi, self._wavelength_roi]
        a = self.scan['spectra'][roi]
        a = np.where(np.isfinite(a), a, 0.0)
        return a
    @property
    def spectra2(self):
        if 'wavelength2' in self.scan and 'spectra2' in self.scan:
            ndim = len(self.scan['spectra2'].shape)-1
            if ndim == 2:
                roi = np.s_[self._x_roi, self._y_roi, self._wavelength2_roi]
            elif ndim == 3:
                roi = np.s_[self._x_roi, self._y_roi, self._z_roi, self._wavelength2_roi]
            a = self.scan['spectra2'][roi]
            a = np.where(np.isfinite(a), a, 0.0)
            return a
        else:
            print('There is no spectra2 dataset')

    def _load_calibrations(self):
        self.fitfunc = lambda x,a,b,c: a*x**2 + b*x + c
        self._px1 = (4.30671055e-13, -1.64351619e-10, -1.45004691e-09)
        self._py1 = (-4.41782891e-13, 8.89024179e-10, -3.43640870e-07)
        self._px2 = (4.39995226e-13, -1.77391339e-10, 2.86613916e-09)
        self._py2 = (-4.46213678e-13, 8.94792646e-10, -3.45533004e-07)
        self._dx1, self._dy1 = self._get_offset(self.wavelength, polarisation=1)
        self._dx2, self._dy2 = self._get_offset(self.wavelength, polarisation=2)

    def apply_corrections(self, a, dataset):
        name = dataset.name.rsplit('/', 1)[1]
        if name in ['x', 'y', 'z']:
            a = (a - (a.min()+a.max())/2.0)
        elif 'spectra' in name:
            a = np.where(np.isfinite(a), a, 0.0)
        return a

    def get_spectra(self, polarisation=1):
        if polarisation == 2:
            assert self.attrs['num_spectrometers'] == 2, 'polarisation does not exist'
        data = self.spectra2 if polarisation == 2 else self.spectra
        wavelength = self.wavelength2 if polarisation == 2 else self.wavelength
        return wavelength, data

    def get_image(self, wl, polarisation=1, axis=2, axslice=None):
        """Returns an image at a given wavelength (layer slice)."""
        wavelength, spectra = self.get_spectra(polarisation)
        if spectra.ndim == 3:
            return spectra[:,:, get_nearest(wavelength, wl)]
        elif spectra.ndim > 3:
            assert axslice is not None, 'slice argument required for 3d images'
            return spectra[:,:, axslice, get_nearest(wavelength, wl)]
        else:
            return None

    def integrate_spectra(self, xlims=None, ylims=None, polarisation=1, axslice=None, return_patch=False):
        wavelength, spectra = self.get_spectra(polarisation)
        if spectra.ndim > 3:
            assert axslice is not None, 'slice argument required for 3d images'
        if xlims is None:
            x_roi = np.s_[:]
        else:
            x_roi = get_roi(self.x, xlims[0], xlims[1])
        if ylims is None:
            y_roi = np.s_[:]
        else:
            y_roi = get_roi(self.y, ylims[0], ylims[1])
        spectra = spectra[x_roi,y_roi,axslice,:] if spectra.ndim > 3 else spectra[x_roi,y_roi,:]
        spectrum = np.mean(spectra, axis=(0,1))
        if return_patch:
            x, y = (self.x[x_roi], self.y[y_roi])
            print('averaged over a %dx%d grid' % (len(x), len(y)))
            patch = np.array([x.min(), y.min(), x.max()-x.min(), y.max()-y.min()])
            return wavelength, spectrum, patch
        else:
            return wavelength, spectrum

    def get_line_spectra(self, axis, line, polarisation=1):
        wavelength, spectra = self.get_spectra(polarisation)
        if axis=='x': line_spectra = np.array(spectra[:,line,:])
        elif axis=='y': line_spectra = np.array(spectra[line,:,:])
        return line_spectra

    def reconstruct_colour_image(self, polarisation=1, norm=True, axslice=None):
        """Take a hyperspectral image and convert it to an rgb image."""
        wavelength, spectra = self.get_spectra(polarisation)
        if spectra.ndim > 3:
            assert axslice is not None, 'slice argument required for 3d images'
            spectra = spectra[:,:,axslice,:]
        img = cr.reconstruct_colour_image(spectra, wavelength, norm)
        return img

    def construct_colour_map(self, polarisation=1, norm=True, axslice=None):
        """Take a hyperspectral image and convert it to an colour map of
        average wavelength."""
        wavelength, spectra = self.get_spectra(polarisation)
        if spectra.ndim > 3:
            assert axslice is not None, 'slice argument required for 3d images'
            spectra = spectra[:,:,axslice,:]
        h, w, s = spectra.shape
        img = np.zeros((h,w))
        for pos in product(list(range(h)), list(range(w))):
            i,j = pos
            spectrum = spectra[i,j,:]
            threshold = spectrum < 0.01*spectrum.max()
            spectrum = np.ma.array(spectrum, mask=threshold)
            wl = np.ma.array(wavelength, mask=threshold)
            img[i,j] = np.ma.average(wl, axis=-1, weights=spectrum)
        return img

    def create_calibration(self, unit='SI', polarisation=1, wl_step=5, axslice=None):
        wavelength, spectra = self.get_spectra(polarisation)
        wavelength = wavelength[::wl_step]
        if unit=='pixel':
            x = np.arange(self.x.size)
            y = np.arange(self.y.size)
        elif unit=='SI':
            x = self.x
            y = self.y
        # for all wavelengths fit a centroid to create an array of x0s, y0s
        x0s = np.zeros_like(wavelength)
        y0s = np.zeros_like(wavelength)
        for i,wl in enumerate(wavelength):
            img = self.get_image(wl, polarisation=1, axslice=axslice)
            x0, y0 = fit_centroid(img, x, y)
            x0s[i] = x0
            y0s[i] = y0
        roi = slice(np.min(np.where(500 < wavelength)), np.max(np.where(wavelength < 1000)))
        # fit the functions wavelength vs x0, y0 for wl to offset correction
        self._fit_calibration(wavelength, x0s, 'x%d'%polarisation, mask=roi)
        self._fit_calibration(wavelength, y0s, 'y%d'%polarisation, mask=roi)
        return wavelength, x0s, y0s

    def _fit_calibration(self, x, y, label, mask=None):
        '''This is an arbitrary quadratic fit function with no dependencies on
        the data supplied, i.e. it is indepdent of the units, pixels or SI.'''
        if mask is not None:
            x = x[mask]
            y = y[mask]
        p, cov = curve_fit(self.fitfunc, x, y)
        setattr(self, '_p'+label, p)
        return p, cov

    def save_calibration(self):
        with open('/Users/alansanders/Desktop/calibration.txt', 'w') as f:
            f.write('p{0:s}: {1}\n'.format('px1', self.px1))
            f.write('p{0:s}: {1}\n'.format('py1', self.py1))
            f.write('p{0:s}: {1}\n'.format('px2', self.px2))
            f.write('p{0:s}: {1}\n'.format('py2', self.py2))

    def load_calibration(self):
        with open('/Users/alansanders/Desktop/calibration.txt', 'w') as f:
            lines = [l.strip() for l in f.readlines()]
            ps = [s.split(': ')[1] for s in lines]
            self._px1 = (ps[0])
            self._py1 = (ps[1])
            self._px2 = (ps[2])
            self._py2 = (ps[3])

    def _get_offset(self, wavelength, polarisation=1, unit='SI'):
        '''Reference wavelength is 500 nm. The function returns how much
        an image should be shifted by in the (dx,dy) direction for each
        wavelength. The units of (dx,dy) can be specified but are based upon
        the assumption that the calibration was done in SI units for
        standardisation between different sized grids.'''
        xr = self.fitfunc(500, *getattr(self, '_px%d'%polarisation))
        yr = self.fitfunc(500, *getattr(self, '_py%d'%polarisation))
        #wavelength, data = self.get_data(polarisation)
        xo = self.fitfunc(wavelength, *getattr(self, '_px%d'%polarisation))
        yo = self.fitfunc(wavelength, *getattr(self, '_py%d'%polarisation))

        if unit=='SI':
            dx = xo-xr
            dy = yo-yr
            return dx, dy
        elif unit=='pixel':
            # now require SI to pixel conversions
            # find out which pixel is closest to xo, yo
            dpx = [abs(self.x - i).argmin() for i in xo] - abs(self.x - xr).argmin()
            dpy = [abs(self.y - i).argmin() for i in yo] - abs(self.y - yr).argmin()
            return dpx, dpy

    def correct_aberrations(self, axslice=None):
        self._correct_chromatic_aberration(polarisation=1, axslice=axslice)
        if self.num_spectrometers==2:
            self._correct_chromatic_aberration(polarisation=2, axslice=axslice)

    def _correct_chromatic_aberration(self, polarisation=1, axslice=None):
        wavelength, spectra = self.get_spectra(polarisation)
        xo, yo = self._get_offset(wavelength, unit='pixel')
        s = spectra.shape
        #print 'starting data shape:', s
        s11 = old_div(s[0],2)
        s12 = s11 + s[0]
        s21 = old_div(s[1],2)
        s22 = s21 + s[1]
        # a 1.6 factor is used to go just beyond the physical maximum shift of
        # 50% of the current view
        if spectra.ndim > 3:
            big_img = np.zeros((1.6*s[-4], 1.6*s[-3], s[-2], s[-1]))
        else:
            big_img = np.zeros((1.6*s[-3], 1.6*s[-2], s[-1]))
        big_img[:] = np.nan
        x_step = self.x[1] - self.x[0]
        x = x_step * np.arange(big_img.shape[0])
        x -= x[old_div(x.size,2)]
        y_step = self.y[1] - self.y[0]
        y = y_step * np.arange(big_img.shape[1])
        y -= y[old_div(y.size,2)]
        for i in range(s[-1]): # for each wavelength (last dimension)
            dx = int(round(xo[i]))
            dy = int(round(yo[i]))
            #print 'shifts:', dx, dy
            #print 'central region:', s12-s11, s22-s21
            #print big_img[s11-dx:s12-dx, s21-dy:s22-dy, i].shape, data[:,:,i].shape
            if spectra.ndim > 3:
                big_img[s11-dx:s12-dx, s21-dy:s22-dy, :, i] = spectra[:,:,:,i]
            else:
                big_img[s11-dx:s12-dx, s21-dy:s22-dy, i] = spectra[:,:,i]
        data = np.nan_to_num(big_img)
        # update data - note that this will invalidate the other polarisation data
        # and that this data is temporary and will be overwritten if ROI changes
        # are called
        setattr(self, 'spectra2' if polarisation==2 else 'spectra', spectra)
        self.x = x
        self.y = y


if __name__ == '__main__':
    hsimg = HyperspectralImage('/Users/alansanders/Desktop/Data/2014/08. Aug/26/data.hdf5','hyperspectral scans', 2)