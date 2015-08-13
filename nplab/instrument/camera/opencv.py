# -*- coding: utf-8 -*-
"""
Created on Wed Jun 11 12:28:18 2014

@author: Richard
"""

import sys
try:
    import cv2
except ImportError:
    explanation="""
WARNING: could not import the Open CV library.
    
Make sure you have installed OpenCV, and that its version matches your Python 
architecture (64 or 32 bit).  You can download a simple installer from:
http://www.lfd.uci.edu/~gohlke/pythonlibs/#opencv
We are using Python %d.%d, so get the corresponding package.
""" % (sys.version_info.major, sys.version_info.minor)
    try:
        import traitsui
        import traitsui.message
        traitsui.message.error(explanation,"OpenCV Missing", buttons=["OK"])
    except Exception as e:
        print "uh oh, problem with the message..."
        print e
        pass
    finally:
        raise ImportError(explanation) 
    
import cv2.cv
import traits
from traits.api import HasTraits, Property, Instance, Float, String, Button, Bool, on_trait_change
import traitsui
from traitsui.api import View, Item, HGroup, VGroup
from traitsui.table_column import ObjectColumn
import chaco
from chaco.api import ArrayPlotData, Plot
from enable.component_editor import ComponentEditor
import threading
import numpy as np

from nplab.instrument.camera import Camera, CameraParameter, ImageClickTool

class OpenCVCameraParameter(CameraParameter):
    value = Property(Float(np.NaN))
    name = String()
    def __init__(self, parent, parameter_name):
        self._cap = parent.cap
        self.name = parameter_name.title().replace('_',' ')
        try:
            self._parameter_ID = getattr(cv2.cv,'CV_CAP_PROP_'+parameter_name.upper().replace(' ','_'))
        except AttributeError:
            raise AttributeError("%s is not a valid capture property, try CameraParameter.list_names()")
            
    def _get_value(self):
        return self._cap.get(self._parameter_ID)
        
    def _set_value(self, value):
        return self._cap.set(self._parameter_ID, value)
        
           
class OpenCVCamera(Camera):
    def __init__(self,capturedevice=0):
        self.cap=cv2.VideoCapture(capturedevice)
        
        super(OpenCVCamera,self).__init__() #NB this comes after setting up the hardware
     
        
    def close(self):
        """Stop communication with the camera and allow it to be re-used."""
        super(OpenCVCamera, self).close()
        self.cap.release()
        
    def raw_snapshot(self, suppress_errors = False):
        """Take a snapshot and return it.  Bypass filters etc."""
        with self.acquisition_lock:
            for i in range(10):
                try:
                    ret, frame = self.cap.read()
                    assert ret, "Failed to capture a frame"
                    return ret, frame
                except Exception as e:
                    print "Attempt number {0} failed to capture a frame from the camera!".format(i)
                    exception = e
        print "Camera.raw_snapshot() has failed to capture a frame."
        if not suppress_errors:
            raise IOError("Dropped too many frames from camera :(")
        else:
            return False, None
        
    def parameter_names(self):
        return [name.replace("CV_CAP_PROP_","") for name in dir(cv2.cv) if "CV_CAP_PROP_" in name ]
    
    def initialise_parameters(self):
        self.parameters = [OpenCVCameraParameter(self,n) for n in self.parameter_names()]
        
    def color_image(self):
        """Get a colour image (bypass filtering, etc.)"""
        ret, frame = self.raw_snapshot()
        return cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        
    def gray_image(self):
        """Get a colour image (bypass filtering, etc.)"""
        ret, frame = self.raw_snapshot()
        return cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)


if __name__ == '__main__':
    cam = OpenCVCamera()
    cam.configure_traits()