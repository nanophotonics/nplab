__author__ = 'alansanders'

from nplab.experiment.scanning_experiment import ContinuousLinearScan, ContinuousLinearScanQt
from nplab.instrument.stage import Stage
from nplab.utils.gui import *
from nplab import inherit_docstring


@inherit_docstring(ContinuousLinearScan)
class ContinuousLinearStageScan(ContinuousLinearScan):
    """Continuous linear scan that specifically spatially scans using a stage."""

    @inherit_docstring(ContinuousLinearScan.__init__)
    def __init__(self):
        super(ContinuousLinearStageScan, self).__init__()
        self.stage = None
        self.axis = None

    @inherit_docstring(ContinuousLinearScan.init_scan)
    def init_scan(self):
        if not isinstance(self.stage, Stage):
            raise AttributeError("No stage has been set.")

    def set_stage(self, stage):
        if not isinstance(stage, Stage):
            raise ValueError("stage must be an instance of Stage.")
        self.stage = stage

    @inherit_docstring(ContinuousLinearScan.set_parameter)
    def set_parameter(self, value):
        """In this subclass the set parameter is the relative position. """
        self.stage.move(value, self.axis, relative=True)


@inherit_docstring(ContinuousLinearStageScan)
class ContinuousLinearStageScanQt(ContinuousLinearStageScan, ContinuousLinearScanQt):

    @inherit_docstring(ContinuousLinearStageScan)
    def __init__(self):
        ContinuousLinearStageScan.__init__(self)
        ContinuousLinearScanQt.__init__(self)

    @inherit_docstring(ContinuousLinearScanQt.run)
    def run(self, rate=0.1):
        # explicitly inherit the method from ContinuousLinearScanQt
        # otherwise method from ContinuousLinearScan may be called
        ContinuousLinearScanQt.run(self, rate)

    @inherit_docstring(ContinuousLinearScanQt.get_qt_ui)
    def get_qt_ui(self):
        # explicitly inherit the method from ContinuousLinearScanQt
        # otherwise method from ContinuousLinearScan may be called
        return ContinuousLinearScanQt.get_qt_ui(self)

    @inherit_docstring(ContinuousLinearScanQt.get_qt_ui_cls)
    @staticmethod
    def get_qt_ui_cls():
        # explicitly inherit the method from ContinuousLinearScanQt
        # otherwise method from ContinuousLinearScan may be called
        return ContinuousLinearScanQt.get_qt_ui_cls()

    @inherit_docstring(ContinuousLinearScanQt.update)
    def update(self, force=False):
        # explicitly inherit the method from ContinuousLinearScanQt
        # otherwise method from ContinuousLinearScan may be called
        ContinuousLinearScanQt.update(self, force)


if __name__ == '__main__':
    import matplotlib
    matplotlib.use('Qt4Agg')
    from nplab.ui.mpl_gui import FigureCanvasWithDeferredDraw as FigureCanvas
    from matplotlib.figure import Figure
    import numpy as np
    from nplab.instrument.stage import DummyStage
    import time

    class DummyLinearStageScan(ContinuousLinearStageScanQt):
        def __init__(self):
            super(DummyLinearStageScan, self).__init__()
            self.stage = None
            self.axis = 'x'
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
        def scan_function(self, index):
            time.sleep(0.01)
            p = self.stage.get_position(self.axis)
            self.d.append(index)
            self.x.append(p)
            self.y.append(np.sin(2*np.pi*0.01*p))
            self.check_for_data_request(self.d, self.x, self.y)
        def update(self, force=False):
            super(DummyLinearStageScan, self).update(force)
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
            return DummyLinearStageScanUI(self)
        def calculate_feedback_input(self):
            return self.y[-1]


    class DummyLinearStageScanUI(ContinuousLinearStageScanQt.get_qt_ui_cls()):
        def __init__(self, linear_scan):
            super(DummyLinearStageScanUI, self).__init__(linear_scan)
            self.canvas = FigureCanvas(self.linear_scan.fig)
            self.canvas.setMaximumSize(300,300)
            self.layout.addWidget(self.canvas)
            self.resize(self.sizeHint())


    stage = DummyStage()
    stage.axis_names = ('x',)
    ls = DummyLinearStageScan()
    ls.set_stage(stage)
    app = get_qt_app()
    gui = ls.get_qt_ui()
    gui.rate = 1./30.
    gui.show()
    sys.exit(app.exec_())

