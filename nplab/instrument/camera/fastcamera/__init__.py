import sys

import pyjisa.autoload
import os
from threading import Lock, Thread
from typing import Callable, Generic, List, Tuple, TypeVar

import numpy as np
from nplab.instrument.camera import Camera

from jisa                      import Util
from jisa.devices.camera       import Camera as JCamera, NPAdapter
from jisa.devices.camera.frame import Frame, RGBFrame, U16RGBFrame

from nplab.instrument.camera.fastcamera.gui import FastCameraGUI, FastCameraPreviewGUI

from .widgets import *

from nplab.utils.notified_property import NotifiedProperty

from qtpy.QtCore import QThreadPool

C = TypeVar("C", bound=JCamera)

class FastCamera(Camera, Generic[C]):

    def __init__(self, camera: C):

        self._parameters = list(camera.getAllParameters())
        super().__init__()
        
        self.camera = camera
        self.buffer = None
        self.arr    = None
        self.pool   = QThreadPool()
        self.queue  = camera.openFrameQueue(1)

        self.camera.addFrameListener(self.updateFrame)


    def updateFrame(self, frame: Frame):

        try:

            with self.acquisition_lock:

                height = frame.getHeight()
                width  = frame.getWidth()
                
                if self.buffer is None or self.rgb.shape[0] != height or self.rgb.shape[1] != width:
                    self.buffer = frame.getARGBData()
                    self.arr    = np.array(self.buffer)
                    self.rgb    = np.empty((height, width, 3), dtype=np.uint8)
                else:
                    frame.readARGBData(self.buffer)
                    np.copyto(self.arr, self.buffer)

                argb2d = self.arr.view(np.uint8).reshape(height, width, 4)

                self.rgb[..., 0] = argb2d[..., 2]
                self.rgb[..., 1] = argb2d[..., 1]
                self.rgb[..., 2] = argb2d[..., 0]

                self.update_latest_frame(self.rgb)

        except Exception as e:
            print(e)


    def raw_snapshot(self) -> Tuple[bool, np.ndarray]:

        frame: Frame = self.camera.getFrame()

        height = frame.getHeight()
        width  = frame.getWidth()
        rgb    = np.empty((height, width, 3), dtype=np.uint8)
        argb2d = np.array(frame.getARGBData()).view(np.uint8).reshape(height, width, 4)

        rgb[..., 0] = argb2d[..., 2]
        rgb[..., 1] = argb2d[..., 1]
        rgb[..., 2] = argb2d[..., 0]

        return True, rgb

    
    def get_next_frame(self, timeout=60, discard_frames=0, assert_live_view=True, raw=True) -> np.ndarray:
        return self.raw_snapshot()[1]
    

    @NotifiedProperty
    def live_view(self) -> bool:
        return self.camera.isAcquiring()
    

    @live_view.setter
    def live_view(self, live: bool):
        
        if live:
            self.camera.startAcquisition()
        else:
            self.camera.stopAcquisition()


    def exposure(self) -> float:
        return self.camera.getIntegrationTime()


    def setExposure(self, time: float):
        self.camera.setIntegrationTime(time)


    exposure = property(exposure, setExposure)

    def gain(self) -> float:
        return 0.0

    def setGain(self, gain: float):
        pass

    gain = property(gain, setGain)

    def getCamera(self) -> C:
        return self.camera
    

    def camera_parameter_names(self):
        return [p.getName() for p in self._parameters]
    

    def get_camera_parameter(self, parameter_name):
        found = [p for p in self._parameters if p.getName() == parameter_name]
        print(found)
        return found[0].getCurrentValue()
    

    def set_camera_parameter(self, parameter_name, value):
        found = [p for p in self._parameters if p.getName() == parameter_name]
        return found[0].set(value)


    def get_qt_ui(self, control_only=False, parameters_only=False):
        return FastCameraGUI(self.camera, self, not control_only)    

    def get_control_widget(self):
        return self.get_qt_ui(control_only=True)


class FastCameraBad(Camera, Generic[C]):

    def __init__(self, camera: C):

        self._parameters = list(camera.getAllParameters())
        super().__init__()
        self._camera     = NPAdapter(camera)

    def raw_snapshot(self):
        return True, np.array(self._camera.raw_snapshot())

    def getCamera(self) -> C:
        return self._camera.getCamera()
    
    def camera_parameter_names(self):
        return [p.getName() for p in self._parameters]
    
    def get_camera_parameter(self, parameter_name):
        found = [p for p in self._parameters if p.getName() == parameter_name]
        print(found)
        return found[0].getCurrentValue()
    
    def set_camera_parameter(self, parameter_name, value):
        found = [p for p in self._parameters if p.getName() == parameter_name]
        return found[0].set(value)

    # def get_qt_ui(self, control_only=False, parameters_only=False):
    #     return FastCameraGUI(self._camera)