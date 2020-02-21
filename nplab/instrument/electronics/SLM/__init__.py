# -*- coding: utf-8 -*-

from __future__ import division
from builtins import zip
from builtins import range
from past.utils import old_div
from nplab.utils.gui import QtWidgets, QtGui, QtCore, uic, get_qt_app
from nplab.ui.ui_tools import UiTools
from nplab.instrument import Instrument
import pyqtgraph.dockarea as dockarea
import numpy as np
import os
import math
from . import gui
from . import pattern_generators


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
    rho = old_div(np.sqrt(x**2 + y**2), beam_size)
    phi = np.arctan2(x, y)

    summ = []
    for k in range(1 + old_div((n - m), 2)):
        summ += [old_div(((-1)**k * math.factorial(n - k) * (rho**(n-2*k))),
                 (math.factorial(k) * math.factorial(old_div((n+m),2) - k) * math.factorial(old_div((n-m),2) - k)))]
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
        """
        :param shape: 2-tuple of int. Width and height of the SLM panel in pixels
        :param resolution:
        :param bitness: int. Number of addressing levels of the SLM
        :param hide_border: bool. Whether to show the standard window border in your OS. Set to False only for debugging
        """
        super(SlmDisplay, self).__init__()

        self._pixels = [int(old_div(x[0],x[1])) for x in zip(shape, resolution)]
        self._bitness = bitness

        self._QImage = None
        self._QLabel = None
        self._make_gui(hide_border)

        self.LUT = None
        # The default LUT assumes that the phase goes from 0 to 2 pi, and we want to display it from 0 to 256
        self.set_lut(old_div(256,(2*np.pi)), 0)

    def _make_gui(self, hide_border=True):
        """Creates and sets the widget layout
        :param hide_border: bool. See __init__
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
        """
        :param options: list of strings. Names of the functionalities you want your SLM to have:
            - gratings
            - vortexbeam
            - focus
            - astigmatism
            - linear_lut
            The order you give these in is important, as they act on the phase pattern sequentially (see make_phase)
        :param slm_monitor: int. Monitor index for the SLM. See _get_monitor_size
        :param correction_phase: array. Some SLMs require a large spatial correction to provide a flat phase
        :param kwargs:
        """
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

    @staticmethod
    def _get_monitor_size(monitor_index):
        """Utility function to automatically detect the SLM panel size
        :param monitor_index: int. Monitor number
        :return: tuple of two integers, width and height in pixels
        """
        app = get_qt_app()
        desktop = app.desktop()
        slm_screen = desktop.screen(monitor_index)

        return [slm_screen.width(), slm_screen.height()]

    def make_phase(self, parameters):
        """Creates and returns the phase pattern

        Iterates over self.options, getting the correct pattern_generator by name and applying them sequentially to an
        array initially full of zeros.

        :param parameters: dict. Keys correspond to the self.options keys, values are the arguments to be passed to the
        pattern_generators as unnamed arguments
        :return:
        """
        self._logger.debug('Making phases: %s, %s' % (self._shape, parameters))
        self.phase = np.zeros(self._shape[::-1])
        for option in self.options:
            self._logger.debug('Making phase: %s' % option)
            try:
                self.phase = getattr(pattern_generators, option)(self.phase, *parameters[option])
            except Exception as e:
                self._logger.warn('Failed because: %s' % e)
        self._logger.debug('Finished making phases')
        return self.phase

    def display_phase(self, phase, slm_monitor=None, **kwargs):
        """Display a phase array, creating/displaying the appropriate widget if necessary

        :param phase: 2D array of phase values
        :param slm_monitor: index of the monitor to display the array in
        :param kwargs: named arguments to be passed to the display widget
        :return:
        """
        if self.Display is None:
            self.Display = SlmDisplay(self._shape, **kwargs)

        self._logger.debug("Setting phase (min, max)=(%g, %g); shape=%s; monitor=%s" % (np.min(phase), np.max(phase),
                                                                                        np.shape(phase), slm_monitor))
        self.Display.set_image(phase + self._correction, slm_monitor=slm_monitor)

        if self.Display.isHidden():
            self.Display.show()

    def get_qt_ui(self):
        return SlmUi(self)


class SlmUi(QtWidgets.QWidget, UiTools):
    def __init__(self, slm):
        """
        :param slm: instance of Slm
        """
        super(SlmUi, self).__init__()
        self.all_widgets = None
        self.all_docks = None
        self.PhaseDisplay = None
        self.dockarea = None
        self.SLM = slm
        self.setup_gui()

    def setup_gui(self):
        """Creates a DockArea and fills it with the Slm.options given

        For each option, it extracts the correct ui from gui by name, loads it into a widget and adds it to the DockArea

        :return:
        """
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'ui_base.ui'), self)
        self.dockarea = dockarea.DockArea()
        self.splitter.insertWidget(0, self.dockarea)
        self.dockarea.show()  # Absolutely no idea why this is needed

        self.all_widgets = dict()
        self.all_docks = []
        for option in self.SLM.options:
            widget = getattr(gui, '%sUi' % option)(self)
            dock = dockarea.Dock(option)
            dock.addWidget(widget)
            self.dockarea.addDock(dock, 'bottom')
            self.all_widgets[option] = widget
            self.all_docks += [dock]
        self.make_pushButton.pressed.connect(self.make)

    def make(self):
        parameters = self.get_gui_phase_params()
        self.SLM._logger.debug('SlmUi.make called with args=%s' % (parameters, ))
        phase = self.SLM.make_phase(parameters)

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
        """Iterates over all widgets, calling get_params, and storing the returns in a dictionary

        :return: dict. Keys are the self.options.keys() and the values are whatever the widgets return from get_params
        """
        all_params = dict()
        for name, widget in list(self.all_widgets.items()):
            all_params[name] = widget.get_params()
        self.SLM._logger.debug('get_gui_phase_params: %s' % all_params)
        return all_params


if __name__ == "__main__":
    settings = ['gratings', 'vortexbeam', 'focus', 'astigmatism', 'linear_lut', 'constant',
                'calibration_responsiveness']
    SLM = Slm(settings, 1)
    SLM._logger.setLevel('DEBUG')
    SLM.show_gui()
