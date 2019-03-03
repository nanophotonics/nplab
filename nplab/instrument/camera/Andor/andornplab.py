# -*- coding: utf-8 -*-

from nplab.utils.gui import QtWidgets, QtCore, uic, QtGui
from nplab.instrument.camera.camera_scaled_roi import CameraRoiScale, DisplayWidgetRoiScale
from nplab.instrument.camera.Andor.andor_sdk import AndorBase
from nplab.utils.notified_property import NotifiedProperty
import nplab.datafile as df
from nplab.utils.notified_property import register_for_property_changes

import os
import numpy as np
from nplab.ui.ui_tools import UiTools
from weakref import WeakSet


class Andor(CameraRoiScale, AndorBase):

    def __init__(self, settings_filepath=None, **kwargs):
        # Camera.__init__(self)
        AndorBase.__init__(self)
        CameraRoiScale.__init__(self)

        # self.wvl_to_pxl = kwargs['wvl_to_pxl']
        # self.magnification = kwargs['magnification']
        # self.pxl_size = kwargs['pxl_size']

        self.CurImage = None
        self.background = None
        self.backgrounded = False
        self.unit_scale = [1, 1]  # for x and y axis
        self.unit_offset = [0, 0]

        if settings_filepath != None:
            self.load_params_from_file(settings_filepath)
        self.isAborted = False

    def __del__(self):
        # Need to explicitly call this method so that the shutdown procedure is followed correctly
        AndorBase.__del__(self)

    '''Used functions'''

    def raw_snapshot(self):
        try:
            imageArray, num_of_images, image_shape = self.capture()

            # The image is reversed depending on whether you read in the conventional CCD register or the EM register,
            # so we reverse it back
            if self._parameters['OutAmp']:
                reshaped = np.reshape(imageArray, (num_of_images,) + image_shape)[..., ::-1]
            else:
                reshaped = np.reshape(imageArray, (num_of_images,) + image_shape)
            if num_of_images == 1:
                reshaped = reshaped[0]
            self.CurImage = self.bundle_metadata(reshaped)
            return True, self.CurImage
        except Exception as e:
            self._logger.warn("Couldn't Capture because %s" % e)

    def get_camera_parameter(self, parameter_name):
        return self.get_andor_parameter(parameter_name)

    def set_camera_parameter(self, parameter_name, parameter_value):
        try:
            self.set_andor_parameter(parameter_name, parameter_value)
        except Exception as e:
            self.log('parameter %s could not be set with the value %s due to error %s' % (parameter_name,
                                                                                          parameter_value, e))

    @NotifiedProperty
    def roi(self):
        # return self.Image[2:]
        return tuple(map(lambda x: x - 1, self.Image[2:]))

    @roi.setter
    def roi(self, value):
        image = self.Image
        # self.Image = image[:2] + value
        self.Image = image[:2] + tuple(map(lambda x: x + 1, value))

    @NotifiedProperty
    def binning(self):
        return self.Image[:2]

    @binning.setter
    def binning(self, value):
        if not isinstance(value, tuple):
            value = (value, value)
        image = self.Image
        self.Image = value + image[2:]

    def get_control_widget(self):
        return AndorUI(self)

    def get_preview_widget(self):
        self._logger.debug('Getting preview widget')
        if self._preview_widgets is None:
            self._preview_widgets = WeakSet()
        new_widget = DisplayWidgetRoiScale()
        self._preview_widgets.add(new_widget)

        return new_widget

    def set_image(self, *params):
        """Set camera parameters for either the IsolatedCrop mode or Image mode

        Parameters
        ----------
        params  optional, inputs for either the IsolatedCrop mode or Image mode

        Returns
        -------

        """
        AndorBase.set_image(*params)
        self.scaling()

    def scaling(self):
        self.unit_scale = self.Image[:2]  # for x and y axis
        self.unit_offset = (self.Image[2], self.Image[4])

        return self.unit_scale, self.unit_offset


class AndorUI(QtWidgets.QWidget, UiTools):
    ImageUpdated = QtCore.Signal()

    def __init__(self, andor):
        assert isinstance(andor, Andor), "instrument must be an Andor"
        super(AndorUI, self).__init__()
        self.Andor = andor
        self.DisplayWidget = None

        uic.loadUi((os.path.dirname(__file__) + '/andor.ui'), self)

        self._setup_signals()
        self.updateGUI()
        self.BinningChanged()
        self.data_file = None
        self.save_all_parameters = False

        self.gui_params = ['ReadMode', 'Exposure', 'CoolerMode'
            , 'AcquisitionMode', 'OutAmp', 'TriggerMode']
        self._func_dict = {}
        for param in self.gui_params:
            func = self.callback_to_update_prop(param)
            self._func_dict[param] = func
            register_for_property_changes(self.Andor, param, self._func_dict[param])
        # self.Andor.updateGUI.connect(self.updateGUI)
        self.autoLevel = True
        self.autoRange = False

    def __del__(self):
        self._stopTemperatureThread = True
        if self.DisplayWidget is not None:
            self.DisplayWidget.hide()
            self.DisplayWidget.close()

    def _setup_signals(self):
        self.comboBoxAcqMode.activated.connect(self.AcquisitionModeChanged)
        self.comboBoxBinning.activated.connect(self.BinningChanged)
        self.comboBoxReadMode.activated.connect(self.ReadModeChanged)
        self.comboBoxTrigMode.activated.connect(self.TrigChanged)
        self.spinBoxNumFrames.valueChanged.connect(self.NumFramesChanged)
        self.spinBoxNumFrames.setRange(1, 1000000)
        self.spinBoxNumAccum.valueChanged.connect(self.NumAccumChanged)
        self.spinBoxNumRows.valueChanged.connect(self.NumRowsChanged)
        self.spinBoxCenterRow.valueChanged.connect(self.NumRowsChanged)
        self.checkBoxROI.stateChanged.connect(self.ROI)
        self.checkBoxCrop.stateChanged.connect(self.IsolatedCrop)
        self.checkBoxCooler.stateChanged.connect(self.Cooler)
        # self.checkBoxAutoExp.stateChanged.connect(self.AutoExpose)
        self.checkBoxEMMode.stateChanged.connect(self.OutputAmplifierChanged)
        self.spinBoxEMGain.valueChanged.connect(self.EMGainChanged)
        self.lineEditExpT.editingFinished.connect(self.ExposureChanged)
        self.lineEditExpT.setValidator(QtGui.QDoubleValidator())
        self.pushButtonDiv5.clicked.connect(lambda: self.ExposureChanged('/'))
        self.pushButtonTimes5.clicked.connect(lambda: self.ExposureChanged('x'))

        self.pushButtonCapture.clicked.connect(self.Capture)
        self.pushButtonLive.clicked.connect(self.Live)
        self.pushButtonAbort.clicked.connect(self.Abort)
        self.save_pushButton.clicked.connect(self.Save)
        self.pushButtonTakeBG.clicked.connect(self.take_background)
        self.checkBoxRemoveBG.stateChanged.connect(self.remove_background)
        self.referesh_groups_pushButton.clicked.connect(self.update_groups_box)

    # GUI FUNCTIONS
    def updateGUI(self):
        trig_modes = {0: 0, 1: 1, 6: 2}
        print self.Andor.parameters
        print self.Andor._parameters
        self.comboBoxAcqMode.setCurrentIndex(self.Andor._parameters['AcquisitionMode'] - 1)
        self.AcquisitionModeChanged()
        self.comboBoxReadMode.setCurrentIndex(self.Andor._parameters['ReadMode'])
        self.ReadModeChanged()
        self.comboBoxTrigMode.setCurrentIndex(trig_modes[self.Andor._parameters['TriggerMode']])
        self.TrigChanged()
        self.comboBoxBinning.setCurrentIndex(np.log2(self.Andor._parameters['Image'][0]))
        self.BinningChanged()
        self.spinBoxNumFrames.setValue(self.Andor._parameters['NKin'])

        self.Andor.get_andor_parameter('AcquisitionTimings')
        self.lineEditExpT.setText(
            str(float('%#e' % self.Andor._parameters['AcquisitionTimings'][0])).rstrip('0'))

    def Cooler(self):
        if self.checkBoxCooler.isChecked():
            if not self.Andor.IsCoolerOn():
                self.Andor.CoolerON()
                self.TemperatureUpdateThread = self._constantlyUpdateTemperature()
        else:
            if self.Andor.IsCoolerOn():
                self.Andor.CoolerOFF()
                if self.TemperatureUpdateThread.isAlive():
                    self._stopTemperatureThread = True

    def AcquisitionModeChanged(self):
        available_modes = ['Single', 'Accumulate', 'Kinetic', 'Fast Kinetic']
        currentMode = self.comboBoxAcqMode.currentText()
        self.Andor.set_andor_parameter('AcquisitionMode', available_modes.index(currentMode) + 1)

        if currentMode == 'Fast Kinetic':
            self.spinBoxNumRows.show()
            self.labelNumRows.show()
        elif self.comboBoxReadMode.currentText() != 'Single track':
            self.spinBoxNumRows.hide()
            self.labelNumRows.hide()
        if currentMode == 'Accumulate':
            self.spinBoxNumAccum.show()
            self.labelNumAccum.show()
        else:
            self.spinBoxNumAccum.hide()
            self.labelNumAccum.hide()

    def ReadModeChanged(self):
        available_modes = ['FVB', 'Multi-track', 'Random track', 'Single track', 'Image']
        currentMode = self.comboBoxReadMode.currentText()
        self.Andor.set_andor_parameter('ReadMode', available_modes.index(currentMode))
        if currentMode == 'Single track':
            self.spinBoxNumRows.show()
            self.labelNumRows.show()
            self.spinBoxCenterRow.show()
            self.labelCenterRow.show()
        elif self.comboBoxAcqMode.currentText() != 'Fast Kinetic':
            self.spinBoxNumRows.hide()
            self.labelNumRows.hide()
            self.spinBoxCenterRow.hide()
            self.labelCenterRow.hide()
        else:
            self.spinBoxCenterRow.hide()
            self.labelCenterRow.hide()

    def update_ReadMode(self, index):
        self.comboBoxReadMode.setCurrentIndex(index)

    def update_TriggerMode(self, value):
        available_modes = {0: 0, 1: 1, 6: 2}
        index = available_modes[value]
        self.comboBoxTrigMode.setCurrentIndex(index)

    def update_Exposure(self, value):
        self.lineEditExpT.setText(str(value))

    def update_Cooler(self, value):
        self.checkBoxCooler.setCheckState(value)

    def update_OutAmp(self, value):
        self.checkBoxEMMode.setCheckState(value)

    def callback_to_update_prop(self, propname):
        """Return a callback function that refreshes the named parameter."""

        def callback(value=None):
            getattr(self, 'update_' + propname)(value)

        return callback

    def TrigChanged(self):
        available_modes = {'Internal': 0, 'External': 1, 'ExternalStart': 6}
        currentMode = self.comboBoxTrigMode.currentText()
        self.Andor.set_andor_parameter('TriggerMode', available_modes[currentMode])

    def OutputAmplifierChanged(self):
        if self.checkBoxEMMode.isChecked():
            self.Andor.set_andor_parameter('OutAmp', 0)
        else:
            self.Andor.set_andor_parameter('OutAmp', 1)
        if self.checkBoxCrop.isChecked():
            self.checkBoxCrop.setChecked(False)
            # self.ROI()

    def BinningChanged(self):
        current_binning = int(self.comboBoxBinning.currentText()[0])
        if self.Andor._parameters['IsolatedCropMode'][0]:
            params = list(self.Andor._parameters['IsolatedCropMode'])
            params[3] = current_binning
            params[4] = current_binning
            self.Andor._logger.debug('BinningChanged: %s' % str(params))
            self.Andor.set_image(*params)
        else:
            self.Andor.binning = current_binning
        self.Andor.FVBHBin = current_binning

    def NumFramesChanged(self):
        num_frames = self.spinBoxNumFrames.value()
        self.Andor.set_andor_parameter('NKin', num_frames)

    def NumAccumChanged(self):
        num_frames = self.spinBoxNumAccum.value()
        # self.Andor.SetNumberAccumulations(num_frames)
        self.Andor.set_andor_parameter('NAccum', num_frames)

    def NumRowsChanged(self):
        num_rows = self.spinBoxNumRows.value()
        if self.Andor._parameters['AcquisitionMode'] == 4:
            self.Andor.set_fast_kinetics(num_rows)
        elif self.Andor._parameters['ReadMode'] == 3:
            center_row = self.spinBoxCenterRow.value()
            if center_row - num_rows < 0:
                self.Andor._logger.info(
                    'Too many rows provided for Single Track mode. Using %g rows instead' % center_row)
                num_rows = center_row
            self.Andor.set_andor_parameter('SingleTrack', center_row, num_rows)
        else:
            self.Andor._logger.info('Changing the rows only works in Fast Kinetic or in Single Track mode')

    def ExposureChanged(self, input=None):
        if input is None:
            expT = float(self.lineEditExpT.text())
        elif input == 'x':
            expT = float(self.lineEditExpT.text()) * 5
        elif input == '/':
            expT = float(self.lineEditExpT.text()) / 5
        self.Andor.Exposure = expT
        # self.Andor.SetExposureTime(expT)
        #    self.Andor.SetParameter('Exposure', expT)
        # self.Andor.GetAcquisitionTimings()
        #    display_str = str(float('%#e' % self.Andor.parameters['AcquisitionTimings']['value'][0])).rstrip('0')
        #   self.lineEditExpT.setText(self.Andor.Exposure)

    def EMGainChanged(self):
        gain = self.spinBoxEMGain.value()
        self.Andor.set_andor_parameter('EMGain', gain)

    def IsolatedCrop(self):
        current_binning = int(self.comboBoxBinning.currentText()[0])
        gui_roi = self.Andor.gui_roi
        shape = self.Andor._parameters['DetectorShape']
        if self.checkBoxEMMode.isChecked():
            maxx = gui_roi[1]
            maxy = gui_roi[3]
        else:
            maxx = shape[0] - gui_roi[1]
            maxy = gui_roi[3]
        if self.checkBoxCrop.isChecked():
            if self.checkBoxROI.isChecked():
                self.checkBoxROI.setChecked(False)
            self.Andor._parameters['IsolatedCropMode'] = (1,)
            self.Andor.set_image(1, maxy, maxx, current_binning, current_binning)
        else:
            self.Andor.set_andor_parameter('IsolatedCropMode', 0, maxy, maxx, current_binning, current_binning)
            self.Andor.set_image()

    def take_background(self):
        self.Andor.background = self.Andor.raw_snapshot()[1]
        self.Andor.backgrounded = True
        self.checkBoxRemoveBG.setChecked(True)

    def remove_background(self):
        if self.checkBoxRemoveBG.isChecked():
            self.Andor.backgrounded = True
        else:
            self.Andor.backgrounded = False

    def Save(self):
        if self.data_file == None:
            self.data_file = df.current()
        data = self.Andor.CurImage
        if self.filename_lineEdit.text() != 'Filename....':
            filename = self.filename_lineEdit.text()
        else:
            filename = 'Andor_data'
        if self.group_comboBox.currentText() == 'AndorData':
            if df._use_current_group == True and df._current_group is not None:
                group = df._current_group
            elif 'AndorData' in self.data_file.keys():
                group = self.data_file['AndorData']
            else:
                group = self.data_file.create_group('AndorData')
        else:
            group = self.data_file[self.group_comboBox.currentText()]
        if np.shape(data)[0] == 1:
            data = data[0]
        if self.save_all_parameters == True:
            attrs = self.Andor.get_andor_parameters()
        else:
            attrs = dict()
        attrs['Description'] = self.description_plainTextEdit.toPlainText()
        if hasattr(self.Andor, 'x_axis'):
            attrs['wavelengths'] = self.Andor.x_axis
        try:
            data_set = group.create_dataset(name=filename, data=data)
        except Exception as e:
            self.Andor._logger.info(e)
        df.attributes_from_dict(data_set, attrs)
        if self.Andor.backgrounded == False and 'background' in data_set.attrs.keys():
            del data_set.attrs['background']

    def update_groups_box(self):
        if self.data_file == None:
            self.data_file = df.current()
        self.group_comboBox.clear()
        if 'AndorData' not in self.data_file.values():
            self.group_comboBox.addItem('AndorData')
        for group in self.data_file.values():
            if type(group) == df.Group:
                self.group_comboBox.addItem(group.name[1:], group)

    def ROI(self):
        if self.checkBoxROI.isChecked():
            self.Andor.roi = self.Andor.gui_roi  # binning + params
        else:
            self.Andor.roi = (0, self.Andor._parameters['DetectorShape'][0]-1,
                              0, self.Andor._parameters['DetectorShape'][1]-1)

    def Capture(self):
        self.Andor.raw_image(update_latest_frame=True)

    def Live(self):
        self.Andor.live_view = True

    def Abort(self):
        self.Andor.live_view = False


def main():
    andor = Andor()  # wvl_to_pxl=32.5 / 1600, magnification=30, pxl_size=16)
    register_for_property_changes(andor, 'latest_raw_frame', andor.update_widgets)
    app = QtWidgets.QApplication([])
    # ui1 = andor.get_control_widget()
    # ui2 = andor.get_preview_widget()
    # print ui1, ui2

    # ui1.show()
    # ui2.show()
    andor.show_gui()


if __name__ == '__main__':
    main()