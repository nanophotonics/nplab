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

class Rolera(Camera):
    exposure = DumbNotifiedProperty(1000)
    def __init__(self):
        super().__init__()
        pvc.init_pvcam()
        self._cam = next(PyVCam.detect_camera())
        self._cam.open()
    
    def raw_snapshot(self):
        return True, self._cam.get_frame(self.exposure)
    
    @NotifiedProperty
    def gain(self):
        return self._cam.gain
   
    @locked_action
    @gain.setter
    def gain(self, value):
        self._cam.gain = int(value)
    
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