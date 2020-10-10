# -*- coding: utf-8 -*-
"""
Created on Sat Jul 08 19:47:22 2017

@author: Hera
"""
from nplab.instrument.camera.Andor import Andor
from nplab.instrument.spectrometer.Kymera import Kymera
import numpy as np
class Kandor(Andor):
    ''' Wrapper class for the kymera and the andor
    '''
    
    def __init__(self, pixel_number=1600,
                 pixel_width=16,
                 use_shifts=False, 
                 laser_wl=632.8,
                 white_shutter=None):
        self.kymera = Kymera()
        self.kymera.pixel_number = pixel_number
        self.kymera.pixel_width = pixel_width
        self.use_shifts = use_shifts
        self.laser_wl = laser_wl
        self.white_shutter = white_shutter
        super().__init__()
        self.metadata_property_names += ('slit_width', 'wavelengths')
        self.ImageFlip = 0
    
    def get_x_axis(self, use_shifts=None):
        X = self.kymera.GetCalibration()
        if all([not x for x in X]):# if the list is all 0s
            X = range(len(X))
        if self.use_shifts and use_shifts in [None, False]:
            
            wavelengths = np.array(X)
            return ( 1./(self.laser_wl*1e-9)- 1./(wavelengths*1e-9))/100    
        
        return X
    x_axis = property(get_x_axis)
    
    @property
    def slit_width(self):
        return self.kymera.slit_width
    
    @property 
    def wavelengths(self):
        return self.get_x_axis(use_shifts=False)

if __name__ == '__main__':
    k = Kandor()
    k.show_gui(block = False)
    ky = k.kymera
    ky.show_gui(block = False)
    k.MultiTrack = (2, 3, 50)
