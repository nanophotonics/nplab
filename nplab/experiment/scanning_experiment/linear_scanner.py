from __future__ import print_function
from builtins import str
from builtins import range
__author__ = 'alansanders'

from nplab.experiment.scanning_experiment import ScanningExperiment, TimedScan
import numpy as np
import threading
import time
from nplab.utils.gui import *
from nplab.ui.ui_tools import UiTools


class LinearScan(ScanningExperiment, TimedScan):
    """

    """

    def __init__(self, start=None, stop=None, step=None):
        ScanningExperiment.__init__(self)
        TimedScan.__init__(self)
        self.scanner = None
        self.start, self.stop, self.step = (start, stop, step)
        self.parameter = None
        # underscored attributes are made into properties
        self.status = 'inactive'
        self.abort_requested = False
        self.estimated_step_time = 0.001
        self.acquisition_thread = None

    def run(self):
        """
        Starts the grid scan in its own thread and runs the update function at the specified
        rate whilst acquiring the data.

        :param rate: the update period in seconds
        :return:
        """
        if isinstance(self.acquisition_thread, threading.Thread) and self.acquisition_thread.is_alive():
            print('scan already running')
            return
        self.init_scan()
        self.acquisition_thread = threading.Thread(target=self.scan,
                                                   args=(self.start, self.stop, self.step))
        self.acquisition_thread.start()

    def init_parameter(self, start, stop, step):
        """Create an parameter array to scan."""
        x = np.arange(start, stop, step)
        self.total_points = x.size
        self.parameter = x
        return x

    def init_current_parameter(self):
        """Convenience method that initialises a grid based on current parameters."""
        self.init_parameter(self.start, self.stop, self.step)

    def set_parameter(self, value):
        """Vary the independent parameter."""
        raise NotImplementedError

    def scan(self, start, stop, step):
        """Scans a grid, applying a function at each position."""
        self.abort_requested = False
        p = self.init_parameter(start, stop, step)
        self.open_scan()
        # get the indices of points along each of the scan axes for use with snaking over array
        pnts = list(range(p.size))

        self.index = -1
        self._index = -1
        self._step_times = np.zeros_like(p)
        self._step_times.fill(np.nan)
        self.status = 'acquiring data'
        self.acquiring.set()
        scan_start_time = time.time()

        for i in pnts:
            if self.abort_requested:
                break
            self.index = i
            self.set_parameter(p[i])
            self.scan_function(i)
            self._index += 1
        self.print_scan_time(time.time() - scan_start_time)
        self.acquiring.clear()
        # move back to initial positions
        #self.set_parameter(p[0])
        # finish the scan
        self.analyse_scan()
        self.close_scan()
        self.status = 'scan complete'


class LinearScanQt(LinearScan, QtCore.QObject):
    """
    A GridScanner subclass containing additional or redefined functions related to GUI operation.
    """

    total_points_updated = QtCore.Signal(int)
    status_updated = QtCore.Signal(str)
    timing_updated = QtCore.Signal(str)

    def __init__(self, start=None, stop=None, step=None):
        LinearScan.__init__(self, start, stop, step)
        QtCore.QObject.__init__(self)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)

    def run(self, rate=0.1):
        super(LinearScanQt, self).run()
        self.acquiring.wait()
        self.timer.start(1000.*rate)

    def get_qt_ui(self):
        return LinearScanUI(self)

    @staticmethod
    def get_qt_ui_cls():
        return LinearScanUI

    def init_parameter(self, start, stop, step):
        parameter = super(LinearScanQt, self).init_parameter(start, stop, step)
        self.total_points_updated.emit(self.total_points)
        return parameter

    def update(self, force=False):
        """
        This is the function that is called in the event loop and at the end of the scan
        and should be reimplemented when subclassing to deal with data updates and GUIs.
        """
        if not self.acquisition_thread.is_alive():
            self.timer.stop()
        self.timing_updated.emit(self.get_formatted_estimated_time_remaining())
        self.status_updated.emit('')


class LinearScanUI(QtWidgets.QWidget, UiTools):
    def __init__(self, linear_scanner):
        assert isinstance(linear_scanner, LinearScanQt), "A valid LinearScanQt subclass must be supplied"
        super(LinearScanUI, self).__init__()
        self.linear_scanner = linear_scanner
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'linear_scanner.ui'), self)
        self.rate = 1./30.

        self.setWindowTitle(self.linear_scanner.__class__.__name__)

        for widget in [self.start, self.stop, self.step]:
            widget.setValidator(QtGui.QDoubleValidator())
            widget.textChanged.connect(self.on_text_change)
        self.update_button.clicked.connect(self.linear_scanner.init_current_parameter)
        self.start_button.clicked.connect(self.on_click)
        self.abort_button.clicked.connect(self.linear_scanner.abort)
        self.step_up.clicked.connect(self.on_click)
        self.step_down.clicked.connect(self.on_click)
        self.linear_scanner.status_updated.connect(self.update_status)
        self.linear_scanner.timing_updated.connect(self.update_timing)
        self.linear_scanner.total_points_updated.connect(self.update_parameters)

        self.start.setText(str(self.linear_scanner.start))
        self.stop.setText(str(self.linear_scanner.stop))
        self.step.setText(str(self.linear_scanner.step))
        self.status.setText(self.linear_scanner.status)

    def on_click(self):
        sender = self.sender()
        if sender == self.start_button:
            self.linear_scanner.run(self.rate)
        elif sender == self.step_up:
            self.linear_scanner.step *= 2
            self.step.setText(str(self.linear_scanner.step))
        elif sender == self.step_down:
            self.linear_scanner.step /= 2
            self.step.setText(str(self.linear_scanner.step))

    def on_text_change(self, value):
        sender = self.sender()
        if sender.validator() is not None:
            state = sender.validator().validate(value, 0)[0]
            if state != QtGui.QValidator.Acceptable:
                return
        if sender == self.start:
            self.linear_scanner.start = float(value)
        elif sender == self.stop:
            self.linear_scanner.stop = float(value)
        elif sender == self.step:
            self.linear_scanner.step = float(value)

    def update_parameters(self):
        self.total_points.setText(str(self.linear_scanner.total_points))
        self.total_points.resize(self.total_points.sizeHint())
        self.est_scan_time.setText(str(self.linear_scanner.estimate_scan_duration()))
        self.est_scan_time.resize(self.est_scan_time.sizeHint())

    def update_status(self):
        self.status.setText(self.linear_scanner.status)

    def update_timing(self, time):
        self.est_time_remain.setText(time)


if __name__ == '__main__':
    import matplotlib
    matplotlib.use('Qt4Agg')
    from nplab.ui.mpl_gui import FigureCanvasWithDeferredDraw as FigureCanvas
    from matplotlib.figure import Figure
    import cProfile
    import pstats

    test = 'qt'
    if test == 'qt':
        template = LinearScanQt
    else:
        template = LinearScan

    class DummyLinearScan(template):
        def __init__(self):
            super(DummyLinearScan, self).__init__()
            self.start, self.stop, self.step = (0, 1, 0.01)
            self.estimated_step_time = 0.0005
            self.fig = Figure()
            self.data = None
        def open_scan(self):
            self.fig.clear()
            self.data = np.zeros_like(self.parameter, dtype=np.float64)
            self.data.fill(np.nan)
            self.ax = self.fig.add_subplot(111)
            #self.ax.set_xlim(self.parameter.min(), self.parameter.max())
        def set_parameter(self, value):
            pass
        def scan_function(self, index):
            time.sleep(0.0005)
            x = self.parameter[index]
            self.data[index] = np.sin(2*np.pi*5*x)
            self.check_for_data_request(self.parameter[:self.index+1], self.data[:self.index+1])
        def run(self, rate=0.1):
            fname = 'profiling.stats'
            cProfile.runctx('super(DummyLinearScan, self).run(%.2f)'%rate, globals(), locals(), filename=fname)
            stats = pstats.Stats(fname)
            stats.strip_dirs()
            stats.sort_stats('cumulative')
            stats.print_stats()
        def update(self, force=False):
            super(DummyLinearScan, self).update(force)
            if self.data is None or self.fig.canvas is None:
                print('no canvas or data')
                return
            if force:
                data = (self.parameter, self.data)
            else:
                data = self.request_data()
            if data is not False:
                sweep, data = data
                if not np.any(np.isfinite(data)):
                    return
                if not self.ax.lines:
                    self.ax.plot(sweep, data)
                else:
                    l, = self.ax.lines
                    l.set_data(sweep, data)
                    self.ax.relim()
                    self.ax.autoscale_view()
                self.fig.canvas.draw()
        def get_qt_ui(self):
            return DummyLinearScanUI(self)

    class DummyLinearScanUI(LinearScanUI):
        def __init__(self, linear_scanner):
            super(DummyLinearScanUI, self).__init__(linear_scanner)
            self.canvas = FigureCanvas(self.linear_scanner.fig)
            self.canvas.setMaximumSize(300,300)
            self.layout.addWidget(self.canvas)
            self.resize(self.sizeHint())

    ls = DummyLinearScan()
    if test == 'qt':
        ls.run(1./30.)
        app = get_qt_app()
        gui = ls.get_qt_ui()
        gui.rate = 1./30.
        gui.show()
        sys.exit(app.exec_())
    else:
        ls.run()