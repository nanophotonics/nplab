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
from scipy.interpolate import interp1d


def zernike_polynomial(array_size, n, m, beam_size=1, unit_circle=True):
    """
    Creates an image of a Zernike polynomial of order n,m (https://en.wikipedia.org/wiki/Zernike_polynomials)
    Keep in mind that they are technically only defined inside the unit circle, but the output of this function is a
    square, so the corners are wrong.

    :param array_size: int
    :param n: int
    :param m: int
    :param beam_size: float
    :param unit_circle: bool
    :return:
    """
    assert n >= 0
    if m < 0:
        odd = True
        m = np.abs(m)
    else:
        odd = False
    assert n >= m

    if type(array_size) == int:
        array_size = (array_size, array_size)
    im_rat = array_size[1]/array_size[0]
    if im_rat >= 1:
        _x = np.linspace(-im_rat, im_rat, array_size[1])
        _y = np.linspace(-1, 1, array_size[0])
    else:
        _x = np.linspace(-1, 1, array_size[1])
        _y = np.linspace(-1/im_rat, 1/im_rat, array_size[0])
    x, y = np.meshgrid(_x, _y)
    # By normalising the radius to the beamsize, we can make Zernike polynomials of different sizes
    rho = old_div(np.sqrt(x**2 + y**2), beam_size)
    phi = np.arctan2(x, y)

    summ = []
    for k in range(1 + old_div((n - m), 2)):
        summ += [old_div(((-1)**k * math.factorial(n - k) * (rho**(n-2*k))),
                 (math.factorial(k) * math.factorial(old_div((n+m), 2) - k) * math.factorial(old_div((n-m), 2) - k)))]
    r = np.sum(summ, 0)
    if (n-m) % 2:
        r = 0

    # Limiting the polynomial to the unit circle, where it is defined:
    if unit_circle:
        r[rho > 1] = 0

    if odd:
        zernike = r * np.sin(m * phi)
    else:
        zernike = r * np.cos(m * phi)

    normalised = zernike / np.sqrt(np.sum(zernike[rho < 1] * zernike[rho < 1]))
    return normalised


class SlmDisplay(QtWidgets.QWidget):
    """Widget for displaying the greyscale holograms on the SLM
    It is simply a plain window with a QImage + QLabel.setPixmap combination for displaying phase arrays
    """
    update_image = QtCore.Signal(np.ndarray)

    def __init__(self, shape=(1000, 1000), resolution=(1, 1), bitness=8, hide_border=True, lut=None):
        """
        :param shape: 2-tuple of int. Width and height of the SLM panel in pixels
        :param resolution:
        :param bitness: int. Number of addressing levels of the SLM
        :param hide_border: bool. Whether to show the standard window border in your OS. Set to False only for debugging
        :param lut: tuple. Parameters passed to set_lut. The default LUT assumes that the phase goes from 0 to 2 pi, and
        we want to display it from 0 to 256
        """
        super(SlmDisplay, self).__init__()

        self._pixels = [int(old_div(x[0], x[1])) for x in zip(shape, resolution)]
        self._bitness = bitness

        self._QImage = None
        self._QLabel = None
        self._make_gui(hide_border)

        self.LUT = None
        if lut is None:
            lut = (2**self._bitness, 0)
        self.set_lut(lut)

        self.update_image.connect(self._set_image, type=QtCore.Qt.QueuedConnection)

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
            self.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)

    def set_lut(self, lut):
        if type(lut) == str:
            lut = np.loadtxt(lut)

        lut = np.array(lut)
        if len(lut.shape) == 1:
            # Assumes the lut corresponds to poly1d parameters
            params = [old_div(x, (2 * np.pi)) for x in lut]
            self.LUT = np.poly1d(params)
        elif len(lut.shape) == 2:
            phase = lut[0]
            gray_level = lut[1]
            self.LUT = interp1d(phase, gray_level)

    def set_image(self, phase, slm_monitor=None):
        # Makes phase go from 0 to 2*pi, and removes floating point errors
        phase = (phase + 0.1*np.pi / 2 ** self._bitness) % (2 * np.pi) - 0.1*np.pi / 2 ** self._bitness
        # Makes phase go from -pi to pi
        phase -= np.pi
        # Transform into SLM display values
        phase = self.LUT(phase)

        self.update_image.emit(phase)

        if slm_monitor is not None:
            app = get_qt_app()
            desktop = app.desktop()
            slm_screen = desktop.screen(slm_monitor)
            assert isinstance(slm_monitor, int)
            assert desktop.screenCount() > slm_monitor >= 0
            self.move(slm_screen.x(), slm_screen.y())
        return phase

    def _set_image(self, phase):
        """Sets an array on the QLabel.Pixmap

        :param phase: np.array from 0 to 2 pi
        :param slm_monitor: int. Optional. If given, it will move the SLM widget to the specified monitor
        :return:
        """
        img = phase.ravel()

        if self._bitness == 8:
            self._QImage = QtGui.QImage(img.astype(np.uint8), phase.shape[1], phase.shape[0], QtGui.QImage.Format_Grayscale8)
        else:
            raise ValueError('Bitness %g is not implemented' % self._bitness)

        self._QLabel.setPixmap(QtGui.QPixmap(self._QImage))


class Slm(Instrument):
    def __init__(self, options, slm_monitor, correction_phase=None, display_kwargs=None, **kwargs):
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
        elif type(correction_phase) == str:
            self._correction = np.loadtxt(correction_phase)
        else:
            assert correction_phase.shape == self._shape
            self._correction = correction_phase

        self.phase = None
        self.Display = None
        if display_kwargs is None:
            self.display_kwargs = dict()
        else:
            self.display_kwargs = display_kwargs
        self.options = options

    @staticmethod
    def _get_monitor_size(monitor_index):
        """Utility function to automatically detect the SLM panel size
        :param monitor_index: int. Monitor number
        :return: tuple of two integers, width and height in pixels
        """
        app = get_qt_app()
        desktop = app.desktop()
        assert 0 <= monitor_index < desktop.screenCount(), 'monitor_index must be between 0 and the number of monitors'
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

    def display_phase(self, phase, slm_monitor=None):
        """Display a phase array, creating/displaying the appropriate widget if necessary

        :param phase: 2D array of phase values
        :param slm_monitor: index of the monitor to display the array in
        :param kwargs: named arguments to be passed to the display widget
        :return:
        """
        if self.Display is None:
            self.Display = SlmDisplay(self._shape, **self.display_kwargs)

        self._logger.debug("Setting phase (min, max)=(%g, %g); shape=%s; monitor=%s" % (np.min(phase), np.max(phase),
                                                                                        np.shape(phase), slm_monitor))
        phase = self.Display.set_image(phase + self._correction, slm_monitor=slm_monitor)

        if self.Display.isHidden():
            self.Display.show()
        return phase

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
        self.save_pushButton.pressed.connect(self.save)
        self.load_pushButton.pressed.connect(self.load)

    @property
    def settings_filename(self):
        filename = self.filename_lineEdit.text()
        if filename == '':
            filename = os.path.join(os.path.dirname(__file__), 'settings.ini')
            self.filename_lineEdit.setText(filename)
        return filename

    @settings_filename.setter
    def settings_filename(self, value):
        self.filename_lineEdit.setText(value)

    def make(self):
        parameters = self.get_gui_phase_params()
        self.SLM._logger.debug('SlmUi.make called with args=%s' % (parameters, ))
        phase = self.SLM.make_phase(parameters)

        slm_monitor = self.slm_monitor_lineEdit.text()
        if slm_monitor == '':
            slm_monitor = None
        else:
            slm_monitor = int(slm_monitor)

        phase = self.SLM.display_phase(np.copy(phase), slm_monitor=slm_monitor)

        # The data is transposed according to the pyqtgraph documentation for axis ordering
        # http://www.pyqtgraph.org/documentation/widgets/imageview.html
        self.PhaseDisplay.setImage(np.copy(phase).transpose())

    def save(self):
        gui_settings = QtCore.QSettings(self.settings_filename, QtCore.QSettings.IniFormat)
        self.save_settings(gui_settings, 'base')
        for name, widget in list(self.all_widgets.items()):
            widget.save_settings(gui_settings, name)
        return

    def load(self):
        gui_settings = QtCore.QSettings(self.settings_filename, QtCore.QSettings.IniFormat)
        self.load_settings(gui_settings, 'base')
        for name, widget in list(self.all_widgets.items()):
            widget.load_settings(gui_settings, name)
        return

    def get_gui_phase_params(self):
        """Iterates over all widgets, calling get_params, and storing the returns in a dictionary

        :return: dict. Keys are the self.options.keys() and the values are whatever the widgets return from get_params
        """
        all_params = dict()
        for name, widget in list(self.all_widgets.items()):
            all_params[name] = widget.get_params()
        self.SLM._logger.debug('get_gui_phase_params: %s' % all_params)
        return all_params

    def closeEvent(self, event):
        if self.SLM.Display is not None:
            self.SLM.Display.close()


if __name__ == "__main__":
    settings = ['gratings', 'vortexbeam', 'focus', 'astigmatism', 'linear_lut', 'constant',
                'calibration_responsiveness']
    SLM = Slm(settings, 1)
    SLM._logger.setLevel('DEBUG')
    SLM.show_gui()
