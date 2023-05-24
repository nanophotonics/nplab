# -*- coding: utf-8 -*-
"""
Created on Mon Aug  5 10:30:06 2019

@author: Eoin Elliott

Provides a popup of some plotted data, as well as the option to accept or reject it.
Useful for manually sorting/classifying nanoparticles

Obviously you'll need to choose what you want to plot.

Changing spyder's matplotlib backed to inline makes it faster.

>Tools>Preferences>IPython Console>graphics>Backend: Inline


"""
import time

import matplotlib.pyplot as plt
import h5py
import numpy as np
from tqdm import tqdm
from nplab.analysis.particle_exclusion.utils import load_rejected, save_rejected
import h5py



plt.ion()

def reject(group, plot_function, cutoff=5000):
    rejected = load_rejected()
    group_len = len(next(iter(
        group.values())))  # number of datasets in each particle group
    scan = {  # read the scan into a dictionary (but not memory)
        n: p
        for n, p in group.items() if (
            n.startswith('Particle')  # has the right name
            and (n not in rejected)  # hasn't been rejected by another script
            )  # is full (nothing went wrong)
    }
    scan = {k: scan[k] for k in sorted(scan,
                                       key=lambda k: int(k.split('_')[-1]))}
    
    for name, particle in tqdm(scan.items()):
        if int(name.split('_')[-1]) > int(cutoff): 
            rejected.add(name)
        elif (len(particle) != group_len):
            rejected.add(name)
        else:
            plot_function(particle, name)
            plt.pause(0.1)
            
            ar = input('a/d = accept/decline: ').strip().lower()
            if ar == 'a':
                pass
            if ar == 'd':
                rejected.add(name)
        save_rejected(rejected)
    return rejected
            

if __name__ == '__main__':
    plt.rc('font',family='arial', size=18)
    start = time.time()
    rejected = load_rejected()
    
    def plot_function(particle, name):
        print('\n')
        print(particle)
        fig, ax = plt.subplots(1, 3, figsize=(30, 10)) #3 subplots, feel free to use more
        z = particle['lab.z_scan_1']
        ax[0].pcolormesh(z)
        #r = particle['H2-TAPP-SMe-60nm_NPoM_633nm_1sx20scans_Powerseries_16']
        #ax[1].pcolormesh(r)
        img = particle['CWL.thumb_image_1']
        ax[2].imshow(img)
       
    my_h5 = h5py.File(r'C:\Users\il322\Desktop\Offline Data\2023-03-25_M-TAPP-SME_60nm_NPoM_Track_DF_Powerseries.h5')    
    with my_h5 as File:   
        rejected = reject(File['ParticleScannerScan_2'], plot_function)    
        save_rejected(rejected)