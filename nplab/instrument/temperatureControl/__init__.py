import numpy as np
from collections import OrderedDict
import itertools
from nplab.instrument import Instrument
import time
import threading
from nplab.utils.gui import *
from nplab.utils.gui import uic
from nplab.ui.ui_tools import UiTools
import nplab.ui
import inspect
from functools import partial
from nplab.utils.formatting import engineering_format
import collections


class TemperatureControl(Instrument):
    """A class representing temperature-control stages.

    This class primarily provides two things: the ability to find the temperature
    of the sensor (using `self.temperature` or `self.temperature()`),
    and the ability to set a target temperature (see `self.move()`).

    Subclassing Notes
    -----------------
    The minimum you need to do in order to subclass this is to override the
    `move` method and the `get_position` method.  NB you must handle the case
    where `axis` is specified and where it is not.  For `move`, `move_axis` is
    provided, which will help emulate single-axis moves on stages that can't
    make them natively.

    In the future, a class factory method might be available, that will
    simplify the emulation of various features.
    """

    metadata_property_names = ('temperature', )

    def __init__(self):
        Instrument.__init__(self)

    def get_temperature(self):
        raise NotImplementedError
    temperature = property(fget=get_temperature)

    def set_target_temperature(self, value):
        raise NotImplementedError
    def get_target_temperature(self):
        return
    target_temperature = property(fset=set_target_temperature, fget=get_target_temperature)