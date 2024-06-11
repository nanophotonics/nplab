# -*- coding: utf-8 -*-
"""
Created on Tue Nov 22 18:19:11 2022

@author: HERA
"""

import time
from particle_tracking_app.particle_tracking_wizard import TrackingWizard, InfiniteTrackingWizard, ParticleException
from setup_gui import laser_measurement, white_light_measurement
from nplab.utils.array_with_attrs import ArrayWithAttrs
import numpy as np
from scipy.optimize import curve_fit


class ParticleTrackMixin:
    def _init_tracking(self, task_list=None):
        
        track_dict = {'spectrometer' : self.spec,
                     'alinger' : self.aligner
                      }
        task_list += ['lab.cwl.thumb_image']
        self.wizard = TrackingWizard(self.cwl, track_dict, task_list=task_list)
        self.wizard.show()
        print('showed')
   
    def get_group(self):
        if self.wizard.scanner_status == 'Scanning!':
            return self.wizard.particle_group
        return self.get_root_data_folder()
    
    @laser_measurement
    def SERS(self):
        return self.andor.raw_image(update_latest_frame=True, bundle_metadata=True)
    
    # @laser_measurement
    # def SERS(self):
    #     attrs = self.andor.metadata
    #     SERS_data =self.andor.raw_image(update_latest_frame = True)
    #     SERS_data=np.reshape(SERS_data,(-1,1600))
    #     return self.wizard.particle_group.create_dataset('SERS', data = SERS_data, attrs=attrs)
    
    
    # @white_light_measurement
    # def z_scan(self, neg=-3., pos=3., stepsize=1.):
    #     return self.aligner.z_scan(dz=np.arange(neg, pos, stepsize))      
    
    @staticmethod
    def wait(seconds):
        time.sleep(seconds)
        
    def thumb_focus(self):
        self.cwl.autofocus(use_thumbnail=True)
    
    def set_temperature(self, T=-20.):
        '''important to stop set the OceanOptics spectrometer temperature
        periodically or it just keeps getting colder for some reaon'''
        self.spec.tec_temperature = T    
    
    def move_up(self, Z=1):
        self.cwl.stage.move_rel([0, 0, float(Z)])
    
    def set_laser(self, _633=False, _785=False):
        self.laser = '_633' if _633 else '_785'
    
    def fwl_and_move_up(self, exp=5, gain=1, OD_pos=11, 
                        z=2):
        '''focus with laser, then move up! 
        use if there's a difference in focus
        between dark-field and laser'''
        self.focus_with_laser(exp, gain, OD_pos)
        self.move_up(z)
        
    ################# Tracking functions ###########################        
    def show_laser(self):
        # self.lab.wutter.close_shutter()
        self.cam.exposure = 0.1
        self.cam.gain = 1
        self.rotation_stage.move_absolute(126)
        # power_control.power = laser_power
        self.lutter.open_shutter() #need to be fixed when 785 comes
        self.df_mirror.move_absolute(47.9980)
        
    def show_camera(self):
        #self.wutter.open_shutter()
        # self.cam.exposure = 250
        # self.cam.gain = 10
        #self.lutter.close_shutter() #need to be fixed when 785 comes
        print('Hello')
    # def z_scan_test(neg=-.7, pos=.7, stepsize=0.035, settling_time = 0.1):
    #    spectra = []
    #    dz = np.arange(neg,pos,stepsize)
    #    lab.show_camera()
    #    time.sleep(0.5)
    #    here = lab.stage.position
    #    lab.df_mirror.open_df()
    #    time.sleep(0.5)

    #    lab.spec.read_spectrum() #reads spectrum trice to clear cached junk before taking measurement
    #    lab.spec.read_spectrum()
    #    for z in dz:
    #        lab.stage.move(np.array([0,0,z])+here)
    #        time.sleep(settling_time)
    #        spectra.append(lab.spec.read_spectrum())

    #    time.sleep(0.5)#
    #    lab.stage.move(here)
    #    lab.df_mirror.close_df()
    #    attrs = lab.spec.metadata
    #    print(spectra)
    #    lab.wizard.particle_group.create_dataset(name ='DF_zscan_%d',data = spectra,attrs = attrs)
    #    print('z scan finished')
  
    def z_scan(self, neg=-.7, pos=.7, stepsize=0.035, settling_time = 0.1):
        spectra = []
        dz = np.arange(neg,pos,stepsize)
        self.show_camera()
        time.sleep(0.5)
        here = self.stage.position
        # self.df_mirror.set_slot(1)
        time.sleep(0.5)

        self.spec.read_spectrum() #reads spectrum trice to clear cached junk before taking measurement
        self.spec.read_spectrum()
        for z in dz:
            self.stage.move(np.array([0,0,z])+here)
            time.sleep(settling_time)
            spectra.append(self.spec.read_spectrum())

        time.sleep(0.5)#
        self.stage.move(here)
        # self.df_mirror.set_slot(0)
        return ArrayWithAttrs(spectra, attrs=self.spec.metadata)

    def time_scan(self, takes=240, settling_time = 1):
        spectra = []
        dz = np.linspace(0,0,takes)
        #self.show_camera()
        time.sleep(1)
        self.spec.read_spectrum() #reads spectrum trice to clear cached junk before taking measurement
        self.spec.read_spectrum()
        for z in dz:
            time.sleep(settling_time)
            spectra.append(self.spec.read_spectrum())

        time.sleep(0.5)#
        return ArrayWithAttrs(spectra, attrs=self.spec.metadata)

  
    def sleep(self,sleep_time=1.0):
        time.sleep(sleep_time)
        
    
    # self.wizard.particle_group.create_dataset(name ='DF_zscan_%d',data = spectra,attrs = attrs)
    def z_scan2(self, neg=-.7, pos=.7, stepsize=0.035, settling_time = 0.1):
        #self.df_mirror.SLOTS = (0, 47.9980)
        self.df_mirror.move_absolute(48)
        time.sleep(1)
        spectra = []
        dz = np.arange(neg,pos,stepsize)
        self.show_camera()
        #time.sleep(0.5)
        here = self.stage.position
        #self.df_mirror.set_slot(1)
        #time.sleep(0.5)
        #self.heights = dz
        #self.spec.read_spectrum() #reads spectrum trice to clear cached junk before taking measurement
        #self.spec.read_spectrum()
        for i, z in enumerate(dz):
            if i == 0:
                time.sleep(2)
            self.stage.move(np.array([0,0,z])+here)
            time.sleep(settling_time)
            spectra.append(self.spec.read_spectrum())
        #time.sleep(0.5)#
        self.stage.move(here)
        self.df_mirror.move_absolute(0)
        time.sleep(1)
        self.latest_z_scan = spectra
        #self.df_mirror.set_slot(0)
        return ArrayWithAttrs(spectra, attrs=self.spec.metadata)
    
    def z_scan_pol(self, neg=-.7, pos=.7, stepsize=0.035, settling_time = 0.1, pol_start=0, pol_stop=180, pol_steps=10):
        #self.df_mirror.SLOTS = (0, 47.9980)
        self.df_mirror.move_absolute(48)
        time.sleep(1)
        spectra = []
        dz = np.arange(neg,pos,stepsize)
        polstepsize = (pol_stop-pol_start)/pol_steps
        dp = np.arange(pol_start,pol_stop,polstepsize)
        self.show_camera()
        #time.sleep(0.5)
        here = self.stage.position
        #self.df_mirror.set_slot(1)
        #time.sleep(0.5)
        #self.heights = dz
        #self.spec.read_spectrum() #reads spectrum trice to clear cached junk before taking measurement
        #self.spec.read_spectrum()
        for i, p in enumerate(dp):
            if i == 0:
                time.sleep(2)
            pol.Rotate_To(np.array(p))
            time.sleep(settling_time)
            spectra.append(self.spec.read_spectrum())       
        #for i, z in enumerate(dz):
        #    if i == 0:
        #        time.sleep(2)
        #    self.stage.move(np.array([0,0,z])+here)
        #    time.sleep(settling_time)
        #    spectra.append(self.spec.read_spectrum())
        #time.sleep(0.5)#
        self.stage.move(here)
        self.df_mirror.move_absolute(0)
        time.sleep(1)
        self.latest_z_scan = spectra
        #self.df_mirror.set_slot(0)
        return ArrayWithAttrs(spectra, attrs=self.spec.metadata) 
    

    def Gauss(self, x, A, B):
            y = A*np.exp(-1*B*x**2)
            return y

    def correct_after_z_scan(self, neg=-.7, pos=.7, stepsize=0.035, ideal_focus_offset=0.0):
        print("0.1")
        spectra = self.latest_z_scan
        results=[]
        print("0.2")
        dz = np.arange(neg,pos,stepsize)
        #array_size = len(spectra)
        print("0.5")
        reference = self.spec.metadata['reference']
        background = self.spec.metadata['background']
        spectra2 = spectra.copy()
        print("1")
        temp = np.zeros(1024)
        for i in range(len(spectra)):
            temp = (spectra[i]-background)/(reference-background)
            spectra2[i] = temp
        print("2")

        try:
            for i in range(300,800):
                data = np.array(spectra2)
                ydata = data[:,i]
                parameters, covariance = curve_fit(self.Gauss, dz[5:32],ydata[5:32])
                #print("3")
                results.append(parameters[0])
            print("4")
            self.focal_height_offset = sum(results)/len(results)
            target = self.focal_height_offset+ideal_focus_offset
            print(target)
            if abs(target)<0.3:
                self.stage.move_rel([0,0,target])
                print("moving by:", target)
            else:
                 print("move would be too large, ignored")
        except:
            print("fitting failed, no change in height applied")
        #attrs = self.focal_height_offset

        print("5")
      #  if abs(target-8)>1:
           # if (target-8)*0.035<0.7:
                #self.stage.move_rel([0,0,(target-8)*0.035])
                #print("would have moved stage by", (target-8)*0.035)
         #   else:
        #        print("focus is fine")
        return results
    
    
    def record_SERS2(self, nspectra=500, t_integration=0.5): #for 633
        self.lutter_633.open_shutter()
        self.wutter.close_shutter()
        time.sleep(1)
        self.andor.Exposure=t_integration
        self.andor.NKin=nspectra
        #kandor.set_andor_parameter(integration, inputs)
        attrs = self.andor.metadata
        SERS_Scan=self.andor.raw_image(update_latest_frame = True)
        #SERS_Scan=np.reshape(SERS_Scan,(-1,1000))
        self.wizard.particle_group.create_dataset('kinetic_SERS', data = SERS_Scan, attrs=attrs)
        self.lutter_633.close_shutter()
        self.wutter.open_shutter()
        time.sleep(1)
        
    def record_SERS(self):
        self.lutter_633.open_shutter()
        self.wutter.close_shutter()
        time.sleep(1)
        attrs = self.andor.metadata
        SERS_Scan=self.andor.raw_image(update_latest_frame = True)
        #SERS_Scan=np.reshape(SERS_Scan,(-1,1000))
        self.wizard.particle_group.create_dataset('kinetic_SERS', data = SERS_Scan, attrs=attrs)
        self.lutter_633.close_shutter()
        self.wutter.open_shutter()
        time.sleep(1)
    
    def take_SERS(self):
        attrs = self.andor.metadata
        Kinetic_Scan=self.andor.raw_image(update_latest_frame = True)
        #Kinetic_Scan=np.reshape(Kinetic_Scan,(-1,1000))
        self.wizard.particle_group.create_dataset('kinetic_SERS', data = Kinetic_Scan, attrs=attrs)
        
    def tracking(self,laser_power=0.03,dz = np.arange(-0.7,0.7,0.035),name='Particle_%d',settling_time=0.2):
        self.show_camera()
        time.sleep(1)
        img=self.cwl.thumb_image()
        # cwl.autofocus()
        # cwl.move_to_feature(img, ignore_z_pos = True)
        # img=cwl.thumb_image()
        self.wizard.particle_group.create_dataset(name ='Thumb_image_%d',data = img)
        self.df_mirror.move_absolute(47.9980)
        time.sleep(0.4)

        spectra = []
        here = self.stage.position
        time.sleep(2)

        self.spec.read_spectrum() #reads spectrum trice to clear cached junk before taking measurement
        self.spec.read_spectrum()
        for z in dz:
            self.stage.move(np.array([0,0,z])+here)
            time.sleep(settling_time)
            spectra.append(self.spec.read_spectrum())

        time.sleep(0.5)#
        self.stage.move(here)
        time.sleep(0.5)
        # cwl.autofocus()
        here = self.stage.position
        self.stage.move_rel([0,0,-0.05])
        attrs = self.spec.metadata
        self.wizard.particle_group.create_dataset(name ='DF_zscan_%d',data = spectra,attrs = attrs)

        self.df_mirror.move_absolute(47.9980)
        time.sleep(1.5)
        self.show_laser()
        # self.rotation_stage.move_absolute(126)
        self.wutter.close_shutter()
        time.sleep(1)
        self.take_SERS()
        self.show_camera()
        time.sleep(1)
        self.stage.move(here)
        time.sleep(0.4)
        img2=self.cwl.thumb_image()
        self.wizard.particle_group.create_dataset(name ='Thumb_image_end_%d',data=img2)
        time.sleep(2)
        
    def run_tracking(self):
        self.tracking()
        
    @laser_measurement
    def simple_power_series(self,
                            minpower=None,
                            maxpower=None,
                            number_powers=5,
                            loop_back=False):
        print('Beginning power series')
        group = self.get_group()
        if self.laser=='_633':
            self.pc=self.pc_633
        if self.laser=='_785':
            self.pc=self.pc_785
        # self.shamdor.AcquisitionMode = 3 # time series
        minpower = min(self.pc.power_calibration['powers']) if minpower is None else float(minpower)
        maxpower = max(self.pc.power_calibration['powers']) if maxpower is None else float(maxpower)
        powers = np.linspace(minpower, maxpower, number_powers)
        if loop_back:
            powers = np.append(powers,np.flipud(powers[:-1]))
  
        measured_powers = []
        for i, power in enumerate(powers):
           self.pc.power = power
           
           group.create_dataset(f'power_series_{i}',
                                data=self.andor.raw_image(bundle_metadata=True,
                                                            update_latest_frame=True))
           measured_powers.append(self.powermeter.power)

        group.create_dataset('powers', data=powers)
        group.create_dataset('measured_powers', data=measured_powers)
        print('Power series complete')
        
   # def set_magnet(status='Zero'):
   #     if status=='Zero':
   #         magnet.Zero()
   #     elif status=='North':
   #         magnet.North()
   #     elif status=='South':
   #         magnet.South()            
###########################################################################
### condition skipping the particle measurement based on max power
    def power_threshold(ndarray,thresh=2000):
        if np.max(ndarrray) < thresh:
            raise ParticleException()

    def SERS_and_analysis(self,power_thresh=2000):
        sers = self.SERS()
        self.wizard.particle_group.create_dataset('test_sers', data = sers, attrs=attrs)
        self.power_threshold(sers,power_thresh)
       
    #############################################################################

        
class InfiniteParticleTrackMixin(ParticleTrackMixin):
    def _init_tracking(self, task_list=None):
        track_dict = {'spectrometer' : self.spec,
                     'alinger' : self.aligner,
                     # 'white_shutter': self.wutter
                      }
        task_list += ['lab.z_scan', 'lab.SERS', 'lab.tracking','lab.sleep','lab.focus_with_laser','lab.simple_power_series','lab.SERS_and_analysis']
        self.wizard = InfiniteTrackingWizard(self.cwl, track_dict, task_list=task_list)
        self.wizard.show()
