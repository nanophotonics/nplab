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
from weakref import WeakSet
from nplab.utils.array_with_attrs import ArrayWithAttrs

class CameraRoiScale(Camera):
    """
    Camera with two main features:
        - Scaled axes with whatever units the user wants. Subclasses may overwrite the pos_to_unit method, or provide
        an array (x_axis or y_axis) as a lookup table.

        - ROI selection using crosshairs. Subclasses should overwrite the roi method, e.g. to set ROI in the camera hardware

    This class also handles binning, and keeps the scaled axes and ROI selection unaffected by the binning
    """
    def __init__(self, crosshair_origin='top_left'):
        super(CameraRoiScale, self).__init__()
        self.axis_values = dict(bottom=None, left=None, top=None, right=None)
        self.axis_units = dict(bottom=None, left=None, top=None, right=None)
        self._roi = (0, 1000, 0, 1000)
        self.detector_shape = (1000, 1000)
        self.crosshair_origin = crosshair_origin

    @property
    def x_axis(self):
        return self.axis_values['bottom']

    @x_axis.setter
    def x_axis(self, value):
        self.axis_values['bottom'] = value

    @property
    def y_axis(self):
        return self.axis_values['left']

    @y_axis.setter
    def y_axis(self, value):
        self.axis_values['left'] = value

    @property
    def roi(self):
        """
        If the camera supports setting a ROI in hardware, the user should overwrite this property

        :return: 4-tuple of integers. Pixel positions xmin, xmax, ymin, ymax
        """
        return self._roi

    @roi.setter
    def roi(self, value):
        """
        By default, setting a ROI will make a filter function that indexes the frame to the given ROI.

        :return: 4-tuple of integers. Pixel positions xmin, xmax, ymin, ymax
        """
        self._roi = value
        def fltr(img):
            return img[self._roi[2]:self._roi[3], self._roi[0]:self._roi[1]]
        setattr(self, 'filter_function', fltr)

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
        """
        The binning property is passed to the display widgets to keep the scaling and units constant, independent of
        binning.

        By default, it is assumed the camera does not support binning, so the property returns (1, 1) and has no setter.
        A subclass should overwrite this if the camera supports binnig
        :return:
        """
        return 1, 1

    def update_widgets(self):
        """
        Setting the position, scale, axis values and units, and crosshair sizes of the _preview_widgets
        :return:
        """
        if self._preview_widgets is not None:
            for widgt in self._preview_widgets:
                if isinstance(widgt, DisplayWidgetRoiScale):
                    # Set the position of the updated image
                    roi = self.roi
                    widgt._pxl_offset = (roi[0], roi[2])
                    # Set the scaling
                    widgt._pxl_scale = self.binning
                    # Set the axes values and units
                    widgt.axis_values = self.axis_values
                    widgt.axis_units = self.axis_units
                    widgt.x_axis = self.x_axis
                    widgt.y_axis = self.y_axis
                    if not self.live_view:  # not sure why it doesn't work in live view
                        widgt.update_axes()
                    widgt.mouseMoved()

                    # Resize the crosshairs, so that they are always 1/40th of the total size of the image, but never
                    # less than 5 pixels
                    size = max(((roi[1] - roi[0])/40., (roi[3]-roi[2])/40., 5))
                    for idx in [1, 2]:
                        xhair = getattr(widgt, 'CrossHair%d' % idx)
                        xhair._size = size
                        if self.crosshair_origin == 'top_left':
                            xhair._origin = [0, 0]
                        elif self.crosshair_origin == 'top_right':
                            xhair._origin = [self.detector_shape[0], 0]
                        elif self.crosshair_origin == 'bottom_left':
                            xhair._origin = [0, self.detector_shape[1]]
                        elif self.crosshair_origin == 'top_right':
                            xhair._origin = [self.detector_shape[0], self.detector_shape[1]]
                        else:
                            self._logger.info('Not recognised: crosshair_origin = %s. Needs to be top_left, top_right, '
                                              'bottom_left or bottom_right' % self.crosshair_origin)
                        xhair.update()

        super(CameraRoiScale, self).update_widgets()


class ArbitraryAxis(pyqtgraph.AxisItem):
    """
    Axis that retains it's underlying coordinates, while displaying different coordinates as ticks.
    It allows one to retain the sizes, shapes and location of widgets added on top the same independently of scaling
    (e.g. CrossHairs)
    """

    def __init__(self, *args, **kwargs):
        super(ArbitraryAxis, self).__init__(*args, **kwargs)
        self.axis_values = None

    def pos_to_unit(self, value):
        def get_value(index):
            """Function that extracts the value from a list (axis_vectors) according to some given position (index),
            returning NaN if the index is out of range"""
            if int(index) < 0 or int(index) > len(self.axis_values):
                return np.nan
            else:
                return self.axis_values[int(index)]

        if self.axis_values is None:
            func = int
        else:
            func = get_value

        if not hasattr(value, '__iter__'):
            return func(value)
        else:
            return map(func, value)

    def tickStrings(self, values, scale, spacing):
        try:
            values = self.pos_to_unit(values)
            spacing = np.abs(np.diff(self.pos_to_unit([0, spacing]))[0])
            spacing += 0.001
            returnval = super(ArbitraryAxis, self).tickStrings(values, scale, spacing)
        except Exception as e:
            # pyqtgraph throws out a TypeError/RuntimeWarning when there's no ticks. We ignore it
            returnval = [''] * len(values)
            print e
        return returnval


class Crosshair(pyqtgraph.GraphicsObject):
    Released = QtCore.Signal()

    def __init__(self, color, size=5, *args):
        super(Crosshair, self).__init__(*args)
        self.color = color
        self._size = size
        self._origin = [0, 0]

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

    def referenced_pos(self):
        pos = self.pos()
        return [np.abs(pos[x] - self._origin[x]) for x in [0, 1]]


class DisplayWidgetRoiScale(QtWidgets.QWidget, UiTools):
    _max_num_line_plots = 4
    update_data_signal = QtCore.Signal(np.ndarray)

    def __init__(self, scale=(1, 1), offset=(0, 0)):
        """TODO: have the checkboxes in a splitter, so they can be taken out of the way"""
        self.axis_values = dict(bottom=None, left=None, top=None, right=None)
        self.axis_units = dict(bottom=None, left=None, top=None, right=None)

        super(DisplayWidgetRoiScale, self).__init__()
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'camera_display_scaled.ui'), self)

        self._pxl_scale = scale
        self._pxl_offset = offset

        # Create a PlotItem in which the shown axis display coordinates that are offset and scaled, without changing the
        # underlying coordinates
        self.splitter = QtWidgets.QSplitter()
        layout = self.layout()
        layout.addWidget(self.splitter, 0, 0, 1, 1)

        _item = pyqtgraph.PlotItem(axisItems=dict(bottom=ArbitraryAxis(orientation="bottom"),
                                                  left=ArbitraryAxis(orientation="left"),
                                                  top=ArbitraryAxis(orientation="top"),
                                                  right=ArbitraryAxis(orientation="right")))
        self.ImageDisplay = pyqtgraph.ImageView(view=_item)
        self.ImageDisplay.imageItem.axisOrder = 'row-major'
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
        self.checkbox_axes.stateChanged.connect(self.hide_axes)
        self.checkbox_autolevel.stateChanged.connect(self.autoLevel)
        self.splitter.setSizes([1, 0])
        self.hide_axes()

    @property
    def x_axis(self):
        return self.axis_values['bottom']

    @x_axis.setter
    def x_axis(self, value):
        self.axis_values['bottom'] = value

    @property
    def y_axis(self):
        return self.axis_values['left']

    @y_axis.setter
    def y_axis(self, value):
        self.axis_values['left'] = value

    def get_axes(self):
        """Returns the pyqtgraph AxisItems"""
        axes_dict = self.ImageDisplay.getView().axes
        names = ["bottom", "left", "top", "right"]  # Ensures its always in the same order
        axs = [axes_dict[name]['item'] for name in names]
        return axs

    def update_axes(self):
        gui_axes = self.get_axes()
        for ax, name in zip(gui_axes, ["bottom", "left", "top", "right"]):
            if self.axis_values[name] is not None:
                setattr(ax, 'axis_values', self.axis_values[name])
            if self.axis_units[name] is not None:
                ax.setLabel(self.axis_units[name])

        # This is kept in case subclasses overwrite the x_axis or y_axis properties
        for ax, value in zip(gui_axes[:2], [self.x_axis, self.y_axis]):
            if value is not None:
                setattr(ax, 'axis_values', value)

    @property
    def autoRange(self):
        return self.checkbox_autorange.isChecked()

    def autoLevel(self):
        if self.checkbox_autolevel.isChecked():
            self.lineEdit_minLevel.setText('0')
            self.lineEdit_maxLevel.setText('100')
            self.lineEdit_minLevel.setReadOnly(True)
            self.lineEdit_maxLevel.setReadOnly(True)
        else:
            self.lineEdit_minLevel.setReadOnly(False)
            self.lineEdit_maxLevel.setReadOnly(False)

    def levels(self):
        min_level = float(self.lineEdit_minLevel.text())
        max_level = float(self.lineEdit_maxLevel.text())
        return min_level, max_level

    def pos_to_unit(self, positions):
        """
        Given an iterable of positions (bottom, left, top, right) returns the scaled values on those axes

        :param positions: 2- or 4-tuple of floats.
        :return:
        """
        axs = self.get_axes()
        units = ()
        # If only 2-tuple given, it corresponds to (bottom, left) axes
        if len(positions) == 2:
            axs = axs[:2]
        for ax, pos in zip(axs, positions):
            if hasattr(ax, 'pos_to_unit'):
                units += (ax.pos_to_unit(pos), )
            else:
                units += (pos, )

        return units

    def mouseMoved(self):
        """
        Displays the current position of the two cross-hairs, as well as the distance between them, in pixels and in
        units (when given)
        :return:
        """
        try:
            # First gets the crosshair positions, and finds the distance between them
            positions = ()
            for idx in [1, 2]:
                xhair = getattr(self, "CrossHair%d" % idx)
                pos = tuple(xhair.referenced_pos())
                positions += pos
            diff = np.linalg.norm(np.array(positions[:2]) - np.array(positions[2:]))
            positions += (diff, )

            display_string = u"Pixels: <span style='color: red'>[%i,%i] </span> " \
                             u"<span style='color: green'> [%i,%i] </span> " \
                             u"\u0394px=%g" % positions

            # If any units are given, get the positions and scale them using pos_to_unit
            if any(map(lambda x: self.axis_units[x] is not None, ['bottom', 'left'])):
                scaled_positions = ()
                for idx in [1, 2]:
                    xhair = getattr(self, "CrossHair%d" % idx)
                    pos = tuple(xhair.referenced_pos())
                    scaled_positions += self.pos_to_unit(pos)
                units = ()
                for ax in ['bottom', 'left']:
                    if self.axis_units[ax] is None:
                        units += ('px', )
                    else:
                        units += (self.axis_units[ax],)
                display_string += u"\t(%s, %s):" \
                                  u"<span style='color: red'> (%g, %g)</span> " \
                                  u"<span style='color: green'> (%g, %g)</span> " % (units + scaled_positions)

                # If the bottom and left axis have the same units, display the distance between the crosshairs
                if self.axis_units['bottom'] == self.axis_units['left']:
                    difft = np.linalg.norm(np.array(scaled_positions[:2]) - np.array(scaled_positions[2:]))
                    unit = self.axis_units['bottom']
                    display_string += u"\u0394%s=%g" % (unit, difft)

            self.label_crosshairpos.setText(display_string)
        except Exception:
            print 'Failed updating mouse'

    def update_image(self, newimage):
        scale = self._pxl_scale
        offset = self._pxl_offset

        if len(newimage.shape) == 1:
            self.splitter.setSizes([0, 1])
            self.plot[0].setData(x=self.x_axis, y=newimage)
        elif len(newimage.shape) == 2:
            if newimage.shape[0] > self._max_num_line_plots:
                self.splitter.setSizes([1, 0])
                levels = map(lambda x: np.percentile(newimage, x), self.levels())
                self.ImageDisplay.setImage(newimage,
                                           pos=offset,
                                           autoRange=self.autoRange,
                                           levels=levels,
                                           scale=scale)
            else:
                self.splitter.setSizes([0, 1])
                for ii in range(newimage.shape[0]):
                    self.plot[ii].setData(x=0, y=newimage[ii])
        elif len(newimage.shape) == 3:
            self.splitter.setSizes([1, 0])
            zvals = 0.99 * np.linspace(0, newimage.shape[0] - 1, newimage.shape[0])
            if newimage.shape[0] == 1:
                newimage = newimage[0]
            levels = map(lambda x: np.percentile(newimage, x), self.levels())
            self.ImageDisplay.setImage(newimage, xvals=zvals,
                                       pos=offset,
                                       autoRange=self.autoRange,
                                       levels=levels,
                                       scale=scale)
        else:
            raise ValueError('Cannot display. Array shape unrecognised')

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

    def hide_axes(self):
        boolean = self.checkbox_axes.isChecked()
        if boolean:
            for ax in self.get_axes():
                ax.hide()
        else:
            for ax in self.get_axes():
                ax.show()

    def get_roi(self):
        """
        Returns the cross hair positions
        :return:
        """
        assert hasattr(self, 'CrossHair1')
        assert hasattr(self, 'CrossHair2')

        pos1 = self.CrossHair1.referenced_pos()
        pos2 = self.CrossHair2.referenced_pos()
        if pos1 == pos2:
            return None

        minx, maxx = map(lambda x: int(x),
                         (min(pos1[0], pos2[0]), max(pos1[0], pos2[0])))
        miny, maxy = map(lambda x: int(x),
                         (min(pos1[1], pos2[1]), max(pos1[1], pos2[1])))

        return minx, maxx, miny, maxy

class DummyCameraRoiScale(CameraRoiScale):
    """A version of the Camera code  """
    def __init__(self, data = 'spectrum'):
        super(DummyCameraRoiScale, self).__init__()
        self.data = data
    def raw_snapshot(self, update_latest_frame = True):
        """Returns a True, stating a succesful snapshot, followed by a (100,100)
        picture randomly generated image"""
        if self.data == 'spectrum':
            ran = 100*ArrayWithAttrs(np.random.random(100))
            ran.attrs['x-axis'] = np.arange(100)
        else:
            ran = 100*np.random.random((100,100))
        self._latest_raw_frame = ran
        return True, ran
    def get_preview_widget(self):
        self._logger.debug('Getting preview widget')
        if self._preview_widgets is None:
            self._preview_widgets = WeakSet()
        new_widget = DisplayWidgetRoiScale()
        self._preview_widgets.add(new_widget)
        return new_widget   
    

if __name__ == '__main__':
    dcrd =  DummyCameraRoiScale()
    dcrd.show_gui(blocking = False)

