// The following ifdef block is the standard way of creating macros which make exporting 
// from a DLL simpler. All files within this DLL are compiled with the TSI_CAM_EXPORTS
// symbol defined on the command line. This symbol should not be defined on any project
// that uses this DLL. This way any other project whose source files include this file see 
// TSI_CAM_API functions as being imported from a DLL, whereas this DLL sees symbols
// defined with this macro as being exported.
//#ifdef TSI_CAM_EXPORTS
//#define TSI_CAM_API extern "C" __declspec(dllexport)
//#else
//#define TSI_CAM_API extern "C" __declspec(dllimport)
//#endif

//#ifdef __cplusplus
//#define TSI_CAM_API extern "C" __declspec(dllexport)
//#else
//#define TSI_CAM_API __declspec(dllexport)
//#endif

#define TSI_CAM_API extern "C" __declspec(dllexport)

TSI_CAM_API int   Open_SDK                  (char *path);
TSI_CAM_API int   Close_SDK                 (void);
TSI_CAM_API int   GetNumberOfCameras_SDK    (void);
TSI_CAM_API int   GetCameraName_SDK         (int camera_number, char *name , int limit);
TSI_CAM_API int   CamerasOpen_SDK           (int camera_number);
TSI_CAM_API int   CamerasClose_SDK          (void);
TSI_CAM_API int   CamerasStart_SDK          (void);
TSI_CAM_API int   CamerasStop_SDK           (void);
TSI_CAM_API int   CamerasStartTrigger_SDK   (void);
TSI_CAM_API int   CamerasStopTrigger_SDK    (void);
TSI_CAM_API int   GetPendingImage_SDK       (void *image);
TSI_CAM_API int   SetEXPOSURE_SDK           (int time_ms);
TSI_CAM_API int   SetGAIN_SDK               (int gain);
TSI_CAM_API int   SetBLACK_LEVEL_SDK        (int level);
TSI_CAM_API int   SetNUM_IMAGE_BUFFERS_SDK  (int num_image_buffers);
TSI_CAM_API int   SoftwareTrigger_SDK       (void);
TSI_CAM_API int   GetImageWidth_SDK         (void);
TSI_CAM_API int   GetImageHeight_SDK        (void);
TSI_CAM_API int   GetImageBitsPerPixel_SDK  (void);
TSI_CAM_API int   GetErrorCode_SDK          (char *code, int limit);
TSI_CAM_API int   SetParameterINT32_SDK     (int ID, __int32 par);
TSI_CAM_API int   SetParameterString_SDK    (int ID, char *par);
TSI_CAM_API int   SetParameterU8_SDK        (int ID, unsigned __int8 par);
TSI_CAM_API int   SetParameterU32_SDK       (int ID, unsigned __int32 par);
TSI_CAM_API int   SetParameterFP_SDK        (int ID, float par);
TSI_CAM_API int   SetParameter_ROI_BIN_SDK  (unsigned __int32 a, unsigned __int32 b, unsigned __int32 c, unsigned __int32 d, unsigned __int32 e, unsigned __int32 f);
TSI_CAM_API int   GetParameterU8_SDK        (int ID);
TSI_CAM_API int   GetParameterU32_SDK       (int ID);
TSI_CAM_API int   GetParameterString_SDK    (int ID, char *result , int len);
TSI_CAM_API int   GetParameterInt32_SDK     (int ID);
TSI_CAM_API float GetParameterFP_SDK        (int ID);
TSI_CAM_API int   GetParameter_ROI_BIN_SDK  (unsigned __int32* n, int size);



//------------------------------------------------------------------------------
// Color functions.
//------------------------------------------------------------------------------
// Note: The color SDK can do color corrections (if enabled) and also allows
//       the user to add additional matrices to be applied against the image. 
//       It also allows the user to set an input and/or output LUT (lookup table)
//       The input LUT translation is done before the matrix stack is applied 
//       and the output LUT translation is done after the matrix multiply. 
//
//       Color cameras are not able to perform binning, so there is no binning for color.
//
//       ROI (Region of interest): should work fine.
//
//------------------------------------------------------------------------------






//------------------------------------------------------------------------------
// AddMatrixTransform_SDK:
//------------------------------------------------------------------------------
//                         @p3x3Matrix - Array of double (floating point) values 
//                                       that comprise a 3x3 matrix. 
//                                       This matrix will be applied against 
//                                       images before they are retrieved via 
//                                       a call to GetPendingColorImage_SDK or
//                                       GetPendingColorImageRGB8_SDK.
//------------------------------------------------------------------------------
// Example:  
//
//  double my_matrix[9];
//  
//  my_matrix[0] = 0.1; my_matrix[1] = 0.5; my_matrix[2] = 0.1;
//  my_matrix[3] = 0.0; my_matrix[4] = 0.1; my_matrix[5] = 0.2;
//  my_matrix[6] = 0.6; my_matrix[7] = 1.8; my_matrix[8] = 0.7;
//
//   AddMatrixTransform_SDK(my_matrix);
//
//------------------------------------------------------------------------------
TSI_CAM_API int AddMatrixTransform_SDK (double* p3x3Matrix); 




#define TSI_sRGB                      0  // Works  - outputBitDepth matters here. Used to clip the bits. -1 uses camera default.
#define TSI_RGB_Linear                1  // Works  - outputBitDepth matters here. Used to clip the bits. -1 uses camera default.
#define TSI_Camera_Color_Correction   6  // Works  - outputBitDepth does not matter here
//TSI_CAM_API int ConcatenateColorTransform2_SDK (int xform_select, unsigned int outputBitDepth);
// Change name to:
//------------------------------------------------------------------------------
// EnableMatrixTransform_SDK:
//------------------------------------------------------------------------------
//                         @matrix_select - A value that selects a predefined 
//                                          matrix to be applied against images.
//                                          0: Enables the matrix to convert 
//                                             images to the sRGB color space.
//                                          1: Enables the matrix to convert 
//                                             images to the linear RGB color space.
//                                          6: Enables the matrix to convert 
//                                             images using the cameras color correction 
//                                             matrix.
//                          
//                         @output_bit_depth - A value that will indicate the bit
//                                             depth to clip the pixels to.
//                                             If the user specifies a 0 then it 
//                                             will use the default bitdepth.
//                                             In the case of TSI_Camera_Color_Correction
//                                             this value is not used. 
//
//  Question: does the output_bit_depth actually change to data size of the channels?
//            For example if I set the output_bit_depth to be 8 are the pixels then 
//            changed from being 3, 16 bit pixels to 3, 8 bit values.
//            So a 0xBBBB 0xGGGG 0xRRRR becomes a 0xBB 0xGG 0xRR, or is it something else? 
//
//------------------------------------------------------------------------------
// Example: EnableMatrixTransform_SDK(6, 14);
//------------------------------------------------------------------------------
TSI_CAM_API int EnableMatrixTransform_SDK(int matrix_select, unsigned int output_bit_depth);




//------------------------------------------------------------------------------
// SetInputTransform_SDK:
// SetOutputTransform_SDK:
//------------------------------------------------------------------------------
//                         @lut_array - array of integer values that for the LUT.
//                         @columns   - even though the array is 1D in memory, logically it is 2D.
//                                      So this argument specifies that component of the martix.
//                         @bit_depth - (1 << bit_depth) specifies the number of columns in the lut_array.
//------------------------------------------------------------------------------
//  The input transform stage is applied before any matrix transform is applied.
//  The output transform stage is appled after all matricies transforms have been applied.
//
//  Example:
//            SetInputTransform_SDK(data, 3, 14);   // int data[49152];
//                                                  // there are 16384 entries in array (1 << 14).
//                                                  // Each entry has 3 components.
//                                                  // The array size is 3 x 16384, which is 49152.
//
//            SetInputTransform_SDK(data, 1, 14);   // int data[16384]; a 1 x 16384 LUT.
//            SetInputTransform_SDK(data, 2, 14);   // int data[32768]; a 2 x 16384 LUT.
//            SetInputTransform_SDK(data, 1, 12);   // int data[ 4096]; a 1 x  4096 LUT.
//            SetInputTransform_SDK(data, 4, 12);   // int data[16384]; a 4 x  4096 LUT.
//
//            SetOutputTransform_SDK(data, 3,  8);   // int data[768  ]; a 3 x 256   LUT.
//            SetOutputTransform_SDK(data, 3, 14);   // int data[49152]; a 3 x 16384 LUT.
//
//         
//------------------------------------------------------------------------------
TSI_CAM_API int SetInputTransform_SDK         (int *lut_array, int columns, int bit_depth);
TSI_CAM_API int SetOutputTransform_SDK        (int *lut_array, int columns, int bit_depth);






//------------------------------------------------------------------------------
// ClearColorPipeline_SDK:
//------------------------------------------------------------------------------
// Clears everything and makes the entire image transformation matrix stack a 
// single identity matrix. 
// This includes the input and output LUT.
//------------------------------------------------------------------------------
TSI_CAM_API int ClearColorPipeline_SDK(void);


//------------------------------------------------------------------------------
// FinalizeColorPipeline_SDK:     
//------------------------------------------------------------------------------
// Commits/Applies the changes made to the image transform pipeline.
// Including matrices and input/output LUTs.
// For use with camera is running. Change color pipeline when camera is running. 
//------------------------------------------------------------------------------
TSI_CAM_API int FinalizeColorPipeline_SDK(void);



#define TSI_COLOR_DEMOSAIC     0
#define TSI_COLOR_POST_PROCESS 1
//------------------------------------------------------------------------------
// SetColorPostProcess:     
//------------------------------------------------------------------------------
// Selects what post processing happens to an image when GetPendingColorImage_SDK()
// of GetPendingColorImageRGB8_SDK() are called.
//
//   TSI_COLOR_DEMOSAIC     = 0
//   TSI_COLOR_POST_PROCESS = 1  (default).
//
//   TSI_COLOR_DEMOSAIC - only will demosaic the image, no color corrections.
//   TSI_COLOR_POST_PROCESS applies all color corrections.
//------------------------------------------------------------------------------
TSI_CAM_API int SetColorPostProcess(int select);

//------------------------------------------------------------------------------
// GetPendingColorImage_SDK:
//------------------------------------------------------------------------------
//                         @image - An array of 16 bit integers, each of which
//                                  represents a color channel.
//                                  The pixel format for color is BGR16.
//                                  0xBBBB 0xGGGG 0xRRRR 0xBBBB 0xGGGG 0xRRRR. 
//                                  
// In order to calculate the correct size of this buffer, you will need to get 
// the image width and height (in pixels), then multiply them by 2 x 3. 
// (image_width * image_height) * (2                   x    3).
//                                16 bits = 2 bytes.        3 channels (BGR).
//                                  
// If there is a pending image, it will get it and copy it into the buffer
// provided in this function call.
//------------------------------------------------------------------------------
TSI_CAM_API int GetPendingColorImage_SDK(void *image);


//------------------------------------------------------------------------------
// GetPendingColorImageRGB8_SDK
//------------------------------------------------------------------------------
//                         @image - An array of 32 bit integers, each of which
//                                  represents a RGB triplet.
//                                  The pixel format is 0x00
//
// In order to calculate the correct size of this buffer, you will need to get 
// the image width and height (in pixels), then multiply them by 4.
// (image_width * image_height) * (4).
//                                 32 bits = 4 bytes. 
//
// If there is a pending image, it will convert it from BGR16 to RGB8 and 
// fill up the buffer provided as an argument in this call.
//------------------------------------------------------------------------------
TSI_CAM_API int GetPendingColorImageRGB8_SDK(void *image);



//------------------------------------------------------------------------------
// By default there are no transforms applied to any image. So if the user 
// wants images that have accurate looking color they will need to enable some 
// transform. 
//
// Full example:
//
// ClearColorPipeline_SDK();
// EnableMatrixTransform_SDK(TSI_Camera_Color_Correction, 0);
// EnableMatrixTransform_SDK(TSI_sRGB, 0);
// FinalizeColorPipeline_SDK();
// CamerasStart_SDK();          
// GetPendingColorImage_SDK() or GetPendingColorImageRGB8_SDK().
//
//
// The image tranforms can be modified while the camera is running as well.
// An example of that would be:
//
//  double my_matrix[9];
//  my_matrix[0] = 0.1; my_matrix[1] = 0.5; my_matrix[2] = 0.1;
//  my_matrix[3] = 0.0; my_matrix[4] = 0.1; my_matrix[5] = 0.2;
//  my_matrix[6] = 0.6; my_matrix[7] = 1.8; my_matrix[8] = 0.7;
//
//  EnableMatrixTransform_SDK(TSI_Camera_Color_Correction, 0);
//  EnableMatrixTransform_SDK(TSI_sRGB, -1);
//  FinalizeColorPipeline_SDK();
//  CamerasStart_SDK();          
//  ...
//  ClearColorPipeline_SDK(); // Does not affect current image pipeline.
//  AddMatrixTransform_SDK(my_matrix);
//  FinalizeColorPipeline_SDK();       // Changes are applied and now images will 
//                                     // affect the images.
// GetPendingColorImage_SDK() or GetPendingColorImageRGB8_SDK().
//  
//  my_matrix[0] = my_matrix[0] + 0.5;
//  AddMatrixTransform_SDK(my_matrix);
//  FinalizeColorPipeline_SDK();       // Apply changes.
//
// GetPendingColorImage_SDK() or GetPendingColorImageRGB8_SDK().
//
//  my_matrix[5] = my_matrix[5] + 0.5;
//  AddMatrixTransform_SDK(my_matrix);
//  FinalizeColorPipeline_SDK();       // Apply changes.
//
// GetPendingColorImage_SDK() or GetPendingColorImageRGB8_SDK().
//  
//
//------------------------------------------------------------------------------

//typedef int (*ADD_MATRIX_TRANSFORM_SDK         )(double *p3x3Matrix);
//typedef int (*ENABLE_MATRIX_TRANSFORM_SDK      )(int matrix_select, unsigned int output_bit_depth);
//typedef int (*SET_INPUT_TRANSFORM_SDK          )(int *lut_array, int columns, int bit_depth);
//typedef int (*SET_OUTPUT_TRANSFORM_SDK         )(int *lut_array, int columns, int bit_depth);
//typedef int (*CLEAR_COLOR_PIPELINE             )(void);
//typedef int (*FINALIZE_COLOR_PIPELINE_SDK      )(void);
//typedef int (*GET_PENDING_COLOR_IMAGE_SDK      )(void *image);
//typedef int (*GET_PENDING_COLOR_IMAGE_RGB8_SDK )(void *image);

