# -*- coding: utf-8 -*-
"""
Created on Fri Mar 11 13:19:10 2022

@author: Hera
"""

from pylablib.devices import M2
from nplab.instrument import Instrument

class Solstis(Instrument):
    def __init__(self, address='172.24.37.153', port=39933, **kwargs):
        super().__init__( **kwargs)
        self.instr = M2.Solstis(address, port)
    
    def set_wavelength(self, val, tolerance=0.05, attemps=10): #nm
        for _ in range(attemps):
            self.instr.coarse_tune_wavelength(val / 1e9)
            if abs(self.wavelength  - val) > tolerance:
                break

    def get_wavelength(self):
        return self.instr.get_coarse_wavelength() * 1e9
    
    wavelength = property(get_wavelength, set_wavelength)
    
    wl = wavelength     
        
if __name__ == '__main__':
    
    s = Solstis()
    
# laser.close()