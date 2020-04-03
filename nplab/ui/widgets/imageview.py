# -*- coding: utf-8 -*-
from __future__ import print_function
from builtins import zip
from builtins import map
from nplab.utils.gui import QtCore, QtWidgets, uic
import pyqtgraph as pg
import numpy as np
import os.path


class ArbitraryAxis(pg.AxisItem):
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
            return list(map(func, value))

    def tickStrings(self, values, scale, spacing):
        try:
            values = self.pos_to_unit(values)
            spacing = np.abs(np.diff(self.pos_to_unit([0, spacing]))[0])
            spacing += 0.001
            returnval = super(ArbitraryAxis, self).tickStrings(values, scale, spacing)
        except Exception as e:
            # pg throws out a TypeError/RuntimeWarning when there's no ticks. We ignore it
            returnval = [''] * len(values)
            print(e)
        return returnval


class Crosshair(pg.GraphicsObject):
    Released = QtCore.Signal()

    def __init__(self, color, size=5, *args):
        super(Crosshair, self).__init__(*args)
        self.color = color
        self._size = size
        self._origin = [0, 0]

    def paint(self, p, *args):
        p.setPen(pg.mkPen(self.color))
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
            rounded_pos = [int(x) + 0.5 for x in self.pos()]
            self.setPos(*rounded_pos)
        else:
            self.setPos(self.startPos + ev.pos() - ev.buttonDownPos())
        self.Released.emit()

    def referenced_pos(self):
        pos = self.pos()
        return [np.abs(pos[x] - self._origin[x]) for x in [0, 1]]


class ExtendedImageView(pg.ImageView):
    """
    Extension of the pg ImageView so that it's possible to put percentile levels instead of playing around with
    the histogram. Also adds the possibility of normalising each image when given a 3D array, instead of normalising to
    the maximum of the whole array.

    # TODO: link the histogram region with the lineedit levels
    """
    def __init__(self, *args, **kwargs):
        self.axis_values = dict(bottom=None, left=None, top=None, right=None)
        self.axis_units = dict(bottom=None, left=None, top=None, right=None)
        kwargs['view'] = pg.PlotItem(axisItems=dict(bottom=ArbitraryAxis(orientation="bottom"),
                                                    left=ArbitraryAxis(orientation="left"),
                                                    top=ArbitraryAxis(orientation="top"),
                                                    right=ArbitraryAxis(orientation="right")))
        super(ExtendedImageView, self).__init__(*args, **kwargs)
        self.imageItem.axisOrder = 'row-major'

        # Setting up the autoleveling GUI
        self.level_percentiles = [0, 100]
        self.levelGroup = uic.loadUi(os.path.join(os.path.dirname(__file__), 'autolevel.ui'))
        self.ui.gridLayout_3.addWidget(self.levelGroup, 2, 0, 1, 1)
        self.levelGroup.setVisible(False)

        self.levelGroup.checkbox_singleimagelevel.stateChanged.connect(self.set_level_percentiles)
        self.levelGroup.lineEdit_minLevel.returnPressed.connect(self.set_level_percentiles)
        self.levelGroup.lineEdit_maxLevel.returnPressed.connect(self.set_level_percentiles)
        self.levelGroup.pushButton_reset.pressed.connect(self.reset)

        # Setting up the additional tools GUI
        self.tools = uic.loadUi(os.path.join(os.path.dirname(__file__), 'imageview_tools.ui'))
        self.ui.splitter.addWidget(self.tools)
        self.tools.checkbox_tools.stateChanged.connect(self.show_tools)
        self.tools.checkbox_aspectratio.stateChanged.connect(
            lambda: self.view.setAspectLocked(self.tools.checkbox_aspectratio.isChecked()))
        self.tools.checkbox_axes.stateChanged.connect(self.hide_axes)

        # Setting up the crosshairs
        for idx, color in enumerate(['r', 'g']):
            crosshair = Crosshair(color)
            self.getView().addItem(crosshair)
            crosshair.Released.connect(self.crosshair_moved)
            setattr(self, 'CrossHair%d' % (idx + 1), crosshair)
        self.label_crosshairpos = QtWidgets.QLabel()
        self.ui.gridLayout.addWidget(self.label_crosshairpos, 2, 0, 1, 3)
        self.label_crosshairpos.hide()
        self.crosshair_moved()

    def show_tools(self):
        boolean = self.tools.checkbox_tools.isChecked()
        if boolean:
            self.getHistogramWidget().show()
            self.ui.roiBtn.show()
            self.ui.menuBtn.show()
        else:
            self.getHistogramWidget().hide()
            self.ui.roiBtn.hide()
            self.ui.menuBtn.hide()

    def roiClicked(self):
        """Ensures that the new widget in the splitter is displayed"""
        super(ExtendedImageView, self).roiClicked()
        if self.hasTimeAxis() and not self.ui.roiBtn.isChecked():
            self.ui.splitter.setSizes([self.height()-70, 35, 35])

    def buildMenu(self):
        """Adds an action to the existing pg.ImageView menu to toggle the visibility of the new GUI"""
        super(ExtendedImageView, self).buildMenu()
        # Percentiles
        self.levelAction = QtWidgets.QAction("Autolevel", self.menu)
        self.levelAction.setCheckable(True)
        self.levelAction.toggled.connect(lambda boolean: self.levelGroup.setVisible(boolean))
        self.menu.addAction(self.levelAction)
        # Crosshair label
        self.labelAction = QtWidgets.QAction("Crosshair label", self.menu)
        self.labelAction.setCheckable(True)
        self.labelAction.toggled.connect(lambda boolean: self.label_crosshairpos.setVisible(boolean))
        self.menu.addAction(self.labelAction)

    # Scaled axis functions
    def get_axes(self):
        """Returns the AxisItems"""
        axes_dict = self.getView().axes
        names = ["bottom", "left", "top", "right"]  # Ensures its always in the same order
        axs = [axes_dict[name]['item'] for name in names]
        return axs

    def hide_axes(self):
        boolean = self.tools.checkbox_axes.isChecked()
        if boolean:
            for ax in self.get_axes():
                ax.hide()
        else:
            for ax in self.get_axes():
                ax.show()

    # Percentile functions
    def getProcessedImage(self):
        """Checks if we want to autolevel for each image and does it"""
        image = super().getProcessedImage()
        if self.levelGroup.checkbox_singleimagelevel.isChecked() and self.hasTimeAxis():
            cur_image = image[self.currentIndex]
            self.levelMin, self.levelMax = self.quickMinMax(cur_image)
            self.autoLevels()  # sets the histogram setLevels(self.levelMin, self.levelMax)
        return image

    def set_level_percentiles(self):
        """
        Reads the GUI lineEdits and sets the level percentiles. If not normalising each image, it also finds the levels
        and sets them
        :return:
        """
        min_level = float(self.levelGroup.lineEdit_minLevel.text())
        max_level = float(self.levelGroup.lineEdit_maxLevel.text())

        self.level_percentiles = [min_level, max_level]
        if not self.levelGroup.checkbox_singleimagelevel.isChecked():
            image = self.getProcessedImage()
            self.levelMin, self.levelMax = self.quickMinMax(image)
            self.autoLevels()
        self.updateImage()

    def reset(self):
        self.levelGroup.lineEdit_minLevel.setText('0')
        self.levelGroup.lineEdit_maxLevel.setText('100')
        self.set_level_percentiles()

    def quickMinMax(self, data):
        """Reimplements the ImageView.quickMinMax to set level percentiles

        :param data:
        :return:
        """
        minval, maxval = super(ExtendedImageView, self).quickMinMax(data)
        rng = maxval - minval
        levelmin = minval + rng * self.level_percentiles[0] / 100.
        levelmax = minval + rng * self.level_percentiles[1] / 100.

        return levelmin, levelmax

    # Crosshairs
    def pos_to_unit(self, positions):
        """
        Given an iterable of positions, iterates over them and returns the scaled values along the corresponding axis.
        Uses the ArbitraryAxis.pos_to_unit method

        :param positions: 2- or 4-tuple of floats. If two values given, assumed it corresponds to the (bottom, left)
        axis, if four values the order should be (bottom, left, top, right) as given by self.get_axes()
        :return:
        """
        axs = self.get_axes()
        units = ()

        if len(positions) == 2:
            axs = axs[:2]
        for ax, pos in zip(axs, positions):
            if hasattr(ax, 'pos_to_unit'):
                units += (ax.pos_to_unit(pos), )
            else:
                units += (pos, )

        return units

    def crosshair_moved(self):
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

            display_string = "Pixels: <span style='color: red'>[%i,%i] </span> " \
                             "<span style='color: green'> [%i,%i] </span> " \
                             u"\u0394px=%g" % positions

            # If any units are given, get the positions and scale them using pos_to_unit
            if any([self.axis_units[x] is not None for x in ['bottom', 'left']]):
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
                display_string += "\t(%s, %s):" \
                                  "<span style='color: red'> (%g, %g)</span> " \
                                  "<span style='color: green'> (%g, %g)</span> " % (units + scaled_positions)

                # If the bottom and left axis have the same units, display the distance between the crosshairs
                if self.axis_units['bottom'] == self.axis_units['left']:
                    difft = np.linalg.norm(np.array(scaled_positions[:2]) - np.array(scaled_positions[2:]))
                    unit = self.axis_units['bottom']
                    display_string += u"\u0394%s=%g" % (unit, difft)

            self.label_crosshairpos.setText(display_string)
        except Exception as e:
            print('Failed updating crosshair position: %s' % e)

    def get_roi(self):
        """
        Pixel positions of the edges of the rectangle bound by the crosshairs
        :return: 4-tuple of integers. left, right, top, and bottom edges
        """
        assert hasattr(self, 'CrossHair1')
        assert hasattr(self, 'CrossHair2')

        pos1 = self.CrossHair1.referenced_pos()
        pos2 = self.CrossHair2.referenced_pos()
        if pos1 == pos2:
            return None

        min_x, max_x = [int(x) for x in (min(pos1[0], pos2[0]), max(pos1[0], pos2[0]))]
        min_y, max_y = [int(x) for x in (min(pos1[1], pos2[1]), max(pos1[1], pos2[1]))]

        return min_x, max_x, min_y, max_y


def test():
    from nplab.utils.gui import get_qt_app
    app = get_qt_app()
    ui = ExtendedImageView()
    data = []
    for ii, dum in enumerate(np.random.random((10, 50, 50))):
        data += [dum + ii]
    data = np.array(data)
    ui.setImage(data)
    ui.show()
    app.exec_()


if __name__ == "__main__":
    test()

