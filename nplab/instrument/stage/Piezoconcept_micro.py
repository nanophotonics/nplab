# -*- coding: utf-8 -*-
"""
Created on Thu Oct 01 11:52:44 2015

@author: wmd22
"""
from __future__ import print_function
from builtins import str
import serial

import nplab.instrument.serial_instrument as si
from nplab.instrument.stage import Stage
import time
import numpy as np
class Piezoconcept(si.SerialInstrument,Stage):
    '''A class for the Piezoconcept objective collar '''
    axis_names = ('z',)
    def __init__(self, port=None,unit='u'):
        '''Set up baudrate etc and recenters the stage to the center of it's range (50um)
        
        Args:
            port(int/str):  The port the device is connected 
                            to in any of the accepted serial formats
            
        '''
        self.termination_character = '\n'
        self.port_settings = {
                    'baudrate':115200,
                    'bytesize':serial.EIGHTBITS,
                    'parity':serial.PARITY_NONE,
                    'stopbits':serial.STOPBITS_ONE,
                    'timeout':1, #wait at most one second for a response
          #          'writeTimeout':1, #similarly, fail if writing takes >1s
           #         'xonxoff':False, 'rtscts':False, 'dsrdtr':False,
                    }
        si.SerialInstrument.__init__(self,port=port)
        Stage.__init__(self)
        self.unit = unit #This can be 'u' for micron or 'n' for nano
        self.recenter()

    def move(self,value,axis = None,relative = False):
        '''Move to an absolute positions between 0 and 100 um 
        
        Args:
            value(float):   position to move to

        '''
        value = np.float32(value)
        if self.unit == "n":
            multiplier=0.001
        if self.unit == "u":
            multiplier=1.0
        print(value)
        if relative ==False:
            if value*multiplier < 1E2 and value*multiplier >=0:
                if (value*multiplier-0.2*multiplier)>0:
                    value=value-0.2*multiplier
                    value = np.float32(value)
                    self.write("MOVEX "+str(value)+self.unit)
            else:
                self.log("The value is out of range! 0-100 um (0-1E8 nm) (Z)",level = 'WARN')
        elif relative == True:
            if (value*multiplier+self.position) < 1E2 and (value*multiplier+self.position) >= 0:
                self.write("MOVRX "+str(value)+self.unit)
            else:
                self.log("The value is out of range! 0-100 um (0-1E8 nm) (Z)",level = 'WARN')
        time.sleep(0.1)
        print(value,self.position)
    def get_position(self):
        str_pos = self.query('GET_X')[:-3]
        print("'"+str_pos+"'")
        return float(self.query('GET_X')[:-3])
                
    def move_step(self,direction):
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
        return self.query("INFOS",multiline=True,termination_line= " blah blah",timeout=.1,)
        
    def DSIO(self):
        ''' '''
        return self.query("DSIO 1",multiline=True,termination_line= " blah blah",timeout=.1,)

        
    
        

        
