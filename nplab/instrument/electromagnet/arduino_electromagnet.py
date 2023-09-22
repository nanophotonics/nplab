# -*- coding: utf-8 -*-
"""
@author: jb2444

controls an electromagnet through an arduino with 4 relays.
inherits from Serial instrument (as it is controlled over COM)
and has 4 basic functions: North, South, Zero, and get_state (which returns currnt state)
there are also an input check function and a set function. 
this is designed to work with the arduino function: 
    'nplab\instrument\arduino\electromagnet_control_final.ino
it is possible to read the reply of the device, which returns the new state - 
for example when commanded 'N' the reply would be 'N':
    ans=magnet.query('N')
    print(ans)


"""

from nplab.ui.ui_tools import QuickControlBox
from nplab.instrument.serial_instrument import SerialInstrument


class Magnet(SerialInstrument):
    termination_character = '\n'
    legal_input='NSZs' # there are the allowed inputs: N sets North, S-South, Z-zero,s-query device for it's state
    port_settings = {'baudrate': 9600,
                     'timeout': 0.05}
    def __init__(self, port=None): # initialize communication and set device to zero
        SerialInstrument.__init__(self, port)
        self._state = None
        self.set_state('Z')
        
    
    def correct_input(self, letter): # check legal input
        if (len(letter)==1) and (letter in self.legal_input): 
            return True
        else:
            return False
       
    def get_state(self, report_success=False): # query current state
        return self.query('s')

    def set_state(self, state): # set state
        if self.correct_input(state):
            if state != self._state:
                self._state = self.query(state)
    
    def flush_buffer(self, *args, **kwargs):
        out = super().query(*args, **kwargs)
        self.log(out, 'info')
        while self.readline() != '':
            pass
        print('finished flushing buffer' + str(self.readline()))
        return out            
    
    def North(self):
         self.set_state('N')

    def Zero(self):
        self.set_state('Z')
    
    def South(self):
        self.set_state('S')
     
    def get_qt_ui(self):
        """Return a graphical interface for the lamp slider."""
        return MagnetUI(self)

class MagnetUI(QuickControlBox):
    def __init__(self, Magnet):
        super().__init__(title='Magnet')
        self.Magnet = Magnet
        self.add_button('North')  # or function to connect
        self.add_button('South')  # or function to connect
        self.add_button('Zero')  # or function to connect
        self.auto_connect_by_name(controlled_object=Magnet)

#%%
if __name__ == '__main__':
    magnet = Magnet('COM3')
    magnet._logger.setLevel('INFO')
    ui = magnet.show_gui(False)
    # ui.show()
