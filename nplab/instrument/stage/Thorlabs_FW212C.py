# -*- coding: utf-8 -*-
"""
Created on Thu Nov 19 18:00:32 2015

@author: Felix Benz (fb400)
"""

from builtins import str
from builtins import object
import visa

class FW212C(object):
    def __init__(self):
        self.visa_address = str('ASRL4::INSTR')
        self.baud_rate=115200
        self.num_position=12
        self.sept_str="\r"
        self.prompt_str=">"
        rm = visa.ResourceManager()
        self.device = rm.open_resource('ASRL4::INSTR', baud_rate=self.baud_rate, read_termination=self.sept_str,write_termination='', timeout=1000)
        
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
    