# -*- coding: utf-8 -*-
"""
Created on Tue Oct 21 15:58:04 2014

@author: Hera
"""


from nplab.instrument.serial_instrument import SerialInstrument
from nplab.instrument.light_sources import LightSource
import serial
from contextlib import closing

class OndaxLaser(SerialInstrument, LightSource):
    def __init__(self, port=None):
        self.port_settings = {'baudrate': 9600,
                        'bytesize':serial.EIGHTBITS,
                        'stopbits':serial.STOPBITS_ONE,
                        'parity':serial.PARITY_NONE,
                        'timeout':1, #wait at most one second for a response
                        'writeTimeout':1, #similarly, fail if writing takes >1s
                        }
        self.termination_character = "\r\n"
        SerialInstrument.__init__(self, port=port)
        LightSource.__init__(self)
        self.min_power=12
        self.max_power=70
        
    def get_power(self):
        """read the current power output in mW"""
        return self.float_query("rli?")

    def readpower(self):
        """deprecated: returns get_power()"""
        return self.get_power()        
        
    def set_power(self, power):
        """set the power output in mW"""
        power = float(power)
        assert power <= self.max_power, ValueError("Exceeded maximum power")
        assert power >= self.min_power, ValueError("Below minimum power")
        self.query("slc:%f" % power)
        return self.readpower()
        
if __name__ == "__main__":
    laser = OndaxLaser("COM1")
    with closing(laser):
        laser.show_gui()
    laser.close()