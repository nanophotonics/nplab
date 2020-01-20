# -*- coding: utf-8 -*-
"""
Created on Sat Jul 08 19:47:22 2017

@author: Hera
"""
from nplab.instrument.camera.Andor import Andor
from nplab.instrument.spectrometer.shamrock import Shamrock
import numpy as np
class Shamdor(Andor):
    ''' Wrapper class for the shamrock and the andor
    '''
    def __init__(self, pixel_number = 1600, use_shifts = False, laser = '_633'):
        self.shamrock = Shamrock()
        #self.shamrock.pixel_number = pixel_number
        self.shamrock.SetNumberPixels(1600)
        self.shamrock.pixel_width = 16
        self.use_shifts = use_shifts
        self.laser = laser
        super(Shamdor, self).__init__()
    def get_xaxis(self):
        if self.use_shifts:
            if self.laser == '_633': centre_wl = 632.8
            elif self.laser == '_785': centre_wl = 784.81
            wavelengths = np.array(self.shamrock.GetCalibration()[::-1])
            return ( 1./(centre_wl*1e-9)- 1./(wavelengths*1e-9))/100    
        else:
            return self.shamrock.GetCalibration()[::-1]
    
    x_axis = property(get_xaxis)
    
if __name__ == '__main__':
    s = Shamdor()
    s.show_gui(blocking = False)
    s.shamrock.GetCalibration()       
    