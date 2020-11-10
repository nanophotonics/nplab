# -*- coding: utf-8 -*-
"""
Ocean Optics Spectrometer Module

This module uses the lightweight SeaBreeze driver from Ocean Optics to provide
access to their spectrometers.  Currently, it works with QE65000, HR4000 and
other high-end spectrometers, but *not* the cheaper ones like Red Tide USB650.
I've not tested it with USB2000, though I believe it should work.

IMPORTANT NOTE ON DRIVERS:
Spectrometers will only show up in this module if they are associated with the
SeaBreeze driver.  This must be done manually if you have previously used the
OmniDriver package (this is what Igor uses with our XOP).  You can do this
through Device Manager: find the spectrometer, right click and select "Update
Driver...".  Select "search for a driver in a particular location" and then
choose C:\Program Files\Ocean Optics\SeaBreeze\Drivers.  Once it installs, you
should see the spectrometer listed as "Ocean Optics Spectrometer (WinUSB)".
After doing this, you must repeat the process if you want to switch back to
OmniDriver.

Contents:
@class: OceanOpticsSpectrometer: this class controls a spectrometer

@class: OceanOpticsError: an exception that is thrown by this module

@fn:    list_spectrometers(): list the available spectrometers

@fn:    shutdown_seabreeze(): close all spectrometers and reset the driver

@author: Richard Bowman (rwb27)
"""
from __future__ import division
from __future__ import print_function

from builtins import str
from builtins import range
from past.utils import old_div
import ctypes
from ctypes import byref, c_int, c_ulong, c_double
import numpy as np
import threading
from nplab.instrument import Instrument
from nplab.utils.gui import QtCore, QtGui, QtWidgets, uic
from nplab.instrument.spectrometer import Spectrometer, Spectrometers, SpectrometerControlUI, SpectrometerDisplayUI, SpectrometerUI
import os
import h5py
import inspect
import datetime
from nplab.utils.array_with_attrs import ArrayWithAttrs
from nplab.datafile import DataFile

try:
    seabreeze = ctypes.cdll.seabreeze
except WindowsError as e:  # if the DLL is missing, warn, either graphically or with an exception.
    explanation = """
WARNING: could not link to the SeaBreeze DLL.

Make sure you have installed the SeaBreeze driver from the Ocean Optics
website (http://downloads.oceanoptics.com/OEM/), and that its version matches
your Python architecture (64 or 32 bit).  See the module help for more
information"""
    try:
        print(explanation, "SeaBreeze Driver Missing")
    except Exception as e:
        print("uh oh, problem with the message...")
        print(e)
        pass
    finally:
        raise Exception(explanation)


def error_string(error_code):
    """convert an error code into a human-readable string"""
    N = 1024  # we need to create a buffer into which we place the returned string
    s = ctypes.create_string_buffer(N)
    seabreeze.seabreeze_get_error_string(error_code, byref(s), N)
    return s.value.decode('utf-8')


def check_error(error_c_int):
    """check the error code returned by a function (as a raw c_int)
    and raise an exception if it's nonzero."""
    if error_c_int.value != 0:
        raise OceanOpticsError(error_c_int.value)


def list_spectrometers():
    """List the serial numbers of all spectrometers connected to the computer"""
    spectrometers = []
    n = 0
    try:
        while True:  # we stop when we run out of spectrometers, signified by an exception
            # the line below creates a spectrometer, initialises, gets the serial number, and closes again
            spectrometers.append(OceanOpticsSpectrometer(n).serial_number)
            # if the spectrometer does not exist, it raises an exception.
            n += 1
    except OceanOpticsError:
        pass
    finally:
        return spectrometers


def shutdown_seabreeze():
    """shut down seabreeze, useful if anything has gone wrong"""
    seabreeze.seabreeze_shutdown()


class OceanOpticsError(Exception):
    def __init__(self, code):
        self.code = code

    def __str__(self):
        return "Code %d: %s." % (self.code, error_string(self.code))


class OceanOpticsSpectrometer(Spectrometer, Instrument):
    """Class representing the Ocean Optics spectrometers, via the SeaBreeze library

    The constructor takes a single numeric argument, which is the index of the
    spectrometer you want, starting at 0.  It has traits, so you can call up a
    GUI to control the spectrometer with s.configure_traits."""

    metadata_property_names = Spectrometer.metadata_property_names+ ("tec_temperature",)

    @staticmethod
    def shutdown_seabreeze():
        """shut down seabreeze, useful if anything has gone wrong"""
        shutdown_seabreeze()

    @classmethod
    def list_spectrometers(cls):
        """List the serial numbers of all spectrometers connected to the computer"""
        return list_spectrometers()

    @classmethod
    def get_spectrometer_instances(cls):
        """return a list of spectrometer instances for all available spectrometers"""
        spectrometers = []
        try:
            n = 0
            while True:
                spectrometers.append(cls(n))
                n += 1
        except OceanOpticsError:
            pass
        finally:
            return spectrometers

    @classmethod
    def get_spectrometers(cls):
        """get a Spectrometers instance containing all available spectrometers"""
        return Spectrometers(cls.get_spectrometer_instances())

    @classmethod
    def get_current_spectrometers(cls):
        """Return the currently-open spectrometers, or all spectrometers.

        If one or more spectrometers are currently open, create a Spectrometers
        wrapper and include them in it.  If not, attempt to open and wrap all
        spectrometers connected to the computer."""
        instances = cls.get_instances()
        print(instances)
        if instances == []:
            return cls.get_spectrometers()
        else:
            return Spectrometers(instances)

    def __init__(self, index):
        """Initialise the spectrometer"""
        self.index = index  # the spectrometer's ID, used by all seabreeze functions
        self._comms_lock = threading.RLock()
        self._isOpen = False
        self._open()
        super(OceanOpticsSpectrometer, self).__init__()
        self.get_API_version() 
        self._minimum_integration_time = None
        self.integration_time = self.minimum_integration_time
        self._tec_enabled = True
        self.enable_tec = True

    def __del__(self):
        self._close()
        super(OceanOpticsSpectrometer, self).__del__()
        return self

    def _open(self, force=False):
        """Open communications with the spectrometer (called on initialisation)."""
        if (self._isOpen and not force):  # don't cause errors if it's already open
            return
        else:
            e = ctypes.c_int()
            seabreeze.seabreeze_open_spectrometer(self.index, byref(e))
            check_error(e)
            self._isOpen = True

    def _close(self, force=False):
        """Close communication with the spectrometer and release it."""
        if (not self._isOpen and not force):
            return
        else:
            e = ctypes.c_int()
            seabreeze.seabreeze_close_spectrometer(self.index, byref(e))
            check_error(e)
            self._isOpen = False

    def open_config_file(self):
        if self._config_file is None:
            f = inspect.getfile(self.__class__)
            d = os.path.dirname(f)
            self._config_file = DataFile(h5py.File(os.path.join(d, self.model_name+'_'+self.serial_number+'_config.h5')))
            self._config_file.attrs['date'] = datetime.datetime.now().strftime("%H:%M %d/%m/%y")
        return self._config_file

    config_file = property(open_config_file)
    def get_API_version(self):
        N = 32  # make a buffer for the DLL to return a string into
        s = ctypes.create_string_buffer(N)
        e = ctypes.c_int()
        try:
            seabreeze.seabreeze_get_model(self.index, byref(e), byref(s), N)
            self.API_ver = 2
        except:
            self.API_ver = 1
        check_error(e)        

    def get_model_name(self):
        if self._model_name is None:
            N = 32  # make a buffer for the DLL to return a string into
            s = ctypes.create_string_buffer(N)
            e = ctypes.c_int()
            try:
                seabreeze.seabreeze_get_model(self.index, byref(e), byref(s), N)
                self.API_ver = 2
            except:
                seabreeze.seabreeze_get_spectrometer_type(self.index, byref(e), byref(s), N)
                self.API_ver = 1
            check_error(e)
            self._model_name = s.value.decode('utf-8')
        return self._model_name

    model_name = property(get_model_name)

    def get_serial_number(self):
        """The spectrometer's serial number."""
        if self._serial_number is None:
            N = 32  # make a buffer for the DLL to return a string into
            s = ctypes.create_string_buffer(N)
            e = ctypes.c_int()
            seabreeze.seabreeze_get_serial_number(self.index, byref(e), byref(s), N)
            check_error(e)
            self._serial_number = s.value.decode('utf-8')
        return self._serial_number

    serial_number = property(get_serial_number)

    def get_usb_descriptor(self, id):
        """The spectrometer's USB descriptor"""
        N = 32  # make a buffer for the DLL to return a string into
        s = ctypes.create_string_buffer(N)
        e = ctypes.c_int()
        seabreeze.seabreeze_get_usb_descriptor_string(self.index, byref(e), c_int(id), byref(s), N)
        check_error(e)
        return s.value.decode('utf-8')

    def get_integration_time(self):
        """The current integration time.

        The SeaBreeze API doesn't seem to allow us to get the current integration time, so
        we work around it by cacheing the last used integration time.  Note that this will
        return None if you've not set the integration time."""
        if hasattr(self, "_latest_integration_time"):
            return self._latest_integration_time
        else:
            return None

    def set_integration_time(self, milliseconds):
        """Set the integration time"""
        e = ctypes.c_int()
        if milliseconds < self.minimum_integration_time:
            raise ValueError("Cannot set integration time below %d microseconds" % self.minimum_integration_time)
        if self.API_ver == 1:
            seabreeze.seabreeze_set_integration_time(self.index, byref(e), c_ulong(int(milliseconds * 1000)))
        if self.API_ver == 2:
            seabreeze.seabreeze_set_integration_time_microsec(self.index, byref(e), c_ulong(int(milliseconds * 1000)))
        
        check_error(e)
        self._latest_integration_time = milliseconds

    integration_time = property(get_integration_time, set_integration_time)

    def get_minimum_integration_time(self):
        """Minimum allowable value for integration time"""
        if self._minimum_integration_time is None:
            e = ctypes.c_int()
            if self.API_ver == 1:
                min_time = seabreeze.seabreeze_get_minimum_integration_time_micros(self.index, byref(e))
            if self.API_ver == 2:
                min_time = seabreeze.seabreeze_get_min_integration_time_microsec(self.index, byref(e))   
            check_error(e)
            self._minimum_integration_time = min_time / 1000.
        return self._minimum_integration_time

    minimum_integration_time = property(get_minimum_integration_time)

    def get_tec_enable(self):
        """Whether or not the thermo-electric cooler is enabled."""
        try:
            return self._tec_enabled
        except OceanOpticsError as error:
            print(error)
            print('Most likely raised due to the lack of a tec on this device')

    def set_tec_enable(self, state=True):
        """Turn the cooling system on or off."""
        try:
            e = ctypes.c_int()
            seabreeze.seabreeze_set_tec_enable(self.index, byref(e), c_int(state))
            check_error(e)
            self._tec_enabled = state
        except OceanOpticsError as error:
            print(error)
            print('Most likely raised due to the lack of a tec on this device')

    enable_tec = property(get_tec_enable, set_tec_enable)

    def get_tec_temperature(self):
        """Current temperature."""
        try:
            e = ctypes.c_int()
            read_tec_temperature = seabreeze.seabreeze_read_tec_temperature
            read_tec_temperature.restype = c_double
            temperature_0 = read_tec_temperature(self.index, byref(e))
            for i in range(100):
                temperature = read_tec_temperature(self.index, byref(e))
                check_error(e)
                if temperature==temperature_0:
                    break
                else:
                    temperature_0=temperature
                if i==99:
                    self.log('Temperature reading inconsitent after 100 attmpets','WARN')
           
            return temperature
        except OceanOpticsError as error:
            print(error)
            print('Most likely raised due to the lack of a tec on this device')

    def set_tec_temperature(self, temperature):
        """Enable the cooling system and set the temperature"""
        try:
            if not self.enable_tec:
                self.enable_tec = True
            e = ctypes.c_int()
            seabreeze.seabreeze_set_tec_temperature(self.index, byref(e), c_double(temperature))
            seabreeze.seabreeze_set_tec_enable(self.index, byref(e), 1)
            check_error(e)
        except OceanOpticsError as error:
            print(error)
            print('Most likely raised due to the lack of a tec on this device')

    tec_temperature = property(get_tec_temperature, set_tec_temperature)

    def read_wavelengths(self):
        """get an array of the wavelengths in nm"""
        self._comms_lock.acquire()
        e = ctypes.c_int()
        N = seabreeze.seabreeze_get_formatted_spectrum_length(self.index, byref(e))
        wavelengths_carray = (c_double * N)()  # this should create a c array of doubles, length N
        seabreeze.seabreeze_get_wavelengths(self.index, byref(e), byref(wavelengths_carray), N)
        self._comms_lock.release()
        check_error(e)
        return np.array(list(wavelengths_carray))

    def get_wavelengths(self):
        """Wavelength values for each pixel.

        NB this caches the value so it's only retrieved from the spectrometer once."""
        if self._wavelengths is None:
            self._wavelengths = self.read_wavelengths()
        return self._wavelengths

    wavelengths = property(get_wavelengths)

    def read_spectrum(self, bundle_metadata=False):
        """Get the current reading from the spectrometer's sensor.

        Acquire a new spectrum and return it.  If bundle_metadata is true, this will be
        returned as an ArrayWithAttrs, including the current metadata."""
        e = ctypes.c_int()
        N = seabreeze.seabreeze_get_formatted_spectrum_length(self.index, byref(e))
        with self._comms_lock:
            spectrum_carray = (c_double * N)()  # this should create a c array of doubles, length N
            seabreeze.seabreeze_get_formatted_spectrum(self.index, byref(e), byref(spectrum_carray), N)
        check_error(e)  # throw an exception if something went wrong
        new_spectrum = np.array(list(spectrum_carray))

        if bundle_metadata:
            return ArrayWithAttrs(new_spectrum, attrs=self.metadata)
        else:
            return new_spectrum

    def get_qt_ui(self, control_only=False, display_only = False):
        """Return a Qt Widget for controlling the spectrometer.

        If control_only is true, this will not contain a graph of the spectrum.
        """
        if control_only:
            return OceanOpticsControlUI(self)
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

class OceanOpticsControlUI(SpectrometerControlUI):
    def __init__(self, spectrometer):
        assert isinstance(spectrometer, OceanOpticsSpectrometer), 'spectrometer must be an OceanOpticsSpectrometer'
        super(OceanOpticsControlUI, self).__init__(spectrometer,os.path.join(os.path.dirname(__file__),'ocean_optics_controls.ui'))
#        self.tec_temperature.setValidator(QtGui.QDoubleValidator())
        # self.tec_temperature.textChanged.connect(self.check_state)
        # self.tec_temperature.textChanged.connect(self.update_param)
        # self.tec_temperature.setText(str(spectrometer.tec_temperature))
        try: 
            self.spectrometer.get_tec_temperature()
            tec = True
        except AttributeError as e:
            print(e, 'removing cooling functionality')
            tec = False
        if tec:
            pass
            self.set_tec_temperature_pushButton.clicked.connect(self.gui_set_tec_temperature)
            self.read_tec_temperature_pushButton.clicked.connect(self.gui_read_tec_tempeature)
            self.enable_tec.stateChanged.connect(self.update_enable_tec)
            self.enable_tec.setChecked(self.spectrometer.enable_tec)
            initial_temperature = np.round(self.spectrometer.tec_temperature, decimals = 1)
            self.tec_temperature_lcdNumber.display(float(initial_temperature))
            self.set_tec_temperature_LineEdit.setText(str(initial_temperature))
            self.update_enable_tec(0) # sometimes helps enable cooling
            self.update_enable_tec(1)
        else:
            self.set_tec_temperature_pushButton.setVisible(False)
            self.read_tec_temperature_pushButton.setVisible(False)
            self.enable_tec.setVisible(False)
            self.tec_temperature_lcdNumber.setVisible(False)
            self.set_tec_temperature_LineEdit.setVisible(False)
            
    def update_param(self, value):
        sender = self.sender()
        if sender.validator() is not None:
            state = sender.validator().validate(value, 0)[0]
            if state != QtGui.QValidator.Acceptable:
                return
        if sender is self.integration_time:
            try:
                self.spectrometer.integration_time = float(value)
            except ValueError:
                pass
        elif sender is self.tec_temperature:
            try:
                self.spectrometer.tec_temperature = float(value)
            except ValueError:
                pass
    
    def gui_set_tec_temperature(self):
        self.spectrometer.tec_temperature = float(self.set_tec_temperature_LineEdit.text().strip())
    
    def gui_read_tec_tempeature(self):
        self.tec_temperature_lcdNumber.display(float(self.spectrometer.tec_temperature))
    
    def update_enable_tec(self, state):
        if state == QtCore.Qt.Checked:
            self.spectrometer.enable_tec = True
        elif state == QtCore.Qt.Unchecked:
            self.spectrometer.enable_tec = False



def main():
    from nplab.instrument.spectrometer import Spectrometers
    import sys
    from nplab.utils.gui import get_qt_app

    try:
        N = len(list_spectrometers())
        print("Spectrometers connected:", list_spectrometers())
        print("%d spectrometers found" % N)
        assert N != 0, 'There are no Ocean Optics spectrometers attached (are you using the seabreeze drivers?)'

        spectrometers = OceanOpticsSpectrometer.get_spectrometers()
        for s in spectrometers.spectrometers:
            print("spectrometer %s is a %s" % (s.serial_number, s.model_name))
            if s.model_name in ["QE65000", "QE-PRO"]:
                s.set_tec_temperature = -20
            s.read()
 #       app = get_qt_app()
 #       ui = spectrometers.get_qt_ui()
 #       ui.show()
 #       sys.exit(app.exec_()) #this is the "long way" of running a GUI
        spectrometers.show_gui()  # the "short way" of running a GUI
    except OceanOpticsError as error:
        print("An error occurred with the spectrometer: %s" % error)
    finally:
        try:
            pass
            #           del s     #we close the spectrometer afterwards, regardless of what happened.
        except:  # of course, if there's no spectrometer this will fail, hence the error handling
            shutdown_seabreeze()  # reset things if we've had errors
            print("The spectrometer did not close cleanly. SeaBreeze has been reset.")
# to alter max/min: s.spectrum_plot.value_mapper.range.high=0.01

# example code:
if __name__ == "__main__":
    print(list_spectrometers(), type(list_spectrometers()))
    # spec1 = OceanOpticsSpectrometer(1)
    # # spec1.show_gui(blocking = False)
    spec2 = OceanOpticsSpectrometer(0)
    spec2.show_gui(blocking = False)
#    main()
    # specs = Spectrometers([spec1, spec2])
    # specs.show_gui(blocking = False)