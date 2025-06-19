# -*- coding: utf-8 -*-
"""
Created on Thu May 23 11:31:20 2024

@author: HERA

Phtocurrent experiment, with equipment specified for BX-60 PC

"""

#%% Init & imports

import os
from nplab.ui.setup_gui import Lab 
# from setup_gui import Lab
import threading
from threading import Thread
import time
import tqdm
import numpy as np
import pyvisa as visa


class EC_lab(Lab):
    
    def __init__(self, *args, **kwargs): 
        super().__init__(*args, **kwargs)
        self.datafile.show_gui(blocking=False)



if __name__ == '__main__':
    os.chdir(r'C:\\Users\\HERA\\Documents\\GitHub\\nplab\\nplab\\Lab1_BX-60 Local Python Scripts')
    if not 'initialized' in dir():
        from nplab.ui.data_group_creator import DataGroupCreator
        from nplab.utils.gui_generator import GuiGenerator
        from nplab.instrument.electronics.thorlabs_pm100 import ThorlabsPowermeter
        from nplab.instrument.electronics.power_meter import dummyPowerMeter
        from nplab.instrument.shutter.thorlabs_sc10 import ThorLabsSC10
        from nplab import datafile
        from nplab.instrument.spectrometer.seabreeze import OceanOpticsSpectrometer
        # from nplab.instrument.stage.thorlabs_ello.ell20 import Ell20, Ell20BiPositional
        # from nplab.instrument.stage.Thorlabs_ELL8K import Thorlabs_ELL8K
        from nplab.instrument.stage.thorlabs_ello.ell8 import Ell8
        # from nplab.instrument.stage.thorlabs_ello.ell14 import Ell14
        from nplab.utils.array_with_attrs import ArrayWithAttrs
        # from nplab.instrument.stage.Thorlabs_ELL18K import Thorlabs_ELL18K
        # from nplab.instrument.stage.thorlabs_ello.ell18 import Ell18
        from nplab.instrument.potentiostat.ivium import Ivium
        # from nplab.instrument.monochromator.bentham_DTMc300 import Bentham_DTMc300
        from nplab.instrument.stage.thorlabs_ello.ell6 import Ell6
        from nplab.instrument.stage.thorlabs_ello import BusDistributor
        from nplab.instrument.monochromator.varia import Varia
        from nplab.instrument.shutter.BX51_uniblitz import Uniblitz

        

#%% Connect to and define device names
        
        # stage = Ell8("COM11") # rotation stage
        putter = ThorLabsSC10('COM11')  # Plasma shutter
        try:
            powermeter = ThorlabsPowermeter(visa.ResourceManager().list_resources()[0]) # Powermeter
        except:
            powermeter = dummyPowerMeter() # Dummy powermeter
            print('no powermeter plugged in, using a dummy to preserve the gui layout')
        
        # spec = OceanOpticsSpectrometer(0)  # OceanOptics spectrometer
        # bentham = Bentham_DTMc300()
        ivium = Ivium()
        varia = Varia(shutter = putter)
        
        wutter = Uniblitz('COM5') 
        lutter_633 = ThorLabsSC10('COM4')  # 633nm shutter
        lutter_785 = ThorLabsSC10('COM8')  # 785nm shutter
        power_bus = BusDistributor('COM14')
        filter_wheel_785 = Ell8(power_bus, 'B')
        filter_wheel_633 = Ell8(power_bus, 'C')
        filter_slider_785 = Ell6(power_bus, 'A')
        filter_slider_633 = Ell6(power_bus, 'D')  
        filter_slider_785.position = 1
        filter_slider_633.position = 1

    
    
#%% Get data file

        dgc = DataGroupCreator()
        data_file = datafile.current()


#%% Add equipment to Lab and GUI
        
        filter_wheel = filter_wheel_633
        filter_slider = filter_slider_633

        equipment_dict = {
            # 'stage': stage,
            # 'cam': cam,
            # 'cwl': cwl,
            # 'df_mirror': df_mirror,
            'filter_wheel': filter_wheel,   
            'filter_slider': filter_slider,
            'filter_wheel_785': filter_wheel_785,   
            'filter_slider_785': filter_slider_785,
            # 'andor': kandor,
            # 'kymera': kandor.kymera,
            'powermeter': powermeter,
            'lutter_633': lutter_633,
            'lutter_785': lutter_785,
            'wutter': wutter,  
            # 'spec': spec,
            # 'aligner': aligner,
            # 'polariser': pol,
            # 'bentham' : bentham,
            'ivium' : ivium,
            'varia' : varia,
            'putter' : putter,
            # 'magnet': magnet
            # 'rotation_stage': rotation_stage,
            }

        lab = EC_lab(equipment_dict)


        gui_equipment_dict = {
                              # 'lab': lab,
                              # 'cam': cam,
                              # 'CWL': cwl,
                              # 'df_mirror': df_mirror,
                              'filter_wheel_633': filter_wheel,
                              'filter_slider_633': filter_slider,
                              'filter_wheel_785': filter_wheel_785,
                              'filter_slider_785': filter_slider_785,
                              'powermeter': powermeter,
                              # 'andor': kandor,
                              # 'kymera': kandor.kymera,
                              'power_control_633': lab.pc,
                              '_633': lutter_633,
                              '_785': lutter_785,
                               'white_shutter': wutter,
                              'data_group_creator': dgc,
                              # 'darkfield': spec,
                              # 'polariser': pol,
                              # 'bentham' : bentham,
                              # 'ivium' : ivium,
                              'varia' : varia,
                              'putter' : putter,
                              # 'rotation_stage': rotation_stage,
                              # 'power_control_785': lab.pc_785,
                              # 'magnet': magnet
                              }
        
        __file__ = r"C:\Users\HERA\Documents\GitHub\nplab\nplab\Lab1_BX-60 Local Python Scripts\gui_config_photocurrent.npy"         
        lab.generated_gui = GuiGenerator(gui_equipment_dict, 
                                         terminal=False, 
                                         dark=False,
                                         dock_settings_path=os.path.dirname(
                                             __file__)+r'\gui_config_photocurrent.npy', scripts_path=os.path.dirname(__file__)+r'\scripts')
        
        initialized = True
        __file = __file__
        def restart_gui():
            '''
            restarts the gui. If you redefine a class by running 
            it in the console, it will use the updated version!
            '''
            if hasattr(lab, 'generated_gui'):
                lab.generated_gui.close()       
            lab.generated_gui = GuiGenerator(gui_equipment_dict, 
                                dock_settings_path = os.path.dirname(__file)+r'\gui_config_phoocurrent.npy',
                                scripts_path = os.path.dirname(__file)+r'\scripts') 


        print("Ayo let's get photocurrentinggggg")


#%% Power calibration over wavelength range


def power_calibration(start_wavelength = 400, end_wavelength = 850, step = 25, bandwidth = 15, group = None):
    
    if group is None:
        group = data_file.create_group('power_calibration_%d')
    
    wavelengths = np.arange(start_wavelength, end_wavelength + step, step)
    
    for wavelength in tqdm.tqdm(wavelengths, leave = True):
        
        varia.set_wavelength(wavelength, bandwidth)
        powermeter.wavelength = wavelength
        putter.open_shutter()
        power = powermeter.read_average(10)
        
        attrs = {'short_setpoint' : varia.short_setpoint,
                 'long_setpoint': varia.long_setpoint,
                 'bandwidth': varia.get_bandwidth(),
                 'wavelength': varia.get_wavelength(),
                 'powermeter_wavelength': powermeter.wavelength}
        
        group.create_dataset(name = str(wavelength) + 'nm' +'_%d',
                             data = power, 
                             attrs = attrs)
        
    putter.close_shutter()


#%% Threading

class ReturnableThread(Thread):
    # This class is a subclass of Thread that allows the thread to return a value.
    def __init__(self, target, args=(), kwargs=None):
        Thread.__init__(self)
        if kwargs is None:
            kwargs = {}
        self._args = args
        self._kwargs = kwargs
        self.target = target
        self.result = None
        self.kwargs = kwargs

    def run(self) -> None:
        self.result = self.target(*self._args, **self._kwargs)
        
    

        
#%% Putter toggle

def putter_wait_toggle(toggle_time = 1):
    
    time.sleep(toggle_time)
    putter.toggle()
    
    if ivium.get_device_status()[0] == 2:
        putter_wait_toggle(toggle_time = toggle_time)
        
    putter.close_shutter()

def lutter_785_wait_toggle(toggle_time = 1):
    
    time.sleep(toggle_time)
    lutter_785.toggle()
    
    if ivium.get_device_status()[0] == 2:
        lutter_785_wait_toggle(toggle_time = toggle_time)
        
    lutter_785.close_shutter()


def lutter_633_wait_toggle(toggle_time = 1):
    
    time.sleep(toggle_time)
    lutter_633.toggle()
    
    if ivium.get_device_status()[0] == 2:
        lutter_633_wait_toggle(toggle_time = toggle_time)
        
    lutter_633.close_shutter()
    

def putter_785_dual_toggle(toggle_time = 10, offset_785 = 5):
    
    time.sleep(toggle_time)
    putter.toggle()
    time.sleep(offset_785)
    lutter_785.toggle()
    
    if ivium.get_device_status()[0] == 2:
        putter_785_dual_toggle(toggle_time, offset_785)
        
    putter.close_shutter()
    lutter_785.close_shutter()
    
    
def shutter_toggle(shutter, on_time = 1, off_time = 1):
        
    shutter.close_shutter()
    time.sleep(off_time)
    shutter.open_shutter()
    time.sleep(on_time)
    shutter.close_shutter()
    
    if ivium.get_device_status()[0] == 2:
        shutter_toggle(shutter, on_time, off_time)
        
    putter.close_shutter()
    

#%% Example threads

thread_lsv = threading.Thread(target = ivium.run_lsv, kwargs = {'title': 'lsv_%d',
                                                                'e_start': -0.2,
                                                                'e_end': 0.2,
                                                                'e_step': 0.01,
                                                                'scanrate' : 0.05})

thread_ca = threading.Thread(target = ivium.run_ca, kwargs = {'title': 'CV_%d',
                                                              'levels_v' : [-0.4, -0.4],
                                                              'levels_t' : [180, 0],
                                                              'cycles' : 1,
                                                              'interval_time' : 0.1})

thread_ocp = threading.Thread(target = ivium.run_ocp_trace, kwargs = {'title': 'OCP_%d',
                                                              'length' : 180,
                                                              'interval' : 0.1})
                    

thread_putter = threading.Thread(target = putter_wait_toggle, kwargs = {'toggle_time' : 30})  

# ivium.run_cv(title = 'Co-TAPP-SMe_CV_dark_%d', e_start = 0.0, vertex_1 = 0.4, vertex_2 = -0.4, e_step = 0.002, scanrate = 0.025, n_scans = 2)
# ivium.run_lsv(title = 'Co-TAPP-SMe_LSV_light_%d', e_start = -0.4, e_end = 0.4, e_step = 0.002, scanrate = 0.025)

# thread_ca.start()
# thread_putter.start()



        

#%% Automated PEC toggle functions


# Automated PEC toggle w/ one-level CA through bandwidths, potentials, and wavelengths

def pec_ca_toggle(toggle_time = 50,
                  scan_time = 500,
                  delay_time = 0,
                  potentials = [-0.4, -0.2, 0, 0.2, 0.4],
                  bandwidths = [15],
                  wavelengths = np.arange(450, 850 + 25, 25),
                  dark_ca_start = True,
                  dark_ca_scan_time = 500,
                  name = 'PEC_CA'):

    for bandwidth in bandwidths:
        
        for potential in potentials:    
            
            levels_v = [potential, potential]
        
            ## Initial dark CA to help stabilize currents at new potential
            if dark_ca_start == True:
                title = name + '_dark_' + str(potential) + 'V_%d'                
                ivium.run_ca(title = title,
                             levels_v = levels_v,
                             levels_t = [dark_ca_scan_time, 0],
                             cycles = 1,
                             interval_time = 0.1)
        
            for wavelength in wavelengths:  
                varia.set_wavelength(wavelength = wavelength, bandwidth = bandwidth)
                title = name + '_' + str(int(wavelength)) + 'nm_' + str(bandwidth) + 'nmFWHM_toggle_' + str(toggle_time) + 's_delay_' + str(delay_time) + 's_CA_' + str(potential) + 'V_%d'                
                thread_ca = threading.Thread(target = ivium.run_ca, kwargs = {'title': title,
                                                                              'levels_v' : levels_v,
                                                                              'levels_t' : [scan_time + delay_time, 0],
                                                                              'cycles' : 1,
                                                                              'interval_time' : 0.1})
                        
                thread_putter = threading.Thread(target = putter_wait_toggle, kwargs = {'toggle_time' : toggle_time})  
                
                thread_ca.start()
                time.sleep(delay_time)
                thread_putter.start()
                thread_ca.join()
                thread_putter.join()
                putter.close_shutter()
                

# Automated PEC toggle at OCP through bandwidths, and wavelengths

def pec_ocp_toggle(toggle_time = 50,
                  scan_time = 500,
                  delay_time = 0,
                  bandwidths = [15],
                  wavelengths = np.arange(450, 850 + 25, 25),
                  name = 'PEC_OCP'):

    for bandwidth in bandwidths:
        
        for wavelength in wavelengths:  
            varia.set_wavelength(wavelength = wavelength, bandwidth = bandwidth)
            title = name + '_' + str(int(wavelength)) + 'nm_' + str(bandwidth) + 'nmFWHM_toggle_' + str(toggle_time) + 's_delay' + str(delay_time) + 's_OCP_%d'                
            thread_ocp = threading.Thread(target = ivium.run_ocp_trace, kwargs = {'title': title,
                                                                          'run_time' : scan_time + delay_time,
                                                                          'interval_time' : 0.1})
                    
            thread_putter = threading.Thread(target = putter_wait_toggle, kwargs = {'toggle_time' : toggle_time})  
            
            thread_ocp.start()
            time.sleep(delay_time)
            thread_putter.start()
            thread_ocp.join()
            thread_putter.join()
            putter.close_shutter()
            
            
# Automated PEC toggle with LSV through bandwidths, and wavelengths

def pec_lsv_toggle(toggle_time = 10,
                  e_start = -0.4,
                  e_end = 0.4,
                  e_step = 0.00027,
                  scanrate = 0.0027,
                  bandwidths = [15],
                  wavelengths = np.arange(450, 850 + 25, 25),
                  name = 'PEC_LSV'):

    for bandwidth in bandwidths:
        
        
        for wavelength in wavelengths:  
            varia.set_wavelength(wavelength = wavelength, bandwidth = bandwidth)
            title = name + '_' + str(int(wavelength)) + 'nm_' + str(bandwidth) + 'nmFWHM_toggle_' + str(toggle_time) + 's_LSV_%d'                
            thread_lsv = threading.Thread(target = ivium.run_lsv, kwargs = {'title': title,
                                                                            'e_start': e_start,
                                                                            'e_end': e_end,
                                                                            'e_step': e_step,
                                                                            'scanrate' : scanrate})
                    
            thread_putter = threading.Thread(target = putter_wait_toggle, kwargs = {'toggle_time' : toggle_time})  
            
            thread_lsv.start()
            thread_putter.start()
            thread_lsv.join()
            thread_putter.join()
            putter.close_shutter()


# Automated PEC VARIA+785 laser dual toggle at OCP through bandwidths, and wavelengths

def pec_ocp_785_dual_toggle(toggle_time = 50,
                  offset_785 = 50,
                  scan_time = 500,
                  delay_time = 0,
                  bandwidths = [15],
                  wavelengths = np.arange(450, 850 + 25, 25),
                  name = 'PEC_OCP_785_dual'):

    ''' Toggles NKT as regular, turns on 785 halfway after NKT goes on, turns off both at same time''' 
    
    for bandwidth in bandwidths:
        
        for wavelength in wavelengths:  
            varia.set_wavelength(wavelength = wavelength, bandwidth = bandwidth)
            title = name + '_' + str(int(wavelength)) + 'nm_' + str(bandwidth) + 'nmFWHM_toggle_' + str(toggle_time) + 's_delay' + str(delay_time) + 's_OCP_%d'                
            thread_ocp = threading.Thread(target = ivium.run_ocp_trace, kwargs = {'title': title,
                                                                          'run_time' : scan_time + delay_time,
                                                                          'interval_time' : 0.1})
                    
            thread_putter = threading.Thread(target = putter_wait_toggle, kwargs = {'toggle_time' : toggle_time})  
            
            thread_785_shutter = threading.Thread(target = shutter_toggle, kwargs = {'shutter' : lutter_785,
                                                                                     'on_time' : toggle_time * 0.5,
                                                                                     'off_time' : toggle_time * 1.5})
            
            thread_ocp.start()
            time.sleep(delay_time)
            thread_putter.start()
            thread_785_shutter.start()
            thread_ocp.join()
            thread_putter.join()
            thread_785_shutter.join()
            putter.close_shutter()
            lutter_785.close_shutter()
            
            
def pec_ocp_785_toggle(toggle_time = 50,
                  scan_time = 500,
                  delay_time = 0,
                  name = 'PEC_OCP_785nm_laser'):

    '''OCP + 785 laser toggle''' 
    
   
    title = name + '__toggle_' + str(toggle_time) + 's_delay' + str(delay_time) + 's_OCP_%d'                
    thread_ocp = threading.Thread(target = ivium.run_ocp_trace, kwargs = {'title': title,
                                                                  'run_time' : scan_time + delay_time,
                                                                  'interval_time' : 0.1})
             
    
    thread_785_shutter = threading.Thread(target = lutter_785_wait_toggle, kwargs = {'toggle_time' : toggle_time})
    
    thread_ocp.start()
    time.sleep(delay_time)
    thread_785_shutter.start()
    thread_ocp.join()
    thread_785_shutter.join()
    lutter_785.close_shutter()
    
    
def pec_ocp_633_toggle(toggle_time = 50,
                  scan_time = 500,
                  delay_time = 0,
                  name = 'PEC_OCP_633nm_laser'):

    '''OCP + 633nm laser toggle''' 
    
   
    title = name + '__toggle_' + str(toggle_time) + 's_delay' + str(delay_time) + 's_OCP_%d'                
    thread_ocp = threading.Thread(target = ivium.run_ocp_trace, kwargs = {'title': title,
                                                                  'run_time' : scan_time + delay_time,
                                                                  'interval_time' : 0.1})
             
    
    thread_633_shutter = threading.Thread(target = lutter_633_wait_toggle, kwargs = {'toggle_time' : toggle_time})
    
    thread_ocp.start()
    time.sleep(delay_time)
    thread_633_shutter.start()
    thread_ocp.join()
    thread_633_shutter.join()
    lutter_633.close_shutter()
        


#%%

group = data_file.create_group('CB5_57nm_MLAgg_%d')
ivium.data_file = group


#%%

# power_calibration(start_wavelength = 400, end_wavelength = 850, step = 25, bandwidth = 15, group = group.create_group('power_calibration_%d'))

reverse_wavelengths = np.arange(450, 850 + 25, 25)[::-1]
filter_slider_785.position = 0
filter_slider_633.position = 0


# pec_ocp_toggle(wavelengths = reverse_wavelengths, toggle_time = 100, scan_time = 1000, delay_time = 500)  
 

# pec_ca_toggle(wavelengths = reverse_wavelengths, toggle_time = 100, scan_time = 1000, delay_time = 100, 
              # potentials = [0.0, -0.1, -0.2, -0.3, -0.4, -0.5, -0.6, -0.7, -0.8, -0.9], dark_ca_start = True, dark_ca_scan_time = 500, name = 'PEC_CA')     

# pec_lsv_toggle(wavelengths = reverse_wavelengths)
# ivium.run_lsv(title = 'LSV_dark_%d', e_start = -0.4, e_end = 0.4, e_step = 0.002, scanrate = 0.025)
# ivium.run_lsv(title = 'LSV_dark_%d', e_start = -0.4, e_end = 0.4, e_step = 0.002, scanrate = 0.025)
# ivium.run_cv(title = 'CV_dark_25mVs_%d', e_start = 0.0, vertex_1 = 0.8, vertex_2 = -1, e_step = 0.002, scanrate = 0.025, n_scans = 2)
# ivium.run_cv(title = 'CV_dark_50mVs_%d', e_start = 0.0, vertex_1 = 0.8, vertex_2 = -1, e_step = 0.002, scanrate = 0.050, n_scans = 2)
# ivium.run_cv(title = 'CV_dark_100mVs_%d', e_start = 0.0, vertex_1 = 0.8, vertex_2 = -1, e_step = 0.002, scanrate = 0.100, n_scans = 2)
# ivium.run_cv(title = 'CV_dark_200mVs_%d', e_start = 0.0, vertex_1 = 0.8, vertex_2 = -1, e_step = 0.002, scanrate = 0.200, n_scans = 2)


# pec_ocp_785_toggle(toggle_time = 100, scan_time = 1000, delay_time = 500)
# pec_ocp_633_toggle(toggle_time = 100, scan_time = 1000, delay_time = 500)
# pec_ocp_785_dual_toggle(wavelengths = reverse_wavelengths, toggle_time = 100, scan_time = 1000, delay_time = 500)  



#%% Angle- dependent measurements

# data_file = data_file['Co-TAPP-Sme_60nm_Dense_NPoM_0']
# ivium.data_file = data_file
# angles = [0, 10, 20, 30, 40]

# ## OCP
# for angle in angles:
#     stage.move(angle)
#     time.sleep(3)
#     pec_ocp_toggle(name = 'PEC_OCP_' + str(angle) + 'deg')

# ## Dark CV
# ivium.run_cv(title = 'CV_dark_%d', e_start = 0.0, vertex_1 = 0.4, vertex_2 = -0.4, e_step = 0.002, scanrate = 0.025, n_scans = 2)
# ivium.run_cv(title = 'CV_dark_%d', e_start = 0.0, vertex_1 = 0.4, vertex_2 = -0.4, e_step = 0.002, scanrate = 0.025, n_scans = 2)

# ## CA at all potentials    
# for angle in angles:
#     stage.move(angle)
#     time.sleep(3)
#     pec_ca_toggle(name = 'PEC_CA_' + str(angle) + 'deg') 

    
#%% For movie!

# wavelengths = [475, 510, 570, 640]

# for wavelength in wavelengths:
#     set_wavelength(wavelength, bandwidth = 10)
#     putter.open_shutter()
#     time.sleep(1)
#     putter.close_shutter()
#     time.sleep(1)
#     putter.open_shutter()
#     time.sleep(1)
#     putter.close_shutter()
#     time.sleep(1)
#     putter.open_shutter()
#     time.sleep(1)
#     putter.close_shutter()
#     time.sleep(1)