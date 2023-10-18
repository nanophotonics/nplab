Python README

The Python SDK supports Thorlabs scientific-camera series CC215, CS126, CS135, CS165, CS2100, CS235, CS505, and CS895. 

The Python SDK is a wrapper around the native SDK, which means python applications need access to the native camera DLLs.

To install the Python SDK, please follow these directions:

1. Install ThorCam and the appropriate drivers. The installer can be found at Thorlabs.com on any of the camera pages. Click on the Software tab, then on the Software button.

2. The Python SDK is provided both as an installable package and as source files. To install the Python SDK in your environment, use a package manager such as pip to install from the package file. 

 Example install command: 'python.exe -m pip install thorlabs_tsi_camera_python_sdk_package.zip'  

 This will install the thorlabs_tsi_sdk package into your current environment. The examples assume you are using this method. 
 If you want to use the source files directly, they are included in SDK\Python Camera Toolkit\source.

3. To use the examples, copy the native DLLs from

   SDK\Native Toolkit\dlls\Native_32_lib\*.dll
   to
   SDK\Python Toolkit\dlls\32_lib\

   or

   SDK\Native Toolkit\dlls\Native_64_lib\*.dll 
   to 
   SDK\Python Toolkit\dlls\64_lib\

   The examples assume that this is the location of the dlls, but you can adjust the example code to fit your needs.

4. A requirements.txt file is provided in the examples folder that lists the libraries needed to run the examples (besides the thorlabs_tsi_sdk package). This can be used with pip to install each dependency at once:

   pip install -r requirements.txt  

5. See the following guide found in the Documentation folder (usually C:\Program Files\Thorlabs\Scientific Imaging\Documentation\Scientific Camera Documents):

   Thorlabs_Camera_Python_API_Reference.chm

6. Be sure to always dispose of cameras and the SDK before exiting your application. Otherwise, crashes can occur upon exit.