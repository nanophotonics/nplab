# -*- coding: utf-8 -*-
"""
Created on Sat Oct 14 15:39:55 2017

@author: wmd22
"""

from builtins import range
import numpy as np
from qtpy import QtCore, QtGui, QtWidgets
import pyqtgraph as pg

# The CircleROI in pyqtgraph has a scale handle
app = QtWidgets.QApplication([])
class MyCircleOverlay(pg.EllipseROI):
    def __init__(self, pos, size, **args):
        pg.ROI.__init__(self, pos, size, **args)
        self.aspectLocked = True
 
def add_particle_circles(image_view,particle_locations, circle_size = 10):
    pen = QtGui.QPen(QtCore.Qt.red, 0.1)
    for particle_loc in particle_locations:
        i.getView().addItem(MyCircleOverlay(pos=(particle_loc[0], particle_loc[1]),
                            size=circle_size, pen=pen, movable=False))

def find_particles(self,img=None,border_pixels = 50):
    """find particles in the supplied image, or in the camera image"""
    self.threshold_image(
                         self.denoise_image( 
                                            cv2.cvtColor(frame,cv2.COLOR_RGB2GRAY) # change to gray
                                            )
                        )[self.border_pixels:-self.border_pixels,
                        self.border_pixels:-self.border_pixels] #ignore the edges
    labels, nlabels = ndimage.measurements.label(img)
    return [np.array(p)+15 for p in ndimage.measurements.center_of_mass(img, labels, list(range(1,nlabels+1)))] #add 15 onto all the positions
            # why 15?
i = pg.ImageView()
i.setFixedSize(800, 600)
img = pg.gaussianFilter(np.random.normal(size=(200, 200)), (5, 5)) * 20 + 100
i.setImage(img)

r = MyCircleOverlay(pos=(100, 100), size=10, pen=pen, movable=False)
i.getView().addItem(r)
# Qt application


# image view
# show and execute Qt app
i.show()
app.exec_()