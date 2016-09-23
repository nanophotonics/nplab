"""
Camera with Location
====================

Very frequently, we use cameras on microscopes.  This generally involves close collaboration between the camera and
the microscope stage - in particular it's nice to click the camera image to move the stage, and to save position
metadata along with images.  That then leads on to tasks like tiling images together, performing closed-loop positioning
and the like.  `CameraWithLocation` is a sort of meta-instrument, which wraps a Camera and a Stage, and provides the
glue code between the two.

It would be nice to make this a mixin for the camera classes, but for now I think it's cleanest to wrap rather than
try to integrate into Camera.  This class is, however, a work-alike for Camera.

A note on coordinate systems
----------------------------
I've tried to stick to two coordinate systems: that used by the stage, generally called a "location", and pixels in an
image.  Older code often refers to "points" which are in units of fractions-of-an-image; these are not used any more as
they got too confusing.

Images have a "datum pixel", specified in metadata or assumed to be the centre (i.e. pixel (N-1)/2 for a width of N).
This need not be an integer pixel position, but is specified in pixels relative to the [0,0] pixel.  When considering
something within an image, the coordinate system is always relative to pixel [0,0], not relative to the datum pixel.
Similarly, the transformation matrix that moves between pixel and stage coordinates uses [0,0] as its origin, not the
datum pixel.  However, when considering the displacement between two images, this is usually with respect to the datum
pixels of the images - though we should generally specify this.
"""

import nplab
from nplab.instrument.camera import Camera
from nplab.instrument.stage import Stage
from nplab.instrument import Instrument
import numpy as np
from nplab.utils.array_with_attrs import ArrayWithAttrs
import cv2
import cv2.cv
from scipy import ndimage

class ImageWithLocation(ArrayWithAttrs):
    """An image, as a numpy array, with attributes to provide location information"""
    def pixel_to_location(self, pixel):
        """Return the location in the sample of the given pixel.

        NB this returns a 3D location, including Z."""
        p = ensure_2d(pixel)
        l = np.dot(np.concatenate([p[0], p[1], 0, 1]), self.pixel_to_sample_matrix)
        return l[:3]

    def location_to_pixel(self, location, check_bounds=False, z_tolerance=np.infty):
        """Return the pixel coordinates of a given location in the sample.

        location : numpy.ndarray
            A 2- or 3- element numpy array representing sample position, in units of distance.
        check_bounds : bool, optional (default False)
            If this is True, raise an exception if the pixel is not in the image.
        z_tolerance : float, optional (defaults to infinity)
            If we are checking the bounds, make sure the sample location is within this distance of the image's Z
            position.  The default is to allow any distance.

        Returns : numpy.ndarray
        A 2- or 3- element position, to match the size of location passed in.
        """
        l = np.concatenate([ensure_3d(location), [1]])
        p = np.dot(l, np.linalg.inv(self.pixel_to_sample_matrix))
        if check_bounds:
            assert np.all(0 <= p[0:2]), "The location was not within the image"
            assert np.all(p[0:2] <= self.shape[0:2]), "The location was not within the image"
            assert np.abs(p[2]) < z_tolerance, "The location was too far away from the plane of the image"
        if len(location) == 2:
            return p[:2]
        else:
            return p[:3]

    @property
    def datum_pixel(self):
        """The pixel that nominally corresponds to where the image "is".  Usually the central pixel."""
        datum = self.attrs.get('datum_pixel', (np.array(self.shape[:2]) - 1)/2)
        assert len(datum) == 2, "The datum pixel didn't have length 2!"
        return datum

    @property
    def datum_location(self):
        """The location in the sample of the datum pixel"""
        return self.pixel_to_location(self.datum_pixel)

    @property
    def pixel_to_sample_matrix(self):
        """The matrix that maps from pixel coordinates to sample coordinates.

        np.dot(p, M) yields a location for the given pixel, where p is [x,y,0,1] and M is this matrix.  The location
        given will be 4 elements long, and will have 1 as the final element.
        """
        M = self.attrs['pixel_to_sample_matrix']
        assert M.shape == (4, 4), "The pixel-to-sample matrix is the wrong shape!"
        return M
    #TODO: make it sensibly deal with metadata on slicing
    #TODO: split the data type out of this module and put it somewhere sensible


def datum_pixel(image):
    """Get the datum pixel of an image - if no property is present, assume the central pixel."""
    try:
        return np.array(image.datum_pixel)
    except:
        return (np.array(image.shape[:2]) - 1)/2


def ensure_3d(vector):
    """Make sure a vector has 3 elements, appending a zero if needed."""
    if len(vector) == 3:
        return vector
    elif len(vector) == 2:
        return np.array([vector[0], vector[1], 0])
    else:
        raise ValueError("Tried to ensure a vector was 3D, but it had neither 2 nor 3 elements!")


def ensure_2d(vector):
    """Make sure a vector has 3 elements, appending a zero if needed."""
    if len(vector) == 2:
        return vector
    elif len(vector) == 3:
        return vector[:2]
    else:
        raise ValueError("Tried to ensure a vector was 2D, but it had neither 2 nor 3 elements!")


def locate_feature_in_image(image, feature, margin=0, restrict=False):
    """Find the given feature (small image) and return the position of its datum (or centre) in the image's pixels.

    image : numpy.array
        The image in which to look.
    feature : numpy.array
        The feature to look for.  Ideally should be an `ImageWithLocation`.
    margin : int (optional)
        Make sure the feature image is at least this much smaller than the big image.  NB this will take account of the
        image datum points - if the datum points are superimposed, there must be at least margin pixels on each side of
        the feature image.
    restrict : bool (optional, default False)
        If set to true, restrict the search area to a square of (margin * 2 + 1) pixels centred on the pixel that most
        closely overlaps the datum points of the two images.

    The `image` must be larger than `feature` by a margin big enough to produce a meaningful search area.  We use the
    OpenCV `matchTemplate` method to find the feature.  The returned position is the position, relative to the corner of
    the first image, of the "datum pixel" of the feature image.  If no datum pixel is specified, we assume it's the
    centre of the image.
    """
    # The line below is superfluous if we keep the datum-aware code below it.
    assert image.shape[0] > feature.shape[0] and image.shape[1] > feature.shape[1], "Image must be larger than feature!"
    # Check that there's enough space around the feature image
    lower_margin = datum_pixel(image) - datum_pixel(feature)
    upper_margin = (image.shape[:2] - datum_pixel(image)) - (feature.shape[:2] - datum_pixel(feature))
    assert np.all(np.array([lower_margin, upper_margin]) >= margin), "The feature image is too large."
    #TODO: sensible auto-crop of the template if it's too large?
    image_shift = np.array((0,0))
    if restrict:
        # if requested, crop the larger image so that our search area is (2*margin + 1) square.
        image_shift = lower_margin - margin
        image = image[image_shift[0]:image_shift[0] + feature.shape[0] + 2 * margin + 1,
                      image_shift[1]:image_shift[1] + feature.shape[1] + 2 * margin + 1, ...]

    corr = cv2.matchTemplate(image, feature,
                             cv2.TM_SQDIFF_NORMED)  # correlate them: NB the match position is the MINIMUM
    corr = -corr # invert the image so we can find a peak
    corr += (corr.max() - corr.min()) * 0.1 - corr.max()  # background-subtract 90% of maximum
    corr = cv2.threshold(corr, 0, 0, cv2.THRESH_TOZERO)[
        1]  # zero out any negative pixels - but there should always be > 0 nonzero pixels
    assert np.sum(corr) > 0, "Error: the correlation image doesn't have any nonzero pixels."
    peak = ndimage.measurements.center_of_mass(corr)  # take the centroid (NB this is of grayscale values, not binary)
    pos = np.array(peak) + image_shift + datum_pixel(feature) # return the position of the feature's datum point.

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


    def __init__(self, camera=None, stage=None):
        # If no camera or stage is supplied, attempt to retrieve them - but crash with an exception if they don't exist.
        if camera is None:
            camera = Camera.get_instance(create=False)
        if stage is None:
            stage = Stage.get_instance(create=False)
        self.camera = camera
        self.stage = stage

        Instrument.__init__(self)

        shape = self.camera.color_image().shape
        self.datum_pixel = np.array(shape[:2])/2.0 # Default to using the centre of the image as the datum point

    @property
    def pixel_to_sample_matrix(self):
        here = self.datum_location
        datum_displacement = np.dot(self.pixel_to_sample_displacement, ensure_3d(self.datum_pixel))
        M = np.zeros((4,4)) # NB M is never a matrix; that would create issues, as then all the vectors must be matrices
        M[0:3, 0:3] = self.pixel_to_sample_displacement # We calibrate the conversion of displacements and store it
        M[0:3] = here - datum_displacement # Ensure that the datum pixel transforms to here.

    @property
    def datum_location(self):
        """The location in the sample of the datum point (i.e. the current stage position)"""
        return self.stage.position

    def _add_position_metadata(self, image):
        """Add position metadata to an image, assuming it has just been acquired"""
        iwl = ImageWithLocation(image)
        assert iwl.shape[:2] == self.pixel_to_sample_displacement_shape[:2], "Image shape is not the same" \
                                                                             "as when we calibrated!"
        iwl.attrs['pixel_to_sample_matrix'] = self.pixel_to_sample_matrix
        iwl.attrs['datum_pixel'] = self.datum_pixel
        iwl.attrs['stage_position'] = self.stage.position
        return iwl

    ####### Wrapping functions for the camera and stage #######
    def raw_image(self, *args, **kwargs):
        """Return a raw image from the camera, including position metadata"""
        return self._add_position_metadata(self.camera.raw_image(*args, **kwargs))

    def gray_image(self, *args, **kwargs):
        """Return a grayscale image from the camera, including position metadata"""
        return self._add_position_metadata(self.camera.gray_image(*args, **kwargs))

    def color_image(self, *args, **kwargs):
        """Return a colour image from the camera, including position metadata"""
        return self._add_position_metadata(self.camera.color_image(*args, **kwargs))

    def move(self, *args, **kwargs):
        """Move the stage to a given position"""
        self.stage.move(*args, **kwargs)

    def move_rel(self, *args, **kwargs):
        """Move the stage by a given amount"""
        self.stage.move_rel(*args, **kwargs)

    ####### Useful functions for closed-loop stage control #######
    def settle(self, flush_camera=True, *args, **kwargs):
        """Wait for the stage to stop moving/vibrating, and (unless specified) discard frame(s) from the camera.

        After moving the stage, to get a fresh image from the camera we usually need to both wait for the stage to stop
        vibrating, and discard one or more frames from the camera, so we have a fresh one.  This function does both of
        those things (except if flush_camera is False).
        """
        time.sleep(self.settling_time)
        for i in range(self.frames_to_discard):
            self.raw_image(*args, **kwargs)

    def move_to_feature(self, feature, ignore_position=False, margin=50, tolerance=0.5, max_iterations = 10):
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
        if not ignore_position:
            try:
                self.move(feature.datum_location) #initial move to where we recorded the feature was
            except:
                print "Warning: no position data in feature image, skipping initial move."
        image = self.color_image()
        assert isinstance(image, ImageWithLocation), "CameraWithLocation should return an ImageWithLocation...?"

        last_move = np.infty
        for i in range(max_iterations):
            try:
                self.settle()
                image = self.color_image()
                pixel_position = locate_feature_in_image(image, feature, margin=margin, restrict=margin>0)
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

    def calibrate_xy(self, step = None, min_step = 1e-5, max_step=1000):
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
        # First, acquire a template image:
        self.settle()
        starting_image = self.color_image()
        starting_location = self.datum_location
        w, h = starting_image.shape[:2]
        template = starting_image[w/4:3*w/4,h/4:3*h/4, ...] # Use the central 50%x50% as template
        threshold_shift = s[0]*0.02 # Require a shift of at least 2% of the image's width
        target_shift = s[0]*0.1 # Aim for a shift of about 10%

        assert np.sum((locate_feature_in_image(images[-1], template) - self.datum_pixel)**2) < 1, "Template's not centred!"

        if step is None:
            # Next, move a small distance until we see a shift, to auto-determine the calibration distance.
            step = min_step
            shift = 0
            while shift < threshold_shift:
                assert step < max_step, "Error, we hit the maximum step before we saw the sample move."
                self.move(starting_location + np.array([step,0,0]))
                image = self.color_image()
                shift = locate_feature_in_image(image, template) - image.datum_pixel
                if np.sqrt(np.sum(shift**2)) > threshold_shift:
                    break
                else:
                    step *= 10**(0.5)
            step *= target_shift / shift # Scale the amount we step the stage by, to get a reasonable image shift.

        # Move the stage in a square, recording the displacement from both the stage and the camera
        pixel_shifts = []
        for p in [[-step, -step, 0], [-step, step, 0], [step, step, 0], [step, -step, 0]]:
            self.move(starting_location + np.array(p))
            self.settle()
            image = self.color_image()
            pixel_shifts.append(-locate_feature_in_image(image, template) - image.datum_pixel)
            # NB the minus sign here: we want the position of the image we just took relative to the datum point of
            # the template, not the other way around.
        # We then use least-squares to fit the XY part of the matrix relating pixels to distance
        location_shifts = np.array([ensure_2d(im.datum_location - starting_location) for im in images])
        pixel_shifts = np.array(pixel_shifts)
        A, res, rank, s = np.linalg.lstsq(pixel_shifts, location_shifts) # we solve pixel_shifts*A = location_shifts
        self.pixel_to_sample_displacement = np.zeros((3,3))
        self.pixel_to_sample_displacement[2,2] = 1 # just pass Z through unaltered
        self.pixel_to_sample_displacement[:2,:2] = A # A deals with xy only
        fractional_error = np.sqrt(np.sum(res)/np.prod(pixel_shifts.shape)) / np.std(pixel_shifts)
        if fractional_error > 0.02: # Check it was a reasonably good fit
            print "Warning: the error fitting measured displacements was %.1f%%" % fractional_error*100
        self.log("Calibrated the pixel-location matrix.  Residuals were {}% of the shift.\nStage positions:\n{}\n"
                 "Pixel shifts:\n{}\nResulting matrix:\n{}".format(fractional_error*100, location_shifts, pixel_shifts,
                                                                   self.pixel_to_sample_displacement))
        return self.pixel_to_sample_displacement, location_shifts, pixel_shifts, fractional_error
