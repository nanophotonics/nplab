# -*- coding: utf-8 -*-
"""
Subclass of Camera that has units for its axis. The GUI also provides crosshairs for defining ROIs
"""
from __future__ import print_function

from nplab.utils.gui import QtCore, QtGui, QtWidgets
from nplab.ui.widgets.imageview import ExtendedImageView
from builtins import zip
from builtins import range
from nplab.instrument.camera import Camera
import pyqtgraph
import numpy as np
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
            if lims is None: lims = (0,1,0,1)
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
                    widgt.crosshair_moved()

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


class DisplayWidgetRoiScale(ExtendedImageView):
    _max_num_line_plots = 4
    update_data_signal = QtCore.Signal(np.ndarray)

    def __init__(self, scale=(1, 1), offset=(0, 0)):
        super(DisplayWidgetRoiScale, self).__init__()

        self._pxl_scale = scale
        self._pxl_offset = offset

        self.LineDisplay = self.ui.roiPlot#creates a PlotWidget instance
        self.LineDisplay.showGrid(x=True, y=True)
        self.ui.splitter.setHandleWidth(10)
        self.getHistogramWidget().gradient.restoreState(list(Gradients.values())[1])
        self.imageItem.setTransform(QtGui.QTransform())
        self.LineDisplay.show()

        self.plot = ()
        for ii in range(self._max_num_line_plots):
            self.plot += (self.LineDisplay.plot(pen=pyqtgraph.intColor(ii, self._max_num_line_plots)),)

        self.toggle_displays()

        self.checkbox_autorange = QtWidgets.QCheckBox('Autorange')
        self.tools.gridLayout.addWidget(self.checkbox_autorange, 0, 3, 1, 1)

    @property
    def x_axis(self):
        """Convenience wrapper for integration with spectrometer code"""
        return self.axis_values['bottom']

    @x_axis.setter
    def x_axis(self, value):
        self.axis_values['bottom'] = value

    @property
    def y_axis(self):
        """Convenience wrapper for integration with spectrometer code"""
        return self.axis_values['left']

    @y_axis.setter
    def y_axis(self, value):
        self.axis_values['left'] = value

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

    def toggle_displays(self, boolean=False):
        """Toggle between an Image display and a Plot widget for Line displays

        :param boolean: if True, display lines. If False, display images
        :return:
        """
        if boolean:
            self.LineDisplay.show()
            self.LineDisplay.showAxis('left')
            self.LineDisplay.setMouseEnabled(True, True)
            self.ui.splitter.setSizes([0, self.height()-35, 35])
        else:
            self.ui.splitter.setSizes([self.height()-35, 0, 35])

    def update_image(self, newimage):
        scale = self._pxl_scale
        offset = self._pxl_offset

        if len(newimage.shape) == 1:
            self.toggle_displays(True)
            self.plot[0].setData(x=self.x_axis, y=newimage)
        elif len(newimage.shape) == 2:
            if newimage.shape[0] > self._max_num_line_plots:
                self.toggle_displays(False)
                # levels = [np.percentile(newimage, x) for x in self.levels()]
                self.setImage(newimage,
                              pos=offset,
                              autoRange=self.checkbox_autorange.isChecked(),
                              # levels=levels,
                              scale=scale)
            else:
                self.toggle_displays(True)
                for ii, ydata in enumerate(newimage):
                    self.plot[ii].setData(x=self.x_axis, y=ydata)
        elif len(newimage.shape) == 3:
            self.toggle_displays(False)
            zvals = 0.99 * np.linspace(0, newimage.shape[0] - 1, newimage.shape[0])
            if newimage.shape[0] == 1:
                newimage = newimage[0]
            # levels = [np.percentile(newimage, x) for x in self.levels()]
            self.setImage(newimage, xvals=zvals,
                          pos=offset,
                          autoRange=self.checkbox_autorange.isChecked(),
                          # levels=levels,
                          scale=scale)
        else:
            raise ValueError('Cannot display. Array shape unrecognised')
            

class DummyCameraRoiScale(CameraRoiScale):
    """A Dummy CameraRoiScale camera  """

    def __init__(self, data='spectrum'):
        super(DummyCameraRoiScale, self).__init__()
        self.data = data

    def raw_snapshot(self, update_latest_frame=True):
        """Returns a True, stating a succesful snapshot, followed by a (100,100)
        picture randomly generated image"""
        if self.data == 'spectrum':
            ran = 100 * ArrayWithAttrs(np.random.random(100))
        else:
            ran = 100 * np.random.random((1600, 200))
        self._latest_raw_frame = ran
        return True, ran

    def get_preview_widget(self):
        self._logger.debug('Getting preview widget')
        if self._preview_widgets is None:
            self._preview_widgets = WeakSet()
        new_widget = DisplayWidgetRoiScale()
        self._preview_widgets.add(new_widget)
        return new_widget

    @property
    def x_axis(self):
        return np.arange(100) + 1

    @x_axis.setter
    def x_axis(self, value):
        self.axis_values['bottom'] = value


if __name__ == '__main__':

    dcrd = DummyCameraRoiScale()
    dcrd.show_gui(blocking=False)
