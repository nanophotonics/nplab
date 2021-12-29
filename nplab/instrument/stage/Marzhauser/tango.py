from nplab.instrument import Instrument
from nplab.instrument.stage import Stage


class Tango(Stage):
    def __init__(self, unit='m'):
        Instrument.__init__(self)
        self.unit = unit

    def move(self, pos, axis=None, relative=False):
        raise NotImplementedError("You must override move() in a Stage subclass")

    def get_position(self, axis=None):
        raise NotImplementedError("You must override get_position in a Stage subclass.")

    def is_moving(self, axes=None):
        """Returns True if any of the specified axes are in motion."""
        raise NotImplementedError("The is_moving method must be subclassed and implemented before it's any use!")
