# -*- coding: utf-8 -*-
"""
Created on Tue Oct 21 15:58:04 2014

@author: Hera
"""


from nplab.instrument.serial_instrument import SerialInstrument
from nplab.instrument.light_sources import LightSource
import serial

class CubeLaser(SerialInstrument, LightSource):
    def __init__(self, port=None):
        self.port_settings = {'baudrate': 19200,
                        'bytesize':serial.EIGHTBITS,
                        'stopbits':serial.STOPBITS_ONE,
                        'timeout':1, #wait at most one second for a response
                        'writeTimeout':1, #similarly, fail if writing takes >1s
                        }
        self.termination_character = "\r"
        SerialInstrument.__init__(self, port=port)
        
    def get_power(self):
        """read the current power output in mW"""
        return self.float_query("?P")

    def readpower(self):
        """deprecated: returns get_power()"""
        return self.get_power()        
        
    def set_power(self, power):
        """set the power output in mW"""
        self.query("P=%.2f" % power)
        return self.readpower()
        
if __name__ == "__main__":
    laser = CubeLaser("COM4")
    laser.show_gui()
    laser.close()