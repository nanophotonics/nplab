# -*- coding: utf-8 -*-
"""
Created on Sun Oct 07 12:43:44 2018

@author: wmd22, ydb20
"""
from builtins import object
from nplab.experiment.gui import run_function_modally
import numpy as np
from scipy.interpolate import interp1d
from scipy.optimize import minimize
from collections import deque
import time
import threading
import os


class WheelOfPower(object):
    """A quick wrapper to add a filter wheel and a powermeter together to create
    an autocalibrate object which can move to a given power"""

    def __init__(self, power_meter, rotation_stage):
        self.power_meter = power_meter
        self.rotation_stage = rotation_stage
        self.abort_deque = False
        self.deque_time = 1.0
        self.deque_length = 100
        self.history_deque = deque(maxlen=self.deque_length)

    def calibrate(self, start=0, stop=360, steps=360):
        stage_positions = np.linspace(start, stop, steps)
        powers = []
        for position in stage_positions:
            self.rotation_stage.move(position)
            powers.append(self.power_meter.average_power)
        powers = np.array(powers)
        interp_function = interp1d(stage_positions, powers)
        new_stage_positions = np.linspace(start, stop, steps * 100)
        new_powers = interp_function(new_stage_positions)
        self.powers = new_powers
        self.stage_position = new_stage_positions

    def power_to_pos(self, power):
        """Find the closest power by looking up the interpolated table """
        return self.stage_position[self.powers == self.find_nearest(self.powers, power)]

    def find_nearest(self, array, value):
        """ find the minimum value of an array"""
        return array[np.abs(array - value).argmin()]

    def move_to_power(self, power):
        pos = self.power_to_pos(power)
        self.rotation_stage.move(pos)

    def update_deque(self):
        running = True
        while running:
            t0 = time.time()
            current_powers = []
            while (time.time() - t0) < self.deque_time:
                current_powers.append(self.power_meter.average_power)
            self.history_deque.append(np.average(current_powers))
            if self.abort_deque == True:
                running = False
        self.abort_deque = False

    def start_deque_thread(self):
        self.deque_thread = threading.Thread(target=self.update_deque)
        self.deque_thread.start()

    def clear_deque_thread(self):
        self.history_deque = deque(maxlen=self.deque_length)


class PowerWheelMixin(object):
    """
    General mixin to add calibration functions to an instrument that controls power. The general calibration is done by
    providing interpolation functions to the measured power dependency.

    The user must implement the raw_power property.
    Optionally, the prepare_calibration gives some flexibility in choosing the interpolation region.
    """

    def __init__(self):
        super(PowerWheelMixin, self).__init__()
        self.cal_to_raw = lambda x: x
        self.raw_to_cal = lambda x: x
        self.calibration = None
        self._raw_calibration = None
        self._raw_min = 0
        self._raw_max = 1

    @property
    def raw_power(self):
        raise NotImplementedError

    @raw_power.setter
    def raw_power(self, value):
        raise NotImplementedError

    def prepare_calibration(self, calibration):
        """
        Allows the user to perform some analysis on the raw_calibration before making an interpolation.
        Useful in a situation where the calibration is not monotonic (making one of the interpolations multivalued)
        :return:
        """
        return calibration

    def _calibration_functions(self, calibration=None):
        if calibration is None:
            calibration = self.calibration
        self.cal_to_raw = interp1d(calibration[1], calibration[0])
        self.raw_to_cal = interp1d(calibration[0], calibration[1])

    def recalibrate(self, power_meter, points=3):
        """
        Selects a few random points. Finds the factor that would most closely bring the calibration to these
        points. This assumes that the only possible change is a multiplicative factor

        :param power_meter: instrument instance with a 'power' property
        :param points: int. Number of points you want to check
        :return:
        """
        assert self.calibration is not None

        old_calibration = np.copy(self.calibration)

        rand_indices = np.random.choice(old_calibration.shape[1], points)
        raw_vals = old_calibration[0, rand_indices]
        old_cal = old_calibration[1, rand_indices]
        run_function_modally(self._recalibrate, points, power_meter, raw_vals, old_cal)

    def _recalibrate(self, power_meter, raw_vals, old_cal, update_progress=lambda p: p):
        new_cal = []
        for idx, raw in enumerate(raw_vals):
            update_progress(idx)
            self.raw_power = raw
            new_cal += [power_meter.power]

        def minimise(params):
            return np.sum(np.abs((old_cal * params[0]) - new_cal))

        results = minimize(minimise, np.array([1]))

        self.calibration[1] *= results.x[0]
        self._calibration_functions()

    def calibrate(self, power_meter, points=51, min_power=None, max_power=None):
        """
        General calibration procedure. Iterates over 'raw_powers', and measures the actual powers using a powermeter

        :param power_meter: powermeter instrument with 'power' property
        :param points: int. Number of interpolation points
        :param min_power: float. minimum value of raw_power
        :param max_power: float. maximum value of raw_power
        :return:
        """
        if min_power is None:
            min_power = self._raw_min
        if max_power is None:
            max_power = self._raw_max

        raw_powers = np.linspace(min_power, max_power, points)
        run_function_modally(self._calibrate, points, power_meter, raw_powers)

    def _calibrate(self, power_meter, raw_powers, update_progress=lambda p: p):
        powers = np.array([])
        for idx, raw in enumerate(raw_powers):
            update_progress(idx)
            self.raw_power = raw
            powers = np.append(powers, power_meter.power)
        self._raw_calibration = np.array([raw_powers, powers])
        self.calibration = self.prepare_calibration(self._raw_calibration)
        self._calibration_functions()

    def save_calibration(self, filename=None):
        """
        Save calibration to a .txt using numpy
        :param filename: str
        :return:
        """
        if filename is None:
            filename = os.path.dirname(os.path.abspath(__file__)) + '/powerwheel_calibration.txt'
        np.savetxt(filename, self.calibration)

    def load_calibration(self, filename=None, power_meter=None):
        """
        Load a numpy-saved .txt

        :param filename: str
        :param power_meter: powermeter instrument with a 'power' attribute. If given, PowerWheel will recalibrate
        :return:
        """
        if filename is None:
            filename = os.path.dirname(os.path.abspath(__file__)) + '/powerwheel_calibration.txt'
        self.calibration = np.loadtxt(filename)
        if power_meter is not None:
            self.recalibrate(power_meter)
        self._calibration_functions()

    @property
    def power(self):
        return self.raw_to_cal(self.raw_power)

    @power.setter
    def power(self, value):
        self.raw_power = self.cal_to_raw(value)
