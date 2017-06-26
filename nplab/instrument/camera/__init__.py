# -*- coding: utf-8 -*-
"""
Created on Wed Jun 11 12:28:18 2014

@author: Richard Bowman
"""

import nplab.utils.gui #load Qt correctly - do this BEFORE traits
from nplab.utils.gui import QtCore, QtGui, QtWidgets, uic
from nplab.ui.ui_tools import UiTools
import threading
import numpy as np
import traceback
import os
import datetime
import time
from PIL import Image
import warnings
import pyqtgraph as pg
from weakref import WeakSet

from nplab.instrument import Instrument
from nplab.utils.notified_property import NotifiedProperty, DumbNotifiedProperty, register_for_property_changes


class CameraParameter(NotifiedProperty):
    """A quick way of creating a property that alters a camera parameter.
    
    The majority of cameras have some sort of mechanism for setting parameters
    like gain, integration time, etc. etc. that involves calling an API
    function that takes the property name as an argument.  This is a way
    of nicely wrapping up the boilerplate code so that these properties map
    onto properties of the camera object.
    
    NB the property will be read immediately after it's written, to ensure
    that the value we send to any listening controls/indicators is correct
    (otherwise we'd send them the value that was requested, even if it was
    not valid).  This behaviour can be disabled by setting read_back to False
    in the constructor.
    """
    def __init__(self, parameter_name, doc=None, read_back=True):
        """Create a property that reads and writes the given parameter.
        
        This internally uses the `get_camera_parameter` and 
        `set_camera_parameter` methods, so make sure you override them.
        """
        if doc is None:
            doc = "Adjust the camera parameter '{0}'".format(parameter_name)
        super(CameraParameter, self).__init__(fget=self.fget, 
                                                      fset=self.fset, 
                                                      doc=doc,
                                                      read_back=read_back)
        self.parameter_name = parameter_name
        
    def fget(self, obj):
        return obj.get_camera_parameter(self.parameter_name)
            
    def fset(self, obj, value):
        obj.set_camera_parameter(self.parameter_name, value)


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
        self.acquisition_lock = threading.Lock()    
        self._latest_frame_update_condition = threading.Condition()
        self._live_view = False
        self._frame_counter = 0
        # Ensure camera parameters get saved in the metadata.  You may want to override this in subclasses
        # to remove junk (e.g. if some of the parameters are meaningless)
#        self.metadata_property_names = self.metadata_property_names + tuple(self.camera_parameter_names())
        self.metadata_property_names = tuple(self.metadata_property_names) + tuple(self.camera_parameter_names())

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
        with self._latest_frame_update_condition:
            # We use the Condition object to block until a new frame appears
            # However we need to check that a new frame has actually been taken
            # so we use the frame counter.
            # NB the current implementation may be vulnerable to dropped frames
            # which will probably cause a timeout error.
            # Checking for frame_counter being >= target_frame is vulnerable to
            # overflow.
            target_frame = self._frame_counter + 1 + discard_frames
            expiry_time = time.time() + timeout
            while self._frame_counter != target_frame and time.time() < expiry_time:
                self._latest_frame_update_condition.wait(timeout) #wait for a new frame
            if time.time() >= expiry_time:
                raise IOError("Timed out waiting for a fresh frame from the video stream.")
            if raw:
                return self.latest_raw_frame
            else:
                return self.latest_frame
        
    def raw_snapshot(self):
        """Take a snapshot and return it.  No filtering or conversion."""
        raise NotImplementedError("Cameras must subclass raw_snapshot!")
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
        with self._latest_frame_update_condition:
            self._latest_raw_frame = frame
            self._frame_counter += 1
            self._latest_frame_update_condition.notify_all()
        
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
    
    def camera_parameter_names(self):
        """Return a list of names of parameters that may be set/read.
        
        This will list the names of all the members of this class that are 
        `CameraParameter`s - you should define one of these for each of the 
        properties of the camera you'd like to expose.
        
        If you need to support dynamic properties, I suggest you use a class
        factory, and add CameraParameters at runtime.  You could do this from
        within the class, but that's a courageous move.
        
        If you need more sophisticated control, I suggest subclassing
        `CameraParameter`, though I can't currently see how that would help...
        """
        # first, identify all the CameraParameter properties we've got
        p_list = []
        for p in dir(self.__class__):
            try:
                if isinstance(getattr(self.__class__, p), CameraParameter):
                    getattr(self,p)
                    p_list.append(p)
            except:
                delattr(self.__class__,p)
                pass
        return p_list
   #     return [p for p in dir(self.__class__)
    #              if isinstance(getattr(self.__class__, p), CameraParameter)]
    
    def get_camera_parameter(self, parameter_name):
        """Return the named property from the camera"""
        raise NotImplementedError("You must override get_camera_parameter to use it")
    def set_camera_parameter(self, parameter_name, value):
        """Return the named property from the camera"""
        raise NotImplementedError("You must override set_camera_parameter to use it")
    
    _live_view = False
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
                self._frame_counter = 0
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
            
    legacy_click_callback = None
    def set_legacy_click_callback(self, function):
        """Set a function to be called when the image is clicked.
        
        Warning: this is only for compatibility with old code and will be removed
        once camera_stage_mapper is updated!
        """
        self.legacy_click_callback = function
        if self._preview_widgets is not None:
            for w in self._preview_widgets:
                w.add_legacy_click_callback(self.legacy_click_callback)
            
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
        if self.legacy_click_callback is not None:
            new_widget.add_legacy_click_callback(self.legacy_click_callback)
        return new_widget
    
    def get_control_widget(self):
        """Return a widget that contains the camera controls but no image."""
        return CameraControlWidget(self)
        
    def get_parameters_widget(self):
        """Return a widget that controls the camera's settings."""
        return CameraParametersWidget(self)
        
    def get_qt_ui(self, control_only=False, parameters_only=False):
        """Create a QWidget that controls the camera.
        
        Specifying control_only=True returns just the controls for the camera.
        Otherwise, you get both the controls and a preview window.
        """
        if control_only:
            return self.get_control_widget()
        elif parameters_only:
            return self.get_parameters_widget(self)
        else:
            return CameraUI(self)
            
        
        
class CameraUI(QtWidgets.QWidget):
    """Generic user interface for a camera."""
    def __init__(self, camera):
        assert isinstance(camera, Camera), "instrument must be a Camera"
        #TODO: better checking (e.g. assert camera has color_image, gray_image methods)
        super(CameraUI, self).__init__()
        self.camera=camera
        
        # Set up the UI        
        self.setWindowTitle(self.camera.__class__.__name__)
        layout = QtWidgets.QVBoxLayout()
        # The image display goes at the top of the window
        self.preview_widget = self.camera.get_preview_widget()
        layout.addWidget(self.preview_widget)
        # The controls go in a layout, inside a group box.
        self.controls = self.camera.get_control_widget()
        layout.addWidget(self.controls)
        #layout.setContentsMargins(5,5,5,5)
        layout.setSpacing(5)
        self.setLayout(layout)
        
class CameraControlWidget(QtWidgets.QWidget, UiTools):
    """Controls for a camera (these are the really generic ones)"""
    def __init__(self, camera, auto_connect=True):
        assert isinstance(camera, Camera), "instrument must be a Camera"
        #TODO: better checking (e.g. assert camera has color_image, gray_image methods)
        super(CameraControlWidget, self).__init__()
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
        fname = QtWidgets.QFileDialog.getSaveFileName(
                                caption = "Select JPEG filename",
                                directory = os.path.join(os.getcwd(),datetime.date.today().strftime("%Y-%m-%d.jpg")),
                                filter = "Images (*.jpg *.jpeg)",
                            )
        j = Image.fromarray(cur_img)
        j.save(fname)
        
    def edit_camera_parameters(self):
        """Pop up a camera parameters dialog box."""
        self.camera_parameters_widget = self.camera.get_parameters_widget()
        self.camera_parameters_widget.show()
        
    description = DumbNotifiedProperty("Description...")
        
    def __del__(self):
        pass

class CameraParametersTableModel(QtCore.QAbstractTableModel):
    """Class to manage a Qt table of a camera's parameters.
    
    With thanks to http://stackoverflow.com/questions/11736560/edit-table-in-
    pyqt-using-qabstracttablemodel"""
    def __init__(self, camera, parent=None):
        super(CameraParametersTableModel, self).__init__(parent)
        self.camera = camera
        self.parameter_names = self.camera.camera_parameter_names()
        for parameter_name in self.parameter_names[:]:   #Added to prevent properties the camera does not posses from trying to appear in the list of parameters
            try:
                getattr(self.camera, parameter_name)
            except:
                self.parameter_names.remove(parameter_name)
        
        # Here, we register to get a callback if any of the parameters change
        # so that we stay in sync with the camera.
        self._callback_functions = dict()       
        for i, pn in enumerate(self.parameter_names):
            callback = self.callback_to_update_row(i)
            register_for_property_changes(self.camera, pn, callback)
            self._callback_functions[pn] = callback
    
    def callback_to_update_row(self, i):
        """Return a callback function that refreshes the i-th parameter."""
        def callback(value=None):
            index = self.createIndex(i, 1)
            self.dataChanged.emit(index, index)
        return callback
    
    def rowCount(self, parent):
        return len(self.parameter_names)
    
    def columnCount(self, parent):
        return 2
    
    def data(self, index, role=QtCore.Qt.DisplayRole):
        "Return the data for the table - property names left, values right."
        if not index.isValid() or role != QtCore.Qt.DisplayRole:
            return None    
        parameter_name = self.parameter_names[index.row()]
        if index.column() == 0:
            return parameter_name
        else:
            return getattr(self.camera, parameter_name)
    
    def headerData(self, i, orientation, role=QtCore.Qt.DisplayRole):
        "Return data for the headers."
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return ["Parameter Name", "Parameter Value"][i]
            else:
                return None
        return None
    
    def setData(self, index, value, role=QtCore.Qt.DisplayRole):
        """If the value is changed, update the corresponding property."""
        assert index.column() == 1, "Can only edit second column!"
        parameter_name = self.parameter_names[index.row()]
        try:
            float(value) # make sure the input is valid
        except:
            return False
        setattr(self.camera, parameter_name, float(value))
        self.dataChanged.emit(index, index) # signal that the data has changed.
        return True
        
    def flags(self, index):
        "Return flags to tell Qt that only the second column is editable."
        if index.column() == 1:
            return (QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | 
                    QtCore.Qt.ItemIsSelectable)
        else:
            return QtCore.Qt.ItemIsEnabled
    
class CameraParametersWidget(QtWidgets.QWidget, UiTools):
    """An editable table that controls a camera's acquisition parameters."""
    def __init__(self, camera, *args, **kwargs):
        super(CameraParametersWidget, self).__init__(*args, **kwargs)
        self.camera = camera
        self.table_model = CameraParametersTableModel(camera)
        self.table_view = QtWidgets.QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setCornerButtonEnabled(False)
        self.table_view.resizeColumnsToContents()
        self.table_view.horizontalHeader().setStretchLastSection(True)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.table_view)
        self.setLayout(layout)

class PreviewViewBox(pg.ViewBox):
    """A pyqtgraph ViewBox for use in the preview widget."""
    def suggestPadding(self, axis):
        """Return a value to use for the padding on a given axis.
        
        We always return zero so the image, by default, fills the window."""
        return 0
        
class PreviewImageItem(pg.ImageItem):
    legacy_click_callback = None
    def mouseClickEvent(self, ev):
        """Handle a mouse click on the image."""
        if ev.button() == QtCore.Qt.LeftButton:
            pos = np.array(ev.pos())
            if self.legacy_click_callback is not None:
                size = np.array(self.image.shape[:2])
                point = pos/size
                self.legacy_click_callback(point[1], point[0])
                ev.accept()
            else:
                pass
        else:
            super(PreviewImageItem, self).mouseClickEvent(ev)
    

class CameraPreviewWidget(pg.GraphicsView):
    """A Qt Widget to display the live feed from a camera."""
    update_data_signal = QtCore.Signal(np.ndarray)
    
    def __init__(self):
        super(CameraPreviewWidget, self).__init__()
        
        self.image_item = PreviewImageItem()
        self.view_box = PreviewViewBox(lockAspect=1.0, invertY=True)
        self.view_box.addItem(self.image_item)
        self.view_box.setBackgroundColor([128,128,128,255])
        self.setCentralWidget(self.view_box)
        self.crosshair = {'h_line': pg.InfiniteLine(pos=0,angle=0),
                          'v_line': pg.InfiniteLine(pos=0,angle=90),}
        for item in self.crosshair.values():
            self.view_box.addItem(item)
        self._image_shape = ()

        # We want to make sure we always update the data in the GUI thread.
        # This is done using the signal/slot mechanism
        self.update_data_signal.connect(self.update_widget, type=QtCore.Qt.QueuedConnection)

    def update_widget(self, newimage):
        """Set the image, but do so in the Qt main loop to avoid threading nasties."""
        # I've explicitly dealt with the datatype of the source image, to avoid
        # a bug in the way pyqtgraph interacts with numpy 1.10.  This means
        # scaling the display values will fail for integer data.  I've thus
        # forced floating-point for anything that isn't a u8, and assumed u8
        # wants to be displayed raw.  You can always use filter_function to
        # tweak the brightness/contrast.
        if newimage.dtype =="uint8":
            self.image_item.setImage(newimage.transpose((1,0,2)), autoLevels=False)
        else:
            self.image_item.setImage(newimage.transpose((1,0,2)).astype(float))
        if newimage.shape != self._image_shape:
            self._image_shape = newimage.shape
            self.set_crosshair_centre((newimage.shape[0]/2.0, newimage.shape[1]/2.0))
            
    def update_image(self, newimage):
        """Update the image displayed in the preview widget."""
        # NB compared to previous versions, pyqtgraph flips in y, hence the
        # funny slice on the next line.
        self.update_data_signal.emit(newimage)
        
    def add_legacy_click_callback(self, function):
        """Add an old-style (coordinates in fractions-of-an-image) callback."""
        self.image_item.legacy_click_callback = function
    
    def set_crosshair_centre(self, pos):
        """Move the crosshair to centre on a given pixel coordinate."""
        self.crosshair['h_line'].setValue(pos[0])
        self.crosshair['v_line'].setValue(pos[1])
        
        
class DummyCamera(Camera):
    exposure = CameraParameter("exposure", "The exposure time in ms.")
    gain = CameraParameter("gain", "The gain in units of bananas.")
    def __init__(self):
        super(DummyCamera, self).__init__()
        self._camera_parameters = {'exposure':40, 'gain':1}
    def raw_snapshot(self):
        ran = np.random.random((100,100,3))
        return True, (ran * 255.9).astype(np.uint8)
    def get_camera_parameter(self, name):
        return self._camera_parameters[name]
    def set_camera_parameter(self, name, value):
        self._camera_parameters[name] = value
        
if __name__ == '__main__':
    cam = DummyCamera()
    g=cam.show_gui(blocking=False)
    