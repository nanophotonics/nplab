__author__ = 'alansanders,rwb27'
#__all__ = ['gui','thread_utils']

import time
import threading
import collections


def monitor_property(instance, property_name, how_long, how_often):
    """
    Given an nplab instrument instance and one of it's properties, it creates a deque containing the property's value
    over time. The deque gets updated in a background thread.

    :param instance: nplab.Instrument
    :param property_name: str
    :param how_long: float. Length of time you want to monitor for. In seconds
    :param how_often: float. Interval between measurements. In seconds
    :return:
    """
    setattr(instance, property_name + '_history', collections.deque(maxlen=how_long / how_often))
    setattr(instance, '_monitoring_' + property_name, True)

    def monitor():
        while getattr(instance, '_monitoring_' + property_name):
            getattr(instance, property_name + '_history').append(getattr(instance, property_name))
            time.sleep(how_often)

    monitor_thread = threading.Thread(target=monitor)
    monitor_thread.start()
