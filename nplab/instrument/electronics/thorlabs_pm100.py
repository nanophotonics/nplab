# -*- coding: utf-8 -*-
"""
Created on Thu Dec 19 16:24:49 2019

@author: ee306
"""
import numpy as np
from nplab.instrument.electronics.power_meter import PowerMeter
from nplab.instrument.visa_instrument import VisaInstrument
import visa


class Thorlabs_powermeter(PowerMeter, VisaInstrument):
    def __init__(self, address = 'USB0::0x1313::0x807B::17121118::INSTR',
                 settings = {
                             # 'timeout': 0.1,
                              'read_termination': '\n',
                              'write_termination': '\r\n',
                                }):
     
        VisaInstrument.__init__(self, address=address, settings=settings)
        PowerMeter.__init__(self)
        self.address = address
        self.settings = settings
        self.num_averages = 10
    def _read(self):
        return float(self.query('READ?'))
    @property
    def wavelength(self):
        return self.query('Sense:Correction:WAVelength?')
    @wavelength.setter
    def wavelength(self, wl):
        self.write('Sense:Correction:WAVelength '+str(wl))
    def read_average(self,num_averages = None):
        """a quick averaging tool for the pm100 power meter """
        live = self.live
        self.live = False
        if num_averages is None:
            num_averages = self.num_averages
        powers = []
        failures = 0
        while failures<20 and len(powers)<num_averages:
            try: 
                powers.append(self.power)
                failures = 0
            except:
                failures+=1
        # average = np.mean([self.power for _ in range(num_averages)])
        average = np.mean(powers)
        self.live = live
        return average
    def read_power(self):
        return self._read()*1000
    def restart(self):
        self.__init__(self.address)
        

if __name__ == '__main__':
    pm = Thorlabs_powermeter(visa.ResourceManager().list_resources()[0])
    pm.show_gui(blocking = False)
