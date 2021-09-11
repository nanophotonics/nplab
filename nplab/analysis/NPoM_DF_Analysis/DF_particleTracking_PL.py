# -*- coding: utf-8 -*-
"""
Created on Fri May 05 09:57:21 2017

@author: wmd22
"""
from __future__ import print_function

from builtins import str
from builtins import range
from nplab.instrument.camera.lumenera import LumeneraCamera
from nplab.instrument.stage.prior import ProScan
from nplab.instrument.spectrometer.seabreeze import OceanOpticsSpectrometer
from nplab.instrument.light_sources.cube_laser import CubeLaser
from nplab.instrument.shutter.BX51_uniblitz import Uniblitz
import time
import threading
from nplab.instrument.spectrometer.spectrometer_aligner import SpectrometerAligner
from nplab.instrument.camera.camera_with_location_car72 import CameraWithLocation
from nplab.utils.array_with_attrs import ArrayWithAttrs
from particle_tracking_app.particle_tracking_wizard_car72 import TrackingWizard
import numpy as np

stage = ProScan("COM3", hardware_version = 2)
cam = LumeneraCamera(1)
spec = OceanOpticsSpectrometer(0)

CWL = CameraWithLocation(cam,stage, init_exp = 582)
CWL.show_gui(blocking =False)
stage.show_gui(blocking = False) 
spec.show_gui(blocking = False)
alinger = SpectrometerAligner(spec,stage)
equipment_dict = {'spectrometer':spec, 'alinger':alinger}

stop_event = threading.Event()
#shutter = Uniblitz('COM9')

wizard = TrackingWizard(CWL, equipment_dict, task_list = ['CWL.thumb_image','alinger.z_scan'])
wizard.data_file.show_gui(blocking = False)
wizard.show()  

def irradiate(time = 10.0,laser_power = 10,number_of_spec = 10):
    spectrum_list = []
    for i in range(number_of_spec):
        spectrum_list.append(spec.read_spectrum())
    attrs = spec.metadata
    attrs['hi'] = 5
    return ArrayWithAttrs(spectrum_list,attrs = attrs)

def recenter_particle():
    feature = wizard.current_feature
    CWL.move_to_feature(feature, ignore_z_pos = True)
    
def takePlBg(laserPower):
    print('Taking PL Background...')
    cube = CubeLaser('COM4')
    shutter = Uniblitz('COM9')
    shutter.open_shutter()
    
    if 'PL Background' not in list(wizard.data_file.keys()):
        wizard.data_file.create_group('PL Background')
        
    gPlBg = wizard.data_file['PL Background']
    cube.set_power(laserPower)
    time.sleep(1.0)  
    gPlBg.create_dataset(name = 'Power %s' % (laserPower), data = spec.read_spectrum(),
                                                  attrs = {'laser_power' : laserPower,
                                                           'wavelengths' : spec.get_wavelengths()})
    
    gPlBg.attrs.update(spec.metadata)
    time.sleep(1.0)
    cube.set_power(0)
    time.sleep(0.5)
    shutter.close_shutter()
    cube.close()
    shutter.close()
    print('\tPL Background successfully measured')

def laserOn(laserPower):
    cube = CubeLaser('COM4')
    cube.mode_switch()
    shutter = Uniblitz('COM9')
    shutter.open_shutter()
    cube.set_power(laserPower)

def laserOff():
    cube = CubeLaser('COM4')
    shutter = Uniblitz('COM9')
    cube.set_power(0)
    shutter.close_shutter()
    cube.close()
    shutter.close()


def df_pl_with_laser_scan(power_iter=1, number_of_iter=1, laser_power=3, number_of_spec=2, Increment=1,
                          cam_exposure = 600, cam_gain = 23):
    """
    Laser irradiation for particle tracking program 
    """
    irad_group = wizard.particle_group.create_group('dark field with irradiation')
    
    log = wizard.data_file['nplab_log']
    lastEventName = sorted(list(log.keys()), key = lambda event: log[event].attrs['creation_timestamp'])[-1]
    lastEvent = str(log[lastEventName])
    
    if 'error centering on feature' in lastEvent.lower():
        print('Readjusting camera exposure and gain')
        CWL.camera.exposure = cam_exposure
        CWL.camera.gain = cam_gain
        print('Exposure set to %s, gain to %s' % (cam_exposure, cam_gain))
        shutter = Uniblitz('COM9')
        shutter.open_shutter()
        shutter.close_shutter()
        shutter.close()
        
    cube = CubeLaser('COM4')
    cube.mode_switch()
    shutter = Uniblitz('COM9')
    laser_power = laser_power
    for i in range (power_iter):
        for i in range (number_of_iter):#while stop_event.is_set()==False and iterations<spectra_num:            

            try:
                shutter.open_shutter()
            except Exception as e:
                print(e, end=' ')
                print('shutter operation failure')
        
            try:
                cube.set_power(laser_power)
                time.sleep(1.0)
            except Exception as e:
                print(e, end=' ')
                print('laser power write fail')
            print(laser_power)
            for i in range(number_of_spec):
                dIrad = irad_group.create_dataset(name = 'PL_%s_%s' % (laser_power, i),
                                                  data = spec.read_spectrum(),
                                                  attrs = {'laser_power' : laser_power,
                                                           'wavelengths' : spec.get_wavelengths()})
                dIrad.attrs.update(spec.metadata)
            
            try:
                cube.set_power(0)
                shutter.close_shutter()
            except Exception as e:
                print(e, end=' ')
                print('laser power write fail')
            print(laser_power)
            time.sleep(1) 
        laser_power=laser_power+Increment
    cube.close()
    shutter.close()