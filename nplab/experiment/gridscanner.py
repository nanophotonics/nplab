"""
Experiment classes for grid scanning experiments. The main classes are GridScanner,
AcquisitionThread and GridScanController. The AcquisitionThread takes the GridScanner,
which defines the scan, and runs its methods in a thread as called by the GridScanController,
which controls the overall experiment.
"""

__author__ = 'alansanders'

import os
import h5py
import numpy as np
import threading
from threading import Thread, RLock, Event
from time import sleep, time
import operator
from nplab.instrument.stage import Stage
from functools import partial
from nplab.utils.gui import *
from PyQt4 import uic
from nplab.ui.ui_tools import UiTools


group_params = {'show_border': True, 'springy': False}
button_params = dict(show_label=False)


class GridScanner(object):
    """

    """

    def __init__(self):
        super(GridScanner, self).__init__()
        self.scanner = Stage()
        self.stage_units = 1
        self.axes = list(self.scanner.axis_names[:2])
        self.axes_names = list(str(ax) for ax in self.scanner.axis_names[:2])
        self.size = np.array([1., 1.], dtype=np.float64)
        self.step = np.array([0.05, 0.05], dtype=np.float64)
        self.init = np.array([0., 0.], dtype=np.float64)
        self.num_axes = 2
        self.scan_axes = None
        self._unit_conversion = {'nm': 1e-9, 'um': 1e-6, 'mm': 1e-3}
        self.size_unit, self.step_unit, self.init_unit = ('um', 'um', 'um')
        self.init_grid(self.axes, self.size, self.step, self.init)
        self.status = 'inactive'
        self.acquiring = Event()

        self.abort_requested = False

        self.estimated_step_time = 0.001

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
        """
        Updates all axes related objects (and sequence lengths) when the number of axes is changed.
        :return:
        """
        current_axes = self.axes
        current_axes_names = self.axes_names
        # numpy arrays must be explicitly copied
        current_size, current_step, current_init = (self.size.copy(), self.step.copy(), self.init.copy())
        if self.num_axes > len(current_axes):
            self.axes = ['']*self.num_axes
            self.axes_names = ['']*self.num_axes
            self.size, self.step, self.init = (np.zeros(self.num_axes), np.zeros(self.num_axes), np.zeros(self.num_axes))
            self.axes[:len(current_axes)] = current_axes
            self.axes_names[:len(current_axes)] = current_axes_names
            self.size[:len(current_axes)] = current_size
            self.step[:len(current_axes)] = current_step
            self.init[:len(current_axes)] = current_init
        else:
            self.axes = current_axes[:self.num_axes]
            self.axes_names = current_axes_names[:self.num_axes]
            self.size = current_size[:self.num_axes]
            self.step = current_step[:self.num_axes]
            self.init = current_init[:self.num_axes]
        #print self.num_axes, self.axes, self.size

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
        self.acquiring.wait()
        self.display_thread.start()

    def abort(self):
        """Requests an abort of the currently running grid scan."""
        if not hasattr(self, 'acquisition_thread'):
            return
        if self.acquisition_thread.is_alive():
            print 'aborting'
            self.abort_requested = True
            self.acquisition_thread.join()

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
        self.scanner.move(position/self.stage_units, axis=axis)

    def get_position(self, axis):
        return self.scanner.get_position(axis=axis)*self.stage_units

    def open_scan(self):
        pass

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
        pass

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
        self.acquiring.set()
        scan_start_time = time()
        for k in pnts[-1]:  # outer most axis
            if self.abort_requested:
                break
            self.update_drift_compensation()
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
        self.acquiring.clear()
        # move back to initial positions
        for i in range(len(axes)):
            self.move(init[i], axes[i])
        # finish the scan
        self.analyse_scan()
        self.close_scan()
        self.status = 'scan complete'

    def update_gui(self, rate=0.2):
        while self.acquisition_thread.is_alive():
            self.update()
            sleep(rate)
        self.update()

    def vary_axes(self, name, multiplier=2.):
        if 'increase_size' in name:
            self.size *= multiplier
        elif 'decrease_size' in name:
            self.size /= multiplier
        elif 'increase_step' in name:
            self.step *= multiplier
        elif 'decrease_step' in name:
            self.step /= multiplier

    def set_init_to_current_position(self):
        for i, ax in enumerate(self.axes):
            self.init[i] = self.scanner.get_position(ax)*self.stage_units / self._unit_conversion[self.init_unit]
        self.init = self.init


class GridScannerQT(GridScanner, QtCore.QObject):
    """
    A GridScanner subclass containing additional or redefined functions related to GUI operation.
    """

    axes_updated = QtCore.pyqtSignal(list)
    axes_names_updated = QtCore.pyqtSignal(list)
    size_updated = QtCore.pyqtSignal(np.ndarray)
    step_updated = QtCore.pyqtSignal(np.ndarray)
    init_updated = QtCore.pyqtSignal(np.ndarray)
    grid_shape_updated = QtCore.pyqtSignal(tuple)
    total_points_updated = QtCore.pyqtSignal(int)
    status_updated = QtCore.pyqtSignal(str)
    timing_updated = QtCore.pyqtSignal(str)

    def __init__(self):
        super(GridScannerQT, self).__init__()

    def get_qt_ui(self):
        return GridScannerUI(self)

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
        while self.acquisition_thread.is_alive():
            self.update()
            self.timing_updated.emit(self.get_formatted_estimated_time_remaining())
            self.status_updated.emit('')
            sleep(rate)
        self.timing_updated.emit(self.get_formatted_estimated_time_remaining())
        self.status_updated.emit('')
        self.update()

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

#base, widget = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'gridscanner.ui'), from_imports=False)

#class GridScannerUI(UiTools, base, widget):
class GridScannerUI(QtGui.QWidget, UiTools):
    def __init__(self, grid_scanner):
        assert isinstance(grid_scanner, GridScannerQT), "A valid GridScannerQT subclass must be supplied"
        super(GridScannerUI, self).__init__()
        self.grid_scanner = grid_scanner
        #self.setupUi(self)
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'gridscanner.ui'), self)

        self.setWindowTitle(self.grid_scanner.__class__.__name__)

        self.num_axes.setValidator(QtGui.QIntValidator())
        self.num_axes.textChanged.connect(self.check_state)
        self.num_axes.returnPressed.connect(self.renew_axes_ui)

        # setting the lists in the GUI list views
        # note that axes are always set as string so if a stage requires an integer as an
        # axis identifier then it must be wrapped in an int() in the move function
        for widget, list, param in zip([self.axes_view, self.axes_names_view, self.size_view, self.step_view, self.init_view],
                                       [self.grid_scanner.axes, self.grid_scanner.axes_names, self.grid_scanner.size, self.grid_scanner.step, self.grid_scanner.init],
                                       ['axes', 'axes_names', 'size', 'step', 'init']):
            model = QtGui.QStringListModel([str(x) for x in list])
            dtype = str if param in ['axes', 'axes_names'] else float
            convert = False if param in ['axes', 'axes_names'] else True
            model.dataChanged.connect(partial(self.set_param, param, dtype=dtype, convert=convert))
            widget.setModel(model)

        self.grid_scanner.axes_updated.connect(partial(self.update_param, 'axes'))
        self.grid_scanner.axes_names_updated.connect(partial(self.update_param, 'axes_names'))
        self.grid_scanner.size_updated.connect(partial(self.update_param, 'size'))
        self.grid_scanner.step_updated.connect(partial(self.update_param, 'step'))
        self.grid_scanner.init_updated.connect(partial(self.update_param, 'init'))

        self.size_unit.activated[str].connect(partial(setattr, self.grid_scanner, 'size_unit'))
        self.step_unit.activated[str].connect(partial(setattr, self.grid_scanner, 'step_unit'))
        self.init_unit.activated[str].connect(partial(setattr, self.grid_scanner, 'init_unit'))

        self.size_up.clicked.connect(partial(self.grid_scanner.vary_axes, 'increase_size', 2.))
        self.size_down.clicked.connect(partial(self.grid_scanner.vary_axes, 'decrease_size', 2.))
        self.step_up.clicked.connect(partial(self.grid_scanner.vary_axes, 'increase_step', 2.))
        self.step_down.clicked.connect(partial(self.grid_scanner.vary_axes, 'decrease_step', 2.))

        self.grid_scanner.grid_shape_updated.connect(self.update_grid)
        self.update_button.clicked.connect(self.grid_scanner.init_current_grid)
        self.start_button.clicked.connect(self.grid_scanner.start)
        self.abort_button.clicked.connect(self.grid_scanner.abort)
        self.grid_scanner.status_updated.connect(self.update_status)
        self.grid_scanner.timing_updated.connect(self.update_timing)

        self.num_axes.setText(str(self.grid_scanner.num_axes))
        self.status.setText(self.grid_scanner.status)

    def update_axes(self):
        print self.axes_view.model().stringList(), self.grid_scanner.axes,\
            self.size_view.model().stringList(), self.grid_scanner.size

    def update_grid(self):
        self.gridshape.setText(str(self.grid_scanner.grid_shape))
        self.gridshape.resize(self.gridshape.sizeHint())
        self.total_points.setText(str(self.grid_scanner.total_points))
        self.total_points.resize(self.total_points.sizeHint())
        self.est_scan_time.setText(str(self.grid_scanner.estimate_scan_duration()))
        self.est_scan_time.resize(self.est_scan_time.sizeHint())

    def update_status(self):
        self.status.setText(self.grid_scanner.status)

    def update_timing(self, time):
        self.est_time_remain.setText(time)

    def set_param(self, param, dtype=float, convert=True):
        """
        Apply changes made in the UI lists to the underlying GridScanner.
        """
        uia = getattr(self, param+'_view')
        a = [dtype(x) for x in uia.model().stringList()]
        if convert:
            a = np.array(a)
        setattr(self.grid_scanner, param, a)

    def update_param(self, param):
        """Update the UI list with changes from the underlying GridScanner."""
        gsa = getattr(self.grid_scanner, param)
        uia = getattr(self, param+'_view')
        uia.model().setStringList([str(x) for x in gsa])

    def renew_axes_ui(self):
        n = int(self.num_axes.text())
        self.grid_scanner.num_axes = n
        for param in ['axes', 'axes_names', 'size', 'step', 'init']:
            self.update_param(param)


if __name__ == '__main__':
    import sys
    from nplab.instrument.stage import DummyStage
    from nplab.utils.gui import *
    import matplotlib
    matplotlib.use('Qt4Agg')
    from nplab.ui.mpl_gui import FigureCanvasWithDeferredDraw as FigureCanvas
    from matplotlib.figure import Figure

    test = 'qt'
    if test == 'qt':
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
            self.lock = RLock()
        def open_scan(self):
            self.fig.clear()
            #with self.lock:
            self.data = np.zeros(self.grid_shape, dtype=np.float64)
            self.data.fill(np.nan)
            self.ax = self.fig.add_subplot(111)
            self.ax.set_aspect('equal')
            mult = 1./self._unit_conversion[self.size_unit]
            x, y = (mult*self.scan_axes[0], mult*self.scan_axes[1])
            self.ax.set_xlim(x.min(), x.max())
            self.ax.set_ylim(y.min(), y.max())
        def scan_function(self, *indices):
            sleep(0.001)
            x,y = (self.scan_axes[0][indices[0]], self.scan_axes[1][indices[1]])
            #with self.lock:
            self.data[indices] = np.sin(2*np.pi*2e6*x) * np.cos(2*np.pi*2e6*y)
        def close_scan(self):
            print self.data.min(), self.data.max()
        def update(self):
            if self.data is None or self.fig.canvas is None:
                print 'no canvas or data'
                return
            #with self.lock:
            #    data = self.data.copy()
            data = self.data
            if not np.any(np.isfinite(self.data)):
                return
            if not self.ax.collections:
                mult = 1./self._unit_conversion[self.size_unit]
                self.ax.pcolormesh(mult*self.scan_axes[-2], mult*self.scan_axes[-1], data.transpose())
                cid = self.fig.canvas.mpl_connect('button_press_event', self.onclick)
                cid = self.fig.canvas.mpl_connect('pick_event', self.onpick4)
            else:
                img, = self.ax.collections
                img.set_array(data.transpose()[:-1,:-1].ravel())
                try:
                    img_min = data[np.isfinite(data)].min()
                    img_max = data[np.isfinite(data)].max()
                except ValueError:
                    print 'There may have been a NaN error'
                    img_min=0
                    img_max=1
                img.set_clim(img_min, img_max)
                self.ax.relim()
                #self.ax.autoscale_view()
            self.fig.canvas.draw()
        def get_qt_ui(self):
            return DummyGridScannerUI(self)
        def start(self, rate=1./10.):
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
            self.canvas.setMaximumSize(300,300)
            self.layout.addWidget(self.canvas)
            self.resize(self.sizeHint())

    gs = DummyGridScanner()
    gs.scanner = DummyStage()
    gs.scanner.axis_names = ('x', 'y', 'z')

    if test == 'qt':
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

