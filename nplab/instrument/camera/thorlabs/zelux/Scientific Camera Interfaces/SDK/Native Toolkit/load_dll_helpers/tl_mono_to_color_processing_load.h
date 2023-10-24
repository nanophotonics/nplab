#pragma once

#include "tl_mono_to_color_processing.h"

#ifdef __cplusplus
extern "C"
{
#endif

	/// <summary>
	/// Loads and initializes the mono-to-color processing module.
	/// </summary>
	/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
	int tl_mono_to_color_processing_initialize(void);

	/// <summary>
	/// Cleans up and terminates the mono-to-color processing module.
	/// </summary>
	/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
	int tl_mono_to_color_processing_terminate(void);

	extern TL_MONO_TO_COLOR_CREATE_MONO_TO_COLOR_PROCESSOR tl_mono_to_color_create_mono_to_color_processor;
	extern TL_MONO_TO_COLOR_GET_COLOR_SPACE tl_mono_to_color_get_color_space;
	extern TL_MONO_TO_COLOR_SET_COLOR_SPACE tl_mono_to_color_set_color_space;
	extern TL_MONO_TO_COLOR_GET_OUTPUT_FORMAT tl_mono_to_color_get_output_format;
	extern TL_MONO_TO_COLOR_SET_OUTPUT_FORMAT tl_mono_to_color_set_output_format;
	extern TL_MONO_TO_COLOR_GET_RED_GAIN tl_mono_to_color_get_red_gain;
	extern TL_MONO_TO_COLOR_SET_RED_GAIN tl_mono_to_color_set_red_gain;
	extern TL_MONO_TO_COLOR_GET_BLUE_GAIN tl_mono_to_color_get_blue_gain;
	extern TL_MONO_TO_COLOR_SET_BLUE_GAIN tl_mono_to_color_set_blue_gain;
	extern TL_MONO_TO_COLOR_GET_GREEN_GAIN tl_mono_to_color_get_green_gain;
	extern TL_MONO_TO_COLOR_SET_GREEN_GAIN tl_mono_to_color_set_green_gain;
	extern TL_MONO_TO_COLOR_TRANSFORM_TO_48 tl_mono_to_color_transform_to_48;
	extern TL_MONO_TO_COLOR_TRANSFORM_TO_32 tl_mono_to_color_transform_to_32;
	extern TL_MONO_TO_COLOR_TRANSFORM_TO_24 tl_mono_to_color_transform_to_24;
	extern TL_MONO_TO_COLOR_GET_CAMERA_SENSOR_TYPE tl_mono_to_color_get_camera_sensor_type;
	extern TL_MONO_TO_COLOR_GET_COLOR_FILTER_ARRAY_PHASE tl_mono_to_color_get_color_filter_array_phase;
	extern TL_MONO_TO_COLOR_GET_COLOR_CORRECTION_MATRIX tl_mono_to_color_get_color_correction_matrix;
	extern TL_MONO_TO_COLOR_GET_DEFAULT_WHITE_BALANCE_MATRIX tl_mono_to_color_get_default_white_balance_matrix;
	extern TL_MONO_TO_COLOR_GET_BIT_DEPTH tl_mono_to_color_get_bit_depth;
	extern TL_MONO_TO_COLOR_DESTROY_MONO_TO_COLOR_PROCESSOR tl_mono_to_color_destroy_mono_to_color_processor;
	extern TL_MONO_TO_COLOR_GET_LAST_ERROR tl_mono_to_color_get_last_error;

#ifdef __cplusplus
}
#endif