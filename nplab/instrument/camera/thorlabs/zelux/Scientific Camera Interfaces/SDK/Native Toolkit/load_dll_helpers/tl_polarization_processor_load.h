#pragma once

#include "tl_polarization_processor.h"

#ifdef __cplusplus
extern "C"
{
#endif

	/// <summary>
	/// Loads and initializes the polarization processing module.
	/// </summary>
	/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
	int tl_polarization_processor_initialize(void);

	/// <summary>
	/// Cleans up and terminates the polarization processor module.
	/// </summary>
	/// <returns>0 if successful or a positive integer error code to indicate failure.</returns>
	int tl_polarization_processor_terminate(void);

	extern TL_POLARIZATION_PROCESSOR_CREATE_POLARIZATION_PROCESSOR tl_polarization_processor_create_polarization_processor;
	extern TL_POLARIZATION_PROCESSOR_SET_CUSTOM_CALIBRATION_COEFFICIENTS tl_polarization_processor_set_custom_calibration_coefficients;
	extern TL_POLARIZATION_PROCESSOR_GET_CUSTOM_CALIBRATION_COEFFICIENTS tl_polarization_processor_get_custom_calibration_coefficients;
	extern TL_POLARIZATION_PROCESSOR_TRANSFORM tl_polarization_processor_transform;
	extern TL_POLARIZATION_PROCESSOR_DESTROY_POLARIZATION_PROCESSOR tl_polarization_processor_destroy_polarization_processor;

#ifdef __cplusplus
}
#endif