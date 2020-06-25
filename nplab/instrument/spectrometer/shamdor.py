# -*- coding: utf-8 -*-
"""
Created on Sat Jul 08 19:47:22 2017

@author: Hera
"""
from __future__ import division
from past.utils import old_div
from nplab.instrument.camera.Andor import Andor, AndorUI
from nplab.instrument.spectrometer.shamrock import Shamrock
import numpy as np
from nplab.instrument.shutter.BX51_uniblitz import Uniblitz

class Shamdor(Andor):
    ''' Wrapper class for the shamrock and the andor
    '''
    def __init__(self, pixel_number = 1600, pixel_width = 16, use_shifts = False, laser = '_633', white_shutter = None):
        self.shamrock = Shamrock()
        self.shamrock.pixel_number = pixel_number
        self.shamrock.pixel_width = pixel_width
        self.use_shifts = use_shifts
        self.laser = laser
        self.white_shutter = white_shutter
        super(Shamdor, self).__init__()
    
    def get_x_axis(self, use_shifts = None):
        if self.use_shifts and use_shifts in [None, False]:
            if self.laser == '_633': centre_wl = 632.8
            elif self.laser == '_785': centre_wl = 784.81
            wavelengths = np.array(self.shamrock.GetCalibration()[::-1])
            return old_div(( 1./(centre_wl*1e-9)- 1./(wavelengths*1e-9)),100)    
        else:
            return self.shamrock.GetCalibration()[::-1]
    x_axis = property(get_x_axis)
    @property
    def Slit(self):
        return self.shamrock.slit_width
    @property 
    def wavelengths(self):
        return self.get_x_axis(use_shifts = False)
def Capture(_AndorUI):
    if _AndorUI.Andor.white_shutter is not None:
        isopen = _AndorUI.Andor.white_shutter.is_open()
        if isopen:
            _AndorUI.Andor.white_shutter.close_shutter()
        _AndorUI.Andor.raw_image(update_latest_frame = True)
        if isopen:
            _AndorUI.Andor.white_shutter.open_shutter()
    else:
        _AndorUI.Andor.raw_image(update_latest_frame = True)
setattr(AndorUI, 'Capture', Capture)
if __name__ == '__main__':
    # wutter = Uniblitz("COM10")
    # wutter.close_shutter()
    s = Shamdor()
    s.show_gui(blocking = False)
    s.shamrock.show_gui(block = False)       
    