# -*- coding: utf-8 -*-
"""
Created on Fri Apr 30 12:10:10 2021

@author: hera
"""

from nplab.instrument.camera import Camera, CameraControlWidget
from nplab.instrument.camera.camera_scaled_roi import CameraRoiScale
from pyvcam import pvc
from pyvcam.camera import Camera as PyVCam
from nplab.ui.ui_tools import QuickControlBox
from nplab.utils.notified_property import NotifiedProperty, DumbNotifiedProperty
from nplab.utils.thread_utils import locked_action
import numpy as np

class Rolera(Camera):
    
    def __init__(self):
        super().__init__()
        pvc.init_pvcam()
        self._cam = next(PyVCam.detect_camera())
        self._cam.open()

    
    def raw_snapshot(self):
        return True, self._cam.get_frame()

    @property
    def roi(self):
        return self._cam.roi

    @roi.setter
    def roi(self, value):
        # Takes in a tuple following (x_start, x_end, y_start, y_end), and
        # sets self.__roi if valid
        if (isinstance(value, tuple) and all(isinstance(x, int) for x in value)
                and len(value) == 4):

            if (value[0] in range(0, self._cam.sensor_size[0] + 1) and
                    value[1] in range(0, self._cam.sensor_size[0] + 1) and
                    value[2] in range(0, self._cam.sensor_size[1] + 1) and
                    value[3] in range(0, self._cam.sensor_size[1] + 1)):
                self._cam.roi = value
                self._cam._calculate_reshape()
                return

            else:
                raise ValueError('Invalid ROI paramaters for {}'.format(self))

        raise ValueError('{} ROI expects a tuple of 4 integers'.format(self))

    
    def get_roi_image(self, value=None,debug=0):
        x,raw_image = self.raw_snapshot()
        if value is None:
            roi = self.roi
        else:
            roi=value
        if debug > 0:
            print("Region of interest:",roi)
        roi_image = raw_image[roi[0]:roi[1],roi[2]:roi[3]]
        if debug > 0:
            print("roi_image.shape:",roi_image.shape)
        return roi_image

    def get_spectrum(self, value=None):    
        roi_image = self.get_roi_image(value)
        raw_spectrum = np.mean(roi_image,axis=0)
        #pixel_offsets = np.array(list(range(0,len(raw_spectrum))))-int(self.FrameWidth/2)
        return raw_spectrum#,pixel_offsets

    
    @NotifiedProperty
    def gain(self):
        return self._cam.gain
   
    @locked_action
    @gain.setter
    def gain(self, value):
        self._cam.gain = int(value)
    
    @NotifiedProperty
    def exposure(self):
        return self._cam.exp_time
   
    @locked_action
    @exposure.setter
    def exposure(self, value):
        self._cam.exposure = value
    
    def get_control_widget(self):
        return RoleraCameraControlWidget(self)
    
class RoleraCameraControlWidget(CameraControlWidget):
    """A control widget for the Rolera camera, with extra buttons."""
    def __init__(self, camera, auto_connect=True):
        super(RoleraCameraControlWidget, self).__init__(camera, auto_connect=False)
        gb = QuickControlBox()
        gb.add_doublespinbox("exposure")
        gb.add_spinbox('gain')
        gb.add_button("show_camera_properties_dialog", title="Camera Setup")
        gb.add_button("show_video_format_dialog", title="Video Format")
        self.layout().insertWidget(1, gb) # put the extra settings in the middle
        self.quick_settings_groupbox = gb        
        
        self.auto_connect_by_name(controlled_object=self.camera, verbose=False)
        
if __name__ == '__main__':
    rolera=Rolera()
    rolera.show_gui(False)