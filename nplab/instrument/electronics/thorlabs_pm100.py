# -*- coding: utf-8 -*-
"""
Created on Thu Dec 19 16:24:49 2019

@author: ee306
"""
import numpy as np
from nplab.instrument.electronics.power_meter import PowerMeter
#from nplab.instrument.electronics.ThorlabPM100_powermeter import ThorlabsPM100
from ThorlabsPM100 import ThorlabsPM100
from nplab.instrument.visa_instrument import VisaInstrument
import visa


class Thorlabs_powermeter(PowerMeter, VisaInstrument):
    def __init__(self, address = 'USB0::0x1313::0x807B::17121118::INSTR',
                 settings = {'timeout': 0.1,
                             'read_termination': '\r',
                             'write_termination': '\r',
                             'send_end': True}):
     
        VisaInstrument.__init__(self, address = address, settings = settings)
        PowerMeter.__init__(self)
        
    def _read(self):
        self.query('READ?')
    def set_wavelength(wl):
        self.write('')
    
    def read_power(self):
        Output=[]
        Fail=0      
        while len(Output)<20:
            try:
                Output.append(self.read())
                Fail=0
            except Exception as e:
                self.e = e
                Fail+=1
            if Fail==10:
                print('Restarting power meter',self.e)
                self.restart()
                return np.NaN
        return np.median(Output)*1000 # mW
    def restart(self):
        self.__init__(self.address)
        

if __name__ == '__main__':
    pm = Thorlabs_powermeter('USB0::0x1313::0x807B::200207307::INSTR')
    pm.show_gui(blocking = False)
