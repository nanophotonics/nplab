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
    def __init__(self):
        super(CameraRoiScale, self).__init__()

    def pos_to_unit(self, pos, axis):
        """
        Returns a position in the appropriate units given by _pxl_scale and _pxl_offset.
        :param pos: QPoint
        :return:
        """
        if axis == 'bottom':
            return map(lambda x: 0.1*x, pos)
        elif axis == 'left':
            return map(lambda x: x, pos)
        else:
            raise ValueError

    @property
    def roi(self):
        return (0, 0, 1, 1)

    @property
    def gui_roi(self):
        assert len(self._preview_widgets) == 1
        for wdg in self._preview_widgets:
            lims = wdg.get_roi()
        return lims

    @property
    def binning(self):
        return (1, 1)

    @binning.setter
    def binning(self, value):
        return

    def axes(self, axis):
        roi = self.roi
        if axis == 'x':
            return self.pos_to_unit(np.arange(roi[0], roi[1]), 'bottom')
        elif axis == 'y':
            return self.pos_to_unit(np.arange(roi[2], roi[3]), 'left')

    def update_widgets(self):
        for widgt in self._preview_widgets:
            roi = self.roi
            widgt._pxl_offset = (roi[0], roi[2])
            widgt._pxl_scale = self.binning
            # size = min(((roi[1] - roi[0])/10, (roi[3]-roi[2])/10))
            # widgt.CrossHair1.update()
            # widgt.CrossHair2.update()

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
        return super(ArbitraryAxis, self).tickStrings(values, scale, spacing)
        # if self.logMode:
        #     return self.logTickStrings(values, scale, spacing)
        #
        # places = max(0, np.ceil(-np.log10(spacing * scale)))
        # strings = []
        # for v in values:
        #     vs = v * scale + self.offset  # This is the only difference from the pure pyqtgraph implementation
        #     if abs(vs) < .001 or abs(vs) >= 10000:
        #         vstr = "%g" % vs
        #     else:
        #         vstr = ("%%0.%df" % places) % vs
        #     strings.append(vstr)
        # return strings


class Crosshair(pyqtgraph.GraphicsObject):
    CrossHairMoved = QtCore.Signal()
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
        return QtCore.QRectF(-self._size, -self._size, 2*self._size, 2*self._size)

    def mouseDragEvent(self, ev):
        ev.accept()
        if ev.isStart():
            self.startPos = self.pos()
        elif ev.isFinish():
            rounded_pos = map(int, self.pos())
            self.setPos(*rounded_pos)
        else:
            self.setPos(self.startPos + ev.pos() - ev.buttonDownPos())
        self.CrossHairMoved.emit()


class DisplayWidgetRoiScale(QtWidgets.QWidget, UiTools):
    _max_num_line_plots = 4
    update_data_signal = QtCore.Signal(np.ndarray)

    def __init__(self, scale=(1, 1), offset=(0, 0), unit="pxl"):
        QtWidgets.QWidget.__init__(self)

        uic.loadUi(os.path.join(os.path.dirname(__file__), 'CameraDefaultDisplay.ui'), self)

        # Create a PlotItem in which the shown axis display coordinates that are offset and scaled, without changing the
        #  underlying coordinates
        _item = pyqtgraph.PlotItem(axisItems=dict(bottom=ArbitraryAxis(orientation="bottom"),
                                                  left=ArbitraryAxis(orientation="left")))
        _view = pyqtgraph.ImageView(view=_item)
        self.ImageDisplay = self.replace_widget(self.imagelayout, self.ImageDisplay, _view)
        self.ImageDisplay.view.setAspectLocked(False)
        self.ImageDisplay.getHistogramWidget().gradient.restoreState(Gradients.values()[1])
        self.labelCrossHairPositions = QtWidgets.QLabel()
        self.imagelayout.addWidget(self.labelCrossHairPositions)
        self.ImageDisplay.imageItem.setTransform(QtGui.QTransform())

        self.plot = ()
        for ii in range(self._max_num_line_plots):
            self.plot += (self.LineDisplay.plot(pen=pyqtgraph.intColor(ii, self._max_num_line_plots)),)

        self.CrossHair1 = Crosshair('r')
        self.CrossHair2 = Crosshair('g')
        self.ImageDisplay.getView().addItem(self.CrossHair1)
        self.ImageDisplay.getView().addItem(self.CrossHair2)

        self.LineDisplay.showGrid(x=True, y=True)

        self.CrossHair1.CrossHairMoved.connect(self.mouseMoved)
        self.CrossHair2.CrossHairMoved.connect(self.mouseMoved)

        self.unit = unit
        self._pxl_scale = scale
        self._pxl_offset = offset
        self.binning = (1, 1)
        self.splitter.setSizes([1, 0])

        self.autoRange = False
        self.autoLevel = True

    def ccdpxl_to_unit(self, pxl):
        return pxl

    def guipxl_to_ccdpxl(self, pos):
        """
        Returns a position in the appropriate units given by _pxl_scale and _pxl_offset.
        :param pos: QPoint
        :return:
        """
        tr = QtGui.QTransform()
        # Order is important!
        tr.translate(*self._pxl_offset)
        tr.scale(*self._pxl_scale)

        return tuple(tr.map(*pos))

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
            post = self.guipxl_to_ccdpxl(pos)
            params += tuple(map(lambda x, y: x * y, pos, self.binning))
            params += post + (self.unit, )

        diff = np.linalg.norm(np.array(params[:2]) - np.array(params[5:7]))
        difft = np.linalg.norm(np.array(params[2:4]) - np.array(params[7:9]))
        params += (diff, difft, self.unit, )

        self.labelCrossHairPositions.setText(
            "<span style='color: red'>Pixel: [%i,%i]px Unit: (%g, %g)%s</span>, " \
            "<span style='color: green'> Pixel: [%i,%i]px Unit: (%g, %g)%s</span>, " \
            "Delta pixel: %g px Delta Unit: %g %s"
            % params)
        # self.labelCrossHairPositions.setText(
        #     "<span style='color: red'>Pixel: [%i,%i]px Unit: (%g, %g)%s</span>, " \
        #     "<span style='color: green'> Pixel: [%i,%i]px Unit: (%g, %g)%s</span>, " \
        #     "Delta pixel: [%i,%i]px Delta Unit: (%g, %g)%s"
        #     % (x1, y1, xu1, yu1, self.unit, x2, y2, xu2, yu2, self.unit, abs(x1 - x2), abs(y1 - y2), abs(xu1 - xu2),
        #        abs(yu1 - yu2), self.unit))

    def update_image(self, newimage):

        scale = self._pxl_scale
        offset = self._pxl_offset

        if len(newimage.shape) == 2:
            if newimage.shape[0] > self._max_num_line_plots:
                self.splitter.setSizes([1, 0])
                self.ImageDisplay.setImage(newimage.T, pos=tuple(map(operator.add, offset, (0, 0))),
                                           autoRange=self.autoRange, scale=(scale[0], scale[1]))
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
                                       scale=(scale[0], scale[1]),
                                       autoLevels=self.autoLevel)

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

        return minx, maxx - 1, miny, maxy - 1



