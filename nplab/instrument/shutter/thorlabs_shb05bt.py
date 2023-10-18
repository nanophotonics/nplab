__author__ = 'alansanders'

from nplab.instrument.shutter import Shutter
import serial

# !!Reverse logic!!
def bool_to_state(Bool):
    if not Bool:
        return 'Open'
    if Bool:
        return 'Closed'
def state_to_bool(state):
    if state == 'Open':
        return False
    if state == 'Closed':
        return True

class ThorLabsSHB05BT(Shutter):
    
    def __init__(self, port=None):
        self.ser = serial.Serial(port=port)
        Shutter.__init__(self)
        self.ignore_echo = True     
        self.state = 'Closed'  # usually the case      
        self.get_state(report_success = True) # overwrites self._state if communication succeeds     
        

        
    def get_state(self, report_success = False):
        try:
            state = self.ser.rts

            if not state:
                self._state = 'Open'            
                return self._state
            if state:
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
        self.ser.rts = state_to_bool(state)
        self._state = state
        
    def open_shutter(self):
        self.set_state("Open")
        
    def close_shutter(self):  
        self.set_state("Closed")
    
    def toggle(self):
        self.ser.rts = not self.ser.rts
        self._state = bool_to_state(self.ser.rts)

    
if __name__ == '__main__':
#    import sys
#    from nplab.utils.gui import *
#    app = get_qt_app()
    
    shutter = ThorLabsSHB05BT('COM4')
    # shutter.query('ens?', termination_line = "r")
#     ui = shutter.get_qt_ui()
#    ui.show()
#    sys.exit(app.exec_())
    shutter.show_gui()