from __future__ import print_function
from builtins import str
__author__ = 'alansanders'

from nplab.experiment.scanning_experiment import ScanningExperiment, TimedScan
from threading import Thread
import time
from nplab.utils.gui import *
from nplab.ui.ui_tools import UiTools
from nplab import inherit_docstring
from functools import partial
import numpy as np


class ContinuousLinearScan(ScanningExperiment, TimedScan):

    @inherit_docstring(TimedScan)
    @inherit_docstring(ScanningExperiment)
    def __init__(self):
        super(ContinuousLinearScan, self).__init__()
        self.step = None
        self.direction = 1
        # Repeat capabilities
        self._num_measurements = 0  # the number of measurements made and incremented to num_repeats
        self.num_repeats = 1  # user sets this in subclass
        self.hold = False  # setting this to true prevents movement commands
        self._last_step = 0.  # this is useful when incrementing a displacement array
        # Feedback attributes
        self.engage_feedback = False
        self.feedback_on = 'Force'
        self.set_point = 0
        self.feedback_gain = 1
        self.feedback_min = -1
        self.feedback_max = 1

    @inherit_docstring(ScanningExperiment.run)
    def run(self, new=True):
        if isinstance(self.acquisition_thread, Thread) and self.acquisition_thread.is_alive():
            print('scan already running')
            return
        self.init_scan()
        self.acquisition_thread = Thread(target=self.scan, args=(new,))
        self.acquisition_thread.start()

    def set_parameter(self, value):
        """Vary the independent parameter."""
        raise NotImplementedError

    @inherit_docstring(ScanningExperiment.scan_function)
    def scan_function(self, index):
        raise NotImplementedError

    def update_parameter(self, value):
        """Vary the independent parameter."""
        raise NotImplementedError

    @inherit_docstring(ScanningExperiment.run)
    def scan(self, new=True):
        self.abort_requested = False
        self.open_scan()
        self.status = 'acquiring data'
        self.acquiring.set()
        scan_start_time = time.time()
        index = 0 if new else 1
        while not self.abort_requested:
            if self.hold or self._num_measurements < self.num_repeats:
                self._last_step = 0.  # used to prevent the incrementing of the displacement
            else:
                self.set_parameter(self.direction*self.step)
                self._num_measurements = 0  # reset the number of measurements made after move
                self._last_step = self.direction*self.step
            self._num_measurements += 1
            self.scan_function(index)
            index += 1
            if self.engage_feedback:
                feedback_input = self.calculate_feedback_input()
                direction, step = self.feedback_loop(feedback_input, self.set_point)
                self.update_from_feedback(direction, step)
            try:
                self.update_parameter(self.direction*self.step)
            except NotImplementedError:
                pass
        self.print_scan_time(time.time() - scan_start_time)
        self.acquiring.clear()
        # finish the scan
        self.analyse_scan()
        self.close_scan()
        self.status = 'scan complete'

    def calculate_feedback_input(self):
        """
        Return the input to the feedback loop.

        :return value: the value of the variable to feed back on
        """
        raise NotImplementedError

    def feedback_loop(self, feedback_input, set_point):
        """
        Returns the direction and step size that should be used in the next loop iteration.
        :param feedback_input: the current value of the target variable
        :param set_point: the target value that should held
        :returns direction, step_size:
        :rtype : object
        """
        e = feedback_input - set_point
        output = -self.feedback_gain*e  # if e>0 i.e. input > set_point for d=1 then d goes to -1
        output = np.clip(output, self.feedback_min, self.feedback_max)
        step_size = abs(output)
        direction = np.sign(output)
        return direction, step_size

    def update_from_feedback(self, direction, step):
        """This function is created simply to be subclass GUI updates."""
        self.direction = direction
        self.step = step


@inherit_docstring(ContinuousLinearScan)
class ContinuousLinearScanQt(ContinuousLinearScan, QtCore.QObject):
    direction_updated = QtCore.Signal(int)
    step_updated = QtCore.Signal(float)

    @inherit_docstring(ContinuousLinearScan.__init__)
    def __init__(self):
        ContinuousLinearScan.__init__(self)
        QtCore.QObject.__init__(self)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)

    @inherit_docstring(ContinuousLinearScan.run)
    def run(self, rate=0.1):
        super(ContinuousLinearScanQt, self).run()
        self.acquiring.wait()
        self.timer.start(1000.*rate)

    def get_qt_ui(self):
        return ContinuousLinearScanUI(self)

    @staticmethod
    def get_qt_ui_cls():
        return ContinuousLinearScanUI

    @inherit_docstring(ContinuousLinearScan.update)
    def update(self, force=False):
        if not self.acquisition_thread.is_alive():
            self.timer.stop()

    @inherit_docstring(ContinuousLinearScan.update_from_feedback)
    def update_from_feedback(self, direction, step):
        super(ContinuousLinearScanQt, self).update_from_feedback(direction, step)
        self.direction_updated.emit(self.direction)
        self.step_updated.emit(self.step)


class ContinuousLinearScanUI(QtWidgets.QWidget, UiTools):
    def __init__(self, cont_linear_scan):
        assert isinstance(cont_linear_scan, ContinuousLinearScanQt), 'An instance of ContinuousLinearScanQt must be supplied'
        super(ContinuousLinearScanUI, self).__init__()

        self.linear_scan = cont_linear_scan
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'continuous_linear_scanner.ui'), self)
        self.rate = 1./30.

        self.setWindowTitle(self.linear_scan.__class__.__name__)

        self.step.setValidator(QtGui.QDoubleValidator())
        self.step.textChanged.connect(self.check_state)
        self.step.textChanged.connect(self.on_text_change)
        self.start_button.clicked.connect(self.on_click)
        self.abort_button.clicked.connect(self.linear_scan.abort)
        self.change_direction_button.clicked.connect(self.on_click)
        self.step_up.clicked.connect(self.on_click)
        self.step_down.clicked.connect(self.on_click)
        self.step.setText(str(self.linear_scan.step))
        self.direction.setText(str(self.linear_scan.direction))

        self.num_repeats.setValidator(QtGui.QDoubleValidator())
        self.num_repeats.textChanged.connect(self.check_state)
        self.num_repeats.textChanged.connect(self.on_text_change)
        self.hold.stateChanged.connect(self.on_state_change)
        self.set_point.setValidator(QtGui.QDoubleValidator())
        self.set_point.textChanged.connect(self.check_state)
        self.set_point.textChanged.connect(self.on_text_change)
        self.engage_feedback.stateChanged.connect(self.on_state_change)

        self.linear_scan.direction_updated.connect(partial(self.update_param, 'direction'))
        self.linear_scan.step_updated.connect(partial(self.update_param, 'step'))

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
        elif sender == self.num_repeats:
            self.linear_scan.num_repeats = int(value)
        elif sender == self.set_point:
            self.linear_scan.set_point = float(value)

    def on_state_change(self, state):
        sender = self.sender()
        if sender == self.hold:
            if state == QtCore.Qt.Checked:
                self.linear_scan.hold = True
            elif state == QtCore.Qt.Unchecked:
                self.linear_scan.hold = False
        elif sender == self.engage_feedback:
            if state == QtCore.Qt.Checked:
                self.linear_scan.engage_feedback = True
            elif state == QtCore.Qt.Unchecked:
                self.linear_scan.engage_feedback = False

    def update_param(self, param, value):
        if param == 'direction':
            self.direction.setText(str(value))
        elif param == 'step':
            self.step.setText(str(value))


if __name__ == '__main__':
    import matplotlib
    matplotlib.use('Qt4Agg')
    from nplab.ui.mpl_gui import FigureCanvasWithDeferredDraw as FigureCanvas
    from matplotlib.figure import Figure
    import numpy as np

    class DummyLinearScan(ContinuousLinearScanQt):
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
            self.d = []
            self.x = []
            self.y = []
            self.ax = self.fig.add_subplot(111)
        def set_parameter(self, value):
            self.p += value
        #def update_parameter(self, value):
        #    self.p += value
        def scan_function(self, index):
            time.sleep(0.01)
            self.d.append(index)
            self.x.append(self.p)
            self.y.append(np.sin(2*np.pi*0.01*self.p))
            self.check_for_data_request(self.d, self.x, self.y)
        def update(self, force=False):
            super(DummyLinearScan, self).update(force)
            if self.y == [] or self.fig.canvas is None:
                return
            if force:
                data = (self.d, self.x, self.y)
            else:
                data = self.request_data()
            if data is not False:
                d, x, y = data
                if not np.any(np.isfinite(y)):
                    return
                if not self.ax.lines:
                    self.ax.plot(d, y)
                else:
                    l, = self.ax.lines
                    l.set_data(d, y)
                    self.ax.relim()
                    self.ax.autoscale_view()
                self.fig.canvas.draw()
        def get_qt_ui(self):
            return DummyLinearScanUI(self)
        def calculate_feedback_input(self):
            return self.y[-1]


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


