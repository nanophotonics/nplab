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
"""
Created on Tue Apr 14 18:45:32 2015

@author: jpg66. Based on code by Hamid Ohadi (hamid.ohadi@gmail.com)
"""

from nplab.instrument.visa_instrument import VisaInstrument
import numpy as np
import time
import copy
import scipy.interpolate as scint

"""
This is the base class for the Triax spectrometer. This should be wrapped for each lab use, due to the differences in calibrations.
"""

def Quad_Interp(x_Points,y_Points,Input): #x are in order

    Number=np.ones(len(Input)).astype(int)
    Barrier=[]
    for i in Number:
        Barrier.append(x_Points[1])
    Barrier=np.array(Barrier)
    while True:
        Change=(Input>Barrier)
        Change[Number==(len(x_Points)-1)]=False 
        if np.sum(Change)==0:
            break 
        else:
            Number[Change]+=1
            for i in np.array(range(len(Number)))[Change]:
                Barrier[i]=x_Points[Number[i]]
    
    Min=np.min(Number)
    Max=np.max(Number)
    Output=np.empty(len(Input))
    while Min<=Max:
        Mask=(Number==Min)
        if np.sum(Mask)!=0:

            Poly=[]
            if Min-2>=0:
                Poly.append(np.polyfit(x_Points[Min-2:Min+1],y_Points[Min-2:Min+1],2))
            if Min+1<len(y_Points):
                Poly.append(np.polyfit(x_Points[Min-1:Min+2],y_Points[Min-1:Min+2],2))
            if len(Poly)==1:
                Output[Mask]=np.polyval(Poly[0],Input[Mask])
            else:
                for i in range(2):
                    Poly[i]=np.polyval(Poly[i],Input[Mask])
                Frac=(Input[Mask]-x_Points[Min-1])/(x_Points[Min]-x_Points[Min-1])
                Output[Mask]=(1.-Frac)*Poly[0]+Frac*Poly[1]
        Min+=1

    return Output

class Triax(VisaInstrument):
    metadata_property_names = ('wavelength', )

    def __init__(self, Address, Calibration_Arrays=[],CCD_Horizontal_Resolution=1600):  
        """
        Initialisation function for the triax class. Address in the port address of the triax connection. Calibration_Arrays is a list of 3x3 numpy arrays
        containing the calibration coefficents for each grating in the spectrometer.
        """
    
        #--------Attempt to open communication------------

        try:

            VisaInstrument.__init__(self, Address, settings=dict(timeout=4000, write_termination='\n'))
            Attempts=0
            End=False
            while End is False:
                if self.query(" ")=='F':
                    End=True
                else:
                    self.instr.write_raw('\x4f\x32\x30\x30\x30\x00') #Move from boot program to main program
                    time.sleep(2)
                    Attempts+=1
                    if Attempts==5:
                        raise Exception('Triax communication error!')

        except:
            raise Exception('Triax communication error!')

        self.Calibration_Data=Calibration_Arrays

        self.Wavelength_Array=None #Not intially set. Updated with a change of grating or stepper motor position
        self.Number_of_Pixels=CCD_Horizontal_Resolution

    def Get_Wavelength_Array(self):
        """
        Returns the wavelength array in memory. If it is yet to be calculated, it is caluculated here
        """
        if self.Wavelength_Array is None:
            Steps=self.Motor_Steps()
            if Steps<self.Grating_Information[0][0] or Steps>self.Grating_Information[0][-1]:
                print('WARNING: You are outside of the calibration range')
            self.Wavelength_Array=self.Convert_Pixels_to_Wavelengths(np.array(range(self.Number_of_Pixels)),Steps)
        return self.Wavelength_Array

    def Grating(self, Set_To=None):
        """
        Function for checking or setting the grating number. If Set_To is left as None, current grating number is returned. If 0,1 or 2 is passed as Set_To, the
        corresponding grating position is rotated to.
        """

   		#-----Check Input-------
        
        if Set_To not in [None,0,1,2]:
            raise ValueError('Invalid input for grating input. Must be None, 0, 1, or 2.')

        #----Return current grating or switch grating---------
            
        if Set_To is None:
            return int(self.query("Z452,0,0,0\r")[1:])

        else:
            self.write("Z451,0,0,0,%i\r" % (Set_To))
            time.sleep(1)
            self.waitTillReady()
            self.Grating_Number = Set_To

    def Motor_Steps(self):
        """
        Returns the current rotation of the grating in units of steps of the internal stepper motor
        """
        self.write("H0\r")
        return int(self.read()[1:])


    def Convert_Pixels_to_Wavelengths(self,Pixel_Array,Steps=None):
        if Steps is None:
            Steps=self.Motor_Steps()

        Extremes=[]
        Calibration_Data=self.Calibration_Data[self.Grating()]
        Root=Calibration_Data[1]
        Calibration_Data=Calibration_Data[0]

        Extremes=[]
        for i in Calibration_Data:
            a,b,c=i[1:]
            Extremes.append([(-b+Root*((b**2-(4*a*(c-0)))**0.5))/(2*a),(-b+Root*((b**2-(4*a*(c-self.Number_of_Pixels+1)))**0.5))/(2*a)])

        Start=np.floor(np.min(np.array(Extremes)))
        End=np.ceil(np.max(np.array(Extremes)))

        if Steps<Start:
            print('Warning: You are outside of calibrated region')
            Edge=self.Convert_Pixels_to_Wavelengths(Pixel_Array,Start)
            In=self.Convert_Pixels_to_Wavelengths(Pixel_Array,Start+1)
            Step=np.mean(Edge-In)
            return (Start-Steps)*Step+Edge
        if Steps>End:
            print('Warning: You are outside of calibrated region')
            Edge=self.Convert_Pixels_to_Wavelengths(Pixel_Array,End)
            In=self.Convert_Pixels_to_Wavelengths(Pixel_Array,End-1)
            Step=np.mean(Edge-In)
            return (Steps-End)*Step+Edge

        Known_Pixels=[]
        Wavelengths=[]
        for i in Calibration_Data:
            Known_Pixels.append(np.sum(np.array([Steps**2,Steps,1])*i[1:]))
            Wavelengths.append(i[0])
        Output=Quad_Interp(np.array(Known_Pixels),np.array(Wavelengths),np.array(Pixel_Array))
        return np.array(Output)
        

    def Find_Required_Step(self,Wavelength,Pixel,Require_Integer=True):
        Bounds=[]
        Calibration_Data=self.Calibration_Data[self.Grating()]
        Root=Calibration_Data[1]
        Calibration_Data=Calibration_Data[0]
        for i in Calibration_Data:
            a,b,c=i[1:]
            Bounds+=[(-b+Root*((b**2-(4*a*(c-0)))**0.5))/(2*a),(-b+Root*((b**2-(4*a*(c-self.Number_of_Pixels+1)))**0.5))/(2*a)]

        Bounds=[np.min(Bounds),np.max(Bounds)]
        Values=[]
        for i in Bounds:
            Values.append(self.Convert_Pixels_to_Wavelengths([Pixel],Steps=i)[0])
        if Values[1]<Values[0]:
            Values=[Values[1],Values[0]]
            Bounds=[Bounds[1],Bounds[0]]

        if Wavelength<Values[0]:
            raise Exception('Outside calibrated area! Cannot move below '+str(np.round(Values[0],2))+'nm for this pixel')
        if Wavelength>Values[1]:
            raise Exception('Outside calibrated area! Cannot move above '+str(np.round(Values[1],2))+'nm for this pixel')

        while Bounds[1]-Bounds[0]>1:
            New=np.mean(Bounds)
            Value=self.Convert_Pixels_to_Wavelengths([Pixel],Steps=New)[0]
            if Value<=Wavelength:
                Bounds[0]=New
                Values[0]=Value
            else:
                Bounds[1]=New
                Values[1]=Value
       
        Fraction=(Wavelength-Values[0])/(Values[1]-Values[0])
        Step=(1-Fraction)*Bounds[0]+Fraction*Bounds[1]
        if Require_Integer is True:
            Step=int(round(Step))
        return Step
           

    def Move_Steps(self, Steps):
        """
        Function to move the grating by a number of stepper motor Steps.
        """
        
        if (Steps <= 0):  # Taken from original code, assume there is an issue moving backwards that this corrects
            self.write("F0,%i\r" % (Steps - 1000))
            time.sleep(1)
            self.waitTillReady()
            self.write("F0,1000\r")
            self.waitTillReady()
        else:
            self.write("F0,%i\r" % Steps)
            time.sleep(1)
            self.waitTillReady()
    def Set_Center_Wavelength(self,Wavelength):  
        if self.ccd_size is None:
            raise ValueError('ccd_size must be set in child class')
        Centre_Pixel=int(self.ccd_size/2)
        Required_Step=self.Find_Required_Step(Wavelength,Centre_Pixel)
        Current_Step=self.Motor_Steps()
        self.Move_Steps(Required_Step-Current_Step)
    
    def Get_Center_Wavelength(self):
        wls = self.Get_Wavelength_Array()
        return wls[len(wls)//2]
    
    center_wavelength = property(Get_Center_Wavelength, Set_Center_Wavelength) 
    def Slit(self, Width=None):
        """
        Function to return or set the triax slit with in units of um. If Width is None, the current width is returned. 
        """
        
        Current_Width=int(self.query("j0,0\r")[1:])
        
        if Width is None:
            return Current_Width
        elif Width > 0:
           To_Move = Width - Current_Width
        if To_Move == 0:
            return
        elif To_Move > 0:  # backlash correction
            self.write("k0,0,%i\r" % (To_Move + 100))
            self.waitTillReady()
        
            self.write("k0,0,-100\r")
            self.waitTillReady()
        else:
            self.write("k0,0,%i\r" % To_Move)
            self.waitTillReady()

    def _isBusy(self):
        """
        Queries whether the Triax is willing to accept further commands
        """
        
        if self.query("E") == 'oz':
            return False
        else:
            return True

    def waitTillReady(self,Timeout=120):
        """
        When called, this function checks the triax status once per second to check if it is busy. When it is not, the function returns. Also return automatically 
        after Timeout seconds.
        """

        Start_Time = time.time()

        while self._isBusy():
            time.sleep(1)
            if (time.time() - Start_Time) > Timeout:
                self._logger.warn('Timed out')
                print('Timed out')
                break
    def get_qt_ui(self):
        return TriaxUI(self)

    #-------------------------------------------------------------------------------------------------

    """
	Held here are functions from the original code that, at this point in time, I do not wish to touch
    """

    def reset(self):
        self.instr.write_raw('\xde')
        time.sleep(5)
        buff = self.query(" ")
        if buff == 'B':
            self.instr.write_raw('\x4f\x32\x30\x30\x30\x00')  # <O2000>0
            buff = self.query(" ")
        if buff == 'F':
            self._logger.debug("Triax is reset")
            self.setup()

    def setup(self):
        self._logger.info("Initiating motor. This will take some time...")
        self.write("A")
        time.sleep(60)
        self.waitTillReady()
        self.Grating(1)
        self.Grating_Number = self.Grating()

    def exitLateral(self):
        self.write("e0\r")
        self.write("c0\r")  # sets entrance mirror to lateral as well

    def exitAxial(self):
        self.write("f0\r")
        self.write("d0\r")  # sets the entrance mirror to axial as well
        

from builtins import input
from builtins import str
from past.utils import old_div
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
        self.triax = Triax(triax_address, Calibration_Data=Calibration_Arrays, CCD_Horizontal_Resolution=CCD_Size) #Initialise triax
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


   

  
    

