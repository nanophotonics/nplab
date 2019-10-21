# -*- coding: utf-8 -*-
"""
Created on Mon Aug 14 11:00:00 2019

@author: Giovanni Orlando
"""
from nplab.instrument.serial_instrument import SerialInstrument
from nplab.instrument.shutter import Shutter
from nplab.ui.ui_tools import QuickControlBox
from nplab.utils.notified_property import NotifiedProperty

class Arduino_TTL_shutter(SerialInstrument,Shutter):
    '''A class for the Piezoconcept objective collar '''

    def __init__(self, port=None):
        '''Set up baudrate etc and recenters the stage to the center of it's range (50um)
        
        Args:
            port(int/str):  The port the device is connected 
                            to in any of the accepted serial formats
            
        '''
        self.termination_character = '\n'
        self.port_settings = {
                    'baudrate':9600,
             #       'bytesize':serial.EIGHTBITS,
                    'timeout':2, #wait at most one second for a response
                    }
        self.termination_character = '\n'
        SerialInstrument.__init__(self,port=port)
        Shutter.__init__(self)
    def get_state(self):
        return self.query('Read')
    def set_state(self,state):
        self.query(state)

        
class Arduino_tri_shutter(SerialInstrument):
    '''Control class for tri shutter '''

    def __init__(self, port=None):
        '''Set up baudrate etc and recenters the stage to the center of it's range (50um)
        
        Args:
            port(int/str):  The port the device is connected 
                            to in any of the accepted serial formats
            
        '''
        self.termination_character = '\n'
        self.port_settings = {
                    'baudrate':9600,
             #       'bytesize':serial.EIGHTBITS,
                    'timeout':2, #wait at most one second for a response
                    }
        self.termination_character = '\r\n'
        SerialInstrument.__init__(self,port=port)
    def set_shutter_1_state(self,state):
        """Set State Command for Shutter 1 used by check box """
        if state == True:
            self._open_shutter_1()
        elif state == False:
            self._close_shutter_1()
            
    def set_shutter_2_state(self,state):
        """Set State Command for Shutter 2 used by check box """
        if state == True:
            self._open_shutter_2()
        elif state == False:
            self._close_shutter_2()
            
    def set_mirror_1_state(self,state):
        """Set State Command for flipper 1 used by check box """
        if state == True:
            self._flip_mirror_0()
        elif state == False:
            self._flip_mirror_1()
            
            

    def open_shutter_1(self):
        """Usable open shutter 1 function that updates GUI when used"""
        self.Shutter_1_State = True
    def close_shutter_1(self):
        """Usable close shutter 1 function that updates GUI when used"""
        self.Shutter_1_State = False
    def open_shutter_2(self):
        """Usable open shutter 2 function that updates GUI when used"""
        self.Shutter_2_State = True
    def close_shutter_2(self):
        """Usable close shutter 2 function that updates GUI when used"""
        self.Shutter_2_State = False
        
    def flip_mirror_0(self):
        """Usable open flip_mirror 1  function that updates GUI when used"""
        self.Flipper_1_State = False
    def flip_mirror_1(self):
        """Usable close flip mirror 1 function that updates GUI when used"""
        self.Flipper_1_State = False
        
        
        
    def _open_shutter_1(self):
        """do not use! Hidden access to open shutter """
        self.query('A')
    def _close_shutter_1(self):
        """do not use! hidden close shutter function"""
        self.query('B')
    def _open_shutter_2(self):
        """do not use! Hidden access to open shutter """
        self.query('C')
    def _close_shutter_2(self):
        """do not use! hidden close shutter function"""
        self.query('D')
    def _flip_mirror_0(self):
        """do not use! hidden open flipper function"""
        self.query('E')
    def _flip_mirror_1(self):
        """do not use! hidden open flipper function"""
        self.query('F')
        
 #   def get_state(self):
 #       return self.query('Read')
 #   def set_state(self,state):
 #       self.query(state)
    def get_qt_ui(self):
        self.ui = tri_shutter_ui(self)
        return self.ui
    def read_state(self):
        states = self.query('S')
        states = states.split(',')
        states = [bool(int(state)) for state in states]
        return states
    states = NotifiedProperty(fget= read_state)
    def get_state_1(self):
        return self.states[0]
    def get_state_2(self):
        return self.states[1]    

    def get_state_3(self):
        return self.states[2]

    
    Shutter_1_State = NotifiedProperty(fset = set_shutter_1_state, fget = get_state_1)
    Shutter_2_State = NotifiedProperty(fset = set_shutter_2_state, fget = get_state_2)
    Flipper_1_State = NotifiedProperty(fset = set_mirror_1_state, fget = get_state_3)    

    #      self.get_state()
  
class tri_shutter_ui(QuickControlBox):
    '''Control Widget for the Shamrock spectrometer
    '''
    def __init__(self,shutter):
        super(tri_shutter_ui,self).__init__(title = 'Tri_shutter')
        self.shutter = shutter
        self.add_checkbox('Shutter_1_State')
        self.add_checkbox('Shutter_2_State')
        self.add_checkbox('Flipper_1_State')
        self.auto_connect_by_name(controlled_object = self.shutter)
if __name__ == '__main__':
    shutter = Arduino_tri_shutter(port = 'COM4')
    
    