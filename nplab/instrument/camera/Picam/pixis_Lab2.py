# -*- coding: utf-8 -*-
"""
# Ralf Mouthaan, Ilya Manyakin, Ermanno Miele
# University of Cambridge
# October 2018
# 
# Class to operate Pixis CCD camera. Communicates with Picam library to achieve
# this. Aim is to use this class in conjunction with Acton spectormeter for
# Raman measurements. Work done with Ermanno Miele.
#
# TODO:
#   * Script connects to first camera it finds and uses this. This will cause 
#       problems if no camera is connected, or more than one camera is
#       connected, or if an unexpected camera is connected. 
#       Should iterate through cameras, checking IDs to find the right one.
#       This is complicated due to the way the C++ code uses lots of structures
#       instead of native data types.
#   * Will not find a camera if it is in use by another process or has not 
#       been shut down properly.

Development notes:
    * API for DLL: Picam 5.x Programmers Manual, 4411-0161, Issue 5, August 2018
    
"""
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
import threading
from builtins import range
from past.utils import old_div
import ctypes as ct
import numpy as np
from matplotlib import pyplot as plt
import nplab.datafile as df
from nplab.instrument.camera.camera_scaled_roi import CameraRoiScale
from nplab.instrument.camera import Camera
from nplab.ui.ui_tools import UiTools
from nplab.utils.gui import QtWidgets, QtCore, uic, QtGui
import sys,os, time
from nplab.utils.log import create_logger
from .picam_constants import PicamSensorTemperatureStatus,PicamParameter,PicamValueType,PicamError,transpose_dictionary,PI_V,PicamConstraintType
from nplab.utils.notified_property import NotifiedProperty

import logging
LOGGER = create_logger('Pixis256E')
PARENT_DIR = os.path.dirname(os.path.realpath(__file__))


class clsPicamReadoutStruct(ct.Structure):
    _fields_ = [("ptr", ct.c_void_p),
                ("intCount", ct.c_int64)]


class Pixis(CameraRoiScale):
    metadata_property_names = ('Exposure', 'x_axis', 'CurrentTemperature',)
    
    def __init__(self,with_start_up = False ,debug=0):
        super(Pixis, self).__init__()
        self.debug = debug
        self.bolRunning = False
        self._logger = LOGGER
        self.y_max = 0
        self.x_max = 0
        self.y_min = 0
        self.x_min = 0
        self.center_row = 128
        self.num_rows = 256
        self.aquisition_mode = 'Image'
        if with_start_up == True:
            self.StartUp()
            self.SetExposureTime(10)
            
        self.boundary_cut = 5
        self.background = None
        self.backgrounded = False
        self.current_frame = None
        self.data_file = None
        
    def __del__(self):
        if self.bolRunning == True:
            self.ShutDown()

    def Capture(self, suppress_errors = False):
        """ 
            Basic camera snapshot function
        """
        try:
            image  = np.array(self.GetCurrentFrame())
            return image
        except Exception as e:
            if suppress_errors==True:
                False, None
            else:
                raise e         
        
    def raw_snapshot(self, suppress_errors=False):
        """
            CameraRoiScale class override
        """
        image  = self.filter_function(self.Capture())

        if self.aquisition_mode == 'Spectrum':
                image = self.get_spectrum(image)
        elif self.aquisition_mode == 'ROI':
                image = self.get_roi(image)
        self.current_frame = image
        return True, image
          

    def get_roi(self,raw_image, x_min=None, x_max = None, y_min=None,y_max = None, suppress_errors=False,debug=0):
        """ 
            Takes input of raw snapshot an outputs ROI image
        """
        if x_min is None:
            x_min = self.x_min
        if y_min is None:
            y_min = self.y_min
        if x_max is None:
            x_max = self.x_max
        if y_max is None:
            y_max = self.y_max
        if debug > 0:
            print("Pixis.get_roi region of interest:",x_min,x_max,y_min,y_max)
        roi_image = raw_image[y_min:y_max, x_min:x_max]
        if debug > 0:
            print("Pixis.roi_image.shape:",roi_image.shape)
        return roi_image

    def get_spectrum(self, raw_image, x_min= None, x_max = None, y_min=None,y_max = None ,with_boundary_cut = False, suppress_errors=False):  
        """ 
            Takes input of raw snapshot an outputs ROI defined spectrum
        """
        roi_image = self.get_roi(raw_image, x_min,x_max,y_min,y_max,suppress_errors)
        #cut edge values from raw spectrum - remove edge effects
        raw_spectrum = np.sum(roi_image,axis=0)
        if with_boundary_cut == True:
            return raw_spectrum[self.boundary_cut:-self.boundary_cut]
        else:
            return raw_spectrum

    def get_parameter(self,parameter_name, label="unknown"):
        """
        Perform GetParameterIntegerValue calls to DLL
        parameter_name : name of parameter as specified in the picam_constants.py file
        """

        if self.debug > 0:
            print("pixis.get_parameter::parameter_name:{}".format(parameter_name))
        self.picam.PicamAdvanced_RefreshParametersFromCameraDevice(self.CameraHandle)
        assert(parameter_name in list(PicamParameter.keys())) #Check that the passed parameter name is valid (ie. in constants file)
        param_type, constraint_type, n = PicamParameter[parameter_name]
        if self.debug > 0:
            print("pixis:get_parameter::param_type: {}".format(param_type))
            print("pixis:get_parameter::constraint_type: {}".format(constraint_type))
            print("pixis:get_parameter::n: {}".format(n))

        param_id = PI_V(value_type=param_type, constraint_type= constraint_type, parameter_index=n)

        #assert returned parameter value type is valid one
        valid_value_types = list(transpose_dictionary(PicamValueType).keys())
        assert(param_type in valid_value_types)

        #assert returned parameter constraint type is valid one
        valid_constraint_types = list(transpose_dictionary(PicamConstraintType).keys())
        assert(constraint_type in valid_constraint_types)
        
        paramtype = param_type.replace("PicamValueType_","")

        if self.debug > 0:
            print("paramtype:", paramtype)

        if paramtype == "Enumeration":
            paramtype="IntegerValue"

        else:
            paramtype=paramtype+"Value"

        function_name = "Picam_GetParameter{}".format(paramtype)
        if self.debug > 0:
            print("Function name:",function_name)
            print("Parameter name:", parameter_name)
            print("Parameter id:",param_id) 
            # print "Function object", f
        
        getter = getattr(self.picam,function_name,None)
        if getter is None:
            raise ValueError("Getter is none!")
        else:
            if self.debug > 0:
                print(getter)
        temp =  {
            "PicamValueType_Integer" : ct.c_int(),
            "PicamValueType_Boolean" : ct.c_bool(),
            "PicamValueType_LargeInteger" : ct.c_long(),

            "PicamValueType_FloatingPoint" : ct.c_double(),

            "PicamValueType_Enumeration": ct.c_int(), #TODO 
            "PicamValueType_Rois": ct.c_int(), #TODO
            "PicamValueType_Pulse": None, #TODO
            "PicamValueType_Modulations": None #None       
        }
        


        value = temp[param_type]
        if self.debug > 0:
            print("pixis.get_parameter::param_type: {}".format(param_type))
            print("pixis.get_parameter::value: {}".format(value))
        if value is not None:
            response = getter(self.CameraHandle,param_id, ct.pointer(value))

            if response != 0:
                print(("Could not GET value of parameter {0} [label:{1}]".format(parameter_name,label)))
                print(("[Code:{0}] {1}".format(response, PicamError[response])))
                return np.nan
        
            return value.value
        else:
            '''
            Cases left to implement:
                PicamValueType_Enumeration,
                PicamValueType_Rois,
                PicamValueType_Pulse,
                PicamValueType_Modulations
            '''
            raise NotImplementedError()
        
    def set_parameter(self,parameter_name,parameter_value):
        '''
        Perform GetParameterIntegerValue calls to DLL
        parameter_name : name of parameter as specified in the picam_constants.py file
        '''
        assert(parameter_name in list(PicamParameter.keys())) #Check that the passed parameter name is valid (ie. in constants file)
        param_type, constraint_type, n = PicamParameter[parameter_name]
        param_id = PI_V(value_type=param_type, constraint_type= constraint_type, parameter_index=n)

        #assert returned parameter value type is valid one
        valid_value_types = list(transpose_dictionary(PicamValueType).keys())
        assert(param_type in valid_value_types)

        #assert returned parameter constraint type is valid one
        valid_constraint_types = list(transpose_dictionary(PicamConstraintType).keys())
        assert(constraint_type in valid_constraint_types)
        

        function_name = "Picam_SetParameter{}Value".format(param_type.replace("PicamValueType_",""))
        setter = getattr(self.picam,function_name)
        # setter = self.picam.Picam_SetParameterFloatingPointValue
        if self.debug > 0:
            print("Function name:",function_name)
            print("Paramer type, Constraint type, n:", param_type, constraint_type, n)
            print("Function object", setter)
        
        temp =  {
            "PicamValueType_Integer" : ct.c_int,
            "PicamValueType_Boolean" : ct.c_bool,
            "PicamValueType_LargeInteger" : ct.c_long,
            "PicamValueType_FloatingPoint" : ct.c_double, #WARNING - THIS SHOULD BE A DOUBLE (64bit), NOT FLOAT (32bit) [for 32bit change to float]
            "PicamValueType_Enumeration": ct.c_int, #Maybe an int 
            "PicamValueType_Rois": ct.c_int() , #TODO
            "PicamValueType_Pulse": None, #TODO
            "PicamValueType_Modulations": None #None       
        }
        
        #allocate memory for parameter for DLL to populate
        value = temp[param_type](parameter_value)

        if value is not None:
            if self.debug > 0:
                print("setting: param_id:  {0}, value:{1}".format(param_id,value))

            response = setter(self.CameraHandle,param_id, value)
            if response != 0:
                print(("Could not SET value of parameter {0} [label:{1}]".format(parameter,label)))
                print(("[Code:{0}] {1}".format(response, PicamError[response])))
                return np.nan
            #check if commit failed
            failed_commit = (ct.c_int*10)()
            failed_count = ct.c_int()
            response = self.picam.Picam_CommitParameters(self.CameraHandle,ct.byref(failed_commit),ct.byref(failed_count))
            if self.debug > 0:
                print("Picam_CommitParameters response:",response, failed_count, list(failed_commit))
            
            assert(int(failed_count.value) == 0)
            #check if commit has passed
            committed = ct.c_bool(False)
            response = self.picam.Picam_AreParametersCommitted(self.CameraHandle,ct.byref(committed))
            if self.debug> 0:
                    print("Picam_CommitParameters response:",response, committed)

            assert(bool(committed.value) == True)
            
            return

        else:
            '''
            Cases left to implement:
                PicamValueType_Enumeration,
                PicamValueType_Rois,
                PicamValueType_Pulse,
                PicamValueType_Modulations
            '''
            raise NotImplementedError()

    def StartUp(self):
        cint_temp = ct.c_int()
        # Find DLL
        try:
            self.picam = ct.WinDLL(os.path.normpath('{}/Picam.dll'.format(PARENT_DIR)))
        except Exception as e:
            logging.warning("Error:",e)
            logging.info("Could not find picam dll")
            return
        #print(self.picam.Picam_GetVersion())
        # Initialise library
        bolInitialised = ct.c_bool(False)
        if self.picam.Picam_InitializeLibrary() != 0:
            print("Could not initialise library")
            return
        self.picam.Picam_IsLibraryInitialized(ct.byref(bolInitialised))
        if bolInitialised == ct.c_bool(False):
            print("Library was not initialised")
            return
        # Get camera handle
        self.CameraHandle = ct.c_void_p()
        if self.picam.Picam_OpenFirstCamera(ct.byref(self.CameraHandle)) != 0:
            print("Could not find camera")
            return

        self.x_max = self.FrameWidth = self.get_parameter(parameter_name="PicamParameter_SensorActiveWidth", label="frame width")
        self.y_max = self.FrameHeight = self.get_parameter(parameter_name="PicamParameter_SensorActiveHeight", label="frame height")
        print("Frame size:", self.x_max, self.y_max)
        self.bolRunning = True
        self.SetTemperatureWithLock(-80.0)

    
    def ShutDown(self):
        if self.bolRunning == False:
            return
        if self.picam.Picam_CloseCamera(self.CameraHandle) != 0:
            print("Could not close camera")
            return
        if self.picam.Picam_UninitializeLibrary() != 0:
            print("Could not shut down library")
            return
        self.bolRunning = False
        
    def SetExposureTime(self,time):
        
        param_name = "PicamParameter_ExposureTime"        
        param_value = time #in milliseconds
        self.set_parameter(parameter_name=param_name,parameter_value=param_value)
        
    def GetExposureTime(self):
        
        param_name = "PicamParameter_ExposureTime"        
        self.get_parameter(parameter_name=param_name)

    def SetTemperatureWithLock(self,temperature):
        self.__SetSensorTemperatureSetPoint(temperature)
        status_code = self.GetTemperatureStatus()
        #while PicamSensorTemperatureStatus[status_code] != "PicamSensorTemperatureStatus_Locked":
         #   print("TemperatureStatus: {3}[{2}] (current: {0}, target:{1})".format(self.GetSensorTemperatureReading(), temperature,status_code, PicamSensorTemperatureStatus[status_code]))
          #  time.sleep(0.5)
           # status_code = self.GetTemperatureStatus()

        #status_code = self.GetTemperatureStatus()
        #print("TemperatureStatus: {0} [{1}]".format(PicamSensorTemperatureStatus[status_code], status_code))
        return


    def GetSensorTemperatureReading(self):
        param_name = "PicamParameter_SensorTemperatureReading"
        return self.get_parameter(param_name)

    def __SetSensorTemperatureSetPoint(self,temperature):
        '''
            Do not use this method if you want to wait for temperature to stabilize, use SetTemperatureWithLock
        '''
        param_name = "PicamParameter_SensorTemperatureSetPoint"
        return self.set_parameter(parameter_name=param_name,parameter_value=temperature)

    def GetTemperatureStatus(self):
        '''
        See picam_constants.PicamSensorTemperatureStatus for
            int <-> status mappings
        '''
        param_name = "PicamParameter_SensorTemperatureStatus"
        return self.get_parameter(param_name)
    
    pixis_temperature = NotifiedProperty(GetSensorTemperatureReading, __SetSensorTemperatureSetPoint)

    def GetSensorType(self):
        param_name = "PicamParameter_SensorType"
        return self.get_parameter(parameter_name=param_name)

    def GetIntensifierStatus(self):
        param_name = "PicamParameter_IntensifierStatus"
        return self.get_parameter(parameter_name=param_name)


    def GetCurrentFrame(self):
        
        if self.bolRunning == False:
            self.StartUp()
        
        structReadout = clsPicamReadoutStruct()
        intErrorMask = ct.c_int()
        
        # Read in pointer to image buffer
        if self.picam.Picam_Acquire(self.CameraHandle, 1, -1, 
                ct.byref(structReadout), ct.byref(intErrorMask)) != 0:
            print("Image acquisition failed")
            return
        if intErrorMask.value != 0:
            print("Image acquisition returned an error")
            return
        
        # Get image
        ctarr = (ct.c_uint16*(self.FrameWidth*self.FrameHeight)) # Create ctypes array
        ctarr = ctarr.from_address(structReadout.ptr) # Read in array from pointer
        nparr = np.array(ctarr) # Convert to numpy array
        nparr = nparr.reshape((self.FrameHeight, self.FrameWidth)) # Reshape numpy array
        
        return nparr
    
    def filter_function(self, frame):
        if self.backgrounded:
            return frame - self.background
        else:
            return frame
        
    def get_pixis_parameters(self):
        print(self.GetExposureTime())
        pixis_parameters = dict()
        pixis_parameters['Temperature'] = self.pixis_temperature
        pixis_parameters['Exposure Time'] = self.GetExposureTime()
        pixis_parameters['ROI'] = np.array([self.center_row, self.num_rows])
        if self.backgrounded:
            pixis_parameters['Background'] = self.background
        return pixis_parameters
        
    
    def get_control_widget(self):
        return PixisUI(self)
    
"""List of avalible Pixis parameters saved in meta data
"""
parameters = dict()

class PixisUI(QtWidgets.QWidget, UiTools):
    def __init__(self,pixis):
        if not isinstance(pixis, Pixis):
           raise TypeError('instrument must be a Pixis camera')
        super(PixisUI, self).__init__()
        
        uic.loadUi(os.path.normpath('{}/pixis_ui.ui'.format(PARENT_DIR)), self)
        self.Pixis = pixis
        self.DisplayWidget = None
        self.data_file = None
        self.save_all_parameters = False
        
        self.Pixis.StartUp()
        self._setup_signals()
    
    def _setup_signals(self):
        #self.comboBoxBinning.activated.connect(self.binning)
        self.comboBoxReadMode.activated.connect(self.read_mode)
        self.spinBoxNumFrames.valueChanged.connect(self.number_frames)
        self.spinBoxNumFrames.setRange(1, 1000000)
        self.spinBoxNumRows.valueChanged.connect(self.number_rows)
        self.spinBoxCenterRow.valueChanged.connect(self.number_rows)
        self.lineEditExpT.editingFinished.connect(self.exposure)
        self.lineEditExpT.setValidator(QtGui.QDoubleValidator())
        self.pushButtonDiv5.clicked.connect(lambda: self.exposure('/'))
        self.pushButtonTimes5.clicked.connect(lambda: self.exposure('x'))
        self.pushButtonCapture.clicked.connect(self.Capture)
        self.pushButtonLive.clicked.connect(self.Live)
        self.pushButtonAbort.clicked.connect(self.Abort)
        #self.save_pushButton.clicked.connect(self.Save)
        self.pushButtonTakeBG.clicked.connect(self.take_background)
        self.checkBoxRemoveBG.stateChanged.connect(self.remove_background)
        self.read_temperature_pushButton.clicked.connect(self.update_temperature_display)
        self.save_pushButton.clicked.connect(self.Save)
        
    def Capture(self):
        #print('capture')
        self.Pixis.raw_image(update_latest_frame=True)
        
    def exposure(self, input = None):
        if input == None:
            ExTime = float(self.lineEditExpT.text())
        elif input == 'x':
            ExTime = float(self.lineEditExpT.text()) *5
            self.update_Exposure(ExTime)
        elif input == '/':
            ExTime = float(self.lineEditExpT.text()) / 5
            self.update_Exposure(ExTime)
        self.Pixis.SetExposureTime(ExTime)
        print(self.Pixis.GetExposureTime())
        
    
    def update_Exposure(self, value):
        self.lineEditExpT.setText(str(value))
        
    def update_temperature_display(self):
        temperature = self.Pixis.pixis_temperature
        self.temperature_lcdNumber.display(float(temperature))
        
    def take_background(self):
        self.Pixis.background = self.Pixis.raw_snapshot()[1]
        self.Pixis.backgrounded = True
        self.checkBoxRemoveBG.setChecked(True)
    
    def remove_background(self):
        if self.checkBoxRemoveBG.isChecked():
            self.Pixis.backgrounded = True
        else:
            self.Pixis.backgrounded = False
            
    def Live(self):
        self.Pixis.live_view = True
        
    def Abort(self):
        self.Pixis.live_view = False
        
    def number_frames(self):
        num_frames = self.spinBoxNumFrames.value()
        
    def number_rows(self):
        num_rows = self.spinBoxNumRows.value()
        center_row = self.spinBoxCenterRow.value()
        self.Pixis.center_row = center_row
        self.Pixis.num_rows = num_rows
        self.Pixis.y_min = int(center_row - (num_rows/2))
        self.Pixis.y_max = int(center_row + (num_rows/2))
    
    def read_mode(self):
        if self.Pixis.aquisition_mode != self.comboBoxReadMode.currentText():
            self.Pixis.aquisition_mode = self.comboBoxReadMode.currentText()
        
    def Save(self):
        if self.data_file is None:
            self.data_file = df.current()
        data = self.Pixis.current_frame
        
        if self.filename_lineEdit.text() != 'Filename....':
            filename = self.filename_lineEdit.text()
        else:
            filename = 'Pixis_data'      
        
        group = self.data_file.create_group('PixisData')

        attrs = self.Pixis.get_pixis_parameters()
        print(attrs)

        attrs['Description'] = self.description_plainTextEdit.toPlainText()
        if hasattr(self.Pixis, 'x_axis'):
            attrs['wavelengths'] = self.Pixis.x_axis
            
        if hasattr(self.Pixis, 'slit_width'):
            attrs['Slit Width'] = self.Pixis.slit_width
            
        try:
            data_set = group.create_dataset(name=filename, data=data)
        except Exception as e:
            self.Pixis._logger.info(e)
        df.attributes_from_dict(data_set, attrs)   
            
    def __del__(self):
        self.Pixis.ShutDown()
        if self.DisplayWidget is not None:
            self.DisplayWidget.hide()
            self.DisplayWidget.close()
        
if __name__ == "__main__":
    
    pixis = Pixis(debug = 0)
    #pixis.StartUp()
    gui = pixis.show_gui(blocking = False)
