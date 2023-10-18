/*
This file is part of THORLABS UNIFIED SDK, distributed under the MIT License
Copyright (c) 2018 Thorlabs Scientific Imaging Corp
For full license details, see the accompanying LICENSE file.
*/

#pragma once

/*! \file tl_color_enum.h
*   \brief This file includes the declarations of all the enumerations used by the TSI color processing modules.
*/

/*! The TL_COLOR_FILTER_ARRAY_PHASE enumeration lists all the possible values
*   that a pixel in a Bayer pattern color arrangement could assume.
*
*   The classic Bayer pattern is
*
*   <pre>
*   -----------------------
*   |          |          |
*   |    R     |    GR    |
*   |          |          |
*   -----------------------
*   |          |          |
*   |    GB    |    B     |
*   |          |          |
*   -----------------------
*   </pre>
*
*   where:
*   
*   - R = a red pixel
*   - GR = a green pixel next to a red pixel
*   - B = a blue pixel
*   - GB = a green pixel next to a blue pixel
*  
*   The primitive pattern shown above represents the fundamental color pixel arrangement in a Bayer pattern
*   color sensor.  The basic pattern would extend in the X and Y directions in a real color sensor containing
*   millions of pixels.
*  
*   Notice that the color of the origin (0, 0) pixel logically determines the color of every other pixel.
*  
*   It is for this reason that the color of this origin pixel is termed the color "phase" because it represents
*   the reference point for the color determination of all other pixels.
*  
*   Every TSI color camera provides the sensor specific color phase of the full frame origin pixel as a discoverable parameter.
*/
enum TL_COLOR_FILTER_ARRAY_PHASE
{
   TL_COLOR_FILTER_ARRAY_PHASE_BAYER_RED /*!< A red pixel. */
 , TL_COLOR_FILTER_ARRAY_PHASE_BAYER_BLUE /*!< A blue pixel. */
 , TL_COLOR_FILTER_ARRAY_PHASE_BAYER_GREEN_LEFT_OF_RED /*!< A green pixel next to a red pixel. */
 , TL_COLOR_FILTER_ARRAY_PHASE_BAYER_GREEN_LEFT_OF_BLUE /*!< A green pixel next to a blue pixel. */
 , TL_COLOR_FILTER_ARRAY_PHASE_MAX /*!< A sentinel value (DO NOT USE). */
};

/*! The TL_COLOR_FORMAT enumeration lists all the possible options for specifying the order of
*   color pixels in input and/or output buffers.
*  
*   This enumeration appears as an argument in certain API functions across the different
*   color modules that a programmer must specify to determine the behavior of that function.
*  
*   Depending on the context, it can specify
*   - the desired pixel order that a module must use when writing color pixel data into an output buffer
*   - the pixel order that a module must use to interpret data in an input buffer.
*/
enum TL_COLOR_FORMAT
{
   TL_COLOR_FORMAT_BGR_PLANAR /*!< The color pixels blue, green, and red are grouped in separate planes in the buffer: BBBBBBBB..., GGGGGGGG..., RRRRRRRR.... */
 , TL_COLOR_FORMAT_BGR_PIXEL /*!< The color pixels blue, green, and red are clustered and stored consecutively in the following pattern: BGRBGRBGR... */
 , TL_COLOR_FORMAT_RGB_PIXEL /*!< The color pixels blue, green, and red are clustered and stored consecutively in the following pattern: RGBRGBRGB... */
 , TL_COLOR_FORMAT_MAX /*!< A sentinel value (DO NOT USE). */
};

/*! The TL_COLOR_FILTER_TYPE enumeration lists all the possible types of color sensor pixel
*   arrangements that can be found in TSI's color camera product line.
*  
*   Every TSI color camera provides the color filter type of its sensor as a discoverable parameter.
*/
enum TL_COLOR_FILTER_TYPE
{
   TL_COLOR_FILTER_TYPE_BAYER /*!< A Bayer pattern color sensor. */
 , TL_COLOR_FILTER_TYPE_MAX /*!< A sentinel value (DO NOT USE). */
};
