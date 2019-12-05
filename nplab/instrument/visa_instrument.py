# -*- coding: utf-8 -*-

from __future__ import print_function
__author__ = 'alansanders'

from nplab.instrument.message_bus_instrument import MessageBusInstrument, queried_property, queried_channel_property
import visa
from functools import partial


class VisaInstrument(MessageBusInstrument):
    """
    An instrument primarily using VISA communications
    """

    def __init__(self, address, settings={}):
        """
        :param address: VISA address as a string
        :param settings: dictionary of instrument settings, including:
            'read_termination', 'write_termination', 'timeout' (0 for inf),
            'send_end' (not recommended to remove end of line character),
            delay (time between write and read during query)
        :type object
        """
        super(VisaInstrument, self).__init__()
        rm = visa.ResourceManager()
        try:
            assert address in rm.list_resources(), "The instrument was not found"
        except AssertionError:
            print('Available equipment:', rm.list_resources())
        self.instr = rm.open_resource(address, **settings)
        self._address = address
        self._settings = settings

    def __del__(self):
        try:
            self.instr.close()
        except Exception as e:
            print("The serial port didn't close cleanly:", e)

    def write(self, *args, **kwargs):
        return self.instr.write(*args, **kwargs)

    def read(self, *args, **kwargs):
        return self.instr.read(*args, **kwargs)

    def query(self, *args, **kwargs):
        return self.instr.query(*args, **kwargs)

    def clear_read_buffer(self):
        empty_buffer = False
        while empty_buffer == False:
            try:
                self.instr.read()
            except Exception:
                print("Buffer emptied")
                empty_buffer = True
                
    #idn = property(fget=partial(query, message='*idn?'))
    idn = queried_property('*idn?', dtype='str')


if __name__ == '__main__':
    instrument = VisaInstrument(address='GPIB0::7::INSTR')
    print(instrument.query('*idn?'))
    print(instrument.idn)
    print(instrument.float_query)
