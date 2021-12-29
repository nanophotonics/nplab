import numpy as np
import time
from nplab.instrument import Instrument
from nplab.instrument.stage import Stage, StageUI
import collections


class Tango(Stage):
    """A class representing motion-control stages.

    This class primarily provides two things: the ability to find the position
    of the stage (using `Stage.position` or `Stage.get_position(axis="a")`),
    and the ability to move the stage (see `Stage.move()`).

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
    axis_names = ('x', 'y', 'z')

    def __init__(self, unit='m'):
        Instrument.__init__(self)
        self.unit = unit

    def move(self, pos, axis=None, relative=False):
        raise NotImplementedError("You must override move() in a Stage subclass")

    def move_rel(self, position, axis=None):
        """Make a relative move, see move() with relative=True."""
        self.move(position, axis, relative=True)

    def move_axis(self, pos, axis, relative=False, **kwargs):
        """Move along one axis.

        This function moves only in one axis, by calling self.move with
        appropriately generated values (i.e. it supplies all axes with position
        instructions, but those not moving just get the current position).

        It's intended for use in stages that don't support single-axis moves."""
        if axis not in self.axis_names:
            raise ValueError("{0} is not a valid axis, must be one of {1}".format(axis, self.axis_names))

        full_position = np.zeros((len(self.axis_names))) if relative else self.position
        full_position[self.axis_names.index(axis)] = pos
        self.move(full_position, relative=relative, **kwargs)

    def get_position(self, axis=None):
        raise NotImplementedError("You must override get_position in a Stage subclass.")

    def select_axis(self, iterable, axis):
        """Pick an element from a tuple, indexed by axis name."""
        assert axis in self.axis_names, ValueError("{0} is not a valid axis name.".format(axis))
        return iterable[self.axis_names.index(axis)]

    def _get_position_proxy(self):
        """Return self.get_position() (this is a convenience to avoid having
        to redefine the position property every time you subclass - don't call
        it directly)"""
        return self.get_position()
    position = property(fget=_get_position_proxy, doc="Current position of the stage (all axes)")

    def is_moving(self, axes=None):
        """Returns True if any of the specified axes are in motion."""
        raise NotImplementedError("The is_moving method must be subclassed and implemented before it's any use!")

    def wait_until_stopped(self, axes=None):
        """Block until the stage is no longer moving."""
        while self.is_moving(axes=axes):
            time.sleep(0.01)

    def get_qt_ui(self):
        if self.unit == 'm':
            return StageUI(self)
        elif self.unit == 'u':
            return StageUI(self, stage_step_min=1E-3, stage_step_max=1000.0, default_step=1.0)
        elif self.unit == 'step':
            return StageUI(self, stage_step_min=1, stage_step_max=1000.0, default_step=1.0)
        elif self.unit == 'deg':
            return StageUI(self, stage_step_min=0.1, stage_step_max=360, default_step=1.0)
        else:
            self._logger.warn('Tried displaying a GUI for an unrecognised unit: %s' % self.unit)

    def get_axis_param(self, get_func, axis=None):
        if axis is None:
            return tuple(get_func(axis) for axis in self.axis_names)
        elif isinstance(axis, collections.Sequence) and not isinstance(axis, str):
            return tuple(get_func(ax) for ax in axis)
        else:
            return get_func(axis)

    def set_axis_param(self, set_func, value, axis=None):
        if axis is None:
            if isinstance(value, collections.Sequence):
                tuple(set_func(v, axis) for v, axis in zip(value, self.axis_names))
            else:
                tuple(set_func(value, axis) for axis in self.axis_names)
        elif isinstance(axis, collections.Sequence) and not isinstance(axis, str):
            if isinstance(value, collections.Sequence):
                tuple(set_func(v, ax) for v, ax in zip(value, axis))
            else:
                tuple(set_func(value, ax) for ax in axis)
        else:
            set_func(value, axis)
