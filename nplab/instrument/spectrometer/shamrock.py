# -*- coding: utf-8 -*-
"""
Created on Fri Apr 10 08:43:56 2015

@author: Felix Benz (fb400), William Deacon(wmd22)
"""
#TODO: Implement functions for:
# - focus mirror
# - flipper mirror
# - accessoires
# - output slit
# - Shutter
from builtins import range
import platform

from ctypes import *
import time
import sys
from nplab.instrument import Instrument
from nplab.utils.notified_property import NotifiedProperty
from nplab.ui.ui_tools import QuickControlBox
from nplab.utils.gui import QtWidgets
from nplab.ui.ui_tools import *
from nplab.utils.gui import *

class Shamrock(Instrument):
    def __init__(self):
        super(Shamrock,self).__init__()
        #for Windows
        architecture = platform.architecture()
        
        if architecture[0] == "64bit":
            self.dll2 = CDLL("C:\\Program Files\\Andor SOLIS\\Drivers\\Shamrock64\\atshamrock")
            self.dll = CDLL("C:\\Program Files\\Andor SOLIS\\Drivers\\Shamrock64\\ShamrockCIF")
            tekst = c_char()        
            error = self.dll.ShamrockInitialize(byref(tekst))

        elif architecture[0] == "32bit":
            self.dll2 = WinDLL("C:\\Program Files\\Andor SDK\\Shamrock\\atshamrock.dll")
            self.dll = WinDLL("C:\\Program Files\\Andor SDK\\Shamrock\\ShamrockCIF.dll")
            tekst = c_char_p("")     
            error = self.dll.ShamrockInitialize(tekst)
            
        self.current_shamrock = 0 #for more than one Shamrock this has to be varied, see ShamrockGetNumberDevices
        self._logger.setLevel('WARN')

    def verbose(self, error, function=''):
        self.log( "[%s]: %s" %(function, error),level = 'info')
    
    #basic Shamrock features    
    def Initialize(self):
        error = self.dll.ShamrockInitialize("")
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
    
    def GetNumberDevices(self):
        no_shamrocks = c_int()
        error = self.dll.ShamrockGetNumberDevices(byref(no_shamrocks))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return no_shamrocks.value
    num_shamrocks = property(GetNumberDevices)   
    
    def Close(self):
        error = self.dll.ShamrockClose()
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)

    
    def GetSerialNumber(self):
        ShamrockSN = c_char()
        error = self.dll.ShamrockGetSerialNumber(self.current_shamrock, byref(ShamrockSN))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ShamrockSN
    serial_number = property(GetSerialNumber)
    
    
    def EepromGetOpticalParams(self):
        self.FocalLength = c_float()
        self.AngularDeviation = c_float()
        self.FocalTilt = c_float()
        error = self.dll.ShamrockEepromGetOpticalParams(self.current_shamrock, byref(self.FocalLength), byref(self.AngularDeviation), byref(self.FocalTilt))
        return {'FocalLength':self.FocalLength,'AngularDeviation':self.AngularDeviation,'FocalTilt':self.FocalTilt}
        
    #basic Grating features
    def GratingIsPresent(self):
        is_present = c_int()
        error = self.dll.ShamrockGratingIsPresent(self.current_shamrock,is_present)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return is_present.vlaue
    grating_present = property(GratingIsPresent)
    
    
    def GetTurret(self):
        Turret = c_int()
        error = self.dll.ShamrockGetTurret(self.current_shamrock,byref(Turret))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return Turret.value
    def SetTurret(self,turret):
        error = self.dll.ShamrockSetTurret(self.current_shamrock,c_int(turret))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
    
    turret_position = NotifiedProperty(GetTurret,SetTurret)
    
    def GetNumberGratings(self):
        self.noGratings = c_int()
        error = self.dll.ShamrockGetNumberGratings(self.current_shamrock,byref(self.noGratings))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return self.noGratings
    num_gratings = property(GetNumberGratings)

    
    def GetGrating(self):
        grating = c_int()
        error = self.dll.ShamrockGetGrating(self.current_shamrock,byref(grating))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return grating.value
    def SetGrating(self,grating_num):
        grating_num = int(grating_num)
        grating = c_int(grating_num)
        error = self.dll.ShamrockSetGrating(self.current_shamrock,grating)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
    current_grating = NotifiedProperty(GetGrating,SetGrating)    
    def GetGratingInfo(self):    
        lines = c_float()
        blaze = c_char()
        home = c_int()                
        offset = c_int()        
        error = self.dll.ShamrockGetGratingInfo(self.current_shamrock,self.current_grating,byref(lines),byref(blaze),byref(home),byref(offset))
        CurrGratingInfo = [lines.value,blaze.value,home.value,offset.value]
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return CurrGratingInfo
    GratingInfo = property(GetGratingInfo)
    
    def GetGratingOffset(self):
        GratingOffset = c_int() #not this is in steps, so int
        error = self.dll.ShamrockGetGratingOffset(self.current_shamrock,self.current_grating,byref(GratingOffset))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return GratingOffset
    def SetGratingOffset(self,offset):
        error = self.dll.ShamrockSetGratingOffset(self.current_shamrock,self.current_grating,c_int(offset))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
    Grating_offset = NotifiedProperty(GetGratingOffset,SetGratingOffset)
    
    def GetDetectorOffset(self):
        DetectorOffset = c_int() #note this is in steps, so int
        #error = self.dll.ShamrockGetDetectorOffset(self.current_shamrock,byref(self.DetectorOffset))
        error = self.dll.ShamrockGetDetectorOffset(self.current_shamrock,byref(DetectorOffset))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return DetectorOffset.value
    def SetDetectorOffset(self,offset):
        error = self.dll.ShamrockSetDetectorOffset(self.current_shamrock,self.current_grating,c_int(offset))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
    
    detector_offset = NotifiedProperty(GetDetectorOffset,SetDetectorOffset)
        

    
    #Wavelength features
    def WavelengthIsPresent(self):
        ispresent = c_int()
        error = self.dll.ShamrockWavelengthIsPresent(self.current_shamrock,byref(ispresent))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ispresent.value
    motor_present = property(WavelengthIsPresent)
        
    def GetWavelength(self):
        curr_wave = c_float()
        error = self.dll.ShamrockGetWavelength(self.current_shamrock,byref(curr_wave))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return curr_wave.value
    def SetWavelength(self,centre_wl):
        error = self.dll.ShamrockSetWavelength(self.current_shamrock,c_float(centre_wl))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)

    center_wavelength = NotifiedProperty(GetWavelength,SetWavelength)  
      
    def AtZeroOrder(self):
        is_at_zero = c_int()
        error = self.dll.ShamrockAtZeroOrder(self.current_shamrock,byref(is_at_zero))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return is_at_zero.value
    wavelength_is_zero = property(AtZeroOrder)  
    
    def GetWavelengthLimits(self):
        min_wl = c_float()
        max_wl = c_float()      
        error = self.dll.ShamrockGetWavelengthLimits(self.current_shamrock,self.current_grating,byref(min_wl),byref(max_wl))
        wl_limits = [min_wl.value, max_wl.value]
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return wl_limits
    wavelength_limits = property(GetWavelengthLimits)
        

    
    def GotoZeroOrder(self):
        error = self.dll.ShamrockGotoZeroOrder(self.current_shamrock)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
    
    #Slit functions
    def AutoSlitIsPresent(self):
        present = c_int()
        slits = []        
    
        for i in range(1,5):
            self.dll.ShamrockAutoSlitIsPresent(self.current_shamrock,i,present)
            slits.append(present.value)
        return slits
    Autoslits = property(AutoSlitIsPresent)
            
    #Sets the slit to the default value (10um)
    def AutoSlitReset(self,slit):
        error = self.dll.ShamrockAutoSlitReset(self.current_shamrock,self.current_slit)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)

    
    #finds if input slit is present
    def SlitIsPresent(self):
        slit_present = c_int()
        error = self.dll.ShamrockSlitIsPresent(self.current_shamrock,byref(slit_present))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return slit_present.value
    slit_present = property(SlitIsPresent)
    
    #Output Slits
    def GetAutoSlitWidth(self,slit):
        slitw = c_float()
        error = self.dll.ShamrockGetAutoSlitWidth(self.current_shamrock,slit,byref(slitw))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return slitw.value
        
    def SetAutoSlitWidth(self,slit,width):
        slit_w = c_float(width)        
        error = self.dll.ShamrockSetAutoSlitWidth(self.current_shamrock,slit,slit_w)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return width
    
    #Input Slits
    def GetSlit(self):
        slitw = c_float()
        error = self.dll.ShamrockGetSlit(self.current_shamrock,byref(slitw))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return slitw.value
    
    def SetSlit(self,width):
        slit_w = c_float(width)
        error = self.dll.ShamrockSetSlit(self.current_shamrock,slit_w)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
    slit_width = NotifiedProperty(GetSlit,SetSlit)
    
    def SlitReset(self):
        error = self.dll.ShamrockSlitReset(self.current_shamrock)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)

        
    #Calibration functions
    def SetPixelWidth(self,width):
        error = self.dll.ShamrockSetPixelWidth(self.current_shamrock,c_float(width))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
    
    def GetPixelWidth(self):
        pixelw = c_float()
        error = self.dll.ShamrockGetPixelWidth(self.current_shamrock,byref(pixelw))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return pixelw.value
    pixel_width = NotifiedProperty(GetPixelWidth,SetPixelWidth)
    
    def GetNumberPixels(self):
        numpix = c_int()
        error = self.dll.ShamrockGetNumberPixels(self.current_shamrock,byref(numpix))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return numpix.value
    
    def SetNumberPixels(self,pixels):
        error = self.dll.ShamrockSetNumberPixels(self.current_shamrock,pixels)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
    pixel_number = NotifiedProperty(GetNumberPixels,SetNumberPixels)
    
    def GetCalibration(self):
        ccalib = c_float*self.pixel_number
        ccalib_array = ccalib()
        error = self.dll.ShamrockGetCalibration(self.current_shamrock,pointer(ccalib_array),self.pixel_number)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        calib = []        
        for i in range(len(ccalib_array)):
            calib.append(ccalib_array[i])
        return calib[:]
    wl_calibration = property(GetCalibration)     
    
    def GetPixelCalibrationCoefficients(self):
        ca = c_float()
        cb = c_float()
        cc = c_float()
        cd = c_float()
        error = self.dll.ShamrockGetPixelCalibrationCoefficients(self.current_shamrock,byref(ca),byref(cb),byref(cc),byref(cd))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return [ca,cb,cc,cd]
    PixelCalibrationCoefficients = property(GetPixelCalibrationCoefficients)
        
    def get_qt_ui(self):
        return ShamrockControlUI(self)
ERROR_CODE = {
    20201: "SHAMROCK_COMMUNICATION_ERROR",
    20202: "SHAMROCK_SUCCESS",
    20266: "SHAMROCK_P1INVALID",
    20267: "SHAMROCK_P2INVALID",
    20268: "SHAMROCK_P3INVALID",
    20269: "SHAMROCK_P4INVALID",
    20270: "SHAMROCK_P5INVALID",
    20275: "SHAMROCK_NOT_INITIALIZED"    
}

class ShamrockControlUI(QuickControlBox):
    '''Control Widget for the Shamrock spectrometer
    '''
    def __init__(self,shamrock):
        super(ShamrockControlUI,self).__init__(title = 'Shamrock')
        self.shamrock = shamrock
        self.add_doublespinbox("center_wavelength")
        self.add_doublespinbox("slit_width")
        self.add_spinbox("current_grating")
        self.add_lineedit('GratingInfo')
        self.controls['GratingInfo'].setReadOnly(True)
        self.auto_connect_by_name(controlled_object = self.shamrock)

def main():
    
    app = get_qt_app()
    s = Shamrock() 
    ui = ShamrockControlUI(shamrock=s)
    ui.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    # main()
    s = Shamrock()
    s.show_gui(block = False)
    