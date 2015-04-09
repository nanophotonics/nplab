# -*- coding: utf-8 -*-
"""
NP Lab Stage Module
===================

This module contains various things to simplify the use of stages in Python.  

@author: Richard Bowman, Alan Sanders
"""

from traits.api import HasTraits, Tuple, Button, Enum, Any, List, Str, Instance, Float, Dict, Array
from traitsui.api import View, Item, ButtonEditor, HGroup, VGroup, Spring, Group, VGrid
from pyface.api import ImageResource
import numpy as np
from collections import OrderedDict
import itertools
import __init__ as nplab
import time
import threading


def step_size_dict(smallest, largest, mantissas=[1,2,5]):
    """Return a dictionary with nicely-formatted distances as keys and metres as values."""
    steps = [m * 10**e 
                for e in np.arange(np.floor(np.log10(smallest)), np.floor(np.log10(largest))+1) 
                for m in mantissas 
                if smallest <= m * 10**e
                if m * 10**e <= largest]
    return OrderedDict((nplab.engineering_format(s, 'm'), s) for s in steps)
class Axis(HasTraits):
    """Lightweight wrapper class that controls one axis of a stage."""
    step_up = Button()
    step_down = Button()
    stage = Instance()
    axis_name = Str()
    traits_view = VGroup(
            Item()
        )
    def __init__(self, stage, axis_name):
        super(Axis, self).__init__()
        self.stage = stage
        self.axis_name = axis_name
    
class Stage(HasTraits):
    """Base class for controlling translation stages.
    
    This class defines an interface for translation stages, it is designed to
    be subclassed when a new stage is added.  The basic interface is very
    simple: the property "position" encapsulates most of a stage's
    functionality.  Setting it moves the stage and getting it returns the
    current position: in both cases its value should be convertable to a numpy
    array (i.e. a list or tuple of numbers is OK, or just a single number if
    appropriate).
    
    More detailed control (for example non-blocking motion) can be achieved 
    with the functions:
    * get_position(): return the current position (as a np.array)
    * move(pos, relative=False, blocking=True): move the stage
    * move_rel(pos, blocking=True): as move() but with relative=True
    * is_moving: whether the stage is moving (property)
    * wait_until_stopped(): block until the stage stops moving
    * stop(): stop the current motion (may be unsupported)
    
    Subclassing nplab.stage.Stage
    -----------------------------
    The only essential commands to subclass are get_position() and _move(). The
    rest will be supplied by the parent class, to give the functionality above.
    _move() has the same signature as move, and is called internally by move().
    This allows the stage class to emulate blocking/non-blocking moves.
    
    NB if a non-blocking move is requested of a stage that doesn't support it, 
    a blocking move can be done in a background thread and is_moving should 
    return whether that thread is alive, wait_until_stopped() is a join().
    """
    axis_names = ["X","Y","Z"]
    default_axes_for_move = ['X','Y','Z']
    default_axes_for_controls = [('X','X'),'Z']
    emulate_blocking_moves = False
    emulate_nonblocking_moves = False
    emulate_multi_axis_moves = False
    last_position = Dict(Str,Float)
    axes = List(Instance())

    def get_position(self):
        """Return the current position of the stage."""
        raise NotImplementedError("The 'get_position' method has not been overridden.")
        return np.zeros(len(axis_names))
    def move_rel(self, pos, **kwargs):
        """Make a relative move: see move(relative=True)."""
        self.move(pos, relative=True, **kwargs)
    def move(self, pos, axis=None, relative=False, blocking=True, axes=None, **kwargs):
        """Move the stage to the specified position.
        
        Arguments:
        * pos: the position to move to, or the displacement to move by
        * relative: whether pos is an absolute or relative move
        * blocking: if True (default), block until the move is complete. If
            False, return immediately.  Use is_moving() to determine when it
            stops, or wait_until_stopped().
        * axes: the axes to move.
        TODO if pos is a dict, allow it to specify axes with keys
        """
        if hasattr(pos, "__len__"):
            if axes is None:
                assert len(pos)<len(self.default_axes_for_move), "More coordinates were passed to move than axis names."
                axes = self.default_axes_for_move[0:len(pos)] #pick axes starting from the first one - allows missing Z coordinates, for example
            else:
                assert len(pos) == len(axes), "The number of items in the pos and axes arguments must match."
            if self.emulate_multi_axis_moves: #break multi-axis moves into multiple single-axis moves
                for p, a in zip(pos, axes):
                    self.move(p, axis=a, relative=relative, blocking=blocking, **kwargs) #TODO: handle blocking nicely.
        else:
            if axis is None:
                axis=self.default_axes_for_move[0] #default to moving the first axis
                
        if blocking and self.emulate_blocking_moves:
            self._move(pos, relative=relative, blocking=False, axes=axes, **kwargs)
            try:
                self.wait_until_stopped()
            except NotImplementedError as e:
                raise NotImplementedError("nplab.stage.Stage was instructed to emulate blocking moves, but wait_until_stopped returned an error.  Perhaps this is because is_moving has not been subclassed? The original error was "+e.message)
        if not blocking and self.emulate_nonblocking_moves:
            raise NotImplementedError("We can't yet emulate nonblocking moves")
        self._move(pos, relative=relative, blocking=blocking, axes=axes)
    def _move(self, position=None, relative=False, blocking=True, *args, **kwargs):
        """This should be overridden to have the same method signature as move.
        If some features are not supported (e.g. blocking) then it should be OK
        to raise NotImplementedError.  If you ask for it with the emulate_* 
        attributes, many missing features can be emulated.
        """
        raise NotImplementedError("You must subclass _move to implement it for your own stage")
    def is_moving(self, axes=None):
        """Returns True if any of the specified axes are in motion."""
        raise NotImplementedError("The is_moving method must be subclassed and implemented before it's any use!")
    def wait_until_stopped(self, axes=None):
        """Block until the stage is no longer moving."""
        while(self.is_moving(axes=axes)):
            time.sleep(0.1)
        return True
    def __init__(self):
        