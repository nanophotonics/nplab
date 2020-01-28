# -*- coding: utf-8 -*-
"""
Created on Fri Oct 05 15:13:50 2018

@author: WMD22

A nplab wrapper to the ThorlabsPM100 reppo
"""
from builtins import str
from builtins import range
from nplab.instrument import Instrument
from ThorlabsPM100 import ThorlabsPM100
import visa
import numpy as np
from nplab.ui.ui_tools import QuickControlBox
from nplab.utils.notified_property import DumbNotifiedProperty,NotifiedProperty

class ThorPM100(ThorlabsPM100,Instrument):
    num_averages = DumbNotifiedProperty()
    def __init__(self,address = 'USB0::0x1313::0x8072::P2004571::0::INSTR',
                 num_averages = 100, calibration = None):
        """A quick wrapper to create a gui and bring in nplab features to the pm100 thorlabs power meter """
        rm = visa.ResourceManager()
        instr = rm.open_resource(address)
        super(ThorPM100, self).__init__(instr)
        self.num_averages = 100
        self.ui = None
        if calibration == None:
            self.calibration = 1.0
        else:
            self.calibration = calibration
    def read_average(self,num_averages = None):
        """a quick averaging tool for the pm100 power meter """
        if num_averages==None:
            num_averages = self.num_averages
        values =[]
        for i in range(num_averages):
            values.append(self.read)
        return np.average(values)
    
    def read_average_power(self):
        """Return the average power including a calibration """
        return self.read_average()*self.calibration
    average_power = NotifiedProperty(read_average_power)
    
    def update_power(self):
        """Update the power in the gui """
        self.ui.controls['Power'].setText(str(self.average_power))
    def get_qt_ui(self):
        if self.ui ==None:
            self.ui=ThorlabsPM100_widget(self)
        return self.ui
    def set_wavelength(self,wavelength):
        self.power_meter.sense.correction.wavelength = wavelength
    def get_wavelength(self):
        return self.sense.correction.wavelength
    wavelength = NotifiedProperty(get_wavelength,set_wavelength)
        

class ThorlabsPM100_widget(QuickControlBox):
    """A very basic quick control box allowing the power meter to display the power """
    def __init__(self, power_meter):
        super(ThorlabsPM100_widget,self).__init__(title = 'PM100')
        self.power_meter = power_meter
        self.add_button('update_power')
        self.add_lineedit('Power')
      #  self.controls['average_read'].setReadOnly(True)
        self.auto_connect_by_name(controlled_object = self.power_meter)
    