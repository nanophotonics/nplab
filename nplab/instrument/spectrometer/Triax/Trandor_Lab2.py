# -*- coding: utf-8 -*-

"""
jpg66
"""
from __future__ import division
from __future__ import print_function

from builtins import input
from builtins import range
from past.utils import old_div
from nplab.instrument.spectrometer.Triax.__init__ import Triax
import numpy as np
from nplab.utils.notified_property import NotifiedProperty
from nplab.instrument.camera.Andor import Andor
import types

Calibration_Arrays=[]

Calibration_Arrays.append([])
Calibration_Arrays.append([])
Calibration_Arrays.append([])

#Calibration_Arrays[0].append([614.0, 708.19, 785.0, 880.0])
#Calibration_Arrays[0].append([-1.426770400496046e-07,8.568118871080799e-08,-3.842673870179174e-08,-1.6931025292314229e-07])
#Calibration_Arrays[0].append([-0.03622191490065281,-0.1703883696157233,-0.09181517506331724,0.018598551356333176])
#Calibration_Arrays[0].append([21803.133194394515, 47048.52913039829, 39063.730061611925, 21204.44706541431])
#
#Calibration_Arrays[1].append([546.,614.0, 708.19, 785.0, 880.0])
#Calibration_Arrays[1].append([-7.33329431e-08,  2.29960498e-07,  5.49540270e-08, -2.13869451e-07,  3.24330445e-08])
#Calibration_Arrays[1].append([-9.36587388e-02, -1.74583163e-01, -1.32106181e-01,-3.97356293e-02, -1.24762620e-01])
#Calibration_Arrays[1].append([ 1.31671421e+04,  2.01994705e+04,  2.02198457e+04,1.42806356e+04,  2.38358208e+04])
#
#Calibration_Arrays[2].append([546., 614.0, 708.19, 785.0, 880.])
#Calibration_Arrays[2].append([ 2.13781882e-07, -2.70362665e-08, -6.43226122e-08, 1.75946165e-07, -1.95240542e-07])
#Calibration_Arrays[2].append([-1.37059698e-01, -1.06307663e-01, -1.03561184e-01, -1.41752470e-01, -7.34959142e-02])
#Calibration_Arrays[2].append([ 8.50652000e+03, 8.33733583e+03, 9.53751217e+03, 1.20245957e+04, 9.96250851e+03])



#Calibration_Arrays=np.array(Calibration_Arrays)

CCD_Size=2048 #Size of ccd in pixels

#Make a deepcopy of the andor capture function, to add a white light shutter close command to if required later
Andor_Capture_Function=types.FunctionType(Andor.capture.__code__, Andor.capture.__globals__, 'Unimportant_Name',Andor.capture.__defaults__, Andor.capture.__closure__)

class Trandor(Andor):#Andor
    
    ''' Wrapper class for the Triax and the andor
    ''' 
    def __init__(self,White_Shutter=None):
        
        # print '__________________'
        # print 'Triax Information:'

        super(Trandor,self).__init__()
        self.triax = Triax('GPIB0::1::INSTR',Calibration_Arrays,CCD_Size) #Initialise triax
        self.White_Shutter=White_Shutter
        self.SetParameter('SetTemperature',-90)  #Turn on andor cooler
        self.CoolerON()
        self.triax.ccd_size = CCD_Size
	
        # print '______________________'
        # print 'Current Grating:',self.triax.Grating()
        # print 'Current Slit Width:', self.triax.Slit(),'um'
        # print '______________________'
        self.Notch_Filters_Tested=True
        

    def Grating(self, Set_To=None):
        return self.triax.Grating(Set_To)

    def Generate_Wavelength_Axis(self):
        return self.triax.Get_Wavelength_Array()

    def Set_Center_Wavelength(self, wavelength):
        ''' backwards compatability with lab codes that use trandor.Set_Center_Wavelength'''
        self.triax.Set_Center_Wavelength(wavelength) 

    def Test_Notch_Alignment(self):
            Accepted=False
            while Accepted is False:
                Input=eval(input('WARNING! A slight misalignment of the narrow band notch filters could be catastrophic! Has the laser thoughput been tested? [Yes/No]'))
                if Input.upper() in ['Y','N','YES','NO']:
                    Accepted=True
                    if len(Input)>1:
                        Input=Input.upper()[0]
            if Input.upper()=='Y':
                print('You are now free to capture spectra')
                self.Notch_Filters_Tested=True
            else:
                print('The next spectrum capture will be allowed for you to test this. Please LOWER the laser power and REDUCE the integration time.')
                self.Notch_Filters_Tested=None

    def capture(self,Close_White_Shutter=True):
        """
        Edits the capture function is a white light shutter object is supplied, to ensure it is closed while the image is taken.
        This behaviour can be overwirtten by passing Close_White_Shutter=False
        """

        if self.Notch_Filters_Tested is False:
            self.Test_Notch_Alignment()
            return (np.array(list(range(CCD_Size)))*0,1,(CCD_Size,))

        else:
            if self.Notch_Filters_Tested is None:
                self.Notch_Filters_Tested=False
            if self.White_Shutter is not None and Close_White_Shutter is True:
                try:
                    self.White_Shutter.close_shutter()
                except:
                    Dump=1
                Output=Andor_Capture_Function(self)
                try:
                    self.White_Shutter.open_shutter()
                except:
                    Dump=1
                return Output
            else:
                return Andor_Capture_Function(self)

    x_axis=NotifiedProperty(Generate_Wavelength_Axis) #This is grabbed by the Andor code 
