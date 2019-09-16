# -*- coding: utf-8 -*-
"""
Created on Thu Sep 12 15:35:06 2019

@author: np-albali
"""

from nplab.instrument.camera import Camera
from pyvcam.camera import Camera as VCamera
from pyvcam import pvc

class VCam(VCamera,Camera):
    def __init__(self):  
        pvc.init_pvcam()
        name = pvc.get_cam_name(0)
        VCamera.__init__(self,name)
        Camera.__init__(self)
        self.open()
        self.exp_time = 1

    def raw_snapshot(self):
        return True, self.get_frame(self.exp_time)
