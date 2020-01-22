# -*- coding: utf-8 -*-

from __future__ import division
from builtins import zip
from builtins import range
from past.utils import old_div
import numpy as np
# import pyfftw
from scipy import misc
import matplotlib.pyplot as plt
from matplotlib import gridspec


# TODO: performance quantifiers for IFT algorithms (smoothness, efficiency)
# TODO: compare initial phase methods in IFT algorithms: quadratic phase; starting in the real plane with a flat phase
# TODO: compare CPU and GPU


def constant(input_phase, offset):
    return input_phase + offset


def calibration_responsiveness(input_phase, grey_level, axis=0):
    """Function for calibrating the phase retardation as a function of addressing voltage
    Need to image the reflected beam directly onto a camera, creating fringes. The fringe shift as a function of voltage
    gives the responsiveness. Note it assumes the retardation is the same across the SLM. If this were not the case, see
    https://doi.org/10.1364/AO.43.006400 for how to measure it.

    :param input_phase:
    :param grey_level:
    :param axis:
    :return:
    """
    shape = np.shape(input_phase)
    centers = [int(old_div(x, 2)) for x in shape]
    out_phase = np.zeros(shape)
    if axis == 0:
        out_phase[centers[0]:] = grey_level
    elif axis == 1:
        out_phase[:, centers[1]:] = grey_level
    else:
        raise ValueError('Unrecognised axis: %d' % axis)
    return out_phase


def gratings(input_phase, grating_const_x=0, grating_const_y=0):
    """Linear phase pattern corresponding to a grating/mirror

    :param input_phase:
    :param grating_const_x: float. Period (in pixels) of the grating along the x direction. Default is no grating
    :param grating_const_y: float. Period (in pixels) of the grating along the y direction. Default is no grating
    :return:
    """
    shape = np.shape(input_phase)
    x = np.arange(shape[1]) - int(old_div(shape[1], 2))
    y = np.arange(shape[0]) - int(old_div(shape[0], 2))
    x, y = np.meshgrid(x, y)

    phase = np.zeros(shape)
    if grating_const_x != 0:
        phase += (old_div(np.pi, grating_const_x)) * x
    if grating_const_y != 0:
        phase += (old_div(np.pi, grating_const_y)) * y

    return input_phase + phase


def focus(input_phase, curvature=0):
    """Quadratic phase pattern corresponding to a perfect lens

    :param input_phase:
    :param curvature: float. Inverse focal length of the lens in arbitrary units
    :return:
    """
    shape = np.shape(input_phase)
    x = np.arange(shape[1]) - int(old_div(shape[1], 2))
    y = np.arange(shape[0]) - int(old_div(shape[0], 2))
    x, y = np.meshgrid(x, y)

    phase = curvature * (x ** 2 + y ** 2)

    return input_phase + phase


def astigmatism(input_phase, horizontal=0, diagonal=0):
    """Cylindrical phase pattern corresponding to astigmatism

    :param input_phase:
    :param horizontal: float. curvature between the x and y axis
    :param diagonal: float. curvature between the axes at 45deg and 135deg
    :return:
    """
    shape = np.shape(input_phase)
    x = np.arange(shape[1]) - int(old_div(shape[1], 2))
    y = np.arange(shape[0]) - int(old_div(shape[0], 2))
    x, y = np.meshgrid(x, y)
    rho = np.sqrt(x ** 2 + y ** 2)
    phi = np.arctan2(x, y)

    phase = (horizontal * np.sin(2 * phi) + diagonal * np.cos(2 * phi)) * rho ** 2

    return input_phase + phase


def vortexbeam(input_phase, order, angle, center=None):
    """Vortices

    :param input_phase:
    :param order: int. Vortex order
    :param angle: float. Orientation of the vortex, in degrees
    :param center: two-iterable of integers. Location of the center of the vortex on the SLM panel
    :return:
    """
    shape = np.shape(input_phase)
    if center is None:
        center = [int(old_div(x, 2)) for x in shape]
    x = np.arange(shape[1]) - center[1]
    y = np.arange(shape[0]) - center[0]
    x, y = np.meshgrid(x, y)

    phase = order * (np.angle(x + y * 1j) + np.pi) + angle * np.pi / 180.

    return input_phase + phase


def linear_lut(input_phase, contrast, offset):
    """

    :param input_phase:
    :param contrast:
    :param offset:
    :return:
    """
    out_phase = np.copy(input_phase)
    out_phase -= out_phase.min()
    out_phase %= 2 * np.pi - 0.000001
    out_phase *= contrast
    out_phase += offset * np.pi
    return out_phase


"""Iterative Fourier Transform algorithms"""


def mraf(original_phase, target_intensity, input_field=None, mixing_ratio=0.4, signal_region_size=0.5, iterations=30):
    """Mixed-Region Amplitude Freedom algorithm for continuous patterns https://doi.org/10.1364/OE.16.002176

    :param original_phase:
    :param target_intensity:
    :param input_field:
    :param mixing_ratio:
    :param signal_region_size:
    :param iterations:
    :return:
    """
    shp = target_intensity.shape
    x, y = np.ogrid[old_div(-shp[1], 2):old_div(shp[1], 2), old_div(-shp[0], 2):old_div(shp[0], 2)]
    x, y = np.meshgrid(x, y)

    target_intensity = np.asarray(target_intensity, np.float)
    if input_field is None:
        # By default, the initial phase focuses a uniform SLM illumination onto the signal region
        input_phase = ((old_div(x ** 2, (old_div(shp[1], (signal_region_size * 2 * np.sqrt(2)))))) +
                       (old_div(y ** 2, (old_div(shp[0], (signal_region_size * 2 * np.sqrt(2)))))))
        input_field = np.exp(1j * input_phase)
    # Normalising the input field and target intensity to 1 (doesn't have to be 1, but they have to be equal)
    input_field /= np.sqrt(np.sum(np.abs(input_field)**2))
    target_intensity /= np.sum(target_intensity)

    # This can leave the center of the SLM one or two pixels
    mask = (x**2 + y**2) < (signal_region_size * np.min(shp))**2
    signal_region = np.ones(shp) * mixing_ratio
    signal_region[~mask] = 0
    noise_region = np.ones(shp) * (1 - mixing_ratio)
    noise_region[mask] = 0
    input_intensity = np.abs(input_field)**2

    for _ in range(iterations):
        output_field = np.fft.fft2(input_field)
        # makes sure power out = power in, so that the distribution of power in signal and noise regions makes sense
        output_field = old_div(output_field, np.sqrt(np.prod(shp)))
        output_field = np.fft.fftshift(output_field)
        output_phase = np.angle(output_field)

        mixed_field = signal_region * np.sqrt(target_intensity) * np.exp(1j * output_phase) + noise_region * output_field
        mixed_field = np.fft.ifftshift(mixed_field)

        input_field = np.fft.ifft2(mixed_field)
        input_phase = np.angle(input_field)
        input_field = np.sqrt(input_intensity) * np.exp(1j*input_phase)
        # print(np.sum(np.abs(input_field)**2), np.sum(target_intensity), np.sum(np.abs(output_field)**2))
    return original_phase + input_phase


def gerchberg_saxton(original_phase, target_intensity, input_field=None, iterations=30):
    """Gerchberg Saxton algorithm for continuous patterns

    Easiest version, where you don't need to keep track of FFT factors, normalising intensities, or FFT shifts since it
    all gets discarded anyway.

    :param original_phase:
    :param target_intensity:
    :param input_field:
    :param iterations:
    :return:
    """
    shp = target_intensity.shape
    target_intensity = np.fft.fftshift(target_intensity)  # this matrix is only used in the Fourier plane
    if input_field is None:
        input_field = np.ones(shp) * np.exp(1j * np.zeros(shp))
    input_intensity = np.abs(input_field) ** 2
    for _ in range(iterations):
        output_field = np.fft.fft2(input_field)  # don't have to normalise since the intensities are replaced
        output_phase = np.angle(output_field)
        output_field = np.sqrt(target_intensity) * np.exp(1j * output_phase)

        input_field = np.fft.ifft2(output_field)
        input_phase = np.angle(input_field)
        input_field = np.sqrt(input_intensity) * np.exp(1j * input_phase)
        # print(np.sum(np.abs(input_field)**2), np.sum(target_intensity), np.sum(np.abs(output_field)**2))
    return original_phase + input_phase


def test_ifft_smoothness(alg_func, *args, **kwargs):
    """Evaluates smoothness of calculated vs target pattern as a function of iteration in an IFFT algorithm

    Smoothness is defined as the sum of absolute difference over the area of interest. For most algorithms the area of
    interest is the whole plane, while for MRAF the area of interest is only the signal region

    :param alg_func:
    :param args:
    :param kwargs:
    :return:
    """
    target = np.asarray(misc.face()[:, :, 0], np.float)
    shp = target.shape
    x, y = np.ogrid[old_div(-shp[1], 2):old_div(shp[1], 2), old_div(-shp[0], 2):old_div(shp[0], 2)]
    x, y = np.meshgrid(x, y)
    mask = (x**2 + y**2) > (0.2 * np.min(shp))**2
    target[mask] = 0
    target /= np.sum(target)

    iterations = 60
    if 'iterations' in kwargs:
        iterations = kwargs['iterations']
    # The algorithms only return the final phase, so to evaluate the smoothness at each iteration, need to set the
    # algorithm to only run one step at a time
    kwargs['iterations'] = 1

    # Defining a mask and a mixing_ratio for calculating the smoothness later
    if alg_func == gerchberg_saxton:
        mask = np.ones(shp, dtype=np.bool)
        mixing_ratio = 1
    elif alg_func == mraf:
        x, y = np.ogrid[old_div(-shp[1], 2):old_div(shp[1], 2), old_div(-shp[0], 2):old_div(shp[0], 2)]
        x, y = np.meshgrid(x, y)
        signal_region_size = 0.5
        if 'signal_region_size' in kwargs:
            signal_region_size = kwargs['signal_region_size']
        mask = (x**2 + y**2) < (signal_region_size * np.min(shp))**2
        mixing_ratio = 0.4
        if 'mixing_ratio' in kwargs:
            mixing_ratio = kwargs['mixing_ratio']
    else:
        raise ValueError('Unrecognised algorithm')

    smth = []
    outputs = []
    for indx in range(iterations):
        init_phase = alg_func(0, target, *args, **kwargs)
        input_field = np.exp(1j * init_phase)
        kwargs['input_field'] = input_field
        output = old_div(np.fft.fftshift(np.fft.fft2(np.exp(1j * init_phase))), (np.prod(shp)))
        output_int = np.abs(output) ** 2
        # print(np.sum(np.abs(output_int)), np.sum(np.abs(output_int)[mask]))
        smth += [old_div(np.sum(np.abs(output_int - mixing_ratio*target)[mask]), np.sum(mask))]
        outputs += [output]

    fig = plt.figure(figsize=(old_div(8*shp[1],shp[0])*2, 8))
    gs = gridspec.GridSpec(1, 2)
    gs2 = gridspec.GridSpecFromSubplotSpec(5, 6, gs[0], 0.001, 0.001)
    reindex = np.linspace(0, iterations-1, 30)
    ax = None
    for indx, _gs in zip(reindex, gs2):
        indx = int(indx)
        ax = plt.subplot(_gs, sharex=ax, sharey=ax)
        ax.imshow(np.abs(outputs[indx]))
        ax.text(shp[1]/2., 0, '%d=%.3g' % (indx, smth[indx]), ha='center', va='top', color='w')
        ax.set_xticklabels([])
        ax.set_yticklabels([])
    ax2 = plt.subplot(gs[1])
    ax2.semilogy(smth)
    return np.array(smth)


def test_ifft_basic(alg_func, *args, **kwargs):
    """Basic testing for IFFT algorithms to see if the final phase truly reproduces an initial target

    Creates an image target (the center of the scipy.misc.face() image), runs the alg_func on it, and plots the results
    for comparison by eye

    :param alg_func:
    :param args:
    :param kwargs:
    :return:
    """
    target = np.asarray(misc.face()[:, :, 0], np.float)
    shp = target.shape
    x, y = np.ogrid[old_div(-shp[1], 2):old_div(shp[1], 2), old_div(-shp[0], 2):old_div(shp[0], 2)]
    x, y = np.meshgrid(x, y)
    mask = (x**2 + y**2) > (0.2 * np.min(shp))**2
    target[mask] = 0
    target /= np.sum(target)  # the target intensity is normalised to 1

    init_phase = np.zeros(target.shape)
    phase = alg_func(init_phase, target, *args, **kwargs)
    output = old_div(np.fft.fftshift(np.fft.fft2(np.exp(1j * phase))), (np.prod(shp)))

    fig, axs = plt.subplots(2, 2, sharey=True, sharex=True, gridspec_kw=dict(wspace=0.01))
    vmin, vmax = (np.min(target), np.max(target))
    axs[0, 0].imshow(target, vmin=vmin, vmax=vmax)
    axs[0, 0].set_title('Target')
    axs[1, 0].imshow(phase)
    axs[1, 0].set_title('Input Phase')
    axs[0, 1].imshow(np.abs(output)**2, vmin=vmin, vmax=vmax)
    axs[0, 1].set_title('Output')
    axs[1, 1].imshow(np.angle(output))
    axs[1, 1].set_title('Output Phase')
    plt.show()


if __name__ == "__main__":
    test_ifft_basic(gerchberg_saxton)
