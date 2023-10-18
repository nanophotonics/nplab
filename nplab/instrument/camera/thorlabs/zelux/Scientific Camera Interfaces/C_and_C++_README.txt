C and C++ README

For C++ support for Thorlabs scientific cameras (340xxx, 1500xxx, 1501xxx, 4070xxx, 8050xxx, and 8051xxx), please see the SDK\Legacy subfolder. The header files and DLLs can be found there.

For C/C++ support for all Thorlabs compact-scientific cameras (CS2100M-USB, CC215MU, CS135xxx, CS165xxx, CS235xxx, CS505xxx, CS895xxx), please follow these directions:

1. Install ThorCam and the appropriate drivers. The installer can be found at Thorlabs.com on any of the camera pages. Click on the Software tab, then on the Software button.

2. Copy the native DLLs from

 SDK\Native Camera Toolkit\dlls\Native_32_lib\*.dll
 or
 SDK\Native Camera Toolkit\dlls\Native_64_lib\*.dll 
 
 to the folder with your executable file (output folder).

3. See the following guides found in the Documentation folder (usually C:\Program Files\Thorlabs\Scientific Imaging\Documentation\Scientific Camera Documents):

 Thorlabs_Camera_C_Programming_Guide.chm
 and
 Thorlabs_Color_Processing_Programming_Guide.chm
 
4. To access the functions in the DLLs, helper files are provided.

   These have the suffix ..._load.c. They can be found in the SDK\Native Toolkit\load_dll_helper folder.

   These helper functions look up the DLL function addresses and assign them to external variables that can directly called. Please see the provided example applications for details.

   For example, the tl_camera_sdk_load.c and tl_camera_sdk_load.h files provide
 
   tl_camera_sdk_dll_initialize()
   
   and
   
   tl_camera_sdk_dll_terminate()

   ***** IMPORTANT: It is important to update these ..._load.c files with each new version of the SDK. *****

5. Be sure to always close cameras, close the SDK, and terminate the dll before exiting your application. Otherwise, crashes can occur upon exit.
