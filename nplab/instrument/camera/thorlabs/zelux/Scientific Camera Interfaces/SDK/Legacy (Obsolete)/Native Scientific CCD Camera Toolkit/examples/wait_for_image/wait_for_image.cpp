//=============================================================================
// amt_sample.cpp
//-----------------------------------------------------------------------------
//=============================================================================
#include <stdio.h>
#include <windows.h>

#define TSI_ENABLE_LOADER
#include "TsiSDK.h"
#include "TsiCamera.h"
#include "TsiImage.h"


//=============================================================================
// main
//-----------------------------------------------------------------------------
// This is a simple windows console application.
//=============================================================================
int main(int argc, char* argv[])
{
int        i                = 0;
int        num_cameras      = 0;
bool       success          = false;
char      *camera_name      = 0;
TsiSDK    *tsi_sdk          = 0;
TsiCamera *tsi_cam          = 0;
TsiImage  *tsi_image        = 0;


char       tsi_fw_version_str   [256];
char       tsi_hw_version_str   [256];
char       tsi_hw_model_str     [256];
char       tsi_hw_serial_num_str[256];


int         op_mode          = TSI_OP_MODE_NORMAL;
int         num_frames       = 0;
int         exposure_time_ms = 200;

int         sensor_width       = 0;
int         sensor_height      = 0;
int         image_width        = 0;
int         image_height       = 0;
int         bin_x              = 2;
int         bin_y              = 2;
int         num_dropped_frames = 0;


TSI_ROI_BIN roi_bin;

int             pixel_buffer_size_in_pixels = 0;
int             pixel_buffer_size_in_bytes  = 0;
unsigned short *pixel_buffer                = 0;


   memset(tsi_fw_version_str   , 0, 256);
   memset(tsi_hw_version_str   , 0, 256);
   memset(tsi_hw_model_str     , 0, 256);
   memset(tsi_hw_serial_num_str, 0, 256);

   printf("Wait For Image Sample Program\n");

   tsi_sdk = get_tsi_sdk(0);
   if(tsi_sdk == 0)
   {
      printf("***ERROR***: get_tsi_sdk(\"thorlabs_ccd_tsi_sdk.dll\"); failed\n");
      return 0;
   }

   success = tsi_sdk->Open();
   if(success == false)
   {
      printf("***ERROR***: tsi_sdk->Open() failed\n");
      return 0;
   }

   num_cameras = tsi_sdk->GetNumberOfCameras();
   if(num_cameras == 0)
   {
      printf("Did not detect any cameras.\n");
      tsi_sdk->Close();
      release_tsi_sdk(tsi_sdk);
      return 0;
   }

   printf("detected %d num of cameras\n", num_cameras);

   for(i=0;i<num_cameras;i++)
   {
      camera_name = tsi_sdk->GetCameraName(i);
      printf("camera %d: %s\n", i, camera_name);
   }

   printf("Attempting to connect to camera 0\n");
   tsi_cam = tsi_sdk->GetCamera(0);
   if(tsi_cam == 0)
   {
      printf("***ERROR***: GetCamera(0) failed\n");
      tsi_sdk->Close();
      release_tsi_sdk(tsi_sdk);
      return 0;
   }

   //--------------------------------------------------------------------------
   // Open camera.
   //--------------------------------------------------------------------------
   success = tsi_cam->Open();
   if(success == false)
   {
      printf("***ERROR***: Failed to open camera\n");
      tsi_sdk->Close();
      release_tsi_sdk(tsi_sdk);
      return 0;
   }


   //--------------------------------------------------------------------------
   // Get/Set camera parameters.
   //
   // Note: As long as the camera is powered, parameter values are persistant.
   //       So it is important to set those parameters we care about each time.
   //       Who knows what the last user set the parameters to.
   //--------------------------------------------------------------------------
   tsi_cam->GetParameter(TSI_PARAM_FW_VER,     256, tsi_fw_version_str);
   tsi_cam->GetParameter(TSI_PARAM_HW_VER,     256, tsi_hw_version_str);
   tsi_cam->GetParameter(TSI_PARAM_HW_MODEL,   256, tsi_hw_model_str);
   tsi_cam->GetParameter(TSI_PARAM_HW_SER_NUM, 256, tsi_hw_serial_num_str);

   printf("TSI Camera firmware version      :%s\n", tsi_fw_version_str);
   printf("TSI Camera hardware version      :%s\n", tsi_hw_version_str);
   printf("TSI Camera hardware model number :%s\n", tsi_hw_model_str);
   printf("TSI Camera hardware serial number:%s\n", tsi_hw_serial_num_str);

   tsi_cam->GetParameter(TSI_PARAM_HSIZE, sizeof(int), &sensor_width);
   tsi_cam->GetParameter(TSI_PARAM_VSIZE, sizeof(int), &sensor_height);

   printf("TSI Camera sensor width:%d  height:%d\n", sensor_width, sensor_height);
   Sleep(5000);


   op_mode = TSI_OP_MODE_NORMAL;
   success = tsi_cam->SetParameter(TSI_PARAM_OP_MODE, (void *)&op_mode);
   if(success == false)
   {
      printf("***ERROR***: SetParameter(TSI_PARAM_OP_MODE) failed\n");
      tsi_cam->Close();
      tsi_sdk->Close();
      release_tsi_sdk(tsi_sdk);
      return 0;
   }


   memset(&roi_bin, 0, sizeof(TSI_ROI_BIN));

   roi_bin.XOrigin = 0;
   roi_bin.YOrigin = 0;
   roi_bin.XPixels = sensor_width;
   roi_bin.YPixels = sensor_height;
   roi_bin.XBin    = bin_x;
   roi_bin.YBin    = bin_y;

   success = tsi_cam->SetParameter(TSI_PARAM_ROI_BIN, (void *)&roi_bin);
   if(success == false)
   {
      printf("***ERROR***: SetParameter(TSI_PARAM_ROI_BIN) failed\n");
      tsi_cam->Close();
      tsi_sdk->Close();
      release_tsi_sdk(tsi_sdk);
      return 0;
   }

   success = tsi_cam->SetParameter(TSI_PARAM_EXPOSURE_TIME, (void *)&exposure_time_ms);
   if(success == false)
   {
      printf("***ERROR***: SetParameter(TSI_PARAM_EXPOSURE_TIME) failed\n");
      tsi_cam->Close();
      tsi_sdk->Close();
      release_tsi_sdk(tsi_sdk);
      return 0;
   }

   //--------------------------------------------------------------------------
   // TSI_PARAM_FRAME_COUNT - Setting this parameter to 0, means that the 
   // camera will continuously generate images.
   // For values greater than 0, the camera will generate that number of frames
   // and then stop.
   //--------------------------------------------------------------------------
   num_frames = 0;
   success = tsi_cam->SetParameter(TSI_PARAM_FRAME_COUNT, (void *)&num_frames);
   if(success == false)
   {
      printf("***ERROR***: SetParameter(TSI_PARAM_FRAME_COUNT) failed\n");
      tsi_cam->Close();
      tsi_sdk->Close();
      release_tsi_sdk(tsi_sdk);
      return 0;
   }


   image_width                 = sensor_width  / bin_x;
   image_height                = sensor_height / bin_y;
   pixel_buffer_size_in_pixels = image_width * image_height;
   pixel_buffer_size_in_bytes  = pixel_buffer_size_in_pixels * sizeof(unsigned short);
   pixel_buffer = (unsigned short *)malloc(pixel_buffer_size_in_bytes);
   if(pixel_buffer == 0)
   {
      printf("***ERROR***: malloc(%d) failed\n", pixel_buffer_size_in_bytes);
      tsi_cam->Close();
      tsi_sdk->Close();
      release_tsi_sdk(tsi_sdk);
      return 0;
   }

   memset(pixel_buffer, 0, pixel_buffer_size_in_bytes);


   //--------------------------------------------------------------------------
   // STARTING CAMERA - When TsiCamera::Start() is called the sequence of 
   // events are as follows:
   //    1. The host software will interrogate a subset of the camera
   //       parameters, such as ROI, binning, etc.
   //    2. The host software will allocate internal image buffers
   //       based on camera parameters, and setup for image acquisition.
   //    3. The host software will then 'trigger' the camera to start
   //       exposure and image frame generation.
   //    4. When/If an image is recieved it is placed into an internal image queue.
   //       Once enqueued, the image is ready for consumption by the user application.
   //
   //    Note: The internal image queue currently has the capacity to store 8 images.
   //          If the image queue is full when an image is received from the camera
   //          the oldest image (the first one in queue) is dequeued, used for the new image
   //          and enqueued at the end of of the queue.
   //                  
   //--------------------------------------------------------------------------
   success = tsi_cam->Start();
   if(success == false)
   {
      printf("***ERROR***: Start() failed\n");
      tsi_cam->Close();
      tsi_sdk->Close();
      release_tsi_sdk(tsi_sdk);
      return 0;
   }

   for(i=0;i<50;i++)
   {
      printf("Waiting for image\n");

      //--------------------------------------------------------------------------
      // Note: WaitForImage() has changed in the latest SDK version. It takes an 
      //       integer value for timeout in milliseconds. It has a default value
      //       of TSI_WAIT_INFINITE (-1). 
      //--------------------------------------------------------------------------
      success = tsi_cam->WaitForImage();
      if(success == false)
      {
         printf("WaitForImage() returned false\n");
         continue;
      }
      
      tsi_image = tsi_cam->GetPendingImage();
      if(tsi_image == 0)
      {
         printf("***ERROR***: Failed to acquire image\n");
         continue;
      }

      //-----------------------------------------------------------------------
      // Copy image data to application memory here.
      //-----------------------------------------------------------------------
      printf("tsi_image->m_PixelData.vptr:0x%08x\n", tsi_image->m_PixelData.vptr);
      memcpy(pixel_buffer, tsi_image->m_PixelData.vptr, pixel_buffer_size_in_bytes);


      //-----------------------------------------------------------------------
      // It is important to 'FreeImage' when done. This image is one of the 8
      // images that are part of the internal image queue. If you never call
      // TsiCamera::FreeImage() after getting an image (via GetPendingImage())
      // then the acquisition software will run out of free images to use for
      // incoming image frames.
      //
      // Note: When TsiCamera::Stop() is called, all image memory is invalid.
      //       So make sure you copy the relevant data you need before calling 
      //       TsiCamera::Stop().
      //-----------------------------------------------------------------------
      tsi_cam->FreeImage(tsi_image);

      printf("Got Image, width:%d height:%d frame_number:%d\n", tsi_image->m_Width, tsi_image->m_Height, tsi_image->m_FrameNumber);
   }


   tsi_cam->GetParameter(TSI_PARAM_DROPPED_FRAMES, sizeof(int), &num_dropped_frames);
   printf("Number of dropped frames:%d\n", num_dropped_frames);

   if(pixel_buffer != 0)
   {
      pixel_buffer_size_in_bytes  = 0;
      pixel_buffer_size_in_pixels = 0;
      free(pixel_buffer);
      pixel_buffer = 0;
   }

   tsi_cam->Stop();
   tsi_cam->Close();
   tsi_sdk->Close();

   release_tsi_sdk(tsi_sdk);

	return 0;
}

