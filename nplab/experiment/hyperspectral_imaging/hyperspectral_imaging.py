from __future__ import division
from __future__ import print_function
from builtins import zip
from builtins import str
from builtins import range
from past.utils import old_div
__author__ = 'alansanders'

from nplab.experiment.scanning_experiment import ScanningExperimentHDF5, GridScanQt
from nplab.instrument.stage import Stage
from nplab.instrument.spectrometer import Spectrometer, Spectrometers
from nplab.instrument.light_sources import LightSource
from nplab.instrument.shutter import Shutter
from nplab.utils.gui import *
from nplab.utils.gui import uic
from nplab.ui.ui_tools import UiTools
import numpy as np
import matplotlib
import warnings
import time

matplotlib.use('Qt4Agg')
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.gridspec as gridspec
#from nplab.ui.mpl_gui import FigureCanvasWithDeferredDraw as FigureCanvas
from matplotlib.figure import Figure
from functools import partial
from types import MethodType
import inspect
from nplab.ui.hdf5_browser import HDF5Browser

import pyqtgraph as pg
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

# TODO: hyperspectral image renderer


class HyperspectralScan(GridScanQt, ScanningExperimentHDF5):
    view_layer_updated = QtCore.Signal(int)

    def __init__(self):
        GridScanQt.__init__(self)
        ScanningExperimentHDF5.__init__(self)
        self.spectrometer = None
        self.light_source = None
        self.num_spectrometers = 1
        self.safe_exit = False
        self.delay = 0.

        self.fig = None#Figure()
        self._created = False
        self.view_wavelength = 600
        self.view_layer = 0
        self.override_view_layer = False  # used to manually show a specific layer instead of current one scanning

    @property
    def view_layer(self):
        return self._view_layer

    @view_layer.setter
    def view_layer(self, value):
        self._view_layer = value
        self.view_layer_updated.emit(value)

    def set_spectrometers(self, spectrometers):
        if not isinstance(spectrometers, (Spectrometer, Spectrometers)):
            raise ValueError('spectrometer must be an instance of either Spectrometer or '
                             'Spectrometers')
        self.spectrometer = spectrometers
        if isinstance(spectrometers, Spectrometers):
            self.num_spectrometers = len(spectrometers.spectrometers)
        else:
            self.num_spectrometers = 1

    def set_light_source(self, light_source):
        assert isinstance(light_source, LightSource), 'light_source must be an instance of LightSource'
        self.light_source = light_source

    @staticmethod
    def _suffix(i):
        return '{}'.format(i+1) if i != 0 else ''

    def init_scan(self):
        # these checks are performed in case equipment is set without using the set_ method
        if not isinstance(self.stage, Stage):
            raise ValueError('stage must be a Stage')
        if not isinstance(self.spectrometer, (Spectrometer, Spectrometers)):
            raise ValueError('spectrometer must be a Spectrometer or Spectrometers')
        # if not self._created:
        #     self.init_figure()

    def open_scan(self):
        super(HyperspectralScan, self).open_scan()
        group = self.f.require_group('hyperspectral_images')
        self.data = group.create_group('scan_%d', attrs=dict(description=self.description))
        print('Saving scan to: {}'.format(self.f.file.filename), self.data)
        raw_group = self.data.create_group('raw_data')
        for axis_name, axis_values in zip(self.axes_names, self.scan_axes):
            self.data.create_dataset(axis_name, data=axis_values)
        for i in range(self.num_spectrometers):
            suffix = self._suffix(i)
            spectrometer = self.spectrometer.spectrometers[i]\
                if isinstance(self.spectrometer, Spectrometers) else self.spectrometer
            self.data.create_dataset('wavelength'+suffix, data=spectrometer.wavelengths)
            self.data.create_dataset('hs_image'+suffix,
                                     shape=self.grid_shape + (spectrometer.wavelengths.size,),
                                     dtype=np.float64,
                                     attrs=spectrometer.metadata)
            self.data.create_dataset('raw_data/hs_image'+suffix,
                                     shape=self.grid_shape + (spectrometer.wavelengths.size,),
                                     dtype=np.float64,
                                     attrs=spectrometer.metadata)
        if isinstance(self.spectrometer, Spectrometer):
            self.read_spectra = self.spectrometer.read_spectrum
            self.process_spectra = self.spectrometer.process_spectrum
        elif isinstance(self.spectrometer, Spectrometers):
            self.read_spectra = self.spectrometer.read_spectra
            self.process_spectra = self.spectrometer.process_spectra
        self.init_figure()

    def close_scan(self):
        super(HyperspectralScan, self).close_scan()
        self.data.file.flush()
        time.sleep(0.1)
        if self.safe_exit:
            if isinstance(self.light_source.shutter, Shutter):
                self.light_source.shutter.toggle()
            else:
                self.light_source.power = 0

    def scan_function(self, *indices):
        time.sleep(self.delay)
        raw_spectra = self.read_spectra()
        spectra = self.process_spectra(raw_spectra)
        self.data['raw_data/hs_image'+self._suffix(0)][indices] = raw_spectra
        self.data['hs_image'+self._suffix(0)][indices] = spectra
#        for i, (spectrum, raw_spectrum) in enumerate(zip(spectra, raw_spectra)):
#            try:
#                suffix = self._suffix(i)
#                self.data['raw_data/hs_image'+suffix][indices] = raw_spectrum
#                self.data['hs_image'+suffix][indices] = spectrum
#            except Exception as e:
#                print e
        self.check_for_data_request(*self.set_latest_view(*indices))

    def set_latest_view(self, *indices):
        view_data = []
        for i in range(self.num_spectrometers):
            suffix = self._suffix(i)
            spectrometer = self.spectrometer.spectrometers[i]\
                if isinstance(self.spectrometer, Spectrometers) else self.spectrometer
            w = abs(spectrometer.wavelengths - self.view_wavelength).argmin()
            data = self.data['hs_image'+suffix]
            if self.num_axes == 2:
                latest_view = data[:, :, w]
                spectrum = self.data['hs_image'+suffix][indices[-2], indices[-1], :]
            elif self.num_axes == 3:
                if self.override_view_layer:
                    k = self.view_layer
                else:
                    k = self.indices[0]
                    if self.view_layer != k:
                        self.view_layer = k
                latest_view = data[k, :, :, w]
                spectrum = self.data['hs_image'+suffix][k, indices[-2], indices[-1], :]
            spectrum = spectrometer.mask_spectrum(spectrum, 0.05)
            view_data += [latest_view, spectrometer.wavelengths, spectrum]
        return tuple(view_data)

    def init_figure(self):
        if self.fig is None:
            return
        self.fig.clear()
        gs = gridspec.GridSpec(2, 2, hspace=0.5, wspace=0.5)
        ax1 = self.fig.add_subplot(gs[0,0])
        ax2 = self.fig.add_subplot(gs[0,1])
        for ax in (ax1, ax2):
            ax.set_xlabel('$x$')
            ax.set_ylabel('$y$')
            ax.set_aspect('equal')
            mult = 1./self._unit_conversion[self.step_unit]
            x, y = (mult*self.scan_axes[-1], mult*self.scan_axes[-2])
            ax.set_xlim(x.min(), x.max())
            ax.set_ylim(y.min(), y.max())
        ax3 = self.fig.add_subplot(gs[1,:])
        ax3.set_xlabel('wavelength (nm)')
        ax3.set_ylabel('intensity (a.u.)')
        ax4 = ax3.twinx()
        ax4.set_ylabel('intensity (a.u.)')
        gs.tight_layout(self.fig)
        cid = self.fig.canvas.mpl_connect('button_press_event', self.on_mouse_click)
        # pos = np.array([0.0, 0.2, 0.5, 1.0])
        # color = np.array([[0,0,0,255], [255,0,0,255], [255,255,0,255], [255,255,255,255]], dtype=np.ubyte)
        # map = pg.ColorMap(pos, color)
        # lut = map.getLookupTable(0.0, 1.0, 256)
        #
        # self.spectrum_plots = [pg.PlotCurveItem() for i in xrange(self.num_spectrometers)]
        # self.image_plots = [pg.ImageItem(lut=lut) for i in xrange(self.num_spectrometers)]
        # for item in self.image_plots:
        #     plot = self.fig.addPlot()
        #     plot.addItem(item)
        #     plot.setAspectLocked(True)
        #     rect=np.array([-self.size[0]/2.,-self.size[1]/2.,
        #                    self.size[0], self.size[1]])
        #     rect /= (self._unit_conversion[self.step_unit]/self._unit_conversion[self.size_unit])
        #     item.setImage(np.zeros((self.si_size[1]/self.si_step[1],
        #                             self.si_size[0]/self.si_step[0])))
        #     item.setRect(QtCore.QRectF(*rect))
        # self.fig.nextRow()
        # plot = self.fig.addPlot()
        # for item in self.spectrum_plots:
        #     plot.addItem(item)
        # self._created = True

    def update(self, force=False):
        super(HyperspectralScan, self).update(force)
        if not self.fig:
            return
        if force:
            data = self.set_latest_view(*self.indices)
        else:
            data = self.request_data()
        if data is not False:
            grouped_data = [data[i:i+3] for i in range(0,len(data),3)]
            colours = ['r', 'b', 'g']
            for i, data_group in enumerate(grouped_data):
                img, wavelengths, spectrum = data_group
                if not np.any(np.isfinite(img)):
                    return
                # self.image_plots[i].setImage(img)
                # self.spectrum_plots[i].setData(x=wavelengths, y=spectrum, pen=colours[i])

                ax = self.fig.axes[i]
                if not ax.collections:
                    mult = 1. / self._unit_conversion[self.step_unit]
                    ax.pcolormesh(mult * self.scan_axes[-1], mult * self.scan_axes[-2], img,
                                  cmap=matplotlib.cm.afmhot)
                else:
                    plot, = ax.collections
                    plot.set_array(img[:-1, :-1].ravel())
                    img_min = img[np.isfinite(img)].min()
                    img_max = img[np.isfinite(img)].max()
                    plot.set_clim(img_min, img_max)
                    ax.relim()
                    #ax.draw_artist(ax.patch)
                    #ax.draw_artist(plot)
                ax = self.fig.axes[i+2]
                c = 'r' if i == 0 else 'b'
                if not ax.lines:
                    ax.plot(wavelengths, spectrum, c=c)
                else:
                    plot, = ax.lines
                    plot.set_data(wavelengths, spectrum)
                    ax.relim()
                    ax.autoscale_view()
            #self.fig.canvas.update()
            #self.fig.canvas.flush_events()
            self.fig.canvas.draw()

    @property
    def estimated_step_time(self):
        if isinstance(self.spectrometer, Spectrometer):
            max_exposure = self.spectrometer.integration_time
        elif isinstance(self.spectrometer, Spectrometers):
            max_exposure = 1e-3 * max([s.integration_time for s in self.spectrometer.spectrometers])
        else:
            max_exposure = 0
            warnings.warn('No integration time as spectrometer is not a valid instance of Spectrometer or Spectrometers.')
        max_travel = 100e-3
        #self.estimated_step_time = max_exposure + max_travel
        return max_exposure + max_travel

    @estimated_step_time.setter
    def estimated_step_time(self, value):
        print(value)

    def get_qt_ui(self):
        return HyperspectralScanUI(self)

    def on_mouse_click(self, event):
        init_scale = old_div(self._unit_conversion[self.step_unit], self._unit_conversion[self.init_unit])
        self.init[:2] = (event.xdata * init_scale, event.ydata * init_scale)
        self.init_updated.emit(self.init)
    #     pos = event.scenePos()
    #     print "Image position:", self.image_plots[0].mapFromScene(pos)


class HyperspectralScanUI(QtWidgets.QWidget, UiTools):
    def __init__(self, grid_scanner, parent=None):
        assert isinstance(grid_scanner, HyperspectralScan), \
            'scanner must be an instance of HyperspectralScan'
        super(HyperspectralScanUI, self).__init__()
        self.grid_scanner = grid_scanner
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'hyperspectral_imaging.ui'), self)
        self.gridscanner_widget = self.replace_widget(self.main_layout, self.gridscanner_widget,
                                                      GridScanQt.get_qt_ui_cls()(self.grid_scanner))
        self.gridscanner_widget.rate = 1./20.

        self.grid_scanner.fig = Figure()  # pg.GraphicsLayoutWidget()
        # self.grid_scanner.fig.scene().sigMouseClicked.connect(self.grid_scanner.on_mouse_click)
        self.figure_widget = self.replace_widget(self.main_layout, self.figure_widget,
                                                 FigureCanvas(self.grid_scanner.fig))

        self.init_stage_select()
        self.init_view_wavelength_controls()
        self.init_view_select()

        self.scan_description.textChanged.connect(self.update_param)
        self.safe_exit.stateChanged.connect(self.on_state_change)

        self.config_stage.clicked.connect(self.on_click)
        self.config_spectrometers.clicked.connect(self.on_click)
        self.config_light_source.clicked.connect(self.on_click)
        self.open_browser.clicked.connect(self.on_click)

    def init_stage_select(self):
        self.stage_select.addItems(['PI', 'SmarAct'])
        self.stage_select.activated[str].connect(self.select_stage)

    def init_view_wavelength_controls(self):
        self.view_wavelength.setValidator(QtGui.QIntValidator())
        # self.view_wavelength.textChanged.connect(self.check_state)
        self.view_wavelength.returnPressed.connect(self.on_view_wavelength_change)

        min_wl = np.min(self.grid_scanner.spectrometer.wavelengths)
        max_wl = np.max(self.grid_scanner.spectrometer.wavelengths)
        self.wavelength_range.setRange(min_wl, max_wl)
        self.wavelength_range.setFocusPolicy(QtCore.Qt.NoFocus)
        self.wavelength_range.valueChanged[int].connect(self.on_wavelength_range_change)

        self.view_wavelength.setText(str(self.grid_scanner.view_wavelength))
        self.wavelength_range.setValue(self.grid_scanner.view_wavelength)

    def init_view_select(self):
        self.view_layer.setValidator(QtGui.QIntValidator())
        self.view_layer.textChanged.connect(
            self.on_view_layer_change)  # (partial(setattr, self.grid_scanner, 'view_layer'))
        self.grid_scanner.view_layer_updated.connect(self.on_gs_view_layer_change)

        self.override_view_layer.stateChanged.connect(self.on_override_view_layer)

    def update_param(self, *args, **kwargs):
        sender = self.sender()
        if sender == self.scan_description:
            self.grid_scanner.description = self.scan_description.toPlainText().encode('utf8')

    def select_stage(self, name):
        print(name)

    def on_click(self):
        sender = self.sender()
        if sender == self.config_stage:
            self.stage_ui = self.grid_scanner.stage.get_qt_ui()
            self.stage_ui.show()
        elif sender == self.config_spectrometers:
            self.spectrometers_ui = self.grid_scanner.spectrometer.get_qt_ui()
            self.spectrometers_ui.show()
        elif sender == self.config_light_source:
            self.light_source_ui = self.grid_scanner.light_source.get_qt_ui()
            self.light_source_ui.show()
            pass
        elif sender == self.open_browser:
            if self.grid_scanner.f is not None:
                print(self.grid_scanner.f)
                self.browser = HDF5Browser(self.grid_scanner.f)
                self.browser.show()

    def on_state_change(self, state):
        sender = self.sender()
        if sender is self.safe_exit:
            if state == QtCore.Qt.Checked:
                self.grid_scanner.safe_exit = True
            elif state == QtCore.Qt.Unchecked:
                self.grid_scanner.safe_exit = False

    def on_view_wavelength_change(self, *args, **kwargs):
        """
        This function is called by the power text box.

        :param args:
        :param kwargs:
        :return:
        """
        print(self.view_wavelength.text())
        value = int(self.view_wavelength.text())
        # self.wavelength_range.valueChanged[int].emit(value)
        self.wavelength_range.setValue(value)

    def on_wavelength_range_change(self, value):
        """
        This function is called by the power slider.

        :param value:
        :return:
        """
        self.grid_scanner.view_wavelength = value
        self.view_wavelength.setText('%d' % value)

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
    from nplab.instrument.spectrometer import DummySpectrometer, Spectrometers
    from nplab import datafile

    f = datafile.get_file()

    stage = DummyStage()
    stage.axis_names = ('x', 'y', 'z')
    spectrometers = Spectrometers([DummySpectrometer(), DummySpectrometer()])

    gs = HyperspectralScan()
    gs.num_axes = 2
    gs.set_stage(stage)
    gs.set_spectrometers(spectrometers)
    app = get_qt_app()
    gui = gs.get_qt_ui()
    gui.show()
    sys.exit(app.exec_())
