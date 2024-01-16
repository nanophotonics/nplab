/*
This file is part of THORLABS UNIFIED SDK, distributed under the MIT License
Copyright (c) 2018 Thorlabs Scientific Imaging Corp
For full license details, see the accompanying LICENSE file.
*/

#pragma once

/*! \file tl_color_LUT.h
*   \brief This file includes the declaration prototyes of all the API functions 
*          contained in the look-up table (LUT) color module.
*/

/*! \brief This function initializes the LUT module.\n\n
*          It must be called prior to calling any other LUT module API function.
*  
*   \returns A ::TL_COLOR_ERROR value to indicate success or failure (::TL_COLOR_NO_ERROR indicates success).
*/
typedef int (*INITIALIZE_LUT_MODULE)(void);

/*! \brief This function creates a LUT instance and returns a pointer to that instance.\n\n
*          The LUT instance is a handle to the internal buffer containing the LUT data.
*  
*   \param[in] size The size in bytes of the LUT data array.
*   \returns A handle to the LUT instance.  A zero (0) handle indicates failure to create the instance.
*/
typedef void* (*CREATE_LUT) (int size);

/*! \brief This function returns a pointer to the internal LUT data array.\n\n
*          This would allow a user to directly manipulate individual LUT data elements.\n\n
*          The individual LUT data elements are stored as 32-bit integers.
*  
*   \param[in] handle The LUT instance handle (obtained by calling create_LUT()).
*   \returns A pointer to the LUT data buffer.  A zero (0) pointer indicates failure.
*/
typedef int* (*GET_LUT_DATA) (void* handle);

/*! \brief This function applies the LUT transform directly to the supplied buffer.
*          It overwrites the data in the supplied buffer so in that sense, it is destructive.\n\n
*          The implementation uses AVX2 vector instructions to accelerate the computation on machines
*          which support that instruction set.\n\n
*          A legacy scalar implementation is also included to support older generation hardware which
*          do not support the new instructions.\n\n
*          The user does not need to choose between the vector vs. scalar implementation - that is done
*          automatically based on a run time interrogation of the CPU capabilities.
*  
*   \param[in] handle The LUT instance handle (obtained by calling create_LUT()).
*   \param[in, out] buffer The data buffer containing the data to be transformed using the LUT data.
*   \param[in] number_of_elements The number of (16-bit) elements in the supplied buffer.
*   \returns A ::TL_COLOR_ERROR value to indicate success or failure (::TL_COLOR_NO_ERROR indicates success).
*/
typedef int (*TRANSFORM_LUT_16) (void* handle, unsigned short* buffer, int number_of_elements);

/*! \brief This function destroys the specified LUT instance.\n\n After this function has been called
*          for the specified instance handle, it is an error to subsequently use that instance in any way.\n\n
*          Any attempt to do so could result in undefined and unpredictable behavior.
*  
*   \param[in] handle The LUT instance handle (obtained by calling create_LUT()).
*   \returns A ::TL_COLOR_ERROR value to indicate success or failure (::TL_COLOR_NO_ERROR indicates success).
*/
typedef int (*DESTROY_LUT) (void* handle);

/*! \brief This function gracefully terminates the LUT module.\n\n It must be called prior to unloading the
*          LUT shared library to ensure proper cleanup of platform resources.
*  
*   \returns A ::TL_COLOR_ERROR value to indicate success or failure (::TL_COLOR_NO_ERROR indicates success).
*/
typedef int (*TERMINATE_LUT_MODULE)(void);
