__author__ = 'alansanders'

from nplab.instrument.visa_instrument import VisaInstrument
from nplab.instrument.stage import Stage
import time
import numpy as np


class PIStage(Stage, VisaInstrument):
    """
    Control interface for PI stages.
    """
    def __init__(self, address='ASRL3::INSTR'):
        super(PIStage, self).__init__(address)
        self.instr.read_termination = '\n'
        self.instr.write_termination = '\n'
        self.axis_names = ('a', 'b', 'c')
        self.positions = [0 for ch in xrange(3)]
        self._stage_id = None

    def move(self, pos, axis=None, relative=False):
        if relative:
            self.write('mvr {0}{1}'.format(axis, 1e6*pos))
        else:
            self.write('mov {0}{1}'.format(axis, 1e6*pos))
        raise NotImplementedError("You must override move() in a Stage subclass")

    def get_position(self, axis=None):
        return self.get_axis_param(lambda axis: 1e6*float(self.query('pos? {0}'.format(axis))), axis)
    position = property(fget=get_position, doc="Current position of the stage")

    def is_moving(self, axes=None):
        """
        Returns True if any of the specified axes are in motion.
        In this case the position is polled 3 times and see if the stage stays close to
        its initial position.
        """
        positions = np.zeros((3, len(axes)))
        for i in xrange(3):
            positions[i] = [self.get_position(axis) for axis in axes]
            time.sleep(0.005)
        sum_of_diffs = np.sum(positions-positions[0], axis=1)
        if np.any(sum_of_diffs > 0.01):
            return True
        else:
            return False

    def wait_until_stopped(self, axes=None):
        """Block until the stage is no longer moving."""
        while self.is_moving(axes=axes):
            time.sleep(0.01)

    def startup(self):
        self.online = 1
        self.loop_mode = 1
        self.speed_mode = 0
        self.velocity = 100
        self.drift_compensation = 0
        self.instr.write('cto 132')
        self.instr.write('cto 232')
        self.instr.write('cto 332')

    def shutdown(self):
        self.loop_mode = 0
        self.online = 0

    def get_velocity(self, axis=None):
        return self.get_axis_param(lambda axis: float(self.query('vel? {0}'.format(axis))), axis)
    def set_velocity(self, value, axis=None):
        self.set_axis_param(lambda value, axis: self.query('vel {0}{1}'.format(axis, value)), value, axis)
    velocity = property(get_velocity, set_velocity)

    def get_drift_compensation(self, axis=None):
        return self.get_axis_param(lambda axis: bool(self.query('dco? {0}'.format(axis))), axis)
    def set_drift_compensation(self, value, axis=None):
        self.set_axis_param(lambda value, axis: self.query('dco {0}{1}'.format(axis, value)), value, axis)
    drift_compensation = property(get_drift_compensation, set_drift_compensation)

    def get_loop_mode(self, axis=None):
        return self.get_axis_param(lambda axis: bool(self.query('svo? {0}'.format(axis))), axis)
    def set_loop_mode(self, value, axis=None):
        """
        Set the mode of each axis control loop
        :param value: servo control mode - 1 for closed loop, 0 for open loop
        :param axis:
        :return:
        """
        self.set_axis_param(lambda value, axis: self.query('svo {0}{1}'.format(axis, value)), value, axis)
    loop_mode = property(get_loop_mode, set_loop_mode)

    def get_speed_mode(self, axis=None):
        return self.get_axis_param(lambda axis: bool(self.query('vco? {0}'.format(axis))), axis)
    def set_speed_mode(self, value, axis=None):
        """
        Set the mode of each axis control loop
        :param value: speed control mode - 1 for controlled speed, 0 for fastest
        :param axis:
        :return:
        """
        self.set_axis_param(lambda value, axis: self.query('vco {0}{1}'.format(axis, value)), value, axis)
    speed_mode = property(get_speed_mode, set_speed_mode)

    def get_online(self):
        return bool(self.query('online?'))
    def set_online(self, value):
        self.write('online {0}'.format(value))
    online = property(get_online, set_online)

    def get_on_target(self):
       return bool(self.query('ont?'))
    on_target = property(get_on_target)

    def get_id(self):
        if self._stage_id is None:
            self._stage_id = self.query('*idn?')
        return self._stage_id
    stage_id = property(get_id)