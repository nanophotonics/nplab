# -*- coding: utf-8 -*-
"""
APT Motor Controller for Thorlabs
Adopted from
https://github.com/HaeffnerLab/Haeffner-Lab-LabRAD-Tools/blob/master/cdllservers/APTMotor/APTMotorServer.py
With thanks to SeanTanner@ThorLabs for providing APT.dll and APT.lib


V1.1
20141125 V1.0    First working version
20141201 V1.0a   Use short notation for moving (movRelative -> mRel)
20150417 V1.1    Implementation of simple QT GUI

Michael Leung
mcleung@stanford.edu
"""
from __future__ import print_function
from builtins import object
DEBUG = False




'''
Installation Notes [Ilya Manyakin,im354m, 05/04/2018]

    * Different DLLs are required for 32/64 bit versions:
        Added 32/64bit versions in DLL/ folder of nplab

    * Possible errors on 64bit machines:
        * [Tested on NP-Delphinius,05/04/2018]:
            * "Program can't start because mfc110.dll is missing"

                This is a system DLL error. The DLL comes from installing "Microsoft Visual C++ Redistributable for Visual Studio 2012 Update 4"
                Site for download [tested 05/04/2018]: https://www.microsoft.com/en-us/download/details.aspx?id=30679

'''
import os,platform 
from ctypes import c_long, c_buffer, c_float, windll, pointer

PARENT_DIR = os.path.dirname(os.path.abspath(__file__))
if DEBUG: 
    print("Current working directory: ",os.getcwd())
    print("PyAPT.py file parent directory: ", PARENT_DIR)
    #determine system type by looking at python executable
    #source: https://docs.python.org/2/library/platform.html
    print("Platform architecture: ",platform.architecture()) 
        

OS_TYPE = platform.architecture()[0]
assert(OS_TYPE in ["32bit","64bit"]),"Cannot determine type of operating system from python executable"
DLL_PATH = os.path.normpath('{0}/DLL/{1}/APT.dll'.format(PARENT_DIR,OS_TYPE))

if DEBUG:
    print("Word length of OS [32/64bit]", OS_TYPE)
    print("APT DLL path:", DLL_PATH)

class APTMotor(object):
    def __init__(self, SerialNum=None, HWTYPE=31,blacklash_correction=0.10,minimum_velocity=0.0,acceleration=5.0,max_velocity=10.0):
        '''
        HWTYPE_BSC001		11	// 1 Ch benchtop stepper driver
        HWTYPE_BSC101		12	// 1 Ch benchtop stepper driver
        HWTYPE_BSC002		13	// 2 Ch benchtop stepper driver
        HWTYPE_BDC101		14	// 1 Ch benchtop DC servo driver
        HWTYPE_SCC001		21	// 1 Ch stepper driver card (used within BSC102,103 units)
        HWTYPE_DCC001		22	// 1 Ch DC servo driver card (used within BDC102,103 units)
        HWTYPE_ODC001		24	// 1 Ch DC servo driver cube
        HWTYPE_OST001		25	// 1 Ch stepper driver cube
        HWTYPE_MST601		26	// 2 Ch modular stepper driver module
        HWTYPE_TST001		29	// 1 Ch Stepper driver T-Cube
        HWTYPE_TDC001		31	// 1 Ch DC servo driver T-Cube
        HWTYPE_LTSXXX		42	// LTS300/LTS150 Long Travel Integrated Driver/Stages
        HWTYPE_L490MZ		43	// L490MZ Integrated Driver/Labjack
        HWTYPE_BBD10X		44	// 1/2/3 Ch benchtop brushless DC servo driver
        '''
        self.Connected = False

        self.aptdll = windll.LoadLibrary(DLL_PATH)

        self.aptdll.EnableEventDlg(True)
        self.aptdll.APTInit()
        #print 'APT initialized'
        self.HWType = c_long(HWTYPE)
        self.blCorr = blacklash_correction #100um backlash correction
        if SerialNum is not None:
            if DEBUG: print(("Serial is", SerialNum))
            self.SerialNum = c_long(SerialNum)
            self.initializeHardwareDevice()
        # TODO : Error reporting to know if initialisation went sucessfully or not.

        else:
            if DEBUG: print("No serial, please setSerialNumber")

        self.setVelocityParameters(minVel=minimum_velocity, acc=acceleration, maxVel=max_velocity)

    def getNumberOfHardwareUnits(self):
        '''
        Returns the number of HW units connected that are available to be interfaced
        '''
        numUnits = c_long()
        self.aptdll.GetNumHWUnitsEx(self.HWType, pointer(numUnits))
        return numUnits.value


    def getSerialNumberByIdx(self, index):
        '''
        Returns the Serial Number of the specified index
        '''
        HWSerialNum = c_long()
        hardwareIndex = c_long(index)
        self.aptdll.GetHWSerialNumEx(self.HWType, hardwareIndex, pointer(HWSerialNum))
        return HWSerialNum

    def setSerialNumber(self, SerialNum):
        '''
        Sets the Serial Number of the specified index
        '''
        if DEBUG: print(("Serial is", SerialNum))
        self.SerialNum = c_long(SerialNum)
        return self.SerialNum.value

    def initializeHardwareDevice(self):
        '''
        Initialises the motor.
        You can only get the position of the motor and move the motor after it has been initialised.
        Once initiallised, it will not respond to other objects trying to control it, until released.
        '''
        if DEBUG: print(('initializeHardwareDevice serial', self.SerialNum))
        result = self.aptdll.InitHWDevice(self.SerialNum)

        if result == 0:
            self.Connected = True
            if DEBUG: print('initializeHardwareDevice connection SUCESS')
        # need some kind of error reporting here
        else:
            raise Exception('Connection Failed. Check Serial Number!')
        return True

        ''' Interfacing with the motor settings '''
    def getHardwareInformation(self):
        model = c_buffer(255)
        softwareVersion = c_buffer(255)
        hardwareNotes = c_buffer(255)
        self.aptdll.GetHWInfo(self.SerialNum, model, 255, softwareVersion, 255, hardwareNotes, 255)
        hwinfo = [model.value, softwareVersion.value, hardwareNotes.value]
        return hwinfo

    def getStageAxisInformation(self):
        minimumPosition = c_float()
        maximumPosition = c_float()
        units = c_long()
        pitch = c_float()
        self.aptdll.MOT_GetStageAxisInfo(self.SerialNum, pointer(minimumPosition), pointer(maximumPosition), pointer(units), pointer(pitch))
        stageAxisInformation = [minimumPosition.value, maximumPosition.value, units.value, pitch.value]
        return stageAxisInformation

    def setStageAxisInformation(self, minimumPosition, maximumPosition):
        minimumPosition = c_float(minimumPosition)
        maximumPosition = c_float(maximumPosition)
        units = c_long(1) #units of mm
        # Get different pitches of lead screw for moving stages for different stages.
        pitch = c_float(self.config.get_pitch())
        self.aptdll.MOT_SetStageAxisInfo(self.SerialNum, minimumPosition, maximumPosition, units, pitch)
        return True

    def getHardwareLimitSwitches(self):
        reverseLimitSwitch = c_long()
        forwardLimitSwitch = c_long()
        self.aptdll.MOT_GetHWLimSwitches(self.SerialNum, pointer(reverseLimitSwitch), pointer(forwardLimitSwitch))
        hardwareLimitSwitches = [reverseLimitSwitch.value, forwardLimitSwitch.value]
        return hardwareLimitSwitches

    def getVelocityParameters(self):
        minimumVelocity = c_float()
        acceleration = c_float()
        maximumVelocity = c_float()
        self.aptdll.MOT_GetVelParams(self.SerialNum, pointer(minimumVelocity), pointer(acceleration), pointer(maximumVelocity))
        velocityParameters = [minimumVelocity.value, acceleration.value, maximumVelocity.value]
        return velocityParameters

    def getVel(self):
        if DEBUG: print('getVel probing...')
        minVel, acc, maxVel = self.getVelocityParameters()
        if DEBUG: print('getVel maxVel')
        return maxVel


    def setVelocityParameters(self, minVel, acc, maxVel):
        minimumVelocity = c_float(minVel)
        acceleration = c_float(acc)
        maximumVelocity = c_float(maxVel)
        self.aptdll.MOT_SetVelParams(self.SerialNum, minimumVelocity, acceleration, maximumVelocity)
        return True

    def setVel(self, maxVel):
        if DEBUG: print(('setVel', maxVel))
        minVel, acc, oldVel = self.getVelocityParameters()
        self.setVelocityParameters(minVel, acc, maxVel)
        return True

    def getVelocityParameterLimits(self):
        maximumAcceleration = c_float()
        maximumVelocity = c_float()
        self.aptdll.MOT_GetVelParamLimits(self.SerialNum, pointer(maximumAcceleration), pointer(maximumVelocity))
        velocityParameterLimits = [maximumAcceleration.value, maximumVelocity.value]
        return velocityParameterLimits

        '''
        Controlling the motors
        m = move
        c = controlled velocity
        b = backlash correction

        Rel = relative distance from current position.
        Abs = absolute position
        '''
    def getPos(self):
        '''
        Obtain the current absolute position of the stage
        '''
        if DEBUG: print('getPos probing...')
        if not self.Connected:
            raise Exception('Please connect first! Use initializeHardwareDevice')

        position = c_float()
        self.aptdll.MOT_GetPosition(self.SerialNum, pointer(position))
        if DEBUG: print(('getPos ', position.value))
        return position.value

    def mRel(self, relDistance):
        '''
        Moves the motor a relative distance specified
        relDistance    float     Relative position desired
        '''
        if DEBUG: print(('mRel ', relDistance, c_float(relDistance)))
        if not self.Connected:
            print('Please connect first! Use initializeHardwareDevice')
            #raise Exception('Please connect first! Use initializeHardwareDevice')
        relativeDistance = c_float(relDistance)
        self.aptdll.MOT_MoveRelativeEx(self.SerialNum, relativeDistance, True)
        if DEBUG: print('mRel SUCESS')
        return True

    def mAbs(self, absPosition):
        '''
        Moves the motor to the Absolute position specified
        absPosition    float     Position desired
        '''
        if DEBUG: print(('mAbs ', absPosition, c_float(absPosition)))
        if not self.Connected:
            raise Exception('Please connect first! Use initializeHardwareDevice')
        absolutePosition = c_float(absPosition)
        self.aptdll.MOT_MoveAbsoluteEx(self.SerialNum, absolutePosition, True)
        if DEBUG: print('mAbs SUCESS')
        return True

    def mcRel(self, relDistance, moveVel=0.5):
        '''
        Moves the motor a relative distance specified at a controlled velocity
        relDistance    float     Relative position desired
        moveVel        float     Motor velocity, mm/sec
        '''
        if DEBUG: print(('mcRel ', relDistance, c_float(relDistance), 'mVel', moveVel))
        if not self.Connected:
            raise Exception('Please connect first! Use initializeHardwareDevice')
        # Save velocities to reset after move
        maxVel = self.getVel()
        # Set new desired max velocity
        self.setVel(moveVel)
        self.mRel(relDistance)
        self.setVel(maxVel)
        if DEBUG: print('mcRel SUCESS')
        return True

    def mcAbs(self, absPosition, moveVel=0.5):
        '''
        Moves the motor to the Absolute position specified at a controlled velocity
        absPosition    float     Position desired
        moveVel        float     Motor velocity, mm/sec
        '''
        if DEBUG: print(('mcAbs ', absPosition, c_float(absPosition), 'mVel', moveVel))
        if not self.Connected:
            raise Exception('Please connect first! Use initializeHardwareDevice')
        # Save velocities to reset after move
        minVel, acc, maxVel = self.getVelocityParameters()
        # Set new desired max velocity
        self.setVel(moveVel)
        self.mAbs(absPosition)
        self.setVel(maxVel)
        if DEBUG: print('mcAbs SUCESS')
        return True

    def mbRel(self, relDistance):
        '''
        Moves the motor a relative distance specified
        relDistance    float     Relative position desired
        '''
        if DEBUG: print(('mbRel ', relDistance, c_float(relDistance)))
        if not self.Connected:
            print('Please connect first! Use initializeHardwareDevice')
            #raise Exception('Please connect first! Use initializeHardwareDevice')
        self.mRel(relDistance-self.blCorr)
        self.mRel(self.blCorr)
        if DEBUG: print('mbRel SUCCESS')
        return True

    def mbAbs(self, absPosition):
        '''
        Moves the motor to the Absolute position specified
        absPosition    float     Position desired
        '''
        if DEBUG: print(('mbAbs ', absPosition, c_float(absPosition)))
        if not self.Connected:
            raise Exception('Please connect first! Use initializeHardwareDevice')
        if (absPosition < self.getPos()):
            if DEBUG: print(('backlash mAbs', absPosition - self.blCorr))
            self.mAbs(absPosition-self.blCorr)
        self.mAbs(absPosition)
        if DEBUG: print('mbAbs SUCCESS')
        return True

        ''' Miscelaneous '''
    def identify(self):
        '''
        Causes the motor to blink the Active LED
        '''
        self.aptdll.MOT_Identify(self.SerialNum)
        return True

    def cleanUpAPT(self):
        '''
        Releases the APT object
        Use when exiting the program
        '''
        self.aptdll.APTCleanUp()
        if DEBUG: print('APT cleaned up')
        self.Connected = False


    def stopMove(self):
        if DEBUG: print(("Stopping stage:{}".format(self.SerialNum)))
        if not self.Connected:
            raise Exception("Not connected to the stage")
        else:
            self.aptdll.MOT_StopProfiled(self.SerialNum)
            if DEBUG: print("Stopped")
            return 
