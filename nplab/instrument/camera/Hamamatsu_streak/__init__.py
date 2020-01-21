# -*- coding: utf-8 -*-

from builtins import str
from nplab.utils.gui import QtWidgets, QtCore, uic
from nplab.instrument.camera.camera_scaled_roi import DisplayWidgetRoiScale, CameraRoiScale
from nplab.instrument.camera.Hamamatsu_streak.streak_sdk import StreakSdk, StreakError
from weakref import WeakSet
import os


class Streak(StreakSdk, CameraRoiScale):
    def __init__(self, *args, **kwargs):
        super(Streak, self).__init__(*args, **kwargs)

    def get_control_widget(self):
        return StreakUI(self)

    def get_preview_widget(self):
        self._logger.debug('Getting preview widget')
        if self._preview_widgets is None:
            self._preview_widgets = WeakSet()
        new_widget = DisplayWidgetRoiScale()
        self._preview_widgets.add(new_widget)
        return new_widget

    def raw_snapshot(self):
        try:
            image = self.capture()
            return True, self.bundle_metadata(image)
        except Exception as e:
            self._logger.warn("Couldn't Capture because %s" % e)


class StreakUI(QtWidgets.QWidget):
    ImageUpdated = QtCore.Signal()

    def __init__(self, streak):
        super(StreakUI, self).__init__()

        self.Streak = streak
        uic.loadUi((os.path.dirname(__file__) + '/Streak.ui'), self)

        self.comboBoxGateMode.activated.connect(self.gate_mode)
        self.comboBoxReadMode.activated.connect(self.read_mode)
        self.comboBoxShutter.activated.connect(self.shutter)
        self.comboBoxTrigMode.activated.connect(self.trigger)
        self.spinBox_MCPGain.valueChanged.connect(self.mcp_gain)
        self.lineEditTimeRange.returnPressed.connect(self.time_range)
        self.comboBoxTimeUnit.activated.connect(self.time_range)
        self.pushButtonLess.clicked.connect(lambda: self.time_range('-'))
        self.pushButtonMore.clicked.connect(lambda: self.time_range('+'))

        self.pushButtonCapture.clicked.connect(lambda: self.Streak.raw_image(update_latest_frame=True))

    def gate_mode(self):
        mode = str(self.comboBoxGateMode.currentText())
        self.Streak.set_parameter('Devices', 'TD', 'Gate Mode', mode)

    def read_mode(self):
        mode = str(self.comboBoxReadMode.currentText())
        self.Streak.set_parameter('Devices', 'TD', 'Mode', mode)

    def shutter(self):
        mode = str(self.comboBoxShutter.currentText())
        self.Streak.set_parameter('Devices', 'TD', 'Shutter', mode)

    def trigger(self):
        mode = str(self.comboBoxTrigMode.currentText())
        self.Streak.set_parameter('Devices', 'TD', 'Trig. Mode', mode)

    def mcp_gain(self):
        gain = int(self.spinBox_MCPGain.value())
        self.Streak.set_parameter('Devices', 'TD', 'MCP Gain', gain)

    def time_range(self, direction=None):
        allowed_times = {'ns': [5, 10, 20, 50, 100, 200, 500],
                         'us': [1, 2, 5, 10, 20, 50, 100, 200, 500],
                         'ms': [1]}
        unit = str(self.comboBoxTimeUnit.currentText())
        given_number = int(self.lineEditTimeRange.text())

        if direction is '+':
            if not (unit == 'ms' and given_number == 1):
                next_unit = str(unit)
                if given_number != 500:
                    next_number = allowed_times[unit][allowed_times[unit].index(given_number) + 1]
                else:
                    next_number = 1
                    if unit == 'ns':
                        self.comboBoxTimeUnit.setCurrentIndex(1)
                        next_unit = 'us'
                    elif unit == 'us':
                        self.comboBoxTimeUnit.setCurrentIndex(2)
                        next_unit = 'ms'
                self.lineEditTimeRange.setText(str(next_number))
                unit = str(next_unit)
            else:
                self.Streak._logger.info('Tried increasing the maximum time range')
                return
        elif direction is '-':
            if not (unit == 'ns' and given_number == 5):
                next_unit = str(unit)
                if given_number != 1:
                    next_number = allowed_times[unit][allowed_times[unit].index(given_number) - 1]
                else:
                    next_number = 500
                    if unit == 'ms':
                        self.comboBoxTimeUnit.setCurrentIndex(1)
                        next_unit = 'us'
                    elif unit == 'us':
                        self.comboBoxTimeUnit.setCurrentIndex(0)
                        next_unit = 'ns'
                self.lineEditTimeRange.setText(str(next_number))
                unit = str(next_unit)
            else:
                self.Streak._logger.info('Tried decreasing the minimum time range')
                return
        else:
            next_number = min(allowed_times[unit], key=lambda x: abs(x - given_number))
            self.lineEditTimeRange.setText(str(next_number))

        # Some camera models don't give you direct access to the time range, but rather you preset a finite number of
        # settings that you then switch between
        try:
            self.Streak.set_parameter('Devices', 'TD', 'Time Range', str(next_number) + ' ' + unit)
        except StreakError:
            self.Streak.set_parameter('Devices', 'TD', 'Time Range', str(next_number))
