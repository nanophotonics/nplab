# -*- coding: utf-8 -*-
"""
Created on Sat Jul 08 19:47:22 2017

@author: Hera
"""
from nplab.instrument.camera.Andor import Andor
from nplab.instrument.spectrometer.shamrock import Shamrock

class Shamdor(Andor):
    ''' Wrapper class for the shamrock and the andor
    '''
    def __init__(self, pixel_number = 1600):
        self.shamrock = Shamrock()
        #self.shamrock.pixel_number = pixel_number
        self.shamrock.SetNumberPixels(1600)
        self.shamrock.pixel_width = 16
        super(Shamdor, self).__init__()
    def get_xaxis(self):
        return self.shamrock.GetCalibration()
    x_axis = property(get_xaxis)
