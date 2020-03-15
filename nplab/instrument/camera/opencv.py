# -*- coding: utf-8 -*-
"""
Created on Wed Jun 11 12:28:18 2014

@author: Richard
"""
from __future__ import print_function

from builtins import range
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
        print("uh oh, problem with the message...")
        print(e)
        pass
    finally:
        raise ImportError(explanation) 
    
from nplab.instrument.camera import Camera, CameraParameter
    
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
                    assert ret, "OpenCV's capture.read() returned False :("
                    if len(frame.shape) == 3:
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    return ret, frame
                except Exception as e:
                    print("Attempt number {0} failed to capture a frame from the camera!".format(i))
                    print(e)
        print("Camera.raw_snapshot() has failed to capture a frame.")
        if not suppress_errors:
            raise IOError("Dropped too many frames from camera :(")
        else:
            return False, None
        
    def get_camera_parameter(self, parameter_name):
        """Get the value of a camera parameter (though you should really use the property)"""
        return self.cap.get(getattr(cv2,parameter_name))
    def set_camera_parameter(self, parameter_name, value):
        """Set the value of a camera parameter (though you should really use the property)"""
        return self.cap.set(getattr(cv2,parameter_name), value)

# Add properties to change the camera parameters, based on OpenCV's parameters.
# It may be wise not to do this, and to filter them instead...
for cvname in dir(cv2):
    if cvname.startswith("CAP_PROP_"):
        name = cvname.replace("CAP_PROP_","").lower()
        setattr(OpenCVCamera, 
                name, 
                CameraParameter(cvname, doc="the camera property %s" % name))

if __name__ == '__main__':
    cam = OpenCVCamera()
    cam.show_gui()
