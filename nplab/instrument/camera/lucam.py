# -*- coding: utf-8 -*-
# lucam.py

# Copyright (c) 2010-2014, Christoph Gohlke
# Copyright (c) 2010-2014, The Regents of the University of California
# Produced at the Laboratory for Fluorescence Dynamics.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
# * Neither the name of the copyright holders nor the names of any
#   contributors may be used to endorse or promote products derived
#   from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""Lumenera(r) USB Camera Interface.

The module contains two main interfaces to the Lumenera LuCam API:

*API*, a low level ctypes interface to the lucamapi.dll version 5,
    exposing all definitions/declarations found in the lucam.h C header.

*Lucam*, a high level object interface wrapping most of the ctypes interface,
    featuring exception based error handling and numpy.array type images.

:Author:
  `Christoph Gohlke <http://www.lfd.uci.edu/~gohlke/>`_

:Organization:
  Laboratory for Fluorescence Dynamics, University of California, Irvine

:Version: 2013.01.18

Requirements
------------
* `CPython 2.7 or 3.3 <http://www.python.org>`_
* `Numpy 1.7 <http://www.numpy.org>`_
* `Lumenera USB camera and drivers 5.0 <http://www.lumenera.com/>`_

Notes
-----
"Lumenera" is a registered trademark of Lumenera Corporation (1).

This module has been tested only with the Lu165M monochrome camera on Windows.

Some LuCam API functions are not yet available in the Lucam wrapper due to
lack of documentation or hardware for testing.

Naming of functions, methods, and constants that have an equivalent in
the LuCam API follows the LuCam API conventions, else PEP8 is followed.

Documentation in HTML format can be generated with Epydoc.

References
----------
(1) `Lumenera Corporation <http://www.lumenera.com/>`_
(2) Lumenera USB Camera API Reference Manual Release 5.0. Lumenera Corporation.

Examples
--------
>>> from lucam import Lucam
>>> camera = Lucam()
>>> image = camera.TakeSnapshot()
>>> camera.SaveImage(image, 'test.tif')

Refer to the test() function at the end of the document for more examples.

"""
from __future__ import print_function



from builtins import str
from builtins import hex
from builtins import range
from builtins import object
import sys
import ctypes

import numpy
import copy

__version__ = '2013.01.18'
__docformat__ = 'restructuredtext en'
__all__ = ['API', 'Lucam', 'LucamEnumCameras', 'LucamNumCameras',
           'LucamError', 'LucamGetLastError', 'LucamSynchronousSnapshots',
           'LucamPreviewAVI', 'LucamConvertBmp24ToRgb24']


def API():
    """Return ctypes interface to the lucamapi.dll dynamic library.

    Raise WindowsError if the LuCam drivers are not installed.

    """
    from numpy.ctypeslib import ndpointer
    from ctypes import c_int, c_char_p, c_void_p, POINTER, WINFUNCTYPE
    from ctypes.wintypes import (BOOL, BYTE, FLOAT, LONG, ULONG, USHORT,
                                 DWORD, LPCSTR, LPCWSTR, HANDLE, HWND, HMENU)

    pUCHAR_LUT = ndpointer(dtype=numpy.uint8, ndim=1, flags='C_CONTIGUOUS')
    pUCHAR_RGB = ndpointer(dtype=numpy.uint8, ndim=3, flags='C_CONTIGUOUS')
    pFLOAT_MATRIX33 = ndpointer(dtype=numpy.float32, ndim=2, shape=(3, 3),
                                flags='C_CONTIGUOUS')

    UCHAR = ctypes.c_ubyte
    LONGLONG = ctypes.c_longlong
    LPCTSTR = LPCSTR
    pBYTE = POINTER(BYTE)
    pUCHAR = POINTER(UCHAR)
    pFLOAT = POINTER(FLOAT)
    pLONG = POINTER(LONG)
    pULONG = POINTER(ULONG)
    pUSHORT = POINTER(USHORT)
    pHANDLE = POINTER(HANDLE)
    pLONGLONG = POINTER(LONGLONG)

    class LUCAM_VERSION(ctypes.Structure):
        """Lucam version structure."""
        _fields_ = [
            ('firmware', ULONG),
            ('fpga', ULONG),
            ('api', ULONG),
            ('driver', ULONG),
            ('serialnumber', ULONG),
            ('reserved', ULONG)]

        def __str__(self):
            return print_structure(self)

    class LUCAM_FRAME_FORMAT(ctypes.Structure):
        """Lucam frame format structure."""
        class X(ctypes.Union):
            _fields_ = [('subSampleX', USHORT), ('binningX', USHORT)]

        class Y(ctypes.Union):
            _fields_ = [('subSampleY', USHORT), ('binningY', USHORT)]

        _anonymous_ = ['_x', '_y']
        _fields_ = [
            ('xOffset', ULONG),
            ('yOffset', ULONG),
            ('width', ULONG),
            ('height', ULONG),
            ('pixelFormat', ULONG),
            ('_x', X),
            ('flagsX', USHORT),
            ('_y', Y),
            ('flagsY', USHORT)]

        def __str__(self):
            return print_structure(self)

    class LUCAM_SNAPSHOT(ctypes.Structure):
        """Lucam snapshot settings structure."""
        class GAINS(ctypes.Union):
            class RBGG(ctypes.Structure):
                _fields_ = [
                    ('gainRed', FLOAT),
                    ('gainBlue', FLOAT),
                    ('gainGrn1', FLOAT),
                    ('gainGrn2', FLOAT)]

            class MCYY(ctypes.Structure):
                _fields_ = [
                    ('gainMag', FLOAT),
                    ('gainCyan', FLOAT),
                    ('gainYel1', FLOAT),
                    ('gainYel2', FLOAT)]

            _anonymous_ = ['_rbgg', '_mcyy']
            _fields_ = [('_rbgg', RBGG), ('_mcyy', MCYY)]

        class STROBE(ctypes.Union):
            _fields_ = [('useStrobe', BOOL), ('strobeFlags', ULONG)]

        _anonymous_ = ['_gains', '_strobe']
        _fields_ = [
            ('exposure', FLOAT),  # time in ms to expose image before readout
            ('gain', FLOAT),  # overall gain as a multiplicative factor
            ('_gains', GAINS),
            ('_strobe', STROBE),
            ('strobeDelay', FLOAT),  # delay in ms from exposure to flash
            ('useHwTrigger', c_int),  # wait for hardware trigger
            ('timeout', FLOAT),  # max time in ms to wait for trigger
            ('format', LUCAM_FRAME_FORMAT),
            ('shutterType', ULONG),
            ('exposureDelay', FLOAT),  # delay in ms from trigger to exposure
            ('bufferlastframe', BOOL),
            ('ulReserved2', ULONG),
            ('flReserved1', FLOAT),
            ('flReserved2', FLOAT)]

        def __str__(self):
            return print_structure(self)

    class LUCAM_CONVERSION(ctypes.Structure):
        """Lucam conversion structure."""
        _fields_ = [
            ('DemosaicMethod', ULONG),
            ('CorrectionMatrix', ULONG)]

    class LUCAM_CONVERSION_PARAMS(ctypes.Structure):
        """Structure used for new conversion functions."""
        class GAINS(ctypes.Union):
            class YUV(ctypes.Structure):
                _fields_ = [
                    ('DigitalGain', FLOAT),
                    ('DigitalWhiteBalanceU', FLOAT),
                    ('DigitalWhiteBalanceV', FLOAT)]

            class RGB(ctypes.Structure):
                _fields_ = [
                    ('DigitalGainRed', FLOAT),
                    ('DigitalGainGreen', FLOAT),
                    ('DigitalGainBlue', FLOAT)]

            _anonymous_ = ['_yuv', '_rgb']
            _fields_ = [('_yuv', YUV), ('_rgb', RGB)]

        _anonymous_ = ['_gains']
        _fields_ = [
            ('Size', ULONG),
            ('DemosaicMethod', ULONG),
            ('CorrectionMatrix', ULONG),
            ('FlipX', BOOL),
            ('FlipY', BOOL),
            ('Hue', FLOAT),
            ('Saturation', FLOAT),
            ('UseColorGainsOverWb', BOOL),
            ('_gains', GAINS)]

        def __str__(self):
            return print_structure(self)

    class LUCAM_IMAGE_FORMAT(ctypes.Structure):
        """Image format information."""
        _fields_ = [
            ('Size', ULONG),
            ('Width', ULONG),
            ('Height', ULONG),
            ('PixelFormat', ULONG),
            ('ImageSize', ULONG),
            ('LucamReserved', ULONG * 8)]

        def __str__(self):
            return print_structure(self)

    pLUCAM_VERSION = POINTER(LUCAM_VERSION)
    pLUCAM_FRAME_FORMAT = POINTER(LUCAM_FRAME_FORMAT)
    pLUCAM_SNAPSHOT = POINTER(LUCAM_SNAPSHOT)
    pLUCAM_CONVERSION = POINTER(LUCAM_CONVERSION)
    pLUCAM_CONVERSION_PARAMS = POINTER(LUCAM_CONVERSION_PARAMS)
    pLUCAM_IMAGE_FORMAT = POINTER(LUCAM_IMAGE_FORMAT)

    # Callback function types
    SnapshotCallback = WINFUNCTYPE(None, c_void_p, pBYTE, ULONG)
    VideoFilterCallback = WINFUNCTYPE(None, c_void_p, pBYTE, ULONG)
    RgbVideoFilterCallback = WINFUNCTYPE(None, c_void_p, pBYTE, ULONG, ULONG)
    ProgressCallback = WINFUNCTYPE(BOOL, c_void_p, FLOAT)
    Rs232Callback = WINFUNCTYPE(None, c_void_p)

    # Function return and argument types
    LucamNumCameras = (LONG, )
    LucamEnumCameras = (LONG, pLUCAM_VERSION, ULONG)
    LucamCameraOpen = (HANDLE, ULONG)
    LucamCameraClose = (BOOL, HANDLE)
    LucamCameraReset = (BOOL, HANDLE)
    LucamQueryVersion = (BOOL, HANDLE, pLUCAM_VERSION)
    LucamQueryExternInterface = (BOOL, HANDLE, pULONG)
    LucamGetCameraId = (BOOL, HANDLE, pULONG)
    LucamGetProperty = (BOOL, HANDLE, ULONG, pFLOAT, pLONG)
    LucamSetProperty = (BOOL, HANDLE, ULONG, FLOAT, LONG)
    LucamPropertyRange = (BOOL, HANDLE, ULONG, pFLOAT, pFLOAT, pFLOAT, pLONG)
    LucamDisplayPropertyPage = (BOOL, HANDLE, HWND)
    LucamDisplayVideoFormatPage = (BOOL, HANDLE, HWND)
    LucamQueryDisplayFrameRate = (BOOL, HANDLE, pFLOAT)
    LucamCreateDisplayWindow = (
        BOOL, HANDLE, LPCTSTR, ULONG, c_int, c_int, c_int, c_int, HWND, HMENU)
    LucamDestroyDisplayWindow = (BOOL, HANDLE)
    LucamAdjustDisplayWindow = (
        BOOL, HANDLE, LPCTSTR, c_int, c_int, c_int, c_int)
    LucamReadRegister = (BOOL, HANDLE, LONG, LONG, pLONG)
    LucamWriteRegister = (BOOL, HANDLE, LONG, LONG, pLONG)
    LucamSetFormat = (BOOL, HANDLE, pLUCAM_FRAME_FORMAT, FLOAT)
    LucamGetFormat = (BOOL, HANDLE, pLUCAM_FRAME_FORMAT, pFLOAT)
    LucamEnumAvailableFrameRates = (ULONG, HANDLE, ULONG, pFLOAT)
    LucamStreamVideoControl = (BOOL, HANDLE, ULONG, HWND)
    LucamStreamVideoControlAVI = (BOOL, HANDLE, ULONG, LPCWSTR, HWND)
    LucamTakeVideo = (BOOL, HANDLE, LONG, pBYTE)
    LucamTakeVideoEx = (BOOL, HANDLE, pBYTE, pULONG, ULONG)
    LucamCancelTakeVideo = (BOOL, HANDLE)
    LucamTakeSnapshot = (BOOL, HANDLE, pLUCAM_SNAPSHOT, pBYTE)
    LucamSaveImage = (BOOL, ULONG, ULONG, ULONG, pBYTE, LPCSTR)  # deprecated
    LucamSaveImageEx = (BOOL, HANDLE, ULONG, ULONG, ULONG, pBYTE, LPCSTR)
    LucamSaveImageW = (BOOL, ULONG, ULONG, ULONG, pBYTE, LPCWSTR)  # deprecated
    LucamSaveImageWEx = (BOOL, HANDLE, ULONG, ULONG, ULONG, pBYTE, LPCWSTR)
    LucamAddStreamingCallback = (LONG, HANDLE, VideoFilterCallback, c_void_p)
    LucamRemoveStreamingCallback = (BOOL, HANDLE, LONG)
    LucamAddRgbPreviewCallback = (
        LONG, HANDLE, RgbVideoFilterCallback, c_void_p, ULONG)
    LucamRemoveRgbPreviewCallback = (BOOL, HANDLE, LONG)
    LucamQueryRgbPreviewPixelFormat = (BOOL, HANDLE, pULONG)
    LucamAddSnapshotCallback = (LONG, HANDLE, SnapshotCallback, c_void_p)
    LucamRemoveSnapshotCallback = (BOOL, HANDLE, LONG)
    LucamConvertFrameToRgb24 = (
        BOOL, HANDLE, pUCHAR_RGB, pBYTE, ULONG, ULONG, ULONG,
        pLUCAM_CONVERSION)
    LucamConvertFrameToRgb32 = (
        BOOL, HANDLE, pBYTE, pBYTE, ULONG, ULONG, ULONG, pLUCAM_CONVERSION)
    LucamConvertFrameToRgb48 = (
        BOOL, HANDLE, pUSHORT, pUSHORT, ULONG, ULONG, ULONG, pLUCAM_CONVERSION)
    LucamConvertFrameToGreyscale8 = (
        BOOL, HANDLE, pBYTE, pBYTE, ULONG, ULONG, ULONG, pLUCAM_CONVERSION)
    LucamConvertFrameToGreyscale16 = (
        BOOL, HANDLE, pUSHORT, pUSHORT, ULONG, ULONG, ULONG, pLUCAM_CONVERSION)
    LucamConvertBmp24ToRgb24 = (None, pUCHAR_RGB, ULONG, ULONG)
    LucamConvertRawAVIToStdVideo = (BOOL, HANDLE, LPCWSTR, LPCWSTR, ULONG)
    LucamPreviewAVIOpen = (HANDLE, LPCWSTR)
    LucamPreviewAVIClose = (BOOL, HANDLE)
    LucamPreviewAVIControl = (BOOL, HANDLE, ULONG, HWND)
    LucamPreviewAVIGetDuration = (
        BOOL, HANDLE, pLONGLONG, pLONGLONG, pLONGLONG, pLONGLONG)
    LucamPreviewAVIGetFrameCount = (BOOL, HANDLE, pLONGLONG)
    LucamPreviewAVIGetFrameRate = (BOOL, HANDLE, pFLOAT)
    LucamPreviewAVIGetPositionTime = (
        BOOL, HANDLE, pLONGLONG, pLONGLONG, pLONGLONG, pLONGLONG)
    LucamPreviewAVIGetPositionFrame = (BOOL, HANDLE, pLONGLONG)
    LucamPreviewAVISetPositionTime = (
        BOOL, HANDLE, LONGLONG, LONGLONG, LONGLONG, LONGLONG)
    LucamPreviewAVISetPositionFrame = (BOOL, HANDLE, LONGLONG)
    LucamPreviewAVIGetFormat = (BOOL, HANDLE, pLONG, pLONG, pLONG, pLONG)
    LucamSetupCustomMatrix = (BOOL, HANDLE, pFLOAT_MATRIX33)
    LucamGetCurrentMatrix = (BOOL, HANDLE, pFLOAT_MATRIX33)
    LucamEnableFastFrames = (BOOL, HANDLE, pLUCAM_SNAPSHOT)
    LucamTakeFastFrame = (BOOL, HANDLE, pBYTE)
    LucamForceTakeFastFrame = (BOOL, HANDLE, pBYTE)
    LucamTakeFastFrameNoTrigger = (BOOL, HANDLE, pBYTE)
    LucamDisableFastFrames = (BOOL, HANDLE)
    LucamSetTriggerMode = (BOOL, HANDLE, BOOL)
    LucamTriggerFastFrame = (BOOL, HANDLE)
    LucamCancelTakeFastFrame = (BOOL, HANDLE)
    LucamEnableSynchronousSnapshots = (
        HANDLE, ULONG, pHANDLE, POINTER(pLUCAM_SNAPSHOT))
    LucamTakeSynchronousSnapshots = (BOOL, HANDLE, POINTER(pBYTE))
    LucamDisableSynchronousSnapshots = (BOOL, HANDLE)
    LucamGpioRead = (BOOL, HANDLE, pBYTE, pBYTE)
    LucamGpioWrite = (BOOL, HANDLE, BYTE)
    LucamGpoSelect = (BOOL, HANDLE, BYTE)
    LucamGpioConfigure = (BOOL, HANDLE, BYTE)
    LucamOneShotAutoExposure = (
        BOOL, HANDLE, UCHAR, ULONG, ULONG, ULONG, ULONG)
    LucamOneShotAutoWhiteBalance = (BOOL, HANDLE, ULONG, ULONG, ULONG, ULONG)
    LucamOneShotAutoWhiteBalanceEx = (
        BOOL, HANDLE, FLOAT, FLOAT, ULONG, ULONG, ULONG, ULONG)
    LucamDigitalWhiteBalance = (BOOL, HANDLE, ULONG, ULONG, ULONG, ULONG)
    LucamDigitalWhiteBalanceEx = (
        BOOL, HANDLE, FLOAT, FLOAT, ULONG, ULONG, ULONG, ULONG)
    LucamAdjustWhiteBalanceFromSnapshot = (
        BOOL, HANDLE, pLUCAM_SNAPSHOT, pBYTE, FLOAT, FLOAT, ULONG, ULONG,
        ULONG, ULONG)
    LucamOneShotAutoIris = (BOOL, HANDLE, UCHAR, ULONG, ULONG, ULONG, ULONG)
    LucamContinuousAutoExposureEnable = (
        BOOL, HANDLE, UCHAR, ULONG, ULONG, ULONG, ULONG, FLOAT)
    LucamContinuousAutoExposureDisable = (BOOL, HANDLE)
    LucamAutoFocusStart = (
        BOOL, HANDLE, ULONG, ULONG, ULONG, ULONG, FLOAT, FLOAT, FLOAT,
        ProgressCallback, c_void_p)
    LucamAutoFocusWait = (BOOL, HANDLE, DWORD)
    LucamAutoFocusStop = (BOOL, HANDLE)
    LucamAutoFocusQueryProgress = (BOOL, HANDLE, pFLOAT)
    LucamInitAutoLens = (BOOL, HANDLE, BOOL)
    LucamSetup8bitsLUT = (BOOL, HANDLE, pUCHAR_LUT, ULONG)
    LucamSetup8bitsColorLUT = (
        BOOL, HANDLE, pUCHAR_LUT, ULONG, BOOL, BOOL, BOOL, BOOL)
    LucamRs232Transmit = (c_int, HANDLE, c_char_p, c_int)
    LucamRs232Receive = (c_int, HANDLE, c_char_p, c_int)
    LucamAddRs232Callback = (BOOL, HANDLE, Rs232Callback, c_void_p)
    LucamRemoveRs232Callback = (None, HANDLE)
    LucamPermanentBufferRead = (BOOL, HANDLE, pUCHAR, ULONG, ULONG)
    LucamPermanentBufferWrite = (BOOL, HANDLE, pUCHAR, ULONG, ULONG)
    LucamGetTruePixelDepth = (BOOL, HANDLE, pULONG)
    LucamSetTimeout = (BOOL, HANDLE, BOOL, FLOAT)
    LucamGetLastError = (ULONG, )
    LucamGetLastErrorForCamera = (ULONG, HANDLE)

    # Pixel format IDs
    LUCAM_PF_8 = 0  # 8 bit raw or monochrome data
    LUCAM_PF_16 = 1  # 16 bit raw or monochrome data
    LUCAM_PF_24 = 2  # 24 bit color data; 8 bits for red, green and blue
    LUCAM_PF_YUV422 = 3  # 16 bit YUV data
    LUCAM_PF_COUNT = 4  # count of pixels with intensity above threshold
    LUCAM_PF_FILTER = 5  # only pixels with intensity above threshold
    LUCAM_PF_32 = 6  # 32 bit color data; 8 bits for red, green, blue and alpha
    LUCAM_PF_48 = 7  # 48 bit color data; 16 bits for red, green and blue
    # Properties uses to access camera settings
    LUCAM_PROP_BRIGHTNESS = 0
    LUCAM_PROP_CONTRAST = 1
    LUCAM_PROP_HUE = 2
    LUCAM_PROP_SATURATION = 3
    LUCAM_PROP_SHARPNESS = 4
    LUCAM_PROP_GAMMA = 5
    LUCAM_PROP_PAN = 16
    LUCAM_PROP_TILT = 17
    LUCAM_PROP_ROLL = 18
    LUCAM_PROP_ZOOM = 19
    LUCAM_PROP_EXPOSURE = 20
    LUCAM_PROP_IRIS = 21
    LUCAM_PROP_FOCUS = 22
    LUCAM_PROP_GAIN = 40
    LUCAM_PROP_GAIN_RED = 41
    LUCAM_PROP_GAIN_BLUE = 42
    LUCAM_PROP_GAIN_GREEN1 = 43
    LUCAM_PROP_GAIN_GREEN2 = 44
    LUCAM_PROP_GAIN_MAGENTA = 41
    LUCAM_PROP_GAIN_CYAN = 42
    LUCAM_PROP_GAIN_YELLOW1 = 43
    LUCAM_PROP_GAIN_YELLOW2 = 44
    LUCAM_PROP_DEMOSAICING_METHOD = 64
    LUCAM_PROP_CORRECTION_MATRIX = 65
    LUCAM_PROP_FLIPPING = 66
    LUCAM_PROP_DIGITAL_WHITEBALANCE_U = 69
    LUCAM_PROP_DIGITAL_WHITEBALANCE_V = 70
    LUCAM_PROP_DIGITAL_GAIN = 71
    LUCAM_PROP_DIGITAL_GAIN_RED = 72
    LUCAM_PROP_DIGITAL_GAIN_GREEN = 73
    LUCAM_PROP_DIGITAL_GAIN_BLUE = 74
    LUCAM_PROP_COLOR_FORMAT = 80
    LUCAM_PROP_MAX_WIDTH = 81
    LUCAM_PROP_MAX_HEIGHT = 82
    LUCAM_PROP_ABS_FOCUS = 85
    LUCAM_PROP_BLACK_LEVEL = 86
    LUCAM_PROP_KNEE1_EXPOSURE = 96
    LUCAM_PROP_STILL_KNEE1_EXPOSURE = 96
    LUCAM_PROP_KNEE2_EXPOSURE = 97
    LUCAM_PROP_STILL_KNEE2_EXPOSURE = 97
    LUCAM_PROP_STILL_KNEE3_EXPOSURE = 98
    LUCAM_PROP_VIDEO_KNEE = 99
    LUCAM_PROP_KNEE1_LEVEL = 99
    LUCAM_PROP_THRESHOLD = 101
    LUCAM_PROP_AUTO_EXP_TARGET = 103
    LUCAM_PROP_TIMESTAMPS = 105
    LUCAM_PROP_SNAPSHOT_CLOCK_SPEED = 106  # 0 is fastest
    LUCAM_PROP_AUTO_EXP_MAXIMUM = 107
    LUCAM_PROP_TEMPERATURE = 108
    LUCAM_PROP_TRIGGER = 110
    LUCAM_PROP_FRAME_GATE = 112
    LUCAM_PROP_EXPOSURE_INTERVAL = 113
    LUCAM_PROP_PWM = 114
    LUCAM_PROP_MEMORY = 115  # value is RO and represent # of frames in memory
    LUCAM_PROP_STILL_STROBE_DURATION = 116
    LUCAM_PROP_FAN = 118
    LUCAM_PROP_SYNC_MODE = 119
    LUCAM_PROP_SNAPSHOT_COUNT = 120
    LUCAM_PROP_LSC_X = 121
    LUCAM_PROP_LSC_Y = 122
    LUCAM_PROP_AUTO_IRIS_MAX = 123
    LUCAM_PROP_LENS_STABILIZATION = 124
    LUCAM_PROP_VIDEO_TRIGGER = 125
    LUCAM_PROP_KNEE2_LEVEL = 163
    LUCAM_PROP_THRESHOLD_LOW = 165
    LUCAM_PROP_THRESHOLD_HIGH = 166
    LUCAM_PROP_TEMPERATURE2 = 167
    LUCAM_PROP_LIGHT_FREQUENCY = 168
    LUCAM_PROP_LUMINANCE = 169
    LUCAM_PROP_AUTO_GAIN_MAXIMUM = 170
    LUCAM_PROP_AUTO_SHARPNESS_GAIN_THRESHOLD_LOW = 171
    LUCAM_PROP_AUTO_SHARPNESS_GAIN_THRESHOLD_HIGH = 172
    LUCAM_PROP_AUTO_SHARPNESS_LOW = 173
    LUCAM_PROP_AUTO_SHARPNESS_HIGH = 174
    LUCAM_PROP_JPEG_QUALITY = 256
    # Binning will be used instead of subsampling
    LUCAM_FRAME_FORMAT_FLAGS_BINNING = 0x0001
    # Property flags
    LUCAM_PROP_FLAG_USE = 0x80000000  # control use of particular property
    LUCAM_PROP_FLAG_AUTO = 0x40000000  # control use of property auto function
    LUCAM_PROP_FLAG_MASTER = 0x40000000  # LUCAM_PROP_SYNC_MODE
    LUCAM_PROP_FLAG_STROBE_FROM_START_OF_EXPOSURE = 0x20000000
    LUCAM_PROP_FLAG_BACKLASH_COMPENSATION = 0x20000000
    LUCAM_PROP_FLAG_USE_FOR_SNAPSHOTS = 0x04000000
    LUCAM_PROP_FLAG_POLARITY = 0x10000000
    LUCAM_PROP_FLAG_MEMORY_READBACK = 0x08000000  # LUCAM_PROP_MEMORY
    LUCAM_PROP_FLAG_BUSY = 0x00040000
    LUCAM_PROP_FLAG_UNKNOWN_MAXIMUM = 0x00020000
    LUCAM_PROP_FLAG_UNKNOWN_MINIMUM = 0x00010000
    LUCAM_PROP_FLAG_LITTLE_ENDIAN = 0x80000000  # for LUCAM_PROP_COLOR_FORMAT
    LUCAM_PROP_FLAG_ALTERNATE = 0x00080000
    LUCAM_PROP_FLAG_READONLY = 0x00010000
    LUCAM_PROP_FLAG_HW_ENABLE = 0x40000000  # VIDEO_TRIGGER
    LUCAM_PROP_FLAG_SW_TRIGGER = 0x00200000  # VIDEO_TRIGGER
    # Use with LUCAM_PROP_GAMMA, LUCAM_PROP_BRIGHTNESS, LUCAM_PROP_CONTRAST
    LUCAM_PROP_FLAG_RED = 0x00000001
    LUCAM_PROP_FLAG_GREEN1 = 0x00000002
    LUCAM_PROP_FLAG_GREEN2 = 0x00000004
    LUCAM_PROP_FLAG_BLUE = 0x00000008
    # Do not access these properties unless you know what you are doing
    LUCAM_PROP_STILL_EXPOSURE = 50
    LUCAM_PROP_STILL_GAIN = 51
    LUCAM_PROP_STILL_GAIN_RED = 52
    LUCAM_PROP_STILL_GAIN_GREEN1 = 53
    LUCAM_PROP_STILL_GAIN_GREEN2 = 54
    LUCAM_PROP_STILL_GAIN_BLUE = 55
    LUCAM_PROP_STILL_GAIN_MAGENTA = 52
    LUCAM_PROP_STILL_GAIN_YELLOW1 = 53
    LUCAM_PROP_STILL_GAIN_YELLOW2 = 54
    LUCAM_PROP_STILL_GAIN_CYAN = 55
    # Color formats for use with LUCAM_PROP_COLOR_FORMAT
    # Bayer format used by camera sensor
    LUCAM_CF_MONO = 0
    LUCAM_CF_BAYER_RGGB = 8
    LUCAM_CF_BAYER_GRBG = 9
    LUCAM_CF_BAYER_GBRG = 10
    LUCAM_CF_BAYER_BGGR = 11
    LUCAM_CF_BAYER_CYYM = 16
    LUCAM_CF_BAYER_YCMY = 17
    LUCAM_CF_BAYER_YMCY = 18
    LUCAM_CF_BAYER_MYYC = 19
    # Parameter for LUCAM_PROP_FLIPPING
    LUCAM_PROP_FLIPPING_NONE = 0
    LUCAM_PROP_FLIPPING_X = 1
    LUCAM_PROP_FLIPPING_Y = 2
    LUCAM_PROP_FLIPPING_XY = 3
    # Streaming Video Modes
    STOP_STREAMING = 0
    START_STREAMING = 1
    START_DISPLAY = 2
    PAUSE_STREAM = 3
    START_RGBSTREAM = 6
    # Streaming AVI Modes
    STOP_AVI = 0
    START_AVI = 1
    PAUSE_AVI = 2
    # Parameters for AVI types
    AVI_RAW_LUMENERA = 0
    AVI_STANDARD_24 = 1
    AVI_STANDARD_32 = 2
    AVI_XVID_24 = 3
    AVI_STANDARD_8 = 4
    # Use with LUCAM_CONVERSION.DemosaicMethod
    LUCAM_DM_NONE = 0
    LUCAM_DM_FAST = 1
    LUCAM_DM_HIGH_QUALITY = 2
    LUCAM_DM_HIGHER_QUALITY = 3
    LUCAM_DM_SIMPLE = 8
    # Use with LUCAM_CONVERSION.CorrectionMatrix
    LUCAM_CM_NONE = 0
    LUCAM_CM_FLUORESCENT = 1
    LUCAM_CM_DAYLIGHT = 2
    LUCAM_CM_INCANDESCENT = 3
    LUCAM_CM_XENON_FLASH = 4
    LUCAM_CM_HALOGEN = 5
    LUCAM_CM_IDENTITY = 14
    LUCAM_CM_CUSTOM = 15
    # Shutter types
    LUCAM_SHUTTER_TYPE_GLOBAL = 0
    LUCAM_SHUTTER_TYPE_ROLLING = 1
    # Extern interfaces
    LUCAM_EXTERN_INTERFACE_USB1 = 1
    LUCAM_EXTERN_INTERFACE_USB2 = 2
    # use with LucamRegisterEventNotification
    LUCAM_EVENT_START_OF_READOUT = 2
    LUCAM_EVENT_GPI1_CHANGED = 4
    LUCAM_EVENT_GPI2_CHANGED = 5
    LUCAM_EVENT_GPI3_CHANGED = 6
    LUCAM_EVENT_GPI4_CHANGED = 7
    LUCAM_EVENT_DEVICE_SURPRISE_REMOVAL = 32

    if sys.platform == 'win32':
        _api = ctypes.windll.LoadLibrary('lucamapi.dll')
    else:
        raise NotImplementedError("Only Windows is supported")

    for _name, _value in list(locals().items()):
        if _name.startswith('Lucam'):
            _func = getattr(_api, _name)
            setattr(_func, 'restype', _value[0])
            setattr(_func, 'argtypes', _value[1:])
        elif not _name.startswith('_'):
            setattr(_api, _name, _value)
    return _api


API = API()


class Lucam(object):
    """Lumenera camera interface.

    Names of wrapper functions have the 'Lucam' prefix removed from
    their API counterparts.

    Member functions raise LucamError() if an error occurs in the
    underlying API function call.

    Camera properties can be accessed in different ways. E.g. the property
    LUCAM_PROP_BRIGHTNESS of a Lucam instance 'lucam' can is accessible as:

    * lucam.GetProperty(API.LUCAM_PROP_BRIGHTNESS)
    * lucam.GetProperty('brightness')
    * lucam.brightness

    """
    Version = API.LUCAM_VERSION
    FrameFormat = API.LUCAM_FRAME_FORMAT
    Snapshot = API.LUCAM_SNAPSHOT
    Conversion = API.LUCAM_CONVERSION
    ConversionParams = API.LUCAM_CONVERSION_PARAMS
    ImageFormat = API.LUCAM_IMAGE_FORMAT

    PROPERTY = {}
    PROP_FLAG = {}
    PROP_FLIPPING = {}
    PIXEL_FORMAT = {}
    COLOR_FORMAT = {}
    DEMOSAIC_METHOD = {}
    CORRECT_MATRIX = {}
    EXTERN_INTERFACE = {}
    AVI_TYPE = {}
    EVENT_ID = {}

    for name in dir(API):
        value = getattr(API, name)
        if name.startswith('_'):
            continue
        elif name.startswith('LUCAM_PROP_FLAG_'):
            PROP_FLAG[name[16:].lower()] = value
        elif name.startswith('LUCAM_PROP_FLIPPING_'):
            PROP_FLIPPING[name[20:].lower()] = value
        elif name.startswith('LUCAM_PROP_'):
            PROPERTY[name[11:].lower()] = value
        elif name.startswith('LUCAM_PF_'):
            PIXEL_FORMAT[name[9:].lower()] = value
        elif name.startswith('LUCAM_CF_'):
            COLOR_FORMAT[name[9:].lower()] = value
        elif name.startswith('LUCAM_CM_'):
            CORRECT_MATRIX[name[9:].lower()] = value
        elif name.startswith('LUCAM_DM_'):
            DEMOSAIC_METHOD[name[9:].lower()] = value
        elif name.startswith('LUCAM_EVENT_'):
            EVENT_ID[name[12:].lower()] = value
        elif name.startswith('AVI_'):
            AVI_TYPE[name[4:].lower()] = value
        elif name.startswith('LUCAM_EXTERN_INTERFACE_'):
            EXTERN_INTERFACE[value] = name[23:]
    #del value
    #del name

    VIDEO_CONTROL = dict(stop_streaming=0, start_streaming=1, start_display=2,
                         pause_stream=3, start_rgbstream=6)

    def __init__(self, number=1):
        """Open connection to Lumenera camera.

        number : int
            Camera number. Must be in range 1 through LucamNumCameras().

        """
        self._handle = API.LucamCameraOpen(number)
        if not self._handle:
            raise LucamError(API.LucamGetLastError())
        self._byteorder = '<' if self.is_little_endian() else '>'
        self._default_frameformat, self._default_framerate = self.GetFormat()
        self._fastframe = None  # frame format while in fast frame mode
        self._streaming = None  # frame format while in streaming mode
        self._callbacks = {}  # references to callback functions
        self._displaying_window = False

    def __del__(self):
        """Close connection to camera."""
        assert not self._displaying_window
        assert self._fastframe is None
        assert self._streaming is None
        if self._handle:
            API.LucamCameraClose(self._handle)

    def __str__(self):
        """Return detailed information about camera as string."""
        default = self._default_frameformat
        camid = self.GetCameraId()
        version = self.QueryVersion()
        interface = self.QueryExternInterface()
        frame, fps = self.GetFormat()
        allfps = self.EnumAvailableFrameRates()
        depth = self.GetTruePixelDepth()
        littleendian = self.is_little_endian()
        gpo, gpi = self.GpioRead()
        pixformat = 'raw8 raw16 RGB24 YUV422 Count Filter RGBA32 RGB48'.split()

        result = [
            "",
            "Camera handle: %s" % hex(int(self._handle)),
            "Camera ID: %s" % hex(int(camid)),
            "Camera model: %s" % CAMERA_MODEL.get(camid, "Unknown"),
            "Serial number: %s" % version.serialnumber,
            "Firmware version: %s" % print_version(version.firmware),
            "FPGA version: %s" % print_version(version.fpga),
            "API version: %s" % print_version(version.api),
            "Driver version: %s" % print_version(version.driver),
            "Interface: %s" % Lucam.EXTERN_INTERFACE[interface],
            "Endianess: %s" % ("little" if littleendian else "big"),
            "GPIO output registers: 0x%01X" % gpo,
            "GPIO input registers: 0x%01X" % gpi,
            "Default size: %i x %i" % (default.width, default.height),
            "Default pixel format: %s" % pixformat[default.pixelFormat],
            "Default frame rate: %.2f" % self._default_framerate,
            "Image offset: %i, %i" % (frame.xOffset, frame.yOffset),
            "Image size: %i x %i" % (frame.width // frame.binningX,
                                     frame.height // frame.binningY),
            "Binning: %ix%i" % (frame.binningX, frame.binningY)
            if frame.flagsX else
            "Subsampling: %ix%i" % (frame.subSampleX, frame.subSampleY),
            "Pixel format: %s" % pixformat[frame.pixelFormat],
            "Pixel depth: %i bit" % (depth if frame.pixelFormat else 8),
            "Frame rate: %.2f" % fps,
            "Available frame rates: %s" % ', '.join('%.2f' % f
                                                    for f in allfps)
        ]
        #mn = API.FLOAT()
        #mx = API.FLOAT()
        value = API.FLOAT()
        flags = API.LONG()
        for name in sorted(Lucam.PROPERTY):
            prop = Lucam.PROPERTY[name]
            if API.LucamGetProperty(self._handle, prop, value, flags):
                name = name.capitalize().replace('_', ' ')
                if flags.value:
                    result.append("%s: %s (%s)" % (
                        name, value.value,
                        ",".join(list_property_flags(flags.value))))
                else:
                    result.append("%s: %s" % (name, value.value))
            #if API.LucamPropertyRange(self._handle, prop,
            #                          mn, mx, value, flags):
            #    result.append("%s range: %s" % (name, print_range(
            #            mn.value, mx.value, value.value, flags.value)))
        return "\n* ".join(result)

    def __getattr__(self, name):
        """Return value of PROPERTY or PROP_RANGE attribute."""
        if name in Lucam.PROPERTY:
            return self.GetProperty(name)[0]
        elif name.endswith("_range"):
            result = self.PropertyRange(name[:-6])
            setattr(self, name, result)
            return result
        raise AttributeError("'Lucam' object has no attribute '%s'" % name)

    def default_snapshot(self):
        """Return default Snapshot settings."""
        snapshot = API.LUCAM_SNAPSHOT()
        snapshot.format = self.GetFormat()[0]
        snapshot.exposure = self.GetProperty('exposure')[0]
        snapshot.gain = self.GetProperty('gain')[0]
        snapshot.timeout = 1000.0
        snapshot.gainRed = 1.0
        snapshot.gainBlue = 1.0
        snapshot.gainGrn1 = 1.0
        snapshot.gainGrn2 = 1.0
        snapshot.useStrobe = False
        snapshot.strobeDelay = 0.0
        snapshot.useHwTrigger = 0
        snapshot.shutterType = 0
        snapshot.exposureDelay = 0.0
        snapshot.bufferlastframe = 0
        return snapshot

    def default_conversion(self):
        """Return default Conversion settings for ConvertFrameToRgb24()."""
        return API.LUCAM_CONVERSION(DemosaicMethod=API.LUCAM_DM_NONE,
                                    CorrectionMatrix=API.LUCAM_CM_NONE)

    def is_little_endian(self):
        """Return Endianess of camera."""
        value, flags = self.GetProperty(API.LUCAM_PROP_COLOR_FORMAT)
        return bool(flags & API.LUCAM_PROP_FLAG_LITTLE_ENDIAN)

    def set_properties(self, **kwargs):
        """Set value of mutiple camera properties."""
        for name, value in list(kwargs.items()):
            if name.endswith('_flag'):
                continue
            prop = Lucam.PROPERTY[name]
            flag = kwargs.get(name + '_flag', 0)
            if not API.LucamSetProperty(self._handle, prop, value, flag):
                raise LucamError(self)

    def CameraClose(self):
        """Close connection to camera."""
        if self._displaying_window:
            self.DestroyDisplayWindow()
        if not API.LucamCameraClose(self._handle):
            raise LucamError(self)
        self._fastframe = None
        self._streaming = None
        self._handle = None

    def CameraReset(self):
        """Reset camera to its power-on default state."""
        if not API.LucamCameraReset(self._handle):
            raise LucamError(self)
        self._fastframe = None
        self._streaming = None

    def QueryVersion(self):
        """Return camera version information as API.LUCAM_VERSION."""
        result = API.LUCAM_VERSION()
        if not API.LucamQueryVersion(self._handle, result):
            raise LucamError(self)
        return result

    def QueryExternInterface(self):
        """Return type of interface between camera and computer.

        Return value is one of Lucam.EXTERN_INTERFACE keys.

        """
        result = API.ULONG()
        if not API.LucamQueryExternInterface(self._handle, result):
            raise LucamError(self)
        return result.value

    def GetCameraId(self):
        """Return camera model ID, one of CAMERA_MODEL keys."""
        result = API.ULONG()
        if not API.LucamGetCameraId(self._handle, result):
            raise LucamError(self)
        return result.value

    def EnumAvailableFrameRates(self):
        """Return available frame rates based on camera's clock rates."""
        result = API.FLOAT()
        size = API.LucamEnumAvailableFrameRates(self._handle, 0, result)
        result = (API.FLOAT * size)()
        if not API.LucamEnumAvailableFrameRates(self._handle, size, result):
            raise LucamError(self)
        return tuple(result)

    def QueryDisplayFrameRate(self):
        """Return average displayed frame rate since preview started."""
        result = API.FLOAT()
        if not API.LucamQueryDisplayFrameRate(self._handle, result):
            raise LucamError(self)
        return result.value

    def DisplayPropertyPage(self, parent):
        """Open a DirectShow dialog window with camera properties."""
        if not API.LucamDisplayPropertyPage(self._handle, parent):
            raise LucamError(self)

    def DisplayVideoFormatPage(self, parent):
        """Open a DirectShow dialog window with video properties."""
        if not API.LucamDisplayVideoFormatPage(self._handle, parent):
            raise LucamError(self)

    def CreateDisplayWindow(self, title=b"", style=282001408,
                            x=0, y=0, width=0, height=0, parent=0, menu=0):
        """Create window, managed by API, for displaying video.

        Parameters
        ----------
        title : byte str
            Title of window that appears in window frame.
        style : int
            Window style.
        x, y : int
           Coordinates of pixel in video stream that will appear in
           upper left corner of display window. Default = 0.
        width, height: int
            Extent of scaled video stream in pixels.

        The window is not automatically resized to the video frame size.

        """
        if not API.LucamCreateDisplayWindow(
                self._handle, title, style, x, y, width, height, parent, menu):
            raise LucamError(self)
        self._displaying_window = True

    def DestroyDisplayWindow(self):
        """Destroy display window created with CreateDisplayWindow()."""
        if not API.LucamDestroyDisplayWindow(self._handle):
            raise LucamError(self)
        self._displaying_window = False

    def AdjustDisplayWindow(self, title=b"", x=0, y=0, width=0, height=0):
        """Scale video stream into preview window.

        Parameters
        ----------
        title : byte str
            Title of window that appears in window frame.
        x, y : int
           Coordinates of pixel in video stream that will appear in
           upper left corner of display window. Can be used to pan the
           display windows across the video stream.
        width, height: int
            Extent of scaled video stream in pixels. Can be used to zoom.

        """
        if not API.LucamAdjustDisplayWindow(self._handle, title,
                                            x, y, width, height):
            raise LucamError(self)
#        self._displaying_window = True #rwb27 commented this out as it's wrong when used to adjust a window I create...

    def GetTruePixelDepth(self):
        """Return actual pixel depth when running in 16 bit mode."""
        result = API.ULONG()
        if not API.LucamGetTruePixelDepth(self._handle, result):
            raise LucamError(self)
        return result.value

    def GetVideoImageFormat(self):
        """Return video image format used to capture video frame.

        Return type is API.LUCAM_IMAGE_FORMAT.

        The video image format is needed to convert a raw Bayer frame
        to either color or greyscale using the ConvertFrame***() functions.

        """
        result = API.LUCAM_IMAGE_FORMAT()
        if not API.LucamGetVideoImageFormat(self._handle, result):
            raise LucamError(self)
        return result

    def GetLastErrorForCamera(self):
        """Return code of last error that occurred in a API function.

        Error codes and messages can be found in LucamError.CODES.

        """
        return API.LucamGetLastErrorForCamera(self._handle)

    def SetProperty(self, prop, value, flags=0):
        """Set value of camera property.

        Parameters
        ----------
        prop : int or str
            Camera property. One of Lucam.PROPERTY keys or values.
        flags : int or sequence of str
            Capability flags for property. One or combination of
            Lucam.PROP_FLAG. Default is 0.

        Not all properties are supported by all cameras. If a capability
        flag is not supported by the property, it is silently ignored.

        """
        prop = Lucam.PROPERTY.get(prop, prop)
        if isinstance(flags, (list, tuple)):
            flags, flagseq = 0x0, flags
            for f in flagseq:
                flags |= Lucam.PROP_FLAG[f]
        if not API.LucamSetProperty(self._handle, prop, value, flags):
            raise LucamError(self)

    def GetProperty(self, prop):
        """Return value and capability flag of camera property.

        Parameters
        ----------
        prop : int or str
            Camera property. One of Lucam.PROPERTY keys or values.

        """
        value = API.FLOAT()
        flags = API.LONG()
        prop = Lucam.PROPERTY.get(prop, prop)
        if not API.LucamGetProperty(self._handle, prop, value, flags):
            raise LucamError(self)
        return value.value, flags.value

    def PropertyRange(self, prop):
        """Return range of valid values for property and its default value.

        Return value is tuple of:
            minimum valid value of camera property,
            maximum valid value of camera property,
            default value of camera property,
            capability flags for property.

        """
        mn = API.FLOAT()
        mx = API.FLOAT()
        default = API.FLOAT()
        flags = API.LONG()
        prop = Lucam.PROPERTY.get(prop, prop)
        if not API.LucamPropertyRange(self._handle, prop, mn, mx,
                                      default, flags):
            raise LucamError(self)
        return mn.value, mx.value, default.value, flags.value

    def GetFormat(self):
        """Return frame format and rate of video data.

        Return type is tuple of API.LUCAM_FRAME_FORMAT and framerate.

        """
        frameformat = API.LUCAM_FRAME_FORMAT()
        framerate = API.FLOAT()
        if not API.LucamGetFormat(self._handle, frameformat, framerate):
            raise LucamError(self)
        return frameformat, framerate.value

    def SetFormat(self, frameformat, framerate):
        """Set frame format and frame rate for video data.

        Parameters
        ----------
        frameformat : API.LUCAM_FRAME_FORMAT
            Video frame format.
        framerate : float
            Frame rate for streaming video.

        The origin of the imager is top left. Each dimension of the subwindow
        must be evenly divisible by 8.

        """
        if not API.LucamSetFormat(self._handle, frameformat, framerate):
            raise LucamError(self)
        if self._fastframe:
            self._fastframe = frameformat
        if self._streaming:
            self._streaming = frameformat

    def ReadRegister(self, address, numreg):
        """Return values from contiguous internal camera registers.

        Parameters
        ----------
        address : int
            Starting register address.
        numreg : int
            Number of contiguous registers to read.

        """
        result = (API.LONG * numreg)()
        if not API.LucamReadRegister(self._handle, address, numreg, result):
            raise LucamError(self)
        return [v.value for v in result]

    def WriteRegister(self, address, values):
        """Write values to contiguous internal camera registers.

        Parameters
        ----------
        address : int
            Starting register address.
        values : sequence of int
            Values to write into registers.

        """
        numreg = len(values)
        pvalue = (API.LONG * numreg)()
        for i in range(numreg):
            pvalue[i] = values[i]
        if not API.LucamWriteRegister(self._handle, address, numreg, pvalue):
            raise LucamError(self)

    def SetTimeout(self, still, timeout):
        """Update timeout value set previously with API.LUCAM_SNAPSHOT.timeout.

        Parameters
        ----------
        still : bool
            If True, update timeout for snapshot mode, else for streaming mode.
        timeout : float
            Maximum time in ms to wait for trigger before returning from
            function.

        """
        if not API.LucamSetTimeout(self._handle, still, timeout):
            raise LucamError(self)

    def SetTriggerMode(self, usehwtrigger):
        """Sets trigger mode used for snapshots while in FastFrames mode.

        Parameters
        ----------
        usehwtrigger : bool
            If True, the camera is set to use the hardware trigger.

        """
        if not API.LucamSetTriggerMode(self._handle, usehwtrigger):
            raise LucamError(self)

    def TriggerFastFrame(self):
        """Initiate the request to take a snapshot.

        The camera should be in Fast Frames mode using EnableFastFrames().
        This function will not wait for the return of the snapshot. Use
        TakeFastFrame() or TakeFastFrameNoTrigger() to take the snapshot.

        """
        if not API.LucamTriggerFastFrame(self._handle):
            raise LucamError(self)

    def CancelTakeFastFrame(self):
        """Cancel call to TakeFastFrame() and other functions.

        Cancel calls to ForceTakeFastFrame(), TakeFastFrameNoTrigger() or
        TakeSnapshot() made in another programming thread. The cancelled
        function will raise LucamError(48).

        """
        if not API.LucamCancelTakeFastFrame(self._handle):
            raise LucamError(self)

    def EnableFastFrames(self, snapshot=None):
        """Enable fast snapshot capture mode.

        Parameters
        ----------
        snapshot : API.LUCAM_SNAPSHOT or None
            Settings to use for the snapshot. If None (default),
            settings returned by default_snapshot() will be used.

        If video is streaming when a snapshot is taken, the stream will
        automatically be stopped (pausing video in the display window if
        present) before the snapshot is taken. It is not restarted after
        the snapshot is taken.

        """
        if snapshot is None:
            snapshot = self.default_snapshot()
        self._fastframe = snapshot.format
        if not API.LucamEnableFastFrames(self._handle, snapshot):
            self._fastframe = None
            raise LucamError(self)

    def TakeFastFrame(self, out=None, validate=True):
        """Return a single image using still imaging mode.

        Parameters
        ----------
        out : numpy array, or None
            Output buffer. If None, a new numpy.array containing the image
            data is returned. Else image data will be copied into the
            output array.
        validate : bool
            If True (default), size and dtype of the output array are
            validated.

        The camera should be in Fast Frames mode using EnableFastFrames().

        """
        data, pdata = ndarray(self._fastframe, self._byteorder, out, validate)
        if not API.LucamTakeFastFrame(self._handle, pdata):
            raise LucamError(self)
        if out is None:
            return data

    def ForceTakeFastFrame(self, out=None, validate=True):
        """Force a SW triggered snapshot while in HW triggered FastFrames mode.

        Parameters
        ----------
        out : numpy array, or None
            Output buffer. If None, a new numpy.array containing the image
            data is returned. Else image data will be copied into the
            output array.
        validate : bool
            If True (default), size and dtype of the output array are
            validated.

        Return a snapshot frame without waiting for the next HW trigger.

        """
        data, pdata = ndarray(self._fastframe, self._byteorder, out, validate)
        if not API.LucamForceTakeFastFrame(self._handle, pdata):
            raise LucamError(self)
        if out is None:
            return data

    def TakeFastFrameNoTrigger(self, out=None, validate=True):
        """Return previously taken single image using still imaging mode.

        Parameters
        ----------
        out : numpy array, or None
            Output buffer. If None, a new numpy.array containing the image
            data is returned. Else image data will be copied into the
            output array.
        validate : bool
            If True (default), size and dtype of the output array are
            validated.

        To use this function, the camera should be in Fast Frames mode
        using EnableFastFrames().
        If the camera is in HW triggered mode, this function can retrieve
        a previously captured image from the API without sending an new
        snapshot request and waiting for the next snapshot.

        """
        data, pdata = ndarray(self._fastframe, self._byteorder,
                              out, validate)
        if not API.LucamTakeFastFrameNoTrigger(self._handle, pdata):
            raise LucamError(self)
        if out is None:
            return data

    def DisableFastFrames(self):
        """Disable fast snapshot capture mode.

        If the camera was streaming when EnableFastFrames() was called,
        streaming will be restored.

        """
        self._fastframe = None
        if not API.LucamDisableFastFrames(self._handle):
            raise LucamError(self)

    def TakeSnapshot(self, snapshot=None, out=None, validate=True):
        """Return single image as numpy array using still imaging.

        Parameters
        ----------
        snapshot : API.LUCAM_SNAPSHOT or None
            Settings to use for the snapshot. If None (default),
            settings returned by default_snapshot() will be used.
        out : numpy array, or None
            Output buffer. If None, a new numpy.array containing the image
            data is returned. Else image data will be copied into the
            output array.

        Equivalent to calling EnableFastFrames(), TakeFastFrame(), and
        DisableFastFrames().

        """
        if snapshot is None:
            snapshot = self.default_snapshot()
        data, pdata = ndarray(snapshot.format, self._byteorder, out, validate)
        if not API.LucamTakeSnapshot(self._handle, snapshot, pdata):
            raise LucamError(self)
        if out is None:
            return data

    def SaveImage(self, data, filename):
        """Save a single image or video frame to disk.

        Parameters
        ----------
        data : numpy array
            Input data.
        filename : str
            Name of file. The file extension indicates the file format:
            .bmp - Windows bitmap
            .jpg - Joint Photograhic Experts Group
            .tif - Tagged Image File Format
            .raw - Raw

        This function accounts for the endianess of the camera output
        when using 16 bit data.

        """
        pdata = data.ctypes.data_as(API.pBYTE)
        height, width = data.shape[-2:]
        pixelformat = {
            (2, 1): API.LUCAM_PF_8,
            (3, 1): API.LUCAM_PF_24,
            (4, 1): API.LUCAM_PF_32,
            (2, 2): API.LUCAM_PF_16,
            (3, 2): API.LUCAM_PF_48}[(data.ndim, data.dtype.itemsize)]
        if not API.LucamSaveImageWEx(self._handle, width, height,
                                     pixelformat, pdata, filename):
            raise LucamError(self)

    def StreamVideoControl(self, ctrltype, window=0):
        """Control streaming video.

        Parameters
        ----------
        ctrltype : str or int
            One of Lucam.VIDEO_CONTROL keys or values.
            'start_display' starts video streaming and displays it in window.
            'start_streaming' starts video streaming without display.
            'stop_streaming' stops video streaming.
            'pause_stream' pauses video streaming.
        window : int
            Handle of window to stream video to. Default is the window
            created by CreateDisplayWindow().

        """
        ctrltype = Lucam.VIDEO_CONTROL.get(ctrltype, ctrltype)
        if ctrltype in (API.START_STREAMING,
                        API.START_DISPLAY,
                        API.START_RGBSTREAM):
            self._streaming = self.GetFormat()[0]
        else:
            self._streaming = None
        if not API.LucamStreamVideoControl(self._handle, ctrltype, window):
            self._streaming = None
            raise LucamError(self)

    def TakeVideo(self, numframes, out=None, validate=True):
        """Take video frames using video mode.

        Parameters
        ----------
        numframes : int
            Number of video frames to take.
        out : numpy array, or None
            Output buffer. If None, a new numpy.array containing the image
            data is returned. Else image data will be copied into the
            output array.
        validate : bool
            If True (default), size and dtype of the output array are
            validated.

        Start the video stream with StreamVideoControl() before calling
        this function.

        """
        data, pdata = ndarray(self._streaming, self._byteorder, out,
                              validate, numframes)
        if numframes is None:
            numframes = data.shape[0]
        if not API.LucamTakeVideo(self._handle, numframes, pdata):
            raise LucamError(self)
        if out is None:
            return data

    def TakeVideoEx(self, out=None, timeout=100.0, validate=True):
        """Return coordinates of video data greater than a specified threshold.

        This function is not implemented yet.

        """
        raise NotImplementedError()

    def CancelTakeVideo(self):
        """Cancel call to TakeVideo() and TakeVideoEx() made in another thread.

        The cancelled function will raise LucamError(48).

        """
        if not API.LucamCancelTakeVideo(self._handle):
            raise LucamError(self)

    def StreamVideoControlAVI(self, ctrltype, filename='', window=0):
        """Control capture of the video in a raw 8 bit AVI file.

        Parameters
        ----------
        ctrltype : str or int
            One of Lucam.VIDEO_CONTROL keys or values:
                'start_display'
                    Starts capture of the video and displays it in window.
                'start_streaming'
                    Captures the video without displaying it, which gives an
                    AVI file with higher quality and frame rate.
                'stop_streaming'
                    Stops video streaming.
                'pause_stream'
                   Pauses video streaming.
        filename : str
            Name of AVI file.
        window : int
            Handle of window to stream video to. Default is the window
            created by CreateDisplayWindow().

        """
        ctrltype = Lucam.VIDEO_CONTROL.get(ctrltype, ctrltype)
        if not API.LucamStreamVideoControlAVI(self._handle, ctrltype,
                                              filename, window):
            raise LucamError(self)

    def ConvertRawAVIToStdVideo(self, outfile, inputfile, outtype=1):
        """Convert raw 8 bit AVI file to 24 or 32 bit standard RGB AVI.

        Parameters
        ----------
        outfile : str
            Name of output AVI file. Must be different from inputfile.
        inputfile : str
            Name of input AVI file obtained with StreamVideoControlAVI().
        outtype : str or int
            Output AVI type: 'standard_24' (default) or 'standard_32'.

        """
        outtype = Lucam.AVI_TYPE.get(outtype, outtype)
        if not API.LucamConvertRawAVIToStdVideo(self._handle, outfile,
                                                inputfile, outtype):
            raise LucamError(self)

    def ConvertFrameToRgb24(self, frameformat, source_frame_pointer, conversion_params=None):
        """Return RGB24 image from raw Bayer data."""
        """
        LucamConvertFrameToRgb24 = (
        BOOL, HANDLE, pUCHAR_RGB, pBYTE, ULONG, ULONG, ULONG,
        pLUCAM_CONVERSION)
    LucamConvertFrameToRgb32 = (
        BOOL, HANDLE, pBYTE, pBYTE, ULONG, ULONG, ULONG, pLUCAM_CONVERSION)
    LucamConvertFrameToRgb48 = (
        BOOL, HANDLE, pUSHORT, pUSHORT, ULONG, ULONG, ULONG, pLUCAM_CONVERSION)
    LucamConvertFrameToGreyscale8 = (
        BOOL, HANDLE, pBYTE, pBYTE, ULONG, ULONG, ULONG, pLUCAM_CONVERSION)
    LucamConvertFrameToGreyscale16 = (
        BOOL, HANDLE, pUSHORT, pUSHORT, ULONG, ULONG, ULONG, pLUCAM_CONVERSION)"""
        if conversion_params is None:
                conversion_params = self.default_conversion()
                conversion_params.DemosaicMethod = API.LUCAM_DM_FAST #need to think about defaults
        f = frameformat
        outputformat = copy.copy(frameformat)
        outputformat.pixelFormat = API.LUCAM_PF_24 #need to modify the frame format for the output
        dest, pDest = ndarray(outputformat)
        w, h = f.width // (f.binningX * f.subSampleX), f.height // (f.binningY * f.subSampleY)
        if not API.LucamConvertFrameToRgb24(self._handle, dest, source_frame_pointer, 
                                            w, h, frameformat.pixelFormat, conversion_params):
            raise LucamError(self)
        return dest

    def ConvertFrameToRgb32(self):
        """Return RGB32 image from raw Bayer data."""
        raise NotImplementedError()

    def ConvertFrameToRgb48(self):
        """Return RGB48 image from raw Bayer data."""
        raise NotImplementedError()

    def ConvertFrameToGreyscale8(self, data, out=None, settings=None):
        """Return 8 bit grayscale image from raw Bayer data."""
        raise NotImplementedError()

    def ConvertFrameToGreyscale16(self, data, out=None, settings=None):
        """Return 16 bit grayscale image from raw Bayer data."""
        raise NotImplementedError()

    def Setup8bitsLUT(self, lut):
        """Populate 8 bit LUT inside camera.

        lut : numpy array, or None
            If None, camera LUT is disabled.
            Else lut.shape must be (256,) and lut.dtype must be uint8.

        """
        lut = numpy.array(lut if lut else [], numpy.uint8)
        if not API.LucamSetup8bitsLUT(self._handle, lut, lut.size):
            raise LucamError(self)

    def Setup8bitsColorLUT(self, lut, red=False, green1=False,
                           green2=False, blue=False):
        """Populate 8 bit Color LUT inside camera.

        Parameters
        ----------
        lut : numpy array, or None
            If None, camera LUT is disabled.
            Else lut.shape must be (256,) and lut.dtype must be uint8.
        red, green1, green2, blue: bool
            Apply lut to color channel.

        """
        lut = numpy.array(lut if lut else [], numpy.uint8)
        if not API.LucamSetup8bitsColorLUT(self._handle, lut, lut.size,
                                           red, green1, green2, blue):
            raise LucamError(self)

    def SetupCustomMatrix(self, matrix):
        """Defines color correction matrix for converting raw data to RGB24.

        Parameters
        ----------
        matrix : numpy array
            3x3 color correction matrix.

        The ConvertFrameToRgb24() function requires a color correction matrix
        parameter. The pre-defined ones may be used, but when a specific
        matrix is required, the LUCAM_CM_CUSTOM parameter can be passed and
        the values defined using this function will be used.

        """
        matrix = numpy.array(matrix, numpy.float32, copy=False)
        if not API.LucamSetupCustomMatrix(self._handle, matrix):
            raise LucamError(self)

    def GetCurrentMatrix(self):
        """Return current color correction matrix."""
        matrix = numpy.empty((3, 3), numpy.float32)
        if not API.LucamGetCurrentMatrix(self._handle, matrix):
            raise LucamError(self)
        return matrix

    def AddStreamingCallback(self, callback, context=None):
        """Add video filter callback function and return callback Id.

        Parameters
        ----------
        callback : function
            API.VideoFilterCallback.
            The function is called after each frame of streaming video
            is returned from the camera.
        context : object
            Context data to be passed to callback function.

        """
        # asVoidPtr = ctypes.pythonapi.PyCObject_AsVoidPtr #this function converts PyCObject to void *, why is it not in ctypes natively...?
        # asVoidPtr.restype = ctypes.c_void_p #we need to set the result and argument types of the imported function
        # asVoidPtr.argtypes = [ctypes.py_object]        
        callback = API.VideoFilterCallback(callback)
        if context is not None:
            context = ctypes.py_object(context)
        callbackid = API.LucamAddStreamingCallback(self._handle,
                                                   callback, context)
        if callbackid == -1:
            raise LucamError(self)
        self._callbacks[(API.VideoFilterCallback, callbackid)] = callback
        return callbackid
        # callback = API.VideoFilterCallback(callback)
        # if context is not None:
        #     context = ctypes.py_object(context)
        # callbackid = API.LucamAddStreamingCallback(self._handle,
        #                                            callback, context)
        # if callbackid == -1:
        #     raise LucamError(self)
        # self._callbacks[(API.VideoFilterCallback, callbackid)] = callback
        # return callbackid

    def RemoveStreamingCallback(self, callbackid):
        """Remove previously registered video filter callback function.

        Parameters
        ----------
        callbackid : int
            Data filter callback function registered with
            AddStreamingCallback().

        """
        if not API.LucamRemoveStreamingCallback(self._handle, callbackid):
            raise LucamError(self)
        del self._callbacks[(API.VideoFilterCallback, callbackid)]

    def AddSnapshotCallback(self, callback, context=None):
        """Add data filter callback function and return callback Id.

        Parameters
        ----------
        callback : function
            API.SnapshotCallback
            The function is called after each hardware triggered snapshot
            is returned from the camera but before it is processed.
        context : object
            Context data to be passed to callback function.

        """
        callback = API.SnapshotCallback(callback)
        if context is not None:
            context = ctypes.py_object(context)
        callbackid = API.LucamAddSnapshotCallback(self._handle,
                                                  callback, context)
        if callbackid == -1:
            raise LucamError(self)
        self._callbacks[(API.SnapshotCallback, callbackid)] = callback
        return callbackid

    def RemoveSnapshotCallback(self, callbackid):
        """Remove previously registered data filter callback function.

        Parameters
        ----------
        callbackid : int
            Data filter callback function registered with
            AddSnapshotCallback().

        """
        if not API.LucamRemoveSnapshotCallback(self._handle, callbackid):
            raise LucamError(self)
        del self._callbacks[(API.SnapshotCallback, callbackid)]

    def AddRgbPreviewCallback(self, callback, pixelformat, context=None):
        """Add video filter callback function and return callback Id.

        Parameters
        ----------
        callback : function
            API.RgbVideoFilterCallback.
            This function is called after each frame of streaming video is
            returned from the camera and after it is processed.
        pixelformat : str or int
            The pixel format of the data should match the format of the video.
            Use QueryRgbPreviewPixelFormat().
            API.LUCAM_PF_24 or API.LUCAM_PF_32.
        context : object
            Context data to be passed to callback function.

        """
        callback = API.RgbVideoFilterCallback(callback)
        pixelformat = Lucam.PIXEL_FORMAT.get(pixelformat, pixelformat)
        if context is not None:
            context = ctypes.py_object(context)
        callbackid = API.LucamAddRgbPreviewCallback(self._handle, callback,
                                                    context, pixelformat)
        if callbackid == -1:
            raise LucamError(self)
        self._callbacks[(API.RgbVideoFilterCallback, callbackid)] = callback
        return callbackid

    def RemoveRgbPreviewCallback(self, callbackid):
        """Remove previously registered video filter callback function.

        Parameters
        ----------
        callbackid : int
            Video filter callback function registered with
            AddRgbPreviewCallback().

        """
        if not API.LucamRemoveRgbPreviewCallback(self._handle, callbackid):
            raise LucamError(self)
        del self._callbacks[(API.RgbVideoFilterCallback, callbackid)]

    def QueryRgbPreviewPixelFormat(self):
        """Return pixel format for preview window."""
        pixelformat = API.ULONG()
        if not API.LucamQueryRgbPreviewPixelFormat(self._handle, pixelformat):
            raise LucamError(self)
        return pixelformat.value

    def OneShotAutoExposure(self, target, startx, starty, width, height):
        """Perform one iteration of exposure adjustment to reach target.

        Parameters
        ----------
        target : int
            Target average brightness (0-255).
        startx, starty, width, height : int
            Window coordinates after any subsampling or binning.

        """
        if not API.LucamOneShotAutoExposure(self._handle, target,
                                            startx, starty, width, height):
            raise LucamError(self)

    def OneShotAutoWhiteBalance(self, startx, starty, width, height):
        """Perform one iteration of analog gain adjustment.

        Parameters
        ----------
        startx, starty, width, height : int
            Window coordinates after any subsampling or binning.

        Perform a single on-chip analog gain adjustment on the video stream
        in order to color balance the image.

        """
        if not API.LucamOneShotAutoWhiteBalance(self._handle,
                                                startx, starty, width, height):
            raise LucamError(self)

    def OneShotAutoWhiteBalanceEx(self, redovergreen, blueovergreen,
                                  startx, starty, width, height):
        """Perform one iteration of exposure adjustment to reach target color.

        Parameters
        ----------
        redovergreen, blueovergreen : float
            Red pixel value of the desired color divided by green value.
            Blue pixel value of the desired color divided by green value.
        startx, starty, width, height : int
            Window coordinates after any subsampling or binning.

        Perform a single on-chip analog gain adjustment on the video stream
        in order to color balance the image to a specific target color.

        """
        if not API.LucamOneShotAutoWhiteBalanceEx(
                self._handle, redovergreen, blueovergreen,
                startx, starty, width, height):
            raise LucamError(self)

    def DigitalWhiteBalance(self, startx, starty, width, height):
        """Perform one iteration of digital color gain adjustment.

        Parameters
        ----------
        startx, starty, width, height : int
            Window coordinates after any subsampling or binning.

        Perform a single digital gain adjustment on the video stream
        in order to color balance the image.

        """
        if not API.LucamDigitalWhiteBalance(self._handle,
                                            startx, starty, width, height):
            raise LucamError(self)

    def LucamDigitalWhiteBalanceEx(self, redovergreen, blueovergreen,
                                   startx, starty, width, height):
        """Perform one iteration of digital color gain adjustment.

        Parameters
        ----------
        redovergreen, blueovergreen : float
            Red pixel value of the desired color divided by green value.
            Blue pixel value of the desired color divided by green value.
        startx, starty, width, height : int
            Window coordinates after any subsampling or binning.

        Perform a single digital gain adjustment on the video stream
        in order to color balance the image to a specific target color.

        """
        if not API.LucamDigitalWhiteBalanceEx(
                self._handle, redovergreen, blueovergreen,
                startx, starty, width, height):
            raise LucamError(self)

    def AdjustWhiteBalanceFromSnapshot(self, snapshot, data, redovergreen,
                                       blueovergreen, startx, starty,
                                       width, height):
        """Adjust digital color gain values of previously taken snapshot.

        Parameters
        ----------
        snapshot : API.LUCAM_SNAPSHOT
            Color gain values of this structure will be changed inplace.
        data : numpy.array
            Image data acquired with given snapshot settings using
            TakeSnapshot() or TakeFastFrames().
        redovergreen, blueovergreen : float
            Red pixel value of the desired color divided by green value.
            Blue pixel value of the desired color divided by green value.
        startx, starty, width, height : int
            Window coordinates after any subsampling or binning.

        If the camera is in Fast Frames mode, this function will also update
        the current color gains used for all subsequent snapshots.

        """
        pdata = data.ctypes.data_as(API.pBYTE)
        if not API.LucamAdjustWhiteBalanceFromSnapshot(
                self._handle, snapshot, pdata, redovergreen, blueovergreen,
                startx, starty, width, height):
            raise LucamError(self)

    def OneShotAutoIris(self, target, startx, starty, width, height):
        """Perform one iteration of iris adjustment to reach target brightness.

        Parameters
        ----------
        target : int
            Target average brightness (0-255).
        startx, starty, width, height : int
            Window coordinates after any subsampling or binning.

        """
        if not API.LucamOneShotAutoIris(self._handle, target,
                                        startx, starty, width, height):
            raise LucamError(self)

    def ContinuousAutoExposureEnable(self, target, startx, starty,
                                     width, height, lightingperiod):
        """Undocumented function."""
        if not API.LucamContinuousAutoExposureEnable(
                self._handle, target, startx, starty,
                width, height, lightingperiod):
            raise LucamError(self)

    def ContinuousAutoExposureDisable(self):
        """Undocumented function."""
        if not API.LucamContinuousAutoExposureDisable(self._handle):
            raise LucamError(self)

    def LucamAutoFocusStart(self, startx, starty, width, height,
                            callback=None, context=None):
        """Start auto focus calibration.

        Parameters
        ----------
        startx, starty, width, height : int
            Window coordinates after any subsampling or binning.
        callback : function or None
            API.ProgressCallback.
            If provided, this function will be called periodically with
            the current progress of the auto focus.
        context : object
            Will be passed to callback function.

        """
        callback = API.ProgressCallback(callback if callback else 0)
        if context is not None:
            context = ctypes.py_object(context)
        if not API.LucamAutoFocusStart(self._handle, startx, starty,
                                       width, height, 0., 0., 0.,
                                       callback, context):
            raise LucamError(self)
        self._callbacks[API.ProgressCallback] = callback

    def LucamAutoFocusWait(self, timeout):
        """Wait for completion of auto focus calibration.

        Parameters
        ----------
        timeout : int
            Duration the auto focus calibration will run before terminating
            if the proper focus value is not found.

        """
        if not API.LucamAutoFocusWait(self._handle, timeout):
            raise LucamError(self)

    def LucamAutoFocusStop(self):
        """Stop auto focus calibration prematurely."""
        if not API.LucamAutoFocusStop(self._handle):
            raise LucamError(self)

    def AutoFocusQueryProgress(self):
        """Return the status in % of the auto focus calibration.

        Only available with cameras that can control a motorized lens.

        """
        percentcomplete = API.FLOAT()
        if not API.LucamAutoFocusQueryProgress(self._handle, percentcomplete):
            raise LucamError(self)
        return percentcomplete.value

    def InitAutoLens(self, force=False):
        """Initialize and calibrate camera lens focus and iris positions.

        Parameters
        ----------
        force : bool
            If True, force a recalibration of lens parameters.

        """
        if not API.LucamInitAutoLens(self._handle):
            raise LucamError(self)

    def PermanentBufferRead(self, offset=0, size=2048):
        """Return data read from user-defined non-volatile memory.

        The non-volatile memory area is 2048 bytes long.

        """
        assert 0 <= (size - offset) <= 2048
        data = numpy.zeros((size,), numpy.uint8)
        pdata = data.ctypes.data_as(API.pUCHAR)
        if not API.LucamPermanentBufferRead(self._handle, pdata, offset, size):
            raise LucamError(self)
        return data

    def PermanentBufferWrite(self, data, offset=0):
        """Write data to user-defined non-volatile memory area.

        The non-volatile memory area is 2048 bytes long and limited to
        100,000 writes.

        """
        data = numpy.array(data, numpy.uint8, copy=False)
        pdata = data.ctypes.data_as(API.pUCHAR)
        size = data.size
        assert 0 <= (size - offset) <= 2048
        if not API.LucamPermanentBufferWrite(self._handle, pdata,
                                             offset, size):
            raise LucamError(self)

    def GpioRead(self):
        """Return external header status from General Purpose IO register.

        Return value of the output and input bits of the register.

        """
        gpo = API.BYTE()
        gpi = API.BYTE()
        if not API.LucamGpioRead(self._handle, gpo, gpi):
            raise LucamError(self)
        return gpo.value, gpi.value

    def GpioWrite(self, gpovalues):
        """Write General Purpose IO register to trigger external header output.

        Parameters
        ----------
        gpovalues : int
            Value of the output bits of the register.

        """
        if not API.LucamGpioWrite(self._handle, gpovalues):
            raise LucamError(self)

    def GpoSelect(self, gpoenable):
        """Enable or disable alternate GPO functionality.

        gpoenable : int
            Bit flags used to enable/disable alternate functionality.

        """
        if not API.LucamGpoSelect(self._handle, gpoenable):
            raise LucamError(self)

    def GpioConfigure(self, enableoutput):
        """Configure direction of bi-directional GPIO pin.

        Parameters
        ----------
        enableoutput : int
            Bit flags used to disable or enable the output on a GPIO.
            Bit values of 1 configure pin as output.
            Bit values of 0 put the pin into input mode (default).

        This function is only available on Lm-based cameras.

        """
        if not API.LucamGpioConfigure(self._handle, enableoutput):
            raise LucamError(self)

    def Rs232Transmit(self):
        """Undocumented function."""
        raise NotImplementedError()

    def Rs232Receive(self):
        """Undocumented function."""
        raise NotImplementedError()

    def AddRs232Callback(self):
        """Undocumented function."""
        raise NotImplementedError()

    def RemoveRs232Callback(self):
        """Undocumented function."""
        raise NotImplementedError()


class LucamError(Exception):
    """Exception to report Lucam problems."""

    def __init__(self, arg=None):
        """Initialize LucamError instance.

        Parameters
        ----------
        arg : int, Lucam instance, or None
            If arg is None or a Lucam instance, the last error that occured
            in the API is raised. Else arg is an error code number.

        """
        if arg is None:
            self.value = API.LucamGetLastError()
        elif isinstance(arg, Lucam):
            self.value = arg.GetLastErrorForCamera()
        else:
            self.value = int(arg)

    def __str__(self):
        """Return error message."""
        return self.CODES.get(self.value, "Unknown error: %i" % self.value)

    CODES = {
        0: """NoError
            Initialization value in the API.""",
        1: """NoSuchIndex
            The index passed to LucamCameraOpen was 0. It must be >= 1.""",
        2: """SnapshotNotSupported
            The camera does not support snapshots or fast frames.""",
        3: """InvalidPixelFormat
            The pixel format parameter passed to the function is invalid.""",
        4: """SubsamplingZero
            A subsampling of zero was passed to a function.""",
        5: """Busy
            The function is unavailable because the camera is busy with
            streaming or capturing fast frames.""",
        6: """FailedToSetSubsampling
            The API failed to set the requested subsampling. This can be due
            to the camera being disconnected. It can also be due to a filter
            not being there.""",
        7: """FailedToSetStartPosition
            The API failed to set the requested subsampling. This can be due
            to the camera being disconnected.""",
        8: """PixelFormatNotSupported
            The camera does not support the pixel format passed to the
            function.""",
        9: """InvalidFrameFormat
            The format passed to the function does not pass the camera
            requirements. Verify that (xOffset + width) is not greater than
            the camera's maximum width. Verify that (width / subSamplingX)
            is a multiple of some 'nice' value. Do the same for the y.""",
        10: """PreparationFailed
            The API failed to prepare the camera for streaming or snapshot.
            This can due to the camera being disconnected. If START_STREAMING
            succeeds and START_DISPLAY fails with this error, this can be due
            to a filter not being there or registered.""",
        11: """CannotRun
            The API failed to get the camera running. This can be due to
            a bandwidth problem.""",
        12: """NoTriggerControl
            Contact Lumenera.""",
        13: """NoPin
            Contact Lumenera.""",
        14: """NotRunning
            The function failed because it requires the camera to be running,
            and it is not.""",
        15: """TriggerFailed
            Contact Lumenera.""",
        16: """CannotSetupFrameFormat
            The camera does not support that its frame format get setup.
            This will happen if your camera is plugged to a USB 1 port and
            it does not support it. LucamCameraOpen will still succeeds,
            but if a call to LucamGetLastError will return this value.""",
        17: """DirectShowInitError
            Direct Show initialization error. This may happen if you run the
            API before having installed a DS compatible camera ever before.
            The Lumenera camera is DS compatible.""",
        18: """CameraNotFound
            The function LucamCameraOpen did not find the camera # index.""",
        19: """Timeout
            The function timed out.""",
        20: """PropertyUnknown
            The API does not know the property passed to LucamGetProperty,
            LucamSetProperty or LucamGetPropertyRange. You may be using an
            old DLL.""",
        21: """PropertyUnsupported
            The camera does not support that property.""",
        22: """PropertyAccessFailed
            The API failed to access the property. Most likely, the reason
            is that the camera does not support that property.""",
        23: """LucustomNotFound
            The lucustom.ax filter was not found.""",
        24: """PreviewNotRunning
            The function failed because preview is not running.""",
        25: """LutfNotLoaded
            The function failed because lutf.ax is not loaded.""",
        26: """DirectShowError
            An error related to the operation of DirectShow occured.""",
        27: """NoMoreCallbacks
            The function LucamAddStreamingCallback failed because the API
            cannot support any more callbacks.""",
        28: """UndeterminedFrameFormat
            The API does not know what is the frame format of the camera.""",
        29: """InvalidParameter
            An parameter has an obviously wrong value.""",
        30: """NotEnoughResources
            Resource allocation failed.""",
        31: """NoSuchConversion
            One of the members of the LUCAM_CONVERSION structure passed is
            either unknown or inappropriate.""",
        32: """ParameterNotWithinBoundaries
            A parameter representing a quantity is outside the allowed
            boundaries.""",
        33: """BadFileIo
            An error occured creating a file or writing to it. Verify that
            the path exists.""",
        34: """GdiplusNotFound
            gdiplus.dll is needed and was not found.""",
        35: """GdiplusError
            gdiplus.dll reported an error. This may happen if there is a file
            IO error.""",
        36: """UnknownFormatType
            Contact Lumenera.""",
        37: """FailedCreateDisplay
            The API failed to create the display window. The reason could be
            unsufficient resources.""",
        38: """DpLibNotFound
            deltapolation.dll is needed and was not found.""",
        39: """DpCmdNotSupported
            The deltapolation command is not supported by the delta
            polation library.""",
        40: """DpCmdUnknown
            The deltapolation command is unknown or invalid.""",
        41: """NotWhilePaused
            The function cannot be performed when the camera is in
            paused state.""",
        42: """CaptureFailed
            Contact Lumenera.""",
        43: """DpError
            Contact Lumenera.""",
        44: """NoSuchFrameRate
            Contact Lumenera.""",
        45: """InvalidTarget
            One of the target parameters is wrong. This error code is used
            when startX + width > (frameFormat.width / frameFormat.subSampleX)
            or startY + height > (frameFormat.height / frameFormat.subSampleY)
            if any of those parameter is odd (not a multiple of 2) or
            or if width or height is 0.""",
        46: """FrameTooDark
            The frame is too dark to perform white balance.""",
        47: """KsPropertySetNotFound
            A DirectShow interface necessary to carry out the operation
            was not found.""",
        48: """Cancelled
            The user cancelled the operation.""",
        49: """KsControlNotSupported
            The DirectShow IKsControl interface is not supported (did you
            unplug the camera?).""",
        50: """EventNotSupported
            Some module attempted to register an unsupported event.""",
        51: """NoPreview
            The function failed because preview was not setup.""",
        52: """SetPositionFailed
            A function setting window position failed (invalid parameters).""",
        53: """NoFrameRateList
            The frame rate list is not available.""",
        54: """FrameRateInconsistent
            There was an error building the frame rate list.""",
        55: """CameraNotConfiguredForCmd
            The camera does not support that particular command.""",
        56: """GraphNotReady
            The graph is not ready.""",
        57: """CallbackSetupError
            Contact Lumenera.""",
        58: """InvalidTriggerMode
            You cannot cause a soft trigger when hw trigger is enabled.""",
        59: """NotFound
            The API was asked to return soomething that is not there.""",
        60: """EepromTooSmall
            The onboard EEPROM is too small.""",
        61: """EepromWriteFailed
            The API failed to write to the onboard eeprom.""",
        62: """UnknownFileType
            The API failed because it failed to recognize the file type of
            a file name passed to it.""",
        63: """EventIdNotSupported
            LucamRegisterEventNotification failed because the event
            is not supported.""",
        64: """EepromCorrupted
            The API found that the EEPROM was corrupted.""",
        65: """SectionTooBig
            The VPD section to write to the eeprom is too big.""",
        66: """FrameTooBright
            The frame is too bright to perform white balance.""",
        67: """NoCorrectionMatrix
            The camera is configured to have no correction matrix
            (PROPERTY_CORRECTION_MATRIX is LUCAM_CM_NONE).""",
        68: """UnknownCameraModel
            The API failed because it needs to know the camera model and it
            is not available.""",
        69: """ApiTooOld
            The API failed because it needs to be upgraded to access a
            feature of the camera.""",
        70: """SaturationZero
            The API failed because the saturation is currently 0.""",
        71: """AlreadyInitialised
            The API failed because the object was already initialised.""",
        72: """SameInputAndOutputFile
            The API failed because the object was already initialised.""",
        73: """FileConversionFailed
            The API failed because the file conversion was not completed.""",
        74: """FileAlreadyConverted
            The API failed because the file is already converted in the
            desired format.""",
        75: """PropertyPageNotSupported
            The API failed to display the property page.""",
        76: """PropertyPageCreationFailed
            The API failed to create the property page.""",
        77: """DirectShowFilterNotInstalled
            The API did not find the required direct show filter.""",
        78: """IndividualLutNotAvailable
            The camera does not support that different LUTs are applied
            to each color.""",
        79: """UnexpectedError
            Contact Lumenera.""",
        80: """StreamingStopped
            LucamTakeFastFrame or LucamTakeVideo failed because another thread
            interrupted the streaming by a call to LucamDisableFastFrames or
            LucamStreamVideoControl.""",
        81: """MustBeInSwTriggerMode
            LucamForceTakeFastFrame was called while the camera is in hardware
            trigger still mode and the camera does not support taking a sw
            trigger snapshot while in that state.""",
        82: """TargetFlaky
            The target is too flaky to perform auto focus.""",
        83: """AutoLensUninitialized
            The auto lens needs to be initialized before the function
            is used.""",
        84: """LensNotInstalled
            The function failed because the lens were not installed correctly.
            Verify that changing the focus has any effect.""",
        85: """UnknownError
            The function failed because of an unknoen error.
            Contact Lumenera.""",
        86: """FocusNoFeedbackError
            There is no feedback available for focus.""",
        87: """LutfTooOld
            LuTF.ax is too old for this feature.""",
        88: """UnknownAviFormat
            Unknown or invalid AVI format for input file.""",
        89: """UnknownAviType
            Unknown AVI type. Verify the AVI type parameter.""",
        90: """InvalidAviConversion
            The AVI conversion is invalid.""",
        91: """SeekFailed
            The seeking operation failed.""",
        92: """AviRunning
            The function cannot be performed while an AVI is being
            captured.""",
        93: """CameraAlreadyOpened
            An attempt was made to open a camera for streaming-related
            reasons while it is already opened for such.""",
        94: """NoSubsampledHighRes
            The API cannot take a high resolution image in subsampled mode
            or binning mode.""",
        95: """OnlyOnMonochrome
            The API function is only available on monochrome cameras.""",
        96: """No8bppTo48bpp
            Building a 48 bpp image from an 8 bpp image is invalid.""",
        97: """Lut8Obsolete
            Use 12 bits LUT instead.""",
        98: """FunctionNotSupported
            That functionnality is not supported.""",
        99: """RetryLimitReached
            Property access failed due to a retry limit."""}


class LucamSynchronousSnapshots(object):
    """Simultaneous image capture from multiple cameras."""

    def __init__(self, cameras=None, settings=None):
        """Enable simultaneous snapshot capture mode.

        Parameters
        ----------
        cameras : sequence of Lucam instances, or None.
            If None (default), snapshots are taken from all connected cameras.
        settings : sequence of API.LUCAM_SNAPSHOT, or None
            Settings to use for the snapshot. If None (default), the settings
            returned by Lucam.default_snapshot() will be used for each camera.

        """
        if cameras is None:
            cameras = [Lucam(i + 1) for i in range(len(LucamEnumCameras()))]
        numcams = len(cameras)
        phcameras = (API.HANDLE * numcams)()
        ppsettings = (API.pLUCAM_SNAPSHOT * numcams)()
        if settings is None:
            settings = [cam.default_snapshot() for cam in cameras]
        for i in range(numcams):
            phcameras[i] = cameras[i]._handle
            ppsettings[i] = ctypes.pointer(settings[i])
        self._cameras = cameras
        self._settings = settings
        self._handle = API.LucamEnableSynchronousSnapshots(numcams, phcameras,
                                                           ppsettings)
        if not self._handle:
            raise LucamError()

    def __del__(self):
        """Disable simultaneous snapshot capture mode."""
        if self._handle:
            API.LucamDisableSynchronousSnapshots(self._handle)

    def Disable(self):
        """Disable simultaneous snapshot capture mode."""
        if not API.LucamDisableSynchronousSnapshots(self._handle):
            raise LucamError()
        self._handle = None

    def Take(self, out=None, validate=True):
        """Simultaneously take single image from several cameras.

        Parameters
        ----------
        out : sequence of numpy arrays, or None
            Output buffer. If None, a list of new numpy.arrays containing
            the image data is returned. Else image data will be copied into
            the output arrays.

        """
        result = []
        ppdata = (API.pBYTE * len(self._cameras))()
        for i in range(len(self._cameras)):
            data, pdata = ndarray(self._settings[i].format,
                                  self._cameras[i]._byteorder,
                                  out[i] if out else None, validate)
            result.append(data)
            ppdata[i] = pdata
        if not API.LucamTakeSynchronousSnapshots(self._handle, ppdata):
            raise LucamError()
        if out is None:
            return result


class LucamPreviewAVI(object):
    """Preview AVI file."""

    CTRLTYPE = {
        'stop': API.STOP_AVI,
        'start': API.START_AVI,
        'pause': API.PAUSE_AVI}

    def __init__(self, filename):
        """Open AVI file for previewing."""
        self._handle = API.LucamPreviewAVIOpen(filename)
        if not self._handle:
            raise LucamError()
        self._filename = filename

    def __del__(self):
        """Close controller to AVI file if still open."""
        if self._handle:
            API.LucamPreviewAVIClose(self._handle)

    def __str__(self):
        """Return information about AVI as string."""
        info = self.GetFormat()
        fileformat = ('RAW_LUMENERA', 'STANDARD_24', 'STANDARD_32',
                      'XVID_24', 'STANDARD_8')[info[2]]
        return "\n* ".join((
            "",
            "File name: %s" % self._filename,
            "Type: %s" % fileformat,
            "Width: %s" % info[0],
            "Height: %s" % info[1],
            "Bit depth: %s" % info[3],
            "Frame rate: %s" % self.GetFrameRate(),
            "Frame count: %s" % self.GetFrameCount(),
            "Duration: %s:%s:%s:%s" % self.GetDuration(),
            "Current frame: %s" % self.GetPositionFrame(),
            "Current time: %s:%s:%s:%s" % self.GetPositionTime()))

    def Close(self):
        """Close controller to AVI file."""
        if not API.LucamPreviewAVIClose(self._handle):
            raise LucamError()
        self._handle = None

    def Control(self, ctrltype, window=0):
        """Control previewing of AVI video.

        Parameters
        ----------
        ctrltype : str or int
            Control type. One of LucamPreviewAVI.CTRLTYPE keys or values.
        window : int
            Handle to the window to preview video to.

        """
        ctrltype = LucamPreviewAVI.CTRLTYPE.get(ctrltype, ctrltype)
        if not API.LucamPreviewAVIControl(self._handle, ctrltype, window):
            raise LucamError()

    def GetDuration(self):
        """Return length of video."""
        minutes = API.LONGLONG()
        seconds = API.LONGLONG()
        millisecs = API.LONGLONG()
        microsecs = API.LONGLONG()
        if not API.LucamPreviewAVIGetDuration(self._handle, minutes, seconds,
                                              millisecs, microsecs):
            raise LucamError()
        return minutes.value, seconds.value, millisecs.value, microsecs.value

    def GetFrameCount(self):
        """Return total number of frames within AVI file."""
        framecount = API.LONGLONG()
        if not API.LucamPreviewAVIGetFrameCount(self._handle, framecount):
            raise LucamError()
        return framecount.value

    def GetFrameRate(self):
        """Return recorded frame rate of AVI file."""
        framerate = API.FLOAT()
        if not API.LucamPreviewAVIGetFrameRate(self._handle, framerate):
            raise LucamError()
        return framerate.value

    def GetPositionTime(self):
        """Return current time based position within AVI file."""
        minutes = API.LONGLONG()
        seconds = API.LONGLONG()
        millisecs = API.LONGLONG()
        microsecs = API.LONGLONG()
        if not API.LucamPreviewAVIGetPositionTime(
                self._handle, minutes, seconds, millisecs, microsecs):
            raise LucamError()
        return minutes.value, seconds.value, millisecs.value, microsecs.value

    def GetPositionFrame(self):
        """Return current frame based position within AVI file."""
        curframe = API.LONGLONG()
        if not API.LucamPreviewAVIGetPositionFrame(self._handle, curframe):
            raise LucamError()
        return curframe.value

    def SetPositionTime(self, minutes, seconds, millisecs, microsecs):
        """Set current time based position within AVI file."""
        if not API.LucamPreviewAVISetPositionTime(
                self._handle, minutes, seconds, millisecs, microsecs):
            raise LucamError()

    def SetPositionFrame(self, framenumber):
        """Set current frame based position within AVI file."""
        if not API.LucamPreviewAVISetPositionFrame(self._handle, framenumber):
            raise LucamError()

    def GetFormat(self):
        """Return AVI file information."""
        width = API.LONG()
        height = API.LONG()
        filetype = API.LONG()
        bitdepth = API.LONG()
        if not API.LucamPreviewAVIGetFormat(self._handle, width, height,
                                            filetype, bitdepth):
            raise LucamError()
        return width.value, height.value, filetype.value, bitdepth.value


def LucamGetLastError():
    """Return code of last error that occurred in a API function.

    Error codes and descriptions can be found in LucamError.CODES.

    """
    return API.LucamGetLastError()


def LucamNumCameras():
    """Return number of cameras attached to system."""
    num = API.LucamNumCameras()
    if num == -1:
        raise LucamError()
    return num


def LucamEnumCameras():
    """Return version information for all cameras attached to computer.

    Return type is a sequence of API.LUCAM_VERSION strutures.

    """
    num = LucamNumCameras()
    version_array = (API.LUCAM_VERSION * num)()
    num = API.LucamEnumCameras(version_array, num)
    if num == -1:
        raise LucamError()
    return version_array[:num]


def LucamConvertBmp24ToRgb24(data):
    """Convert Windows bitmap BGR24 data to RGB24.

    Parameters
    ----------
    data : numpy array
        Input data.

    Convert a frame of data from the format returned by
    Lucam.ConvertFrametoRGB24() (BGR) to standard format (RGB).

    """
    assert data.shape[2] == 3
    if not API.LucamConvertBmp24ToRgb24(data, data.shape[1], data.shape[0]):
        raise LucamError()


def ndarray(frameformat, byteorder='=', out=None, validate=True, numframes=1):
    """Return numpy.ndarray and ctypes pointer.

    Parameters
    ----------
    frameformat : API.LUCAM_FRAME_FORMAT
        Frame format.
    byteorder : char
        Byte order of 16 bit camera data:
        '<' - little endian
        '>' - big endian
        '=' - native order
    out : numpy array, or None
        If None, a new array will be returned. Else the output array
        size and dtype will be verified.
    validate : bool
        If True (default), size and dtype of the output array are
        validated.
    numframes : int
        Number of frames the array must buffer.

    """
    if out is not None and not validate:
        return out, out.ctypes.data_as(API.pBYTE)

    if (frameformat.width % frameformat.binningX
            or frameformat.height % frameformat.binningY):
        raise ValueError('Invalid frame format')

    width = frameformat.width // frameformat.binningX
    height = frameformat.height // frameformat.binningY
    pformat = frameformat.pixelFormat

    if pformat in (0, 2, 6):
        dtype = numpy.dtype('uint8')
    elif pformat in (1, 3, 7):
        dtype = numpy.dtype(byteorder + 'u2')
    else:
        raise ValueError("Pixel format not supported")

    if pformat in (0, 1, 3, 4, 5):
        shape = (height, width)
    elif pformat in (2, 7):
        shape = (height, width, 3)
    elif pformat == 6:
        shape = (height, width, 4)
    else:
        raise ValueError("Invalid pixel format")

    if out is None:
        if int(numframes) > 1:  # numframes must be provided
            shape = (numframes, ) + shape
        data = numpy.empty(shape, dtype=dtype)
    else:
        # validate size and type of output array
        if numframes is None:
            numframes = out.shape[0]
        if numframes > 1:
            shape = (numframes, ) + shape
        if numpy.prod(shape) != out.size or dtype != out.dtype:
            raise ValueError("numpy array does not match image size or type")
        data = out

    return data, data.ctypes.data_as(API.pBYTE)


def list_property_flags(flags):
    """Return list of PROPERTY_FLAG strings from flag number."""
    return [k for k, v in list(Lucam.PROP_FLAG.items()) if (v & flags)]


def print_property_range(minval, maxval, default, flags):
    """Return string representation of Lucam.PropertyRange() results."""
    if flags:
        return "[%s, %s] default=%s flags=%s" % (
            minval, maxval, default,
            ",".join(k for k, v in list(Lucam.PROP_FLAG.items()) if (v & flags)))
    else:
        return "[%s, %s] default=%s" % (minval, maxval, default)


def print_version(version):
    """Return string representation of version number."""
    class Version(ctypes.Union):
        _fields_ = [('uint', ctypes.c_uint), ('byte', ctypes.c_ubyte * 4)]

    result = []
    for i in reversed(Version(uint=version).byte):
        if i or result:
            result.append('%i' % i)
    return '.'.join(result)


def print_structure(structure, indent=""):
    """Return string representation of ctypes.Structure."""
    result = [] if indent else ['']
    for field in structure._fields_:
        name = field[0]
        attr = getattr(structure, name)
        if isinstance(attr, ctypes.Structure):
            if name in structure._anonymous_:
                line = "%s- Struct\n%s" % (
                    indent, print_structure(attr, indent + "  "))
            else:
                line = "%s* %s:\n%s" % (
                    indent, name, print_structure(attr, indent + "  "))
        elif isinstance(attr, ctypes.Union):
            line = "%s- Union\n%s" % (
                indent, print_structure(attr, indent + "  "))
        else:
            line = "%s* %s: %s" % (indent, name, attr)
        result.append(line)
    return "\n".join(result)


CAMERA_MODEL = {
    0x091: 'Lu050M, Lu055M (Discontinued)',
    0x095: 'Lu050C, Lu055C (Discontinued)',
    0x093: 'Lu056C (Discontinued)',
    0x08C: 'Lu070M, Lu075M, Lu070C, Lu075C',
    0x18C: 'Lw070M, Lw075M, Lw070C, Lw075C',
    0x28C: 'Lm075M, Lm075C',
    0x085: 'Lu080M, Lu085M, Lu080C, Lu085C',
    0x284: 'Lm085M, Lm085C',
    0x092: 'Lu100M, Lu105M, Lu100C, Lu105C',
    0x094: 'Lu110M, Lu115M, Lu110C, Lu115C (Discontinued)',
    0x49F: 'Lw110M, Lw115M, Lw110C, Lw115C',
    0x096: 'Lu120M, Lu125M, Lu120C, Lu125C',
    0x09A: 'Lu130M, Lu135M, Lu130C, Lu135C',
    0x19A: 'Lw130M, Lw135M, Lw130C, Lw135C',
    0x29A: 'Lm135M, Lm135C',
    0x08A: 'Lu160M, Lu165M, Lu160C, Lu165C',
    0x18A: 'Lw160M, Lw165M, Lw160C, Lw165C',
    0x28A: 'Lm165M, Lm165C',
    0x09E: 'Lu170M, Lu175M, Lu170C, Lu175C',
    0x082: 'Lu176C',
    0x097: 'Lu200C, Lu205C',
    0x180: 'Lw230M, Lw235M, Lw230C, Lw235C',
    0x08D: 'Lu270C, Lu275C',
    0x1CD: 'Lw290C, Lw295C',
    0x09B: 'Lu330C, Lu335C',
    0x19B: 'Lw330C, Lw335C',
    0x08B: 'Lu370C, Lu375C',
    0x1CE: 'Lw560M, Lw565M, Lw560C, Lw565C',
    0x1C5: 'Lw570M, Lw575M, Lw570C, Lw575C',
    0x186: 'Lw620M, Lw625M, Lw620C, Lw625C',
    0x1C8: 'Lw11050C, Lw11056C, Lw11057C, Lw11058C, Lw11059C',
    0x0A0: 'Infinityx-21M, Infinityx-21C',
    0x1A9: 'Infinityx-32M, Infinityx-32C',
    0x0A1: 'Infinity1-1M, Infinity 1M, Infinity1-1C, Infinity 1C',
    0x4A2: 'Infinity1-2C',
    0x0A3: 'Infinity1-3C, Infinity 3C',
    0x1Ac: 'Infinity1-5',
    0x1A6: 'Infinity1-6M, Infinity1-6C',
    0x0A2: 'Infinity 2M, Infinity 2C',
    0x1A2: 'Infinity2-1M, Infinity2-1C',
    0x1A7: 'Infinity2-2M, Infinity2-2C',
    0x1A4: 'Infinity2-3C',
    0x1A5: 'Infinity3-1M, Infinity3-1C',
    0x1AF: 'Infinity3-1UM, Infinity3-1UC',
    0x1AB: 'Infinity4-4M, Infinity4-4C',
    0x1A8: 'Infinity4-11M, Infinity4-11C'}


# Documentation in HTML format can be generated with Epydoc
__docformat__ = "restructuredtext en"


def test():
    """Demonstrate use of Lucam object and functions (monochrome only)."""
    import time

    # print serial numbers of all connected cameras
    allcameras = LucamEnumCameras()
    print(("Cameras found:",
          ", ".join(str(cam.serialnumber) for cam in allcameras)))

    # use first camera
    lucam = Lucam(1)

    # print detailed information about camera
    print(("Camera Properties", lucam))

    # set camera to 16 bit, 4x4 binning, max framerate
    lucam.SetFormat(
        Lucam.FrameFormat(0, 0, 348 * 4, 256 * 4, API.LUCAM_PF_16,
                          binningX=4, flagsX=1, binningY=4, flagsY=1),
        framerate=100.0)

    # disable all internal image enhancements
    lucam.set_properties(brightness=1.0, contrast=1.0, saturation=1.0,
                         hue=0.0, gamma=1.0, exposure=100.0, gain=1.0)

    # get actual frame format, framerate, and bit depth
    frameformat, framerate = lucam.GetFormat()
    pixeldepth = lucam.GetTruePixelDepth()
    print(("Pixel Depth:", pixeldepth))
    print(("Framerate:", framerate))
    print(("Frame Format", frameformat))

    print("Color correction matrix:")
    print(lucam.GetCurrentMatrix())

    # take snapshot, the easy way
    image = lucam.TakeSnapshot()
    import matplotlib.pyplot as plt
    plt.imshow(image)
    plt.show()

    # take another snapshot into same image buffer
    lucam.TakeSnapshot(out=image)

    # take multiple snapshots
    try:
        snapshot = Lucam.Snapshot(exposure=lucam.exposure, gain=1.0,
                                timeout=1000.0, format=frameformat)
        lucam.EnableFastFrames(snapshot)
        startsnapshots = time.clock()
        for _ in range(8):
            lucam.ForceTakeFastFrame(image, validate=False)
        endsnapshots = time.clock()
        print("Took 8 snapshots in %f seconds" % (endsnapshots - startsnapshots))
    except LucamError:
        print("Warning: ForceTakeFastFrame() failed")
    finally:
        lucam.DisableFastFrames()

    # take multiple snapshots with HW trigger enabled
    lucam.EnableFastFrames(snapshot)
    lucam.SetTriggerMode(True)
    lucam.SetTimeout(True, 100.0)  # timeout after 0.1 s
    try:
        # might time out if no HW trigger
        lucam.TakeFastFrame(image)
    except LucamError:
        print('TakeFastFrame() timed out')
    try:
        # retrieve previous image
        lucam.TakeFastFrameNoTrigger(image)
    except LucamError:
        print('TakeFastFrameNoTrigger() timed out')
    try:
        # request to take snapshot
        # seems not to work on Infinity 2??
        lucam.TriggerFastFrame()
        lucam.TakeFastFrame(image)
    except LucamError:
        print('TriggerFastFrame() TakeFastFrame() timed out')
        # force taking snapshot
    try:
        lucam.ForceTakeFastFrame(image)
    except LucamError:
        print('ForceTakeFastFrame() timed out')
    finally:
        lucam.SetTriggerMode(False)
        lucam.DisableFastFrames()

    # draw diagonal line into frame buffer
    numpy.fill_diagonal(image, 255)

    # save last image as TIFF file
    lucam.SaveImage(image, '_tmp.tif')

    # take video in streaming mode
    lucam.StreamVideoControl('start_streaming')  # streaming without display
    video = lucam.TakeVideo(8)  # take a 8 frames video
    lucam.TakeVideo(None, out=video)  # take another video into same buffer
    lucam.StreamVideoControl('stop_streaming')

    # save first video frame as RAW file
    lucam.SaveImage(video, '_tmp.raw')

    # preview video stream in window
    lucam.CreateDisplayWindow(b"Test")
    lucam.StreamVideoControl('start_display')
    time.sleep(1.0)
    lucam.AdjustDisplayWindow(width=frameformat.width * 2,
                              height=frameformat.height * 2)
    time.sleep(1.0)
    print("Display rate: %.2f" % lucam.QueryDisplayFrameRate())
    lucam.StreamVideoControl('stop_streaming')
    lucam.DestroyDisplayWindow()

    # reset camera to power-on defaults
    lucam.CameraReset()

    # set camera to 8 bit VGA mode at low framerate
    lucam.SetFormat(
        Lucam.FrameFormat(64, 64, 640, 480, API.LUCAM_PF_8,
                          binningX=1, flagsX=1, binningY=1, flagsY=1),
        framerate=10.0)
    frameformat, framerate = lucam.GetFormat()

    # run a callback function during snapshot
    def snapshot_callback(context, data, size):
        data[0] = 42
        print(("Snapshot callback function:", context, data[:2], size))
    callbackid = lucam.AddSnapshotCallback(snapshot_callback)
    image = lucam.TakeSnapshot()
    assert image[0, 0] == 42
    lucam.RemoveSnapshotCallback(callbackid)

    # run a callback function in streaming mode
    def streaming_callback(context, data, size):
        data[0] = 42
        print(("Streaming callback function:", context, data[:2], size))
    callbackid = lucam.AddStreamingCallback(streaming_callback)
    lucam.StreamVideoControl('start_streaming')
    time.sleep(2.0 / framerate)
    lucam.StreamVideoControl('stop_streaming')
    lucam.RemoveStreamingCallback(callbackid)

    # set camera look up table to invers
    lucam.Setup8bitsLUT(list(reversed(list(range(256)))))

    # stream to AVI file
    lucam.StreamVideoControlAVI('start_streaming', '_tmp.avi')
    time.sleep(1.0)
    lucam.StreamVideoControlAVI('stop_streaming')

    # reset camera look up table
    lucam.Setup8bitsLUT(None)

    # convert 8 bit AVI to 24 bit.
    lucam.ConvertRawAVIToStdVideo('_tmp24.avi', '_tmp.avi', 'standard_24')

    # Read user-defined non-volatile memory
    memory = lucam.PermanentBufferRead()
    print(("Non-volatile memory:", memory))

    # close camera connection
    lucam.CameraClose()
    del lucam

    # simultaneously take images from all connected cameras
    allcameras = [Lucam(i + 1) for i in range(len(LucamEnumCameras()))]
    sync = LucamSynchronousSnapshots(allcameras)
    data = sync.Take()  # take snapshot
    sync.Take(data)  # take second snapshot into same buffer
    sync.Disable()

    # preview AVI files
    avi = LucamPreviewAVI('_tmp.avi')
    avi.Control('start')
    time.sleep(1.0)
    avi.Control('pause')
    avi.SetPositionFrame(avi.GetFrameCount() // 2)
    avi.Control('stop')
    print(("AVI Properties", avi))
    print("Done")


if __name__ == "__main__":
    test()

