# -*- coding: utf-8 -*-
"""
Created on Sat Jul 08 19:47:22 2017

@author: Hera
"""
from __future__ import division
from past.utils import old_div
from nplab.instrument.camera.Andor import Andor, AndorUI
from nplab.instrument.spectrometer.shamrock import Shamrock
from nplab.utils.notified_property import NotifiedProperty
import numpy as np
import types
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
    
    
 #   def Grating(self, Set_To=None):
 #       return self.triax.Grating(Set_To)

 #   def Set_Center_Wavelength(self, centre_wavelength) :
 #       self.centre_wl = centre_wavelength
#     def Set_Center_Wavelength(self,Wavelength):  
#        Centre_Pixel=int(CCD_Size/2)
#        Required_Step=self.triax.Find_Required_Step(Wavelength,Centre_Pixel)
#        Current_Step=self.triax.Motor_Steps()
#        self.triax.Move_Steps(Required_Step-Current_Step)
    
#    def read_spectrum(self):
#        return np.array(self.capture()[0])
 
    def get_xaxis(self):
        if self.use_shifts: # Converts to Raman Shift (or Wavenumber)
            if self.laser == '_633': centre_wl = 632.8
            elif self.laser == '_785': centre_wl = 784.81
            wavelengths = np.array(self.shamrock.GetCalibration()[::-1])
#            print wavelengths
#            print centre_wl
            return ( 1./(centre_wl*1e-9)- 1./(wavelengths*1e-9))/100    
        else:
            return self.shamrock.GetCalibration()[::-1]
    x_axis=NotifiedProperty(get_xaxis) #This is grabbed by the Andor code 

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
    wutter = Uniblitz("COM10")
    wutter.close_shutter()
    s = Shamdor(white_shutter = wutter)
    s.show_gui(blocking = False)
    s.shamrock.show_gui(block = False)       
    
