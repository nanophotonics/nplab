''' 
# Ralf Mouthaan
# University of Cambridge
# October 2018
# 
# Class to operate Pixis CCD camera. Communicates with Picam library to achieve
# this. Aim is to use this class in conjunction with Acton spectormeter for
# Raman measurements. Work done with Ermanno Miele.
#
# TODO:
#   * Script connects to first camera it finds and uses this. This will cause 
#       problems if no camera is connected, or more than one camera is
#       connected, or if an unexpected camera is connected. 
#       Should iterate through cameras, checking IDs to find the right one.
#       This is complicated due to the way the C++ code uses lots of structures
#       instead of native data types.
#   * Will not find a camera if it is in use by another process or has not 
#       been shut down properly.

Development notes:
    * API for DLL: Picam 5.x Programmers Manual, 4411-0161, Issue 5, August 2018
    
'''

import ctypes as ct
import numpy as np
from matplotlib import pyplot as plt
from nplab.instrument.camera import Camera
import sys,os

PARENT_DIR = os.path.dirname(os.path.realpath(__file__))

class clsPicamReadoutStruct(ct.Structure):
    _fields_ = [("ptr", ct.c_void_p),
                ("intCount", ct.c_int64)]

class Pixis(Camera):
    def __init__(self,with_start_up = False):
    
        self.bolRunning = False
        self.y_max = 0
        self.x_max = 0
        if with_start_up == True:
            self.StartUp()
            self.SetExposureTime(10)
            
        self.boundary_cut = 5
    def __del__(self):
        
        if self.bolRunning == True:
            self.ShutDown()
    
    #Parameter to number mappings from Picam 5.x Programmers Manual
    commands = {}

    def raw_snapshot(self, suppress_errors=False):
        """
            Camera class override
        """
        try:
            image  = self.GetCurrentFrame()
            return True, image
        except Exception, e:
            if suppress_errors==True:
                False, None
            else:
                raise e        

    def get_roi(self,x_min=0, x_max = None, y_min=0,y_max = None, suppress_errors=False,debug=0):
        _,raw_image = self.raw_snapshot(suppress_errors=suppress_errors)
        if x_max is None:
            x_max = self.x_max
        if y_max is None:
            y_max = self.y_max

        if debug > 0:
            print "Pixis.get_roi region of interest:",x_min,x_max,y_min,y_max
        roi_image = raw_image[max(0,y_min):min(y_max,self.y_max),max(0,x_min):min(self.x_max,x_max)]
        if debug > 0:
            print "Pixis.roi_image.shape:",roi_image.shape
        return roi_image

    def get_spectrum(self, x_min=0, x_max = None, y_min=0,y_max = None,with_boundary_cut = True, suppress_errors=False):    
        roi_image = self.get_roi(x_min,x_max,y_min,y_max,suppress_errors)
        #cut edge values from raw spectrum - remove edge effects
        raw_spectrum = np.mean(roi_image,axis=0)
        pixels = range(0,len(raw_spectrum))
        if with_boundary_cut == True:
            return raw_spectrum[self.boundary_cut:-self.boundary_cut], pixels[self.boundary_cut:-self.boundary_cut]

        else:
            return raw_spectrum,pixels

    def get_parameter(self,parameter, label="unknown"):
        '''
        Perform GetParameterIntegerValue calls to DLL
        parameter: integer number identifying parameter to fetch
            where to look these up? - not sure
        '''
        cint_temp = ct.c_int()
        if self.picam.Picam_GetParameterIntegerValue(
                self.CameraHandle, parameter, ct.byref(cint_temp)) != 0:
            print("Could not determine value of parameter {0} [label:{1}]".format(parameter,label))
            return np.nan
        return cint_temp.value

    # def get_parameter(self,parameter_name)
    def StartUp(self):
        cint_temp = ct.c_int()
        # Find DLL
        try:
            self.picam = ct.WinDLL(os.path.normpath('{}/Picam/picam_64bit.dll'.format(PARENT_DIR)))
        except:
            print("Could not find picam dll")
            return
        # Initialise library
        bolInitialised = ct.c_bool(False)
        if self.picam.Picam_InitializeLibrary() != 0:
            print("Could not initialise library")
            return
        self.picam.Picam_IsLibraryInitialized(ct.byref(bolInitialised))
        if bolInitialised == ct.c_bool(False):
            print("Library was not initialised")
            return
        # Get camera handle
        self.CameraHandle = ct.c_void_p()
        if self.picam.Picam_OpenFirstCamera(ct.byref(self.CameraHandle)) != 0:
            print("Could not find camera")
            return
        self.x_max = self.FrameWidth = self.get_parameter(parameter=16842811, label="frame width")
        self.y_max = self.FrameHeight = self.get_parameter(parameter=16842812, label="frame height")
        
        self.bolRunning = True 
    
    def ShutDown(self):
        if self.bolRunning == False:
            return
        if self.picam.Picam_CloseCamera(self.CameraHandle) != 0:
            print("Could not close camera")
            return
        if self.picam.Picam_UninitializeLibrary() != 0:
            print("Could not shut down library")
            return
        self.bolRunning = False
        
    def SetExposureTime(self,time): 
        # Exposure time is measured in ms
        cint_temp = ct.c_int(time)  
        if self.bolRunning == False:
            self.StartUp
        response = self.picam.Picam_SetParameterIntegerValue(self.CameraHandle, 33685527, cint_temp)# ct.byref(cint_temp))    
        if response != 0:
            print("Could not set exposure time. Error code: {0}".format(response))
        
    def GetExposureTime(self):
        
        # Exposure time is measured in ms
        cint_temp = ct.c_int()
        if self.bolRunning == False:
            self.StartUp()
        return self.get_parameter(parameter=33685527, label="exposure time")
    
    def GetCurrentFrame(self):
        
        if self.bolRunning == False:
            self.StartUp()
        
        structReadout = clsPicamReadoutStruct()
        intErrorMask = ct.c_int()
        
        # Read in pointer to image buffer
        if self.picam.Picam_Acquire(self.CameraHandle, 1, -1, 
                ct.byref(structReadout), ct.byref(intErrorMask)) != 0:
            print("Image acquisition failed")
            return
        if intErrorMask.value != 0:
            print("Image acquisition returned an error")
            return
        
        # Get image
        ctarr = (ct.c_uint16*(self.FrameWidth*self.FrameHeight)) # Create ctypes array
        ctarr = ctarr.from_address(structReadout.ptr) # Read in array from pointer
        nparr = np.array(ctarr) # Convert to numpy array
        nparr = nparr.reshape((self.FrameWidth, self.FrameHeight)) # Reshape numpy array
        
        return nparr
        
if __name__ == "__main__":
    
    p = Pixis()
    
    p.SetExposureTime(10)
    _,Frame = p.raw_snapshot()
    p.ShutDown()
    
    plt.imshow(Frame, cmap='gray')
    plt.show()
