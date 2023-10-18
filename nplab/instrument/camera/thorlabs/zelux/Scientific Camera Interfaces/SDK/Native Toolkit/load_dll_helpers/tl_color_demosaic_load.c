#include "tl_color_demosaic_load.h"
#include <stdio.h>

#ifndef THORLABS_TSI_BUILD_DLL

TL_DEMOSAIC_TRANSFORM_16_TO_48 tl_demosaic_transform_16_to_48;

static void* demosaic_handle = 0;

static TL_DEMOSAIC_MODULE_INITIALIZE tl_demosaic_module_initialize = 0;
static TL_DEMOSAIC_MODULE_TERMINATE tl_demosaic_module_terminate = 0;

#ifdef _WIN32
#include "windows.h"
#endif

#ifdef __linux__
#include "dlfcn.h"
#endif

#ifdef _WIN32
static const char* DEMOSAIC_MODULE_NAME = "thorlabs_tsi_demosaic.dll";
static HMODULE demosaic_obj = NULL;
#endif
#ifdef __linux__
static const char* DEMOSAIC_MODULE_NAME = "libthorlabs_tsi_demosaic.so";
void* demosaic_obj = 0;
#endif

/// <summary>
///     Initializes the demosaic function pointers to 0.
/// </summary>
static void init_demosaic_function_pointers()
{
    tl_demosaic_transform_16_to_48 = 0;
}

static int init_error_cleanup()
{
    #ifdef _WIN32
        if (demosaic_obj != NULL)
        {
            FreeLibrary(demosaic_obj);
            demosaic_obj = NULL;
        }
    #endif
    #ifdef __linux__
        if (demosaic_obj != 0)
        {
            dlclose (demosaic_obj);
            demosaic_obj = 0;
        }
    #endif
    init_demosaic_function_pointers();
    tl_demosaic_module_initialize = 0;
    tl_demosaic_module_terminate = 0;
    return (1);
}

/// <summary>
///     Loads the demosaic module and maps all the functions so that they can be called directly.
/// </summary>
/// <returns>
///     1 for error, 0 for success
/// </returns>
int tl_demosaic_initialize(void)
{
    //printf("Entering tl_camera_sdk_dll_initialize");
    init_demosaic_function_pointers();

    // Platform specific code to get a handle to the SDK kernel module.
#ifdef _WIN32
    demosaic_obj = LoadLibraryA (DEMOSAIC_MODULE_NAME);
#endif
#ifdef __linux__
    // First look in the current folder for the .so entry dll, then in the path (/usr/local/lib most likely).
    char local_path_to_library[2048];
    sprintf(local_path_to_library, "./%s", DEMOSAIC_MODULE_NAME);
    demosaic_obj = dlopen(local_path_to_library, RTLD_LAZY);
    if (!demosaic_obj)
    {
        demosaic_obj = dlopen(DEMOSAIC_MODULE_NAME, RTLD_LAZY);
    }
#endif
    if (!demosaic_obj)
    {
        return (init_error_cleanup());
    }

#ifdef _WIN32
    tl_demosaic_module_initialize = (TL_DEMOSAIC_MODULE_INITIALIZE)(GetProcAddress(demosaic_obj, (char*) "tl_demosaic_module_initialize"));
#endif
#ifdef __linux__
    tl_demosaic_module_initialize = (TL_DEMOSAIC_MODULE_INITIALIZE) (dlsym (demosaic_obj, "tl_demosaic_module_initialize"));
#endif
    if (!tl_demosaic_module_initialize)
    {
        return (init_error_cleanup());
    }

#ifdef _WIN32
    tl_demosaic_transform_16_to_48 = (TL_DEMOSAIC_TRANSFORM_16_TO_48)(GetProcAddress(demosaic_obj, (char*) "tl_demosaic_transform_16_to_48"));
#endif
#ifdef __linux__
    tl_demosaic_transform_16_to_48 = (TL_DEMOSAIC_TRANSFORM_16_TO_48) (dlsym (demosaic_obj, "tl_demosaic_transform_16_to_48"));
#endif
    if (!tl_demosaic_module_initialize)
    {
        return (init_error_cleanup());
    }

#ifdef _WIN32
    tl_demosaic_module_terminate = (TL_DEMOSAIC_MODULE_TERMINATE)(GetProcAddress(demosaic_obj, (char*) "tl_demosaic_module_terminate"));
#endif
#ifdef __linux__
    tl_demosaic_module_terminate = (TL_DEMOSAIC_MODULE_TERMINATE) (dlsym (demosaic_obj, "tl_demosaic_module_terminate"));
#endif
    if (!tl_demosaic_module_terminate)
    {
        return (init_error_cleanup());
    }

    if (tl_demosaic_module_initialize())
    {
#ifdef _WIN32
        if (demosaic_obj != NULL)
        {
            FreeLibrary(demosaic_obj);
            demosaic_obj = NULL;
        }
#endif
#ifdef __linux__
        if (demosaic_obj != 0)
        {
            dlclose(demosaic_obj);
            demosaic_obj = 0;
        }
#endif
        return (init_error_cleanup());
    }

    return (0);
}

int tl_demosaic_terminate(void)
{
    if (tl_demosaic_module_terminate)
    {
        tl_demosaic_module_terminate();
    }

#ifdef _WIN32
    if (demosaic_obj != NULL)
    {
        FreeLibrary(demosaic_obj);
        demosaic_obj = NULL;
    }
#endif
#ifdef __linux__
    if (demosaic_obj != 0)
    {
        dlclose(demosaic_obj);
        demosaic_obj = 0;
    }
#endif

    init_demosaic_function_pointers();
    return (0);
}

#endif
