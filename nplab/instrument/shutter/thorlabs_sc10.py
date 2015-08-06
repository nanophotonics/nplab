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
        super(ThorLabsSC10, self).__init__(port=port)

    def toggle(self):
        self.write('ens')

    def get_state(self):
        return self.query('ens?')
