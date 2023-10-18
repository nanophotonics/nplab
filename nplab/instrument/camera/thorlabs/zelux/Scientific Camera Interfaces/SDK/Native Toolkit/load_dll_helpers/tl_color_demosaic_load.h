#pragma once

#include "tl_color_demosaic.h"

#ifdef __cplusplus
extern "C"
{
#endif

	/// <summary>
	/// Loads and initializes the demosaic module.
	/// </summary>
	/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
	int tl_demosaic_initialize(void);

	/// <summary>
	/// Cleans up and terminates the demosaic module.
	/// </summary>
	/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
	int tl_demosaic_terminate(void);

	extern TL_DEMOSAIC_TRANSFORM_16_TO_48 tl_demosaic_transform_16_to_48;

#ifdef __cplusplus
}
#endif