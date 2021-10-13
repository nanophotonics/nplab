# -*- coding: utf-8 -*-
"""
Created on Tue Oct 12 14:21:21 2021

@author: Eoin
"""

import spectroscopy_conversions as cnv
from constants import c


def nm_to_hz(nm, laser):
    return (c / (laser * 1e-9) - c / (nm * 1e-9))


def hz_to_nm(hz, laser):
    return 1e9 / (1 / (laser * 1e-9) - hz / c)


raman_conversions = {
    'to_hz': {
        'nm': nm_to_hz,
        'ev': cnv.ev_to_hz,
        'cm': cnv.cm_to_hz,
        'thz': cnv.thz_to_hz,
        'hz': lambda x: x
    },
    'hz_to': {
        'nm': hz_to_nm,
        'ev': cnv.hz_to_ev,
        'cm': cnv.hz_to_cm,
        'thz': cnv.hz_to_thz,
        'hz': lambda x: x
    },
}

if __name__ == '__main__':
    laser = 633
    print(hz_to_nm(cnv.cm_to_hz(500), laser))
