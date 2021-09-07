__author__ = 'alansanders'

from nplab.instrument.visa_instrument import VisaInstrument, queried_property
from functools import partial


class SignalGenerator(VisaInstrument):
    def __init__(self, address='GPIB0::3::INSTR'):
        super(SignalGenerator, self).__init__(address)
        self.instr.read_termination = '\n'
        self.instr.write_termination = '\n'

    frequency = queried_property('freq?', 'freq {0}')
    function = queried_property('function:shape?', 'function:shape {0}',
                                validate=['sinusoid', 'dc'], dtype='str')
    voltage = queried_property('voltage?', 'voltage {0}')
    offset = queried_property('voltage:offset?', 'voltage:offset {0}')
    output_load = queried_property('output:load?', 'output:load {0}',
                                   validate=['inf'], dtype='str')
    volt_high = queried_property('volt:high?', 'volt:high {0}')
    volt_low = queried_property('volt:low?', 'volt:low {0}')
    output = queried_property('output?', 'output {0}',
                              validate=['OFF', 'ON'], dtype='str')

    def reset(self):
        self.write('*rst')

if __name__ == '__main__':
    s = SignalGenerator(address='USB0::0x0957::0x0407::MY44037109::0::INSTR')
    print(s.frequency)
    s.frequency = 1e3
    print(s.frequency)
    print(s.function)
    s.function = 'sinusoid'
    print(s.function)