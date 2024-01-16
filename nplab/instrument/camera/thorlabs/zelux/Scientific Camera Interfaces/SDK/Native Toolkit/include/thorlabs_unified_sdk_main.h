/*
* Copyright 2017 by Thorlabs, Inc.  All rights reserved.  Unauthorized use (including,
* without limitation, distribution and copying) is strictly prohibited.  All use requires, and is
* subject to, explicit written authorization and nondisclosure agreements with Thorlabs, Inc.
*/

/*! \mainpage Thorlabs Scientific Unified SDK
*
* \section Introduction
*
* The target audience for this document is the any software engineer who wants
* to interface to TSI cameras at the lowest possible software level.
*
*/

/*! \file thorlabs_unified_sdk_main.h
*   \brief This file includes the declaration prototypes of all the API functions
*          contained in the unified SDK.
*/

#pragma once

///*! This function obtains the unified SDK version.
//*
//*   \returns A character string value indicating the unified SDK version.
//*/
//typedef char * (*TL_MODULE_GET_VERSION)(); /* tl_module_get_version */

/*! This function opens the unified SDK and initializes its internal state.
*   This function must be called prior to calling any other API function (except tl_module_get_version).
*
*   \returns A ::tl_error_codes value to indicate success or failure (::TL_NO_ERROR indicates success).
*/
typedef int (*TL_OPEN_SDK)(); /* tl_open_sdk */

/*! This function close the unified SDK and cleans up any internal state.  After this function has been called,
*   it is an error to subsequently call any other API function.
*   Any attempt to do so could result in undefined and unpredictable behavior.
*
*   \returns A ::tl_error_codes value to indicate success or failure (::TL_NO_ERROR indicates success).
*/
typedef int (*TL_CLOSE_SDK)(); /* tl_close_sdk */

/*! This function discovers SDK supported devices and returns a string containing unique identifiers to each
*   device that was found.
*
*   \param[out] The character string that receives the IDs of the discovered devices.
*   \param[in] The size of the character string.
*
*   \returns A ::tl_error_codes value to indicate success or failure (::TL_NO_ERROR indicates success).
*/
typedef int (*TL_GET_DEVICE_IDS)(char *, int); /* tl_get_device_ids */

/*! This function opens the device specified by the combination of the device module ID and device ID.
*
*   \param[in] The character string that specifies the module ID of the device to open.
*   \param[in] The character string that specifies the unique ID of the device to open.
*   \param[out] The returned handle of the device after it has been successfully open.
*
*   \returns A ::tl_error_codes value to indicate success or failure (::TL_NO_ERROR indicates success).
*/
typedef int (*TL_OPEN_DEVICE)(char *, char *, void **); /* tl_open_device */

/*! This function closes the device corresponding to the specified device ID.
*
*   \param[in] The character string that specifies the unique ID of the device to close.
*
*   \returns A ::tl_error_codes value to indicate success or failure (::TL_NO_ERROR indicates success).
*/
typedef int (*TL_CLOSE_DEVICE)(void *); /* tl_close_device */

/*! This function gets the data associated with the specified parameter for the specified device.
*
*   \param[in] The handle to the device.
*   \param[in] Command string to send to the device.
*   \param[in] The command size (in bytes) including any null terminator.
*   \param[out] Buffer to write binary data to. Some commands may not return any data. Ignored if pointer is null.
*   \param[in] The size of the buffer in bytes.
*   \param[out] Buffer to write the string response to. 
*   \param[in] The max size of the response string buffer in bytes.
*   \param[in] Specifies that this invocation should be non-blocking (it will immediately return after being invoked).
*
*   \returns A ::tl_error_codes value to indicate success or failure (::TL_NO_ERROR indicates success).
*/
// TODO: Just a note that the non-blocking parameter is not used by the C camera interface, it always wants to block. Perhaps the parameter should be removed and assume blocking? - JTF 1/15/21
typedef int (*TL_GET_DATA)(void *, const char *, const size_t, void *, const size_t, char *, const size_t, int); /* tl_get_data */

/*! This function gets the data associated with the specified parameter for the specified device.
*
*   \param[in] The handle to the device.
*   \param[in] Command string to send to the device.
*   \param[in] The command size (in bytes) including any null terminator.
*   \param[in] Buffer to read binary data from. Some commands may not use this data. Ignored if pointer is null.
*   \param[in] The size of the buffer in bytes.
*   \param[out] Buffer to write the string response to.
*   \param[in] The max size of the response string buffer in bytes.
*
*   \returns A ::tl_error_codes value to indicate success or failure (::TL_NO_ERROR indicates success).
*/
typedef int (*TL_SET_DATA)(void *, const char *, const size_t, void *, const size_t, char *, const size_t); /* tl_set_data */

/*! This function gets all the module IDs that are supported by the current unified SDK instance.
*
*   \param[out] The character string that receives the list of module IDs.
*   \param[in] The size of the module ID string.
*
*   \returns A ::tl_error_codes value to indicate success or failure (::TL_NO_ERROR indicates success).
*/
typedef int (*TL_GET_DEVICE_MODULE_IDS)(char *, int); /* tl_get_device_module_ids */

/*! This function gets the data associated with the specified parameter for the specified module ID.
*
*   \param[in] The character string that specifies the module ID.
*   \param[in] The parameter associated with the data to get.
*   \param[out] A pointer to a buffer to receive the data.
*   \param[in] The size of the buffer to receive the data.
*
*   \returns A ::tl_error_codes value to indicate success or failure (::TL_NO_ERROR indicates success).
*/
typedef int (*TL_DEVICE_MODULE_GET_DATA)(const char *, const char *, void *, int); /* tl_device_module_get_data */

/*! This function sets the data associated with the specified parameter for the specified module ID.
*
*   \param[in] The character string that specifies the module ID.
*   \param[in] The parameter associated with the data to get.
*   \param[in] A pointer to a buffer that contains the data to set.
*   \param[in] The size of the buffer that contains the data to set.
*
*   \returns A ::tl_error_codes value to indicate success or failure (::TL_NO_ERROR indicates success).
*/
typedef int (*TL_DEVICE_MODULE_SET_DATA)(const char *, const char *, void *, int); /* tl_device_module_set_data */
