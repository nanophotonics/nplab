# -*- coding: utf-8 -*-
"""
Created on Mon May 19 14:42:05 2025

@author: il322


Nplab class + UI for Varia Monochromator for NKT SuperK EVO system. 
Simple set wavelength, get wavelength/bandwidth functions
Can declare shutter to close during set_wavelength and set_bandwidth for safetty while changing wavelengths
Relies on nkt_tools library (pip install nkt_tools)

Can expand to control SuperK EVO white light laser as well...
Also, there's no monochromator parent class...
"""

import os
import time
import tqdm
import numpy as np
import nkt_tools.varia
import nkt_tools.NKTP_DLL as nkt
import nplab
from nplab.instrument import Instrument
from nplab.utils.notified_property import NotifiedProperty
from nplab.utils.gui import QtGui, QtWidgets, uic
from nplab.ui.ui_tools import UiTools
from nplab.instrument.shutter.thorlabs_sc10 import ThorLabsSC10
# shutter = ThorLabsSC10('COM11')



class Varia(Instrument, nkt_tools.varia.Varia):

    def __init__(self, shutter = None):
        Instrument.__init__(self)
        nkt_tools.varia.Varia.__init__(self)
        
        if issubclass(type(shutter), nplab.instrument.shutter.Shutter):
            self.shutter = shutter
        else:
            self.shutter = None
            print('\nWarning: No Shutter set for Varia! set_wavelength() and set_bandwidth() operations will not close shutter before setting new wavelength')

        self.set_wavelength(600, 10)

    def get_bandwidth(self):
        
        bandwidth = self.long_setpoint - self.short_setpoint
        return bandwidth
    
    def get_wavelength(self):
    
        wavelength = (self.long_setpoint + self.short_setpoint)/2   
        return wavelength

    def is_filter_moving(self):
        
        """
        Check if any of the three monochromator filters are currently moving
        """
        
        register_address = 0x66
        result, byte = nkt.registerReadU16(self.portname, self.module_address,
                                           register_address, -1)
        bits = bin(byte)
        
        if len(bits) <= 11:
            filter_moving = False
        elif bits[12] + bits[13] + bits[14] != 0:
            filter_moving = True
        else:
            filter_moving == False
        
        return filter_moving

    def set_wavelength(self, wavelength, bandwidth = 10):
        
        ## Close shutter if set and if open
        if self.shutter is not None:
            shutter_state = self.shutter.get_state()
            
            if shutter_state == 'Open':
                self.shutter.close_shutter()
        
        ## Change wavelength
        self.short_setpoint = wavelength - (bandwidth/2)
        self.long_setpoint = wavelength + (bandwidth/2)
        while self.is_filter_moving() == True:
            time.sleep(0.1)
        
        ## Open shutter if it was open
        if self.shutter is not None and shutter_state == 'Open':
            self.shutter.open_shutter()
            
        ## Warning if wavelength is out of recommended range
        if self.long_setpoint > 850 or self.short_setpoint < 390:
            print('Warning: Varia wavelength is outside of reliable range (400 - 840 nm)')

    def set_bandwidth(self, bandwidth):
        
        ## Close shutter if set and if open
        if self.shutter is not None:
            shutter_state = self.shutter.get_state()
                        
            if shutter_state == 'Open':
                self.shutter.close_shutter()
              
        ## Change bandwidth
        wavelength = self.get_wavelength()
        self.short_setpoint = wavelength - (bandwidth/2)
        self.long_setpoint = wavelength + (bandwidth/2)
        while self.is_filter_moving() == True:
            time.sleep(0.1)
        
        ## Open shutter if it was open
        if self.shutter is not None and shutter_state == 'Open':
            self.shutter.open_shutter()

        ## Warning if bandwidth is out of recommended range
        if self.get_bandwidth() < 10 or self.get_bandwidth() > 100:
            print('Warning: Varia bandwidth exceeds reliable range (10 - 100 nm FWHM)')
        
        ## Warning if wavelength is out of recommended range
        if self.long_setpoint > 850 or self.short_setpoint < 390:
            print('Warning: Varia wavelength is outside of reliable range (400 - 840 nm)')

class VariaControlUI(QtWidgets.QWidget,UiTools):
    def __init__(self, varia, ui_file =os.path.join(os.path.dirname(__file__),'varia.ui'),  parent=None):
        assert isinstance(varia, Varia), "instrument must be a Varia"
        super(VariaControlUI, self).__init__()
        uic.loadUi(ui_file, self)
        self.varia = varia
        self.centre_wl_lineEdit.returnPressed.connect(self.set_wl_gui)
        self.bw_lineEdit.returnPressed.connect(self.set_bw_gui)     
        self.centre_wl_lineEdit.setText(str(self.varia.get_wavelength()))
        self.bw_lineEdit.setText(str(self.varia.get_bandwidth()))
    def set_wl_gui(self):
        self.varia.set_wavelength(float(self.centre_wl_lineEdit.text().strip()))
    def set_bw_gui(self):
        self.varia.set_bandwidth(float(self.bw_lineEdit.text().strip()))


if __name__ == "__main__":

	v = Varia(shutter = None)
	ui = VariaControlUI(varia = v)
	ui.show()
