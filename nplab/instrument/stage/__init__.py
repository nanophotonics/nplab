"""
Base class and interface for Stages.
"""
from __future__ import division
from __future__ import print_function

from builtins import str
from builtins import zip
from builtins import range
from past.utils import old_div
__author__ = 'alansanders, richardbowman'

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


class Stage(Instrument):
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
    def __init__(self,unit = 'm'):
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
                tuple(set_func(v, axis) for v,axis in zip(value, self.axis_names))
            else:
                tuple(set_func(value, axis) for axis in self.axis_names)
        elif isinstance(axis, collections.Sequence) and not isinstance(axis, str):
            if isinstance(value, collections.Sequence):
                tuple(set_func(v, ax) for v,ax in zip(value, axis))
            else:
                tuple(set_func(value, ax) for ax in axis)
        else:
            set_func(value, axis)

    # TODO: stored dictionary of 'bookmarked' locations for fast travel


class PiezoStage(Stage):

    def __init__(self):
        super(PiezoStage, self).__init__()

    def get_piezo_level(self, axis=None):
        """ Returns the voltage levels of the specified piezo axis. """
        raise NotImplementedError("You must override get_piezo_leveln in a Stage subclass.")
        if axis is None:
            return [self.get_scanner_level(axis) for axis in self.axis_names]
        else:
            if axis not in self.axis_names:
                raise ValueError("{0} is not a valid axis, must be one of {1}".format(axis, self.axis_names))

    def set_piezo_level(self, level, axis):
        """ Sets the voltage levels of the specified piezo axis. """
        raise NotImplementedError("You must override set_piezo_level in a Stage subclass.")
        if axis not in self.axis_names:
            raise ValueError("{0} is not a valid axis, must be one of {1}".format(axis, self.axis_names))

    def get_piezo_voltage(self, axis):
        """ Returns the voltage of the specified piezo axis. """
        raise NotImplementedError("You must override get_piezo_voltage in a Stage subclass.")

    def set_piezo_voltage(self, axis, voltage):
        """ Sets the voltage of the specified piezo axis. """
        raise NotImplementedError("You must override set_piezo_voltage in a Stage subclass.")

    def get_piezo_position(self, axis=None):
        """ Returns the position of the specified piezo axis. """
        raise NotImplementedError("You must override get_piezo_position in a Stage subclass.")

    def set_piezo_position(self, axis=None):
        """ Sets the position of the specified piezo axis. """
        raise NotImplementedError("You must override set_piezo_position in a Stage subclass.")





class StageUI(QtWidgets.QWidget, UiTools):
    update_ui = QtCore.Signal([int], [str])

    def __init__(self, stage, parent=None, stage_step_min=1e-9, stage_step_max=1e-3, default_step=1e-6):
        assert isinstance(stage, Stage), "instrument must be a Stage"
        super(StageUI, self).__init__()
        self.stage = stage
        #self.setupUi(self)
        self.step_size_values = step_size_dict(stage_step_min, stage_step_max,unit = self.stage.unit)
        self.step_size = [self.step_size_values[list(self.step_size_values.keys())[0]] for axis in stage.axis_names]
        self.update_ui[int].connect(self.update_positions)
        self.update_ui[str].connect(self.update_positions)
        self.create_axes_layout(default_step)
        self.update_positions()

    def move_axis_absolute(self, position, axis):
        self.stage.move(position, axis=axis, relative=False)
        if type(axis) == str:
            self.update_ui[str].emit(axis)
        elif type(axis) == int:
            self.update_ui[int].emit(axis)

    def move_axis_relative(self, index, axis, dir=1):
        self.stage.move(dir * self.step_size[index], axis=axis, relative=True)
        if type(axis) == str:
            #    axis = QtCore.QString(axis)
            self.update_ui[str].emit(axis)
        elif type(axis) == int:
            self.update_ui[int].emit(axis)

    def zero_all_axes(self, axes):
        pass
#        for axis in axes:
#            self.move_axis_absolute(0, axis)

    def create_axes_layout(self, default_step=1e-6, arrange_buttons='cross', rows=None):
        """Layout of the PyQt widgets for absolute and relative movement of all axis

        :param default_step:
        :param arrange_buttons: either 'cross' or 'stack'. If 'cross', assumes the stages axes are x,y,z movement,
        placing the arrows in an intuitive cross pattern
        :param rows: number of rows per column when distributing the QtWidgets
        :return:
        """
        if rows is None:
            rows = np.ceil(np.sqrt(len(self.stage.axis_names)))
        rows = int(rows)  # int is needed for the old_div and the modulo operations

        uic.loadUi(os.path.join(os.path.dirname(__file__), 'stage.ui'), self)
        self.update_pos_button.clicked.connect(partial(self.update_positions, None))
        path = os.path.dirname(os.path.realpath(nplab.ui.__file__))
        icon_size = QtCore.QSize(12, 12)
        self.positions = []
        self.set_positions = []
        self.set_position_buttons = []
        for i, ax in enumerate(self.stage.axis_names):
            col = 4 * (old_div(i, rows))
            position = QtWidgets.QLineEdit('', self)
            position.setReadOnly(True)
            self.positions.append(position)
            set_position = QtWidgets.QLineEdit('0', self)
            set_position.setMinimumWidth(40)
            self.set_positions.append(set_position)
            set_position_button = QtWidgets.QPushButton('', self)
            set_position_button.setIcon(QtGui.QIcon(os.path.join(path, 'go.png')))
            set_position_button.setIconSize(icon_size)
            set_position_button.resize(icon_size)
            set_position_button.clicked.connect(self.button_pressed)
            self.set_position_buttons.append(set_position_button)
            # for each stage axis add a label, a field for the current position,
            # a field to set a new position and a button to set a new position ..
            self.info_layout.addWidget(QtWidgets.QLabel(str(ax), self), i % rows, col)
            self.info_layout.addWidget(position, i % rows, col + 1)
            self.info_layout.addWidget(set_position, i % rows, col + 2)
            self.info_layout.addWidget(set_position_button, i % rows, col + 3)

            if i % rows == 0:
                if arrange_buttons == 'cross':
                    group = QtWidgets.QGroupBox('axes {0}'.format(1 + (old_div(i, rows))), self)
                    layout = QtWidgets.QGridLayout()
                    layout.setSpacing(3)
                    group.setLayout(layout)
                    self.axes_layout.addWidget(group, 0, old_div(i, rows))
                    offset = 0
                elif arrange_buttons == 'stack':
                    layout = self.axes_layout
                    offset = 7 * old_div(i, rows)
                else:
                    raise ValueError('Unrecognised arrangment: %s' % arrange_buttons)

            step_size_select = QtWidgets.QComboBox(self)
            step_size_select.addItems(list(self.step_size_values.keys()))
            step_size_select.activated[str].connect(partial(self.on_activated, i))
            step_str = engineering_format(default_step, self.stage.unit)
            step_index = list(self.step_size_values.keys()).index(step_str)
            step_size_select.setCurrentIndex(step_index)
            layout.addWidget(QtWidgets.QLabel(str(ax), self), i % rows, 5 + offset)
            layout.addWidget(step_size_select, i % rows, 6 + offset)
            if i % 3 == 0 and arrange_buttons == 'cross':
                layout.addItem(QtWidgets.QSpacerItem(12, 0), 0, 4)

            plus_button = QtWidgets.QPushButton('', self)
            plus_button.clicked.connect(partial(self.move_axis_relative, i, ax, 1))
            minus_button = QtWidgets.QPushButton('', self)
            minus_button.clicked.connect(partial(self.move_axis_relative, i, ax, -1))
            if arrange_buttons == 'cross':
                if i % rows == 0:
                    plus_button.setIcon(QtGui.QIcon(os.path.join(path, 'right.png')))
                    minus_button.setIcon(QtGui.QIcon(os.path.join(path, 'left.png')))
                    layout.addWidget(minus_button, 1, 0)
                    layout.addWidget(plus_button, 1, 2)
                elif i % rows == 1:
                    plus_button.setIcon(QtGui.QIcon(os.path.join(path, 'up.png')))
                    minus_button.setIcon(QtGui.QIcon(os.path.join(path, 'down.png')))
                    layout.addWidget(plus_button, 0, 1)
                    layout.addWidget(minus_button, 2, 1)
                elif i % rows == 2:
                    plus_button.setIcon(QtGui.QIcon(os.path.join(path, 'up.png')))
                    minus_button.setIcon(QtGui.QIcon(os.path.join(path, 'down.png')))
                    layout.addWidget(plus_button, 0, 3)
                    layout.addWidget(minus_button, 2, 3)
            elif arrange_buttons == 'stack':
                plus_button.setIcon(QtGui.QIcon(os.path.join(path, 'right.png')))
                minus_button.setIcon(QtGui.QIcon(os.path.join(path, 'left.png')))
                layout.addWidget(minus_button, i % rows, 0 + offset)
                layout.addWidget(plus_button, i % rows, 1 + offset)
            else:
                raise ValueError('Unrecognised arrangment: %s' % arrange_buttons)
            plus_button.setIconSize(icon_size)
            plus_button.resize(icon_size)
            minus_button.setIconSize(icon_size)
            minus_button.resize(icon_size)

    def button_pressed(self, *args, **kwargs):
        sender = self.sender()
        if sender in self.set_position_buttons:
            index = self.set_position_buttons.index(sender)
            axis = self.stage.axis_names[index]
            position = float(self.set_positions[index].text())
            self.move_axis_absolute(position, axis)

    def on_activated(self, index, value):
        # print self.sender(), index, value
        self.step_size[index] = self.step_size_values[value]

    @QtCore.Slot(int)
    # @QtCore.pyqtSlot('QString')
    @QtCore.Slot(str)
    def update_positions(self, axis=None):
        if axis not in self.stage.axis_names:
            axis = None
        if axis is None:
            for axis in self.stage.axis_names:
                self.update_positions(axis=axis)
        else:
            i = self.stage.axis_names.index(axis)
            try:
                p = engineering_format(self.stage.position[i], base_unit=self.stage.unit, digits_of_precision=4)
            except ValueError:
                p = '0 m'
            self.positions[i].setText(p)


def step_size_dict(smallest, largest, mantissas=[1, 2, 5],unit = 'm'):
    """Return a dictionary with nicely-formatted distances as keys and metres as values."""
    log_range = np.arange(np.floor(np.log10(smallest)), np.floor(np.log10(largest)) + 1)
    steps = [m * 10 ** e for e in log_range for m in mantissas if smallest <= m * 10 ** e <= largest]
    return OrderedDict((engineering_format(s, unit), s) for s in steps)


class PiezoStageUI(StageUI):

    def __init__(self, stage, parent=None, stage_step_min=1e-9,
                 stage_step_max=1e-3, default_step=1e-8,show_xy_pos=True,
                 show_z_pos=True):
        self.show_xy_pos = show_xy_pos
        self.show_z_pos = show_z_pos
        assert isinstance(stage, Stage), "instrument must be a Stage"
        super(PiezoStageUI, self).__init__(stage, parent, stage_step_min, stage_step_max, default_step)


    def create_axes_layout(self, default_step=1e-8, stack_multiple_stages='horizontal'):
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'piezo_stage.ui'), self)
        path = os.path.dirname(os.path.realpath(nplab.ui.__file__))
        icon_size = QtCore.QSize(12, 12)
        self.position_widgets = []
        self.xy_positions = []
        self.set_positions = []
        self.set_position_buttons = []
        for i, ax in enumerate(self.stage.axis_names):
            col = 4 * (old_div(i, 3))
            if i % 3 == 0:
                # absolute position for different stages consisting of 3 axes
                position_widget = XYZPositionWidget(self.stage.max_voltage_levels[old_div(i,3)],
                                                    self.stage.max_voltage_levels[old_div(i,3)+1],
                                                    self.stage.max_voltage_levels[old_div(i,3)+2],
                                                    show_xy_pos=self.show_xy_pos,
                                                    show_z_pos=self.show_z_pos)
                if self.show_xy_pos:
                    xy_position = position_widget.xy_widget.crosshair
                    xy_position.CrossHairMoved.connect(self.crosshair_moved)
                    self.xy_positions.append(xy_position)

                self.position_widgets.append(position_widget)

                self.info_layout.addWidget(position_widget, 0, col,3,1)

                # position control elements for different stages consisting of 3 axes, arranged in a grid layout
                group = QtWidgets.QGroupBox('stage {0}'.format(1 + (old_div(i, 3))), self)
                layout = QtWidgets.QGridLayout()
                layout.setSpacing(3)
                group.setLayout(layout)
                self.axes_layout.addWidget(group, 0, old_div(i, 3))
                zero_button = QtWidgets.QPushButton('', self)
                zero_button.setIcon(QtGui.QIcon(os.path.join(path, 'zero.png')))
                zero_button.setIconSize(icon_size)
                zero_button.resize(icon_size)
                n = len(self.stage.axis_names) - i if len(self.stage.axis_names) - i < 3 else 3
                #axes_set = self.stage.axis_names[i:i + n]
                #zero_button.clicked.connect(partial(self.zero_all_axes, axes_set))
                layout.addWidget(zero_button, 1, 1)

            set_position = QtWidgets.QLineEdit('0', self)   # text field to set position
            set_position.setMinimumWidth(40)
            set_position.setReadOnly(True)
            self.set_positions.append(set_position)
            set_position_button = QtWidgets.QPushButton('', self)
            set_position_button.setIcon(QtGui.QIcon(os.path.join(path, 'go.png')))
            set_position_button.setIconSize(icon_size)
            set_position_button.resize(icon_size)
            set_position_button.clicked.connect(self.button_pressed)
            self.set_position_buttons.append(set_position_button)
            # for each stage axis add a label, a field for the current position,
            # a field to set a new position and a button to set a new position ..
            self.info_layout.addWidget(QtWidgets.QLabel(str(ax), self), i % 3, col+1)
            self.info_layout.addWidget(set_position, i % 3, col + 2)
            self.info_layout.addWidget(set_position_button, i % 3, col + 3)

            step_size_select = QtWidgets.QComboBox(self)
            step_size_select.addItems(list(self.step_size_values.keys()))
            step_size_select.activated[str].connect(partial(self.on_activated, i))
            step_str = engineering_format(default_step, self.stage.unit)
            step_index = list(self.step_size_values.keys()).index(step_str)
            step_size_select.setCurrentIndex(step_index)
            layout.addWidget(QtWidgets.QLabel(str(ax), self), i % 3, 5)
            layout.addWidget(step_size_select, i % 3, 6)
            if i % 3 == 0:
                layout.addItem(QtWidgets.QSpacerItem(12, 0), 0, 4)

            plus_button = QtWidgets.QPushButton('', self)
            plus_button.clicked.connect(partial(self.move_axis_relative, i, ax, 1))
            minus_button = QtWidgets.QPushButton('', self)
            minus_button.clicked.connect(partial(self.move_axis_relative, i, ax, -1))
            if i % 3 == 0:
                plus_button.setIcon(QtGui.QIcon(os.path.join(path, 'right.png')))
                minus_button.setIcon(QtGui.QIcon(os.path.join(path, 'left.png')))
                layout.addWidget(minus_button, 1, 0)
                layout.addWidget(plus_button, 1, 2)
            elif i % 3 == 1:
                plus_button.setIcon(QtGui.QIcon(os.path.join(path, 'up.png')))
                minus_button.setIcon(QtGui.QIcon(os.path.join(path, 'down.png')))
                layout.addWidget(plus_button, 0, 1)
                layout.addWidget(minus_button, 2, 1)
            elif i % 3 == 2:
                plus_button.setIcon(QtGui.QIcon(os.path.join(path, 'up.png')))
                minus_button.setIcon(QtGui.QIcon(os.path.join(path, 'down.png')))
                layout.addWidget(plus_button, 0, 3)
                layout.addWidget(minus_button, 2, 3)
            plus_button.setIconSize(icon_size)
            plus_button.resize(icon_size)
            minus_button.setIconSize(icon_size)
            minus_button.resize(icon_size)

    def crosshair_moved(self):
        sender = self.sender()
        if sender in self.xy_positions:
            i = self.xy_positions.index(sender)
            self.stage.set_piezo_level(self.xy_positions[i].pos()[0],i*3)
            self.stage.set_piezo_level(self.xy_positions[i].pos()[1],i*3+1)
            # print "crosshair moved in xy_widget ", i
            # print self.xy_positions[i].pos()

    @QtCore.Slot(int)
    @QtCore.Slot(str)
    def update_positions(self, axis=None):
        piezo_levels = self.stage.piezo_levels
        if axis is None:
            for i in range(len(self.position_widgets)):
                if self.show_xy_pos:
                    self.position_widgets[i].xy_widget.setValue(piezo_levels[i*3],piezo_levels[i*3+1])
                if self.show_z_pos:
                    self.position_widgets[i].z_bar.setValue(piezo_levels[i*3+2])

        else:
            if self.show_xy_pos:
                if axis % 3 == 0:
                    self.position_widgets[old_div(axis,3)].xy_widget.setValue(piezo_levels[axis],piezo_levels[axis+1])
                elif axis % 3 == 1:
                    self.position_widgets[old_div(axis,3)].xy_widget.setValue(piezo_levels[axis-1],piezo_levels[axis])
            if self.show_z_pos and axis % 3 == 2:
                self.position_widgets[old_div(axis,3)].z_bar.setValue(piezo_levels[axis])








# class Stage(HasTraits):
#    """Base class for controlling translation stages.
#
#    This class defines an interface for translation stages, it is designed to
#    be subclassed when a new stage is added.  The basic interface is very
#    simple: the property "position" encapsulates most of a stage's
#    functionality.  Setting it moves the stage and getting it returns the
#    current position: in both cases its value should be convertable to a numpy
#    array (i.e. a list or tuple of numbers is OK, or just a single number if
#    appropriate).
#
#    More detailed control (for example non-blocking motion) can be achieved
#    with the functions:
#    * get_position(): return the current position (as a np.array)
#    * move(pos, relative=False, blocking=True): move the stage
#    * move_rel(pos, blocking=True): as move() but with relative=True
#    * is_moving: whether the stage is moving (property)
#    * wait_until_stopped(): block until the stage stops moving
#    * stop(): stop the current motion (may be unsupported)
#
#    Subclassing nplab.stage.Stage
#    -----------------------------
#    The only essential commands to subclass are get_position() and _move(). The
#    rest will be supplied by the parent class, to give the functionality above.
#    _move() has the same signature as move, and is called internally by move().
#    This allows the stage class to emulate blocking/non-blocking moves.
#
#    NB if a non-blocking move is requested of a stage that doesn't support it,
#    a blocking move can be done in a background thread and is_moving should
#    return whether that thread is alive, wait_until_stopped() is a join().
#    """
#    axis_names = ["X","Y","Z"]
#    default_axes_for_move = ['X','Y','Z']
#    default_axes_for_controls = [('X','X'),'Z']
#    emulate_blocking_moves = False
#    emulate_nonblocking_moves = False
#    emulate_multi_axis_moves = False
#    last_position = Dict(Str,Float)
#    axes = List(Instance())
#
#    def get_position(self):
#        """Return the current position of the stage."""
#        raise NotImplementedError("The 'get_position' method has not been overridden.")
#        return np.zeros(len(axis_names))
#    def move_rel(self, pos, **kwargs):
#        """Make a relative move: see move(relative=True)."""
#        self.move(pos, relative=True, **kwargs)
#    def move(self, pos, axis=None, relative=False, blocking=True, axes=None, **kwargs):
#        """Move the stage to the specified position.
#
#        Arguments:
#        * pos: the position to move to, or the displacement to move by
#        * relative: whether pos is an absolute or relative move
#        * blocking: if True (default), block until the move is complete. If
#            False, return immediately.  Use is_moving() to determine when it
#            stops, or wait_until_stopped().
#        * axes: the axes to move.
#        TODO if pos is a dict, allow it to specify axes with keys
#        """
#        if hasattr(pos, "__len__"):
#            if axes is None:
#                assert len(pos)<len(self.default_axes_for_move), "More coordinates were passed to move than axis names."
#                axes = self.default_axes_for_move[0:len(pos)] #pick axes starting from the first one - allows missing Z coordinates, for example
#            else:
#                assert len(pos) == len(axes), "The number of items in the pos and axes arguments must match."
#            if self.emulate_multi_axis_moves: #break multi-axis moves into multiple single-axis moves
#                for p, a in zip(pos, axes):
#                    self.move(p, axis=a, relative=relative, blocking=blocking, **kwargs) #TODO: handle blocking nicely.
#        else:
#            if axis is None:
#                axis=self.default_axes_for_move[0] #default to moving the first axis
#
#        if blocking and self.emulate_blocking_moves:
#            self._move(pos, relative=relative, blocking=False, axes=axes, **kwargs)
#            try:
#                self.wait_until_stopped()
#            except NotImplementedError as e:
#                raise NotImplementedError("nplab.stage.Stage was instructed to emulate blocking moves, but wait_until_stopped returned an error.  Perhaps this is because is_moving has not been subclassed? The original error was "+e.message)
#        if not blocking and self.emulate_nonblocking_moves:
#            raise NotImplementedError("We can't yet emulate nonblocking moves")
#        self._move(pos, relative=relative, blocking=blocking, axes=axes)
#    def _move(self, position=None, relative=False, blocking=True, *args, **kwargs):
#        """This should be overridden to have the same method signature as move.
#        If some features are not supported (e.g. blocking) then it should be OK
#        to raise NotImplementedError.  If you ask for it with the emulate_*
#        attributes, many missing features can be emulated.
#        """
#        raise NotImplementedError("You must subclass _move to implement it for your own stage")
#    def is_moving(self, axes=None):
#        """Returns True if any of the specified axes are in motion."""
#        raise NotImplementedError("The is_moving method must be subclassed and implemented before it's any use!")
#    def wait_until_stopped(self, axes=None):
#        """Block until the stage is no longer moving."""
#        while(self.is_moving(axes=axes)):
#            time.sleep(0.1)
#        return True
##    def __init__(self):


class DummyStage(Stage):
    """A stub stage for testing purposes, prints moves to the console."""

    def __init__(self):
        super(DummyStage, self).__init__()
        self.axis_names = ('x1', 'y1', 'z1', 'x2', 'y2', 'z2')
        self.max_voltage_levels = [4095 for ch in range(len(self.axis_names))]
        self._position = np.zeros((len(self.axis_names)), dtype=np.float64)
        self.piezo_levels = [50,50,50,50,50,50]

    def move(self, position, axis=None, relative=False):
        def move_axis(position, axis):
            if relative:
                self._position[self.axis_names.index(axis)] += position
            else:
                self._position[self.axis_names.index(axis)] = position
        self.set_axis_param(move_axis, position, axis)
        #i = self.axis_names.index(axis)
        #if relative:
        #    self._position[i] += position
        #else:
        #    self._position[i] = position
            # print "stage now at", self._position

    #def move_rel(self, position, axis=None):
    #    self.move(position, relative=True)

    def get_position(self, axis=None):
        return self.get_axis_param(lambda axis: self._position[self.axis_names.index(axis)], axis)

    position = property(get_position)

    def get_qt_ui(self):
        return PiezoStageUI(self,show_z_pos=False)



if __name__ == '__main__':
    import sys
    from nplab.utils.gui import get_qt_app

    stage = DummyStage()
    print(stage.move(2e-6, axis=('x1', 'x2')))
    print(stage.get_position())
    print(stage.get_position('x1'))
    print(stage.get_position(['x1', 'y1']))

    app = get_qt_app()
    ui = stage.get_qt_ui()
    ui.show()
    sys.exit(app.exec_())
