# -*- coding: utf-8 -*-
"""
Created on Thu Jul  4 11:49:05 2024

@author: HERA
"""


import os
import numpy as np
import time
import tqdm
        
from nplab.instrument.electronics.thorlabs_pm100 import ThorlabsPowermeter
from nplab.instrument.electronics.power_meter import dummyPowerMeter
from nplab.ui.data_group_creator import DataGroupCreator
from nplab.utils.gui_generator import GuiGenerator
from nplab import datafile

from nplab.instrument.spectrometer.seabreeze import OceanOpticsSpectrometer

import pyvisa as visa
import nkt_tools
from nkt_tools.varia import Varia
from nkt_tools.extreme import Extreme

try:
    powermeter = ThorlabsPowermeter(visa.ResourceManager().list_resources()[0]) # Powermeter
except:
    powermeter = dummyPowerMeter() # Dummy powermeter
    print('no powermeter plugged in, using a dummy to preserve the gui layout')


varia = Varia()
spec = OceanOpticsSpectrometer(0)  # OceanOptics spectrometer
dgc = DataGroupCreator()
data_file = datafile.current()

equipment_dict = {
    'powermeter': powermeter,
    'spec': spec
    }

gui_equipment_dict = {
    'powermeter': powermeter,
    'dgc': dgc,
    'spec': spec
    }

gui = GuiGenerator(gui_equipment_dict)


#%% Functions for Varia

def get_bandwidth(varia = varia):
    
    bandwidth = varia.long_setpoint - varia.short_setpoint
    return bandwidth
    
def centre_setpoint(varia = varia):

    centre = (varia.long_setpoint + varia.short_setpoint)/2   
    return centre
    

#%% Measure power at diff wavelengths

group = data_file['power_calibration_100nmFWHM_1']

def power_test(start_wavelength = 400, end_wavelength = 850, step = 50, bandwidth = 100, group = group):
    
    wavelengths = np.arange(start_wavelength, end_wavelength + step, step)
    
    for wavelength in tqdm.tqdm(wavelengths, leave = True):
        
        varia.short_setpoint = wavelength - (bandwidth/2)
        varia.long_setpoint = wavelength + (bandwidth/2)
        powermeter.wavelength = wavelength
        time.sleep(5)
        power = powermeter.read_average(10)
        
        assert centre_setpoint() == wavelength, 'Error: wavelength incorrect \n' + 'set wavelength: ' + str(wavelength) +'\nactual wavelength: ' + str(centre_setpoint())
        assert get_bandwidth() == bandwidth, 'Error: bandwidth incorrect \n' + 'set bandwidth: ' + str(bandwidth) +'\nactual bandwidth: ' + str(get_bandwidth())        
        
        attrs = {'short_setpoint' : varia.short_setpoint,
                 'long_setpoint': varia.long_setpoint,
                 'bandwidth': get_bandwidth(),
                 'wavelength': centre_setpoint(),
                 'powermeter_wavelength': powermeter.wavelength}
        
        group.create_dataset(name = str(wavelength) + 'nm' +'_%d',
                             data = power, 
                             attrs = attrs)
        

#%% Measure power over time at one wavelength

def power_stability_test(wavelength = 400, bandwidth = 10, length = 10, interval = 10, group = group):
    
    varia.short_setpoint = wavelength - (bandwidth/2)
    varia.long_setpoint = wavelength + (bandwidth/2)
    powermeter.wavelength = wavelength
    assert centre_setpoint() == wavelength, 'Error: wavelength incorrect \n' + 'set wavelength: ' + str(wavelength) +'\nactual wavelength: ' + str(centre_setpoint())
    assert get_bandwidth() == bandwidth, 'Error: bandwidth incorrect \n' + 'set bandwidth: ' + str(bandwidth) +'\nactual bandwidth: ' + str(get_bandwidth())        
    
    time.sleep(5)
    
    times = np.arange(0, length * 60 + interval, interval)
    
    start_time = time.time()
    
    for this_time in times:        
    
        actual_time = time.time() - start_time
        power = powermeter.read_power()
    
        attrs = {'short_setpoint' : varia.short_setpoint,
                 'long_setpoint': varia.long_setpoint,
                 'bandwidth': get_bandwidth(),
                 'wavelength': centre_setpoint(),
                 'powermeter_wavelength': powermeter.wavelength,
                 'time' : time.time() - start_time,
                 'interval' : interval}
    
        group.create_dataset(name = str(this_time) + 's' +'_%d',
                             data = power, 
                             attrs = attrs)
        
        time.sleep(interval)


# wavelengths = np.arange(400, 900, 100) 

# for wavelength in tqdm.tqdm(wavelengths, leave = True):
        
#     group = data_file.create_group('power_stability_10min_'+str(wavelength)+'nm_10nm_width_%d')
    
#     power_stability_test(wavelength = wavelength, group = group)
    

#%% Measure spectrum at diff wavelengths

group = data_file['varia_spectrum_10nm_width_free_space_2']

def spectra_test(start_wavelength = 400, end_wavelength = 840, bandwidth = 10, group = group):
    
    wavelengths = np.arange(start_wavelength, end_wavelength + bandwidth, bandwidth)
    
    for wavelength in tqdm.tqdm(wavelengths, leave = True):

        varia.short_setpoint = wavelength - (bandwidth/2)
        varia.long_setpoint = wavelength + (bandwidth/2)
        time.sleep(10)
        spec.read_spectrum()
        spec.read_spectrum()
        spectrum = spec.read_spectrum()
        
        assert centre_setpoint() == wavelength, 'Error: wavelength incorrect \n' + 'set wavelength: ' + str(wavelength) +'\nactual wavelength: ' + str(centre_setpoint())
        assert get_bandwidth() == bandwidth, 'Error: bandwidth incorrect \n' + 'set bandwidth: ' + str(bandwidth) +'\nactual bandwidth: ' + str(get_bandwidth())        
        
        attrs = {'short_setpoint' : varia.short_setpoint,
                 'long_setpoint': varia.long_setpoint,
                 'bandwidth': get_bandwidth(),
                 'wavelength': centre_setpoint()}
        
        attrs = attrs | spec.metadata
        
        group.create_dataset(name = str(wavelength) + 'nm' +'_%d',
                             data = spectrum, 
                             attrs = attrs)
        
#%% Measure spectrum at one wavelength at different bandwidths

group = data_file['varia_spectrum_varying_width_free_space_0']

bandwidths = np.round(np.geomspace(1,400,50))

def spectra_bandwidth_test(wavelength = 640, bandwidths = bandwidths, group = group):
        
    for bandwidth in tqdm.tqdm(bandwidths, leave = True):

        varia.short_setpoint = wavelength - (bandwidth/2)
        varia.long_setpoint = wavelength + (bandwidth/2)
        time.sleep(10)
        spec.read_spectrum()
        spec.read_spectrum()
        spectrum = spec.read_spectrum()
        
        assert centre_setpoint() == wavelength, 'Error: wavelength incorrect \n' + 'set wavelength: ' + str(wavelength) +'\nactual wavelength: ' + str(centre_setpoint())
        assert get_bandwidth() == bandwidth, 'Error: bandwidth incorrect \n' + 'set bandwidth: ' + str(bandwidth) +'\nactual bandwidth: ' + str(get_bandwidth())        
        
        attrs = {'short_setpoint' : varia.short_setpoint,
                 'long_setpoint': varia.long_setpoint,
                 'bandwidth': get_bandwidth(),
                 'wavelength': centre_setpoint()}
        
        attrs = attrs | spec.metadata
        
        group.create_dataset(name = str(bandwidth) + 'nm_width' +'_%d',
                             data = spectrum, 
                             attrs = attrs)
        


    
