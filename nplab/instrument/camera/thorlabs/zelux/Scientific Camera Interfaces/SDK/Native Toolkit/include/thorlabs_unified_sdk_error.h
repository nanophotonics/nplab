/*
* Copyright 2017 by Thorlabs, Inc.  All rights reserved.  Unauthorized use (including,
* without limitation, distribution and copying) is strictly prohibited.  All use requires, and is
* subject to, explicit written authorization and nondisclosure agreements with Thorlabs, Inc.
*/

#pragma once

enum tl_error_codes
{
    TL_NO_ERROR,
    TL_MEMORY_DEALLOCATE_ERROR,
    TL_TOO_MANY_INTERNAL_FUNCTIONS_REQUESTED,
    TL_FAILED_TO_OPEN_MODULE,
    TL_FAILED_TO_MAP_FUNCTION,
    TL_OBJECT_NOT_FOUND,
    TL_GET_DATA_FAILED,
    TL_SET_DATA_FAILED,
    TL_INITIALIZATION_FAILURE,
    TL_FAILED_TO_OPEN_DEVICE,
    TL_FAILED_TO_CLOSE_DEVICE,
    TL_FAILED_TO_START_DEVICE,
    TL_FAILED_TO_STOP_DEVICE,
    TL_COMMUNICATION_FAILURE,
    TL_DEVICE_DISCONNECTED,
    TL_INSUFFICIENT_BUFFER_SIZE,
    TL_INVALID_POINTER,
    TL_ERROR_MAX
};
