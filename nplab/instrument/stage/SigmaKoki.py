# -*- coding: utf-8 -*-
"""
This is an interface module for instruments produced by Sigma Koki

__author__: Yago
"""
from __future__ import division
from builtins import zip
from builtins import str
from builtins import map
from builtins import range
from nplab.utils.thread_utils import locked_action
from nplab.instrument.stage import Stage
from nplab.instrument.serial_instrument import SerialInstrument
from nplab.instrument.visa_instrument import VisaInstrument
import time


class GSC01(SerialInstrument, Stage):
    """
    Stage controller GSC-01
    """

    counts_per_degree = 400.
    axis_names = ('1', )
    metadata_property_names = ('position', )

    def __init__(self, address, **kwargs):

        self.port_settings = dict(baudrate=9600,
                                  bytesize=8,
                                  stopbits=1,
                                  parity='N',
                                  xonxoff=True,
                                  timeout=0.5,
                                  writeTimeout=0.5,
                                  rtscts=True
                                  )
        SerialInstrument.__init__(self, address)
        self.termination_character = '\r\n'
        Stage.__init__(self)

        if 'offsetOrigin' in kwargs:
            self.offsetOrigin(kwargs['offsetOrigin'])  # 20000)

        if 'home_on_start' in list(kwargs.keys()):
            if kwargs['home_on_start']:
                self.MechanicalHome()

    def __del__(self):
        try:
            self.ser.close()
        except:
            self._logger.warn("Couldn't close GSC01")

    def wait(self):
        while self.getACK3() != 'R':
            time.sleep(0.1)
            # pass

    def write_cmd(self, command, read=True, wait=False):
        '''
        :param command: serial command to send to device
        :param read: if True, reads out standard 'OK' or 'NG' reply from the GSC-01
        :param fname: name of calling function, only useful when verbose
        :return:
        '''

        self.write(command)

        if read:
            reply = self.readline()
            self._logger.debug('[%s]: %s' % (command, reply))
        else:
            reply = self.readline()
            if reply != 'OK\n':
                self._logger.warn('%s replied %s' % (command, reply))

        if wait:
            self.wait()

        return reply

    def MechanicalHome(self):
        '''
        This command is used to detect the mechanical origin for a stage and set that position as the origin. The moving
        speed S: 500pps, F:5000ps, R:200mS. Running a stop command suspends the operation. Any other commands are not
        acceptable.
        :return:
        '''
        self.write_cmd('H:1', read=False, wait=True)

    def initializeOrigin(self):
        """
        Sets the origin to the current position.
        """
        self.write('R:1')

    def offsetOrigin(self, steps):
        """
        Sets and offset to the homing command, so that the origin is not beside the limit sensors
        Effective only for the homing operation in MINI system. Value is initialised to zero when turning power off.
        :param steps: offset steps (integer)
        :return:
        """

        self.write('S:N%d' % steps)

    @locked_action
    def move(self, pos, axis=None, relative=False, wait=True):
        counts = self.counts_per_degree * pos
        if relative:
            if not (-16777214 <= counts <= 16777214):
                raise ValueError('stage1 must be between -16777214 and 16777214.')

            command = 'M:W'
            if counts >= 0:
                command += '+P%d' % counts
            else:
                command += '-P%d' % -counts
        else:
            command = 'A:W'
            if counts >= 0:
                command += '+P%d' % counts
            else:
                command += '-P%d' % -counts
        self.write_cmd(command, read=False)
        self._go()

        if wait:
            t0 = time.time()
            curpos = self.get_position()[0]
            while curpos != pos and time.time()-t0 < 10:
                curpos = self.get_position()[0]
                time.sleep(0.1)

    def get_position(self, axis=None):
        status = self.getStatus()
        counts = status.split(',')[0]
        position = float(counts)/self.counts_per_degree
        self._logger.debug('Status: %s. Counts: %s. Position returned %g' %(status, counts, position))
        return [position]

    def jog(self, direction, timeout=2):
        """
        Moves stage continuously at jogging speed for specified length of time.
        :param direction: either '+' or '-'
        :param timeout: in seconds
        :return:
        """

        self.write('J:1%s' % direction)
        t0 = time.time()
        self._go()
        while time.time() - t0 < timeout:
            time.sleep(0.1)
        self.decelerate()

    def _go(self):
        """
        Moves the stages. To be used internally.
        """
        self.write_cmd('G:', read=False)

    def decelerate(self):
        """
        Decelerates and stop the stages.
        """
        self.write('L:1')

    def stop(self):
        """
        Stops the stages immediately.
        """
        self.write('L:E')

    def setSpeed(self, minSpeed1, maxSpeed1, accelerationTime1):
        """
        Set minimum and maximum speeds and acceleration time.
        :param minSpeed1: between 100 and 20000, in steps of 100 [PPS]
        :param maxSpeed1: between 100 and 20000, in steps of 100 [PPS]
        :param accelerationTime1: between 0 and 1000 [ms]
        :return:
        """
        if not (100 <= minSpeed1 <= maxSpeed1 <= 20000):
            raise ValueError('Must be 100 <= minSpeed1 <= maxSpeed1 <= 20000')

        if not (0 <= accelerationTime1 <= 1000):
            raise ValueError('Must be 00 <= accelerationTime1 <= 1000.')

        self.write('D:1S%dF%dR%d' % (minSpeed1, maxSpeed1, accelerationTime1))

    def setJogSpeed(self, speed):
        """
        Set jog speed
        :param speed: between 100 and 20000, in steps of 100 [PPS]
        :return:
        """
        if 100 < speed < 20000:
            raise ValueError('Speed must be in 100-20000 range')

        self.write('S:J%d' % speed)

    def enableMotorExcitation(self, stage1=True):
        """
        Turn motor on/off
        :param stage1: True (on) or False (off)
        :return:
        """

        self.write('C:1%d' % stage1)

    def getStatus(self):
        """
        Gets the current status, consisting of position, command status, stop status, and motor readiness
        :return: position, ACK1, ACK2, ACK3
                ACK1:   X   Command Error
                        K   Command accepted normally
                ACK2:   L   Limit Sensor stop
                        K   Normal stop
                ACK3:   B   Busy
                        R   Ready
        """
        return self.write_cmd('Q:')

    def getACK3(self):
        """
        :return: 'R' if motor ready, 'B' if motor busy
        """
        self.write_cmd('!:', read=False)
        return self.readline()

    def getVersion(self):
        """
        Returns the ROM version
        """
        self.write('?:V', read=False)
        return self.readline()


class SHOT(VisaInstrument, Stage):
    """
    https://www.global-optosigma.com/en_jp/software/motorize/manual_en/SHOT-102.zip
    """
    axis_names = ('1', '2')

    def __init__(self, address, **kwargs):

        self.port_settings = dict(baudrate=38400,
                                  bytesize=8,
                                  stopbits=1,
                                  parity='N',
                                  xonxoff=True,
                                  timeout=0.5,
                                  writeTimeout=0.5,
                                  rtscts=True
                                  )
        VisaInstrument.__init__(self, address)
        self.termination_character = '\r\n'
        Stage.__init__(self, unit="step")

    def _rom_version(self):
        """
        Request an internal ROM version from the controller.
        :return: str, ROM version
        """
        return self.query("?:V")

    def _go(self, wait=True):
        """
        Moves the stages. To be used internally.
        """
        self._write_check('G:', wait=wait)

    @locked_action
    def _write_check(self, command, wait=False):
        self._logger.debug("Writing: %s" %command)
        self.write(command)
        self._logger.debug("Writing successful")
        reply = self.read()
        self._logger.debug("Read: %s" %reply)

        if reply == 'NG\n':
            self._logger.warn('%s replied %s' % (command, reply))
        else:
            if wait:
                self._wait()
            return reply

    def _wait(self):
        """
        Wait until controller is ready
        """
        while self.is_busy():
            time.sleep(0.1)

    def home(self, axis="W", direction="+"):
        """
        Detects the machine zero on the stage, and define the position as the home position
        :param axis: either 1, 2 or W (for both)
        :param direction: either + or -
        :return:
        """

        self._write_check("H:%s%s" % (axis, direction))

    def set_origin(self, axis="W"):
        """
        Sets the origin to the current position.
        :param axis: either 1, 2 or W (for both)
        """

        self._write_check('R:' + str(axis))

    def move(self, counts, axis=1, relative=False, wait=True):
        """

        :param counts: either an integer, or a tuple of two integers. Positive or negative
        :param axis: either 1, 2 or W (for both)
        :param relative:
        :param wait:
        :return:
        """
        if not hasattr(counts, '__iter__'):
            counts = (counts, )
        for count in counts:
            if not (-16777214 <= count <= 16777214):
                raise ValueError('stage1 must be between -16777214 and 16777214.')

        if relative:
            command = "M:"
        else:
            command = "A:"

        if not hasattr(axis, '__iter__'):
            command += str(axis)
        else:
            command += 'W'
        for count in counts:
            if count >= 0:
                command += '+P%d' % count
            else:
                command += '-P%d' % -count

        self._write_check(command, wait=wait)
        self._go(wait=wait)

    def get_position(self, axis=None):
        status = self.status()
        counts = list(map(int, status.split(',')[:2]))
        if axis is None:
            axis = self.axis_names
        elif not isinstance(axis, list) and not isinstance(axis, tuple):
            axis = [axis]
        return [self.select_axis(counts, ax) for ax in axis]

    def jog(self, axis="W", direction="+", timeout=2):
        """
        Moves stage continuously at jogging speed for specified length of time.

        :param axis: either 1, 2 or W (for both)
        :param direction: either + or -
        :param timeout: amount of seconds to jog for
        :return:
        """

        self._write_check("J:%s%s" % (axis, direction))

        t0 = time.time()
        self._go()
        while time.time() - t0 < timeout:
            time.sleep(0.1)
        self.decelerate()

    def decelerate(self, axis="W"):
        """
        Decelerates and stop the stages.
        :param axis: either 1, 2 or W (for both)
        """

        self._write_check('L:' + str(axis))

    def emergency_stop(self):
        """
        Stops the stages immediately.
        """
        self.write('L:E')

    def set_speed(self, axes, min_speed, max_speed, accel_time):
        """Changing the movement speed
        On turning ON the power, SHOT-102 will default a minimum speed (S), maximum speed (F), and
        acceleration/deceleration time (R), all set by switches 9 and 10 on DIP Switch 1 for each speed range.
        :param axis: either 1, 2 or W (for both)
        :param min_speed: integer or tuple of two integers
        :param max_speed: integer or tuple of two integers
        :param accel_time: integer or tuple of two integers
        :return:
        """

        if not (1 <= min_speed <= max_speed <= 20000):
            raise ValueError('Must be 1 <= min_speed <= max_speed <= 20000')
        if not (0 <= accel_time <= 5000):
            raise ValueError('Must be 0 <= accel_time <= 5000')
        if not hasattr(min_speed, "__iter__"):
            min_speed = tuple(min_speed)
        if not hasattr(max_speed, "__iter__"):
            max_speed = tuple(max_speed)
        if not hasattr(accel_time, "__iter__"):
            accel_time = tuple(accel_time)
        if axes == "W":
            if len(min_speed) != 2 or len(min_speed) != 2 or len(min_speed) != 2:
                raise ValueError('You need to provide speeds and times for both axis')

        command = "D:%s" %axes
        for mn, mx, at in zip(min_speed, max_speed, accel_time):
            command += "S" + str(mn) + "F" + str(mx) + "R" + str(at)
        self._write_check(command)

    def on_off(self, axes, state):
        """
        Deenergizes (motor free) or Energizes (hold) the motor.
        Execute this command to move (rotate) stages manually. Once executed, the actual stage position does not
        coincide with the coordinate value being displayed. For proper positioning, perform zero return and make the
        stage position consistent with the coordinate value being displayed.
        :param axes: either 1, 2 or W (for both)
        :param state: 0 (off) or 1 (on)
        :return:
        """
        self._write_check("C:%s%s" % (axes, state))

    def status(self):
        """
        A command to check the validity of an immediately preceding command, and request a controller to return the
        state of stage operations, coordinates of axes, etc.
        :return: str coord_1, coord_2, ACK1, ACK2, ACK3
            coordinates are 10-digit data including sign (positive is space)
            ACK1:   X - command or parameter error
                    K - successful command
            ACK2:   L - axis 1 emergency stop
                    M - axis 2 emergency stop
                    W - both axis emergency stop
                    K - normal stop
            ACK3:   B - busy
                    R - ready
        """
        return self.query("Q:")

    def is_busy(self):
        """

        :return: bool
        """
        reply = self.query("!:")

        if "B" in reply:
            return True
        else:
            return False


class HIT(SerialInstrument, Stage):
    """
    Stage controller for the many-axis HIT controller.

    https://www.global-optosigma.com/en_jp/software/motorize/manual_en/HIT_En.pdf
    """

    # TODO: interpolation commands. They set a position in the plane of two axes and jog in a curved or straight path
    # TODO: add units

    axis_names = list(map(str, list(range(8))))
    axis_LUT = dict(list(zip(list(map(str, list(range(8)))), list(range(8)))))

    def __init__(self, address, **kwargs):

        self.port_settings = dict(baudrate=38400,
                                  bytesize=8,
                                  stopbits=1,
                                  parity='N',
                                  xonxoff=True,
                                  timeout=0.5,
                                  writeTimeout=0.5,
                                  rtscts=True
                                  )
        SerialInstrument.__init__(self, address)
        self.termination_character = '\r\n'
        Stage.__init__(self, unit="step")

    def _axes_iterable(self, axes=None):
        """Convenience function

        Given a list of axes names or axes numbers (can be mixed), returns an list of the corresponding axes numbers
        using axis_LUT

        :param axes: list of axes names or number (can be mixed)
        :return:
        """
        if axes is None:
            axes = self.axis_names
        if not isinstance(axes, list) and not isinstance(axes, tuple):
            axes = (axes, )
        axes_iter = []
        for ax in axes:
            if ax in list(self.axis_LUT.keys()):
                axes_iter += [self.axis_LUT[ax]]
            elif type(ax) == int:
                axes_iter += [ax]
            else:
                raise ValueError("Unrecognised axis: %s %s" % (ax, type(ax)))
        return axes_iter

    def move(self, counts, axes=None, relative=False, wait=True):
        """

        :param counts: (int) number of motor steps. If iterable, should be same length as axes.
        :param axes: list of axes
        :param relative: (bool)
        :param wait: bool
        :return:
        """
        axes = self._axes_iterable(axes)
        if not hasattr(counts, '__iter__'):
            counts = [counts] * len(axes)
        for count in counts:
            assert -134217728 < count < +134217727
        counts = list(map(int, counts))

        if relative:
            command = 'M'
        else:
            command = 'A'

        self.multi_axis_cmd(command, axes, counts, wait)

        # TODO: add checking for Stage limits using status +-LS

    def get_position(self, axes=None):
        axes = self._axes_iterable(axes)
        all_positions = self.query("Q:").split(",")
        positions = []
        for ax in axes:
            try:
                positions += [int(all_positions[ax])]
            except ValueError:
                positions += [None]
        return positions

    def status(self, axes=None):
        """

        :param axes: list of strings/integers corresponding to the names or indices of the axes, or a single string/integer
        :return: string corresponding to the overall status, and a dictionary for the individual axes' status
        """
        bit_list = ["", "DRV alarm", "Scale alarm", "Z limit", "Near", "ORG", "+LS", "-LS"]
        raw_statuses = self.query("Q:S").split(",")
        status = []
        for rs in raw_statuses:
            try:
                # Converting to 8-bit hexadecimal. https://stackoverflow.com/questions/1425493/convert-hex-to-binary
                _bin = bin(int(rs, 16))[2:].zfill(8)
                _status = []
                for bit, bit_name in zip(_bin, bit_list):
                    if bool(int(bit)):
                        _status += [bit_name]
                if len(_status) > 0:
                    status += [_status]
                else:
                    status += ["OK"]
            except ValueError:
                status += [None]
        overall_status = status[0]
        axes_status = status[1:]

        axes = self._axes_iterable(axes)
        reply = dict()
        for name, indx in zip(self.axis_names, axes):
            reply[name] = axes_status[indx]
        return overall_status, reply

    def is_moving(self, axes=None):
        axes = self._axes_iterable(axes)
        statuses = self.query("!:").split(",")
        status = []
        for ax in axes:
            status += [bool(int(statuses[ax]))]  # converting a '0' or '1' to a False or True
        return any(status)

    @locked_action
    def write_check(self, command, wait=False):
        """
        Light wrapper providing error checking, locking and waiting

        :param command: full serial command to send to device
        :param wait: bool
        :return:
        """
        self.write(command)

        reply = self.readline()[:-1]  # excluding the \n termination
        self._logger.debug("Reply: %s" % reply)

        if reply == 'NG':
            self._logger.warn('%s replied %s' % (command, reply))
        else:
            if wait:
                self.wait_until_stopped()
            return reply

    def multi_axis_cmd(self, command, axes, parameters, wait=False):
        """Convenience function

        Creates commands with the appropriate parameters in the appropriate places.
        e.g. by simply giving 'H', None, 1 it creates the command H:,1,,,1,,,1 (assuming the stage has three active axes at positions 1, 4 and 7

        :param command: command code to send to device
        :param axes: axes name or index (or list of)
        :param parameters: list of parameters to pass. If iterable, it passes each item to each of the axes. Otherwise it passes the same argument to all axes
        :param wait: if True, calls self.wait before returning
        :return:
        """
        axes_iter = self._axes_iterable(axes)

        if not hasattr(parameters, "__iter__"):
            parameters = [parameters] * len(axes_iter)
        if len(parameters) != len(axes_iter):
            raise ValueError("Length of axes and parameters must be the same")

        self._logger.debug("Axes: %s axes_iter: %s Parameters: %s" % (axes, axes_iter, parameters))

        argument_list = ['DUMMY']*8
        for ax, param in zip(axes_iter, parameters):
            argument_list[ax] = str(param)
        argument_string = ','.join(argument_list)
        argument_string = argument_string.replace('DUMMY', '')
        command += ':' + argument_string
        self._logger.debug('Writing: %s' % command)

        self.write_check(command, wait)

    def mechanical_home(self, axes=None):
        """
        This command is used to detect the mechanical origin for a stage and set that position as the origin. The moving
        speed S: 500pps, F:5000ps, R:200mS. Running a stop command suspends the operation. Any other commands are not
        acceptable.
        :param axes: axes name or index (or list of)
        :return:
        """
        self.multi_axis_cmd('H', axes, 1, wait=True)

    def set_home(self, axes=None):
        """
        Sets the origin to the current position.
        :param axes: axes name or index (or list of)
        :return:
        """
        self.multi_axis_cmd('R', axes, 1)

    def jog(self, directions, axes=None, timeout=2):
        """
        Moves stage continuously at jogging speed for specified length of time.
        :param directions: a single value or iterable of either '+' or '-'
        :param axes:
        :param timeout: in seconds
        :return:
        """

        # TODO: make the write_check non-blocking for this to work
        raise NotImplementedError
        # self.multi_axis_cmd('J', axes, directions)
        # t0 = time.time()
        # while time.time() - t0 < timeout:
        #     time.sleep(0.1)
        # self.decelerate(axes)

    def decelerate(self, axes=None):
        """
        Decelerates and stop the stages.

        :param axes: axes name or index (or list of)
        :return:
        """

        self.multi_axis_cmd('L', axes, 1)

    def stop_all_stages(self):
        """
        Stops the stages immediately.
        """
        self.write_check('L:E')

    def set_speed(self, axis, start_speed, max_speed, acceleration_time):
        """

        :param axis: axes name or index
        :param start_speed:  between 100 and 20000, in steps of 100 [PPS]
        :param max_speed: between 100 and 20000, in steps of 100 [PPS]
        :param acceleration_time: between 0 and 1000 [ms]
        :return:
        """

        if not (1 <= start_speed <= max_speed <= 999999999):
            raise ValueError('Must be 1 <= start_speed <= max_speed <= 999999999')

        if not (1 <= acceleration_time <= 1000):
            raise ValueError('Must be 00 <= acceleration_time <= 1000.')

        axes = self._axes_iterable(axis)
        for axis in axes:
            self.write_check('D:%d,%d,%d,%d' % (axis, start_speed, max_speed, acceleration_time))

    def on_off(self, axes=None, on_off=None):
        """
        Turn motor on/off
        :param axes: axes name or index (or list of)
        :param on_off: True (on) or False (off)
        :return:
        """
        if on_off is None:
            on_off = 1

        self.multi_axis_cmd('C', axes, on_off)


if __name__ == '__main__':
    hit = HIT('COM15')
    hit._logger.setLevel("DEBUG")
    hit.show_gui()
