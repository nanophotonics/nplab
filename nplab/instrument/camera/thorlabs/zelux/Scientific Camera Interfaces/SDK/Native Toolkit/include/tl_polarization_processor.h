/*
* Copyright 2019 by Thorlabs, Inc.  All rights reserved.  Unauthorized use (including,
* without limitation, distribution and copying) is strictly prohibited.  All use requires, and is
* subject to, explicit written authorization and nondisclosure agreements with Thorlabs, Inc.
*/

/*! \mainpage Thorlabs Scientific Polarization Processor
*
* \section Introduction
*
* The target audience for this document is the experienced software engineer with a background
* in polarized image processing.
*
*/

#pragma once

#include "tl_polarization_processor_enums.h"

/*! \file tl_polarization_processor.h
*   \brief This file includes the declaration prototypes of all the API functions 
*          contained in the polarization processor module.
*/

/*! This function initializes the polarization processing module.  It must be called prior to
*   calling any other polarization processing module API function.
*  
*   \returns A ::TL_POLARIZATION_PROCESSOR_ERROR value to indicate success or failure (::TL_POLARIZATION_PROCESSOR_ERROR_NONE indicates success).
*/
typedef int (*TL_POLARIZATION_PROCESSOR_MODULE_INITIALIZE)(void);

/*! This function creates a polarization processing instance and returns a pointer to that instance.
*  
*   The polarization processor instance is a handle to the internal polarization processing state which consists of:
*   - polarization calibration coefficients
*  
*   \param[out] pp_handle A pointer to pointer to a polarization processor handle.  This argument captures the instance that is returned by the function.
*   \returns A ::TL_POLARIZATION_PROCESSOR_ERROR value to indicate success or failure (::TL_POLARIZATION_PROCESSOR_ERROR_NONE indicates success).
*/
typedef int (*TL_POLARIZATION_PROCESSOR_CREATE_POLARIZATION_PROCESSOR)(void**);

/*! This function allows the caller to set the polarization processor calibration coefficients.
*  
*   The coefficients are set for each pixel in the polarization processor quartet.
*
*   The coefficients are specified for the 4 different polar phases of the origin pixel in the quartet:
*   - 0 (zero) degrees polar phase
*   - 45 degrees polar phase
*   - 90 degress polar phase
*   - 135 degrees polar phase
*  
*   \param[in] pp_handle A pointer to a polarization processor handle (pointer to pointer).
*   \param[out] calibration_4_x_4_matrix_0_degrees_phase A 16 element float array specifying the calibration coefficients for the 0 (zero) degrees phase pixel in the quartet.
*   \param[out] calibration_4_x_4_matrix_45_degrees_phase A 16 element float array specifying the calibration coefficients for the 45 degrees phase pixel in the quartet.
*   \param[out] calibration_4_x_4_matrix_90_degrees_phase A 16 element float array specifying the calibration coefficients for the 90 degrees phase pixel in the quartet.
*   \param[out] calibration_4_x_4_matrix_135_degrees_phase A 16 element float array specifying the calibration coefficients for the 135 degrees phase pixel in the quartet.
*   \returns A ::TL_POLARIZATION_PROCESSOR_ERROR value to indicate success or failure (::TL_POLARIZATION_PROCESSOR_ERROR_NONE indicates success).
*/
typedef int (*TL_POLARIZATION_PROCESSOR_SET_CUSTOM_CALIBRATION_COEFFICIENTS) (void* /*pp_handle*/
                                                                            , float* /*calibration_4_x_4_matrix_0_degrees_phase*/
                                                                            , float* /*calibration_4_x_4_matrix_45_degrees_phase*/
                                                                            , float* /*calibration_4_x_4_matrix_90_degrees_phase*/
                                                                            , float* /*calibration_4_x_4_matrix_135_degrees_phase*/);
																	  
/*! This function allows the caller to get the polarization processor calibration coefficients.
*  
*   The coefficients are obtained for each pixel in the polarization processor quartet.
*
*   The coefficients are specified for the 4 different polar phases of the origin pixel in the quartet:
*   - 0 (zero) degrees polar phase
*   - 45 degrees polar phase
*   - 90 degress polar phase
*   - 135 degrees polar phase
*  
*   \param[in] pp_handle A polarization processor handle.
*   \param[in] calibration_4_x_4_matrix_0_degrees_phase A 16 element float array specifying the calibration coefficients for the 0 (zero) degrees phase pixel in the quartet.
*   \param[in] calibration_4_x_4_matrix_45_degrees_phase A 16 element float array specifying the calibration coefficients for the 45 degrees phase pixel in the quartet.
*   \param[in] calibration_4_x_4_matrix_90_degrees_phase A 16 element float array specifying the calibration coefficients for the 90 degrees phase pixel in the quartet.
*   \param[in] calibration_4_x_4_matrix_135_degrees_phase A 16 element float array specifying the calibration coefficients for the 135 degrees phase pixel in the quartet.
*   \returns A ::TL_POLARIZATION_PROCESSOR_ERROR value to indicate success or failure (::TL_POLARIZATION_PROCESSOR_ERROR_NONE indicates success).
*/
typedef int (*TL_POLARIZATION_PROCESSOR_GET_CUSTOM_CALIBRATION_COEFFICIENTS) (void* /*pp_handle*/
                                                                            , float* /*calibration_4_x_4_matrix_0_degrees_phase*/
                                                                            , float* /*calibration_4_x_4_matrix_45_degrees_phase*/
                                                                            , float* /*calibration_4_x_4_matrix_90_degrees_phase*/
                                                                            , float* /*calibration_4_x_4_matrix_135_degrees_phase*/);
																	  
/*! This function implements the actual polarization processing computation.
*  
*   It takes an input array consisting of pixel values from a 2-dimensional image and transforms that data into 1 of several output arrays depending on the desired computation.
*   The following computations are supported:
*
*   - Normalized stokes vector coefficients
*   - Total power
*   - Horizontal/Vertical linear polarization
*   - Diagonal linear polarization
*   - Azimuth
*   - DOLP (degree of linear polarization)
*
*   The caller indicates the desired output computation by specifying a non-zero buffer pointer for the corresponding function argument.
*
*   A zero output buffer argument indicates that the corresponding output computation is not wanted and in that case, the computation is skipped.
*
*   \param[in] pp_handle A polarization processor handle.
*   \param[in] polar_phase The polar phase (in degrees) of the origin pixel in the input buffer.
*   \param[in] input_image_buffer A pointer to the input image buffer.
*   \param[in] input_image_buffer_x_origin The input buffer origin x coordinate relative to the full frame (necessary to support arbitrary ROIs)
*   \param[in] input_image_buffer_y_origin The input buffer origin y coordinate relative to the full frame (necessary to support arbitrary ROIs)
*   \param[in] input_image_buffer_width Input image buffer width.
*   \param[in] input_image_buffer_height Input image buffer height.
*   \param[in] input_image_buffer_data_bit_depth Input image buffer bit depth.
*   \param[in] output_buffer_max_scaling_value The maximum pixel intensity value that should be used for the output buffers.  This value must be between 1 and 65535.
*   \param[out] normalized_stokes_vector_coefficients_x2_output_buffer Output buffer which captures the normalized stokes vector coefficients s0, s1, s2, and s3.
*                                                                      s0 is always 1.0 since s1 and s2 are normalized to it and s3 is always 0.0 since it is not possible
*                                                                      for us to determine its value.  Therefore, this buffer only contains values for s1 and s2.
*                                                                      The order of data in the output buffer is s1_0, s2_0, s1_1, s2_1, ....  In other words, it is interleaved.
*                                                                      The user should specify a 0 pointer if this output is not needed.
*   \param[out] total_optical_power_output_buffer Output buffer of the total power (intensity).  This is value of the s0 stokes vector coefficient for each pixel.
*                                                 The user should specify a 0 pointer if this output is not needed.
*   \param[out] horizontal_vertical_linear_polarization_output_buffer Output buffer of the horizontal/vertical linear polarization.  This is the value of the s1 stokes vector coefficient for each pixel.
*                                                                     The user should specify a 0 pointer if this output is not needed.
*   \param[out] diagonal_linear_polarization_output_buffer Output buffer of the diagonal linear polarization. This is the value of the s2 stokes vector coefficient for each pixel.
*                                                          The user should specify a 0 pointer if this output is not needed.
*   \param[out] azimuth_output_buffer Output buffer of the azimuth (polar angle) of each pixel.  The user should specify a 0 pointer if this output is not needed.
*   \param[out] DOLP_output_buffer Output buffer of the DOLP (degree of linear polarization) for each pixel.  The user should specify a 0 pointer if this output is not needed.
*   \returns A ::TL_POLARIZATION_PROCESSOR_ERROR value to indicate success or failure (::TL_POLARIZATION_PROCESSOR_ERROR_NONE indicates success).
*/
typedef int (*TL_POLARIZATION_PROCESSOR_TRANSFORM) (void* /*pp_handle*/
                                                  , enum TL_POLARIZATION_PROCESSOR_POLAR_PHASE /*polar_phase*/
                                                  , unsigned short* /*input_image_buffer*/
                                                  , int /*input_image_buffer_x_origin*/
                                                  , int /*input_image_buffer_y_origin*/
                                                  , int /*input_image_buffer_width*/
                                                  , int /*input_image_buffer_height*/
                                                  , int /*input_image_buffer_data_bit_depth*/
                                                  , unsigned short /*output_buffer_max_scaling_value*/
                                                  , float* /*normalized_stokes_vector_coefficients_x2_output_buffer*/
                                                  , unsigned short* /*total_optical_power_output_buffer*/
                                                  , unsigned short* /*horizontal_vertical_linear_polarization_output_buffer*/
                                                  , unsigned short* /*diagonal_linear_polarization_output_buffer*/
                                                  , unsigned short* /*azimuth_output_buffer*/
                                                  , unsigned short* /*DOLP_output_buffer*/);
											
/*! This function destroys the specified polarization processing instance.  After this function has been called
*   for the specified instance handle, it is an error to subsequently use that instance in any way.
*   Any attempt to do so could result in undefined and unpredictable behavior.
*  
*   \param[in] pp_handle A polarization processor handle.
*   \returns A ::TL_POLARIZATION_PROCESSOR_ERROR value to indicate success or failure (::TL_POLARIZATION_PROCESSOR_ERROR_NONE indicates success).
*/
typedef int (*TL_POLARIZATION_PROCESSOR_DESTROY_POLARIZATION_PROCESSOR) (void* /*pp_handle*/);

/*! This function gracefully terminates the polarization processing module.  It must be called prior to unloading the
*   polarization processor component to ensure proper cleanup of platform resources.
*  
*   \returns A ::TL_POLARIZATION_PROCESSOR_ERROR value to indicate success or failure (::TL_POLARIZATION_PROCESSOR_ERROR_NONE indicates success).
*/
typedef int (*TL_POLARIZATION_PROCESSOR_MODULE_TERMINATE) (void);
