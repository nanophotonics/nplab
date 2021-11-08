# -*- coding: utf-8 -*-
"""
Created on Sat Oct 30 12:10:31 2021

@author: Eoin
"""

from pathlib import Path
import h5py
from scipy.signal import find_peaks
from scipy.stats import linregress
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures
import json
from collections import defaultdict

plt.ion()


def closest(val, seq):
    '''return the closes value in a sequence to val'''
    return min(seq, key=lambda s: abs(val - s))


lines = list(map(float, open('spectral lines.txt', 'r').read().split('\n')))
lines = [l / 10 for l in lines] # angstrom to wl

cd = h5py.File('wavelength calibration.h5') # calibration data
for name, dset in cd.items():
    grating = int(name.split('_')[-1]) # 'wavelength_calibration_1' for example
    steps = dset.attrs['steps'] # spectrometer motor steps
    for filename in (f'all_peaks_to_assign_grating_{grating}.json',
                     f'all_assigned_peaks_grating_{grating}.json'):
        if not (file := (Path() / filename)).is_file():
            json.dump(
                dict(),
                open(file, 'w'),
            )
        # if the json file don't exist, make them
    all_peaks_to_assign = json.load(
        open(f'all_peaks_to_assign_grating_{grating}.json', 'r')) or {}
    all_assigned_peaks = json.load(
        open(f'all_assigned_peaks_grating_{grating}.json', 'r')) or {}
    # open any existing assignment so you don't start from scratch in case of a mistake
    for i, (step, spec) in enumerate(zip(map(str, steps), dset)):
        if ((not (i % 25)) and (step not in all_assigned_peaks)):
            # every 25th spectrum - feel free to change
            spec = spec[::-1] # for the andor, CCD is reversed
            peaks = find_peaks(spec, height=500, distance=40)[0].tolist()
            # feel free to play with these parameters
            all_peaks_to_assign[step] = peaks
            assigned = []
            while len(assigned) < len(peaks):
                plt.figure(figsize=(6, 3))
                plt.title(step)

                peaks = find_peaks(spec, height=500, distance=40)[0]
                for peak in peaks:
                    plt.axvline(peak, color='k', linestyle='--')
                for peak in peaks[:len(assigned)]:
                    plt.axvline(peak, color='r', linestyle='--')
                plt.axvline(peaks[len(assigned)], color='b', linestyle='--')
                plt.plot(spec, color='tab:green')
                plt.pause(0.1)
                c = input('next peak (nm): ').strip()
                if c == '?':
                    assigned.append(None)
                else:
                    assigned.append(closest(float(c), lines)) # assing the closest spectral line
            all_assigned_peaks[step] = assigned
            json.dump(all_peaks_to_assign,
                      open(f'all_peaks_to_assign_grating_{grating}.json', 'w'))
            json.dump(all_assigned_peaks,
                      open(f'all_assigned_peaks_grating_{grating}.json', 'w'))
