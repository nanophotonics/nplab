# -*- coding: utf-8 -*-
"""
Created on Wed Jun 11 12:28:18 2014

@author: Richard Bowman
"""

import nplab.utils.gui #load Qt correctly - do this BEFORE traits
import traits
from traits.api import HasTraits, Property, Instance, Float, String, Button, Bool, on_trait_change, Range
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
import os
import datetime
from PyQt4 import QtGui
from PIL import Image
import warnings

from nplab.instrument import Instrument

class CameraParameter(HasTraits):
    value = Property(Float(np.NaN))
    name = String()

    def __init__(self,parent,name):
        self.parent = parent
        self.name=name

    def _get_value(self):
        """get the value of this parameter"""
        pass
    
    def _set_value(self, value):
        """get the value of this parameter"""
        pass
    
    def default_traits_view(self):
        return View(Item(name="value", label=self.name),kind="live")


class ImageClickTool(enable.api.BaseTool):
    """This handles clicks on the image and relays them to a callback function"""
    def __init__(self,plot):
        super(ImageClickTool, self).__init__()
        self.plot = plot
        
    def normal_left_up(self, event):
        """Handle a regular click on the image.
        
        This calls the callback function with two numbers between 0 and 1,
        corresponding to X and Y on the image.  Multiply by image size to get
        pixel coordinates."""
        if hasattr(self, "callback"):
            self.callback(1.-self.plot.y_axis.mapper.map_data(event.y),
                          self.plot.x_axis.mapper.map_data(event.x),)
        else:
            print "Clicked on image:", \
            self.plot.y_axis.mapper.map_data(event.y),\
            self.plot.x_axis.mapper.map_data(event.x)
          
          
class Camera(Instrument, HasTraits):
    """Generic class for representing cameras.
    
    This should always be subclassed in order to make a useful instrument."""
    latest_frame = traits.trait_numeric.Array(dtype=np.uint8,shape=(None, None, 3))
    """the last frame acquired by the camera.  Particularly useful when
    live_view is enabled.  See also latest_frame_updated."""
    latest_raw_frame = traits.trait_numeric.Array()
    """the last frame acquired by the camera.  Particularly useful when
    live_view is enabled.  This is before processing by any filter function
    that may be in effect. See also latest_frame_updated."""
    
    latest_frame_updated = None
    """This threading.Event is set every time the latest frame is updated."""
    
    image_plot = Instance(Plot) #chaco plot used to display the latest frame
    take_snapshot = Button
    save_jpg_snapshot = Button
    save_snapshot = Button
    edit_camera_properties = Button
    
    live_view = Bool(False)
    """When live_view is true, the camera runs (in a background thread) and
    takes frames continuously, which can be displayed in a preview window or
    accessed using latest_frame."""
    
    video_priority = Bool(False)
    """Set video_priority to True to avoid disturbing the video stream when
    taking images.  raw_snapshot may ignore the setting, but get_image and by
    extension rgb_image and gray_image will honour it."""
    
    parameters = traits.trait_types.List(trait=Instance(CameraParameter))
    
    filter_function = None 
    """This function is run on the image before it's displayed in live view.  
    It should accept, and return, an RGB image as its argument."""
    
    description = String("Description...")
    zoom = Float(1.0)
    """Sets the zoom of the preview video (in the default camera UI)."""

    traits_view = View(VGroup(
                    Item(name="image_plot",editor=ComponentEditor(),show_label=False,springy=True),
                    VGroup(
                        HGroup(
                            Item(name="live_view"),
                            Item(name="zoom"),
                            Item(name="take_snapshot",show_label=False),
                            Item(name="edit_camera_properties",label="Properties",show_label=False),
                        ),
                        HGroup(
                            Item(name="description"),
                            Item(name="save_snapshot",show_label=False),
                            Item(name="save_jpg_snapshot",show_label=False),
                        ), 
                        springy=False,
                    ),
                    layout="split"), kind="live",resizable=True,width=500,height=600,title="Camera")
                
    properties_view = View(VGroup( #used to edit camera properties
                        Item(name="parameters",show_label=False,springy=True,
                         editor=traitsui.api.TableEditor(columns=
                             [ObjectColumn(name="name", editable=False),
                              ObjectColumn(name="value")])),
                        ),
                        kind="live",resizable=True,width=500,height=600,title="Camera Properties"
                    )
                    
    def __init__(self):
        super(Camera,self).__init__()
        self.initialise_parameters()
        self.acquisition_lock = threading.Lock()    
        self.latest_frame_updated = threading.Event()
        self._setup_plot()
        
    def __del__(self):
        self.close()
#        super(Camera,self).__del__() #apparently not...?
    def close(self):
        """Stop communication with the camera and allow it to be re-used.
        
        override in subclass if you want to shut down hardware."""
        self.live_view = False
        
    def _take_snapshot_fired(self): self.update_latest_frame()
    def update_latest_frame(self, frame=None):
        """Take a new frame and store it as the "latest frame".
        
        Returns the image as displayed, including filters, etc."""
        if frame is None: 
            frame = self.color_image()
        if frame is not None:
            self.latest_raw_frame = frame
            if self.filter_function is not None:
                self.latest_frame=self.filter_function(frame)
            else:
                self.latest_frame=frame #This doesn't duplicate latest_raw_frame thanks to numpy :)
            self.latest_frame_updated.set()
            return self.latest_frame
        else:
            print "Failed to get an image from the camera"
    
    def get_next_frame(self, timeout=60, discard_frames=0, 
                       assert_live_view=True, raw=True):
        """Wait for the next frame to arrive and return it.
        
        This function is mostly intended for acquiring frames from a video
        stream that's running in live view - it returns a fresh frame without
        interrupting the video.  If called with timeout=None when live view is
        false, it may take a very long time to return.
        
        @param: timeout: Maximum length of time to wait for a new frame.  None
        waits forever, but this may be a bad idea (could hang your script).
        @param: discard_frames: Wait for this many new frames before returning
        one.  This option is useful if the camera buffers frames, so you must
        wait for several frames to be acquired before getting a "fresh" one.
        The default setting of 0 means the first new frame that arrives is
        returned.
        @param: assert_live_view: If True (default) raise an assertion error if
        live view is not enabled - this function is intended only to be used
        when that is the case.
        @param: raw: The default (True) returns a raw frame - False returns the
        frame after processing by the filter function if any.
        """
        if assert_live_view:
            assert self.live_view, """Can't wait for the next frame if live view is not enabled!"""
        for i in range(discard_frames + 1): #wait for a fresh frame
            self.latest_frame_updated.clear() #reset the flag
            if not self.latest_frame_updated.wait(timeout): #wait for frame
                raise TimeoutError("Timed out waiting for a fresh frame from the video stream.")
                
        if raw:
            return self.latest_raw_frame
        else:
            return self.latest_frame
    
    def _save_snapshot_fired(self):
        d=self.create_dataset('snapshot', data=self.update_latest_frame(), attrs=self.get_metadata())
        d.attrs.create('description',self.description)
        
    def _save_jpg_snapshot_fired(self):
        cur_img = self.update_latest_frame()
        fname = QtGui.QFileDialog.getSaveFileName(
                                caption = "Select Data File",
                                directory = os.path.join(os.getcwd(),datetime.date.today().strftime("%Y-%m-%d.jpg")),
                                filter = "Images (*.jpg *.jpeg)",
                            )
        j = Image.fromarray(cur_img)
        j.save(fname)
        
    def get_metadata(self):
        """Return a dictionary of camera settings."""
        ret = dict()
        for p in self.parameters:
            try:
                ret[p.name]=p.value
            except:
                pass #if there was a problem getting metadata, ignore it.
        return ret
    
    def _edit_camera_properties_fired(self):
        self.edit_traits(view="properties_view")
        
    def raw_snapshot(self):
        """Take a snapshot and return it.  No filtering or conversion."""
        return True, np.zeros((640,480,3),dtype=np.uint8)
        
    def get_image(self):
        """Take an image from the camera, respecting video priority.
        
        If live view is enabled and video_priority is true, return the next
        frame in the video stream.  Otherwise, return a specially-acquired
        image from raw_snapshot.
        """
        if self.live_view and self.video_priority:
            return self.get_next_frame(raw=True)
        else:
            return self.raw_snapshot()
            
    def color_image(self):
        """Get a colour image (bypass filtering, etc.)"""
        ret, frame = self.get_image()
        try:
            assert frame.shape[2]==3
            return frame
        except:
            try:
                assert len(frame.shape)==2
                return np.vstack((frame,)*3) #turn gray into color by duplicating!
            except:
                return None
    def gray_image(self):
        """Get a colour image (bypass filtering, etc.)"""
        ret, frame = self.get_image()
        try:
            assert len(frame.shape)==2
            return frame
        except:
            try:
                assert frame.shape[2]==3
                return np.mean(frame, axis=2, dtype=frame.dtype)
            except:
                return None
                
    def parameter_names(self):
        """Return a list of names of parameters that may be set."""
        return ['exposure','gain']
    
    def _latest_frame_changed(self):
        """Update the Chaco plot with the latest image."""
        try:
            self._image_plot_data.set_data("latest_frame",self.latest_frame)
            self.image_plot.aspect_ratio = float(self.latest_frame.shape[1])/float(self.latest_frame.shape[0])
        except Exception as e:
            print "Warning: exception occurred when updating the image graph:", e
            print "=========== Traceback ============"
            traceback.print_exc()
            print "============== End ==============="
    
    def initialise_parameters(self):
        """populate the list of camera settings that can be adjusted."""
        self.parameters = [CameraParameter(self, n) for n in self.parameter_names()]
        
    def _zoom_changed(self):
        """Update the graph to reflect the value of zoom required"""
        r = self.image_plot.range2d
        for axisrange in [r.x_range, r.y_range]:
            axisrange.low = 0.5-0.5/self.zoom
            axisrange.high = 0.5+0.5/self.zoom

    def _setup_plot(self):
        """Construct the Chaco plot used for displaying the image"""
        
        self._image_plot_data = ArrayPlotData(latest_frame=self.latest_frame,
                                              across=[0,1],middle=[0.5,0.5])
        self.image_plot = Plot(self._image_plot_data)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore") #this line raises a futurewarning
            #it's a bug in Enable that's not been fixed for ages.
            self.image_plot.img_plot("latest_frame",origin="top left")
        self.image_plot.plot(("across","middle"),color="yellow") #crosshair
        self.image_plot.plot(("middle","across"),color="yellow")
        
        #remove the axes... there ought to be a neater way to do this!
        self.image_plot.underlays = [u for u in self.image_plot.underlays \
                                    if not isinstance(u, chaco.axis.PlotAxis)]
        self.image_plot.padding = 0 #fill the plot region with the image
        self.image_plot_tool = ImageClickTool(self.image_plot)
        self.image_plot.tools.append(self.image_plot_tool)

    def _live_view_changed(self):
        """Turn live view on and off"""
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
        
