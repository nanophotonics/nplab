# -*- coding: utf-8 -*-
"""
Created on Mon May 13 14:15:25 2024

@author: HERA
"""

#%% Init & imports

import os
global PLOT_AUTOFOCUS
PLOT_AUTOFOCUS = False
from setup_gui import Lab
from particle_track_mixin import InfiniteParticleTrackMixin
import threading
import time
import numpy as np
import pyvisa as visa
from scipy import interpolate



class PT_lab(Lab, InfiniteParticleTrackMixin):
    
    def __init__(self, *args, **kwargs): 
        super().__init__(*args, **kwargs)
        self._init_tracking([]) #task_list=['lab.SERS','lab.tracking']
        self.datafile.show_gui(blocking=False)


if __name__ == '__main__':
    os.chdir(r'C:\\Users\\HERA\\Documents\\GitHub\\nplab\\nplab\\Lab1_BX-60 Local Python Scripts')
    if not 'initialized' in dir():
        from nplab.ui.data_group_creator import DataGroupCreator
        from nplab.utils.gui_generator import GuiGenerator
        from nplab.instrument.camera.camera_with_location import CameraWithLocation
        from nplab.instrument.electronics.thorlabs_pm100 import ThorlabsPowermeter
        from nplab.instrument.electronics.power_meter import dummyPowerMeter
        from kandor import Kandor
        from nplab.instrument.shutter.thorlabs_sc10 import ThorLabsSC10
        from nplab import datafile
        from nplab.instrument.camera.lumenera import LumeneraCamera
        from nplab.instrument.stage.prior import ProScan
        from nplab.instrument.spectrometer.seabreeze import OceanOpticsSpectrometer
        from nplab.instrument.spectrometer.spectrometer_aligner import SpectrometerAligner
        from nplab.instrument.stage.thorlabs_ello.ell20 import Ell20, Ell20BiPositional
        from nplab.instrument.stage.Thorlabs_ELL8K import Thorlabs_ELL8K
        from nplab.instrument.stage.rotators import Rotators
        from nplab.instrument.stage.thorlabs_ello.ell6 import Ell6
        from nplab.instrument.stage.thorlabs_ello.ell8 import Ell8
        from nplab.instrument.stage.thorlabs_ello.ell14 import Ell14
        from nplab.utils.array_with_attrs import ArrayWithAttrs
        import lamp_slider as df_shutter
        # from nplab.instrument.stage.Thorlabs_ELL18K import Thorlabs_ELL18K
        from nplab.instrument.stage.thorlabs_ello.ell18 import Ell18
        from nplab.instrument.potentiostat.ivium import Ivium
        from nplab.instrument.monochromator.bentham_DTMc300 import Bentham_DTMc300
        from nplab.instrument.stage.thorlabs_ello import BusDistributor
        # from nplab.instrument.electromagnet import arduino_electromagnet # Magnet
        # from nplab.instrument.camera.thorlabs.kiralux import Kiralux
        
        
#%%


bus = BusDistributor('COM13')

wheel1 = Ell18(bus, 0, debug=0)
wheel2 = Ell18(bus, 1, debug=0)