__author__ = 'alansanders'

from nplab.instrument import Instrument
import numpy as np
import numpy.ma as ma
from nplab.utils.gui import *
from PyQt4 import uic
import matplotlib
matplotlib.use('Qt4Agg')
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from nplab.ui.ui_tools import UiTools
import h5py
from multiprocessing.pool import ThreadPool


class Spectrometer(Instrument):

    def __init__(self):
        super(Spectrometer, self).__init__()
        self._model_name = None
        self._serial_number = None
        self._wavelengths = None
        self.reference = None
        self.background = None
        self.latest_raw_spectrum = None
        self.latest_spectrum = None

    @property
    def model_name(self):
        if self._model_name is None:
            self._model_name = 'model_name'
        return self._model_name

    @property
    def serial_number(self):
        if self._serial_number is None:
            self._serial_number = 'serial_number'
        return self._serial_number

    def get_integration_time(self):
        return 0

    def set_integration_time(self, value):
        print 'setting 0'

    integration_time = property(get_integration_time, set_integration_time)

    @property
    def wavelengths(self):
        if self._wavelengths is None:
            self._wavelengths = np.arange(400,1200,1)
        return self._wavelengths

    def read_spectrum(self):
        self.latest_raw_spectrum = np.zeros(0)
        return self.latest_raw_spectrum

    def read_background(self):
        self.background = self.read_spectrum()

    def clear_background(self):
        self.background = None

    def read_reference(self):
        self.reference = self.read_spectrum()

    def clear_reference(self):
        self.reference = None

    def is_background_compensated(self):
        return len(self.background)==len(self.latest_raw_spectrum) and \
            sum(self.background)>0

    def is_referenced(self):
        return self.is_background_compensated and \
            len(self.reference)==len(self.latest_raw_spectrum) and \
            sum(self.reference)>0

    def process_spectrum(self, spectrum):
        if self.background is not None:
            if self.reference is not None:
                old_error_settings = np.seterr(all='ignore')
                new_spectrum = (spectrum - self.background)/(self.reference - self.background)
                np.seterr(**old_error_settings)
                new_spectrum[np.isinf(new_spectrum)] = np.NaN #if the reference is nearly 0, we get infinities - just make them all NaNs.
            else:
                new_spectrum = spectrum - self.background
        else:
            new_spectrum = spectrum
        return new_spectrum

    def read_processed_spectrum(self):
        spectrum = self.read_spectrum()
        self.latest_spectrum = self.process_spectrum(spectrum)
        return self.latest_spectrum

    def read(self):
        return self.wavelengths, self.read_processed_spectrum()

    def mask_spectrum(self, spectrum, threshold):
        if self.reference is not None and self.background is not None:
            reference = self.reference - self.background
            mask = reference < reference.max() * threshold
            return ma.array(spectrum, mask=mask)
        else:
            return spectrum

    def get_qt_ui(self, control_only=False):
        if control_only:
            return SpectrometerControlUI(self)
        else:
            return SpectrometerUI(self)

    def save_spectrum(self, name, spectrum=None, h5group=None, with_attrs={'background', 'reference', 'wavelengths'}):
        spectrum = self.read_processed_spectrum() if spectrum is None else spectrum
        dset = h5group.create_dataset(name, data=spectrum)
        if with_attrs is not {}:
            for attr in with_attrs:
                dset.attrs[attr] = getattr(self, attr)

    def save_reference_to_file(self):
        pass

    def load_reference_from_file(self):
        pass


class Spectrometers(Instrument):
    def __init__(self, spectrometer_list):
        assert False not in [isinstance(s, Spectrometer) for s in spectrometer_list],\
            'an invalid spectrometer was supplied'
        super(Spectrometers, self).__init__()
        self.spectrometers = spectrometer_list
        self.num_spectrometers = len(spectrometer_list)
        self._pool = ThreadPool(processes=self.num_spectrometers)
        self._wavelengths = None

    def __del__(self):
        self._pool.close()

    def add_spectrometer(self, spectrometer):
        assert isinstance(spectrometer, Spectrometer), 'spectrometer must be an instance of Spectrometer'
        if spectrometer not in self.spectrometers:
            self.spectrometers.append(spectrometer)
            self.num_spectrometers = len(self.spectrometers)

    @property
    def wavelengths(self):
        if self._wavelengths is None:
            self._wavelengths = [s.wavelengths for s in self.spectrometers]
        return self._wavelengths

    def read_spectra(self):
        return self._pool.map(lambda s: s.read_spectrum(), self.spectrometers)

    def read_processed_spectra(self):
        return self._pool.map(lambda s: s.read_processed_spectrum(), self.spectrometers)

    def mask_spectra(self, spectra, threshold):
        return [spectrometer.mask_spectrum(spectrum, threshold) for (spectrometer, spectrum) in zip(self.spectrometers, spectra)]

    def get_qt_ui(self):
        return SpectrometersUI(self)

    def save_spectra(self, name, spectra=None, h5group=None, with_attrs={'background', 'reference', 'wavelengths'}):
        spectra = self.read_processed_spectra() if spectra is None else spectra
        for i,spectrum in enumerate(spectra):
            suffix = str(i) if i>0 else ''
            dset = h5group.create_dataset(name+suffix, data=spectra[i])
            if with_attrs is not {}:
                for attr in with_attrs:
                    dset.attrs[attr] = getattr(self.spectrometers[i], attr)


controls_base, controls_widget = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'spectrometer_controls.ui'))
display_base, display_widget = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'spectrometer_view.ui'))


class SpectrometerControlUI(UiTools, controls_base, controls_widget):
    def __init__(self, spectrometer, parent=None):
        assert isinstance(spectrometer, Spectrometer), "instrument must be a Spectrometer"
        super(SpectrometerControlUI, self).__init__()
        self.spectrometer = spectrometer
        self.setupUi(self)

        self.integration_time.setValidator(QtGui.QDoubleValidator())
        self.integration_time.textChanged.connect(self.check_state)
        self.integration_time.textChanged.connect(self.update_param)

        self.read_background_button.clicked.connect(self.button_pressed)
        self.read_reference_button.clicked.connect(self.button_pressed)
        self.clear_background_button.clicked.connect(self.button_pressed)
        self.clear_reference_button.clicked.connect(self.button_pressed)

        self.background_subtracted.stateChanged.connect(self.state_changed)
        self.referenced.stateChanged.connect(self.state_changed)

        self.id_string.setText('{0} {1}'.format(self.spectrometer.model_name, self.spectrometer.serial_number))
        self.id_string.resize(self.id_string.sizeHint())

        self.integration_time.setText(str(spectrometer.integration_time))

    def update_param(self, *args, **kwargs):
        sender = self.sender()
        if sender is self.integration_time:
            try:
                self.spectrometer.integration_time = float(args[0])
            except ValueError:
                pass

    def button_pressed(self, *args, **kwargs):
        sender = self.sender()
        if sender is self.read_background_button:
            self.spectrometer.read_background()
            self.background_subtracted.setChecked(True)
        elif sender is self.clear_background_button:
            self.spectrometer.clear_background()
            self.background_subtracted.setChecked(False)
        elif sender is self.read_reference_button:
            self.spectrometer.read_reference()
            self.referenced.setChecked(True)
        elif sender is self.clear_reference_button:
            self.spectrometer.clear_reference()
            self.referenced.setChecked(False)

    def state_changed(self, state):
        sender = self.sender()
        if sender is self.background_subtracted and state == QtCore.Qt.Checked:
            self.spectrometer.read_background()
        elif sender is self.background_subtracted and state == QtCore.Qt.Unchecked:
            self.spectrometer.clear_background()
        if sender is self.referenced and state == QtCore.Qt.Checked:
            self.spectrometer.read_reference()
        elif sender is self.referenced and state == QtCore.Qt.Unchecked:
            self.spectrometer.clear_reference()


class SpectrometerDisplayUI(UiTools, display_base, display_widget):
    def __init__(self, spectrometer, parent=None):
        assert isinstance(spectrometer, Spectrometer) or isinstance(spectrometer, Spectrometers),\
            "instrument must be a Spectrometer or an instance of Spectrometers"
        super(SpectrometerDisplayUI, self).__init__()
        self.spectrometer = spectrometer
        self.setupUi(self)
        self.fig = Figure()
        self.figure_widget = self.replace_widget(self.display_layout,
                                                 self.figure_widget, FigureCanvas(self.fig))

        self.take_spectrum_button.clicked.connect(self.button_pressed)
        self.live_button.clicked.connect(self.check_updating)

        self.threshold.setValidator(QtGui.QDoubleValidator())
        self.threshold.textChanged.connect(self.check_state)

    def button_pressed(self, *args, **kwargs):
        sender = self.sender()
        if sender is self.take_spectrum_button:
            read_processed_spectrum = self.spectrometer.read_processed_spectra \
                if isinstance(self.spectrometer, Spectrometers) \
                else self.spectrometer.read_processed_spectrum
            spectrum = read_processed_spectrum()
            self.update_display(spectrum)
        elif sender is self.save_button:
            save_spectrum = self.spectrometer.save_spectra \
                if isinstance(self.spectrometer, Spectrometers) \
                else self.spectrometer.save_spectrum
            save_spectrum()

    def update_display(self, spectrum=None):
        if spectrum is None:
            read_processed_spectrum = self.spectrometer.read_processed_spectra \
                if isinstance(self.spectrometer, Spectrometers) \
                else self.spectrometer.read_processed_spectrum
            spectrum = read_processed_spectrum()
        if self.enable_threshold.checkState() == QtCore.Qt.Checked:
            threshold = float(self.threshold.text())
            if isinstance(self.spectrometer, Spectrometers):
                spectrum = [spectrometer.mask_spectrum(s, threshold) for (spectrometer, s) in zip(self.spectrometer.spectrometers, spectrum)]
            else:
                spectrum = self.spectrometer.mask_spectrum(spectrum, threshold)
        if not self.fig.axes:
            if hasattr(spectrum, '__len__'):
                ax = self.fig.add_subplot(111)
                ax.plot(self.spectrometer.wavelengths[0], spectrum[0], 'r-')
                ax2 = ax.twinx()
                ax2.plot(self.spectrometer.wavelengths[1], spectrum[1], 'b-')
            else:
                ax = self.fig.add_subplot(111)
                ax.plot(self.spectrometer.wavelengths, spectrum, 'r-')
        else:
            if hasattr(spectrum, '__len__'):
                ax, ax2 = self.fig.axes
                for i, axis in enumerate([ax, ax2]):
                    l, = axis.lines
                    l.set_data(self.spectrometer.wavelengths[i], spectrum[i])
                    axis.relim()
                    axis.autoscale_view()
            else:
                ax, = self.fig.axes
                l, = ax.lines
                l.set_data(self.spectrometer.wavelengths, spectrum)
                ax.relim()
                ax.autoscale_view()
        self.fig.canvas.draw()

    def check_updating(self, period=0.2):
        if self.live_button.isChecked():
            print 'updating'
            self._timer = QtCore.QTimer()
            self._timer.timeout.connect(self.update_display)
            self._timer.start(period)
        else:
            print 'stopped updating'
            self._timer.stop()


class SpectrometerUI(QtGui.QWidget):
    """
    Joins together the control and display UIs into a single spectrometer UI.
    """

    def __init__(self, spectrometer):
        assert isinstance(spectrometer, Spectrometer), "instrument must be a Spectrometer"
        super(SpectrometerUI, self).__init__()
        self.spectrometer = spectrometer
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle(self.spectrometer.__class__.__name__)
        self.controls = self.spectrometer.get_qt_ui(control_only=True)
        self.display = SpectrometerDisplayUI(self.spectrometer)
        layout = QtGui.QVBoxLayout()
        controls_layout = QtGui.QVBoxLayout()
        controls_layout.addWidget(self.controls)
        controls_layout.setContentsMargins(0,0,0,0)
        controls_group = QtGui.QGroupBox()
        controls_group.setTitle('Spectrometer')
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        layout.addWidget(self.display)
        layout.setContentsMargins(5,5,5,5)
        layout.setSpacing(5)
        self.setLayout(layout)


class SpectrometersUI(QtGui.QWidget):
    def __init__(self, spectrometers):
        assert isinstance(spectrometers, Spectrometers), "instrument must be an instance of Spectrometers"
        super(SpectrometersUI, self).__init__()
        self.spectrometers = spectrometers
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle('Spectrometers')
        self.controls_layout = QtGui.QHBoxLayout()
        controls_group = QtGui.QGroupBox()
        controls_group.setTitle('Spectrometers')
        controls_group.setLayout(self.controls_layout)
        self.controls = []
        for spectrometer in self.spectrometers.spectrometers:
            control = spectrometer.get_qt_ui(control_only=True)
            self.controls_layout.addWidget(control)
            self.controls.append(control)
        self.display = SpectrometerDisplayUI(self.spectrometers)
        layout = QtGui.QVBoxLayout()
        layout.addWidget(controls_group)
        layout.addWidget(self.display)
        self.setLayout(layout)


class DummySpectrometer(Spectrometer):
    def __init__(self):
        super(DummySpectrometer, self).__init__()

    def read_spectrum(self):
        return np.array([np.random.random() for wl in self.wavelengths])


if __name__ == '__main__':
    import sys
    from nplab.utils.gui import get_qt_app
    s1 = DummySpectrometer()
    s2 = DummySpectrometer()
    spectrometers = Spectrometers([s1, s2])
    app = get_qt_app()
    ui = SpectrometersUI(spectrometers)
    ui.show()
    sys.exit(app.exec_())