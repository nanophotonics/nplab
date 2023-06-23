# -*- coding: utf-8 -*-
"""
Created on Fri Aug  6 16:52:49 2021

@author: Hera
"""

from nplab.utils.notified_property import NotifiedProperty
from nplab.ui.ui_tools import QuickControlBox
from nplab.instrument.stage.thorlabs_ello import ElloDevice


class Ell6(ElloDevice):
    positions = 2

    def __init__(self, serial_device, device_index=0, debug=0):
        '''can be passed either a BusDistributor instance, or  "COM5"  '''
        super().__init__(serial_device, device_index=0, debug=0)
        self.home()

    def home(self):
        self.query_device('ho')
        self._position = 0

    def set_position(self, pos):
        assert 0 <= pos < self.positions
        
        while pos > self._position:
            self.move_forward()
        while pos < self._position:
            self.move_backward()
        
    def get_position(self):
        return self._position
   
    position = NotifiedProperty(get_position, set_position)

    def get_qt_ui(self):
        '''
        Get UI for stage
        '''

        return ELL6UI(self)

    def move_forward(self):
        self.query_device('fw')
        self._position += 1

    def move_backward(self):
        self.query_device('bw')
        self._position -= 1
    

class ELL6UI(QuickControlBox):
    def __init__(self, instr):
        super().__init__('ELL6')
        self.add_spinbox('position', vmin=0, vmax=1)
        self.auto_connect_by_name(controlled_object=instr)


if __name__ == '__main__':
    # f = ThorlabsELL6('COM9')
    f = ThorlabsELL6('COM6')
    f.show_gui(False)
