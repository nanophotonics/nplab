__author__ = 'alansanders'

from nplab.instrument.visa_instrument import VisaInstrument, queried_property, queried_channel_property
from functools import partial
import numpy as np
from struct import unpack


class DSOChannel(object):
    def __init__(self, dso, channel):
        self.parent = dso
        self.ch = channel

    def capture(self):
        self.parent.write(':digitize channel{0}'.format(self.ch))

    def validate(self, param, value):
        if param == ':display':
            assert value in [0, 1]
        elif param == ':coupling':
            assert value in ['ac', 'dc']
        elif param == ':unit':
            assert value in ['volt', 'ampere']

    display = queried_channel_property(':channel{0}:display?', ':channel{0}:display {1}',
                                       fvalidate=partial(validate, param=':display'), dtype='int')
    range = queried_channel_property(':channel{0}:range?', ':channel{0}:range {1}')
    scale = queried_channel_property(':channel{0}:scale?', ':channel{0}:scale {1}')
    offset = queried_channel_property(':channel{0}:offset?', ':channel{0}:offset {1}')
    coupling = queried_channel_property(':channel{0}:coupling?', ':channel{0}:coupling {1}',
                                        fvalidate=partial(validate, param=':coupling'), dtype='str')
    units = queried_channel_property(':channel{0}:unit?', ':channel{0}:unit {1}',
                                     fvalidate=partial(validate, param=':unit'), dtype='str')
    label = queried_channel_property(':channel{0}:label?', ':channel{0}:label {1}')
    probe = queried_channel_property(':channel{0}:probe?', ':channel{0}:probe {1}')


class DSO(VisaInstrument):
    """
    Interface to the Agilent digital storage oscilloscopes.
    """
    def __init__(self, address='USB0::0x0957::0x1799::MY51330673::INSTR'):
        super(DSO, self).__init__(address=address)
        self.instr.read_termination = '\n'
        self.instr.write_termination = '\n'
        self.channel_names = (1, 2)
        for ch in self.channel_names:
            setattr(self, 'channel{0}'.format(ch), DSOChannel(self, ch))
        self.channels = tuple(getattr(self, 'channel{0}'.format(ch)) for ch in self.channel_names)
        # set byte transmission
        self.waveform_format = 'byte'
        byteorder = self.waveform_byteorder
        self.waveform_unsigned = 1
        byteorder = True if byteorder == 'MSBF' else False
        self.instr.values_format.use_binary('B', byteorder, np.array)

    def reset(self):
        self.write('*rst')

    def clear(self):
        self.write('*cls')

    def autoscale(self):
        self.write(':autoscale')

    def capture(self, channel=None):
        if channel is None:
            self.write(':digitize')
        else:
            assert channel in self.channels
            self.write(':digitize channel{0}'.format(channel))

    def run(self):
        self.write(':run')

    def single_shot(self):
        self.write(':single')

    def stop(self):
        self.write(':stop')

    def force_trigger(self):
        self.write(':trigger:force')

    def validate(self, param, value):
        if param == ':':
            assert value in ['run', 'single', 'stop']
        elif param == ':timebase:mode':
            assert value in ['main', 'window', 'xy', 'roll', 'MAIN']
        elif param == ':trigger:mode':
            assert value in ['edge', 'glitch', 'pattern', 'tv', 'EDGE']
        elif param == ':trigger:sweep':
            assert value in ['normal', 'auto', 'NORM', 'AUTO']
        elif param == ':trigger:nreject':
            assert value in [0,1]
        elif param == ':trigger:hfreject':
            assert value in [0,1]
        elif param == ':trigger:source':
            assert value in ['channel1', 'channel2', 'external', 'line', 'wgen', 'CHAN1', 'CHAN2']
        elif param == ':trigger:slope':
            assert value in ['positive', 'negative', 'either', 'alternate', 'POS', 'NEG']
        elif param == ':acquire:type':
            assert value in ['normal', 'average', 'hresolution', 'peak']
        elif param == ':waveform:points:mode':
            assert value in ['normal', 'maximum', 'raw', 'NORM', 'MAX', 'RAW']
        elif param == ':waveform:format':
            assert value in ['byte', 'ascii']
        elif param == ':waveform:byteorder':
            assert value in ['lsbfirst', 'msbfirst', 'LSBFirst', 'MSBFirst', 'LSBF', 'MSBF']
        elif param == ':waveform:unsigned':
            assert value in [0,1]

    acquire_type = queried_property(':acquire:type?', ':acquire:type {0}',
                                    fvalidate=partial(validate, param=':acquire:type'), dtype='str'),
    acquire_complete = queried_property(':acquire:complete?', ':acquire:complete {0}'),
    acquire_count = queried_property(':acquire:count?', ':acquire:count {0}'),
    acquire_points = queried_property(':acquire:points?', dtype='int')
    armed = queried_property(':aer?')
    #mode = queried_property(set_cmd=':{0}', fvalidate=partial(validate, param=':'))
    opc = queried_property('*opc?')
    operegister_condition = queried_property(':operegister:condition?', dtype='int')
    time_mode = queried_property(':timebase:mode?', ':timebase:mode {0}',
                                 fvalidate=partial(validate, param=':timebase:mode'), dtype='str')
    time_range = queried_property(':timebase:range?', ':timebase:range {0}')
    time_scale = queried_property(':timebase:scale?', ':timebase:scale {0}')
    time_ref = queried_property(':timebase:reference?', ':timebase:reference {0}',
                                fvalidate=partial(validate, param=':timebase:reference'), dtype='str')
    time_delay = queried_property(':timebase:delay?', ':timebase:delay {0}')
    trigger_sweep = queried_property(':trigger:sweep?', ':trigger:sweep {0}',
                                     fvalidate=partial(validate, param=':trigger:sweep'), dtype='str')
    trigger_mode = queried_property(':trigger:mode?', ':trigger:mode {0}',
                                    fvalidate=partial(validate, param=':trigger:mode'), dtype='str')
    trigger_level = queried_property(':trigger:level?', ':trigger:level {0}')
    trigger_source = queried_property(':trigger:source?', ':trigger:source {0}',
                                      fvalidate=partial(validate, param=':trigger:source'), dtype='str')
    trigger_slope = queried_property(':trigger:slope?', ':trigger:slope {0}',
                                     fvalidate=partial(validate, param=':trigger:slope'), dtype='str')
    trigger_reject_noise = queried_property(':trigger:nreject?', ':trigger:nreject {0}',
                                            fvalidate=partial(validate, param=':trigger:nreject'), dtype='int')
    trigger_filter = queried_property(':trigger:hfreject?', ':trigger:hfreject {0}',
                                      fvalidate=partial(validate, param=':trigger:hfreject'), dtype='int')
    trigger_status = queried_property(':ter?', dtype='int')
    waveform_format = queried_property(':waveform:format?', ':waveform:format {0}',
                                       fvalidate=partial(validate, param=':waveform:format'), dtype='str')
    waveform_byteorder = queried_property(':waveform:byteorder?', ':waveform:byteorder {0}',
                                          fvalidate=partial(validate, param='waveform:byteorder'), dtype='str')
    waveform_unsigned = queried_property(':waveform:unsigned?', ':waveform:unsigned {0}',
                                         fvalidate=partial(validate, param=':waveform:unsigned'), dtype='int')
    waveform_points = queried_property(':waveform:points?', ':waveform:points {0}', dtype='int')
    waveform_points_mode = queried_property(':waveform:points:mode?', ':waveform:points:mode {0}',
                                            fvalidate=partial(validate, param=':waveform:points:mode'), dtype='str')

    # read parameters
    def set_source(self, ch):
        assert ch in self.channel_names
        self.write(":waveform:source channel{0}".format(ch))

    x_or = queried_property(":waveform:xorigin?")
    x_inc = queried_property(":waveform:xincrement?")
    y_or = queried_property(":waveform:yorigin?")
    y_inc = queried_property(":waveform:yincrement?")
    y_ref = queried_property(":waveform:yreference?")

    def set_trace_parameters(self, ch, mode='maximum'):
        assert ch in self.channel_names
        self.set_source(ch)
        self.waveform_points_mode = mode
        self.waveform_points = self.acquire_points

    def scale_trace(self, trace):
        trace = self.y_or + (self.y_inc * (trace - self.y_ref))
        time = np.arange(trace.size)*self.x_inc + self.x_or
        return time, trace

    def read_trace(self, ch, renew=True):
        assert ch in self.channel_names
        if renew:
            self.set_trace_parameters(ch)
        self.set_source(ch)
        trace = self.instr.query_values(':waveform:data?')

        time, trace = self.scale_trace(trace)
        return time, trace

    def check_trigger(self, force):
        if force:
            self.force_trigger
        return bool(self.trigger_status)


if __name__ == '__main__':
    dso = DSO()
    print dso.time_range
    print dso.channel1.range
    dso.capture()
    t,v = dso.read_trace(1)

    import matplotlib.pyplot as plt
    plt.plot(1e3*t,v)
    plt.show()