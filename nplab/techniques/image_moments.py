from __future__ import division
from __future__ import print_function
from past.utils import old_div
__author__ = 'alansanders'

import numpy as np
from scipy.optimize import curve_fit


def find_centroid(img, x=None, y=None, threshold=None):
    """
    Find the centroid of an image using image moments.

    Note that x and y in this case are defined as img[y][x], where x

    :param img: 2d numpy array of the image
    :param x: 1d numpy array corresponding to the rows of the image
    :param y: 1d numpy array corresponding to the columns of the image
    :param threshold: bottom fraction of the background-subtracted image to remove
                      before calculating image moments
    :return: Returns the x and y centroids

    :rtype : float, float
    """
    img = img.copy()  # img is copied since it is later modified
    # get x and y or create if necessary (pixel coordinates)
    if x is None:
        x = np.arange(img.shape[-1])
    elif y is None:
        y = np.arange(img.shape[-2])
    if img.shape != (y.size, x.size):
        raise ValueError('Shape of img(y,x) does not match (x,y)')
    # remove background - the maximum value of the outer array elements and threshold to 0
    bkgd = np.concatenate((img[0, :],  # bottom
                           img[-1, :],  # top
                           img[:, 0].flatten(),  # left
                           img[:, -1].flatten())  # right
                          ).max()
    img *= (img - bkgd >= 0)
    # apply threshold
    if threshold is not None:
        threshold = threshold*img.max() + (1 - threshold)*img.min()  # n(x-y)+y = nx +y(1-n)
        img *= (img >= threshold)
    # calculate moments
    m10 = np.sum(y.reshape(img.shape[0], 1) * img)
    m01 = np.sum(x.reshape(1, img.shape[1]) * img)
    m00 = np.sum(img)
    centroid_x = old_div(m01, m00)
    centroid_y = old_div(m10, m00)
    return centroid_x, centroid_y


gaussian = lambda x, bkgd, A, x0, sigma: bkgd + A * np.exp(old_div(-(x - x0) ** 2, sigma ** 2))


def measure_fwhm(img, x=None, y=None, return_curve=False):
    if x is None:
        x = np.arange(img.shape[-1])
    if y is None:
        y = np.arange(img.shape[-2])
    # create initial guess parameters for gaussian fit
    cx, cy = find_centroid(img, x, y)
    xdata = np.sum(img, axis=0)
    ydata = np.sum(img, axis=1)
    p0_x = [xdata.min(), xdata.max() - xdata.min(), cx, old_div((x.max() - x.min()), 2)]
    p0_y = [ydata.min(), ydata.max() - ydata.min(), cy, old_div((y.max() - y.min()), 2)]
    popt_x, pcov_x = curve_fit(gaussian, x, xdata, p0_x)
    popt_y, pcov_y = curve_fit(gaussian, y, ydata, p0_y)
    fwhm_x = 2 * np.sqrt(2 * np.log(2)) * popt_x[3]
    fwhm_y = 2 * np.sqrt(2 * np.log(2)) * popt_y[3]
    if return_curve:
        return fwhm_x, fwhm_y, xdata, ydata, popt_x, popt_y
    else:
        return fwhm_x, fwhm_y


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    x = np.linspace(-1, 2, 200)
    y = np.linspace(-1, 1, 100)
    xx, yy = np.meshgrid(x, y)
    img = gaussian(xx,0,1,0,1) * gaussian(yy,0,1,0,0.5)
    plt.pcolormesh(x,y,img)

    cx, cy = find_centroid(img, x, y)
    print(cy, cy)
    plt.plot([cx], [cy], 'wo')

    plt.show()