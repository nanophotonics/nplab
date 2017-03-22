# -*- coding: utf-8 -*-
"""
Created on Tue Jul 21 10:22:28 2015

@author: WMD
"""

import nplab.instrument.serial_instrument as si
from nplab.instrument.stage import Stage
import serial
import time

class NanoPZ(si.SerialInstrument,Stage):
    def __init__(self, port=None,controllerNOM ="1"):
        self.port_settings = {
                    'baudrate':19200,
                    'bytesize':serial.EIGHTBITS,
                    'parity':serial.PARITY_NONE,
                    'stopbits':serial.STOPBITS_ONE,
                    'timeout':1, #wait at most one second for a response
                    'writeTimeout':1, #similarly, fail if writing takes >1s
                    'xonxoff':True, 'rtscts':False, 'dsrdtr':False,
                    }
        si.SerialInstrument.__init__(self,port=port)
        self.termination_character = '\r'
        self.stepsize = 10
        if controllerNOM<10:
            controllerNOM = "0%s" %controllerNOM
        self.controllerNOM = controllerNOM
        self.motor_on()
        
    def move_rel(self,value):
        self.write("{0}PR{1}".format(self.controllerNOM, value))
    
    def move_step(self,direction):
        self.move_rel(direction*self.stepsize)
        
    def motor_on(self):
        self.write("{0}MO".format(self.controllerNOM))
        
    def get_position(self, axis=None):
        return self.query("{0}TP?".format(self.controllerNOM))[len("{0}TP?")-1:]
        
    def set_zero(self):
        self.write("{0}OR".format(self.controllerNOM))
        
    def lower_limit(self,value):
        if value <0:
            self.write("{0}SL{1}".format(self.controllerNOM, value))
        else:
            print "The lower Limit must be less than 0, current lower limit = ",self.query("{0}SL?".format(self.controllerNOM))
            
    def upper_limit(self,value):
        if value >0:
            self.write("{0}SR{1}".format(self.controllerNOM, value))
        else:
            print "The upper Limit must be greater than 0, current upper limit = ",self.query("{0}SR?".format(self.controllerNOM))
             
    
        
if __name__ == '__main__':
    teststage = NanoPZ(port = "COM25")
        