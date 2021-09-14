# -*- coding: utf-8 -*-
"""
Created on Fri Aug  6 15:40:03 2021

@author: Hera
"""

from nplab.instrument.serial_instrument import SerialInstrument
from nplab.utils.notified_property import NotifiedProperty
from nplab.ui.ui_tools import QuickControlBox
import serial


class VariSpec(SerialInstrument):
    termination_character = "\r"
    port_settings = dict(baudrate=9600,bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1, #wait at most one second for a response
                        writeTimeout=1, #similarly, fail if writing takes >1s
                        xonxoff=False, rtscts=False, dsrdtr=False
                    )  
    ignore_echo = True
    
    def __init__(self, port):
        super().__init__(port=port)
        self._set = False
        self._logger.info(f'wavelength range = {self.wavelength_range}')
    
    def reset_error(self):
        self.write("R 1")
    
    def get_wavelength(self):
        if self._set:
            return float(self.query("W ?")[3:])
        else:
            self._logger.warning('wavelength has not been set')
    
    def set_wavelength(self, wl):
        self._set = True
        self.write(f'W {wl:.2f}')
        e = self.get_error()
        if e =='0':
            return 
        if e == '12': 
            self._logger.warning(f'{wl=} out of range')
        else:
            self._logger.warning(f'error code {e} raised')
  
    wavelength = NotifiedProperty(get_wavelength, set_wavelength) 
    wl = wavelength
    
    def get_error(self):
        e = self.query('R ?')[1:].strip()
        self.reset_error()
        return e
    
    
    def get_wavelength_range(self):
        return tuple(map(float, self.query('V ?').split()[2:4]))
    wavelength_range = property(get_wavelength_range)
    wl_range = wavelength_range
    def get_qt_ui(self):
        return VariSpecUI(self)
    
class VariSpecUI(QuickControlBox):
    def __init__(self, instr):
        super().__init__()
        self.instr = instr
        self.add_doublespinbox('wavelength', *instr.get_wavelength_range())
        self.add_button('reset_error')
        self.auto_connect_by_name(controlled_object=instr)   
        
if __name__ == '__main__':
    vs = VariSpec('COM13')
    # def loop_wavelength(self, startwl, stopwl, steps, cycles, time):
    #     if(startwl<stopwl) and start>500 and stopwl < 700:
    #         self.write("%s", startwl)
    #         wl = (stopwl-startwl)/steps
    #         for i in range(steps):
    #                 wl_new = startwl+wl*steps
    #                 if(wl_new < 700):
    #                     self.write("w %s \r", wl_new)
    #                 else:
    #                     print("wavelength outside of acceotable range", wl_new)
    #     else:
    #         print("invalid wavelength selected")
