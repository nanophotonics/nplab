# -*- coding: utf-8 -*-

__author__ = 'jm806'


from nplab.instrument.shutter import ShutterWithEmulatedRead
from nplab.instrument.serial_instrument import SerialInstrument
import serial
import time

class Uniblitz(ShutterWithEmulatedRead, SerialInstrument):
    """
    Shutter controller from Uniblitz for BX51 white light path
    """
    def __init__(self, port=None):
        self.port_settings = {'baudrate': 9600,
                        'bytesize':serial.EIGHTBITS,
                        'parity':serial.PARITY_NONE,
                        'stopbits':serial.STOPBITS_ONE,
                        'timeout':1, #wait at most one second for a response
                        'writeTimeout':1, #similarly, fail if writing takes >1s
                        }
        self.termination_character = "\r"
        SerialInstrument.__init__(self, port=port)
        ShutterWithEmulatedRead.__init__(self)
        self.shutter_state = 0
    
    def set_state(self,state):
        if state=='Open':
            self.ser.write(str.encode('@'))
        elif state == 'Closed': 
            self.ser.write(str.encode('A'))
        # time.sleep(0.1)
#
#    def toggle(self):
#        if self.shutter_state == 'Open':
#            self.close_shutter()
#        elif self.shutter_state == 'Closed':
#            self.open_shutter()

#    def open_shutter(self):
#        # using write commands from the instrument class causes errors (at least on my computer...)
#        # Error message: 'ser' does not have an attribute 'outWaiting'
#        self.ser.write('@')
#        self.shutter_state = 1
#
#    def close_shutter(self):
#        self.ser.write('A')
#        self.shutter_state = 0


if __name__ == '__main__':

    shutter = Uniblitz('COM7')
    # shutter.show_gui()
    # shutter.close()