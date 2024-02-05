# -*- coding: utf-8 -*-
"""
Created on Thu Oct 01 11:52:44 2015

@author: wmd22
"""
from __future__ import print_function
from builtins import str
import serial

from nplab.instrument.serial_instrument import SerialInstrument
from nplab.instrument.stage import Stage
import time
import numpy as np


class Piezoconcept(SerialInstrument, Stage):
    '''A class for the Piezoconcept objective collar '''
    axis_names = ('z',)

    def __init__(self, port=None, unit='u', cmd_axis='Z'):
        '''Set up baudrate etc and recenters the stage to the center of it's range (50um)
        
        Args:
            port(int/str):  The port the device is connected 
                            to in any of the accepted serial formats
            
        '''
        self.termination_character = '\n'
        self.port_settings = {
            'baudrate': 115200,
            'bytesize': serial.EIGHTBITS,
            'parity': serial.PARITY_NONE,
            'stopbits': serial.STOPBITS_ONE,
            'timeout': 1,  # wait at most one second for a response
            #          'writeTimeout':1, #similarly, fail if writing takes >1s
            #         'xonxoff':False, 'rtscts':False, 'dsrdtr':False,
        }
        SerialInstrument.__init__(self, port=port)
        Stage.__init__(self)
        self.cmd_axis = cmd_axis.upper()
        self.unit = unit  # This can be 'u' for micron or 'n' for nano
        self.distance_scale = 1 if unit == 'n' else 1_000.
    
    def move(self, value, axis=None, relative=False):
        '''Move to an absolute positions between 0 and 100 um 
        
        Args:
            value(float):   position to move to

        '''
        nm = int(self.distance_scale*value)
        if relative:
            if 0 <= nm/1_000 + self.position*1_000 < 100_000:
                self.write(f'MOVR{self.cmd_axis} {nm}n')
            else:
                self._logger.warn(
                    "The value is out of range! 0-100 um (0-1E8 nm) (Z)")          
        else:
            if 0 <= nm < 100_000:
            #     if (multiplied-0.2*self.distance_scale) > 0:
            #         value = value-0.2*self.distance_scale  # why?
      
                self.write(f'MOVE{self.cmd_axis} {nm}n')
                # print(self.readline(), 'reply')
            else:
                self._logger.warn(
                    "The value is out of range! 0-100 um (0-1E8 nm) (Z)")
            
     

    def get_position(self):
        return float(self.query(f'GET_{self.cmd_axis}')[:-3])

    def move_step(self, direction):
        '''Move a predefined step in either direction
        Args:
            direction(int):     +1/-1 corresponding to either positive or negative directions
            
        Notes:
            There is no value checking on the directions value therefore 
            it can also be used to perform integer multiples of steps
        '''
        self.move_rel(direction*self.stepsize)

    def recenter(self):
        '''Recenter the stage (50um) and reset software position 
        '''
        self.move(50)

    def INFO(self):
        ''' '''
        return self.query("INFOS", multiline=True, termination_line=" blah blah", timeout=.1,)

    def DSIO(self):
        ''' '''
        return self.query("DSIO 1", multiline=True, termination_line=" blah blah", timeout=.1,)

    def HELP(self):
        return self.query('HELP_')
if __name__ == '__main__':
    z = Piezoconcept('COM16')
