# -*- coding: utf-8 -*-
"""
@author: Ana Andres-Arroyo
GUI which controls a uc480 camera
"""
# documentation:
# http://instrumental-lib.readthedocs.io/en/latest/uc480-cameras.html

import os
import datetime
import time
from qtpy import QtCore, QtWidgets, uic
from scipy.misc import imsave
import pyqtgraph as pg
import numpy as np
import nplab
from nplab.ui.ui_tools import UiTools
from instrumental import list_instruments, instrument


class uc480(QtWidgets.QMainWindow, UiTools):
    """
    GUI which controls a uc480 camera.
    """
    
    def __init__(self, serial=False):
        super(self.__class__, self).__init__()
        # get the path of this file in case we are calling this class from another location
        file_path = os.path.dirname(__file__)
        ui_file = file_path + '\uc480_gui_design.ui'
        uic.loadUi(ui_file, self)
        
        # maximise GUI window
#        self.showMaximized()
        
        # set initial tabs to display
        self.SettingsTabWidget.setCurrentIndex(0) 
        
        # set initial splitter sizes
        self.splitter.setSizes([50,60000])
        
        # enable / disable push buttons
        self.reset_gui_without_camera()
      
        # connect GUI elements
        self.AutoExposurePushButton.clicked.connect(self.auto_exposure)
        self.TakeImagePushButton.clicked.connect(self.take_image)
        self.SaveImagePushButton.clicked.connect(self.save_image)
        self.NewFilePushButton.clicked.connect(self.new_hdf5_file)
        self.LiveViewCheckBox.stateChanged.connect(self.live_view)
        self.StartVideoPushButton.clicked.connect(self.acquire_video)
        self.OpenCameraPushButton.clicked.connect(self.open_camera_button)
        self.CloseCameraPushButton.clicked.connect(self.close_camera)    
        self.FindCamerasPushButton.clicked.connect(self.find_cameras)
                        
        # create live view widget
        image_widget = pg.GraphicsLayoutWidget()
        self.replace_widget(self.verticalLayout, self.LiveViewWidget, image_widget)
        view_box = image_widget.addViewBox(row=1,col=1)        
        self.imv = pg.ImageItem()
        self.imv.setOpts(axisOrder='row-major')
        view_box.addItem(self.imv)
        view_box.setAspectLocked(True)
        
        # populate image format combobox
        self.ImageFormatComboBox.addItem('hdf5',0)
        self.ImageFormatComboBox.addItem('png',1)
        self.ImageFormatComboBox.addItem('tiff',2)
        self.ImageFormatComboBox.addItem('jpg',3)
        self.ImageFormatComboBox.setCurrentIndex(0)    
        
        # populate video format combobox
        self.VideoFormatComboBox.addItem('hdf5',0)
        self.VideoFormatComboBox.setCurrentIndex(0)    

        # set df and df_gui to False until the hdf5 file is needed
        self.df = False
        self.df_gui = False

        # open camera
        self.open_camera(serial)
        
        # set initial parameters
        self.file_path = ''
        self.ExposureTimeNumberBox.setValue(2)
        self.FramerateNumberBox.setValue(10)
        self.DisplayFramerateNumberBox.setValue(10)
        self.GainNumberBox.setValue(0)
        self.GammaNumberBox.setValue(1)
        self.BlacklevelNumberBox.setValue(255)       
        self.ROICheckBox.setChecked(True)
        self.ROIWidthCheckBox.setChecked(True)
        self.ROIHeightCheckBox.setChecked(True)
        self.ROIWidthNumberBox.setValue(self.camera.max_width)
        self.ROIHeightNumberBox.setValue(self.camera.max_height)
#        self.ROIWidthNumberBox.setValue(700)
#        self.ROIHeightNumberBox.setValue(300)
        
        # take image with the initial parameters and calculate the best exposure
        self.auto_exposure()
    
    def open_camera_button(self):
        """Read serial number from GUI and connect to the camera."""
        serial = self.SerialComboBox.currentText()
        self.open_camera(serial=serial)
    
    def open_camera(self, serial=False):
        """Connect to a uc480 camera.""" 
        print 'Attempting to connect to the camera...'
        if serial: 
            print "Serial number: %s" %serial
            self.camera = instrument(serial=serial) # specified camera
        else: 
            print "Available instruments:"
            print list_instruments()
            self.camera = instrument('uc480') # default camera
        
        # set the camera gui buttons
        self.reset_gui_with_camera()
        print 'Camera connection successful.\n'  
        self.find_cameras()
        
        # set camera width and height labels
        self.CameraWidthLabel.setText(str(self.camera.max_width))
        self.CameraHeightLabel.setText(str(self.camera.max_height)) 
        
        # determine which camera parameters can be set        
        try: 
            self.camera.gamma = int(self.GammaNumberBox.value())
            self.set_gamma = True
        except: 
            print "WARNING: Can't set gamma.\n"
            self.set_gamma = False              
        try: 
            self.camera.auto_whitebalance = self.AutoWhitebalanceCheckBox.checkState() 
            self.set_whitebalance = True
        except: 
            print "WARNING: Can't set auto_whitebalance.\n"
            self.set_whitebalance = False    
        
        # initialise the attributes dictionary
        self.attributes = dict()

        # take first image        
        self.take_image()        
        
    def close_camera(self):
        """Close the uc480 camera connection.""" 
        self.camera.close()
        self.reset_gui_without_camera()
        print 'Camera connection closed.\n'  
        del self.camera
        self.camera = False
        
    def closeEvent(self, event):
        """This will happen when the GUI is closed."""
        # close the camera connection
        if self.camera: self.close_camera()
        # close the datafile
        if self.df: self.df.close()
        # close the databrowser gui
        if self.df_gui: self.df_gui.close()
    
    def find_cameras(self):
        """Find serial numbers of available cameras."""
        drivers = list_instruments()
        self.SerialComboBox.clear()
        for driver in drivers:
            if driver['classname'] == 'UC480_Camera':
                self.SerialComboBox.addItem(driver['serial'])
        try:
            serial = self.camera.serial
            index = self.SerialComboBox.findText(serial)
            self.SerialComboBox.setCurrentIndex(index)
        except:
            print "No camera is currently open.\n"
    
    def take_image(self):
        """Grab an image and display it."""
        image = self.grab_image()
        self.display_image(image)
        return image

    def get_brightest_pixel(self, image):
        """Get the brightest pixel value from the image."""
        brightest_pixel = np.amax(image)
        self.CurrentMaxGrayLabel.setText(str(brightest_pixel))
        return brightest_pixel
        
    def auto_exposure(self):
        """Get parameters from the gui and set auto exposure."""
        min_gray = self.MinGrayNumberBox.value()
        max_gray = self.MaxGrayNumberBox.value()
        precision = self.ExposureTimePrecisionNumberBox.value()
        self.set_auto_exposure(min_gray=min_gray, max_gray=max_gray, precision=precision)
    
    def set_auto_exposure(self, min_gray=200, max_gray=250, precision=1, max_attempts=10):
        """Determine the optimal exposure time."""
        image = self.take_image()
        brightest_pixel = self.get_brightest_pixel(image)
        okay = True
        attempt = 0
        
        while (brightest_pixel > max_gray or brightest_pixel < min_gray) and okay:
            attempt += 1
            current_exposure = float(self.CurrentExposureLabel.text())
            
            # adjust the exposure time
            if brightest_pixel > max_gray:
                print "REDUCE exposure time...\n"
                new_exposure = current_exposure/2
            elif brightest_pixel < min_gray:
                print "INCREASE exposure time...\n"
                new_exposure = current_exposure/brightest_pixel*max_gray*0.99
            
            # try the new exposure time
            self.ExposureTimeNumberBox.setValue(new_exposure)
            image = self.take_image()
            brightest_pixel = self.get_brightest_pixel(image)            
            previous_exposure = current_exposure
            current_exposure = float(self.CurrentExposureLabel.text())
            self.ExposureTimeNumberBox.setValue(current_exposure)
            
            # don't keep on trying the same exposure
            if np.abs(previous_exposure - current_exposure) < precision: okay = False 
            # don't keep on trying forever
            if attempt > max_attempts: okay = False 

            # update the gui
            QtWidgets.qApp.processEvents()

        
    def display_image(self, image):
        """Display the latest captured image."""
        # make a copy of the data so it can be accessed when saving an image
        self.image = image
        # set levels to [0,255] because otherwise it autoscales when plotting
        self.imv.setImage(image, autoDownsample=True, levels=[0,255])   
    
    def display_camera_parameters(self, camera_parameters):
        """Display the current camera parameters on the GUI."""
        self.CurrentFramerateLabel.setText(str(camera_parameters['framerate']))
        self.CurrentExposureLabel.setText(str(camera_parameters['exposure_time']))
        self.CurrentWidthLabel.setText(str(camera_parameters['width']))
        self.CurrentHeightLabel.setText(str(camera_parameters['height']))
        self.MaxWidthLabel.setText(str(camera_parameters['max_width']))
        self.MaxHeightLabel.setText(str(camera_parameters['max_height']))  
        self.CurrentMasterGainLabel.setText(str(camera_parameters['master_gain']))
        self.CurrentGainBoostLabel.setText(str(camera_parameters['gain_boost']))
        self.CurrentBlacklevelLabel.setText(str(camera_parameters['blacklevel_offset']))
        self.CurrentAutoBlacklevelLabel.setText(str(camera_parameters['auto_blacklevel']))
        if self.set_whitebalance: self.CurrentAutoWhitebalanceLabel.setText(str(camera_parameters['auto_whitebalance']))
        if self.set_gamma: self.CurrentGammaLabel.setText(str(camera_parameters['gamma']))
    
    def get_camera_parameters(self):
        """Read parameter values from the camera."""
        camera_parameters = dict()
        camera_parameters['framerate'] = self.camera.framerate.magnitude
        camera_parameters['exposure_time'] = self.camera._get_exposure().magnitude
        camera_parameters['width'] = self.camera.width
        camera_parameters['max_width'] = self.camera.max_width
        camera_parameters['height'] = self.camera.height
        camera_parameters['max_height'] = self.camera.max_height        
        camera_parameters['master_gain'] = self.camera.master_gain
        camera_parameters['gain_boost'] = self.camera.gain_boost
        camera_parameters['blacklevel_offset'] = self.camera.blacklevel_offset
        camera_parameters['auto_blacklevel'] = self.camera.auto_blacklevel
        if self.set_whitebalance: camera_parameters['auto_whitebalance'] = self.camera.auto_whitebalance
        if self.set_gamma: camera_parameters['gamma'] = self.camera.gamma
        return camera_parameters
        
    def set_video_parameters(self):
        """Read parameters from the GUI and return a dictionary."""
        video_parameters = self.set_capture_parameters()        
        framerate = "{} hertz".format(str(self.FramerateNumberBox.value()))
        video_parameters['framerate'] = framerate                
        return video_parameters
            
    def set_capture_parameters(self):
        """Read parameters from the GUI and return a dictionary."""
        capture_parameters = dict()
        exposure_time = "{} millisecond".format(str(self.ExposureTimeNumberBox.value()))        
        capture_parameters['exposure_time'] = exposure_time
        capture_parameters['gain'] = float(self.GainNumberBox.value())
        capture_parameters['vbin'] = int(self.VBinNumberBox.value())
        capture_parameters['hbin'] = int(self.HBinNumberBox.value())
        capture_parameters['vsub'] = int(self.VSubNumberBox.value())
        capture_parameters['hsub'] = int(self.HSubNumberBox.value())        
        capture_parameters = self.set_ROI(capture_parameters)
        self.set_camera_properties()          
        return capture_parameters
    
    def set_camera_properties(self):
        """Read parameters from the GUI and set the corresponding camera properties."""
        self.camera.auto_blacklevel = self.AutoBlacklevelCheckBox.checkState()
        self.camera.blacklevel_offset = int(self.BlacklevelNumberBox.value())         
        self.camera.gain_boost = self.GainBoostCheckBox.checkState()
        if self.set_gamma: self.camera.gamma = int(self.GammaNumberBox.value())
        if self.set_whitebalance: self.camera.auto_whitebalance = self.AutoWhitebalanceCheckBox.checkState()            
    
    def set_ROI(self, parameters_dict):
        """Read ROI coordinates from the GUI."""
        ROI_dict = {'width':[self.ROIWidthCheckBox, self.ROIWidthNumberBox],
                    'height':[self.ROIHeightCheckBox, self.ROIHeightNumberBox],
                    'left':[self.ROILeftEdgeCheckBox, self.ROILeftEdgeNumberBox],
                    'right':[self.ROIRightEdgeCheckBox, self.ROIRightEdgeNumberBox],
                    'top':[self.ROITopEdgeCheckBox, self.ROITopEdgeNumberBox],
                    'bottom':[self.ROIBottomEdgeCheckBox, self.ROIBottomEdgeNumberBox],
                    'cx':[self.ROICentreXCheckBox, self.ROICentreXNumberBox],
                    'cy':[self.ROICentreYCheckBox, self.ROICentreYNumberBox],
                    }
        
        # clear all of the old ROI parameters
        for item in ROI_dict.keys():
            if item in parameters_dict.keys():
                del parameters_dict[item]
        
        # use maximum width and height available
        parameters_dict['width'] = self.camera.max_width
        parameters_dict['height'] = self.camera.max_height
        
        # repopulate ROI parameters with the selected ones
        if self.ROICheckBox.checkState():            
            for item in ROI_dict.keys():
                if ROI_dict[item][0].checkState():
                    parameters_dict[item] = int(ROI_dict[item][1].value())
        
        return parameters_dict

        
    def grab_image(self):
        """Grab an image with the camera."""
        # set the desired capture parameters and update the attributes
        capture_parameters = self.set_capture_parameters()
        self.attributes.update(capture_parameters)
        
        # get the capture_timestamp with millisecond precision
        # insert a T to match the creation_timestamp formatting
        self.attributes['capture_timestamp'] = str(datetime.datetime.now()).replace(' ', 'T')

        # grab the image
        image = self.camera.grab_image(**capture_parameters)
        self.get_brightest_pixel(image)
        print 'Image grabbed.\n'

        # get and display the camera parameters and update the attributes
        camera_parameters = self.get_camera_parameters()
        self.display_camera_parameters(camera_parameters)    
        self.attributes.update(camera_parameters)               
        return image
        
    def get_info(self):
        """Get info from the GUI."""
        info = dict()
        info['description'] = self.DescriptionLineEdit.text()
        return info
        
    def save_image(self, dummy_variable=False, group_name='images'):
        """Save the latest image."""
        # make a copy of the image so the saved image is the one that was on the 
        # screen when the save button was pressed, not when the file name was chosen
        image = self.image
        image_format = self.ImageFormatComboBox.currentText()
        
        if image_format == 'hdf5':
            # update the attributes dictionary
            self.attributes.update(self.get_info())
            # get the datafile
            if not self.df: self.new_hdf5_file()
            # write data in the "images" group within the datafile
            dg = self.df.require_group(name=group_name)
            # write data to the file
            dg.create_dataset("image_%d", data=image, attrs=self.attributes)
            dg.file.flush()
            print "Image saved to the hdf5 file.\n"
            
        else:
            # user input to choose file name
            self.file_path = QtWidgets.QFileDialog.getSaveFileName(self, 'Save image', 
                                                                   self.file_path, 
                                                                   "(*."+self.ImageFormatComboBox.currentText()+")")
            if len(self.file_path):        
                # save image            
                imsave(self.file_path, np.flip(image, axis=0))
                print "Image saved: " + self.file_path + "\n"
            else:
                print "WARNING: Image wasn't saved.\n" 

    def new_hdf5_file(self):     
        """Open a new HDF5 file and its databrowser GUI."""
        # close the datafile
        if self.df: self.df.close() 
        # open new datafile
        self.df = nplab.current_datafile()
        # close the databrowser gui
        if self.df_gui: self.df_gui.close() 
        # open new databrowser gui
        self.df_gui = self.df.show_gui(blocking=False)                    
        # update the file name on the camera gui
        self.FilePathLineEdit.setText(self.df.filename)
        print       
        
    def live_view(self):
        """Continous image acquisition."""
        if self.LiveViewCheckBox.isChecked():                      
            # enable/disable gui buttons
            self.StopVideoPushButton.setEnabled(False)          
            # create thread
            self.LiveView = LiveViewThread(self.camera)
            # connect thread
            self.LiveViewCheckBox.stateChanged.connect(self.LiveView.terminate)
            self.LiveView.finished.connect(self.terminate_live_view)
            # live view
            print "Live view..."
            self.start_live_view(save=False)                      
            
    def acquire_video(self):
        """Acquire video frames."""            
        # enable/disable gui buttons          
        self.LiveViewCheckBox.setEnabled(False)
        self.StopVideoPushButton.setEnabled(True)
        self.SaveImagePushButton.setEnabled(False)    
        # create thread
        self.LiveView = LiveViewThread(self.camera)
        # connect thread
        self.StopVideoPushButton.clicked.connect(self.LiveView.terminate)
        self.LiveView.finished.connect(self.terminate_video_acquisition)
        # live view
        self.start_live_view(save=True)        
        
    def start_live_view(self, save=False):
        """Start continuous image acquisition."""
        # enable/disable gui buttons
        self.TakeImagePushButton.setEnabled(False)
        self.AutoExposurePushButton.setEnabled(False)
        self.StartVideoPushButton.setEnabled(False)
        self.OpenCameraPushButton.setEnabled(False)
        self.CloseCameraPushButton.setEnabled(False)
        self.NewFilePushButton.setEnabled(False)
        
        # connect signals
        self.LiveView.display_signal.connect(self.display_image)
        self.LiveView.attributes_signal.connect(self.update_attributes)
        
        # set video_parameters and update thread attributes
        video_parameters = self.set_video_parameters()
        self.LiveView.attributes.update(video_parameters)
                
        # start live view
        self.LiveView.live_view(video_parameters, 
                                      save=save,
                                      timeout=self.TimeoutNumberBox.value(),                                       
#                                      max_frames=self.MaxFramesNumberBox.value(),
                                      max_frames=float('inf'),
                                      display_framerate=self.DisplayFramerateNumberBox.value(),
                                      )
        
        # get and display camera parameters and update thread attributes
        camera_parameters = self.get_camera_parameters()    
        self.display_camera_parameters(camera_parameters)
        self.LiveView.attributes.update(camera_parameters)
        self.LiveView.attributes.update(self.get_info())
        
        # start continuous image acquisition
        self.LiveView.start()
    
    def update_attributes(self, attributes):
        """Update attributes dictionary and display on the GUI."""
        self.attributes.update(attributes)   
        self.display_camera_parameters(self.attributes)           
    
    def terminate_live_view(self):
        """This will run when the live view thread is terminated."""
        print "Finished live view.\n"
        self.delete_thread()
        
    def terminate_video_acquisition(self):
        """This will run when the video acquisition thread is terminated."""
        print "Finished acquiring video.\n"
        self.save_video()        
        self.delete_thread()
        
    def delete_thread(self):    
        """Delete the live view thread and reset the GUI."""
        # stop live video mode
        self.camera.stop_live_video()
        # delete the thread to free up memory
        del self.LiveView        
        # remove some attribute keys so they don't get recorded in still images
        attributes_keys_del = ['capture_time_sec', 'max_frames', 'timeout']
        for key in attributes_keys_del:
            if attributes_keys_del in self.attributes.keys():
                del self.attributes[key]
        # reset the gui buttons
        self.reset_gui_with_camera()    
    
    def save_video(self):
        """Save the acquired video into a file."""
        print "Saving video to file, please wait for a while..."            
        # TODO: allow saving as different file formats other than hdf5
        # TODO: write hdf5 data renderer for saved video from the colour camera
        
        # disable the GUI whilst the video is being saved
        self.setEnabled(False)
        
        QtWidgets.qApp.processEvents()
        # get the datafile
        if not self.df: self.new_hdf5_file()
        # get the "videos" group within the datafile
        datagroup = self.df.require_group("videos")
        
        # save video to the datafile
        datagroup.create_dataset("video_%d", 
                                 # save only the captured frames even if frame_number < max_frames
                                 data=self.LiveView.image_array[range(self.LiveView.frame_number)],
                                 attrs=self.LiveView.attributes)
        
        # flushing at the end
        datagroup.file.flush() 
        print "Finished saving video.\n"
            
    def reset_gui_with_camera(self):
        """Enable/disable GUI elements when a camera connection exists."""
        self.setEnabled(True)
        
        self.StartVideoPushButton.setEnabled(True)  
        self.StopVideoPushButton.setEnabled(False)

        self.LiveViewCheckBox.setEnabled(True)
        self.LiveViewCheckBox.setChecked(False)

        self.TakeImagePushButton.setEnabled(True)
        self.AutoExposurePushButton.setEnabled(True)
        self.SaveImagePushButton.setEnabled(True)
        
        self.OpenCameraPushButton.setEnabled(False)
        self.CloseCameraPushButton.setEnabled(True)
        self.NewFilePushButton.setEnabled(True)
    
    def reset_gui_without_camera(self):
        """Enable/disable GUI elements when no camera connection exists."""
        self.setEnabled(True)
        
        self.StartVideoPushButton.setEnabled(False)  
        self.StopVideoPushButton.setEnabled(False)

        self.LiveViewCheckBox.setEnabled(False)
        self.LiveViewCheckBox.setChecked(False)

        self.TakeImagePushButton.setEnabled(False)
        self.AutoExposurePushButton.setEnabled(False)
        self.SaveImagePushButton.setEnabled(False)
        
        self.OpenCameraPushButton.setEnabled(True)
        self.CloseCameraPushButton.setEnabled(False)
        self.NewFilePushButton.setEnabled(False)        
        
class LiveViewThread(QtCore.QThread):
    """Thread wich allows live view of the camera."""
    display_signal = QtCore.Signal(np.ndarray)
    attributes_signal = QtCore.Signal(dict)
    
    def __init__(self, camera):
        QtCore.QThread.__init__(self)       
        self.camera = camera
        self.attributes = dict()               
        
    def __del__(self):
        self.wait()
            
    def live_view(self, video_parameters, save=False, 
                        timeout=1000, max_frames=100,
                        display_framerate = 10):
        """Start live view with the video parameters received from the main GUI."""

        self.timeout = "{} millisecond".format(str(timeout))        
        self.save = save
        self.max_frames = max_frames
                       
        # get the capture_timestamp with millisecond precision
        # insert a T to match the creation_timestamp formatting
        self.attributes['capture_timestamp'] = str(datetime.datetime.now()).replace(' ', 'T')
        self.attributes['max_frames'] = max_frames
        self.attributes['timeout'] = timeout
        
        # start timer with microsecond precision
        self.high_precision_time = HighPrecisionWallTime()     
        
        # start live video
        self.camera.start_live_video(**video_parameters)       
        
        # calculate when we need to emit the image to the gui        
        capture_framerate = self.camera.framerate.magnitude
        self.frame_multiple = int(capture_framerate / display_framerate)
        # if display_framerate > capture_framerate then frame_multiple < 1
        # since we cannot emit each image more than once, frame_multiple must be >= 1
        if self.frame_multiple < 1: self.frame_multiple = 1
        
        # initialise data arrays
        if save:
            print "Recording video..."  
            
            image = self.camera.latest_frame()
            # image_array size is the max_frames by the size of the image taken (works for monochrome and colour)
            self.array_dim = [self.max_frames] + list(image.shape)
            print "Array dimensions: " + str(self.array_dim)
            
            self.image_array = np.empty(self.array_dim, dtype='uint8') # unit8 for minimum file size
            self.capture_timestamp_array = np.empty(self.max_frames, dtype='float')
        
    def run(self):
        """Continuously acquire frames until the stop button is pressed
        or the maximum number of frames is reached."""
        self.frame_number = 0
        while not self.isFinished() and self.frame_number < self.max_frames:
            # we need to run wait_for_frame so the video framerate is consistent
            if self.camera.wait_for_frame(timeout=self.timeout):        
                # get the capture_time with microsecond precision
                capture_time_sec = self.high_precision_time.sample()                
                
                # capture the latest frame
                image = self.camera.latest_frame()
                if self.save:
                    self.save_frame(image, capture_time_sec, self.frame_number)
                
                if self.frame_number % self.frame_multiple == 0:
                    # emit signals to the main gui
                    self.attributes_signal.emit(self.attributes)
                    self.display_signal.emit(image) # crashes more often - maybe?               
                self.frame_number += 1
                
        
    def save_frame(self, image, capture_time_sec, frame_number):
        """Save the frame to RAM."""
        self.image_array[frame_number,:,:] = image
        self.capture_timestamp_array[frame_number] = capture_time_sec
        self.attributes['capture_time_sec'] = self.capture_timestamp_array                
        

class HighPrecisionWallTime():
    def __init__(self,):
        self._wall_time_0 = time.time()
        self._clock_0 = time.clock()

    def sample(self,):
        dc = time.clock()-self._clock_0
        return self._wall_time_0 + dc
    
if __name__ == '__main__':
    drivers = list_instruments()
    if not len(drivers):
        print "No instruments found"
    
    app = QtWidgets.QApplication([])
    cameras = list()
    for driver in drivers:
        print "Instrument driver:"
        print driver
        print
        if driver['classname'] == 'UC480_Camera':
            cameras.append(uc480(serial=driver['serial']))
            cameras[-1].show()
            cameras[-1].activateWindow()
