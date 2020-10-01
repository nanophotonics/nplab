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
            print 'Warning: You are outside of calibrated region'
            Edge=self.Convert_Pixels_to_Wavelengths(Pixel_Array,Start)
            In=self.Convert_Pixels_to_Wavelengths(Pixel_Array,Start+1)
            Step=np.mean(Edge-In)
            return (Start-Steps)*Step+Edge
        if Steps>End:
            print 'Warning: You are outside of calibrated region'
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
class TriaxUI(QtWidgets.QWidget,UiTools):
    def __init__(self, triax, ui_file =os.path.join(os.path.dirname(__file__),'triax_ui.ui'),  parent=None):
        assert isinstance(triax, Triax), "instrument must be a Triax"
        super(TriaxUI, self).__init__()
        uic.loadUi(ui_file, self)
        self.triax = triax
        self.centre_wl_lineEdit.returnPressed.connect(self.set_wl_gui)
        self.slit_lineEdit.returnPressed.connect(self.set_slit_gui)     
        self.centre_wl_lineEdit.setText(str(np.around(self.triax.center_wavelength)))
        self.slit_lineEdit.setText(str(self.triax.Slit()))
        eval('self.grating_'+str(self.triax.Grating())+'_radioButton.setChecked(True)')
        for radio_button in range(3):
            eval('self.grating_'+str(radio_button)+'_radioButton.clicked.connect(self.set_grating_gui)')
    def set_wl_gui(self):
        self.triax.Set_Center_Wavelength(float(self.centre_wl_lineEdit.text().strip()))
    def set_slit_gui(self):
        self.triax.Slit(float(self.slit_lineEdit.text().strip()))
    def set_grating_gui(self):
        s = self.sender()
        if s is self.grating_0_radioButton:
            self.triax.Grating(0)
        elif s is self.grating_1_radioButton:
            self.triax.Grating(1)
        elif s is self.grating_2_radioButton:
            self.triax.Grating(2)
        else:
            raise ValueError('radio buttons not connected!')