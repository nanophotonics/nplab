# -*- coding: utf-8 -*-
"""
Created on Sat July 7 2022

@author: Yonatan - jb2444

this code excludes particles based on their dakfield scattering spectrum:
    particle would be excluded if their DF peak is below a threshold,
    default is 650nm

"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from nplab.analysis import latest_scan, load_h5, Spectrum
from nplab.analysis.particle_exclusion.utils import load_rejected, save_rejected
from scipy import ndimage, signal
from tqdm import tqdm



class DarkfieldExcluder():
    '''excludes particles who's darkfield spectrum peaks below a threshold (set by a user) '''

    def __init__(self, scan, DF_name='lab.z_scan0',cutoff_wavelength=650, sigma=6):
        # DF_name is the name of the group of the darkfield data,
        # if the global maximum of the darkfield spectrum is below cutoff_wavelength the particle will be excluded
        # sigma is the width of the gaussian filter used for smoothing
        self.scan = scan
        self.DF_name = DF_name
        # the DF maximum should be above this wavelength:
        self.cutoff_wavelength = cutoff_wavelength
        self.sigma = sigma  # smoothing weight
        self.fig_dir = Path() / 'spectra figures'  # may not exist yet

    def run(self, plot=False, overwrite=True):
        if plot:
            if not self.fig_dir.exists(
            ):  # make the folder if it doesn't exist
                self.fig_dir.mkdir()

        rejected = set() if overwrite else load_rejected()
        total = len(self.scan)
        for name, group in tqdm(list(self.scan.items())):
            if not name.startswith('Particle'):
                continue
            temp_spec=Spectrum.from_h5(group[self.DF_name]) # extracts the DF spectrum from file
            spec= temp_spec.split(450, 950).max(axis=0).remove_cosmic_ray() # cleans and makes a single spectrum
            wl=spec.wl # extracts wavelength vector
            smoothed_spec = ndimage.gaussian_filter1d(spec, sigma=self.sigma,axis=0) # smooth data
            max_ind=np.where(smoothed_spec==np.max(smoothed_spec))[0] # finds the global maximum
            wl_max=wl[max_ind] # finds the wavelength of global maximum
            reject_flag=False
            if wl_max <= self.cutoff_wavelength:
                rejected.add(name)
                reject_flag=True

            if plot:
                plt.figure(figsize=(9, 3), dpi=80)
                status = 'rejected' if reject_flag else 'accepted'
                plt.suptitle(f'{name}, {status}')
                plt.plot(wl,spec)
                plt.plot(wl,smoothed_spec)
                plt.vlines(self.cutoff_wavelength,np.min(spec), np.max(spec), colors=None, linestyles='dashed')
                plt.savefig(self.fig_dir / f'DF_{name}.png')
                plt.close()
        save_rejected(rejected)
        print(f'{(len(rejected) / total)*100}% rejected')


if __name__ == '__main__':
    scan = latest_scan(load_h5())
    mie = DarkfieldExcluder(scan)
    mie.run()
