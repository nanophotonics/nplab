/*
* Copyright 2019 by Thorlabs, Inc.  All rights reserved.  Unauthorized use (including,
* without limitation, distribution and copying) is strictly prohibited.  All use requires, and is
* subject to, explicit written authorization and nondisclosure agreements with Thorlabs, Inc.
*/

/*! \mainpage Thorlabs Scientific Logger
*
* \section Introduction
*
* The target audience for this document is a software professional who wants to incorporate
* their component into the TSI logging framework.
*
*/

#pragma once
#include "tsi_log_priority.h"

/*! \file tsi_log.h
*   \brief This file includes the declaration prototypes of all the API functions 
*          contained in the logger module.
*/

/*! This function creates a handle to a logger based on the specified parameters.
*  
*   \param[in] moduleID A character string identifying the name of the module containing the statements to log
*   \param[in] groupID A character string identifying an alternate name to use when creating a logger.
*                      This name should be different than the moduleID and is used to subclass a logger from
*                      the primary identifier which is the groupID.
*   \param[in] configFileName The name of the configuration file to use for this instance of the logger.
*   \returns A handle to a logger.
*/
typedef void* (*TSI_GET_LOG) (const char *moduleID, const char *groupID, const char *configFileName);

/*! This function will log the specified statement according to the specified parameters.
*
*   \param[in] logger A handle to the desired logger.
*   \param[in] priority A character string indicating the log priority.
*                       Valid values are:
*                       - "Fatal"
*                       - "Critical"
*                       - "Error"
*                       - "Warning"
*                       - "Notice"
*                       - "Information"
*                       - "Debug"
*                       - "Trace"
*   \param[in] file_name The file name containing the statement to log.
*   \param[in] file_line The line number in the file containing the statement to log.
*   \param[in] function_name The name of the function containing the statement to log.
*   \param[in] msg The statement to log.
*   \returns 0 to indicate success and 1 to indicate failure.
*/
typedef int (*TSI_LOG) (void *logger, enum TSI_LOG_PRIORITY priority, const char *file_name, int file_line, const char *function_name, const char *msg);

/*! This function destroys the logger with the specified parameters.
*  
*   \param[in] moduleID A character string identifying the name of the module containing the statements to log
*   \param[in] groupID A character string identifying an alternate name to use when creating a logger.
*                      This name should be different than the moduleID and is used to subclass a logger from
*                      the primary identifier which is the groupID.
*/
typedef void (*TSI_FREE_LOG) (const char *moduleID, const char *groupID);
