# -*- coding: utf-8 -*-
"""
Created on Thu Feb 11 13:41:47 2021

@author: hera
"""
from nplab.utils.gui import QtCore, QtGui, QtWidgets
from nplab.ui.widgets.imageview import ExtendedImageView
from nplab.instrument.camera.camera_scaled_roi import CameraRoiScale
from nplab.utils.array_with_attrs import ArrayWithAttrs
import numpy as np
from nplab.instrument.camera.Picam.pixis import Pixis


class PixisUI(CameraRoiScale, Pixis):
    """A Dummy CameraRoiScale camera  """

    def __init__(self, data='spectrum'):
        super(PixisUI, self).__init__()
        self.data = data
        self.pixis = Pixis(debug=0)
        self.pixis.StartUp()

    def raw_snapshot(self, update_latest_frame=True):
        """Returns a True, stating a succesful snapshot, followed by a (100,100)
        picture randomly generated image"""
        if self.data == 'spectrum':
            self.pixis.SetExposureTime(1)
            ran = 100 * np.random.random((200, 1600))#self.pixis.raw_snapshop()
            print(ran)
        else:
            ran = 100 * np.random.random((200, 1600))
        self._latest_raw_frame = ran
        return True, ran
    
    def end(self):
        self.pixis.ShutDown()

    @property
    def x_axis(self):
        return np.arange(1600) + 1

    @x_axis.setter
    def x_axis(self, value):
        self.axis_values['bottom'] = value
        
if __name__ == '__main__':

    dcrd = PixisUI()
    dcrd.data = 'spectrum'
    gui = dcrd.show_gui(blocking=False)
    dw = gui.preview_widget
    dw.setImage(np.random.random((200, 1600)))