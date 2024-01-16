# -*- coding: utf-8 -*-
"""
Created on Tue Oct 12 14:21:21 2021

@author: Eoin
"""

from nplab.unit_conversions.constants import c, e, h, pi


def ev_to_joules(ev, *args, **kwargs):
    return e * ev


def joules_to_ev(joules, *args, **kwargs):
    return joules / e


def joules_to_hz(joules, *args, **kwargs):
    return joules / h


def hz_to_joules(hz, *args, **kwargs):
    return hz * h


def ev_to_hz(ev, *args, **kwargs):
    return joules_to_hz(ev_to_joules(ev))


def hz_to_ev(hz, *args, **kwargs):
    return joules_to_ev(hz_to_joules(hz))


def nm_to_hz(nm, *args, **kwargs):
    return c / (nm * 1e-9)


def hz_to_nm(hz, *args, **kwargs):
    return 1e9 / (hz / c)


def cm_to_hz(cm, *args, **kwargs):
    return cm * c * 100


def hz_to_cm(hz, *args, **kwargs):
    return 0.01 * hz / c


def thz_to_hz(thz, *args, **kwargs):
    return thz * 1e12


def hz_to_thz(hz, *args, **kwargs):
    return hz * 1e-12


def hz_to_rads(hz, *args, **kargs):
    return 2 * pi * hz


def rads_to_hz(rads, *args, **kargs):
    return rads / (2 * pi)


spectroscopy_conversions = {
    "to_hz": {
        "nm": nm_to_hz,
        "ev": ev_to_hz,
        "cm": cm_to_hz,
        "thz": thz_to_hz,
        'rads': rads_to_hz,
        "hz": lambda x: x,  # returns itself
    },
    "hz_to": {
        "nm": hz_to_nm,
        "ev": hz_to_ev,
        "cm": hz_to_cm,
        "thz": hz_to_thz,
        'rads': hz_to_rads,
        "hz": lambda x: x,
    },
}

if __name__ == "__main__":
    laser = 633
    print(hz_to_nm(cm_to_hz(500)))
