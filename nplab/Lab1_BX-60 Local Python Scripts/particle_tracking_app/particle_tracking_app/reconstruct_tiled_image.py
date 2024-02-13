# -*- coding: utf-8 -*-
"""
Reconstruction of tiled images

@author: rwb27
"""
from __future__ import division
from __future__ import print_function

from builtins import zip
from builtins import range
from past.utils import old_div
import nplab
import numpy as np
import matplotlib.pyplot as plt
import cv2
#import cv2.cv
from scipy import ndimage
from nplab.utils.image_with_location import ImageWithLocation
from nplab.utils.array_with_attrs import ArrayWithAttrs

def get_pixel_positions(tiles):
    """Given a list of images, extract the relative positions of the images.
    
    tiles: [h5py.Dataset or ArrayWithAttrs]
        Each tile should be an image, assumed to be all the same size, in RGB
        format.  Each must have a pixel_to_sample_matrix attribute, as defined
        in ArrayWithAttrs.  Currently this script ignores datum_position.
        
    Returns: numpy.ndarray, numpy.ndarray
        The first return value is Nx2, where N is the number of tiles.  The 
        positions are relative to the mean position of all images, and are in 
        units of pixels (NB NOT "camera units").
        The second return value is 2 elements, the mean position (in sample
        coordinates) of all the images.  This corresponds to a "pixel position"
        of (0,0)
    """
    image_size = np.array(tiles[0].shape[:2]) #:2 because we only want width, height
    positions = []
    for tile in tiles:
        iwl = ImageWithLocation(tile, tile.attrs) # Yes, this does unnecessarily load images.
                                                  # We can optimise if it's a problem...
        positions.append(iwl.datum_location)
        assert np.all(tile.shape[:2] == tuple(image_size)), "Images were not all the same size!"
    iwl = ImageWithLocation(tiles[-1], tiles[-1].attrs) # Make an ImageWithLocation for the transforms
    positions = np.array(positions)

    # We want the position in pixels of the centre of each image, relative to the overall centre (defined as the mean
    # position of all images, i.e. the centroid.  NB this currently uses the transform information only from the last
    # tile - but they will most likely all be the same anyway...
    centre = np.mean(positions, axis=0)
    pixel_centre = iwl.location_to_pixel(centre)
    pixel_positions = np.array([iwl.location_to_pixel(pos) - pixel_centre for pos in positions])
    return pixel_positions, centre

def plot_images_in_situ(tiles, positions, ax=None, 
                        downsample=5, outlines=False, centres=False):
    """Plot a set of images at the given (pixel) positions.
    
    Arguments:
    tiles: [h5py.Dataset]
        A list of images as HDF5 datasets or numpy ndarrays.
    positions: numpy.ndarray Nx2
        A numpy array of positions, in pixels, of each image.
    ax: matplotlib.Axes
        An axes object in which to plot the images - default: create new figure
    downsample: int
        Set the downsampling factor: we speed up plotting by only using every
        nth pixel in X and Y.  Default may vary - but currently it's 5.
    outlines: bool
        Whether to plot the outline of each image as a line
    centres: bool
        Whether to plot a dot at the centre of each image
    """
    if ax is None:
        f, ax = plt.subplots(1,1)
    ax.set_aspect(1)
    #plot the images in position
    for pos, image in zip(positions, tiles):
        small_image = image[::downsample,::downsample,:]
        ax.imshow(small_image[::1,::-1,:].transpose(1,0,2),
                  extent=[pos[i] + s*tile.shape[i] 
                          for i in [0,1] for s in [-0.5,0.5]],
                 )
    if outlines:#plot the outlines
        square = np.array([[-1,-1],[-1,1],[1,1],[1,-1],[-1,-1]])
        for pos in pixel_positions:
            rect = pos + image_size * 0.5 * square
            ax.plot(rect[:,0],rect[:,1])
    if centres:#plot the centre of each image
        ax.plot(positions[:,0],positions[:,1],'ro')
    ax.autoscale()


def compareplot(a,b, gain=10, axes=None):
    """Plot two sets of coordinates, highlighting their differences.
    
    a, b: numpy.ndarray
        An Nx2 array of points
    gain: float
        The amount to amplify differences when plotting arrows
    axes: matplotlib.Axes
        An axes object in which we make the plot - otherwise a new one
        will be created.
    """
    if axes is None:
        f, axes = plt.subplots(1,1)
    axes.plot(a[:,0],a[:,1])
    axes.plot(b[:,0],b[:,1])
    for ai, bi in zip(a,b):
        axes.arrow(ai[0],ai[1],(bi[0]-ai[0])*10,(bi[1]-ai[1])*10)


def find_overlapping_pairs(pixel_positions, image_size,
                           fractional_overlap=0.1):
    """Identify pairs of images with significant overlap.
    
    Given the positions (in pixels) of a collection of images (of given size),
    calculate the fractional overlap (i.e. the overlap area divided by the area
    of one image) and return a list of images that have significant overlap.
    
    Arguments:
    pixel_positions: numpy.ndarray
        An Nx2 array, giving the 2D position in pixels of each image.
    image_size: numpy.ndarray
        An array of length 2 giving the size of each image in pixels.
    fractional_overlap: float
        The fractional overlap (overlap area divided by image area) that two
        images must have in order to be considered overlapping.
    
    Returns: [(int,int)]
        A list of tuples, where each tuple describes two images that overlap.
        The second int will be larger than the first.
    """
    tile_pairs = []
    for i in range(pixel_positions.shape[0]):
        for j in range(i+1, pixel_positions.shape[0]):
            overlap = image_size - np.abs(pixel_positions[i,:2] -
                                          pixel_positions[j,:2])
            overlap[overlap<0] = 0
            tile_pairs.append((i, j, np.product(overlap)))
    overlaps = np.array([o for i,j,o in tile_pairs])
    try:
        overlap_threshold = np.max(overlaps)*0.2
        overlapping_pairs = [(i,j) for i,j,o in tile_pairs if o>overlap_threshold]
    except ValueError:
        overlapping_pairs = []
    return overlapping_pairs

#################### Cross-correlate overlapping pairs to match them up #######
def croscorrelate_overlapping_images(tiles, overlapping_pairs, 
                                     pixel_positions, 
                                     fractional_margin=0.02):
    """Calculate actual displacements between pairs of overlapping images.
    
    For each pair of overlapping images, perform a cross-correlation to
    fine-tune the displacement between them.
    
    Arguments:
    tiles: [h5py.Dataset]
        A list of datasets (or numpy images) that represent the images.
    overlapping_pairs: [(int,int)]
        A list of tuples, where each tuple describes two images that overlap.
    pixel_positions: numpy.ndarray
        An Nx2 array, giving the 2D position in pixels of each image.
    fractional_margin: float
        Allow for this much error in the specified positions (given as a 
        fraction of the length of the smaller side of the image).  Defaults to
        0.02 which should be fine for our typical microscope set-ups.
    
    Results: np.ndarray
        An Mx2 array, giving the displacement in pixels between each pair of
        images specified in overlapping_pairs.
    """
    #FIXME currently half a pixel out for odd-sized images
    #FIXME currently breaks if overlap in X or Y is negative
    image_size = np.array(tiles[0].shape[:2]) #:2 because we only want width, height
    margin = np.int(np.min(image_size) * 0.02)
    correlated_pixel_displacements = []
    for i, j in overlapping_pairs:
        original_displacement = np.round(pixel_positions[j,:2] - pixel_positions[i,:2])
        overlap_size = image_size - np.abs(original_displacement)
        assert np.all(overlap_size > margin), "Overlaps must be greater than the margin"
        assert np.all(overlap_size <= image_size), "Overlaps can't be bigger than the image"
        #this slightly dense structure creates slices for the overlapping part
        i_slices = [slice(0,ol) if od<0 else slice(im-ol,im) 
                    for im, ol, od in zip(image_size.astype(np.int), 
                                          overlap_size.astype(np.int), 
                                          original_displacement)]
        j_slices = [slice(margin,ol-margin) if od>0 else slice(im-ol+margin,im-margin) 
                    for im, ol, od in zip(image_size.astype(np.int), 
                                          overlap_size.astype(np.int), 
                                          original_displacement)]
        #correlate them: NB the match position is the MINIMUM
        corr = -cv2.matchTemplate(np.array(tiles[i])[i_slices+[slice(None)]],
                                  np.array(tiles[j])[j_slices+[slice(None)]],
                                  cv2.TM_SQDIFF_NORMED)
        corr += (corr.max()-corr.min())*0.1 - corr.max() #background-subtract 90% of maximum
        corr = cv2.threshold(corr, 0, 0, cv2.THRESH_TOZERO)[1] #zero out any negative pixels - but there should always be > 0 nonzero pixels
        peak = ndimage.measurements.center_of_mass(corr) #take the centroid (NB this is of grayscale values not just binary)
        shift = peak - old_div(np.array(corr.shape),2)
        correlated_pixel_displacements.append(original_displacement + shift)
    correlated_pixel_displacements = np.array(correlated_pixel_displacements)
    return correlated_pixel_displacements

def pair_displacements(pairs, positions):
    """Calculate the displacement between each pair of positions specified.
    
    Arguments:
    pairs: [(int,int)]
        A list of tuples, where each tuple describes two images that overlap.
    positions: numpy.ndarray
        An Nx2 array, giving the 2D position in pixels of each image.
    
    Result: numpy.ndarray
        An Mx2 array, giving the 2D displacement between each pair of images.
    """
    return np.array([positions[j,:]-positions[i,:] for i,j in pairs])

                                            
def fit_affine_transform(pairs, positions, displacements):
    """Find an affine transform to make positions match a set of displacements.
    
    Find an affine tranform (i.e. 2x2 matrix) that, when applied to the 
    positions, matches the specified pair displacements as closely as possible.
    
    Arguments:
    pairs: [(int,int)]
        A list of M tuples, where each tuple describes two images that overlap.
    positions: numpy.ndarray
        An Nx2 array, giving the 2D position in pixels of each image.
    displacements: numpy.ndarray
        An Mx2 array, giving the 2D displacement between each pair of images.
    
    Result: numpy.ndarray, numpy.ndarray
        A tuple of two things: firstly, a 2x2 matrix that transforms the given
        pixel positions to match the displacements.  Secondly, the positions
        so transformed (i.e. the corrected positions).
    """
    starting_displacements = pair_displacements(pairs, positions)
    if pairs:
        affine_transform = np.linalg.lstsq(starting_displacements, 
                                           displacements)[0]
    else:
        affine_transform = np.identity(2)
    corrected_positions = np.dot(positions, affine_transform)
    return affine_transform, corrected_positions
    
    
def rms_error(pairs, positions, displacements, print_err=False):
    """Find the RMS error in image positons (against some given displacements)
    
    Arguments:
    pairs: [(int,int)]
        A list of M tuples, where each tuple describes two images that overlap.
    positions: numpy.ndarray
        An Nx2 array, giving the 2D position in pixels of each image.
    displacements: numpy.ndarray
        An Mx2 array, giving the 2D displacement between each pair of images.
    print_err: bool
        If true, print the RMS error to the console.
    
    Returns: float
        The RMS difference between the displacements calculated from the given
        positions and the displacements specified.
    """
    error = np.std(pair_displacements(pairs, positions) - displacements)
    if print_err:
        print("RMS Error: %.2f pixels" % error)
    return error
        

###################### Look at each image and shift it to the optimal place ###
def optimise_positions(pairs, positions, displacements):
    """Adjust the positions slightly so they better match the displacements.
    
    After fitting an affine transform (which takes out calibration error) we 
    run this method: it moves each tile to minimise the difference between 
    measured and current displacements.
    
     Arguments:
    pairs: [(int,int)]
        A list of M tuples, where each tuple describes two images that overlap.
    positions: numpy.ndarray
        An Nx2 array, giving the 2D position in pixels of each image.  NB this
        will be modified!  Copy it first if you don't want that.
    displacements: numpy.ndarray
        An Mx2 array, giving the 2D displacement between each pair of images.
    
    Returns: numpy.ndarray
        The modified positions array.
    
    Side Effects:
        "positions" will be modified so it better matches displacements.
    """
    if pairs:
        positions_d = pair_displacements(pairs, positions)
        for k in range(positions.shape[0]): #for each particle
            # find the displacement from here to each overlapping image
            measured_d = np.array([d if i==k else -d 
                                   for (i,j), d in zip(pairs, displacements)
                                   if i==k or j==k])
            current_d = np.array([d if i==k else -d 
                                   for (i,j), d in zip(pairs, positions_d)
                                   if i==k or j==k])
            # shift the current tile in the direction suggested by measured 
            # displacements
            #print "shift:", np.mean(measured_d-current_d,axis=0)
            positions[k,:] -= np.mean(measured_d-current_d,axis=0)
    return positions
        


################### Stitch the images together ################################
def stitch_images(tiles, positions, downsample=3):
    """Merge images together, using supplied positions (in pixels).
    
    Currently we use a crude algorithm - we pick the pixel from whichever image
    is closest.
    
    Arguments:
    tiles: [h5py.Dataset]
        A list of datasets (or numpy images) that represent the images.
    positions: numpy.ndarray
        An Nx2 array, giving the 2D position in pixels of each image.
    downsample: int
        The size of the stitched image will be reduced by this amount in each
        dimension, to save on resources.  NB currently it decimates rather than
        taking a mean, for speed - in the future a mean may be an option.
        Images are downsampled after taking into account their position, i.e.
        if you downsample by a factor of 5, you'll still be within 1 original
        pixel, not within 5, of the right position.  Currently we don't do
        any sub-pixel shifting.
        
    Returns: (stitched_image, stitched_centre, image_centres)
        (numpy.ndarray, numpy.ndarray, numpy.ndarray)
        An MxPx3 array containing the stitched image, a 1D array of length
        2 containing the coordinates of the centre of the image in non-
        downsampled pixel coordinates, and an Nx2 array of the positions of the
        source images (their centres) relative to the top left of the stitched
        image, in downsampled pixels.
    """
    positions = positions.copy() #prevent unpleasant side effects
    p = positions
    # first, work out the size and position of the stitched image
    image_size = np.array(tiles[0].shape[:2])
    stitched_size = np.array(np.round(old_div((np.max(p, axis=0) - np.min(p, axis=0) 
                                + image_size),downsample)),dtype = np.int)
    
    stitched_centre = old_div((np.max(p, axis=0) + np.min(p, axis=0)),2)
    stitched_image = np.zeros(tuple(stitched_size)+(3,), dtype=np.uint8)
    # now calculate the position of each image relative to the big image
    stitched_centres = old_div((positions - stitched_centre 
                        + np.array(stitched_image.shape[:2])*downsample/2.0),downsample)
    for tile, centre in zip(tiles, stitched_centres):
        topleft = centre - image_size/2.0/downsample
        #topleft is the (downsampled) pixel coordinates of the tile's corner in the big image
        shift = (np.ceil(topleft) - topleft) * downsample
        w, h, d = tile.shape
        img = np.zeros((old_div(w,downsample) - 1, old_div(h,downsample) - 1, d), dtype=np.uint8)
        # Crudely downsample (TODO: take a mean rather than downsampling)
        #for dx in range(downsample):
        #    for dy in range(downsample):
        #        img += tile[shift+dx:shift+dx+downsample*img.shape[0]:downsample,
        #                    shift+dy:shift+dy+downsample*img.shape[1]:downsample,
        #                    :] / downsample**2
        img = tile[int(shift[0]):int(shift[0]+downsample*img.shape[0]):downsample,
                   int(shift[1]):int(shift[1]+downsample*img.shape[1]):downsample,
                   :]
        # Now, we zero out the tile for all the pixels where the centre of
        # another image is closer than the centre of this one
        for other_centre in stitched_centres:
            if np.any(other_centre != centre): # don't compare to this image
                difference = other_centre - centre
                midpoint = old_div((other_centre + centre),2)
                for yi in range(img.shape[1]):
                    
                    y = np.ceil(topleft[1]) + yi
                    xi_threshold = int(np.ceil(midpoint[0] 
                                            - old_div((y - midpoint[1])*difference[1],difference[0]) 
                                            - np.ceil(topleft[0])))
                    # we pretty much want to set pixels to zero where
                    # difference.(x - midpoint) > 0
                    # FIXME: this might go wrong if ever we hit zero exactly...
                    if difference[0] > 0:
                        if xi_threshold < 0:
                            xi_threshold = 0
                        if xi_threshold < img.shape[0]:
                            img[int(xi_threshold):,yi,:] = 0
                    else:
                        if xi_threshold > img.shape[0]:
                            xi_threshold = img.shape[0]
                        if xi_threshold > 0:
                            img[:xi_threshold,yi,:] = 0
        #print "Inserting image at {0}, size {1}, canvas size {2}".format(
        #        np.ceil(topleft), img.shape, stitched_image.shape)
        stitched_image[int(np.ceil(topleft[0])):int(np.ceil(topleft[0])+img.shape[0]),
                       int(np.ceil(topleft[1])):int(np.ceil(topleft[1])+img.shape[1]),:] += img
    return stitched_image, stitched_centre, stitched_centres
                       
def reconstruct_tiled_image(tiles,
                            downsample=1):
    """Combine a sequence of images into a large tiled image.
    
    This function takes a list of images and approximate positions.  It first
    aligns the images roughly, then uses crosscorrelation to find relative
    positions of the images.  Positions of the images are optimised and the
    tiles are then stitched together with a crude pick-the-closest-image-centre
    algorithm.  Importantly, we keep careful track of the relationship between
    pixels in the original images, their positions (in "sample" units), and the
    same features in the stitched image.
    
    Arguments:
    tiles: [h5py.Dataset]
        Each tile should be an image, assumed to be all the same size, in RGB
        format.  Each must have attributes "pixel_to_sample_matrix" as defined
        in the ImageWithLocation class
    positioning_error: float [removed - may come back...]
        The error (in fraction-of-an-image units) to allow for in the given
        positions.  1 corresponds to an entire image width - values larger than
        1/3 of the overlap between images are likely to be problematic.  The
        default of 0.02 is sensible for a good mechanical stage.
    downsample: int
        Downsampling factor (produces a less huge output image).  Only applies
        to the final stitching step.
    
    Returns: dict
        This function returns a dictionary with various elements:
        stitched_image: numpy.ndarray
            The stitched image as a numpy array
        stitched_to_sample: numpy.ndarray
            A mapping matrix that transforms from image coordinates (0-1 for X 
            and Y) to "sample" coordinates (whatever the original positions 
            were specified in)
        stitched_centre: numpy.ndarray
            The centre of the stitched image, again in sample coordinates.
        image_centres: numpy.ndarray
            The centres of the tiles, in pixels in the stitched image (mostly 
            for debug purposes, but can be useful to locate the original tile 
            for a given pixel).  It has dimensions Nx2, where N is the number
            of source images.
        corrected_camera_to_sample: numpy.ndarray
            The 2x2 mapping matrix passed as input, tweaked to better match
            the measured displacements between the images, and their given
            positions.
    """
    # extract positions from the metadata
   # positions, scan_centre = get_pixel_positions(tiles, camera_to_sample)
    positions, scan_centre = get_pixel_positions(tiles) # removed input (camera to sample)
    # then find images with at least 10% overlap
    pairs = find_overlapping_pairs(positions, tiles[0].shape[:2], 
                                   fractional_overlap=0.1)
                                   
    print("Finding displacements between  images (may take a while)...")
    # compare overlapping images to find the true displacement between them
    displacements = croscorrelate_overlapping_images(tiles, pairs, positions, 
                                                     fractional_margin=0.02)
                                                     
    # now we start the optimisation...
    errors = [rms_error(pairs, positions, displacements, print_err=True)]
    
    # first, fit an affine transform, to correct for the calibration between
    # camera and stage being slightly off (rotation, scaling, etc.)
    affine_transform, positions = fit_affine_transform(pairs, positions,
                                                       displacements)
    pixel_to_sample_matrix = tiles[-1].attrs['pixel_to_sample_matrix']
    pixel_to_sample_matrix[:2,:2] = np.dot(np.linalg.inv(affine_transform),
                                           pixel_to_sample_matrix[:2,:2])
    errors.append(rms_error(pairs, positions, displacements, print_err=True))
    
    print("Optimising image positions...")
    # next, optimise the positions iteratively
    while len(errors) < 5 or (errors[-2] - errors[-1]) > 0.001:
        assert len(errors) < 100, "Optimisation failed to converge"
        positions = optimise_positions(pairs, positions, displacements)
        errors.append(rms_error(pairs, positions, displacements, print_err=True))
    
    print("Combining images...")
    # finally, stitch the image!
    stitched_image, stitched_centre, image_centres = stitch_images(tiles, 
                                            positions, downsample=downsample)
    
    # now work out how the new image relates to the stage coordinates
    # the correct camera-to-sample matrix for source images is 
    # corrected_camera_to_sample; we need to adjust for image size though.
    stitched_image = ImageWithLocation(stitched_image)
    stitched_image.attrs['datum_pixel'] = [stitched_centre[0]+old_div(stitched_image.shape[0],2),
                                             stitched_centre[1]+old_div(stitched_image.shape[1],2)]
#    stitched_image.attrs['datum_pixel'] = [stitched_centre[0]+stitched_image.shape[0],
#                                             stitched_centre[1]+stitched_image.shape[1]]
#    stitched_image.attrs['datum_pixel'] = [stitched_image.shape[0]/2,
#                                             stitched_image.shape[1]/2]
    stitched_image.attrs['stage_position'] = scan_centre
    pixel_to_sample_mat = np.zeros((4,4))
    pixel_to_sample_mat[:2,:2] = tiles[-1].attrs['pixel_to_sample_matrix'][:2,:2]*downsample
    pixel_to_sample_mat[2,2] = 1
    theory_centre =np.dot(stitched_image.attrs['datum_pixel'],pixel_to_sample_mat[:2,:2])
    offset = scan_centre[:2] - theory_centre
    pixel_to_sample_mat[3,:2]=offset #wrong must be the 0,0 pixel location not the e
    pixel_to_sample_mat[3,2]=scan_centre[2]
    stitched_image.attrs['pixel_to_sample_matrix'] = pixel_to_sample_mat
    return stitched_image
#    image_size = np.array(tiles[0].shape[:2])
#    stitched_size = np.array(stitched_image.shape[:2])
#    size_in_images =  stitched_size.astype(np.float) * downsample / image_size
#    stitched_to_sample = corrected_camera_to_sample * size_in_images[:, np.newaxis]
#    
#    shift_in_sample_coords = np.dot(stitched_centre/image_size,
#                                    corrected_camera_to_sample)
#    stitched_centre = np.append(shift_in_sample_coords,0) + scan_centre
#     
#    return {'stitched_image': stitched_image, 
#            'stitched_to_sample': stitched_to_sample, 
#            'stitched_centre': stitched_centre, 
#            'image_centres': image_centres,
#            'corrected_camera_to_sample': corrected_camera_to_sample}
    
if __name__ == "__main__":
    nplab.datafile.set_current("2015-10-01_3.h5",mode="r")
    df = nplab.current_datafile()
    tiled_image = df['CameraStageMapper/tiled_image_2']
    tiles = tiled_image.numbered_items("tile")
    camera_to_sample = tiled_image.attrs.get("camera_to_sample")

    print("Combining {0} images into a tiled scan.".format(len(tiles)))
    
    reconstruction = reconstruct_tiled_image(tiles,
                                             camera_to_sample=camera_to_sample,
                                             positioning_error=0.02,
                                             downsample=1)
    stitched_image = reconstruction['stitched_image']
    stitched_to_sample = reconstruction['stitched_to_sample']
    stitched_centre = reconstruction['stitched_centre']
    
    stitched_size = np.array(stitched_image.shape[:2])
    retransformed_coords = np.dot(old_div(image_centres,stitched_size)-0.5, 
                                  stitched_to_sample) + stitched_centre[:2]    
    actual_coords = np.array([tile.attrs.get("camera_centre_position") 
                              for tile in tiles])
    # check the original positions match (+/- stage error):
    #compareplot(retransformed_coords, actual_coords)
    
    if False:
        # A crude interactive example that shows the source tile when the
        # stitched image is clicked.  Needs a lot of work!
        corrected_camera_to_sample = reconstruction['corrected_camera_to_sample']
        image_centres = reconstruction['image_centres']
        image_size = np.array(tiles[0].shape[:2])
        stitched_size = np.array(stitched_image.shape[:2])
        """Make an interactive, clickable plot"""
    
        f, ax = plt.subplots(1,2)
        ax[0].imshow(stitched_image)
        ax[0].plot(image_centres[:,1],image_centres[:,0],'bo')
        current_tile_index = -1
        def clicked_stitched_image(event):
            """Pop up the original image for a clicked point, and show the point"""
            global current_tile_index
            here = np.array([event.ydata,event.xdata])
            tile_index = np.argmin(np.sum((image_centres-here)**2, axis=1))
            tile = tiles[tile_index]
            if tile_index != current_tile_index:
                current_tile_index = tile_index
                ax[1].imshow(tile)
                print("now closest to tile %d" % tile_index)
                ax[1].autoscale()
            
            # work out where we clicked in sample coords
            image_coords = old_div(here.astype(np.float),np.array(stitched_image.shape[:2]))
            image_coords -= np.array([0.5,0.5])
            sample_coords = np.dot(image_coords, stitched_to_sample)
            sample_coords += stitched_centre[:2]
            print("clicked on sample coords: {0}".format(tuple(sample_coords)))
            
            # highlight that point in the source image
            displacement_in_tile = sample_coords - tile.attrs.get('camera_centre_position')[:2]
            displacement_pixels = image_size * np.dot(displacement_in_tile,
                                                      np.linalg.inv(corrected_camera_to_sample)) #NO LONGER RETURNED!!
            pixel_position = displacement_pixels + old_div(image_size,2)
            if len(ax[1].lines) == 0:
                ax[1].plot(pixel_position[1],pixel_position[0],'r+')
            else:
                ax[1].lines[0].set_data((pixel_position[1],pixel_position[0]))
            ax[0].figure.canvas.draw()
            print("pixel position in tile: ", pixel_position)
        f.canvas.mpl_connect('button_release_event', clicked_stitched_image)

    """
    if plot_as_we_go:
        f, ax = plt.subplots(1,1)
        ax.set_aspect('auto')
        ax.plot(errors)
        ax.set_xlabel("Iteration")
        ax.set_ylabel("RMS error in image positions")
        
    if plot_as_we_go:
        downsample=3
        f = plt.figure()
        ax0 = f.add_subplot(1,2,1)
        ax1 = f.add_subplot(1,2,2,sharex=ax0,sharey=ax0)
        for ax in [ax0,ax1]:
            ax.set_aspect(1)
        #plot the images in position
    """
