# -*- coding: utf-8 -*-
"""
Subclass of Camera that has units for its axis. The GUI also provides crosshairs for defining ROIs
"""

from nplab.utils.gui import QtCore, QtGui, QtWidgets, uic
from nplab.ui.ui_tools import UiTools
from nplab.instrument.camera import Camera
import pyqtgraph
import numpy as np
import os
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients
import operator
from functools import partial


class CameraRoiScale(Camera):
    """
    Camera with two main features:
        - Scaled axes with whatever units the user wants. Subclasses may overwrite the pos_to_unit method, or provide
        an array (x_axis or y_axis) as a lookup table.

        - ROI selection using crosshairs. Subclasses should overwrite the roi method, e.g. to set ROI in the camera hardware

    This class also handles binning, and keeps the scaled axes and ROI selection unaffected by the binning
    """
    def __init__(self):
        super(CameraRoiScale, self).__init__()
        self.x_axis = None
        self.y_axis = None

    def pos_to_unit(self, pos, axis):
        """
        Function used to calibrate the camera pixels in the GUI.

        There are two ways a user can provide a calibration:
            - Overwrite this function in a subclass.
            - Provide an array (self.x_axis or self.y_axis) of the same size as the relevant axis of the camera.

        :param pos: list of integers
        :param axis: string. Either 'bottom' or 'left'
        :return: list of floats
        """

        def get_value(axis_vector, index):
            """Function that extracts the value from a list (axis_vectors) according to some given position (index),
            returning 0 if the index is out of range"""
            try:
                return axis_vector[int(index)]
            except IndexError:
                return 0

        if axis == 'bottom':
            if self.x_axis is not None:
                return map(partial(get_value, self.x_axis), pos)
            else:
                return map(int, pos)
        elif axis == 'left':
            if self.y_axis is not None:
                return map(partial(get_value, self.y_axis), pos)
            else:
                return map(int, pos)
        else:
            raise ValueError

    @property
    def roi(self):
        """

        :return: 4-tuple of integers. Pixel positions xmin, xmax, ymin, ymax
        """
        return 0, 1, 0, 1

    @property
    def gui_roi(self):
        """

        :return: 4-tuple of integers. x, y positions of the two crosshairs in the preview widget
        """
        assert len(self._preview_widgets) == 1
        for wdg in self._preview_widgets:
            lims = wdg.get_roi()
        return lims

    @property
    def binning(self):
        return 1, 1

    def update_widgets(self):
        for widgt in self._preview_widgets:
            roi = self.roi
            widgt._pxl_offset = (roi[0], roi[2])
            widgt._pxl_scale = self.binning
            setattr(widgt, '_pos_to_unit', self.pos_to_unit)

            size = min(((roi[1] - roi[0])/50, (roi[3]-roi[2])/50))
            for idx in [1, 2]:
                xhair = getattr(widgt, 'CrossHair%d' % idx)
                xhair._size = size
                xhair.update()

            vw = widgt.ImageDisplay.getView()
            for idx, lbl in enumerate(["bottom", "left"]):
                ax = vw.axes[lbl]["item"]
                setattr(ax, 'pos_to_unit', partial(self.pos_to_unit, axis=lbl))
        super(CameraRoiScale, self).update_widgets()


class ArbitraryAxis(pyqtgraph.AxisItem):
    """
    Axis that retains it's underlying coordinates, while displaying different coordinates as ticks.
    It allows one to retain the sizes, shapes and location of widgets added on top the same independently of scaling
    (e.g. CrossHairs)
    """

    def __init__(self, *args, **kwargs):
        super(ArbitraryAxis, self).__init__(*args, **kwargs)

    def pos_to_unit(self, value):
        return value

    def tickStrings(self, values, scale, spacing):
        values = self.pos_to_unit(values)
        spacing = np.abs(np.diff(self.pos_to_unit([0, spacing])))
        try:
            returnval = super(ArbitraryAxis, self).tickStrings(values, scale, spacing)
        except TypeError:
            # pyqtgraph throws out a TypeError when there's no ticks. We ignore it
            returnval = []
        return returnval


class Crosshair(pyqtgraph.GraphicsObject):
    Released = QtCore.Signal()

    def __init__(self, color, size=5, *args):
        super(Crosshair, self).__init__(*args)
        self.color = color
        self._size = size

    def paint(self, p, *args):
        p.setPen(pyqtgraph.mkPen(self.color))
        p.drawLine(-self._size, 0, self._size, 0)
        p.drawLine(0, -self._size, 0, self._size)

    def boundingRect(self):
        """Makes a clickable rectangle around the center, which is half the size of the cross hair"""
        return QtCore.QRectF(-self._size, -self._size, 2*self._size, 2*self._size)

    def mouseDragEvent(self, ev):
        # Ensures the Crosshair always remains in the center of a pixel, which makes the ROI selection easier
        ev.accept()
        if ev.isStart():
            self.startPos = self.pos()
        elif ev.isFinish():
            rounded_pos = map(lambda x: int(x) + 0.5, self.pos())
            self.setPos(*rounded_pos)
        else:
            self.setPos(self.startPos + ev.pos() - ev.buttonDownPos())
        self.Released.emit()


class DisplayWidgetRoiScale(QtWidgets.QWidget, UiTools):
    _max_num_line_plots = 4
    update_data_signal = QtCore.Signal(np.ndarray)

    def __init__(self, scale=(1, 1), offset=(0, 0), units=("pxl", "pxl")):
        # QtWidgets.QWidget.__init__(self)
        super(DisplayWidgetRoiScale, self).__init__()
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'camera_controls_scaled.ui'), self)

        self.units = units
        self._pxl_scale = scale
        self._pxl_offset = offset
        self.binning = (1, 1)

        # Create a PlotItem in which the shown axis display coordinates that are offset and scaled, without changing the
        #  underlying coordinates
        self.splitter = QtWidgets.QSplitter()
        layout = self.layout()
        layout.addWidget(self.splitter, 0, 0, 1, 2)

        _item = pyqtgraph.PlotItem(axisItems=dict(bottom=ArbitraryAxis(orientation="bottom"),
                                                  left=ArbitraryAxis(orientation="left")))
        self.ImageDisplay = pyqtgraph.ImageView(view=_item)
        self.splitter.addWidget(self.ImageDisplay)

        self.LineDisplay = pyqtgraph.PlotWidget()
        self.LineDisplay.showGrid(x=True, y=True)
        self.splitter.addWidget(self.LineDisplay)
        self.splitter.setHandleWidth(10)
        self.ImageDisplay.getHistogramWidget().gradient.restoreState(Gradients.values()[1])
        self.ImageDisplay.imageItem.setTransform(QtGui.QTransform())

        self.plot = ()
        for ii in range(self._max_num_line_plots):
            self.plot += (self.LineDisplay.plot(pen=pyqtgraph.intColor(ii, self._max_num_line_plots)),)

        for idx, color in enumerate(['r', 'g']):
            crosshair = Crosshair(color)
            self.ImageDisplay.getView().addItem(crosshair)
            crosshair.Released.connect(self.mouseMoved)
            setattr(self, 'CrossHair%d' % (idx + 1), crosshair)

        self.checkbox_aspectratio.stateChanged.connect(self.fix_aspect_ratio)
        self.checkbox_tools.stateChanged.connect(self.show_tools)
        self.splitter.setSizes([1, 0])

    @property
    def autoRange(self):
        return self.checkbox_autorange.isChecked()
    @property
    def autoLevel(self):
        return self.checkbox_autolevel.isChecked()

    def _pos_to_unit(self, pos, axis):
        """This is overwritten in CameraScaledRoi.update_widgets, setting it to CameraScaledRoi.pos_to_unit"""
        return pos

    def pos_to_unit(self, pos):
        """Using the CameraScaledRoi.pos_to_unit for each of the axes"""
        x = self._pos_to_unit([pos[0]], 'bottom')[0]
        y = self._pos_to_unit([pos[1]], 'left')[0]

        return x, y

    def _rescale(self):
        """
        Applies the displays scale and offset to the scalable axis

        :return:
        """
        vw = self.ImageDisplay.getView()
        for idx, lbl in enumerate(["bottom", "left"]):
            ax = vw.axes[lbl]["item"]
            ax.offset = self._pxl_offset[idx]
            ax.setScale(self._pxl_scale[idx])
        self.mouseMoved()  # To update the pixel position display label

    def mouseMoved(self):
        """
        Displays the current position of the two cross-hairs, as well as the distance between them, in pixels and in
        units
        :return:
        """
        params = ()
        for idx in [1, 2]:
            xhair = getattr(self, "CrossHair%d" % idx)
            pos = tuple(xhair.pos())
            post = self.pos_to_unit(pos)
            params += tuple(map(lambda x, y: x * y, pos, self.binning))
            params += post + (self.units[idx-1], )

        diff = np.linalg.norm(np.array(params[:2]) - np.array(params[5:7]))
        if self.units[0] == self.units[1]:
            difft = np.linalg.norm(np.array(params[2:4]) - np.array(params[7:9]))
            unit = self.units[0]
        else:
            difft = -1
            unit = ''
        params += (diff, difft, unit, )

        self.labelCrossHairPositions.setText(
            "<span style='color: red'>Pixel: [%i,%i]px Unit: (%g, %g)%s</span>, " \
            "<span style='color: green'> Pixel: [%i,%i]px Unit: (%g, %g)%s</span>, " \
            "Delta pixel: %g px Delta Unit: %g %s"
            % params)

    def update_image(self, newimage):

        scale = self._pxl_scale
        offset = self._pxl_offset

        if len(newimage.shape) == 2:
            if newimage.shape[0] > self._max_num_line_plots:
                self.splitter.setSizes([1, 0])
                self.ImageDisplay.setImage(newimage.T,
                                           pos=tuple(map(operator.add, offset, (0, 0))),
                                           autoRange=self.autoRange,
                                           autoLevels=self.autoLevel,
                                           scale=(scale[0], scale[1]))
            else:
                self.splitter.setSizes([0, 1])
                for ii in range(newimage.shape[0]):
                    self.plot[ii].setData(x=0, y=newimage[ii])
        else:
            self.splitter.setSizes([1, 0])
            image = np.transpose(newimage, (0, 2, 1))
            zvals = 0.99 * np.linspace(0, image.shape[0] - 1, image.shape[0])
            if image.shape[0] == 1:
                image = image[0]
            self.ImageDisplay.setImage(image, xvals=zvals,
                                       pos=tuple(map(operator.add, offset, (0, 0))),
                                       autoRange=self.autoRange,
                                       autoLevels=self.autoLevel,
                                       scale=(scale[0], scale[1]))
        self.mouseMoved()

    def fix_aspect_ratio(self):
        boolean = self.checkbox_aspectratio.isChecked()
        self.ImageDisplay.getView().getViewBox().setAspectLocked(boolean, 1)

    def show_tools(self):
        boolean = self.checkbox_tools.isChecked()
        if boolean:
            self.ImageDisplay.getHistogramWidget().show()
            self.ImageDisplay.ui.roiBtn.show()
            self.ImageDisplay.ui.menuBtn.show()
        else:
            self.ImageDisplay.getHistogramWidget().hide()
            self.ImageDisplay.ui.roiBtn.hide()
            self.ImageDisplay.ui.menuBtn.hide()

    def get_roi(self):
        """
        Returns the cross hair positions
        :return:
        """
        assert hasattr(self, 'CrossHair1')
        assert hasattr(self, 'CrossHair2')

        pos1 = self.CrossHair1.pos()
        pos2 = self.CrossHair2.pos()
        if pos1 == pos2:
            return None

        minx, maxx = map(lambda x: int(x),
                         (min(pos1[0], pos2[0]), max(pos1[0], pos2[0])))
        miny, maxy = map(lambda x: int(x),
                         (min(pos1[1], pos2[1]), max(pos1[1], pos2[1])))

        return minx, maxx, miny, maxy



