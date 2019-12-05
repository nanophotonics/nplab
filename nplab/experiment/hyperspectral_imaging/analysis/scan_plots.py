from __future__ import division
from __future__ import absolute_import
from past.utils import old_div
__author__ = 'alansanders'

import matplotlib as mpl
from matplotlib.patches import Rectangle
from mpl_toolkits.axes_grid1 import ImageGrid

from nputils.figure_setup import setup_figure
from nputils.plot_functions import make_dummy_subplot
from nputils.spectra_plotting import *
from .hyperspectral_plots import *


def plot_wavelength_images(hsimg, axslice, roi, fig, ax, subplot_spec, amp=5):
    wavelengths = [500,600,700,800,900]
    n_axes = len(wavelengths) + 1  # add 1 axis for colour reconstruction

    #gs1 = gridspec.GridSpecFromSubplotSpec(int(np.ceil(n_axes/3)), 3, subplot_spec,
    #                                       hspace=0.05, wspace=0.05)
    grid = ImageGrid(fig, subplot_spec, # similar to subplot(111)
                nrows_ncols = (int(np.ceil(old_div(n_axes,3))), 3), # creates 2x3 grid of axes
                axes_pad=0.05, # pad between axes in inch.
                )

    ax = make_dummy_subplot(ax)
    ax.set_ylabel('$y$ (nm)', labelpad=23)
    ax.set_xlabel('$x$ (nm)', labelpad=15)

    for i,wl in enumerate(wavelengths):
        ax = grid[i]  #fig.add_subplot(gs1[i])
        if i>2: xlabels=True
        else: xlabels = False
        if i%3==0: ylabels = True
        else: ylabels = False
        plot_wavelength(hsimg, ax, wl, axslice=axslice, xlabels=xlabels, ylabels=ylabels,
                        wlnorm=False, threshold=0.5, smoothing=(0, 1),
                        img_kwargs={'cmap': mpl.cm.afmhot, 'vmin': 0.0})
        ax.set_xlabel('')
        ax.set_ylabel('')
        #if i==3:
        #    ax.set_xlabel('')
        #    ax.set_ylabel('')
        #if i==0:
        #    ax.set_ylabel('')
    ax = fig.add_subplot(grid[i+1])
    img = plot_colour(hsimg, ax, amp=amp, axslice=axslice, smoothing=(0,1,0), norm=True, ylabels=False)
    ax.set_xlabel('')
    ax.add_patch(Rectangle((1e9*roi[0],1e9*roi[2]), 1e9*(roi[1]-roi[0]), 1e9*(roi[3]-roi[2]), ec='w', fc='w', alpha=0.1, linewidth=1.5))


def plot_scan(hsimg, axslice, roi, amp=5):
    axial_wavelength, axial_spectrum = hsimg.integrate_spectra(xlims=(roi[0],roi[1]), ylims=(roi[2],roi[3]), axslice=axslice)
    transverse_wavelength, transverse_spectrum = hsimg.integrate_spectra(xlims=(roi[0],roi[1]), ylims=(roi[2],roi[3]), axslice=axslice, polarisation=2)

    wavelengths = [500,600,700,800,900]
    n_axes = len(wavelengths) + 1  # add 1 axis for colour reconstruction
    aspect = 0.75 + 0.6

    fig = setup_figure(width='column', aspect=aspect, tex=False)
    gs0 = gridspec.GridSpec(2, 1, height_ratios=[0.75,0.6], hspace=0.34)
    gs1 = gridspec.GridSpecFromSubplotSpec(int(np.ceil(old_div(n_axes,3))), 3, gs0[0], hspace=0.05, wspace=0.05)

    # make dummy axes from gridspec gs0[0]
    ax = fig.add_subplot(gs0[0])
    ax = make_dummy_subplot(ax)
    ax.set_ylabel('$y$ (nm)', labelpad=23)
    ax.text(-0.12,1.05,'(a)', ha='right', va='top', transform=ax.transAxes)

    for i,wl in enumerate(wavelengths):
        ax = fig.add_subplot(gs1[i])
        if i>2: xlabels=True
        else: xlabels = False
        if i%3==0: ylabels = True
        else: ylabels = False
        plot_wavelength(hsimg, ax, wl, axslice=axslice, xlabels=xlabels, ylabels=ylabels,
                        wlnorm=False, threshold=0.5, smoothing=(0,1),
                        img_kwargs={'cmap':mpl.cm.afmhot, 'vmin':0.0})
        if i==3:
            ax.set_xlabel('')
            ax.set_ylabel('')
        if i==0:
            ax.set_ylabel('')
    ax = fig.add_subplot(gs1[i+1])
    img = plot_colour(hsimg, ax, amp=amp, axslice=axslice, smoothing=(0,1,0), norm=True, ylabels=False)
    ax.set_xlabel('')
    #img = plot_colour_map(hsimg, ax, axslice=5, img_kwargs={'cmap':mpl.cm.spectral})
    #plt.setp(ax.get_yticklabels(), visible=False)
    ax.add_patch(Rectangle((1e9*roi[0],1e9*roi[2]), 1e9*(roi[1]-roi[0]), 1e9*(roi[3]-roi[2]), ec='w', fc='w', alpha=0.1, linewidth=1.5))

    ax = fig.add_subplot(gs0[1])
    ax.text(-0.12,1.05,'(b)', ha='right', va='top', transform=ax.transAxes)

    plot_spectrum(axial_wavelength, axial_spectrum, color='r', label='axial')
    plot_spectrum(transverse_wavelength, transverse_spectrum, color='b', label='transverse')
    format_spectrum(ax)
    ax.set_ylabel('optical\nresponse (a.u.)')
    ax.legend(loc='best', fontsize='small')
    ax.set_ylim(ymin=0.)
    ax.set_xlim(450,1150)
    ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(0.1))
    ax.yaxis.set_minor_locator(mpl.ticker.AutoMinorLocator(4))

    #gs.tight_layout(fig, w_pad=0.2, h_pad=0.2)
    #plt.tight_layout()
    return fig