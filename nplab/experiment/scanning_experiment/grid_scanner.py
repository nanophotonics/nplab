"""
Experiment classes for grid scanning experiments. The main classes are GridScanner,
AcquisitionThread and GridScanController. The AcquisitionThread takes the GridScanner,
which defines the scan, and runs its methods in a thread as called by the GridScanController,
which controls the overall experiment.
"""

__author__ = 'alansanders'

import numpy as np
import threading
import time
import operator
from nplab.experiment.scanning_experiment import ScanningExperiment, TimedScan
from nplab.instrument.stage import Stage
from functools import partial
from nplab.utils.gui import *
from nplab.ui.ui_tools import UiTools


class GridScan(ScanningExperiment, TimedScan):
    """

    """

    def __init__(self):
        ScanningExperiment.__init__(self)
        TimedScan.__init__(self)
        self.stage = Stage()
        self.stage_units = 1
        self.axes = list(self.stage.axis_names)
        self.axes_names = list(str(ax) for ax in self.stage.axis_names)
        self.size = 1. * np.ones(len(self.axes), dtype=np.float64)
        self.step = 0.05 * np.ones(len(self.axes), dtype=np.float64)
        self.init = np.zeros(len(self.axes), dtype=np.float64)
        self.scan_axes = None
        # underscored attributes are made into properties
        self._num_axes = len(self.axes)
        self._unit_conversion = {'nm': 1e-9, 'um': 1e-6, 'mm': 1e-3}
        self._size_unit, self._step_unit, self._init_unit = ('um', 'um', 'um')
        self.grid_shape = (0,0)
        #self.init_grid(self.axes, self.size, self.step, self.init)

    def _update_axes(self, num_axes):
        """
        Updates all axes related objects (and sequence lengths) when the number of axes is changed.

        :param num_axes: the new number of axes to scan
        :return:
        """
        self._num_axes = num_axes
        # lists can be reassigned to copy
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

    def rescale_parameter(self, param, value):
        """
        Rescales the parameter (size, step or init) if its units are changed.

        :param param:
        :param value:
        :return:
        """
        assert value in self._unit_conversion.keys(), 'a valid unit must be supplied'
        unit_param = '_%s_unit' % param
        old_value = getattr(self, unit_param) if hasattr(self, unit_param) else value
        setattr(self, unit_param, value)
        a = getattr(self, param)
        a *= self._unit_conversion[old_value] / self._unit_conversion[value]

    num_axes = property(fget=lambda self: getattr(self, '_num_axes'), fset=_update_axes)
    size_unit = property(fget=lambda self: getattr(self, '_size_unit'), fset=partial(rescale_parameter, param='size'))
    step_unit = property(fget=lambda self: getattr(self, '_step_unit'), fset=partial(rescale_parameter, param='step'))
    init_unit = property(fget=lambda self: getattr(self, '_init_unit'), fset=partial(rescale_parameter, param='init'))

    def run(self):
        """
        Starts the grid scan in its own thread and runs the update function at the specified
        rate whilst acquiring the data.

        :param rate: the update period in seconds
        :return:
        """
        if isinstance(self.acquisition_thread, threading.Thread) and self.acquisition_thread.is_alive():
            print 'scan already running'
            return
        self.init_scan()
        self.acquisition_thread = threading.Thread(target=self.scan,
                                                   args=(self.axes, self.size, self.step, self.init))
        self.acquisition_thread.start()

    def init_grid(self, axes, size, step, init):
        """Create a grid on which to scan."""
        scan_axes = []
        for i in range(len(axes)):
            s = size[i] * self._unit_conversion[self.size_unit]
            st = step[i] * self._unit_conversion[self.step_unit]
            s0 = init[i] * self._unit_conversion[self.init_unit]
            ax = np.arange(0, s+st/2., st) - s/2. + s0
            scan_axes.append(ax)
        scan_axes = scan_axes[::-1]
        self.grid_shape = tuple(ax.size for ax in scan_axes)
        self.total_points = reduce(operator.mul, self.grid_shape, 1)
        self.scan_axes = scan_axes
        return scan_axes

    def init_current_grid(self):
        """Convenience method that initialises a grid based on current parameters."""
        self.init_grid(self.axes, self.size, self.step, self.init)

    def set_stage(self, stage, axes=None):
        """
        Sets the stage and move methods.

        :param axes: sequence of axes
        """
        assert isinstance(stage, Stage), "stage must be an instance of Stage."
        self.stage = stage
        #self.move = self.stage.move
        if axes is None:
            self.axes = list(self.stage.axis_names[:self.num_axes])
        else:
            for ax in axes:
                if ax not in self.stage.axis_names:
                    raise ValueError('one of the supplied axes are invalid (not found in the stage axis names)')
            self.num_axes = len(axes)
            self.axes = list(axes)
        self.set_init_to_current_position()

    def move(self, position, axis):
        """Move to a position along a given axis."""
        self.stage.move(position/self.stage_units, axis=axis)

    def get_position(self, axis):
        return self.stage.get_position(axis=axis)*self.stage_units

    def update_drift_compensation(self):
        """Update the current drift compensation.

        If you have a nice way of compensating for drift, you should use this
        function to do it - it's called each time the outermost scan axis
        updates."""
        pass

    def scan(self, axes, size, step, init):
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
        scan_start_time = time.time()
        for k in pnts[0]:  # outer most axis
            if self.abort_requested:
                break
            self.update_drift_compensation()
            self.status = 'Scanning layer {0:d}/{1:d}'.format(k + 1, len(pnts[0]))
            self.move(scan_axes[0][k], axes[0])
            pnts[1] = pnts[1][::-1]  # reverse which way is iterated over each time
            for j in pnts[1]:
                if self.abort_requested:
                    break
                self.move(scan_axes[1][j], axes[1])
                if len(axes) == 3:  # for 3d grid (volume) scans
                    pnts[2] = pnts[2][::-1]  # reverse which way is iterated over each time
                    for i in pnts[2]:
                        if self.abort_requested:
                            break
                        self.move(scan_axes[2][i], axes[2])
                        self.indices = (k, j, i)
                        self.scan_function(k, j, i)
                        self._index += 1
                elif len(axes) == 2:  # for regular 2d grid scans ignore third axis i
                    self.indices = (k, j)
                    self.scan_function(k, j)
                    self._index += 1

        self.print_scan_time(time.time() - scan_start_time)
        self.acquiring.clear()
        # move back to initial positions
        for i in range(len(axes)):
            self.move(init[i], axes[i])
        # finish the scan
        self.analyse_scan()
        self.close_scan()
        self.status = 'scan complete'

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
            self.init[i] = self.stage.get_position(ax)*self.stage_units / self._unit_conversion[self.init_unit]
        self.init = self.init


class GridScanQT(GridScan, QtCore.QObject):
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
        GridScan.__init__(self)
        QtCore.QObject.__init__(self)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)

    def run(self, rate=0.1):
        super(GridScanQT, self).run()
        self.acquiring.wait()
        self.timer.start(1000*rate)

    def get_qt_ui(self):
        return GridScanUI(self)

    @staticmethod
    def get_qt_ui_cls():
        return GridScanUI

    def _update_axes(self, num_axes):
        """
        This is called to emit a signal when the axes list is changed and update all dependencies.

        :return:
        """
        super(GridScanQT, self)._update_axes(num_axes)
        self.axes_updated.emit(self.axes)

    def init_grid(self, axes, size, step, init):
        scan_axes = super(GridScanQT, self).init_grid(axes, size, step, init)
        self.grid_shape_updated.emit(self.grid_shape)
        self.total_points_updated.emit(self.total_points)
        return scan_axes

    def update(self, force=False):
        """
        This is the function that is called in the event loop and at the end of the scan
        and should be reimplemented when subclassing to deal with data updates and GUIs.
        """
        if not self.acquisition_thread.is_alive():
            self.timer.stop()
        self.timing_updated.emit(self.get_formatted_estimated_time_remaining())
        self.status_updated.emit('')

    def rescale_parameter(self, param, value):
        """
        Rescales the list or array-type axes grid parameters and emits the new values
        to update the variables in the grid scanner.
        """
        super(GridScanQT, self).rescale_parameter(param, value)
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
        super(GridScanQT, self).vary_axes(name, multiplier=2.)
        getattr(self, '%s_updated' % param).emit(getattr(self, param))

    num_axes = property(fget=lambda self: getattr(self, '_num_axes'), fset=_update_axes)
    size_unit = property(fget=lambda self: getattr(self, '_size_unit'), fset=partial(rescale_parameter, param='size'))
    step_unit = property(fget=lambda self: getattr(self, '_step_unit'), fset=partial(rescale_parameter, param='step'))
    init_unit = property(fget=lambda self: getattr(self, '_init_unit'), fset=partial(rescale_parameter, param='init'))

#base, widget = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'gridscanner.ui'), from_imports=False)

#class GridScannerUI(UiTools, base, widget):
class GridScanUI(QtGui.QWidget, UiTools):
    def __init__(self, grid_scanner):
        assert isinstance(grid_scanner, GridScanQT), "A valid GridScannerQT subclass must be supplied"
        super(GridScanUI, self).__init__()
        self.grid_scanner = grid_scanner
        #self.setupUi(self)
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'grid_scanner.ui'), self)

        self.rate = 0.1

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
        self.start_button.clicked.connect(self.on_click)
        self.abort_button.clicked.connect(self.grid_scanner.abort)
        self.grid_scanner.status_updated.connect(self.update_status)
        self.grid_scanner.timing_updated.connect(self.update_timing)

        self.num_axes.setText(str(self.grid_scanner.num_axes))
        self.status.setText(self.grid_scanner.status)

        self.resize(self.sizeHint())

    def on_click(self):
        sender = self.sender()
        if sender == self.start_button:
            self.grid_scanner.run(self.rate)

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
    import matplotlib
    matplotlib.use('Qt4Agg')
    from nplab.ui.mpl_gui import FigureCanvasWithDeferredDraw as FigureCanvas
    from matplotlib.figure import Figure
    import cProfile
    import pstats

    test = 'qt'
    if test == 'qt':
        template = GridScanQT
    else:
        template = GridScan

    class DummyGridScan(template):
        def __init__(self):
            super(DummyGridScan, self).__init__()
            self.estimated_step_time = 0.0005
            self.fig = Figure()
            self.data = None
        def open_scan(self):
            self.fig.clear()
            self.data = np.zeros(self.grid_shape, dtype=np.float64)
            self.data.fill(np.nan)
            self.ax = self.fig.add_subplot(111)
            self.ax.set_aspect('equal')
            mult = 1./self._unit_conversion[self.size_unit]
            x, y = (mult*self.scan_axes[-1], mult*self.scan_axes[-2])
            self.ax.set_xlim(x.min(), x.max())
            self.ax.set_ylim(y.min(), y.max())
        def scan_function(self, *indices):
            time.sleep(0.0005)
            x,y = (self.scan_axes[-1][indices[-1]], self.scan_axes[-2][indices[-2]])
            self.data[indices] = np.sin(2*np.pi*2e6*x) * np.cos(2*np.pi*2e6*y)
            if self.num_axes == 2:
                self.check_for_data_request(self.data)
            elif self.num_axes == 3:
                self.check_for_data_request(self.data[indices[0],:,:])
        #@profile
        #def start(self, rate=0.1):
        #    super(DummyGridScanner, self).start(0.1)
        def run(self, rate=0.1):
            fname = 'profiling.stats'
            cProfile.runctx('super(DummyGridScan, self).run(%.2f)'%rate, globals(), locals(), filename=fname)
            stats = pstats.Stats(fname)
            stats.strip_dirs()
            stats.sort_stats('cumulative')
            stats.print_stats()
        def update(self, force=False):
            super(DummyGridScan, self).update(force)
            if self.data is None or self.fig.canvas is None:
                print 'no canvas or data'
                return
            if force:
                data = (self.data,)
            else:
                data = self.request_data()
            if data is not False:
                data, = data
                if not np.any(np.isfinite(data)):
                    return
                if not self.ax.collections:
                    mult = 1./self._unit_conversion[self.size_unit]
                    self.ax.pcolormesh(mult*self.scan_axes[-1], mult*self.scan_axes[-2], data)
                    cid = self.fig.canvas.mpl_connect('button_press_event', self.onclick)
                    cid = self.fig.canvas.mpl_connect('pick_event', self.onpick4)
                else:
                    img, = self.ax.collections
                    img.set_array(data[:-1,:-1].ravel())
                    try:
                        img_min = data[np.isfinite(data)].min()
                        img_max = data[np.isfinite(data)].max()
                    except ValueError:
                        print 'There may have been a NaN error'
                        img_min=0
                        img_max=1
                    img.set_clim(img_min, img_max)
                    self.ax.relim()
                self.fig.canvas.draw()
        def get_qt_ui(self):
            return DummyGridScanUI(self)
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

    class DummyGridScanUI(GridScanUI):
        def __init__(self, grid_scanner):
            super(DummyGridScanUI, self).__init__(grid_scanner)
            self.canvas = FigureCanvas(self.grid_scanner.fig)
            self.canvas.setMaximumSize(300,300)
            self.layout.addWidget(self.canvas)
            self.resize(self.sizeHint())

    gs = DummyGridScan()
    gs.stage = DummyStage()
    gs.stage.axis_names = ('x', 'y', 'z')
    gs.num_axes = 2
    gs.step /= 2

    if test == 'qt':
        gs.run(0.2)
        app = get_qt_app()
        gui = gs.get_qt_ui()
        gui.rate = 0.2
        gui.show()
        sys.exit(app.exec_())
    else:
        print gs.size_unit, gs.size
        print gs._unit_conversion['um'] / gs._unit_conversion['nm']
        gs.size_unit = 'nm'
        print gs.size_unit, gs.size
        gs.run()
