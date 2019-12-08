# -*- coding: utf-8 -*-
"""
Created on Wed Sept 20 2017

@author: Femi Ojambati (fo263)
"""
from __future__ import print_function



from builtins import str
from ctypes import *
import sys
from nplab.instrument import Instrument
import time
import numpy as np
import matplotlib.pyplot as plt
#from nplab.utils.notified_property import NotifiedProperty
#from nplab.ui.ui_tools import QuickControlBox
#from nplab.utils.gui import QtWidgets

class TimeHarp(Instrument):
    
    timeharp_mode = 0  #0=standard histogramming, 1=TTTR
    ctcstatus = 0
    countrate = 0
    BLOCKSIZE =  4096;

    def __init__(self):
        super(TimeHarp,self).__init__()
        #for Windows
        #self.TH_dll = cdll.LoadLibrary(r'C:\Program Files (x86)\PicoQuant\TH200-THLibv61\Thlib_for_x64\Thlib.dll')
       # self.TH_dll = cdll.LoadLibrary('C:\Program Files\PicoQuant\TH200-THLibv61\ThLib.lib')
        self.TH_dll =windll.LoadLibrary(r'ThLib.dll')

        self.Timeharp_Initialize(self.timeharp_mode)
        
    def verbose(self, error, function=''):
        self.log( "[%s]: %s" %(function, error),level = 'info')
        

    def Timeharp_Initialize(self, timeharp_mode):
        retint = self.TH_dll.TH_Initialize(timeharp_mode)
        if retint < 0:
            self.verbose(self.FindError(retint), sys._getframe().f_code.co_name) 
            self.TH_dll.TH_Shutdown()
        
    def TimeHarp_Calibrate(self):
        retint = self.TH_dll.TH_Calibrate();
        if retint < 0:
            self.verbose(self.FindError(retint), sys._getframe().f_code.co_name) 
            self.TH_dll.TH_Shutdown()
        
    def TimeHarp_SetCFDDiscrMin(self, CFDLevel = 20):
        retint = self.TH_dll.TH_SetCFDDiscrMin(CFDLevel)
        if retint < 0:
            self.verbose(self.FindError(retint), sys._getframe().f_code.co_name) 
            self.TH_dll.TH_Shutdown()
        
    def TimeHarp_SetCFDZeroX(self, CFDZeroX = 20):
        retint = self.TH_dll.TH_SetCFDZeroCross(CFDZeroX)
        if retint < 0:
            self.verbose(self.FindError(retint), sys._getframe().f_code.co_name) 
            self.TH_dll.TH_Shutdown()

    def TimeHarp_SetSyncLevel(self, SyncLevel = -700):
        retint = self.TH_dll.TH_SetSyncLevel(SyncLevel)
        if retint < 0:
            self.verbose(self.FindError(retint), sys._getframe().f_code.co_name) 
            self.TH_dll.TH_Shutdown()
        
    def TimeHarp_SetRange(self, Range = 0):
        # range code 0 = base resolution, 1 = 2 x base resolution and so on.      
        retint = self.TH_dll.TH_SetRange(Range)
        if retint < 0:
            self.verbose(self.FindError(retint), sys._getframe().f_code.co_name) 
            self.TH_dll.TH_Shutdown()

    def TimeHarp_SetOffset(self, Offset = 0):    
        retint = self.TH_dll.TH_SetOffset(Offset)
        if retint < 0:
            self.verbose(self.FindError(retint), sys._getframe().f_code.co_name) 
            self.TH_dll.TH_Shutdown()
        
    def TimeHarp_SetStopOverflow(self):    
        retint = self.TH_dll.TH_SetStopOverflow( 1, 65535)
        if retint < 0:
            self.verbose(self.FindError(retint), sys._getframe().f_code.co_name) 
            self.TH_dll.TH_Shutdown()
        
    def TimeHarp_GetResolution(self):    
        retint = self.TH_dll.TH_GetResolution()
        if retint < 0:
            self.verbose(self.FindError(retint), sys._getframe().f_code.co_name) 
            self.TH_dll.TH_Shutdown()
        return retint
    
    def TimeHarp_SetSyncMode(self):
        retint = self.TH_dll.TH_SetSyncMode()
        if retint < 0:
            self.verbose(self.FindError(retint), sys._getframe().f_code.co_name) 
            self.TH_dll.TH_Shutdown()        
        
    
    def TimeHarp_GetCountRate(self):
        retint = self.TH_dll.TH_GetCountRate()
        if retint < 0:
            self.verbose(self.FindError(retint), sys._getframe().f_code.co_name) 
            self.TH_dll.TH_Shutdown()
        return retint    
       
    
    def TimeHarp_ClearHistMem(self, TH_block = 0):
        retint =self.TH_dll.TH_ClearHistMem(TH_block)
        if retint < 0:
            self.verbose(self.FindError(retint), sys._getframe().f_code.co_name) 
            self.TH_dll.TH_Shutdown()
    
    def TimeHarp_GetFlags(self):
        retint =self.TH_dll.TH_GetFlags()
        if retint < 0:
            self.verbose(self.FindError(retint), sys._getframe().f_code.co_name) 
            self.TH_dll.TH_Shutdown()
            
            
    def TimeHarp_StartMeas(self):
        retint =self.TH_dll.TH_StartMeas()
        if retint < 0:
            self.verbose(self.FindError(retint), sys._getframe().f_code.co_name) 
            self.TH_dll.TH_Shutdown()
            
    def TimeHarp_CTCStatus(self):
        retint =self.TH_dll.TH_CTCStatus()
        if retint < 0:
            self.verbose(self.FindError(retint), sys._getframe().f_code.co_name) 
            self.TH_dll.TH_Shutdown()
        return retint

    def TimeHarp_SetMMode(self, mmode = 0, tacq = 1000): #acquire for 1s
        retint =self.TH_dll.TH_SetMMode(mmode, tacq)
        if retint < 0:
            self.verbose(self.FindError(retint), sys._getframe().f_code.co_name) 
            self.TH_dll.TH_Shutdown()
        return retint
    
    
    def TimeHarp_StopMeas(self):
        retint =self.TH_dll.TH_StopMeas()
        if retint < 0:
            self.verbose(self.FindError(retint), sys._getframe().f_code.co_name) 
            self.TH_dll.TH_Shutdown()
            
    def TimeHarp_ShutDown(self):
        self.TH_dll.TH_Shutdown()
            
    def TimeHarp_GetBlock(self, block = 0):
        retarr_p = c_uint32*self.BLOCKSIZE
        retarr = retarr_p()
        retint= self.TH_dll.TH_GetBlock(byref(retarr), block)
        if retint < 0:
            self.verbose(self.FindError(retint), sys._getframe().f_code.co_name) 
            self.TH_dll.TH_Shutdown()
        return retarr, retint
    
       
    def ReadErrorFile(self):
        #mypath = r'C:\Program Files (x86)\PicoQuant\TH200-THLibv61'
        mypath = r'R:\fo263\manuals\TimeHarp200_SW_and_DLL_v6_1';
        
        filename = 'Errcodes_mod_170920.txt'
        myFile = open(mypath + '\\' + filename, 'r')
        filecontent = myFile.read()
        err_code = filecontent.split();
        myFile.close()
        
        return err_code
    
    ERROR_CODE = property(ReadErrorFile)

                       
        
    def FindError(self, thiserror):
        error_index = self.ERROR_CODE.index(str(thiserror))
        return self.ERROR_CODE[error_index - 1]
if __name__ == '__main__':   
    th = TimeHarp()
    th.TimeHarp_Calibrate()
    Offset       = 0;       
    CFDZeroX     = 10;     
    CFDLevel     = 50;     
    SyncLevel    = -700;    
    Range        = 0;       
    Tacq         = 5000;     #acquisition time in milliseconds
    timeharp_mode = 0  #0=standard histogramming, 1=TTTR
    mmode = 0 # mmode = 0 for one-time histogramming and TTTR 1 for continuous mode
    
    th = TimeHarp()
       
    th.TimeHarp_Calibrate()
    time.sleep(1)
    
    th.TimeHarp_SetCFDDiscrMin(CFDLevel)
    th.TimeHarp_SetCFDZeroX(CFDZeroX)
    th.TimeHarp_SetSyncLevel(SyncLevel)
    th.TimeHarp_SetRange(Range) #range code 0 = base resolution, 1 = 2 x base resolution and so on.
    th.TimeHarp_SetOffset(Offset)
    
    resoltuion = th.TimeHarp_GetResolution()
    
    th.TimeHarp_SetSyncMode()
    time.sleep(1)
    syncrate = th.TimeHarp_GetCountRate()
    
    th.TimeHarp_SetStopOverflow()
    
    th.TimeHarp_SetMMode(mmode, Tacq)
    
    th.TimeHarp_ClearHistMem()
    
    th.TimeHarp_GetFlags()
    
    time.sleep(1)
    countrate = th.TimeHarp_GetCountRate()
    
    th.TimeHarp_StartMeas()
    
    ctcdone=0;
    while ctcdone==0:
        ctcdone = th.TimeHarp_CTCStatus()
    
    
    th.TimeHarp_StopMeas()
    
    blockcount, total_count = th.TimeHarp_GetBlock(0)
    
    th.TimeHarp_ShutDown()
    
    
    print(('The resolution is ' + str(resoltuion)))
    print(('The Sync Rate is ' + str(syncrate)))
    print(('The Count Rate is ' + str(countrate)))
    print(('The total count is ' + str(total_count)))
    
    counts = []
    #
    for i in blockcount: 
        counts.append(int(i)), 
       
    
    
    plt.figure()
    plt.plot(np.linspace(1, th.BLOCKSIZE, th.BLOCKSIZE), counts)
    
    
    
        
    #np.plot(counts)
    # 
    #np.plot(blockcount)
    
    #class TimeHarpControlUI(QuickControlBox):
    #    '''Control Widget for the Shamrock spectrometer
    #    '''
    #    def __init__(self,TimeHarp):
    #        super(TimeHarpControlUI,self).__init__(title = 'Shamrock')
    #        self.TimeHarp = TimeHarp
    #        self.add_doublespinbox("center_wavelength")
    #        self.add_doublespinbox("slit_width")
    #        self.add_spinbox("turret_position")
    #        self.add_lineedit('GratingInfo')
    #        self.controls['GratingInfo'].setReadOnly(True)
    #        self.auto_connect_by_name(controlled_object = self.TimeHarp)
    #    