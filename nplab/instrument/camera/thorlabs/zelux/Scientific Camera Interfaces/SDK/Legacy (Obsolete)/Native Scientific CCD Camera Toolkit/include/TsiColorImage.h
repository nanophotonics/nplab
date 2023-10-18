#pragma once

#include "TsiImage.h"
#include "platform_specific.h"

class TsiColorImage : public TsiImage
{
public:
   TsiColorImage() : m_ColorImageSizeInBytes (0)
   {
      m_ColorPixelDataBGR.vptr = 0;
   }

   TsiColorImage (TsiImage* img) : m_ColorImageSizeInBytes (0)
   {
      Copy (img);
   }

   //--------------------------------------------------------------------------
   // Color image buffer data.
   //--------------------------------------------------------------------------
   union
   {
      void            *vptr;
      char             *i8;
      unsigned char    *ui8;
      short            *i16;
      unsigned short  *ui16;
      uint32_t        *ui32;

      struct
      {
         unsigned char b;
         unsigned char g;
         unsigned char r;
      } *BGR_8;   

      struct
      {
         unsigned short b;
         unsigned short g;
         unsigned short r;
      } *BGR_16;

      struct
      {
         uint32_t b;
         uint32_t g;
         uint32_t r;
      } *BGR_32;
   } m_ColorPixelDataBGR;                // The pointers in this union point to
                                         // the address of the image buffer.
   unsigned int m_ColorImageSizeInBytes; // Size of color image in bytes.

protected: 
};
