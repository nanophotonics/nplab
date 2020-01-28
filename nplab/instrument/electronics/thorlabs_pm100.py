# -*- coding: utf-8 -*-
"""
Created on Thu Dec 19 16:24:49 2019

@author: ee306
"""
import numpy as np
from nplab.instrument.electronics.power_meter import PowerMeter
#from nplab.instrument.electronics.ThorlabPM100_powermeter import ThorlabsPM100
from ThorlabsPM100 import ThorlabsPM100
import visa


class Thorlabs_powermeter(ThorlabsPM100, PowerMeter):
    def __init__(self, address = 'USB0::0x1313::0x807B::17121118::INSTR'):
        rm = visa.ResourceManager()
        instr = rm.open_resource(address, timeout = 0.1)       
        PowerMeter.__init__(self)
        ThorlabsPM100.__init__(self,instr)
    
    def read_power(self):
        Output=[]
        Fail=0      
        while len(Output)<20:
            try:
                Output.append(self.read)
                Fail=0
            except:
                Fail+=1
            if Fail==10:
                print('Restart power meter')
                break
        return np.median(Output)*1000 # mW
    

if __name__ == '__main__':
    pm = Thorlabs_powermeter()
    pm.show_gui(blocking = False)
    