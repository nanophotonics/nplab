# -*- coding: utf-8 -*-
"""
Created on Tue Oct 21 15:58:04 2014

@author: Hera
"""
from __future__ import print_function

from builtins import str
from nplab.instrument.serial_instrument import SerialInstrument
from nplab.instrument.light_sources import LightSource
import serial
import sys
from PyQt4 import QtGui

class CubeLaser(SerialInstrument, LightSource):
    def __init__(self, port=None):
        self.port_settings = {'baudrate': 19200,
                        'bytesize':serial.EIGHTBITS,
                        'stopbits':serial.STOPBITS_ONE,
                        'timeout':1, #wait at most one second for a response
                        'writeTimeout':1, #similarly, fail if writing takes >1s
                        }
        self.termination_character = "\r"
        SerialInstrument.__init__(self, port=port)
        
    def get_power(self):
        """read the current power output in mW"""
        power = self.float_query("?P") 
        print("%.1f mW" % power)
        return power  
        
    def set_power(self, power):
        """set the power output in mW"""
        if 0<=power<=40:
            self.query("P=%.1f" % power)
        else:
            print('Input power must be between 0 an 40 mW')

    def mode_switch(self,pulsed=0): #if pulsed=0, then CW; if 1 then pulsed
        self.query("CW=%.f" % (1-pulsed))
        if pulsed == 0:
            mode = 'CW mode'
        elif pulsed == 1:
            mode = 'Pulsed mode'
        else:
            mode = 'pulsed must be 0 (CW) or 1 (Pulsed)'           
        print(mode)

class CubeLaserUI(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.setWindowTitle("Cube Laser")
        self.resize(300,100)
        self.move(100,1500)
        self.power_switch = QtGui.QCheckBox('Power ON',self)
        self.power_switch.clicked.connect(self.handle_power_switch)
        self.pulsed_switch = QtGui.QCheckBox('Pulsed Mode',self)
        self.pulsed_switch.clicked.connect(self.handle_pulsed_switch)
        self.power_input_label = QtGui.QLabel('Input Power:')
        self.power_input = QtGui.QDoubleSpinBox()
        self.power_input.valueChanged.connect(self.handle_power_input)
        self.power_input.setMinimum(0)
        self.power_input.setMaximum(40)
        self.power_input_unit = QtGui.QLabel('mW')
        self.power_readout_label = QtGui.QLabel('Readout Power:')
        self.power_readout = QtGui.QLabel('0.0')
        self.power_readout_unit = QtGui.QLabel('mW')

        layout = QtGui.QGridLayout(self)
        
        layout.addWidget(self.power_switch, 1, 0)
        layout.addWidget(self.power_input_label, 2, 0)
        layout.addWidget(self.power_input, 2, 1)
        layout.addWidget(self.power_input_unit, 2, 2)
        layout.addWidget(self.power_readout_label, 3, 0)
        layout.addWidget(self.power_readout, 3, 1)
        layout.addWidget(self.power_readout_unit, 3, 2)
        layout.addWidget(self.pulsed_switch, 4, 0)
        
        
    def handle_power_switch(self):
        laser = CubeLaser("COM7")
        if self.power_switch.isChecked():
            laser.set_power(self.power_input.value())
            print('Power ON')
        else:
            laser.set_power(0)
            print('Power OFF')
            
        self.power_readout.setText(str(laser.get_power()))    
        laser.close()
    
    def handle_pulsed_switch(self):
        laser = CubeLaser("COM7")
        if self.pulsed_switch.isChecked():
            laser.mode_switch(1)
        else:
            laser.mode_switch(0)
        self.power_readout.setText(str(laser.get_power()))    
        laser.close()
    
    def handle_power_input(self):
        laser = CubeLaser("COM7")
        if self.power_switch.isChecked():
            laser.set_power(self.power_input.value())
        else:
            laser.set_power(0)      
        self.power_readout.setText(str(laser.get_power()))    
        laser.close()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    win = CubeLaserUI()
    win.show()
    #sys.exit(app.exec_())
    #laser = CubeLaser("COM7")
    #laser.set_power(10)
    #laser.close()