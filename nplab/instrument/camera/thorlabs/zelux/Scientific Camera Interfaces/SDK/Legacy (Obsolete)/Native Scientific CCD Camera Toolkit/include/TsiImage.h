/******************************************************************************/
/* TsiImage.h                                                                 */
/*----------------------------------------------------------------------------*/
/*                                                                            */
/******************************************************************************/
#ifndef __THORLABS_SCIENTIFIC_IMAGING_IMAGE_H__
#define __THORLABS_SCIENTIFIC_IMAGING_IMAGE_H__

#include <cstring>

//==============================================================================
// TsiImage C++ Class
//------------------------------------------------------------------------------
//==============================================================================
class TsiImage
{
   //---------------------------------------------------------------------------
   // PUBLIC
   //---------------------------------------------------------------------------
   public:

      unsigned int m_Width;             // Width  of image in pixels.
      unsigned int m_Height;            // Height of image in pixels.
      unsigned int m_BitsPerPixel;      // The number of significant bits per pixel in the pixel data.
      unsigned int m_BytesPerPixel;     // The number of bytes consumed by a pixel. 
      unsigned int m_SizeInPixels;      // Size of image in pixels.
      unsigned int m_SizeInBytes;       // Size of image in bytes.
      unsigned int m_XBin;              // Horizontal binning value.
      unsigned int m_VBin;              // Vertical binning value.
      unsigned int m_ROI[4];            // The region of interest (subimage) 
                                        // that the pixels were gathered from.
                                        // Format: [x0, y0, x1, y1]
      unsigned int m_ExposureTime_ms;   // Exposure time in milliseconds.
      unsigned int m_FrameNumber;       // Frame number returned from frame grabber.

      //--------------------------------------------------------------------------
      // Image buffer data.
      //--------------------------------------------------------------------------
      union
      {
         void            *vptr;
         char             *i8;
         unsigned char    *ui8;
         short            *i16;
         unsigned short  *ui16;
         unsigned int    *ui32;
      } m_PixelData;                    // The pointers in this union point to
                                        // the address of the image buffer.


      //==========================================================================
      // TsiImage - Constructor.
      //==========================================================================
      TsiImage(void) 
      {
         m_Width                = 0;
         m_Height               = 0;
         m_BitsPerPixel         = 0; 
         m_BytesPerPixel        = 0;
         m_SizeInPixels         = 0;
         m_SizeInBytes          = 0;
         m_XBin                 = 0;   
         m_VBin                 = 0;    
         m_ROI[0]               = 0;      
         m_ROI[1]               = 0;      
         m_ROI[2]               = 0;      
         m_ROI[3]               = 0;      
         m_ExposureTime_ms      = 0;
         m_FrameNumber          = 0;

         m_ImageBuffer          = 0;
         m_ImageBufferAllocSize = 0;
         m_PixelData.vptr       = 0;


      };

      //==========================================================================
      // TsiImage - Destructor.
      //==========================================================================
      virtual ~TsiImage() 
      {
      };

      //==========================================================================
      // Copy - Copies an existing TsiImage's data.
      //--------------------------------------------------------------------------
      // If the image buffer (memory pointed to by m_PixelData) is not large
      // enough, it will attempt to allocate enough memory .
      //==========================================================================
      bool Copy(TsiImage *src)
      {
      unsigned char *src_data  = 0;
      unsigned char *dest_data = 0;
      int            num_bytes = 0;

         if(src == 0) return false; 

         m_Width            = src->m_Width;
         m_Height           = src->m_Height;
         m_BitsPerPixel     = src->m_BitsPerPixel; 
         m_BytesPerPixel    = src->m_BytesPerPixel;
         m_SizeInBytes      = src->m_SizeInBytes;
         m_XBin             = src->m_XBin;   
         m_VBin             = src->m_VBin;    
         m_ROI[0]           = src->m_ROI[0];      
         m_ROI[1]           = src->m_ROI[1];      
         m_ROI[2]           = src->m_ROI[2];      
         m_ROI[3]           = src->m_ROI[3];      
         m_ExposureTime_ms  = src->m_ExposureTime_ms;
	      m_FrameNumber      = src->m_FrameNumber;

         if(src->m_PixelData.vptr == 0)
         {
            return false;
         }

         if(m_ImageBufferAllocSize < m_SizeInBytes)
         {
            if(m_ImageBuffer != 0) 
            {
               delete(m_ImageBuffer);
               m_ImageBuffer          = 0;
               m_PixelData.vptr       = 0;
               m_ImageBufferAllocSize = 0;
            }

            m_ImageBuffer = (void *)new unsigned char[m_SizeInBytes];
            if(m_ImageBuffer == 0)
            {
               return false;
            }
            
            m_PixelData.vptr       = m_ImageBuffer;
            m_ImageBufferAllocSize = m_SizeInBytes;
         }

         num_bytes = m_SizeInBytes;
         src_data  = src->m_PixelData.ui8;
         dest_data = m_PixelData.ui8;
         //for(;0<num_bytes;--num_bytes) *dest_data++ = *src_data++;
         memcpy(m_ImageBuffer, src->m_PixelData.vptr, src->m_SizeInBytes);

         return true;
      }


      //==========================================================================
      // [STATIC] Clones - Creates a new duplicate of the specified TsiImage. 
      //--------------------------------------------------------------------------
      //==========================================================================
      static TsiImage *Clone(TsiImage *src)
      {
      TsiImage      *image     = 0;
      bool           success   = 0;

         if(src == 0) return image; 

         image = new TsiImage();
         if(image == 0) return image;

         success = image->Copy(src);
         if(success == false) 
         {
            delete(image);
            image = 0;
         }

         return image;
      }

   
   //---------------------------------------------------------------------------
   // PROTECTED
   //---------------------------------------------------------------------------
   protected:
      unsigned int m_ImageBufferAllocSize;
      void        *m_ImageBuffer;
};

#endif
