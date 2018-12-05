"""
jpg66 10/2018
"""

from nplab.instrument.spectrometer.Triax.__init__ import Triax
import numpy as np
from nplab.utils.notified_property import NotifiedProperty
from nplab.instrument.camera.Andor import Andor
import types

Calibration_Arrays=[]

Calibration_Arrays.append([])
Calibration_Arrays.append([])
Calibration_Arrays.append([[ -1.51319453e-09 , 9.60766480e-07],[  5.16869111e-04, -4.40076883e-01],[ -1.83290709e+01,  2.85258107e+04]])
#Calibration_Arrays.append([[ 1.00000000e-08, -1.51319453e-09 , 9.60766480e-07],[ 1.00000000e-08 , 5.16869111e-04, -4.40076883e-01],[ 1.00000000e-08, -1.83290709e+01,  2.85258107e+04]])

Calibration_Arrays=np.array(Calibration_Arrays)

CCD_Size=2048 #Size of ccd in pixels

#Make a deepcopy of the andor capture function, to add a white light shutter close command to if required later
Andor_Capture_Function=types.FunctionType(Andor.capture.func_code, Andor.capture.func_globals, 'Unimportant_Name',Andor.capture.func_defaults, Andor.capture.func_closure)

class Trandor(Andor):#Andor
    
    ''' Wrapper class for the Triax and the andor
    ''' 
    def __init__(self,White_Shutter=None):

        super(Trandor,self).__init__()
        self.triax = Triax('GPIB0::1::INSTR',Calibration_Arrays) #Initialise triax
        self.White_Shutter=White_Shutter
        self.SetParameter('SetTemperature',-90)  #Turn on andor cooler
        self.CoolerON()
        
        print '---------------------------'
        print 'Triax Information:'
        print 'Current Grating:',self.triax.Grating()
        print 'Current Slit Width:', self.triax.Slit(),'um'
        print '---------------------------'
        

    def Grating(self, Set_To=None):
        return self.triax.Grating(Set_To)

    def Generate_Wavelength_Axis(self):
        Pixels=np.arange(0,CCD_Size)
        return self.triax.Convert_Pixels_to_Wavelengths(Pixels)

    def Set_Center_Wavelength(self,Wavelength):  
        Centre_Pixel=int(CCD_Size/2)
        Required_Step=self.triax.Find_Required_Step(Wavelength,Centre_Pixel)
        Current_Step=self.triax.Motor_Steps()
        self.triax.Move_Steps(Required_Step-Current_Step)
         
    def capture(self,Close_White_Shutter=True):
        """
        Edits the capture function is a white light shutter object is supplied, to ensure it is closed while the image is taken.
        This behaviour can be overwirtten by passing Close_White_Shutter=False
        """
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

