__author__ = 'alansanders'

import nplab.instrument.serial_instrument as serial
from nplab.instrument.light_sources import LightSource


class Fianium(LightSource, serial.SerialInstrument):
    """
    Interface for the Fianium supercontinuum lasers
    """

    port_settings = dict(baudrate=19200,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1, #wait at most one second for a response
                        writeTimeout=1, #similarly, fail if writing takes >1s
                        xonxoff=False, rtscts=False, dsrdtr=False,
                    )
    termination_character = "\n" #: All messages to or from the instrument end with this character.

    def __init__(self, port=None):
        super(LightSource, self).__init__(port=port)
        self.min_power = 0
        self.max_power = 2000

    def get_dac(self):
        return self.float_query('Q?')

    def set_dac(self, dac):
        self.write('Q=%d' % dac)

    dac = property(get_dac, set_dac)

    def get_power(self):
        return self.get_dac()

    def set_power(self, value):
        self.set_dac(value)

    power = property(get_power, set_power)
