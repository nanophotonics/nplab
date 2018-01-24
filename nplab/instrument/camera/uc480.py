# -*- coding: utf-8 -*-
"""
@author: Ana Andres-Arroyo
GUI which controls a Thorlabs camera
"""
# documentation:
# http://instrumental-lib.readthedocs.io/en/latest/uc480-cameras.html

import os
import datetime
from qtpy import QtCore, QtWidgets, uic
from scipy.misc import imsave
import pyqtgraph as pg
import numpy as np
import nplab
from nplab.ui.ui_tools import UiTools
from instrumental import list_instruments, instrument

def get_camera_parameters(camera):
    """Get camera parameters."""
    camera_parameters = dict()
    camera_parameters['framerate'] = camera.framerate
    camera_parameters['exposure_time'] = camera._get_exposure()
    camera_parameters['width'] = camera.width
    camera_parameters['max_width'] = camera.max_width
    camera_parameters['height'] = camera.height
    camera_parameters['max_height'] = camera.max_height        
    camera_parameters['master_gain'] = camera.master_gain
    camera_parameters['gain_boost'] = camera.gain_boost
    camera_parameters['auto_blacklevel'] = camera.auto_blacklevel
    camera_parameters['blacklevel_offset'] = camera.blacklevel_offset
    
    return camera_parameters

class uc480(QtWidgets.QMainWindow, UiTools):
    """
    GUI which controls a Thorlabs camera.
    """
    
    def __init__(self):
        super(self.__class__, self).__init__()
        # Get the path of this file in case we are calling this class from another location
        file_path = os.path.dirname(__file__)
        ui_file = file_path + '\uc480_gui_design.ui'
        uic.loadUi(ui_file, self)
        
        # Maximise GUI window
#        self.showMaximized()
        
        # Set initial tabs to display
        self.SettingsTabWidget.setCurrentIndex(0) 
        
        # Set initial splitter sizes
        self.splitter.setSizes([50,60000])
        
        # Disable stop video button
        self.StopVideoPushButton.setEnabled(False)
        
        # Set starting parameters
        self.file_path = ''
        self.ExposureTimeNumberBox.setValue(3)
        self.FramerateNumberBox.setValue(10)
        self.GainNumberBox.setValue(0)
        self.BlacklevelNumberBox.setValue(255)
      
        # Connect GUI elements
        self.TakeImagePushButton.clicked.connect(self.take_image)
        self.SaveImagePushButton.clicked.connect(self.save_image)
        self.NewFilePushButton.clicked.connect(self.new_hdf5_file)
        self.LiveViewCheckBox.stateChanged.connect(self.start_live_view)
        self.StartVideoPushButton.clicked.connect(self.save_video)
        
        # Initialise empty dictionary for capture and video parameters
        self.capture_parameters = dict()
        self.video_parameters = dict()
        self.camera_parameters = dict()
        self.attributes = dict()
                        
        # Create live view widget
        image_widget = pg.GraphicsLayoutWidget()
        self.replace_widget(self.verticalLayout, self.LiveViewWidget, image_widget)
        view_box = image_widget.addViewBox(row=1,col=1)        
        self.imv = pg.ImageItem()
        self.imv.setOpts(axisOrder='row-major')
        view_box.addItem(self.imv)
        view_box.setAspectLocked(True)
        
        # Populate image format combobox
        self.ImageFormatComboBox.addItem('hdf5',0)
        self.ImageFormatComboBox.addItem('png',1)
        self.ImageFormatComboBox.addItem('tiff',2)
        self.ImageFormatComboBox.addItem('jpg',3)
        self.ImageFormatComboBox.setCurrentIndex(0)    
        
        # Populate video format combobox
        self.VideoFormatComboBox.addItem('hdf5',0)
        self.VideoFormatComboBox.setCurrentIndex(0)    

        # Open hdf5 file show hdf5 browser gui
        # TODO: only get hdf5 file the first time it's needed to save data
        self.df = False
        self.new_hdf5_file()

        # open camera and take image
        print list_instruments()
        self.open_camera()
        self.take_image()

    
    def open_camera(self):
        """Connect to a Thorlabs camera.""" 
        self.camera = instrument('uc480')
        print 'Camera connection started.'  

        self.ROIWidthNumberBox.setValue(self.camera.max_width)
        self.ROIHeightNumberBox.setValue(self.camera.max_height)
        self.CameraWidthLabel.setText(str(self.camera.max_width))
        self.CameraHeightLabel.setText(str(self.camera.max_height))                 

        
    def close_camera(self):
        """Close the Thorlabs camera connection.""" 
        self.camera.close()
        print 'Camera connection closed.'  
        
    def closeEvent(self,event):
        self.close_camera()
        self.df.close()
        self.df_gui.close()
    
    def take_image(self):
        """Grab an image and display it."""
        image = self.grab_image()
        self.display_image(image)
        
    def display_image(self, image):
        """Display the latest captured image."""
        # make a copy of the data so it can be accessed when saving an image
        self.image = image
        # set levels to [0,255] because otherwise it autoscales when plotting
        self.imv.setImage(image, autoDownsample=True, levels=[0,255])   
    
    def display_camera_parameters(self, camera_parameters):
        """Display the current camera parameters on the GUI."""
        self.CurrentFramerateLabel.setText(str(round(camera_parameters['framerate'].magnitude,5)))
        self.CurrentExposureLabel.setText(str(round(camera_parameters['exposure_time'].magnitude,5)))
        self.CurrentWidthLabel.setText(str(camera_parameters['width']))
        self.CurrentHeightLabel.setText(str(camera_parameters['height']))
        self.MaxWidthLabel.setText(str(camera_parameters['max_width']))
        self.MaxHeightLabel.setText(str(camera_parameters['max_height']))  
        self.CurrentMasterGainLabel.setText(str(camera_parameters['master_gain']))
        self.CurrentGainBoostLabel.setText(str(camera_parameters['gain_boost']))
        self.CurrentAutoBlacklevelLabel.setText(str(camera_parameters['auto_blacklevel']))
        self.CurrentBlacklevelLabel.setText(str(camera_parameters['blacklevel_offset']))
        
            
    def set_capture_parameters(self):
        """Read capture parameters from the GUI."""
        # TODO: fix errors that ocurr when n_frames > 1
        self.capture_parameters['n_frames'] = int(self.FramesNumberBox.value())
        self.capture_parameters = self.set_exposure_time(self.capture_parameters)
        self.capture_parameters = self.set_ROI(self.capture_parameters)
        self.capture_parameters['gain'] = float(self.GainNumberBox.value())
        self.capture_parameters['vbin'] = int(self.VBinNumberBox.value())
        self.capture_parameters['hbin'] = int(self.HBinNumberBox.value())
        self.capture_parameters['vsub'] = int(self.VSubNumberBox.value())
        self.capture_parameters['hsub'] = int(self.HSubNumberBox.value())
        self.set_camera_properties()        
#        print "Capture parameters:"
#        print self.capture_parameters
    
    def set_camera_properties(self):
        """Read capture parameters from the GUI and set the corresponding camera properties."""
        self.camera.auto_blacklevel = self.AutoBlacklevelCheckBox.checkState()
        self.camera.blacklevel_offset = int(self.BlacklevelNumberBox.value())         
        self.camera.gain_boost = self.GainBoostCheckBox.checkState()
    
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

        # repopulate ROI parameters with the selected ones
        if self.ROICheckBox.checkState():            
            for item in ROI_dict.keys():
                if ROI_dict[item][0].checkState():
                    parameters_dict[item] = int(ROI_dict[item][1].value())
        
        return parameters_dict
        
    def set_exposure_time(self, parameters_dict):
        """Read exposure time from the GUI."""
        exposure_time = "{} millisecond".format(str(self.ExposureTimeNumberBox.value()))
        parameters_dict['exposure_time'] = exposure_time
        return parameters_dict            
        
    def grab_image(self):
        """Grab an image with the camera."""
        # set the desired capture parameters
        self.set_capture_parameters() # populate self.capture_parameters
        # get the capture_timestamp
        # insert a T to match the creation_timestamp formatting
        self.attributes['capture_timestamp'] = str(datetime.datetime.now()).replace(' ', 'T')
        # grab the image
        image = self.camera.grab_image(**self.capture_parameters)
        print 'Image grabbed.'
        # get camera parameters and display them on the GUI
        self.camera_parameters = get_camera_parameters(self.camera)
        # update the attributes dictionary
        self.attributes.update(self.capture_parameters)
        self.attributes.update(self.camera_parameters)
        self.display_camera_parameters(self.camera_parameters)        
        return image
        
    def get_info(self):
        """Get info from the GUI."""
        info = dict()
        info['description'] = self.DescriptionLineEdit.text()
        return info
        
    def save_image(self, group_name=False):
        """Save the latest image."""
        # make a copy of the image so the saved image is the one that was on the 
        # screen when the save button was pressed, not when the file name was chosen
        image = self.image
        image_format = self.ImageFormatComboBox.currentText()
        
        # when the save button is pressed group_name=False even if a default value is specified in the function definition
        # so we need this statement to make 'images' be the default
        if not group_name:
            group_name = 'images'
        
        if image_format == 'hdf5':
            # update the attributes dictionary
            self.attributes.update(self.get_info())
            # get the datafile
            df = nplab.current_datafile()
            # write data in the "images" group within the datafile
            dg = df.require_group(name=group_name)
            # write data to the file
            dg.create_dataset("image_%d", data=image, attrs=self.attributes)
            dg.file.flush()
            print "Image saved to the hdf5 file."
            
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
        if self.df:
            # close the datafile
            self.df.close() 
            # open new datafile
            self.df = nplab.current_datafile() 
            # update the datafile for the gui
            self.df_gui.treeWidget.model.data_group = self.df 
            # refresh the tree
            self.df_gui.refresh_tree_button.click() 
        else:
            # open new datafile
            self.df = nplab.current_datafile()
            # open gui
            self.df_gui = self.df.show_gui(blocking=False)                    
        self.FilePathLineEdit.setText(self.df.filename)
        return self.df
        
    def set_video_parameters(self):
        """Read video parameters from the GUI."""
        self.timeout = "{} millisecond".format(str(self.TimeoutNumberBox.value()))
        self.video_parameters['framerate'] = "{} hertz".format(str(self.FramerateNumberBox.value()))
        self.video_parameters = self.set_exposure_time(self.video_parameters)
        self.video_parameters = self.set_ROI(self.video_parameters)
        self.video_parameters['gain'] = float(self.GainNumberBox.value())
        self.video_parameters['vbin'] = int(self.VBinNumberBox.value())
        self.video_parameters['hbin'] = int(self.HBinNumberBox.value())
        self.video_parameters['vsub'] = int(self.VSubNumberBox.value())
        self.video_parameters['hsub'] = int(self.HSubNumberBox.value())
        self.set_camera_properties()        
#        print "Video parameters:"
#        print self.video_parameters
        
    def start_live_view(self):
        """Start/stop the live view."""
        if self.LiveViewCheckBox.isChecked():
                        
            # enable/disable gui buttons
            self.TakeImagePushButton.setEnabled(False)
            self.StartVideoPushButton.setEnabled(False)
            self.StopVideoPushButton.setEnabled(False)
            
            # start thread
            self.LiveView = LiveViewThread(self.camera)
            # connect thread
            self.LiveViewCheckBox.stateChanged.connect(self.LiveView.terminate)
            self.LiveView.finished.connect(self.terminated_live_view)
            # live view
            print "Live view..."
            self.live_view(save=False)                       

            
    def save_video(self):
        """Save a video."""            
        # connect buttons and functions              
        self.LiveViewCheckBox.setEnabled(False)
        self.TakeImagePushButton.setEnabled(False)        
        self.StartVideoPushButton.setEnabled(False)
        self.StopVideoPushButton.setEnabled(True)
        
        # start thread
        self.LiveView = LiveViewThread(self.camera)
        # connect thread
        self.StopVideoPushButton.clicked.connect(self.LiveView.terminate)
        self.LiveView.finished.connect(self.terminated_live_view)
        # live view
        print "Saving video..."
        self.live_view(save=True)
        
    def live_view(self, save=False):                
        # connect signals
        self.LiveView.display_signal.connect(self.display_image)
        self.LiveView.attributes_signal.connect(self.update_attributes)
        
        # populate self.video_parameters and self.timeout
        self.set_video_parameters() 
        
        # starting live view
        self.LiveView.start_live_view(self.video_parameters, self.timeout, save=save)
        
        self.LiveView.attributes.update(self.video_parameters)
        self.camera_parameters = get_camera_parameters(self.camera)    
        self.LiveView.attributes.update(self.camera_parameters)
        self.LiveView.attributes.update(self.get_info())
        self.display_camera_parameters(self.camera_parameters)
        self.LiveView.start()
    
    def update_attributes(self, attributes):
        self.attributes.update(attributes)   
#        self.display_camera_parameters(self.attributes)                             
    
    def terminated_live_view(self):
        print "Terminated live view."
        self.LiveViewCheckBox.setEnabled(True)
        self.LiveViewCheckBox.setChecked(False)
        self.TakeImagePushButton.setEnabled(True)
        self.StartVideoPushButton.setEnabled(True)
        self.StopVideoPushButton.setEnabled(False)
            
        
class LiveViewThread(QtCore.QThread):
    """
    Thread wich allows live view of the camera.
    """
    display_signal = QtCore.Signal(np.ndarray)
    attributes_signal = QtCore.Signal(dict)
    
    def __init__(self, camera):
        QtCore.QThread.__init__(self)       
        self.camera = camera
        self.attributes = dict()               
        
    def __del__(self):
        self.wait()
    
    def set_video_parameters(self, video_parameters, timeout):
        """Set video parameters."""
        self.timeout = timeout        
        self.video_parameters = video_parameters
            
    def start_live_view(self, video_parameters, timeout, save=False):
        """Start live view with the video parameters received from the main GUI."""

        self.set_video_parameters(video_parameters, timeout)
        self.camera.start_live_video(**self.video_parameters)
        
        self.save = save
        if save:
            print "Saving video..."
            # get the datafile
            df = nplab.current_datafile()
            # write data in the "videos" group within the datafile
            dg = df.require_group("videos")
            # create a new unique group for this video
            self.datagroup = dg.require_group("video_%d")
        
    def run(self):
        """Continuously acquire frames."""
        while not self.isFinished():
            if self.camera.wait_for_frame(timeout=self.timeout):
                # get the capture_timestamp
                # insert a T to match the creation_timestamp formatting
                self.attributes['capture_timestamp'] = str(datetime.datetime.now()).replace(' ', 'T')
                # capture the latest frame
                image = self.camera.latest_frame()
                if self.save:
                    self.save_frame(image)
                    
                # emit signals to the main gui
                self.attributes_signal.emit(self.attributes)
                self.display_signal.emit(image)
        
    def save_frame(self, image):
        """Save the frame to the hdf5 file."""
        # write data to the file
        self.datagroup.create_dataset("image_%d", data=image, attrs=self.attributes)
        self.datagroup.file.flush()       
#        print "Image saved to the hdf5 file."

    
if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    camera = uc480()
    camera.show()
    camera.activateWindow()
