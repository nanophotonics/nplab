# -*- coding: utf-8 -*-
"""
Created on Thu Jul 06 13:57:22 2017

@author: Hera
"""
from builtins import str
import serial
import numpy as np

from nplab.instrument.serial_instrument import SerialInstrument
from nplab.utils.notified_property import NotifiedProperty
from nplab.ui.ui_tools import QuickControlBox


class Maitai(SerialInstrument):
    port_settings = dict(baudrate=38400,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1, #wait at most one second for a response
                        writeTimeout=1, #similarly, fail if writing takes >1s
                        xonxoff=True, rtscts=False, dsrdtr=False,
                    )
    termination_character = "\n"
    def __init__(self, port):
        '''Maitai Ti:saphire laser: just requires port number to inialise '''
        super(Maitai, self).__init__(port)
        self.set_watchdog(0)
    
    def on(self):
        '''Turn the Maitai on'''
        self.write('ON')
    def off(self):
        '''Turn the Maitai off'''
        self.write('OFF')
    def open_shutter(self):
        '''Opens the shutter using the shutter state property'''
        self.shutter_state = True
    def close_shutter(self):
        '''Close the shutter using the shutter state property '''
        self.shutter_state = False
    def get_shutter_state(self):
        '''Get shutter state and convert it to a bool
        returns:
            bool: True == open and False == close'''
        return bool(int(self.query('SHUTTER?')))
    def set_shutter_state(self,state):
        ''' Sets the shutter from a bool
        Args:
            bool True == Open, false == closed
        '''
        self.write('SHUTTER '+str(int(state)))
    shutter_state = NotifiedProperty(get_shutter_state,set_shutter_state)
        
    def get_humidity(self):
        '''Returns the humidity '''
        return self.query('READ:HUM?')
    def get_power(self):
        '''Returns the IR power
        '''
        return self.query('READ:POWER?')
    
    def get_green_power(self):
        '''Returns the IR power
        '''
        return self.query('READ:PLASER:POWER?')
    def get_current_wavelength(self):
        ''' The current real time wavelength - allowing you to check if the maitai ahs moved to the set wavelength yet
        '''
        return self.query('READ:WAVELENGTH?')
    current_wavelength = property(get_current_wavelength)
    def save(self):
        '''Save tje current maitai settings for restart '''
        self.write('SAVE')
    def get_set_wavelength(self):
        ''' wavelength(float):  The current set wavelength of the Maitai (in nm)
                                must between 690 and 1020
        '''
        return float(self.query('WAVELENGTH?')[:-2])
#    def set_wavelength(self,wavelength):
#        if wavelength>690 and wavelength<1020:
#            return self.write('WAVELENGTH ')
#        else:
#            self.log('Wavelength out of range ('+wavelength+')')
        
    def set_wavelength(self,wavelength):
        if wavelength>690 and wavelength<1020:
            return self.write('WAVelength ' + str(wavelength))
        else:
            self.log('Wavelength out of range ('+wavelength+')')            
        
    wavelength = NotifiedProperty(get_set_wavelength,set_wavelength)
    
    def set_watchdog(self,n):
        '''Sets the watchdog timer i.e. the ammount of time the laser will 
        keep itself on without stay alive command. If set to zero this is disabled
        '''
        self.write('TIMER:WATCHDOG '+str(n))
        
    def get_qt_ui(self):
        return MaitaiControlUI(self)
class MaitaiControlUI(QuickControlBox):
    '''Control Widget for the MaiTai laser
    '''
    def __init__(self,maitai):
        super(MaitaiControlUI,self).__init__(title = 'MaiTai')
        self.maitai = maitai
        self.add_button('on')
        self.add_button('off')
        self.add_button('open_shutter')
        self.add_button('close_shutter')
        self.add_doublespinbox("wavelength")
        self.auto_connect_by_name(controlled_object = self.maitai)
    
        