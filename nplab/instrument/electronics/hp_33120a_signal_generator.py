__author__ = 'alansanders'

from nplab.instrument.visa_instrument import VisaInstrument, queried_property
from functools import partial


class SignalGenerator(VisaInstrument):
    def __init__(self, address='GPIB0::3::INSTR'):
        super(SignalGenerator, self).__init__(address)
        self.instr.read_termination = '\n'
        self.instr.write_termination = '\n'

    def validate(self, param, value):
        if param == 'function:shape':
            assert value in ['sinusoid', 'dc']
        elif param == 'output:load':
            assert value in ['inf']

    frequency = queried_property('freq?', 'freq {0}')
    function = queried_property('function:shape?', 'function:shape {0}',
                                fvalidate=partial(validate, param='function:shape'),
                                dtype='str')
    voltage = queried_property('voltage?', 'voltage {0}')
    offset = queried_property('voltage:offset?', 'voltage:offset {0}')
    output_load = queried_property('output:load?', 'output:load {0}',
                                   fvalidate=partial(validate, param='output:load'),
                                   dtype='str')
    volt_high = queried_property('volt:high?', 'volt:high {0}')
    volt_low = queried_property('volt:low?', 'volt:low {0}')

    def reset(self):
        self.write('*rst')

if __name__ == '__main__':
    s = SignalGenerator()
    print s.frequency
    s.frequency = 1e3
    print s.frequency
    s.frequency = 2e3
    print s.frequency
    print s.function
    s.function = 'sinusoid'
    print s.function