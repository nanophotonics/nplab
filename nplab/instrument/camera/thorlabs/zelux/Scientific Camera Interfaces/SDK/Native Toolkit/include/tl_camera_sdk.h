/*
* Copyright 2017 by Thorlabs, Inc.  All rights reserved.  Unauthorized use (including,
* without limitation, distribution and copying) is strictly prohibited.  All use requires, and is
* subject to, explicit written authorization and nondisclosure agreements with Thorlabs, Inc.
*/

/*! \mainpage Thorlabs Camera C API Reference
*
* \section dotnet_section Getting Started
* Getting started programming Thorlabs scientific cameras is straightforward. This guide describes
* how to program Thorlabs scientific cameras using compiled languages such as C or C++. Separate guides are available for Python, C#/VB.Net, LabVIEW, or MATLAB languages.
*
* NOTE: This guide shows function type definitions in ALL_CAPITAL_LETTERS and the corresponding function pointers in all_lowercase_letters. For example, after calling tl_camera_sdk_dll_initialize, the function pointer tl_camera_open_sdk is available with a type definition of TL_CAMERA_OPEN_SDK.
*
* All camera and mono-to-color functions are thread-safe, so no additional thread-locking is required.
*
* There are two approaches to getting images from a camera: Poll for images from any thread or register a callback that is automatically invoked on a worker thread whenever images are received from the camera. The following steps describe the order in which the APIs should be called. It is important to perform all clean-up steps at the end to avoid crashes.
*
* - Call tl_camera_sdk_dll_initialize to dynamically load the SDK DLL and get handles to its exported functions. Ensure that all required DLLs are in the same folder as the executable or discoverable in the Windows PATH variable.
* - Initialize the SDK by calling tl_camera_open_sdk.
* - Discover the serial numbers of all connected cameras by calling tl_camera_discover_available_cameras. This step must be called at least once before attempting to open any camera.
* - Open a connection to a camera by calling tl_camera_open_camera with its serial number.
* - Set camera properties like exposure, operation mode, and number of frames per trigger by calling the appropriate API functions such as tl_camera_set_exposure, tl_camera_set_operation_mode, and tl_camera_set_frames_per_trigger_zero_for_unlimited, respectively.
* - Optionally, register a callback function to enable your application to receive a notification when an image is available by calling tl_camera_set_frame_available_callback. IMPORTANT: This notification will arrive on a worker thread, and blocking this thread too long will force incoming frames to drop.
* - Prepare the camera to send images to your application by calling tl_camera_arm. After arming, only a few parameters can be set such as exposure time. See the individual parameters for which ones are available once armed.
* - Command the camera to start delivering images by calling tl_camera_issue_software_trigger or by setting up the camera to respond to external hardware triggers by setting the operation mode.
* - If a callback is registered, then the SDK will invoke the registered callback each time an image is received; otherwise, poll for an image in a loop or on a timer using tl_camera_get_pending_frame_or_null.
* - When your application has completed acquiring images, stop the camera by calling tl_camera_disarm.
* - Close the connection to the camera by calling tl_camera_close_camera.
* - Clean up and release SDK resources by calling tl_camera_close_sdk.
* - Call tl_camera_sdk_dll_terminate to unload the SDK DLL.
*/

// ReSharper disable CppEnforceTypeAliasCodeStyle

#pragma once

#include <stddef.h>  // NOLINT(modernize-deprecated-headers)

// ReSharper disable once CppUnusedIncludeDirective
#include "tl_color_enum.h"
#include "tl_polarization_processor_enums.h"

/// \file tl_camera_sdk.h
/// \brief This file includes the declarations of all API functions and data structures in the C Camera SDK.

/// <summary>
///     The TL_CAMERA_COMMUNICATION_INTERFACE enumeration defines the values the SDK uses for specifying the physical camera interface.
/// </summary>
enum TL_CAMERA_COMMUNICATION_INTERFACE
{
    /// <summary>
    ///     The camera uses the GigE Vision (GigE) interface standard.
    /// </summary>
    TL_CAMERA_COMMUNICATION_INTERFACE_GIG_E = 0,

    /// <summary>
    ///     The camera uses the CameraLink serial-communication-protocol standard.
    /// </summary>
    TL_CAMERA_COMMUNICATION_INTERFACE_CAMERA_LINK = 1,

    /// <summary>
    ///     The camera uses a USB interface.
    /// </summary>
    TL_CAMERA_COMMUNICATION_INTERFACE_USB = 2,

    /// <summary>
    ///     Marks the end of the enumeration. Do not use.
    /// </summary>
    TL_CAMERA_COMMUNICATION_INTERFACE_MAX = 3
};

/// <summary>
///     The TL_CAMERA_DATA_RATE enumeration defines the options
///     for setting the desired image data delivery rate.
/// </summary>
enum TL_CAMERA_DATA_RATE
{
    /// <summary>
    ///     Sets the device to an image readout frequency of 20 MHz.
    /// </summary>
    TL_CAMERA_DATA_RATE_READOUT_FREQUENCY_20,

    /// <summary>
    ///     Sets the device to an image readout frequency of 40 MHz.
    /// </summary>
    TL_CAMERA_DATA_RATE_READOUT_FREQUENCY_40,

    /// <summary>
    ///     Sets the device to deliver images at 30 frames per second.
    /// </summary>
    TL_CAMERA_DATA_RATE_FPS_30,

    /// <summary>
    ///     Sets the device to deliver images at 50 frames per second.
    /// </summary>
    TL_CAMERA_DATA_RATE_FPS_50,

    /// <summary>
    ///     Marks the end of the enumeration. Do not use.
    /// </summary>
    TL_CAMERA_DATA_RATE_MAX
};

// NOLINT(clang-diagnostic-documentation-unknown-command)
/// <summary>
///     The TL_CAMERA_EEP_STATUS enumeration defines the options
///     available for specifying the device's EEP mode.
///     Equal Exposure Pulse (EEP) mode is an LVTTL-level signal
///     that is active during the time when all rows have been
///     reset during rolling reset, and the end of the exposure time
///     (and the beginning of rolling readout).  The signal
///     can be used to control an external light source that will be
///     on only during the equal exposure period, providing
///     the same amount of exposure for all pixels in the ROI.\n\n
///     When EEP mode is disabled, the status will always be EEPStatus.Off.\n
///     EEP mode can be enabled, but, depending on the exposure
///     value, active or inactive.\n
///     If EEP is enabled in bulb mode, it will always give a status of Bulb.
/// </summary>
enum TL_CAMERA_EEP_STATUS
{
    /// <summary>
    ///     EEP mode is disabled.
    /// </summary>
    TL_CAMERA_EEP_STATUS_DISABLED,

    /// <summary>
    ///     EEP mode is enabled and currently active.
    /// </summary>
    TL_CAMERA_EEP_STATUS_ENABLED_ACTIVE,

    /// <summary>
    ///     EEP mode is enabled, but due to an unsupported exposure value, currently inactive.
    /// </summary>
    TL_CAMERA_EEP_STATUS_ENABLED_INACTIVE,

    /// <summary>
    ///     EEP mode is enabled in bulb mode.
    /// </summary>
    TL_CAMERA_EEP_STATUS_ENABLED_BULB,

    /// <summary>
    ///     Marks the end of the enumeration. Do not use.
    /// </summary>
    TL_CAMERA_EEP_STATUS_MAX
};

/// <summary>
///     The CAMERA_ERROR enumeration defines tl_camera_sdk error codes that can be returned from function calls.\n\n
/// </summary>
enum TL_CAMERA_ERROR
{
    /// <summary>
    ///     The command request to the camera succeeded with no errors.
    /// </summary>
    TL_CAMERA_ERROR_NONE,

    /// <summary>
    ///     The camera received an unknown command.
    /// </summary>
    TL_CAMERA_ERROR_COMMAND_NOT_FOUND,

    /// <summary>
    ///     The camera encountered too MANY arguments for the specified command.
    /// </summary>
    TL_CAMERA_ERROR_TOO_MANY_ARGUMENTS,

    /// <summary>
    ///     The camera encountered too FEW arguments for the specified command.
    /// </summary>
    TL_CAMERA_ERROR_NOT_ENOUGH_ARGUMENTS,

    /// <summary>
    ///     The camera received an invalid command.
    /// </summary>
    TL_CAMERA_ERROR_INVALID_COMMAND,

    /// <summary>
    ///     The camera received a duplicate command.
    /// </summary>
    TL_CAMERA_ERROR_DUPLICATE_COMMAND,

    /// <summary>
    ///     The camera received a command that is not documented in JSON.
    /// </summary>
    TL_CAMERA_ERROR_MISSING_JSON_COMMAND,

    /// <summary>
    ///     The camera rejected the request because the it is being initialized.
    /// </summary>
    TL_CAMERA_ERROR_INITIALIZING,

    /// <summary>
    ///     The user specified an unsupported and/or unknown command argument.
    /// </summary>
    TL_CAMERA_ERROR_NOTSUPPORTED,

    /// <summary>
    ///     The camera rejected the request because the FPGA has not been programmed with a firmware image.
    /// </summary>
    TL_CAMERA_ERROR_FPGA_NOT_PROGRAMMED,

    /// <summary>
    ///     The user specified an invalid ROI width.
    /// </summary>
    TL_CAMERA_ERROR_ROI_WIDTH_ERROR,

    /// <summary>
    ///     The user specified an invalid ROI range.
    /// </summary>
    TL_CAMERA_ERROR_ROI_RANGE_ERROR,

    /// <summary>
    ///     The user specified an invalid range for the specified command.
    /// </summary>
    TL_CAMERA_ERROR_RANGE_ERROR,

    /// <summary>
    ///     The camera rejected the request because use of the specified command is restricted.
    /// </summary>
    TL_CAMERA_ERROR_COMMAND_LOCKED,

    /// <summary>
    ///     The camera rejected the request because the specified command can only be accepted when the camera is stopped.
    /// </summary>
    TL_CAMERA_ERROR_CAMERA_MUST_BE_STOPPED,

    /// <summary>
    ///     The camera encountered an ROI/binning error.
    /// </summary>
    TL_CAMERA_ERROR_ROI_BIN_COMBO_ERROR,

    /// <summary>
    ///     The camera encountered an image data sync error.
    /// </summary>
    TL_CAMERA_ERROR_IMAGE_DATA_SYNC_ERROR,

    /// <summary>
    ///     The camera rejected the request because the specified command can only be accepted when the camera is disarmed.
    /// </summary>
    TL_CAMERA_ERROR_CAMERA_MUST_BE_DISARMED,

    /// <summary>
    ///     Marks the end of the enumeration. Do not use.
    /// </summary>
    TL_CAMERA_ERROR_MAX_ERRORS
};

/// <summary>
/// The TL_CAMERA_OPERATION_MODE enumeration defines the available mode for camera. To determine
/// which modes a camera supports, use tl_camera_get_is_operation_mode_supported().
/// </summary>
enum TL_CAMERA_OPERATION_MODE
{
    /// <summary>
    ///     Use software operation mode to generate one or more frames per trigger or to run continuous video mode.
    /// </summary>
    TL_CAMERA_OPERATION_MODE_SOFTWARE_TRIGGERED,

    /// <summary>
    ///     Use hardware triggering to generate one or more frames per trigger by issuing hardware signals.
    /// </summary>
    TL_CAMERA_OPERATION_MODE_HARDWARE_TRIGGERED,

    /// <summary>
    ///     Use bulb-mode triggering to generate one or more frames per trigger by issuing hardware signals. Please refer to the camera manual for signaling details.
    /// </summary>
    TL_CAMERA_OPERATION_MODE_BULB,

    /// <summary>
    ///     Reserved for internal use.
    /// </summary>
    TL_CAMERA_OPERATION_MODE_RESERVED1,

    /// <summary>
    ///     Reserved for internal use.
    /// </summary>
    TL_CAMERA_OPERATION_MODE_RESERVED2,

    /// <summary>
    ///     Marks the end of the enumeration. Do not use.
    /// </summary>
    TL_CAMERA_OPERATION_MODE_MAX
};

/// <summary>
/// This describes the physical capabilities of the camera sensor.
/// </summary>
enum TL_CAMERA_SENSOR_TYPE
{
    /// <summary>
    ///    Each pixel of the sensor indicates an intensity.
    /// </summary>
    TL_CAMERA_SENSOR_TYPE_MONOCHROME,

    /// <summary>
    ///     The sensor has a bayer-patterned filter overlaying it, allowing the camera SDK to distinguish red, green, and blue values.
    /// </summary>
    TL_CAMERA_SENSOR_TYPE_BAYER,

    /// <summary>
    ///     The sensor has a polarization filter overlaying it allowing the camera to capture polarization information from the incoming light.
    /// </summary>
    TL_CAMERA_SENSOR_TYPE_MONOCHROME_POLARIZED,

    /// <summary>
    ///     Marks the end of the enumeration. Do not use.
    /// </summary>
    TL_CAMERA_SENSOR_TYPE_MAX
};

/// <summary>
///     Scientific CCD cameras support one or more taps.\n\n
///     After exposure is complete, a CCD pixel array holds the charge corresponding to the amount of light collected at
///     each pixel location. The data is then read out through 1, 2, or 4 channels at a time.
/// </summary>
enum TL_CAMERA_TAPS
{
    /// <summary>
    ///     Charges are read out through a single analog-to-digital converter.
    /// </summary>
    TL_CAMERA_TAPS_SINGLE_TAP = 0,

    /// <summary>
    ///     Charges are read out through two analog-to-digital converters.
    /// </summary>
    TL_CAMERA_TAPS_DUAL_TAP = 1,

    /// <summary>
    ///     Charges are read out through four analog-to-digital converters.
    /// </summary>
    TL_CAMERA_TAPS_QUAD_TAP = 2,

    /// <summary>
    ///     Marks the end of the enumeration. Do not use.
    /// </summary>
    TL_CAMERA_TAPS_MAX_TAP = 3
};

/// <summary>
/// The TRIGGER_POLARITY enumeration defines the options available for specifying the hardware trigger polarity.\n\n
/// These values specify which edge of the input trigger pulse that will initiate image acquisition.
/// </summary>
enum TL_CAMERA_TRIGGER_POLARITY
{
    /// <summary>
    ///     Acquire an image on the RISING edge of the trigger pulse.
    /// </summary>
    TL_CAMERA_TRIGGER_POLARITY_ACTIVE_HIGH,

    /// <summary>
    ///     Acquire an image on the FALLING edge of the trigger pulse.
    /// </summary>
    TL_CAMERA_TRIGGER_POLARITY_ACTIVE_LOW,

    /// <summary>
    ///     Marks the end of the enumeration. Do not use.
    /// </summary>
    TL_CAMERA_TRIGGER_POLARITY_MAX
};

/// <summary>
/// The TL_CAMERA_USB_PORT_TYPE enumeration defines the values the SDK uses for specifying the USB bus speed.\n\n
/// These values are returned by SDK API functions and callbacks based on the type of physical USB port that the device is connected to.
/// </summary>
enum TL_CAMERA_USB_PORT_TYPE
{
    /// <summary>
    ///     The device is connected to a USB 1.0/1.1 port (1.5 Mbits/sec or 12 Mbits/sec).
    /// </summary>
    TL_CAMERA_USB_PORT_TYPE_USB1_0,

    /// <summary>
    ///     The device is connected to a USB 2.0 port (480 Mbits/sec).
    /// </summary>
    TL_CAMERA_USB_PORT_TYPE_USB2_0,

    /// <summary>
    ///     The device is connected to a USB 3.0 port (5000 Mbits/sec).
    /// </summary>
    TL_CAMERA_USB_PORT_TYPE_USB3_0,

    /// <summary>
    ///     Marks the end of the enumeration. Do not use.
    /// </summary>
    TL_CAMERA_USB_PORT_TYPE_MAX
};

/// @cond HIDDEN_VARIABLES  // NOLINT(clang-diagnostic-documentation-unknown-command)
// ReSharper disable once CppInconsistentNaming
typedef int (*_INTERNAL_COMMAND)(void *tl_camera_handle, char *data, size_t command_size_bytes_including_any_null_terminator, char *response, size_t response_size);  // NOLINT(bugprone-reserved-identifier)

/// @endcond

/// <summary>
/// Before issuing software or hardware triggers to get images from
/// a camera, prepare it for imaging by calling tl_camera_arm.\n\n
/// Depending on the desired trigger type, either call
/// tl_camera_issue_software_trigger or issue a hardware trigger.\n\n
/// To start a camera in continuous mode:\n
/// 1. Ensure that the camera is not armed.\n
/// 2. Set the operation mode to software triggered.\n
/// 3. Set the number of frames per trigger to 0 (which indicates continuous operation from a single trigger).\n
/// 4. Arm the camera.\n
/// 5. Issue a single software trigger. The camera will then self-trigger frames until tl_camera_disarm() is called.\n\n
/// To start a camera for hardware triggering:\n
/// 1. Ensure that the camera is not armed.\n
/// 2. Set the operation mode to hardware or bulb triggered.\n
/// 3. Set the number of frames per trigger to 1.\n
/// 4. Set the trigger polarity to rising- or falling-edge triggering.\n
/// 5. Arm the camera.\n
/// 6. Issue a hardware-trigger signal on the trigger input.\n\n
/// </summary>
/// <param name="tl_camera_handle">The handle to the camera to arm.</param>
/// <param name="number_of_frames_to_buffer">
/// The number of frames to allocate in the internal image buffer.
/// This should be set to 2 (or more), which allows one image to be transferring from the camera to the buffer while the other is being read out.\n\n
/// </param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_ARM)(void *tl_camera_handle, int number_of_frames_to_buffer);

/// <summary>
/// Terminates the host application's connection to the specified camera.\n\n
/// This function releases platform resources used by the camera's software abstraction and
/// generally cleans up state associated with the specified camera.
/// After calling this function, the specified handle is invalid and must NOT be used for
/// any further camera interaction.\n\n
/// Any attempt to do so is not permitted and could result in undefined behavior.
/// </summary>
/// <param name="tl_camera_handle">The handle to the camera to close.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_CLOSE_CAMERA)(void *tl_camera_handle);

/// <summary>
/// Releases any platform resources that were used by the SDK and generally cleans up SDK state.\n\n
/// This function must be called by the user application prior to exiting.\n\n
/// Any attempt to call an API function after this function has been called
/// is not permitted and could result in undefined behavior.\n\n
/// </summary>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_CLOSE_SDK)(void);

/// <summary>
/// Enables the user application to register for notifications of device connect events.\n\n
/// The SDK will invoke the registered callback function every time a device is connected to the computer.
/// </summary>
/// <param name="cameraSerialNumber">The serial number of the connected device.</param>
/// <param name="usb_port_type">The USB port type that the device was connected to.</param>
/// <param name="context">A pointer to a user specified context.  This parameter is ignored by the SDK.</param>
typedef void (*TL_CAMERA_CONNECT_CALLBACK)(char *cameraSerialNumber, enum TL_CAMERA_USB_PORT_TYPE usb_port_type, void *context);

/// <summary>
///     Converts the decibel value received from tl_camera_convert_gain_to_decibels back into a gain index value.
///     This function will return the closest index to the specified decibel gain.
/// </summary>
/// <param name="tl_camera_handle">The camera handle.</param>
/// <param name="gain_dB">The decibel value to convert.</param>
/// <param name="index_of_gain_value">A reference to receive the gain index value.</param>
/// <returns>
///     0 if successful or a positive integer error code to indicate failure. In case of error, call
///     tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_CONVERT_DECIBELS_TO_GAIN)(void *tl_camera_handle, double gain_dB, int *index_of_gain_value);

/// <summary>
///     The gain value is set in the camera with tl_camera_set_gain. It is retrieved from the camera with tl_camera_get_gain.
///     The range of possible gain values varies by camera model. It can be retrieved from the camera with tl_camera_get_gain_range.
///     The gain value units vary by camera model, but with this conversion function, it can be converted to decibels (dB).
///     A gain range of 0 to 0 means that the camera model does not support setting gain.
/// </summary>
/// <param name="tl_camera_handle">The camera handle.</param>
/// <param name="index_of_gain_value">The gain value returned by tl_camera_get_gain.</param>
/// <param name="gain_dB">A reference to receive the gain value in decibels (dB).</param>
/// <returns>
///     0 if successful or a positive integer error code to indicate failure. In case of error, call
///     tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_CONVERT_GAIN_TO_DECIBELS)(void *tl_camera_handle, int index_of_gain_value, double *gain_dB);

/// <summary>
/// When finished issuing software or hardware triggers, call
/// tl_camera_disarm(). This will cause a camera in continuous image delivery
/// mode to stop delivering images and will reset the camera's internal image
/// delivery state.\n\n
/// This allows setting parameters are are not available
/// in armed mode such as ROI and binning.\n\n
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the disarm request.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_DISARM)(void *tl_camera_handle);

/// <summary>
/// Enables the user application to register for notifications of device disconnect events.\n\n
/// The SDK will invoke the registered callback function every time a device is disconnected from the computer.
/// </summary>
/// <param name="cameraSerialNumber">The serial number of the disconnected device.</param>
/// <param name="context">A pointer to a user specified context.  This parameter is ignored by the SDK.</param>
typedef void (*TL_CAMERA_DISCONNECT_CALLBACK)(char *cameraSerialNumber, void *context);

/// <summary>
/// Returns a space character delimited list of detected camera serial numbers.\n\n
/// This step is required before opening a camera even if the serial number is already known.\n\n
/// </summary>
/// <param name="serial_numbers">A pointer to a character string to receive the serial number list.</param>
/// <param name="str_length">The size in bytes of the character buffer specified in the serial_numbers parameter.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_DISCOVER_AVAILABLE_CAMERAS)(char *serial_numbers, int str_length);

/// <summary>
/// <para>Register a callback function for notifications of frame (image) availability.</para>
/// <para>NOTE: There are two methods for getting image frames from the camera: Polling or registering for a callback.</para>
/// <para>1. Poll with the tl_camera_get_pending_frame_or_null function, typically from the main thread (polling from any thread is valid).</para>
/// <para>2. Register for a callback. In this case, frames will arrive on a worker thread to avoid interrupting the main thread. Be sure to use proper thread-locking techniques if the data needs to be marshaled from the worker thread to the main thread (such as for display in a graphical user interface).</para>
/// <para>The SDK will invoke the registered callback function every time an image is received from the camera.</para>
/// <para>IMPORTANT: The memory is allocate inside the camera SDK. The provided pointer is only valid for the duration of this callback. Either complete copy the data before returning from this callback or complete all tasks related to the image before returning.</para>
/// <para>The data for both color and monochrome cameras are ordered left to right across a row followed by the
/// next row below it.</para>
/// <para>For monochrome and color cameras, each pixel requires two bytes.</para>
/// <para>For color cameras, it is necessary to demosaic the image in order to get
/// separate blue, red, and green channels for each pixel. A performant
/// demosaic algorithm is provided in tl_mono_to_color_create_mono_to_color_processor().
/// Once demosaicked, each pixel requires two bytes for blue followed by two bytes
/// for green followed by two bytes for red (BBGGRRBBGGRRBBGGRR...).
/// Therefore, each color pixel requires six bytes. See the example color
/// applications for details on converting a monochrome mosaicked
/// image to a color demosaicked image.</para>
/// <param name="tl_camera_handle_sender">The instance of the tl_camera sending the event.</param>
/// <param name="image_buffer">The pointer to the buffer that contains the image data. The byte ordering of the data in this buffer is little-endian.  IMPORTANT: This pointer is only valid for the duration of this callback.</param>
/// <param name="frame_count">The image count corresponding to the received image during the current acquisition run.  If the image metadata section was not found, this will be 0.</param>
/// <param name="metadata">The pointer to the buffer that contains the image metadata.  The byte ordering of the data in this buffer is little-endian.  If the metadata section was not found, this will be null. IMPORTANT: This pointer is only valid for the duration of this callback. For details about the metadata, please see tl_camera_get_pending_frame_or_null.</param>
/// <param name="metadata_size_in_bytes">The size (in bytes) of the image metadata buffer. If the metadata section was not found, this will be 0.</param>
/// <param name="context">A pointer to a user specified context.  This parameter is ignored by the SDK.</param>
/// For more information on the image metadata format, click here: \ref IMAGE_METADATA_DOCUMENTATION
typedef void (*TL_CAMERA_FRAME_AVAILABLE_CALLBACK)(void *tl_camera_handle_sender, unsigned short *image_buffer, int frame_count, unsigned char *metadata, int metadata_size_in_bytes, void *context);

/// <summary>
///     Binning sums adjacent sensor pixels into "super pixels". It trades
///     off spatial resolution for sensitivity and speed. For example, if a
///     sensor is 1920 by 1080 pixels and binning is set to two in the X
///     direction and two in the Y direction, the resulting image will be 960
///     by 540 pixels. Since smaller images require less data to be
///     transmitted to the host computer, binning may increase the frame
///     rate. By default, binning is set to one in both horizontal and vertical
///     directions.\n\n
///     Gets the current horizontal binning value for the specified camera.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the horizontal binning request.</param>
/// <param name="binx">A reference to receive the current horizontal binning value.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_BINX)(void *tl_camera_handle, int *binx);

/// <summary>
///     Binning sums adjacent sensor pixels into "super pixels". It trades
///     off spatial resolution for sensitivity and speed. For example, if a
///     sensor is 1920 by 1080 pixels and binning is set to two in the X
///     direction and two in the Y direction, the resulting image will be 960
///     by 540 pixels. Since smaller images require less data to be
///     transmitted to the host computer, binning may increase the frame
///     rate. By default, binning is set to one in both horizontal and vertical
///     directions.\n\n
///     Gets the range of acceptable values for the horizontal (adjacent pixels in the X direction) binning setting for the specified camera.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the horizontal binning range request.</param>
/// <param name="hbin_min">A reference to receive the minimum acceptable value for horizontal binning.</param>
/// <param name="hbin_max">A reference to receive the maximum acceptable value for horizontal binning.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_BINX_RANGE)(void *tl_camera_handle, int *hbin_min, int *hbin_max);

/// <summary>
///     Binning sums adjacent sensor pixels into "super pixels". It trades
///     off spatial resolution for sensitivity and speed. For example, if a
///     sensor is 1920 by 1080 pixels and binning is set to two in the X
///     direction and two in the Y direction, the resulting image will be 960
///     by 540 pixels. Since smaller images require less data to be
///     transmitted to the host computer, binning may increase the frame
///     rate. By default, binning is set to one in both horizontal and vertical
///     directions.\n\n
///     Gets the current vertical binning value for the specified camera.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the vertical binning request.</param>
/// <param name="biny">A reference to receive the current vertical binning value.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_GET_BINY)(void *tl_camera_handle, int *biny);

/// <summary>
///     Binning sums adjacent sensor pixels into "super pixels". It trades
///     off spatial resolution for sensitivity and speed. For example, if a
///     sensor is 1920 by 1080 pixels and binning is set to two in the X
///     direction and two in the Y direction, the resulting image will be 960
///     by 540 pixels. Since smaller images require less data to be
///     transmitted to the host computer, binning may increase the frame
///     rate. By default, binning is set to one in both horizontal and vertical
///     directions.\n\n
///     Gets the range of acceptable values for the vertical (adjacent pixels in the Y direction) binning setting for the specified camera.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the vertical binning range request.</param>
/// <param name="vbin_min">A reference to receive the minimum acceptable value for vertical binning.</param>
/// <param name="vbin_max">A reference to receive the maximum acceptable value for vertical binning.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_GET_BINY_RANGE)(void *tl_camera_handle, int *vbin_min, int *vbin_max);

/// <summary>
/// The number of bits to which a pixel value is digitized on a camera.\n\n
/// In the image data that is delivered to the host application, the
/// bit depth indicates how many of the lower bits of each 16-bit value are relevant.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the pixel bit depth request.</param>
/// <param name="pixel_bit_depth">A reference to receive the current pixel bit depth.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_GET_BIT_DEPTH)(void *tl_camera_handle, int *pixel_bit_depth);

/// <summary>
/// Gets the current black level value for the specified camera.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the black level request.</param>
/// <param name="black_level">A reference to receive the current black level value.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_GET_BLACK_LEVEL)(void *tl_camera_handle, int *black_level);

/// <summary>
/// Gets the black level maximum value for the specified camera.
/// If the connected camera supports BlackLevel, the BlackLevelRange will have a maximum greater than zero.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the black level command.</param>
/// <param name="min">A reference to receive the black level minimum value.</param>
/// <param name="max">A reference to receive the black level maximum value.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_GET_BLACK_LEVEL_RANGE)(void *tl_camera_handle, int *min, int *max);

/// <summary>
/// Gets the output color space of the camera.
/// </summary>
typedef int (*TL_CAMERA_GET_CAMERA_COLOR_CORRECTION_MATRIX_OUTPUT_COLOR_SPACE)(void *tl_camera_handle, char *output_color_space);

/// <summary>
/// Gets the camera sensor type.
/// </summary>
typedef int (*TL_CAMERA_GET_CAMERA_SENSOR_TYPE)(void *tl_camera_handle, enum TL_CAMERA_SENSOR_TYPE *camera_sensor_type);

/// <summary>
/// Gets the default color correction matrix of the camera.
/// </summary>
typedef int (*TL_CAMERA_GET_COLOR_CORRECTION_MATRIX)(void *tl_camera_handle, float *matrix);

/// <summary>
/// Gets the the color filter array of the camera.
/// </summary>
typedef int (*TL_CAMERA_GET_COLOR_FILTER_ARRAY_PHASE)(void *tl_camera_handle, enum TL_COLOR_FILTER_ARRAY_PHASE *cfaPhase);

/// <summary>
/// Determine if active-cooling mode is enabled.
/// Some camera models include special hardware that provides additional cooling (beyond the conventional
/// passive cooling hardware) for the sensor and the internal camera chamber.\n To determine if a camera supports
/// active cooling, use tl_camera_get_is_cooling_supported().
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the cooling mode get request.</param>
/// <param name="is_cooling_enabled">A reference that receives the cooling mode enable status.\n 0 (zero) for off and 1 (one) for on.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_IS_COOLING_ENABLED)(void *tl_camera_handle, int *is_cooling_enabled);

/// <summary>
/// Gets the current value of the camera sensor-level data readout rate.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the data rate request.</param>
/// <param name="data_rate">A reference that receives the current data rate value.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_GET_DATA_RATE)(void *tl_camera_handle, enum TL_CAMERA_DATA_RATE *data_rate);

/// <summary>
/// Gets the default white balance matrix of the camera.
/// </summary>
typedef int (*TL_CAMERA_GET_DEFAULT_WHITE_BALANCE_MATRIX)(void *tl_camera_handle, float *matrix);

/// <summary>
/// Returns the current camera exposure value in microseconds.\n\n
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the exposure request.</param>
/// <param name="exposure_time_us">A reference to receive the integer exposure value in microseconds.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_EXPOSURE_TIME)(void *tl_camera_handle, long long *exposure_time_us);

/// <summary>
/// Returns the range of supported exposure values in whole microseconds for the specified camera.\n\n
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the exposure range request.</param>
/// <param name="exposure_time_us_min">A reference to receive the minimum exposure value in whole microseconds supported by the specified camera.</param>
/// <param name="exposure_time_us_max">A reference to receive the maximum exposure value in whole microseconds supported by the specified camera.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_EXPOSURE_TIME_RANGE)(void *tl_camera_handle, long long *exposure_time_us_min, long long *exposure_time_us_max);

/// <summary>
/// Returns a string containing the version information for all firmware components for the specified camera.\n\n
/// Each individual component is separated by '\r' and '\n' characters with a null terminator at the end of the
/// collection. A char buffer of size 1024 is recommended.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the firmware version request.</param>
/// <param name="firmware_version">A pointer to a character string to receive the version information.</param>
/// <param name="str_length">The length in bytes of the firmware_version buffer.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_FIRMWARE_VERSION)(void *tl_camera_handle, char *firmware_version, int str_length);

/// <summary>
/// Gets the TL_CAMERA_FRAME_AVAILABLE_CALLBACK callback function.\n\n
/// </summary>
/// <param name="tl_camera_handle">The camera handle to associate with the callback.</param>
/// <param name="handler">A pointer to the callback function.\n This function must conform to the TL_CAMERA_FRAME_AVAILABLE_CALLBACK prototype.</param>
typedef int (*TL_CAMERA_GET_FRAME_AVAILABLE_CALLBACK)(void *tl_camera_handle, TL_CAMERA_FRAME_AVAILABLE_CALLBACK *handler);

/// <summary>
/// Gets the current frame rate value for the specified camera.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the frame rate control request.</param>
/// <param name="frame_rate_fps">A reference to receive the current frame rate value in frames per second.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_GET_FRAME_RATE_CONTROL_VALUE)(void *tl_camera_handle, double *frame_rate_fps);

/// <summary>
/// Returns the time, in microseconds (us), required for a frame to be exposed and read out from the sensor.
/// When triggering frames, this property may be used to determine when the camera is ready to accept another
/// trigger. Other factors such as the communication speed between the camera and the host computer can affect the
/// maximum trigger rate.\n\n
/// NOTE: This parameters depends on tl_camera_set_frames_per_trigger_zero_for_unlimited
/// and tl_camera_set_exposure_time.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the frame time request.</param>
/// <param name="frame_time_us">A reference to receive the current frame_time_us value for the specified camera.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_FRAME_TIME)(void *tl_camera_handle, int *frame_time_us);

/// <summary>
/// Returns the current camera image poll time out value in milliseconds.\n\n
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the exposure request.</param>
/// <param name="timeout_ms">A reference to receive the time out value.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_IMAGE_POLL_TIMEOUT)(void *tl_camera_handle, int *timeout_ms);

/// <summary>
/// Gets the communication interface that the camera is connected to.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the communication interface request.</param>
/// <param name="communication_interface">A reference that receives the COMMUNICATION_INTERFACE.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_COMMUNICATION_INTERFACE)(void *tl_camera_handle, enum TL_CAMERA_COMMUNICATION_INTERFACE *communication_interface);

/// <summary>
/// Equal Exposure Pulse (EEP) mode is an LVTTL-level signal that is
/// active between the time when all rows have been reset during rolling
/// reset, and the end of the exposure time (and the beginning of rolling
/// readout).  The signal can be used to control an external light source
/// that will be triggered on only during the equal exposure period, providing the
/// same amount of exposure for all pixels in the ROI.\n\n
/// Please see the camera documentation for details on EEP mode.\n\n
/// This function gets the EEP status.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the EEP request.</param>
/// <param name="eep_status_enum">A reference that receives the current EEP status.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_GET_EEP_STATUS)(void *tl_camera_handle, enum TL_CAMERA_EEP_STATUS *eep_status_enum);

/// <summary>
/// Gets the range of acceptable values for the frames per trigger camera parameter.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the frames per trigger request.</param>
/// <param name="number_of_frames_per_trigger_min">A reference that receives the minimum valid frames per trigger value.</param>
/// <param name="number_of_frames_per_trigger_max">A reference that receives the maximum valid frames per trigger value.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_FRAMES_PER_TRIGGER_RANGE)(void *tl_camera_handle, unsigned int *number_of_frames_per_trigger_min, unsigned int *number_of_frames_per_trigger_max);

/// <summary>
/// Gets the number of frames per trigger.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the frames per trigger request.</param>
/// <param name="number_of_frames_per_trigger_or_zero_for_unlimited">A reference that receives the number of frames per trigger value.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_FRAMES_PER_TRIGGER_ZERO_FOR_UNLIMITED)(void *tl_camera_handle, unsigned int *number_of_frames_per_trigger_or_zero_for_unlimited);

/// <summary>
/// Gets the range of acceptable values for the frame rate control setting for the specified camera. If the maximum is zero, then
/// frame rate control is not supported in the camera.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the frame rate range request.</param>
/// <param name="frame_rate_fps_max">A reference to receive the maximum frame rate in frames per second. </param>
/// <param name="frame_rate_fps_min">A reference to receive the minimum frame rate in frames per second. </param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_GET_FRAME_RATE_CONTROL_VALUE_RANGE)(void *tl_camera_handle, double *frame_rate_fps_min, double *frame_rate_fps_max);

/// <summary>
///     Gets the current gain value for the specified camera.\n\n
///     The units of measure for this value vary by camera model. To convert this
///     value to decibels (dB), use tl_camera_convert_gain_to_decibels().
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the gain request.</param>
/// <param name="gain">A reference to receive the current gain value.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_GET_GAIN)(void *tl_camera_handle, int *gain);

/// <summary>
///     Get the range of possible gain values.\n\n
///     The units of measure for this value vary by camera model. To convert this
///     value to decibels (dB), use tl_camera_convert_gain_to_decibels().
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the image width range request.</param>
/// <param name="gain_min">A reference that receives the minimum value in dB * 10 for gain.</param>
/// <param name="gain_max">A reference that receives the maximum value in dB * 10 for gain.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_GAIN_RANGE)(void *tl_camera_handle, int *gain_min, int *gain_max);

/// <summary>
/// This function may be used to get the current threshold value for hot-pixel correction.\n\n
/// This value is a quantitative measure of how aggressively the camera will remove hot pixels.\n\n
/// To determine whether the camera supports hot-pixel correction, see tl_camera_get_hot_pixel_correction_threshold_range().
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the hot pixel correction threshold command.</param>
/// <param name="hot_pixel_correction_threshold">A reference that receives the current value of the hot pixel correction threshold for the specified camera.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_HOT_PIXEL_CORRECTION_THRESHOLD)(void *tl_camera_handle, int *hot_pixel_correction_threshold);

/// <summary>
/// This function may be used to get the range of acceptable hot pixel correction threshold values.\n\n
/// If the maximum value is 0 (zero), that is an indication that hot pixel correction is not supported by
/// the specified camera.\n\n
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the hot pixel correction threshold command.</param>
/// <param name="hot_pixel_correction_threshold_min">A reference that receives the minimum acceptable value for the hot pixel correction threshold.</param>
/// <param name="hot_pixel_correction_threshold_max">A reference that receives the maximum acceptable value for the hot pixel correction threshold.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_HOT_PIXEL_CORRECTION_THRESHOLD_RANGE)(void *tl_camera_handle, int *hot_pixel_correction_threshold_min, int *hot_pixel_correction_threshold_max);

/// <summary>
/// Gets the current image height in pixels.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the image width request.</param>
/// <param name="height_pixels">A reference that receives the value in pixels for the current image height.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_IMAGE_HEIGHT)(void *tl_camera_handle, int *height_pixels);

/// <summary>
/// Gets the range of possible image height values.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the image height range request.</param>
/// <param name="image_height_pixels_min">A reference that receives the minimum value in pixels for the image height.</param>
/// <param name="image_height_pixels_max">A reference that receives the maximum value in pixels for the image height.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_IMAGE_HEIGHT_RANGE)(void *tl_camera_handle, int *image_height_pixels_min, int *image_height_pixels_max);

/// <summary>
/// Gets the current image width in pixels.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the image width request.</param>
/// <param name="width_pixels">A reference that receives the value in pixels for the current image width.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_IMAGE_WIDTH)(void *tl_camera_handle, int *width_pixels);

/// <summary>
/// Get the range of possible image width values.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the image width range request.</param>
/// <param name="image_width_pixels_min">A reference that receives the minimum value in pixels for the image width.</param>
/// <param name="image_width_pixels_max">A reference that receives the maximum value in pixels for the image width.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_IMAGE_WIDTH_RANGE)(void *tl_camera_handle, int *image_width_pixels_min, int *image_width_pixels_max);

/// <summary>
/// Gets the camera is armed or not.
/// </summary>
typedef int (*TL_CAMERA_GET_IS_ARMED)(void *tl_camera_handle, int *is_armed);

/// <summary>
/// Gets the cooling is supported or not of the camera.
/// </summary>
typedef int (*TL_CAMERA_GET_IS_COOLING_SUPPORTED)(void *tl_camera_handle, int *is_cooling_supported);

/// <summary>
/// Scientific-CCD cameras and compact-scientific cameras handle sensor-
/// level data-readout speed differently.\n\n
/// Use this method to test whether the connected camera supports a particular data rate.\n\n
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the data rate request.</param>
/// <param name="data_rate">The data rate enumeration value to check for support.</param>
/// <param name="is_data_rate_supported">
/// An indication of whether or not the data rate value is supported.\n
/// A 1 (one) indicates that the specified data rate is supported and a 0 (zero) indicates that the specified data rate is not supported.
/// </param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_IS_DATA_RATE_SUPPORTED)(void *tl_camera_handle, enum TL_CAMERA_DATA_RATE data_rate, int *is_data_rate_supported);

/// <summary>
/// Gets the EEP is supported or not of the camera.
/// </summary>
typedef int (*TL_CAMERA_GET_IS_EEP_SUPPORTED)(void *tl_camera_handle, int *is_eep_supported);

/// <summary>
/// Gets the status of the frame rate control.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the frame rate control request.</param>
/// <param name="is_enabled">A value that returns the current frame rate control status. </param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_GET_IS_FRAME_RATE_CONTROL_ENABLED)(void *tl_camera_handle, int *is_enabled);

/// <summary>
/// Some scientific cameras include an LED indicator light on the back panel.\n\n
/// This function gets the LED status.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the LED request.</param>
/// <param name="is_led_on">A reference that receives the LED status.\n 0 (zero) for off and 1 (one) for on.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_GET_IS_LED_ON)(void *tl_camera_handle, int *is_led_on);

/// <summary>
/// Gets the LED is supported or not of the camera.
/// </summary>
typedef int (*TL_CAMERA_GET_IS_LED_SUPPORTED)(void *tl_camera_handle, int *is_led_supported);

/// <summary>
/// Due to variability in manufacturing, some pixels have inherently higher
/// dark current which manifests as abnormally bright pixels in images,
/// typically visible with longer exposures. Hot-pixel correction identifies
/// hot pixels and then substitutes a calculated value based on the values
/// of neighboring pixels in place of hot pixels.\n\n
/// This function may be used to get the current state of hot-pixel correction.\n\n
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the hot pixel correction request.</param>
/// <param name="is_hot_pixel_correction_enabled">
/// A reference that receives the state of the hot pixel correction functionality for the specified camera.\n
/// A 0 (zero) value indicates that hot pixel correction is disabled and a 1 (one) indicates that it is enabled.\n\n
/// </param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_IS_HOT_PIXEL_CORRECTION_ENABLED)(void *tl_camera_handle, int *is_hot_pixel_correction_enabled);

/// <summary>
/// Gets the NIRBoost is supported or not of the camera.
/// </summary>
typedef int (*TL_CAMERA_GET_IS_NIR_BOOST_SUPPORTED)(void *tl_camera_handle, int *is_nir_boost_supported);

/// <summary>
/// Gets the operation mode of the camera.
/// </summary>
typedef int (*TL_CAMERA_GET_IS_OPERATION_MODE_SUPPORTED)(void *tl_camera_handle, enum TL_CAMERA_OPERATION_MODE operation_mode, int *is_operation_mode_supported);

/// <summary>
/// Gets the tap is supported or not of the camera.
/// </summary>
typedef int (*TL_CAMERA_GET_IS_TAPS_SUPPORTED)(void *tl_camera_handle, int *is_taps_supported, enum TL_CAMERA_TAPS tap);

/// <summary>
/// Provides a character string that describes the most recent error that has occurred.\n\n
/// </summary>
/// <returns>
/// A character string indicating the most recent error that has occurred.
/// The application must NOT attempt modify or deallocate the character string.
/// Any attempt to do so is not permitted and could result in undefined behavior.
/// </returns>
typedef char *(*TL_CAMERA_GET_LAST_ERROR)(void);

/// <summary>
/// Gets the current rate of frames in frames per second that are delivered to the host computer.
/// The frame rate can be affected by the performance capabilities of the host computer and
/// the communication interface.\n\n
///     This method can be polled for updated values as needed.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the fps request.</param>
/// <param name="frames_per_second">A reference to receive the current fps value for the specified camera.  Note that this parameter is specified as a reference to a double precision floating point value.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_MEASURED_FRAME_RATE)(void *tl_camera_handle, double *frames_per_second);

/// <summary>
/// Gets the camera model information.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the model info request.</param>
/// <param name="model">A pointer to a character buffer to receive the model information.</param>
/// <param name="str_length">The length in bytes of the specified character buffer.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_MODEL)(void *tl_camera_handle, char *model, int str_length);

/// <summary>
/// Gets the range of valid character string buffer lengths that must be specified to receive the camera model string.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the model info request.</param>
/// <param name="model_min">A reference that receives the minimum length of the model character string.</param>
/// <param name="model_max">A reference that receives the maximum length of the model character string.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_MODEL_STRING_LENGTH_RANGE)(void *tl_camera_handle, int *model_min, int *model_max);

/// <summary>
/// Gets the camera name.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the name request.</param>
/// <param name="name">A pointer to a character string to receive the camera name.</param>
/// <param name="str_length">The length of the name character string.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_NAME)(void *tl_camera_handle, char *name, int str_length);

/// <summary>
/// Gets the range of valid character string buffer lengths that must be specified to receive or set the camera name string.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the name request.</param>
/// <param name="name_min">A reference that receives the minimum length of the name character string.</param>
/// <param name="name_max">A reference that receives the maximum length of the name character string.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_NAME_STRING_LENGTH_RANGE)(void *tl_camera_handle, int *name_min, int *name_max);

/// <summary>
/// Determine if near-infrared-boost mode is enabled.
/// Some camera models include support for boosting the intensity of wavelengths of light in the
/// near-infrared part of the spectrum.\n To determine if a camera supports NIR-boost mode, use
/// tl_camera_get_is_nir_boost_supported().
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the NIR boost get request.</param>
/// <param name="nir_boost_enable">A reference that receives the NIR boost enable status.\n 0 (zero) for off and 1 (one) for on.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_NIR_BOOST_ENABLE)(void *tl_camera_handle, int *nir_boost_enable);

/// <summary>
/// Gets the operation mode of the camera.
/// </summary>
typedef int (*TL_CAMERA_GET_OPERATION_MODE)(void *tl_camera_handle, enum TL_CAMERA_OPERATION_MODE *operation_mode);

// ReSharper disable once CppDoxygenUnresolvedReference
/// <summary>
/// <para>Returns the current camera frame or null.\n\n</para>
/// <para>IMPORTANT: The memory is allocated inside the camera SDK. Therefore, the provided pointer will be set to a position in the internal buffer. Either complete all tasks related to this image or make a copy of the data before returning from this function. Once this function exits, the pointer to the image buffer becomes invalid.</para>
/// <para>NOTE: There are two methods for getting image frames from the camera: Polling or registering for a callback.</para>
/// <para>1. Poll with the tl_camera_get_pending_frame_or_null function, typically from the main thread (polling from any thread is valid).</para>
/// <para>2. Register for a callback. In this case, frames will arrive on a worker thread to avoid interrupting the main thread. Be sure to use proper thread-locking techniques if the data needs to be marshaled from the worker thread to the main thread (such as for display in a graphical user interface).</para>
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the image request.</param>
/// <param name="image_buffer">The pointer to the buffer that contains the image data. The byte ordering of the data in this buffer is little-endian.  IMPORTANT: This pointer is only valid for the duration of this callback.</param>
/// <para>The data for both color and monochrome cameras are ordered left to right across a row followed by the
/// next row below it.</para>
/// <para>For monochrome and color cameras, each pixel requires two bytes.</para>
/// <para>For color cameras, it is necessary to demosaic the image in order to get
/// separate blue, red, and green channels for each pixel. A performant
/// demosaic algorithm is provided in tl_mono_to_color_create_mono_to_color_processor().
/// Once demosaicked, each pixel requires two bytes for blue followed by two bytes
/// for green followed by two bytes for red (BBGGRRBBGGRRBBGGRR...).
/// Therefore, each color pixel requires six bytes. See the example color
/// applications for details on converting a monochrome mosaicked
/// image to a color demosaicked image.</para>
/// <param name="frame_count">The image count corresponding to the received image during the current acquisition run.  If the image metadata section was not found, this will be 0.</param>
/// <param name="metadata">The pointer to the buffer that contains the image metadata.  The byte ordering of the data in this buffer is little-endian.  If the metadata section was not found, this will be null. IMPORTANT: This pointer is only valid for the duration of this callback.</param>
/// <param name="metadata_size_in_bytes">The size (in bytes) of the image metadata buffer. If the metadata section was not found, this will be 0.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
/// \anchor IMAGE_METADATA_DOCUMENTATION
/// The metadata section consists of tag ID/value pairs in the following format:\n\n
/// |------ Tag ID (4 ASCII characters [4 bytes]) -----|----- Tag data [4 bytes] -----|\n\n
/// These pairs occur consecutively in memory for all the tags supported by the camera.\n\n
/// To iterate over the tag/value pairs, start with the pointer to the metadata and increment by 8 bytes to go from one pair to the next. Either the size of the metadata buffer or the detection of the ENDT tag should be used to determine when to stop.\n\n
/// The following table lists the metadata tags along with a brief description:
///
/// <table>
/// <caption id="multi_row">Image Metadata Tag Description</caption>
/// <tr><th>Tag ID<th>Description
/// <tr><td>TSI\0<td>Start of metadata tag region - the data value of this tag is always 0
/// <tr><td>FCNT<td>Frame count
/// <tr><td>PCKH<td>Pixel clock count - upper 32 bits
/// <tr><td>PCKL<td>Pixel clock count - lower 32 bits
/// <tr><td>IFMT<td>Image data format
/// <tr><td>IOFF<td>Offset to pixel data in multiple of 8 bytes
/// <tr><td>ENDT<td>End of metadata tag region - the data value of this tag is always 0
/// </table>
///
/// NOTE: Not all tags are supported (are present in the metadata tag section) by all camera models. The IFMT (Image data format) tag is not present on the Zelux or Quantalux cameras.\n
/// ### How-To: Read Tags
/// The example below assumes `tl_camera_get_pending_frame_or_null()` will be called and `metadata` is not NULL. It shows one way of taking the metadata pointer and iterating over the tag / value pairs.\n
/// \snippet examples.c read tags
/// ### How-To: Calculate Relative Timestamp (nanoseconds)
/// Pixel clock count can be used to get a relative timestamp using the following formula: `relative_timestamp_ns = (pixel_clock_count / timestamp_clock_frequency) * 1000000000`\n
///  - `pixel_clock_count` can be found by combining the upper and lower pixel clock counts from the metadata: `(pixel_clock_count_upper << 32) | pixel_clock_count_lower`.\n
///  - `timestamp_clock_frequency` can be found using the following function: `tl_camera_get_timestamp_clock_frequency()`.\n
///  .
/// This timestamp is relative to an internal timer and is recorded immediately after exposure finishes. To get the time elapsed, subtract the relative timestamp of the first frame from the relative timestamp of the last frame. If `tl_camera_get_timestamp_clock_frequency()` returns an error code, then the camera does not support relative time stamping.\n\n
typedef int (*TL_CAMERA_GET_PENDING_FRAME_OR_NULL)(void *tl_camera_handle, unsigned short **image_buffer, int *frame_count, unsigned char **metadata, int *metadata_size_in_bytes);

/// <summary>
/// Gets the camera polar phase information.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the model info request.</param>
/// <param name="polar_phase">A pointer to a TL_POLARIZATION_PROCESSOR_POLAR_PHASE enumeration value.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_POLAR_PHASE)(void *tl_camera_handle, enum TL_POLARIZATION_PROCESSOR_POLAR_PHASE *polar_phase);

/// <summary>
/// Gets the current Region of Interest (ROI) values.\n\n
/// The ROI is specified by 2 sets of x,y coordinates that establish a bounded rectangular area:\n
/// - 1 for the upper left corner
/// - 1 for the lower right corner.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the ROI request.</param>
/// <param name="upper_left_x_pixels">A reference to receive the x coordinate of the upper left corner of the ROI.</param>
/// <param name="upper_left_y_pixels">A reference to receive the y coordinate of the upper left corner of the ROI.</param>
/// <param name="lower_right_x_pixels">A reference to receive the x coordinate of the lower right corner of the ROI.</param>
/// <param name="lower_right_y_pixels">A reference to receive the y coordinate of the lower right corner of the ROI.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_GET_ROI)(void *tl_camera_handle, int *upper_left_x_pixels, int *upper_left_y_pixels, int *lower_right_x_pixels, int *lower_right_y_pixels);

/// <summary>
/// Gets the range of acceptable values for Region of Interest (ROI) coordinates.\n\n
/// The ROI is specified by 2 sets of x,y coordinates that establish a bounded rectangular area:\n
/// - 1 for the upper left corner
/// - 1 for the lower right corner.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the ROI range request.</param>
/// <param name="upper_left_x_pixels_min">A reference to receive the the minimum x coordinate of the upper left corner of the ROI.</param>
/// <param name="upper_left_y_pixels_min">A reference to receive the the minimum y coordinate of the upper left corner of the ROI.</param>
/// <param name="lower_right_x_pixels_min">A reference to receive the the minimum x coordinate of the lower right corner of the ROI.</param>
/// <param name="lower_right_y_pixels_min">A reference to receive the the minimum y coordinate of the lower right corner of the ROI.</param>
/// <param name="upper_left_x_pixels_max">A reference to receive the the maximum x coordinate of the upper left corner of the ROI.</param>
/// <param name="upper_left_y_pixels_max">A reference to receive the the maximum y coordinate of the upper left corner of the ROI.</param>
/// <param name="lower_right_x_pixels_max">A reference to receive the the maximum x coordinate of the lower right corner of the ROI.</param>
/// <param name="lower_right_y_pixels_max">A reference to receive the the maximum y coordinate of the lower right corner of the ROI.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_GET_ROI_RANGE)(void *tl_camera_handle, int *upper_left_x_pixels_min, int *upper_left_y_pixels_min, int *lower_right_x_pixels_min, int *lower_right_y_pixels_min, int *upper_left_x_pixels_max, int *upper_left_y_pixels_max, int *lower_right_x_pixels_max, int *lower_right_y_pixels_max);

/// <summary>
/// Gets the sensor height in pixels.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the sensor height request.</param>
/// <param name="height_pixels">A reference that receives the value in pixels for the sensor height.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_SENSOR_HEIGHT)(void *tl_camera_handle, int *height_pixels);

/// <summary>
/// Get the physical height, in micrometers, of a single light-sensitive photo site on the sensor.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the pixel height request.</param>
/// <param name="pixel_height_um">A reference to receive the current pixel height value in micrometers.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_GET_SENSOR_PIXEL_HEIGHT)(void *tl_camera_handle, double *pixel_height_um);

/// <summary>
/// Get the current pixel size in bytes.  This represents the amount of space 1 pixel will occupy in the frame buffer.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the pixel size request.</param>
/// <param name="sensor_pixel_size_bytes">A reference to receive the current pixel size value in bytes.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_GET_SENSOR_PIXEL_SIZE_BYTES)(void *tl_camera_handle, int *sensor_pixel_size_bytes);

/// <summary>
/// Get the physical width, in micrometers, of a single light-sensitive photo site on the sensor.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the pixel width request.</param>
/// <param name="pixel_width_um">A reference to receive the current pixel width value in micrometers.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_GET_SENSOR_PIXEL_WIDTH)(void *tl_camera_handle, double *pixel_width_um);

/// <summary>
/// Gets the send readout time for the specified camera.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the sensor readout time request.</param>
/// <param name="sensor_readout_time_ns">A reference to receive the current send readout time value in nanoseconds.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_SENSOR_READOUT_TIME)(void *tl_camera_handle, int *sensor_readout_time_ns);

/// <summary>
/// Gets the sensor width in pixels.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the sensor width request.</param>
/// <param name="width_pixels">A reference that receives the value in pixels for the sensor width.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_SENSOR_WIDTH)(void *tl_camera_handle, int *width_pixels);

/// <summary>
/// Gets the camera serial number.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the serial number request.</param>
/// <param name="serial_number">A pointer to a character string to receive the camera serial number.</param>
/// <param name="str_length">The length of the serial number character string.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_GET_SERIAL_NUMBER)(void *tl_camera_handle, char *serial_number, int str_length);

/// <summary>
/// Gets the range of valid character string buffer lengths that must be specified to receive the camera serial number string.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the serial number range request.</param>
/// <param name="serial_number_min">A reference that receives the minimum length of the serial number character string.</param>
/// <param name="serial_number_max">A reference that receives the maximum length of the serial number character string.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_GET_SERIAL_NUMBER_STRING_LENGTH_RANGE)(void *tl_camera_handle, int *serial_number_min, int *serial_number_max);

/// <summary>
/// Gets the value of the current camera tap balance setting.
/// The higher frame rates enabled by multi-tap operation are not without tradeoffs.
/// Since each tap has a different analog to digital converter with a different gain,
/// this difference can manifest in the image by each half (or quadrant) having slightly different
/// intensities. The tap balance feature mitigates this effect across a wide range of exposure, gain,
/// and black level values.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the taps request.</param>
/// <param name="taps_balance_enable">A reference that receives the tap balance enable status.\n 0 (zero) for off and 1 (one) for on.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_TAP_BALANCE_ENABLE)(void *tl_camera_handle, int *taps_balance_enable);

/// <summary>
/// Gets the current camera taps value.
/// Scientific CCD cameras support one or more taps.\n\n
/// After exposure is complete, a CCD pixel array holds the charge corresponding to the amount of light collected at
/// each pixel location. The data is then read out through 1, 2, or 4 channels at a time.
/// Reading the data through more than 1 channel (for cameras that support multi-tap operation) can
/// enable higher maximum frame rates.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the taps request.</param>
/// <param name="taps">A pointer to a TL_CAMERA_TAPS enumeration value.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_TAPS)(void *tl_camera_handle, enum TL_CAMERA_TAPS *taps);

/// <summary>
/// Gets the timestamp clock frequency for the camera in Hz. This can be used along with the
/// clock count value in each frame's metadata to calculate the relative time from plug for that frame.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the timestamp clock frequency request.</param>
/// <param name="timestamp_clock_frequency_hz_or_zero">A reference to receive the current time stamp clock frequency value in Hz or zero if unsupported.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_GET_TIMESTAMP_CLOCK_FREQUENCY)(void *tl_camera_handle, int *timestamp_clock_frequency_hz_or_zero);

/// <summary>
/// Gets the current hardware trigger polarity of the specified camera.\n\n
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the hardware trigger mode request.</param>
/// <param name="trigger_polarity_enum">A reference to a TRIGGER_POLARITY to receive the currently configured trigger polarity.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_TRIGGER_POLARITY)(void *tl_camera_handle, enum TL_CAMERA_TRIGGER_POLARITY *trigger_polarity_enum);

/// <summary>
/// Gets the USB port type that the camera is connected to.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the USB port type request.</param>
/// <param name="usb_port_type">A reference that receives the USB port type.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_GET_USB_PORT_TYPE)(void *tl_camera_handle, enum TL_CAMERA_USB_PORT_TYPE *usb_port_type);

/// <summary>
///     Read on-camera, non-volatile memory that is available to the user.\n\n
///     Use tl_camera_get_user_memory_maximum_size to query the available memory.
///     <param name="tl_camera_handle">The camera handle associated with the USB port type request.</param>
///     <param name="destination_data_buffer">A byte buffer in which to receive the specified number of bytes.</param>
///     <param name="number_of_bytes_to_read">The number of bytes of user memory to read.</param>
///     <param name="camera_user_memory_offset_bytes">A byte offset in the on-camera, non-volatile memory from which to start reading.\n\n
///         Use a value of zero to read from the beginning of user memory.
///     </param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
/// <seealso cref="TL_CAMERA_GET_USER_MEMORY_MAXIMUM_SIZE" />
/// <seealso cref="TL_CAMERA_SET_USER_MEMORY" />
/// </summary>
typedef int (*TL_CAMERA_GET_USER_MEMORY)(void *tl_camera_handle, unsigned char *destination_data_buffer, long long number_of_bytes_to_read, long long camera_user_memory_offset_bytes);

/// <summary>
///     Gets the number of bytes of on-camera, non-volatile memory storage available to the user.
///     <param name="tl_camera_handle">The camera handle associated with the USB port type request.</param>
///     <param name="maximum_size_bytes">A reference that receives the 64-bit number of available bytes.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
/// </summary>
typedef int (*TL_CAMERA_GET_USER_MEMORY_MAXIMUM_SIZE)(void *tl_camera_handle, long long *maximum_size_bytes);

/// This function will generate a trigger through the camera SDK
/// rather than through the hardware trigger input.\n\n
/// The behavior of a software trigger
/// depends on the number of frames configured using tl_camera_set_number_of_frames_per_trigger.\n
/// - If the number of frames per trigger is set to zero, then a single
///   software trigger will start continuous-video mode.\n\n
/// - If the number of frames per trigger is set to one or higher, then
///   one software trigger will generate the requested number of frames. In this
///   case, it is important to avoid issuing subsequent software triggers until
///   the time specified by tl_camera_get_frame_time multiplied by the number of frames has elapsed.
///   If insufficient time elapses, the trigger is ignored by the camera.\n
///   NOTE: Some versions of camera firmware exhibit a longer frame time than is ideal.
///   Please check the website for the latest available firmware.\n\n
/// Multiple software triggers can be issued before calling Disarm().\n\n
/// See also tl_camera_get_frame_time, tl_camera_get_exposure_time, and tl_camera_get_sensor_readout_time.
/// <param name="tl_camera_handle">The camera handle for issuing a software trigger.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_ISSUE_SOFTWARE_TRIGGER)(void *tl_camera_handle);

/// <summary>
/// Gets a handle to a camera with the specified serial number.\n\n
/// The handle represents the software abstraction of the physical camera.\n\n
/// The returned handle must be used with most API functions
/// to perform the camera specific task corresponding to the particular function.
/// </summary>
/// <param name="camera_serial_number">The camera serial number.</param>
/// <param name="tl_camera_handle">A reference to receive the handle to the camera with the specified serial number.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_OPEN_CAMERA)(char *camera_serial_number, void **tl_camera_handle);

/// <summary>
/// The tl_camera_open_sdk function is used to initialize the SDK.  This function must be called prior to calling any other API function.\n\n
/// </summary>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_OPEN_SDK)(void);

/// <summary>
///     Binning sums adjacent sensor pixels into "super pixels". It trades
///     off spatial resolution for sensitivity and speed. For example, if a
///     sensor is 1920 by 1080 pixels and binning is set to two in the X
///     direction and two in the Y direction, the resulting image will be 960
///     by 540 pixels. Since smaller images require less data to be
///     transmitted to the host computer, binning may increase the frame
///     rate. By default, binning is set to one in both horizontal and vertical
///     directions.\n\n
///     Sets the current horizontal binning value for the specified camera.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the horizontal binning command.</param>
/// <param name="binx">A value that is used to configure the horizontal binning setting.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_SET_BINX)(void *tl_camera_handle, int binx);

/// <summary>
///     Binning sums adjacent sensor pixels into "super pixels". It trades
///     off spatial resolution for sensitivity and speed. For example, if a
///     sensor is 1920 by 1080 pixels and binning is set to two in the X
///     direction and two in the Y direction, the resulting image will be 960
///     by 540 pixels. Since smaller images require less data to be
///     transmitted to the host computer, binning may increase the frame
///     rate. By default, binning is set to one in both horizontal and vertical
///     directions.\n\n
///     Sets the current vertical binning value for the specified camera.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the vertical binning command.</param>
/// <param name="biny">A value that is used to configure the vertical binning setting.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_SET_BINY)(void *tl_camera_handle, int biny);

/// <summary>
/// Sets the black level value for the specified camera.
/// To determine if a camera model supports range, see tl_camera_get_black_level_range().
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the black level command.</param>
/// <param name="black_level">A value that is used to configure the black level setting.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_SET_BLACK_LEVEL)(void *tl_camera_handle, int black_level);

/// <summary>
/// Sets the TL_CAMERA_CONNECT_CALLBACK callback function.\n\n
/// </summary>
/// <param name="handler">A pointer to the callback function.\n This function must conform to the TL_CAMERA_CONNECT_CALLBACK prototype.</param>
/// <param name="context">A pointer to a user specified context.  This parameter is ignored by the SDK.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_SET_CAMERA_CONNECT_CALLBACK)(TL_CAMERA_CONNECT_CALLBACK handler, void *context);

/// <summary>
/// Sets the TL_CAMERA_DISCONNECT_CALLBACK callback function.\n\n
/// </summary>
/// <param name="handler">A pointer to the callback function.\n This function must conform to the TL_CAMERA_DISCONNECT_CALLBACK prototype.</param>
/// <param name="context">A pointer to a user specified context.  This parameter is ignored by the SDK.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_SET_CAMERA_DISCONNECT_CALLBACK)(TL_CAMERA_DISCONNECT_CALLBACK handler, void *context);

/// <summary>
/// Sets the current value of the camera sensor-level data readout rate.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the data rate request.</param>
/// <param name="data_rate">The data rate value to set.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_SET_DATA_RATE)(void *tl_camera_handle, enum TL_CAMERA_DATA_RATE data_rate);

/// <summary>
/// Sets the specified camera's exposure to a value which must be specified in microseconds.\n\n
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the exposure change.</param>
/// <param name="exposure_time_us">A whole number of microseconds which represents the new exposure value.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_SET_EXPOSURE_TIME)(void *tl_camera_handle, long long exposure_time_us);

/// <summary>
/// <para>Sets the TL_CAMERA_FRAME_AVAILABLE_CALLBACK callback function.</para>
/// <para>NOTE: There are two methods for getting image frames from the camera: Polling or registering for a callback.</para>
/// <para>1. Poll with the tl_camera_get_pending_frame_or_null function, typically from the main thread (polling from any thread is valid).</para>
/// <para>2. Register for a callback. In this case, frames will arrive on a worker thread to avoid interrupting the main thread. Be sure to use proper thread-locking techniques if the data needs to be marshaled from the worker thread to the main thread (such as for display in a graphical user interface).</para>
/// <para>For details, please see the documentation for TL_CAMERA_FRAME_AVAILABLE_CALLBACK.</para>
/// </summary>
/// <param name="tl_camera_handle">The camera handle to associate with the callback.</param>
/// <param name="handler">A pointer to the callback function.\n This function must conform to the TL_CAMERA_FRAME_AVAILABLE_CALLBACK prototype.</param>
/// <param name="context">A pointer to a user specified context.  This parameter is ignored by the SDK.</param>
typedef int (*TL_CAMERA_SET_FRAME_AVAILABLE_CALLBACK)(void *tl_camera_handle, TL_CAMERA_FRAME_AVAILABLE_CALLBACK handler, void *context);

/// <summary>
/// Sets the frame rate value in frames per second for the specified camera.
/// To determine if frame-rate control is supported by a camera model, see tl_camera_get_frame_rate_control_value_range().
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the frame rate control request.</param>
/// <param name="frame_rate_fps">A value that is used to configure the frame rate setting in frames per second. </param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_SET_FRAME_RATE_CONTROL_VALUE)(void *tl_camera_handle, double frame_rate_fps);

/// <summary>
/// Sets the number of frames per trigger.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the frames per trigger request.</param>
/// <param name="number_of_frames_per_trigger_or_zero_for_unlimited">The number of frames per trigger value to set.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_SET_FRAMES_PER_TRIGGER_ZERO_FOR_UNLIMITED)(void *tl_camera_handle, unsigned int number_of_frames_per_trigger_or_zero_for_unlimited);

/// <summary>
///     Sets the current gain value for the specified camera. To determine if a camera supports gain, see tl_camera_get_gain_range().
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the gain command.</param>
/// <param name="gain">A value that is used to configure the gain setting.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_SET_GAIN)(void *tl_camera_handle, int gain);

/// <summary>
/// This function may be used to set the current threshold value for hot-pixel correction.\n\n
/// This value is a quantitative measure of how aggressively the camera will remove hot pixels.\n\n
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the hot pixel correction threshold command.</param>
/// <param name="hot_pixel_correction_threshold">A reference that specifies the current value of the hot pixel correction threshold for the specified camera.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_SET_HOT_PIXEL_CORRECTION_THRESHOLD)(void *tl_camera_handle, int hot_pixel_correction_threshold);

/// <summary>
/// Sets the current camera image poll time out value in milliseconds.\n\n
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the exposure request.</param>
/// <param name="timeout_ms">The time out value to be set.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_SET_IMAGE_POLL_TIMEOUT)(void *tl_camera_handle, int timeout_ms);

/// <summary>
/// Enables or disables the EEP operating mode.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the EEP request.</param>
/// <param name="is_eep_enabled">A value that enables or disables EEP.  0 (zero) to disable EEP and 1 (one) to enable EEP.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_SET_IS_EEP_ENABLED)(void *tl_camera_handle, int is_eep_enabled);

/// <summary>
/// Enables or disables frame rate control.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the frame rate control request.</param>
/// <param name="is_enabled">A value that enables or disables frame rate control.  0 (zero) to disable frame rate control and 1 (one) to enable frame rate control. </param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_SET_IS_FRAME_RATE_CONTROL_ENABLED)(void *tl_camera_handle, int is_enabled);

/// <summary>
/// This function may be used to set the current state of hot-pixel correction.\n\n
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the hot pixel correction command.</param>
/// <param name="is_hot_pixel_correction_enabled">
/// A value that specifies the state of the hot pixel correction functionality for the specified camera.
/// A 0 (zero) value disables hot pixel correction and a 1 (one) enables hot pixel correction.\n\n
/// </param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_SET_IS_HOT_PIXEL_CORRECTION_ENABLED)(void *tl_camera_handle, int is_hot_pixel_correction_enabled);

/// <summary>
/// Some scientific cameras include an LED indicator light on the back panel.\n\n
/// This function sets the LED.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the LED request.</param>
/// <param name="is_led_on">A value that controls the LED.\n 0 (zero) for off and 1 (one) for on.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_SET_IS_LED_ON)(void *tl_camera_handle, int is_led_on);

/// <summary>
/// Sets the camera name.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the name request.</param>
/// <param name="name">A pointer to a character string containing the new camera name.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_SET_NAME)(void *tl_camera_handle, char *name);

/// <summary>
/// Enable or disable near-infrared-boost mode.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the cooling mode set request.</param>
/// <param name="nir_boost_enable">A value that enables/disables NIR boost mode.\n 0 (zero) for off and 1 (one) for on.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_SET_NIR_BOOST_ENABLE)(void *tl_camera_handle, int nir_boost_enable);

/// <summary>
/// Gets the operation mode of the camera.
/// </summary>
typedef int (*TL_CAMERA_SET_OPERATION_MODE)(void *tl_camera_handle, enum TL_CAMERA_OPERATION_MODE operation_mode);

/// <summary>
/// Sets the current Region of Interest (ROI) values.\n\n
/// The ROI is specified by 2 sets of x,y coordinates that establish a bounded rectangular area:\n
/// - 1 for the upper left corner
/// - 1 for the lower right corner.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the ROI request.</param>
/// <param name="upper_left_x_pixels">The x coordinate of the upper left corner of the ROI.</param>
/// <param name="upper_left_y_pixels">The y coordinate of the upper left corner of the ROI.</param>
/// <param name="lower_right_x_pixels">The x coordinate of the lower right corner of the ROI.</param>
/// <param name="lower_right_y_pixels">The y coordinate of the lower right corner of the ROI.</param>
/// <returns>
/// 0 if successful or a positive integer error code to indicate failure. In case of error, call
/// tl_camera_get_last_error to get details. This error string is valid until another API called on the same thread.
/// </returns>
typedef int (*TL_CAMERA_SET_ROI)(void *tl_camera_handle, int upper_left_x_pixels, int upper_left_y_pixels, int lower_right_x_pixels, int lower_right_y_pixels);

/// <summary>
/// Sets the camera tap balance value.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the taps request.</param>
/// <param name="taps_balance_enable">A value that enables/disables the tap balance feature.\n 0 (zero) for off and 1 (one) for on.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_SET_TAP_BALANCE_ENABLE)(void *tl_camera_handle, int taps_balance_enable);

/// <summary>
/// Sets the camera taps value.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the taps request.</param>
/// <param name="taps">A TL_CAMERA_TAPS enumeration value.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_SET_TAPS)(void *tl_camera_handle, enum TL_CAMERA_TAPS taps);

/// <summary>
/// Sets the current hardware trigger polarity for the specified camera.
/// </summary>
/// <param name="tl_camera_handle">The camera handle associated with the hardware trigger mode request.</param>
/// <param name="trigger_polarity_enum">A TRIGGER_POLARITY value that is used to configure the trigger polarity.</param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
typedef int (*TL_CAMERA_SET_TRIGGER_POLARITY)(void *tl_camera_handle, enum TL_CAMERA_TRIGGER_POLARITY trigger_polarity_enum);

/// <summary>
///     Write to the on-camera, non-volatile memory that is available to the user.\n\n
///     Use tl_camera_get_user_memory_maximum_size to query the available memory.\n\n
///     Non-volatile memory can handle many writes, but the total number of writes is finite. Avoid unnecessary writes.
///     <param name="tl_camera_handle">The camera handle associated with the USB port type request.</param>
///     <param name="source_data_buffer">A byte buffer from which to write up to the specified number of bytes.</param>
///     <param name="number_of_bytes_to_write">The number of bytes of the given data buffer to write at the given offset into on-camera, non-volatile, user-store memory.</param>
///     <param name="camera_user_memory_offset_bytes">A byte offset in the on-camera, non-volatile memory from which to start reading.\n\n
///         Use a value of zero to read from the beginning of user memory.
///     </param>
/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
/// <seealso cref="TL_CAMERA_GET_USER_MEMORY_MAXIMUM_SIZE" />
/// <seealso cref="TL_CAMERA_GET_USER_MEMORY" />
/// </summary>
typedef int (*TL_CAMERA_SET_USER_MEMORY)(void *tl_camera_handle, unsigned char *source_data_buffer, long long number_of_bytes_to_write, long long camera_user_memory_offset_bytes);

#ifndef thorlabs_tsi_camera_sdk_EXPORTS

#ifdef __cplusplus
extern "C"
{
#endif

    /// @cond HIDDEN_VARIABLES
    extern _INTERNAL_COMMAND _internal_command;
    extern TL_CAMERA_ARM tl_camera_arm;
    extern TL_CAMERA_CLOSE_CAMERA tl_camera_close_camera;
    extern TL_CAMERA_CLOSE_SDK tl_camera_close_sdk;
    extern TL_CAMERA_DISARM tl_camera_disarm;
    extern TL_CAMERA_CONVERT_GAIN_TO_DECIBELS tl_camera_convert_gain_to_decibels;
    extern TL_CAMERA_CONVERT_DECIBELS_TO_GAIN tl_camera_convert_decibels_to_gain;
    extern TL_CAMERA_DISCOVER_AVAILABLE_CAMERAS tl_camera_discover_available_cameras;
    extern TL_CAMERA_GET_BINX tl_camera_get_binx;
    extern TL_CAMERA_GET_BINX_RANGE tl_camera_get_binx_range;
    extern TL_CAMERA_GET_BINY tl_camera_get_biny;
    extern TL_CAMERA_GET_BINY_RANGE tl_camera_get_biny_range;
    extern TL_CAMERA_GET_BIT_DEPTH tl_camera_get_bit_depth;
    extern TL_CAMERA_GET_BLACK_LEVEL tl_camera_get_black_level;
    extern TL_CAMERA_GET_BLACK_LEVEL_RANGE tl_camera_get_black_level_range;
    extern TL_CAMERA_GET_CAMERA_COLOR_CORRECTION_MATRIX_OUTPUT_COLOR_SPACE tl_camera_get_camera_color_correction_matrix_output_color_space;
    extern TL_CAMERA_GET_CAMERA_SENSOR_TYPE tl_camera_get_camera_sensor_type;
    extern TL_CAMERA_GET_COLOR_CORRECTION_MATRIX tl_camera_get_color_correction_matrix;
    extern TL_CAMERA_GET_COLOR_FILTER_ARRAY_PHASE tl_camera_get_color_filter_array_phase;
    extern TL_CAMERA_GET_COMMUNICATION_INTERFACE tl_camera_get_communication_interface;
    extern TL_CAMERA_GET_DATA_RATE tl_camera_get_data_rate;
    extern TL_CAMERA_GET_DEFAULT_WHITE_BALANCE_MATRIX tl_camera_get_default_white_balance_matrix;
    extern TL_CAMERA_GET_EEP_STATUS tl_camera_get_eep_status;
    extern TL_CAMERA_GET_EXPOSURE_TIME tl_camera_get_exposure_time;
    extern TL_CAMERA_GET_EXPOSURE_TIME_RANGE tl_camera_get_exposure_time_range;
    extern TL_CAMERA_GET_FIRMWARE_VERSION tl_camera_get_firmware_version;
    extern TL_CAMERA_GET_FRAME_AVAILABLE_CALLBACK tl_camera_get_frame_available_callback;
    extern TL_CAMERA_GET_FRAME_RATE_CONTROL_VALUE tl_camera_get_frame_rate_control_value;
    extern TL_CAMERA_GET_FRAME_RATE_CONTROL_VALUE_RANGE tl_camera_get_frame_rate_control_value_range;
    extern TL_CAMERA_GET_FRAME_TIME tl_camera_get_frame_time;
    extern TL_CAMERA_GET_FRAMES_PER_TRIGGER_RANGE tl_camera_get_frames_per_trigger_range;
    extern TL_CAMERA_GET_FRAMES_PER_TRIGGER_ZERO_FOR_UNLIMITED tl_camera_get_frames_per_trigger_zero_for_unlimited;
    extern TL_CAMERA_GET_GAIN tl_camera_get_gain;
    extern TL_CAMERA_GET_GAIN_RANGE tl_camera_get_gain_range;
    extern TL_CAMERA_GET_HOT_PIXEL_CORRECTION_THRESHOLD tl_camera_get_hot_pixel_correction_threshold;
    extern TL_CAMERA_GET_HOT_PIXEL_CORRECTION_THRESHOLD_RANGE tl_camera_get_hot_pixel_correction_threshold_range;
    extern TL_CAMERA_GET_IMAGE_HEIGHT tl_camera_get_image_height;
    extern TL_CAMERA_GET_IMAGE_HEIGHT_RANGE tl_camera_get_image_height_range;
    extern TL_CAMERA_GET_IMAGE_POLL_TIMEOUT tl_camera_get_image_poll_timeout;
    extern TL_CAMERA_GET_IMAGE_WIDTH tl_camera_get_image_width;
    extern TL_CAMERA_GET_IMAGE_WIDTH_RANGE tl_camera_get_image_width_range;
    extern TL_CAMERA_GET_IS_ARMED tl_camera_get_is_armed;
    extern TL_CAMERA_GET_IS_COOLING_SUPPORTED tl_camera_get_is_cooling_supported;
    extern TL_CAMERA_GET_IS_DATA_RATE_SUPPORTED tl_camera_get_is_data_rate_supported;
    extern TL_CAMERA_GET_IS_EEP_SUPPORTED tl_camera_get_is_eep_supported;
    extern TL_CAMERA_GET_IS_FRAME_RATE_CONTROL_ENABLED tl_camera_get_is_frame_rate_control_enabled;
    extern TL_CAMERA_GET_IS_HOT_PIXEL_CORRECTION_ENABLED tl_camera_get_is_hot_pixel_correction_enabled;
    extern TL_CAMERA_GET_IS_LED_ON tl_camera_get_is_led_on;
    extern TL_CAMERA_GET_IS_LED_SUPPORTED tl_camera_get_is_led_supported;
    extern TL_CAMERA_GET_IS_NIR_BOOST_SUPPORTED tl_camera_get_is_nir_boost_supported;
    extern TL_CAMERA_GET_IS_OPERATION_MODE_SUPPORTED tl_camera_get_is_operation_mode_supported;
    extern TL_CAMERA_GET_IS_TAPS_SUPPORTED tl_camera_get_is_taps_supported;
    extern TL_CAMERA_GET_LAST_ERROR tl_camera_get_last_error;
    extern TL_CAMERA_GET_MEASURED_FRAME_RATE tl_camera_get_measured_frame_rate;
    extern TL_CAMERA_GET_MODEL tl_camera_get_model;
    extern TL_CAMERA_GET_MODEL_STRING_LENGTH_RANGE tl_camera_get_model_string_length_range;
    extern TL_CAMERA_GET_NAME tl_camera_get_name;
    extern TL_CAMERA_GET_NAME_STRING_LENGTH_RANGE tl_camera_get_name_string_length_range;
    extern TL_CAMERA_GET_NIR_BOOST_ENABLE tl_camera_get_nir_boost_enable;
    extern TL_CAMERA_GET_OPERATION_MODE tl_camera_get_operation_mode;
    extern TL_CAMERA_GET_PENDING_FRAME_OR_NULL tl_camera_get_pending_frame_or_null;
    extern TL_CAMERA_GET_POLAR_PHASE tl_camera_get_polar_phase;
    extern TL_CAMERA_GET_ROI tl_camera_get_roi;
    extern TL_CAMERA_GET_ROI_RANGE tl_camera_get_roi_range;
    extern TL_CAMERA_GET_SENSOR_HEIGHT tl_camera_get_sensor_height;
    extern TL_CAMERA_GET_SENSOR_PIXEL_HEIGHT tl_camera_get_sensor_pixel_height;
    extern TL_CAMERA_GET_SENSOR_PIXEL_SIZE_BYTES tl_camera_get_sensor_pixel_size_bytes;
    extern TL_CAMERA_GET_SENSOR_PIXEL_WIDTH tl_camera_get_sensor_pixel_width;
    extern TL_CAMERA_GET_SENSOR_READOUT_TIME tl_camera_get_sensor_readout_time;
    extern TL_CAMERA_GET_SENSOR_WIDTH tl_camera_get_sensor_width;
    extern TL_CAMERA_GET_SERIAL_NUMBER tl_camera_get_serial_number;
    extern TL_CAMERA_GET_SERIAL_NUMBER_STRING_LENGTH_RANGE tl_camera_get_serial_number_string_length_range;
    extern TL_CAMERA_GET_TAP_BALANCE_ENABLE tl_camera_get_tap_balance_enable;
    extern TL_CAMERA_GET_TAPS tl_camera_get_taps;
    extern TL_CAMERA_GET_TIMESTAMP_CLOCK_FREQUENCY tl_camera_get_timestamp_clock_frequency;
    extern TL_CAMERA_GET_TRIGGER_POLARITY tl_camera_get_trigger_polarity;
    extern TL_CAMERA_GET_USB_PORT_TYPE tl_camera_get_usb_port_type;
    extern TL_CAMERA_GET_USER_MEMORY tl_camera_get_user_memory;
    extern TL_CAMERA_GET_USER_MEMORY_MAXIMUM_SIZE tl_camera_get_user_memory_maximum_size;
    extern TL_CAMERA_ISSUE_SOFTWARE_TRIGGER tl_camera_issue_software_trigger;
    extern TL_CAMERA_OPEN_CAMERA tl_camera_open_camera;
    extern TL_CAMERA_OPEN_SDK tl_camera_open_sdk;
    extern TL_CAMERA_SET_BINX tl_camera_set_binx;
    extern TL_CAMERA_SET_BINY tl_camera_set_biny;
    extern TL_CAMERA_SET_BLACK_LEVEL tl_camera_set_black_level;
    extern TL_CAMERA_SET_CAMERA_CONNECT_CALLBACK tl_camera_set_camera_connect_callback;
    extern TL_CAMERA_SET_CAMERA_DISCONNECT_CALLBACK tl_camera_set_camera_disconnect_callback;
    extern TL_CAMERA_GET_IS_COOLING_ENABLED tl_camera_get_is_cooling_enabled;
    extern TL_CAMERA_SET_DATA_RATE tl_camera_set_data_rate;
    extern TL_CAMERA_SET_EXPOSURE_TIME tl_camera_set_exposure_time;
    extern TL_CAMERA_SET_FRAME_AVAILABLE_CALLBACK tl_camera_set_frame_available_callback;
    extern TL_CAMERA_SET_FRAME_RATE_CONTROL_VALUE tl_camera_set_frame_rate_control_value;
    extern TL_CAMERA_SET_FRAMES_PER_TRIGGER_ZERO_FOR_UNLIMITED tl_camera_set_frames_per_trigger_zero_for_unlimited;
    extern TL_CAMERA_SET_GAIN tl_camera_set_gain;
    extern TL_CAMERA_SET_HOT_PIXEL_CORRECTION_THRESHOLD tl_camera_set_hot_pixel_correction_threshold;
    extern TL_CAMERA_SET_IS_EEP_ENABLED tl_camera_set_is_eep_enabled;
    extern TL_CAMERA_SET_IS_FRAME_RATE_CONTROL_ENABLED tl_camera_set_is_frame_rate_control_enabled;
    extern TL_CAMERA_SET_IS_HOT_PIXEL_CORRECTION_ENABLED tl_camera_set_is_hot_pixel_correction_enabled;
    extern TL_CAMERA_SET_IS_LED_ON tl_camera_set_is_led_on;
    extern TL_CAMERA_SET_IMAGE_POLL_TIMEOUT tl_camera_set_image_poll_timeout;
    extern TL_CAMERA_SET_NAME tl_camera_set_name;
    extern TL_CAMERA_SET_NIR_BOOST_ENABLE tl_camera_set_nir_boost_enable;
    extern TL_CAMERA_SET_OPERATION_MODE tl_camera_set_operation_mode;
    extern TL_CAMERA_SET_ROI tl_camera_set_roi;
    extern TL_CAMERA_SET_TAP_BALANCE_ENABLE tl_camera_set_tap_balance_enable;
    extern TL_CAMERA_SET_TAPS tl_camera_set_taps;
    extern TL_CAMERA_SET_TRIGGER_POLARITY tl_camera_set_trigger_polarity;
    extern TL_CAMERA_SET_USER_MEMORY tl_camera_set_user_memory;
    /// @endcond

#ifdef __cplusplus
}
#endif

#endif
