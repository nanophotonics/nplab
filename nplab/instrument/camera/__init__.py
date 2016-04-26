# -*- coding: utf-8 -*-
"""
Created on Wed Jun 11 12:28:18 2014

@author: Richard Bowman
"""

import nplab.utils.gui #load Qt correctly - do this BEFORE traits
from nplab.utils.gui import QtCore, QtGui, uic
from nplab.ui.ui_tools import UiTools
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
from PIL import Image
import warnings
import pyqtgraph as pg
from weakref import WeakSet

from nplab.instrument import Instrument
from nplab.utils.notified_property import NotifiedProperty, DumbNotifiedProperty

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
          
          
class Camera(Instrument):
    """Generic class for representing cameras.
    
    This should always be subclassed in order to make a useful instrument.
    
    The minimum you should do is alter raw_snapshot to acquire and return a
    frame from the camera.  All other acquisition functions can come from that.
    If your camera also supports video streaming (for live view, for example)
    you should override     
    """
    
    video_priority = DumbNotifiedProperty(False)
    """Set video_priority to True to avoid disturbing the video stream when
    taking images.  raw_snapshot may ignore the setting, but get_image and by
    extension rgb_image and gray_image will honour it."""
    
    parameters = None
    
    filter_function = None 
    """This function is run on the image before it's displayed in live view.  
    It should accept, and return, an RGB image as its argument."""
    
    def __init__(self):
        super(Camera,self).__init__()
        self.initialise_parameters()
        self.acquisition_lock = threading.Lock()    
        self.latest_frame_updated = threading.Event()
        self._live_view = False
    
    def __del__(self):
        self.close()
#        super(Camera,self).__del__() #apparently not...?
    def close(self):
        """Stop communication with the camera and allow it to be re-used.
        
        override in subclass if you want to shut down hardware."""
        self.live_view = False
        
    
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
                raise IOError("Timed out waiting for a fresh frame from the video stream.")
                
        if raw:
            return self.latest_raw_frame
        else:
            return self.latest_frame
    
    def get_metadata(self):
        """Return a dictionary of camera settings."""
        ret = dict()
        for p in self.parameters:
            try:
                ret[p.name]=p.value
            except:
                pass #if there was a problem getting metadata, ignore it.
        return ret
        
    def raw_snapshot(self):
        """Take a snapshot and return it.  No filtering or conversion."""
        return True, np.zeros((640,480,3),dtype=np.uint8)
        
    def get_image(self):
        print "Warning: get_image is deprecated, use raw_image() instead."
        return self.raw_image()
        
    def raw_image(self, bundle_metadata=False, update_latest_frame=False):
        """Take an image from the camera, respecting video priority.
        
        If live view is enabled and video_priority is true, return the next
        frame in the video stream.  Otherwise, return a specially-acquired
        image from raw_snapshot.
        """
        frame = None
        if self.live_view and self.video_priority:
            frame = self.get_next_frame(raw=True)
        else:
            status, frame = self.raw_snapshot()
        if update_latest_frame:
            self.latest_raw_frame = frame
        # return it as an ArrayWithAttrs including self.metadata, if requested
        return self.bundle_metadata(frame, bundle_metadata)
            
    def color_image(self, **kwargs):
        """Get a colour image (bypass filtering, etc.)
        
        Additional keyword arguments are passed to raw_image."""
        frame = self.raw_image(**kwargs)
        try:
            assert frame.shape[2]==3
            return frame
        except:
            try:
                assert len(frame.shape)==2
                gray_frame = np.vstack((frame,)*3) #turn gray into color by duplicating!
                if hasattr(frame, "attrs"):
                    return ArrayWithAttrs(gray_frame, attrs=frame.attrs)
                else:
                    return gray_frame
            except:
                raise Exception("Couldn't convert the camera's raw image to colour.")
        
    def gray_image(self, **kwargs):
        """Get a colour image (bypass filtering, etc.)
        
        Additional keyword arguments are passed to raw_image."""
        frame = self.raw_image(**kwargs)
        try:
            assert len(frame.shape)==2
            return frame
        except:
            try:
                assert frame.shape[2]==3
                return np.mean(frame, axis=2, dtype=frame.dtype)
            except:
                raise Exception("Couldn't convert the camera's raw image to grayscale.")
                
    def save_raw_image(self, update_latest_frame=True, attrs={}):
        """Save an image to the default place in the default HDF5 file."""
        d=self.create_dataset('snapshot_%d', 
                              data=self.raw_image(
                                  bundle_metadata=True,
                                  update_latest_frame=update_latest_frame))
        d.attrs.update(attrs)
                
    def parameter_names(self):
        """Return a list of names of parameters that may be set."""
        return ['exposure','gain']
    
    _latest_raw_frame = None
    @NotifiedProperty
    def latest_raw_frame(self):
        """The last frame acquired by the camera.  
        
        This property is particularly useful when
        live_view is enabled.  This is before processing by any filter function
        that may be in effect.  May be NxMx3 or NxM for monochrome.  To get a
        fresh frame, use raw_image().  Setting this property will update any
        preview widgets that are in use."""
        return self._latest_raw_frame
    @latest_raw_frame.setter
    def latest_raw_frame(self, frame):
        """Set the latest raw frame, and update the preview widget if any."""
        self._latest_raw_frame = frame
        self.latest_frame_updated.set()
        
        # TODO: use the NotifiedProperty to do this with less code?
        if self._preview_widgets is not None:
            for w in self._preview_widgets:
                try:
                    w.update_image(self.latest_frame)
                except Exception as e:
                    print "something went wrong updating the preview widget"
                    print e
                
    @property
    def latest_frame(self):
        """The last frame acquired (in live view/from GUI), after filtering."""
        if self.filter_function is not None:
            return self.filter_function(self.latest_raw_frame)
        else:
            return self.latest_raw_frame
    
    
    def update_latest_frame(self, frame=None):
        """Take a new frame and store it as the "latest frame"
        
        Returns the image as displayed, including filters, etc.
        This should rarely be used - raw_image, color_image and gray_image are
        the preferred way of acquiring data.  If you supply an image, it will
        use that image as if it was the most recent colour image to be 
        acquired.
        
        Unless you need the filtered image, you should probably use 
        raw_image, color_image or gray_image.
        """
        if frame is None: 
            frame = self.color_image()
        if frame is not None:
            self.latest_raw_frame = frame
            
            return self.latest_frame
        else:
            print "Failed to get an image from the camera"    
    
    def initialise_parameters(self):
        """populate the list of camera settings that can be adjusted."""
        self.parameters = [CameraParameter(self, n) for n in self.parameter_names()]
            
    @NotifiedProperty
    def live_view(self):
        """Whether the camera is currently streaming and displaying video"""
        return self._live_view
    @live_view.setter
    def live_view(self, live_view):
        """Turn live view on and off.
        
        This is used to start and stop streaming of the camera feed.  The
        default implementation just repeatedly takes snapshots, but subclasses
        are encouraged to override that behaviour by starting/stopping a stream
        and using a callback function to update self.latest_raw_frame."""
        if live_view==True:
            if self._live_view:
                return # do nothing if it's going already.
            print "starting live view thread"
            try:
                self._live_view_stop_event = threading.Event()
                self._live_view_thread = threading.Thread(target=self._live_view_function)
                self._live_view_thread.start()
                self._live_view = True
            except AttributeError as e: #if any of the attributes aren't there
                print "Error:", e
        else:
            if not self._live_view:
                return # do nothing if it's not running.
            print "stopping live view thread"
            try:
                self._live_view_stop_event.set()
                self._live_view_thread.join()
                del(self._live_view_stop_event, self._live_view_thread)
                self._live_view = False
            except AttributeError:
                raise Exception("Tried to stop live view but it doesn't appear to be running!")
    def _live_view_function(self):
        """This function should only EVER be executed by _live_view_changed.
        
        Loop until the event tells us to stop, constantly taking snapshots.
        Ideally you should override live_view to start and stop streaming
        from the camera, using a callback function to update latest_raw_frame.
        """
        while not self._live_view_stop_event.wait(timeout=0.1):
            success, frame = self.raw_snapshot()
            self.update_latest_frame(frame)
            
    _preview_widgets = None
    def get_preview_widget(self):
        """A Qt Widget that can be used as a viewfinder for the camera.
        
        In live mode, this is continuously updated.  It's also updated whenever
        a snapshot is taken using update_latest_frame.  Currently this returns
        a single widget instance - in future it might be able to generate (and
        keep updated) multiple widgets."""
        if self._preview_widgets is None:
            self._preview_widgets = WeakSet()
        new_widget = CameraPreviewWidget()
        self._preview_widgets.add(new_widget)
        return new_widget
    
    def get_qt_ui(self, control_only=False):
        """Create a QWidget that controls the camera.
        
        Specifying control_only=True returns just the controls for the camera.
        Otherwise, you get both the controls and a preview window.
        """
        if control_only:
            return CameraControlUI(self)
        else:
            return CameraUI(self)
        
        
class CameraUI(QtGui.QWidget):
    """Generic user interface for a camera."""
    def __init__(self, camera):
        assert isinstance(camera, Camera), "instrument must be a Camera"
        #TODO: better checking (e.g. assert camera has color_image, gray_image methods)
        super(CameraUI, self).__init__()
        self.camera=camera
        
        # Set up the UI        
        self.setWindowTitle(self.camera.__class__.__name__)
        layout = QtGui.QVBoxLayout()
        # The image display goes at the top of the window
        self.preview_widget = self.camera.get_preview_widget()
        layout.addWidget(self.preview_widget)
        # The controls go in a layout, inside a group box.
        self.controls = self.camera.get_qt_ui(control_only=True)
        layout.addWidget(self.controls)
        #layout.setContentsMargins(5,5,5,5)
        layout.setSpacing(5)
        self.setLayout(layout)
        
class CameraControlUI(QtGui.QWidget, UiTools):
    """Controls for a camera (these are the really generic ones)"""
    def __init__(self, camera):
        assert isinstance(camera, Camera), "instrument must be a Camera"
        #TODO: better checking (e.g. assert camera has color_image, gray_image methods)
        super(CameraControlUI, self).__init__()
        self.camera=camera
        self.load_ui_from_file(__file__,"camera_controls_generic.ui")
        self.auto_connect_by_name(controlled_object=self.camera, verbose=False)
        
    def snapshot(self):
        """Take a new snapshot and display it."""
        self.camera.raw_image(update_latest_frame=True)
    
    def save_to_data_file(self):
        self.camera.save_raw_image(
            attrs={'description':self.description_lineedit.text()})
        
    def save_jpeg(self):
        cur_img = self.camera.color_image()
        fname = QtGui.QFileDialog.getSaveFileName(
                                caption = "Select JPEG filename",
                                directory = os.path.join(os.getcwd(),datetime.date.today().strftime("%Y-%m-%d.jpg")),
                                filter = "Images (*.jpg *.jpeg)",
                            )
        j = Image.fromarray(cur_img)
        j.save(fname)
        
    def __del__(self):
        pass

class CameraPreviewWidget(pg.GraphicsView):
    """A Qt Widget to display the live feed from a camera."""
    update_data_signal = QtCore.pyqtSignal(np.ndarray)
    
    def __init__(self):
        super(CameraPreviewWidget, self).__init__()
        
        self.image_item = pg.ImageItem()
        self.view_box = pg.ViewBox(lockAspect=True)
        self.view_box.addItem(self.image_item)
        self.view_box.setBackgroundColor([128,128,128,255])
        self.setCentralWidget(self.view_box)
        
        # We want to make sure we always update the data in the GUI thread.
        # This is done using the signal/slot mechanism
        self.update_data_signal.connect(self.update_widget, type=QtCore.Qt.QueuedConnection)
        self._image_shape = ()

    def update_widget(self, newimage):
        """Draw the canvas, but do so in the Qt main loop to avoid threading nasties."""
        self.image_item.setImage(newimage)
        
    def update_image(self, newimage):
        """Update the image displayed in the preview widget."""
        self.update_data_signal.emit(newimage.transpose((1,0,2)).astype(np.float))
        if self._image_shape != newimage.shape:
            self._image_shape = newimage.shape
            # TODO: autorange sensibly when the image changes size.
        
class DummyCamera(Camera):
    def raw_snapshot(self):
        ran = np.random.random((100,100,3))
        return True, (ran * 255.9).astype(np.uint8)
        
if __name__ == '__main__':
    cam = DummyCamera()
    cam.show_gui()