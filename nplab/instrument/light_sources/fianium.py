__author__ = 'alansanders'

import nplab.instrument.serial_instrument as serial
from nplab.instrument.light_sources import LightSource
from traits.api import Int, Range, Button, Property
from traitsui.api import View, HGroup, Item, Spring


class Fianium(LightSource, serial.SerialInstrument):
    '''
    Class for the Fianium supercontinuum lasers
    '''

    port_settings = dict(baudrate=19200,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1, #wait at most one second for a response
                        writeTimeout=1, #similarly, fail if writing takes >1s
                        xonxoff=False, rtscts=False, dsrdtr=False,
                    )
    termination_character = "\n" #: All messages to or from the instrument end with this character.

    set_dac_button = Button('Set DAC')

    view = View(
                HGroup(Item('dac'), Item('power'),
                      Item('set_power_button', show_label=False), Spring(),
                      label='Fianium Controls', show_border=True
                      ),
                resizable=True, title="Fianium"
               )

    def __init__(self, port=None):
        super(LightSource, self).__init__(port=port)
        self._min_power = 0
        self._max_power = 2000

    def get_dac(self):
        return self.float_query('Q?')

    def set_dac(self, dac):
        self.write('Q=%d' % dac)

    dac = Property(get_dac, set_dac)

    def _power_changed(self, value):
        self.set_dac(value)

    def _set_power_button_fired(self):
        value = self.dac_range
        self.set_dac(value)
