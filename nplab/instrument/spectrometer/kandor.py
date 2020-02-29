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
        X = self.kymera.GetCalibration()
        if all([not x for x in X]):# if the list is all 
            X = range(len(X))
        return X
    x_axis = property(get_xaxis)
if __name__ == '__main__':
    k = Kandor()
    k.show_gui(block = False)
    ky = k.kymera
    ky.show_gui(block = False)
