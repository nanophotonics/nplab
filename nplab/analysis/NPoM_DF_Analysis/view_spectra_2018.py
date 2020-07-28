# -*- coding: utf-8 -*-
"""
Created on Thu Jun 26 17:33:15 2014

@author: Richard Bowman

Edited January 2018 

@author Charlie Readman to 
Works with Will's new particle tracking code.
Just place in the same folder as hdf5 data and run - it will auto-detect files with names in "yyyy-mm-dd.h5" format.
Output summary file should be identical to output of old view_spectra code - can be used directly with usual Igor multipeakfitBeta05d code.

"""
from __future__ import division
from __future__ import print_function

from builtins import range
from past.utils import old_div
if __name__ == '__main__':
    print('Importing modules')

import traits
from traits.api import HasTraits, Property, Instance, Float, Range, Array, Int, String, Button, Bool, on_trait_change
import traitsui
from traitsui.api import View, Item, HGroup, VGroup, Tabbed
from traitsui.table_column import ObjectColumn
import threading
import numpy as np
from nplab.utils.traitsui_mpl_qt import MPLFigureEditor
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import h5py
import gaussian_fit
import scipy.ndimage.filters
import scipy.stats
import os
import re

if __name__ == '__main__':
    print('Modules imported\n')
    print('Initialising...\n')

class OverviewViewer(HasTraits):
    figure = Instance(Figure, ())
    scan_number = Range(0,136,0)
    group_number = Range(0,6,6)
    traits_view = View(
                    VGroup(
                        Item(name = "scan_number"),
                        Item(name = "group_number"),
                        Item('figure', editor = MPLFigureEditor(),
                               show_label = False, label = "Last Alignment", springy = True),
                    ),
                    resizable = True, title = "Overview Viewer",
                )
    
    def __init__(self, hdf5file):
        super(OverviewViewer, self).__init__()
        
        if isinstance(hdf5file, h5py.File):
            self._hdf5file = hdf5file
        
        else:
            self._hdf5file=h5py.File(hdf5file)
        self._group_number_changed()
#        self._scan_number_changed()
    
    def __del__(self):
        self._hdf5file.close()
    
    def _group_number_changed(self):
        self._scan_number_changed()
    
    def _scan_number_changed(self):
        
        try:
            
            try:
                g = self._hdf5file["ParticleScannerScan_%d/" % (self.group_number)]
            
            except Exception as e:
                print("error switching to ParticleScannerScan_%d/\n" % (self.group_number))
                raise e
            
            image = g["reconstructed_tiles" % self.scan_number]
            #image2 = g["overview_image_%d_thresholded" % self.scan_number]
            self.replot(image)#, image2)
        
        except:
            print("out of range :(")
    
    def replot(self, image):  #, image2):
        #plot the image on the left
        ax = self.figure.axes
        
        if not ax[0].images:
            ax[0].imshow(image)
            #ax[1].imshow(image2)
        
        else:
            ax[0].images[0].set_array(image)
            #ax[1].images[0].set_array(image2)
        
        canvas = self.figure.canvas
        
        if canvas is not None:
            canvas.draw()
            
class ScanViewer(HasTraits):
    figure = Instance(Figure, ())
    scan_number = Range(0,100000,0)
    group_number = Range(0,6,1)
    use_reference = Bool(True)
    background_subtract = Bool(True)
    reference_threshold = Range(0,200000,10000)
    traits_view = View(
                    VGroup(
                        Item(name="scan_number"),
                        Item(name="group_number"),
                        Item(name="use_reference"),
                        Item(name="reference_threshold"),
                        Item(name="background_subtract"),
                        Item('figure', editor=MPLFigureEditor(),
                               show_label=False, label="Last Alignment",springy=True),
                    ),
                    resizable=True, title="Scan Viewer",
                )
    
    def __init__(self,hdf5file):
        super(ScanViewer, self).__init__()
        
        if isinstance(hdf5file,h5py.Group) or isinstance(hdf5file,h5py.File):
            self._hdf5file = hdf5file
        
        else:
            self._hdf5file=h5py.File(hdf5file)
        
        self.figure.add_axes((0,0,0.5,1))
        self.figure.add_axes((0.5,0,0.5,1))
        self.refresh_data()
#        self._scan_number_changed()
    
    def __del__(self):
        self._hdf5file.close()
    
    @on_trait_change("use_reference,background_subtract,scan_number,group_number")
    
    def refresh_data(self):
        print("switching to scan %d" % self.scan_number)
        
        try:
            g = self._hdf5file["ParticleScannerScan_%d/Particle_%d" % (self.group_number,self.scan_number)]
        
        except Exception as e:
            print("Error switching to ParticleScannerScan_%d/Particle_%d\n" % (self.group_number,self.scan_number))
            print(e)
            return False
        
        image = g['CWL.thumb_image_0']
        zscan = g['alinger.z_scan_0']
        spectrum = np.mean(zscan, axis=0)
        wavelengths = zscan.attrs.get("wavelengths")
        reference = zscan.attrs.get("reference")
        background = zscan.attrs.get("background")
        
        if self.background_subtract or self.use_reference:
            spectrum -= background
        
        if self.use_reference: 
            mask = [r < self.reference_threshold for r in (reference-background)] #mask dodgy pixels
            spectrum = np.ma.masked_array(spectrum, mask=mask)
            reference = np.ma.masked_array(reference, mask=mask)
            wavelengths = np.ma.masked_array(wavelengths, mask=mask)
            background = np.ma.masked_array(background, mask=mask)
            spectrum /= abs(reference - background)+0.001
        
        self.replot(image[old_div(image.shape[0],2)-50:old_div(image.shape[0],2)+50,old_div(image.shape[1],2)-50:old_div(image.shape[1],2)+50,], zscan, wavelengths, spectrum)
    
    def replot(self, image, zscan, wavelengths, spectrum):
        fig = self.figure
        
        if fig is None: return #don't plot to a non-existent figure...
        fig.clf() #clear the plot
        
        ax0=fig.add_axes((0.05,0.53,0.32,0.42)) #plot the overview image
        ax0.imshow(image, extent=(0,1,0,1))#, aspect="equal")
        ax0.plot([0.5,0.5],[0.2,0.8],"w-")
        ax0.plot([0.2,0.8],[0.5,0.5],"w-")
        ax0.get_xaxis().set_visible(False)
        ax0.get_yaxis().set_visible(False)
        ax0.set_title("Particle Image")
        
        ax1=fig.add_axes((0.05,0.08,0.32,0.42)) #plot the z stack
        ax1.imshow(zscan, extent=(wavelengths.min(), wavelengths.max(), -4, 4), aspect="auto", cmap="cubehelix")
        ax1.set_xlabel("Wavelength/nm")
        ax1.set_ylabel("Z/um")        
        
        ax2=fig.add_axes((0.5,0.08,0.47,0.87)) #plot the spectrum
        ax2.plot(wavelengths, spectrum)
        ax2.set_xlabel("Wavelength/nm")
        ax2.set_ylabel("Z-averaged Spectrum")
        
        if self.figure.canvas is not None: self.figure.canvas.draw()

def fit_gaussians_to_z_scan(z_scan, z=None, background=None, threshold=0.2, smoothing_width=1.5):
    """Fit a Gaussian to the spectrometer counts vs Z curve for each spectrometer pixel.
    
    Parameters:
        z_scan: 2D array (will be converted to numpy.ndarray) of spectra vs
            Z, where Z is the first index and wavelength is the second.
        z: 1D array of Z values for each row of z_scan.  If z_scan is an HDF5
            dataset with attribute 'dz', this will be used by default.
        background: 1D array containing a dark spectrum which is subtracted
            from the z_scan.  Defaults to HDF5 attribute 'background' as above.
            
    Return value: spectrum, peak_z, standard_deviation, background, r
        spectrum: peak height for the fitted Gaussian at each wavelength
        peak_z: Z value at which the peak height occurs
        standard_deviation: width of the Gaussian
        background: revised version of the supplied (or extracted) background,
            if the Gaussian fit suggests there is a constant background.
        r: correlation coefficient between fitted and actual curve, which can
            be a useful diagnostic as to how well the fit worked.
    
    N.B. You can re-run the fit, specifying the returned background - this may
    improve accuracy, though the effect seems minimal now that it uses a
    threshold to find the peak.  If the SNR of your data is particularly low,
    or you might have peaks very close to the edge, it may make sense to
    increase the threshold.
    """
    if z is None: #try to find the Z values of the different spectra from metadata if not specified
        
        try:
            z = z_scan.attrs.get('dz') #this should work for datasets in an HDF5 file
        
        except:
            print("Warning: no valid z positions were found, using indices instead")
            z = list(range(z_scan.shape[0])) #fall back to indices
    
    if background is None: #similarly, get a head-start on the background from metadata
        
        try:
            background = z_scan.attrs.get('background') #this should work for datasets in an HDF5 file
        
        except:
            z = np.zeros(z_scan.shape[1]) #fall back to zero.  NB it will take a *really* long time to converge like this...
    
    Particle_array = np.array(z_scan, dtype = np.float) - background #first prepare background-subtracted, thresholded arrays
    scan_s = scipy.ndimage.filters.gaussian_filter1d(Particle_array, smoothing_width, axis = 0, mode = 'nearest')
    scan_s[scan_s < 0.] = 0. #smooth and remove negative points so that we don't get NaNs
    scan_t = old_div((scan_s - scan_s.min(axis = 0)), (scan_s.max(axis = 0)-scan_s.min(axis = 0))) - threshold
    scan_t[scan_t < 0.] = 0. #background-subtracted, thresholded version of Particle_array - used for finding the peak
    #Now the fitting starts: find the centroid and width of the distribution in Z (the threshold helps avoid bias from background):
    peak_z = old_div(np.sum(scan_t * z[:, np.newaxis], axis = 0), np.sum(scan_t, axis = 0))#the z[np.newaxis,:] is "numpy broadcasting", google it!
    standard_deviation = np.sqrt(old_div(np.sum(scan_s * (z[:, np.newaxis] - peak_z) ** 2, axis = 0), np.sum(scan_s, axis = 0))) 
    #Next, construct a Gaussian in Z with the right parameters and use linear least squares to fit offset/peak to the data
    gaussians = np.exp(old_div(-(z[:, np.newaxis] - peak_z[np.newaxis, :]) ** 2, (2 * standard_deviation ** 2)))
    var_x = np.var(gaussians, axis = 0)
    mean_x = np.mean(gaussians, axis = 0)
    var_y = np.var(Particle_array, axis = 0)
    mean_y = np.mean(Particle_array, axis = 0)
    covariance = np.mean((gaussians - mean_x) * (Particle_array - mean_y), axis = 0)
    slopes = old_div(covariance, var_x)
    intercepts = mean_y - slopes * mean_x
    peak_height = slopes
    r = old_div(covariance, np.sqrt(var_x * var_y))
    return peak_height, peak_z, standard_deviation, background + intercepts, r

def extract_all_spectra(datafile, outputfile):
    """Go through a file, extract all the spectra, and save in an output file."""
    group_names = [k for k in datafile if "ParticleScannerScan_" in k]
    
    group_names = sorted(group_names, key = lambda group_name: len(datafile[group_name]))[::-1] #Sort ParticleScannerScan_ groups in order of size, so that the largest dataset (usually the one of interest) is named "scan0" in the summary file.
    
    for n, group_name in enumerate(group_names):
        data_group = datafile[group_name]
        save_group = outputfile.require_group('particleScanSummaries/scan%s' % n)
        Particle_groups = [group for key, group in list(data_group.items()) if "Particle_" in key] #filter out scan groups from overview images, etc.

        if len(Particle_groups) > 0:
            shape = (len(Particle_groups), Particle_groups[0]['alinger.z_scan_0'].attrs.get('wavelengths').shape[0])
            #these datasets will save the fit parameters to each spectrum in the current scan
            spectra = save_group.create_dataset("spectra", shape)
            
            for name, value in list(Particle_groups[0]['alinger.z_scan_0'].attrs.items()):
                spectra.attrs.create(name, value)
            
            peak_z = save_group.create_dataset("peak_z", shape)
            standard_deviation = save_group.create_dataset("standard_deviation", shape)
            fitted_background = save_group.create_dataset("fitted_background", shape)
            correlation_coefficient = save_group.create_dataset("correlation_coefficient", shape)
            
            for i in range(len(Particle_groups)):
                
                try:
                    spectra[i, :], peak_z[i, :], standard_deviation[i, :], fitted_background[i, :], correlation_coefficient[i, :] = fit_gaussians_to_z_scan(data_group['Particle_%d/alinger.z_scan_0' % i])
                
                except Exception as e:
                    print("Failed to get alinger.z_scan_0 in group %s." % group_name)
                    raise e

if __name__ == "__main__":
    
    for filename in os.listdir('.'):
        
        if re.match('\d\d\d\d-[01]\d-[0123]\d.h5', filename):#Finds first instance of file with name in "yyyy-mm-dd.h5" format
            break
    
    print('About to extract data from %s\n' % filename)
    
    file = h5py.File(filename, mode = "r")
    sv = ScanViewer(file)
    ov = OverviewViewer(file)
    sv.edit_traits()
    #ov.edit_traits()
    output_file = h5py.File("summary.h5")
    extract_all_spectra(file, output_file)
    output_file.close()
    
    print('\nData extracted successfully (ignore the sad face)')