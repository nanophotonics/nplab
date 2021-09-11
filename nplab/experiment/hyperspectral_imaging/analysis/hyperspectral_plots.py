from __future__ import division
from builtins import str
from builtins import range
from past.utils import old_div
__author__ = 'alansanders'

import numpy as np
from scipy.ndimage.filters import gaussian_filter
import matplotlib.pyplot as plt
# required for formatting image axes
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
from matplotlib.ticker import AutoMinorLocator, MaxNLocator
from matplotlib.ticker import NullLocator, NullFormatter
from matplotlib import cm, gridspec
from nputils.plotting.plot_functions import scale_axes
from nputils.plotting import np_cmap

locs = {'upper right' : (0.95,0.95),
        'upper left'  : (0.05,0.95),
        'lower left'  : (0.05,0.05),
        'lower right' : (0.95,0.15)}


def _plot_image(x, y, z, ax, **kwargs):
    img_kwargs = {'vmin': z.min(), 'vmax': z.max(), 'cmap': cm.afmhot,
                  'rasterized': True, 'shading': 'gouraud'}
    for k in kwargs:
        img_kwargs[k] = kwargs[k]
    x, y = np.meshgrid(x, y, indexing='ij')
    img = ax.pcolormesh(x, y, z, **img_kwargs)
    ax.set_xlim(x.min(), x.max())
    ax.set_ylim(y.min(), y.max())
    return img


def _format_image_plot(ax, xlabel=None, ylabel=None, invert=False):
    ax.minorticks_on()
    ax.set_aspect('equal')
    ax.tick_params(axis='both', which='major', labelsize='small')
    for axis in [ax.xaxis, ax.yaxis]:
        axis.set_major_locator(MaxNLocator(5))
        axis.set_minor_locator(AutoMinorLocator(4))
        axis.set_major_formatter(FormatStrFormatter('%d'))
    if invert:
        [i.set_color('white') for i in ax.xaxis.get_ticklines()]
        [i.set_color('white') for i in ax.yaxis.get_ticklines()]
        [ax.spines[s].set_color('white') for s in ax.spines]
    if xlabel is not None:
        ax.set_xlabel(xlabel)
    else:
        plt.setp(ax.get_xticklabels(), visible=False)
    if ylabel is not None:
        ax.set_ylabel(ylabel)
    else:
        plt.setp(ax.get_yticklabels(), visible=False)


def plot_wavelength(hs_image, ax, wl, polarisation=1, wlnorm=True, rescale_axes=False,
                    smoothing=None, contour_lines=None, mult=1.,
                    loc='upper right', xlabels=True, ylabels=True, threshold=None,
                    img_kwargs={}, contour_kwargs={'colors':'k'}, **kwargs):
    """Plots the hyperspectral image at the selected wavelength on a given axis."""

    image = hs_image.get_image(wl, polarisation, **kwargs)
    if wlnorm:
        minimum, maximum = (image.min(), image.max())
    else:
        wavelength, spectra = hs_image.get_spectra(polarisation)
        minimum, maximum = (spectra.min(), spectra.max())
    if threshold is not None:
        maximum = threshold*maximum + (1-threshold)*minimum

    x, unit = scale_axes(hs_image.x)
    y, unit = scale_axes(hs_image.y)
    if rescale_axes:
        x -= x.mean()
        y -= y.mean()
    image *= mult
    if smoothing is not None:
        image = gaussian_filter(image, smoothing)
    img = _plot_image(x, y, image, ax, **img_kwargs)
    if contour_lines is not None:
        ax.contour(x, y, image, contour_lines, **contour_kwargs)
    if xlabels: xlabel = '$x$ (%s)'%unit
    else: xlabel = None
    if ylabels: ylabel = '$y$ (%s)'%unit
    else: ylabel = None
    _format_image_plot(ax, xlabel=xlabel, ylabel=ylabel)
    tx, ty = locs[loc]
    ax.text(tx, ty, str(wl)+' nm', va='top', ha='right',
            transform=ax.transAxes, color='white', fontsize='small', fontweight='bold')
    return img


def plot_colour_map(hs_image, ax, polarisation=1, norm=True,
                    smoothing=None,
                    loc='upper right', xlabels=True, ylabels=True,
                    img_kwargs={}, **kwargs):
    """Plots the hyperspectral image at the selected wavelength on a given axis."""

    image = hs_image.construct_colour_map(polarisation, norm, **kwargs)
    x, unit = scale_axes(hs_image.x)
    y, unit = scale_axes(hs_image.y)
    if smoothing is not None:
        image = gaussian_filter(image, smoothing)
    img = _plot_image(x, y, image, ax, **img_kwargs)
    if xlabels: xlabel = '$x$ (%s)'%unit
    else: xlabel = None
    if ylabels: ylabel = '$y$ (%s)'%unit
    else: ylabel = None
    _format_image_plot(ax, xlabel=xlabel, ylabel=ylabel)
    #tx, ty = locs[loc]
    #ax.text(tx, ty, 'false colour', va='top', ha='right',
    #        transform=ax.transAxes, color='white', fontsize='small')
    return img


def plot_colour(hs_image, ax, amp=1, smoothing=None, loc='upper right',
                xlabels=True, ylabels=True,
                **kwargs):
    ax.set_axis_bgcolor('black')
    image = hs_image.reconstruct_colour_image(**kwargs)
    if smoothing is not None:
        image = gaussian_filter(image, smoothing)
    image[:,:,3] = amp*image[:,:,3]
    image[:,:,3] = np.where(image[:,:,3] > 1, 1, image[:,:,3])
    x, unit = scale_axes(hs_image.x)
    y, unit = scale_axes(hs_image.y)
    limits = np.array([x.min(), x.max(),
                       y.min(), y.max()])
    ax.imshow(image, origin='lower', extent=limits)
    ax.set_xlim(limits[0], limits[1])
    ax.set_ylim(limits[2], limits[3])
    if xlabels: xlabel = '$x$ (%s)'%unit
    else: xlabel = None
    if ylabels: ylabel = '$y$ (%s)'%unit
    else: ylabel = None
    _format_image_plot(ax, xlabel=xlabel, ylabel=ylabel)
    tx, ty = locs[loc]
    ax.text(tx, ty, 'colour', va='top', ha='right',
            transform=ax.transAxes, color='white', fontsize='small')
    return image


def plot_line_scan(hs_image, ax, axis, line, imnorm=False, linenorm=False, dat='', smooth=None):
    if dat=='':
        spectra = hs_image.spectra
        wavelength = hs_image.wavelength
    elif dat=='trans':
        data = hs_image.data_t
        wavelength = hs_image.wavelength_t
    line_spectra = hs_image.get_line_spectra(axis, line, dat)

    if smooth != None: line_spectra = gaussian_filter(line_spectra, smooth)

    if linenorm == True:
        for i in range(line_spectra.shape[0]):
            line_spectra[i] = old_div(line_spectra[i], line_spectra[i].max())

    if imnorm == True:
        minimum = line_spectra.min()
        maximum = line_spectra.max()
    else:
        minimum = data.min() * (data.min()>=0.0)
        maximum = data.max() * (data.max()>=0.0)

    #lev_exp = np.linspace(np.log10(minimum), np.log10(maximum), 200)
    #levs = np.power(10, lev_exp)
    #norm = LogNorm(minimum, maximum)
    levs = np.linspace(minimum, maximum, 200)
    norm = cm.colors.Normalize(vmax=maximum, vmin=minimum)

    X, Y = np.meshgrid(hs_image.x, wavelength, indexing='ij')
    ax.contourf(X, Y, line_spectra, levs, norm=norm, cmap=cm.CMRmap)

    if axis=='x': label = 'y={0:.2f} nm'.format(hs_image.x[line])
    if axis=='y': label = 'x={0:.2f} nm'.format(hs_image.y[line])
    ax.text(0.95, 0.95, label, va='top', ha='right',
            transform=ax.transAxes, color='white', fontsize='small')
    ax.tick_params(axis='both', which='major', labelsize='small')
    ax.set_xlim(hs_image.x.min(), hs_image.x.max())
    ax.set_ylim(wavelength.min(), wavelength.max())
    _format_image_plot(ax)
    return line_spectra