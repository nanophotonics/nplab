# import nplab.utils.gui
from nplab.utils.gui import QtWidgets, QtCore, uic
from nplab.instrument.camera import Camera, CameraParameter
from nplab.utils.notified_property import NotifiedProperty
from nplab.utils.thread_utils import background_action, locked_action
import nplab.datafile as df
from nplab.utils.array_with_attrs import ArrayWithAttrs
from nplab.utils.notified_property import register_for_property_changes

import os
import platform
import time
from ctypes import *
import numpy as np
import pyqtgraph
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients


class AndorCapabilities(Structure):
    _fields_ = [("ulSize", c_ulong),
                ("ulAcqModes", c_ulong),
                ("ulReadModes", c_ulong),
                ("ulTriggerModes", c_ulong),
                ("ulCameraType", c_ulong),
                ("ulPixelMode", c_ulong),
                ("ulSetFunctions", c_ulong),
                ("ulGetFunctions", c_ulong),
                ("ulFeatures", c_ulong),
                ("ulPCICard", c_ulong),
                ("ulEMGainCapability", c_ulong),
                ("ulFTReadModes", c_ulong)]


class AndorWarning(Warning):
    def __init__(self, code, msg, reply):
        super(AndorWarning, self).__init__()
        self.error_code = code
        self.error_name = ERROR_CODE[code]

        self.msg = msg
        self.reply = reply

    def __str__(self):
        return self.error_name + '\n Error sent: ' + self.msg + '\n Error reply: ' + self.reply


class AndorParameter(NotifiedProperty):
    """A quick way of creating a property that alters an Andor parameter.
    
    NB the property will be read immediately after it's written, to ensure
    that the value we send to any listening controls/indicators is correct
    (otherwise we'd send them the value that was requested, even if it was
    not valid).  This behaviour can be disabled by setting read_back to False
    in the constructor.
    """

    def __init__(self, parameter_name, doc=None, read_back=True):
        """Create a property that reads and writes the given parameter.
        
        This internally uses the `get_camera_parameter` and 
        `set_camera_parameter` methods, so make sure you override them.
        """
        if doc is None:
            doc = "Adjust the camera parameter '{0}'".format(parameter_name)
        super(AndorParameter, self).__init__(fget=self.fget,
                                             fset=self.fset,
                                             doc=doc,
                                             read_back=read_back)
        self.parameter_name = parameter_name

    def fget(self, obj):
        value = obj.GetParameter(self.parameter_name)
        if (type(value) == tuple) and (len(value) == 1):
            return value[0]
        else:
            return value

    def fset(self, obj, value):
        if type(value) != tuple:
            value = (value,)
        obj.SetParameter(self.parameter_name, value)


class AndorBase:
    """
    The self.parameters dictionary contains all the information necessary to deal with the camera parameters. Each
    entry in the dictionary corresponds to a specific parameter and allows you to specify the Get and/or Set command
    name and datatype (from the .dll).

    Most parameters are straightforward, since the Andor dll either has inputs (for setting parameters) or outputs
    (for getting parameters). So you can just intuitively call Andor.GetParameter(name) or Andor.SetParameter(name, value)
    with name and value provided by the user.
    Some parameters, like VSSpeed, HSSpeed..., require inputs to get outputs, so the user must say, e.g.,
        Andor.GetParameter('VSSpeed', 0)
    Which does not return the current VSSpeed, but the VSSpeed (in us) of the setting 0.
    """

    def __init__(self):
        if platform.system() == 'Windows':
            if platform.architecture()[0] == '32bit':
                self.dll = windll(os.path.dirname(__file__) + "\\atmcd32d")
            elif platform.architecture()[0] == '64bit':
                self.dll = CDLL(os.path.dirname(__file__) + "\\atmcd64d")
            else:
                raise Exception("Cannot detect Windows architecture")
        elif platform.system() == "Linux":
            dllname = "usr/local/lib/libandor.so"
            self.dll = cdll.LoadLibrary(dllname)
        else:
            raise Exception("Cannot detect operating system for Andor")
            #       self.channel = (0,)
        self.parameters = parameters
        # , Inputs=(c_int, c_int,)
        self.Initialize()

    #        self.capabilities = {}
    #        for property_name in self.parameters:
    #            print property_name
    #            setattr(self, property_name, AndorParameter(property_name))

    def __del__(self):
        """
        If the camera is not a Newton, we start a thread that determines whether the camera is too cold for shutdown.
        This can be modified to include other cameras that are safe to shutdown when cold
        :return:
        """
        if self.parameters['Capabilities']['value']['CameraType'] != 8:
            waitThread = WaitThread(self)
            waitThread.start()
            waitThread.wait()
        self._dllWrapper('ShutDown')
        libHandle = self.dll._handle
        if platform.system() == 'Windows':
            if platform.architecture()[0] == '32bit':
                windll.kernel32.FreeLibrary(libHandle)
            elif platform.architecture()[0] == '64bit':
                # Following http://stackoverflow.com/questions/19547084/can-i-explicitly-close-a-ctypes-cdll
                from ctypes import wintypes
                kernel32 = WinDLL('kernel32')
                kernel32.FreeLibrary.argtypes = [wintypes.HMODULE]
                kernel32.FreeLibrary(libHandle)
            else:
                raise Exception("Cannot detect Windows architecture")
        elif platform.system() == "Linux":
            cdll.LoadLibrary('libdl.so').dlclose(libHandle)
        del self.dll

    '''Base functions'''

    @locked_action
    def _dllWrapper(self, funcname, inputs=(), outputs=(), reverse=False):
        """Handler for all the .dll calls of the Andor

        Parameters
        ----------
        funcname    Name of the dll function to be called
        inputs      Inputs to be handed in to the dll function
        outputs     Outputs to be expected from the dll
        reverse     Whether to have the inputs first or the outputs first when calling the dll

        Returns
        -------

        """
        dll_input = ()
        if reverse:
            for output in outputs:
                dll_input += (byref(output),)
            for inpt in inputs:
                dll_input += (inpt['type'](inpt['value']),)
        else:
            for inpt in inputs:
                dll_input += (inpt['type'](inpt['value']),)
            for output in outputs:
                dll_input += (byref(output),)
        error = getattr(self.dll, funcname)(*dll_input)
        self._errorHandler(error, funcname, *(inputs + outputs))

        returnVals = ()
        for output in outputs:
            if hasattr(output, 'value'):
                returnVals += (output.value,)
            if isinstance(output, AndorCapabilities):
                dicc = {}
                for key, value in output._fields_:
                    dicc[key[2:]] = getattr(output, key)
                returnVals += (dicc,)
        if len(returnVals) == 1:
            return returnVals[0]
        else:
            return returnVals

    def _errorHandler(self, error, funcname='', *args):
        if '_logger' in self.__dict__:
            self._logger.debug("[%s]: %s %s" % (funcname, ERROR_CODE[error], str(args)))
        #        elif 'verbosity' in self.__dict__:
        #            if self.verbosity:
        #                self._logger.error("[%s]: %s" % (funcname, ERROR_CODE[error]))
        if funcname == 'GetTemperature':
            return
        if error != 20002:
            raise AndorWarning(error, funcname, ERROR_CODE[error])

    @background_action
    def _constantlyUpdateTemperature(self):
        self.aborted = False
        while not self.aborted:
            print self.GetParameter('CurrentTemperature')
            time.sleep(10)

    def SetParameter(self, param_loc, *inputs):
        """Parameter setter

        Using the information contained in the self.parameters dictionary, send a general parameter set command to the
        Andor. The command name, and number of inputs and their types are stored in the self.parameters

        Parameters
        ----------
        param_loc   dictionary key of self.parameters
        inputs      inputs required to set the particular parameter. Must be at least one

        Returns
        -------

        """
        if len(inputs) == 1 and type(inputs[0]) == tuple:
            if len(np.shape(inputs)) == 2:
                inputs = inputs[0]
            elif len(np.shape(inputs)) == 3:
                inputs = inputs[0][0]
        if 'Set' in self.parameters[param_loc]:
            func = self.parameters[param_loc]['Set']

            form_in = ()
            if 'Input_params' in func:
                for input_param in func['Input_params']:
                    form_in += ({'value': getattr(self, input_param[0]), 'type': input_param[1]},)
            for ii in range(len(inputs)):
                form_in += ({'value': inputs[ii], 'type': func['Inputs'][ii]},)
            self._dllWrapper(func['cmdName'], inputs=form_in)

            if len(inputs) == 1:
                self.parameters[param_loc]['value'] = inputs[0]
            else:
                self.parameters[param_loc]['value'] = inputs

            if 'Finally' in self.parameters[param_loc]:
                self.GetParameter(self.parameters[param_loc]['Finally'])
                #       if 'GetAfterSet' in self.parameters[param_loc]:
                #          self.GetParameter(param_loc, *inputs)
        if 'Get' not in self.parameters[param_loc].keys():
            if len(inputs) == 1:
                setattr(self, '_' + param_loc, inputs[0])
            else:
                setattr(self, '_' + param_loc, inputs)
            self.parameters[param_loc]['value'] = getattr(self, '_' + param_loc)

    def GetParameter(self, param_loc, *inputs):
        """Parameter getter

        Using the information contained in the self.parameters dictionary, send a general parameter get command to the
        Andor. The command name, and number of inputs and their types are stored in the self.parameters

        Parameters
        ----------
        param_loc   dictionary key of self.parameters
        inputs      optional inputs for getting the specific parameter

        Returns
        -------

        """
        if 'Get' in self.parameters[param_loc].keys():
            func = self.parameters[param_loc]['Get']

            form_out = ()
            if param_loc == 'Capabilities':
                form_out += (func['Outputs'][0],)
            else:
                for output in func['Outputs']:
                    form_out += (output(),)
            form_in = ()
            if 'Input_params' in func:
                for input_param in func['Input_params']:
                    form_in += ({'value': getattr(self, input_param[0]), 'type': input_param[1]},)
            for ii in range(len(inputs)):
                form_in += ({'value': inputs[ii], 'type': func['Inputs'][ii]},)
            if 'Iterator' not in func.keys():
                vals = self._dllWrapper(func['cmdName'], inputs=form_in, outputs=form_out)
            else:
                vals = ()
                for i in range(getattr(self, func['Iterator'])):
                    form_in_iterator = form_in + ({'value': i, 'type': c_int},)
                    vals += (self._dllWrapper(func['cmdName'], inputs=form_in_iterator, outputs=form_out),)
            # if len(vals) == 1:
            #     vals = vals[0]
            self.parameters[param_loc]['value'] = vals
            return vals
        elif 'Get_from_prop' in self.parameters[param_loc].keys() and hasattr(self, '_' + param_loc):
            vals = getattr(self, self.parameters[param_loc]['Get_from_prop'])[getattr(self, '_' + param_loc)]
            self.parameters[param_loc]['value'] = vals
            return vals
        elif 'Get_from_fixed_prop' in self.parameters[param_loc].keys():
            vals = getattr(self, self.parameters[param_loc]['Get_from_fixed_prop'])[0]
            self.parameters[param_loc]['value'] = vals
            return vals

        elif hasattr(self, '_' + param_loc):
            self.parameters[param_loc]['value'] = getattr(self, '_' + param_loc)
            return getattr(self, '_' + param_loc)
        else:
            self._logger.info('The ' + param_loc + ' has not previously been set!')
            return None

    def GetAllParameters(self):
        '''Gets all the parameters that can be gotten
        Returns:
            An up to date paramters dict containing only values and names
        '''
        param_dict = dict()
        for param in self.parameters:
            param_dict[param] = getattr(self, param)
        return param_dict

    def SetAllParameters(self, Param_dict):
        """Sets the values of the parameters listed within the dict Param_dict, It can take any number of parameters
        """
        if type(Param_dict) == dict:

            for param in Param_dict:
                if hasattr(self, param):
                    if Param_dict[param] != None:
                        if 'Get_from_prop' in self.parameters[param]:
                            value = getattr(self, self.parameters[param]['Get_from_prop'])[np.where(
                                np.array(getattr(self, self.parameters[param]['Get_from_prop'])) == Param_dict[param])[
                                0][0]]
                        else:
                            value = Param_dict[param]
                        try:
                            setattr(self, param, value)
                        except Exception as e:
                            print e, param
                    else:
                        self._logger.info('%s has not been set, as the value provided was "None" ' % param)
                else:
                    self._logger.warn('The parameter ' + param + 'does not exist and therefore cannot be set')
        else:
            self._logger.warn('Parameter set input must be a dict!')

    # def SetAllParameters(self, parameters):
    #     # msg = ''
    #     for param in parameters.keys():
    #         if param not in ['EMMode', 'FastKinetics', 'ImageRotate', 'HSSpeed', 'VSSpeed', 'PreAmpGain', 'BitDepth',
    #                          'NumHSSpeed']:
    #             if 'Set' in self.parameters[param] and 'value' in self.parameters[param]:
    #                 if self.parameters[param]['value'] is not None:
    #                     if hasattr(self.parameters[param]['value'], '__iter__'):
    #                         self.SetParameter(param, *self.parameters[param]['value'])
    #                     else:
    #                         self.SetParameter(param, self.parameters[param]['value'])
    #
    #     #             else:
    #     #                 msg += param + ' '
    #     # self._logger.info('')

    '''Used functions'''

    def abort(self):
        try:
            self._dllWrapper('AbortAcquisition')
        except AndorWarning:
            pass

    def Initialize(self):
        self._dllWrapper('Initialize', outputs=(c_char(),))

        self.channel = 0
        self.backgrounded = False
        self.SetParameter('ReadMode', 4)
        self.SetParameter('AcquisitionMode', 1)
        self.SetParameter('TriggerMode', 0)
        self.SetParameter('Exposure', 0.01)
        self.SetParameter('Image', 1, 1, 1, self.DetectorShape[0], 1,
                          self.DetectorShape[1])
        self.SetParameter('Shutter', 1, 0, 1, 1)
        self.SetParameter('SetTemperature', -60)
        self.SetParameter('CoolerMode', 0)
        self.SetParameter('FanMode', 0)
        self.SetParameter('OutAmp', 1)

        #      self.GetAllParameters()

    # @background_action
    @locked_action
    def capture(self):
        """Capture function for Andor

        Wraps the three steps required for a camera acquisition: StartAcquisition, WaitForAcquisition and
        GetAcquiredData. The function also takes care of ensuring that the correct shape of array is passed to the
        GetAcquiredData call, according to the currently set parameters of the camera.

        Returns
        -------
        A numpy array containing the captured image(s)
        The number of images taken
        The shape of the images taken

        """
        self._dllWrapper('StartAcquisition')
        self._dllWrapper('WaitForAcquisition')
        self.WaitForDriver()

        if self.parameters['AcquisitionMode']['value'] == 4:
            num_of_images = 1  # self.parameters['FastKinetics']['value'][1]
            image_shape = (self.parameters['FastKinetics']['value'][-1], self.parameters['DetectorShape']['value'][0])
        else:
            if self.parameters['AcquisitionMode']['value'] == 1:
                num_of_images = 1
            elif self.parameters['AcquisitionMode']['value'] == 2:
                num_of_images = 1
            elif self.parameters['AcquisitionMode']['value'] == 3:
                num_of_images = self.parameters['NKin']['value']
            else:
                raise NotImplementedError('Acquisition Mode %g' % self.parameters['AcquisitionMode']['value'])

            if self.parameters['ReadMode']['value'] == 0:
                if self.parameters['IsolatedCropMode']['value'][0]:
                    image_shape = (
                        self.parameters['IsolatedCropMode']['value'][2] / self.parameters['IsolatedCropMode']['value'][
                            4],)
                else:
                    image_shape = (self.parameters['DetectorShape']['value'][0] / self.parameters['FVBHBin']['value'],)
            elif self.parameters['ReadMode']['value'] == 3:
                image_shape = (self.parameters['DetectorShape']['value'][0],)
            elif self.parameters['ReadMode']['value'] == 4:
                if self.parameters['IsolatedCropMode']['value'][0]:
                    image_shape = (
                        self.parameters['IsolatedCropMode']['value'][1] / self.parameters['IsolatedCropMode']['value'][
                            3],
                        self.parameters['IsolatedCropMode']['value'][2] / self.parameters['IsolatedCropMode']['value'][
                            4])
                else:
                    image_shape = (
                        (self.parameters['Image']['value'][5] - self.parameters['Image']['value'][4] + 1) /
                        self.parameters['Image']['value'][1],
                        (self.parameters['Image']['value'][3] - self.parameters['Image']['value'][2] + 1) /
                        self.parameters['Image']['value'][0],)
            else:
                raise NotImplementedError('Read Mode %g' % self.parameters['ReadMode']['value'])

        dim = num_of_images * np.prod(image_shape)
        cimageArray = c_int * dim
        cimage = cimageArray()
        if '_logger' in self.__dict__:
            self._logger.debug('Getting AcquiredData for %i images with dimension %s' % (num_of_images, image_shape))
        try:
            self._dllWrapper('GetAcquiredData', inputs=({'type': c_int, 'value': dim},), outputs=(cimage,),
                             reverse=True)
            imageArray = []
            for i in range(len(cimage)):
                imageArray.append(cimage[i])
        except RuntimeWarning as e:
            if '_logger' in self.__dict__:
                self._logger.warn('Had a RuntimeWarning: %s' % e)
            imageArray = []
            for i in range(len(cimage)):
                imageArray.append(0)

        return imageArray, num_of_images, image_shape

    # @locked_action
    def SetImage(self, *params):
        """Set camera parameters for either the IsolatedCrop mode or Image mode

        Parameters
        ----------
        params  optional, inputs for either the IsolatedCrop mode or Image mode

        Returns
        -------

        """
        if self.parameters['IsolatedCropMode']['value'][0]:
            if len(params) == 0:
                params += (self.parameters['IsolatedCropMode']['value'])
            elif len(params) != 5:
                raise ValueError('Wrong number of parameters (need bool, cropheight, cropwidth, vbin, hbin')

            # Making sure we pass a valid set of parameters
            params = list(params)
            params[1] -= (params[1]) % params[3]
            params[2] -= (params[2]) % params[4]
            self.SetParameter('IsolatedCropMode', *params)
        else:
            if len(params) == 0:
                params = self.parameters['Image']['value']
            elif len(params) != 6:
                raise ValueError('Wrong number of parameters (need hbin, vbin, hstart, hend, vstart, vend')

            # Making sure we pass a valid set of parameters
            params = list(params)
            params[3] -= (params[3] - params[2] + 1) % params[0]
            params[5] -= (params[5] - params[4] + 1) % params[1]
            self.SetParameter('Image', *params)

    # @locked_action
    def SetROI(self, *params):
        if len(params) != 4:
            raise ValueError('Wrong number of inputs')
        current_binning = self.parameters['Image']['value'][:2]
        self.SetImage(*(current_binning + params))

    # @locked_action
    def SetBinning(self, *params):
        if len(params) not in [1, 2]:
            raise ValueError('Wrong number of inputs')
        if len(params) == 1:
            params += params
        current_ROI = self.parameters['Image']['value'][2:]
        self.SetImage(*(params + current_ROI))

    @locked_action
    def SetFastKinetics(self, n_rows=None):
        """Set the parameters for the Fast Kinetic mode

        Uses the already set parameters of exposure time, ReadMode, and binning as defaults to be passed to the Fast
        Kinetic parameter setter

        Parameters
        ----------
        n_rows

        Returns
        -------

        """

        if n_rows is None:
            n_rows = self.parameters['FastKinetics']['value'][0]

        series_Length = int(self.parameters['DetectorShape']['value'][1] / n_rows) - 1
        expT = self.parameters['AcquisitionTimings']['value'][0]
        mode = self.parameters['ReadMode']['value']
        hbin = self.parameters['Image']['value'][0]
        vbin = self.parameters['Image']['value'][1]
        offset = self.parameters['DetectorShape']['value'][1] - n_rows

        self.SetParameter('FastKinetics', n_rows, series_Length, expT, mode, hbin, vbin, offset)

    def GetStatus(self):
        error = self._dllWrapper('GetStatus', outputs=(c_int(),))
        self._status = ERROR_CODE[error]
        return self._status

    @locked_action
    def WaitForDriver(self):
        """
        This function is here because the dll.WaitForAcquisition does not work when in Accumulate mode

        Returns
        -------

        """
        status = c_int()
        self.dll.GetStatus(byref(status))
        while ERROR_CODE[status.value] == 'DRV_ACQUIRING':
            time.sleep(0.1)
            self.dll.GetStatus(byref(status))

    def CoolerON(self):
        self._dllWrapper('CoolerON')

    def CoolerOFF(self):
        self._dllWrapper('CoolerOFF')

    def IsCoolerOn(self):
        self.Cooler = self._dllWrapper('IsCoolerOn', outputs=(c_int(),))
        return self.Cooler

    def GetSeriesProgress(self):
        acc = c_long()
        series = c_long()
        error = self.dll.GetAcquisitionProgress(byref(acc), byref(series))
        if ERROR_CODE[error] == "DRV_SUCCESS":
            return series.value
        else:
            return None

    def GetAccumulationProgress(self):
        acc = c_long()
        series = c_long()
        error = self.dll.GetAcquisitionProgress(byref(acc), byref(series))
        if ERROR_CODE[error] == "DRV_SUCCESS":
            return acc.value
        else:
            return None

    def save_params_to_file(self, filepath=None):
        if filepath == None:
            data_file = df.create_file(set_current=False, mode='a')
        else:
            data_file = df.DataFile(filepath)
        data_file.create_dataset(name='AndorSettings', data=[], attrs=self.GetAllParameters())
        data_file.close()

    def load_params_from_file(self, filepath=None):
        if filepath == None:
            data_file = df.open_file(set_current=False, mode='r')
        else:
            data_file = df.DataFile(filepath)
        if 'AndorSettings' in data_file.keys():
            self.SetAllParameters(dict(data_file['AndorSettings'].attrs))
        else:
            self._logger.error('Load settings failed as "AndorSettings" does not exist')
        data_file.close()


parameters = dict(
    channel=dict(value=0),
    backgrounded=dict(value=False),
    background=dict(value=None),
    SoftwareWaitBetweenCaptures=dict(value=0),
    DetectorShape=dict(Get=dict(cmdName='GetDetector', Outputs=(c_int, c_int)), value=None),
    SerialNumber=dict(Get=dict(cmdName='GetCameraSerialNumber', Outputs=(c_int,)), value=None),
    HeadModel=dict(Get=dict(cmdName='GetHeadModel', Outputs=(c_char,) * 20), value=None),
    Capabilities=dict(Get=dict(cmdName='GetCapabilities', Outputs=(
        AndorCapabilities(sizeof(c_ulong) * 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),)), value=None),
    AcquisitionMode=dict(Set=dict(cmdName='SetAcquisitionMode', Inputs=(c_int,)), value=None),
    TriggerMode=dict(Set=dict(cmdName='SetTriggerMode', Inputs=(c_int,)), value=None),
    ReadMode=dict(Set=dict(cmdName='SetReadMode', Inputs=(c_int,)), value=None),
    CropMode=dict(Set=dict(cmdName='SetCropMode', Inputs=(c_int,) * 3), value=None),
    IsolatedCropMode=dict(Set=dict(cmdName='SetIsolatedCropMode', Inputs=(c_int,) * 5), value=(0,)),
    AcquisitionTimings=dict(Get=dict(cmdName='GetAcquisitionTimings', Outputs=(c_float, c_float, c_float)),
                            value=None),
    AccumCycleTime=dict(Set=dict(cmdName='SetAccumulationCycleTime', Inputs=(c_float,)),
                        Finally='AcquisitionTimings'),
    KinCycleTime=dict(Set=dict(cmdName='SetKineticCycleTime', Inputs=(c_float,)),
                      Finally='AcquisitionTimings'),
    Exposure=dict(Set=dict(cmdName='SetExposureTime', Inputs=(c_float,)), Get_from_fixed_prop='AcquisitionTimings'),
    Image=dict(Set=dict(cmdName='SetImage', Inputs=(c_int,) * 6), value=None),
    NAccum=dict(Set=dict(cmdName='SetNumberAccumulations', Inputs=(c_int,)), value=1),
    NKin=dict(Set=dict(cmdName='SetNumberKinetics', Inputs=(c_int,)), value=1),
    FastKinetics=dict(Set=dict(cmdName='SetFastKineticsEx', Inputs=(c_int, c_int, c_float,) + (c_int,) * 4)),
    EMGain=dict(Set=dict(cmdName='SetEMCCDGain', Inputs=(c_int,)),
                Get=dict(cmdName='GetEMCCDGain', Outputs=(c_int,)), value=None),
    EMAdvancedGain=dict(Set=dict(cmdName='SetEMAdvanced', Inputs=(c_int,)), value=None),
    EMMode=dict(Set=dict(cmdName='SetEMCCDGainMode', Inputs=(c_int,)), value=None),
    EMGainRange=dict(Set=dict(cmdName='GetEMCCDGainRange', Outputs=(c_int,) * 2), value=None),
    Shutter=dict(Set=dict(cmdName='SetShutter', Inputs=(c_int,) * 4), value=None),
    CoolerMode=dict(Set=dict(cmdName='SetCoolerMode', Inputs=(c_int,)), value=None),
    FanMode=dict(Set=dict(cmdName='SetFanMode', Inputs=(c_int,)), value=None),
    ImageFlip=dict(Set=dict(cmdName='SetImageFlip', Inputs=(c_int,) * 2), value=None),
    ImageRotate=dict(Set=dict(cmdName='SetImageRotate', Inputs=(c_int,)), value=None),
    CurrentTemperature=dict(Get=dict(cmdName='GetTemperature', Outputs=(c_int,)), value=None),
    SetTemperature=dict(Set=dict(cmdName='SetTemperature', Inputs=(c_int,)), value=None),
    OutAmp=dict(Set=dict(cmdName='SetOutputAmplifier', Inputs=(c_int,))),
    FrameTransferMode=dict(Set=dict(cmdName='SetFrameTransferMode', Inputs=(c_int,)), value=None),
    SingleTrack=dict(Set=dict(cmdName='SetSingleTrack', Inputs=(c_int,) * 2), value=None),
    MultiTrack=dict(Set=dict(cmdName='SetMultiTrack', Inputs=(c_int,) * 3, Outputs=(c_int,) * 2)),
    FVBHBin=dict(Set=dict(cmdName='SetFVBHBin', Inputs=(c_int,)), value=None),
    Spool=dict(Set=dict(cmdName='SetSpool', Inputs=(c_int, c_int, c_char, c_int)), value=None),
    NumVSSpeed=dict(Get=dict(cmdName='GetNumberVSSpeeds', Outputs=(c_int,)), value=None),
    NumHSSpeed=dict(Get=dict(cmdName='GetNumberHSSpeeds', Outputs=(c_int,),
                             Input_params=(('channel', c_int), ('OutAmp', c_int))), value=None),
    VSSpeed=dict(Set=dict(cmdName='SetVSSpeed', Inputs=(c_int,)), Get_from_prop='VSSpeeds', GetAfterSet=True),
    VSSpeeds=dict(Get=dict(cmdName='GetVSSpeed', Inputs=(c_int,), Outputs=(c_float,), Iterator='NumVSSpeed'),
                  GetAfterSet=True),
    # why no work?
    HSSpeed=dict(Set=dict(cmdName='SetHSSpeed', Inputs=(c_int,), Input_params=(('OutAmp', c_int),)),
                 Get_from_prop='HSSpeeds'),
    HSSpeeds=dict(Get=dict(cmdName='GetHSSpeed', Inputs=(c_int,) * 2, Iterator='NumHSSpeed', Outputs=(c_float,),
                           Input_params=(('channel', c_int), ('OutAmp', c_int),))),
    NumPreAmp=dict(Get=dict(cmdName='GetNumberPreAmpGains', Outputs=(c_int,))),
    PreAmpGains=dict(Get=dict(cmdName='GetPreAmpGain', Inputs=(c_int,), Outputs=(c_float,), Iterator='NumPreAmp')),
    PreAmpGain=dict(Set=dict(cmdName='SetPreAmpGain', Inputs=(c_int,)), Get_from_prop='PreAmpGains', GetAfterSet=True),
    NumADChannels=dict(Get=dict(cmdName='GetNumberADChannels', Outputs=(c_int,))),
    ADChannel=dict(Set=dict(cmdName='SetADChannel', Inputs=(c_int,))),
    BitDepth=dict(Get=dict(cmdName='GetBitDepth', Inputs=(c_int,), Outputs=(c_int,), Iterator='NumADChannels'))
)
for param_name in parameters:
    setattr(AndorBase, param_name, AndorParameter(param_name))


class Andor(Camera, AndorBase):
    #    Exposure = CameraParameter('Exposure', "The exposure time in s")
    #    AcquisitionMode = CameraParameter('AcquisitionMode')
    #    TriggerMode = CameraParameter('TriggerMode')
    metadata_property_names = ('Exposure', 'AcquisitionMode', 'TriggerMode', 'background')

    def __init__(self, settings_filepath=None, **kwargs):
        Camera.__init__(self)
        AndorBase.__init__(self)

        # self.wvl_to_pxl = kwargs['wvl_to_pxl']
        # self.magnification = kwargs['magnification']
        # self.pxl_size = kwargs['pxl_size']

        self.CurImage = None
        self.background = None
        self.x_axis = None

        if settings_filepath != None:
            self.load_params_from_file(settings_filepath)

    '''Used functions'''

    def Abort(self):
        self.isAborted = True
        self.abort()

    def raw_snapshot(self):
        try:
            imageArray, num_of_images, image_shape = self.capture()

            self.imageArray = imageArray

            # The image is reversed depending on whether you read in the conventional CCD register or the EM register, so we reverse it back
            if self.parameters['OutAmp']['value']:
                self.CurImage = np.reshape(self.imageArray, (num_of_images,) + image_shape)[..., ::-1]
            else:
                self.CurImage = np.reshape(self.imageArray, (num_of_images,) + image_shape)
            self.CurImage = self.bundle_metadata(self.CurImage)
            if len(self.CurImage) == 1:
                return 1, self.CurImage[0]
            else:
                return 1, self.CurImage
        except Exception as e:
            self._logger.warn("Couldn't Capture because %s" % e)

    def get_camera_parameter(self, parameter_name):
        return self.GetParameter(parameter_name)

    def set_camera_parameter(self, parameter_name, parameter_value):
        self.SetParameter(parameter_name, parameter_value)

    def get_qt_ui(self):
        if not hasattr(self, 'ui'):
            self.ui = AndorUI(self)
        elif not isinstance(self.ui, AndorUI):
            self.ui = AndorUI(self)
        return self.ui

    def get_control_widget(self):
        return self.get_qt_ui()

    def get_preview_widget(self):
        ui = self.get_qt_ui()
        if ui.DisplayWidget is None:
            ui.DisplayWidget = DisplayWidget()
        return self.ui.DisplayWidget

    #
    # def getRelevantParameters(self):
    #     relevant_parameters = ['AcquisitionMode', 'ReadMode', 'Image', 'Exposure', 'NKin']
    #     dicc = {}
    #     for param in relevant_parameters:
    #         dicc[param] = self.parameters[param]['value']
    #     return dicc
    # def setRelevantParameters(self, parameters):
    #     for param in parameters:
    #         if hasattr(parameters[param], '__iter__'):
    #             self.SetParameter(param, *parameters[param])
    #         else:
    #             self.SetParameter(param, parameters[param])

    '''Not-used functions'''

    # def SaveAsFITS(self, filename, type):
    #     error = self.dll.SaveAsFITS(filename, type)
    #     self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
    #     return ERROR_CODE[error]


# TODO: get the GUI to update when parameters are changed from the command line
class AndorUI(QtWidgets.QWidget):
    ImageUpdated = QtCore.Signal()

    def __init__(self, andor):
        assert isinstance(andor, Andor), "instrument must be an Andor"
        super(AndorUI, self).__init__()
        #        self.ImageUpdated = QtCore.SIGNAL('AndorImageUpdated')
        self.captureThread = None
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
        self.spinBoxNumAccum.valueChanged.connect(self.NumAccumChanged)
        self.spinBoxNumRows.valueChanged.connect(self.NumRowsChanged)
        self.spinBoxCenterRow.valueChanged.connect(self.NumRowsChanged)
        self.checkBoxROI.stateChanged.connect(self.ROI)
        self.checkBoxCrop.stateChanged.connect(self.IsolatedCrop)
        self.checkBoxCooler.stateChanged.connect(self.Cooler)
        # self.checkBoxAutoExp.stateChanged.connect(self.AutoExpose)
        self.checkBoxEMMode.stateChanged.connect(self.OutputAmplifierChanged)
        self.spinBoxEMGain.valueChanged.connect(self.EMGainChanged)
        self.lineEditExpT.returnPressed.connect(self.ExposureChanged)
        self.pushButtonDiv5.clicked.connect(lambda: self.ExposureChanged('/'))
        self.pushButtonTimes5.clicked.connect(lambda: self.ExposureChanged('x'))

        self.pushButtonCapture.clicked.connect(self.Capture)
        self.pushButtonLive.clicked.connect(self.Live)
        self.pushButtonAbort.clicked.connect(self.Abort)
        self.save_pushButton.clicked.connect(self.Save)
        self.pushButtonTakeBG.clicked.connect(self.take_background)
        self.checkBoxRemoveBG.stateChanged.connect(self.remove_background)
        self.referesh_groups_pushButton.clicked.connect(self.update_groups_box)

    @background_action
    def _constantlyUpdateTemperature(self):
        self._stopTemperatureThread = False
        self.Andor.GetParameter('CurrentTemperature')
        while np.abs(self.Andor.parameters['CurrentTemperature']['value'] -
                             self.Andor.parameters['SetTemperature']['value']) > 2:
            if self._stopTemperatureThread:
                break
            temp = self.Andor.GetParameter('CurrentTemperature')
            self.checkBoxCooler.setText('Cooler (%g)' % temp)
            for ii in range(100):
                if self._stopTemperatureThread:
                    return
                time.sleep(0.1)

    # GUI FUNCTIONS
    def updateGUI(self):
        trig_modes = {0: 0, 1: 1, 6: 2}
        self.comboBoxAcqMode.setCurrentIndex(self.Andor.parameters['AcquisitionMode']['value'] - 1)
        self.AcquisitionModeChanged()
        self.comboBoxReadMode.setCurrentIndex(self.Andor.parameters['ReadMode']['value'])
        self.ReadModeChanged()
        self.comboBoxTrigMode.setCurrentIndex(trig_modes[self.Andor.parameters['TriggerMode']['value']])
        self.TrigChanged()
        self.comboBoxBinning.setCurrentIndex(np.log2(self.Andor.parameters['Image']['value'][0]))
        self.BinningChanged()
        self.spinBoxNumFrames.setValue(self.Andor.parameters['NKin']['value'])

        self.Andor.GetParameter('AcquisitionTimings')
        self.lineEditExpT.setText(
            str(float('%#e' % self.Andor.parameters['AcquisitionTimings']['value'][0])).rstrip('0'))

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
        self.Andor.SetParameter('AcquisitionMode', available_modes.index(currentMode) + 1)

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
        self.Andor.SetParameter('ReadMode', available_modes.index(currentMode))
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

    #    def update_IsolatedCropMode(self,value):
    #        self.checkBoxCrop.setChec

    def callback_to_update_prop(self, propname):
        """Return a callback function that refreshes the named parameter."""

        def callback(value=None):
            getattr(self, 'update_' + propname)(value)

        return callback

    def TrigChanged(self):
        available_modes = {'Internal': 0, 'External': 1, 'ExternalStart': 6}
        currentMode = self.comboBoxTrigMode.currentText()
        self.Andor.SetParameter('TriggerMode', available_modes[currentMode])

    def OutputAmplifierChanged(self):
        if self.checkBoxEMMode.isChecked():
            self.Andor.SetParameter('OutAmp', 0)
        else:
            self.Andor.SetParameter('OutAmp', 1)
        if self.checkBoxCrop.isChecked():
            self.checkBoxCrop.setChecked(False)
            # self.ROI()

    def BinningChanged(self):
        current_binning = int(self.comboBoxBinning.currentText()[0])
        if self.Andor.parameters['IsolatedCropMode']['value'][0]:
            params = list(self.Andor.parameters['IsolatedCropMode']['value'])
            params[3] = current_binning
            params[4] = current_binning
            self.Andor._logger.debug('BinningChanged: %s' % str(params))
            self.Andor.SetImage(*params)
        else:
            self.Andor.SetImage(current_binning, current_binning, *self.Andor.parameters['Image']['value'][2:])
        self.Andor.SetParameter('FVBHBin', current_binning)

    def NumFramesChanged(self):
        num_frames = self.spinBoxNumFrames.value()
        self.Andor.SetParameter('NKin', num_frames)

    def NumAccumChanged(self):
        num_frames = self.spinBoxNumAccum.value()
        # self.Andor.SetNumberAccumulations(num_frames)
        self.Andor.SetParameter('NAccum', num_frames)

    def NumRowsChanged(self):
        num_rows = self.spinBoxNumRows.value()
        if self.Andor.parameters['AcquisitionMode']['value'] == 4:
            self.Andor.SetFastKinetics(num_rows)
        elif self.Andor.parameters['ReadMode']['value'] == 3:
            center_row = self.spinBoxCenterRow.value()
            if center_row - num_rows < 0:
                self.Andor._logger.info(
                    'Too many rows provided for Single Track mode. Using %g rows instead' % center_row)
                num_rows = center_row
            self.Andor.SetParameter('SingleTrack', center_row, num_rows)
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
        self.Andor.SetParameter('EMGain', gain)

    def IsolatedCrop(self):
        if self.DisplayWidget is None:
            return
        if hasattr(self.DisplayWidget, 'CrossHair1') and hasattr(self.DisplayWidget, 'CrossHair2'):
            current_binning = int(self.comboBoxBinning.currentText()[0])
            pos1 = self.DisplayWidget.CrossHair1.pos()
            pos2 = self.DisplayWidget.CrossHair2.pos()
            shape = self.Andor.parameters['DetectorShape']['value']
            if self.checkBoxEMMode.isChecked():
                minx, maxx = map(lambda x: int(x),
                                 (min(pos1[0], pos2[0]), max(pos1[0], pos2[0])))
                miny, maxy = map(lambda x: int(x),  # shape[1] -
                                 (min(pos1[1], pos2[1]), max(pos1[1], pos2[1])))
            else:
                maxx, minx = map(lambda x: shape[0] - int(x),
                                 (min(pos1[0], pos2[0]), max(pos1[0], pos2[0])))
                miny, maxy = map(lambda x: int(x),  # shape[1] -
                                 (min(pos1[1], pos2[1]), max(pos1[1], pos2[1])))
            if self.checkBoxCrop.isChecked():
                if self.checkBoxROI.isChecked():
                    self.checkBoxROI.setChecked(False)
                self.Andor.parameters['IsolatedCropMode']['value'] = (1,)
                self.Andor.SetImage(1, maxy, maxx, current_binning, current_binning)
                # if self.checkBoxEMMode.isChecked():
                #     self.Andor.SetImage(1, maxy, maxx, current_binning, current_binning)
                #     print maxy, maxx
                # else:
                #     self.Andor.SetImage(1, maxy, shape[0]-maxx, current_binning, current_binning)
                #     print maxy, shape[0] - maxx
            else:
                self.Andor.SetParameter('IsolatedCropMode', 0, maxy, maxx, current_binning, current_binning)
                self.Andor.SetImage()
        else:
            self.Andor._logger.warn("You can't crop an image using a DisplayWidget that doesn't have CrossHairs...")

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
            if 'AndorData' in self.data_file.keys():
                group = self.data_file['AndorData']
            else:
                group = self.data_file.create_group('AndorData')
        else:
            group = self.data_file[self.group_comboBox.currentText()]
        if np.shape(data)[0] == 1:
            data = data[0]
        if self.save_all_parameters == True:
            attrs = self.Andor.GetAllParameters()
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
        if self.DisplayWidget is None:
            return
        if hasattr(self.DisplayWidget, 'CrossHair1') and hasattr(self.DisplayWidget, 'CrossHair2'):
            hbin, vbin = self.Andor.parameters['Image']['value'][:2]
            if self.checkBoxROI.isChecked():
                if self.checkBoxCrop.isChecked():
                    self.checkBoxCrop.setChecked(False)
                pos1 = self.DisplayWidget.CrossHair1.pos()
                pos2 = self.DisplayWidget.CrossHair2.pos()
                shape = self.Andor.parameters['DetectorShape']['value']
                # print 'GUI ROI. CrossHair: ', pos1, pos2
                maxx, minx = map(lambda x: shape[0] - int(x),
                                 (min(pos1[0], pos2[0]), max(pos1[0], pos2[0])))
                miny, maxy = map(lambda x: int(x) + 1,  # shape[1] -
                                 (min(pos1[1], pos2[1]), max(pos1[1], pos2[1])))

                # print 'ROI. ImageInfo: ',hbin, vbin, minx, maxx, miny, maxy
                # if self.Andor.parameters['OutAmp']['value']:
                #     self.Andor.SetImage(hbin, vbin, shape[0]-maxx, shape[0]-minx, miny, maxy)
                # else:
                self.Andor.SetImage(hbin, vbin, minx, maxx, miny, maxy)
                # self.Andor.parameters['Image']['value'] = [hbin, vbin, minx, miny, maxx, maxy]
                # print 'GUI ROI. ShapeInfo: ', self.Andor.parameters['Image']
                # self.Andor.SetImage()
            else:
                self.Andor.SetParameter('Image', hbin, vbin, 1, self.Andor.parameters['DetectorShape']['value'][0],
                                        1, self.Andor.parameters['DetectorShape']['value'][1])
                # self.Andor.parameters['Image'] = [1, 1, self.Andor.parameters['DetectorShape'][0],
                #                                   self.Andor.parameters['DetectorShape'][1]]
                # self.Andor.SetImage()
        else:
            self.Andor._logger.warn("You can't set the ROI using a DisplayWidget that doesn't have CrossHairs...")

    def Capture(self, wait=True):
        if self.captureThread is not None:
            if not self.captureThread.isFinished():
                return
        self.captureThread = CaptureThread(self.Andor)
        self.captureThread.updateImage.connect(self.updateImage)
        self.captureThread.start()

        if wait:
            self.captureThread.wait()

    def Live(self, wait=True):
        if self.captureThread is not None:
            if not self.captureThread.isFinished():
                return
        self.captureThread = CaptureThread(self.Andor, live=True)
        #        self.connect(self.captureThread, self.captureThread.updateImage, self.updateImage)
        self.captureThread.updateImage.connect(self.updateImage)
        # self.captureThread.finished.connect(self.updateImage)
        self.captureThread.start()

        if wait:
            self.captureThread.wait()

    def Abort(self):
        # self.Andor.abort = True
        self.Andor.Abort()

    def updateImage(self):
        if self.DisplayWidget is None:
            self.DisplayWidget = DisplayWidget()
        if self.DisplayWidget.isHidden():
            self.DisplayWidget.show()

        # The offset is designed so that image ends up being displayed at the correct crosshair coordinates
        # The scale is used for scaling the image according to the binning, hence also preserving the crosshair coordinates
        if self.Andor.parameters['IsolatedCropMode']['value'][0]:
            # If the camera is in IsolatedCropMode, which side of the camera is being cropped depends on the amplifier being used
            if self.checkBoxEMMode.isChecked():
                offset = (0, 0)
            else:
                offset = (
                    (self.Andor.parameters['DetectorShape']['value'][0] -
                     self.Andor.parameters['IsolatedCropMode']['value'][2]), 0)
            scale = self.Andor.parameters['IsolatedCropMode']['value'][-2:]
        else:
            offset = ((self.Andor.parameters['DetectorShape']['value'][0] - self.Andor.parameters['Image']['value'][3]),
                      self.Andor.parameters['Image']['value'][4] - 1)
            scale = self.Andor.parameters['Image']['value'][:2]
        data = np.copy(self.Andor.CurImage)
        if np.shape(data[0]) == np.shape(self.Andor.background) and self.Andor.backgrounded == True:
            if self.Andor.backgrounded == True:
                for image_number in range(len(self.Andor.CurImage)):
                    data[image_number] = data[image_number] - self.Andor.background
        elif self.Andor.backgrounded == True:
            self.Andor._logger.info(
                'The background and the current image are different shapes and therefore cannot be subtracted')
        try:
            if self.Andor.x_axis == None or np.shape(self.Andor.CurImage)[-1] != np.shape(self.Andor.x_axis)[0]:
                xvals = np.linspace(0, self.Andor.CurImage.shape[-1] - 1, self.Andor.CurImage.shape[-1])
            else:

                xvals = self.Andor.x_axis
        except Exception as e:
            print e
        if len(self.Andor.CurImage.shape) == 2:
            if self.Andor.CurImage.shape[0] > self.DisplayWidget._max_num_line_plots:
                self.DisplayWidget.splitter.setSizes([1, 0])
                self.DisplayWidget.ImageDisplay.setImage(data, xvals=xvals, pos=offset, autoRange=False,
                                                         scale=scale)
            else:
                self.DisplayWidget.splitter.setSizes([0, 1])
                for ii in range(self.Andor.CurImage.shape[0]):
                    self.DisplayWidget.plot[ii].setData(x=xvals, y=data[ii])

        else:
            self.DisplayWidget.splitter.setSizes([1, 0])
            image = np.transpose(data, (0, 2, 1))
            zvals = 0.99 * np.linspace(0, image.shape[0] - 1, image.shape[0])
            if image.shape[0] == 1:
                image = image[0]
                self.DisplayWidget.ImageDisplay.setImage(image, xvals=zvals,
                                                         pos=offset, autoRange=False,
                                                         scale=scale)

            else:
                self.DisplayWidget.ImageDisplay.setImage(image, xvals=zvals,
                                                         pos=offset, autoRange=False,
                                                         scale=scale)
        self.ImageUpdated.emit()


class DisplayWidget(QtWidgets.QWidget):
    _max_num_line_plots = 4

    def __init__(self):
        QtWidgets.QWidget.__init__(self)

        uic.loadUi(os.path.join(os.path.dirname(__file__), 'CameraDefaultDisplay.ui'), self)

        self.ImageDisplay.getHistogramWidget().gradient.restoreState(Gradients.values()[1])
        self.plot = ()
        for ii in range(self._max_num_line_plots):
            self.plot += (self.LineDisplay.plot(pen=pyqtgraph.intColor(ii, self._max_num_line_plots)),)
        # self.plot1 = self.LineDisplay.plot(pen='y')
        # self.plot2 = self.LineDisplay.plot(pen='g')
        # self.plot3 = self.LineDisplay.plot(pen='b')
        # self.plot4 = self.LineDisplay.plot(pen='w')

        self.CrossHair1 = Crosshair('r')
        self.CrossHair2 = Crosshair('g')
        self.ImageDisplay.getView().addItem(self.CrossHair1)
        self.ImageDisplay.getView().addItem(self.CrossHair2)

        self.LineDisplay.showGrid(x=True, y=True)

        #        self.connect(self.CrossHair1, self.CrossHair1.CrossHairMoved, self.mouseMoved)
        #        self.connect(self.CrossHair2, self.CrossHair2.CrossHairMoved, self.mouseMoved)
        self.CrossHair1.CrossHairMoved.connect(self.mouseMoved)
        self.CrossHair2.CrossHairMoved.connect(self.mouseMoved)

        self.unit = 'pxl'
        self.splitter.setSizes([1, 0])

    def pxl_to_unit(self, pxl):
        return pxl

    def mouseMoved(self):
        x1 = self.CrossHair1.pos()[0]
        y1 = self.CrossHair1.pos()[1]
        x2 = self.CrossHair2.pos()[0]
        y2 = self.CrossHair2.pos()[1]

        xu1, yu1 = self.pxl_to_unit((x1, y1))
        xu2, yu2 = self.pxl_to_unit((x2, y2))

        self.labelCrossHairPositions.setText(
            "<span style='color: red'>Pixel: [%i,%i]px Unit: (%g, %g)%s</span>, " \
            "<span style='color: green'> Pixel: [%i,%i]px Unit: (%g, %g)%s</span>, " \
            "Delta pixel: [%i,%i]px Delta Unit: (%g, %g)%s"
            % (x1, y1, xu1, yu1, self.unit, x2, y2, xu2, yu2, self.unit, abs(x1 - x2), abs(y1 - y2), abs(xu1 - xu2),
               abs(yu1 - yu2), self.unit))


class Crosshair(pyqtgraph.GraphicsObject):
    CrossHairMoved = QtCore.Signal()
    Released = QtCore.Signal()

    def __init__(self, color):
        super(Crosshair, self).__init__()
        self.color = color

    #        self.CrossHairMoved = QtCore.SIGNAL('CrossHairMoved')
    #        self.Released = QtCore.SIGNAL('CrossHairReleased')

    def paint(self, p, *args):
        p.setPen(pyqtgraph.mkPen(self.color))
        p.drawLine(-2, 0, 2, 0)
        p.drawLine(0, -2, 0, 2)

    def boundingRect(self):
        return QtCore.QRectF(-2, -2, 4, 4)

    def mouseDragEvent(self, ev):
        ev.accept()
        if ev.isStart():
            self.startPos = self.pos()
        elif ev.isFinish():
            self.setPos(*map(int, self.pos()))
        else:
            self.setPos(self.startPos + ev.pos() - ev.buttonDownPos())

        #        self.emit(self.CrossHairMoved)
        self.CrossHairMoved.emit()

        # def mouseReleaseEvent(self, ev):
        #     print 'CrossHair released'
        #     ev.accept()
        #     self.setPos(map(int, self.pos()))
        #     self.emit(self.Released)


class CaptureThread(QtCore.QThread):
    updateImage = QtCore.Signal()

    def __init__(self, andor, live=False):
        QtCore.QThread.__init__(self, parent=None)
        #        self.updateImage = QtCore.SIGNAL("UpdateImage")
        self.Andor = andor
        self.live = live

    def stop(self):
        self.isAborted = True
        self.wait()

    def run(self):
        if self.live:
            self.Andor.isAborted = False
            while not self.Andor.isAborted:
                try:
                    self.SingleAcquire()
                except AndorWarning:
                    pass
        else:
            self.SingleAcquire()
        self.Andor.isAborted = False

    def SingleAcquire(self):
        self.Andor.raw_snapshot()
        if self.Andor.parameters['AcquisitionMode']['value'] in [1, 2] and self.Andor.parameters['NKin']['value'] > 1:
            if self.Andor.parameters['SoftwareWaitBetweenCaptures']['value']:
                time.sleep(self.Andor.parameters['SoftwareWaitBetweenCaptures']['value'])

            final_array = np.zeros(
                (self.Andor.parameters['NKin']['value'],) + self.Andor.CurImage.shape[1:])
            final_array[0] = self.Andor.CurImage[0]
            for ii in range(1, self.Andor.parameters['NKin']['value']):
                if self.Andor.isAborted:
                    break
                self.Andor.raw_snapshot()
                final_array[ii] = self.Andor.CurImage[0]
            self.Andor.CurImage = final_array

        self.updateImage.emit()


# self.emit(self.updateImage)


class WaitThread(QtCore.QThread):
    def __init__(self, andor):
        QtCore.QThread.__init__(self, parent=None)
        self.Andor = andor

    def run(self):
        self.Andor._logger.infor('Waiting for temperature to come up')
        temp = 30
        try:
            temp = self.Andor._dllWrapper('GetTemperature', outputs=(c_int(),))[0]
        except AndorWarning as warn:
            if warn.error_name != 'DRV_TEMP_OFF':
                raise warn
        if self.Andor.IsCoolerOn():
            self.Andor.CoolerOFF()
        if temp < 30:
            toggle = windll.user32.MessageBoxA(0, 'Camera is cold (%g), do you want to wait before ShutDown? '
                                                  '\n Not waiting can cause irreversible damage' % temp, '', 4)
            if toggle == 7:
                return
            else:
                while temp < -20:
                    self.Andor._logger.info('Waiting for temperature to come up. %g' % temp)
                    time.sleep(10)
                    try:
                        temp = self.Andor._dllWrapper('GetTemperature', outputs=(c_int(),))[0]
                    except AndorWarning as warn:
                        if warn.error_name != 'DRV_TEMP_OFF':
                            raise warn


ERROR_CODE = {
    20001: "DRV_ERROR_CODES",
    20002: "DRV_SUCCESS",
    20003: "DRV_VXNOTINSTALLED",
    20006: "DRV_ERROR_FILELOAD",
    20007: "DRV_ERROR_VXD_INIT",
    20010: "DRV_ERROR_PAGELOCK",
    20011: "DRV_ERROR_PAGE_UNLOCK",
    20013: "DRV_ERROR_ACK",
    20024: "DRV_NO_NEW_DATA",
    20026: "DRV_SPOOLERROR",
    20034: "DRV_TEMP_OFF",
    20035: "DRV_TEMP_NOT_STABILIZED",
    20036: "DRV_TEMP_STABILIZED",
    20037: "DRV_TEMP_NOT_REACHED",
    20038: "DRV_TEMP_OUT_RANGE",
    20039: "DRV_TEMP_NOT_SUPPORTED",
    20040: "DRV_TEMP_DRIFT",
    20050: "DRV_COF_NOTLOADED",
    20053: "DRV_FLEXERROR",
    20066: "DRV_P1INVALID",
    20067: "DRV_P2INVALID",
    20068: "DRV_P3INVALID",
    20069: "DRV_P4INVALID",
    20070: "DRV_INIERROR",
    20071: "DRV_COERROR",
    20072: "DRV_ACQUIRING",
    20073: "DRV_IDLE",
    20074: "DRV_TEMPCYCLE",
    20075: "DRV_NOT_INITIALIZED",
    20076: "DRV_P5INVALID",
    20077: "DRV_P6INVALID",
    20083: "P7_INVALID",
    20089: "DRV_USBERROR",
    20091: "DRV_NOT_SUPPORTED",
    20095: "DRV_INVALID_TRIGGER_MODE",
    20099: "DRV_BINNING_ERROR",
    20990: "DRV_NOCAMERA",
    20991: "DRV_NOT_SUPPORTED",
    20992: "DRV_NOT_AVAILABLE"
}

if __name__ == '__main__':
    andor = Andor()  # wvl_to_pxl=32.5 / 1600, magnification=30, pxl_size=16)
    app = QtWidgets.QApplication([])
    ui1 = andor.get_control_widget()
    ui2 = andor.get_preview_widget()
    print ui1, ui2

    ui1.show()
    ui2.show()
    # andor.show_gui(True)
