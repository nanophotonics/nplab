__author__ = 'alansanders'

from nplab.experiment.gridscanner import GridScannerQT as GridScanner, GridScannerUI
from nplab.instrument.stage import Stage
from nplab.instrument.spectrometer import Spectrometer, Spectrometers
from nplab.instrument.light_sources import LightSource
from nplab.utils.gui import *
import numpy as np
import matplotlib
matplotlib.use('Qt4Agg')
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from time import sleep
from functools import partial
from types import MethodType


class HyperspectralScanner(GridScanner):

        view_layer_updated = QtCore.pyqtSignal(int)

        def __init__(self):
            super(HyperspectralScanner, self).__init__()
            self.spectrometer = Spectrometer()
            self.light_source = LightSource()
            self.num_spectrometers = 1
            self.estimated_step_time = 30e-3
            self.safe_exit = False
            self.delay = 0.

            self.data = None

            self.fig = Figure()
            self.view_wavelength = 600
            self.view_layer = 0
            self.override_view_wavelength = True
            self.override_view_layer = False

        @property
        def view_layer(self):
            return self._view_layer
        @view_layer.setter
        def view_layer(self, value):
            self._view_layer = value
            self.view_layer_updated.emit(value)

        def set_stage(self, stage, move_method=None, pos_method=None):
            assert isinstance(stage, Stage), 'stage must be an instance of Stage'
            self.scanner = stage
            print self.move
            self.move = stage.move_axis
            print self.move
            #self.scanner.configure()
            # move_method = get_move_method(self, self.scanner, self.stage_select)
            # setattr(self, move_method.__name__, MethodType(move_method, self))
            # position_method = get_position_method(self, self.scanner, self.stage_select)
            # setattr(self, position_method.__name__, MethodType(position_method, self))
            # # possibly requires third argument of self.__class__ or HyperspectralAcquisition
            self.set_init_to_current_position()


        def set_spectrometers(self, spectrometers):
            assert isinstance(spectrometers, Spectrometer) or isinstance(spectrometers, Spectrometers),\
            'spectrometer must be an instance of either Spectrometer or Spectrometers'
            self.spectrometer = spectrometers
            if hasattr(spectrometers, '__len__'):
                self.num_spectrometers = len(spectrometers)
            else:
                self.num_spectrometers = 1

        def set_light_source(self, light_source):
            assert isinstance(light_source, LightSource), 'light_source must be an instance of LightSource'
            self.light_source = light_source

        def open_scan(self):
            super(HyperspectralScanner, self).open_scan()
            self.data = np.zeros(self.grid_shape+(100,), dtype=np.float64)
            self.data.fill(np.nan)
            self.fig.clear()

        def close_scan(self):
            super(HyperspectralScanner, self).close_scan()
            sleep(0.1)
            if self.safe_exit:
                self.light_source.power = 0
            #self.scanner.close()

        def scan_function(self, *indices):
            sleep(self.delay)
            if self.num_spectrometers == 1:
                raw_spectrum = self.spectrometer.read_spectrum()
                spectrum = self.spectrometer.process_spectrum(raw_spectrum)
                self.data[indices] = spectrum
            elif self.num_spectrometers > 1:
                pass

            # raw_spectra = self.spectrometers.read_spectra()
            # pairs = zip(raw_spectra, self.spectrometers.spectrometers)
            # spectra = [s[1].process_spectrum(s[0]) for s in pairs]
            # for i in range(len(spectra)):
            #     suffix = str(i+1) if i != 0 else ''
            #     data = self.scan['spectra'+suffix]
            #     data[indices] = spectra[i]
            #     raw_data = self.scan['raw data/spectra'+suffix]
            #     raw_data[indices] = raw_spectra[i]

        def update_axis_image(self, ax, spectrometer, data_id):
            w = abs(spectrometer.read_wavelengths() - self.view_wavelength).argmin()
            suffix = str(data_id+1) if data_id != 0 else ''
            data = self.data#self.scan['spectra'+suffix]

            if self.num_axes == 2:
                latest_view = data[:,:,w]
            elif self.num_axes == 3:
                if self.override_view_layer:
                    k = self.view_layer
                else:
                    k = self.indices[-1]
                    if self.view_layer != k:
                        self.view_layer = k
                latest_view = data[:,:,k,w]
            data = latest_view.transpose()
            if not np.any(np.isfinite(data)):
                return
            if not ax.collections:
                mult = 1./self._unit_conversion[self.size_unit]
                ax.pcolormesh(mult*self.scan_axes[0], mult*self.scan_axes[1], data,
                                   cmap=matplotlib.cm.afmhot)
                cid = self.fig.canvas.mpl_connect('button_press_event', self.onclick)
                cid = self.fig.canvas.mpl_connect('pick_event', self.onpick4)
            else:
                img, = ax.collections
                img.set_array(data[:-1,:-1].ravel())
                img_min = data[np.isfinite(data)].min()
                img_max = data[np.isfinite(data)].max()
                img.set_clim(img_min, img_max)
                ax.relim()
                #self.ax.autoscale_view()
                ax.draw_artist(ax.patch)
                ax.draw_artist(img)

        def update(self):
            if self.data is None or self.fig.canvas is None:
                return
            if self.num_spectrometers == 1:
                if not self.fig.axes:
                    self.ax = self.fig.add_subplot(111)
                    self.ax.set_aspect('equal')
                    mult = 1./self._unit_conversion[self.size_unit]
                    x, y = (mult*self.scan_axes[0], mult*self.scan_axes[1])
                    self.ax.set_xlim(x.min(), x.max())
                    self.ax.set_ylim(y.min(), y.max())
                    self.fig.canvas.draw()
                self.update_axis_image(self.ax, self.spectrometer, 0)
            elif self.num_spectrometers > 1:
                n = len(self.spectrometer)
                for i in range(n):
                    if not self.fig.axes or len(self.fig.axes) != n:
                        self.ax = self.fig.add_subplot(n,1,i+1)
                        self.ax.set_aspect('equal')
                        mult = 1./self._unit_conversion[self.size_unit]
                        x, y = (mult*self.scan_axes[0], mult*self.scan_axes[1])
                        self.ax.set_xlim(x.min(), x.max())
                        self.ax.set_ylim(y.min(), y.max())
                        self.fig.canvas.draw()
                    self.update_axis_image(self.ax, self.spectrometer[i], i)

            if self.fig.canvas is not None:
                self.fig.canvas.update()
                self.fig.canvas.flush_events()
                #self.fig.canvas.draw()

        def get_qt_ui(self):
            return HyperspectralScannerUI(self)

        def start(self, rate=0.2):
            super(HyperspectralScanner, self).start(rate)

        def onclick(self, event):
            init_scale = self._unit_conversion[self.size_unit] / self._unit_conversion[self.init_unit]
            self.init[:2] = (event.xdata * init_scale, event.ydata * init_scale)
            self.init_updated.emit(self.init)

        def onpick4(self, event):
            artist = event.artist
            if isinstance(artist, matplotlib.image.AxesImage):
                im = artist
                A = im.get_array()
                print 'onpick4 image', A.shape

        def update_estimated_step_time(self):
            max_exposure = 1e-3 * max([s.integration_time for s in self.spectrometers.spectrometers])
            max_travel = 100e-3
            self.estimated_step_time = max_exposure + max_travel


class HyperspectralScannerUI(GridScannerUI):
    def __init__(self, grid_scanner):
        assert isinstance(grid_scanner, HyperspectralScanner),\
            'scanner must be an instance of HyperspectralScanner'
        super(HyperspectralScannerUI, self).__init__(grid_scanner)
        self.init_display()

    def init_display(self):
        display_layout = QtGui.QHBoxLayout()

        self.hs_control_layout = QtGui.QVBoxLayout()
        hs_control_group = QtGui.QGroupBox()
        hs_control_group.setTitle('Hyperspectral Controls')
        hs_control_group.setContentsMargins(0,10,0,0)
        hs_control_group.setLayout(self.hs_control_layout)
        display_layout.addWidget(hs_control_group)

        scan_description_label = QtGui.QLabel('Scan Description:', self)
        self.scan_description = QtGui.QLineEdit()
        for widget in [scan_description_label, self.scan_description]:
            widget.setStyleSheet('font-size: 11pt')
            widget.resize(widget.sizeHint())
            self.hs_control_layout.addWidget(widget)
        self.init_stage_select()
        self.init_view_wavelength_controls()
        self.init_view_select()

        self.hs_control_layout.setSizeConstraint(QtGui.QLayout.SetMinimumSize)
        self.canvas = FigureCanvas(self.grid_scanner.fig)
        self.canvas.resize(self.canvas.sizeHint())
        self.canvas.setMaximumSize(300,300)
        display_layout.addWidget(self.canvas)

        display_layout.addStretch()
        self.layout.addLayout(display_layout)

    def init_stage_select(self):
        stage_select_label = QtGui.QLabel('Stage Select:', self)
        stage_select_label.setStyleSheet('font-size: 11pt')
        stage_select_label.resize(stage_select_label.sizeHint())
        self.hs_control_layout.addWidget(stage_select_label)
        self.stage_select = QtGui.QComboBox(self)
        self.stage_select.addItems(['PI', 'SmarAct'])
        self.stage_select.activated[str].connect(self.select_stage)
        self.hs_control_layout.addWidget(self.stage_select)

    def init_view_wavelength_controls(self):
        wavelength_label = QtGui.QLabel('Wavelength:', self)

        self.view_wavelength = QtGui.QLineEdit(self)
        self.view_wavelength.setValidator(QtGui.QIntValidator())
        #self.view_wavelength.textChanged.connect(self.check_state)
        self.view_wavelength.returnPressed.connect(self.on_view_wavelength_change)

        self.wavelength_range = QtGui.QSlider(QtCore.Qt.Horizontal, self)
        self.wavelength_range.setRange(400, 1100)
        self.wavelength_range.setFocusPolicy(QtCore.Qt.NoFocus)
        self.wavelength_range.valueChanged[int].connect(self.on_wavelength_range_change)
        self.wavelength_range.setMinimumWidth(50)

        self.override_view_wavelength = QtGui.QCheckBox(self)
        self.override_view_wavelength.stateChanged.connect(self.on_override_view_wavelength)

        for widget in [wavelength_label, self.view_wavelength,
                       self.wavelength_range, self.override_view_wavelength]:
            widget.setStyleSheet('font-size: 11pt')
            widget.resize(widget.sizeHint())

        self.view_wavelength.setText(str(self.grid_scanner.view_wavelength))
        self.wavelength_range.setValue(self.grid_scanner.view_wavelength)

        wavelength_layout = QtGui.QHBoxLayout()
        wavelength_layout.addWidget(wavelength_label)
        wavelength_layout.addWidget(self.wavelength_range)
        wavelength_layout.addWidget(self.view_wavelength)
        wavelength_layout.addWidget(self.override_view_wavelength)
        self.hs_control_layout.addLayout(wavelength_layout)

    def init_view_select(self):
        view_layer_label = QtGui.QLabel('Layer:', self)

        self.view_layer = QtGui.QLineEdit('0', self)
        self.view_layer.setValidator(QtGui.QIntValidator())
        self.view_layer.textChanged.connect(self.on_view_layer_change)#(partial(setattr, self.grid_scanner, 'view_layer'))
        self.grid_scanner.view_layer_updated.connect(self.on_gs_view_layer_change)

        self.override_view_layer = QtGui.QCheckBox(self)
        self.override_view_layer.stateChanged.connect(self.on_override_view_layer)

        for widget in [view_layer_label, self.view_layer, self.override_view_layer]:
            widget.setStyleSheet('font-size: 11pt')
            widget.resize(widget.sizeHint())

        line_layout = QtGui.QHBoxLayout()
        line_layout.addWidget(view_layer_label)
        line_layout.addWidget(self.view_layer)
        line_layout.addWidget(self.override_view_layer)
        self.hs_control_layout.addLayout(line_layout)

    def select_stage(self, name):
        print name

    def on_view_wavelength_change(self, *args, **kwargs):
        """
        This function is called by the power text box.
        :param args:
        :param kwargs:
        :return:
        """
        print self.view_wavelength.text()
        value = int(self.view_wavelength.text())
        #self.wavelength_range.valueChanged[int].emit(value)
        self.wavelength_range.setValue(value)

    def on_wavelength_range_change(self, value):
        """
        This function is called by the power slider.
        :param value:
        :return:
        """
        self.grid_scanner.view_wavelength = value
        self.view_wavelength.setText('%d' % value)

    def on_override_view_wavelength(self, state):
        if state == QtCore.Qt.Checked:
            self.grid_scanner.override_view_wavelength = True
        else:
            self.grid_scanner.override_view_wavelength = False

    def on_view_layer_change(self, *args, **kwargs):
        self.grid_scanner.view_layer = int(self.view_layer.text())

    def on_gs_view_layer_change(self, value):
        self.view_layer.setText(str(value))

    def on_override_view_layer(self, state):
        if state == QtCore.Qt.Checked:
            self.grid_scanner.override_view_layer = True
        else:
            self.grid_scanner.override_view_layer = False


if __name__ == '__main__':
    import sys
    from nplab.instrument.stage import DummyStage

    class DummySpectrometer(Spectrometer):
        def __init__(self):
            pass
        def read_spectrum(self):
            #sleep(0.001)
            return np.random.rand(100)
        def read_wavelengths(self):
            return np.linspace(0,1000,100)

    gs = HyperspectralScanner()
    gs.set_stage(DummyStage())
    gs.set_spectrometers(DummySpectrometer())
    gui = gs.get_qt_ui()
    app = get_qt_app()
    gui.show()
    sys.exit(app.exec_())
