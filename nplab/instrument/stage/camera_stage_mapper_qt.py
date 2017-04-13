# -*- coding: utf-8 -*-
"""
Created on Tue Apr 11 11:26:55 2017

@author: Will
"""

import nplab.instrument.camera
import nplab.instrument.stage
from nplab.instrument import Instrument
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import time, threading
import pyqtgraph as pg
from nplab.utils.gui import QtCore, QtGui, QtWidgets
from nplab.ui.ui_tools import UiTools
import cv2
from scipy import ndimage


class CameraStageMapper(Instrument):
    """
    This class sits between a camera and a stage, allowing coordinate conversion.

    Coordinate Systems
    ------------------
    We consider the centre of the image to be our current position, and give
    the position of each pixel on the camera such that it would be brought to
    the centre of the camera image by moving the stage to (-position).
    """
#    do_calibration = Button()
#    calibration_distance = Float(7, tooltip="Distance to move in each direction when calibrating, in um")
#    camera_to_sample = Array(shape=(2,2))
#    do_autofocus = Button()
#    autofocus_range = Range(0., 100., 5.)
#    autofocus_step = Range(0., 10., 0.5)
#    autofocus_default_ranges = [np.arange(-5,5,0.5),np.arange(-1,1,0.2)]
#    frames_to_discard = Int(1)
#    settling_time = Float(0.2)
#    disable_live_view = True
#    traits_view = View(
#                    VGroup(
#                        Item(name="calibration_distance"),
#                        Item(name="do_calibration"),
#                        Item(name="autofocus_range"),
#                        Item(name="autofocus_step"),
#                        Item(name="do_autofocus"),
#                        Item(name="camera_to_sample"),
#                    ),
#                    title="Camera-Stage Mapper",
#                )
    def __init__(self, camera, stage):
        super(CameraStageMapper, self).__init__()
        self.camera = camera
        self.stage = stage
        self.autofocus_range = 5.0
        self.autofocus_step = 0.5
        self.autofocus_default_ranges = [np.arange(-5,5,0.5),np.arange(-1,1,0.2)]
        self.camera_to_sample = np.identity(2)
        self.camera_centre = (0.5,0.5)
        self.calibration_distance = 7
        self.settling_time = 0.2
        self.frames_to_discard = 1
        self.camera.set_legacy_click_callback(self.move_to_camera_point)
        self.disable_live_view = True
        self._action_lock = threading.Lock() #prevent us from doing two things involving motion at once!
    
    ############ Coordinate Conversion ##################
    def camera_pixel_to_point(self, p):
        """convert pixel coordinates to point coordinates (normalised 0-1)"""
        return np.array(p,dtype=float)/ \
                np.array(self.camera.latest_frame.shape[0:2], dtype=float)
    def camera_point_to_pixel(self, p):
        """convert point coordinates (normalised 0-1) to pixel"""
        return np.array(p)*np.array(self.camera.latest_frame.shape[0:2])
    def camera_pixel_to_sample(self, p):
        return self.camera_point_to_sample(self.camera_pixel_to_point(p))
    def camera_point_to_sample(self, p):
        displacement = np.dot(np.array(p) - np.array(self.camera_centre),
                              self.camera_to_sample)
        return self.camera_centre_position()[0:2] + displacement
    def camera_point_displacement_to_sample(self, p):
        """Convert a displacement from camera point units to microns"""
        return np.dot(np.array(p), self.camera_to_sample)
    def camera_pixel_displacement_to_sample(self, p):
        """Convert from pixels to microns for relative moves"""
        return self.camera_point_displacement_to_sample(self.camera_pixel_to_point(p))
    
    ############## Stage Control #####################
    def move_to_camera_pixel(self, p):
        """bring the object at pixel p=(x,y) on the camera to the centre"""
        return self.move_to_camera_point(*tuple(self.camera_pixel_to_point(p)))
    def move_to_camera_point(self, x, y=None):
        """Move the stage to centre point (x,y) on the camera
        
        (x,y) is the position on the camera, where x,y range from 0 to 1"""
        if y is None:
            p=x
        else:
            p=(x,y)
        displacement = np.dot(np.array(p) - np.array(self.camera_centre),
                              self.camera_to_sample)
        current_position = displacement +self.camera_centre_position()[0:2]
        self.move_to_sample_position(current_position)

    def move_to_sample_position(self, p):
        """Move the stage to centre sample position p on the camera"""
        self.stage.move(-np.array(p))
    
    def camera_centre_position(self):
        """return the position of the centre of the camera view, on the sample"""
        return -self.stage.position
    
    ################## Closed loop stage control #################
    def centre_on_feature(self, feature_image, search_size=(50,50), tolerance=0.3, max_iterations=10, **kwargs):
        """Adjust the stage slightly to centre on the given feature.
        
        This should be called immediately after moving the stage to centre on a
        feature in the image: first move the stage to bring that feature to the
        centre, then call this function to fine-tune.
        
        Arguments
        =========
        * feature_image: an RGB image of a feature.  Must be
        significantly smaller than the camera image.
        * search_size: size of the area around the image centre to search, in
        pixels.  Should be a tuple of length 2.
        * tolerance: how accurately we're going to centre (in um)
        * max_iterations: maximum number of shifts
        """
        shift=[999.,999.]
        n=0
        if self.disable_live_view:
            camera_live_view = self.camera.live_view
            self.camera.live_view = False
        while np.sqrt(np.sum(np.array(shift)**2))>tolerance and n<max_iterations:
            n+=1
            try:
                shift=self.centre_on_feature_iterate(feature_image, 
                                                     search_size=search_size, 
                                                     **kwargs)
                print "Centring on feature: moving by %.2f, %.2f" % tuple(shift)
            except:
                print "Something went wrong with auto-centering - trying again." #don't worry, we incremented N so this won't go on forever!
        if np.sqrt(np.sum(np.array(shift)**2))>tolerance:
            print "Performed %d iterations but did not converge on the feature to within %.3fum" % (n, tolerance)
        else:
            print "Centered on feature in %d iterations." % n
        if self.disable_live_view:
            self.camera.live_view = camera_live_view #reenable live view if necessary
    def centre_on_feature_iterate(self, feature_image, search_size=(50,50), image_filter=lambda x: x):
        """Measure the displacement of the sample and move to correct it.
        
        Arguments:
        feature_image : numpy.ndarray
            This is the feature that should be at the centre of the camera.  It
            must be smaller than the camera image + search size.
        search_size : (int, int)
            The distance in pixels to search over.  Defaults to (50,50).
        image_filter : function (optional)
            If supplied, run this function on the image before cross-correlating
            (you can use this to cross-correlate in grayscale, for example).
        """
        try:
            self.flush_camera_and_wait()
            current_image = image_filter(self.camera.color_image()) #get the current image
            corr = cv2.matchTemplate(current_image,feature_image,cv2.TM_SQDIFF_NORMED) #correlate them: NB the match position is the MINIMUM
            #restrict to just the search area, and invert so we find the maximum
            corr = -corr[(corr.shape[0]/2. - search_size[0]/2.):(corr.shape[0]/2. + search_size[0]/2.),
                         (corr.shape[1]/2. - search_size[1]/2.):(corr.shape[1]/2. + search_size[1]/2.)] #invert the image so we can find a peak
            corr += (corr.max()-corr.min())*0.1 - corr.max() #background-subtract 90% of maximum
            corr = cv2.threshold(corr, 0, 0, cv2.THRESH_TOZERO)[1] #zero out any negative pixels - but there should always be > 0 nonzero pixels
            peak = ndimage.measurements.center_of_mass(corr) #take the centroid (NB this is of grayscale values not just binary)
            self.move_to_camera_pixel(np.array(peak) - np.array(corr.shape[0:2])/2.+np.array(current_image.shape[0:2])/2.)
            return self.camera_pixel_displacement_to_sample(np.array(peak) - np.array(corr.shape[0:2])/2.)
        except Exception as e:
            print "Exception: ", e
            print "Corr: ", corr
            print "Feature: ", feature_image
            print "Feature Size: ", feature_image.shape
            print "Corr size: ", corr.shape
            print "Peak: ", peak
            print "sum(corr): ", np.sum(corr)
            print "max(corr): ", np.max(corr)
            raise e

########## Calibration ###############
    def calibrate_in_background(self):
        threading.Thread(target=self.calibrate).start()
    def calibrate(self, dx=None):
        """Move the stage in a square and set the transformation matrix."""
        with self._action_lock:
            if dx is None or dx is False: dx=self.calibration_distance #use a sensible default
            here = self.camera_centre_position()
            if len(self.stage.axis_names)==2:
                pos = [np.array([i,j]) for i in [-dx,dx] for j in [-dx,dx]]
            elif len(self.stage.axis_names)==3:
                pos = [np.array([i,j,0]) for i in [-dx,dx] for j in [-dx,dx]]
            print pos, dx
            camera_pos = []
            self.camera.update_latest_frame() # make sure we've got a fresh image
            initial_image = self.camera.gray_image()
            w, h, = initial_image.shape
            template = initial_image[w/4:3*w/4,h/4:3*h/4] #.astype(np.float)
            #template -= cv2.blur(template, (21,21), borderType=cv2.BORDER_REPLICATE)
    #        self.calibration_template = template
    #        self.calibration_images = []
            camera_live_view = self.camera.live_view
            if self.disable_live_view:
                self.camera.live_view = False
            for p in pos:
                self.move_to_sample_position(here + p)
                self.flush_camera_and_wait()
                current_image = self.camera.gray_image()
                corr = cv2.matchTemplate(current_image,template,cv2.TM_SQDIFF_NORMED)
                corr *= -1. #invert the image
                corr += (corr.max()-corr.min())*0.1 - corr.max() ##
                corr = cv2.threshold(corr, 0, 0, cv2.THRESH_TOZERO)[1]
    #            peak = np.unravel_index(corr.argmin(),corr.shape)
                peak = ndimage.measurements.center_of_mass(corr)
                camera_pos.append(peak - (np.array(current_image.shape) - \
                                                       np.array(template.shape))/2)
    #            self.calibration_images.append({"image":current_image,"correlation":corr,"pos":p,"peak":peak})
            self.move_to_sample_position(here)
            self.flush_camera_and_wait()#otherwise we get a worrying "jump" when enabling live view...
            self.camera.live_view = camera_live_view
            #camera_pos now contains the displacements in pixels for each move
            sample_displacement = np.array([-p[0:2] for p in pos]) #nb need to convert to 2D, and the stage positioning is flipped from sample coords
            camera_displacement = np.array([self.camera_pixel_to_point(p) for p in camera_pos])
            print "sample was moved (in um):\n",sample_displacement
            print "the image shifted (in fractions-of-a-camera):\n",camera_displacement
            A, res, rank, s = np.linalg.lstsq(camera_displacement, sample_displacement)
            self.camera_to_sample = A

    def flush_camera_and_wait(self):
        """take and discard a number of images from the camera to make sure the image is fresh
        
        This functionality should really be in the camera, not the aligner!"""
        time.sleep(self.settling_time)
        for i in range(self.frames_to_discard):
            self.camera.raw_image() #acquire, then discard, an image from the camera

    ######## Image Tiling ############
    def acquire_tiled_image(self, n_images=(3,3), dest=None, overlap=0.33,
                            autofocus_args={},live_plot=False, downsample=8):
        """Raster-scan the stage and take images, which we can later tile.

        Arguments:
        @param: n_images: A tuple of length 2 specifying the number of images
        to take in X and Y
        @param: dest: An HDF5 Group object to store the images in.  Each image
        will be tagged with metadata to mark where it was taken.  If no dest
        is specified, a new group will be created in the current datafile.
        @param: overlap: the fraction of each image to overlap with the 
        adjacent one (it's important this is high enough to match them up)
        @param: autofocus_args: A dictionary of keyword arguments for the
        autofocus that occurs before each image is taken.  Set to None to
        disable autofocusing.
        """
        reset_interactive_mode = live_plot and not matplotlib.is_interactive()
        if live_plot:
            plt.ion()
            fig = plt.figure()
            axes = fig.add_subplot(111)
            axes.set_aspect(1)
            
        with self._action_lock:
            if dest is None:
                dest = self.create_data_group("tiled_image_%d") #or should this be in RAM??
            centre_position = self.camera_centre_position()[0:2] #only 2D
            x_indices = np.arange(n_images[0]) - (n_images[0] - 1)/2.0
            y_indices = np.arange(n_images[1]) - (n_images[1] - 1)/2.0
            for y_index in y_indices:
                for x_index in x_indices:
                    position = centre_position + self.camera_point_displacement_to_sample(np.array([x_index, y_index]) * (1-overlap))
                    self.move_to_sample_position(position) #go to the raster point
                    if autofocus_args is not None:
                        self.autofocus(**autofocus_args)
                    self.flush_camera_and_wait() #wait for the camera to be ready/stage to settle
                    tile = dest.create_dataset("tile_%d", 
                                               data=self.camera.color_image(),
                                               attrs=self.camera.metadata)
                    tile.attrs.create("stage_position",self.stage.position)
                    tile.attrs.create("camera_centre_position",self.camera_centre_position())
                    if live_plot:
                        #Plot the image, in sample coordinates
                        corner_points = np.array([self.camera_point_to_sample((xcorner,ycorner)) 
                                                for ycorner in [0,1] for xcorner in [0,1]]) #positions of corners
                        plot_skewed_image(tile[::downsample, ::downsample, :],
                                          corner_points, axes=axes)
                        fig.canvas.draw()
                x_indices = x_indices[::-1] #reverse the X positions, so we do a snake-scan
            dest.attrs.set("camera_to_sample",self.camera_to_sample)
            dest.attrs.set("camera_centre",self.camera_centre)
            self.move_to_sample_position(centre_position) #go back to the start point
        if reset_interactive_mode:
            plt.ioff()
        return dest
        
    ######## Autofocus Stuff #########
    def autofocus_merit_function(self): # we maximise this...
        """Take an image and calculate the focus metric, this is what we optimise.
        
        Currently, this calculates the sum of the square of the Laplacian of the image
        which should pick out sharp features quite effectively.  It can, however, be
        thrown off by very bright objects if the camera is saturated."""
        self.flush_camera_and_wait()
#        self.camera.update_latest_frame() #take an extra frame to make sure this one is fresh
        img = self.camera.raw_image()
#        return np.sum((img - cv2.blur(img,(21,21))).astype(np.single)**2)
        return np.sum(cv2.Laplacian(cv2.cvtColor(img,cv2.COLOR_BGR2GRAY), ddepth=cv2.CV_32F)**2)


    def autofocus_in_background(self):
        def work():
            self.autofocus_iterate(np.arange(-self.autofocus_range/2, self.autofocus_range/2, self.autofocus_step))
        threading.Thread(target=work).start()
    
    def autofocus_iterate(self, dz, method="centre_of_mass", noise_floor=0.3):
        self._action_lock.acquire()
        """Move in z and take images.  Move to the sharpest position."""
        here = self.stage.position
        positions = [here]                              #positions keeps track of where we sample
        powers = [self.autofocus_merit_function()]      #powers holds the value of the merit fn at each point
        camera_live_view = self.camera.live_view
        if self.disable_live_view:
            self.camera.live_view = False
        for z in dz:
            self.stage.move(np.array([0,0,z])+here)     #visit each point and evaluate merit function
 #           time.sleep(0.5)
            positions.append(self.stage.position)
            powers.append(self.autofocus_merit_function())
        powers = np.array(powers)
        positions = np.array(positions)
        z = positions[:,2] 
        if method=="centre_of_mass":
            threshold = powers.min() + (powers.max()-powers.min())*noise_floor #(powers.min() if len(powers)<4 else np.max([powers[z.argmin()],powers[z.argmax()]])) #ensure edges are zero
            weights = powers - threshold
            weights[weights<0] = 0. #zero out any negative values
            if(np.sum(weights)==0): 
                new_position = positions[powers.argmax(),:]
            else: 
                new_position = np.dot(weights, positions)/np.sum(weights)
        elif method=="parabola":
            coefficients = np.polyfit(z, powers, deg=2) #fit a parabola
            root = -coefficients[1]/(2*coefficients[0]) #p = c[0]z**" + c[1]z + c[2] which has max (or min) at 2c[0]z + c[1]=0 i.e. z=-c[1]/2c[0]
            if z.min() < root and root < z.max():
                new_position = [here[0],here[1],root]
            else:
                new_position = positions[powers.argmax(),:]
        else:
            new_position = positions[powers.argmax(),:]
        self.stage.move(new_position)
        self.camera.live_view = camera_live_view
        self._action_lock.release()
        return new_position-here, positions, powers

    def autofocus(self, ranges=None, max_steps=10):
        """move the stage to bring the sample into focus
        
        Presently, it just does one iteration for each range passed in: usually
        this would mean a coarse focus then a fine focus.
        """ #NEEDS WORK!
        if ranges is None or ranges is False:
            ranges = self.autofocus_default_ranges
        n=0
        for r in ranges:
            pos = self.autofocus_iterate(r)[0]
            print "moving Z by %.3f" % pos[2]
            n+=1
        print "Autofocus: performed %d iterations" % n
    
    def get_qt_ui(self):
        return CameraStageMapperControlWidget(self)
class CameraStageMapperControlWidget(QtWidgets.QWidget, UiTools):
    """Controls for the Camera stage mapper"""
    def __init__(self, camerastagemapper):
        super(CameraStageMapperControlWidget, self).__init__()
        self.camerastagemapper = camerastagemapper
        self.load_ui_from_file(__file__,"camerastagemapper.ui")
        self.auto_connect_by_name(controlled_object=self.camerastagemapper, verbose=True)
        
#if __name__ == '__main__':
    #WARNING this is old, probably broken, code.
#    import nplab.instrument.camera.lumenera as camera
#    import nplab.instrument.stage.prior as prior_stage
#    c = camera.Camera(0)
#    s = prior_stage.ProScan()
#    
#    m = CameraStageMapper(c, s)
#    
#    m.autofocus_iterate(np.arange(-5,5,0.5))
#    m.calibrate(5)
#    
#    c.edit_traits()
#    m.edit_traits()
#    
#    def move_to_feature_at_point(x,y):
#        #first, extract image of where we want to go
#        p = m.camera_point_to_pixel([x,y])
#        feature_image = c.color_image()[p[0]-25:p[0]+25, p[1]-25:p[1]+25]
#        m.move_to_camera_point(x,y)
#        time.sleep(0.5)
#        shift=[999,999]
#        while np.sqrt(np.sum(np.array(shift)**2))>0.5:
#            shift=m.centre_on_feature(feature_image)
#            print "moving by %.2f, %.2f" % tuple(shift)
#            
#    
#    def close():
#        c.close()
#        s.close()
#    