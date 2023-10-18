/*
This file is part of THORLABS UNIFIED SDK, distributed under the MIT License
Copyright (c) 2018 Thorlabs Scientific Imaging Corp
For full license details, see the accompanying LICENSE file.
*/

#pragma once

/*! \file tl_color_error.h
*   \brief This file contains an enumeration that specifies all the possible error codes
*          that the API functions in the color modules could return (assuming that the
*          API functions have been defined to return an error code - some don't).
*/

/*! The TL_COLOR_ERROR enumeration lists all the possible error codes that any color processing
*   API function could return.
*/
enum TL_COLOR_ERROR
{
    TL_COLOR_NO_ERROR /*!< Functions will return this error code to indicate SUCCESS. */
  , TL_COLOR_MODULE_NOT_INITIALIZED /*!< The module has not been initialized therefore it is in an undefined state. */
  , TL_COLOR_NULL_INSTANCE_HANDLE /*!< The specified module instance handle is NULL. */
  , TL_COLOR_NULL_INPUT_BUFFER_POINTER /*!< The specified input buffer pointer is NULL. */
  , TL_COLOR_NULL_OUTPUT_BUFFER_POINTER /*!< The specified output buffer pointer is NULL. */
  , TL_COLOR_IDENTICAL_INPUT_AND_OUTPUT_BUFFERS /*!< The same buffer pointer was specified for both the input and output buffers. */
  , TL_COLOR_INVALID_COLOR_FILTER_ARRAY_PHASE /*!< The specified color filter array phase is invalid. */
  , TL_COLOR_INVALID_COLOR_FILTER_TYPE /*!< The specified color filter type is unknown. */
  , TL_COLOR_INVALID_BIT_DEPTH /*!< The specified pixel bit depth is invalid. */
  , TL_COLOR_INVALID_INPUT_COLOR_FORMAT /*!< The specified input color format is unknown. */
  , TL_COLOR_INVALID_OUTPUT_COLOR_FORMAT /*!< The specified output color format is unknown. */
  , TL_COLOR_INVALID_BIT_SHIFT_DISTANCE /*!< The specified bit shift distance is invalid. */
  , TL_COLOR_INVALID_CLAMP_VALUE /*!< The specified pixel clamp value is invalid. */
  , TL_COLOR_INVALID_INPUT_IMAGE_WIDTH /*!< The specified input image width is invalid. */
  , TL_COLOR_INVALID_INPUT_IMAGE_HEIGHT /*!< The specified input image height is invalid. */
  , TL_COLOR_ERROR_MAX /*!< A sentinel value (DO NOT USE). */
};
