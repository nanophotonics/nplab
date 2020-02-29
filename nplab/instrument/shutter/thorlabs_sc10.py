from __future__ import print_function
from builtins import str
__author__ = 'alansanders'

from nplab.instrument.shutter import Shutter
import nplab.instrument.serial_instrument as serial

def bool_to_state(Bool):
    if Bool:
        return 'Open'
    if not Bool:
        return 'Closed'
def state_to_bool(state):
    if state == 'Open':
        return True
    if state == 'Closed':
        return False

class ThorLabsSC10(Shutter, serial.SerialInstrument):
    port_settings = dict(baudrate=9600,
                         bytesize=serial.EIGHTBITS,
                         parity=serial.PARITY_NONE,
                         stopbits=serial.STOPBITS_ONE,
                         timeout=1,  # wait at most one second for a response
                         writeTimeout=1,  # similarly, fail if writing takes >1s
                         xonxoff=False, rtscts=False, dsrdtr=False,
                         )
    termination_character = "\r"  #: All messages to or from the instrument end with this character.
    '''
    self._state trys to keep track of the shutter state. This is because communication quite frequently fails with this shutter for some reason.
    The toggle function always works, however self.query('ens?') often returns None, along with the message 'Command did not echo!!!'.
    self._state may be incorrect initially, if the laser shutter is open, and communication fails. 
    In this case, simply specify the shutter state manually with
    >>> shutter._state = 'Open' # for example
    
    The self._state attribute is overwritten if communication with the shutter succeeds at any time, so this should maximise the state being right. 
    using the physical buttons on the shutter will of course mess this all up. 
    -ee306
    '''
    def __init__(self, port=None):
        serial.SerialInstrument.__init__(self, port=port)
        Shutter.__init__(self)
        self.ignore_echo = True     
        self._state = 'Closed'  # usually the case      
        self.get_state(report_success = True) # overwrites self._state if communication succeeds     
            
    def toggle(self):
        self.write('ens')
        self._state = bool_to_state(not state_to_bool(self._state))#toggles self._state
#        
#    def get_state(self):
#        if self.query('ens?') == '0':
#            return 'Closed'
#        elif self.query('ens?') == '1':
#            return 'Open'
    
    def get_state(self, report_success = False):
        try:
            state = bool(int(self.query('ens?')))

            if state:
                self._state = 'Open'            
                return self._state
            if not state:
                self._state = 'Closed'            
                return self._state
            assert False 
        except (ValueError, AssertionError):
            if report_success: 
                print(
                        '''Communication with shutter failed; assuming shutter is closed.\nChange shutter._state if not!'''
                      )          
            return self._state
    
    def set_state(self, state):
        if state_to_bool(self.get_state()) != state_to_bool(state):
            self.toggle()
        
    def open_shutter(self):
        if not state_to_bool(self.get_state()):
            self.toggle()
        elif state_to_bool(self._state):
            print('Shutter is already open!')
        
    def close_shutter(self):  
        if state_to_bool(self._state):
            self.toggle()
        elif not state_to_bool(self._state):
            print('Shutter is already closed!')
        
    def set_mode(self,n):
        """ Where n equals an associated mode
            mode=1: Sets the unit to Manual Mode
            mode=2: Sets the unit to Auto Mode
            mode=3: Sets the unit to Single Mode
            mode=4: Sets the unit to Repeat Mode
            mode=5: Sets the unit to the External Gate Mode"""
        self.query('mode='+str(n))
    def get_mode(self):
        self.query('mode?')
    
if __name__ == '__main__':
#    import sys
#    from nplab.utils.gui import *
#    app = get_qt_app()
    
    shutter = ThorLabsSC10('COM3')
    # shutter.query('ens?', termination_line = "r")
#     ui = shutter.get_qt_ui()
#    ui.show()
#    sys.exit(app.exec_())
    shutter.show_gui()