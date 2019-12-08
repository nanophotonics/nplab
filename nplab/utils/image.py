# -*- coding: utf-8 -*-
"""
Created on Wed Oct 21 18:41:41 2015

@author: rwb27
"""
from __future__ import division
from __future__ import print_function

from past.utils import old_div
from nplab.utils.array_with_attrs import ArrayWithAttrs
import numpy as np
import cv2

def jpeg_encode(image, quality=90):
    """Encode an image from a numpy array to a JPEG.
    
    This function allows compressed JPEG images to be stored in an HDF5 file.
    You can pass in an OpenCV style image (i.e. an NxMx3 numpy array) and it
    will return a 1d array of uint8 that is smaller, depending on the
    quality factor specified.  It is returned as an array_with_attrs so that
    we can set attributes (that will be saved to HDF5 automatically) to say
    it was saved as a JPEG.
    """
    ret, encoded_array = cv2.imencode('.jpeg',image, 
                                      (cv2.cv.CV_IMWRITE_JPEG_QUALITY, quality))
    assert ret, "Error encoding image"
    jpeg = ArrayWithAttrs(encoded_array)
    jpeg.attrs.create("image_format", "jpeg")
    jpeg.attrs.create("jpeg_quality", quality)
    return jpeg
    
def jpeg_decode(image):
    """Unpack a compressed jpeg image into an uncompressed numpy array."""
    return cv2.imdecode(image, cv2.cv.CV_LOAD_IMAGE_COLOR)
    
def png_decode(image):
    """Unpack a compressed image into an uncompressed numpy array."""
    return cv2.imdecode(image, cv2.cv.CV_LOAD_IMAGE_COLOR)
    
def png_encode(image, compression=3):
    """Encode an image from a numpy array to a JPEG.
    
    This function allows compressed PNG images to be stored in an HDF5 file.
    You can pass in an OpenCV style image (i.e. an NxMx3 numpy array) and it
    will return a 1d array of uint8 that is smaller, depending on the
    quality factor specified.  It is returned as an array_with_attrs so that
    we can set attributes (that will be saved to HDF5 automatically) to say
    it was saved as a PNG.
    """
    ret, encoded_array = cv2.imencode('.png',image, 
                                      (cv2.cv.CV_IMWRITE_PNG_COMPRESSION, compression))
    assert ret, "Error encoding image"
    png = ArrayWithAttrs(encoded_array)
    png.attrs.create("image_format", "png")
    png.attrs.create("png_compression", compression)
    return png
    
def test_image_codecs():
    """Unit test for the image encoding/decoding functions"""
    noise = np.random.random((1000,1000,3))
    noise[300:700,300:700,:] *= 4
    noise *= 255.0/4
    img = noise.astype(np.uint8)
    
    print("image size is %d" % img.size)
    
    png = png_encode(img)
    print("PNG size is %d (%.d%%)" % (png.size, old_div((100*png.size),img.size)))
    assert png.size < img.size, "The PNG was bigger than the image!"
    
    jpeg = jpeg_encode(img)
    print("JPEG size is %d (%d%%)" % (jpeg.size, old_div((100*jpeg.size),img.size)))

    assert jpeg.size < img.size, "The JPEG was bigger than the image!"
    
    assert np.all(png_decode(png) == img), "The PNG did not uncompress losslessly."
    assert np.any(jpeg_decode(jpeg) != img), "The JPEG uncompressed losslessly - wtf?"
    
    jpeg_noise = jpeg_decode(jpeg).astype(np.float) - img
    print("JPEG differed from source image by %.2f RMS" % np.std(jpeg_noise))


if __name__ == '__main__':
    test_image_codecs()
