# -*- coding: utf-8 -*-
from __future__ import division
__author__ = 'alansanders,rwb27'
#__all__ = ['gui','thread_utils']

import time
import threading
import collections


def monitor_property(instance, property_name, how_long, how_often, warn_limits=None):
    """
    Given an nplab instrument instance and one of it's properties, it creates a deque containing the property's value
    over time. The deque gets updated in a background thread.

    :param instance: nplab.Instrument
    :param property_name: str
    :param how_long: float. Length of time you want to monitor for. In seconds
    :param how_often: float. Interval between measurements. In seconds
    :param warn_limits: None or 2-tuple. If the monitored value goes outside these limits, throws out a warning.
    :return:
    """
    setattr(instance, property_name + '_history', collections.deque(maxlen=int(how_long / how_often)))
    setattr(instance, '_monitoring_' + property_name, True)

    def monitor():
        while getattr(instance, '_monitoring_' + property_name):
            value = getattr(instance, property_name)
            if warn_limits is not None:
                if value < warn_limits[0] or value > warn_limits[1]:
                    raise ValueError('%s=%g is outside of range' % (property_name, value))
            getattr(instance, property_name + '_history').append(value)
            time.sleep(how_often)

    monitor_thread = threading.Thread(target=monitor)
    monitor_thread.setDaemon(True)  # a daemon thread will not prevent the program from exiting
    monitor_thread.start()
