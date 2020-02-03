# -*- coding: utf-8 -*-
"""
Created on Thu Dec 19 16:24:49 2019

@author: ee306
"""


import numpy as np

import time
from nplab.utils.gui import QtCore, QtWidgets, uic
from nplab.utils.notified_property import DumbNotifiedProperty, register_for_property_changes
from nplab.ui.ui_tools import UiTools
from nplab.instrument import Instrument
import threading
import os

class PowerMeter(Instrument):
    '''
    brings basic nplab functionality, and a gui with live mode to a powermeter.
    The minimum you need to do to subclass this is overwrite the read_power method
    '''
    live = DumbNotifiedProperty(False)
    def __init__(self):
        super(PowerMeter, self).__init__()
        
    def read_power(self):
        raise NotImplementedError
    @property
    def power(self):
        return self.read_power()
        
    def get_qt_ui(self):
        return PowerMeterUI(self)
    
class PowerMeterUI(QtWidgets.QWidget, UiTools):
    update_data_signal = QtCore.Signal(np.ndarray)
    def __init__(self, pm):    
        super(PowerMeterUI, self).__init__()
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'power_meter.ui'),self)
        self.pm = pm        
        self.update_condition = threading.Condition()        
        self.display_thread = DisplayThread(self)        
        self.SetupSignals()
        register_for_property_changes(self.pm, 'live', self.live_changed)
    def SetupSignals(self):
        self.read_pushButton.clicked.connect(self.button_pressed)
        self.live_button.clicked.connect(self.button_pressed)
        self.display_thread.ready.connect(self.update_display)
    def button_pressed(self):
        if self.sender() == self.read_pushButton:
            self.display_thread.single_shot = True
        elif self.sender() == self.live_button:
            self.pm.live = self.live_button.isChecked()
        self.display_thread.start()
    def update_display(self, power):
        self.power_lcdNumber.display(float(power))
    def live_changed(self, new):
        print('delete_me')
        self.live_button.setChecked(new)
        
class DisplayThread(QtCore.QThread):
    ready = QtCore.Signal(float)
    def __init__(self, parent):
        super(DisplayThread, self).__init__()
        self.parent = parent
        self.single_shot = False
        self.refresh_rate = 4.

    def run(self):
        t0 = time.time()
        while self.parent.pm.live or self.single_shot:
            p = self.parent.pm.power
            if time.time()-t0 < 1./self.refresh_rate:
                continue
            else:
                t0 = time.time()
            self.ready.emit(p)
            if self.single_shot:
                self.single_shot = False               
                break
        self.finished.emit()
        
class dummyPowerMeter(PowerMeter):
    def __init__(self):
        super(PowerMeter, self).__init__()
    def read_power(self):
        return np.random.rand()*10

if __name__ == '__main__':
    dpm = dummyPowerMeter()
    dpm.show_gui(blocking = False)
    
    
    
        
    
