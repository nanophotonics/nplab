# -*- coding: utf-8 -*-

from builtins import object
from nplab.utils import monitor_property
import threading
import time


class TemperatureControlMixin(object):
    """A class representing temperature-control stages.

    This class provides two threads: a temperature control thread that monitors the temperature every second and sends a
    warning when the temperature is out of range, and a temperature monitoring thread that saves the temperature every
    second and stores the latest temperatures

    Subclassing Notes
    -----------------
    The minimum you need to do in order to subclass this is to override the
    `get_temperature` method
    """
    def __init__(self):
        super(TemperatureControlMixin, self).__init__()

        self._control_thread = None
        self._controlling = False

    def get_temperature(self):
        raise NotImplementedError
    temperature = property(fget=get_temperature)

    def set_target_temperature(self, value):
        raise NotImplementedError

    def get_target_temperature(self):
        return
    target_temperature = property(fset=set_target_temperature, fget=get_target_temperature)

    def monitor_temperature(self, how_long=5, how_often=10, warn_limits=None):
        """Sets a thread to monitor the temperature

        :param int how_long: how long a history to keep, in minutes
        :param int how_often: how often to add a value to the history, in seconds
        :param 2-tuple warn_limits: min/max temperature below/above which a warning is raised
        :return:
        """
        monitor_property(self, 'temperature', how_long * 60, how_often, warn_limits)

    def control_temperature(self, upper_target=None, lower_target=None):
        """
        Starts a background thread that checks the temperature is within the stated range. If both range limits are
        None, and the target_temperature property has not been set, we assume an upper limit of 1000

        :param upper_target: float
        :param lower_target: float
        :return:
        """
        if upper_target is None and lower_target is None:
            if self.target_temperature is not None:
                upper_target = self.target_temperature
            else:
                upper_target = 1000
        if self._control_thread is not None:
            self._controlling = False
            self._control_thread.join()
            del self._control_thread
        self._control_thread = threading.Thread(target=self._control_temperature, args=(upper_target, lower_target))
        self._controlling = True
        self._control_thread.start()

    def _control_temperature(self, upper_temp=None, lower_temp=None):
        while upper_temp > self.temperature > lower_temp:
            time.sleep(1)
            if not self._controlling:
                break
        self._logger.warn('Temperature out of range')
