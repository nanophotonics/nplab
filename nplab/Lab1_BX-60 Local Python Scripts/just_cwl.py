# -*- coding: utf-8 -*-
"""
Created on Tue Nov 22 14:58:29 2022

@author: HERA
"""

from nplab.instrument.stage.prior import ProScan
from nplab.instrument.camera.lumenera import LumeneraCamera
from nplab.instrument.camera.camera_with_location import CameraWithLocation
import nplab.datafile as df
   
if __name__ == '__main__':
    
    
    cam = LumeneraCamera(1)
    stage = ProScan("COM4", hardware_version = 2)
    CWL = CameraWithLocation(cam, stage)
    CWL.show_gui(blocking=False)
    # cam.show_gui(block=False)
    data_file = df.current()
    data_file.show_gui(blocking = False)