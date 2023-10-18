/*
This file is part of THORLABS UNIFIED SDK, distributed under the MIT License
Copyright (c) 2018 Thorlabs Scientific Imaging Corp
For full license details, see the accompanying LICENSE file.
*/

#pragma once

#include "tl_color_enum.h"

/*! \file tl_color_demosaic.h
*   \brief This file includes the declaration prototypes of all the API functions 
*          contained in the demosaic color module.
*/

/*! This function initializes the demosaic module.  It must be called prior to 
*   calling any other demosaic module API function.
*  
*   \returns A ::TL_COLOR_ERROR value to indicate success or failure (::TL_COLOR_NO_ERROR indicates success).
*/
typedef int (*TL_DEMOSAIC_MODULE_INITIALIZE)(void);

/*! This function takes an input buffer containing monochrome image data and writes
*   a color image into the specified output buffer using a standard demosaic computation.
*  
*   The transformation can be viewed as "expanding" the single channel monochrome pixel data into
*   three color channels of pixel data.
*  
*   The implementation uses AVX2 vector instructions to accelerate the computation on machines
*   which support that instruction set.
*  
*   A legacy scalar implementation is also included to support older generation hardware which
*   do not support the new instructions.
*  
*   The user does not need to choose between the vector vs. scalar implementation - that is done
*   automatically based on a run time interrogation of the CPU capabilities.
*  
*   \param[in] width The width (x-axis) in pixels of the region of interest (ROI) specified in the input buffer.
*   \param[in] height The height (y-axis) in pixels of the ROI specified in the input buffer.
*   \param[in] x_origin The x coordinate of the origin pixel in the ROI relative to the full frame.
*   \param[in] y_origin The y coordinate of the origin pixel in the ROI relative to the full frame.
*   \param[in] color_phase The Bayer pattern color (::TL_COLOR_FILTER_ARRAY_PHASE) of the origin pixel in the full frame.
*   \param[in] output_color_format The desired pixel order (::TL_COLOR_FORMAT) that should be used when the color data is written to the output buffer.
*   \param[in] color_filter_type The color filter type (::TL_COLOR_FILTER_TYPE) of the device which produced the input data.
*   \param[in] bit_depth The pixel bit depth of the input buffer data.  The maximum number of bits used to specify a pixel intensity value in the input buffer.
*   \param[in] input_buffer A pointer to the 16-bit input monochrome data.
*   \param[out] output_buffer A pointer to the output 16-bit color data buffer.
*   \returns A TL_COLOR_ERROR value to indicate success or failure (::TL_COLOR_NO_ERROR indicates success).
*/
typedef int (*TL_DEMOSAIC_TRANSFORM_16_TO_48) (int width
                                             , int height
                                             , int x_origin
                                             , int y_origin
                                             , enum TL_COLOR_FILTER_ARRAY_PHASE color_phase
                                             , enum TL_COLOR_FORMAT output_color_format
                                             , enum TL_COLOR_FILTER_TYPE color_filter_type
                                             , int bit_depth
                                             , unsigned short* input_buffer
                                             , unsigned short* output_buffer);

/*! This function gracefully terminates the demosaic module.  It must be called prior to unloading the 
*   demosaic shared library to ensure proper cleanup of platform resources.
*  
*   \returns A ::TL_COLOR_ERROR value to indicate success or failure (::TL_COLOR_NO_ERROR indicates success).
*/
typedef int (*TL_DEMOSAIC_MODULE_TERMINATE)(void);
