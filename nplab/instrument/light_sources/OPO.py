# -*- coding: utf-8 -*-
"""
Created on Fri Feb 02 15:21:59 2018

@author: wmd22
"""

from builtins import str
from nplab.instrument.serial_instrument import SerialInstrument
from nplab.utils.notified_property import NotifiedProperty

import serial
class inspire_OPO(SerialInstrument):
    port_settings = dict(baudrate=9600,
                         bytesize=serial.EIGHTBITS,
                         parity=serial.PARITY_NONE,
                         stopbits=serial.STOPBITS_ONE,
                         timeout=1,  #wait at most one second for a response
                         writeTimeout=1,  #similarly, fail if writing takes >1s
                         xonxoff=False, rtscts=False, dsrdtr=False,
                         )
    
    def __init__(self, port):
        self.mode = 'power'
        self.initialise()
        
    def initialise(self):
        self.write('00 550.0')
    
    def set_wavelength(self,wavelength):
        wavelength=str(int(wavelength))+'.0'
        self.write(self.mode_dict[self.mode]+ wavelength)
    def get_wavelength(self):
        wavelength = self.query('50 550.0')
        return wavelength
    wavelength = NotifiedProperty(get_wavelength,set_wavelength)
    def enable_power_mode(self):
        self.query(mode_dict['power']+' '+self.wavelength)
    mode_dict = {'tune':'03',
                 'power':'04'}
    def SHG_on(self):
        self.query('08 000.0')
    def SHG_off(self):
        self.query('09 000.0')
    def SHG_find(self):
        self.query('10 000.0')
    def SHG_optimise(self):
        self.query('11 000.0')
    
    def auto_cavity(self):
        self.query('07 '+self.wavelength)
        
#    def get_spectrum(self):
        