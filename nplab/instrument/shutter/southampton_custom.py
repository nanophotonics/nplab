# -*- coding: utf-8 -*-
"""
Created on Tue Jun 14 11:51:46 2016

@author: rwb27
"""
from __future__ import print_function

from nplab.instrument.shutter import ShutterWithEmulatedRead
from nplab.instrument.serial_instrument import SerialInstrument
import serial
import time

class ILShutter(SerialInstrument, ShutterWithEmulatedRead):
    def __init__(self, port):
        self.port_settings = {'baudrate': 19200,
                        'bytesize':serial.SEVENBITS,
                        'parity':serial.PARITY_ODD,
                        'stopbits':serial.STOPBITS_ONE,
                        'timeout':1, #wait at most one second for a response
                        'writeTimeout':1, #similarly, fail if writing takes >1s
                        }
        self.termination_character = "\r"
        SerialInstrument.__init__(self, port=port)
        ShutterWithEmulatedRead.__init__(self)
        self.query("ct") #enable computer control
        
    def set_state(self, value):
        """Set the shutter to be either "Open" or "Closed" """
        if value.title() == "Open":
            self.query("S4U")
            self.__state = "Open"
        else:
            self.query("S4D")
            self.__state = "Closed"
        
if __name__ == "__main__":
    shutter = ILShutter("COM3")
    shutter.show_gui()
    time.sleep(1)
    shutter.expose(1)
    print(ILShutter.get_instances()) #Check there's not two here...