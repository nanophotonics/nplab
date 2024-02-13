# -*- coding: utf-8 -*-
"""
Created on Tue Nov 22 18:25:48 2022

@author: HERA
"""

from __future__ import print_function

import os
import time

import matplotlib.pyplot as plt
import numpy as np
from decorator import decorator
from nplab import datafile
from nplab.instrument import Instrument
from nplab.instrument.electronics.power_control import PowerControl
from nplab.instrument.spectrometer.spectrometer_aligner import \
    SpectrometerAligner
from nplab.ui.ui_tools import UiTools
from nplab.utils.gui import QtWidgets, uic
from nplab.utils.notified_property import (DumbNotifiedProperty,
                                           NotifiedProperty,
                                           register_for_property_changes)
from nplab.utils.thread_utils import background_action, locked_action
from scipy.interpolate import UnivariateSpline
from nplab.instrument.electronics.power_control import PowerControl
global PLOT_AUTOFOCUS
PLOT_AUTOFOCUS = False


def laser_merit(im):
    '''way of determining how focused a laser beam is'''

    im = np.sum(im, axis=2)  # convert to grey
    x_len, y_len = np.shape(im)
    xindices = np.arange(x_len // 2 - 5,
                         x_len // 2 + 5)  #take a line ten pixels wide
    x_slice = np.mean(np.take(im, xindices, axis=0),
                      axis=0)  #average across those 10
    spl = UnivariateSpline(list(range(len(x_slice))),
                           x_slice - x_slice.max() / 3)  #fit a spline,
    roots = spl.roots()  #  get the FWHM

    if PLOT_AUTOFOCUS:

        plt.figure('laser plot')
        plt.plot(x_slice - x_slice.max() / 3, color='tab:red')
        plt.vlines(roots)

    try:
        merit = 1 / (max(roots) - min(roots))
    except:
        merit = 0
    return merit


exact_wavelengths = {'_633': 632.8, '_785': 784.8}


@decorator
def laser_measurement(f, self, *args, **kwargs):

    wutter_open = self.wutter.is_open()
    vutter_closed = self.vutter.is_closed()

    if wutter_open: self.wutter.close_shutter()
    if vutter_closed:
        self.vutter.toggle()  # toggle is more efficient than open/close

    to_return = f(self, *args, **kwargs)

    if wutter_open: self.wutter.open_shutter()
    if vutter_closed: self.vutter.toggle()

    return to_return


@decorator
def white_light_measurement(f, self, *args, **kwargs):
    wutter_closed = self.wutter.is_closed()
    vutter_open = self.vutter.is_open()

    if wutter_closed: self.wutter.close_shutter()
    if vutter_open:
        self.vutter.toggle()  # toggle is more efficient than open/close

    to_return = f(self, *args, **kwargs)

    if wutter_closed: self.wutter.open_shutter()
    if vutter_open: self.vutter.toggle()

    return to_return


class Lab(Instrument):
    '''
    meta-instrument for all the equipment in Lab 6. Works analogously to CWL in many respects.
    Takes care of data handling, use the create_dataset, create_group functions. 
    Keeps track of all their states. Functions which will be called by buttons should be put in here
    Each instrument should have its own gui though!
    '''
    def __init__(self, equipment_dict, init=True):
        Instrument.__init__(self)
        for key, val in equipment_dict.items():
            setattr(self, key, val)
        self.initialize_instruments()
        self.datafile = datafile.current()

    def initialize_instruments(self):
        # self.kymera.pixel_number = 1024
        # self.kymera.pixel_width = 26
        # self.kymera.slit_width = 100
        #self.kymera.slit_width = 100
        #self.andor.HSSpeed = 1 # Horizontal read speed
        #self.andor.Shutter = (1, 0, 0, 0) # closed
        #self.andor.SetTemperature = -90
        #self.andor.cooler = True
        #self.andor.Exposure = 1
        #self.andor.ReadMode = 3 # kinetic mode
        #self.andor.SingleTrack = (150, 30) # centered at 100, 30 rows
        #self.andor.AcquisitionMode = 1 # single acquisition

        #self.stage.move(75, axis='z')
 #       self.aligner = SpectrometerAligner(self.dark_spec, self.stage)

        try:
            self.cwl.load_calibration()
        except:
            print('no xy calibration found for cwl')

        def pre():
            powermeter_live = self.powermeter.live
            wutter_open = self.wutter.is_open()
            #vutter_closed = self.wutter.is_closed()

            self.powermeter.live = False
            if wutter_open: self.wutter.close_shutter()
            #if vutter_closed: self.vutter.open_shutter()

            return powermeter_live, wutter_open, #vutter_closed

        def post(powermeter_live, wutter_open):#, vutter_closed):
            self.powermeter.live = powermeter_live
            if wutter_open: self.wutter.open_shutter()
            #if vutter_closed: self.vutter.close_shutter()

        self.pc = PowerControl(self.filter_wheel,
                                self.powermeter,
                                before_calibration_func=pre,
                                after_calibration_func=post,
                                move_range=(0, 360))

    @laser_measurement
    def fancy_capture(self):
        '''
        Takes a spectrum on the shamdor, but turns off the white light and turns on the laser first, 
        then restores the instrument to its initial state
        '''
        return self.andor.raw_image(update_latest_frame=True)

    @laser_measurement
    def focus_with_laser(self, exp=5, gain=1, OD_pos=11):
        '''uses the laser to focus. Sets camera to minimum and laser power.
        takes a slice of the image and uses the FWHM of the laser area as a merit for focused-ness
        '''
        init_z = self.cwl.stage.position[-1]
        initial_exp = self.cwl.camera.exposure
        initial_gain = self.cwl.camera.gain
        # initial_power = self.power_wheel.position

        self.cwl.camera.exposure = exp
        self.cwl.camera.gain = gain
        # self.power_wheel.position = OD_pos

        time.sleep(0.2)

        self.cwl.autofocus(merit_function=laser_merit)

        self.cwl.camera.exposure = initial_exp
        self.cwl.camera.gain = initial_gain
        # self.power_wheel.position = initial_power

        return init_z - self.cwl.stage.position[-1]
    
    @laser_measurement
    def laser_autofocus(self,step_size= 0.1,steps = 20, exp = 1.0, gain = 1.0, wheel_pos = 240):
        # power_wheel_pos = power_wheel.position
        # power_wheel.move(wheel_pos)
        
        original_exposure = self.cam.exposure
        original_gain = self.cam.gain
        self.cam.exposure= exp
        self.cam.gain = gain
        self.cwl.stage.Z.move_rel(-0.5*step_size*steps)
        max_pixels = []
        poses = []    
        for i in range(steps):
            image = self.cam.raw_image()
            grey_im = np.sum(image,axis=2)
            flat_im = np.reshape(grey_im,grey_im.shape[0]*grey_im.shape[1])
            max_pix = np.average(flat_im[flat_im.argsort()[-10:]])
            max_pixels.append(max_pix)
            poses.append(self.cwl.stage.Z.position)
            self.cwl.stage.Z.move_rel(step_size)
        new_pos = np.array(poses)[np.array(max_pixels)==np.max(max_pixels)]
        # power_wheel.move(power_wheel_pos)
        self.cwl.stage.Z.move(new_pos[0])
        self.cam.exposure = original_exposure
        self.cam.gain = original_gain

    def get_qt_ui(self):
        self.gui = LabGui(self)
        return self.gui
    



class LabGui(QtWidgets.QWidget, UiTools):
    use_shifts = DumbNotifiedProperty(False)

    exp = DumbNotifiedProperty(5)
    gain = DumbNotifiedProperty(1)
    OD_pos = DumbNotifiedProperty(11)

    def __init__(self, lab):
        super().__init__()
        uic.loadUi(os.path.dirname(__file__) + '\setup_gui.ui', self)
        self.lab = lab
        self.auto_connect_by_name()
        self.SetupSignals()
        #register_for_property_changes(self.lab, 'laser', self.laser_changed)
        register_for_property_changes(self, 'use_shifts',
                                      self.use_shifts_changed)
        #self.laser_changed(self.lab.laser)

    def SetupSignals(self):
        self.fancy_capture_pushButton.clicked.connect(
            lambda: self.lab.fancy_capture())
        # using a lambda as decorated functions and pyqt bindings don't play well together
        self._633_radioButton.clicked.connect(self.update_laser_gui)
        self._785_radioButton.clicked.connect(self.update_laser_gui)

    @background_action
    def focus_with_laser(self, *args):  # Something passes a False to this func
        return self.lab.focus_with_laser(self.exp, self.gain, self.OD_pos)

    def use_shifts_changed(self, new):
        self.lab.shamdor.use_shifts = new

    def update_laser_gui(self):
        s = self.sender()
        if s is self._633_radioButton:
            self.lab.laser = '_633'
        elif s is self._785_radioButton:
            self.lab.laser = '_785'

    def laser_changed(self, new):
        eval(f'self.{new}_radioButton.setChecked(True)')


if __name__ == '__main__':

    from nplab.instrument.camera.camera_with_location import CameraWithLocation
    from nplab.instrument.camera.lumenera import LumeneraCamera
    from nplab.instrument.spectrometer.Kymera import Kymera
    from nplab.instrument.spectrometer.seabreeze import OceanOpticsSpectrometer
    
    from nplab.instrument.stage.apt_vcp_motor import DC_APT
    from nplab.instrument.stage.parker_stepper import ParkerStepper
    #from nplab.instrument.stage.camera_stage_mapper_qt import CameraStageMapper
    # from nplab.instrument.stage.xyzstage_wrapper import piezoconcept_thorlabsMSL02_wrapper
    from nplab.instrument.stage.Piezoconcept_micro import Piezoconcept
    from nplab.instrument.stage.xy_z_wrapper import XY_ZWrapper
    
    from nplab.ui.data_group_creator import DataGroupCreator
    from nplab.utils.gui_generator import GuiGenerator
    
    from nplab.instrument.shutter.thorlabs_sc10 import ThorLabsSC10
    from nplab.instrument.shutter.BX51_uniblitz import Uniblitz
    from nplab.instrument.spectrometer.kandor import Kandor
    
    from Thorlabs_ELL18K import ELL18K as FilterWheel
    from nplab.instrument.electronics.thorlabs_pm100 import ThorlabsPowermeter
    
    from nplab.instrument.stage.prior import ProScan
    
    os.chdir(r'C:\Users\hera\Documents')
    # #xy_stage = DC_APT(port='COM7',
    #                   destination={
    #                       'x': 0x21,
    #                       'y': 0x22
    #                   },
    #                   stage_type='MLS',
    #                   unit='u')

    #z_stage = Piezoconcept('COM5')
    stage = ProScan("COM7") 
    cam = LumeneraCamera(1)
    cwl = CameraWithLocation(cam, stage)
    try:
        cwl.load_calibration()
    except KeyError:
        pass
    dark_spec = OceanOpticsSpectrometer(0)
    # kymera = Kymera()
    # kymixis = Kymixis()
    kandor = Kandor(pixel_number=1600)
    parker = ParkerStepper('COM4')
    vutter = ThorLabsSC10('COM13')
    mutter = ThorLabsSC10('COM14')
    wutter = Uniblitz('COM16')
    filter_wheel = FilterWheel('COM12')    
    # powermeter = ThorlabsPowermeter('USB0::0x1313::0x807B::200207307::0::INSTR')

    instr_dict = {
        'dark_spec': dark_spec,
        'cwl': cwl,
        'cam': cam,
        'stage': stage,
        # 'pixis': kymixis,
        # 'kymera': kymixis.kymera,
        'andor': kandor,
        'kymera': kandor.kymera,
        'wutter': wutter,
        'vutter': vutter,
        'mutter': mutter,
        'filter_wheel': filter_wheel,
        # 'powermeter': powermeter
    }

    # pometer = ThorlabsPowermeter('USB0::0x1313::0x807B::200207307::INSTR')

    lab = Lab(instr_dict)
    print('Lab initialized, generating GUI')
    gui_equipment_dict = {
        **instr_dict,
        **{
            'data_group_creator': DataGroupCreator(),
            # 'power_control': lab.pc
        }
    }

    lab.generated_gui = GuiGenerator(
        gui_equipment_dict,
        terminal=False,
        dock_settings_path=os.path.dirname(__file__) + r'\gui_config.npy',
        scripts_path=os.path.dirname(__file__) + r'\scripts')

    # def restart(lab):
    #     '''
    #     restarts the gui. If you redefine a class by running
    #     it in the console, it will use the updated version!
    #     '''
    #     if hasattr(lab, 'generated_gui'):
    #         lab.generated_gui.close()
    #         lab = Lab(equipment_dict, init = False)
    #         print('Lab initialized, generating GUI')
    #         lab.generated_gui = GuiGenerator(gui_equipment_dict,
    #                            dock_settings_path = os.path.dirname(__file__)+r'\gui_config.npy',
    #                            scripts_path = os.path.dirname(__file__)+r'\scripts')