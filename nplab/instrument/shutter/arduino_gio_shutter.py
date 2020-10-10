# -*- coding: utf-8 -*-
"""
Created on Thu Feb 27 10:36:15 2020

@author: Eoin Elliott
"""

from nplab.instrument.serial_instrument import SerialInstrument
from nplab.instrument.shutter import ShutterWithEmulatedRead
class ArduinoShutter(ShutterWithEmulatedRead, SerialInstrument):
    def __init__(self, port):
        self.termination_character = '\r'
        SerialInstrument.__init__(self, port)
        ShutterWithEmulatedRead.__init__(self)
        self.flush_input_buffer()
        self.readline()
        self.timeout = 1
    def set_state(self, State):
        if State == self.get_state(): return print(f'shutter is already {State}')
        if State == 'Open':
            if self.query('1')!= '1\n':
                print('error opening shutter')
        if State == 'Closed':
            if self.query('0')!= '0\n':
                print('error opening shutter' )
        
if __name__ == '__main__':    
    ard = ArduinoShutter('COM3')
    
    # ard.close_shutter()
    # ard.open_shutter()
    # ard.toggle()
    # ard.toggle()
