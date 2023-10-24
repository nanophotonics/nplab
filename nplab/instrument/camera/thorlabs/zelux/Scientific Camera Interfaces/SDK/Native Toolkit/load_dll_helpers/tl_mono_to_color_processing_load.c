#include "tl_mono_to_color_processing_load.h"
#include "tl_mono_to_color_enum.h"
#include <stdbool.h>
#include <stdio.h>

#ifndef THORLABS_TSI_BUILD_DLL

TL_MONO_TO_COLOR_CREATE_MONO_TO_COLOR_PROCESSOR tl_mono_to_color_create_mono_to_color_processor;
TL_MONO_TO_COLOR_GET_COLOR_SPACE tl_mono_to_color_get_color_space;
TL_MONO_TO_COLOR_SET_COLOR_SPACE tl_mono_to_color_set_color_space;
TL_MONO_TO_COLOR_GET_OUTPUT_FORMAT tl_mono_to_color_get_output_format;
TL_MONO_TO_COLOR_SET_OUTPUT_FORMAT tl_mono_to_color_set_output_format;
TL_MONO_TO_COLOR_GET_RED_GAIN tl_mono_to_color_get_red_gain;
TL_MONO_TO_COLOR_SET_RED_GAIN tl_mono_to_color_set_red_gain;
TL_MONO_TO_COLOR_GET_BLUE_GAIN tl_mono_to_color_get_blue_gain;
TL_MONO_TO_COLOR_SET_BLUE_GAIN tl_mono_to_color_set_blue_gain;
TL_MONO_TO_COLOR_GET_GREEN_GAIN tl_mono_to_color_get_green_gain;
TL_MONO_TO_COLOR_SET_GREEN_GAIN tl_mono_to_color_set_green_gain;
TL_MONO_TO_COLOR_TRANSFORM_TO_48 tl_mono_to_color_transform_to_48;
TL_MONO_TO_COLOR_TRANSFORM_TO_32 tl_mono_to_color_transform_to_32;
TL_MONO_TO_COLOR_TRANSFORM_TO_24 tl_mono_to_color_transform_to_24;
TL_MONO_TO_COLOR_GET_CAMERA_SENSOR_TYPE tl_mono_to_color_get_camera_sensor_type;
TL_MONO_TO_COLOR_GET_COLOR_FILTER_ARRAY_PHASE tl_mono_to_color_get_color_filter_array_phase;
TL_MONO_TO_COLOR_GET_COLOR_CORRECTION_MATRIX tl_mono_to_color_get_color_correction_matrix;
TL_MONO_TO_COLOR_GET_DEFAULT_WHITE_BALANCE_MATRIX tl_mono_to_color_get_default_white_balance_matrix;
TL_MONO_TO_COLOR_GET_BIT_DEPTH tl_mono_to_color_get_bit_depth;
TL_MONO_TO_COLOR_GET_LAST_ERROR tl_mono_to_color_get_last_error;
TL_MONO_TO_COLOR_DESTROY_MONO_TO_COLOR_PROCESSOR tl_mono_to_color_destroy_mono_to_color_processor;

static TL_MONO_TO_COLOR_PROCESSING_MODULE_INITIALIZE tl_mono_to_color_processing_module_initialize = 0;
static TL_MONO_TO_COLOR_PROCESSING_MODULE_TERMINATE tl_mono_to_color_processing_module_terminate = 0;

static bool is_sdk_open = false;

#ifdef _WIN32
#include "windows.h"
#endif

#ifdef __linux__
#include "dlfcn.h"
#endif

#ifdef _WIN32
static const char* mono_to_color_processing_module_name = "thorlabs_tsi_mono_to_color_processing.dll";
static HMODULE mono_to_color_processing_obj = NULL;
#endif

#ifdef __linux__
static const char* mono_to_color_processing_module_name = "libthorlabs_tsi_mono_to_color_processing.so";
void* mono_to_color_processing_obj = 0;
#endif

/// <summary>
///     Initializes the mono_to_color_processing function pointers to 0.
/// </summary>
static void init_mono_to_color_processing_function_pointers()
{
	tl_mono_to_color_create_mono_to_color_processor = 0;
	tl_mono_to_color_get_color_space = 0;
	tl_mono_to_color_set_color_space = 0;
	tl_mono_to_color_get_output_format = 0;
	tl_mono_to_color_set_output_format = 0;
	tl_mono_to_color_get_red_gain = 0;
	tl_mono_to_color_set_red_gain = 0;
	tl_mono_to_color_get_blue_gain = 0;
	tl_mono_to_color_set_blue_gain = 0;
	tl_mono_to_color_get_green_gain = 0;
	tl_mono_to_color_set_green_gain = 0;
	tl_mono_to_color_transform_to_48 = 0;
	tl_mono_to_color_transform_to_32 = 0;
	tl_mono_to_color_transform_to_24 = 0;
	tl_mono_to_color_get_camera_sensor_type = 0;
	tl_mono_to_color_get_color_filter_array_phase = 0;
	tl_mono_to_color_get_color_correction_matrix = 0;
	tl_mono_to_color_get_default_white_balance_matrix = 0;
	tl_mono_to_color_get_last_error = 0;
	tl_mono_to_color_destroy_mono_to_color_processor = 0;
}

static int init_error_cleanup()
{
	is_sdk_open = false;
#ifdef _WIN32
	if (mono_to_color_processing_obj != NULL)
	{
		FreeLibrary(mono_to_color_processing_obj);
		mono_to_color_processing_obj = NULL;
	}
#endif

#ifdef __linux__
    if (mono_to_color_processing_obj != 0)
    {
        dlclose (mono_to_color_processing_obj);
        mono_to_color_processing_obj = 0;
    }
#endif
	init_mono_to_color_processing_function_pointers();
	tl_mono_to_color_processing_module_initialize = 0;
	tl_mono_to_color_processing_module_terminate = 0;
	return (TL_MONO_TO_COLOR_ERROR_INITIALIZATION_ERROR);
}

/// <summary>
///     Loads the color processing module and maps all the functions so that they can be called directly.
/// </summary>
/// <returns>
///     TL_MONO_TO_COLOR_ERROR_INITIALIZATION_ERROR for error, TL_MONO_TO_COLOR_ERROR_NONE for success
/// </returns>
int tl_mono_to_color_processing_initialize(void)
{
	// check to see if sdk is still open
	if(is_sdk_open)
	{
		return (TL_MONO_TO_COLOR_ERROR_INITIALIZATION_ERROR);
	}

	//printf("Entering tl_camera_sdk_dll_initialize");
	init_mono_to_color_processing_function_pointers();

	// Platform specific code to get a handle to the SDK kernel module.
#ifdef _WIN32
	mono_to_color_processing_obj = LoadLibraryA(mono_to_color_processing_module_name);
#endif

#ifdef __linux__
	// First look in the current folder for the .so entry dll, then in the path (/usr/local/lib most likely).
	char local_path_to_library[2048];
	sprintf(local_path_to_library, "./%s", mono_to_color_processing_module_name);
    mono_to_color_processing_obj = dlopen (local_path_to_library, RTLD_LAZY);
	if (!mono_to_color_processing_obj)
	{
		mono_to_color_processing_obj = dlopen(mono_to_color_processing_module_name, RTLD_LAZY);
	}
#endif
	if (!mono_to_color_processing_obj)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_processing_module_initialize = (TL_MONO_TO_COLOR_PROCESSING_MODULE_INITIALIZE)(GetProcAddress(mono_to_color_processing_obj, (char *) "tl_mono_to_color_processing_module_initialize"));
#endif
#ifdef __linux__
    tl_mono_to_color_processing_module_initialize = (TL_MONO_TO_COLOR_PROCESSING_MODULE_INITIALIZE) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_processing_module_initialize"));
#endif
	if (!tl_mono_to_color_processing_module_initialize)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_create_mono_to_color_processor = (TL_MONO_TO_COLOR_CREATE_MONO_TO_COLOR_PROCESSOR)(GetProcAddress(mono_to_color_processing_obj, (char *) "tl_mono_to_color_create_mono_to_color_processor"));
#endif
#ifdef __linux__
    tl_mono_to_color_create_mono_to_color_processor = (TL_MONO_TO_COLOR_CREATE_MONO_TO_COLOR_PROCESSOR) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_create_mono_to_color_processor"));
#endif
	if (!tl_mono_to_color_create_mono_to_color_processor)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_get_color_space = (TL_MONO_TO_COLOR_GET_COLOR_SPACE)(GetProcAddress(mono_to_color_processing_obj, (char *) "tl_mono_to_color_get_color_space"));
#endif
#ifdef __linux__
    tl_mono_to_color_get_color_space = (TL_MONO_TO_COLOR_GET_COLOR_SPACE) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_get_color_space"));
#endif
	if(!tl_mono_to_color_get_color_space)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_set_color_space = (TL_MONO_TO_COLOR_SET_COLOR_SPACE)(GetProcAddress(mono_to_color_processing_obj, (char *) "tl_mono_to_color_set_color_space"));
#endif
#ifdef __linux__
    tl_mono_to_color_set_color_space = (TL_MONO_TO_COLOR_SET_COLOR_SPACE) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_set_color_space"));
#endif
	if(!tl_mono_to_color_set_color_space)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_get_output_format = (TL_MONO_TO_COLOR_GET_OUTPUT_FORMAT)(GetProcAddress(mono_to_color_processing_obj, (char *) "tl_mono_to_color_get_output_format"));
#endif
#ifdef __linux__
    tl_mono_to_color_get_output_format = (TL_MONO_TO_COLOR_GET_OUTPUT_FORMAT) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_get_output_format"));
#endif
	if (!tl_mono_to_color_get_output_format)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_set_output_format = (TL_MONO_TO_COLOR_SET_OUTPUT_FORMAT)(GetProcAddress(mono_to_color_processing_obj, (char *) "tl_mono_to_color_set_output_format"));
#endif
#ifdef __linux__
    tl_mono_to_color_set_output_format = (TL_MONO_TO_COLOR_SET_OUTPUT_FORMAT) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_set_output_format"));
#endif
	if (!tl_mono_to_color_set_output_format)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_get_red_gain = (TL_MONO_TO_COLOR_GET_RED_GAIN)(GetProcAddress(mono_to_color_processing_obj, (char *) "tl_mono_to_color_get_red_gain"));
#endif
#ifdef __linux__
    tl_mono_to_color_get_red_gain = (TL_MONO_TO_COLOR_GET_RED_GAIN) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_get_red_gain"));
#endif
	if (!tl_mono_to_color_get_red_gain)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_set_red_gain = (TL_MONO_TO_COLOR_SET_RED_GAIN)(GetProcAddress(mono_to_color_processing_obj, (char *) "tl_mono_to_color_set_red_gain"));
#endif
#ifdef __linux__
    tl_mono_to_color_set_red_gain = (TL_MONO_TO_COLOR_SET_RED_GAIN) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_set_red_gain"));
#endif
	if (!tl_mono_to_color_set_red_gain)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_get_blue_gain = (TL_MONO_TO_COLOR_GET_BLUE_GAIN)(GetProcAddress(mono_to_color_processing_obj, (char *) "tl_mono_to_color_get_blue_gain"));
#endif
#ifdef __linux__
    tl_mono_to_color_get_blue_gain = (TL_MONO_TO_COLOR_GET_BLUE_GAIN) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_get_blue_gain"));
#endif
	if (!tl_mono_to_color_get_blue_gain)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_set_blue_gain = (TL_MONO_TO_COLOR_SET_BLUE_GAIN)(GetProcAddress(mono_to_color_processing_obj, (char *) "tl_mono_to_color_set_blue_gain"));
#endif
#ifdef __linux__
    tl_mono_to_color_set_blue_gain = (TL_MONO_TO_COLOR_SET_BLUE_GAIN) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_set_blue_gain"));
#endif
	if (!tl_mono_to_color_set_blue_gain)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_get_green_gain = (TL_MONO_TO_COLOR_GET_GREEN_GAIN)(GetProcAddress(mono_to_color_processing_obj, (char *) "tl_mono_to_color_get_green_gain"));
#endif
#ifdef __linux__
    tl_mono_to_color_get_green_gain = (TL_MONO_TO_COLOR_GET_GREEN_GAIN) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_get_green_gain"));
#endif
	if (!tl_mono_to_color_get_green_gain)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_set_green_gain = (TL_MONO_TO_COLOR_SET_GREEN_GAIN)(GetProcAddress(mono_to_color_processing_obj, (char *) "tl_mono_to_color_set_green_gain"));
#endif
#ifdef __linux__
    tl_mono_to_color_set_green_gain = (TL_MONO_TO_COLOR_SET_GREEN_GAIN) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_set_green_gain"));
#endif
	if (!tl_mono_to_color_set_green_gain)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_transform_to_48 = (TL_MONO_TO_COLOR_TRANSFORM_TO_48)(GetProcAddress(mono_to_color_processing_obj, (char *) "tl_mono_to_color_transform_to_48"));
#endif
#ifdef __linux__
    tl_mono_to_color_transform_to_48 = (TL_MONO_TO_COLOR_TRANSFORM_TO_48) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_transform_to_48"));
#endif
	if (!tl_mono_to_color_transform_to_48)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_transform_to_32 = (TL_MONO_TO_COLOR_TRANSFORM_TO_32)(GetProcAddress(mono_to_color_processing_obj, (char *) "tl_mono_to_color_transform_to_32"));
#endif
#ifdef __linux__
    tl_mono_to_color_transform_to_32 = (TL_MONO_TO_COLOR_TRANSFORM_TO_32) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_transform_to_32"));
#endif
	if (!tl_mono_to_color_transform_to_32)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_transform_to_24 = (TL_MONO_TO_COLOR_TRANSFORM_TO_24)(GetProcAddress(mono_to_color_processing_obj, (char *) "tl_mono_to_color_transform_to_24"));
#endif
#ifdef __linux__
    tl_mono_to_color_transform_to_24 = (TL_MONO_TO_COLOR_TRANSFORM_TO_24) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_transform_to_24"));
#endif
	if (!tl_mono_to_color_transform_to_24)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_get_camera_sensor_type = (TL_MONO_TO_COLOR_GET_CAMERA_SENSOR_TYPE)(GetProcAddress(mono_to_color_processing_obj, (char *) "tl_mono_to_color_get_camera_sensor_type"));
#endif
#ifdef __linux__
    tl_mono_to_color_get_camera_sensor_type = (TL_MONO_TO_COLOR_GET_CAMERA_SENSOR_TYPE) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_get_camera_sensor_type"));
#endif
	if (!tl_mono_to_color_get_camera_sensor_type)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_get_color_filter_array_phase = (TL_MONO_TO_COLOR_GET_COLOR_FILTER_ARRAY_PHASE)(GetProcAddress(mono_to_color_processing_obj, (char *) "tl_mono_to_color_get_color_filter_array_phase"));
#endif
#ifdef __linux__
    tl_mono_to_color_get_color_filter_array_phase = (TL_MONO_TO_COLOR_GET_COLOR_FILTER_ARRAY_PHASE) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_get_color_filter_array_phase"));
#endif
	if (!tl_mono_to_color_get_color_filter_array_phase)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_get_color_correction_matrix = (TL_MONO_TO_COLOR_GET_COLOR_CORRECTION_MATRIX)(GetProcAddress(mono_to_color_processing_obj, (char *) "tl_mono_to_color_get_color_correction_matrix"));
#endif
#ifdef __linux__
    tl_mono_to_color_get_color_correction_matrix = (TL_MONO_TO_COLOR_GET_COLOR_CORRECTION_MATRIX) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_get_color_correction_matrix"));
#endif
	if (!tl_mono_to_color_get_color_correction_matrix)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_get_default_white_balance_matrix = (TL_MONO_TO_COLOR_GET_DEFAULT_WHITE_BALANCE_MATRIX)(GetProcAddress(mono_to_color_processing_obj, (char *) "tl_mono_to_color_get_default_white_balance_matrix"));
#endif
#ifdef __linux__
    tl_mono_to_color_get_default_white_balance_matrix = (TL_MONO_TO_COLOR_GET_DEFAULT_WHITE_BALANCE_MATRIX) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_get_default_white_balance_matrix"));
#endif
	if (!tl_mono_to_color_get_default_white_balance_matrix)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_get_bit_depth = (TL_MONO_TO_COLOR_GET_BIT_DEPTH)(GetProcAddress(mono_to_color_processing_obj, (char *) "tl_mono_to_color_get_bit_depth"));
#endif
#ifdef __linux__
    tl_mono_to_color_get_bit_depth = (TL_MONO_TO_COLOR_GET_BIT_DEPTH) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_get_bit_depth"));
#endif
	if (!tl_mono_to_color_get_bit_depth)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_destroy_mono_to_color_processor = (TL_MONO_TO_COLOR_DESTROY_MONO_TO_COLOR_PROCESSOR)(GetProcAddress(mono_to_color_processing_obj, (char*) "tl_mono_to_color_destroy_mono_to_color_processor"));
#endif
#ifdef __linux__
    tl_mono_to_color_destroy_mono_to_color_processor = (TL_MONO_TO_COLOR_DESTROY_MONO_TO_COLOR_PROCESSOR) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_destroy_mono_to_color_processor"));
#endif
	if (!tl_mono_to_color_destroy_mono_to_color_processor)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_get_last_error = (TL_MONO_TO_COLOR_GET_LAST_ERROR)(GetProcAddress(mono_to_color_processing_obj, (char*) "tl_mono_to_color_get_last_error"));
#endif
#ifdef __linux__
    tl_mono_to_color_get_last_error = (TL_MONO_TO_COLOR_GET_LAST_ERROR) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_get_last_error"));
#endif
	if(!tl_mono_to_color_get_last_error)
	{
		return (init_error_cleanup());
	}

#ifdef _WIN32
	tl_mono_to_color_processing_module_terminate = (TL_MONO_TO_COLOR_PROCESSING_MODULE_TERMINATE)(GetProcAddress(mono_to_color_processing_obj, (char*) "tl_mono_to_color_processing_module_terminate"));
#endif
#ifdef __linux__
    tl_mono_to_color_processing_module_terminate = (TL_MONO_TO_COLOR_PROCESSING_MODULE_TERMINATE) (dlsym (mono_to_color_processing_obj, "tl_mono_to_color_processing_module_terminate"));
#endif
	if (!tl_mono_to_color_processing_module_terminate)
	{
		return (init_error_cleanup());
	}
#else
	// Linux specific stuff
#endif

	if (tl_mono_to_color_processing_module_initialize() != TL_MONO_TO_COLOR_ERROR_NONE)
	{
#ifdef _WIN32
		if (mono_to_color_processing_obj != NULL)
		{
			FreeLibrary(mono_to_color_processing_obj);
			mono_to_color_processing_obj = NULL;
		}
#else
		//Linux specific stuff
#endif
		return (init_error_cleanup());
	}

	is_sdk_open = true;
	return (TL_MONO_TO_COLOR_ERROR_NONE);
}

int tl_mono_to_color_processing_terminate(void)
{
	int was_destruction_unclean = 0;
	if (tl_mono_to_color_processing_module_terminate)
	{
		tl_mono_to_color_processing_module_terminate();
	}
	else
	{
		was_destruction_unclean = 1;
	}

#ifdef _WIN32
	if (mono_to_color_processing_obj)
	{
		FreeLibrary(mono_to_color_processing_obj);
		mono_to_color_processing_obj = NULL;
	}
	else
	{
		was_destruction_unclean = 1;
	}
#else
	//Linux specific stuff
#endif

	init_mono_to_color_processing_function_pointers();
	tl_mono_to_color_processing_module_initialize = 0;
	tl_mono_to_color_processing_module_terminate = 0;

	is_sdk_open = false;

	if(was_destruction_unclean)
	{
		return(TL_MONO_TO_COLOR_ERROR_TERMINATION_ERROR);
	}
	return (was_destruction_unclean);
}
