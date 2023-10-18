/*
* Copyright 2019 by Thorlabs, Inc.  All rights reserved.  Unauthorized use (including,
* without limitation, distribution and copying) is strictly prohibited.  All use requires, and is
* subject to, explicit written authorization and nondisclosure agreements with Thorlabs, Inc.
*/

/*! \mainpage Thorlabs Scientific Mono To Color Processor
*
* \section Introduction
*
* The target audience for this document are software engineers with knowledge of C and Thorlabs 
* cameras. Knowledge of color processing is helpful but not required.
*
* The mono to color processing sdk is an all-in-one module to easily transform monochrome image
* data into colored image data. It wraps around the color processing suite, which is a more complex 
* set of libraries that allows one to control every aspect of color processing. See the \ref Advanced section for more details. 
* 
* When image data is received from the camera using the camera SDK, it represents raw intensities coming
* off the sensor. Without color processing, this will look like a monochrome mosaic or pixelated version of the 
* scene the camera is looking at. This is because Thorlabs color cameras have a color filter in front of the 
* sensor which will selectively allow certain wavelengths of light to pass through for each pixel. In the case 
* of Bayer filters, each pixel is only receiving Red wavelengths, Blue wavelengths, or Green wavelengths of light.
* The mosaic pattern that one will see from the raw image data will correspond to this Bayer color filter pattern.
* 
* Fortunately, the camera holds all the model-specific parameters that one needs to turn this monochrome mosaic image 
* data into a colored image. Two of those parameters are the color filter type and the color filter array 
* phase, which specify the physical features of the color filter. The camera also contains a color correction 
* matrix and a default white balance matrix that are used in the color processing pipeline to take the colored image and 
* adjust the colors to more accurately reflect what is seen by humans under typical conditions. All these parameters can 
* be used to initialize a mono to color processor for typical lighting environments. The end result is a nicely 
* colored image that requires only a few steps to create. There are additional controls after initialization to allow the user to 
* customize the coloring of the image for more accurate color correction.
* 
* \section Guide Getting Started
* 
* Getting started programming with the Thorlabs mono to color processing sdk is straightforward. This guide describes 
* how to program with the mono to color processing sdk using compiled (native) languages such as C or C++. This guide 
* assumes the user knows how to open a camera and get an image. To learn about working with Thorlabs cameras in native 
* code, check out the Thorlabs Camera C API Reference. This guide contains snippets of code that show short examples 
* of how to use specific functions. The full example that these snippets are based on can be found in the \ref Example section.
* 
* - Call tl_mono_to_color_processing_initialize() to dynamically load the mono to color SDK library and get handles to its exported functions.
* \snippet mono_to_color_example_snippets.c initialize sdk
* - Get all the information needed to initialize a mono to color processor:
*	- camera_sensor_type - use tl_camera_get_camera_sensor_type() to query this value from the camera.
*	 \snippet mono_to_color_example_snippets.c get camera sensor type
*	- color_filter_array_phase - use tl_camera_get_color_filter_array_phase() to query this value from the camera.
*	 \snippet mono_to_color_example_snippets.c get color filter array phase
*	- color_correction_matrix - use tl_camera_get_color_correction_matrix() to query this value from the camera.
*	 \snippet mono_to_color_example_snippets.c get color correction matrix
*	- default_white_balance_matrix - use tl_camera_get_default_white_balance_matrix() to query this from the camera.
*	 \snippet mono_to_color_example_snippets.c get default white balance matrix
*	- bit_depth - use tl_camera_get_bit_depth() to query this from the camera.
*	 \snippet mono_to_color_example_snippets.c get bit depth
* - Create a mono to color processor by calling tl_mono_to_color_create_mono_to_color_processor() with the above information.
* \snippet mono_to_color_example_snippets.c create mono to color processor
* - After creating a mono to color processor you can adjust the output format using tl_mono_to_color_set_output_format(). You can also adjust the color space 
*   using tl_mono_to_color_set_color_space().
*   \snippet mono_to_color_example_snippets.c set color space
*   \snippet mono_to_color_example_snippets.c set output format 
* - There are red, blue, and green gain values that can be adjusted to alter the colors of the output images. To set each of these gain values use 
*   tl_mono_to_color_set_red_gain(), tl_mono_to_color_set_blue_gain(), and tl_mono_to_color_set_green_gain() respectively. Higher gain values amplify the 
*   intensity of that color, whereas lower gain values will diminish the intensity.
*   \snippet mono_to_color_example_snippets.c set red gain
*   \snippet mono_to_color_example_snippets.c set green gain
*   \snippet mono_to_color_example_snippets.c set blue gain
* - Allocate memory for the colored output data. The amount of space that needs to be allocated depends on the number of pixels in the image data 
*   and the desired output bit depth. The following is an example of what size the output buffer needs to be when the image data corresponds to an image with 
*   dimensions 1920 x 1080 (2,073,600 pixels):
*	- For 24 bpp images, the output buffer size is: (sizeof(unsigned char) * (2073600) * 3) = 49766400 bytes.
*	- For 32 bpp images, the output buffer size is: (sizeof(unsigned char) * (2073600) * 4) = 66355200 bytes.
*	- For 48 bpp images, the output buffer size is: (sizeof(unsigned short) * (2073600) * 3) = 99532800 bytes;
* - Call the appropriate transform function for the desired output bit depth to get the colored image:
*	- tl_mono_to_color_transform_to_24(): This will output the color image data as 8 bits per channel, 3 channels per pixel.
* \snippet mono_to_color_example_snippets.c transform to 24
*	- tl_mono_to_color_transform_to_32(): This will output the color image data as 8 bits per channel, 4 channels per pixel. The fourth channel is a byte padding that can be used as an Alpha channel.
* \snippet mono_to_color_example_snippets.c transform to 32
*	- tl_mono_to_color_transform_to_48(): This will output the color image data as 16 bits per channel, 3 channels per pixel.
* \snippet mono_to_color_example_snippets.c transform to 48
* - Each transform function requires the pointers to the input buffer (the image data) and the output buffer, but they also require the width and height of the
*   image corresponding to the data in the input buffer. It is recommended to save the image width and height to variables after arming a camera and pass 
*   those variables to the mono to color processor each time transform is called. This is because querying these values from the camera each time a transform function 
*   needs to be called will significantly slow down the image processing. It is safe to save the image width and height after arming since the camera cannot 
*   change these values while it is armed.
* \snippet mono_to_color_example_snippets.c get image width
* \snippet mono_to_color_example_snippets.c get image height
* - When the application is finished with the mono to color processor, dispose of it using tl_mono_to_color_destroy_mono_to_color_processor(). Feel free to use as many 
*   mono to color processors as your application requires, just make sure they are all cleanly destroyed.
* \snippet mono_to_color_example_snippets.c destroy processor
* - When the application is finished with the mono to color processing sdk, dispose of it using tl_mono_to_color_processing_module_terminate(). 
* \snippet mono_to_color_example_snippets.c destroy sdk
* 
* \section Example
* 
* The following code shows how to use a mono to color processor to get a color image. The code is meant to 
* be a working example that goes through the entire imaging process, starting from opening a Thorlabs camera. 
* 
* \include mono_to_color_example_full.c
* 
*  
*  \section Advanced Advanced Color Processing
*  
*  The mono to color processing sdk utilizes the color processing suite to transform monochrome 
*  images. The color processing suite is made up of a couple SDKs and a number of DLLs that perform specific 
*  functions in the color processing pipeline. A color processing pipeline itself is made up of a number of 
*  steps, each with customizable parameters. The color processing suite allows for total customization of this 
*  processing pipeline. Instead of exposing all these controls, the mono to color processing sdk wraps up the color 
*  processing suite into a single sdk with a reduced API. It sets the pipeline up for a very common use case, but 
*  allows the details to still be controlled using high level properties like color space and color gains.
*  This will be useful for a large majority of users who are looking to get a colored image. 
*  
*  For advanced users looking to dive into the details of color processing pipelines, the color processing suite 
*  is available for use. The mono to color processing sdk can be used alongside the color processing suite, but to 
*  reduce confusion it is recommended to use one or the other. See the Thorlabs Scientific Color Processing Suite 
*  documentation to learn about what is possible with the color processing suite.
*  
*/

#pragma once

#include "tl_mono_to_color_enum.h"
#include "tl_color_enum.h"
#include "tl_camera_sdk.h"

///  \file tl_mono_to_color_processing.h
///  \brief This file includes the declaration prototypes of all the API functions contained in the mono to color processing module.

/// <summary>
/// This function initializes the  mono to color processing module.  It must be called prior to calling any other mono to color processing module API function.\n\n
/// </summary>
/// <returns>::TL_MONO_TO_COLOR_ERROR value to indicate success or failure (::TL_MONO_TO_COLOR_ERROR_NONE indicates success). </returns>

typedef int(*TL_MONO_TO_COLOR_PROCESSING_MODULE_INITIALIZE) (void);

/// <summary>
/// This function creates a mono to color processor instance and returns a pointer to that instance.\n\n
/// The mono to color processing instance is a handle to the internal mono to color processing state.\n\n
/// </summary>
/// <param name="camera_sensor_type">The camera sensor type that will be used. This value should be queried form the camera.</param>
/// <param name="color_filter_array_phase"> The color filter array phase that will be used. This value should be queried from the camera.</param>
/// <param name="color_correction_matrix"> The color correction matrix that will be used. This value should be queried from the camera.</param>
/// <param name="default_white_balance_matrix"> The default white balance matrix that will be used. The initial values of the color gains are derived from this matrix. This value should be queried from the camera.</param>
/// <param name="bit_depth"> The desired bit depth for this mono to color processor. This value should be queried from the camera.</param>
/// <param name="mono_to_color_handle"> Pointer to a pointer to the new mono to color processor instance.</param>
/// <returns>::TL_MONO_TO_COLOR_ERROR value to indicate success or failure (::TL_MONO_TO_COLOR_ERROR_NONE indicates success).</returns>
typedef int(*TL_MONO_TO_COLOR_CREATE_MONO_TO_COLOR_PROCESSOR) (enum TL_CAMERA_SENSOR_TYPE
																, enum TL_COLOR_FILTER_ARRAY_PHASE
																, float *
																, float *
																, int
																, void **);

/// <summary>
///  This function destroys a mono to color processor instance.\n\n 
///  After this function is called, the mono to color processor cannot be used. It is advised to set the mono_to_color_processor pointer 
///  to NULL to avoid accidental usage after this function has been called. The pointer does not need to be deleted. This function must be 
///  called for each mono to color processor before the program exits to cleanly release any open resources.\n\n
/// </summary>
/// <param name="mono_to_color_handle">A pointer to a mono to color processor handle.</param>
/// <returns>::TL_MONO_TO_COLOR_ERROR value to indicate success or failure (::TL_MONO_TO_COLOR_ERROR_NONE indicates success).</returns>
typedef int(*TL_MONO_TO_COLOR_DESTROY_MONO_TO_COLOR_PROCESSOR) (void *);

/// <summary>
///  This function allows the caller to get the color space of the mono to color processor.\n\n
///  The color space property specifies how the colors will be represented when output from the mono to color processor. 
///  The default value is ::TL_MONO_TO_COLOR_SPACE_SRGB.
/// </summary>
/// <param name="mono_to_color_handle">A pointer to a mono to color processor handle.</param>
/// <param name="color_space">A pointer to a ::TL_MONO_TO_COLOR_SPACE. The color space is returned by reference.</param>
/// <returns>::TL_MONO_TO_COLOR_ERROR value to indicate success or failure (::TL_MONO_TO_COLOR_ERROR_NONE indicates success).</returns>
typedef int(*TL_MONO_TO_COLOR_GET_COLOR_SPACE) (void *, enum TL_MONO_TO_COLOR_SPACE *);

/// <summary>
///  This function allows the caller to set the color space of the mono to color processor.\n\n
/// </summary>
/// <param name="mono_to_color_handle">A pointer to a mono to color processor handle.</param>
/// <param name="color_space">A ::TL_MONO_TO_COLOR_SPACE that the mono to color will use to set its color space property.</param>
/// <returns>A ::TL_MONO_TO_COLOR_ERROR value to indicate success or failure (::TL_MONO_TO_COLOR_ERROR_NONE indicates success).</returns>
typedef int(*TL_MONO_TO_COLOR_SET_COLOR_SPACE) (void *, enum TL_MONO_TO_COLOR_SPACE);

/// <summary>
/// This function allows the caller to get the output format of the mono to color processor.\n\n
/// The output format property specifies the ordering of the data that is output from the mono to color processor. 
/// For example, RGB_PIXEL will layout pixel data in sets of 3 corresponding to Red, Green, and Blue components: RGBRGBRGBRGB...,
/// Whereas BGR_PLANAR will layout all the Blue components, then all the Green components, and then all the Red components: BBBB... GGGG... RRRR... .\n\n
/// The default value is ::TL_COLOR_FORMAT_RGB_PIXEL.\n\n
/// </summary>
/// <param name="mono_to_color_handle">A pointer to a mono to color processor handle.</param>
/// <param name="color_space">A pointer to a ::TL_COLOR_FORMAT. The output format is returned by reference.</param>
/// <returns>A ::TL_MONO_TO_COLOR_ERROR value to indicate success or failure (::TL_MONO_TO_COLOR_ERROR_NONE indicates success).</returns>
typedef int(*TL_MONO_TO_COLOR_GET_OUTPUT_FORMAT) (void *, enum TL_COLOR_FORMAT *);

/// <summary>
/// This function allows the caller to set the output format of the mono to color processor.\n\n
/// </summary>
/// <param name="mono_to_color_handle">A pointer to a mono to color processor handle.</param>
/// <param name="output_format">A ::TL_COLOR_FORMAT that the mono to color processor will use to set its color space property.</param>
/// <returns>A ::TL_MONO_TO_COLOR_ERROR value to indicate success or failure (::TL_MONO_TO_COLOR_ERROR_NONE indicates success).</returns>
typedef int(*TL_MONO_TO_COLOR_SET_OUTPUT_FORMAT) (void *, enum TL_COLOR_FORMAT);

/// <summary>
/// This function allows the caller to get the red gain of the mono to color processor.\n\n
/// The red gain is used to amplify or diminish the red component of images transformed by the mono to color processor. 
/// Lower values correspond to a less intense red component and higher values correspond to a more intense red component.
/// The red, blue, and green gain values can be used to color-correct images, such as white balancing an image. 
/// The default value for red gain is determined by the default white balance matrix that is given to the mono to color processor during construction.\n\n
/// </summary>
/// <param name="mono_to_color_handle">A pointer to a mono to color processor handle.</param>
/// <param name="red_gain">A pointer to a float value. The red gain is returned by reference.</param>
/// <returns>::TL_MONO_TO_COLOR_ERROR value to indicate success or failure (::TL_MONO_TO_COLOR_ERROR_NONE indicates success).</returns>
typedef int(*TL_MONO_TO_COLOR_GET_RED_GAIN) (void *, float *);

/// <summary>
/// This function allows the caller to set the red gain of the mono to color processor.\n\n
/// </summary>
 /// <param name="mono_to_color_handle">A pointer to a mono to color processor handle.</param>
 /// <param name="red_gain">A float value that the mono to color processor will use to set its red gain property.</param>
/// <returns>::TL_MONO_TO_COLOR_ERROR value to indicate success or failure (::TL_MONO_TO_COLOR_ERROR_NONE indicates success).</returns>
typedef int(*TL_MONO_TO_COLOR_SET_RED_GAIN) (void *, float);

/// <summary>
/// This function allows the caller to get the blue gain of the mono to color processor.\n\n
/// The blue gain is used to amplify or diminish the blue component of images transformed by the mono to color processor.
/// Lower values correspond to a less intense blue component and higher values correspond to a more intense blue component.
/// The red, blue, and green gain values can be used to color-correct images, such as white balancing an image.
/// The default value for blue gain is determined by the default white balance matrix that is given to the mono to color processor during construction.\n\n
/// </summary>
/// <param name="mono_to_color_handle">A pointer to a mono to color processor handle.</param>
/// <param name="blue_gain">A pointer to a float value. The blue gain is returned by reference.</param>
/// <returns>A ::TL_MONO_TO_COLOR_ERROR value to indicate success or failure (::TL_MONO_TO_COLOR_ERROR_NONE indicates success).</returns>
typedef int(*TL_MONO_TO_COLOR_GET_BLUE_GAIN) (void *, float *);

/// <summary>
/// This function allows the caller to set the blue gain of the mono to color processor.\n\n
/// </summary>
/// <param name="mono_to_color_handle"> A pointer to a mono to color processor handle.</param>
/// <param name="blue_gain"> A float value that the mono to color processor will use to set its blue gain property.</param>
/// <returns>A ::TL_MONO_TO_COLOR_ERROR value to indicate success or failure (::TL_MONO_TO_COLOR_ERROR_NONE indicates success).</returns>
typedef int(*TL_MONO_TO_COLOR_SET_BLUE_GAIN) (void *, float);

/// <summary>
/// This function allows the caller to get the green gain of the mono to color processor.\n\n
/// The green gain is used to amplify or diminish the green component of images transformed by the mono to color processor. 
/// Lower values correspond to a less intense green component and higher values correspond to a more intense green component. 
/// The red, blue, and green gain values can be used to color-correct images, such as white balancing an image. 
/// The default value for green gain is determined by the default white balance matrix that is given to the mono to color processor during construction.\n\n
/// </summary>
/// <param name="mono_to_color_handle">A pointer to a mono to color processor handle.</param>
/// <param name="green_gain">A pointer to a float value. The green gain is returned by reference.</param>
/// <returns>A ::TL_MONO_TO_COLOR_ERROR value to indicate success or failure (::TL_MONO_TO_COLOR_ERROR_NONE indicates success).</returns>
typedef int(*TL_MONO_TO_COLOR_GET_GREEN_GAIN) (void *, float *);

/// <summary>
/// This function allows the caller to set the green gain of the mono to color processor.\n\n
/// </summary>
/// <param name="mono_to_color_handle">A pointer to a mono to color processor handle.</param>
/// <param name="green_gain">A float value that the mono to color processor will use to set its green gain property.</param>
/// <returns>A ::TL_MONO_TO_COLOR_ERROR value to indicate success or failure (::TL_MONO_TO_COLOR_ERROR_NONE indicates success).</returns>
typedef int(*TL_MONO_TO_COLOR_SET_GREEN_GAIN) (void *, float);

/// <summary>
/// This function transforms a monochrome image into a color image with 48 bits per pixel, where each pixel contains 3 channels and each channel is 16 bits. 
/// The number of elements in the output buffer should be 3x that of the input buffer.\n\n
/// </summary>
/// <param name="mono_to_color_handle">A pointer to a mono to color processor handle.</param>
/// <param name="input_buffer">The monochrome image data from the camera.</param>
/// <param name="image_width">The width in pixels associated with the image data in input_buffer.</param>
/// <param name="image_height">The height in pixels associated with the image data in input_buffer.</param>
/// <param name="output_buffer">The output buffer containing the colored image created by transforming the image data in input_buffer.</param>
/// <returns>A ::TL_MONO_TO_COLOR_ERROR value to indicate success or failure (::TL_MONO_TO_COLOR_ERROR_NONE indicates success).</returns>
typedef int(*TL_MONO_TO_COLOR_TRANSFORM_TO_48) (void *
												, unsigned short *
												, int
												, int
												, unsigned short *);

/// <summary>
/// This function transforms a monochrome image into a color image with 32 bits per pixel, where each pixel contains 4 channels and each channel is 8 bits. 
/// The 4th channel will be an Alpha channel with all values set to 0 (0% opacity). For example, if the output format is RGB_PIXEL, then the resulting structure 
/// of the output data will be RGBARGBARGBARGBA... .\n\n
/// The number of elements in the output buffer should be 4x that of the input buffer, but the data type should be unsigned char instead of unsigned short.\n\n
/// </summary>
/// <param name="mono_to_color_handle">A pointer to a mono to color processor handle.</param>
/// <param name="input_buffer">The monochrome image data from the camera.</param>
/// <param name="image_width">The width in pixels associated with the image data in input_buffer.</param>
/// <param name="image_height">The height in pixels associated with the image data in input_buffer.</param>
/// <param name="output_buffer">The output buffer containing the colored image created by transforming the image data in input_buffer.</param>
/// <returns>A ::TL_MONO_TO_COLOR_ERROR value to indicate success or failure (::TL_MONO_TO_COLOR_ERROR_NONE indicates success).</returns>
typedef int(*TL_MONO_TO_COLOR_TRANSFORM_TO_32) (void *
												, unsigned short *
												, int
												, int
												, unsigned char *);

/// <summary>
/// This function transforms a monochrome image into a color image with 24 bits per pixel, where each pixel contains 3 channels and each channel is 8 bits. 
/// The number of elements in the output buffer should be 3x that of the input buffer, but the data type should be unsigned char instead of unsigned short.\n\n
/// </summary>
/// <param name="mono_to_color_handle">A pointer to a mono to color processor handle.</param>
/// <param name="input_buffer">The monochrome image data from the camera.</param>
/// <param name="image_width">The width in pixels associated with the image data in input_buffer.</param>
/// <param name="image_height">The height in pixels associated with the image data in input_buffer.</param>
/// <param name="output_buffer">The output buffer containing the colored image created by transforming the image data in input_buffer.</param>
/// <returns>A ::TL_MONO_TO_COLOR_ERROR value to indicate success or failure (::TL_MONO_TO_COLOR_ERROR_NONE indicates success).</returns>
typedef int(*TL_MONO_TO_COLOR_TRANSFORM_TO_24) (void *
												, unsigned short *
												, int
												, int
												, unsigned char *);

/// <summary>
/// This function terminates the mono to color processing module. After this function is called, tl_mono_to_color_ functions will no longer be defined.
/// This function must be called before the program is finished to cleanly dispose of any open resources.\n\n
/// </summary>
/// <returns>A ::TL_MONO_TO_COLOR_ERROR value to indicate success or failure (::TL_MONO_TO_COLOR_ERROR_NONE indicates success).</returns>
typedef int(*TL_MONO_TO_COLOR_PROCESSING_MODULE_TERMINATE) (void);

/// <summary>
/// This function returns a human-friendly string of that corresponds to the last error that occured.\n\n
/// </summary>
/// <returns> A pointer to a Null-terminated const char string that contains the error message.</returns>
typedef const char *(*TL_MONO_TO_COLOR_GET_LAST_ERROR) (void);

/// <summary>
/// This function allows the user to retrieve the camera sensor type that has been associated with the given mono to color processor. 
/// This value is set during construction and cannot be modified during the lifetime of a mono to color object.\n\n
/// <summary>
/// <param name="mono_to_color_handle">A pointer to a mono to color processor handle.</param>
/// <param name="camera_sensor_type">The camera sensor type returned to the caller by reference.</param>
/// <returns>A ::TL_MONO_TO_COLOR_ERROR value to indicate success or failure (::TL_MONO_TO_COLOR_ERROR_NONE indicates success).</returns>
typedef int(*TL_MONO_TO_COLOR_GET_CAMERA_SENSOR_TYPE) (void *, enum TL_CAMERA_SENSOR_TYPE *);

/// <summary>
/// This function allows the user to retrieve the color filter array phase associated with the given mono to color processor.
/// This value is set during construction and cannot be modified during the lifetime of a mono to color object.\n\n
/// </summary>
/// <param name="mono_to_color_handle">A pointer to a mono to color processor handle.</param>
/// <param name="color_filter_array_phase">A pointer to a ::TL_COLOR_FILTER_ARRAY_PHASE. The color filter array phase is returned to the caller by reference.</param>
/// <returns>A ::TL_MONO_TO_COLOR_ERROR value to indicate success or failure (::TL_MONO_TO_COLOR_ERROR_NONE indicates success).</returns>
typedef int(*TL_MONO_TO_COLOR_GET_COLOR_FILTER_ARRAY_PHASE) (void *, enum TL_COLOR_FILTER_ARRAY_PHASE *);

/// <summary>
/// This function allows the user to retrieve the color correction matrix that has been associated with the given mono to color processor. 
/// The color correction matrix is a 3x3 matrix that is represented by a float array of 9 elements. 
/// This value is set during construction and cannot be modified during the lifetime of a mono to color object. \n\n
/// </summary>
/// <param name="mono_to_color_handle">A pointer to a mono to color processor handle.</param>
/// <param name="color_correction_matrix">The color correction matrix from the mono to color processor will be copied into this array. This array must have a size of at least 9.</param>
/// <returns>A ::TL_MONO_TO_COLOR_ERROR value to indicate success or failure (::TL_MONO_TO_COLOR_ERROR_NONE indicates success).</returns>
typedef int(*TL_MONO_TO_COLOR_GET_COLOR_CORRECTION_MATRIX) (void *, float *);

/// <summary>
/// This function allows the user to retrieve the default white balance matrix that has been associated with the given mono to color processor. 
/// The default white balance matrix is a 3x3 matrix that is represented by a float array of 9 elements. 
/// This value is set during construction and cannot be modified during the lifetime of a mono to color object.\n\n
/// </summary>
/// <param name="mono_to_color_handle">A pointer to a mono to color processor handle.</param>
/// <param name="default_white_balance_matrix">The default white balance matrix from the mono to color processor will be copied into this array. This array must have a size of at least 9.</param>
/// <returns>A ::TL_MONO_TO_COLOR_ERROR value to indicate success or failure (::TL_MONO_TO_COLOR_ERROR_NONE indicates success).</returns>
typedef int(*TL_MONO_TO_COLOR_GET_DEFAULT_WHITE_BALANCE_MATRIX) (void *, float *);

/// <summary>
/// This function allows the user to retrieve the bit depth associated with the given color processor.
/// This value is set during construction and cannot be modified during the lifetime of a mono to color object.\n\n
/// </summary>
/// <param name="mono_to_color_handle">A pointer to a mono to color processor handle.</param>
/// <param name="bit_depth">The bit depth is returned to the caller by reference.</param>
/// <returns>A ::TL_MONO_TO_COLOR_ERROR value to indicate success or failure (::TL_MONO_TO_COLOR_ERROR_NONE indicates success).</returns>
typedef int(*TL_MONO_TO_COLOR_GET_BIT_DEPTH) (void *, int *);
