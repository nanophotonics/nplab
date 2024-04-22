from nplab.instrument.spectrometer import Spectrometer
from nplab.instrument.spectrometer.wasatch_usb import SIGspectrometer
from h5py import File
import numpy as np

class XS(Spectrometer):
    
    metadata_property_names = ('model_name', 'serial_number', 'integration_time',
                               'reference', 'background', 'wavelengths',
                               'background_int', 'reference_int','variable_int_enabled',
                               'background_gradient','background_constant', 'averaging_enabled'
                               ,'absorption_enabled', 'laser_enabled', 'gain', 'laser_power')
    
    def __init__(self) -> None:
        
        self._spec             = SIGspectrometer()      
        self._model_name       = "SIG Raman Spectrometer"
        self._serial_number    = self._spec.serial_number
        self._wavelengths      = self._spec.wavelengths
        self._integration_time = self._spec.eeprom["startup_integration_time_ms"] / 1e3
        self._laser_enabled    = False
        self._gain             = 0.0
        self._power            = 100.0
        self._raman_mode       = True
        self._modulation       = True
        self._raman_delay      = 0
        self._watchdog         = 1.0
        self._mod_period       = 0
        self._mod_width        = 0
    
    def get_serial_number(self):
        return self._serial_number
    
    
    def get_integration_time(self):
        return self._integration_time
    
    
    def set_integration_time(self, value):
        self._integration_time = value
        self._spec.set_integration_time_ms(int(1e3 * value))
        
    
    def get_wavelengths(self):
        return self._spec.wavelengths
    
    
    def read_spectrum(self, bundle_metadata=False):
        self.latest_raw_spectrum = np.array(self._spec.get_spectrum())
        return self.bundle_metadata(self.latest_raw_spectrum, enable=bundle_metadata)
    
    
    @property    
    def laser_enabled(self) -> bool:
        return self._laser_enabled
    
    
    @laser_enabled.setter
    def set_laser_enabled(self, enabled: bool, warmup:int=0):
        self._laser_enabled = enabled
        self._spec.set_laser_enable(enabled, warmup)
    
    
    @property
    def gain(self) -> float:
        return self._gain
    
    
    @gain.setter
    def set_gain(self, db: float):
        self._gain = db
        self._spec.set_gain_db(db)
        
    
    @property
    def laser_power(self) -> float:
        return self._power
    
    
    @laser_power.setter
    def set_laser_power(self, power:float):
        self._power = power
        self._spec.set_laser_power_perc(power)
        
    
    @property
    def raman_mode(self) -> bool:
        return self._raman_mode
    
    
    @raman_mode.setter
    def set_raman_mode(self, mode: bool):
        self._raman_mode = mode
        self._spec.set_raman_mode(mode)
        
    
    @property
    def modulation(self) -> bool:
        self._modulation
        
    
    @modulation.setter
    def set_modulation(self, mode: bool):
        self._modulation = mode
        self._spec.set_modulation_enable(mode)
        
        
    @property
    def raman_delay(self) -> int:
        return self._raman_delay
    
    
    @raman_delay.setter
    def set_raman_delay(self, delay: int):
        self._raman_delay = delay
        self._spec.set_raman_delay_ms(delay)
        
        
    @property
    def laser_watchdog(self) -> float:
        return self._watchdog
    
    
    @laser_watchdog.setter
    def set_laser_watchdog(self, value: float):
        self._watchdog = value
        self._spec.set_watchdog_sec(value)
        
        
    @property
    def laser_modulation_period(self) -> int:
        return self._mod_period
    
    
    @laser_modulation_period.setter
    def set_laser_modulation_period(self, period: int):
        self._mod_period = period
        self._spec.set_mod_period_us(period)
        
    
    @property
    def laser_modulation_width(self) -> int:
        return self._mod_width
    
    
    @laser_modulation_width.setter
    def set_laser_modulation_width(self, width: int):
        self._mod_width = width
        self._spec.set_mod_width_us(width)

