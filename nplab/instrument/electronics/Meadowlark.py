# -*- coding: utf-8 -*-

from __future__ import division
from builtins import map
from past.utils import old_div
from nplab.instrument.serial_instrument import SerialInstrument
from serial import EIGHTBITS, PARITY_NONE, STOPBITS_ONE
import time


class VariableRetarder(SerialInstrument):
    """
    Serial control of a 3040. It does NOT provide all the functionality of the CellDrive 3000 Advanced
    Because it wants commands sent to it ending in \r, but it returns commands that end in \r\n had to rewrite the read write functions
    """
    port_settings = dict(baudrate=38400, bytesize=EIGHTBITS, parity=PARITY_NONE, stopbits=STOPBITS_ONE,
                         timeout=2)
    termination_character = '\n'
    wait_time = 2

    def __init__(self, port=None):
        super(VariableRetarder, self).__init__(port)
        self._channel = 1

    def write(self, query_string):
        """Re-writing the nplab.SerialInstrument.write because the instrument has different termination characters for
        sending and receiving commands"""
        with self.communications_lock:
            assert self.ser.isOpen(), "Warning: attempted to write to the serial port before it was opened.  Perhaps you need to call the 'open' method first?"
            try:
                if self.ser.outWaiting() > 0: self.ser.flushOutput()  # ensure there's nothing waiting
            except AttributeError:
                if self.ser.out_waiting > 0: self.ser.flushOutput()  # ensure there's nothing waiting
            self.ser.write(query_string + '\r')

    def readline(self, timeout=None):
        """Read one line from the serial port."""
        with self.communications_lock:
            return self.ser_io.readline().replace("\r\n", '')

    def query(self, queryString, *args, **kwargs):
        reply = super(VariableRetarder, self).query(queryString, *args, **kwargs)

        split_reply = reply.split(':')
        split_query = queryString.split(':')
        if split_reply[0] != split_query[0]:
            self._logger.warn('Error trying to query')
        return split_reply[1]

    @property
    def firmware_version(self):
        return self.query('ver:?')

    @property
    def channel(self):
        """
        Sets the default channel to performs queries on
        :return:
        """
        return self._channel

    @channel.setter
    def channel(self, value):
        self._channel = value

    @property
    def voltage(self):
        """
        Query the voltage setting on the current channel
        :return:
        """
        reply = self.query('ld:%d,?' % self.channel)
        integer = int(reply.split(',')[1])
        voltage = integer / 6553.5
        return voltage

    @voltage.setter
    def voltage(self, value):
        """
        Sets the modulation voltage on the specified LC channel.
        Converts integer i to a squarewave amplitude voltage.
        :param value: float
        :return:
        """
        assert 0 <= value <= 10
        integer = value * 6553.5
        self.write('ld:%d,%d' % (self.channel, integer))
        time.sleep(self.wait_time)

    @property
    def all_voltages(self):
        """
        Query voltage settings on all four channels.
        :return:
        """
        reply = self.query('ldd:?')
        integers = list(map(int, reply.split(',')))
        voltages = [x / 6553.5 for x in integers]
        return voltages

    @all_voltages.setter
    def all_voltages(self, value):
        """
        Simultaneously sets the modulation voltages on all four LC channels.
        Converts each integer i to a square-wave amplitude voltage.

        :param value: 4-tuple of floats
        :return:
        """
        for val in value:
            assert 0 <= val <= 10
        voltages = tuple(value)
        integers = [x * 6553.5 for x in voltages]
        self.write('ldd:%d,%d,%d,%d' % integers)

    @property
    def temperature(self):
        """
        Query the current temperature of a temperature-controlled LC.
        :return:
        """
        integer = int(self.query('tmp:?'))
        return (old_div(integer * 500, 65535)) - 273.15

    @property
    def temperature_setpoint(self):
        """
        Query the current temperature setpoint.
        :return:
        """
        integer = int(self.query('tsp:?'))
        return (old_div(integer * 500, 16384)) - 273.15

    @temperature_setpoint.setter
    def temperature_setpoint(self, value):
        """
        Sets the temperature setpoint for temperature control.
        :param value:
        :return:
        """
        integer = old_div((value + 273.15) * 16384, 500)
        self.write('tsp:%d' % integer)

    def sync(self):
        """
        Produces a sync pulse (highlow) on the front panel sync connector.
        :return:
        """
        self.write('sout:')

    def extin(self, channels):
        """
        Enables output channels to be driven by signal applied to front panel external input connector.
        :param channels: 4-tuple of booleans
        :return:
        """
        integer = 0
        for idx, chn in enumerate(channels):
            if chn:
                integer += 2 ** idx
        self.write('extin:%d' % integer)
