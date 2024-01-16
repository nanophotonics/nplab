/*
* Copyright 2019 by Thorlabs, Inc.  All rights reserved.  Unauthorized use (including,
* without limitation, distribution and copying) is strictly prohibited.  All use requires, and is
* subject to, explicit written authorization and nondisclosure agreements with Thorlabs, Inc.
*/

#pragma once

/*! \file tl_polarization_processor_error.h
*   \brief This file contains an enumeration that specifies all the possible error codes
*          that the API functions in the polarization processor module could return.
*/

/*! The TL_POLARIZATION_PROCESSOR_ERROR enumeration lists all the possible error codes that any polarization processor
*   API function could return.
*/

enum TL_POLARIZATION_PROCESSOR_ERROR
{
    TL_POLARIZATION_PROCESSOR_ERROR_NONE /*!< This error code indicates SUCCESS. */
  , TL_POLARIZATION_PROCESSOR_ERROR_UNKNOWN /*!< This error code indicates an unknown error. */
  , TL_POLARIZATION_PROCESSOR_ERROR_MODULE_NOT_INITIALIZED /*!< The module has not been initialized therefore it is in an undefined state. */
  , TL_POLARIZATION_PROCESSOR_ERROR_MEMORY_ALLOCATION_FAILURE /*!< The module has not been initialized therefore it is in an undefined state. */
  , TL_POLARIZATION_PROCESSOR_ERROR_NULL_INSTANCE_HANDLE /*!< The specified module instance handle is NULL. */
  , TL_POLARIZATION_PROCESSOR_ERROR_NULL_INPUT_BUFFER_POINTER /*!< The specified input buffer pointer is NULL. */
  , TL_POLARIZATION_PROCESSOR_ERROR_ALL_OUTPUT_BUFFER_POINTERS_ARE_NULL /*!< All specified output buffers are NULL. */
  , TL_POLARIZATION_PROCESSOR_ERROR_IDENTICAL_INPUT_AND_OUTPUT_BUFFERS /*!< An output buffer has been specified that is identical to the input buffer. */
  , TL_POLARIZATION_PROCESSOR_ERROR_DUPLICATE_OUTPUT_BUFFER /*!< Two or more output buffers are identical. */
  , TL_POLARIZATION_PROCESSOR_ERROR_INVALID_POLAR_PHASE /*!< An invalid (unknown) polar phase was specified. */
  , TL_POLARIZATION_PROCESSOR_ERROR_INVALID_MAX_SCALING_VALUE /*!< An invalid maximum scaling value was specified. */
  , TL_POLARIZATION_PROCESSOR_ERROR_INVALID_IMAGE_WIDTH /*!< An invalid image width was specified. */
  , TL_POLARIZATION_PROCESSOR_ERROR_INVALID_IMAGE_HEIGHT /*!< An invalid image height was specified. */
  , TL_POLARIZATION_PROCESSOR_ERROR_INVALID_IMAGE_DATA_BIT_DEPTH /*!< An invalid image bit depth was specified. */
  , TL_POLARIZATION_PROCESSOR_ERROR_INITIALIZATION_ERROR /*!< This indicates an error during initialization, usually attributed to missing or incompatible dynamic libraries. */
  , TL_POLARIZATION_PROCESSOR_ERROR_TERMINATION_ERROR /*!< This indicates an error during cleanup. */
  , TL_POLARIZATION_PROCESSOR_ERROR_MAX /*!< A sentinel value (DO NOT USE). */
};
