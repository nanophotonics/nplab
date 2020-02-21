# -*- coding: utf-8 -*-
"""
Created on Tue Jul 25 10:18:49 2017

@author: wmd22
"""
from __future__ import division
from __future__ import print_function


from builtins import zip
from builtins import str
from builtins import range
from past.utils import old_div
from numpy.lib.stride_tricks import as_strided
import cv2
import numpy as np
from nplab.utils.notified_property import DumbNotifiedProperty, NotifiedProperty, register_for_property_changes
from nplab.instrument import Instrument
from nplab.ui.ui_tools import QuickControlBox
from nplab.utils.image_with_location import ImageWithLocation

class Image_Filter_box(Instrument):
    threshold = DumbNotifiedProperty()
    bin_fac = DumbNotifiedProperty()
    min_size = DumbNotifiedProperty()
    max_size = DumbNotifiedProperty()
    bilat_height = DumbNotifiedProperty()
    bilat_size = DumbNotifiedProperty()
    morph_kernel_size = DumbNotifiedProperty()
    show_particles = DumbNotifiedProperty()
    return_original_with_particles = DumbNotifiedProperty()
    def __init__(self,threshold = 40, bin_fac = 4,min_size = 2,max_size = 6,
                 bilat_size = 3, bilat_height = 40, morph_kernel_size = 3):
        self.threshold = threshold
        self.bin_fac = bin_fac
        self.min_size = min_size
        self.max_size = max_size
        self.bilat_size = bilat_size
        self.bilat_height = bilat_height
        self.morph_kernel_size = morph_kernel_size
        self.filter_options = ['None','STBOC_with_size_filter','strided_rescale','StrBiThresOpen']
        self.show_particles = False
        self.return_original_with_particles = False
        self.current_filter_index = 0
        self.update_functions = []
    def current_filter(self,image):
        if self.current_filter_proxy == None:
            return image
        else:
            return self.current_filter_proxy(image)

    def set_current_filter_index(self,filter_index):
        filter_name = self.filter_options[filter_index]
        self._filter_index = filter_index
        if filter_name =='None':
              self.current_filter_proxy = None
        else:
            self.current_filter_proxy = getattr(self,filter_name)
        self._current_filter_str = filter_name
    def get_current_filter_index(self):
        return self._filter_index
    current_filter_index = NotifiedProperty(fget=get_current_filter_index,fset=set_current_filter_index)
    def STBOC_with_size_filter(self,g,return_centers = False):
        try:
            return STBOC_with_size_filter(g, bin_fac= self.bin_fac,
                                           bilat_size = self.bilat_size, bilat_height = self.bilat_height,
                                           threshold =self.threshold,min_size = self.min_size,max_size = self.max_size,
                                           morph_kernel_size = self.morph_kernel_size, show_particles = self.show_particles,
                                           return_original_with_particles = self.return_original_with_particles,return_centers = return_centers)
        except Exception as e:
            self.log('Image processing has failed due to: '+str(e),level = 'WARN')
    def strided_rescale(self,g):
        try:
            return strided_rescale(g, bin_fac= self.bin_fac)
        except Exception as e:
            self.log('Image processing has failed due to: '+str(e),level = 'WARN')
    
    def StrBiThresOpen(self,g):
        try:
            return StrBiThresOpen(g, bin_fac= self.bin_fac,
                                           bilat_size = self.bilat_size, bilat_height = self.bilat_height,
                                           threshold =self.threshold,
                                           morph_kernel_size = self.morph_kernel_size)
        except Exception as e:
            self.log('Image processing has failed due to: '+str(e),level = 'WARN')
    def connect_function_to_property_changes(self,function):
    #    print function
        for variable_name in vars(self.__class__):
            self.update_functions.append(function)
            if (type(getattr(self.__class__,variable_name)) == DumbNotifiedProperty or
                type(getattr(self.__class__,variable_name)) == NotifiedProperty):
                
                register_for_property_changes(self,variable_name,self.update_functions[-1])
        
    def get_qt_ui(self):
        return Camera_filter_Control_ui(self)
            
class Camera_filter_Control_ui(QuickControlBox):

    '''Control Widget for the Shamrock spectrometer
    '''
    def __init__(self,filter_box):
        super(Camera_filter_Control_ui,self).__init__(title = 'Camera_filter_Controls')
        self.filter_box = filter_box
        self.add_spinbox('threshold',vmin=-255,vmax=255)
        self.add_spinbox('bin_fac' , vmin=1)
        self.add_spinbox('bilat_size')
        self.add_spinbox('bilat_height')
        self.add_spinbox('min_size')
        self.add_spinbox('max_size')
        self.add_spinbox('morph_kernel_size')
        self.add_checkbox('show_particles')
        self.add_checkbox('return_original_with_particles')
        self.add_combobox('current_filter_index',options = self.filter_box.filter_options)
        self.auto_connect_by_name(controlled_object = self.filter_box)

            
def strided_rescale(g, bin_fac= 4):
    try:
        attrs = g.attrs
        return_image_with_loc = True
    except:
        return_image_with_loc = False
    g = g.sum(axis=2)
    try:
        strided = as_strided(g,
            shape=(g.shape[0]//bin_fac, g.shape[1]//bin_fac, bin_fac, bin_fac),
            strides=((g.strides[0]*bin_fac, g.strides[1]*bin_fac)+g.strides))
        strided = strided.sum(axis=-1).sum(axis=-1)
        strided = np.uint8((strided-np.min(strided))*254.0/(np.max(strided)-np.min(strided)))
        strided=strided.repeat(bin_fac,0)
        strided=strided.repeat(bin_fac,1)
        if return_image_with_loc==True:
            return ImageWithLocation(np.copy(strided),attrs = attrs)
        else:
            return np.copy(strided)
    except Exception as e:
        print(e)
        
def StrBiThresOpen(g, bin_fac= 4,threshold =40,bilat_size = 3,bilat_height = 40,morph_kernel_size = 3):
    try:
        strided = strided_rescale(g,bin_fac = bin_fac)
        strided = cv2.bilateralFilter(np.uint8(strided),bilat_size,bilat_size,50)
    #    strided[strided<threshold]=1
      #  strided = cv2.adaptiveThreshold(strided,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,\
     #       cv2.THRESH_BINARY,3,2)
        strided = cv2.adaptiveThreshold(strided,255,cv2.ADAPTIVE_THRESH_MEAN_C,cv2.THRESH_BINARY,101,-1*threshold)
        
        strided = cv2.bilateralFilter(np.uint8(strided),bilat_size,old_div(bilat_height,4),50)
      #  strided[strided>threshold]-=threshold
        kernel = np.ones((morph_kernel_size,morph_kernel_size),np.uint8)
        strided =cv2.morphologyEx(strided, cv2.MORPH_OPEN, kernel)
        strided = cv2.morphologyEx(strided, cv2.MORPH_CLOSE, kernel)
        strided[strided!=0]=255
        return np.copy(strided)
    except Exception as e:
        print(e)
        
def STBOC_with_size_filter(g, bin_fac= 4, bilat_size = 3, bilat_height = 40,
                           threshold =20,min_size = 2,max_size = 6,morph_kernel_size = 3,
                           show_particles = False, return_original_with_particles = False,
                           return_centers = False):
    try:
        g = np.copy(g)
        strided = StrBiThresOpen(g, bin_fac,threshold,bilat_size,bilat_height,morph_kernel_size)
        contours, hierarchy = cv2.findContours(strided,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)[-2:]
        centers = []
        radi = []
        for cnt in contours:
            (x,y),radius = cv2.minEnclosingCircle(cnt)
        #    center = (int(x),int(y))
            center = (int(x),int(y))
      #      radius = int(radius)+2
            if radius>max_size or radius<min_size:
                radius = int(radius)+2
                strided[center[1]-radius:center[1]+radius,center[0]-radius:center[0]+radius] = 0
            else:
                M = cv2.moments(cnt,binaryImage = True)
                center = (int(old_div(M['m10'],M['m00'])),int(old_div(M['m01'],M['m00'])))
                centers.append(center)
                radi.append(radius)
        if return_centers==True:
            return np.array(centers)[:,::-1]
        elif return_original_with_particles == True:
      #      g = cv2.cvtColor(g,cv2.COLOR_GRAY2RGB)
       #     g = g#/255.0
            for cnt,radius in zip(centers,radi):
                cv2.circle(g, cnt, int(radius*2), (255, 0, 0), 2)
            return g
        elif show_particles==True:

   #         strided =  cv2.cvtColor(strided,cv2.COLOR_GRAY2RGB)
      #      strided_copy = np.copy(strided)
            strided = strided[:,:,np.newaxis]
            strided = strided.repeat(3,axis = 2)
        #    strided=strided/255.0
            for cnt,radius in zip(centers,radi):
          #      print np.shape(strided_copy),  center
                cv2.circle(strided, cnt, int(radius*2), (255,0,0), 2)

        strided[strided!=0]=255
        return strided
        
   #     strided=strided.repeat(bin_fac, 0)
    #    strided=strided.repeat(bin_fac, 1)
 #       return strided
    except Exception as e:
        print(e)

def find_particles(self,img=None,border_pixels = 50):
    """find particles in the supplied image, or in the camera image"""
    self.threshold_image(self.denoise_image(
            cv2.cvtColor(frame,cv2.COLOR_RGB2GRAY)))[self.border_pixels:-self.border_pixels,self.border_pixels:-self.border_pixels] #ignore the edges
    labels, nlabels = ndimage.measurements.label(img)
    return [np.array(p)+15 for p in ndimage.measurements.center_of_mass(img, labels, list(range(1,nlabels+1)))] #add 15 onto all the positions

#def STBOC_with_size_filter_switch(g, bin_fac= 4,bilat_size = 3, bilat_height = 40,
#                           threshold =20,min_size = 2,max_size = 6,morph_kernel_size = 3):
# #   if len(g.shape)==3:
#    g = g.sum(axis=2)
# #   g[g<threshold] = 0
#    try:
#        g = cv2.bilateralFilter(np.uint8(g),bilat_size,bilat_height,50)
#        strided = as_strided(g,
#            shape=(g.shape[0]//bin_fac, g.shape[1]//bin_fac, bin_fac, bin_fac),
#            strides=((g.strides[0]*bin_fac, g.strides[1]*bin_fac)+g.strides))
#        strided = strided.sum(axis=-1).sum(axis=-1)
#        strided= np.uint8((strided-2-np.min(strided))/((np.max(strided)-np.min(strided))/255))
#        
#    #    strided[strided<threshold]=1
#      #  strided = cv2.adaptiveThreshold(strided,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,\
#     #       cv2.THRESH_BINARY,3,2)
#        strided = cv2.adaptiveThreshold(strided,255,cv2.ADAPTIVE_THRESH_MEAN_C,cv2.THRESH_BINARY,101,-1*threshold)
#        
#  #      strided = cv2.bilateralFilter(np.uint8(strided),bilat_size,bilat_height/4,50)
#      #  strided[strided>threshold]-=threshold
#        kernel = np.ones((morph_kernel_size,morph_kernel_size),np.uint8)
#        close_kernel = np.ones((2*morph_kernel_size,2*morph_kernel_size),np.uint8)
#        strided =cv2.morphologyEx(strided, cv2.MORPH_OPEN, kernel)
#        strided = cv2.morphologyEx(strided, cv2.MORPH_CLOSE, close_kernel)
#        strided, contours, hierarchy = cv2.findContours(strided,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
#        for cnt in contours:
#            (x,y),radius = cv2.minEnclosingCircle(cnt)
#            center = (int(x),int(y))
#      #      radius = int(radius)+2
#            if radius>max_size or radius<min_size:
#                radius = int(radius)+2
#                strided[center[1]-radius:center[1]+radius,center[0]-radius:center[0]+radius] = 0
#      #  strided= np.uint8((strided-2-np.min(strided))/((np.max(strided)-np.min(strided))/255))
#        return strided
#    except Exception as e:
#        print e
        
def build_strided_filter(func):
    def filter_func(image):
        return func(strided_rescale(image))
    return filter_func
#if __name__ == '__main__':
#    from nplab.instrument.camera.lumenera import LumeneraCamera
#    cam = LumeneraCamera(1)
#    cam.show_gui(blocking = False)
#    cam_filter = Camera_Filter_box()
#    cam_filter.show_gui(blocking = False)
#    cam.filter_function = cam_filter.STBOC_with_size_filter
