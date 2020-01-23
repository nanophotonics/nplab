"""
jpg66
"""
from __future__ import division
from __future__ import print_function

from past.utils import old_div
from nplab.instrument.spectrometer.Triax.__init__ import Triax
import numpy as np
from nplab.utils.notified_property import NotifiedProperty
from nplab.instrument.camera.Andor import Andor
import types
import future

Calibration_Arrays=[]

Calibration_Arrays.append([])
Calibration_Arrays.append([])
Calibration_Arrays.append([])

#Calibration_Arrays[0].append([546.,614.,633.,708.19,785.,880.])
#Calibration_Arrays[0].append([-1.54766997e-05, 3.12560316e-06, 7.48822074e-06, 1.26048704e-05 , 4.21666043e-06, 2.43945244e-05])
#Calibration_Arrays[0].append([-1.63503325e+00, -1.94141892e+00, -2.02516092e+00, -2.17431238e+00, -1.87265593e+00, -2.60909451e+00])
#Calibration_Arrays[0].append([1.44780946e+04, 1.75785703e+04, 1.85922568e+04, 2.17816013e+04, 1.10551705e+04, 3.03183653e+04])

Calibration_Arrays[1].append([546.,614.,633.,708.19,785.,880.])
Calibration_Arrays[1].append([-5.65248674e-06, -3.01056645e-06, -1.99047684e-06, -2.24562594e-05, 2.02336235e-06,  1.15803962e-05])
Calibration_Arrays[1].append([-1.75115459, -1.79100089, -1.79852965, -1.59951646, -1.85506506,-1.98678881])
Calibration_Arrays[1].append([7601.12273137,  8563.71071556,  8849.60197977,  9361.94861663,11023.31118393, 12621.76193336])

Calibration_Arrays[2].append([546.,614.,633.,708.19,785.,880.])
Calibration_Arrays[2].append([-3.93887893e-05,-6.91910954e-06,-3.18089126e-06,-6.25746333e-06, -1.60444375e-06, -1.57248823e-05])
Calibration_Arrays[2].append([-1.67741919,-1.73940226,-1.74976480,-1.74174632, -1.75474092, -1.71174797])
Calibration_Arrays[2].append([2.53324771e+03,2.76268959e+03,2.83115874e+03,3.06497573e+03, 3.30744597e+03, 3.56084766e+03])


Calibration_Arrays=np.array(Calibration_Arrays)

CCD_Size=1600 #Size of ccd in pixels

#Make a deepcopy of the andor capture function, to add a white light shutter close command to if required later
Andor_Capture_Function=types.FunctionType(Andor.capture.__code__, Andor.capture.__globals__, 'Unimportant_Name',Andor.capture.__defaults__, Andor.capture.__closure__)

class Trandor(Andor):#Andor
    
    ''' Wrapper class for the Triax and the andor
    ''' 
    def __init__(self, White_Shutter=None, triax_address = 'GPIB0::1::INSTR', use_shifts = False, laser = '_633'):
        
        print('---------------------------')
        print ('Triax Information:')

        super(Trandor,self).__init__()
        self.triax = Triax(triax_address, Calibration_Arrays,CCD_Size) #Initialise triax
        self.White_Shutter=White_Shutter
        self.SetParameter('SetTemperature',-90)  #Turn on andor cooler
        self.CoolerON()
        self.triax.ccd_size = CCD_Size
        self.use_shifts = use_shifts
        self.laser = laser 
        print ('---------------------------')
        print ('Current Grating:'+str(self.triax.Grating()))
        print ('Current Slit Width:'+str(self.triax.Slit())+'um')
        print ('---------------------------')
        

    def Grating(self, Set_To=None):
        return self.triax.Grating(Set_To)

    def Generate_Wavelength_Axis(self):
    
           
   
        if self.use_shifts:
            if self.laser == '_633': centre_wl = 632.8
            elif self.laser == '_785': centre_wl = 784.81
            wavelengths = np.array(self.triax.Get_Wavelength_Array()[::-1])
            return ( 1./(centre_wl*1e-9)- 1./(wavelengths*1e-9))/100    
        else:
            return self.triax.Get_Wavelength_Array()[::-1]
    def Test_Notch_Alignment(self):
        	Accepted=False
        	while Accepted is False:
        		Input=raw_input('WARNING! A slight misalignment of the narrow band notch filters could be catastrophic! Has the laser thoughput been tested? [Yes/No]')
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
    
    def capture(self,Close_White_Shutter=True):
        """
        Edits the capture function if a white light shutter object is supplied, to ensure it is closed while the image is taken.
        This behaviour can be overwirtten by passing Close_White_Shutter=False
        """
        if self.White_Shutter is not None and Close_White_Shutter is True:
            try:
                self.White_Shutter.close_shutter()
            except:
                 pass
                    
            Output=Andor_Capture_Function(self)
                
            try:
                self.White_Shutter.open_shutter()
            except:
                pass
            return Output
        else:
           return Andor_Capture_Function(self)

    x_axis=NotifiedProperty(Generate_Wavelength_Axis) #This is grabbed by the Andor code 
    
    def read_spectrum(self):
            return np.array(self.capture()[0])

    def read_spectrum(self):
        return np.array(self.capture()[0])
