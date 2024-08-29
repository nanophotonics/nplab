# -*- coding: utf-8 -*-
"""
Created on Thu May 23 11:31:20 2024

@author: HERA
"""

#%% Init & imports

import os
import threading
import time
import tqdm
import numpy as np
import pyvisa as visa
import nkt_tools
from nkt_tools.varia import Varia
from nkt_tools.extreme import Extreme


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
        # from nplab.instrument.stage.thorlabs_ello.ell8 import Ell8
        # from nplab.instrument.stage.thorlabs_ello.ell14 import Ell14
        from nplab.utils.array_with_attrs import ArrayWithAttrs
        # from nplab.instrument.stage.Thorlabs_ELL18K import Thorlabs_ELL18K
        # from nplab.instrument.stage.thorlabs_ello.ell18 import Ell18
        from nplab.instrument.potentiostat.ivium import Ivium
        # from nplab.instrument.monochromator.bentham_DTMc300 import Bentham_DTMc300
        
    
        putter = ThorLabsSC10('COM8')  # Plasma shutter
        try:
            powermeter = ThorlabsPowermeter(visa.ResourceManager().list_resources()[0]) # Powermeter
        except:
            powermeter = dummyPowerMeter() # Dummy powermeter
            print('no powermeter plugged in, using a dummy to preserve the gui layout')
        # # filter_wheel = Ell18('COM11') # ND filter wheel - Need to fix GUI
        # spec = OceanOpticsSpectrometer(0)  # OceanOptics spectrometer
        # bentham = Bentham_DTMc300()
        ivium = Ivium()
        varia = Varia()
    
    
        dgc = DataGroupCreator()
        data_file = datafile.current()
        
        equipment_dict = {
            'powermeter': powermeter,
            'putter': putter,
            # 'spec': spec
            }
        
        gui_equipment_dict = {
            'powermeter': powermeter,
            'dgc': dgc,
            'putter' : putter,
            # 'spec': spec
            }
        
        gui = GuiGenerator(gui_equipment_dict)
    
#%% Functions for Varia

def get_bandwidth(varia = varia):
    
    bandwidth = varia.long_setpoint - varia.short_setpoint
    return bandwidth
    
def centre_setpoint(varia = varia):

    centre = (varia.long_setpoint + varia.short_setpoint)/2   
    return centre

def set_wavelength(wavelength, bandwidth = 10, varia = varia):
    
    putter.close_shutter()
    
    varia.short_setpoint = wavelength - (bandwidth/2)
    varia.long_setpoint = wavelength + (bandwidth/2)
    
    time.sleep(5)
    
    
#%%

   
    # #%% Add equipment to Lab and GUI
        
    #     equipment_dict = {
    #         # 'powermeter': powermeter,   
    #         'putter': putter,  
    #         # 'spec': spec,
    #         # 'bentham' : bentham,
    #         # 'ivium' : ivium
    #         }
    
    # #         lab = PT_lab(equipment_dict)
    
    #     gui_equipment_dict = {#'powermeter': powermeter,
    #                             'plasma_shutter': putter,
    #                            'data_group_creator': dgc,
    #                           # 'darkfield': spec,
    #                           # 'bentham' : bentham,
    #                             # 'ivium' : ivium
    #                           # 'rotation_stage': rotation_stage,
    #                           # 'power_control_785': lab.pc_785,
    #                           }
        
    #     GuiGenerator(gui_equipment_dict)#, terminal = False, dark = False)
            
    #     # generated_gui = GuiGenerator(gui_equipment_dict, 
    #     #                                   terminal=False, 
    #     #                                   dark=False,
    #     #                                   dock_settings_path=os.path.dirname(
    #     #                                       __file__)+r'\gui_config.npy', scripts_path=os.path.dirname(__file__)+r'\scripts')
    
    #     # initialized = True
    #     # __file = __file__
    #     # def restart_gui():
    #     #     '''
    #     #     restarts the gui. If you redefine a class by running 
    #     #     it in the console, it will use the updated version!
    #     #     '''
    #     #     if hasattr(lab, 'generated_gui'):
    #     #         lab.generated_gui.close()       
    #     #     lab.generated_gui = GuiGenerator(gui_equipment_dict, 
    #     #                         dock_settings_path = os.path.dirname(__file)+r'\gui_config.npy',
    #     #                         scripts_path = os.path.dirname(__file)+r'\scripts') 


    #     print("Ayo let's get photocurrenting")
        
        
#%%

def putter_wait_toggle(wait_time = 1):
    
    time.sleep(wait_time)
    putter.toggle()
    
    if ivium.get_device_status()[0] == 2:
        putter_wait_toggle(wait_time = wait_time)
        
    putter.close_shutter()
    
def putter_wait_toggle_echem(wait_time = 1):
    print('Start')
    print(ivium.get_device_status()[0])
    while ivium.get_device_status()[0] == 2:
        print('Running')
        putter_wait_toggle(wait_time)
    print('End')
    print(ivium.get_device_status()[0])

#%%

# lsv_data = ivium.run_lsv() # Here specify the method/parameters you want to use from python (if you change parameters in Ivium soft, data will not be saved correctly)


thread_lsv = threading.Thread(target = ivium.run_lsv, kwargs = {'title': 'Co-TAPP-SMe_LSV_dark_%d',
                                                                'scanrate' : 0.05})

thread_ca = threading.Thread(target = ivium.run_ca, kwargs = {'title': 'Co-TAPP-SMe_500nm_toggle_30s_CA_-0.4V_%d',
                                                              'levels_v' : [-0.4, -0.4],
                                                              'levels_t' : [180, 0],
                                                              'cycles' : 1,
                                                              'interval_time' : 0.1})


thread_putter = threading.Thread(target = putter_wait_toggle, kwargs = {'wait_time' : 30})  

# ivium.run_cv(title = 'Co-TAPP-SMe_CV_dark_%d', e_start = 0.0, vertex_1 = 0.4, vertex_2 = -0.4, e_step = 0.002, scanrate = 0.025, n_scans = 2)
# ivium.run_lsv(title = 'Co-TAPP-SMe_LSV_light_%d', e_start = -0.4, e_end = 0.4, e_step = 0.002, scanrate = 0.025)

# thread_ca.start()
# thread_putter.start()


#%% Power calibration over wavelength range


def power_calibration(start_wavelength = 400, end_wavelength = 850, step = 50, bandwidth = 50, group = None):
    
    if group is None:
        group = data_file.create_group('power_calibration_%d')
    
    wavelengths = np.arange(start_wavelength, end_wavelength + step, step)
    
    for wavelength in tqdm.tqdm(wavelengths, leave = True):
        
        set_wavelength(wavelength, bandwidth)
        powermeter.wavelength = wavelength
        putter.open_shutter()
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
        
    putter.close_shutter()
        

#%% Automated CA toggle sweep through wavelengths and potentials

bandwidths = [50]
potentials = [-0.4, -0.2, 0.0, 0.2, 0.4]
wavelengths = np.arange(450, 850 + 50, 50)

for bandwidth in bandwidths:
    
    for potential in potentials:
        
        levels_v = [potential, potential]
    
        
    
        for wavelength in wavelengths:
            
            set_wavelength(wavelength = wavelength, bandwidth = bandwidth)
            
            title = 'BPDT_60nm_MLAgg_' + str(int(wavelength)) + 'nm_' + str(bandwidth) + 'nmFWHM_toggle_50s_CA_' + str(potential) + 'V_%d' 
            
            thread_ca = threading.Thread(target = ivium.run_ca, kwargs = {'title': title,
                                                                          'levels_v' : levels_v,
                                                                          'levels_t' : [500, 0],
                                                                          'cycles' : 1,
                                                                          'interval_time' : 0.1})
        
        
            thread_putter = threading.Thread(target = putter_wait_toggle, kwargs = {'wait_time' : 50})  
            
            thread_ca.start()
            thread_putter.start()
            thread_ca.join()
            thread_putter.join()
            putter.close_shutter()
