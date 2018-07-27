# -*- coding: utf-8 -*-
"""
Created on Tue Oct 21 15:58:04 2014

@author: Hera
"""


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
        print "DAC current:  %.2f mA" % DAC
        return readout
        
    def set_power(self, power):
        """set the power output in mW"""
        self.query("c u 1 1234")
        #self.query("c 4 %.2f" % power)
        number='{0:012b}'.format(power)
        self.query("c 6 %int" % int(number))
        return self.readpower()
        
if __name__ == "__main__":
    laser = MatchboxLaser("COM9")
    laserID=laser.query("ID?")
    laserName=laser.query("NM?")
    #laser.show_gui()
    #laser.close()