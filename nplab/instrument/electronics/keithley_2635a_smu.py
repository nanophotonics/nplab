__author__ = 'alansanders'

from nplab.instrument.visa_instrument import VisaInstrument
import numpy as np


class Keithley2635A(VisaInstrument):
    def __init__(self, address='GPIB0::26::INSTR'):
        super(Keithley2635A, self).__init__(address)
        self.instr.read_termination = '\n'
        self.instr.write_termination = '\n'
        self.reset()

    ### Basic commands

    def reset(self):
        self.instr.write('reset()')

    ### Front panel commands

    def get_output(self):
        return self.instr.read('print(smua.source.output)')
    def set_output(self, state):
        assert state in ['smua.OUTPUT_ON', 'smua.OUTPUT_OFF', 0, 1], "Output must either be 0 (off) or 1 (on)"
        self.instr.write('smua.source.output=%s' % state)
    output = property(get_output, set_output)

    def get_source(self):
        return self.instr.query('print(smua.source.func)')
    def set_source(self, source):
        assert source in ['smua.OUTPUT_DCVOLTS', 'smua.OUTPUT_DCAMPS', 0, 1], "Invalid mode"  # should this be a ValueError
        self.instr.write('smua.source.func=%s' % source)
    source = property(get_source, set_source)

    def get_src_voltage(self):
        return float(self.instr.query('print(smua.source.levelv)'))
    def set_src_voltage(self, voltage):
        self.instr.write('smua.source.levelv=%s' % voltage)
        self.check_voltage_range(voltage)
    src_voltage = property(get_src_voltage, set_src_voltage)

    def get_src_current(self):
        return float(self.instr.query('print(smua.source.leveli)'))
    def set_src_current(self, current):
        self.instr.write('smua.source.leveli=%s' % current)
    src_current = property(get_src_current, set_src_current)

    def get_src_voltage_range(self):
        return float(self.instr.query('print(smua.source.rangev)'))
    def set_src_voltage_range(self, voltage_range):
        self.instr.write('smua.source.rangev=%s' % voltage_range)
    src_voltage_range = property(get_src_voltage_range, set_src_voltage_range)

    def get_src_current_range(self):
        return float(self.instr.query('print(smua.source.rangei)'))
    def set_src_current_range(self, current_range):
        self.instr.write('smua.source.rangei=%s' % current_range)
    src_current_range = property(get_src_current_range, set_src_current_range)

    def get_meas_voltage_range(self):
        return float(self.instr.query('print(smua.measure.rangev)'))
    def set_meas_voltage_range(self, voltage_range):
        self.instr.write('smua.measure.rangev=%s' % voltage_range)
    meas_voltage_range = property(get_meas_voltage_range, set_meas_voltage_range)

    def get_meas_current_range(self):
        return float(self.instr.query('print(smua.measure.rangei)'))
    def set_meas_current_range(self, current_range):
        self.instr.write('smua.measure.rangei=%s' % current_range)
    meas_current_range = property(get_meas_current_range, set_meas_current_range)

    def get_src_compliance(self):
        return float(self.instr.query('print(smua.source.compliance)'))
    def set_src_compliance(self, compliance):
        assert compliance in [0,1], "Autorange must either be 0 (off) or 1 (on)"
        self.instr.write('smua.source.compliance=%s' % compliance)
    src_compliance = property(get_src_compliance, set_src_compliance)

    def get_src_voltage_limit(self):
        return float(self.instr.query('print(smua.source.limitv)'))
    def set_src_voltage_limit(self, limit):
        self.instr.write('smua.source.limitv=%s' % limit)
    src_voltage_limit = property(get_src_voltage_limit, set_src_voltage_limit)

    def get_src_current_limit(self):
        return float(self.instr.query('print(smua.source.limiti)'))
    def set_src_current_limit(self, limit):
        self.instr.write('smua.source.limiti=%s' % limit)
    src_current_limit = property(get_src_current_limit, set_src_current_limit)

    def get_display(self):
        return self.instr.query('print(display.smua.measure.func)')
    def set_display(self, display):
        self.instr.write('display.smua.measure.func=%s' % display)
    display = property(get_display, set_display)

    def get_src_voltage_autorange(self):
        return self.instr.query('print(smua.source.autorangev)')
    def set_src_voltage_autorange(self, autorange):
        assert autorange in [0,1], "Autorange must either be 0 (off) or 1 (on)"
        self.instr.write('smua.source.autorangev=%s' % autorange)
    src_voltage_autorange = property(get_src_voltage_autorange, set_src_voltage_autorange)

    def get_src_current_autorange(self):
        return self.instr.query('print(smua.source.autorangei)')
    def set_src_current_autorange(self, autorange):
        assert autorange in [0,1], "Autorange must either be 0 (off) or 1 (on)"
        self.instr.write('smua.source.autorangei=%s' % autorange)
    src_current_autorange = property(get_src_current_autorange, set_src_current_autorange)

    def get_src_voltage_lowrange(self):
        return self.instr.query('print(smua.source.lowrangev)')
    def set_src_voltage_lowrange(self, low_range):
        self.instr.write('smua.source.lowrangev=%s' % low_range)
    src_voltage_lowrange = property(get_src_voltage_lowrange, set_src_voltage_lowrange)

    def get_src_current_lowrange(self):
        return self.instr.query('print(smua.source.lowrangei)')
    def set_src_current_lowrange(self, low_range):
        self.instr.write('smua.source.lowrangei=%s' % low_range)
    src_current_lowrange = property(get_src_current_lowrange, set_src_current_lowrange)

    def get_meas_voltage_autorange(self):
        return self.instr.query('print(smua.measure.autorangev)')
    def set_meas_voltage_autorange(self, autorange):
        assert autorange in [0,1], "Autorange must either be 0 (off) or 1 (on)"
        self.instr.write('smua.measure.autorangev=%s' % autorange)
    meas_voltage_autorange = property(get_meas_voltage_autorange, set_meas_voltage_autorange)

    def get_meas_current_autorange(self):
        return self.instr.query('print(smua.measure.autorangei)')
    def set_meas_current_autorange(self, autorange):
        assert autorange in [0,1], "Autorange must either be 0 (off) or 1 (on)"
        self.instr.write('smua.measure.autorangei=%s' % autorange)
    meas_current_autorange = property(get_meas_current_autorange, set_meas_current_autorange)

    def get_meas_voltage_lowrange(self):
        return self.instr.query('print(smua.measure.lowrangev)')
    def set_meas_voltage_lowrange(self, low_range):
        self.instr.write('smua.measure.lowrangev=%s' % low_range)
    meas_voltage_lowrange = property(get_meas_voltage_lowrange, set_meas_voltage_lowrange)

    def get_meas_current_lowrange(self):
        return self.instr.query('print(smua.measure.lowrangei)')
    def set_meas_current_lowrange(self, low_range):
        self.instr.write('smua.measure.lowrangei=%s' % low_range)
    meas_current_lowrange = property(get_meas_current_lowrange, set_meas_current_lowrange)

    ### Measurements

    def read_voltage(self):
        return float(self.instr.query('print(smua.measure.v())'))
    def read_current(self):
        return float(self.instr.query('print(smua.measure.i())'))
    def read_resistance(self):
        return float(self.instr.query('print(smua.measure.r())'))
    def read_power(self):
        return float(self.instr.query('print(smua.measure.p())'))
    def read_iv(self):
        self.instr.write('i,v = smua.measure.iv()')
        return float(self.instr.query('print(i)')),\
               float(self.instr.query('print(v)'))

    ### Other commands

    def get_error(self):
        self.instr.write('errorCode, message = errorqueue.next()')
        code = self.instr.query('print(errorCode)')
        msg = self.instr.query('print(message)')
        return '{0:s}: {1:s}'.format(code, msg)

    def measure_iv(self, autoscale=True):
        current, voltage = self.read_iv()
        if autoscale:
            voltage = self.check_voltage_range(voltage)
            current = self.check_current_range(current)
        return voltage, current

    def check_current_range(self, i):
        i_range = self.get_meas_current_range()
        while abs(i) >= i_range:
            i_range = 10 ** (np.ceil(np.log10(i_range) + 1))  # go up one order of magnitude
            self.set_meas_current_range(i_range)
            i = self.read_current()
            # print 'i up', i, i_range
        if i != 0:
            minimum = 1e-8
            while (np.log10(abs(i)) - np.log10(i_range) <= -3) and i_range > minimum:
                i_range = 10 ** (np.ceil(np.log10(abs(i))))
                # set a lower limit
                i_range = i_range if i_range >= minimum else minimum
                self.set_meas_current_range(i_range)
                i = self.read_current()
                # print 'i down', i, i_range
        return i

    def check_voltage_range(self, v):
        v_range = self.get_src_voltage_range()
        while abs(v) >= v_range:  # say v=1.2 and v_range=1, aim for v_range=10
            v_range = 2 * 10 ** (np.ceil(np.log10(abs(v))))
            self.set_src_voltage_range(v_range)
            v = self.get_src_voltage()
            # print 'v up', v, v_range
        # autorange to a lower voltage range if the voltage value is 2 orders
        # of magnitude higher than the measurement
        if v != 0:
            minimum = 200e-3
            while (np.log10(abs(v)) - np.log10(v_range) <= -2) and v_range > minimum:
                v_range = 2 * 10 ** (np.ceil(np.log10(abs(v))))
                v_range = v_range if v_range >= minimum else minimum
                self.set_src_voltage_range(v_range)
                v = self.get_src_voltage()
                # print 'v down', v, v_range
        return v

if __name__ == '__main__':
    smu = Keithley2635A()
    smu.output = 1
    smu.src_voltage = 10e-3
    print smu.read_iv()
    print smu.read_resistance()