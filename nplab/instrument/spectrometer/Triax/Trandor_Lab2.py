from __future__ import division
from __future__ import print_function

# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 28 11:01:37 2020

@author: Hera
"""
"""
jpg66
"""
"""
Created on Tue Apr 14 18:45:32 2015

@author: jpg66. Based on code by Hamid Ohadi (hamid.ohadi@gmail.com)
"""

from nplab.instrument.visa_instrument import VisaInstrument
import numpy as np
import time
import copy
import scipy.interpolate as scint
from builtins import input
from builtins import str
from past.utils import old_div
import numpy as np
from nplab.instrument.camera.Andor import Andor, AndorUI
import types
import future
import os

"""

"""

from nplab.instrument.spectrometer.Triax.trandor import Trandor
from nplab.instrument.camera.Andor import AndorUI

# def Capture(_AndorUI):
#     if _AndorUI.Andor.white_shutter is not None:
#         isopen = _AndorUI.Andor.white_shutter.is_open()
#         if isopen:
#             _AndorUI.Andor.white_shutter.close_shutter()
#         _AndorUI.Andor.raw_image(update_latest_frame=True)
#         if isopen:
#             _AndorUI.Andor.white_shutter.open_shutter()
#     else:
#         _AndorUI.Andor.raw_image(update_latest_frame=True)


# setattr(AndorUI, 'Capture', Capture)

if __name__ == '__main__':
    from triax_calibration.auto_calibrate import Calibrator
    t = Trandor(calibrator=Calibrator(Trandor.CCD_size))
    t.show_gui(False)
    t.triax.show_gui(False)
