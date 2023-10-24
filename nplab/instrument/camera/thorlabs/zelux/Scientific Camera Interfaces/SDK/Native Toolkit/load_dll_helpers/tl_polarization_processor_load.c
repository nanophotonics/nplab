#include "tl_polarization_processor_load.h"
#include "tl_polarization_processor_enums.h"
#include "tl_polarization_processor_error.h"
#include <stdio.h>
#include <stdbool.h>

#ifndef THORLABS_TSI_BUILD_DLL

TL_POLARIZATION_PROCESSOR_CREATE_POLARIZATION_PROCESSOR tl_polarization_processor_create_polarization_processor;
TL_POLARIZATION_PROCESSOR_SET_CUSTOM_CALIBRATION_COEFFICIENTS tl_polarization_processor_set_custom_calibration_coefficients;
TL_POLARIZATION_PROCESSOR_GET_CUSTOM_CALIBRATION_COEFFICIENTS tl_polarization_processor_get_custom_calibration_coefficients;
TL_POLARIZATION_PROCESSOR_TRANSFORM tl_polarization_processor_transform;
TL_POLARIZATION_PROCESSOR_DESTROY_POLARIZATION_PROCESSOR tl_polarization_processor_destroy_polarization_processor;

static TL_POLARIZATION_PROCESSOR_MODULE_INITIALIZE tl_polarization_processor_module_initialize = 0;
static TL_POLARIZATION_PROCESSOR_MODULE_TERMINATE tl_polarization_processor_module_terminate = 0;

static bool is_sdk_open = false;

#ifdef _WIN32
#include "windows.h"
#endif

#ifdef __linux__
#include "dlfcn.h"
#endif

#ifdef _WIN32
static const char* polarization_processor_module_name = "thorlabs_tsi_polarization_processor.dll";
static HMODULE polarization_processor_obj = NULL;
#endif

#ifdef __linux__
static const char* polarization_processor_module_name = "libthorlabs_tsi_polarization_processor.so";
void* polarization_processor_obj = 0;
#endif

/// <summary>
///     Initializes the polarization_processor function pointers to 0.
/// </summary>
static void init_polarization_processor_function_pointers()
{
    tl_polarization_processor_create_polarization_processor = 0;
    tl_polarization_processor_set_custom_calibration_coefficients = 0;
    tl_polarization_processor_get_custom_calibration_coefficients = 0;
    tl_polarization_processor_transform = 0;
    tl_polarization_processor_destroy_polarization_processor = 0;
}

static int init_error_cleanup()
{
    is_sdk_open = false;
#ifdef _WIN32
    if (polarization_processor_obj != NULL)
    {
        FreeLibrary(polarization_processor_obj);
        polarization_processor_obj = NULL;
    }
#endif

#ifdef __linux__
    if (polarization_processor_obj != 0)
    {
        dlclose (polarization_processor_obj);
        polarization_processor_obj = 0;
    }
#endif
    init_polarization_processor_function_pointers();
    tl_polarization_processor_module_initialize = 0;
    tl_polarization_processor_module_terminate = 0;
    return (TL_POLARIZATION_PROCESSOR_ERROR_INITIALIZATION_ERROR);
}

/// <summary>
///     Loads the polarization processor module and maps all the functions so that they can be called directly.
/// </summary>
/// <returns>
///     TL_POLARIZATION_PROCESSOR_ERROR_INITIALIZATION_ERROR for error, TL_POLARIZATION_PROCESSOR_ERROR_NONE for success
/// </returns>
int tl_polarization_processor_initialize(void)
{
    // check to see if sdk is still open
    if(is_sdk_open)
    {
        return (TL_POLARIZATION_PROCESSOR_ERROR_INITIALIZATION_ERROR);
    }

    //printf("Entering tl_camera_sdk_dll_initialize");
    init_polarization_processor_function_pointers();

    // Platform specific code to get a handle to the SDK kernel module.
#ifdef _WIN32
    polarization_processor_obj = LoadLibraryA(polarization_processor_module_name);
#endif

#ifdef __linux__
    // First look in the current folder for the .so entry dll, then in the path (/usr/local/lib most likely).
    char local_path_to_library[2048];
    sprintf(local_path_to_library, "./%s", polarization_processor_module_name);
    polarization_processor_obj = dlopen(local_path_to_library, RTLD_LAZY);
    if (!polarization_processor_obj)
    {
        polarization_processor_obj = dlopen(polarization_processor_module_name, RTLD_LAZY);
    }
#endif
    if (!polarization_processor_obj)
    {
        return (init_error_cleanup());
    }

#ifdef _WIN32
    tl_polarization_processor_module_initialize = (TL_POLARIZATION_PROCESSOR_MODULE_INITIALIZE)(GetProcAddress(polarization_processor_obj, (char *) "tl_polarization_processor_module_initialize"));
#endif
#ifdef __linux__
    tl_polarization_processor_module_initialize = (TL_POLARIZATION_PROCESSOR_MODULE_INITIALIZE) (dlsym (polarization_processor_obj, "tl_polarization_processor_module_initialize"));
#endif
    if (!tl_polarization_processor_module_initialize)
    {
        return (init_error_cleanup());
    }

#ifdef _WIN32
    tl_polarization_processor_create_polarization_processor = (TL_POLARIZATION_PROCESSOR_CREATE_POLARIZATION_PROCESSOR)(GetProcAddress(polarization_processor_obj, (char *) "tl_polarization_processor_create_polarization_processor"));
#endif
#ifdef __linux__
    tl_polarization_processor_create_polarization_processor = (TL_POLARIZATION_PROCESSOR_CREATE_POLARIZATION_PROCESSOR) (dlsym (polarization_processor_obj, "tl_polarization_processor_create_polarization_processor"));
#endif
    if (!tl_polarization_processor_create_polarization_processor)
    {
        return (init_error_cleanup());
    }

#ifdef _WIN32
    tl_polarization_processor_set_custom_calibration_coefficients = (TL_POLARIZATION_PROCESSOR_SET_CUSTOM_CALIBRATION_COEFFICIENTS)(GetProcAddress(polarization_processor_obj, (char*)"tl_polarization_processor_set_custom_calibration_coefficients"));
#endif
#ifdef __linux__
    tl_polarization_processor_set_custom_calibration_coefficients = (TL_POLARIZATION_PROCESSOR_SET_CUSTOM_CALIBRATION_COEFFICIENTS)(dlsym(polarization_processor_obj, "tl_polarization_processor_set_custom_calibration_coefficients"));
#endif
    if (!tl_polarization_processor_set_custom_calibration_coefficients)
    {
        return (init_error_cleanup());
    }

#ifdef _WIN32
    tl_polarization_processor_get_custom_calibration_coefficients = (TL_POLARIZATION_PROCESSOR_GET_CUSTOM_CALIBRATION_COEFFICIENTS)(GetProcAddress(polarization_processor_obj, (char*)"tl_polarization_processor_get_custom_calibration_coefficients"));
#endif
#ifdef __linux__
    tl_polarization_processor_get_custom_calibration_coefficients = (TL_POLARIZATION_PROCESSOR_GET_CUSTOM_CALIBRATION_COEFFICIENTS)(dlsym(polarization_processor_obj, "tl_polarization_processor_get_custom_calibration_coefficients"));
#endif
    if (!tl_polarization_processor_get_custom_calibration_coefficients)
    {
        return (init_error_cleanup());
    }

#ifdef _WIN32
    tl_polarization_processor_transform = (TL_POLARIZATION_PROCESSOR_TRANSFORM)(GetProcAddress(polarization_processor_obj, (char*)"tl_polarization_processor_transform"));
#endif
#ifdef __linux__
    tl_polarization_processor_transform = (TL_POLARIZATION_PROCESSOR_TRANSFORM)(dlsym(polarization_processor_obj, "tl_polarization_processor_transform"));
#endif
    if (!tl_polarization_processor_transform)
    {
        return (init_error_cleanup());
    }

#ifdef _WIN32
    tl_polarization_processor_destroy_polarization_processor = (TL_POLARIZATION_PROCESSOR_DESTROY_POLARIZATION_PROCESSOR)(GetProcAddress(polarization_processor_obj, (char*)"tl_polarization_processor_destroy_polarization_processor"));
#endif
#ifdef __linux__
    tl_polarization_processor_destroy_polarization_processor = (TL_POLARIZATION_PROCESSOR_DESTROY_POLARIZATION_PROCESSOR)(dlsym(polarization_processor_obj, "tl_polarization_processor_destroy_polarization_processor"));
#endif
    if (!tl_polarization_processor_destroy_polarization_processor)
    {
        return (init_error_cleanup());
    }

#ifdef _WIN32
    tl_polarization_processor_module_terminate = (TL_POLARIZATION_PROCESSOR_MODULE_TERMINATE)(GetProcAddress(polarization_processor_obj, (char*) "tl_polarization_processor_module_terminate"));
#endif
#ifdef __linux__
    tl_polarization_processor_module_terminate = (TL_POLARIZATION_PROCESSOR_MODULE_TERMINATE) (dlsym (polarization_processor_obj, "tl_polarization_processor_module_terminate"));
#endif
    if (!tl_polarization_processor_module_terminate)
    {
        return (init_error_cleanup());
    }
#else
    // Linux specific stuff
#endif

    if (tl_polarization_processor_module_initialize() != TL_POLARIZATION_PROCESSOR_ERROR_NONE)
    {
#ifdef _WIN32
        if (polarization_processor_obj != NULL)
        {
            FreeLibrary(polarization_processor_obj);
            polarization_processor_obj = NULL;
        }
#else
        //Linux specific stuff
#endif
        return (init_error_cleanup());
    }

    is_sdk_open = true;
    return (TL_POLARIZATION_PROCESSOR_ERROR_NONE);
}

int tl_polarization_processor_terminate(void)
{
    int was_destruction_unclean = 0;
    if (tl_polarization_processor_module_terminate)
    {
        tl_polarization_processor_module_terminate();
    }
    else
    {
        was_destruction_unclean = 1;
    }

#ifdef _WIN32
    if (polarization_processor_obj)
    {
        FreeLibrary(polarization_processor_obj);
        polarization_processor_obj = NULL;
    }
    else
    {
        was_destruction_unclean = 1;
    }
#else
    //Linux specific stuff
#endif

    init_polarization_processor_function_pointers();
    tl_polarization_processor_module_initialize = 0;
    tl_polarization_processor_module_terminate = 0;

    is_sdk_open = false;

    if(was_destruction_unclean)
    {
        return(TL_POLARIZATION_PROCESSOR_ERROR_TERMINATION_ERROR);
    }
    return (was_destruction_unclean);
}
