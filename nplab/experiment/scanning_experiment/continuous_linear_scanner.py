__author__ = 'alansanders'

from nplab.experiment.scanning_experiment import ScanningExperiment, TimedScan
from threading import Thread
import time
from nplab.utils.gui import *
from nplab.ui.ui_tools import UiTools


class ContinuousLinearScan(ScanningExperiment, TimedScan):
    def __init__(self):
        super(ContinuousLinearScan, self).__init__()
        self.step = None
        self.direction = 1

    def run(self, new=True):
        if isinstance(self.acquisition_thread, Thread) and self.acquisition_thread.is_alive():
            print 'scan already running'
            return
        self.init_scan()
        self.acquisition_thread = Thread(target=self.scan, args=(new,))
        self.acquisition_thread.start()

    def set_parameter(self, value):
        """Vary the independent parameter."""
        raise NotImplementedError

    def scan(self, new=True):
        self.abort_requested = False
        self.open_scan()
        self.status = 'acquiring data'
        self.acquiring.set()
        scan_start_time = time.time()
        index = 0 if new else 1
        while not self.abort_requested:
            self.set_parameter(self.direction*self.step)
            self.scan_function(index)
            index += 1
            self.update_parameter(self.direction*self.step)
        self.print_scan_time(time.time() - scan_start_time)
        self.acquiring.clear()
        # move back to initial positions
        #self.set_parameter(p[0])
        # finish the scan
        self.analyse_scan()
        self.close_scan()
        self.status = 'scan complete'


class ContinuousLinearScanQT(ContinuousLinearScan, QtCore.QObject):

    def __init__(self):
        ContinuousLinearScan.__init__(self)
        QtCore.QObject.__init__(self)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)

    def run(self, rate=0.1):
        super(ContinuousLinearScanQT, self).run()
        self.acquiring.wait()
        self.timer.start(1000.*rate)

    def get_qt_ui(self):
        return ContinuousLinearScanUI(self)

    @staticmethod
    def get_qt_ui_cls():
        return ContinuousLinearScanUI

    def update(self, force=False):
        """
        This is the function that is called in the event loop and at the end of the scan
        and should be reimplemented when subclassing to deal with data updates and GUIs.
        """
        if not self.acquisition_thread.is_alive():
            self.timer.stop()


class ContinuousLinearScanUI(QtGui.QWidget, UiTools):
    def __init__(self, cont_linear_scan):
        assert isinstance(cont_linear_scan, ContinuousLinearScanQT), 'An instance of ContinuousLinearScanQT must be supplied'
        super(ContinuousLinearScanUI, self).__init__()

        self.linear_scan = cont_linear_scan
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'continuous_linear_scanner.ui'), self)
        self.rate = 1./30.

        self.setWindowTitle(self.linear_scan.__class__.__name__)

        self.step.setValidator(QtGui.QDoubleValidator())
        self.step.textChanged.connect(self.on_text_change)
        self.start_button.clicked.connect(self.on_click)
        self.abort_button.clicked.connect(self.linear_scan.abort)
        self.change_direction_button.clicked.connect(self.on_click)
        self.step_up.clicked.connect(self.on_click)
        self.step_down.clicked.connect(self.on_click)
        self.step.setText(str(self.linear_scan.step))
        self.direction.setText(str(self.linear_scan.direction))

    def on_click(self):
        sender = self.sender()
        if sender == self.start_button:
            self.linear_scan.run(self.rate)
        elif sender == self.change_direction_button:
            self.linear_scan.direction *= -1
            self.direction.setText(str(self.linear_scan.direction))
        elif sender == self.step_up:
            self.step.blockSignals(True)
            self.linear_scan.step *= 2
            self.step.setText(str(self.linear_scan.step))
            self.step.blockSignals(False)
        elif sender == self.step_down:
            self.step.blockSignals(True)
            self.linear_scan.step /= 2
            self.step.setText(str(self.linear_scan.step))
            self.step.blockSignals(False)

    def on_text_change(self, value):
        sender = self.sender()
        if sender.validator() is not None:
            state = sender.validator().validate(value, 0)[0]
            if state != QtGui.QValidator.Acceptable:
                return
        if sender == self.step:
            self.linear_scan.step = float(value)


if __name__ == '__main__':
    import matplotlib
    matplotlib.use('Qt4Agg')
    from nplab.ui.mpl_gui import FigureCanvasWithDeferredDraw as FigureCanvas
    from matplotlib.figure import Figure
    import numpy as np

    class DummyLinearScan(ContinuousLinearScanQT):
        def __init__(self):
            super(DummyLinearScan, self).__init__()
            self.step = 1.
            self.direction = 1.
            self.fig = Figure()
            self.p = None
            self.x = None
            self.y = None
        def open_scan(self):
            self.fig.clear()
            self.p = 0
            self.x = []
            self.y = []
            self.ax = self.fig.add_subplot(111)
        def set_parameter(self, value):
            pass
        def update_parameter(self, value):
            self.p += value
        def scan_function(self, index):
            time.sleep(0.01)
            self.x.append(self.p)
            self.y.append(np.sin(2*np.pi*0.01*self.p))
            self.check_for_data_request(self.x, self.y)
        def update(self, force=False):
            super(DummyLinearScan, self).update(force)
            if self.y == [] or self.fig.canvas is None:
                return
            if force:
                data = (self.x, self.y)
            else:
                data = self.request_data()
            if data is not False:
                x, y = data
                if not np.any(np.isfinite(y)):
                    return
                if not self.ax.lines:
                    self.ax.plot(x, y)
                else:
                    l, = self.ax.lines
                    l.set_data(x, y)
                    self.ax.relim()
                    self.ax.autoscale_view()
                self.fig.canvas.draw()
        def get_qt_ui(self):
            return DummyLinearScanUI(self)


    class DummyLinearScanUI(ContinuousLinearScanUI):
        def __init__(self, linear_scan):
            super(DummyLinearScanUI, self).__init__(linear_scan)
            self.canvas = FigureCanvas(self.linear_scan.fig)
            self.canvas.setMaximumSize(300,300)
            self.layout.addWidget(self.canvas)
            self.resize(self.sizeHint())


    ls = DummyLinearScan()
    app = get_qt_app()
    gui = ls.get_qt_ui()
    gui.rate = 1./30.
    gui.show()
    sys.exit(app.exec_())


