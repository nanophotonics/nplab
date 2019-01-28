"""
jpg66 10/2018
"""

from nplab.instrument.spectrometer.Triax.__init__ import Triax
import numpy as np
from nplab.utils.notified_property import NotifiedProperty
from nplab.instrument.camera.Andor import Andor
import types

Calibration_Arrays=[]

#Calibration_Arrays.append([[-7.424439108610487e-10, 6.292460768517561e-07],[0.00036874014847660606, -0.44250724366972605],[16.477735624797166, 37308.72895571748]])
Calibration_Arrays.append([[-1.10599855e-11,  1.63061503e-08, -5.96937267e-06], [ 7.52866906e-06, -1.09783996e-02,  3.85775710e+00],[-1.32813537e+00,  1.97407296e+03, -6.88516843e+05]])
Calibration_Arrays.append([[-2.4177914470470333e-09, 1.6417391549636192e-06],[0.0007738426921082634, -0.6321570360204632],[-36.638718339068475, 41890.920064338614]])
Calibration_Arrays.append([[2.254536467105263e-09, -1.5938649616776316e-06], [-0.0003591761835526315, 0.14020083408881573],[25.670334605263154, -8126.616965131576]])

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

        self.Notch_Filters_Tested=True
        

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

    def Test_Notch_Alignment(self):
        	Accepted=False
        	while Accepted is False:
        		Input=raw_input('WARNING! A slight misalignment of the narrow band notch filters could be catastrophic! Has the laser thoughput been tested? [Yes/No]')
        		if Input.upper() in ['Y','N','YES','NO']:
        			Accepted=True
        			if len(Input)>1:
        				Input=Input.upper()[0]
        	if Input.upper()=='Y':
        		print 'You are now free to capture spectra'
        		self.Notch_Filters_Tested=True
        	else:
        		print 'The next spectrum capture will be allowed for you to test this. Please LOWER the laser power and REDUCE the integration time.'
        		self.Notch_Filters_Tested=None

         
    def capture(self,Close_White_Shutter=True):
        """
        Edits the capture function is a white light shutter object is supplied, to ensure it is closed while the image is taken.
        This behaviour can be overwirtten by passing Close_White_Shutter=False
        """

        if self.Notch_Filters_Tested is False:
            self.Test_Notch_Alignment()
            return (np.array(range(CCD_Size))*0,1,(CCD_Size,))
        	
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

