from __future__ import division
from __future__ import print_function

# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 28 11:01:37 2020

@author: Hera
"""

"""
jpg66
"""


from builtins import input
from builtins import str
from past.utils import old_div
from nplab.instrument.spectrometer.Triax import Triax
import numpy as np
from nplab.instrument.camera.Andor import Andor, AndorUI
import types
import future

Calibration_Arrays=[]

Calibration_Arrays.append([])
Calibration_Arrays.append([])
Calibration_Arrays.append([])

Calibration_Arrays[2].append([764.61,  2.27389453e-07, -1.50626785e-01,  1.21487041e+04])
Calibration_Arrays[2].append([789.48,  1.59023464e-07, -1.38884759e-01,  1.19635203e+04])
Calibration_Arrays[2].append([823.5, 4.03268378e-08, -1.17709195e-01,  1.14389462e+04])
Calibration_Arrays[2].append([828.15, 1.2025391e-08, -1.1258273e-01,  1.1259733e+04])
Calibration_Arrays[2].append([834.76, -1.61822540e-08, -1.07392158e-01,  1.11077126e+04])
Calibration_Arrays[2].append([841.12, -6.09192196e-08, -9.91452193e-02,  1.08073451e+04])
Calibration_Arrays[2].append([882.44, -2.41269681e-07, -6.46639473e-02,  9.68027416e+03])
Calibration_Arrays[2].append([895.32, -2.42364194e-07, -6.43223220e-02,  9.82060231e+03])
Calibration_Arrays[2].append([904.72, -2.15463477e-07, -6.95790273e-02,  1.01941429e+04])
Calibration_Arrays[2].append([916.35, -1.62169936e-07, -8.02752427e-02,  1.08757910e+04])
Calibration_Arrays[2].append([938.31, -4.38217497e-09, -1.12728352e-01,  1.28287277e+04])
Calibration_Arrays[2].append([979.72, 2.16188951e-07, -1.59901057e-01,  1.58551361e+04])
Calibration_Arrays[2].append([992.11, 2.23593080e-07, -1.61622854e-01,  1.61153277e+04])


Calibration_Arrays[2] = [Calibration_Arrays[2],-1]


Calibration_Arrays=np.array(Calibration_Arrays)


CCD_Size=2048 #Size of ccd in pixels

#Make a deepcopy of the andor capture function, to add a white light shutter close command to if required later
# Andor_Capture_Function=types.FunctionType(Andor.capture.__code__, Andor.capture.__globals__, 'Unimportant_Name',Andor.capture.__defaults__, Andor.capture.__closure__)

class Trandor(Andor):#Andor
    ''' Wrapper class for the Triax and the andor
    ''' 
    # Calibration_Arrays = Calibration_Arrays
    def __init__(self, white_shutter=None, triax_address = 'GPIB0::1::INSTR', use_shifts = False, laser = '_633'):
        print ('Triax Information:')
        super(Trandor,self).__init__()
        self.triax = Triax(triax_address, CCD_Size=CCD_Size, Calibration_Data=Calibration_Arrays) #Initialise triax
        self.white_shutter = white_shutter
        self.triax.ccd_size = CCD_Size
        self.use_shifts = use_shifts
        self.laser = laser
        
        print ('Current Grating:'+str(self.triax.Grating()))
        print ('Current Slit Width:'+str(self.triax.Slit())+'um')
        self.metadata_property_names += ('slit_width', 'wavelengths')
        # self.triax.Calibration_Arrays = Calibration_Arrays
    
    def Grating(self, Set_To=None):
        return self.triax.Grating(Set_To)

    def Generate_Wavelength_Axis(self, use_shifts=None):

        if use_shifts is None:
            use_shifts = self.use_shifts
        if use_shifts:
            if self.laser == '_633': centre_wl = 632.8
            elif self.laser == '_785': centre_wl = 784.81
            wavelengths = np.array(self.triax.Get_Wavelength_Array()[::-1])
            return ( 1./(centre_wl*1e-9)- 1./(wavelengths*1e-9))/100    
        else:
            return self.triax.Get_Wavelength_Array()[::-1]
    x_axis = property(Generate_Wavelength_Axis)

    @property
    def wavelengths(self):
        return self.Generate_Wavelength_Axis(use_shifts=False)
    @property
    def slit_width(self):
        return self.triax.Slit()

    def Test_Notch_Alignment(self):
        	Accepted=False
        	while Accepted is False:
        		Input=input('WARNING! A slight misalignment of the narrow band notch filters could be catastrophic! Has the laser thoughput been tested? [Yes/No]')
        		if Input.upper() in ['Y','N','YES','NO']:
        			Accepted=True
        			if len(Input)>1:
        				Input=Input.upper()[0]
        	if Input.upper()=='Y':
        		print ('You are now free to capture spectra')
        		self.Notch_Filters_Tested=True
        	else:
        		print ('The next spectrum capture will be allowed for you to test this. Please LOWER the laser power and REDUCE the integration time.')
        		self.Notch_Filters_Tested=None
    def Set_Center_Wavelength(self, wavelength):
        ''' backwards compatability with lab codes that use trandor.Set_Center_Wavelength'''
        self.triax.Set_Center_Wavelength(wavelength)    
    
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


   

  
    

