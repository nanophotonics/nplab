#pragma once

#include "TsiCamera.h"

class TsiColorImage;

enum TSI_TRANSFORM
{
   TSI_sRGB,
   TSI_RGB_Linear,
   TSI_sRGB8_24,
   TSI_sRGB8_32,
   TSI_PCS_48,
   TSI_Mono_12,
   TSI_Mono_14,
   TSI_Mono_16,
   TSI_Camera_Color_Correction,
   TSI_Default_White_Balance,
   TSI_Quick_Color_Configuration
};

enum TSI_COLOR_PROCESSING_MODE
{
   TSI_COLOR_DEMOSAIC,
   TSI_COLOR_POST_PROCESS
};

enum TSI_START_PIXEL
{
   TSI_R,
   TSI_B,
   TSI_Gr,
   TSI_Gb
};

enum TSI_PATTERN
{
   TSI_BAYER,
   TSI_TRUE_SENSE
};

// input = pointer to input data
// output = pointer to demosaiced data (returned by SDK)
// n = # of bytes in input buffer
// sp = the color of the upper right pixel (the starting pixel) for the color image sensor
// p = the layout of the color pixels
typedef void (*TSI_DEMOSAIC_FUNCTION)(int* input, int** output, int n, TSI_START_PIXEL sp, TSI_PATTERN p);

class TsiColorCamera : public TsiCamera
{
public:
   virtual bool SetDemosaicFunction (TSI_DEMOSAIC_FUNCTION f) = 0;
   virtual bool ConcatenateColorTransform (double* p3x3Matrix) = 0;
   virtual bool ConcatenateColorTransform (TSI_TRANSFORM t, unsigned int outputBitDepth) = 0;
   virtual bool SetInputTransform (int* pNx2pBmatrix, int N, int B) = 0;
   virtual bool SetOutputTransform (int* pMx2pBmatrix, int M, int B) = 0;
   virtual void ClearColorPipeline() = 0;
   virtual bool FinalizeColorPipeline() = 0;
   virtual TsiColorImage* GetPendingColorImage (TSI_COLOR_PROCESSING_MODE postProcess) = 0;
   virtual TsiColorImage* GetLastPendingColorImage (TSI_COLOR_PROCESSING_MODE postProcess) = 0;
   virtual bool FreeColorImage (TsiColorImage* tsi_img) = 0;
};
