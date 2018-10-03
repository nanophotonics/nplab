#from nplab.instrument.spectrometer.Triax import Updated_Version_Work_In_Progress as Triax
import Updated_Version_Work_In_Progress as Triax
import numpy as np
from nplab.utils.notified_property import NotifiedProperty
from nplab.instrument.camera.Andor import Andor

Calibration_Arrays=[]

Calibration_Arrays.append(np.array([]))
Calibration_Arrays.append(np.array([[ 4.94388732e-11, -2.16939715e-08, -1.13540608e-05], [-1.31783914e-06,  1.27606623e-03, -2.03620149e+00],[ 4.72696666e-03,  7.87338518e+00,  1.84807750e+03]]))

Calibration_Arrays=np.array(Calibration_Arrays)

CCD_Size=1600 #Size of ccd in pixels


class Trandor(Andor):#Andor
    
    ''' Wrapper class for the Triax and the andor
    ''' 
    def __init__(self):

        super(Trandor,self).__init__()
        self.triax = Triax.Triax('GPIB0::1::INSTR',Calibration_Arrays) #Initialise triax
        #self.Initialize() #Initialise andor

        #self.SetParameter('SetTemperature',-90)  #Turn on andor cooler
       # self.CoolerON()
        
        print '---------------------------'
        print 'Triax Information:'
        print 'Current Grating:',self.triax.Grating()
        print 'Current Slit Width:', self.triax.Slit(),'um'
        print '---------------------------'

    def Grating(self, Set_To=None):
        return self.triax.Grating(Set_To)

    def Generate_Wavelength_Axis(self):
        Pixels=np.arange(0,CCD_Size)
        return np.flipud(self.triax.Convert_Pixels_to_Wavelengths(Pixels))

    def Set_Center_Wavelength(self,Wavelength):   #FIX!!! Broken!!!
        Centre_Pixel=int(CCD_Size/2)
        Required_Step=self.triax.Find_Required_Step(Wavelength,Centre_Pixel)
        Current_Step=self.triax.Motor_Steps()
        self.triax.Move_Steps(Required_Step-Current_Step)

    x_axis=NotifiedProperty(Generate_Wavelength_Axis) #This is grabbed by the Andor code 

