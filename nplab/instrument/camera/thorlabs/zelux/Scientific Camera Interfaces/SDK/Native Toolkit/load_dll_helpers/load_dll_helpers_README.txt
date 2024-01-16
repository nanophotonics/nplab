DLL modules such as the camera SDK or the polarization SDK must be loaded dynamically.

In order to load the DLLs and look up the API function pointers, ...load.c files are provided.

Please compile the ...load.c file(s) with your application or library.

#include the corresponding .h file

Then call the corresponding ...initialize() function.

When finished with the DLL, call the corresponding ...terminate() function to unload the DLL.

For more details, see the .chm or .pdf help files and the example applications.

***** IMPORTANT: It is important to update these ..._load.c files with each new version of the SDK. *****
