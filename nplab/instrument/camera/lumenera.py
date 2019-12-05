# -*- coding: utf-8 -*-

"""
Lumenera camera wrapper for NPLab
=================================

This module wraps the lucam script from the legendary Christoph Gohlke 
<http://www.lfd.uci.edu/~gohlke/> and depends on having the lucam DLL installed
(most easily achieved by installing the Infinity Capture or Infinity Driver 
software from Lumenera's website).

@author: Richard Bowman (rwb27@cam.ac.uk)
"""
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import


from builtins import range
from past.utils import old_div
import sys
import time
import ctypes
# asVoidPtr = ctypes.pythonapi.PyCObject_AsVoidPtr #this function converts PyCObject to void *, why is it not in ctypes natively...?
# asVoidPtr.restype = ctypes.c_void_p #we need to set the result and argument types of the imported function
# asVoidPtr.argtypes = [ctypes.py_object]

try:
    from . import lucam
except WindowsError:
    explanation="""
WARNING: could not open the lucam driver.
    
Make sure you have installed the Infinity drivers (included with Infinity
Capture), and that its version matches your Python architecture (64 or 32 bit).
"""
    try:
        import traitsui.message
        traitsui.message.error(explanation,"Infinity Driver Missing", buttons=["OK"])
    except Exception as e:
        print("uh oh, problem with the message...")
        print(e)
        pass
    finally:
        raise ImportError(explanation) 

import numpy as np
from nplab.instrument.camera import Camera, CameraParameter, CameraControlWidget
from nplab.utils.notified_property import NotifiedProperty
from nplab.ui.ui_tools import QuickControlBox
        
class LumeneraCamera(Camera):
    last_frame_time = -1
    fps = -1
    
    
#    traits_view = View(VGroup(
#                Item(name="image_plot",editor=ComponentEditor(),show_label=False,springy=True),
#                HGroup(
#                    VGroup(
#                        VGroup(
#                            Item(name="exposure"),
#                            Item(name="zoom"),
#                            Item(name="gain"),
#                            Item(name="live_view")
#                            ), #the vgroup is a trick to make the column narrower
#                        HGroup(
#                            Item(name="edit_properties",show_label=False),
#                            Item(name="edit_video_properties",show_label=False),
#                            Item(name="edit_camera_properties",show_label=False),
#                        ),
#                    springy=False),
#                    VGroup(
#                        Item(name="take_snapshot",show_label=False),
#                        HGroup(Item(name="description")),
#                        Item(name="save_snapshot",show_label=False),
#                        Item(name="save_jpg_snapshot",show_label=False),
#                        HGroup(Item(name="video_priority")),
#                    springy=False),
#                springy=True),
#            layout="split"), kind="live",resizable=True,width=500,height=600,title="Camera")
    def __init__(self,camera_number=1):
        self.cam = lucam.Lucam(camera_number) #lucam is 1-indexed...
        self._camera_number = camera_number
        self._cameraIsStreaming = False
        
        #populate metadata - important in case we restart
        self.auto_restore_metadata = {'exposure':self.exposure, 'gain':self.gain,} #
        
        super(LumeneraCamera,self).__init__() #NB this comes after setting up the hardware
        self.metadata_property_names = ['gain', 'exposure']
        self.auto_crop_fraction = None
#        for pname in lucam.Lucam.PROPERTY.keys():
#            try:
#                getattr(self, pname)
#            except:
#                del lucam.Lucam.PROPERTY[pname]
#         #       del self.metadata_property_names[pname]
#                delattr(self.__class__,pname)
    
    def restart(self):
        """Close down the Lumenera camera, wait, and re-open.  Useful if it crashes."""
        live_view_setting = self.live_view 
        self.log("Attempting to restart camera")
        self.live_view = False
        self.cam.CameraClose()
        self.log("Camera closed")
        try:
            del self.cam
            self.log("Camera deleted")
        except Exception as e:
            print("Warning, an exception was raised deleting the old camera:\n{0}".format(e))
        time.sleep(2)
        self.log("Creating new camera object")
        self.cam = lucam.Lucam(self._camera_number)
        self.log("New camera object greated")
        self.log("Setting live view, gain and exposure")
        self.live_view = live_view_setting
        self.gain = self.auto_restore_metadata['gain']
        self.exposure = self.auto_restore_metadata['exposure']
        self.log("Camera restarted")
        
        
    def close(self):
        """Stop communication with the camera and allow it to be re-used."""
        self.live_view = False
        super(LumeneraCamera, self).close()
        self.cam.CameraClose()
        
    def raw_snapshot(self, suppress_errors=False, reset_on_error=True, retrieve_metadata=True,crop_fraction = None):
        """Take a snapshot and return it.  Bypass filters etc.
        
        @param: video_priority: If this is set to True, don't interrupt video
        streaming and just return the latest frame.  If it's set to false,
        stop the video stream, take a snapshot, and re-start the video stream.
        @param: suppress_errors: don't raise an exception if we can't get a 
        valid frame.
        @param: reset_on _error: attempt to turn the camera off and on again
        if it's not behaving(!)
        @param: retrieve_metadata: by default, we retrieve certain camera 
        parameters (gain, exposure, etc.) when we take a frame, and store them
        in self.metadata.  Set this to false to disable the behaviour."""
        #I removed logic for video priority here.  That belongs in raw_image.
        if self.auto_crop_fraction is not None:
            crop_fraction = self.auto_crop_fraction
        with self.acquisition_lock:
            for i in range(10):
                try:
                    # first we must construct the settings object.
                    # we need to make sure there's enough time in the timeout
                    # to cope with the exposure.
                    settings = self.cam.default_snapshot()
                    settings.timeout = self.cam.GetProperty('exposure')[0] + 500
                    frame = self.cam.TakeSnapshot(snapshot=settings)
                    assert frame is not None, "Failed to capture a frame"
                    frame_pointer = frame.ctypes.data_as(
                                        ctypes.POINTER(ctypes.c_byte))
                    image = self.convert_frame(frame_pointer,np.product(frame.shape))
                    if crop_fraction is not None:
                        x_size = old_div(int(image.shape[0]*crop_fraction),2)
                        x_mid = old_div(int(image.shape[0]),2)
                        y_size = old_div(int(image.shape[1]*crop_fraction),2)
                        y_mid = old_div(int(image.shape[1]),2)
                        image = image[x_mid-x_size:x_mid+x_size,y_mid-y_size:y_mid+y_size]
                    return True, image
                except Exception as e:
                    print("Attempt number {0} failed to capture a frame from the camera: {1}".format(i,e))
        print("Camera.raw_snapshot() has failed to capture a frame.")
        if reset_on_error:
            print("Camera dropped lots of frames.  Turning it off and on again.  Fingers crossed!")
            self.restart() #try restarting the camera!
            return self.raw_snapshot(suppress_errors=suppress_errors, 
                                     reset_on_error=False, #this matters: avoid infinite loop!
                                     )
        if not suppress_errors:
            raise IOError("Dropped too many frames from camera :(")
        else:
            return False, None
        
    def _streamingCallback(self, context, frame_pointer, frame_size):
        """This function is called on each frame that comes back from the camera when it's streaming.
        
        We keep track of the frame rate, and convert each frame to RGB so we 
        can store it in latest_image and thus update the GUI.
        """
        now = time.clock()
        self.fps = old_div(1,(now - self.last_frame_time))
        self.last_frame_time = now
        try:
            self.latest_raw_frame = self.convert_frame(frame_pointer, frame_size)
        except:
            print("invalid frame size")
            
    def convert_frame(self, frame_pointer, frame_size):
        """Convert a frame from the camera to an RGB numpy array."""
        f = self.cam.GetFormat()[0]
        w, h = f.width // (f.binningX * f.subSampleX), f.height // (f.binningY * f.subSampleY)
        assert frame_size == w*h, "The frame size did not match the image format!"
        converted_frame = self.cam.ConvertFrameToRgb24(f, frame_pointer) #actually convert the frame
        return converted_frame[:,:,::-1] #for some reason frames come back BGR - flip them to RGB
        
    def start_streaming(self):
        """Start streaming video from the camera as a preview.
        
        Don't call this function directly, use the live_view property."""
        self.cam.StreamVideoControl('start_streaming')
        # time.sleep(0.5)
        self._callback_id = self.cam.AddStreamingCallback(self._streamingCallback)
        self._cameraIsStreaming = True
        
    def stop_streaming(self):
        """Stop streaming video from the camera.
        
        Don't call this function directly, use the live_view function."""
        self.cam.StreamVideoControl('stop_streaming')
        # time.sleep(0.5)
        self.cam.RemoveStreamingCallback(self._callback_id)
        self._cameraIsStreaming = False
    
    @NotifiedProperty
    def live_view(self):
        """Whether the camera is currently streaming and displaying video"""
        return self._cameraIsStreaming
    @live_view.setter
    def live_view(self, live_view):
        """Turn live view on and off.
        
        This is used to start and stop streaming of the camera feed. """
        if live_view == self.live_view:
            return # Don't execute the start/stop functions twice.
        if live_view==True:
            self.start_streaming()
        else:
            self.stop_streaming()
        
    def get_camera_parameter(self, parameter_name):
        """Get the value of a camera setting.  But you should use the property..."""
        return self.cam.GetProperty(parameter_name)[0]
        
    def set_camera_parameter(self, parameter_name, value):
        """Get the value of a camera setting.  But you should use the property..."""
        self.cam.SetProperty(parameter_name, value)
        
    def get_metadata(self):
        """Return a dictionary of camera settings and parameters."""
        ret = super(LumeneraCamera, self).get_metadata()
        
        camid=self.cam.GetCameraId()
        version = self.cam.QueryVersion()
        interface = self.cam.QueryExternInterface()
        frame, fps = self.cam.GetFormat()
        depth = self.cam.GetTruePixelDepth()
        
        pixformat = 'raw8 raw16 RGB24 YUV422 Count Filter RGBA32 RGB48'.split()
        ret['camera_id'] = camid
        ret['camera_model'] = lucam.CAMERA_MODEL.get(camid, "Unknown")
        ret['serial_number'] = version.serialnumber
        ret['firmware_version'] = lucam.print_version(version.firmware)
        ret['FPGA_version'] = lucam.print_version(version.fpga)
        ret['API_version'] = lucam.print_version(version.api)
        ret['driver_version'] = lucam.print_version(version.driver)
        ret['Interface'] = lucam.Lucam.EXTERN_INTERFACE[interface]
        ret['image_offset'] = (frame.xOffset, frame.yOffset)
        ret['image_size'] = (frame.width // frame.binningX,
                                     frame.height // frame.binningY)
        if frame.flagsX:
            ret['binning'] = (frame.binningX, frame.binningY)
        else:
            ret['subsampling'] = (frame.subSampleX, frame.subSampleY)
        ret['pixel_format'] = pixformat[frame.pixelFormat]
        ret['bit_depth'] = (depth if frame.pixelFormat else 8)
        ret['frame_rate'] = fps
        return ret
    
    def show_camera_properties_dialog(self):
        """Display the camera's built-in properties dialog."""
        self.cam.DisplayPropertyPage(None)
    def show_video_format_dialog(self):
        """Display the camera's built-in video format dialog."""
        self.cam.DisplayVideoFormatPage(None)
    def get_control_widget(self):
        "Get a Qt widget with the camera's controls (but no image display)"
        return LumeneraCameraControlWidget(self)
        
class LumeneraCameraControlWidget(CameraControlWidget):
    """A control widget for the Lumenera camera, with extra buttons."""
    def __init__(self, camera, auto_connect=True):
        super(LumeneraCameraControlWidget, self).__init__(camera, auto_connect=False)
        gb = QuickControlBox()
        gb.add_doublespinbox("exposure")
        gb.add_doublespinbox("gain")
        gb.add_button("show_camera_properties_dialog", title="Camera Setup")
        gb.add_button("show_video_format_dialog", title="Video Format")
        self.layout().insertWidget(1, gb) # put the extra settings in the middle
        self.quick_settings_groupbox = gb        
        
        self.auto_connect_by_name(controlled_object=self.camera, verbose=False)
    

# this is slightly dangerous, but here we populate the camera with properties
# to set all the things in its list of properties.  We may want to prune this
# a little.
for pname in list(lucam.Lucam.PROPERTY.keys()):
    setattr(LumeneraCamera, pname, CameraParameter(pname))


if __name__ == "__main__":
    cam = LumeneraCamera(1)
    cam.show_gui(True)
    cam.close()
