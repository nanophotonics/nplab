# -*- coding: utf-8 -*-

from nplab.utils.gui import QtWidgets, QtGui, QtCore, uic, get_qt_app
from nplab.ui.ui_tools import UiTools
from nplab.instrument import Instrument
import pyqtgraph as pg
import pyqtgraph.dockarea as dockarea
import numpy as np
import os
import math
import gui
import pattern_generators


# TODO: make calibration class https://doi.org/10.1364/AO.43.006400


def zernike_polynomial(array_size, n, m, beam_size=1):
    """
    Creates an image of a Zernike polynomial of order n,m (https://en.wikipedia.org/wiki/Zernike_polynomials)
    Keep in mind that they are technically only defined inside the unit circle, but the output of this function is a
    square, so the corners are wrong.

    :param array_size: int
    :param n: int
    :param m: int
    :param beam_size: float
    :return:
    """
    assert n >= 0
    if m < 0:
        odd = True
        m = np.abs(m)
    else:
        odd = False
    assert n >= m

    _x = np.linspace(-1, 1, array_size)
    x, y = np.meshgrid(_x, _x)
    # By normalising the radius to the beamsize, we can make Zernike polynomials of different sizes
    rho = np.sqrt(x**2 + y**2) / beam_size
    phi = np.arctan2(x, y)

    summ = []
    for k in range(1 + (n - m) / 2):
        summ += [((-1)**k * math.factorial(n - k) * (rho**(n-2*k))) /
                 (math.factorial(k) * math.factorial((n+m)/2 - k) * math.factorial((n-m)/2 - k))]
    r = np.sum(summ, 0)
    if (n-m) % 2:
        r = 0

    # Limiting the polynomial to the unit circle, where it is defined:
    r[rho > 1] = 0

    if odd:
        return r * np.sin(m * phi)
    else:
        return r * np.cos(m * phi)


class SlmDisplay(QtWidgets.QWidget):
    """Widget for displaying the greyscale holograms on the SLM
    It is simply a plain window with a QImage + QLabel.setPixmap combination for displaying phase arrays
    """
    def __init__(self, shape=(1000, 1000), resolution=(1, 1), bitness=8, hide_border=True):
        super(SlmDisplay, self).__init__()

        self._pixels = [int(x[0]/x[1]) for x in zip(shape, resolution)]
        self._bitness = bitness

        self._QImage = None
        self._QLabel = None
        self._make_gui(hide_border)

        self.LUT = None
        # The default LUT assumes that the phase goes from 0 to 2 pi, and we want to display it from 0 to 256
        self.set_lut(256/(2*np.pi), 0)

    def _make_gui(self, hide_border=True):
        """Creates and sets the widget layout

        :param hide_border: bool. Whether to show the standard window border in your OS. Useful for debugging.
        :return:
        """
        self._QLabel = QtWidgets.QLabel(self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._QLabel)
        self.setLayout(layout)

        self.setWindowTitle('SLM Phase')
        if hide_border:
            self.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.FramelessWindowHint)

    def set_lut(self, *params):
        self.LUT = np.poly1d(params)

    def set_image(self, phase, slm_monitor=None):
        """Sets an array on the QLabel.Pixmap

        :param phase: np.array from 0 to 2 pi
        :param slm_monitor: int. Optional. If given, it will move the SLM widget to the specified monitor
        :return:
        """
        phase = self.LUT(phase)

        img = phase.ravel()
        img_slm = np.dstack((img, img, img, img)).astype(np.uint8)
        self._QImage = QtGui.QImage(img_slm, phase.shape[1], phase.shape[0], QtGui.QImage.Format_RGB32)
        self._QLabel.setPixmap(QtGui.QPixmap(self._QImage))

        if slm_monitor is not None:
            app = get_qt_app()
            desktop = app.desktop()
            slm_screen = desktop.screen(slm_monitor)
            assert isinstance(slm_monitor, int)
            assert desktop.screenCount() > slm_monitor >= 0
            self.move(slm_screen.x(), slm_screen.y())


class Slm(Instrument):
    def __init__(self, options, slm_monitor, correction_phase=None, **kwargs):
        super(Slm, self).__init__()

        self._shape = self._get_monitor_size(slm_monitor)
        if correction_phase is None:
            self._correction = np.zeros(self._shape[::-1])
        else:
            assert correction_phase.shape == self._shape
            self._correction = correction_phase

        self.phase = None
        self.Display = None
        self.options = options

    def make_phase(self, **kwargs):
        self._logger.debug('Making phases: %s, %s' % (self._shape, kwargs))
        self.phase = np.zeros(self._shape[::-1])
        for option in self.options:
            self._logger.debug('Making phase: %s' % option)
            try:
                self.phase = getattr(pattern_generators, option)(self.phase, *kwargs[option])
            except Exception as e:
                self._logger.warn('Failed because: %s' % e)
        return self.phase

    def get_qt_ui(self):
        return SlmUi(self)

    @staticmethod
    def _get_monitor_size(monitor_index):
        """
        :param monitor_index: int. Monitor number
        :return: tuple of two integers, width and height in pixels
        """
        app = get_qt_app()
        desktop = app.desktop()
        slm_screen = desktop.screen(monitor_index)

        return [slm_screen.width(), slm_screen.height()]

    def display_phase(self, phase, slm_monitor=None, **kwargs):
        """Display a phase array, creating/displaying the appropriate widget if necessary

        :param phase: 2D array of phase values
        :param slm_monitor: index of the monitor to display the array in
        :param kwargs: named arguments to be passed to the display widget
        :return:
        """
        if self.Display is None:
            self.Display = SlmDisplay(self._shape, **kwargs)

        self._logger.debug("Setting phase (min, max)=(%g, %g); shape=%s; monitor=%d" % (np.min(phase), np.max(phase),
                                                                                        np.shape(phase), slm_monitor))
        self.Display.set_image(phase + self._correction, slm_monitor=slm_monitor)

        if self.Display.isHidden():
            self.Display.show()


class SlmUi(QtWidgets.QWidget, UiTools):
    """
    To create the GUI for a different application, you only need to subclass and replace the get_gui_phase_params method
    """
    def __init__(self, slm):
        super(SlmUi, self).__init__()
        self.all_widgets = None
        self.all_docks = None
        self.PhaseDisplay = None
        self.dockarea = None
        self.SLM = slm
        self.setup_gui()

    def setup_gui(self):
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'ui_base.ui'), self)
        self.dockarea = dockarea.DockArea()
        self.splitter.replaceWidget(0, self.dockarea)
        self.dockarea.show()  # Absolutely no idea why this is needed

        self.all_widgets = dict()
        self.all_docks = []
        for option in self.SLM.options:
            widget = getattr(gui, '%sUi' % option)()
            dock = dockarea.Dock(option)
            dock.addWidget(widget)
            self.dockarea.addDock(dock, 'bottom')
            self.all_widgets[option] = widget
            self.all_docks += [dock]
        self.make_pushButton.pressed.connect(self.make)

    def make(self):
        args = self.get_gui_phase_params()
        self.SLM._logger.debug('SlmUi.make called with args=%s' % (args, ))
        phase = self.SLM.make_phase(**args)

        # The data is transposed according to the pyqtgraph documentation for axis ordering
        # http://www.pyqtgraph.org/documentation/widgets/imageview.html
        self.PhaseDisplay.setImage(np.copy(phase).transpose())

        slm_monitor = self.slm_monitor_lineEdit.text()
        if slm_monitor == '':
            slm_monitor = None
        else:
            slm_monitor = int(slm_monitor)

        self.SLM.display_phase(np.copy(phase), slm_monitor=slm_monitor)

    def get_gui_phase_params(self):
        """Reads parameters from the user-created GUI to be passed to the Slm.make_phase method. Needs to be
        reimplemented for all subclasses
        :return:
        """
        all_params = dict()
        for name, widget in self.all_widgets.items():
            all_params[name] = widget.get_params()
        self.SLM._logger.debug('get_gui_phase_params: %s' % all_params)
        return all_params


if __name__ == "__main__":
    settings = ['gratings', 'vortexbeam', 'focus', 'astigmatism', 'linear_lut']
    SLM = Slm(settings, 1)
    SLM._logger.setLevel('DEBUG')
    SLM.show_gui()
