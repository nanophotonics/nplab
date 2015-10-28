"""
Classes related to the Keithley 2635A SMU.
"""

__author__ = 'alansanders'

from nplab.instrument.visa_instrument import VisaInstrument, queried_property
import numpy as np
from nplab.utils.gui import *
from PyQt4 import uic


class Keithley2635A(VisaInstrument):
    """Interface to the Keithley 2635A SMU."""
    def __init__(self, address='GPIB0::26::INSTR'):
        super(Keithley2635A, self).__init__(address)
        self.instr.read_termination = '\n'
        self.instr.write_termination = '\n'
        self.reset()

    def reset(self):
        """Reset the SMU to its default state."""
        self.write('reset()')

    output = queried_property('print(smua.source.output)', 'smua.source.output={0}',
                              validate=['smua.OUTPUT_ON', 'smua.OUTPUT_OFF', 0, 1], dtype='str',
                              doc='Turn the SMU on or off')
    source = queried_property('print(smua.source.func)', 'smua.source.func={0}',
                              validate=['smua.OUTPUT_DCVOLTS', 'smua.OUTPUT_DCAMPS', 0, 1], dtype='str',
                              doc='Set the source type, either voltage or current')

    # def set_src_voltage(self, voltage):
    #    self.instr.write('smua.source.levelv=%s' % voltage)
    #    self.check_voltage_range(voltage)

    src_voltage = queried_property('print(smua.source.levelv)', 'smua.source.levelv={0}',
                                   doc='Source voltage')
    src_current = queried_property('print(smua.source.leveli)', 'smua.source.leveli={0}',
                                   doc='Source current')
    src_voltage_range = queried_property('print(smua.source.rangev)', 'smua.source.rangev={0}',
                                         doc='Source voltage range')
    src_current_range = queried_property('print(smua.source.rangei)', 'smua.source.rangei={0}',
                                         doc='Source current range')
    meas_voltage_range = queried_property('print(smua.measure.rangev)', 'smua.measure.rangev={0}',
                                          doc='Measured voltage range')
    meas_current_range = queried_property('print(smua.measure.rangei)', 'smua.measure.rangei={0}',
                                          doc='Measured current range')
    src_compliance = queried_property('print(smua.source.compliance)', 'smua.source.compliance={0}',
                                      doc='Source compliance')
    src_voltage_limit = queried_property('print(smua.source.limitv)', 'smua.source.limitv={0}',
                                         doc='Source voltage limit')
    src_current_limit = queried_property('print(smua.source.limiti)', 'smua.source.limiti={0}',
                                         doc='Source current limit')

    display = queried_property('print(display.smua.measure.func)', 'display.smua.measure.func={0}',
                               validate=['display.MEASURE_DCAMPS', 'display.MEASURE_DCVOLTS', 'display.MEASURE_OHMS',
                                         'display.MEASURE_WATTS', 0, 1, 2, 3],
                               dtype='str', doc='Measurement displayed on the SMU front panel')

    src_voltage_autorange = queried_property('print(smua.source.autorangev)', 'smua.source.autorangev=%s',
                                             validate=[0, 1, False, True], dtype='int',
                                             doc='Source voltage autorange')
    src_current_autorange = queried_property('print(smua.source.autorangei)', 'smua.source.autorangei=%s',
                                             validate=[0, 1, False, True], dtype='int',
                                             doc='Source current autorange')

    src_voltage_lowrange = queried_property('print(smua.source.lowrangev)', 'smua.source.lowrangev=%s',
                                            doc='Minimum range the source voltage autorange will set')
    src_current_lowrange = queried_property('print(smua.source.lowrangei)', 'smua.source.lowrangei=%s',
                                            doc='Minimum range the source current autorange will set')

    meas_voltage_autorange = queried_property('print(smua.measure.autorangev)', 'smua.measure.autorangev=%s',
                                              validate=[0, 1, False, True], dtype='int',
                                              doc='Measurement voltage autorange')
    meas_current_autorange = queried_property('print(smua.measure.autorangei)', 'smua.measure.autorangei=%s',
                                              validate=[0, 1, False, True], dtype='int',
                                              doc='Measurement current autorange')

    meas_voltage_lowrange = queried_property('print(smua.measure.lowrangev)', 'smua.measure.lowrangev=%s',
                                             doc='Minimum range the measurement voltage autorange will set')
    meas_current_lowrange = queried_property('print(smua.measure.lowrangei)', 'smua.measure.lowrangei=%s',
                                             doc='Minimum range the measurement current autorange will set')

    def read_voltage(self):
        """Measure the voltage."""
        return float(self.instr.query('print(smua.measure.v())'))

    def read_current(self):
        """Measure the current."""
        return float(self.instr.query('print(smua.measure.i())'))

    def read_resistance(self):
        """Measure the resistance."""
        return float(self.instr.query('print(smua.measure.r())'))

    def read_power(self):
        """Measure the power."""
        return float(self.instr.query('print(smua.measure.p())'))

    def read_iv(self):
        """Measure the voltage and the current."""
        self.instr.write('i,v = smua.measure.iv()')
        return float(self.instr.query('print(i)')), \
               float(self.instr.query('print(v)'))

    @property
    def error(self):
        """Get the next error code from the SMU."""
        self.instr.write('errorCode, message = errorqueue.next()')
        code = self.instr.query('print(errorCode)')
        msg = self.instr.query('print(message)')
        return '{0:s}: {1:s}'.format(code, msg)

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

    def get_qt_ui(self):
        return SmuUI(self)


class SmuUI(QtGui.QWidget):
    def __init__(self, smu, parent=None):
        super(SmuUI, self).__init__()
        self.smu = smu
        self.parent = parent
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'smu.ui'), self)

        self.current_button.clicked.connect(self.state_changed)
        self.voltage_button.clicked.connect(self.state_changed)
        self.source_value.returnPressed.connect(self.set_parameter)
        self.source_range.returnPressed.connect(self.set_parameter)
        self.source_autorange.stateChanged.connect(self.state_changed)
        self.source_limit.returnPressed.connect(self.set_parameter)
        self.measurement_range.returnPressed.connect(self.set_parameter)
        self.measurement_autorange.stateChanged.connect(self.state_changed)
        self.measurement_limit.returnPressed.connect(self.set_parameter)
        self.measure_button.clicked.connect(self.measure_button_clicked)
        self.display_select.activated[str].connect(self.on_activated)
        self.output.stateChanged.connect(self.state_changed)

        self.voltage_button.setChecked(True)
        self.source_value.setText(str(self.smu.src_voltage))
        self.source_range.setText(str(self.smu.src_voltage_range))
        self.source_autorange.setChecked(bool(self.smu.src_voltage_autorange))
        self.source_limit.setText(str(self.smu.src_voltage_limit))
        self.measurement_range.setText(str(self.smu.meas_current_range))
        self.measurement_autorange.setChecked(bool(self.smu.meas_current_autorange))
        self.measurement_limit.setText(str(self.smu.src_current_limit))
        self.output.setChecked(False)

    def set_parameter(self):
        sender = self.sender()
        value = sender.text()
        if sender.validator() is not None:
            state = sender.validator().validate(value, 0)[0]
            if state != QtGui.QValidator.Acceptable:
                return
        if self.voltage_button.isChecked():
            if sender == self.source_value:
                self.smu.src_voltage = float(value)
            elif sender == self.source_range:
                self.source_autorange.setChecked(False)
                self.smu.src_voltage_range = float(value)
            elif sender == self.source_limit:
                self.smu.src_voltage_limit = float(value)
            elif sender == self.measurement_range:
                self.measurement_autorange.setChecked(False)
                self.smu.meas_current_range = float(value)
            elif sender == self.measurement_limit:
                self.smu.src_current_limit = float(value)
        elif self.current_button.isChecked():
            if sender == self.source_value:
                self.smu.src_current = float(value)
            elif sender == self.source_range:
                self.source_autorange.setChecked(False)
                self.smu.src_current_range = float(value)
            elif sender == self.source_limit:
                self.smu.src_current_limit = float(value)
            elif sender == self.measurement_range:
                self.maesurement_autorange.setChecked(False)
                self.smu.meas_voltage_range = float(value)
            elif sender == self.measurement_limit:
                self.smu.meas_voltage_limit = float(value)

    def state_changed(self, state):
        sender = self.sender()
        value = True if state == QtCore.Qt.Checked else False
        if sender == self.voltage_button:
            if value:
                self.current_button.blockSignals(True)
                self.current_button.setChecked(False)
                self.current_button.blockSignals(False)
                self.smu.source = 0
        elif sender == self.current_button:
            if value:
                self.voltage_button.blockSignals(True)
                self.voltage_button.setChecked(False)
                self.voltage_button.blockSignals(False)
                self.smu.source = 1
        elif sender == self.source_autorange:
            if self.voltage_button.isChecked():
                self.smu.src_voltage_autorange = value
            elif self.current_button.isChecked():
                self.smu.src_current_autorange = value
        elif sender == self.measurement_autorange:
            if self.voltage_button.isChecked():
                self.smu.meas_current_autorange = value
            elif self.current_button.isChecked():
                self.smu.meas_voltage_autorange = value
        elif sender == self.output:
            if value:
                self.smu.output = 1
            else:
                self.smu.output = 0

    def measure_button_clicked(self):
        voltage = self.smu.read_voltage()
        current = self.smu.read_current()
        resistance = self.smu.read_resistance()
        power = self.smu.read_power()
        self.measurements.setText(
            '{0:.2e} V, {1:.2e} A, {2:.2e} Ohms, {3:.2e} W'.format(voltage, current, resistance, power))

    def on_activated(self, value):
        # print self.sender(), index, value
        if value == 'voltage':
            self.smu.display = 1
        elif value == 'current':
            self.smu.display = 0
        elif value == 'resistance':
            self.smu.display = 2
        elif value == 'power':
            self.smu.display = 3


if __name__ == '__main__':
    smu = Keithley2635A()
    smu.output = 1
    smu.src_voltage = 10e-3
    print smu.read_iv()
    print smu.read_resistance()
    smu.output = 0

    smu.show_gui()
