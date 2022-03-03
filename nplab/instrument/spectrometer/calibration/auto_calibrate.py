# -*- coding: utf-8 -*-
"""
Created on Sat Oct 30 12:10:31 2021

@author: Eoin
"""

from pathlib import Path
import h5py
from scipy.signal import find_peaks
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures
import json
import numpy as np
from scipy.optimize import minimize


def closest(val, seq):
    return min(seq, key=lambda s: abs(val - s))


def fit_model(all_peaks_to_assign, all_assigned_peaks):
    model = make_pipeline(PolynomialFeatures(degree=2), LinearRegression())
    # feel free to change degree, higher orders more accurate, but may be weird outside calibration range
    X, y = [], []
    for step in all_assigned_peaks:
        assigned = all_assigned_peaks[step]
        peaks = all_peaks_to_assign[step]

        for peak, ass in zip(peaks, assigned):
            if ass is not None:
                X.append((float(step), peak))
                y.append([ass])
    # make X = n_samples * n_features, y = n_samples
    # features = step position, pixel number, n_features = 2
    model.fit(X, y)

    _coef = model['linearregression'].coef_.flatten()
    _intercept = model['linearregression'].intercept_
    _powers = model['polynomialfeatures'].powers_

    def simple_predictor(step,
                         pixel,
                         coef=_coef,
                         intercept=_intercept,
                         powers=_powers):
        '''recombine regression coefficients, intercept and powers'''
        return np.sum(coef * (np.product(np.array([step, pixel])**powers,
                                         axis=1))) + intercept[0]

    return simple_predictor


class Calibrator:
    def __init__(self, CCD_size, grating=1):
        self.CCD_size = CCD_size
        self.grating = grating
        self.root = Path(__file__).parent
        # there will be a predictor, middle_step and initial_predictor for each grating
        self.predictors = {}
        self.middle_steps = {}
        self.initial_predictors = {}
        
        lines = list(
            map(float,
                open(self.root / 'spectral lines.txt',
                     'r').read().split('\n')))
        lines = [l / 10 for l in lines]
        cd = h5py.File(self.root / 'wavelength calibration.h5', 'r')
        for name, dset in cd.items():
            grating = int(name.split('_')[-1])
            steps = dset.attrs['steps']
            all_peaks_to_assign = json.load(
                open(self.root / f'all_peaks_to_assign_grating_{grating}.json',
                     'r')) or {}
            all_assigned_peaks = json.load(
                open(self.root / f'all_assigned_peaks_grating_{grating}.json',
                     'r')) or {}
            self.middle_steps[grating] = steps[len(steps) // 2]
            self.initial_predictors[grating] = fit_model(
                all_peaks_to_assign, all_assigned_peaks)
            all_assigned_peaks = {}
            all_peaks_to_assign = {}
            for step, spec in zip(steps, dset):

                peaks = find_peaks(spec, height=500, distance=40)[0].tolist()
                all_peaks_to_assign[str(step)] = peaks
                predicted = [
                    self.initial_predictors[grating](step, p) for p in peaks
                ]
                all_assigned_peaks[str(step)] = [
                    closest(p, lines) for p in predicted
                ]

            self.predictors[grating] = fit_model(all_peaks_to_assign,
                                                 all_assigned_peaks)

    @property
    def predictor(self):
        return self.predictors[self.grating]

    def steps_to_wl(self, step):
        return self.predictor(step, self.CCD_size // 2) # middle of the CCD

    def wavelength_axis(self, step):
        if self.grating not in self.predictors:
            return range(self.CCD_size) # if not calibrated, just give a 0-CCD_size range
        return [self.predictor(step, p) for p in range(self.CCD_size)]

    def wl_to_steps(self, wl):
        def func(step):
            return abs(wl - self.predictor(step[0], self.CCD_size // 2))
        return minimize(func, self.middle_steps[self.grating]).x[0]

class DummyCalibrator:
    def __init__(self, CCD_size, grating=1):
        self.CCD_size = CCD_size
    
    def steps_to_wl(self, step):
        return step

    def wavelength_axis(self, step):
        return range(self.CCD_size)
        
    def wl_to_steps(self, wl):
        return wl

if __name__ == '__main__':
    c = Calibrator(1600)
    steps = np.linspace(4500, 6000)
    plt.figure()
    plt.plot(steps, [c.initial_predictors[1](s, 800) for s in steps],
             label='initial')
    plt.plot(steps, [c.predictor(s, 800) for s in steps], label='final')
    plt.legend()
    c.wl_to_steps(633)
    plt.xlabel('steps')
    plt.ylabel('wavelengths')
