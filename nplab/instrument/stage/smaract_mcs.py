__author__ = 'alansanders, chrisgrosse'

import ctypes
from ctypes import byref, c_int, c_uint
from nplab.instrument import Instrument
from nplab.instrument.stage import Stage, StageUI
import os
from nplab.utils.gui import *
from nplab.utils.gui import uic
from nplab.ui.ui_tools import UiTools
from nplab.utils.formatting import engineering_format


try:
    mcsc = ctypes.cdll.MCSControl
except:
    raise Warning("MCSControl dll not found")

file_dir = os.path.dirname(os.path.realpath(__file__))


def get_enums():
    with open(os.path.join(file_dir, 'MCSControl.h'), 'r') as f:
        lines = [line.strip().split(' ') for line in f.readlines() if line.startswith('#define')]
        enums = {}
        for line in lines:
            while '' in line: line.remove('')
            if len(line) == 3:
                try:
                    enums[line[1]] = int(line[2])
                except ValueError:
                    pass
    return enums


def set_enums():
    enums = get_enums()
    for k, v in zip(enums.keys(), enums.values()):
        # print k+' = '+str(v)
        cmd = k + ' = c_int(' + str(v) + ')'
        exec cmd in globals()


set_enums()
max_acc = 1e7
max_speed = 1e8


class MCSError(Exception):
    def __init__(self, value):
        try:
            self.value = value
            error_text = ctypes.c_char_p()
            mcsc.SA_GetStatusInfo(value, byref(error_text))
            print "MCS error {:d}".format(value)
            print ctypes.string_at(error_text)
        except:
            print "MCS error {:d}".format(value)


class SmaractError(Exception): #?? why two different types of errors: MCSError and SmaractError??
    def __init__(self, msg):
        print "SmarAct error: %s" % msg


class SmaractMCS(Stage):
    """
    Smaract MCS controller interface for SmarAct stages.

    Check SmarAct's MCS Progammer's Guide for mor information.
    """

    @staticmethod
    def check_status(status):
        """
        Checks the status of the MCS controller. If not 'SA_OK' return the MCSError code
        """
        if (status != SA_OK.value):
            raise MCSError(status)
        else:
            return True

    @classmethod
    def find_mcs_systems(cls):
        """
        Get a list of all MCS devices available on this computer. The list
        contains MCS IDs which are unique numbers to identify a MCS.
        """
        outBuffer = ctypes.create_string_buffer(4096)
        bufferSize = c_int(4096)  # ctypes.sizeof(outBuffer)
        # outBuffer holds the locator strings, separated by '\n'
        # bufferSize holds the number of bytes written to outBuffer
        if cls.check_status(mcsc.SA_FindSystems("", outBuffer, byref(bufferSize))):
            print 'buffer size:', bufferSize
            print 'buffer:', ctypes.string_at(outBuffer)
        return ctypes.string_at(outBuffer)

    def __init__(self, system_id):
        super(SmaractMCS, self).__init__()
        self.mcs_id = system_id
        self.handle = c_int(0)
        # self.setup()  #?? why setup() not used anymore?? => sets sensor power modes, low vibration modes, speeds, acceleration, ... => maybe because don't need to be set/changed for every software start??
        self.is_open = False
        self._num_ch = None
        self.axis_names = tuple(i for i in range(self.num_ch))
        self.positions = [0 for ch in range(self.num_ch)]
        self.levels = [0 for ch in range(self.num_ch)]
        self.voltages = [0 for ch in range(self.num_ch)]
        self.scan_positions = [0 for ch in range(self.num_ch)]
        self.min_voltage = [0, 0, 0, 0, 0, 0]
        self.max_voltage = [100, 100, 100, 100, 100, 100]

    ### ====================== ###
    ### Initialization methods ###
    ### ====================== ###

    def check_open_status(self):
        if self.open_mcs():
            return
        else:
            raise SmaractError('Error opening')

    def open_mcs(self):
        if not self.is_open:
            mode = ctypes.c_char_p('sync') # use synchronouse communication mode
            if self.check_status(mcsc.SA_OpenSystem(byref(self.handle), self.mcs_id, mode)):
                self.is_open = True
                return True
            else:
                return False
        else:
            return True

    def close_mcs(self):
        if self.is_open:
            if self.check_status(mcsc.SA_CloseSystem(self.handle)):
                self.is_open = False
                return True
            else:
                return False
        else:
            return True

    def get_num_channels(self):
        if self._num_ch is not None:
            return self._num_ch
        num_ch = c_int()
        self.check_open_status()
        if self.check_status(mcsc.SA_GetNumberOfChannels(self.handle, byref(num_ch))):
            self._num_ch = num_ch.value
            return num_ch.value
        else:
            return False

    def setup(self):
        self.check_open_status()
        self.set_sensor_power_mode(2)
        for i in range(self.num_ch):
            self.set_speed(ch, 0)
            self.set_acceleration(ch, 0)
            self.set_low_vibration_mode(ch, 1)
            ch = c_int(i)
            self.check_status(mcsc.SA_SetStepWhileScan_S(self.handle, ch, SA_NO_STEP_WHILE_SCAN))

    def set_sensor_power_mode(self, mode):
        modes = {0: SA_SENSOR_DISABLED, 1: SA_SENSOR_ENABLED, 2: SA_SENSOR_POWERSAVE}
        self.check_open_status()
        self.check_status(mcsc.SA_SetSensorEnabled_S(self.handle, modes[mode]))

    def set_low_vibration_mode(self, ch, enable):
        ch = c_int(int(ch))
        values = {0: SA_DISABLED, 1: SA_ENABLED}
        self.check_open_status()
        self.check_status(mcsc.SA_SetChannelProperty_S(self.handle, ch,
                                                       mcsc.SA_EPK(SA_GENERAL, SA_LOW_VIBRATION, SA_OPERATION_MODE),
                                                       values[enable]))

    def get_acceleration(self, ch):
        ch = c_int(int(ch))
        acceleration = c_int()
        self.check_open_status()
        mcsc.SA_GetClosedLoopMoveAcceleration_S(self.handle, ch, byref(acceleration))
        return acceleration.value

    def set_acceleration(self, ch, acceleration):
        '''
        units are um/s/s.
        '''
        ch = c_int(int(ch))
        acceleration = c_int(int(acceleration))
        self.check_open_status()
        mcsc.SA_SetClosedLoopMoveAcceleration_S(self.handle, ch, acceleration)

    def get_speed(self, ch):
        ch = c_int(int(ch))
        speed = c_int()
        self.check_open_status()
        self.check_status(mcsc.SA_GetClosedLoopMoveSpeed_S(self.handle, ch,
                                                           byref(speed)))
        return speed.value

    def set_speed(self, ch, speed):
        '''
        units are nm/s, max is 1e8. A value of 0 deactivates speed control
        (defaults to max.).
        '''
        ch = c_int(int(ch))
        speed = c_int(int(speed))
        self.check_open_status()
        self.check_status(mcsc.SA_SetClosedLoopMoveSpeed_S(self.handle, ch,
                                                           speed))

    def get_frequency(self, ch):
        ch = c_int(int(ch))
        frequency = c_int()
        self.check_open_status()
        self.check_status(mcsc.SA_GetClosedLoopMaxFrequency_S(self.handle, ch,
                                                              byref(frequency)))
        return frequency.value

    def set_frequency(self, ch, frequency):
        '''
        units are nm/s, min is 50, max is 18,500. A value of 0 deactivates speed control
        (defaults to max.).
        '''
        ch = c_int(int(ch))
        frequency = c_int(int(frequency))
        self.check_open_status()
        self.check_status(mcsc.SA_SetClosedLoopMaxFrequency_S(self.handle, ch,
                                                              frequency))

    ### Calibration Methods ###

    def wait_until_stopped(self, ch):
        status = c_int(4)
        if type(ch) is not c_int:
            ch = c_int(ch)
        while status.value != SA_STOPPED_STATUS.value:
            self.check_status(mcsc.SA_GetStatus_S(self.handle, ch, byref(status)))
        return

    def get_channel_status(self, ch):
        ch = c_int(ch)
        status = c_int(4)
        self.check_status(mcsc.SA_GetStatus_S(self.handle, ch, byref(status)))
        return status.value

    def calibrate_system(self):
        print 'calibrating system'
        self.check_open_status()
        self.set_sensor_power_mode(1)
        num_ch = self.get_num_channels()
        for ch in range(num_ch):
            self.check_status(mcsc.SA_CalibrateSensor_S(self.handle, ch))
            self.wait_until_stopped(ch)

    def set_safe_directions(self):
        """
        Sets the safe directions for all channels to move when referencing.
        Vertical channels should all move upwards (i.e. SA_FORWARD_DIRECTION).
        The left channel should move left (SA_BACKWARD_DIRECTION) while the
        right channel should move right (SA_FORWARD_DIRECTION). The remaining
        two forward channels should move backwards away from the objective
        (SA_BACKWARD_DIRECTION).

        Note that this function is currently based on the tip experiment arrangement.
        """
        self.check_open_status()
        # self.set_sensor_power_mode(1)
        num_ch = self.get_num_channels()
        forward_channels = [3]  # was [0,1,2,5]
        for i in range(num_ch):
            value = SA_FORWARD_DIRECTION if (i in forward_channels) \
                else SA_BACKWARD_DIRECTION
            ch = c_int(int(i))
            self.check_status(mcsc.SA_SetSafeDirection_S(self.handle,
                                                         ch, value))
        return forward_channels

    def find_references_ch(self, ch):
        print 'finding reference for ch', ch
        ch = c_int(int(ch))
        self.check_open_status()
        self.set_sensor_power_mode(1)
        forward_channels = self.set_safe_directions()
        value = SA_FORWARD_DIRECTION if (ch.value in forward_channels) else SA_BACKWARD_DIRECTION
        self.check_status(mcsc.SA_FindReferenceMark_S(self.handle, ch, value, 0, SA_AUTO_ZERO))
        self.wait_until_stopped(ch)

    def find_references(self):
        self.check_open_status()
        num_ch = self.get_num_channels()
        for i in range(num_ch):
            self.find_references_ch(i)

    ### ==================================================== ###
    ### Methods to read-out position and move to a specific  ###
    ### position via slip-stick motion and piezo movement    ###
    ## ===================================================== ###

    def get_position(self, axis=None):
        """
        Get the position of the stage or of a specified axis.
        :param axis:
        :return:
        """
        if axis is None:
            return [self.get_position(axis) for axis in self.axis_names]
        else:
            if axis not in self.axis_names:
                raise ValueError("{0} is not a valid axis, must be one of {1}".format(axis, self.axis_names))
            ch = c_int(int(axis))
            position = c_int()
            self.check_open_status()
            mcsc.SA_GetPosition_S(self.handle, ch, byref(position))
            return 1e-9 * position.value

    def move(self, position, axis, relative=False):
        """
        Move the stage to the requested position. The function should block all further
        actions until the stage has finished moving.
        :param position: units of m (SI units, converted to nm in the method)
        :param axis: integer channel index
        :param relative:
        :return:
        """
        if axis not in self.axis_names:
            raise ValueError("{0} is not a valid axis, must be one of {1}".format(axis, self.axis_names))
        position *= 1e9 #??? why not 1e-9??
        ch = c_int(int(axis))
        position = c_int(int(position))
        self.check_open_status()
        if relative:
            self.check_status(mcsc.SA_GotoPositionRelative_S(self.handle, ch, position, c_int(0)))
        else:
            self.check_status(mcsc.SA_GotoPositionAbsolute_S(self.handle, ch, position, c_int(0)))
        self.wait_until_stopped(ch)

    def stop(self, axis=None):
        """
        stops any ongoing movement of the positioner
        """
        if axis is None: # stop movement of all positioner
            axes= [c_int(int(axis)) for axis in self.axis_names]
            for ch in axes:
                self.check_status(mcsc.SA_Stop_S(self.handle, ch))
        elif axis not in self.axis_names: # wrong positioner name
            raise ValueError("{0} is not a valid axis, must be one of {1}".format(axis, self.axis_names))
        else:  # just stop movement of specified positioner
            ch = c_int(int(axis))
            self.check_status(mcsc.SA_Stop_S(self.handle, ch))

    def set_initial_position(self, ch, position):
        """
        defines the current position to have a specific value; the measuring
        scale is shifted accordingly
        """
        ch = c_int(int(ch))
        position = c_int(position)
        self.check_open_status()
        mcsc.SA_SetPosition_S(self.handle, ch, position)

    def set_position(self, ch, position): # same as set_initial_position() !!!
        '''
        units are nm
        '''
        position *= 1e9
        ch = c_int(int(ch))
        position = c_int(int(position))
        self.check_open_status()
        mcsc.SA_SetPosition_S(self.handle, ch, position)

    def physical_position_known(self, ch):
        ch = c_int(int(ch))
        known = c_int()
        self.check_open_status()
        mcsc.SA_GetPhysicalPositionKnown_S(self.handle, ch, byref(known))
        if known == SA_PHYSICAL_POSITION_KNOWN:
            return True
        elif known == SA_PHYSICAL_POSITION_UNKNOWN:
            return False
        else:
            raise SmaractError('Unknown return value')

    def multi_move(self, positions, axes, relative=False): #?? doesn't this method include the simple move() method??
        self.check_open_status()

        positions = [c_int(1e9 * p) for p in positions]
        channels = [c_int(int(axis)) for axis in axes]

        for i in range(len(axes)):
            if relative:
                self.check_status(mcsc.SA_GotoPositionRelative_S(self.handle, channels[i], positions[i], c_int(0)))
            else:
                self.check_status(mcsc.SA_GotoPositionAbsolute_S(self.handle, channels[i], positions[i], c_int(0)))
        for axis in axes:
            self.wait_until_stopped(axis)

    def multi_move_rel(self, step, axes):
        steps = [1e9 * step for axis in axes]
        self.multi_move(steps, axes, relative=True)


    ### ==================================== ###
    ### Method to control slip-stick motion ###
    ### ==================================== ###

    def slip_stick_move(self, axis, steps=1, amplitude=1800, frequency=100):
        """
        this method perforems a burst of slip-stick coarse motion steps.

        :param axis: chanel index of selected SmarAct stage
        :param steps: number and direction of steps, ranging between -30,000 .. 30,000
                      with 0 stopping the positioner and +/-30,000 perfomes unbounded
                      move, which is strongly riscouraged!
        :param amplitude: voltage amplitude of the pulse send to the piezo,
                          ranging from 0 .. 4,095 with 0 corresponding to 0 V
                          and 4,095 corresponding to 100 V, a value of 2047
                          roughly leads to a 500 nm step
        :param frequency: frequency the steps are performed with in Hz, ranging
                          from 1 .. 18,500
        """
        if axis not in self.axis_names:
            raise ValueError("{0} is not a valid axis, must be one of {1}".format(axis, self.axis_names))
        ch = c_int(int(axis))
        steps = c_int(int(steps))
        amplitude = c_uint(int(amplitude))
        frequency = c_uint(int(frequency))
        self.check_open_status()
        self.check_status(mcsc.SA_StepMove_S(self.handle, ch, steps, amplitude, frequency))


    ### ===================================== ###
    ### Methods to control the piezo scanners ###
    ### ===================================== ###

    ### primary methods that provide diret interface to MCS main controller

    def get_scanner_position(self, axis=None):
        """
        Get the scanning position of the stage or of a specified axis.
        :param axis:
        :return:
        """
        if axis is None:
            return [1e-9*10.*self.get_voltage(axis) for axis in self.axis_names]
        else:
            if axis not in self.axis_names:
                raise ValueError("{0} is not a valid axis, must be one of {1}".format(axis, self.axis_names))
            voltage = self.get_voltage(axis)
            position = 1e-9*10.*voltage
            return position

    def get_scanner_level(self, axis):
        ch = c_int(int(axis))
        level = c_int()
        self.check_open_status()
        mcsc.SA_GetVoltageLevel_S(self.handle, ch, byref(level))
        return level.value

    def set_scanner_level(self, level, axis, speed=4095, relative=False):
        """
        Scan up to 100V
        level: 0 - 100 V, 0 - 4095
        speed: 4095 s - 1 us for full 4095 voltage range, 1 - 4,095,000,000
        """
        if axis not in self.axis_names:
            raise ValueError("{0} is not a valid axis, must be one of {1}".format(axis, self.axis_names))
        ch = c_int(int(axis))
        level = c_int(int(level))
        speed = c_int(int(speed))
        self.check_open_status()
        if relative:
            self.check_status(mcsc.SA_ScanMoveRelative_S(self.handle, ch, level, speed))
        else:
            self.check_status(mcsc.SA_ScanMoveAbsolute_S(self.handle, ch, level, speed))
        self.wait_until_stopped(ch)

    def multi_set_scanner_level(self, levels, axes, speeds, relative=False):
        self.check_open_status()
        levels = [c_int(int(level)) for level in levels]
        axes = [c_int(int(axis)) for axis in axes]
        speeds = [c_int(int(speed)) for speed in speeds]
        for i in range(len(axes)):
            if relative:
                pass
            else:
                self.check_status(mcsc.SA_ScanMoveAbsolute_S(self.handle, axes[i], levels[i], speeds[i]))
        for axis in axes:
            self.wait_until_stopped(axis)


    ### additional useful methods to control the piezo scanners

    def set_scanner_level_rel(self, diff, axis, speed=4095):
        """
        Scan up to 50V
        diff: -100 - 100 V, -4095 - 4095
        speed: 4095 s - 1 us for full 4095 voltage range, 1 - 4,095,000,000
        """
        self.set_scanner_level(diff, axis, speed, relative=True)

    def set_voltage(self, axis, voltage, speed=4095000000, relative=False):
        """
        Scan to 50V
        level: 0 - 100 V, 0 - 4095
        speed: 4095 s - 1 us for full 4095 voltage range, 1 - 4,095,000,000
        """
        level = self.voltage_to_level(voltage)
        self.set_scanner_level(level, axis, speed, relative)

    def set_rel_voltage(self, axis, voltage_diff, speed):
        """
        Scan to 50V
        level: 0 - 100 V, 0 - 4095
        speed: 4095 s - 1 us for full 4095 voltage range, 1 - 4,095,000,000
        """
        diff = self.voltage_to_level(voltage_diff)
        self.set_scanner_level(diff, axis, speed, relative=True)

    def move_scanner_to_position(self, position, axis, speed, relative=False):
        level = self.position_to_level(1e9*position)
        self.set_scanner_level(level, axis, speed, relative)

    def move_scanner_rel_to_position(self, axis, step, speed):
        diff = self.position_to_level(1e9*step)
        self.set_scanner_level(diff, axis, speed, relative=True)

    def multi_set_voltage(self, voltages, axes, speeds, relative=False):
        levels = [self.voltage_to_level(v) for v in voltages]
        self.multi_set_scanner_level(levels, axes, speeds, relative)

    def multi_move_scanner_to_position(self, positions, axes, speeds, relative=False):
        levels = [self.position_to_level(1e9*p) for p in positions]
        self.multi_set_scanner_level(levels, axes, speeds, relative)

    def position_to_level(self, position):
        # 1.5 um per 100 V, position can be between 0 and 1500 nm
        voltage = position / 15.
        level = self.voltage_to_level(voltage)
        return level

    def voltage_to_level(self, voltage):
        level = voltage * 4095. / 100.
        level = round(level)
        return level

    def level_to_voltage(self, level):
        voltage = 100. * level / 4095.
        return voltage

    def level_to_position(self, level):
        voltage = self.level_to_voltage(level)
        position = voltage * 10.
        return position

    def get_voltage(self, ch):
        level = self.get_scanner_level(ch)
        voltage = self.level_to_voltage(level)
        return voltage

    def get_qt_ui(self):
        return SmaractMCSUI(self)

    ### Useful Properties ###
    num_ch = property(get_num_channels)
    position = property(get_position)
    scan_position = property(get_scanner_position)


class SmaractStageUI(StageUI):
    def __init__(self, stage):
        super(SmaractStageUI, self).__init__(stage, stage_step_min=50e-9)

    def move_axis_relative(self, index, axis, dir=1):
        if axis in [1,2,4,5]:
            dir *= -1
        self.stage.move(dir*self.step_size[index], axis=axis, relative=True)
        self.update_ui[int].emit(axis)

class SmaractScanStageUI(StageUI):
    def __init__(self, stage):
        super(SmaractScanStageUI, self).__init__(stage, stage_step_max=100e-6)

    def move_axis_relative(self, index, axis, dir=1):
        if axis in [1,2,4,5]:
            dir *= -1
        self.stage.move_scanner_to_position(dir*self.step_size[index], axis=axis, speed=4095, relative=True)
        self.update_ui[int].emit(axis)

    @QtCore.Slot(int)
    @QtCore.Slot(str)
    def update_positions(self, axis=None):
        if axis is None:
            current_position = self.stage.scan_position
            for i in range(len(self.positions)):
                p = engineering_format(current_position[i], base_unit='m', digits_of_precision=3)
                self.positions[i].setText(p)
        else:
            i = self.stage.axis_names.index(axis)
            p = engineering_format(self.stage.scan_position[i], base_unit='m', digits_of_precision=3)
            self.positions[i].setText(p)


class SmaractMCSUI(QtWidgets.QWidget, UiTools):
    def __init__(self, mcs, parent=None):
        assert isinstance(mcs, SmaractMCS), "system must be a Smaract MCS"
        super(SmaractMCSUI, self).__init__()
        self.mcs = mcs
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'smaract_mcs.ui'), self)
        self.mcs_id.setText(str(mcs.mcs_id))
        self.num_ch.setText(str(mcs.num_ch))
        self.reference_button.clicked.connect(self.mcs.find_references)
        self.calibrate_button.clicked.connect(self.mcs.calibrate_system)
        self.step_stage_widget = self.replace_widget(self.step_stage_layout, self.step_stage_widget, SmaractStageUI(self.mcs))
        self.scan_stage_widget = self.replace_widget(self.scan_stage_layout, self.scan_stage_widget, SmaractScanStageUI(self.mcs))


if __name__ == '__main__':
    # print SA_OK
    system_id = SmaractMCS.find_mcs_systems()
    stage = SmaractMCS(system_id)
    #print stage.position
    #print stage.get_position()
    #print stage.get_position(0)

    import sys
    from nplab.utils.gui import get_qt_app
    app = get_qt_app()
    ui = stage.get_qt_ui()
    ui.show()
    sys.exit(app.exec_())
