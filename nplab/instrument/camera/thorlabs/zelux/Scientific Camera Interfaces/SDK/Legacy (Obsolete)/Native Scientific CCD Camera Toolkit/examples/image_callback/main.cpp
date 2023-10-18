#include <stdio.h>
#include <windows.h>

#include "TsiSDK.h"
#include "TsiCamera.h"
#include "TsiImage.h"



static HMODULE    _tsi_dll_handle = 0;
static TsiImage  *_tsi_image      = 0;


static int load_tsi_sdk   (TsiSDK **tsi_sdk);
static int unload_tsi_sdk (TsiSDK  *tsi_sdk);


typedef void (__cdecl *TSI_FUNCTION_IMAGE_NOTIFICATION_CALLBACK) (int  notification,   void *context);

//==============================================================================
// image_notification_callback
//------------------------------------------------------------------------------
//==============================================================================
static void __cdecl image_notification_callback(int event_id, void *context)
{
TsiCamera *tsi_camera = (TsiCamera *)context;

   if(tsi_camera == 0) return;


   if(event_id == TSI_IMAGE_NOTIFICATION_PENDING_IMAGE)
   {
      _tsi_image = tsi_camera->GetPendingImage(); 
   }

   return;
}


//==============================================================================
// Main
//------------------------------------------------------------------------------
//==============================================================================
int main(int argc, char *argv[])
{
TsiSDK    *tsi_sdk    = 0;
TsiCamera *tsi_camera = 0;
int        success;
int        num_cameras;
bool       status;

   printf("tsi_test - tsi_sdk test application.\n");

   //---------------------------------------------------------------------------
   // Load the thorlabs_ccd_tsi_sdk.dll and get the tsi_create_sdk() function.
   success = load_tsi_sdk(&tsi_sdk);
   if(success == 0)
   {
      printf("load_tsi_sdk() failed\n");
      return 0;
   }

   if(tsi_sdk == 0)
   {
      printf("tsi_sdk is 0\n");
      return 0;
   }

   //---------------------------------------------------------------------------
   // Open the SDK.
   status = tsi_sdk->Open();
   if(status == false)
   {
      printf("***ERROR***: TsiSDK::Open() failed\n");
      unload_tsi_sdk(tsi_sdk);
      tsi_sdk = 0;
      return 0;
   }

   //---------------------------------------------------------------------------
   // Call GetNumberOfCameras(), this will load up the different interface DLLs
   // such as thorlabs_ccd_pleora_ebus.dll and thorlabs_ccd_edt_camera_link.dll and invoke discovery on
   // each one.
   num_cameras = tsi_sdk->GetNumberOfCameras();
   printf("discovered %d cameras\n", num_cameras);
   if(num_cameras != 0)
   {
      tsi_camera = tsi_sdk->GetCamera(0);
      if(tsi_camera == 0)
      {
         printf("***ERROR***: TsiSDK::GetCamera(0) failed\n");
         tsi_sdk->Close();
         unload_tsi_sdk(tsi_sdk);
         tsi_sdk = 0;
         return 0;
      }

      //------------------------------------------------------------------------
      // Open the camera.
      status = tsi_camera->Open();
      if(status == false)
      {
         printf("***ERROR***: TsiCamera::Open() failed\n");
         tsi_sdk->Close();
         unload_tsi_sdk(tsi_sdk);
         tsi_sdk = 0;
         return 0;
      }

      //------------------------------------------------------------------------
      // Setup callback
      status = tsi_camera->SetImageNotificationCallback((TSI_FUNCTION_IMAGE_NOTIFICATION_CALLBACK)image_notification_callback, (void*)tsi_camera);
      if(status == false)
      {
         printf("***ERROR***: TsiCamera::SetImageNotificationCallback() failed\n");
         tsi_sdk->Close();
         unload_tsi_sdk(tsi_sdk);
         tsi_sdk = 0;
         return 0;
      }

      //------------------------------------------------------------------------
      // Note: By setting TSI_PARAM_FRAME_COUNT to 0, the camera will continuously 
      //       generate images.
      tsi_camera->SetParameter(TSI_PARAM_FRAME_COUNT,     0);

      //------------------------------------------------------------------------
      // Set exposure time to 100 milliseconds.
      tsi_camera->SetParameter(TSI_PARAM_EXPOSURE_TIME, 100);

      //------------------------------------------------------------------------
      // Start the camera.
      tsi_camera->Start();

      //------------------------------------------------------------------------
      // Call GetPendingImage() until we get an image.
      while(_tsi_image == 0)
      {
         Sleep(100);
      }

      if(_tsi_image != 0)
      {
         printf("image recieved\n");
         printf("image width :  %4d\n", _tsi_image->m_Width);
         printf("image height:  %4d\n", _tsi_image->m_Height);
         tsi_camera->FreeImage(_tsi_image);
         _tsi_image = 0;
      }

      //------------------------------------------------------------------------
      // Stop the camera.
      tsi_camera->Stop();

      //------------------------------------------------------------------------
      // Close the camera.
      tsi_camera->Close();
   }

   //------------------------------------------------------------------------
   // Close the SDK.
   status = tsi_sdk->Close();

   //------------------------------------------------------------------------
   // Unload the SDK.
   unload_tsi_sdk(tsi_sdk);
   tsi_sdk = 0;

   printf("done\n");
   
   return 0;
}






//==============================================================================
// load_tsi_sdk
//------------------------------------------------------------------------------
//==============================================================================
int load_tsi_sdk(TsiSDK **tsi_sdk)
{
TSI_CREATE_SDK tsi_create_sdk = 0;

   if(tsi_sdk == 0)
   {
      return 0;
   }

   _tsi_dll_handle = LoadLibraryA("thorlabs_ccd_tsi_sdk.dll");
   if(_tsi_dll_handle == 0)
   {
      return 0;
   }

   tsi_create_sdk = (TSI_CREATE_SDK)GetProcAddress(_tsi_dll_handle, "tsi_create_sdk");
   if(tsi_create_sdk == 0)
   {
      FreeLibrary(_tsi_dll_handle);
      _tsi_dll_handle = 0;
      return 0;
   }

   *tsi_sdk = tsi_create_sdk();
   
   return 1;
}

//==============================================================================
// unload_tsi_sdk
//------------------------------------------------------------------------------
//==============================================================================
int unload_tsi_sdk(TsiSDK *tsi_sdk)
{
TSI_DESTROY_SDK tsi_destroy_sdk = 0;

   if(tsi_sdk == 0)
   {
      return 0;
   }

   tsi_destroy_sdk = (TSI_DESTROY_SDK)GetProcAddress(_tsi_dll_handle, "tsi_destroy_sdk");
   if(tsi_destroy_sdk == 0)
   {
      FreeLibrary(_tsi_dll_handle);
      _tsi_dll_handle = 0;
      return 0;
   }

   tsi_destroy_sdk(tsi_sdk);
   
   return 1;
}


