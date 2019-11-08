# -*- coding: utf-8 -*-
"""
Created on Sat Jul 08 19:47:22 2017

@author: Hera
"""
from nplab.instrument.camera.Andor import Andor
from nplab.instrument.spectrometer.Kymera import Kymera

class Kandor(Andor):
    ''' Wrapper class for the shamrock and the andor
    '''
    def __init__(self,pixel_number = 1600):
        self.kymera = Kymera()
        super(Kandor, self).__init__()
        self.kymera.pixel_number = pixel_number
        self.kymera.pixel_width = 16
        self.ImageFlip = 0
    def get_xaxis(self):
        return self.kymera.GetCalibration()
    x_axis = property(get_xaxis)
