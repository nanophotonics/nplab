/*
* Copyright 2019 by Thorlabs, Inc.  All rights reserved.  Unauthorized use (including,
* without limitation, distribution and copying) is strictly prohibited.  All use requires, and is
* subject to, explicit written authorization and nondisclosure agreements with Thorlabs, Inc.
*/

#pragma once

/*! \file tl_mono_to_color_enum.h
*   \brief This file includes the declarations of all the enumerations unique to the mono to color processing module.
*/


/*! The TL_MONO_TO_COLOR_SPACE enumeration lists all the supported color spaces in the mono to color processing module.
*
*   A color space describes how the colors in an image are going to be specified. Some commonly used color spaces are those derived from the 
*   RGB color model, in which each pixel has a Red, Blue, and Green component. This means the amount of color that can expressed in a single 
*   pixel is all the possible combinations of Red, Blue, and Green. If we assume the image data is in bytes, each component can take any value 
*   from 0 to 255. The total number of colors that a pixel could express can be calculated as 256 * 256 * 256 = 16777216 different colors.
*   
*   There are many different color spaces that are used for different purposes. The mono to color processor supports two color spaces that 
*   are both derived from the RGB color model: sRGB and Linear sRGB.
*   
*   **sRGB** or standard Red Green Blue is a common color space used for displaying images on computer monitors or for sending images over the internet. 
*   In addition to the Red, Blue, and Green components combining to define the color of a pixel, the final RGB values undergo a nonlinear transformation 
*   to be put in the sRGB color space. The exact transfer function can be found online by searching for the sRGB specification. The purpose of this 
*   transformation is to represent the colors in a way that looks more accurate to humans.
*   
*    <pre>
*                           __________________
*                          |                  |
*                          |    Non Linear    |
*    RGB intensities  -->  |                  |  -->  sRGB data
*                          |  Transformation  |
*                          |__________________|
*    </pre> 
*   
*   **Linear sRGB** is very similar to sRGB, but does not perform the non linear transformation. The transformation of the data in sRGB changes the RGB intensities, 
*   whereas this color space is much more representative of the raw image data coming off the sensor. Without the transformation however, images in the Linear 
*   sRGB color space do not look as accurate as those in sRGB. When deciding between Linear sRGB and sRGB, use Linear sRGB when the actual intensities of the raw 
*   image data are important, and use sRGB when the image needs to look accurate to the human eye.
*    
*/
enum TL_MONO_TO_COLOR_SPACE
{
	TL_MONO_TO_COLOR_SPACE_SRGB /*!< The sRGB color space. */
	, TL_MONO_TO_COLOR_SPACE_LINEAR_SRGB /*!< The Linear sRGB color space. */
	, TL_MONO_TO_COLOR_SPACE_MAX /*!< A sentinel value (DO NOT USE). */
};


/*! The TL_MONO_TO_COLOR_ERROR enumeration lists all possible error codes that can be returned from the mono to color processing library. 
 *
 */
enum TL_MONO_TO_COLOR_ERROR
{
	TL_MONO_TO_COLOR_ERROR_NONE /*!< The command succeeded with no errors. */
	, TL_MONO_TO_COLOR_ERROR_COLOR_PROCESSING_ERROR /*!< An error was thrown in the color processing module. */
	, TL_MONO_TO_COLOR_ERROR_DEMOSAIC_ERROR /*!< An error was thrown in the demosaic module. */
	, TL_MONO_TO_COLOR_ERROR_CAMERA_ERROR /*!< An error was thrown in the camera module. */
	, TL_MONO_TO_COLOR_ERROR_INITIALIZATION_ERROR /*!< An error was thrown during module initialization. */
	, TL_MONO_TO_COLOR_ERROR_NULL_INSTANCE /*!< A pointer that was about to be dereferenced was null. */
	, TL_MONO_TO_COLOR_ERROR_UNKNOWN_ERROR /*!< An unknown error occured. */
	, TL_MONO_TO_COLOR_ERROR_INVALID_INPUT /*!< An unacceptable input was passed to this function. */
	, TL_MONO_TO_COLOR_ERROR_RUNTIME_ERROR /*!< Mono to color processor caught an invalid action. */
	, TL_MONO_TO_COLOR_ERROR_TERMINATION_ERROR /*!< An error was thrown during module termination. */
	, TL_MONO_TO_COLOR_ERROR_MAX /*!< A sentinel value (DO NOT USE). */
};
