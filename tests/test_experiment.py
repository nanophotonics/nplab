"""
Test for the experiment module
==============================

unfortunately, this needs a GUI to test it - so it's not compatible with
automated unit testing (yet...)
"""

from traits.api import Button, Int
from traitsui.api import Item, VGroup, View

import nplab
import nplab.experiment
import nplab.instrument
from nplab.experiment import Experiment


class Blinky(nplab.instrument.Instrument):
    status = Int(0)

if __name__ == '__main__':
    b = Blinky()
    b.edit_traits()

    e = Experiment()
    e.configure_traits()

