# -*- coding: utf-8 -*-
"""
Created on Wed Apr 27 19:32:16 2016

@author: rwb27
"""

import nplab
from nplab.instrument.camera import CameraControlWidget
from nplab.instrument.camera.opencv import OpenCVCamera
from nplab.ui.ui_tools import QuickControlBox
from nplab.utils.gui import QtCore, QtGui, QtWidgets


class MyOpenCVCamera(OpenCVCamera):
    def get_control_widget(self):
        "Return a widget with the camera's controls (but no image viewer)"
        return MyCameraControlWidget(self)

class MyCameraControlWidget(CameraControlWidget):
    def __init__(self, camera, auto_connect=True):
        super(MyCameraControlWidget, self).__init__(camera, auto_connect=False)

        gb = QuickControlBox()
        gb.add_doublespinbox("gain")
        gb.add_doublespinbox("exposure")
        self.layout().insertWidget(1, gb) # put the extra settings in the middle
        self.quick_settings_groupbox = gb        
        
        self.auto_connect_by_name(controlled_object=self.camera, verbose=False)
        
if __name__ == '__main__':
    cam = MyOpenCVCamera()
    cam.live_view = True
    gui = cam.show_gui(blocking=False)
    