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
import enable
import traceback

class CameraParameter(HasTraits):
    value = Property(Float(np.NaN))
    name = String()
    def __init__(self,videoCapture,parameter_name):
        self._cap = videoCapture
        self.name = parameter_name.title().replace('_',' ')
        try:
            self._parameter_ID = getattr(cv2.cv,'CV_CAP_PROP_'+parameter_name.upper().replace(' ','_'))
        except AttributeError:
            raise AttributeError("%s is not a valid capture property, try CameraParameter.list_names()")
    def _get_value(self):
        return self._cap.get(self._parameter_ID)
    def _set_value(self, value):
        return self._cap.set(self._parameter_ID, value)
    def default_traits_view(self):
        return View(Item(name="value", label=self.name),kind="live")
        
    @classmethod
    def list_names(cls):
        return [name.replace("CV_CAP_PROP_","") for name in dir(cv2.cv) if "CV_CAP_PROP_" in name ]

class ImageClickTool(enable.api.BaseTool):
    """This handles clicks on the image and relays them to a callback function"""
    def __init__(self,plot):
        super(ImageClickTool, self).__init__()
        self.plot = plot
    def normal_left_up(self, event):
        if hasattr(self, "callback"):
            self.callback(1.-self.plot.y_axis.mapper.map_data(event.y),
                          self.plot.x_axis.mapper.map_data(event.x),)
        else:
            print "Clicked on image:", \
            self.plot.y_axis.mapper.map_data(event.y),\
            self.plot.x_axis.mapper.map_data(event.x)
            
class Camera(HasTraits):
    latest_frame = traits.trait_numeric.Array(dtype=np.uint8,shape=(None, None, 3))
    image_plot = Instance(Plot)
    take_snapshot = Button
    live_view = Bool
    parameters = traits.trait_types.List(trait=Instance(CameraParameter))
    filter_function = None
    
    traits_view = View(VGroup(
                    Item(name="image_plot",editor=ComponentEditor(),show_label=False,springy=True),
                    HGroup(
                        VGroup(
                            Item(name="take_snapshot",show_label=False),
                            HGroup(Item(name="live_view")), #the hgroup is a trick to make the column narrower
                        springy=False),
                        Item(name="parameters",show_label=False,springy=True,
                             editor=traitsui.api.TableEditor(columns=
                                 [ObjectColumn(name="name", editable=False),
                                  ObjectColumn(name="value")])),
                    springy=False),
                ), kind="live",resizable=True,width=500,height=600,title="OpenCV Camera")
    
    def __init__(self,capturedevice=0):
        super(Camera,self).__init__()
        
        self.cap=cv2.VideoCapture(capturedevice)
        self._image_plot_data = ArrayPlotData(latest_frame=self.latest_frame,
                                              across=[0,1],middle=[0.5,0.5])
        self.image_plot = Plot(self._image_plot_data)
        self.image_plot.img_plot("latest_frame",origin="top left")
        self.image_plot.plot(("across","middle"),color="yellow")
        self.image_plot.plot(("middle","across"),color="yellow")
        #remove the axes... there ought to be a neater way to do this!
        self.image_plot.underlays = [u for u in self.image_plot.underlays \
                                    if not isinstance(u, chaco.axis.PlotAxis)]
        self.image_plot.padding = 0
        self.image_plot_tool = ImageClickTool(self.image_plot)
        self.image_plot.tools.append(self.image_plot_tool)

        self.parameters = [CameraParameter(self.cap, n) for n in CameraParameter.list_names()]        
        self.acquisition_lock = threading.Lock()        
        
    def __del__(self):
        self.close()
#        super(Camera,self).__del__() #apparently not...?
    def close(self):
        """Stop communication with the camera and allow it to be re-used."""
        self.live_view = False
        self.cap.release()
    def _take_snapshot_fired(self): self.update_latest_frame()
    def update_latest_frame(self, frame=None):
        """Take a new frame and store it as the "latest frame".  Return the image as displayed, including filters, etc."""
        if frame is None: 
            ret, frame = self.raw_snapshot()
        if frame is not None:
            rgbframe=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            if self.filter_function is not None:
                self.latest_frame=self.filter_function(rgbframe)
            else:
                self.latest_frame=rgbframe
            return self.latest_frame
        else:
            print "Dropped a frame! cv2 return value:", ret
    def raw_snapshot(self):
        """Take a snapshot and return it.  Bypass filters etc."""
        with self.acquisition_lock:
            for i in range(10):
                try:
                    ret, frame = self.cap.read()
                    assert ret, "Failed to capture a frame"
                    return ret, frame
                except:
                    print "Attempt number %d failed to capture a frame from the camera!"
        print "Camera.raw_snapshot() has failed to capture a frame."
        return false, None
    def color_image(self):
        """Get a colour image (bypass filtering, etc.)"""
        ret, frame = self.raw_snapshot()
        return cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
    def gray_image(self):
        """Get a colour image (bypass filtering, etc.)"""
        ret, frame = self.raw_snapshot()
        return cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
    def _latest_frame_changed(self):
        try:
            self._image_plot_data.set_data("latest_frame",self.latest_frame)
            self.image_plot.aspect_ratio = float(self.latest_frame.shape[1])/float(self.latest_frame.shape[0])
        except Exception as e:
            print "Warning: exception occurred when updating the image graph:", e
            print "=========== Traceback ============"
            traceback.print_exc()
            print "============== End ==============="
    def _live_view_changed(self):
        if self.live_view==True:
            print "starting live view thread"
            try:
                self._live_view_stop_event = threading.Event()
                self._live_view_thread = threading.Thread(target=self._live_view_function)
                self._live_view_thread.start()
            except AttributeError as e: #if any of the attributes aren't there
                print "Error:", e
        else:
            print "stopping live view thread"
            try:
                self._live_view_stop_event.set()
                self._live_view_thread.join()
                del(self._live_view_stop_event, self._live_view_thread)
            except AttributeError:
                raise Exception("Tried to stop live view but it doesn't appear to be running!")
    def _live_view_function(self):
        """this function should only EVER be executed by _live_view_changed."""
        while not self._live_view_stop_event.wait(timeout=0.1):
            self.update_latest_frame()
        
#example code:
if __name__ == "__main__":
    c = Camera(0)
    c.configure_traits()
    c.close()
    del c