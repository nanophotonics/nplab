# -*- coding: utf-8 -*-

import numpy as np


def gratings(input_phase, grating_const_x=0, grating_const_y=0):
    """Linear phase pattern corresponding to a grating/mirror

    :param input_phase:
    :param grating_const_x: int. Period (in pixels) of the grating along the x direction. Default is no grating
    :param grating_const_y: int. Period (in pixels) of the grating along the y direction. Default is no grating
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
