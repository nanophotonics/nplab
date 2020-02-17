# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from past.utils import old_div
__author__ = 'alansanders'

import numpy as np


def software_lockin(t, signal, reference, harmonic=1, trigger=None, smoothing=None, basis='cartesian'):
    """
    Extract the amplitude and phase of a signal component at a frequency set by a reference
    signal.

    :param t: a numpy array of time values
    :param signal: a numpy
    :param reference:
    :param harmonic:
    :param trigger:
    :param smoothing:
    :param basis: cartesian (x,y) or polar (r,theta) return
    :return: Depending on the basis, either a cartesian (real, imaginary) pair of values is
             returned or a polar amplitude and angle (phase) pair of values.

    :rtype : object
    """
    assert len(signal) == len(t) and len(reference) == len(t), 'all arrays must be the same length.'
    if type(t) != np.ndarray:
        t = np.array(t)  # casting t to numpy array for boolean slicing
    # find the zero crossings of the reference signal to determine its frequency and phase.
    # a rising edge is used only
    cond1 = reference[:-1] < np.mean(reference)
    cond2 = reference[1:] >= np.mean(reference)
    zero_crossings = t[cond1 & cond2]  # these are the points in time that are zero
    # fit a line to the zero crossing
    n = np.arange(zero_crossings.size)  # number of rising triggers
    p = np.polyfit(n, zero_crossings, 1)  # result is p[0]*t + p[1]
    # extract the frequency and phase of the reference wave
    omega_r = old_div(2*np.pi,p[0])
    phi_r = -omega_r*p[1]  # if the phase is not between 0 and 2pi its ok since its put into an exp
    ref = np.exp(-1j*harmonic*(omega_r*t + phi_r))  # construct the reference waveform
    cmplx = 2j*np.mean(signal*ref)  # multiply signal with reference
    x = cmplx.real
    y = cmplx.imag
    if basis == 'cartesian':
        return x, y
    elif basis == 'polar':
        return cart2pol(x, y)


def cart2pol(x, y):
    """
    Converts (x,y) cartesian coordinates to (r,theta) polar coordinates.

    :param x:
    :param y:
    :return:
    """
    return np.sqrt(x**2 + y**2), np.angle(x + 1j*y)


if __name__ == '__main__':
    import matplotlib.pyplot as plt

    t = np.linspace(0, 1, 1000)
    phi = old_div(np.pi,2)
    ref = np.sin(2*np.pi*10*t + phi)
    signal = np.sin(2*np.pi*10*t + phi + old_div(np.pi,2))

    x, y = software_lockin(t, signal, ref, harmonic=1)
    r, theta = cart2pol(x, y)
    print(r, old_div(theta,np.pi))

    plt.show()
