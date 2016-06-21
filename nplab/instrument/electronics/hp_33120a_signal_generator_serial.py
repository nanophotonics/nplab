__author__ = 'alansanders'

from nplab.instrument.serial_instrument import SerialInstrument
from nplab.instrument.message_bus_instrument import queried_property
from functools import partial
import serial

class SignalGenerator(SerialInstrument):
    port_settings = dict(baudrate=9600,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1, #wait at most one second for a response
                    writeTimeout=1, #similarly, fail if writing takes >1s
                    xonxoff=False, rtscts=False, dsrdtr=True,
                )
    def __init__(self, port=None):
        SerialInstrument.__init__(self, port=port) #this opens the port
        self.query("SYST:REMOTE")

    frequency = queried_property('freq?', 'freq {0}')
    function = queried_property('function:shape?', 'function:shape {0}',
                                validate=['sinusoid', 'dc', 'square'], dtype='str')
    voltage = queried_property('voltage?', 'voltage {0}')
    offset = queried_property('voltage:offset?', 'voltage:offset {0}')
    output_load = queried_property('output:load?', 'output:load {0}',
                                   validate=['inf'], dtype='str')
    volt_high = queried_property('volt:high?', 'volt:high {0}')
    volt_low = queried_property('volt:low?', 'volt:low {0}')

    def reset(self):
        self.write('*rst')

if __name__ == '__main__':
    s = SignalGenerator("COM10")
#    print s.frequency
#    s.frequency = 1e3
#    print s.frequency
#    s.frequency = 2e3
#    print s.frequency
#    print s.function
#    s.function = 'sinusoid'
#    print s.function