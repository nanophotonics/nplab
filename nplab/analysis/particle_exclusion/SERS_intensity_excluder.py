# -*- coding: utf-8 -*-
"""
Created on Sat July 7 2022

@author: Yonatan - jb2444

this code excludes particles based on their SERS signal:
particle would be excluded if the maximum intensity of the SERS signal is below 500 cts.

"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from nplab.analysis import latest_scan, load_h5, Spectrum
from nplab.analysis.particle_exclusion.utils import load_rejected, save_rejected
from scipy import ndimage, signal
from tqdm import tqdm



class IntensityExcluder():
    '''excludes particles who's darkfield spectrum peaks below a threshold (set by a user) '''

    def __init__(self, scan, SERS_name='lab.SERS_0',counts_thresh=500):
        # SERS_name is the name of the group of the SERS data,
        # if the global maximum of the SERS is below counts_thresh the particle will be excluded
        self.scan = scan
        self.SERS_name = SERS_name
        # the DF maximum should be above this wavelength:
        self.counts_thresh = counts_thresh
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
            spec=Spectrum.from_h5(group[self.SERS_name]) # extracts the DF spectrum from file
            wl = spec.wl
            global_max = np.max(spec)
            reject_flag=False
            
            reject_flag = True
            for sp in spec:
                ind_list = np.where(sp > self.counts_thresh)[0]
                
                if len(ind_list)>=7:
                    reject_flag = False
                    continue
            if reject_flag:
                rejected.add(name)
                
            # if global_max <= self.counts_thresh:
            #     rejected.add(name)
            #     reject_flag=True

            if plot:
                plt.figure(figsize=(9, 3), dpi=80)
                status = 'rejected' if reject_flag else 'accepted'
                plt.suptitle(f'{name}, {status}')
                for sp in spec:
                    plt.plot(wl,sp)
                    plt.hlines(self.counts_thresh,np.min(wl), np.max(wl), colors=None, linestyles='dashed')
                plt.savefig(self.fig_dir / f'_{name}.png')
                plt.close()
        save_rejected(rejected)
        print(f'{(len(rejected) / total)*100}% rejected')


if __name__ == '__main__':
    scan = latest_scan(load_h5())
    mie = IntensityExcluder(scan)
    mie.run()
