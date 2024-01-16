////////////////////////////////////////////////////////////////////////////////
//  
// This software system is an unpublished work protected under the copyright
// laws of the United States of America.
//  
// Copyright © 2015 Thorlabs Scientific, Inc.  All Rights Reserved
//  
////////////////////////////////////////////////////////////////////////////////

// The following sample is intended to illustrate the fundamental
// software constructs that are needed to interface a host application
// to TSI's scientific cameras.
//
// It makes no attempt to do anything sophisticated.  Instead it:
// 1. Initializes the TSI SDK.
// 2. Connects to the first TSI camera (assuming that is finds one).
// 3. Converts it to a color camera (if the camera supports color imaging).
// 3. Captures 10 frames from the camera at 10 frames per second.
// 4. Cleans up SDK resources.
//
// The user will need to include the SDK headers and DLLS in order
// to compile and run this example code.  These artifacts are not
// distributed with this source since they will be constantly updated
// and any specific versions that are included with this may be out
// of date.
//

#include <cstdio>
#include <Windows.h>
#include "TsiSDK.h"
#include "TsiCamera.h"
#include "TsiColorImage.h"
#include "TsiColorCamera.h"

using namespace std;

// The following class makes it easier to deal with
// Windows event objects by encapsulating their creation
// and cleanup inside it (RAII idiom).
class TsiEvent
{
public:
   TsiEvent()
   {
      if (!(m_event = CreateEvent(NULL, FALSE, FALSE, 0)))
         printf ("Failed to create the TSI SDK event.\n");
   }

   ~TsiEvent()
   {
      CloseHandle (m_event);
   }

   // Useful when an instance of this class is passed to Win32 functions
   // that expect a HANDLE argument.
   operator HANDLE() { return (m_event); }

private:
   HANDLE m_event;
};

struct ImageNotificationData
{
   explicit ImageNotificationData (TsiColorCamera* cam, TsiEvent& stopEvent, const size_t numberOfFrames) : m_cam (cam)
                                                                                                          , m_stopEvent (stopEvent)
                                                                                                          , m_numberOfFrames (numberOfFrames) {}
   TsiColorCamera* m_cam;
   TsiEvent m_event;
   TsiEvent& m_stopEvent;
   const size_t m_numberOfFrames;
};

void PrintRGBPixelValues (TsiColorImage* image)
{
   printf ("Red: %d, Green: %d, Blue: %d - ", image->m_ColorPixelDataBGR.BGR_16[2*image->m_Width + 1].r 
                                           , image->m_ColorPixelDataBGR.BGR_16[2*image->m_Width + 1].g 
                                           , image->m_ColorPixelDataBGR.BGR_16[2*image->m_Width + 1].b);
}

void ImageNotificationCallback (int event_id, void *context)
{
   ImageNotificationData& notificationData = *(static_cast <ImageNotificationData*> (context));
   switch (event_id)
   {
   case TSI_IMAGE_NOTIFICATION_PENDING_IMAGE:
      // 1. Get an image and if it is valid.
      // 2. Print the RGB intensity values for the first pixel tuple.
      // 3. Free the image.
      if (TsiColorImage* image = notificationData.m_cam->GetPendingColorImage(TSI_COLOR_POST_PROCESS))
      {
         PrintRGBPixelValues (image);
         notificationData.m_cam->FreeColorImage (image);
         // Notify the main acquisition loop that a single image has been processed successfully.
         SetEvent (notificationData.m_event);
      }
      break;

   case TSI_IMAGE_NOTIFICATION_ACQUISITION_ERROR:
      printf ("An image acquisition error occurred for camera: %s", notificationData.m_cam->GetCameraName());
      break;
   
   default:
      break;
   };
}

void CameraControlCallback (int notification, void* context)
{
   TsiEvent& stopEvent = *(static_cast <TsiEvent*> (context));
   switch (notification)
   {
   case TSI_CAMERA_CONTROL_SEQUENCE_COMPLETE:
      SetEvent (stopEvent);
      break;

   default:
      break;
   }
}

void AcquireImages (ImageNotificationData& notificationData)
{
   size_t numFrames = 0;
   const HANDLE waitEvents[2] = {notificationData.m_event, notificationData.m_stopEvent};
   const HANDLE* waitEventsPtr = waitEvents;

   // Start acquiring images.
   notificationData.m_cam->Start();

   while (numFrames < notificationData.m_numberOfFrames)
   {
      DWORD signaledEvent = ::WaitForMultipleObjects (2, waitEventsPtr, FALSE, INFINITE);
      if (signaledEvent == WAIT_OBJECT_0 + 1)
      {
         SetEvent (notificationData.m_stopEvent);
         break;
      }
      // A single image has been successfully processed, so
      // increment the image counter.
      ++numFrames;
      printf ("Received frame %d!\n", numFrames);
   }

   // We are done, so stop acquiring images.
   notificationData.m_cam->Stop();
   printf ("Received %d images.\n", numFrames);
   WaitForSingleObject (notificationData.m_stopEvent, INFINITE);
}

int main()
{
   // Open a handle to the TSI SDK DLL.
   HMODULE sdk_handle = NULL;
   sdk_handle = ::LoadLibrary ("thorlabs_ccd_tsi_sdk.dll");
   if (!sdk_handle)
   {
      printf ("Unable to open the TSI SDK.\n");
      exit (1);
   }

   TSI_CREATE_SDK tsi_create_sdk = reinterpret_cast <TSI_CREATE_SDK> (GetProcAddress(sdk_handle, "tsi_create_sdk"));
   if (!tsi_create_sdk)
   {
      printf ("Unable to map the TSI SDK object creation function.\n");
      // Free the SDK DLL.
      if (sdk_handle)
      {
         ::FreeLibrary (sdk_handle);
         sdk_handle = NULL;
      }
      exit (1);
   }

   // Create an instance of the TSI SDK.
   TsiSDK* sdk = tsi_create_sdk();
   if (!sdk)
   {
      printf ("Failed to create the SDK.\n");
      // Free the SDK DLL.
      if (sdk_handle)
      {
         ::FreeLibrary (sdk_handle);
         sdk_handle = NULL;
      }      
      exit (1);
   }
   
   // Open the SDK.
   if (!sdk->Open())
   {
      printf ("Failed to open the SDK.\n");
      // Destroy the SDK instance.
      TSI_DESTROY_SDK tsi_destroy_sdk = reinterpret_cast <TSI_DESTROY_SDK> (GetProcAddress(sdk_handle, "tsi_destroy_sdk"));
      if (tsi_destroy_sdk)
      {
         tsi_destroy_sdk (sdk);
         sdk = NULL;
      }
      else
      {
         printf ("Failed to destroy the SDK DLL.\n");
      }

      // Free the SDK DLL.
      if (sdk_handle)
      {
         ::FreeLibrary (sdk_handle);
         sdk_handle = NULL;
      }
      exit (1);
   }

   // Query the number of cameras.
   int num_cameras = sdk->GetNumberOfCameras();
   printf ("Number of cameras = %d\n", num_cameras);

   if (num_cameras)
   {
      printf ("Open the first camera.\n");
      // Get a handle to the first camera (only).
      TsiCamera* cam = sdk->GetCamera (0);
      if (cam->Open())
      {
         // We successfully got a handle to the first camera.
         char colorFiltertype [32] = {0};
         if (!cam->GetParameter (TSI_PARAM_COLOR_FILTER_TYPE, 32, colorFiltertype))
         {
            printf ("Failed to query the camera for color capability.\n");
            exit (1);
         }

         if ((strlen (colorFiltertype) != 0) && (strcmp (colorFiltertype, "mono") == 0))
         {
            printf ("This camera does not have color capability.\n");
            exit (1);
         }
         
         TSI_COLOR_FILTER_ARRAY_PHASE_VALUES cfaPhase;
         cam->GetParameter (TSI_PARAM_COLOR_FILTER_PHASE, sizeof(TSI_COLOR_FILTER_ARRAY_PHASE_VALUES), static_cast <void*> (&cfaPhase));

         char irFilterType [32] = {0};
         cam->GetParameter (TSI_PARAM_COLOR_IR_FILTER_TYPE, 32, irFilterType);

         double ccm[9];
         cam->GetParameter (TSI_PARAM_COLOR_CAMERA_CORRECTION_MATRIX, sizeof(double*), static_cast <void*> (&ccm));

         char ccmOutputColorSpace [32] = {0};
         cam->GetParameter (TSI_PARAM_CCM_OUTPUT_COLOR_SPACE, 32, ccmOutputColorSpace);

         double dwb[9];
         cam->GetParameter (TSI_PARAM_DEFAULT_WHITE_BALANCE_MATRIX, 9, static_cast <void*> (&dwb));

         // If we get here, the camera supports color imaging
         // so we cast our existing TsiCamera pointer to a TsiColorCamera
         // to expose the color specific API.
         TsiColorCamera* colorCam = (TsiColorCamera*) cam;

         static const int CAMERA_ATTRIBUTE_SIZE = 256;
         char firmwareRevision [CAMERA_ATTRIBUTE_SIZE];
         char hardwareRevision [CAMERA_ATTRIBUTE_SIZE];
         char cameraModel [CAMERA_ATTRIBUTE_SIZE];
         char cameraSerialNumber [CAMERA_ATTRIBUTE_SIZE];

         // Get the camera descriptive parameters.
         memset (&firmwareRevision, 0, sizeof (firmwareRevision));
         memset (&hardwareRevision, 0, sizeof (hardwareRevision));  
         memset (&cameraModel, 0, sizeof (cameraModel));  
         memset (&cameraSerialNumber, 0, sizeof (cameraSerialNumber));

         // Camera firmware version.
         if (colorCam->GetParameter(TSI_PARAM_FW_VER, CAMERA_ATTRIBUTE_SIZE, firmwareRevision))
         {
            printf ("firmware revision is: %s\n", firmwareRevision);
         }
         else
         {
            printf ("Unable to get the firmware version.\n");
         }

         // Camera hardware version.
	      if (colorCam->GetParameter(TSI_PARAM_HW_VER, CAMERA_ATTRIBUTE_SIZE, hardwareRevision))
         {
            printf ("hardware revision is: %s\n", hardwareRevision);
         }
         else
         {
            printf ("Unable to get the hardware version.\n");
         }

         // Camera model name.
	      if (colorCam->GetParameter(TSI_PARAM_HW_MODEL, CAMERA_ATTRIBUTE_SIZE, cameraModel))
         {
            printf ("camera model is: %s\n", cameraModel);
         }
         else
         {
            printf ("Unable to get the camera model.\n");
         }

         // Camera serial number.
	      if (colorCam->GetParameter(TSI_PARAM_HW_SER_NUM, CAMERA_ATTRIBUTE_SIZE, cameraSerialNumber))
         {
            printf ("camera serial number is: %s\n", cameraSerialNumber);
         }
         else
         {
            printf ("Unable to get the camera serial number.\n");
         }

         // Set exposure time to give 10 fps.
         int units = TSI_EXP_UNIT_MILLISECONDS;
	      if (!colorCam->SetParameter(TSI_PARAM_EXPOSURE_UNIT, (void *)&units))
         {
            printf ("Failed to set the exposure units.\n");
         }
         
         // 100 ms exposure time.
         int etime = 100; 
	      if (!colorCam->SetParameter(TSI_PARAM_EXPOSURE_TIME, (void *)&etime))
         {
            printf ("Failed to set the exposure time.\n");
         }
     
         // Set the ROI and binning properties for the camera.
         TSI_ROI_BIN	roi_bin;
         memset (&roi_bin, 0, sizeof (roi_bin));

         // 1x1 binning
         roi_bin.XBin = 1;
         roi_bin.YBin = 1;
         int swidth = 0;
         // Set the requested frame size equal to the full frame size of the sensor.
         if (colorCam->GetParameter (TSI_PARAM_HSIZE, sizeof(swidth), &swidth))
            roi_bin.XPixels = swidth;
         else
         {
            printf ("Failed to read the sensor width. Setting requested width to 640 pixels.\n");
            roi_bin.XPixels = 640;
         }

         int sheight = 0;
         if (colorCam->GetParameter (TSI_PARAM_VSIZE, sizeof(sheight), &sheight))
         {
            roi_bin.YPixels = sheight;
         }
         else
         {
            printf ("Failed to read the sensor height. Setting requested width to 480 pixels.\n");
            roi_bin.XPixels = 480;
         }

         // This sends the selections to the camera.
         if (!cam->SetParameter(TSI_PARAM_ROI_BIN, static_cast <void*> (&roi_bin)))
         {
            printf ("Unable to set the ROI parameters.\n");
         }

         // Request the camera to send 10 frames.
         int numberOfFrames = 10;
         if (!colorCam->SetParameter (TSI_PARAM_FRAME_COUNT, static_cast <void*> (&numberOfFrames)))
         {
            printf ("Failed to set the requested number of frames to %d\n", numberOfFrames);
         }

         // Set image notification callback.
         // The SDK will call this function when a frame is available for consumption
         // by the host application.
         TsiEvent stopEvent;
         ImageNotificationData imageNotificationData (colorCam, stopEvent, numberOfFrames);
         colorCam->SetImageNotificationCallback (ImageNotificationCallback, &imageNotificationData);
         colorCam->SetCameraControlCallback (CameraControlCallback, &stopEvent);

         // Setup the color pipeline to include the camera correction matrix and to output sRGB48.
         colorCam->ClearColorPipeline();
         colorCam->ConcatenateColorTransform (TSI_Camera_Color_Correction, 0);
         colorCam->ConcatenateColorTransform (TSI_sRGB, 14);
         colorCam->FinalizeColorPipeline();

         // Image acquisition loop.
         AcquireImages (imageNotificationData);

         // We are done, so cleanup the camera.
         if (!colorCam->Close())
         {
            printf ("Failed to close the camera.\n");
         }   
      }
      else
      {
         printf ("Failed to open the camera.\n");
      }
   }

   // Close the SDK.
   if (!sdk->Close())
   {
      printf ("Failed to close the SDK.\n");
      exit (1);     
   }

   // Destroy the SDK instance.
   TSI_DESTROY_SDK tsi_destroy_sdk = reinterpret_cast <TSI_DESTROY_SDK> (GetProcAddress(sdk_handle, "tsi_destroy_sdk"));
   if (tsi_destroy_sdk)
   {
      tsi_destroy_sdk (sdk);
      sdk = NULL;
   }
   else
   {
      printf ("Failed to destroy the SDK DLL.\n");
   }

   // Free the SDK DLL.
   if (sdk_handle)
   {
      ::FreeLibrary (sdk_handle);
      sdk_handle = NULL;
   }

   return (0);
}
