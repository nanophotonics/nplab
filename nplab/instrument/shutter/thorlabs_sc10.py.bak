__author__ = 'alansanders'

from nplab.instrument.shutter import Shutter
import nplab.instrument.serial_instrument as serial


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

    def __init__(self, port=None):
        serial.SerialInstrument.__init__(self, port=port)
        Shutter.__init__(self)
        self.ignore_echo = True
    def toggle(self):
        self.write('ens')

    def get_state(self):
        if self.query('ens?') == '0':
            return 'Closed'
        elif self.query('ens?') == '1':
            return 'Open'
        
    def open_shutter(self):
        if self.get_state() == 'Closed':
            self.toggle()
        else:
            print 'Shutter is already open!'
    def close_shutter(self):
        if self.get_state() == 'Open':
            self.toggle()
        else:
            print 'Shutter is already closed!'
            
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
    import sys
#    from nplab.utils.gui import *
#    app = get_qt_app()
    shutter = ThorLabsSC10('COM5')
#    ui = shutter.get_qt_ui()
#    ui.show()
#    sys.exit(app.exec_())
    shutter.show_gui()