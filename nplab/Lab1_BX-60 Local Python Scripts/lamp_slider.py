# -*- coding: utf-8 -*-
"""
Created on Wed Mar 23 12:33:12 2022

@author: nsm44

improvised white-light shutter code.
this code controls the white light shutter of an olympus bx60 which is motorized through an arduino-controlled motor.

"""

from nplab.ui.ui_tools import QuickControlBox
from nplab.instrument.shutter import Shutter
import time
from nplab.instrument.serial_instrument import SerialInstrument


class LampSlider(Shutter, SerialInstrument):
    termination_character = '\n'
    termination_read = '\r\n'
    def __init__(self, port=None):
        SerialInstrument.__init__(self, port)
        Shutter.__init__(self)
        self._state = None
        self.timeout = 2
        time.sleep(2)
        self.query('E60')
        self.open_shutter()
    
    def query(self, *args, **kwargs):
        out = super().query(*args, **kwargs)
        self.log(out, 'info')
        while self.readline() != '':
            pass
        print('finished query lamp slider' + str(self.readline()))
        return out

    def get_state(self, report_success=False):
        return self._state

    def set_state(self, state):
        if state != self._state:
            if state == 'Open':
                self.query('O')
                self._state = 'Open'
    
            elif state == 'Closed':
                self.query('C')
                self._state = 'Closed'
    
            time.sleep(1.5)

    def lamp_on(self):
         self.set_state('Open')

    def lamp_off(self):
         self.set_state('Closed')

    def get_qt_ui(self):
        """Return a graphical interface for the lamp slider."""
        return LampSliderUI(self)

class LampSliderUI(QuickControlBox):
    def __init__(self, lamp_slider):
        super().__init__(title='wutter')
        self.lamp_slider = lamp_slider
        self.add_button('lamp_on')  # or function to connect
        self.add_button('lamp_off')  # or function to connect
        self.auto_connect_by_name(controlled_object=lamp_slider)


if __name__ == '__main__':
    ls = LampSlider('COM4')
    ls._logger.setLevel('INFO')
    ui = ls.show_gui(False)
    ui.show()
