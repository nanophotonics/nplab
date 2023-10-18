/******************************************************************************/
/* TSI_SDK.H                                                                  */
/*----------------------------------------------------------------------------*/
/* Copywrite, etc, blah blah blah                                             */
/******************************************************************************/
#ifndef __THORLABS_SCIENTIFIC_IMAGING_SOFTWARE_DEVELOPER_KIT_H__
#define __THORLABS_SCIENTIFIC_IMAGING_SOFTWARE_DEVELOPER_KIT_H__

/*! \mainpage Thorlabs Legacy SDK
*
* \section Getting Started
* This API can be used to interface with the legacy CCD cameras.
* This document is NOT the official API documentation.
*
*/

/// \file TsiSDK.h
/// \brief This file includes the declarations of all API functions and data structures in the main SDK interface.

#include "TsiError.h"
#include "platform_specific.h"

//------------------------------------------------------------------------------
// C++ SDK Class
//------------------------------------------------------------------------------
// Example: Below is a simple example to create a TsiSDK object.
//
// If you want to use the loader in the header file, you will need to 
// define TSI_ENABLE_LOADER, other wise you will need to LoadLibrary and
// GetProcAddress yourself.
//
//#define TSI_ENABLE_LOADER 1
//#include "TsiSDK.h"
//
//TsiSDK *sdk = 0;
//
//   sdk = get_tsi_sdk(0);
//   if(sdk == 0)
//   {
//      printf("***ERROR***: get_tsi_sdk() failed\n");
//   }
//
//------------------------------------------------------------------------------
#ifdef __cplusplus



class TsiCamera;
class TsiUtil;


//------------------------------------------------------------------------------
// TSI_ADDRESS_SELECT
//------------------------------------------------------------------------------
typedef enum  _TSI_ADDRESS_SELECT
{
   TSI_ADDRESS_SELECT_IP,
   TSI_ADDRESS_SELECT_MAC,
   TSI_ADDRESS_SELECT_ADAPTER_ID,
   TSI_ADDRESS_SELECT_USB_PORT_TYPE,
   TSI_ADDRESS_SELECT_MAX

} TSI_ADDRESS_SELECT;



//==============================================================================
// TsiSDK C++ Class
//------------------------------------------------------------------------------
//==============================================================================
class TsiSDK
{
   //---------------------------------------------------------------------------
   // PUBLIC
   //---------------------------------------------------------------------------
   public:

      virtual bool            Open               (void               );
      virtual bool            Close              (void               );

      virtual int             GetNumberOfCameras        (void              );
      virtual TsiCamera      *GetCamera                 (int camera_number );
      virtual char           *GetCameraInterfaceTypeStr (int camera_number );
      virtual char           *GetCameraAddressStr       (int camera_number, TSI_ADDRESS_SELECT address_select);
      virtual char           *GetCameraName             (int camera_number );
      virtual char           *GetCameraSerialNumStr     (int camera_number );

      virtual uint64_t        ElapsedTime        (uint64_t start_time);

      virtual char           *GetLastErrorStr    (void                                       );
      virtual TSI_ERROR_CODE  GetErrorCode       (void                                       );
      virtual bool            ClearError         (void                                       );
      virtual bool            GetErrorStr        (TSI_ERROR_CODE code, char *str, int &str_len);

      virtual TsiUtil        *GetUtilityObject   (void);



   //---------------------------------------------------------------------------
   // Protected
   //---------------------------------------------------------------------------
   protected:
               TsiSDK (void);
      virtual ~TsiSDK (void);
};


//------------------------------------------------------------------------------
// Exported function prototype typedefs.
//------------------------------------------------------------------------------
typedef TsiSDK *(*TSI_CREATE_SDK     )(void    );      // Create a TsiSDK object.
typedef void    (*TSI_DESTROY_SDK    )(TsiSDK *);      // Destroy a TsiSDK object.
typedef char   *(*TSI_GET_VERSION_STR)(void    );      // Get version string.

typedef int     (*TSI_SET_CAMERA_CONNECT_CALLBACK)(void (*cb)(int event, int cam_index, char *name, char *serial_num, char *bus_str, void*), void *); 


//------------------------------------------------------------------------------
// [TSI_ENABLE_LOADER - DLL runtime linking code]
//
// #define TSI_ENABLE_LOADER to use.
//------------------------------------------------------------------------------
#if defined(TSI_ENABLE_LOADER)       
#if defined(_MSC_VER)                
#include <windows.h>
static HMODULE _tsi_dll_handle = 0;

//------------------------------------------------------------------------------
// get_tsi_sdk
//------------------------------------------------------------------------------
static TsiSDK *get_tsi_sdk(char *path)
{
TsiSDK        *tsi_sdk        = 0;
TSI_CREATE_SDK tsi_create_sdk = 0;

   _tsi_dll_handle = LoadLibraryA("thorlabs_ccd_tsi_sdk.dll"); 
   if(_tsi_dll_handle == 0)  return tsi_sdk; 

   tsi_create_sdk = (TSI_CREATE_SDK)GetProcAddress(_tsi_dll_handle, "tsi_create_sdk");
   if(tsi_create_sdk == 0)
   {
      FreeLibrary(_tsi_dll_handle);
      _tsi_dll_handle = 0;
      return tsi_sdk;
   }

   tsi_sdk = tsi_create_sdk();

   return tsi_sdk; 
}

//------------------------------------------------------------------------------
// release_tsi_sdk
//------------------------------------------------------------------------------
static void release_tsi_sdk(TsiSDK *tsi_sdk)
{
TSI_DESTROY_SDK tsi_destroy_sdk = 0;

   if(_tsi_dll_handle != 0)
   {
      tsi_destroy_sdk = (TSI_DESTROY_SDK)GetProcAddress(_tsi_dll_handle, "tsi_destroy_sdk");
      if(tsi_destroy_sdk != 0)
      {
         tsi_destroy_sdk(tsi_sdk);
      }

      FreeLibrary(_tsi_dll_handle);
      _tsi_dll_handle = 0;
   }
}



//------------------------------------------------------------------------------
// get_version_str
//------------------------------------------------------------------------------
static char *get_version_str(void)
{
char               *str             = 0;
TSI_GET_VERSION_STR get_version_str = 0;

   if(_tsi_dll_handle != 0)
   {
      get_version_str = (TSI_GET_VERSION_STR)GetProcAddress(_tsi_dll_handle, "get_version_str");
      if(get_version_str != 0)
      {
         str = get_version_str();
      }
   }

   return str;
}


//------------------------------------------------------------------------------
// set_camera_connect_callback
//------------------------------------------------------------------------------
// Whenever a camera is connected to the host, or disconnect from the host,
// the SDK will send a message via the callback.
//------------------------------------------------------------------------------
#define EVENT_ID_CONNECT    1
#define EVENT_ID_DISCONNECT 2
static int set_camera_connect_callback(void (*cb)(int event_id, int index, char *name, char *serial_num, char *bus_str, void *ctx), void *ctx)
{
int status = 0;
TSI_SET_CAMERA_CONNECT_CALLBACK set_camera_connect_callback = 0;

   if(_tsi_dll_handle != 0)
   {
      set_camera_connect_callback = (TSI_SET_CAMERA_CONNECT_CALLBACK)GetProcAddress(_tsi_dll_handle, "tsi_set_camera_connect_callback");
      if(set_camera_connect_callback != 0)
      {
         status = set_camera_connect_callback(cb, ctx);
      }
   }

   return status;
}

#endif // _MSC_VER
#endif // TSI_ENABLE_LOADER
#endif // __cplusplus


#endif
