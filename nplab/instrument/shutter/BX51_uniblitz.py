__author__ = 'jm806'


from nplab.instrument.shutter import Shutter
from nplab.instrument.serial_instrument import SerialInstrument
import serial


class Uniblitz(Shutter, SerialInstrument):
    # port settings
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
        super(Uniblitz, self).__init__()
        Shutter.__init__(self)
        self.shutter_state = 0

    def toggle(self):
        if self.shutter_state:
            self.close_shutter()
        else:
            self.open_shutter()

    def open_shutter(self):
        self.ser.write('@')
        self.shutter_state = 1

    def close_shutter(self):
        self.ser.write('A')
        self.shutter_state = 0


if __name__ == '__main__':

    shutter = Uniblitz('COM4')
    shutter.show_gui()
    shutter.close()