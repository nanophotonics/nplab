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

#        gb = QtGui.QGroupBox()
#        self.quick_settings_groupbox = gb
#        gb.setTitle("Quick Settings")
#        gb.setLayout(QtGui.QFormLayout())
#        
#        self.gain_spinbox = QtGui.QDoubleSpinBox()
#        self.gain_spinbox.setObjectName("gain_spinbox")
#        print "gain spinbox is called " + self.gain_spinbox.objectName()
#        gb.layout().addRow("Gain:",self.gain_spinbox)
#        self.exposure_spinbox = QtGui.QDoubleSpinBox()
#        self.exposure_spinbox.setObjectName("exposure_spinbox")
#        gb.layout().addRow("Exposure:",self.exposure_spinbox)
        
        gb = QuickControlBox()
        gb.add_doublespinbox("gain")
        gb.add_doublespinbox("exposure")
        self.layout().insertWidget(1, gb) # put the extra settings in the middle
        self.quick_settings_groupbox = gb        
        
        self.auto_connect_by_name(controlled_object=self.camera, verbose=True)
        
if __name__ == '__main__':
    cam = MyOpenCVCamera()
    cam.show_gui()
    
    gb = QuickControlBox()
    gb.add_doublespinbox("gain")
    gb.add_checkbox("live_view")
    gb.auto_connect_by_name(cam, verbose=True)
    gb.show()
    cam.show_gui()
    