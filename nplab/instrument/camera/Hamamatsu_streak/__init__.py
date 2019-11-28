# -*- coding: utf-8 -*-

from builtins import map
from builtins import str
from builtins import zip
from builtins import range
import collections
import os
import pprint
import socket
import struct
import time

import numpy as np

from nplab.utils.gui import QtWidgets, QtCore, uic
from nplab.instrument import Instrument
from nplab.instrument.camera.camera_scaled_roi import DisplayWidgetRoiScale

PrettyPrinter = pprint.PrettyPrinter(indent=4)

TIMEOUT = 5
MAX_MESSAGE_HISTORY = 10
BUFFER_SIZE = 4096
SLEEPING_TIME = 0.1


def string_to_number(s):
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s


def dict_of_Nones(lst):
    return dict(list(zip(lst, [None] * len(lst))))


class StreakError(Exception):
    def __init__(self, code, msg, reply):
        super(StreakError, self).__init__()
        self.error_code = code
        self.error_name = ERROR_CODES[code]

        self.msg = msg
        self.reply = reply

    def __str__(self):
        return self.error_name + '\n Error sent: ' + self.msg + '\n Error reply: ' + self.reply


class StreakBase(Instrument):
    """
    Implements the RemoteExProgrammersHandbook91

    Not Implemented Functions:
        'MainParamInfo', 'MainParamInfoEx', 'GenParamInfo', 'GenParamInfoEx', 'AcqLiveMonitor', 'AcqLiveMonitorTSInfo',
        'acqLiveMonitorTSFormat', 'CamSetupSendSerial', 'ImgStatusSet', 'ImgRingBufferGet', 'ImgAnalyze', 'ImgRoiGet',
        'ImgRoiSet', 'ImgRoiSelectedRoiGet', 'ImgRoiSelectedRoiSet', 'SeqCopyToSeparateImg', 'SeqImgIndexGet', '
        All of the auxiliary devices, processing, defect pixel tools

    TODO:
        Inherit from message_bus_instrument if you want to use the communication_lock
    """

    def set_single_metadata(self, name, value):
        inputs = tuple(name) + (value,)
        self.set_parameter(*inputs)

    def get_single_metadata(self, name):
        return self.get_parameter(*name)

    def __init__(self, address, start_app=False, get_all_parameters=False, **kwargs):
        """

        :param address: tuple of the streak TCP address (TCP_IP,TCP_PORT)
        :param kwargs: optional dictionary keys, also passed to nplab.Instrument
            CloseAppWhenDone:  closes the streak GUI when you delete the Python class instance
            get_all_parameters:  gets the values of all the parameters on startup
        """

        Instrument.__init__(self)

        # self.address = address
        self.socket = None
        self.data_socket = None
        self._connect(address)

        self.current_message = ''
        self.current_reply = ''
        self.message_history = collections.deque(maxlen=MAX_MESSAGE_HISTORY)

        self.busy = False
        if "CloseAppWhenDone" in kwargs:
            self.close_app_when_done = kwargs['CloseAppWhenDone']
        else:
            self.close_app_when_done = False
        self.image = None

        # self.captureThread = QtCore.QThread()
        self._setup_parameter_dictionaries()

        # Starting the HPDTA GUI
        if start_app:
            self.socket.settimeout(120)
            self.start_app()
            self.socket.settimeout(TIMEOUT)

        # Getting all the parameters
        if get_all_parameters:
            self.get_parameter()

    def __del__(self):
        if self.close_app_when_done:
            self.end_app()
        self.socket.close()

    def _connect(self, address):
        if self.socket is not None:
            del self.socket
        if self.data_socket is not None:
            del self.data_socket

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(address)
        self.socket.settimeout(TIMEOUT)

        self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.data_socket.connect((address[0], address[1] + 1))
        self.data_socket.settimeout(100)

    def send_command(self, operation, *parameters, **kwargs):
        """
        Implements the TCP command structure, saves it to the message_history, sends it to the device and reads the reply
        :param operation:
        :param parameters:
        :return:
        """

        self._logger.debug("send_command: %s, %s, %s" % (operation, parameters, kwargs))
        params = list(map(str, parameters))
        self.current_message = operation + '(' + ','.join(params) + ')'
        self.current_message += '\r'
        self.message_history.append({'sent': self.current_message.rstrip(), 'received': []})

        self.socket.send(self.current_message)
        time.sleep(SLEEPING_TIME)
        self._handshake()

    def _read(self, previous_message='', size=BUFFER_SIZE):
        """Reads BUFFER_SIZE from the socket
        Within BUFFER_SIZE there could be more than one message, so if it doesn't end in \r, we read again, until we
        have a finished number of messages.
            ybd20:  This can still leave unread messages at the Streak, which is not ideal, but I don't think there's any
                    way of knowing how many messages are left
        Once a complete number of messages has been read, it makes a list of them and returns it

        """
        _reply = self.socket.recv(size)

        time.sleep(SLEEPING_TIME)
        # Ensure we've read a full number of messages by checking that the string ends with newline
        if not _reply.endswith('\r'):
            return self._read(previous_message + _reply)
        else:
            message_list = str(previous_message + _reply).split('\r')
            return message_list[:-1]  # the last message is an empty string so we always ignore it

    def _handshake(self):
        """Makes sure last sent command executed properly

        Most times a command is sent to the streak, it replies with a message containing an error code (see ERROR_CODES)
        and the command name. This command iterates over all the other possible messages the Streak wants to send to
        check if there is a handshake message somewhere, and either returns the error message if there's been an error,
        or tries to handshake again if there was no handshake message.

        :return:
        """
        # Read a bunch of messages from the streak and add them to the message history
        message_list = self._read()
        self.message_history[-1]['received'].append(message_list)

        # Iterate over the messages received until a handshake is produced or an error raised
        _handshaked = False
        for message in message_list:
            if not _handshaked:
                if message[0].isdigit():
                    split_reply = message.split(',')

                    if split_reply[0] not in ['4', '5']:
                        if split_reply[0] != '0':
                            self._error_handling(int(split_reply[0]))
                        elif self.current_message.split('(')[0] != split_reply[1]:
                            self._logger.error('Comparing this: %s' % self.current_message.split('(')[0] +
                                               'to this: %s' % split_reply[1])
                            raise RuntimeError('Handshake did not work')
                        else:
                            _handshaked = True
                            self.current_reply = message
                            self._logger.debug('Handshake worked. %s' % split_reply[1])
                            self._logger.debug('Sent: %s \nReply: %s' % (self.current_message, self.current_reply))
        # If a handshake was not present in the previous bunch of messages, try to handshake again
        if not _handshaked:
            self._handshake()

    def _error_handling(self, error_code):
        raise StreakError(error_code, self.current_message, self.current_reply)

    def _setup_parameter_dictionaries(self):
        app_params = ['Date', 'Version', 'Directory', 'Title', 'Titlelong', 'ProgDataDir']
        main_params = ['ImageSize', 'Message', 'Temperature', 'GateMode', 'MCPGain', 'Mode', 'Plugin', 'Shutter',
                       'StreakCamera', 'TimeRange']
        gen_params = ['RestoreWindowPos', 'UserFunctions', 'ShowStreakControl', 'ShowDelay1Control',
                      'ShowDelay2Control', 'ShowSpectrControl']
        acquisition_params = ['DisplayInterval', '32BitInAI', 'WriteDPCFile', 'AdditionalTimeout',
                              'DeactivateGrbNotInUse',
                              'CCDGainForPC', '32BitInPC', 'MoireeReduction']
        setup_param = ['TimingMode', 'TriggerMode', 'TriggerSource', 'TriggerPolarity', 'ScanMode', 'Binning',
                       'CCDArea', 'LightMode', 'Hoffs', 'HWidth', 'VOffs', 'VWidth', 'ShowGainOffset', 'NoLines',
                       'LinesPerImage', 'ScrollingLiveDisplay', 'FrameTrigger', 'VerticalBinning', 'TapNo',
                       'ShutterAction', 'Cooler', 'TargetTemperature', 'ContrastEnhancement', 'Offset', 'Gain',
                       'XDirection', 'ScanSpeed', 'MechanicalShutter', 'Subtype', 'AutoDetect', 'Wait2ndFrame', 'DX',
                       'DY', 'XOffset', 'YOffset', 'BPP', 'CameraName', 'ExposureTime', 'ReadoutTime', 'OnChipAmp',
                       'CoolingFan', 'Cooler', 'ExtOutputPolarity', 'ExtOutputDelay', 'ExtOutputWidth',
                       'LowLightSensitivity', 'AutomaticBundleHeight', 'CameraInfo']
        # Two parameters called Offset and Width were not included (name shadowing, must be a bug in the program or a
        # typo in the manual). Additionally, all the sensor specific parameters were not included
        tab_param = ['Exposure', 'Gain', 'Offset', 'NrTrigger', 'Threshold', 'Threshold2', 'DoRTBackSub',
                     'DoRTShading', 'NrExposures', 'ClearFrameBuffer', 'AmpGain', 'SMD', 'RecurNumber', 'HVoltage',
                     'AMD', 'ASH', 'ATP', 'SOP', 'SPX', 'MCP', 'TDY', 'IntegrAfterTrig', 'SensitivityValue', 'EMG',
                     'BGSub', 'RecurFilter', 'HightVoltage', 'StreakTrigger', 'FGTrigger', 'SensitivitySwitch',
                     'BGOffset', 'ATN', 'SMDExtended', 'LightMode', 'ScanSpeed', 'BGDataMemory', 'SHDataMemory',
                     'SensitivityMode', 'Sensitivity', 'Sensitivity2Mode', 'Sensitivity2', 'ContrastControl',
                     'ContrastGain', 'ContrastOffset', 'PhotonImagingMode', 'HighDynamicRangeMode', 'RecurNumber2',
                     'RecurFilter2', 'FrameAvgNumber', 'FrameAvg']
        cam_params = dict(Setup=dict(list(zip(setup_param, [None] * len(setup_param)))),
                          Live=dict(list(zip(tab_param, [None] * len(tab_param)))),
                          Acquire=dict(list(zip(tab_param, [None] * len(tab_param)))),
                          AI=dict(list(zip(tab_param, [None] * len(tab_param)))),
                          PC=dict(list(zip(tab_param, [None] * len(tab_param)))))

        dev_params = ['TD', 'Streak', 'Streakcamera', 'Spec', 'Spectrograph', 'Del', 'Delay', 'Delaybox', 'Del1',
                      'Del2',
                      'Delay2', 'DelayBox2']

        bkg_param = ['BackgroundSource', 'BakcFilesForAcqModes', 'GeneralFile', 'LiveFile', 'AcquireFile', 'AIFile',
                     'Constant', 'ClipZero', 'AutoBacksub']
        curv_param = ['CorrectionFile', 'AutoCurvature']
        defect_pixel_param = ['DefectCorrection', 'DefectPixelFile']
        shading_param = ['ShadingFile', 'ShadingConstant', 'AutoShading', 'SensitivityCorrection', 'LampFile']
        correction_params = dict(Background=dict(list(zip(bkg_param, [None] * len(bkg_param)))),
                                 Shading=dict(list(zip(curv_param, [None] * len(curv_param)))),
                                 Curvature=dict(list(zip(defect_pixel_param, [None] * len(defect_pixel_param)))),
                                 DefectPixel=dict(list(zip(shading_param, [None] * len(shading_param)))))

        img_params = ['AcquireToSameWindow', 'DefaultZoomFactor', 'WarnWhenUnsaved', 'Calibrated', 'LowerLUTIsZero',
                      'AutoLUT', 'AutoLUTInLive', 'AutoLUTInROI', 'HorizontalRuler', 'VerticalRuler', 'FixedITEXHeader']

        quick_profile_params = ['UseMinAsZero', 'DisplayQPOutOfImage', 'QPRelativeSpace', 'DisplayDirectionForRect',
                                'AdjustQPHeight', 'DisplayFWHM', 'DoGaussFit', 'FWHMColor', 'FWHMSize', 'FWHMNoOfDigis']

        LUT_params = ['Limits', 'Cursors', 'Color', 'Inverted', 'Gamma', 'Linearity', 'Overflowcolors']

        sequence_params = ['AutoCorrectAfterSeq', 'DisplayImgDuringSequence', 'PromptBeforeStart', 'EnableStop',
                           'Warning', 'EnableAcquireWrap', 'LoadHISSequence', 'PackHisFiles', 'NeverLoadToRam',
                           'LiveStreamingBuffers', 'WrapPlay', 'PlayInterval', 'ProfileNo', 'CorrectionDirection',

                           'AcquisitionMode', 'NoOfLoops', 'AcquisitionSpeed', 'AcquireInterval', 'DoAcquireWrap',

                           'AcquireImages', 'ROIOnly', 'StoreTo', 'FirstImgToStore', 'DisplayDataOnly',
                           'UsedHDSpaceForCheck', 'AcquireProfiles', 'FirstPrfToStore',

                           'AutoFixpoint', 'ExcludeSample',

                           'SampleType', 'CurrentSample', 'NumberOfSamples']

        self.parameters = dict(
            Application={'get': 'AppInfo',
                         'set': None,
                         'info': None,
                         'value': dict_of_Nones(app_params)},
            Main={'get': 'MainParamGet',
                  'set': None,
                  'info': 'MainParamInfo',
                  'value': dict_of_Nones(main_params)},
            General={'get': 'GenParamGet',
                     'set': 'GenParamSet',
                     'info': 'GenParamInfo',
                     'value': dict_of_Nones(gen_params)},
            Acquisition={'get': 'AcqParamGet',
                         'set': 'AcqParamSet',
                         'info': 'AcqParamInfoEx',
                         'value': dict_of_Nones(acquisition_params)},
            Camera={'get': 'CamParamGet',
                    'set': 'CamParamSet',
                    'info': 'CamParamInfoEx',
                    'value': cam_params},
            Devices={'get': 'DevParamGet',
                     'set': 'DevParamSet',
                     'info': 'DevParamInfoEx',
                     'value': dict_of_Nones(dev_params)},
            Corrections={'get': 'CorParamGet',
                         'set': 'CorParamSet',
                         'info': 'CorParamInfoEx',
                         'value': correction_params},
            Images={'get': 'ImgParamGet',
                    'set': 'ImgParamSet',
                    'info': 'ImgParamGet',
                    'value': dict_of_Nones(img_params)},
            QuickProfile={'get': 'QprParamGet',
                          'set': 'QprParamSet',
                          'info': 'QprParamInfo',
                          'value': dict_of_Nones(quick_profile_params)},
            LUT={'get': 'LutParamGet',
                 'set': 'LutParamSet',
                 'info': 'LutParamInfo',
                 'value': dict_of_Nones(LUT_params)},
            Sequence={'get': 'SeqParamGet',
                      'set': 'SeqParamSet',
                      'info': 'SeqParamInfo',
                      'value': dict_of_Nones(sequence_params)}
        )

        self.list_dev_params()

    def get_parameter(self, *give_params):
        """
        Gets any number of parameters contained in self.parameters. Each input can be either a string, or a iterable of
        strings, the function will return the appropriate value/dictionary of values
        :param give_params: three optional inputs, for each level of the self.parameters dictionary.
        :return:
        """

        if len(give_params) >= 1:
            names = give_params[0]
            if not hasattr(names, '__iter__'):
                names = (names,)
        else:
            names = list(self.parameters.keys())
        if len(give_params) > 3:
            raise ValueError('Too many input parameters')

        return_dict = {}
        for name in names:
            command_name = str(self.parameters[name]['get'])
            param_dictionary = self.parameters[name]['value']
            return_dict[name] = {}
            if type(param_dictionary[list(param_dictionary.keys())[0]]) == dict:
                if len(give_params) >= 2:
                    locations = give_params[1]
                    if not hasattr(locations, '__iter__'):
                        locations = (locations,)
                else:
                    locations = list(param_dictionary.keys())

                for location in locations:
                    if param_dictionary[location] == 'NotAvailable':
                        continue
                    if len(give_params) == 3:
                        params = give_params[2]
                        if not hasattr(params, '__iter__'):
                            params = (params,)
                    else:
                        params = list(param_dictionary[location].keys())
                    # print 'Location: ', location
                    # if params == 'All':
                    #     params = param_dictionary[location].keys()
                    # elif not hasattr(params, '__iter__'):
                    #     params = (params,)
                    return_dict[name][location] = {}
                    for param in params:
                        if param not in list(param_dictionary[location].keys()):
                            raise ValueError('Parameter %s not recognised' % param)
                        try:
                            self.send_command(command_name, location, param)
                            value = string_to_number(self.current_reply.split(',')[-1])
                            param_dictionary[location][param] = value
                            return_dict[name][location][param] = value
                            if len(give_params) == 3:
                                return param_dictionary[location][param]
                        except StreakError as e:
                            if e.error_code == 2:
                                param_dictionary[location][param] = 'NotAvailable'
                            else:
                                raise e
            else:
                if len(give_params) == 2:
                    params = give_params[1]
                    if not hasattr(params, '__iter__'):
                        params = (params,)
                else:
                    params = list(param_dictionary.keys())
                    # if params is 'All':  # init_params
                    #     params = param_dictionary.keys()
                    # print param_dictionary.keys()
                    # elif not hasattr(params, '__iter__'):  # type(params) != list:
                    #     params = (params,)
                    # raise ValueError('Parameter needs to be given as an iterable')
                for param in params:
                    # print 'Parameter: ', param
                    if param not in list(param_dictionary.keys()):
                        raise ValueError('%s parameter %s not recognised' % (name, param))
                    try:
                        self.send_command(command_name, param)
                        value = string_to_number(self.current_reply.split(',')[-1])
                        param_dictionary[param] = value
                        return_dict[name][param] = value
                        if len(give_params) == 2:  # len(params) == 1 and len(names) == 1:
                            return param_dictionary[param]
                    except StreakError as e:
                        if e.error_code == 2:
                            param_dictionary[param] = 'NotAvailable'
                        else:
                            raise e
        return return_dict

    def set_parameter(self, *args):
        """
        Set one or more Streak parameters
        :param args: Each parameter should be set by either a 3-tuple or a 4-tuple, containing two/three strings for
                    locating theparameter and a value for that parameter.
                    One can also provide a list of 3-tuples or 4-tuples, to set several parameters.
        :return:
        """
        if not hasattr(args[0], '__iter__'):
            args = (args,)

        for give_params in args:
            name = give_params[0]
            if name not in list(self.parameters.keys()):
                raise ValueError('Name %s not recognised' % name)
            if self.parameters[name]['set'] is not None:
                if len(give_params) == 3:
                    param = give_params[1]
                    value = give_params[2]
                    if param not in list(self.parameters[name]['value'].keys()):
                        raise ValueError('Parameter %s not recognised' % param)
                    self.send_command(self.parameters[name]['set'], param, value)
                    self.parameters[name]['value'][param] = value
                elif len(give_params) == 4:
                    location = give_params[1]
                    param = give_params[2]
                    value = give_params[3]
                    if location not in list(self.parameters[name]['value'].keys()):
                        raise ValueError('Location %s not recognised' % location)
                    if param not in list(self.parameters[name]['value'][location].keys()):
                        raise ValueError('Parameter %s not recognised' % param)
                    self.send_command(self.parameters[name]['set'], location, param, value)
                    self.parameters[name]['value'][location][param] = value
                else:
                    raise ValueError(
                        'Wrong number of inputs, need to give name, location (optional), parameter and value')
            else:
                self._logger.warn('Parameter cannot be set')

    def parameter_info(self, *give_params):
        name = give_params[0]
        if name not in list(self.parameters.keys()):
            raise ValueError('Name %s not recognised' % name)
        if self.parameters[name]['info'] is not None:
            if len(give_params) == 2:
                param = give_params[1]
                if param not in list(self.parameters[name]['value'].keys()):
                    raise ValueError('Parameter %s not recognised' % param)
                self.send_command(self.parameters[name]['info'], param)
            elif len(give_params) == 3:
                location = give_params[1]
                param = give_params[2]
                if location not in list(self.parameters[name]['value'].keys()):
                    raise ValueError('Location %s not recognised' % location)
                if param not in list(self.parameters[name]['value'][location].keys()):
                    raise ValueError('Parameter %s not recognised' % param)
                self.send_command(self.parameters[name]['info'], location, param)
            else:
                raise ValueError('Wrong number of inputs, need to give name, location (optional), and parameter')

            split_response = self.current_reply.split(',')
            reply_dict = dict(ErrorCode=split_response[0], CommandName=split_response[1], Label=split_response[2])

            if split_response[4].isdigit():
                if int(split_response[4]) in list(PARAMETER_TYPES.keys()):
                    reply_dict['CurrentValue'] = split_response[3]
                    reply_dict['ParameterType'] = PARAMETER_TYPES[int(split_response[4])]
                if split_response[4] == '1':
                    reply_dict['Minimum'] = split_response[5]
                    reply_dict['Maximum'] = split_response[6]
            else:
                reply_dict['Info'] = ','.join(split_response[3:])

            return reply_dict
        else:
            return {}

    '''General commands'''

    def appInfo(self):
        """
        Returns the current application type (HiPic or HPDTA). This command is executed even if the
        application has not been started.

        :return: 0, Appinfo, HiPic
        """
        self.send_command('Appinfo', 'type')

        return self.current_reply.split(',')[-1]

    def stop(self):
        """
        Stops the command currently executed if possible. (Few commands have implemented this
        command right now)

        :return: 0,Stop
        """
        self.send_command('Stop')

    def shutdown(self):
        """
        This command shuts down the application and the RemoteEx program. Response is sent before
        shutdown.
        The usefulness of this command is limited because it cannot be sent once the application has been
        hang up. Restarting of the remote application if an error has occurred should be done by other
        means (example: Power off and on the computer from remote and starting the RemoteEx from the
        autostart).

        :return: 0,Shutdown
        """
        self.send_command('Shutdown')

    '''Application commands'''

    def start_app(self, visible=1, iniFile=None):
        """
        This command starts the application. If the application has already been started this command
        returns immediately, otherwise it waits until it has been started completely.
        If visible is 0 or FALSE the application starts invisible. If this parameter is omitted or if it is others
        than 0 or FALSE the application starts visible. This parameter is ignored if the application is
        already running. If you want to make sure that the visible state is set if desired you should first close
        the application with AppEnd() and then restart it with the AppStart() command.
        If iniFile is specified the application starts with the INI-File (new from version 8.3.0). This
        parameter is also ignored if the application is already running.
        :param visible:
        :param iniFile:
        :return:
        """

        if iniFile is not None:
            self.send_command('AppStart', visible, iniFile, timeout=120)
        else:
            self.send_command('AppStart', visible, timeout=120)

    def end_app(self):
        self.send_command('AppEnd')

    '''Acquisition commands'''

    def start_acquisition(self, mode='Acquire'):
        """
        This command starts an acquisition.
        :param mode: one of the following:
                'Live'      Live mode
                'Acquire'   Acquire mode
                'AI'        Analog integration
                'PC'        Photon counting
        :return:
        """
        self.send_command('AcqStart', mode)

    def isAcquisitionBusy(self):
        """
        This command returns the status of an acquisition.
        :return:
        """
        self.send_command('AcqStatus')
        if self.current_reply.split(',')[2] == 'idle':
            self.busy = False
        elif self.current_reply.split(',')[2] == 'busy':
            self.busy = True
        return self.busy

    def stop_acquisition(self, timeout=1000):
        """
        This command stops the currently running acquisition. It can have an optional parameter (available
        from 8.2.0 pf5) indicating the timeout value (in ms) until this command should wait for an
        acquisition to end. The range of this timeout value is [1...60000] and the default value is 1000 (if
        not specified).
        :param timeout:
        :return: 0,AcqStop (Successfully stopped)
                or
                7,AcqStop,timeout (Timeout while waiting for stop)
        """
        self.send_command('AcqStop', timeout)

    '''Camera commands'''

    def get_live_bkg(self):
        """
        This command gets a new background image which is used for real time background subtraction
        (RTBS). It is only available of LIVE mode is running.
        :return:
        """
        self.send_command('CamGetLiveBG')

    '''External device commands (HPD-TA only)'''

    def list_dev_params(self, devices=None):
        """
        This command returns a list of all parameters of a specified device.
        :param devices: one of:
                ['TD', 'Streak', 'Streakcamera', 'Spec', 'Spectrograph', 'Del', 'Delay', 'Delaybox',
                    'Del1', 'Del2', 'Delay2', 'DelayBox2']
        :return:
        """
        if devices is None:
            devices = list(self.parameters['Devices']['value'].keys())
        for device in devices:
            if device not in list(self.parameters['Devices']['value'].keys()):
                raise ValueError('Device %s not recognised' % device)
            try:
                self.send_command('DevParamsList', device)
                split_response = self.current_reply.split(',')
                param_list = []
                for ii in range(3, 3 + int(split_response[2])):
                    param_list.append(split_response[ii])

                device_dict = dict_of_Nones(param_list)
                self.parameters['Devices']['value'][device] = device_dict
            except StreakError as e:
                if e.error_code == 7:
                    self.parameters['Devices']['value'][device] = 'NotAvailable'
                else:
                    raise e

    '''Auxiliary devices commands'''

    '''Correction commands'''

    def do_correction(self, destination='Current', type='BacksubShadingCurvature'):
        """

        :param destination: either 'Current' or a number between 0 and 19
        :param type: one of:
         ['Backsub', 'Background', 'Shading', 'Curvature', 'BacksubShading', 'BacksubCurvature',
         'BacksubShadingCurvature', 'DefectCorrect']
        :return:
        """
        if type == 'DefectCorrect':
            raise NotImplementedError
        self.send_command('CorDoCorrection', destination, type)

    '''Processing commands'''

    '''Defect pixel tool commands'''

    '''Image commands'''

    def save_image(self, image_index='Current', image_type='TIF', filename='DefaultImage.tif', overwrite=False,
                   directory=None):
        """

        :param image_index: image to be saved, either 'Current' or a number between 0 and 19
        :param image_type: one of 'IMG' (ITEX file), 'TIF', 'TIFF', 'ASCII',
                                'data2tiff', 'data2tif', 'display2tiff', 'display2tif'
        :param filename: file path
        :param overwrite: whether to overwrite existing files
        :param directory:
        :return:
        """
        if directory is None:
            directory = os.getcwd()
        if not os.path.isabs(filename):
            filename = os.path.join(directory, filename)
        self.send_command('ImgSave', image_index, image_type, filename, int(overwrite))

    def load_image(self, filename='DefaultImage.txt', image_type='ASCII'):
        """
        Not that not all file types which can be saved can also be loaded. Some file types are intended for export only.
        Note: This load functions loads the image always into a new window independently of the setting of
        the option AcquireToSameWindow. If the maximum number of windows is reached an error is
        returned.
        :param filename: path
        :param image_type: one of 'IMG' (ITEX file), 'TIF', 'TIFF', 'ASCII',
                                'data2tiff', 'data2tif', 'display2tiff', 'display2tif'
        :return:
        """
        if not os.path.isabs(filename):
            filename = os.path.join(os.getcwd(), filename)
        self.send_command('ImgLoad', image_type, filename)

    def delete_image(self, image_index='Current'):
        """
        Note1: This function deletes the specified images independent whether their content has been saved
        or not. If you want to keep the content of the image please save the image before executing this
        command.
        Note2: This function does not delete images on hard disk.
        :param image_index: 'Current', 'All' or a number between 0-19
        :return:
        """
        self.send_command('ImgDelete', image_index)

    def get_image_status(self, image_index='Current', *identifiers):
        """

        :param image_index: 'Current' or a number between 0-19
        :param identifiers: section identifier and (optional) token identifier
        :return:
        """
        if len(identifiers) == 0:
            self.send_command('ImgStatusGet', image_index, 'All')
        elif len(identifiers) == 1:
            self.send_command('ImgStatusGet', image_index, 'Section', identifiers[0])
        elif len(identifiers) == 2:
            self.send_command('ImgStatusGet', image_index, 'Token', identifiers[0], identifiers[1])
        else:
            raise ValueError('Too many parameters')
        split_reply = self.current_reply.split(',')
        del split_reply[0]
        del split_reply[0]
        joint_reply = ','.join(split_reply).rstrip()
        replies = joint_reply.split('[')
        del replies[0]
        parsed_reply = dict()
        for reply1 in replies:
            split_reply = reply1.split(',')
            for reply2 in split_reply:
                if reply2:
                    if reply2[-1] == ']':
                        location = reply2[0:-1]
                        parsed_reply[location] = {}
                    else:
                        parameter = reply2.split('=')[0]
                        value = reply2.split('=')[1]
                        parsed_reply[location][parameter] = value
        return parsed_reply

    def get_index_of_curr_img(self):
        self.send_command('ImgIndexGet')

        return self.current_reply.split(',')[-1]

    def set_as_curr_img(self, image_index):
        self.send_command('ImgIndexSet', image_index)

    def get_img_default_directory(self):
        self.send_command('ImgDefaultDirGet')
        return self.current_reply.split(',')[-1]

    def set_img_default_directory(self, path):
        self.send_command('ImgDefaultDirSet', path)

    def get_img_info(self, image_index='Current'):
        """
        This command returns the image size in pixels and the Bytes per pixel of a single pixel.
        :param image_index:
        :return:
        """
        self.send_command('ImgDataInfo', image_index, 'Size')
        shape = list(map(int, tuple(self.current_reply.split(',')[2:6])))
        bytes_per_pixel = int(self.current_reply.split(',')[-1])
        return shape, bytes_per_pixel

    def get_image_data(self, image_index='Current', type='Data', *profile_params):
        """
        This command gets image, display or profile data of the select image.
        The image data is transferred by the optional second TCP-IP channel. If this channel is not available
        an error is issued.
        :param image_index: 'Current' or number between 1-19
        :param type:
                - 'Data': raw image data (1,2 or 4 BPP)
                - 'Display': display data (1 BPP)
                - 'Profile': profile (4 bytes floating point values)
        :param profile_params: five numbers:
                - Profile type: 1 (line profile), 2 (horizontal bin), 3 (vertical bin)
                - Coordinates: iX, iY, iDX, iDY
        :return:
        """
        if type != 'Profile':
            self.send_command('ImgDataGet', image_index, type)
        else:
            self.send_command('ImgDataGet', image_index, type, *profile_params)

    def dump_image_data(self, path, image_index='Current', type='Data', *profile_params):
        """
        This command gets image or display data of the select image and writes it to file (only binary data,
        no header). It can be used to get image or profile data alternatively to using the second TCP-IP port.
        :param path:
        :param image_index:
        :param type:
                - 'Data': raw image data (1,2 or 4 BPP)
                - 'Display': display data (1 BPP)
                - 'Profile': profile (4 bytes floating point values)
        :param profile_params: five numbers:
                - Profile type: 1 (line profile), 2 (horizontal bin), 3 (vertical bin)
                - Coordinates: iX, iY, iDX, iDY
        :return:
        """
        if type != 'Profile':
            self.send_command('ImgDataDump', image_index, type, path)
        else:
            profile_type = profile_params[0]
            iX = profile_params[1]
            iY = profile_params[2]
            iDX = profile_params[3]
            iDY = profile_params[4]
            self.send_command('ImgDataDump', image_index, type, profile_type, iX, iY, iDX, iDY, path)

    '''Quick profile commands'''

    '''LUT commands'''

    def auto_LUT(self):
        self.send_command('LutSetAuto')
        return self.current_reply.split(',')[2:5]

    '''Sequence commands'''

    def start_sequence(self, directory=None, wait=False):
        if directory is not None:
            self.set_parameter('Sequence', 'StoreTo', 'HD <individual files - all modes>')
            self.set_parameter('Sequence', 'FirstImgToStore', directory)
        self.send_command('SeqStart')

        if wait:
            status = self.sequence_status()
            while type(status) == list and status[0] == 'busy':
                time.sleep(0.5)
                status = self.sequence_status()

    def stop_sequence(self):
        self.send_command('SeqStop')

    def sequence_status(self):
        self.send_command('SeqStatus')
        split_reply = self.current_reply.split(',')
        if len(split_reply) == 3:
            return split_reply[-1]
        elif len(split_reply) == 4:
            return split_reply[2:4]
        else:
            return 'BUGBUG'

    def delete_sequence(self):
        """
        Deletes the current sequence from memory.
        Note: This function does not delete a sequence on the hard disk.
        :return:
        """
        self.send_command('SeqDelete')

    def save_sequence(self, image_type='ASCII', filename='DefaultSequence.txt', overwrite=0):
        if not os.path.isabs(filename):
            filename = os.path.join(os.getcwd(), filename)
        self.send_command('SeqSave', image_type, filename, overwrite)

    def load_sequence(self, image_type='ASCII', filename='DefaultSequence.txt'):
        if not os.path.isabs(filename):
            filename = os.path.join(os.getcwd(), filename)
        self.send_command('SeqLoad', image_type, filename)

    '''My commands'''

    def capture(self, mode='Acquire', save=False, delete=False, save_kwargs=None):
        try:
            if mode == 'Acquire':
                self.start_acquisition(mode)

                if save:
                    # time.sleep(1)  # This sleep-time was arrived to by trial and error
                    self.save_image(**save_kwargs)
                    if delete:
                        self.delete_image()
                else:
                    time.sleep(1.5)  # This sleep-time was arrived to by trial and error
                    shape, pixel_size = self.get_img_info()
                    n_pixels = (shape[2] - shape[0]) * (shape[3] - shape[1])

                    self.get_image_data()
                    self._logger.debug('Receiving: %s pixels of size %g' % (n_pixels, pixel_size))

                    image = []
                    for pxl_num in range(n_pixels):
                        pixel = self.data_socket.recv(pixel_size)
                        image += [struct.unpack('!B', pixel[0])[0]]
                    image = np.array(image).reshape((1, shape[2] - shape[0], shape[3] - shape[1]))
                    self.image = image
                    if delete:
                        self.delete_image()
                    return image
            elif mode == 'Sequence':
                self.start_sequence()
                time.sleep(0.1)
                status = self.sequence_status()
                while status[0] == 'busy':
                    time.sleep(0.5)
                    status = self.sequence_status()
                if delete:
                    self.delete_sequence()
            else:
                raise ValueError('Capture mode not recognised')
        except Exception as e:
            self._logger.warn("Failed capture at Thread because: %s" % e)

    # def capture(self, mode='Acquire', wait=False, save=False, save_kwargs=None):
    #     try:
    #         self.captureThread = StreakThread(self, mode, save, save_kwargs)
    #         self.captureThread.start()
    #         if wait:
    #             self.captureThread.wait()
    #         return self.image
    #     except Exception as e:
    #         self._logger.warn("Failed capture because: %s" % e)

    def get_qt_ui(self):
        return StreakUI(self)


class StreakThread(QtCore.QThread):
    def __init__(self, streak, mode, save=False, save_kwargs=None):
        super(StreakThread, self).__init__()
        self.Streak = streak
        self.mode = mode
        self.save = save
        if save_kwargs is None:
            self.save_kwargs = dict()
        else:
            self.save_kwargs = dict(save_kwargs)

    def stop(self):
        self.wait()

    def run(self):
        try:
            if self.mode == 'Acquire':
                self.Streak.start_acquisition(self.mode)

                if self.save:
                    time.sleep(1)  # This sleep-time was arrived to by trial and error
                    self.Streak.save_image(**self.save_kwargs)
                else:
                    time.sleep(1.5)  # This sleep-time was arrived to by trial and error
                    shape, pixel_size = self.Streak.get_img_info()
                    n_pixels = (shape[2] - shape[0]) * (shape[3] - shape[1])

                    self.Streak.get_image_data()
                    self.Streak._logger.debug('Receiving: %s pixels of size %g' % (n_pixels, pixel_size))

                    image = []
                    for pxl_num in range(n_pixels):
                        pixel = self.Streak.data_socket.recv(pixel_size)
                        image += [struct.unpack('!B', pixel[0])[0]]
                    image = np.array(image).reshape((1, shape[2] - shape[0], shape[3] - shape[1]))
                    self.Streak.image = image
                self.Streak.delete_image()
            elif self.mode == 'Sequence':
                self.Streak.start_sequence()
                time.sleep(0.5)
                status = self.Streak.sequence_status()
                while status[0] == 'busy':
                    time.sleep(0.5)
                    status = self.Streak.sequence_status()
                self.Streak.delete_sequence()
            else:
                raise ValueError('Capture mode not recognised')
        except Exception as e:
            self.Streak._logger.warn("Failed capture at Thread because: %s" % e)


class StreakUI(QtWidgets.QWidget):
    ImageUpdated = QtCore.Signal()

    def __init__(self, streak):
        assert isinstance(streak, StreakBase), "instrument must be an StreakBase"
        super(StreakUI, self).__init__()

        self.Streak = streak
        uic.loadUi((os.path.dirname(__file__) + '/Streak.ui'), self)

        self.comboBoxGateMode.activated.connect(self.GateModeChanged)
        self.comboBoxReadMode.activated.connect(self.ReadModeChanged)
        self.comboBoxShutter.activated.connect(self.ShutterChanged)
        self.comboBoxTrigMode.activated.connect(self.TriggerChanged)
        self.lineEditMCPGain.returnPressed.connect(self.MCPGainChanged)
        self.lineEditTimeRange.returnPressed.connect(self.TimeRangeChanged)
        self.comboBoxTimeUnit.activated.connect(self.TimeRangeChanged)
        self.pushButtonLess.clicked.connect(lambda: self.TimeRangeChanged('-'))
        self.pushButtonMore.clicked.connect(lambda: self.TimeRangeChanged('+'))

        self.pushButtonCapture.clicked.connect(self.Capture)

        self.DisplayWidget = None

        # self.Streak.captureThread.finished.connect(self.updateImage)

        self.updateGUI()

    def updateGUI(self):
        self.Streak.get_parameter('Devices', 'TD')

        # PrettyPrinter.pprint(self.Streak.parameters)

        # gateMode = self.Streak.parameters['Devices']['value']['TD']['Gate Mode']
        # readMode = self.Streak.parameters['Devices']['value']['TD']['Mode']
        # shutter = self.Streak.parameters['Devices']['value']['TD']['Shutter']
        # trig = self.Streak.parameters['Devices']['value']['TD']['Trig. Mode']
        # gain = self.Streak.parameters['Devices']['value']['TD']['MCP Gain']
        # time = self.Streak.parameters['Devices']['value']['TD']['Time Range']
        #
        # self.comboBoxGateMode.setCurrentIndex(self.comboBoxGateMode.findText(gateMode))
        # self.comboBoxReadMode.setCurrentIndex(self.comboBoxReadMode.findText(readMode))
        # self.comboBoxShutter.setCurrentIndex(self.comboBoxShutter.findText(shutter))
        # self.comboBoxTrigMode.setCurrentIndex(self.comboBoxTrigMode.findText(trig))
        # self.lineEditMCPGain.setText(str(gain))
        # self.lineEditTimeRange.setText(time.split(' ')[0])
        # self.comboBoxTimeUnit.setCurrentIndex(self.comboBoxTimeUnit.findText(time.split(' ')[1]))

    def GateModeChanged(self):
        currentMode = str(self.comboBoxGateMode.currentText())
        self.Streak.set_parameter('Devices', 'TD', 'Gate Mode', currentMode)

    def ReadModeChanged(self):
        currentMode = str(self.comboBoxReadMode.currentText())
        self.Streak.set_parameter('Devices', 'TD', 'Mode', currentMode)

        # Close Shutter
        # Bring MCP gain to 0

    def ShutterChanged(self):
        currentMode = str(self.comboBoxShutter.currentText())
        self.Streak.set_parameter('Devices', 'TD', 'Shutter', currentMode)

    def TriggerChanged(self):
        currentMode = str(self.comboBoxTrigMode.currentText())
        self.Streak.set_parameter('Devices', 'TD', 'Trig. Mode', currentMode)

    def MCPGainChanged(self):
        currentGain = int(self.lineEditMCPGain.text())
        if currentGain < 0:
            currentGain = 0
            self.comboBoxTrigMode.setText(str(currentGain))
        if currentGain > 63:
            currentGain = 63
            self.comboBoxTrigMode.setText(str(currentGain))

        self.Streak.set_parameter('Devices', 'TD', 'MCP Gain', currentGain)

    def TimeRangeChanged(self, direction=None):
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
                # self.Streak.set_parameter('Devices', 'TD', 'Time Range', str(next_number) + ' ' + next_unit)
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
                # self.Streak.set_parameter('Devices', 'TD', 'Time Range', str(next_number) + ' ' + next_unit)
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

    def Capture(self):
        self.Streak.capture()
        self.updateImage()

    def updateImage(self):
        if self.DisplayWidget is None:
            self.DisplayWidget = DisplayWidgetRoiScale()
        if self.DisplayWidget.isHidden():
            self.DisplayWidget.show()
        if len(self.Streak.image.shape) == 0:
            self.DisplayWidget.splitter.setSizes([0, 1])
        else:
            self.DisplayWidget.splitter.setSizes([1, 0])

        self.DisplayWidget.ImageDisplay.setImage(np.array(self.Streak.image[0]), autoRange=False,
                                                 autoLevels=True)  # np.array(self.Streak.image))

        self.ImageUpdated.emit()
        # , 'Streak')


PARAMETER_TYPES = {0: 'Boolean', 1: 'Numeric', 2: 'List', 3: 'String', 4: 'Exposure Time', 5: 'String'}

ERROR_CODES = {0: 'Success',
               1: 'Invalid syntax (command must be followed by parentheses and must have the correct number and type '
                  'of parameters separated by comma)',
               2: 'Command or Parameters are unknown.',
               3: 'Command currently not possible',
               4: 'A message during runtime (example: a string indicating the frame rate during live mode)',
               5: 'Reply value of a message box. The structure of RemoteEx does not allow sending inquiry commands '
                  'from the RemoteEx to the client. In cases where the standalone program needs to popup a message box '
                  'to get some information from the user the RemoteEx just continues execution with the default value '
                  'of this message box. When such case happens a string is sent to the RemoteEx Client informing it '
                  'about this default value. ',
               6: 'Parameter is missing',
               7: 'Command cannot be executed',
               8: 'An error has occurred during execution',
               9: 'Data cannot be sent by TCP-IP',
               10: 'Value of a parameter is out of range'}

if __name__ == "__main__":
    streak = StreakBase(('localhost', 1001))
    streak.show_gui()
