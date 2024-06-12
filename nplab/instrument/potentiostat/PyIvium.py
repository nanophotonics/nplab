# -*- coding: utf-8 -*-
"""
Created on Mon Feb 28 02:01:19 2022

@author: gk463
"""

DEBUG = True

import os, platform, time, psutil
from ctypes import *

from nplab.instrument import Instrument

'''
IviumSoft-software should always be running in the background when the dll to operate the device.
'''
class Ivium(Instrument):
    def __init__(self, device=1):
        '''

        '''
        super().__init__()
        
        PARENT_DIR = os.path.dirname(os.path.abspath(__file__))
        
        OS_TYPE = platform.architecture()[0]
        assert(OS_TYPE in ["32bit","64bit"]),"Cannot determine type of operating system from python executable"
        if OS_TYPE == "32bit":
            DLL_PATH = os.path.normpath('C:\IviumStat\Software Development Driver\IVIUM_remdriver.dll')
        else:
            DLL_PATH = os.path.normpath('C:\IviumStat\Software Development Driver\IVIUM_remdriver64.dll')
        
        self.openIviumSoft()
        
        self._connected = False
        
        self.dll = CDLL(DLL_PATH)
        self.dll.IV_open()
        # If connected one device, device is always 1
        self._device = device
        self._StatusMessage = {'-1': "No IviumSoft",
                               '0': "Not connected",
                               '1': "Availble, idle",
                               '2': "Available, busy",
                               '3': "No device available"}
        self._status = self.getDeviceStatus()
        self._SerialNumber = self.getSerialNumber()
        self.connect()
            
        #    raise Exception("No potentiostat available!")
        
        if DEBUG:
            print("================Debugging info after initialization================")
            print("Current working directory: ",os.getcwd())
            print("PyIvium.py file parent directory: ", PARENT_DIR)
            print("Platform architecture: ",platform.architecture())
            print("Word length of OS [32/64bit]", OS_TYPE)
            print("DLL path:", DLL_PATH)
            print("Device number: ", self._device)
            print("Device status: ", self._StatusMessage[str(self._status)])
            print("Serial number: ", self._SerialNumber)
            print("===================================================================")
            
    def checkIviumSoft(self):
        return "IviumSoft.exe" in (p.name() for p in psutil.process_iter())
    
    def openIviumSoft(self):
        if self.checkIviumSoft():
            print("IviumSoft already running...")
        if not self.checkIviumSoft():
            print("Opening IviumSoft...")
            os.startfile("C:\IviumStat\IviumSoft.exe")
            time.sleep(1)
            print("IviumSoft opened.")
            
    def closeIviumSoft(self):
        if self.checkIviumSoft():
            print("Closing IviumSoft.")
            os.system("TASKKILL /F /IM IviumSoft.exe")
        else:
            print("IviumSoft is not running now...")
        
    def connect(self):
        for i in range(3):
            print("Connecting to potentiostat... "+str(i+1)+"/3")
            self.dll.IV_connect(pointer(c_long(self._device)))
            time.sleep(0.5)
            self._status = self.getDeviceStatus()
            print(self._StatusMessage[str(self._status)])
            if self._status == 1 or self._status == 2:
                self._connected = True
                print("Connected to potentiostat")
                return 1
            else:
                self._connected = False
        exit("Potentiostat connection failed")
    
    def getDeviceStatus(self):
        '''
        -1 = no IviumSoft;   0 = not connected
        1 = available_idle;  2 = available_busy;   3 = no device available
        '''
        return self.dll.IV_getdevicestatus()
        
    def getSerialNumber(self):
        '''
        Returns the serial number of the connected device
        '''
        sntext = c_char(self._device)
        return self.dll.IV_readSN(pointer(sntext))
    
    def getIVVersion(self):
        return self.dll.IV_VersionDll()
    
    def readMethod(self, methodfname=""):
        '''
        Loads method procedure from disk
        '''
        self.dll.IV_readmethod(methodfname)
        
    def saveMetohd(self, methodfname=""):
        '''
        Saves method procedure to disk
        '''
        self.dll.IV_savemethod(methodfname)
        
    def startMethod(self, methodfname=""):
        '''
        Start method procedure, If methodfname is empty, presently loaded
        procedure is used, else the procedure is loaded from disk.

        '''
        self.dll.IV_startmethod(methodfname)
        self.getDeviceStatus()

    def getNDataPoints(self):
        i = c_long()
        return self.dll.IV_Ndatapoints(byref(i))
        
    def getDataPoints(self, index):
        i = c_long(index)
        d1, d2, d3 = c_double(), c_double(), c_double()
        self.dll.getdata(byref(i),byref(d1),byref(d2),byref(d3))
        return d1,d2,d3
    
if __name__ == '__main__':
    p = Ivium()
    method = b"CV_example.imf"
    #p.readMethod(method)
    p.startMethod(method)
    time.sleep(1)
    
    #data = np.array()
    print(p.getDeviceStatus())
    while p.getDeviceStatus() == 2:
        n = p.getNDataPoints()
        print(n)
        prev_n = n
        if prev_n != n:
            print(n)
            print(p.getDataPoints(n))
    
    print(p.getDeviceStatus())
    p.dll.IV_close()