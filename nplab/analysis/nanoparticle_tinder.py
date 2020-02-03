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
from __future__ import print_function
from __future__ import division

from builtins import range
from builtins import str
from builtins import input
import matplotlib.pyplot as plt
import h5py
import numpy as np

import time

plt.ion()

def accept_reject(group, cutoff = 5000):
    accepted = []
    rejected = []
    #---load the previously saved NPs
    try:
        previously_accepted = np.load('accepted.npy')
        previosly_rejected = np.load('rejected.npy')
    except:
        previously_accepted = []
        previosly_rejected = []
    accepted.extend(previously_accepted)
    rejected.extend(previosly_rejected)
    prar = np.append(previously_accepted, previosly_rejected).tolist()
    
    Progress = [10, 25, 50, 75, 90]
    for index, P in enumerate(list(group.items())):
        p_name = P[0] # name of the particle e.g 'Particle_7'
        particle = P[1] # the particle data group
        if p_name[:3] != 'Par': # discarding non-particle groups
            continue
        if int(p_name.split('_')[1]) not in list(range(cutoff)): #eg. if your track stopped after particle 100, put in 101
            continue
        if p_name in prar: # if you're continuing from some previously saved accepted/rejected lists
            continue
        
        if index*100//len(group)>Progress[0] :# prints the progress. May not work if len(group)<100
            print(str(Progress.pop(0))+'% done')
            
        fig, ax = plt.subplots(1, 3, figsize=(30, 10)) #3 subplots, feel free to use more
        z = particle['z_scan']
        ax[0].plot(z)
        r = particle['SERS']
        ax[1].pcolormesh(r)
        img = particle['image']
        ax[2].imshow(img)
       
        plt.pause(0.1)
        
        ar = input('a/d = accept/decline: ')
        if ar == 'a':
            accepted.append(p_name)
        elif ar == 'd':
            rejected.append(p_name)
        if ar == 'v': # stop the program and save the NPs so far
            np.save('accepted', accepted)
            np.save('rejected', accepted)
            break
        if ar == 'c': # stop the program without saving
            break
        plt.close('all') 
        np.save('accepted', accepted)
        np.save('rejected', accepted)
    
    return accepted, rejected
            

if __name__ == '__main__':
    plt.rc('font',family='arial', size = 18)
    start = time.time()
    
    with [Your_File_here] as File:   
        accepted, rejected = accept_reject(File['ParticleScannerScan_0'])    
        np.save('accepted', accepted)
        np.save('rejected', accepted)
    
    
    print('That took '+str(int(end - time.time))+ ' seconds')
