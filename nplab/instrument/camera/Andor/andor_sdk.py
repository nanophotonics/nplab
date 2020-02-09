# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from builtins import zip
from builtins import str
from builtins import range
from builtins import object
from past.utils import old_div
from nplab.instrument.camera import CameraParameter
from nplab.utils.thread_utils import locked_action
from nplab.utils.log import create_logger
import nplab.datafile as df
import os
import platform
import time
from ctypes import *
import numpy as np
import tempfile
import shutil


LOGGER = create_logger('Andor SDK')
TEMPORARY_PREFIX = '_andortemporary'


def to_bits(integer):
    """ Returns a list of bits representing the integer in base 2. Used to parse over the capabilities
    :param integer:
    :return: list of 1s and 0s
    """
    bits = integer.bit_length()
    return [1 if integer & (1 << (bits-1-n)) else 0 for n in range(bits)]


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


class AndorParameter(CameraParameter):
    """Light wrapper of the CameraParameter that ensures the getting and setting of values takes care of possible
    multiple values"""

    def __init__(self, parameter_name, doc=None, read_back=True):
        super(AndorParameter, self).__init__(parameter_name, doc=doc, read_back=read_back)

    def fget(self, obj):
        value = super(AndorParameter, self).fget(obj)
        if (type(value) == tuple) and (len(value) == 1):
            return value[0]
        else:
            return value

    def fset(self, obj, value):
        if type(value) != tuple:
            value = (value,)
        super(AndorParameter, self).fset(obj, value)


class AndorBase(object):
    """Base code handling the Andor SDK

    Most of the code for this class is setting up a general way of reading and writing parameters, which are then set up
    from the parameters dictionary after class definition.

    The self.parameters dictionary contains all the information necessary to deal with the camera parameters. Each
    entry in the dictionary corresponds to a specific parameter and allows you to specify the Get and/or Set command
    name and datatype (from the .dll).

    Most parameters are straightforward, since the Andor dll either has inputs (for setting parameters) or outputs
    (for getting parameters). So you can just intuitively call GetParameter(name) or SetParameter(name, value) with name
    and value provided by the user.
    Some parameters, like VSSpeed, HSSpeed..., require inputs to get outputs, so the user must say, e.g.,
        Andor.GetParameter('VSSpeed', 0)
    Which does not return the current VSSpeed, but the VSSpeed (in microseconds) of the setting 0.
    """
    def start(self, camera_index=None):
        if not hasattr(self, '_logger'):
            self._logger = LOGGER

        if platform.system() == 'Windows':
            directory = os.path.dirname(__file__)
            bitness = platform.architecture()[0][:2]  # either 32 or 64
            original_file = "%s/atmcd%sd.dll" % (directory, bitness)

            if bitness == '32':
                self.dll = windll.LoadLibrary(original_file)
            elif bitness == '64':
                self.dll = CDLL(original_file)
            else:
                raise Exception("Cannot detect Windows architecture")
        elif platform.system() == "Linux":
            original_file = "usr/local/lib/libandor.so"
            self.dll = cdll.LoadLibrary(original_file)
        else:
            raise Exception("Cannot detect operating system for Andor")
        self.parameters = parameters
        self._parameters = dict()
        for key, value in list(parameters.items()):
            if 'value' in value:
                self._parameters[key] = value['value']
            else:
                self._parameters[key] = None

        self.camera_index = camera_index
        if camera_index is None:
            self.camera_index = 0
        if self.get_andor_parameter('AvailableCameras') > 1:
            if camera_index is None:
                self._logger.warn('More than one camera available, but no index provided. Initializing camera 0')
            camera_handle = self.get_andor_parameter('CameraHandle', self.camera_index)
            self.set_andor_parameter('CurrentCamera', camera_handle)
        self.initialize()

    def end(self):
        """ Safe shutdown procedure """
        # If the camera is a Classic or iCCD, wait for the temperature to be higher than -20 before shutting down
        if self.Capabilities['CameraType'] in [3, 4]:
            if self.cooler:
                self.cooler = 0
            while self.CurrentTemperature < -20:
                print('Waiting')
                time.sleep(1)
        self._logger.info('Shutting down')
        self._dll_wrapper('ShutDown')

    def _set_dll_camera(self):
        """Ensures the DLL library is pointing to the correct instrument for any particular instances of this class"""
        camera_handle = c_uint()
        error = getattr(self.dll, 'GetCameraHandle')(c_uint(self.camera_index), byref(camera_handle))
        self._error_handler(error)

        error = getattr(self.dll, 'SetCurrentCamera')(camera_handle)
        self._error_handler(error)

    '''Base functions'''

    @locked_action
    def _dll_wrapper(self, funcname, inputs=(), outputs=(), reverse=False):
        """Handler for all the .dll calls of the Andor

        :param funcname:    name of the dll function to be called
        :param inputs:      inputs to be handed in to the dll function
        :param outputs:     outputs to be expected from the dll
        :param reverse:     bool. whether to have the inputs first or the outputs first when calling the dll
        :return:
        """

        self._set_dll_camera()

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
        self._error_handler(error, funcname, *(inputs + outputs))

        return_values = ()
        for output in outputs:
            if hasattr(output, 'value'):
                return_values += (output.value,)
            if isinstance(output, AndorCapabilities):
                dicc = {}
                for key, value in output._fields_:
                    dicc[key[2:]] = getattr(output, key)
                return_values += (dicc,)
        if len(return_values) == 1:
            return return_values[0]
        else:
            return return_values

    def _error_handler(self, error, funcname='', *args):
        self._logger.debug("[%s]: %s %s" % (funcname, ERROR_CODE[error], str(args)))
        if funcname == 'GetTemperature':
            return
        if error != 20002:
            raise AndorWarning(error, funcname, ERROR_CODE[error])

    def set_andor_parameter(self, param_loc, *inputs):
        """Parameter setter

        Using the information contained in the self.parameters dictionary, send a general parameter set command to the
        Andor. The command name, and number of inputs and their types are stored in the self.parameters

        :param param_loc: dictionary key of self.parameters
        :param inputs: inputs required to set the particular parameter. Must be at least one
        :return:
        """
        if len(inputs) == 1 and type(inputs[0]) == tuple:
            if len(np.shape(inputs)) == 2:
                inputs = inputs[0]
            elif len(np.shape(inputs)) == 3:
                inputs = inputs[0][0]
        if 'not_supported' in self.parameters[param_loc] and self.parameters[param_loc]['not_supported']:
            return
        if 'Set' in self.parameters[param_loc]:
            func = self.parameters[param_loc]['Set']

            form_in = ()
            if 'Input_params' in func:
                for input_param in func['Input_params']:
                    form_in += ({'value': getattr(self, input_param[0]), 'type': input_param[1]},)
            for ii in range(len(inputs)):
                form_in += ({'value': inputs[ii], 'type': func['Inputs'][ii]},)
            try:
                self._dll_wrapper(func['cmdName'], inputs=form_in)

                if len(inputs) == 1:
                    self.parameters[param_loc]['value'] = inputs[0]
                    self._parameters[param_loc] = inputs[0]
                else:
                    self.parameters[param_loc]['value'] = inputs
                    self._parameters[param_loc] = inputs

                if 'Finally' in self.parameters[param_loc]:
                    self.get_andor_parameter(self.parameters[param_loc]['Finally'])
            except AndorWarning as andor_warning:
                if andor_warning.error_name == 'DRV_NOT_SUPPORTED':
                    if self.parameters[param_loc]['value'] is None:
                        self._logger.error('Not supported parameter and None value in the parameter dictionary')
                    else:
                        self.parameters[param_loc]['not_supported'] = True
                        inputs = self.parameters[param_loc]['value']
                        if not isinstance(inputs, tuple):
                            inputs = (inputs, )
                else:
                    self._logger.warn(andor_warning)

        if 'Get' not in list(self.parameters[param_loc].keys()):
            if len(inputs) == 1:
                setattr(self, '_' + param_loc, inputs[0])
            else:
                setattr(self, '_' + param_loc, inputs)
            self.parameters[param_loc]['value'] = getattr(self, '_' + param_loc)
            self._parameters[param_loc] = getattr(self, '_' + param_loc)

    def get_andor_parameter(self, param_loc, *inputs):
        """Parameter getter

        Using the information contained in the self.parameters dictionary, send a general parameter get command to the
        Andor. The command name, and number of inputs and their types are stored in the self.parameters

        :param param_loc: dictionary key of self.parameters
        :param inputs: optional inputs for getting the specific parameter
        :return:
        """
        if 'not_supported' in self.parameters[param_loc]:
            self._logger.debug('Ignoring get %s because it is not supported' % param_loc)
            self.parameters[param_loc]['value'] = getattr(self, '_' + param_loc)
            self._parameters[param_loc] = getattr(self, '_' + param_loc)
            return getattr(self, '_' + param_loc)
        if 'Get' in list(self.parameters[param_loc].keys()):
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
            if 'Iterator' not in list(func.keys()):
                vals = self._dll_wrapper(func['cmdName'], inputs=form_in, outputs=form_out)
            else:
                vals = ()
                for i in range(getattr(self, func['Iterator'])):
                    form_in_iterator = form_in + ({'value': i, 'type': c_int},)
                    vals += (self._dll_wrapper(func['cmdName'], inputs=form_in_iterator, outputs=form_out),)
            self.parameters[param_loc]['value'] = vals
            self._parameters[param_loc] = vals
            return vals
        elif 'Get_from_prop' in list(self.parameters[param_loc].keys()) and hasattr(self, '_' + param_loc):
            vals = getattr(self, self.parameters[param_loc]['Get_from_prop'])[getattr(self, '_' + param_loc)]
            self.parameters[param_loc]['value'] = vals
            self._parameters[param_loc] = vals
            return vals
        elif 'Get_from_fixed_prop' in list(self.parameters[param_loc].keys()):
            vals = getattr(self, self.parameters[param_loc]['Get_from_fixed_prop'])[0]
            self.parameters[param_loc]['value'] = vals
            self._parameters[param_loc] = vals
            return vals

        elif hasattr(self, '_' + param_loc):
            self.parameters[param_loc]['value'] = getattr(self, '_' + param_loc)
            self._parameters[param_loc] = getattr(self, '_' + param_loc)
            return getattr(self, '_' + param_loc)
        else:
            self._logger.info('The ' + param_loc + ' has not previously been set!')
            return None

    def get_andor_parameters(self):
        """Gets all the parameters that can be gotten

        :return: an up to date parameters dict containing only values and names
        """
        param_dict = dict()
        for param in self.parameters:
            param_dict[param] = getattr(self, param)
        return

    def set_andor_parameters(self, parameter_dictionary):
        """Sets all parameters tha can be set

        :param parameter_dictionary: dictionary of parameters to be set
        :return:
        """

        assert isinstance(parameter_dictionary, dict)
        for name, value in list(parameter_dictionary.items()):
            if not hasattr(self, name):
                self._logger.warn('The parameter ' + name + 'does not exist and therefore cannot be set')
                continue
            if value is None:
                self._logger.info('%s has not been set, as the value provided was "None" ' % name)
                continue

            if 'Get_from_prop' in self.parameters[name]:
                value = getattr(self, self.parameters[name]['Get_from_prop'])[
                    np.where(np.array(getattr(self, self.parameters[name]['Get_from_prop'])) == value)[0][0]]
            try:
                setattr(self, name, value)
            except Exception as e:
                self._logger.warn('Failed to set %s because %s' % (name, e))

    '''Used functions'''

    @property
    def capabilities(self):
        """Parsing of the Andor capabilities

        Transforming bit values contained in the self.Capabilities attribute into human-understandable parameters, as
        given by the manual

        :return:
        """
        capabilities = dict(AcqModes=[], ReadModes=[], FTReadModes=[], TriggerModes=[], CameraType=None, PixelMode=[],
                            SetFunctions=[], GetFunctions=[], Features=[], PCICard=None, EMGainCapability=[])

        bits = to_bits(self.Capabilities['AcqModes'])
        keys = ['Single', 'Video', 'Accumulate', 'Kinetic', 'FrameTransfer', 'FastKinetic', 'Overlap']
        for bit, key in zip(bits, keys):
            if bit:
                capabilities['AcqModes'] += [key]

        bits = to_bits(self.Capabilities['ReadModes'])
        keys = ['FullImage', 'SubImage', 'SingleTrack', 'FVB', 'MultiTrack', 'RandomTrack']
        for bit, key in zip(bits, keys):
            if bit:
                capabilities['ReadModes'] += [key]

        bits = to_bits(self.Capabilities['FTReadModes'])  # Frame transfer read modes
        keys = ['FullImage', 'SubImage', 'SingleTrack', 'FVB', 'MultiTrack', 'RandomTrack']
        for bit, key in zip(bits, keys):
            if bit:
                capabilities['FTReadModes'] += [key]

        bits = to_bits(self.Capabilities['TriggerModes'])
        keys = ['Internal', 'External', 'External_FVB_EM', 'Continuous',
                'ExternalStart', 'Bulb', 'ExternalExposure', 'Inverted']
        for bit, key in zip(bits, keys):
            if bit:
                capabilities['TriggerModes'] += [key]

        keys = ['PDA', 'iXon', 'iCCD', 'EMCCD', 'CCD', 'iStar', 'Video', 'iDus', 'Newton',
                'Surcam', 'USBiStar', 'Luca', 'Reserved', 'iKon', 'InGaAs', 'iVac', 'Clara']
        capabilities['CameraType'] = keys[int(self.Capabilities['CameraType'])]

        bits = to_bits(self.Capabilities['PixelMode'])
        keys = ['8bit', '14bit', '16bit', '32bit', 'mono', 'RGB', 'CMY']
        for bit, key in zip(bits, keys):
            if bit:
                capabilities['PixelMode'] += [key]

        bits = to_bits(self.Capabilities['SetFunctions'])
        keys = ['VSSpeed', 'HSSpeed', 'Temperature', 'MCPGain', 'EMCCDGain', 'BaselineClamp', 'VSAmplitude',
                'HighCapacity', 'BaselineOffset', 'PreAmpGain', 'CropMode/IsolatedCropMode', 'DMAParameters',
                'HorizontalBin', 'MultiTrackHRange', 'RandomTracks', 'EMAdvanced']
        for bit, key in zip(bits, keys):
            if bit:
                capabilities['SetFunctions'] += [key]

        bits = to_bits(self.Capabilities['GetFunctions'])
        keys = ['Temperature', 'TemperatureRange', 'Detector', 'MCPGain', 'EMCCDGain', 'BaselineClamp']
        for bit, key in zip(bits, keys):
            if bit:
                capabilities['GetFunctions'] += [key]

        bits = to_bits(self.Capabilities['Features'])
        keys = ['Status', 'DriverEvent', 'Spool', 'Shutter', 'ShutterEx', 'I2C', 'SaturationEvent', 'FanMode',
                'LowFanMode', 'TemperatureDuringAcquitisition', 'KeepClean', 'Internal', 'FTandExternalExposure',
                'KineticAndExternalExposure', 'Internal', 'Internal', 'IOcontrol', 'PhotonCounting', 'CountConvert',
                'DualMode']
        for bit, key in zip(bits, keys):
            if bit:
                capabilities['Features'] += [key]

        capabilities['PCICard'] = int(self.Capabilities['PCICard'])

        bits = to_bits(self.Capabilities['EMGainCapability'])
        keys = ['8bit', '12bit', 'Linear12', 'Real12']
        for bit, key in zip(bits, keys):
            if bit:
                capabilities['EMGainCapability'] += [key]

        return capabilities

    def abort(self):
        try:
            self._dll_wrapper('AbortAcquisition')
        except AndorWarning:
            pass

    def initialize(self):
        """Sets the initial parameters for the Andor typical for our experiments"""
        self._dll_wrapper('Initialize', outputs=(c_char(),))
        self.channel = 0
        self.set_andor_parameter('ReadMode', 4)
        self.set_andor_parameter('AcquisitionMode', 1)
        self.set_andor_parameter('TriggerMode', 0)
        self.set_andor_parameter('Exposure', 0.01)
        detector_shape = self.get_andor_parameter('DetectorShape')
        self.set_andor_parameter('Image', 1, 1, 1, detector_shape[0], 1, detector_shape[1])
        self.set_andor_parameter('Shutter', 1, 0, 1, 1)
        self.set_andor_parameter('SetTemperature', -90)
        self.set_andor_parameter('CoolerMode', 0)
        self.set_andor_parameter('FanMode', 0)
        self.set_andor_parameter('OutAmp', 1) # This means EMCCD off - this is the default mode
        self.cooler = 1

    @locked_action
    def capture(self):
        """Capture an image

        Wraps the three steps required for a camera acquisition: StartAcquisition, WaitForAcquisition and
        GetAcquiredData. The function also takes care of ensuring that the correct shape of array is passed to the
        GetAcquiredData call, according to the currently set parameters of the camera.

        :return:
            np.array    2D or 3D array of the captured image(s)
            int         number of images taken
            tuple       shape of the images taken
        """
        self._dll_wrapper('StartAcquisition')
        self._dll_wrapper('WaitForAcquisition')
        self.wait_for_driver()
        if self._parameters['AcquisitionMode'] == 4:
            num_of_images = 1  # self.parameters['FastKinetics']['value'][1]
            image_shape = (self._parameters['FastKinetics'][-1], self._parameters['DetectorShape'][0])
        else:
            if self._parameters['AcquisitionMode'] == 1:
                num_of_images = 1
            elif self._parameters['AcquisitionMode'] == 2:
                num_of_images = 1
            elif self._parameters['AcquisitionMode'] == 3:
                num_of_images = self._parameters['NKin']
            else:
                raise NotImplementedError('Acquisition Mode %g' % self._parameters['AcquisitionMode'])

            if self._parameters['ReadMode'] == 0:
                if self._parameters['IsolatedCropMode'][0]:
                    image_shape = (old_div(self._parameters['IsolatedCropMode'][2], self._parameters['IsolatedCropMode'][4]), )
                else:
                    image_shape = (old_div(self._parameters['DetectorShape'][0], self._parameters['FVBHBin']), )
            elif self._parameters['ReadMode'] == 3:
                image_shape = (self._parameters['DetectorShape'][0],)
            elif self._parameters['ReadMode'] == 4:
                # if self._parameters['IsolatedCropMode'][0]:
                #     image_shape = (
                #         self._parameters['IsolatedCropMode'][1] / self._parameters['IsolatedCropMode'][3],
                #         self._parameters['IsolatedCropMode'][2] / self._parameters['IsolatedCropMode'][4])
                # else:
                image_shape = (
                    old_div((self._parameters['Image'][5] - self._parameters['Image'][4] + 1), self._parameters['Image'][1]),
                    old_div((self._parameters['Image'][3] - self._parameters['Image'][2] + 1), self._parameters['Image'][0]),)
            else:
                raise NotImplementedError('Read Mode %g' % self._parameters['ReadMode'])

        image_shape = tuple([int(x) for x in image_shape])
        dim = num_of_images * np.prod(image_shape)
        cimageArray = c_int * dim
        cimage = cimageArray()
        self._logger.debug('Getting AcquiredData for %i images with dimension %s' % (num_of_images, image_shape))
        try:
            self._dll_wrapper('GetAcquiredData', inputs=({'type': c_int, 'value': dim},), outputs=(cimage,),
                              reverse=True)
            imageArray = []
            for i in range(len(cimage)):
                imageArray.append(cimage[i])
        except RuntimeWarning as e:
            self._logger.warn('Had a RuntimeWarning: %s' % e)
            imageArray = []
            for i in range(len(cimage)):
                imageArray.append(0)

        return imageArray, num_of_images, image_shape

    @property
    def Image(self):
        return self.get_andor_parameter('Image')

    @Image.setter
    def Image(self, value):
        """Ensures a valid image shape is passed

        e.g. if binning is 2x2, and an image with an odd number of pixels along one direction is passed, this function
        rounds it down to the nearest even number, providing a valid image shape

        :param value:
        :return:
        """
        if len(value) == 4:
            image = self._parameters['Image']
            value = image[:2] + value
        # Making sure we pass a valid set of parameters
        value = list(value)
        value[3] -= (value[3] - value[2] + 1) % value[0]
        value[5] -= (value[5] - value[4] + 1) % value[1]

        self.set_andor_parameter('Image', *value)

        crop = self.IsolatedCropMode
        if crop is not None:
            crop = [crop[0], value[5], value[3], value[0], value[1]]
        else:
            crop = [0, value[5], value[3], value[0], value[1]]
        self.set_andor_parameter('IsolatedCropMode', *crop)

    @locked_action
    def set_fast_kinetics(self, n_rows=None):
        """Set the parameters for the Fast Kinetic mode

        Uses the already set parameters of exposure time, ReadMode, and binning as defaults to be passed to the Fast
        Kinetic parameter setter

        :param n_rows: int. Number of rows to use
        :return:
        """

        if n_rows is None:
            n_rows = self._parameters['FastKinetics'][0]

        series_Length = int(old_div(self._parameters['DetectorShape'][1], n_rows)) - 1
        expT = self._parameters['AcquisitionTimings'][0]
        mode = self._parameters['ReadMode']
        hbin = self._parameters['Image'][0]
        vbin = self._parameters['Image'][1]
        offset = self._parameters['DetectorShape'][1] - n_rows

        self.set_andor_parameter('FastKinetics', n_rows, series_Length, expT, mode, hbin, vbin, offset)

    @property
    def status(self):
        error = self._dll_wrapper('GetStatus', outputs=(c_int(),))
        return ERROR_CODE[error]

    @locked_action
    def wait_for_driver(self):
        """This function is here because the dll.WaitForAcquisition does not work when in Accumulate mode"""
        status = c_int()
        self.dll.GetStatus(byref(status))
        while ERROR_CODE[status.value] == 'DRV_ACQUIRING':
            time.sleep(0.1)
            self.dll.GetStatus(byref(status))

    @property
    def cooler(self):
        return self._dll_wrapper('IsCoolerOn', outputs=(c_int(),))

    @cooler.setter
    def cooler(self, value):
        if value:
            self._dll_wrapper('CoolerON')
        else:
            self._dll_wrapper('CoolerOFF')

    def get_series_progress(self):
        acc = c_long()
        series = c_long()
        error = self.dll.GetAcquisitionProgress(byref(acc), byref(series))
        if ERROR_CODE[error] == "DRV_SUCCESS":
            return series.value
        else:
            return None

    def get_accumulation_progress(self):
        acc = c_long()
        series = c_long()
        error = self.dll.GetAcquisitionProgress(byref(acc), byref(series))
        if ERROR_CODE[error] == "DRV_SUCCESS":
            return acc.value
        else:
            return None

    def save_params_to_file(self, filepath=None):
        if filepath is None:
            data_file = df.create_file(set_current=False, mode='a')
        else:
            data_file = df.DataFile(filepath)
        data_file.create_dataset(name='AndorSettings', data=[], attrs=self.get_andor_parameters())
        data_file.close()

    def load_params_from_file(self, filepath=None):
        if filepath is None:
            data_file = df.open_file(set_current=False, mode='r')
        else:
            data_file = df.DataFile(filepath)
        if 'AndorSettings' in list(data_file.keys()):
            self.set_andor_parameters(dict(data_file['AndorSettings'].attrs))
        else:
            self._logger.error('Load settings failed as "AndorSettings" does not exist')
        data_file.close()


parameters = dict(
    AvailableCameras=dict(Get=dict(cmdName='GetAvailableCameras', Outputs=(c_uint,)), value=None),
    CurrentCamera=dict(Get=dict(cmdName='GetCurrentCamera', Outputs=(c_uint,)),
                       Set=dict(cmdName='SetCurrentCamera', Inputs=(c_uint,))),
    CameraHandle=dict(Get=dict(cmdName='GetCameraHandle', Outputs=(c_uint,), Inputs=(c_uint, ))),
    channel=dict(value=0),
    PixelSize=dict(Get=dict(cmdName='GetPixelSize', Outputs=(c_float, c_float))),
    SoftwareWaitBetweenCaptures=dict(value=0),
    SoftwareVersion=dict(Get=dict(cmdName='GetSoftwareVersion', Outputs=(c_int, c_int, c_int, c_int, c_int, c_int))),
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
    FVBHBin=dict(Set=dict(cmdName='SetFVBHBin', Inputs=(c_int,)), value=1),
    Spool=dict(Set=dict(cmdName='SetSpool', Inputs=(c_int, c_int, c_char, c_int)), value=None),
    NumVSSpeed=dict(Get=dict(cmdName='GetNumberVSSpeeds', Outputs=(c_int,)), value=None),
    NumHSSpeed=dict(Get=dict(cmdName='GetNumberHSSpeeds', Outputs=(c_int,),
                             Input_params=(('channel', c_int), ('OutAmp', c_int))), value=None),
    VSSpeed=dict(Set=dict(cmdName='SetVSSpeed', Inputs=(c_int,)), Get_from_prop='VSSpeeds'),
    VSSpeeds=dict(Get=dict(cmdName='GetVSSpeed', Inputs=(c_int,), Outputs=(c_float,), Iterator='NumVSSpeed')),
    # why no work?
    HSSpeed=dict(Set=dict(cmdName='SetHSSpeed', Inputs=(c_int,), Input_params=(('OutAmp', c_int),)),
                 Get_from_prop='HSSpeeds'),
    HSSpeeds=dict(Get=dict(cmdName='GetHSSpeed', Inputs=(c_int,) * 2, Iterator='NumHSSpeed', Outputs=(c_float,),
                           Input_params=(('channel', c_int), ('OutAmp', c_int),))),
    NumPreAmp=dict(Get=dict(cmdName='GetNumberPreAmpGains', Outputs=(c_int,))),
    PreAmpGains=dict(Get=dict(cmdName='GetPreAmpGain', Inputs=(c_int,), Outputs=(c_float,), Iterator='NumPreAmp')),
    PreAmpGain=dict(Set=dict(cmdName='SetPreAmpGain', Inputs=(c_int,)), Get_from_prop='PreAmpGains'),
    NumADChannels=dict(Get=dict(cmdName='GetNumberADChannels', Outputs=(c_int,))),
    ADChannel=dict(Set=dict(cmdName='SetADChannel', Inputs=(c_int,))),
    BitDepth=dict(Get=dict(cmdName='GetBitDepth', Inputs=(c_int,), Outputs=(c_int,), Iterator='NumADChannels'))
)
for param_name in parameters:
    if param_name != 'Image':
        setattr(AndorBase, param_name, AndorParameter(param_name))


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
