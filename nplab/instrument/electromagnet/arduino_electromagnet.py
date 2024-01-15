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
import serial
from time import sleep

class Magnet(SerialInstrument):
    termination_character = '\n'
    legal_input='NSZs' # there are the allowed inputs: N sets North, S-South, Z-zero,s-query device for it's state
    port_settings = {'baudrate': 9600,
                     'timeout': 0.05,
                     'bytesize':serial.EIGHTBITS,
                     'parity':serial.PARITY_NONE,
                     'stopbits':serial.STOPBITS_ONE,
                     'writeTimeout':0.05, 
                     }

    def __init__(self, port=None): # initialize communication and set device to zero
        SerialInstrument.__init__(self, port)
        self._state = None
        self.set_state('Z')
        self.flush_input_buffer()
    
    def correct_input(self, letter): # check legal input
        if (len(letter)==1) and (letter in self.legal_input): 
            return True
        else:
            return False
       
    def get_state(self, report_success=False): # query current state
        s = self.query('s')
        self.flush_input_buffer()
        return s

    def set_state(self, state): # set state
        if self.correct_input(state):
            if state != self._state:
                #self.write(state)
                #self._state = self.get_state()
                #self._state = self.ser.write(bytes(state, "ASCII"))
                self._state = self.query(state)
        #self.flush_input_buffer()
        return self._state

    
    # def flush_buffer(self, *args, **kwargs):
    #     while self.readline() != '':
    #         pass
    #     print('finished flushing buffer' + str(self.readline()))
    #     return out
                    
    
    def North(self):
         return self.set_state('N')

    def Zero(self):
        return self.set_state('Z')
    
    def South(self):
        return self.set_state('S')
     
    def get_qt_ui(self):
        """Return a graphical interface for the lamp slider."""
        return MagnetUI(self)

    def test(self,N=10,sleep_time=1):
        for qq in range(N):
            print(magnet.North())
            print('north')
            sleep(sleep_time)
            print(magnet.Zero())
            print('zero')
            sleep(sleep_time)
            print(magnet.South())
            sleep(sleep_time)
            print('south')
        

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
    magnet = Magnet('COM6')
    #magnet._logger.setLevel('INFO')
    ui = magnet.show_gui(False)
    # ui.show()

