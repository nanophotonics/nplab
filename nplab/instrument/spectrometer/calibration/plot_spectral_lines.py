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
import pandas as pd

plt.ion()


def closest(val, seq):
    return min(seq, key=lambda s: abs(val - s))


lines = list(map(float, open('spectral lines.txt', 'r').read().split('\n')))
lines = [l / 10 for l in lines[:-450]]

df = pd.read_csv(open('Ne IR lines.csv', 'r'))

plt.figure(figsize=(6, 3))

for intensity, line in zip(df['intensity'], df['angstrom']):
    line = line / 10
    intensity = float(intensity)
    if (690 < line < 900):
        plt.plot(line, intensity, 'o')
        plt.annotate(round(line), (line, intensity))
