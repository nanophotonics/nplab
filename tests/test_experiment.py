"""
Test for the experiment module
==============================
"""

import sys
sys.path.append("../")
sys.path.append("./")
import os

import nplab
import nplab.experiment, nplab.instrument
from nplab.experiment import Experiment
from traits.api import Button, Int
from traitsui.api import View, VGroup, Item

class Blinky(nplab.instrument.Instrument):
    status = Int(0)

if __name__ == '__main__':
    b = Blinky()
    b.edit_traits()

    e = Experiment()
    e.configure_traits()

