# -*- coding: utf-8 -*-
"""
Created on Tue Nov 22 18:09:58 2022

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
        from nplab.instrument.shutter.BX51_uniblitz import Uniblitz
        import lamp_slider as df_shutter
        # from nplab.instrument.stage.Thorlabs_ELL18K import Thorlabs_ELL18K
        from nplab.instrument.stage.thorlabs_ello.ell18 import Ell18
        from nplab.instrument.potentiostat.ivium import Ivium
        from nplab.instrument.monochromator.bentham_DTMc300 import Bentham_DTMc300
        from nplab.instrument.stage.thorlabs_ello import BusDistributor

        # from nplab.instrument.electromagnet import arduino_electromagnet # Magnet
        # from nplab.instrument.camera.thorlabs.kiralux import Kiralux
       
#%% Connect to and define device names
        
        stage = ProScan("COM7") # Microscope stage
        cam = LumeneraCamera(1) # Infinity camera
        cwl = CameraWithLocation(cam, stage)
        cwl.settling_time = 0.2
        # lutter_633 = ThorLabsSC10('COM5')  # 633nm shutter
        lutter_785 = ThorLabsSC10('COM8')  # 785nm shutter
        df_mirror = Ell20BiPositional('COM10') # 2 position slider w/ mirror for darkfield
        df_mirror.SLOTS = (0.1,0.8) # movement range of df_mirror as %
        df_mirror.move_home()
        df_mirror.slot = 0 
        pol = Ell14('COM12') # Polarizer rotation mount
        try:
            powermeter = ThorlabsPowermeter(visa.ResourceManager().list_resources()[0]) # Powermeter
        except:
            powermeter = dummyPowerMeter() # Dummy powermeter
            print('no powermeter plugged in, using a dummy to preserve the gui layout')

        filter_wheel = Ell18('COM11') # ND filter wheel - Need to fix GUI
        kandor = Kandor() # Andor Kymera spectrometer + Newton camera
        kymera = kandor.kymera
        kandor.PreAmpGain = 2 # Set Gain to 4x
        wutter = Uniblitz('COM5') 
        # filter_slider = Ell6('COM14') # 2 position slider w/ ND filter
        # filter_slider.position = 0
        spec = OceanOpticsSpectrometer(0)  # OceanOptics spectrometer
        aligner = SpectrometerAligner(spec, stage)
        # bentham = Bentham_DTMc300()
        # ivium = Ivium()
        # magnet=arduino_electromagnet.Magnet('COM4')


#%% Get data file

        dgc = DataGroupCreator()
        data_file = datafile.current()


#%% Add equipment to Lab and GUI
        
        equipment_dict = {
            'stage': stage,
            'cam': cam,
            'cwl': cwl,
            'df_mirror': df_mirror,
            'filter_wheel': filter_wheel,
            # 'filter_slider': filter_slider,
            'andor': kandor,
            'kymera': kandor.kymera,
            'powermeter': powermeter,
            # 'lutter_633': lutter_633,
            'lutter_785': lutter_785,
            'wutter': wutter,  
            'spec': spec,
            'aligner': aligner,
            'polariser': pol,
            # 'bentham' : bentham,
            # 'ivium' : ivium
            # 'magnet': magnet
            # 'rotation_stage': rotation_stage,
            }

        lab = PT_lab(equipment_dict)


        gui_equipment_dict = {'lab': lab,
                              'cam': cam,
                              'CWL': cwl,
                              'df_mirror': df_mirror,
                                'filter_wheel': filter_wheel,
                              # 'filter_slider': filter_slider,
                              'powermeter': powermeter,
                              'andor': kandor,
                              'kymera': kandor.kymera,
                              'power_control_633': lab.pc,
                              # '_633': lutter_633,
                              '_785': lutter_785,
                              'white_shutter': wutter,
                              'data_group_creator': dgc,
                               'darkfield': spec,
                              'polariser': pol,
                              # 'bentham' : bentham,
                               # 'ivium' : ivium
                              # 'rotation_stage': rotation_stage,
                              # 'power_control_785': lab.pc_785,
                              # 'magnet': magnet
                              }
                
        lab.generated_gui = GuiGenerator(gui_equipment_dict, 
                                         terminal=False, 
                                         dark=False,
                                         dock_settings_path=os.path.dirname(
                                             __file__)+r'\gui_config.npy', scripts_path=os.path.dirname(__file__)+r'\scripts')
        
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
                                dock_settings_path = os.path.dirname(__file)+r'\gui_config.npy',
                                scripts_path = os.path.dirname(__file)+r'\scripts') 


        print("Ayo let's get trackingggggg")


#%% Ishaan's powerseries stuff

    def laser_autofocus(step_size= 0.02,steps = 20, exp = 1.0, gain = 1.0, filter_wheel_pos = 340, filter_slider_slot = 1):
        
        '''
        Autofocus with laser function adapted from Yonatan. Autofocuses using laser spot.
        Tends to be more reliable than camera white light autofocus
        
        Parameters:
            step_size (float = 0.02): z-stage step size
            steps (float = 20): number of z-stage steps
            exp (float = 1.0): camera exposure during autofocus
            gain (float = 1.0): camera gain during autofocus
            filter_wheel_pos (float = 340): filter_wheel position during autofocus (should be minimum power)
            filter_slider_slot (int = 1): filter_slider slot during autofocus (should be minimum power)
            
        Improvements:
            - Move to other file
            - Expand to both lasers
            - Error message and continue if fail?
        '''
        
        df_mirror.slot = 0
        
        ## Move to low power, open shutter        
        # filter_slider.position = filter_slider_slot
        # filter_wheel.move_absolute(filter_wheel_pos)
        lab.lutter_633.open_shutter()
        
        ## Get original camera & stage settings
        original_exposure = lab.cam.exposure
        original_gain = lab.cam.gain
        original_position=lab.cwl.stage.position
        
        ## Set camera to new settings
        lab.cam.exposure= exp
        lab.cam.gain = gain

        ## Move stage to minimum height
        lab.cwl.stage.move_rel([0,0,-0.5*step_size*steps])
        
        ## Autofocusing
        max_pixels = []
        poses = []    
        for i in range(steps):
            image = lab.cam.raw_image()
            grey_im = np.sum(image,axis=2)
            flat_im = np.reshape(grey_im,grey_im.shape[0]*grey_im.shape[1])
            max_pix = np.average(flat_im[flat_im.argsort()[-10:]])
            max_pixels.append(max_pix)
            poses.append(lab.cwl.stage.position[-1])
            lab.cwl.stage.move_rel([0,0,step_size])
        new_pos = np.array(poses)[np.array(max_pixels)==np.max(max_pixels)]
        
        ## Reset camera & stage to original, close shutter
        lab.cwl.stage.move([original_position[0],original_position[1],new_pos[0]])
        lab.cam.exposure = original_exposure
        lab.cam.gain = original_gain
        lab.lutter_633.close_shutter()
        
        df_mirror.slot = 1
    
    OD_to_power_cal_dict = {0 : 'power control_0', 1 : 'power control_2'}
    
    # lutter_633 = lutter_785
    lab.pc.min_param = 85
    lab.pc.max_param = 350
    
    def SERS_with_name(name, laser_wln = 785, laser_power = None, sample = '', time_scale = 0):
        print('SERS Start')
        if laser_power is None:
            if lab.pc.param > 350:
                lab.pc.param = 350
            lab.pc.update_power_calibration(OD_to_power_cal_dict[filter_slider.get_position()])
            laser_power = round(float(lab.pc.param_to_power(round(lab.pc.param,2))),4)
            
        data = kandor.raw_image()
        lab.get_group().create_dataset(name,data=data, attrs={
            'filter_wheel':filter_wheel.get_position(), 
            'laser_wavelength': laser_wln, 
            'laser_power':laser_power, 
            'filter_slider':filter_slider.get_position(),
            'grating' : kandor.kymera.GetGrating(),
            'centre_wavelength':kandor.kymera.GetWavelength(),
            'sample': sample,
            'power (mW)': laser_power,
            'cycle_time': kandor.AcquisitionTimings[1],
            'slit_width': kandor.kymera.GetSlit(),
            'gain':kandor.PreAmpGains[kandor.NumPreAmp-1],
            'readout (MHz)':kandor.HSSpeed,
            'time_scale (mW*s)': time_scale,
            'objective': '20x_0.4NA'})
        print('SERS Finish')
    
    def power_to_param2(power, kind = 'cubic'):
        
        params = lab.pc.power_calibration['parameters']
        powers = np.array(lab.pc.power_calibration['powers'])
        curve = interpolate.interp1d(powers, params, kind=kind)
        return curve(power)
    
    def powerseries(min_power, 
                    max_power, 
                    num_powers,
                    loop = False,
                    back_to_min = False, 
                    log = True, 
                    time_scale = 0,
                    iterations = 1,
                    wavelength = 785,
                    power_control_dict = {0 : 'power control_0', 1 : 'power control_1'}, 
                    SERS_name = 'SERS_Powerseries_%d', 
                    sample = '', 
                    test = False):
        
        '''
        Function to take SERS powerseries. Can use multiple power calibrations for
        multiple discrete ND filters. Checks powers are in range of power calibration.
        Can scale integration time to laser power
        
        Parameters:
            min_power: minimum laser power in mW
            max_power: maximum laser power in mW
            num_powers (int): number of powers to measure
            loop (boolean = False): if true, loops back down from max to min powers
            back_to_min (boolean = False): if true, jumps back to min power after each power in series, then jumps back to next power
            log (boolean = True): if true goes in log steps between min and max powers. If false goes linear
            time_scale (float = 0): scaling factor for integration time (in mW*s). If 0, integration time is constant
            iterations (int = 1): number of times to repeat full powerseries
            power_control_dict (dictionary = {0 : 'power control_0'}): Dictionary mapping {filter_slot position : power calibration name}
            SERS_name (str = SERS_powerseries_%d): Name to save SERS spectra
            sample (str = ''): Sample name
            test (bool = False): if True, just tests powers can be achieved with given power calibration and doesn't run measurements
            
        Improvements/limitations:
            - only works for 633 right now
            - how to better pass attributes to SERS_with_name()
            - Move to other file
        '''
        
        if wavelength == 785:
            lutter = lutter_785
        elif wavelength == 633:
            lutter = lutter_633
        
        wutter.close_shutter()
        
        # Get array of laser powers
        
        if log == True:
            powers = np.logspace(np.log10(min_power), np.log10(max_power), num_powers)
            
        else:
            powers = np.linspace(min_power, max_power, num_powers)            
            
        if loop == True:
            powers = np.append(powers, np.flip(powers[:len(powers)-1]))
            num_powers = len(powers)
            
        if back_to_min == True:
              where = np.where(powers > min_power)
              powers = np.insert(powers, where[0]+1, min_power)
              num_powers = len(powers)
              # for i, power in enumerate(powers):
              #     print(power)
              #     print(min_power)
              #     if power > min_power:
              #         np.insert(powers, i, min_power)
            
        print('Powers (mW):')
        print(powers)
        
        time_sum = 0
        for power in powers:
            time1 = time_scale/power
            time_sum += time1
        time_sum = time_sum * iterations
        print('Estimated time per particle (s): ')
        print(time_sum)
        
        # Get slider positions for each power
        
        ## Slider position array for each power (start with nans)
        slider_positions = np.empty(num_powers)
        slider_positions.fill(np.NaN)
        
        ## Find power calibration/slider position for each power
        for i in power_control_dict:
            lab.pc.update_power_calibration(power_control_dict[i])
            for j, power in enumerate(powers):
                if power < lab.pc.param_to_power(lab.pc.min_param) and power > lab.pc.param_to_power(lab.pc.max_param):
                    slider_positions[j] = i
        
        ## Return powers out of calibration range (where nans are still present)
        for i, position in enumerate(slider_positions):
            if np.isnan(position):
                print('Power out of calibration range: ' + str(powers[i]) + 'mW')
        
        ## Assert all powers in range (no nans) before continuing
        assert np.isnan(slider_positions).any() == False, 'Powers our of calibration range: ' + str(powers[np.where(np.isnan(slider_positions) == True)])
        print('Slider positions:')
        print(slider_positions)
        
        
        # Print filter_wheel positions for each power
        wheel_positions = np.empty(num_powers)
        for i, power in enumerate(powers):
            lab.pc.update_power_calibration(power_control_dict[slider_positions[i]])
            wheel_positions[i] = power_to_param2(power)
        print('Wheel positions: ')
        print(wheel_positions)
        
        # End here if just testing
        if test == True:
            return powers
        
        
        # Start at lowest power & open shutter
        
        filter_slider.position = int(slider_positions[powers.argmin()])
        lab.pc.update_power_calibration(OD_to_power_cal_dict[filter_slider.get_position()])
        filter_wheel.move_absolute(power_to_param2(min_power))
        time.sleep(1)
        lutter.open_shutter()
        
        
        # Loop over each iteration

        N_iterations = 0
        while N_iterations < iterations:

            ## Loop over each power and take measurement
            for i, power in enumerate(powers):
                
                ### Navigate to power
                filter_slider.position = int(slider_positions[i])
                lab.pc.update_power_calibration(OD_to_power_cal_dict[filter_slider.get_position()])
                filter_wheel.move_absolute(wheel_positions[i])
                time.sleep(1)
                
                ### Time scaling with power
                if time_scale > 0:
                    exposure = (time_scale/power) - (kandor.AcquisitionTimings[1] - kandor.AcquisitionTimings[0])
                    kandor.set_andor_parameter('Exposure', exposure)
                
                ### Take SERS
                SERS_with_name(name = SERS_name, laser_wln = wavelength, laser_power = power, sample = sample, time_scale = time_scale)
            
            N_iterations += 1
            
        lutter.close_shutter()
        wutter.open_shutter()    
        
        
    def pol_z_scan():
        angles = np.linspace(0, 90, 2)
        for angle in angles:
            pol.move_absolute(angle)
            lab.z_scan()
    
        
    def power_switch_recovery():
        
        num_particles = 10
        particle_number = int(lab.wizard.current_particle)
        index = int(np.floor(particle_number/num_particles))
        wait_time = 0
        
        powerseries(0.001, 0.1, 2, iterations = 5, back_to_min=True, time_scale = 0.04, wavelength = 633, test = True, SERS_name = 'SERS_Powerseries_%d', sample = '2023-11-28_Co-TAPP-SMe_MLAgg_on_Glass_c')
        
        
        
        
        
        
        
        
        
    def power_switch():
              
        # Start at lowest power & open shutter
        wutter.close_shutter()
        filter_slider.position = 1
        filter_wheel.move_absolute(252)
        lutter_633.open_shutter()
                
        for i in range(0, 10):
            
            # 1uW spectrum
            filter_slider.position = 1
            filter_wheel.move_absolute(252)
            time.sleep(1)
            kandor.set_andor_parameter('Exposure', 250)
            SERS_with_name(name = 'SERS_633nm_1uW_%d', laser_wln = 633, sample = '2023-07-31_Co-TAPP-SMe_60nm_MLAgg_on_Glass_b', time_scale = 0.25, laser_power = 0.001)
        
            #500uW spectrum
            filter_slider.position = 0
            filter_wheel.move_absolute(123)
            time.sleep(1)
            kandor.set_andor_parameter('Exposure', 0.38)
            SERS_with_name(name = 'SERS_633nm_700uW_%d', laser_wln = 633, sample = '2023-07-31_Co-TAPP-SMe_60nm_MLAgg_on_Glass_b', time_scale = 0.25, laser_power = 0.700)
      
            
        lutter_633.close_shutter()
        wutter.open_shutter()
        
        
    def wait(wait_time):
        time.sleep(wait_time)
        
#%%
    
    def scan_expt(min_power, max_power, num_powers, exposure = 1, scan_scale = 500, num_particles = 10):
    
        # Accurately set kandor exposure (taking into account cycle time)
        
        cycle_time = exposure
        kandor.set_andor_parameter('Exposure', cycle_time)
        exposure = cycle_time - (kandor.AcquisitionTimings[1] - kandor.AcquisitionTimings[0])
        kandor.set_andor_parameter('Exposure', exposure)
    
    
        # Get scan powers and scan lengths
        
        scan_powers = np.logspace(np.log10(min_power), np.log10(max_power), num_powers)
        scan_lengths = np.zeros(num_powers)
        
        ## Scan length is absolute value of laser power order of magnitude times scan_scale - longer for lower powers
        for i in range(0, len(scan_lengths)):
            scan_lengths[i] = np.floor(np.log10(scan_powers[i])) - 1
            scan_lengths[i] = abs(scan_lengths[i]) * scan_scale
        
            
        # Move on to next power and scan length after num_particles - have to start at particle '0'
        
        particle_number = int(lab.wizard.current_particle)
        index = int(np.floor(particle_number/num_particles))
        this_power = scan_powers[index]
        this_length = int(scan_lengths[index]/cycle_time)
        kandor.set_andor_parameter('NKin', this_length)
        
        power_name = 'SERS_5s_' + str(np.round(this_power * 1000, 1)) + 'uW_%d'
    
        powerseries(this_power, this_power, 1, SERS_name = power_name, sample = '2023-11-28_Co-TAPP-SMe_60nm_MLAgg_on_Glass_c')    

#%%  Threaded CV + SERS
from threading import Thread
# thread_cv = threading.Thread(target = ivium.run_cv, kwargs={'title': 'CV_test_%d'})
# thread_SERS = threading.Thread(target = SERS_with_name, kwargs={'name': 'SERS_%d', 'laser_power': 0})
# thread_cv.start()
# thread_SERS.start()

class ThreadWithReturnValue(Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None
    def run(self):
        if self._Thread__target is not None:
            self._return = self._Thread__target(*self._Thread__args,
                                                **self._Thread__kwargs)
    def join(self):
        Thread.join(self)
        return self._return

def time_scan2(takes = 10, settling_time = 0.2):
    time1 = time.time()
    timestart = time.ctime()
    spectra = []
    # dz = np.linspace(0,0,takes)
    #self.show_camera()
    #time.sleep(1)
    lab.spec.read_spectrum() #reads spectrum trice to clear cached junk before taking measurement
    # lab.spec.read_spectrum()
    for i in range (0, takes):
        #time.sleep(settling_time)
        spectra.append(lab.spec.read_spectrum())

    #time.sleep(0.5)#
    # data = ArrayWithAttrs(spectra, attrs=lab.spec.metadata)
    time2 = time.time()
    lab.get_group().create_dataset(name = 'df_timescan_%d', data = spectra, attrs = lab.spec.metadata)
    print('Scan time: ' + str(time2-time1))
    print('Scan start time: ' + str(timestart))
    
def ca2():
    time1 = time.time()
    timestart = time.ctime()
    data = ivium.run_ca(title = 'CA_%d',
            mode = 'Standard',
               levels_v  = [0.9,0.6, 0.3,0,-0.3,-0.6, -0.9],
               levels_t = [ 5, 5,5,5,5,5,5],
               cycles =10 ,
               interval_time  = 0.1,
               current_range  = '10uA',
               method_file_path  = r"C:\Users\HERA\Documents\GitHub\nplab\nplab\instrument\potentiostat\CA_Standard.imf",
               save  = False)
    time2 = time.time()
    lab.get_group().create_dataset(name = 'CA_%d', data = data, attrs = data.attrs)
    print('CA total time: ' + str(time2-time1))
    print('CA start time' + str(timestart))

# thread_scan = Thread(target = time_scan2, kwargs = {'takes' : 50, 'settling_time' : 1})
# thread_ca = Thread(target = ca2)
# thread_scan.start()
# thread_ca.start()

def scanning2():
    thread_scan = Thread(target = time_scan2, kwargs = {'takes' : 380, 'settling_time' : 1})
    thread_ca = Thread(target = ca2)
    thread_scan.start()
    thread_ca.start()
    #time.sleep(210)
    
def scanning2():
    img= cwl.thumb_image()
    self.wizard.particle_group.create_dataset(name ='Thumb_image_%d',data = img)
    thread_scan = Thread(target = time_scan2, kwargs = {'takes' : 50, 'settling_time' : 1})
    thread_ca = Thread(target = ca2)
    thread_scan.start()
    thread_ca.start()
    #time.sleep(210)
    
#%%

def map_df(step_size = 7.5, rows = 200):
    
    df_mirror.slot = 1
    wutter.open_shutter()
    
    group = lab.create_data_group('MLAgg_map_%d')
    
    for i in range(0, rows):
        print('\n' + str(time.ctime()))
        print('\nStarting column  ' + str(i))
        stage.move_rel([step_size, 0, 0])
        
        for j in range(0, rows):
            
            if j % 99 == 0:
                lab.cwl.autofocus()
                time.sleep(2)
            
            stage.move_rel([0, step_size, 0])
    
            try:
                img = cwl.thumb_image()    
                group.create_dataset(data = img, name = 'thumb_image_' + str(i) + '_' + str(j) + '_%d')
                
                time.sleep(0.2)
    
            except:
                pass
            
            spectrum = lab.spec.read_spectrum() 
            data = ArrayWithAttrs(spectrum, attrs = lab.spec.metadata)
            group.create_dataset(data = data, name = 'spec_' + str(i) + '_' + str(j) + '_%d', attrs = {'step_size' : step_size, 'rows' : rows, 'row' : j, 'column' : i})
            
        stage.move_rel([0, -rows * step_size, 0])
    
# map_df()

   