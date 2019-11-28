from __future__ import division
from __future__ import print_function
from builtins import map
from builtins import range
from past.utils import old_div
__author__ = 'chrisgrosse'


import sys
from qtpy.QtWidgets import QWidget, QGridLayout, QHBoxLayout
from qtpy import QtCore
from qtpy.QtCore import Qt
from qtpy.QtGui import QPainter, QColor, QPen
import pyqtgraph as pg
import numpy as np


""" A small vertical bar indicating, for example, the position of a piezo scanner.

    The arguments needed to create a class object specify the minimum
    and maximum of the displayed value, as well as the size of the margin when
    the bar changes its colour form green to red because the value is close to
    the specified limits. The default value of the margin parameter is 0.1,
    that is, the bar changes colour when its value is closer than 10% of the
    total region to the limits.
    """
class PositionBarWidget(QWidget):

    def __init__(self, min_value, max_value, margin=0.1):
        super(PositionBarWidget, self).__init__()
        self.min_value = min_value
        self.max_value = max_value
        self.range = max_value-min_value
        self.margin = margin
        self.initUI()
        self.setValue(old_div(self.range,2))



    def initUI(self):
        self.setMinimumSize(15,50)

    def setValue(self, value):
        self.value = value-self.min_value
        self.repaint()

    def paintEvent(self, e):
        qp = QPainter()
        qp.begin(self)
        self.drawWidget(qp)
        qp.end()

    def drawWidget(self, qp):
        size = self.size()
        w = size.width()
        h = size.height()

        lower_threshold = self.margin*self.range
        upper_threshold = (1-self.margin)*self.range

        till = round(old_div((h * (self.range-self.value)),self.range))

        if self.value <= lower_threshold or self.value >= upper_threshold:
            qp.setBrush(QColor(255, 100, 100))
        else:
            qp.setBrush(QColor(50, 255, 50))
        qp.setPen(QColor(0,0,0))
        qp.drawRect(0, h-1, w, till-h)

        pen = QPen(QColor(20, 20, 20), 1, Qt.SolidLine)
        qp.setPen(pen)
        qp.setBrush(Qt.NoBrush)
        qp.drawRect(0, 0, w-1, h-1)

        sepeation_marks = int(round(h / 10.0))
        for i in range(sepeation_marks, 10*sepeation_marks, sepeation_marks):
            qp.drawLine(0, i, 5, i)


class XYPositionWidget(pg.PlotWidget):

    def __init__(self, xrange_nm, yrange_nm):
        super(XYPositionWidget, self).__init__(background=None)
        self.setXRange(0,xrange_nm)
        self.setYRange(0,yrange_nm)
        self.init_plot()
        self.crosshair = CrossHair('r')
        self.addItem(self.crosshair)
        self.crosshair.crosshair_size=0.05*xrange_nm
#        self.crosshair.CrossHairMoved.connect(self.mouseMoved)
        self.pos = []
        self.unit = 'pxl'

    def init_plot(self):

#        self.setGeometry(400, 50, 400, 400)
#        self.setBackground(background=None)
#        data = np.zeros((100,100))
#        img = pg.ImageItem(image=data)
#        self.addItem(img)
        self.showAxis('right',show=True)
        self.showAxis('top',show=True)
        self.getAxis('left').setPen('k')
        self.getAxis('bottom').setPen('k')
        self.getAxis('right').setPen('k')
        self.getAxis('top').setPen('k')
        self.getAxis('top').showLabel(show=False)
        self.getAxis('right').setStyle(showValues=False)
        self.getAxis('top').setStyle(showValues=False)
        self.getAxis('left').setStyle(showValues=False)
        self.getAxis('bottom').setStyle(showValues=False)
        self.setMouseEnabled(x=False,y=False)
        self.setMinimumSize(150,100)
        self.show()


    def setValue(self, new_x, new_y):
        return self.crosshair.setPos(new_x, new_y)


    def pxl_to_unit(self, pxl):
        return pxl

    def mouseMoved(self):
        self.pos = self.crosshair.pos()
        x1 = self.crosshair.pos()[0]
        y1 = self.crosshair.pos()[1]
#        xu1, yu1 = self.pxl_to_unit((x1, y1))
        print("cursor moved to pixel: [%i,%i]" % (x1,y1))



""" simple crosshair for guis, copied from Andor code
"""
class CrossHair(pg.GraphicsObject):
    CrossHairMoved = QtCore.Signal()
    Released = QtCore.Signal()

    def __init__(self, color):
        super(CrossHair, self).__init__()
        self.color = color
        self.crosshair_size = 2

    def paint(self, p, *args):
        p.setPen(pg.mkPen(self.color))
        p.drawLine(-self.crosshair_size, 0, self.crosshair_size, 0)
        p.drawLine(0, -self.crosshair_size, 0, self.crosshair_size)

    def boundingRect(self):
        return QtCore.QRectF(-self.crosshair_size, -self.crosshair_size, 2*self.crosshair_size, 2*self.crosshair_size)

    def mouseDragEvent(self, ev):
        ev.accept()
        if ev.isStart():
            self.startPos = self.pos()
        elif ev.isFinish():
            self.setPos(*list(map(int, self.pos())))
        else:
            self.setPos(self.startPos + ev.pos() - ev.buttonDownPos())
        self.CrossHairMoved.emit()



""" A position widget for a 3-axes (piezo) stage.
    It is a combination of the XYPositionWidget and the PositionBarWidget.
"""
class XYZPositionWidget(QWidget):

    def __init__(self,xrange_nm, yrange_nm, zrange_nm, show_xy_pos=True,
                 show_z_pos=True):
        super(XYZPositionWidget, self).__init__()
        layout = QHBoxLayout()
        if show_xy_pos:
            self.xy_widget = XYPositionWidget(xrange_nm, yrange_nm)
            layout.addWidget(self.xy_widget)
        if show_z_pos:
            self.z_bar = PositionBarWidget(0,zrange_nm)
            layout.addWidget(self.z_bar)
        self.setLayout(layout)
#       grid = QGridLayout()
#        grid.addWidget(self.xy_widget, 0,0)
#        grid.addWidget(self.z_bar, 0,1)
#        self.setLayout(grid)
#        self.setMinimumSize(150,100)
#        self.setGeometry(100, 100, 220, 200)



if __name__ == '__main__':

    from PyQt4 import QtGui

    app = QtGui.QApplication(sys.argv)  # create PyQt application object
    pg.setConfigOption('foreground','k')
    xyz_widget = XYZPositionWidget(200,200,100,show_xy_pos=False)
    xyz_widget.show()



