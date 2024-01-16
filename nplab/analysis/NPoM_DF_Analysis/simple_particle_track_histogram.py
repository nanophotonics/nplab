import matplotlib.pyplot as plt
import numpy as np

from scipy.signal import argrelextrema

from nplab.analysis import Spectrum, latest_scan, load_h5
from nplab.analysis.particle_exclusion.utils import load_rejected
from nplab.datafile import current

def closest(iterable, val):
    ''' return the closest element in an iterable to val'''
    return min(iterable, key=lambda e: abs(e - val))


def closest_index(iterable, val):
    ''' return its index'''
    return min(enumerate(iterable), key=lambda i_e: abs(i_e[0] - val))[1]


# scan = latest_scan(load_h5())  # most recent particle track, most recent file
scan = latest_scan(current(mode='r')) # pop up a window 
rejected = load_rejected()  # create with monotonous_image_excluder

group_len = len(next(iter(
    scan.values())))  # number of datasets in each particle group
scan = {  # read the scan into a dictionary (but not memory)
    n: p
    for n, p in scan.items() if ((
        n.startswith('Particle')  # has the right name
        and (n not in rejected)  # hasn't been rejected by another script
        and (len(p) == group_len)))  # is full (nothing went wrong)
}
stack = []
for name, group in scan.items():
    z = Spectrum.from_h5(group['alinger.z_scan_0'])  # TODO make sure this is
    # the right name!
    stack.append(z.split(450, 950).max(axis=0).remove_cosmic_ray())
    # between 450 and 950 nm, max(axis=0) condenses it
wl = stack[0].wl[:]  # keep the wl axis as a variable for later

#%% group peaks by maxima
bounds = np.arange(740, 880, 10)  #steps of 10nm, feel free to change
bins = [np.mean(bounds[np.array([i, i + 1])]) for i in range(len(bounds) - 1)]
# the center of the bounds
grouped = {b: [] for b in bins}  # gonna group particles by bin
peaks = []
for spec in stack:
    smooth = spec.smooth(3)  # uses gaussian_filter
    maxima = argrelextrema(smooth, np.greater)[0]  # indices of maxima
    maxima = sorted(maxima,
                    key=lambda i: -smooth[i])  # sort according to height
    if len(maxima):  # if there are any maxima (peaks)
        maximum = spec.wl[maxima[0]]  # take the highest
        if bounds.min() < maximum < bounds.max(
        ):  # if it's within the full bounds
            grouped[closest(grouped,
                            maximum)].append(spec)  # add it to the right bin
            peaks.append(maximum)  # keep the value
#%%compute averages in each bin

averages = {
    group: Spectrum(np.mean(spectra, axis=0), wl)
    if spectra else Spectrum(np.zeros(len(wl)), wl)
    for group, spectra in grouped.items() 
}
#%% plot
fig, ax = plt.subplots()
colors = plt.cm.Spectral(np.linspace(1, 0, len(averages)))

*_, patches = ax.hist(peaks, bins=bounds)
for i, p in enumerate(patches):
    plt.setp(p, 'facecolor', colors[i])
ax.set_ylabel('frequency')
ax.set_xlabel('wavelength (nm)')
ax = plt.twinx(ax)
for i, spectrum in enumerate(averages.values()):
    ax.plot(spectrum.wl, spectrum.smooth(6), color=colors[i])
ax.set_ylabel('intensity')
ax.set_title(f'center = ${np.mean(peaks):.1f}\pm{np.std(peaks):.1f}$nm')
