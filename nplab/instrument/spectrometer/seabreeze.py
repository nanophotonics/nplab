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

import ctypes
from ctypes import byref, c_int, c_ulong, c_double
import numpy as np
import threading
from nplab.instrument import Instrument
from nplab.utils.gui import QtCore, QtGui
from nplab.instrument.spectrometer import Spectrometer, Spectrometers, SpectrometerControlUI, SpectrometerDisplayUI, SpectrometerUI
import traitsui
import os
from PyQt4 import uic
import h5py
import inspect
import datetime

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
        traitsui.message.error(explanation, "SeaBreeze Driver Missing", buttons=["OK"])
    except Exception as e:
        print "uh oh, problem with the message..."
        print e
        pass
    finally:
        raise Exception(explanation)


def error_string(error_code):
    """convert an error code into a human-readable string"""
    N = 1024  # we need to create a buffer into which we place the returned string
    s = ctypes.create_string_buffer(N)
    seabreeze.seabreeze_get_error_string(error_code, byref(s), N)
    return s.value


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

    metadata_property_names = Spectrometer.metadata_property_names + ("tec_temperature",)

    @staticmethod
    def shutdown_seabreeze():
        """shut down seabreeze, useful if anything has gone wrong"""
        seabreeze.seabreeze_shutdown()

    @classmethod
    def list_spectrometers(cls):
        """list all spectrometers available"""
        spectrometers = []
        n = 0
        try:
            while True:  # we stop when we run out of spectrometers, signified by an exception
                # the line below creates a spectrometer, initialises, gets the serial number, and closes again
                spectrometers.append(cls(n).serial_number)
                # if the spectrometer does not exist, it raises an exception.
                n += 1
        except OceanOpticsError:
            pass
        finally:
            return spectrometers

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
        """get a Spectrometers instance containing all previously instanced spectrometers"""
        return Spectrometers(cls.get_instances())

    def __init__(self, index):
        """initialise the spectrometer"""
        self.index = index  # the spectrometer's ID, used by all seabreeze functions
        self._comms_lock = threading.RLock()
        self._isOpen = False
        self._open()
        super(OceanOpticsSpectrometer, self).__init__()
        self._minimum_integration_time = None
        self.integration_time = self.minimum_integration_time
        self._tec_enabled = True
        self.enable_tec = True

    def __del__(self):
        super(OceanOpticsSpectrometer, self).__del__()
        self._close()
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
            self._config_file = h5py.File(os.path.join(d, self.model_name+'_'+self.serial_number+'_config.h5'))
            self._config_file.attrs['date'] = datetime.datetime.now().strftime("%H:%M %d/%m/%y")
        return self._config_file

    config_file = property(open_config_file)

    def get_model_name(self):
        if self._model_name is None:
            N = 32  # make a buffer for the DLL to return a string into
            s = ctypes.create_string_buffer(N)
            e = ctypes.c_int()
            seabreeze.seabreeze_get_spectrometer_type(self.index, byref(e), byref(s), N)
            check_error(e)
            self._model_name = s.value
        return self._model_name

    model_name = property(get_model_name)

    def get_serial_number(self):
        if self._serial_number is None:
            N = 32  # make a buffer for the DLL to return a string into
            s = ctypes.create_string_buffer(N)
            e = ctypes.c_int()
            seabreeze.seabreeze_get_serial_number(self.index, byref(e), byref(s), N)
            check_error(e)
            self._serial_number = s.value
        return self._serial_number

    serial_number = property(get_serial_number)

    def get_usb_descriptor(self, id):
        """get the spectrometer's USB descriptor"""
        N = 32  # make a buffer for the DLL to return a string into
        s = ctypes.create_string_buffer(N)
        e = ctypes.c_int()
        seabreeze.seabreeze_get_usb_descriptor_string(self.index, byref(e), c_int(id), byref(s), N)
        check_error(e)
        return s.value

    def get_integration_time(self):
        """return the last set integration time"""
        # note there is no API call to get the integration time
        if hasattr(self, "_latest_integration_time"):
            return self._latest_integration_time
        else:
            return None

    def set_integration_time(self, milliseconds):
        """set the integration time"""
        e = ctypes.c_int()
        if milliseconds < self.minimum_integration_time:
            raise ValueError("Cannot set integration time below %d microseconds" % self.minimum_integration_time)
        seabreeze.seabreeze_set_integration_time(self.index, byref(e), c_ulong(int(milliseconds * 1000)))
        check_error(e)
        self._latest_integration_time = milliseconds

    integration_time = property(get_integration_time, set_integration_time)

    def get_minimum_integration_time(self):
        """minimum allowable value for integration time"""
        if self._minimum_integration_time is None:
            e = ctypes.c_int()
            min_time = seabreeze.seabreeze_get_minimum_integration_time_micros(self.index, byref(e))
            check_error(e)
            self._minimum_integration_time = min_time / 1000.
        return self._minimum_integration_time

    minimum_integration_time = property(get_minimum_integration_time)

    def get_tec_enable(self):
        return self._tec_enabled

    def set_tec_enable(self, state=True):
        """
        Turn the cooling system on or off.
        """
        e = ctypes.c_int()
        seabreeze.seabreeze_set_tec_enable(self.index, byref(e), c_int(state))
        check_error(e)
        self._tec_enabled = state

    enable_tec = property(get_tec_enable, set_tec_enable)

    def get_tec_temperature(self):
        """get current temperature"""
        e = ctypes.c_int()
        read_tec_temperature = seabreeze.seabreeze_read_tec_temperature
        read_tec_temperature.restype = c_double
        temperature = read_tec_temperature(self.index, byref(e))
        check_error(e)
        return temperature

    def set_tec_temperature(self, temperature):
        """enable the cooling system and set the temperature"""
        if not self.enable_tec:
            self.enable_tec = True
        e = ctypes.c_int()
        seabreeze.seabreeze_set_tec_temperature(self.index, byref(e), c_double(temperature))
        seabreeze.seabreeze_set_tec_enable(self.index, byref(e), 1)
        check_error(e)

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
        """Return the cached wavelengths property"""
        if self._wavelengths is None:
            self._wavelengths = self.read_wavelengths()
        return self._wavelengths

    wavelengths = property(get_wavelengths)

    def read_spectrum(self):
        """get the current reading from the spectrometer's sensor"""
        self._comms_lock.acquire()
        e = ctypes.c_int()
        N = seabreeze.seabreeze_get_formatted_spectrum_length(self.index, byref(e))
        spectrum_carray = (c_double * N)()  # this should create a c array of doubles, length N
        seabreeze.seabreeze_get_formatted_spectrum(self.index, byref(e), byref(spectrum_carray), N)
        self._comms_lock.release()  # NB we release the lock before throwing exceptions
        check_error(e)  # throw an exception if something went wrong
        return np.array(list(spectrum_carray))

    def get_qt_ui(self, control_only=False):
        """Return a Qt Widget for controlling the spectrometer.

        If control_only is true, this will not contain a graph of the spectrum.
        """
        if control_only:
            return OceanOpticsControlUI(self)
        else:
            return SpectrometerUI(self)


oo_base, oo_widget = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ocean_optics_controls.ui'))

#class OceanOpticsControlUI(SpectrometerControlUI, oo_base, oo_widget):
class OceanOpticsControlUI(oo_base, SpectrometerControlUI, oo_widget):
    def __init__(self, spectrometer):
        assert isinstance(spectrometer, OceanOpticsSpectrometer), 'spectrometer must be an OceanOpticsSpectrometer'
        super(OceanOpticsControlUI, self).__init__(spectrometer)
        #self.setupUi(self)

        self.tec_temperature.setValidator(QtGui.QDoubleValidator())
        self.tec_temperature.textChanged.connect(self.check_state)
        self.tec_temperature.textChanged.connect(self.update_param)
        self.tec_temperature.setText(str(spectrometer.tec_temperature))

        self.enable_tec.stateChanged.connect(self.update_enable_tec)
        self.enable_tec.setChecked(self.spectrometer.enable_tec)
        self.read_tec.clicked.connect(self.update_tec)

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

    def update_enable_tec(self, state):
        if state == QtCore.Qt.Checked:
            self.spectrometer.enable_tec = True
        elif state == QtCore.Qt.Unchecked:
            self.spectrometer.enable_tec = False

    def update_tec(self):
        self.tec_temperature.setText(str(self.spectrometer.tec_temperature))


# example code:
if __name__ == "__main__":
    from nplab.instrument.spectrometer import Spectrometers
    import sys
    from nplab.utils.gui import get_qt_app

    try:
        N = len(list_spectrometers())
        print "Spectrometers connected:", list_spectrometers()
        print "%d spectrometers found" % N
        assert N != 0, 'There are no Ocean Optics spectrometers attached (are you using the seabreeze drivers?)'

        spectrometers = OceanOpticsSpectrometer.get_spectrometers()
        for s in spectrometers.spectrometers:
            print "spectrometer %s is a %s" % (s.serial_number, s.model_name)
            if s.model_name in ["QE65000", "QE-PRO"]:
                s.set_tec_temperature = -20
            s.read()
 #       app = get_qt_app()
 #       ui = spectrometers.get_qt_ui()
 #       ui.show()
 #       sys.exit(app.exec_()) #this is the "long way" of running a GUI
        spectrometers.show_gui()  # the "short way" of running a GUI
    except OceanOpticsError as error:
        print "An error occurred with the spectrometer: %s" % error
    finally:
        try:
            pass
            #           del s     #we close the spectrometer afterwards, regardless of what happened.
        except:  # of course, if there's no spectrometer this will fail, hence the error handling
            shutdown_seabreeze()  # reset things if we've had errors
            print "The spectrometer did not close cleanly. SeaBreeze has been reset."
# to alter max/min: s.spectrum_plot.value_mapper.range.high=0.01
