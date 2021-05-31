# -*- coding: utf-8 -*-
"""
Created on Fri May 28 15:50:10 2021

@author: Eoin
"""

import sys, os, time
from functools import wraps
from pathlib import Path

from nplab.instrument.camera import Camera, CameraControlWidget
from nplab.utils.notified_property import NotifiedProperty
from nplab.utils.thread_utils import locked_action
from nplab.ui.ui_tools import QuickControlBox

from thorlabs_tsi_sdk.tl_camera import TLCameraSDK
from thorlabs_tsi_sdk.tl_camera_enums import SENSOR_TYPE
from thorlabs_tsi_sdk.tl_mono_to_color_processor import MonoToColorProcessorSDK



dll_path = Path(__file__).parent / 'dlls'
is_64bits = sys.maxsize > 2**32

if is_64bits:
    dll_path /= '64_lib'
else:
    dll_path /= '32_lib'
#this line actually works
os.environ['PATH'] = str(dll_path.absolute()) + os.pathsep + os.environ['PATH']

# this one should, but doesn't
os.add_dll_directory(dll_path.absolute())


def disarmer(f, wait=0.1):
    '''some properties like roi and binning and  frames_per_capture.. need the camera to be "disarmed" to
    be set. This decorator disarms and re-arms the camera before and after the
    funciton is called. Particularly for binning, it seems like the camera 
    needs a few secs before it can be changed, hence the time.sleep.
    '''
    @wraps(f)
    def inner_func(self, *args, **kwargs):
        armed = self._camera.is_armed
        if armed:
            self._camera.disarm()
            time.sleep(wait)
        out = f(self, *args, **kwargs)
        self._image_width = self._camera.image_width_pixels
        self._image_height = self._camera.image_height_pixels # a compromise
        # between querying for every capture and wrapping binx and biny setter
        # methods individually. 
        if armed:
            self._camera.arm(2) # 2 frames to buffer
        if self.live_view:
            self._camera.issue_software_trigger()
        return out
    return inner_func
             
class Kiralux(Camera):
    disarmed_properties = ('roi', 'binx', 'biny', 'frames_per_trigger_zero_for_unlimited')
    # properties that need the camera to be disarmed to set - there may be more.
    notified_properties = ('gain',) # properties that are in the gui
    def __init__(self):
        super().__init__()
        self._sdk = TLCameraSDK()
        self._camera = self._sdk.open_camera(self._sdk.discover_available_cameras()[0])
        
        if self._camera.camera_sensor_type != SENSOR_TYPE.BAYER:
            # Sensor type is not compatible with the color processing library
            self._is_color = False
            self.process_frame = lambda f: f # no processing for grey images
        else:
            self._mono_to_color_sdk = MonoToColorProcessorSDK()
            self._image_width = self._camera.image_width_pixels
            self._image_height = self._camera.image_height_pixels
            self._mono_to_color_processor = self._mono_to_color_sdk.create_mono_to_color_processor(
                SENSOR_TYPE.BAYER,
                self._camera.color_filter_array_phase,
                self._camera.get_color_correction_matrix(),
                self._camera.get_default_white_balance_matrix(),
                self._camera.bit_depth
            )
            self._is_color = True
            self.process_frame = self.process_color_frame

        self._bit_depth = self._camera.bit_depth
        self._camera.image_poll_timeout_ms = 0  
        self._populate_properties()
        
        self._camera.frames_per_trigger_zero_for_unlimited = 1 # snapshot mode
        self._camera.arm(2)
        
    
    def _populate_properties(self):
        ''' adds all the properties from TLCamera to Kiralux, for easy access.
        
        '''
        
        def prop_factory(thor_prop, disarmed=False, notified=False): # to get around late binding
            def fget(self):
                return thor_prop.fget(self._camera)
            def fset(self, val):
                return locked_action(thor_prop.fset(self._camera, val))
            if disarmed: fset = disarmer(fset)
            if notified: return NotifiedProperty(*map(locked_action, (fget, fset)))
            return property(*map(locked_action, (fget, fset)))
        
        cls = self.__class__    
        for thor_attr in dir(thor_cls := self._camera.__class__):
            if hasattr(thor_prop := getattr(thor_cls, thor_attr), 'fget'): 
                # if it's a property
                if not hasattr(cls, thor_attr):
                    # and it's not in Kiralux already
                    setattr(cls,
                            thor_attr, # add the property
                            prop_factory(thor_prop,
                                         thor_attr in cls.disarmed_properties,
                                         thor_attr in cls.notified_properties))
                                         # if it's in disarmed_properties, 
                                         # decorate the setter and return a 
                                         # notified property appropriately.

    @NotifiedProperty
    def exposure(self): # in ms by nplab convention
        return self.exposure_time_us/1000.0
    
    @exposure.setter
    def exposure(self, val):
        self.exposure_time_us = int(val*1000)
     
    def get_frame(self, timeout=None):
        '''try to get a frame until it timeouts - shouldn't fail if stuff is
        working right'''
        if timeout is None:
            timeout = (self.exposure/100) # 10*exposure time
        start = time.time()
        while not ((f := self._camera.get_pending_frame_or_null())
                    or (time.time()-start) > timeout):
            pass
        return f
    
    def process_color_frame(self, frame):
        color_image_data = self._mono_to_color_processor.transform_to_24(frame.image_buffer,
                                                                              self._image_width,
                                                                          self._image_height)
        color_image_data = color_image_data.reshape(self._image_height, self._image_width, 3)
        return color_image_data
    
    def raw_snapshot(self):
        if not self.live_view:
            self._camera.issue_software_trigger()
        # if it's in live_view, camera should already be triggered
        frame = self.get_frame()
        if frame:
            return True, self.process_frame(frame)
        return False, None
    
    @Camera.live_view.setter
    def live_view(self, live_view):
        if live_view == self._live_view: return # small redundancy with Camera.live_view
        Camera.live_view.fset(self, live_view)
        if live_view:
            self.frames_per_trigger_zero_for_unlimited = 0 # unlimited
            # decorator should trigger as self.live_view == True
        else:
            self.frames_per_trigger_zero_for_unlimited = 1 # disarms and rearms
            
    def get_control_widget(self):
        "Get a Qt widget with the camera's controls (but no image display)"
        return KiraluxCameraControlWidget(self)
        
class KiraluxCameraControlWidget(CameraControlWidget):
    """A control widget for the Thorlabs camera, with extra buttons."""
    def __init__(self, camera, auto_connect=True):
        super().__init__(camera, auto_connect=False)
        gb = QuickControlBox()
        gb.add_doublespinbox("exposure",
                             *(e/1000 for e in camera.exposure_time_range_us)) 
        gb.add_spinbox("gain", *camera.gain_range) # setting range
        gb.add_button("show_camera_properties_dialog", title="Camera Setup")
        gb.add_button("show_video_format_dialog", title="Video Format")
        self.layout().insertWidget(1, gb) # put the extra settings in the middle
        self.quick_settings_groupbox = gb        
        
        self.auto_connect_by_name(controlled_object=self.camera, verbose=False)
        
if __name__ == '__main__':        
                
    k = Kiralux()
    k.show_gui(False)
