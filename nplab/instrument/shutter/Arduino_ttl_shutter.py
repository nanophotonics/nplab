# -*- coding: utf-8 -*-
"""
Created on Wed Aug 02 21:16:42 2017

@author: Hera
"""
from nplab.instrument.serial_instrument import SerialInstrument
from nplab.instrument.shutter import Shutter
import serial
class Arduino_TTL_shutter(SerialInstrument,Shutter):
    '''A class for the Piezoconcept objective collar '''

    def __init__(self, port=None):
        '''Set up baudrate etc and recenters the stage to the center of it's range (50um)
        
        Args:
            port(int/str):  The port the device is connected 
                            to in any of the accepted serial formats
            
        '''
        self.termination_character = '\n'
        self.port_settings = {
                    'baudrate':9600,
             #       'bytesize':serial.EIGHTBITS,
                    'timeout':2, #wait at most one second for a response
                    }
        self.termination_character = '\n'
        SerialInstrument.__init__(self,port=port)
        Shutter.__init__(self)
    def get_state(self):
        return self.query('Read')
    def set_state(self,state):
        self.write(state)
if __name__ == '__main__':
    shutter = Arduino_TTL_shutter(port = 'COM15')
    