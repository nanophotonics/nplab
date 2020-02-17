# -*- coding: utf-8 -*-
"""
Created on Thu Nov 19 18:00:32 2015

@author: Felix Benz (fb400)
"""

from builtins import range
from builtins import str
from nplab.instrument import Instrument
import visa
from nplab.ui.ui_tools import UiTools
from nplab.utils.gui import QtWidgets, uic
import os
class FW212C(Instrument):
    def __init__(self, address = 'ASRLCOM7::INSTR'):
        self.visa_address = str(address)
        self.baud_rate=115200
        self.num_position=12
        self.sept_str="\r"
        self.prompt_str=">"
        rm = visa.ResourceManager()
        self.device = rm.open_resource(self.visa_address, baud_rate=self.baud_rate, read_termination=self.sept_str,write_termination='', timeout=1000)
        self.setSpeedMode(1)
        self.setSensorMode(0)
        self.setPositionCount(self.num_position)
    
    def clear(self):
        self.device.read()

    def write(self,msg):
        self.device.write(msg+self.sept_str)
        self.clear()    
    
    def query(self,msg):
        self.device.query(msg+self.sept_str)
        return int(self.device.read())    
    
    def setPosition(self,position):
        self.write("pos="+str(position))    
    def getPosition(self):
        pos=self.query("pos?")
        return int(pos)  
    position = property(getPosition, setPosition)  
    
    def setPositionCount(self,posCount):
        self.write("pcount="+str(int(posCount)))
       
    def getPositionCount(self):
        return int(self.query("pcount?"))
        
    def setSpeedMode(self,mode):
        #slow: 0, fast:1
        self.write("speed="+str(int(mode)))
        
    def getSpeedMode(self):
        #slow: 0, fast:1
        return int(self.query("speed?"))
        
    def setSensorMode(self,mode):
        #off when idle: 0, always on: 1
        self.write("sensors="+str(int(mode)))
        
    def getSensorMode(self):
        #off when idle: 0, always on: 1
        return int(self.query("sensors?"))
        
    def saveSettings(self):
        self.write("save")
        
    def shutdown(self):
        self.device.close()
    def get_qt_ui(self):
        return FW212C_UI(self)

class FW212C_UI(QtWidgets.QWidget, UiTools):
    def __init__(self, fw):
        super(FW212C_UI, self).__init__()
        self.fw = fw
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'thorlabs_fw212c.ui'), self)
        for button in range(1,13):#1-12
            eval('self.radioButton_'+str(button)+'.clicked.connect(self.button_pressed)')
    def button_pressed(self):
        '''buttons are called radioButton_x'''
        self.fw.position = int(self.sender().objectName().split('_')[-1])
if __name__ == '__main__':
    fw = FW212C()
    fw.show_gui(blocking = False)
    