#pragma once

#include "tl_color_processing.h"

#ifdef __cplusplus
extern "C"
{
#endif

	/// <summary>
	/// Loads and initializes the color processing module.
	/// </summary>
	/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
	int tl_color_processing_initialize(void);

	/// <summary>
	/// Cleans up and terminates the color processing module.
	/// </summary>
	/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
	int tl_color_processing_terminate(void);

	extern TL_COLOR_CREATE_COLOR_PROCESSOR tl_color_create_color_processor;
	extern TL_COLOR_GET_BLUE_INPUT_LUT tl_color_get_blue_input_LUT;
	extern TL_COLOR_GET_GREEN_INPUT_LUT tl_color_get_green_input_LUT;
	extern TL_COLOR_GET_RED_INPUT_LUT tl_color_get_red_input_LUT;
	extern TL_COLOR_ENABLE_INPUT_LUTS tl_color_enable_input_LUTs;
	extern TL_COLOR_APPEND_MATRIX tl_color_append_matrix;
	extern TL_COLOR_CLEAR_MATRIX tl_color_clear_matrix;
	extern TL_COLOR_GET_BLUE_OUTPUT_LUT tl_color_get_blue_output_LUT;
	extern TL_COLOR_GET_GREEN_OUTPUT_LUT tl_color_get_green_output_LUT;
	extern TL_COLOR_GET_RED_OUTPUT_LUT tl_color_get_red_output_LUT;
	extern TL_COLOR_ENABLE_OUTPUT_LUTS tl_color_enable_output_LUTs;
	extern TL_COLOR_TRANSFORM_48_TO_48 tl_color_transform_48_to_48;
    extern TL_COLOR_TRANSFORM_48_TO_64 tl_color_transform_48_to_64;
	extern TL_COLOR_TRANSFORM_48_TO_32 tl_color_transform_48_to_32;
	extern TL_COLOR_TRANSFORM_48_TO_24 tl_color_transform_48_to_24;
	extern TL_COLOR_DESTROY_COLOR_PROCESSOR tl_color_destroy_color_processor;

	double sRGBCompand(double colorPixelIntensity);

	void sRGB_companding_LUT(int bit_depth, int* lut);

#ifdef __cplusplus
}
#endif