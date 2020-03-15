# -*- coding: utf-8 -*-
"""
Created on Fri Oct 02 20:13:01 2015

@author: rwb27
"""
from __future__ import division
from __future__ import print_function

from past.utils import old_div
import matplotlib.pyplot as plt
import numpy as np
import matplotlib
from scipy import ndimage

def plot_skewed_image(image, corners, axes=None, *args, **kwargs):
    """Plot an image in a quadrilateral that has the given corners.
    
    Unfortunately, images plotted with the (very fast) imshow method must be
    bounded by a rectangle with sides parallel to the axes.  This method allows
    images to be plotted in an arbitrary quadrilateral, useful (for example) if
    we want to plot images in units of stage displacement.
    
    @param: ax: A matplotlib axes object in which to plot the image
    @param: image: An image, stored as an NxM or NxMx3 array
    @param: corners: Coordinates of the corners of the array in the order
    [bottom left, top left, bottom right, top right] as a list of tuples or a
    4x2 array.
    
    Extra arguments/keyword arguments are passed to axes.pcolormesh
    """
    shape = image.shape
    assert len(shape) == 2 or (len(shape) == 3 and (shape[2] == 3 or shape[2] == 4)), "the image argument must have shape (N*M) or (N*M*3) or (N*M*4)."                   
    
    if axes is None:
        axes = plt.gca()
    #First, we need to generate the coordinates of the vertices.  Start by
    #putting the corner coordinates in a 2x2x2 array
    assert np.array(corners).shape == (4,2), "The 'corners' argument must be four two-element positions, i.e. have shape (4, 2)"
    corner_coordinate_array = np.array(corners).reshape((2,2,2))
    #now, we "zoom" this array using bilinear interpolation (order=1) so that
    #it has the correct dimensions - one greater than the size of the image.
    coordinate_array = ndimage.zoom(corner_coordinate_array,
                                    (old_div((shape[0]+1),2),old_div((shape[1]+1),2),1),
                                    order=1)
    if len(shape)==2: #grayscale image
        mesh = ax.pcolormesh(coordinate_array[:,:,0],
                             coordinate_array[:,:,1],
                             image,
                             *args
                             **kwargs)
    else:
        #Sadly, pcolormesh doesn't seem to do RGB.  The work-around is to first
        #plot a monochrome image, then set the color for each pixel later.
        mesh = ax.pcolormesh(coordinate_array[:,:,0],
                      coordinate_array[:,:,1],
                      image[:,:,0],
                      *args,
                      **kwargs)
        #we need to pass the colors as a flattened array of (R,G,B).  Worse,
        #these need to be floating point values between 0 and 1!
        if image.dtype == np.dtype('uint8'):
            divisor = 255.0
        elif image.dtype == np.dtype('uint16'):
            divisor = 65535.0
        elif image.max() <= 1.0:
            divisor = 1.0
        else:
            divisor = image.max()
            
        mesh.set_color(old_div(image.reshape((shape[0]*shape[1],shape[2])),divisor)) 
        
if __name__ == '__main__':
    image = np.random.random((100,100,3))
    f = plt.figure()
    ax = f.add_subplot(111)
    print("Plotting...")
    plot_skewed_image(image,[(0,0),(-0.5,1),(1,0.5),(0.5,1.5)],ax)
    print("Drawing...")
    f.canvas.draw()
    print("Done")
    plt.show()
    