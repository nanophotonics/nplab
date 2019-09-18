# -*- coding: utf-8 -*-

from nplab.utils.gui import QtWidgets, QtGui, QtCore, uic, get_qt_app
from nplab.ui.ui_tools import UiTools
from nplab.instrument import Instrument
import pyqtgraph as pg
import numpy as np
import os
import math


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
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        img_slm_zero = np.zeros(np.prod(self._pixels))
        img_slm = np.dstack((img_slm_zero, img_slm_zero, img_slm_zero, img_slm_zero)).astype(np.uint8)
        self._QImage = QtGui.QImage(img_slm, self._pixels[0], self._pixels[1], QtGui.QImage.Format_RGB32)

        label = QtWidgets.QLabel(self)
        label.setPixmap(QtGui.QPixmap(self._QImage))
        self._QLabel = label

        layout.addWidget(label)
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


class SlmBase(Instrument):
    """Base SLM class. Together with it's GUI it implements all of the basic displaying of phase arrays and the static
    corrections (if any) to be applied to the SLM display

    To create an SLM class for a different application, you need only subclass and replace the make_phase method, and
    connect to a GUI that subclasses SLMBaseUI replacing get_gui_phase_params
    """
    def __init__(self, slm_monitor, correction_phase=None, **kwargs):
        super(SlmBase, self).__init__()

        self._shape = self._get_monitor_size(slm_monitor)
        if correction_phase is None:
            self._correction = np.zeros(self._shape)
        else:
            assert correction_phase.shape == self._shape
            self._correction = correction_phase

        self.phase = None
        self.Display = None

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
        self.Display.set_image(phase + self._correction.transpose(), slm_monitor=slm_monitor)

        if self.Display.isHidden():
            self.Display.show()

    def get_qt_ui(self):
        return SlmBaseUi(self)

    def make_phase(self, *args):
        """Called from the GUI every time a new hologram is created. Re-implemented in all subclasses

        :param args:
        :return:
        """
        raise NotImplementedError


class SlmBaseUi(QtWidgets.QWidget, UiTools):
    """
    To create the GUI for a different application, you only need to subclass and replace the get_gui_phase_params method
    """
    def __init__(self, slm, ui_filename='slm_base.ui'):
        super(SlmBaseUi, self).__init__()

        self.PhaseDisplay = None
        self.SLM = slm
        self.setup_gui(ui_filename)

    def setup_gui(self, ui_filename):
        uic.loadUi(os.path.join(os.path.dirname(__file__), ui_filename), self)
        self.PhaseDisplay = pg.ImageView()
        self.Display_frame.layout().addWidget(self.PhaseDisplay, 0, 0)

        self.auto_connect_by_name()
        self.make_pushButton.pressed.connect(self.make)

    def make(self):
        args = self.get_gui_phase_params()
        self.SLM._logger.debug('SLMBaseUI.make called with args=%s' % (args, ))
        phase = self.SLM.make_phase(*args)

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
        """Reads parameters from the user-created GUI to be passed to the SLMBase.make_phase method. Needs to be
        reimplemented for all subclasses
        :return:
        """
        raise NotImplementedError


class SlmCalibration(SlmBase):
    """Simple class for testing an SLM with gratings, lenses and astigmatism"""
    def __init__(self, *args, **kwargs):
        super(SlmCalibration, self).__init__(*args, **kwargs)

    def make_phase(self, kx=0, ky=0, fcs=0, ax=0, ay=0, contrast=1, offset=0):
        """
        :param kx: grating constant along the width
        :param ky: grating constant along the height
        :param fcs: focal value (currently in arbitrary units)
        :param ax: horizongal-vertical astigmatism
        :param ay: diagonal-antidiagonal astigmatism
        :param contrast: voltage difference between 0 and 2*pi phase
        :param offset: voltage offset for 0 phase
        :return:
        """
        x = np.arange(self._shape[0]) - int(self._shape[0]/2)
        y = np.arange(self._shape[1]) - int(self._shape[1]/2)
        x, y = np.meshgrid(x, y)
        rho = np.sqrt(x**2 + y**2)
        phi = np.arctan2(x, y)

        # Grating
        grating = np.zeros(x.shape)
        if kx != 0:
            grating += (np.pi / kx) * x
        if ky != 0:
            grating += (np.pi / ky) * y

        # Focus
        focus = fcs * (x**2 + y**2)

        # Astigmatism
        astigmatism = (ax * np.sin(2*phi) + ay * np.cos(2*phi)) * rho**2

        phase = grating + focus + astigmatism
        phase -= phase.min()
        phase %= 2 * np.pi - 0.000001  # The substraction takes care of rounding errors

        try:
            phase *= contrast
            phase += offset
        except AssertionError:
            self._logger.warn('You tried setting a phase modulation of more than 2 pi')
        return phase

    def get_qt_ui(self):
        return SlmCalibrationUi(self)


class SlmCalibrationUi(SlmBaseUi):
    def __init__(self, slm):
        super(SlmCalibrationUi, self).__init__(slm, 'slm_calibration.ui')
        self._connect()

    def _connect(self):
        # Connects the offset slider to the lineEdits
        self.offset_lineEdit_step.returnPressed.connect(self.update_offset_lineedit)
        self.offset_lineEdit_offset.returnPressed.connect(self.update_offset_lineedit)
        self.offset_slider.valueChanged.connect(self.update_offset_lineedit)
        self.offset_lineEdit.returnPressed.connect(self.update_offset_slider)

        # Connects the contrast slider to the lineEdits
        self.contrast_lineEdit_step.returnPressed.connect(self.update_contrast_lineedit)
        self.contrast_lineEdit_offset.returnPressed.connect(self.update_contrast_lineedit)
        self.contrast_slider.valueChanged.connect(self.update_contrast_lineedit)
        self.contrast_lineEdit.returnPressed.connect(self.update_contrast_slider)

    def update_offset_lineedit(self):
        step_size = float(self.offset_lineEdit_step.text())
        offset = float(self.offset_lineEdit_offset.text())
        steps = self.offset_slider.value()
        value = offset + steps * step_size

        self.offset_lineEdit.setText(str(value))

    def update_offset_slider(self):
        value = float(self.offset_lineEdit.text())
        step_size = float(self.offset_lineEdit_step.text())
        offset = float(self.offset_lineEdit_offset.text())

        steps = int((value - offset) / step_size)
        self.offset_slider.setValue(steps)

    def update_contrast_lineedit(self):
        step_size = float(self.contrast_lineEdit_step.text())
        offset = float(self.contrast_lineEdit_offset.text())
        steps = self.contrast_slider.value()
        value = offset + steps * step_size

        self.contrast_lineEdit.setText(str(value))

    def update_contrast_slider(self):
        value = float(self.contrast_lineEdit.text())
        step_size = float(self.contrast_lineEdit_step.text())
        offset = float(self.contrast_lineEdit_offset.text())

        steps = int((value - offset) / step_size)
        self.contrast_slider.setValue(steps)

    def get_gui_phase_params(self):
        """

        :return:
        """
        # Grating
        kx = float(self.gratingx_lineEdit.text())
        ky = float(self.gratingy_lineEdit.text())

        # Astigmatism
        ax = float(self.astigmatismx_lineEdit.text())
        ay = float(self.astigmatismy_lineEdit.text())

        # Focus
        fcs = float(self.focus_lineEdit.text())

        # Contrast and offset
        contrast = float(self.contrast_lineEdit.text())
        offset = float(self.offset_lineEdit.text())

        return kx, ky, fcs, ax, ay, contrast, offset


class LaguerreSlm(SlmBase):
    """Simple class for creating Laguerre-Gauss beams of arbitrary order and orientation"""
    def __init__(self, *args, **kwargs):
        super(LaguerreSlm, self).__init__(*args, **kwargs)

    def make_phase(self, order, angle, contrast=1, offset=0, focus=0, center=None):
        """

        :param order:
        :param angle:
        :param contrast:
        :param offset:
        :param focus:
        :param center:
        :return:
        """
        if center is None:
            center = [int(x/2) for x in self._shape]

        x = np.arange(self._shape[0]) - center[0]
        y = np.arange(self._shape[1]) - center[1]
        x, y = np.meshgrid(x, y)
        phase = order * (np.angle(x + y * 1j) + angle)  # creates a phase vortex

        # Since np.angle goes form -pi to pi, we offset it and and make it go from 0 to 2pi
        phase += order * np.pi
        phase %= 2 * np.pi - 0.000001

        phase += focus * (x**2 + y**2)

        phase *= contrast
        phase += offset

        return phase

    def get_qt_ui(self):
        return LaguerreSlmUi(self)


class LaguerreSlmUi(SlmBaseUi):
    def __init__(self, slm):
        super(LaguerreSlmUi, self).__init__(slm, 'slm_laguerre.ui')
        self._connect()

    def _connect(self):
        self.offset_lineEdit_step.returnPressed.connect(self.update_offset_lineedit)
        self.offset_lineEdit_offset.returnPressed.connect(self.update_offset_lineedit)
        self.offset_slider.valueChanged.connect(self.update_offset_lineedit)
        self.offset_lineEdit.returnPressed.connect(self.update_offset_slider)

        self.contrast_lineEdit_step.returnPressed.connect(self.update_contrast_lineedit)
        self.contrast_lineEdit_offset.returnPressed.connect(self.update_contrast_lineedit)
        self.contrast_slider.valueChanged.connect(self.update_contrast_lineedit)
        self.contrast_lineEdit.returnPressed.connect(self.update_contrast_slider)

    def update_offset_lineedit(self):
        step_size = float(self.offset_lineEdit_step.text())
        offset = float(self.offset_lineEdit_offset.text())
        steps = self.offset_slider.value()
        value = offset + steps * step_size

        self.offset_lineEdit.setText(str(value))

    def update_offset_slider(self):
        value = float(self.offset_lineEdit.text())
        step_size = float(self.offset_lineEdit_step.text())
        offset = float(self.offset_lineEdit_offset.text())

        steps = int((value - offset) / step_size)
        self.offset_slider.setValue(steps)

    def update_contrast_lineedit(self):
        step_size = float(self.contrast_lineEdit_step.text())
        offset = float(self.contrast_lineEdit_offset.text())
        steps = self.contrast_slider.value()
        value = offset + steps * step_size

        self.contrast_lineEdit.setText(str(value))

    def update_contrast_slider(self):
        value = float(self.contrast_lineEdit.text())
        step_size = float(self.contrast_lineEdit_step.text())
        offset = float(self.contrast_lineEdit_offset.text())

        steps = int((value - offset) / step_size)
        self.contrast_slider.setValue(steps)

    def get_gui_phase_params(self):
        """

        :return:
        """
        contrast = float(self.contrast_lineEdit.text())
        offset = float(self.offset_lineEdit.text())
        angle = float(self.LGangle_lineEdit.text())
        order = int(self.LGorder_lineEdit.text())
        focus = float(self.focus_lineEdit.text())

        return order, angle, contrast, offset, focus


if __name__ == "__main__":
    SLM = SlmCalibration(1)
    # slm = LaguerreSlm(1)
    SLM._logger.setLevel('DEBUG')
    SLM.show_gui()
