# -*- coding: utf-8 -*-

from builtins import map
from builtins import range
from nplab.instrument.visa_instrument import VisaInstrument
import os
import pprint
import socket
import struct
import time
import numpy as np
import re
import visa


PrettyPrinter = pprint.PrettyPrinter(indent=4)

TIMEOUT = 5000  # in milliseconds
BUFFER_SIZE = 4096
SLEEPING_TIME = 0.1


class StreakError(Exception):
    def __init__(self, code, msg, reply):
        if isinstance(code, str):
            code = int(code)
        super(StreakError, self).__init__()
        self.msg = msg
        self.reply = reply
        self.error_code = code
        self.error_name = ERROR_CODES[code]

    def __str__(self):
        return '%s Sent: %s Reply: %s' % (self.error_name, self.msg, self.reply)


class StreakSdk(VisaInstrument):
    """
    Implements the RemoteExProgrammersHandbook91

    Not Implemented Functions:
        'MainParamInfo', 'MainParamInfoEx', 'GenParamInfo', 'GenParamInfoEx', 'AcqLiveMonitor', 'AcqLiveMonitorTSInfo',
        'acqLiveMonitorTSFormat', 'CamSetupSendSerial', 'ImgStatusSet', 'ImgRingBufferGet', 'ImgAnalyze', 'ImgRoiGet',
        'ImgRoiSet', 'ImgRoiSelectedRoiGet', 'ImgRoiSelectedRoiSet', 'SeqCopyToSeparateImg', 'SeqImgIndexGet', '
        All of the auxiliary devices, processing, defect pixel tools
    """

    def __init__(self, address, start_app=False, get_all_parameters=False, **kwargs):
        """

        :param address: tuple of the streak TCP address (TCP_IP,TCP_PORT)
        :param kwargs: optional dictionary keys, also passed to nplab.Instrument
            CloseAppWhenDone:  closes the streak GUI when you delete the Python class instance
            get_all_parameters:  gets the values of all the parameters on startup
        """
        visa_address = 'TCPIP::%s::%d::SOCKET' % address
        settings = dict(read_termination='\r', write_termination='\r', timeout=TIMEOUT, query_delay=SLEEPING_TIME)
        super(StreakSdk, self).__init__(visa_address, settings)

        message = self.read()  # reads the default message that gets sent from RemoteEx
        if message != 'RemoteEx Ready':
            self._logger.warn('Not ready: %s' % message)

        self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.data_socket.connect((address[0], address[1] + 1))
        self.data_socket.settimeout(10)
        message = self.data_socket.recv(100).decode().rstrip()
        if message != 'RemoteEx Data Ready':
            self._logger.warn('Data socket not ready: %s' % message)
        self.clear_read_buffer()

        self.close_app_when_done = False
        if "CloseAppWhenDone" in kwargs:
            self.close_app_when_done = kwargs['CloseAppWhenDone']

        # Starting the HPDTA GUI
        if start_app:
            self.start_app()

        self._setup_parameter_dictionaries()

        # Getting all the parameters
        if get_all_parameters:
            self.get_parameter()

    def __del__(self):
        if self.close_app_when_done:
            self.send_command('AppEnd')
        super(StreakSdk, self).__del__()

    def reopen_connection(self):
        """For some reason, sometimes the remote app crashes, and it's useful to restart the connection without
        restarting the local python app

        :return:
        """
        if hasattr(self, 'instr'):
            del self.instr
        if hasattr(self, 'data_socket'):
            self.data_socket.close()
            del self.data_socket

        settings = dict(read_termination='\r', write_termination='\r', timeout=TIMEOUT, query_delay=SLEEPING_TIME)

        rm = visa.ResourceManager()
        self.instr = rm.open_resource(self._address, **settings)

        message = self.read()  # reads the default message that gets sent from RemoteEx
        if message != 'RemoteEx Ready':
            self._logger.warn('Not ready: %s' % message)

        address = self._address.split('::')[1:3]
        self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.data_socket.connect((address[0], int(address[1]) + 1))
        self.data_socket.settimeout(10)
        message = self.data_socket.recv(100).decode().rstrip()
        if message != 'RemoteEx Data Ready':
            self._logger.warn('Data socket not ready: %s' % message)
        self.clear_read_buffer()

    def query(self, msg, *args, **kwargs):
        """Light wrapper to add logging and handshaking

        :param msg:
        :param args:
        :param kwargs:
        :return:
        """
        self._logger.debug("write: %s" % msg)
        full_reply = super(StreakSdk, self).query(msg, *args, **kwargs)
        self._logger.debug("read: %s" % full_reply)
        reply = self._handshake(msg, full_reply, *args, **kwargs)
        return reply

    def _handshake(self, message, full_reply, *args, **kwargs):
        """Checks command was executed without errors

        Most times a command is sent to the streak, it replies with a message containing an error code (see ERROR_CODES)
        and the command name. This method returns the error message if there's been an error, or tries to handshake
        again if there was no handshake message.

        :return:
        """
        try:
            split_reply = full_reply.split(',', 2)

            # Some commands have a response (len = 3), others simply have a handshake (len = 2)
            if len(split_reply) == 2:
                split_reply += ('', )
            error_code, command, reply = split_reply

            if error_code in ['4', '5']:
                # Some messages in the buffer simply state the streak status
                self._logger.debug('Useless reply:\t%s\t%s\t%s' % (error_code, command, reply))
                # They are generally not useful, so we handshake again
                full_reply = self.read(*args, **kwargs)
                return self._handshake(message, full_reply, *args, **kwargs)
            elif message.split('(')[0] != command:
                self._logger.error('Comparing this: %s \t to this: %s' % (message.split('(')[0], command))
                raise RuntimeError('Replied command does not match')
            elif error_code == '0':
                self._logger.debug('Handshake worked\t%s\t%s' % (command, reply))
                return reply
            else:
                raise StreakError(error_code, message, full_reply)
        except Exception as e:
            self._logger.warn('Handshake failed: %s' % e)

    def send_command(self, operation, *parameters, **kwargs):
        """Simply parses a command and parameters into the expected TCPIP string command structure:
            operation(parameter1, parameter2, parameter3...)

        :param operation: str
        :param parameters: list of parameters to be passed to operation
        :return:
        """

        self._logger.debug("send_command: %s, %s, %s" % (operation, parameters, kwargs))
        msg = '%s(%s)' % (operation, ','.join(map(str, parameters)))
        return self.query(msg, **kwargs)

    def _setup_parameter_dictionaries(self):
        """Setting up a dictionary (self.parameters) that contains all the information for calling parameters, as well
        as their values (once called)

        Streak parameters are hierarchical (e.g. there are 7 parameters related to the Application). Some have one level
        (like Application) but others have two levels (e.g. Camera has Binning inside Setup, but Exposure inside one of
        Live/Acquire/AI/PC).

        TODO: make parameters into CameraParameters that can then be bundled into metadata
            Problem: some parameters do not have names amenable to being attributes (with spaces, stops, slashes)
        TODO: handle unavailable parameters and devices

        :return:
        """
        self.parameters = dict()

        # APPLICATION
        app_params = ['Date', 'Version', 'Directory', 'Title', 'Titlelong', 'ProgDataDir', 'type']
        self.parameters['Application'] = {'get': 'AppInfo',
                                          'set': None,
                                          'info': None,
                                          'value': {key: None for key in app_params}}

        # MAIN
        main_params = ['ImageSize', 'Message', 'Temperature', 'GateMode', 'MCPGain', 'Mode', 'Plugin', 'Shutter',
                       'StreakCamera', 'TimeRange']
        self.parameters['Main'] = {'get': 'MainParamGet',
                                   'set': None,
                                   'info': 'MainParamInfo',
                                   'value': {key: None for key in main_params}}

        # GENERAL
        gen_params = ['RestoreWindowPos', 'UserFunctions', 'ShowStreakControl', 'ShowDelay1Control',
                      'ShowDelay2Control', 'ShowSpectrControl']
        self.parameters['General'] = {'get': 'GenParamGet',
                                      'set': 'GenParamSet',
                                      'info': 'GenParamInfo',
                                      'value': {key: None for key in gen_params}}

        # ACQUISITION
        acquisition_params = ['DisplayInterval', '32BitInAI', 'WriteDPCFile', 'AdditionalTimeout',
                              'DeactivateGrbNotInUse', 'CCDGainForPC', '32BitInPC', 'MoireeReduction']
        self.parameters['Acquisition'] = {'get': 'AcqParamGet',
                                          'set': 'AcqParamSet',
                                          'info': 'AcqParamInfoEx',
                                          'value': {key: None for key in acquisition_params}}

        # CAMERA
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
        cam_params = dict(Setup={key: None for key in setup_param},
                          Live={key: None for key in tab_param},
                          Acquire={key: None for key in tab_param},
                          AI={key: None for key in tab_param},
                          PC={key: None for key in tab_param})
        self.parameters['Camera'] = {'get': 'CamParamGet',
                                     'set': 'CamParamSet',
                                     'info': 'CamParamInfoEx',
                                     'value': cam_params}

        # CORRECTIONS
        bkg_param = ['BackgroundSource', 'BackFilesForAcqModes', 'GeneralFile', 'LiveFile', 'AcquireFile', 'AIFile',
                     'Constant', 'ClipZero', 'AutoBacksub']
        curv_param = ['CorrectionFile', 'AutoCurvature']
        defect_pixel_param = ['DefectCorrection', 'DefectPixelFile']
        shading_param = ['ShadingFile', 'ShadingConstant', 'AutoShading', 'SensitivityCorrection', 'LampFile']
        correction_params = dict(Background={key: None for key in bkg_param},
                                 Shading={key: None for key in curv_param},
                                 Curvature={key: None for key in defect_pixel_param},
                                 DefectPixel={key: None for key in shading_param})
        self.parameters['Corrections'] = {'get': 'CorParamGet',
                                          'set': 'CorParamSet',
                                          'info': 'CorParamInfoEx',
                                          'value': correction_params}

        # IMAGES
        img_params = ['AcquireToSameWindow', 'DefaultZoomFactor', 'WarnWhenUnsaved', 'Calibrated', 'LowerLUTIsZero',
                      'AutoLUT', 'AutoLUTInLive', 'AutoLUTInROI', 'HorizontalRuler', 'VerticalRuler', 'FixedITEXHeader']
        self.parameters['Images'] = {'get': 'ImgParamGet',
                                     'set': 'ImgParamSet',
                                     'info': 'ImgParamGet',
                                     'value': {key: None for key in img_params}}

        # QUICK PROFILE
        quick_profile_params = ['UseMinAsZero', 'DisplayQPOutOfImage', 'QPRelativeSpace', 'DisplayDirectionForRect',
                                'AdjustQPHeight', 'DisplayFWHM', 'DoGaussFit', 'FWHMColor', 'FWHMSize', 'FWHMNoOfDigis']
        self.parameters['QuickProfile'] = {'get': 'QprParamGet',
                                           'set': 'QprParamSet',
                                           'info': 'QprParamInfo',
                                           'value': {key: None for key in quick_profile_params}}

        # LUT
        LUT_params = ['Limits', 'Cursors', 'Color', 'Inverted', 'Gamma', 'Linearity', 'Overflowcolors']
        self.parameters['LUT'] = {'get': 'LutParamGet',
                                  'set': 'LutParamSet',
                                  'info': 'LutParamInfo',
                                  'value': {key: None for key in LUT_params}}

        # SEQUENCE
        sequence_params = ['AutoCorrectAfterSeq', 'DisplayImgDuringSequence', 'PromptBeforeStart', 'EnableStop',
                           'Warning', 'EnableAcquireWrap', 'LoadHISSequence', 'PackHisFiles', 'NeverLoadToRam',
                           'LiveStreamingBuffers', 'WrapPlay', 'PlayInterval', 'ProfileNo', 'CorrectionDirection',
                           'AcquisitionMode', 'NoOfLoops', 'AcquisitionSpeed', 'AcquireInterval', 'DoAcquireWrap',
                           'AcquireImages', 'ROIOnly', 'StoreTo', 'FirstImgToStore', 'DisplayDataOnly',
                           'UsedHDSpaceForCheck', 'AcquireProfiles', 'FirstPrfToStore',
                           'AutoFixpoint', 'ExcludeSample',
                           'SampleType', 'CurrentSample', 'NumberOfSamples']
        self.parameters['Sequence'] = {'get': 'SeqParamGet',
                                       'set': 'SeqParamSet',
                                       'info': 'SeqParamInfo',
                                       'value': {key: None for key in sequence_params}}

        # DEVICES
        dev_params = ['TD', 'Streak', 'Streakcamera', 'Spec', 'Spectrograph',
                      'Del', 'Delay', 'Delaybox', 'Del1',
                      'Del2', 'Delay2', 'DelayBox2']
        self.parameters['Devices'] = {'get': 'DevParamGet',
                                      'set': 'DevParamSet',
                                      'info': 'DevParamInfoEx',
                                      'value': {key: None for key in dev_params}}
        self.list_dev_params()

    def get_parameter(self, base_name=None, sub_level=None, sub_sub_level=None):
        """Gets and returns streak parameter(s)

        If either sub_level or sub_sub_level are None, returns all the values at that hierarchy

        >>>> streak.get_parameter()  # returns ALL the streak parameters

        >>>> streak.get_parameter('Devices', 'TD')
        >>>> {'Time Range': '2', 'Mode': 'Operate', 'Gate Mode': 'Normal', 'MCP Gain': '11', 'Shutter': 'Open',
              'Blanking Amp.': 'off', 'H Trig. mode': 'Cont', 'H Trig. status': 'Reset', 'H Trig. level': '0.5',
              'H Trig. slope': 'Rising', 'FocusTimeOver': '5', 'Delay': '0'}

        TODO: handle unrecognised/unavailable parameters/devices

        :param base_name: str
        :param sub_level: str
        :param sub_sub_level: str
        :return:
        """
        self._logger.debug('Getting parameter: %s %s %s' % (base_name, sub_level, sub_sub_level))
        if base_name is None:
            return_dict = dict()
            for base_name in self.parameters:
                return_dict[base_name] = self.get_parameter(base_name)
            return return_dict

        command = self.parameters[base_name]['get']
        base_dictionary = self.parameters[base_name]['value']

        if sub_level is not None and sub_sub_level is not None:
            return self.send_command(command, sub_level, sub_sub_level)
        elif sub_sub_level is None:
            sub_dictionary = base_dictionary[sub_level]
            if isinstance(sub_dictionary, dict):
                return_dict = dict()
                for subsublevel in list(sub_dictionary.keys()):
                    return_dict[subsublevel] = self.get_parameter(base_name, sub_level, subsublevel)
                return return_dict
            else:
                return self.send_command(command, sub_level, sub_sub_level)
        else:
            return_dict = dict()
            for sublevel in list(base_dictionary.keys()):
                return_dict[sublevel] = self.get_parameter(base_name, sublevel)
            return return_dict

    def set_parameter(self, base_name, sub_level=None, sub_sub_level=None, value=None):
        """Sets streak parameter(s)

        >>>> streak.set_parameter('General', 'ShowStreakControl', None, 1)
        >>>> streak.set_parameter('General', value=dict(ShowStreakControl=1, ShowDelay1Control=0))
        >>>> streak.set_parameter('Camera', 'Acquire', 'Exposure', '1 s')

        TODO: handle unrecognised/unavailable parameters/devices

        :param base_name: str
        :param sub_level: str
        :param sub_sub_level: str
        :param value: str/int/float or a dictionary of values. If a single value is given, it should correspond to the
        parameter located by combining base_name, sublevel and subsublevel. If a dictionary, all key/value pairs should
        be the same as those in base_name+sublevel
        :return:
        """
        self._logger.debug('Setting parameter: %s %s %s %s' % (base_name, sub_level, sub_sub_level, value))
        assert base_name in self.parameters
        assert value is not None  # always need a value
        command = self.parameters[base_name]['set']
        if command is None:
            self._logger.warn('Cannot set %s' % base_name)
            return
        base_dictionary = self.parameters[base_name]['value']

        if sub_level is not None and sub_sub_level is not None:
            self.send_command(command, sub_level, sub_sub_level, value)
        elif sub_sub_level is None:
            sub_dictionary = base_dictionary[sub_level]
            if isinstance(sub_dictionary, dict):
                for sub_sub_level, subsub_value in list(value.items()):
                    assert sub_sub_level in sub_dictionary
                    self.set_parameter(base_name, sub_level, sub_sub_level, subsub_value)
            else:
                self.send_command(command, sub_level, value)
        else:
            for sub_level, values in list(value.items()):
                self.set_parameter(base_name, sub_level, sub_sub_level, values)

    def get_parameter_info(self, base_name, sub_level=None, sub_sub_level=None):
        """

        >>>> streak.get_parameter_info('Devices', 'TD', 'Time Range')
        >>>> '-1,-1,Time Range,2,2,5,1,2,3,4,5'

        # TODO: parse reply into more useful strings (need to read through the manual for this)

        :param base_name: str
        :param sub_level: str
        :param sub_sub_level: str
        :return:
        """
        self._logger.debug('Getting parameter info: %s %s %s' % (base_name, sub_level, sub_sub_level))
        assert base_name in self.parameters
        command = self.parameters[base_name]['info']
        if command is None:
            self._logger.warn('Cannot get info %s' % base_name)
        base_values = self.parameters[base_name]['value']

        if sub_level is not None and sub_sub_level is not None:
            return self.send_command(command, sub_level, sub_sub_level)
        elif sub_sub_level is None:
            sub_values = base_values[sub_level]
            if isinstance(sub_values, dict):
                return_vals = dict()
                for sub_sub_level in list(sub_values.keys()):
                    return_vals[sub_sub_level] = self.get_parameter_info(base_name, sub_level, sub_sub_level)
                return return_vals
            else:
                return self.send_command(command, sub_level, sub_sub_level)
        else:
            return_vals = dict()
            for sub_level in list(base_values.keys()):
                return_vals[sub_level] = self.get_parameter_info(base_name, sub_level)
            return return_vals

    '''General commands'''
    def stop(self):
        """
        Stops the command currently executed. Not currently available due to the VISA communication being locked
        :return:
        """
        self.send_command('Stop')

    def shutdown(self):
        """
        This command shuts down the application and the RemoteEx program. Response is sent before shutdown.
        The usefulness of this command is limited because it cannot be sent once the application has hung. Restarting of
        the remote application if an error has occurred should be done by other means (example: Power off and on the
        computer from remote and starting the RemoteEx from the autostart).

        :return:
        """
        self.send_command('Shutdown')

    '''Application commands'''

    def start_app(self, visible=1, ini_file=None):
        """Starts the application on the remote computer

        If the application has already been started this command returns immediately, otherwise it waits until it has
        been started completely. This can take a while, so the timeout is increased to 2 minutes.

        :param visible: int or bool. If 0/False, initiates an invisible application (no window in remote computer). If
            ommitted or any other value, initiates a visible application. Ignored if application is already running
        :param ini_file: str. File location. If given, the application starts with the INI-File (new from version 8.3.0).
            This parameter is also ignored if the application is already running.
        :return:
        """
        timeout = self.instr.timeout
        self.instr.timeout = 120000

        if ini_file is not None:
            self.send_command('AppStart', visible, ini_file)
        else:
            self.send_command('AppStart', visible)

        self.instr.timeout = timeout

    '''Acquisition commands'''

    def start_acquisition(self, mode='Acquire', wait=True):
        """
        This command starts an acquisition.
        :param mode: one of the following:
                'Live'      Live mode
                'Acquire'   Acquire mode
                'AI'        Analog integration
                'PC'        Photon counting
        :param wait: bool. Whether to wait until the acquisition is done
        :return:
        """
        self.send_command('AcqStart', mode)
        if wait:
            while self.is_acquisition_busy():
                time.sleep(0.1)

    def is_acquisition_busy(self):
        """
        This command returns the status of an acquisition.
        :return:
        """
        reply = self.send_command('AcqStatus').split(',')
        if reply[0] == 'idle':
            return False
        elif reply[0] == 'busy':
            return True
        else:
            raise ValueError('Unrecognised status: %s' % reply)

    def stop_acquisition(self, timeout=1000):
        """
        This command stops the currently running acquisition. It can have an optional parameter (available
        from 8.2.0 pf5) indicating the timeout value (in ms) until this command should wait for an
        acquisition to end. The range of this timeout value is [1...60000] and the default value is 1000 (if
        not specified)
        # TODO: somehow get the AcquisitionStop/SequenceStop functionality working. Threads in the background?
        :param timeout:
        :return: 0,AcqStop (Successfully stopped)
                or
                7,AcqStop,timeout (Timeout while waiting for stop)
        """
        self.send_command('AcqStop', timeout)

    '''Camera commands'''

    def get_live_bkg(self):
        """
        This command gets a new background image which is used for real time background subtraction (RTBS). It is only
        available of LIVE mode is running.
        :return:
        """
        self.send_command('CamGetLiveBG')

    '''External device commands (HPD-TA only)'''

    def list_dev_params(self, devices=None):
        """Find list of device parameters

        Queries the streak camera devices to find their parameters, and saves them into self.parameters

        :param devices: iterable with one or more of
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
                reply = self.send_command('DevParamsList', device)
                param_list = reply.split(',')[1:]

                self.parameters['Devices']['value'][device] = {key: None for key in param_list}
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
            reply = self.send_command('ImgStatusGet', image_index, 'All')
        elif len(identifiers) == 1:
            reply = self.send_command('ImgStatusGet', image_index, 'Section', identifiers[0])
        elif len(identifiers) == 2:
            reply = self.send_command('ImgStatusGet', image_index, 'Token', identifiers[0], identifiers[1])
        else:
            raise ValueError('Too many parameters')

        # Split the large string into sections that start with a word within square parenthesis followed by a comma, and
        # then a bunch of other things until the next square parenthesis
        sections = re.findall('\[(.+?)\],([^\[]+)', reply)
        parsed_reply = dict()
        for section_title, section in sections:
            parsed_reply[section_title] = dict()
            # Divide the section into substrings of "something=something", separated by commas or the end of the line
            subsections = re.findall('(.+?)="?(.+?)"?[,"$]', section)
            for subsection, value in subsections:
                parsed_reply[section_title][subsection] = value

        return parsed_reply

    @property
    def current_index(self):
        return int(self.send_command('ImgIndexGet'))

    @current_index.setter
    def current_index(self, index):
        self.send_command('ImgIndexSet', index)

    @property
    def default_directory(self):
        return self.send_command('ImgDefaultDirGet')

    @default_directory.setter
    def default_directory(self, path):
        self.send_command('ImgDefaultDirSet', path)

    def get_img_info(self, image_index='Current'):
        """
        This command returns the image size in pixels and the Bytes per pixel of a single pixel.
        :param image_index:
        :return:
        """
        response = self.send_command('ImgDataInfo', image_index, 'Size')
        response = [int(x) for x in response.split(',')]
        shape = response[:4]
        bytes_per_pixel = response[-1]
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

    def auto_lut(self):
        """Automatically sets the LUT of the current image"""
        return self.send_command('LutSetAuto')

    '''Sequence commands'''

    def start_sequence(self, directory=None, wait=False):
        """Starts a streak sequence

        :param directory: str or None. If not None, the images in the sequence will be automatically saved to the given
            directory in the remote computer
        :param wait: bool. If True, waits until the acquisition is finished before returning
        :return:
        """
        if directory is not None:
            self.set_parameter('Sequence', 'StoreTo', 'HD <individual files - all modes>')
            self.set_parameter('Sequence', 'FirstImgToStore', directory)
        self.send_command('SeqStart')

        if wait:
            while self.is_sequence_busy():
                time.sleep(0.5)

    def stop_sequence(self):
        self.send_command('SeqStop')

    def is_sequence_busy(self):
        reply = self.send_command('SeqStatus')
        split_reply = reply.split(',')
        if split_reply[0] == 'idle':
            return False
        elif split_reply[0] == 'busy':
            return True
        else:
            raise ValueError('Unrecognised sequence status: %s' % reply)

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
        """Utility function that takes an image and returns the data array

        # TODO: test capturing and returning a sequence

        :param mode:
        :param save:
        :param delete:
        :param save_kwargs:
        :return:
        """
        if mode == 'Acquire':
            self.start_acquisition(mode)

            if save:
                self.save_image(**save_kwargs)
                if delete:
                    self.delete_image()
            else:
                shape, pixel_size = self.get_img_info()
                n_pixels = (shape[2] - shape[0]) * (shape[3] - shape[1])

                self.get_image_data()
                self._logger.debug('Receiving: %s pixels of size %g' % (n_pixels, pixel_size))

                image = []
                for pxl_num in range(n_pixels):
                    pixel = self.data_socket.recv(pixel_size)
                    pixel_value = struct.unpack('h', pixel)[0]
                    image += [pixel_value]
                image = np.array(image).reshape((shape[3] - shape[1], shape[2] - shape[0]))
                if delete:
                    self.delete_image()
                return image
        elif mode == 'Sequence':
            self.start_sequence(wait=True)

            if delete:
                self.delete_sequence()
        else:
            raise ValueError('Capture mode not recognised')


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
