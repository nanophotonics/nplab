"""
Image With Location
===================

This datatype supports the various operations that rely on linking a camera to a microscope stage.  It is an image
along with the metadata required to relate positions in the image to positions in real life.

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

We transform between pixel and location coordinate systems with a matrix, the `pixel_to_sample_matrix`.  Usually it
is called ``M`` in mathematical expressions.  To convert a pixel coordinate to a location, we post-multiply the pixel
coordinate by the matrix, i.e. ``l = p.M`` and to convert the other way we use the inverse of ``M`` so ``p = l.M``
where the dot denotes matrix multiplication using `numpy.dot`.
"""
from __future__ import division

from builtins import range
from past.utils import old_div
import numpy as np
from nplab.utils.array_with_attrs import ArrayWithAttrs
import cv2
#import cv2.cv
from scipy import ndimage

class ImageWithLocation(ArrayWithAttrs):
    """An image, as a numpy array, with attributes to provide location information"""
#    def __array_finalize__(self, obj):
#        """Ensure that the object is a properly set-up ImageWithLocation"""
#        ArrayWithAttrs.__array_finalize__(self, obj) # Ensure we have self.attrs
    def __getitem__(self, item):
        """Update the metadata when we extract a slice"""
        try:
            # Handle specially the case where we are extracting a 2D region of the image, i.e. the first and second
            # indices are slices.  We test for that here - and do it in a try: except block so that if, for example,
            # item is not indexable,
            assert isinstance(item[0], slice), "First index was not a slice"
            assert isinstance(item[1], slice), "Second index was not a slice"
            start = np.array([item[i].start for i in range(2)])
            start = np.where(start == np.array(None), 0, start) # missing start points are equivalent to zero
            step = np.array([item[i].step for i in range(2)])
            step = np.where(step == np.array(None), 1, step) # missing step is equivalent to step==1
        except:
            # If the above doesn't work, assume we're not dealing with a 2D slice and give up.
            return super(ImageWithLocation, self).__getitem__(item) # pass it on up

        out = super(ImageWithLocation, self).__getitem__(item) # retrieve the slice
        out.datum_pixel -= start # adjust the datum pixel so it refers to the same part of the image
        # Next, we adjust the constant part of the pixel-sample matrix so pixels stay in the same place
        location_shift = np.dot(ensure_3d(start), self.pixel_to_sample_matrix[:3,:3])
        out.pixel_to_sample_matrix[3,:3] += location_shift
        if not np.all(step == 1):
            # if we're downsampling, remember to scale datum_pixel accordingly
            out.datum_pixel = old_div(out.datum_pixel, step)
            # Scale the pixel-to-sample matrix if we've got a non-unity step in the slice
            # I don't understand why I can't do this with slicing, but it all goes wrong...
            for i in range(2):
                out.pixel_to_sample_matrix[i, :3] *= step[i]
        return out

    def pixel_to_location(self, pixel):
        """Return the location in the sample of the given pixel.

        NB this returns a 3D location, including Z."""
        p = ensure_2d(pixel)
        l = np.dot(np.array([p[0], p[1], 0, 1]), self.pixel_to_sample_matrix)
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
        l = ensure_2d(location)
        l = l[:2]-self.pixel_to_sample_matrix[3,:2]
        p = np.dot(l, np.linalg.inv(self.pixel_to_sample_matrix[:2,:2]))
        if check_bounds:
            assert np.all(0 <= p[0:2]), "The location was not within the image"
            assert np.all(p[0:2] <= self.shape[0:2]), "The location was not within the image"
            assert np.abs(p[2]) < z_tolerance, "The location was too far away from the plane of the image"
        if len(location) == 2:
            return p[:2]
        else:
            return p[:3]

    def feature_at(self, centre_position, size=(100,100), set_datum_to_centre=True):
        """Return a thumbnail cropped out of this image, centred on a particular pixel position.

        This is simply a convenience method that saves typing over the usual slice syntax.  Below are two equivalent
        ways of extracting a thumbnail:
            pos = (240,320)
            size = (100,100)
            thumbnail = image[pos[0] - size[0]/2:pos[0] + size[0]/2, pos[1] - size[1]/2:pos[1] + size[1]/2, ...]
            thumbnail2 = image.feature_at(pos, size)
            thumbnail3 = image[190:290 270:370]

        ``centre_position`` and ``size`` should be two-element tuples, but the intention is that this code will cope
        gracefully with floating-point values.

        NB the datum pixel of the returned image will be set to its centre, not the datum position of the original image
        by default.  Give the argument ``set_datum_to_centre=False`` to disable this behaviour.
        """
        try:
            float(centre_position[0])
            float(centre_position[1])
            float(size[0])
            float(size[1])
        except:
            raise IndexError("Error: arguments of feature_at were invalid: {}, {}".format(centre_position, size))
        pos = centre_position

        # For now, rely on numpy to complain if the feature is outside the image.  May do bound-checking at some point.
        # If so, we might need to think carefully about the datum pixel of the resulting image.
        thumb = self[pos[0] - old_div(size[0],2):pos[0] + old_div(size[0],2), pos[1] - old_div(size[1],2):pos[1] + old_div(size[1],2), ...]
        if set_datum_to_centre:
            thumb.datum_pixel = (old_div(size[0],2), old_div(size[1],2)) # Make the datum point of the new image its centre.
        return thumb

    def downsample(self, n):
        """Return a view of the image, downsampled (sliced with a non-unity step).

        In the future, an optional argument to this function may take means of blocks of the images to improve signal
        to noise.  Currently it just decimates (i.e. throws away rows and columns).
        """
        assert n > 0, "The downsampling factor must be an integer greater than 0"
        return self[::int(n), ::int(n), ...] # The slicing code handles updating metadata

    @property
    def datum_pixel(self):
        """The pixel that nominally corresponds to where the image "is".  Usually the central pixel."""
        datum = self.attrs.get('datum_pixel', old_div((np.array(self.shape[:2]) - 1),2))
        assert len(datum) == 2, "The datum pixel didn't have length 2!"
        return datum

    @datum_pixel.setter
    def datum_pixel(self, datum):
        assert len(datum) == 2, "The datum pixel didn't have length 2!"
        self.attrs['datum_pixel'] = datum

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
        assert M.dtype.kind == "f", "The pixel-to-sample matrix is not floating point!"
        return M

    @pixel_to_sample_matrix.setter
    def pixel_to_sample_matrix(self, M):
        M = np.asanyarray(M) #ensure it's an ndarray subclass
        assert M.shape == (4, 4), "The pixel-to-sample matrix must be 4x4!"
        assert M.dtype.kind == "f", "The pixel-to-sample matrix must be floating point!"
        self.attrs['pixel_to_sample_matrix'] = M

    #TODO: split the data type out of this module and put it somewhere sensible


def datum_pixel(image):
    """Get the datum pixel of an image - if no property is present, assume the central pixel."""
    try:
        return np.array(image.datum_pixel)
    except:
        return old_div((np.array(image.shape[:2]) - 1),2)


def ensure_3d(vector):
    """Make sure a vector has 3 elements, appending a zero if needed."""
    if len(vector) == 3:
        return np.array(vector)
    elif len(vector) == 2:
        return np.array([vector[0], vector[1], 0])
    else:
        raise ValueError("Tried to ensure a vector was 3D, but it had neither 2 nor 3 elements!")


def ensure_2d(vector):
    """Make sure a vector has 3 elements, appending a zero if needed."""
    if len(vector) == 2:
        return np.array(vector)
    elif len(vector) == 3:
        return np.array(vector[:2])
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
    centre of the image.  The output of this function can be passed into the pixel_to_location() method of the larger
    image to yield the position in the sample of the feature you're looking for.
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
        image_shift = np.array(lower_margin - margin,dtype = int)
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
    return pos