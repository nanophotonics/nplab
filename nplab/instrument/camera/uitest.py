# -*- coding: utf-8 -*-
"""
Created on Mon Apr 25 11:48:15 2016

@author: rwb27
"""

from nplab.utils.gui import QtGui, QtCore, uic, get_qt_app
import matplotlib
import numpy as np
import h5py
import pyqtgraph as pg
import os
import threading
import time

from nplab.ui.ui_tools import UiTools

class MyGUI(QtGui.QDialog, UiTools):
    def __init__(self):
        super(MyGUI, self).__init__()
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'untitled.ui'), self)

class CameraPreviewWidget(pg.GraphicsView):
    """A Qt Widget to display the live feed from a camera."""
    update_data_signal = QtCore.pyqtSignal(np.ndarray)
    
    def __init__(self):
        super(CameraPreviewWidget, self).__init__()
        
        self.image_item = pg.ImageItem()
        self.view_box = pg.ViewBox(lockAspect=True)
        self.view_box.addItem(self.image_item)
        self.view_box.setContentsMargins(0,0,0,0)
        self.view_box.setBackgroundColor([128,128,128,255])
        self.setCentralWidget(self.view_box)
        self.setContentsMargins(0,0,0,0)
        
        # We want to make sure we always update the data in the GUI thread.
        # This is done using the signal/slot mechanism
        self.update_data_signal.connect(self.update_widget, type=QtCore.Qt.QueuedConnection)

    def update_widget(self, newimage):
        """Draw the canvas, but do so in the Qt main loop to avoid threading nasties."""
        self.image_item.setImage(newimage)
        
    def update_image(self, newimage):
        self.update_data_signal.emit(newimage)



if __name__ == '__main__':
    app = get_qt_app()
#    g = MyGUI()
#    g.show()
    pw = CameraPreviewWidget()
    
    stop_video = False
    def make_video():
        while not stop_video:
            time.sleep(0.1)
            pw.update_image(np.random.random((100,100)))
    
    pw.show()
    t = threading.Thread(target=make_video)
    t.start()
    