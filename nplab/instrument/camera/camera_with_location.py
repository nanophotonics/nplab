# -*- coding: utf-8 -*-
"""
Camera with Location
====================

Very frequently, we use cameras on microscopes.  This generally involves close collaboration between the camera and
the microscope stage - in particular it's nice to click the camera image to move the stage, and to save position
metadata along with images.  That then leads on to tasks like tiling images together, performing closed-loop positioning
and the like.  `CameraWithLocation` is a sort of meta-instrument, which wraps a Camera and a Stage, and provides the
glue code between the two.

It would be nice to make this a mixin for the camera classes, but for now I think it's cleanest to wrap rather than
try to integrate into Camera.  This class is, however, a work-alike for Camera; to get the full benefit of this class
you should use its `color_image`, `gray_image` and `raw_image` methods rather than those of the underlying `Camera`.

NB see the note on coordinate systems in utils/image_with_location.py
"""
from __future__ import division
from __future__ import print_function
from builtins import range
from past.utils import old_div
import nplab
from nplab.instrument.camera import Camera
import nplab.instrument.camera
from nplab.instrument.stage import Stage
from nplab.instrument import Instrument
import numpy as np
from nplab.utils.image_with_location import ImageWithLocation, ensure_3d, ensure_2d, locate_feature_in_image, datum_pixel
from nplab.experiment import Experiment, ExperimentStopped
from nplab.experiment.gui import ExperimentWithProgressBar, run_function_modally
from nplab.utils.gui import QtCore, QtGui, QtWidgets
import cv2
#import cv2.cv
from scipy import ndimage
from scipy.signal import argrelextrema
from nplab.ui.ui_tools import QuickControlBox, UiTools
from nplab.utils.notified_property import DumbNotifiedProperty
import time

# Autofocus merit functions
def af_merit_squared_laplacian(image):
    """Return the mean squared Laplacian of an image - a sharpness metric.

    The image will be converted to grayscale if its shape is MxNx3"""
    if len(image.shape) == 3:
        image = np.mean(image, axis=2, dtype=image.dtype)
    assert len(image.shape) == 2, "The image is the wrong shape - must be 2D or 3D"
    return np.sum(cv2.Laplacian(image, ddepth=cv2.CV_32F) ** 2)


class CameraWithLocation(Instrument):
    """
    A class wrapping a camera and a stage, allowing them to work together.

    This is designed to handle the low-level stuff like calibration, crosscorrelation, and closed-loop stage control.
    It also handles autofocus, and has logic for drift correction.  It could compensate for a non-horizontal sample to
    some extent by adding a tilt to the image plane - but this is as yet unimplemented.
    """
    pixel_to_sample_displacement = None # A 3x3 matrix that relates displacements in pixels to distance units
    pixel_to_sample_displacement_shape = None # The shape of the images taken to calibrate the stage
    drift_estimate = None # Reserved for future use, to compensate for drift
    datum_pixel = None # The position, in pixels in the image, of the "datum point" of the system.
    settling_time = 0.0 # How long to wait for the stage to stop vibrating.
    frames_to_discard = 1 # How many frames to discard from the camera after a move.
    disable_live_view = DumbNotifiedProperty(False) # Whether to disable live view while calibrating/autofocusing/etc.
    af_step_size = DumbNotifiedProperty(1) # The size of steps to take when autofocusing
    af_steps = DumbNotifiedProperty(7) # The number of steps to take during autofocus

    def __init__(self, camera=None, stage=None):
        # If no camera or stage is supplied, attempt to retrieve them - but crash with an exception if they don't exist.
        if camera is None:
            camera = Camera.get_instance(create=False)
        if stage is None:
            stage = Stage.get_instance(create=False)
        self.camera = camera
        self.stage = stage
        self.filter_images = False
        Instrument.__init__(self)

        shape = self.camera.color_image().shape
        self.datum_pixel = np.array(shape[:2])/2.0 # Default to using the centre of the image as the datum point
   #     self.camera.set_legacy_click_callback(self.move_to_feature_pixel)
        self.camera.set_legacy_click_callback(self.move_to_pixel)

    @property
    def pixel_to_sample_matrix(self):
        here = self.datum_location
        assert self.pixel_to_sample_displacement is not None, "The CameraWithLocation must be calibrated before use!"
        datum_displacement = np.dot(ensure_3d(self.datum_pixel), self.pixel_to_sample_displacement)
        M = np.zeros((4,4)) # NB M is never a matrix; that would create issues, as then all the vectors must be matrices
        M[0:3, 0:3] = self.pixel_to_sample_displacement # We calibrate the conversion of displacements and store it
        M[3, 0:3] = here - datum_displacement # Ensure that the datum pixel transforms to here.
        return M

    def _add_position_metadata(self, image):
        """Add position metadata to an image, assuming it has just been acquired"""
        iwl = ImageWithLocation(image)
        iwl.attrs['datum_pixel'] = self.datum_pixel
        iwl.attrs['stage_position'] = self.stage.position
        if self.pixel_to_sample_displacement is not None:
  #          assert iwl.shape[:2] == self.pixel_to_sample_displacement.shape[:2], "Image shape is not the same" \
  #                                                                               "as when we calibrated!" #These lines dont make much sense, the iwl has the size of the image while the martix is always only 3x3
            iwl.attrs['pixel_to_sample_matrix'] = self.pixel_to_sample_matrix
        else:
            iwl.attrs['pixel_to_sample_matrix'] = np.identity(4)
            print('Stage is not yet calbirated')
        return iwl


    ####### Wrapping functions for the camera #######
    def raw_image(self, *args, **kwargs):
        """Return a raw image from the camera, including position metadata"""
        return self._add_position_metadata(self.camera.raw_image(*args, **kwargs))

    def gray_image(self, *args, **kwargs):
        """Return a grayscale image from the camera, including position metadata"""
        return self._add_position_metadata(self.camera.gray_image(*args, **kwargs))

    def color_image(self,ignore_filter=False, *args, **kwargs):
        """Return a colour image from the camera, including position metadata"""
        image = self.camera.color_image(*args, **kwargs)
        if (ignore_filter == False and 
            self.filter_images == True and 
            self.camera.filter_function is not None):
            image = self.camera.filter_function(image)
        return self._add_position_metadata(image)
    def thumb_image(self,size = (100,100)):
        """Return a cropped "thumb" from the CWL with size  """
        image =self.color_image()
        thumb = image[old_div(image.shape[0],2)-old_div(size[0],2):old_div(image.shape[0],2)+old_div(size[0],2),
                     old_div(image.shape[1],2)-old_div(size[1],2):old_div(image.shape[1],2)+old_div(size[1],2)]
        return thumb

    ###### Wrapping functions for the stage ######
    def move(self, *args, **kwargs): # TODO: take account of drift
        """Move the stage to a given position"""
        self.stage.move(*args, **kwargs)

    def move_rel(self, *args, **kwargs):
        """Move the stage by a given amount"""
        self.stage.move_rel(*args, **kwargs)
    def move_to_pixel(self,x,y):
        
        iwl = ImageWithLocation(self.camera.latest_raw_frame)
        iwl.attrs['datum_pixel'] = self.datum_pixel
#        self.use_previous_datum_location = True
        iwl.attrs['pixel_to_sample_matrix'] = self.pixel_to_sample_matrix
        if (iwl.pixel_to_sample_matrix != np.identity(4)).any():
            #check if the image has been calibrated
            #print('move coords', image.pixel_to_location([x,y]))
            #print('current position', self.stage.position)
            self.move(iwl.pixel_to_location([x,y]))
            #print('post move position', self.stage.position)
#        self.use_previous_datum_location = False
    @property
    def datum_location(self):
        """The location in the sample of the datum point (i.e. the current stage position, corrected for drift)"""
        if self.drift_estimate == None:
            return self.stage.position
        else:
            return self.stage.position-self.drift_estimate
        return self.stage.position - self.drift_estimate

    ####### Useful functions for closed-loop stage control #######
    def settle(self, flush_camera=True, *args, **kwargs):
        """Wait for the stage to stop moving/vibrating, and (unless specified) discard frame(s) from the camera.

        After moving the stage, to get a fresh image from the camera we usually need to both wait for the stage to stop
        vibrating, and discard one or more frames from the camera, so we have a fresh one.  This function does both of
        those things (except if flush_camera is False).
        """
        time.sleep(self.settling_time)
        for i in range(self.frames_to_discard):
            self.camera.raw_image(*args, **kwargs)

    def move_to_feature(self, feature, ignore_position=False, ignore_z_pos = False, margin=50, tolerance=0.5, max_iterations = 10):
        """Bring the feature in the supplied image to the centre of the camera

        Strictly, what this aims to do is move the sample such that the datum pixel of the "feature" image is on the
        datum pixel of the camera.  It does this by first (unless instructed not to) moving to the datum point as
        defined by the image.  It then compares the image from the camera with the feature, and adjusts the position.

        feature : ImageWithLocation or numpy.ndarray
            The feature that we want to move to.
        ignore_position : bool (optional, default False)
            Set this to true to skip the initial move using the image's metadata.
        margin : int (optional)
            The maximum error, in pixels, that we can cope with (this sets the size of the search area we use to look
            for the feature in the camera image, it is (2*range + 1) in both X and Y.  Set to 0 to use the maximum
            possible search area (given by the difference in size between the feature image and the camera image)
        tolerance : float (optional)
            Once the error between our current position and the feature's position is below this threshold, we stop.
        max_iterations : int (optional)
            The maximum number of moves we make to fine-tune the position.
        """
        if (feature.datum_pixel[0]<0 or feature.datum_pixel[0]>np.shape(feature)[0] or 
            feature.datum_pixel[1]<0 or feature.datum_pixel[1]>np.shape(feature)[1]):
                self.log('The datum picture of the feature is outside of the image!',level = 'WARN')
            
        if not ignore_position:
            try:
                if ignore_z_pos==True:
                    self.move(feature.datum_location[:2]) #ignore original z value
                else:
                    self.move(feature.datum_location) #initial move to where we recorded the feature was
            except:
                print("Warning: no position data in feature image, skipping initial move.")
        image = self.color_image()
        assert isinstance(image, ImageWithLocation), "CameraWithLocation should return an ImageWithLocation...?"

        last_move = np.infty
        for i in range(max_iterations):
            try:
                self.settle()
                image = self.color_image()
                pixel_position = locate_feature_in_image(image, feature, margin=margin, restrict=margin>0)
             #   pixel_position = locate_feature_in_image(image, feature,margin=margin)
                new_position = image.pixel_to_location(pixel_position)
                self.move(new_position)
                last_move = np.sqrt(np.sum((new_position - image.datum_location)**2)) # calculate the distance moved
                self.log("Centering on feature, iteration {}, moved by {}".format(i, last_move))
                if last_move < tolerance:
                    break
            except Exception as e:
                self.log("Error centering on feature, iteration {} raised an exception:\n{}\n".format(i, e) +
                         "The feature size was {}\n".format(feature.shape) +
                         "The image size was {}\n".format(image.shape))
        if last_move > tolerance:
            self.log("Error centering on feature, final move was too large.")
        return last_move < tolerance
        
    def move_to_feature_pixel(self,x,y,image = None):
        if self.pixel_to_sample_matrix is not None:
            if image is None:
                image = self.color_image()
            feature = image.feature_at((x,y))
            self.last_feature = feature
            self.move_to_feature(feature)
        else:
            print('CameraWithLocation is not yet calibrated!!')
        

    def autofocus(self, dz=None, merit_function=af_merit_squared_laplacian,
                  method="centre_of_mass", noise_floor=0.3,exposure_factor =1.0,
                  use_thumbnail = False, update_progress=lambda p:p):
        """Move to a range of Z positions and measure focus, then move to the best one.

        Arguments:
        dz : np.array (optional, defaults to values specified in af_step_size and af_steps
            Z positions, relative to the current position, to move to and measure focus.
        merit_function : function, optional
            A function that takes an image and returns a focus score, which we maximise.
        update_progress : function, optional
            This will be called each time we take an image - for use with run_function_modally.
        """
        self.camera.exposure = old_div(self.camera.exposure,exposure_factor)
        if dz is None:
            dz = (np.arange(self.af_steps) - old_div((self.af_steps - 1),2)) * self.af_step_size # Default value
        here = self.stage.position
        positions = []  # positions keeps track of where we sample
        powers = []  # powers holds the value of the merit fn at each point
        camera_live_view = self.camera.live_view
        if self.disable_live_view:
            self.camera.live_view = False

        for step_num, z in enumerate(dz):
            self.stage.move(np.array([0, 0, z]) + here)
            self.settle()
            positions.append(self.stage.position)
            if use_thumbnail is True:
                image = self.thumb_image()
            else:
                image = self.color_image()
            powers.append(merit_function(image))
            update_progress(step_num)
        powers = np.array(powers)
        positions = np.array(positions)
        z = positions[:, 2]
        if method == "centre_of_mass":
            threshold = powers.min() + (powers.max() - powers.min()) * noise_floor
            weights = powers - threshold
            weights[weights < 0] = 0.  # zero out any negative values
            indices_of_maxima = argrelextrema(np.pad(weights, (1, 1), 'minimum'), np.greater)[0]-1
            number_of_maxima = indices_of_maxima.size
            if (np.sum(weights) == 0):
                print("Warning, something went wrong and all the autofocus scores were identical! Returning to initial position.")
                new_position = here # Return to initial position if something fails
            elif (number_of_maxima == 1) and not (indices_of_maxima[0] == 0 or indices_of_maxima[-1] == (weights.size-1)):
                new_position = old_div(np.dot(weights, positions), np.sum(weights))
            else:
                print("Warning, a maximum autofocus score could not be found. Returning to initial position.")
                new_position = here
        elif method == "parabola":
            coefficients = np.polyfit(z, powers, deg=2)  # fit a parabola
            root = old_div(-coefficients[1], (2 * coefficients[
                0]))  # p = c[0]z**" + c[1]z + c[2] which has max (or min) at 2c[0]z + c[1]=0 i.e. z=-c[1]/2c[0]
            if z.min() < root and root < z.max():
                new_position = [here[0], here[1], root]
            else:
                # The new position would have been outside the scan range - clip it to the outer points.
                new_position = positions[powers.argmax(), :]
        else:
            new_position = positions[powers.argmax(), :]
        self.stage.move(new_position)
        self.camera.live_view = camera_live_view
        update_progress(self.af_steps+1)
        self.camera.exposure = self.camera.exposure*exposure_factor
        return new_position - here, positions, powers

    def quick_autofocus(self, dz=0.5, full_dz = None, trigger_full_af=True, update_progress=lambda p:p, **kwargs):
        """Do a quick 3-step autofocus, performing a full autofocus if needed

        dz is a single number - we move this far above and below the current position."""
        shift, pos, powers = self.autofocus(np.array([-dz,0,dz]), method="parabola", update_progress=update_progress)
        if np.linalg.norm(shift) >= dz and trigger_full_af:
            return self.autofocus(full_dz, update_progress=update_progress, **kwargs)
        else:
            return shift, pos, powers

    def autofocus_gui(self):
        """Run an autofocus using default parameters, with a GUI progress bar."""
        run_function_modally(self.autofocus, progress_maximum=self.af_steps+1)

    def quick_autofocus_gui(self):
        """Run an autofocus using default parameters, with a GUI progress bar."""
        run_function_modally(self.quick_autofocus, progress_maximum=self.af_steps+1)

    def calibrate_xy(self,update_progress=lambda p:p, step = None, min_step = 1e-5, max_step=1000):
        """Make a series of moves in X and Y to determine the XY components of the pixel-to-sample matrix.

        Arguments:
        step : float, optional (default None)
            The amount to move the stage by.  This should move the sample by approximately 1/10th of the field of view.
            If it is left as None, we will attempt to auto-determine the step size (see below).
        min_step : float, optional
            If we auto-determine the step size, start with this step size.  It's deliberately tiny.
        max_step : float, optional
            If we're auto-determining the step size, fail if it looks like it's more than this.

        This starts by gingerly moving the stage a tiny amount.  That is repeated, increasing the distance exponentially
        until we see a reasonable movement.  This means we shouldn't need to worry too much about setting the distance
        we use for calibration.

        NB this currently assumes the stage deals with backlash correction for us.
        """
        #,bonus_arg = None,
        # First, acquire a template image:
        self.settle()
        starting_image = self.color_image()
        starting_location = self.datum_location
        w, h = starting_image.shape[:2]
        template = starting_image[int(w/4):int(3*w/4),int(h/4):int(3*h/4), ...] # Use the central 50%x50% as template
        threshold_shift = w*0.02 # Require a shift of at least 2% of the image's width ,changed s[0] to w
        target_shift = w*0.1 # Aim for a shift of about 10%
        # Swapping images[-1] for starting_image
        assert np.sum((locate_feature_in_image(starting_image, template) - self.datum_pixel)**2) < 1, "Template's not centred!"
        update_progress(1)
        if step is None:
            # Next, move a small distance until we see a shift, to auto-determine the calibration distance.
            step = min_step
            shift = 0
            while np.linalg.norm(shift) < threshold_shift:
                assert step < max_step, "Error, we hit the maximum step before we saw the sample move."
                self.move(starting_location + np.array([step,0,0]))
                image = self.color_image()
                shift = locate_feature_in_image(image, template) - image.datum_pixel
                if np.sqrt(np.sum(shift**2)) > threshold_shift:
                    break
                else:
                    step *= 10**(0.5)
            step *= old_div(target_shift, shift) # Scale the amount we step the stage by, to get a reasonable image shift.
        update_progress(2)
        # Move the stage in a square, recording the displacement from both the stage and the camera
        pixel_shifts = []
        images = []
        for i, p in enumerate([[-step, -step, 0], [-step, step, 0], [step, step, 0], [step, -step, 0]]):
          #          print 'premove'
        #        print starting_location,p
            self.move(starting_location + np.array(p))
        #        print 'post move'
            self.settle()
            image = self.color_image()
            pixel_shifts.append(-locate_feature_in_image(image, template) + image.datum_pixel)
            images.append(image)
            # NB the minus sign here: we want the position of the image we just took relative to the datum point of
            # the template, not the other way around.
            update_progress(3+i)
        # We then use least-squares to fit the XY part of the matrix relating pixels to distance
        # location_shifts = np.array([ensure_2d(im.datum_location - starting_location) for im in images])
        # Does this need to be the datum_location... will this really work for when the stage has not previously been calibrated
        location_shifts = np.array([ensure_2d(im.attrs['stage_position'] - starting_location) for im in images])
        pixel_shifts = np.array(pixel_shifts)
        print(np.shape(pixel_shifts),np.shape(location_shifts))
        A, res, rank, s = np.linalg.lstsq(pixel_shifts, location_shifts) # we solve pixel_shifts*A = location_shifts

        self.pixel_to_sample_displacement = np.zeros((3,3))
        self.pixel_to_sample_displacement[2,2] = 1 # just pass Z through unaltered
        self.pixel_to_sample_displacement[:2,:2] = A # A deals with xy only
        fractional_error = np.sqrt(np.sum(res)/np.prod(pixel_shifts.shape)) / np.std(pixel_shifts)
        print(fractional_error)
        print(np.sum(res),np.prod(pixel_shifts.shape),np.std(pixel_shifts))
        if fractional_error > 0.02: # Check it was a reasonably good fit
            print("Warning: the error fitting measured displacements was %.1f%%" % (fractional_error*100))
        self.log("Calibrated the pixel-location matrix.\nResiduals were {}% of the shift.\nStage positions:\n{}\n"
                 "Pixel shifts:\n{}\nResulting matrix:\n{}".format(fractional_error*100, location_shifts, pixel_shifts,
                                                                   self.pixel_to_sample_displacement))
        update_progress(7)
        self.update_config('pixel_to_sample_displacement',self.pixel_to_sample_displacement)
        return self.pixel_to_sample_displacement, location_shifts, pixel_shifts, fractional_error
    def load_calibration(self):
        """Acquire a new spectrum and use it as a reference."""
        self.pixel_to_sample_displacement = self.config_file['pixel_to_sample_displacement'][:]
    def get_qt_ui(self):
        """Create a QWidget that controls the camera.

        Specifying control_only=True returns just the controls for the camera.
        Otherwise, you get both the controls and a preview window.
        """
        return CameraWithLocationUI(self)

    def get_control_widget(self):
        """Create a QWidget to control the CameraWithLocation"""
        return CameraWithLocationControlUI(self)

class CameraWithLocationControlUI(QtWidgets.QWidget):
    """The control box for a CameraWithLocation"""
    calibration_distance = DumbNotifiedProperty(0)
    def __init__(self, cwl):
        super(CameraWithLocationControlUI, self).__init__()
        self.cwl = cwl
        cc = QuickControlBox("Settings")
        cc.add_doublespinbox("calibration_distance")
        cc.add_button("calibrate_xy_gui", "Calibrate XY")
        cc.add_button('load_calibration_gui', 'Load Calibration')
        cc.auto_connect_by_name(self)
        self.calibration_controls = cc

        fc = QuickControlBox("Autofocus")
        fc.add_doublespinbox("af_step_size")
        fc.add_spinbox("af_steps")
        fc.add_button("autofocus_gui", "Autofocus")
        fc.add_button("quick_autofocus_gui", "Quick Autofocus")
        fc.auto_connect_by_name(self.cwl)
        self.focus_controls = fc

#        sc = 

        l = QtWidgets.QHBoxLayout()
        l.addWidget(cc)
        l.addWidget(fc)
        self.setLayout(l)

    def calibrate_xy_gui(self):
        """Run an XY calibration, with a progress bar in the foreground"""
        # 
        run_function_modally(self.cwl.calibrate_xy,
                             progress_maximum=self.cwl.af_steps+1, step = None if self.calibration_distance<= 0 else float(self.calibration_distance))
    def load_calibration_gui(self):
        self.cwl.load_calibration()

class CameraWithLocationUI(QtWidgets.QWidget):
    """Generic user interface for a camera."""

    def __init__(self, cwl):
        assert isinstance(cwl, CameraWithLocation), "instrument must be a CameraWithLocation"
        super(CameraWithLocationUI, self).__init__()
        self.cwl = cwl

        # Set up the UI
        self.setWindowTitle(self.cwl.camera.__class__.__name__ + " (location-aware)")
        layout = QtWidgets.QVBoxLayout()
        # We use a tabbed control section below an image.
        self.tabs = QtWidgets.QTabWidget()
        self.microscope_controls = self.cwl.get_control_widget()
        self.camera_controls = self.cwl.camera.get_control_widget()
        self.tabs.addTab(self.microscope_controls, "Camera with Location controls")
        self.tabs.addTab(self.camera_controls, "Camera")
        # The camera viewer widget is provided by the camera...
        self.camera_preview = self.cwl.camera.get_preview_widget()
        # The overall layout puts the image at the top and the controls below
        l = QtWidgets.QVBoxLayout()
        l.addWidget(self.camera_preview)
        l.addWidget(self.tabs)
        self.setLayout(l)

class AcquireGridOfImages(ExperimentWithProgressBar):
    """Use a CameraWithLocation to acquire a grid of image tiles that can later be stitched together"""
    def __init__(self, camera_with_location=None,completion_function= None, **kwargs):
        super(AcquireGridOfImages, self).__init__(**kwargs)
        self.cwl = camera_with_location
        self.completion_function = completion_function

    def prepare_to_run(self, n_tiles=None, overlap_pixels = 250,
                       data_group=None, autofocus = False, *args, **kwargs):
        self.autofocus = autofocus
        self.progress_maximum = n_tiles[0] * n_tiles[1]
        self.overlap_pixels = overlap_pixels
        self.dest = self.cwl.create_data_group("tiled_image_%d")  if data_group is None else data_group

    def run(self, n_tiles=(1,1), autofocus_args=None):
        """Acquire a grid of images with the specified overlap."""
        self.update_progress(0)
        centre_image = self.cwl.color_image()
        scan_step = np.array(centre_image.shape[:2]) - self.overlap_pixels
        self.log("Starting a {} scan with a step size of {}".format(n_tiles, scan_step))

        dest = self.dest
        x_indices = np.arange(n_tiles[0]) - (n_tiles[0] - 1) / 2.0
        y_indices = np.arange(n_tiles[1]) - (n_tiles[1] - 1) / 2.0
        images_acquired = 0
        try:
            for y_index in y_indices:
                for x_index in x_indices:
                    # Go to the grid point
                    self.cwl.move(centre_image.pixel_to_location(np.array([x_index, y_index]) * scan_step)[:2])
                    # TODO: make autofocus update drift or something...
                    if autofocus_args is not None:
                        self.cwl.autofocus(**autofocus_args)
                    self.cwl.settle()  # wait for the camera to be ready/stage to settle
                    dest.create_dataset("tile_%d",data=self.cwl.color_image())
                    dest.file.flush()
                    images_acquired += 1 # TODO: work out why I can't just use dest.count_numbered_items("tile")
                    self.update_progress(images_acquired)
                x_indices = x_indices[::-1]  # reverse the X positions, so we do a snake-scan
        except ExperimentStopped:
            self.log("Experiment was aborted.")
        finally:
            self.cwl.move(centre_image.datum_location)  # go back to the start point
            if self.completion_function is not None:
                self.completion_function()
        return dest
