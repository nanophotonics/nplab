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
import traits
from traits.api import HasTraits, Property, Instance, Float, Int, String, Button, Bool, on_trait_change
import traitsui
from traitsui.api import View, Item, Group, HGroup, VGroup
import chaco
from chaco.api import ArrayPlotData, Plot
from chaco.chaco_plot_editor import ChacoPlotItem
from enable.component_editor import ComponentEditor
import threading
from nplab.instrument import Instrument



try:
    seabreeze = ctypes.cdll.seabreeze
except WindowsError as e: #if the DLL is missing, warn, either graphically or with an exception.
    explanation="""
WARNING: could not link to the SeaBreeze DLL.
    
Make sure you have installed the SeaBreeze driver from the Ocean Optics 
website (http://downloads.oceanoptics.com/OEM/), and that its version matches 
your Python architecture (64 or 32 bit).  See the module help for more 
information"""
    try:
        traitsui.message.error(explanation,"SeaBreeze Driver Missing", buttons=["OK"])
    except Exception as e:
        print "uh oh, problem with the message..."
        print e
        pass
    finally:
        raise Exception(explanation) 

def error_string(error_code):
    """convert an error code into a human-readable string"""
    N = 1024 #we need to create a buffer into which we place the returned string
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
        while True: #we stop when we run out of spectrometers, signified by an exception
            #the line below creates a spectrometer, initialises, gets the serial number, and closes again
            spectrometers.append(OceanOpticsSpectrometer(n).serial_number)
            #if the spectrometer does not exist, it raises an exception.
            n+=1
    except OceanOpticsError:
        pass
    finally:
        return spectrometers
        
def shutdown_seabreeze():
    """shut down seabreeze, useful if anything has gone wrong"""
    seabreeze.seabreeze_shutdown()
        
class OceanOpticsError(Exception):
    def __init__(self,code):
        self.code = code
    def __str__(self):
        return "Code %d: %s." % (self.code, error_string(self.code))

class OceanOpticsSpectrometer(Instrument, HasTraits):
    """Class representing the Ocean Optics spectrometers, via the SeaBreeze library
    
    The constructor takes a single numeric argument, which is the index of the 
    spectrometer you want, starting at 0.  It has traits, so you can call up a
    GUI to control the spectrometer with s.configure_traits."""
    model_name = Property(trait=String()) #Type of the spectrometer (e.g. QE65000)
    serial_number = Property(trait=String()) #The spectrometer's serial number
    integration_time = Property(trait=Float(None)) #Integration time in milliseconds
    tec_temperature = Property(trait=Float(None)) #TEC temperature

    latest_spectrum = traits.trait_numeric.Array(shape=(None)) #last spectrum read (except using the fast read_spectrum method)
    latest_raw_spectrum = traits.trait_numeric.Array(shape=(None)) #Ditto for background
    wavelengths = Property(trait=traits.trait_numeric.Array(shape=(None))) #Ditto for wavelength
    reference = traits.trait_numeric.Array(shape=(None)) #Ditto for reference
    background = traits.trait_numeric.Array(shape=(None)) #Ditto for background
    is_referenced = Property(trait=Bool(False)) #whether the reference and background are set
    is_background_compensated = Property(trait=Bool(False)) #whether the background is set

    spectrum_plot = Property(trait=Instance(Plot)) #a graph of the spectrum against wavelength, for the UI
    take_spectrum = Button()
    live_view = Bool(False)
    take_reference = Button()
    take_background = Button()
    clear_reference = Button()
    clear_background = Button()

    traits_view = View(HGroup(
                        VGroup(
                            VGroup(
                                Item(name="integration_time",label = "Integration Time/ms"),
                                Item(name="take_spectrum",show_label=False),
                                Item(name="live_view")
                            ),
                            HGroup(
                                VGroup(
                                    Item(name="take_reference",show_label=False),
                                    Item(name="clear_reference",show_label=False),
                                ),
                                VGroup(
                                    Item(name="take_background",show_label=False),
                                    Item(name="clear_background",show_label=False),
                                ),
                            ),
                        springy=False),
                        Item(name="spectrum_plot",editor=ComponentEditor(),show_label=False),
                        #ChacoPlotItem("wavelengths","latest_spectrum",show_label=False),
                    layout="split"),resizable=True,width=500,height=400,title="Ocean Optics Spectrometer")

    def __init__(self, index):
        """initialise the spectrometer"""
        self.index = index #the spectrometer's ID, used by all seabreeze functions
        self._comms_lock = threading.RLock()
        self._isOpen = False
        self._open()
        super(OceanOpticsSpectrometer, self).__init__()
        HasTraits.__init__(self)
    def __del__(self):
        self.live_view=False
        self._close()
        return self
    def _open(self, force=False):
        """Open communications with the spectrometer (called on initialisation)."""
        if(self._isOpen and not force): #don't cause errors if it's already open
            return
        else:
            e = ctypes.c_int()
            seabreeze.seabreeze_open_spectrometer(self.index,byref(e))
            check_error(e)
            self._isOpen = True
    def _close(self,force=False):
        """Close communication with the spectrometer and release it."""
        if(not self._isOpen and not force):
            return
        else:
            e = ctypes.c_int()
            seabreeze.seabreeze_close_spectrometer(self.index,byref(e))
            check_error(e)
            self._isOpen = False
    @traits.api.cached_property
    def _get_model_name(self): 
        """Get the type of the spectrometer."""
        N = 32 #make a buffer for the DLL to return a string into
        s = ctypes.create_string_buffer(N)
        e = ctypes.c_int()
        seabreeze.seabreeze_get_spectrometer_type(self.index, byref(e), byref(s), N)
        check_error(e)
        return s.value
    def get_usb_descriptor(self,id): 
        """get the spectrometer's USB descriptor"""
        N = 32 #make a buffer for the DLL to return a string into
        s = ctypes.create_string_buffer(N)
        e = ctypes.c_int()
        seabreeze.seabreeze_get_usb_descriptor_string(self.index, byref(e), c_int(id), byref(s), N)
        check_error(e)
        return s.value
    @traits.api.cached_property
    def _get_serial_number(self): 
        """get the spectrometer's serial number"""
        N = 32 #make a buffer for the DLL to return a string into
        s = ctypes.create_string_buffer(N)
        e = ctypes.c_int()
        seabreeze.seabreeze_get_serial_number(self.index, byref(e), byref(s), N)
        check_error(e)
        return s.value
    def _get_integration_time(self):
        """return the last set integration time"""
        if hasattr(self,"_latest_integration_time"):
            return self._latest_integration_time
        else:
            return None
    def _set_integration_time(self,milliseconds): 
        """set the integration time"""
        e = ctypes.c_int()
        if milliseconds*1000 < self.minimum_integration_time():
            raise ValueError("Cannot set integration time below %d microseconds" % self.minimum_integration_time())
        seabreeze.seabreeze_set_integration_time(self.index, byref(e), c_ulong(int(milliseconds*1000)))
        check_error(e)
        self._latest_integration_time = milliseconds
    def minimum_integration_time(self): 
        """minimum allowable value for integration time"""
        e = ctypes.c_int()
        mintime = seabreeze.seabreeze_get_minimum_integration_time_micros(self.index, byref(e))
        check_error(e)
        return mintime
    def _get_tec_temperature(self): 
        """get current temperature"""
        e = ctypes.c_int()
        read_tec_temperature = seabreeze.seabreeze_read_tec_temperature
        read_tec_temperature.restype = c_double
        temperature = read_tec_temperature(self.index, byref(e))
        check_error(e)
        return temperature
    def _set_tec_temperature(self, temperature): 
        """enable the cooling system and set the temperature"""
        e = ctypes.c_int()
        seabreeze.seabreeze_set_tec_temperature(self.index, byref(e), c_double(temperature))
        seabreeze.seabreeze_set_tec_enable(self.index, byref(e), 1)
        check_error(e)
    def disable_tec(self): 
        """turn off the cooling system"""
        seabreeze.seabreeze_set_tec_enable(self.index, byref(e), 0)
        check_error(e)
    def read_wavelengths(self): 
        """get an array of the wavelengths"""
        self._comms_lock.acquire()
        e = ctypes.c_int()
        N = seabreeze.seabreeze_get_formatted_spectrum_length(self.index, byref(e))
        wavelengths_carray = (c_double * N)() #this should create a c array of doubles, length N
        seabreeze.seabreeze_get_wavelengths(self.index, byref(e), byref(wavelengths_carray), N)
        self._comms_lock.release()
        check_error(e)
        return np.array(list(wavelengths_carray))
    @traits.api.cached_property 
    def _get_wavelengths(self): #this function should only be called once, thanks to the @cached_property decorator
        return self.read_wavelengths()
    def read_spectrum(self): 
        """get the current reading from the spectrometer's sensor"""
        self._comms_lock.acquire()
        e = ctypes.c_int()
        N = seabreeze.seabreeze_get_formatted_spectrum_length(self.index, byref(e))
        spectrum_carray = (c_double * N)() #this should create a c array of doubles, length N
        seabreeze.seabreeze_get_formatted_spectrum(self.index, byref(e), byref(spectrum_carray), N)
        self._comms_lock.release() #NB we release the lock before throwing exceptions
        check_error(e) #throw an exception if something went wrong
        return np.array(list(spectrum_carray))
    def _take_spectrum_fired(self): self.update_spectrum()
    def update_spectrum(self, spectrum=None):
        """read the spectrum, storing a copy in the trait.
        
        It is the function to call if you want to get a processed spectrum.
        It can also be used to manually update the interface with a previously
        aquired spectrum."""
        self.latest_raw_spectrum = self.read_spectrum() if spectrum is None else spectrum
        if self.is_background_compensated:
            if self.is_referenced:
                old_error_settings = np.seterr(all='ignore')
                spectrum = (self.latest_raw_spectrum - self.background)/(self.reference - self.background)
                np.seterr(**old_error_settings)
                spectrum[np.isinf(spectrum)]=np.NaN #if the reference is nearly 0, we get infinities - just make them all NaNs.
                self.latest_spectrum = spectrum #NB we shouldn't work directly with self.latest_spectrum or it will play havoc with updates...
            else:
                self.latest_spectrum = self.latest_raw_spectrum - self.background
        else:
            self.latest_spectrum = self.latest_raw_spectrum
        return self.latest_spectrum
    def get_metadata(self):
        return self.get(['model_name','serial_number','integration_time','tec_temperature','reference','background','wavelengths'])
    def read(self): 
        """convenience method returning a tuple of wavelengths, spectrum"""
        return (self.wavelengths, self.update_spectrum())
    @on_trait_change('take_background')
    def update_background(self):
        """Acquire a new spectrum and use it as the background
        
        The background will be subtracted from all subsequent spectra returned
        using the read() or update_spectrum() methods."""
        self.background = self.read_spectrum()
    @on_trait_change('clear_background')
    def _clear_background(self):
        self.background = np.zeros(0)
    @on_trait_change('take_reference')
    def update_reference(self):
        """Acquire a new spectrum and use it as the reference
        
        All subsequent spectra returned by the read() or update_spectrum() 
        methods will be divided by the reference."""
        self.reference = self.read_spectrum()
    @on_trait_change('clear_reference')
    def _clear_reference(self):
        self.reference = np.zeros(0)
    @traits.api.cached_property # only draw the graph the first time it's needed
    def _get_spectrum_plot(self):
        """make a nice plot of spectrum vs wavelength"""
        self._plot_data = ArrayPlotData(wavelengths=self.wavelengths,spectrum=self.latest_spectrum)
        p = Plot(self._plot_data)
        p.plot(("wavelengths","spectrum"),type='line',color='blue')
        return p
    def _latest_spectrum_changed(self):
        if hasattr(self, "_plot_data"):
            self._plot_data.set_data("spectrum",self.latest_spectrum)
#]    def _take_spectrum_fired(self):
  #      self.update_spectrum()
    def _live_view_changed(self):
        if self.live_view==True:
            print "starting live view thread"
            try:
                self._live_view_stop_event = threading.Event()
                self._live_view_thread = threading.Thread(target=self._live_view_function)
                self._live_view_thread.start()
            except AttributeError as e: #if any of the attributes aren't there
                print "Error:", e
        else:
            print "stopping live view thread"
            try:
                self._live_view_stop_event.set()
                self._live_view_thread.join()
                del(self._live_view_stop_event, self._live_view_thread)
            except AttributeError:
                raise Exception("Tried to stop live view but it doesn't appear to be running!")
    def _live_view_function(self):
        """this function should only EVER be executed by _live_view_changed."""
        while not self._live_view_stop_event.wait(timeout=0.1):
            self.update_spectrum()
    def _get_is_referenced(self):
        return self.is_background_compensated and \
            len(self.reference)==len(self.latest_spectrum) and \
            sum(self.reference)>0
    def _get_is_background_compensated(self):
        return len(self.background)==len(self.latest_spectrum) and \
            sum(self.background)>0
#example code:
if __name__ == "__main__":
#    import matplotlib.pyplot as plt
    try:
        N=len(list_spectrometers())
        print "Spectrometers connected:", list_spectrometers()
        print "%d spectrometers found" % N
        
        def testSpectrometerGUI(n,**kwargs):
            s = OceanOpticsSpectrometer(0)
            print "spectrometer %s is a %s" % (s.serial_number, s.model_name)
            if s.model_name=="QE65000":
                s.set_tec_temperature(-20)
                print "temperature: %f C" % s.read_tec_temperature()
            s.integration_time=1e2
            s.read()
            s.configure_traits(**kwargs)
            del s
        testSpectrometerGUI(0)
        
    except OceanOpticsError as error:
        print "An error occurred with the spectrometer: %s" % error
    finally: 
        try:
            pass
 #           del s     #we close the spectrometer afterwards, regardless of what happened.
        except:       #of course, if there's no spectrometer this will fail, hence the error handling
            shutdown_seabreeze() #reset things if we've had errors
            print "The spectrometer did not close cleanly. SeaBreeze has been reset."
#to alter max/min: s.spectrum_plot.value_mapper.range.high=0.01

