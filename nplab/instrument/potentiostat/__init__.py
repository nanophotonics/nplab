# -*- coding: utf-8 -*-
"""
Created on Tue Mar  1 23:15:56 2022

@author: gk463
"""

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
from nplab.ui.widgets.position_widgets import XYZPositionWidget
import inspect
from functools import partial
from nplab.utils.formatting import engineering_format
import collections

class Potentiostat(Instrument):
    def __init__(self):
        super(Instrument, self).__init__()
        self._model_name = None
        self._serial_number = None
        
    def get_model_name(self):
        """The model name of the spectrometer."""
        if self._model_name is None:
            self._model_name = 'model_name'
        return self._model_name
    
    model_name = property(get_model_name)
    
    def get_serial_number(self):
        """The spectrometer's serial number (as a string)."""
        warnings.warn("Using the default implementation for get_serial_number: this should be overridden!",DeprecationWarning)
        if self._serial_number is None:
            self._serial_number = 'serial_number'
        return self._serial_number

    serial_number = property(get_serial_number)
    
if __name__ == '__main__':
    import sys
    from nplab.utils.gui import get_qt_app

    potentiostat = Potentiostat()

    app = get_qt_app()
    ui = potentiostat.get_qt_ui()
    ui.show()
    sys.exit(app.exec_())