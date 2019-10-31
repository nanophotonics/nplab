# -*- coding: utf-8 -*-

import numpy as np
# import pyfftw


# TODO: performance quantifiers for IFT algorithms (smoothness, efficiency)
# TODO: compare initial phase methods in IFT algorithms: quadratic phase; starting in the real plane with a flat phase
# TODO: compare CPU and GPU


def constant(input_phase, offset):
    return input_phase + offset


def gratings(input_phase, grating_const_x=0, grating_const_y=0):
    """Linear phase pattern corresponding to a grating/mirror

    :param input_phase:
    :param grating_const_x: float. Period (in pixels) of the grating along the x direction. Default is no grating
    :param grating_const_y: float. Period (in pixels) of the grating along the y direction. Default is no grating
    :return:
    """
    shape = np.shape(input_phase)
    x = np.arange(shape[1]) - int(shape[1] / 2)
    y = np.arange(shape[0]) - int(shape[0] / 2)
    x, y = np.meshgrid(x, y)

    phase = np.zeros(shape)
    if grating_const_x != 0:
        phase += (np.pi / grating_const_x) * x
    if grating_const_y != 0:
        phase += (np.pi / grating_const_y) * y

    return input_phase + phase


def focus(input_phase, curvature=0):
    """Quadratic phase pattern corresponding to a perfect lens

    :param input_phase:
    :param curvature: float. Inverse focal length of the lens in arbitrary units
    :return:
    """
    shape = np.shape(input_phase)
    x = np.arange(shape[1]) - int(shape[1] / 2)
    y = np.arange(shape[0]) - int(shape[0] / 2)
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
    x = np.arange(shape[1]) - int(shape[1] / 2)
    y = np.arange(shape[0]) - int(shape[0] / 2)
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
        center = [int(x / 2) for x in shape]
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


def mraf(input_phase, target_intensity, input_field=None, mixing_ratio=0.4, signal_region_size=0.5, iterations=30):
    """Mixed-Region Amplitude Freedom algorithm for continuous patterns https://doi.org/10.1364/OE.16.002176

    :param input_phase:
    :param target_intensity:
    :param input_field:
    :param mixing_ratio:
    :param signal_region_size:
    :param iterations:
    :return:
    """
    shp = input_phase.shape
    target_intensity = np.asarray(target_intensity, np.float)
    if input_field is None:
        input_field = np.ones(shp) + 1j * np.zeros(shp)
    # Normalising the input field and target intensity to 1 (doesn't have to be 1, but they have to be equal)
    input_field /= np.sqrt(np.sum(np.abs(input_field)**2))
    target_intensity /= np.sum(target_intensity)

    # This can leave the center of the SLM one or two pixels
    x, y = np.ogrid[-shp[1] / 2:shp[1] / 2, -shp[0] / 2:shp[0] / 2]
    x, y = np.meshgrid(x, y)
    mask = (x**2 + y**2) < (signal_region_size * np.min(shp))**2
    signal_region = np.ones(shp) * mixing_ratio
    signal_region[~mask] = 0
    noise_region = np.ones(shp) * (1 - mixing_ratio)
    noise_region[mask] = 0
    input_intensity = np.abs(input_field)**2

    for _ in range(iterations):
        output_field = np.fft.fft2(input_field)
        # makes sure power out = power in, so that the distribution of power in signal and noise regions makes sense
        output_field = output_field / np.sqrt(np.prod(shp))
        output_field = np.fft.fftshift(output_field)
        output_phase = np.angle(output_field)

        mixed_field = signal_region * np.sqrt(target_intensity) * np.exp(1j * output_phase) + noise_region * output_field
        mixed_field = np.fft.ifftshift(mixed_field)

        input_field = np.fft.ifft2(mixed_field)
        input_phase = np.angle(input_field)
        input_field = np.sqrt(input_intensity) * np.exp(1j*input_phase)

    return input_phase


def gerchberg_saxton(input_phase, target_intensity, iterations=30):
    """Gerchberg Saxton algorithm for continuous patterns

    Easiest version, where you don't need to keep track of FFT factors, normalising intensities, or FFT shifts since it
    all gets discarded anyway.

    :param input_phase:
    :param target_intensity:
    :param iterations:
    :return:
    """
    kinoform = np.copy(input_phase)

    shp = target_intensity.shape
    input_intensity = np.ones(shp)
    target_intensity = np.fft.fftshift(target_intensity)  # this matrix is only used in the Fourier plane

    input_field = input_intensity * np.exp(1j * np.ones(shp))
    for iter in range(iterations):
        output_field = np.fft.fft2(input_field)
        output_phase = np.angle(output_field)
        output_field = target_intensity * np.exp(1j * output_phase)

        input_field = np.fft.ifft2(output_field)
        input_phase = np.angle(input_field)
        input_field = input_intensity * np.exp(1j * input_phase)

    return kinoform + input_phase


def test_ifft_alg(alg_func, *args, **kwargs):
    target = np.copy(misc.face()[:, :, 0])
    shp = target.shape
    x, y = np.ogrid[-shp[1] / 2:shp[1] / 2, -shp[0] / 2:shp[0] / 2]
    x, y = np.meshgrid(x, y)
    mask = (x**2 + y**2) > (0.2 * np.min(shp))**2
    target[mask] = 0
    init_phase = np.zeros(target.shape)
    phase = alg_func(init_phase, target, *args, **kwargs)

    fig, axs = plt.subplots(2, 2, sharey=True, sharex=True)
    axs[0, 0].imshow(target)
    axs[1, 0].imshow(phase)
    axs[0, 1].imshow(np.abs(np.fft.fftshift(np.fft.fft2(np.exp(1j * phase)))))
    axs[1, 1].imshow(np.angle(np.fft.fftshift(np.fft.fft2(np.exp(1j * phase)))))
    plt.show()


if __name__ == "__main__":
    from scipy import misc
    import matplotlib.pyplot as plt
    test_ifft_alg(gerchberg_saxton)

    # test_ifft_alg(mraf, mixing_ratio=0.4, signal_region_size=0.5, iterations=30)
