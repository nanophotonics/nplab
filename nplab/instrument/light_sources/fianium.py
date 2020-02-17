from __future__ import print_function
__author__ = 'alansanders'

import nplab.instrument.serial_instrument as serial
from nplab.instrument.light_sources import LightSource


class Fianium(LightSource, serial.SerialInstrument):
    """
    Interface for the Fianium supercontinuum lasers
    """

    COMMAND_LIST = {

    "A?" : {"description":"Get Alarms", "type":"query"},
    "B?" : {"description":"Get back reflection photodiode value","type":"query"},
    "H?" : {"description":"Display list of commands","type":"query"},
    "I?" : {"description":"Get status display interval","type":"query"},
    "M?" : {"description":"Get laser control mode","type":"query"},
    "P?" : {"description":"Get preamplifier photodiode value","type":"query"},
    "Q?" : {"description":"Get amplifier control DAC value","type":"query"},
    "V?" : {"description":"Get control software version and release date","type":"query"},
    "W?" : {"description":"Get laser operating time counter","type":"query"},
    "X?" : {"description":"Get status display mode","type":"query"},
       
    "A=" : {"description":"Clear all alarms","type":"setter"},
    "I=" : {"description":"Set status display interval","type":"setter"},
    "M=" : {"description":"Set status display interval","type":"setter"},
    "Q=" : {"description":"Set amplifier current control DAC value in USB mode","type":"setter"},
    "X=" : {"description":"Set status display mode","type":"setter"}
    }

    port_settings = dict(baudrate=19200,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1, #wait at most one second for a response
                        writeTimeout=1, #similarly, fail if writing takes >1s
                        xonxoff=False, rtscts=False, dsrdtr=False,
                    )
    termination_character = "\n" #: All messages to or from the instrument end with this character.

    def __init__(self, port=None, shutter=None):
        serial.SerialInstrument.__init__(self, port=port)
        LightSource.__init__(self, shutter=shutter)
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


    def get_queries(self):
        for k,v in list(self.COMMAND_LIST.items()):
            if v["type"]=="query":
                print("Query:[{0}], Description:[{1}]".format(k,v["description"]))

    def get_setters(self):
        for k,v in list(self.COMMAND_LIST.items()):
            if v["type"]=="setter":
                print("Query:[{0}], Description:[{1}]".format(k,v["description"]))
    
    


    def get_alarms(self):
        response = self.query('A?')
        print("Fianium.get_alarms:", response)
        return response

    def get_back_reflection_value(self):
        response = self.float_query('B?')
        return response



if __name__ == '__main__':
    import sys
    from nplab.utils.gui import *
    from nplab.instrument.shutter.thorlabs_sc10 import ThorLabsSC10
    app = get_qt_app()
    #shutter = ThorLabsSC10('COM12')
    fianium = Fianium('COM1')
    ui = fianium.get_qt_ui()
    ui.show()
    sys.exit(app.exec_())
