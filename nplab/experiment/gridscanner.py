"""
Experiment classes for grid scanning experiments. The main classes are GridScanner,
AcquisitionThread and GridScanController. The AcquisitionThread takes the GridScanner,
which defines the scan, and runs its methods in a thread as called by the GridScanController,
which controls the overall experiment.
"""

__author__ = 'alansanders'

import os
import h5py
from traits.api import HasTraits, Instance, Button, Int, Array, List, Property, Float
from traits.api import Tuple, String, Enum, Dict, Bool, NO_COMPARE
from traitsui.api import View, Item, Group, HGroup, VGroup, spring
import numpy as np
import threading
from threading import Thread
from time import sleep, time
import operator
from nplab.instrument.stage import Stage
from nplab.utils.gui import QtCore, QtGui
from functools import partial


group_params = {'show_border': True, 'springy': False}
button_params = dict(show_label=False)


class GridScanner(object):
    """

    """

    def __init__(self):
        super(GridScanner, self).__init__()
        self.scanner = Stage()
        self.stage_units = 1
        self.axes = ['x', 'y']
        self.size = np.array([1., 1.], dtype=np.float64)
        self.step = np.array([0.1, 0.1], dtype=np.float64)
        self.init = np.array([0., 0.], dtype=np.float64)
        self.num_axes = 2
        self.scan_axes = None
        self._unit_conversion = {'nm': 1e-9, 'um': 1e-6, 'mm': 1e-3}
        self.size_unit, self.step_unit, self.init_unit = ('um', 'um', 'um')
        self.init_grid(self.axes, self.size, self.step, self.init)
        self.status = 'inactive'

        self.abort_requested = False

        self.estimated_step_time = 0.001

    #@property
    #def status(self):
    #    return self._status
    #@status.setter
    #def status(self, value):
    #    self._status = value
        #self.status_updated.emit(value)

    @property
    def num_axes(self):
        return self._num_axes
    @num_axes.setter
    def num_axes(self, value):
        self._num_axes = value
        self._update_axes()

    def rescale_parameter(self, param, value):
        assert value in self._unit_conversion.keys(), 'a valid unit must be supplied'
        unit_param = '_%s_unit' % param
        old_value = getattr(self, unit_param) if hasattr(self, unit_param) else value
        setattr(self, unit_param, value)
        a = getattr(self, param)
        a *= self._unit_conversion[old_value] / self._unit_conversion[value]

    @property
    def size_unit(self):
        return self._size_unit
    @size_unit.setter
    def size_unit(self, value):
        self.rescale_parameter('size', value)

    @property
    def step_unit(self):
        return self._step_unit
    @step_unit.setter
    def step_unit(self, value):
        self.rescale_parameter('step', value)

    @property
    def init_unit(self):
        return self._init_unit
    @init_unit.setter
    def init_unit(self, value):
        self.rescale_parameter('init', value)

    def _update_axes(self):
        current_axes = self.axes
        current_size, current_step, current_init = (self.size.copy(), self.step.copy(), self.init.copy())
        if self.num_axes > len(current_axes):
            self.axes = ['']*self.num_axes
            self.size, self.step, self.init = (np.zeros(self.num_axes), np.zeros(self.num_axes), np.zeros(self.num_axes))
            self.axes[:len(current_axes)] = current_axes
            self.size[:len(current_axes)] = current_size
            self.step[:len(current_axes)] = current_step
            self.init[:len(current_axes)] = current_init
        else:
            self.axes = current_axes[:self.num_axes]
            self.size = current_size[:self.num_axes]
            self.step = current_step[:self.num_axes]
            self.init = current_init[:self.num_axes]
        #self.axes_updated.emit(self.axes)
        #self.size_updated.emit(self.size)
        #self.step_updated.emit(self.step)
        #self.init_updated.emit(self.init)
        print self.num_axes, self.axes, self.size

    def start(self, rate=0.2):
        """Starts grid scanner data acquisition."""
        if (hasattr(self, 'acquisition_thread') and self.acquisition_thread.is_alive()) or\
                (hasattr(self, 'display_thread') and self.display_thread.is_alive()):
            print 'scan already running'
            return
        self.acquisition_thread = threading.Thread(target=self.scan_grid,
                                                   args=(self.axes, self.size, self.step, self.init))
        self.display_thread = threading.Thread(target=self.update_gui, args=(rate,))
        self.acquisition_thread.start()
        self.display_thread.start()

    def abort(self):
        """Requests an abort of the currently running grid scan."""
        if not hasattr(self, 'acquisition_thread'):
            return
        if self.acquisition_thread.is_alive():
            print 'aborting'
            self.abort_requested = True
            while self.acquisition_thread.is_alive():
                continue

    def init_grid(self, axes, size, step, init):
        """Create a grid on which to scan."""
        scan_axes = []
        for i in range(len(axes)):
            s = size[i] * self._unit_conversion[self.size_unit]
            st = step[i] * self._unit_conversion[self.step_unit]
            s0 = init[i] * self._unit_conversion[self.init_unit]
            ax = np.arange(0, s+st/2., st) - s/2. + s0
            scan_axes.append(ax)
        self.grid_shape = tuple(ax.size for ax in scan_axes)
        self.total_points = reduce(operator.mul, self.grid_shape, 1)
        self.scan_axes = scan_axes
        return scan_axes

    def init_current_grid(self):
        """Convenience method that initialises a grid based on current parameters."""
        self.init_grid(self.axes, self.size, self.step, self.init)

    def move(self, position, axis):
        """Move to a position along a given axis."""
        self.scanner.move_axis(position/self.stage_units, axis=axis)

    def get_position(self, axis):
        return self.scanner.get_position(axis=axis)*self.stage_units

    def open_scan(self):
        self.acquiring = True

    def scan_function(self, *indices):
        """Applied at each position in the grid scan."""
        #print 'func', indices
        sleep(0.01)

    def _timed_scan_function(self, *indices):
        t0 = time()
        self.scan_function(*indices)
        dt = time() - t0
        self._step_times[indices] = dt

    def analyse_scan(self):
        pass

    def close_scan(self):
        self.acquiring = False

    def update_drift_compensation(self):
        """Update the current drift compensation.

        If you have a nice way of compensating for drift, you should use this
        function to do it - it's called each time the outermost scan axis
        updates."""
        pass

    def estimate_scan_duration(self):
        """Estimate the duration of a grid scan."""
        estimated_time = self.total_points * self.estimated_step_time
        return self.format_time(estimated_time)

    def get_estimated_time_remaining(self):
        """Estimate the time remaining of the current scan."""
        if not hasattr(self, '_step_times'):
            return np.inf
        mask = np.isfinite(self._step_times)
        if not np.any(mask):
            return 0
        average_step_time = np.mean(self._step_times[mask])
        etr = (self.total_points - self._index) * average_step_time  # remaining steps = self.total_points - index
        return etr

    def format_time(self, t):
        """Formats the time in seconds into a string with convenient units."""
        if t < 120:
            return '{0:.1f} s'.format(t)
        elif (t >= 120) and (t < 3600):
            return '{0:.1f} mins'.format(t / 60.)
        elif t >= 3600:
            return '{0:.1f} hours'.format(t / 3600.)
        else:
            return 'You should probably not be running this scan!'

    def get_formatted_estimated_time_remaining(self):
        """Returns a string of convenient units for the estimated time remaining."""
        if self.acquisition_thread.is_alive():
            etr = self.get_estimated_time_remaining()
            return self.format_time(etr)
        else:
            return 'inactive'

    def print_scan_time(self, t):
        """Prints the duration of the scan."""
        print 'Scan took', self.format_time(t)

    def scan_grid(self, axes, size, step, init):
        """Scans a grid, applying a function at each position."""
        self.abort_requested = False
        scan_axes = self.init_grid(axes, size, step, init)
        self.open_scan()
        # get the indices of points along each of the scan axes for use with snaking over array
        pnts = [range(axis.size) for axis in scan_axes]

        self.indices = (-1,) * len(axes)
        self._index = 0
        self._step_times = np.zeros(self.grid_shape)
        self._step_times.fill(np.nan)
        self.status = 'acquiring data'
        scan_start_time = time()
        for k in pnts[-1]:  # outer most axis
            if self.abort_requested:
                break
            #self.grid_scanner.update_drift_compensation()
            self.status = 'Scanning layer {0:d}/{1:d}'.format(k + 1, len(pnts[-1]))
            self.move(scan_axes[-1][k], axes[-1])
            pnts[-2] = pnts[-2][::-1]  # reverse which way is iterated over each time
            for j in pnts[-2]:
                if self.abort_requested:
                    break
                self.move(scan_axes[-2][j], axes[-2])
                if len(axes) == 3:  # for 3d grid (volume) scans
                    pnts[-3] = pnts[-3][::-1]  # reverse which way is iterated over each time
                    for i in pnts[-3]:
                        if self.abort_requested:
                            break
                        self.move(scan_axes[-3][i], axes[-3])
                        self.indices = (i, j, k)
                        self._timed_scan_function(i, j, k)
                        self._index += 1
                elif len(axes) == 2:  # for regular 2d grid scans ignore third axis i
                    self.indices = (j, k)
                    self._timed_scan_function(j, k)
                    self._index += 1

        self.print_scan_time(time() - scan_start_time)
        # move back to initial positions
        for i in range(len(axes)):
            self.move(init[i], axes[i])
        # finish the scan
        self.analyse_scan()
        self.close_scan()
        self.status = 'scan complete'

    def update_gui(self, rate=0.2):
        # wait for thread to start acquiring
        while not self.acquisition_thread.is_alive():
            sleep(rate)
        # once acquiring update gui
        while self.acquisition_thread.is_alive():
            self.update()
            sleep(rate)
        self.update()
        print 'gui update stopped'

    def update(self):
        print 'update'

    def get_qt_ui(self):
        return GridScannerUI(self)

    ### GUI ###

    def _acquire_button_fired(self):
        self.start()

    def _abort_button_fired(self):
        self.abort()

    def _size_unit_changed(self, name, old, new):
        self.size *= self._unit_conversion[old] / self._unit_conversion[new]

    def _step_unit_changed(self, name, old, new):
        self.step *= self._unit_conversion[old] / self._unit_conversion[new]

    def _init_unit_changed(self, name, old, new):
        self.init *= self._unit_conversion[old] / self._unit_conversion[new]

    def _button_fired(self, name):
        print name

    def _increase_size_fired(self):
        self.size *= 2

    def _decrease_size_fired(self):
        self.size /= 2

    def _increase_step_fired(self):
        self.step *= 2

    def _decrease_step_fired(self):
        self.step /= 2

    def vary_axes(self, name, multiplier=2.):
        if 'increase_size' in name:
            self.size *= multiplier
        elif 'decrease_size' in name:
            self.size /= multiplier
        elif 'increase_step' in name:
            self.step *= multiplier
        elif 'decrease_step' in name:
            self.step /= multiplier
        print self.size, self.step

    def set_init_to_current_position(self):
        for i, ax in enumerate(self.axes):
            self.init[i] = self.scanner.get_position(ax)*self.stage_units / self._unit_conversion[self.init_unit]
        self.init = self.init

    def _update_grid_button_fired(self):
        """
        Initialises the grid with the current parameters. This is mainly
        used to check what size grid is being used if size/speed is
        important to the scan.
        """
        self.init_current_grid()


class GridScannerTraits(GridScanner, HasTraits):

    num_axes = Int(3)
    axes = List()
    size = Array(np.float64, shape=(None,), comparison_mode=NO_COMPARE)
    step = Array(np.float64, shape=(None,), comparison_mode=NO_COMPARE)
    init = Array(np.float64, shape=(None,), comparison_mode=NO_COMPARE)
    size_unit = Enum('um', 'nm', 'mm')
    step_unit = Enum('um', 'nm', 'mm')
    init_unit = Enum('um', 'nm', 'mm')
    grid_shape = Tuple
    total_points = Int
    update_grid_button = Button('Update Grid')
    scanner = Instance(Stage)
    indices = Tuple
    status = String
    acquiring = Bool(False)

    increase_size = Button()
    decrease_size = Button()
    increase_step = Button()
    decrease_step = Button()

    update_grid_button = Button('Update Grid')
    acquire_button = Button('Scan Grid')
    abort_button = Button('Abort Scan')
    estimated_time_remaining = String()

    stage_units = Float(1)

    traits_view = View(VGroup(HGroup(Item('num_axes', width=-30), spring),
                              HGroup(Item('axes', width=-80),
                                     Item('size', width=-50),
                                     Item('size_unit', show_label=False),
                                     VGroup(Item('increase_size', **button_params),
                                                                Item('decrease_size', **button_params)),
                                     Item('step', width=-50),
                                     Item('step_unit', show_label=False),
                                     VGroup(Item('increase_step', **button_params),
                                                                Item('decrease_step', **button_params)),
                                     Item('init', width=-50),'init_unit'),
                              HGroup(Item('grid_shape', style='readonly'), Item('total_points', style='readonly'),
                                     Item('update_grid_button', **button_params), Item('acquire_button', **button_params), Item('abort_button', **button_params))
                              )
                       )

    # traits_view = View(
    #     Group(
    #     HGroup(Item('num_axes', width=-30),
    #            Item('axes', width=-100),
    #            label='Axes', **group_params),
    #     HGroup(Item('size', width=-35),
    #            Item('size_unit', width=-40, show_label=False),
    #            VGroup(Item('increase_size', width=-10, show_label=False),
    #                   Item('decrease_size', width=-10, show_label=False), ),
    #            Item('step', width=-35),
    #            Item('step_unit', width=-40, show_label=False),
    #            VGroup(Item('increase_step', width=-10, show_label=False),
    #                   Item('decrease_step', width=-10, show_label=False), ),
    #            Item('init', width=-50),
    #            label='Scan Parameters', **group_params),
    #     HGroup(Item('grid_shape', style='readonly'),
    #            Item('update_grid_button', show_label=False),
    #            **group_params),
    #     HGroup(Item('_status', label='Status', style='readonly')),
    #     springy=False,),
    #     VGroup(VGroup(Item('estimated_time_remaining', style='readonly'),
    #                   HGroup(Item('acquire_button', show_label=False),
    #                          Item('abort_button', show_label=False)),),
    #            spring),
    #     width=700, height=400, resizable=True, title="Grid Scan")

    def __init__(self):
        super(GridScannerTraits, self).__init__()
        self.on_trait_change(self._update_axes, 'num_axes')
        self.on_trait_change(self._button_fired, ['increase_size', 'decrease_size'])


class GridScannerQT(GridScanner, QtCore.QObject):
    axes_updated = QtCore.pyqtSignal(list)
    size_updated = QtCore.pyqtSignal(np.ndarray)
    step_updated = QtCore.pyqtSignal(np.ndarray)
    init_updated = QtCore.pyqtSignal(np.ndarray)
    grid_shape_updated = QtCore.pyqtSignal(tuple)
    total_points_updated = QtCore.pyqtSignal(int)
    status_updated = QtCore.pyqtSignal(str)
    timing_updated = QtCore.pyqtSignal(str)

    def __init__(self):
        super(GridScannerQT, self).__init__()

    def _update_axes(self):
        """
        This is called to emit a signal when the axes list is changed and update all dependencies.
        :return:
        """
        super(GridScannerQT, self)._update_axes()
        self.axes_updated.emit(self.axes)

    def init_grid(self, axes, size, step, init):
        scan_axes = super(GridScannerQT, self).init_grid(axes, size, step, init)
        self.grid_shape_updated.emit(self.grid_shape)
        self.total_points_updated.emit(self.total_points)
        return scan_axes

    def update_gui(self, rate=0.2):
        # wait for thread to start acquiring
        while not self.acquisition_thread.is_alive():
            sleep(rate)
        # once acquiring update gui
        while self.acquisition_thread.is_alive():
            self.update()
            self.timing_updated.emit(self.get_formatted_estimated_time_remaining())
            self.status_updated.emit('')
            sleep(rate)
        self.timing_updated.emit(self.get_formatted_estimated_time_remaining())
        self.status_updated.emit('')
        self.update()
        print 'gui update stopped'

    def rescale_parameter(self, param, value):
        """
        Rescales the list or array-type axes grid parameters and emits the new values
        to update the variables in the grid scanner.
        """
        super(GridScannerQT, self).rescale_parameter(param, value)
        a = getattr(self, param)
        updater = getattr(self, '%s_updated' % param)
        updater.emit(a)

    def vary_axes(self, name, multiplier=2.):
        """

        :param name:
        :param multiplier:
        :return:
        """
        param = name.split('_',1)[1]
        super(GridScannerQT, self).vary_axes(name, multiplier=2.)
        getattr(self, '%s_updated' % param).emit(getattr(self, param))


class GridScannerUI(QtGui.QWidget):
    def __init__(self, grid_scanner):
        assert isinstance(grid_scanner, GridScanner), "A valid GridScanner subclass must be supplied"
        super(GridScannerUI, self).__init__()
        self.grid_scanner = grid_scanner
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle(self.grid_scanner.__class__.__name__)
        # axes selection
        axes_layout = QtGui.QHBoxLayout()

        ## Number of axes ##
        col1 = QtGui.QVBoxLayout()
        num_axes_label = QtGui.QLabel('Num. Axes:')
        self.num_axes = QtGui.QLineEdit(str(self.grid_scanner.num_axes), self)
        s = num_axes_label.sizeHint()
        s.setHeight(80)
        self.num_axes.setMaximumSize(s)
        self.num_axes.setValidator(QtGui.QIntValidator())
        #self.num_axes.returnPressed.connect(partial(setattr, self.grid_scanner, 'num_axes'))
        self.num_axes.returnPressed.connect(self.renew_axes_ui)
        for widget in [num_axes_label, self.num_axes]:
            widget.resize(widget.sizeHint())
        col1.addWidget(num_axes_label)
        col1.addWidget(self.num_axes)
        col1.addStretch()

        ## Axes List ##
        col2 = QtGui.QHBoxLayout()
        # the axes
        self.axes, self.size, self.step, self.init = (QtGui.QListView(self), QtGui.QListView(self), QtGui.QListView(self), QtGui.QListView(self))
        for widget, list, param in zip([self.axes, self.size, self.step, self.init],
                                       [self.grid_scanner.axes, self.grid_scanner.size, self.grid_scanner.step, self.grid_scanner.init],
                                       ['axes', 'size', 'step', 'init']):
            model = QtGui.QStringListModel([str(x) for x in list])
            dtype = str if param == 'axes' else float
            convert = False if param == 'axes' else True
            model.dataChanged.connect(partial(self.set_param, param, dtype=dtype, convert=convert))
            widget.setModel(model)
        self.grid_scanner.axes_updated.connect(partial(self.update_param, 'axes'))
        self.grid_scanner.size_updated.connect(partial(self.update_param, 'size'))
        self.grid_scanner.step_updated.connect(partial(self.update_param, 'step'))
        self.grid_scanner.init_updated.connect(partial(self.update_param, 'init'))

        ## Size, step and init lists ##
        #self.size, step, init = (QtGui.QTableWidget(self.grid_scanner.num_axes, 1, self),)*3
        #widgets = ()
        #for a in (self.grid_scanner.size, self.grid_scanner.step, self.grid_scanner.init):
        #    w = QtGui.QListWidget(self)
        #    w.addItems([str(i) for i in a])
        #    widgets += (w,)
        #self.size, self.step, self.init = widgets
        for widget in [self.axes, self.size, self.step, self.init]:
            #widget.resizeColumnsToContents()
            #widget.resizeRowsToContents()
            widget.setMaximumSize(QtCore.QSize(40,70))
            #if widget == self.size:
            #    widget.itemChanged.connect(partial(setattr, self.grid_scanner, 'size'))
            #elif widget == self.axes:
            #    widget.dataChanged(0,0).connect

        ## Unit enums ##
        size_unit, step_unit, init_unit = (QtGui.QComboBox(), QtGui.QComboBox(), QtGui.QComboBox())
        for widget, param in zip([size_unit, step_unit, init_unit], ['size_unit', 'step_unit', 'init_unit']):
            widget.addItems(['nm', 'um', 'mm'])
            widget.activated[str].connect(partial(setattr, self.grid_scanner, param))
            widget.setCurrentIndex(1)
            widget.setMaximumWidth(60)

        ## Grid scaling ##
        increase_size_button = QtGui.QPushButton('', self)
        decrease_size_button = QtGui.QPushButton('', self)
        increase_step_button = QtGui.QPushButton('', self)
        decrease_step_button = QtGui.QPushButton('', self)
        for button, direction, method in zip([increase_size_button, decrease_size_button,
                                              increase_step_button, decrease_step_button],
                                             ['up', 'down', 'up', 'down'],
                                             ['increase_size', 'decrease_size', 'increase_step', 'decrease_step']):
            button.setIcon(QtGui.QIcon('../ui/%s.png'%direction))
            button.setIconSize(QtCore.QSize(10,10))
            #button.resize(QtCore.QSize(20,6))#(button.sizeHint())
            button.clicked.connect(partial(self.grid_scanner.vary_axes, method, 2.))
        set_init_to_current_button = QtGui.QPushButton('Set Init\nto Current', self)
        set_init_to_current_button.setStyleSheet('font-size: 11pt')

        ## Overall axes control layouts ##
        axes_label, size_label, step_label, init_label = (QtGui.QLabel('Axes', self), QtGui.QLabel('Size', self),
                                                          QtGui.QLabel('Step', self), QtGui.QLabel('Init.', self))
        for label in [axes_label, size_label, step_label, init_label]:
            label.setStyleSheet('font-size: 11pt')

        for widget in [axes_label, self.axes,
                       size_label, self.size, size_unit, increase_size_button, decrease_size_button,
                       step_label, self.step, step_unit, increase_step_button, decrease_step_button,
                       init_label, self.init, init_unit, set_init_to_current_button]:
            widget.resize(widget.sizeHint())
            if widget in [axes_label, size_label, step_label, init_label,
                          size_unit, step_unit, init_unit]:
                l = QtGui.QVBoxLayout()
                l.addWidget(widget)
                col2.addLayout(l)
            elif widget in [self.axes, self.size, self.step, self.init,
                            increase_size_button, decrease_size_button,
                            increase_step_button, decrease_step_button,
                            set_init_to_current_button]:
                l.addWidget(widget)
            else:
                col2.addWidget(widget)
        col2.addStretch()
        col2.setSpacing(0)
        col2.setContentsMargins(0,0,0,0)

        ## Estimations and scanning buttons ##
        button_layout = QtGui.QHBoxLayout()

        grid_shape_label = QtGui.QLabel('Grid Shape:')
        total_points_label = QtGui.QLabel('Total Points:')
        estimated_time_label = QtGui.QLabel('Estimated Scan Time:')
        self.grid_shape_view = QtGui.QLineEdit(self)
        self.grid_scanner.grid_shape_updated.connect(self.update_grid)
        self.total_points_view = QtGui.QLineEdit(self)
        self.estimated_time_view = QtGui.QLineEdit(self)
        for view, label in zip([self.grid_shape_view, self.total_points_view, self.estimated_time_view],
                               [grid_shape_label, total_points_label, estimated_time_label]):
            view.resize(self.grid_shape_view.sizeHint())
            view.setMaximumWidth(100)
            view.setReadOnly(True)
            view.setStyleSheet('font-size: 11pt')
            label.resize(label.sizeHint())
            label.setStyleSheet('font-size: 11pt')
            l = QtGui.QVBoxLayout()
            l.addWidget(label)
            l.addWidget(view)
            button_layout.addLayout(l)

        update_button = QtGui.QPushButton('Update', self)
        start_button = QtGui.QPushButton('Start', self)
        abort_button = QtGui.QPushButton('Abort', self)
        for button, method, tool_tip in zip([update_button, start_button, abort_button],
                                            [self.grid_scanner.init_current_grid, self.grid_scanner.start, self.grid_scanner.abort],
                                            ['Update the current grid', 'Start a scan', 'Abort the current scan']):
            button.resize(button.sizeHint())
            button.setStyleSheet('font-size: 11pt')
            button.clicked.connect(method)
            button.setToolTip(tool_tip)
            button_layout.addWidget(button)
        button_layout.addStretch()
        button_layout.setSizeConstraint(QtGui.QLayout.SetMinimumSize)

        # status and estimated times
        status_layout = QtGui.QHBoxLayout()
        status_label = QtGui.QLabel('Status:')
        timing_label = QtGui.QLabel('Estimated time remaining:')
        self.status = QtGui.QLineEdit(self.grid_scanner.status, self)
        self.timing = QtGui.QLineEdit(self)
        for widget in [status_label, self.status, timing_label, self.timing]:
            widget.setStyleSheet('font-size: 11pt')
            widget.resize(widget.sizeHint())
            if widget in [self.status, self.timing]:
                widget.setReadOnly(True)
            status_layout.addWidget(widget)
        self.grid_scanner.status_updated.connect(self.update_status)
        self.grid_scanner.timing_updated.connect(self.update_timing)

        axes_layout.addLayout(col1)
        axes_layout.addLayout(col2)
        axes_layout.addStretch()
        axes_layout.setSizeConstraint(QtGui.QLayout.SetMinimumSize)

        control_group = QtGui.QGroupBox()
        control_group.setTitle('Grid Scanner Controls')
        l = QtGui.QVBoxLayout()
        l.addLayout(axes_layout)
        l.addLayout(button_layout)
        control_group.setLayout(l)
        control_group.setContentsMargins(0,10,0,0)

        # overall layout
        for layout in [axes_layout, button_layout, status_layout]:
            layout.setContentsMargins(0,0,0,0)
        self.layout = QtGui.QVBoxLayout()
        self.layout.addWidget(control_group)
        self.layout.addLayout(status_layout)
        self.layout.setSpacing(5)
        self.layout.setContentsMargins(5,5,5,5)
        self.layout.setSizeConstraint(QtGui.QLayout.SetMinimumSize)
        self.setLayout(self.layout)

    def update_axes(self):
        print self.axes.model().stringList(), self.grid_scanner.axes,\
            self.size.model().stringList(), self.grid_scanner.size

    def update_grid(self):
        self.grid_shape_view.setText(str(self.grid_scanner.grid_shape))
        self.grid_shape_view.resize(self.grid_shape_view.sizeHint())
        self.total_points_view.setText(str(self.grid_scanner.total_points))
        self.total_points_view.resize(self.total_points_view.sizeHint())
        self.estimated_time_view.setText(str(self.grid_scanner.estimate_scan_duration()))
        self.estimated_time_view.resize(self.estimated_time_view.sizeHint())

    def update_status(self):
        self.status.setText(self.grid_scanner.status)

    def update_timing(self, time):
        self.timing.setText(time)

    def set_param(self, param, dtype=float, convert=True):
        """
        Apply changes made in the UI lists to the underlying GridScanner.
        """
        uia = getattr(self, param)
        a = [dtype(x) for x in uia.model().stringList()]
        if convert:
            a = np.array(a)
        setattr(self.grid_scanner, param, a)

    def update_param(self, param):
        """Update the UI list with changes from the underlying GridScanner."""
        gsa = getattr(self.grid_scanner, param)
        uia = getattr(self, param)
        uia.model().setStringList([str(x) for x in gsa])

    def renew_axes_ui(self):
        n = int(self.num_axes.text())
        self.grid_scanner.num_axes = n
        for param in ['axes', 'size', 'step', 'init']:
            self.update_param(param)
        #for widget, list in zip([self.axes, self.size, self.step, self.init],
        #                        [self.grid_scanner.axes, self.grid_scanner.size,
        #                         self.grid_scanner.step, self.grid_scanner.init]):
            #widget.model().setData alternative use
        #    widget.model().setStringList([str(x) for x in list])
        #self.axes.setColumnCount(n)
        #for i in range(4):
        #    for j in range(n):
        #        self.axes.setItem(i,j,QtGui.QTableWidgetItem(str(0)))
        #self.axes.resizeColumnsToContents()
        #self.axes.resizeRowsToContents()


if __name__ == '__main__':
    import sys
    from nplab.instrument.stage import DummyStage
    from nplab.utils.gui import *
    import matplotlib
    matplotlib.use('Qt4Agg')
    from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure

    test = 'qt'
    if test == 'traits':
        template = GridScannerTraits
    elif test == 'qt':
        template = GridScannerQT
    else:
        template = GridScanner

    class DummyGridScanner(template):
        def __init__(self):
            super(DummyGridScanner, self).__init__()
            self.estimated_step_time = 0.001
            self.fig = Figure()
            self.ax = self.fig.add_subplot(111)
            self.ax.set_aspect('equal')
            self.data = None
        def open_scan(self):
            self.data = np.zeros(self.grid_shape, dtype=np.float64)
            self.data.fill(np.nan)
            self.ax.clear()
            mult = 1./self._unit_conversion[self.size_unit]
            x, y = (mult*self.scan_axes[0], mult*self.scan_axes[1])
            self.ax.set_xlim(x.min(), x.max())
            self.ax.set_ylim(y.min(), y.max())
        def scan_function(self, *indices):
            sleep(0.001)
            x,y = (self.scan_axes[0][indices[0]], self.scan_axes[1][indices[1]])
            f = 2*np.pi*2e6
            self.data[indices] = np.sin(f*x) * np.cos(f*y)
        def close_scan(self):
            print self.data.min(), self.data.max()
        def update(self):
            if self.data is None or self.fig.canvas is None:
                print 'no canvas or data'
                return
            if not self.ax.collections:
                mult = 1./self._unit_conversion[self.size_unit]
                self.ax.pcolormesh(mult*self.scan_axes[-2], mult*self.scan_axes[-1], self.data.transpose())
                cid = self.fig.canvas.mpl_connect('button_press_event', self.onclick)
                cid = self.fig.canvas.mpl_connect('pick_event', self.onpick4)
            else:
                img, = self.ax.collections
                img.set_array(self.data.transpose()[:-1,:-1].ravel())
                try:
                    img_min = self.data[np.isfinite(self.data)].min()
                    img_max = self.data[np.isfinite(self.data)].max()
                except ValueError:
                    print 'There may have been a NaN error'
                    img_min=0
                    img_max=1
                img.set_clim(img_min, img_max)
                #self.ax.relim()
                #self.ax.autoscale_view()
            self.fig.canvas.draw()
        def get_qt_ui(self):
            return DummyGridScannerUI(self)
        def start(self, rate=0.2):
            super(DummyGridScanner, self).start(rate)
        def onclick(self, event):
            print 'button=%d, x=%d, y=%d, xdata=%f, ydata=%f'%(
            event.button, event.x, event.y, event.xdata, event.ydata)
            init_scale = self._unit_conversion[self.size_unit] / self._unit_conversion[self.init_unit]
            self.init[:2] = (event.xdata * init_scale, event.ydata * init_scale)
            self.init_updated.emit(self.init)
        def onpick4(self, event):
            artist = event.artist
            if isinstance(artist, matplotlib.image.AxesImage):
                im = artist
                A = im.get_array()
                print('onpick4 image', A.shape)

    class DummyGridScannerUI(GridScannerUI):
        def __init__(self, grid_scanner):
            super(DummyGridScannerUI, self).__init__(grid_scanner)
            self.canvas = FigureCanvas(self.grid_scanner.fig)
            self.layout.addWidget(self.canvas)

    gs = DummyGridScanner()
    gs.scanner = DummyStage()

    #gs.num_axes = 3
    #gs.num_axes = 4
    #gs.num_axes = 2
    #gs.num_axes = 1
    #gs.num_axes = 3

    if test=='traits':
        gs.configure_traits()
    elif test == 'qt':
        gui = gs.get_qt_ui()
        #gs.num_axes = 3
        app = get_qt_app()
        gui.show()
        sys.exit(app.exec_())
    else:
        print gs.size_unit, gs.size
        print gs._unit_conversion['um'] / gs._unit_conversion['nm']
        gs.size_unit = 'nm'
        print gs.size_unit, gs.size

        gs.start()

