# -*- coding: utf-8 -*-
"""
Created on Tue Oct 21 15:58:04 2014

@author: Hera
"""
from __future__ import print_function


from nplab.instrument.serial_instrument import SerialInstrument
from nplab.instrument.light_sources import LightSource
import serial
import numpy as np

class MatchboxLaser(SerialInstrument, LightSource):
    def __init__(self, port=None):
        self.port_settings = {'baudrate': 115200,
                        'bytesize':serial.EIGHTBITS,
                        'stopbits':serial.STOPBITS_ONE,
                        'timeout':1, #wait at most one second for a response
                        'writeTimeout':1, #similarly, fail if writing takes >1s
                        }
        self.termination_character = "\r"
        SerialInstrument.__init__(self, port=port)
        self.turn_on()
        
    def __del__(self):
        self.turn_off()
        return 

    def close(self):
        self.turn_off()
        self.__del__()

    def turn_on(self):
        """change laser status from off to on"""
        self.query("e 1")
        
    def turn_off(self):
        """change laser status from on to off"""
        self.query("e 0")        
    
    def get_power(self):
        """read the current power output in mW"""
        readings=self.query("r r")
        readout=np.fromstring(readings[11:], dtype=np.float,sep=' ' ,count=4)
        return readout[3]


    def readpower(self):
        """deprecated: returns get_power()"""
        return self.get_power()   

        
    def read_setParameters(self):
        """read out set Parameters: Set T1 (deg.), set T2  (deg.), set LD current (mA),
        set Optical power 12bit range, set Optical power (mW),max allowed LD current (mA),
        Autostart enable (boolean), access leve; (float)"""
        readings=self.query("r s")
        settings=np.fromstring(readings, dtype=np.float,sep=' ' ,count=8)
        return settings
        
    def read_parameters(self):
        """read out Parameters: T1 (deg.), T2  (deg.),T3 (deg.),LD current (mA),
        TEC1 load%, TEC2 load%, laserstatus"""
        readings=self.query("r r")
        readout=np.fromstring(readings[11:], dtype=np.float,sep=' ' ,count=4)
        DAC=readout[3]
        print("DAC current:  %.2f mA" % DAC)
        return readout
        
    def set_power(self, power):
        """Set optical power DAC in 12 bit full range"""
        '''Max value: 8191, min value 0
        Note: this does not turn off the laser
        '''
        power = abs(int(power))
        print("Setting power:{} (min:0, max: 8191)".format(power))
        self.query("c 6 {}".format(power))
        return self.get_power()
        
if __name__ == "__main__":
    laser = MatchboxLaser("/dev/ttyUSB0")
    laserID=laser.query("ID?")
    laserName=laser.query("NM?")
    laser.show_gui()
    laser.close()