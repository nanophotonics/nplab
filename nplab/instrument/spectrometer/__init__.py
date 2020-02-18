from __future__ import division
from __future__ import print_function
from builtins import str
from builtins import zip
from builtins import range
from past.utils import old_div
__author__ = 'alansanders'

import numpy as np
import numpy.ma as ma
from nplab.utils.gui import QtCore, QtGui, QtWidgets, get_qt_app, uic

from collections import deque

from nplab.ui.ui_tools import UiTools
import nplab.datafile as df
from nplab.datafile import DataFile
from nplab.utils.notified_property import NotifiedProperty, DumbNotifiedProperty, register_for_property_changes
from nplab.utils.array_with_attrs import ArrayWithAttrs
import h5py
from multiprocessing.pool import ThreadPool
from nplab.experiment.gui import run_function_modally

import time

import os
import inspect
import datetime
from nplab.instrument import Instrument
import warnings
import pyqtgraph as pg
from weakref import WeakSet


class Spectrometer(Instrument):

    metadata_property_names = ('model_name', 'serial_number', 'integration_time',
                               'reference', 'background', 'wavelengths',
                               'background_int', 'reference_int','variable_int_enabled',
                               'background_gradient','background_constant', 'averaging_enabled'
                               ,'absorption_enabled')
   
    variable_int_enabled = DumbNotifiedProperty(False)
    filename = DumbNotifiedProperty("spectrum")

    def __init__(self):
        super(Spectrometer, self).__init__()
        self._model_name = None
        self._serial_number = None
        self._wavelengths = None
        self.reference = None
        self.background = None
        self.background_constant =None
        self.background_gradient = None
        self.background_int = None
        self.reference_int = None
      #  self.variable_int_enabled = DumbNotifiedProperty(False)
        self.latest_raw_spectrum = None
        self.latest_spectrum = None
        self.averaging_enabled = False
        self.spectra_deque = deque(maxlen = 1)
        self.absorption_enabled = False
        self._config_file = None

        self.stored_references = {}
        self.stored_backgrounds = {}
        self.reference_ID = 0
        self.spectra_buffer = np.zeros(0)
        self.data_file = df.current()
        self.curr_scan=None
        self.num_spectra = 1
        self.delay = 0
        self.time_series_name = 'time_series_%d'


    def __del__(self):
        try:
            self._config_file.close()
        except AttributeError:
            pass #if it's not present, we get an exception - which doesn't matter.

    def open_config_file(self):
        """Open the config file for the current spectrometer and return it, creating if it's not there"""
        if self._config_file is None:
            f = inspect.getfile(self.__class__)
            d = os.path.dirname(f)
            self._config_file = DataFile(h5py.File(os.path.join(d, 'config.h5')))
            self._config_file.attrs['date'] = datetime.datetime.now().strftime("%H:%M %d/%m/%y")
        return self._config_file

    config_file = property(open_config_file)

    def update_config(self, name, data, attrs= None):
        """Update the configuration file for this spectrometer.
        
        A file is created in the nplab directory that holds configuration
        data for the spectrometer, including reference/background.  This
        function allows values to be stored in that file."""
        f = self.config_file
        if name not in f:
            f.create_dataset(name, data=data ,attrs = attrs)
        else:
            dset = f[name]
            dset[...] = data
            f.flush()

    def get_model_name(self):
        """The model name of the spectrometer."""
        if self._model_name is None:
            self._model_name = 'model_name'
        return self._model_name

    model_name = property(get_model_name)

    def get_serial_number(self):
        """The spectrometer's serial number (as a string)."""
        warnings.warn("Using the default implementation for get_serial_number: this should be overridden!",DeprecationWarning)
        if self._serial_number is None:
            self._serial_number = 'serial_number'
        return self._serial_number

    serial_number = property(get_serial_number)

    def get_integration_time(self):
        """The integration time of the spectrometer (this function is a stub)!"""
        warnings.warn("Using the default implementation for integration time: this should be overridden!",DeprecationWarning)
        return 0

    def set_integration_time(self, value):
        """Set the integration time of the spectrometer (this is a stub)!"""
        warnings.warn("Using the default implementation for integration time: this should be overridden!",DeprecationWarning)
        print('setting 0')

    integration_time = property(get_integration_time, set_integration_time)

    def get_wavelengths(self):
        """An array of wavelengths corresponding to the spectrometer's pixels."""
        warnings.warn("Using the default implementation for wavelengths: this should be overridden!",DeprecationWarning)

        if self._wavelengths is None:
            self._wavelengths = np.arange(400,1200,1)
        return self._wavelengths

    wavelengths = property(get_wavelengths)

    def read_spectrum(self, bundle_metadata=False):
        """Take a reading on the spectrometer and return it"""
        warnings.warn("Using the default implementation for read_spectrum: this should be overridden!",DeprecationWarning)
        self.latest_raw_spectrum = np.zeros(0)
        return self.bundle_metadata(self.latest_raw_spectrum, enable=bundle_metadata)

    def read_background(self):
        """Acquire a new spectrum and use it as a background measurement.
        This background should be less than 50% of the spectrometer saturation"""
        if self.averaging_enabled == True:
            background_1 = np.average(self.read_averaged_spectrum(True,True),axis=0)
        else:
            background_1 = self.read_spectrum()
        self.integration_time = 2.0*self.integration_time
        if self.averaging_enabled == True:
            background_2 = np.average(self.read_averaged_spectrum(True,True),axis=0)
        else:
            background_2 = self.read_spectrum()
        self.integration_time = self.integration_time/2.0
        self.background_gradient = old_div((background_2-background_1),self.integration_time)
        self.background_constant = background_1-(self.integration_time*self.background_gradient)
        self.background = background_1
        self.background_int = self.integration_time
        self.stored_backgrounds[self.reference_ID] = {'background_gradient' : self.background_gradient,
                                                     'background_constant' : self.background_constant,
                                                     'background' : self.background,
                                                     'background_int': self.background_int}
        self.update_config('background_gradient', self.background_gradient)
        self.update_config('background_constant', self.background_constant)
        self.update_config('background', self.background)
        self.update_config('background_int', self.background_int)

    def clear_background(self):
        """Clear the current background reading."""
        self.background = None
        self.background_gradient = None
        self.background_constant = None
        self.background_int = None

    def read_reference(self):
        """Acquire a new spectrum and use it as a reference."""
        if self.averaging_enabled == True:
            self.reference = np.average(self.read_averaged_spectrum(True,True),axis=0)
        else:
            self.reference = self.read_spectrum() 
        self.reference_int = self.integration_time
        self.update_config('reference', self.reference)
        self.update_config('reference_int',self.reference_int) 
        self.stored_references[self.reference_ID] = {'reference' : self.reference,
                                                    'reference_int' : self.reference_int}
    def load_reference(self,ID):
        for attr in self.stored_backgrounds[ID]:
            setattr(self,attr,self.stored_backgrounds[ID][attr])
        for attr in self.stored_references[ID]:
            setattr(self,attr,self.stored_references[ID][attr])

    def clear_reference(self):
        """Clear the current reference spectrum"""
        self.reference = None
        self.reference_int = None

    def is_background_compensated(self):
        """Return whether there's currently a valid background spectrum"""
        return len(self.background)==len(self.latest_raw_spectrum) and \
            sum(self.background)>0

    def is_referenced(self):
        """Check whether there's currently a valid background and reference spectrum"""
        try:
            return self.is_background_compensated and \
                len(self.reference)==len(self.latest_raw_spectrum) and \
                sum(self.reference)>0
        except TypeError:
            return False

    def process_spectrum(self, spectrum):
        """Subtract the background and divide by the reference, if possible"""
        if self.background is not None:
            if self.reference is not None:
                old_error_settings = np.seterr(all='ignore')
           #     new_spectrum = (spectrum - (self.background-np.min(self.background))*self.integration_time/self.background_int+np.min(self.background))/(((self.reference-np.min(self.background))*self.integration_time/self.reference_int - (self.background-np.min(self.background))*self.integration_time/self.background_int)+np.min(self.background))
                if self.variable_int_enabled == True:
                    new_spectrum = (old_div((spectrum-(self.background_constant+self.background_gradient*self.integration_time)),(old_div((self.reference-(self.background_constant+self.background_gradient*self.reference_int))*self.integration_time,self.reference_int))))
                else:
                    new_spectrum = old_div((spectrum-self.background),(self.reference-self.background))
                np.seterr(**old_error_settings)
                new_spectrum[np.isinf(new_spectrum)] = np.NaN #if the reference is nearly 0, we get infinities - just make them all NaNs.
            else:
                if self.variable_int_enabled == True:
                    new_spectrum = spectrum-(self.background_constant+self.background_gradient*self.integration_time)
                else:
                    new_spectrum = spectrum-self.background
                
        else:
            new_spectrum = spectrum
        if self.absorption_enabled == True:
            return np.log10(old_div(1,new_spectrum))
        return new_spectrum

    def read_processed_spectrum(self):
        """Acquire a new spectrum and return a processed (referenced/background-subtracted) spectrum.
        
        NB if saving data to file, it's best to save raw spectra along with metadata - this is a
        convenience method for display purposes."""
        if self.averaging_enabled == True:
            spectrum = np.average(self.read_averaged_spectrum(fresh = True),axis=0)
        else:
            spectrum = self.read_spectrum()
        self.latest_spectrum = self.process_spectrum(spectrum)
        return self.latest_spectrum

    def read(self):
        """Acquire a new spectrum and return a tuple of wavelengths, spectrum"""
        return self.wavelengths, self.read_processed_spectrum()

    def mask_spectrum(self, spectrum, threshold):
        """Return a masked array of the spectrum, showing only points where the reference
        is bright enough to be useful."""
        if self.reference is not None and self.background is not None:
            reference = self.reference - self.background
            mask = reference < reference.max() * threshold
            if len(spectrum.shape)>1:
                mask = np.tile(mask, spectrum.shape[:-1]+(1,))
            return ma.array(spectrum, mask=mask)
        else:
            return spectrum
    _preview_widgets = WeakSet()
    def get_qt_ui(self, control_only=False,display_only = False):
        """Create a Qt interface for the spectrometer"""
        if control_only:
            
            newwidget = SpectrometerControlUI(self)
            self._preview_widgets.add(newwidget)
            return newwidget
        elif display_only:
            return SpectrometerDisplayUI(self)
        else:
            return SpectrometerUI(self)
            
    def get_control_widget(self):
        """Convenience function """
        return self.get_qt_ui(control_only=True)
        
    def get_preview_widget(self):
        """Convenience function """
        return self.get_qt_ui(display_only=True)

    def save_spectrum(self, spectrum=None, attrs={}, new_deque = False):
        """Save a spectrum to the current datafile, creating if necessary.
        
        If no spectrum is passed in, a new spectrum is taken.  The convention
        is to save raw spectra only, along with reference/background to allow
        later processing.
        
        The attrs dictionary allows extra metadata to be saved in the HDF5 file."""
        if self.averaging_enabled == True:
            spectrum = self.read_averaged_spectrum(new_deque = new_deque)
        else:
            spectrum = self.read_spectrum() if spectrum is None else spectrum
        metadata = self.metadata
        metadata.update(attrs) #allow extra metadata to be passed in
        self.create_dataset(self.filename, data=spectrum, attrs=metadata) 
        #save data in the default place (see nplab.instrument.Instrument)
    def read_averaged_spectrum(self,new_deque = False,fresh = False):
            if fresh == True:
                self.spectra_deque.append(self.read_spectrum())
            if new_deque == True:
                self.spectra_deque.clear()
            while len(self.spectra_deque) < self.spectra_deque.maxlen:
                self.spectra_deque.append(self.read_spectrum())
            return self.spectra_deque
        
    def save_reference_to_file(self):
        pass

    def load_reference_from_file(self):
        pass
    
    def time_series(self, num_spectra = None, delay = None, update_progress = lambda p:p):# delay in ms
        if num_spectra is None:
            num_spectra = self.num_spectra
        if delay is None:
            delay = self.delay
        delay/=1000
        update_progress(0)
        metadata = self.metadata
        extra_metadata = {'number of spectra' : num_spectra,
                          'spectrum end-to-start delay' : delay
                           }
        metadata.update(extra_metadata) 
        to_save = []
        times = []
        start = time.time()
        for spectrum_number in range(num_spectra):
            times.append(time.time() - start)
            to_save.append(self.read_spectrum()) # should be a numpy array
            time.sleep(delay)
            update_progress(spectrum_number)
        metadata.update({'start times' : times})
        self.create_dataset(self.time_series_name, data=to_save, attrs=metadata)
        to_return = ArrayWithAttrs(to_save, attrs = metadata)
        return to_return

class Spectrometers(Instrument):
    def __init__(self, spectrometer_list):
        assert False not in [isinstance(s, Spectrometer) for s in spectrometer_list],\
            'an invalid spectrometer was supplied'
        super(Spectrometers, self).__init__()
        self.spectrometers = spectrometer_list
        self.num_spectrometers = len(spectrometer_list)
        self._pool = ThreadPool(processes=self.num_spectrometers)
        self._wavelengths = None
        filename = DumbNotifiedProperty('spectra')

    def __del__(self):
        self._pool.close()

    def add_spectrometer(self, spectrometer):
        assert isinstance(spectrometer, Spectrometer), 'spectrometer must be an instance of Spectrometer'
        if spectrometer not in self.spectrometers:
            self.spectrometers.append(spectrometer)
            self.num_spectrometers = len(self.spectrometers)

    def get_wavelengths(self):
        if self._wavelengths is None:
            self._wavelengths = [s.wavelengths for s in self.spectrometers]
        return self._wavelengths

    wavelengths = property(get_wavelengths)

    def read_spectra(self):
        """Acquire spectra from all spectrometers and return as a list."""
        return self._pool.map(lambda s: s.read_spectrum(), self.spectrometers)

    def read_processed_spectra(self):
        """Acquire a list of processed (referenced, background subtracted) spectra."""
        return self._pool.map(lambda s: s.read_processed_spectrum(), self.spectrometers)

    def process_spectra(self, spectra):
        pairs = list(zip(self.spectrometers, spectra))
        return self._pool.map(lambda s_spectrum: s_spectrum[0].process_spectrum(s_spectrum[1]), pairs)

    def get_metadata_list(self):
        """Return a list of metadata for each spectrometer."""
        return self._pool.map(lambda s: s.get_metadata(), self.spectrometers)

    def mask_spectra(self, spectra, threshold):
        return [spectrometer.mask_spectrum(spectrum, threshold) for (spectrometer, spectrum) in zip(self.spectrometers, spectra)]

    def get_qt_ui(self):
        return SpectrometersUI(self)

    def save_spectra(self, spectra=None, attrs={}):
        """Save spectra from all the spectrometers, in a folder in the current
        datafile, creating the file if needed.

        If no spectra are given, new ones are acquired - NB you should pass
        raw spectra in - metadata will be saved along with the spectra.
        """
        spectra = self.read_spectra() if spectra is None else spectra
        metadata_list = self.get_metadata_list()
        g = self.create_data_group(self.filename,attrs=attrs) # create a uniquely numbered group in the default place
        for spectrum,metadata in zip(spectra,metadata_list):
            g.create_dataset('spectrum_%d',data=spectrum,attrs=metadata)
            
    def get_metadata(self):
        """
        Returns a list of dictionaries containing relevant spectrometer properties
        for each spectrometer.
        """
        return [spectrometer.metadata for spectrometer in self.spectrometers]

    metadata = property(get_metadata)

  
            

class SpectrometerControlUI(QtWidgets.QWidget,UiTools):
    
    def __init__(self, spectrometer, ui_file =os.path.join(os.path.dirname(__file__),'spectrometer_controls.ui'),  parent=None):
        assert isinstance(spectrometer, Spectrometer), "instrument must be a Spectrometer"
        super(SpectrometerControlUI, self).__init__()
        uic.loadUi(ui_file, self)
        self.spectrometer = spectrometer
        
        self.integration_time.setValidator(QtGui.QDoubleValidator())
        self.integration_time.textChanged.connect(self.check_state)
        self.integration_time.textChanged.connect(self.update_param)

        self.read_background_button.clicked.connect(self.button_pressed)
        self.read_reference_button.clicked.connect(self.button_pressed)
        self.clear_background_button.clicked.connect(self.button_pressed)
        self.clear_reference_button.clicked.connect(self.button_pressed)
        self.load_state_button.clicked.connect(self.button_pressed)

        self.background_subtracted.stateChanged.connect(self.state_changed)
        self.referenced.stateChanged.connect(self.state_changed)
        
        self.Absorption_checkBox.stateChanged.connect(self.state_changed)
                
        register_for_property_changes(self.spectrometer,'variable_int_enabled',self.variable_int_state_change)
#        if self.spectrometer.variable_int_enabled:
#                self.background_subtracted.blockSignals(True)
#                self.background_subtracted.setCheckState(QtCore.Qt.Checked)
#                self.background_subtracted.blockSignals(False)
        self.Variable_int.stateChanged.connect(self.state_changed)
        
#                if self.spectrometer.variable_int_enabled:
#                self.background_subtracted.blockSignals(True)
#                self.background_subtracted.setCheckState(QtCore.Qt.Checked)
#                self.background_subtracted.blockSignals(False)
        self.average_checkBox.stateChanged.connect(self.state_changed)
        self.Average_spinBox.valueChanged.connect(self.update_averages)
        
        self.referenceID_spinBox.valueChanged.connect(self.update_references)


        self.id_string.setText('{0} {1}'.format(self.spectrometer.model_name, self.spectrometer.serial_number))
        self.id_string.resize(self.id_string.sizeHint())

        self.integration_time.setText(str(spectrometer.integration_time))

        self.num_spectra_spinBox.valueChanged.connect(self.update_time_series_params)
        self.delay_doubleSpinBox.valueChanged.connect(self.update_time_series_params)
        self.time_series_name_lineEdit.textChanged.connect(self.update_time_series_name)
        self.time_series_pushButton.clicked.connect(self.time_series)

    def update_param(self, *args, **kwargs):
        sender = self.sender()
        if sender is self.integration_time:
            try:
                self.spectrometer.integration_time = float(args[0])
            except ValueError:
                pass
            
    def update_averages(self,*args,**kwargs):
        self.spectrometer.spectra_deque = deque(maxlen = args[0])

    def button_pressed(self, *args, **kwargs):
        sender = self.sender()
        if sender is self.read_background_button:
            self.spectrometer.read_background()
            self.background_subtracted.blockSignals(True)
            self.background_subtracted.setCheckState(QtCore.Qt.Checked)
            self.background_subtracted.blockSignals(False)            
        elif sender is self.clear_background_button:
            self.spectrometer.clear_background()
            self.background_subtracted.blockSignals(True)
            self.background_subtracted.setCheckState(QtCore.Qt.Unchecked)
            self.background_subtracted.blockSignals(False)
        elif sender is self.read_reference_button:
            self.spectrometer.read_reference()
            self.referenced.blockSignals(True)
            self.referenced.setCheckState(QtCore.Qt.Checked)
            self.referenced.blockSignals(False)
        elif sender is self.clear_reference_button:
            self.spectrometer.clear_reference()
            self.referenced.blockSignals(True)
            self.referenced.setCheckState(QtCore.Qt.Unchecked)
            self.referenced.blockSignals(False)
        elif sender is self.load_state_button:
            if 'background' in self.spectrometer.config_file:
                self.spectrometer.background = self.spectrometer.config_file['background'][:] #load the background
                if 'background_constant' in self.spectrometer.config_file:
                    self.spectrometer.background_constant = self.spectrometer.config_file['background_constant'][:]
                if 'background_gradient' in self.spectrometer.config_file:
                    self.spectrometer.background_gradient = self.spectrometer.config_file['background_gradient'][:]
                if 'background_int' in self.spectrometer.config_file:
                    self.spectrometer.background_int = self.spectrometer.config_file['background_int'][...]
                    
                self.background_subtracted.blockSignals(True)
                self.background_subtracted.setCheckState(QtCore.Qt.Checked)
                self.background_subtracted.blockSignals(False)
            else:
                print('background not found in config file')
            if 'reference' in self.spectrometer.config_file:
                self.spectrometer.reference = self.spectrometer.config_file['reference'][:]
                if 'reference_int' in self.spectrometer.config_file:
                    self.spectrometer.reference_int = self.spectrometer.config_file['reference_int'][...]
                self.referenced.blockSignals(True)
                self.referenced.setCheckState(QtCore.Qt.Checked)
                self.referenced.blockSignals(False)
            else:
                print('reference not found in config file')
                

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
            
        elif sender is self.Variable_int and\
        self.Variable_int.isChecked() != self.spectrometer.variable_int_enabled:
            self.spectrometer.variable_int_enabled = not self.spectrometer.variable_int_enabled
            
        elif sender is self.average_checkBox:
            self.spectrometer.averaging_enabled = not self.spectrometer.averaging_enabled
            
        elif sender is self.Absorption_checkBox:
            self.spectrometer.absorption_enabled = not self.spectrometer.absorption_enabled
        
    def variable_int_state_change(self, new):
        self.Variable_int.setChecked(new)
            
    def update_references(self,*args, **kwargs):
        self.spectrometer.reference_ID = args[0]
        try:
            self.spectrometer.load_reference(self.spectrometer.reference_ID )
        except KeyError:
            self.spectrometer.clear_reference()
            self.referenced.blockSignals(True)
            self.referenced.setCheckState(QtCore.Qt.Unchecked)
            self.referenced.blockSignals(False)
            
            self.spectrometer.clear_background()
            self.background_subtracted.blockSignals(True)
            self.background_subtracted.setCheckState(QtCore.Qt.Unchecked)
            self.background_subtracted.blockSignals(False)


            self.spectrometer._logger.info('No refence/background saved in slot %s to load' %args[0])
            
    def update_time_series_params(self):
        self.spectrometer.num_spectra = int(self.num_spectra_spinBox.value())   
        self.spectrometer.delay = float(self.delay_doubleSpinBox.value()) 
        self.time_total_lcdNumber.display(np.round(self.spectrometer.num_spectra*(self.spectrometer.integration_time + self.spectrometer.delay)/1000, decimals = 0))
    def update_time_series_name(self):
        self.spectrometer.time_series_name = self.time_series_name_lineEdit.text().strip()
    def time_series(self):
        run_function_modally(self.spectrometer.time_series, progress_maximum = self.spectrometer.num_spectra)


class DisplayThread(QtCore.QThread):
    spectrum_ready = QtCore.Signal(np.ndarray)
    spectra_ready = QtCore.Signal(list)

    def __init__(self, parent):
        super(DisplayThread, self).__init__()
        self.parent = parent
        self.single_shot = False
        self.refresh_rate = 30.

    def run(self):
        t0 = time.time()
        while self.parent.live_button.isChecked() or self.single_shot:
            read_processed_spectrum = self.parent.spectrometer.read_processed_spectra \
                if isinstance(self.parent.spectrometer, Spectrometers) \
                else self.parent.spectrometer.read_processed_spectrum
            spectrum = read_processed_spectrum()
            if time.time()-t0 < 1./self.refresh_rate:
                continue
            else:
                t0 = time.time()
            if type(spectrum) == np.ndarray:
                self.spectrum_ready.emit(spectrum)
            elif type(spectrum) == list:
                self.spectra_ready.emit(spectrum)
            if self.single_shot:
                break
        self.finished.emit()


class SpectrometerDisplayUI(QtWidgets.QWidget,UiTools):
    def __init__(self, spectrometer,ui_file = os.path.join(os.path.dirname(__file__),'spectrometer_view.ui'), parent=None):
        assert isinstance(spectrometer, Spectrometer) or isinstance(spectrometer, Spectrometers),\
            "instrument must be a Spectrometer or an instance of Spectrometers"
        super(SpectrometerDisplayUI, self).__init__()
        uic.loadUi(ui_file, self)
        if isinstance(spectrometer, Spectrometers) and spectrometer.num_spectrometers == 1:
            spectrometer = spectrometer.spectrometers[0]
        if isinstance(spectrometer,Spectrometer):
            spectrometer.num_spectrometers = 1
        self.spectrometer = spectrometer
        print(self.spectrometer)

        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.plotbox = QtWidgets.QGroupBox()
        self.plotbox.setLayout(QtWidgets.QGridLayout())
        self.plotlayout = self.plotbox.layout()          
        self.plots =[]

        for spectrometer_nom in range(self.spectrometer.num_spectrometers):
            self.plots.append(pg.PlotWidget(labels = {'bottom':'Wavelength (nm)'}))
            self.plotlayout.addWidget(self.plots[spectrometer_nom])

        self.figure_widget = self.replace_widget(self.display_layout,
                                                 self.figure_widget, self.plotbox)         
        self.take_spectrum_button.clicked.connect(self.button_pressed)
        self.live_button.clicked.connect(self.button_pressed)
        self.save_button.clicked.connect(self.button_pressed)
        self.threshold.setValidator(QtGui.QDoubleValidator())
        self.threshold.textChanged.connect(self.check_state)
        self._display_thread = DisplayThread(self)
        self._display_thread.spectrum_ready.connect(self.update_display)
        self._display_thread.spectra_ready.connect(self.update_display)

        self.period = 0.2
        self.filename_lineEdit.textChanged.connect(self.filename_changed_ui)
       
        register_for_property_changes(self.spectrometer,'filename',self.filename_changed)
    def button_pressed(self, *args, **kwargs):
        sender = self.sender()
        if sender is self.take_spectrum_button:
            #if self._display_thread.is_alive():
            if self._display_thread.isRunning():
                print('already acquiring')
                return
            #self._display_thread = Thread(target=self.update_spectrum)
            self._display_thread.single_shot = True
            self._display_thread.start()
            #self.update_spectrum()
        elif sender is self.save_button:
            save_spectrum = self.spectrometer.save_spectra \
                if isinstance(self.spectrometer, Spectrometers) \
                else self.spectrometer.save_spectrum
            save_spectrum(attrs={'description':str(self.description.text())})
        elif sender is self.live_button:
            if self.live_button.isChecked():
                #if self._display_thread.is_alive():
                if self._display_thread.isRunning():
                    print('already acquiring')
                    return
                #self._display_thread = Thread(target=self.continuously_update_spectrum)
                self._display_thread.single_shot = False
                self._display_thread.start()

    def update_spectrum(self):
        read_processed_spectrum = self.spectrometer.read_processed_spectra \
            if isinstance(self.spectrometer, Spectrometers) \
            else self.spectrometer.read_processed_spectrum
        spectrum = read_processed_spectrum()
        self.update_display(spectrum)

    def continuously_update_spectrum(self):
        t0 = time.time()
        while self.live_button.isChecked():
            if time.time()-t0 < 1./30.:
                continue
            else:
                t0 = time.time()
            self.update_spectrum()

    def update_display(self, spectrum):
        #Update the graphs
        if len(np.ravel(spectrum))>len(spectrum):# checking if it's 2d
            spectrum = np.array([[0 if np.isnan(i) else i for i in s] for s in list(spectrum)])
        else:
            spectrum= np.array([0 if np.isnan(i) else i for i in spectrum])
        wavelengths = self.spectrometer.wavelengths
        if self.enable_threshold.checkState() == QtCore.Qt.Checked:
            threshold = float(self.threshold.text())
            if isinstance(self.spectrometer, Spectrometers):
                spectrum = [spectrometer.mask_spectrum(s, threshold) for (spectrometer, s) in zip(self.spectrometer.spectrometers, spectrum)]
            else:
                spectrum = self.spectrometer.mask_spectrum(spectrum, threshold)
                    
        if not self.plots[0].getPlotItem().listDataItems():
            self.plotdata = []
            if isinstance(self.spectrometer, Spectrometers):
                for spectrometer_nom in range(self.spectrometer.num_spectrometers):
                    self.plotdata.append(self.plots[spectrometer_nom].plot(x = wavelengths[spectrometer_nom],y \
                    = spectrum[spectrometer_nom],pen =(spectrometer_nom,len(list(range(self.spectrometer.num_spectrometers))))))
            else:                
                self.plotdata.append(self.plots[0].plot(x = wavelengths,y = spectrum,pen =(0,len(list(range(self.spectrometer.num_spectrometers))))))
        else:
            if isinstance(self.spectrometer, Spectrometers):
                for spectrometer_nom in range(self.spectrometer.num_spectrometers):
                    self.plotdata[spectrometer_nom].setData(x = wavelengths[spectrometer_nom],y= spectrum[spectrometer_nom])
            else:
                self.plotdata[0].setData(x = wavelengths,y= spectrum)

    def filename_changed_ui(self):
        self.spectrometer.filename = self.filename_lineEdit.text()
    def filename_changed(self):
        self.filename_lineEdit.setText(self.spectrometer.filename)

class SpectrometerUI(QtWidgets.QWidget):
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
        layout = QtWidgets.QVBoxLayout()
    #    controls_layout = QtWidgets.QVBoxLayout()
    #    controls_layout.addWidget(self.controls)
    #    controls_layout.setContentsMargins(0,0,0,0)
    #    controls_group = QtWidgets.QGroupBox()
    #    controls_group.setTitle('Spectrometer')
    #    controls_group.setLayout(controls_layout)
        layout.addWidget(self.controls)
        layout.addWidget(self.display)
        layout.setContentsMargins(5,5,5,5)
        layout.setSpacing(5)
        self.setLayout(layout)


class SpectrometersUI(QtWidgets.QWidget):
    def __init__(self, spectrometers):
        assert isinstance(spectrometers, Spectrometers), "instrument must be an instance of Spectrometers"
        super(SpectrometersUI, self).__init__()
        self.spectrometers = spectrometers
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle('Spectrometers')
        self.controls_layout = QtWidgets.QHBoxLayout()
        controls_group = QtWidgets.QGroupBox()
        controls_group.setTitle('Spectrometers')
        controls_group.setLayout(self.controls_layout)
        self.controls = []
        for spectrometer in self.spectrometers.spectrometers:
            control = spectrometer.get_qt_ui(control_only=True)
            self.controls_layout.addWidget(control)
            self.controls.append(control)
        self.display = SpectrometerDisplayUI(self.spectrometers)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(controls_group)
        layout.addWidget(self.display)
        self.setLayout(layout)


class DummySpectrometer(Spectrometer):
    """A trivial stub spectrometer, for use in development."""
    metadata_property_names = ["integration_time", "wavelengths"]
    def __init__(self):
        super(DummySpectrometer, self).__init__()
        self._integration_time = 10
        self.background = np.zeros(len(self.wavelengths))
        self.reference = np.ones(len(self.wavelengths))
    def get_integration_time(self):
        return self._integration_time

    def set_integration_time(self, value):
        self._integration_time = value

    integration_time = property(get_integration_time, set_integration_time)

    def get_wavelengths(self):
        return np.arange(400,1200,1)

    wavelengths = property(get_wavelengths)
    
    
    def read_spectrum(self, bundle_metadata=False):
        from time import sleep
        sleep(self.integration_time/1000.)
        if bundle_metadata:
            return self.bundle_metadata(np.array([np.random.random() for wl in self.wavelengths])*self.integration_time/1000.0,
                                    enable=bundle_metadata)
        return np.array([np.random.random() for wl in self.wavelengths])*self.integration_time/1000.0


if __name__ == '__main__':
    import sys
    from nplab.utils.gui import get_qt_app
    s1 = DummySpectrometer()
    s1.show_gui(blocking = False)
#    s2 = DummySpectrometer()
#    s3 = DummySpectrometer()
#    s4 = DummySpectrometer()
#    spectrometers = Spectrometers([s1, s2,s3,s4])
#    for spectrometer in spectrometers.spectrometers:
#        spectrometer.integration_time = 100
#    import timeit
##    print '{0:.2f} ms'.format(1000*timeit.Timer(spectrometers.read_spectra).timeit(number=10)/10)
##    app = get_qt_app()
##    ui = SpectrometersUI(spectrometers)
##    ui.show()
#  #  sys.exit(app.exec_())
