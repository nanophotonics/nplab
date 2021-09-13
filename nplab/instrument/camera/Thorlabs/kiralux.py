# -*- coding: utf-8 -*-
"""
Created on Fri Mar  5 16:10:03 2021

@author: Eoin ee306
Tested with the Thorlabs Kiralux CS895CU. Should work with any of them though.

https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=ThorCam
"""
import platform
import os
import time
from functools import wraps
from pathlib import Path
import numpy as np
import threading

from nplab.utils.gui import QtWidgets
from nplab.instrument.camera import Camera, CameraControlWidget
from nplab.utils.notified_property import NotifiedProperty
from nplab.ui.ui_tools import QuickControlBox

from thorlabs_tsi_sdk.tl_camera import TLCameraSDK, Range, _logger
_logger.setLevel('CRITICAL') # mutes a lot of unnecessary logging
from thorlabs_tsi_sdk.tl_camera_enums import SENSOR_TYPE
from thorlabs_tsi_sdk.tl_mono_to_color_processor import MonoToColorProcessorSDK


dll_path = Path(__file__).parent / 'dlls' #relative to this file
if platform.architecture()[0] == '64bit':
    dll_path /= 'Native_64_lib'
if platform.architecture()[0] == '32bit':
    dll_path /= 'Native_32_lib'

os.add_dll_directory(dll_path.absolute()) # 3.8 specific
os.environ['PATH'] = str(dll_path.absolute())+';' + os.environ['PATH'] 
# need both these for some reason

def disarmed(f):
    ''' A Thorlabs camera must be "armed" before an image can 
    be taken. However, once armed, certain parameters cannot be 
    changed, or methods called. This decorator ensures the camera
    is disarmed while performing a certain function. Calling 
    such decorated methods may disrupt live view. 
    '''
    @wraps(f)
    def inner_func(self, *args, **kwargs):
        armed = self._camera.is_armed
        if armed:
            self._camera.disarm() # could use self.disarm, but no need
        returned = f(self, *args, **kwargs)
        if armed:
            self._camera.arm(1) # 1 frame to buffer
        return returned
    return inner_func

'''these two function pass a property's getter and setter 
methods onto the internal _camera attribute - so getting a 
property like `kiralux.is_led_on` is equivalent to 
`kiralux._camera.is_led_on`. This is nice for easy user access to sdk methods,
and for automatic gui generation of camera parameters.'''        
def convert_getter(attr):
    return lambda obj: getattr(obj._camera, attr)
def convert_setter(attr):
    return lambda obj, val: setattr(obj._camera, attr, val)       

class Kiralux(Camera):
    '''can't inherit directly from TLCamera due to complications
    with how they're opened.'''
    controllables = [] # properties that can be read and set
    readables = [] # properties that are read-only
    def __init__(self):
        
        self.sdk = TLCameraSDK() 
        '''acquire an SDK instance - this is used to open the camera
        multiple thorlabs cameras will need to use the same instance
        so will need refactoring'''
        camera_list = self.sdk.discover_available_cameras()
        self._camera = self.sdk.open_camera(camera_list[0]) 
        
        if self._camera.camera_sensor_type != SENSOR_TYPE.BAYER:
            # Sensor type is not compatible with the color processing library
            self.raw_snapshot = self.grey_raw_snapshot
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
        self._camera.frames_per_trigger_zero_for_unlimited = 1
        self._camera.arm(2)
        self._camera.image_poll_timeout_ms = 0
        self._add_parameters() # put the _camera properties in Kiralux
        super().__init__()
    
    def _add_parameters(self):
        # add all of Kiralux's properties to controllables/readables
        for attr in dir(self.__class__):
            prop = getattr(self.__class__, attr)
            if isinstance(prop, (property, NotifiedProperty)): # if it's a property
                if prop.fset is None: # if it has not setter it's read-only
                    self.readables.append(attr)
                else:
                    self.controllables.append(attr)
        
        # and add all of tl_camera's
        clss = self._camera.__class__
        for attr in dir(clss):
            prop = getattr(clss, attr)
            if (isinstance(prop, property) and # if it's a property
                not hasattr(self, attr)): # and it's not already in Kiralux (like gain etc. )
                if prop.fset is None:
                    self.readables.append(attr)
                else:
                    self.controllables.append(attr)
                # add to Kiralux as a NotifiedProperty    
                setattr(self.__class__,
                        attr,
                        NotifiedProperty(convert_getter(attr),
                                         convert_setter(attr)))  
        # try set the controllables, read the readables and discard 
        # any that don't work. Prints a lot of stuff if _logger isn't in CRITICAL
        for attr in self.controllables:
            try:
                v = getattr(self, attr)
                setattr(self, attr, v)
            except:
                self.controllables.remove(attr)
        for attr in self.readables:
            try:
                getattr(self, attr)
            except:
                self.readables.remove(attr)
        
    @NotifiedProperty
    @disarmed
    def frames_per_trigger(self):
        return self._camera.frames_per_trigger_zero_for_unlimited

    @frames_per_trigger.setter
    @disarmed
    def frames_per_trigger(self, val):
        self._camera.frames_per_trigger_zero_for_unlimited = val
    
    @property # how long to wait for a frame before deciding it isn't coming
    def timeout(self): #s
        return self.exposure*3/1_000
    
    def raw_snapshot(self):
        frame = self.get_frame() # mono image
        if frame is not None:
            width = frame.image_buffer.shape[1]
            height = frame.image_buffer.shape[0]
            if (width != self._image_width) or (height != self._image_height):
                self._image_width = width
                self._image_height = height
                print("Image dimension change detected, image acquisition thread was updated")
            # color the image. transform_to_24 will scale to 8 bits per channel
            color_image_data = self._mono_to_color_processor.transform_to_24(frame.image_buffer,
                                                                             self._image_width,
                                                                             self._image_height)
            color_image_data = color_image_data.reshape(self._image_height, self._image_width, 3)
            return True, color_image_data
        return False, None
            
    def get_frame(self, timeout=None):
        if not self.is_armed:
            self.arm(1) # has to be armed!
        if not self._live_view:
            # should already be sending frames if in live_view 
            # otherwise you have to ask for one!
            self._camera.issue_software_trigger()
        frame = None
        start = time.time()
        if timeout is None: timeout=self.timeout
        while frame is None and (time.time() - start) < timeout:
            frame = self._camera.get_pending_frame_or_null()
            # return a frame once you get one, or it times out
        return frame
            
    def grey_raw_snapshot(self):
        frame = self.get_frame()
        if frame is not None:
            return True, frame
        return False, np.array([])
    
    def grey_image(self):
        frame = self.get_frame()
        if frame is not None:
            scaled_image = frame.image_buffer >> (self._bit_depth - 8) # downscale
            return  scaled_image
        
    # slightly refactoring arming the camera into a property for
    # ease of gui integration
    @NotifiedProperty
    def armed(self):
        return self._camera.is_armed
    @armed.setter
    def armed(self, val):
        if val:
            return self._camera.arm(1)
        else:
            return self._camera.disarm()
            
    @property 
    def gain_range(self):
        # explicitly adding gain range although _add_parameters does
        # it to make the below more readable. 
        # returns a Range type named tuple. 
        return self._camera.gain_range
    
    @NotifiedProperty
    def gain(self):
        return self._camera.gain
    @gain.setter
    def gain(self, val):
        # don't allow gains outside range
        if val > (max_ := self.gain_range.max):
            val = max_
        if val < (min_ := self.gain_range.min):
            val = min_
        self._camera.gain = val
    
    @property
    def exposure_range(self): # in ms
        return Range(*np.array(self._camera.exposure_time_range_us)/1_000)
    
    @NotifiedProperty
    def exposure(self): # in ms
        return self._camera.exposure_time_us/1_000 # from us
    
    @exposure.setter
    def exposure(self, val): # in ms
        
        if val > (max_ := self.exposure_range.max):
            val = max_
        if val < (min_ := self.exposure_range.min):
            val = min_
        self._camera.exposure_time_us = val*1_000
    
    # putting live_view setter in Kiralux as needs modification to handle
     # arming/disarming and triggering the camera. 
    @NotifiedProperty
    def live_view(self):
        """Whether the camera is currently streaming and displaying video"""
        return self._live_view
    
    @live_view.setter
    def live_view(self, live_view):
        """Turn live view on and off.
        
        This is used to start and stop streaming of the camera feed.  The
        default implementation just repeatedly takes snapshots, but subclasses
        are encouraged to override that behaviour by starting/stopping a stream
        and using a callback function to update self.latest_raw_frame."""
        if live_view==True:
            if self._live_view:
                return # do nothing if it's going already.
            print("starting live view thread")
            self.frames_per_trigger = 0 # unlimited
            self._camera.issue_software_trigger()
            try:
                self._frame_counter = 0
                self._live_view_stop_event = threading.Event()
                self._live_view_thread = threading.Thread(target=self._live_view_function)
                self._live_view_thread.start()
                self._live_view = True
            except AttributeError as e: #if any of the attributes aren't there
                print("Error:", e)
        else:
            if not self._live_view:
                return # do nothing if it's not running.
            print("stopping live view thread")
            
            try:
                self._live_view_stop_event.set()
                self._live_view_thread.join()
                del(self._live_view_stop_event, self._live_view_thread)
                self._live_view = False
                self._camera.frames_per_trigger = 1 # back to single image mode
            except AttributeError:
                raise Exception("Tried to stop live view but it doesn't appear to be running!")    
    
    def camera_parameter_names(self):
        return self.controllables # + readables 
        '''the parameter view widget isn't very good at setting stuff,
        so could add the readables just to see them too? '''                                        
    
    def get_control_widget(self):
        "Get a Qt widget with the camera's controls (but no image display)"
        return KiraluxCameraControlWidget(self)


class KiraluxCameraControlWidget(CameraControlWidget):
    """A control widget for the Kiralux camera, with extra buttons."""
    def __init__(self, camera, auto_connect=True):
        super().__init__(camera, auto_connect=False)
        self.camera = camera
        gb = QuickControlBox()
        arm = QtWidgets.QCheckBox()
        arm.setText('Arm')
        arm.clicked.connect(self.arm)
        arm.setChecked(camera.is_armed)
        gb.layout().addRow("", arm)
        gb.add_spinbox("exposure", *camera.exposure_range)
        gb.add_spinbox("gain", *camera.gain_range)
       
        self.layout().insertWidget(1, gb) # put the extra settings in the middle
        self.quick_settings_groupbox = gb        
        
        self.auto_connect_by_name(controlled_object=self.camera, verbose=False)
    
    def arm(self, Bool):
       self.camera.armed = Bool
       
if __name__ == '__main__':
    k = Kiralux()
    k.show_gui(False)       

