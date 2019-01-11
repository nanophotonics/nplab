"""
Created on Tue Apr 14 18:45:32 2015

@author: jpg66. Based on code by Hamid Ohadi (hamid.ohadi@gmail.com)
"""

from nplab.instrument.visa_instrument import VisaInstrument
import numpy as np
import time
import copy

"""
This is the base class for the Triax spectrometer. This should be wrapped for each lab use, due to the differences in calibrations.
"""

class Triax(VisaInstrument):
    metadata_property_names = ('wavelength', )

    def __init__(self, Address, Calibration_Data=[],Iterative_Calibration_Steps=0):  
        """
        Initialisation function for the triax class. Address in the port address of the triax connection.

        For each grating, have a list of wavelengths used for calibration (in acending order), followed by experimental data points for each coefficient.
        """
        
        VisaInstrument.__init__(self, Address, settings=dict(timeout=4000, write_termination='\n'))
        
        Attempts=0
        End=False
        while End is False:
            if self.query(" ")=='F':
                End=True
            else:
                self.instr.write_raw('\x4f\x32\x30\x30\x30\x00')
                time.sleep(2)
                Attempts+=1
                if Attempts==5:
                    raise Exception('Triax communication error!')
        
        self.Grating_Number=self.Grating() #Current grating number
        self.Calibration_Arrays=[]
        for i in Calibration_Data:
            self.Calibration_Arrays.append([])
            if isinstance(i,list)==True and len(i)==4:
                for j in i[1:]:
                    self.Calibration_Arrays[-1].append(np.polyfit(i[0],j,2))

        self.Spline_Data=[]   #For reach grating, there is a list of lists. These are cali wavelengths, then lists of quad coeff for use in the spline
        for i in Calibration_Data:
            self.Spline_Data.append([i[0]])
            for j in i[1:]:
                self.Spline_Data[-1].append([])
                for k in range(len(self.Spline_Data[0]))[1:-1]:
                    self.Spline_Data[-1][-1].append(np.polyfit(self.Spline_Data[-1][0][k-1:k+2],j[k-1:k+2],2))

        self.Iterative_Calibration_Steps=Iterative_Calibration_Steps

        print 'This Triax spectrometer is calibrated for use over the following ranges:'
        for i in range(len(Calibration_Data)):
            if isinstance(Calibration_Data[i],list)==True and len(Calibration_Data[i])==4:
                print 'Grating',i,':',np.min(Calibration_Data[i][0]),'nm - ',np.max(Calibration_Data[i][0]),'nm'


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

    def Iterate_Pixels_to_Wavelengths(self,Pixel_Array,Steps,Current_Wavelength_Estimation_Array):
        Spline_Data=self.Calibration_Data[self.Grating_Number] #[Calibration_Wavelength,Square_Coefficents,Linear_Coefficents,Constant_Coefficents]
        
        #Split wavelength array into different regions of the quadratic spline

        Coefficent_Blocks=[]
        for i in range(len(Spline_Data[1])):
            Coefficent_Blocks.append(np.array([Spline_Data[1][i],Spline_Data[2][i],Spline_Data[3][i]]))
        #Coefficent_Blocks=[Coefficent_Blocks[0]]+Coefficent_Blocks+[Coefficent_Blocks[-1]]

        Chunks=[]
        Counter=0
        while Counter<len(Current_Wavelength_Estimation_Array):
            Region=0
            while Region<len(Spline_Data[0]) and Spline_Data[0][n]<Current_Wavelength_Estimation_Array[Counter]:
                Region+=1
            if Region==0:
                Start=-np.inf
            else:
                Start=Spline_Data[0][Region-1]
            if Region==len(Spline_Data[0]):
                End=np.inf
            else:
                End=Spline_Data[0][Region]
            m=0
            while Counter+m<len(Current_Wavelength_Estimation_Array) and Current_Wavelength_Estimation_Array[Counter+m]>=Start and Current_Wavelength_Estimation_Array[Counter+m]<=End:
                m+=1
            Chunks.append([Region,Counter,Counter+m])
            Counter+=m

        Changing_Coefficents=[]
        for i in Chunks:
            Chunk=np.array(Current_Wavelength_Estimation_Array[i[1]:i[2]])
            if i[0]<=1:
                Chunk*=0
                Chunk+=1
                Changing_Coefficents+=(Chunk*Coefficent_Blocks[0]).tolist()
            elif i[0]>=len(Spline_Data)-1:
                Chunk*=0
                Chunk+=1
                C hanging_Coefficents+=(Chunk*Coefficent_Blocks[-1]).tolist()
            else:
                Chunk-=Spline_Data[0][i[0]-1]
                Chunk/=Spline_Data[0][i[0]]-Spline_Data[0][i[0]-1]
                Changing_Coefficents+=((1-Chunk)*Coefficent_Blocks[i[0]-1]+Chunk*Coefficent_Blocks[i[0]]).tolist()

        return Changing_Coefficents


    def Convert_Pixels_to_Wavelengths(self,Pixel_Array):
        """
        Function to convert a 1-D array of pixel values (Pixel Array) into corresponding wavelengths
        """
            
        Steps=self.Motor_Steps() #Check grating position
            
        if self.Grating_Number>=len(self.Calibration_Arrays): #Check calibration exists
            if len(self.Calibration_Arrays)==0 or len(self.Calibration_Arrays[self.Grating_Number])==0:
                return Pixel_Array
            else:
                raise ValueError('Current grating is not calibrated! No calibration supplied!')
            
        #Perform conversion using quadratic estimation
            
        Coefficents=np.transpose(copy.deepcopy(self.Calibration_Arrays[self.Grating_Number]))
        Step_Array=np.array([Steps**2,Steps,1]).astype(np.float64)
            
        Coefficents*=Step_Array
        Coefficents=np.sum(Coefficents,axis=1)

        if len(Coefficents)==3:
            Lambda=(-Coefficents[1]+np.sqrt((Coefficents[1]**2)-(4*Coefficents[0]*(Coefficents[2]-Pixel_Array))))/(2*Coefficents[0])
            return Lambda
        if len(Coefficents)==2:
            return (Pixel_Array-Coefficents[1])/Coefficents[0]
            
    def Find_Required_Step(self,Wavelength,Pixel):
        """
        Function to return the required motor step value that would place a given Wavelength on a given Pixel of the CCD
        """

        if self.Grating_Number>=len(self.Calibration_Arrays): #Check calibration exists
            raise ValueError('Current grating is not calibrated! No calibration supplied!')
        
        #Perform Conversion
        
        if len(self.Calibration_Arrays[self.Grating_Number][0])==3:
            Coefficents=np.sum(self.Calibration_Arrays[self.Grating_Number]*np.array([Wavelength**2,Wavelength,1.]),axis=1)
        elif len(self.Calibration_Arrays[self.Grating_Number][0])==2:
            Coefficents=np.sum(self.Calibration_Arrays[self.Grating_Number]*np.array([Wavelength,1.]),axis=1)
        return int((-Coefficents[1]-np.sqrt((Coefficents[1]**2)-(4*Coefficents[0]*(Coefficents[2]-Pixel))))/(2*Coefficents[0]))

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

        while self._isBusy()==True:
            time.sleep(1)
            if (time.time() - Start_Time) > Timeout:
                self._logger.warn('Timed out')
                print 'Timed out'
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