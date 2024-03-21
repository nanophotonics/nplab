# -*- coding: utf-8 -*-
'''
Created on 2023-02-06
@author: car72

Module with specific functions for processing and analysing NPoM SERS spectra
Inherits spectral classes from spectrum_tools.py
'''

import h5py
import os
import math
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

from importlib import reload

from nplab.analysis import spc_to_h5 as spc


from nplab.analysis.general_spec_tools import spectrum_tools as spt
from nplab.analysis.general_spec_tools import dft_raman_tools as drt
from nplab.analysis.general_spec_tools import all_rc_params as arp

timescan_params = arp.master_param_dict['NPoM SERS Timescan']

def summarise_h5(data_dir, h5_files, summary_filename = 'SERS Summary.h5', scan_format = 'ParticleScannerScan_', 
                 scans_to_omit = [], particle_format = 'Particle_', sers_format = 'kinetic_SERS', z_scan_format = 'lab.z_scan',
                 img_format = 'CWL.thumb_image'):
    '''
    Condenses data from multiple h5_files and/or ParticleScannerScan_ groups therein into one file
    Creates h5 file containing only Particle_0, Particle_1, ..., Particle_{n} groups, each with SERS, image and/or z_scan datasets
    Returns filename of new h5 summary file
    If you want to omit scans from the analysis, add their numbers to the scans_to_omit list
    '''

    os.chdir(data_dir)

    if type(h5_files) == str:
        h5_files = [h5_files]

    if summary_filename in os.listdir():
        os.remove(summary_filename)

    print('Assembling list of particle groups...')

    all_particle_groups = {}
    scans_to_omit = [f'{scan_format}{n}' for n in scans_to_omit]

    for h5_file in h5_files:
        with h5py.File(h5_file, 'r') as F:
            scan_groups = [(scan_name, scan_group) for scan_name, scan_group in F.items()
                           if scan_name.startswith(scan_format)
                           and len(scan_group) > 3 and scan_name not in scans_to_omit
                          ]

            all_particle_groups[h5_file] = []

            for scan_name, scan_group in scan_groups:
                particle_names = sorted([i for i in scan_group.keys()
                                         if i.startswith(particle_format)],
                                        key = lambda i: int(i.split('_')[-1]))
                for particle_name in particle_names:
                    particle_path = f'{scan_name}/{particle_name}'
                    if sers_format in F[particle_path].keys():
                        all_particle_groups[h5_file].append(particle_path)
            
            print('  Done\n')

            
    n = 0

    n_spectra = len([i for j in all_particle_groups.values() for i in j])

    for h5_file in h5_files:
        with h5py.File(h5_file, 'r') as F:
            with h5py.File(summary_filename, 'a') as G:
                print('Transferring data...')            

                for n, particle_path in enumerate(all_particle_groups[h5_file], n + 1):
                    #print(n)

                    spt.percent_progress(n, n_spectra, resolution = 5, indent = 1)

                    g_particle_old = F[particle_path]

                    sers_dsets = [i[1] for i in g_particle_old.items() if i[0].startswith(sers_format)]

                    if len(sers_dsets) == 0:
                        print(g_particle_old.keys())
                        continue

                    sers_dset = sers_dsets[0]                
                    sers_attrs = sers_dset.attrs           

                    g_particle_new = G.create_group(f'{particle_format}{n}')
                    g_particle_new.attrs['original_path'] = f'{h5_file}/{particle_path}'

                    d_sers = g_particle_new.create_dataset(sers_format, data = sers_dset)
                    d_sers.attrs.update(sers_attrs)

                    particle_imgs = [i for i in g_particle_old.items()
                                     if i[0].startswith(img_format)
                                    ]

                    z_scans = [i for i in g_particle_old.items()
                              if i[0].startswith(z_scan_format)
                              ]

                    for dsets in [particle_imgs, z_scans]:
                        for dset in dsets:
                            new_dset = g_particle_new.create_dataset(dset[0], data = dset[1])
                            new_dset.attrs.update(dset[1].attrs)

            print('Done')

    return summary_filename

def plot_all_timescans(h5_summary, data_dir = None, powder_spectrum = None, agg_sers_spectrum = None, 
                       dft_collection = None, sers_format = 'kinetic_SERS', save_figs = True, 
                       x_scale = 1, x_shift = 0,
                       **kwargs):
    
    np.seterr('ignore')

    if data_dir is not None:
        os.chdir(data_dir)

    if 'Timescans' not in os.listdir():
        os.mkdir('Timescans')

    with h5py.File(h5_summary, 'r') as G:
        particle_groups = sorted(G.items(), key = lambda i: int(i[0].split('_')[-1]))
        
        for n, (particle_name, particle_group) in enumerate(particle_groups):
            spt.percent_progress(n, len(particle_groups), 5)
            
            if sers_format not in particle_group.keys():
                continue

            timescan = NPoM_SERS_Timescan(particle_group[sers_format], powder_spectrum = powder_spectrum, 
                                          agg_sers_spectrum = agg_sers_spectrum, particle_name = particle_name,
                                          dft_collection = dft_collection, save_figs = save_figs,
                                          **kwargs)
            timescan.scale_x(x_scale, x_shift)
            timescan.plot_npom_sers_timescan(**kwargs)

    np.seterr('warn')

class NPoM_SERS_Spectrum(spt.Spectrum):
    '''
    Object containing xy data and functions for NPoM SERS spectral analysis and plotting
    Inherits from "Spectrum" object class in spectrum_tools module
    args can be y data, x and y data, h5 dataset or h5 dataset and its name
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    '''
    Work in Progress
    '''

class NPoM_SERS_Timescan(spt.Timescan):
    '''
    Object containing xy data and functions for NPoM SERS spectral analysis and plotting
    Inherits from "Timescan" object class in spectrum_tools module
    args can be y data, x and y data, h5 dataset or h5 dataset and its name
    Optional inputs:
        powder_spectrum: spt.Spectrum object containing powder Raman data
        agg_sers_spectrum: spt.Spectrum object containing aggregate SERS data
        dft_collection: drt.DFT_Raman_Collection object
        raman_excitation: excitation wavelength from which to convert wavelength to wavenumber
            NB: leave raman_excitation = None if x input is already in wavenumbers
    '''
    def __init__(self, *args, powder_spectrum = None, agg_sers_spectrum = None, dft_collection = None,
                 raman_excitation = 633, use_powder_xlim = True, particle_name = 'Particle_', find_dft = True, **kwargs):

        super().__init__(*args, raman_excitation = raman_excitation, **kwargs)

        self.powder_spectrum = powder_spectrum
        self.agg_sers_spectrum = agg_sers_spectrum
        self.dft_collection = dft_collection
        self.particle_name = particle_name

        self.x_min = self.x.min()
        self.x_max = self.x.max()

        if use_powder_xlim == True:
            if self.agg_sers_spectrum is not None and self.powder_spectrum is not None:
                self.x_min = min([self.powder_spectrum.x.min(), self.agg_sers_spectrum.x.min()])
                self.x_max = max([self.powder_spectrum.x.max(), self.agg_sers_spectrum.x.max()])

            if self.powder_spectrum is not None:
                self.x_min = self.powder_spectrum.x.min()
                self.x_max = self.powder_spectrum.x.max()

            elif self.agg_sers_spectrum is not None:
                self.x_min = self.agg_sers_spectrum.x.min()
                self.x_max = self.agg_sers_spectrum.x.max()            

        if self.dft_collection is None and find_dft == True:
            self.dft_collection = drt.DFT_Raman_Collection(x_min = self.x_min, x_max = self.x_max, **kwargs)
            if len(self.dft_collection.dft_dict) == 0:
                print('No DFT Raman found')
                self.dft_collection = None

        if self.dft_collection == False:
            self.dft_collection = None

    def plot_powder_agg(self, ax = None, powder = True, agg_sers = True, rc_params = timescan_params):

        if ax is None:
            old_rc_params = plt.rcParams.copy()
            plt.rcParams.update(rc_params)
            external_ax = False
            fig, ax = plt.subplots()
        else:
            external_ax = True

        powder = self.powder_spectrum
        agg_sers = self.agg_sers_spectrum

        ax.plot(powder.x, powder.y, 'k')
        ax.plot(agg_sers.x, agg_sers.y + 1, 'r')
        ax.set_xlabel('Raman Shift (cm$^{-1}$)')
        ax.set_ylabel('Counts')
        ax.set_yticks([])

        if external_ax == False:
            plt.show()
            plt.rcParams.update(old_rc_params)

    def plot_npom_sers_timescan(self, particle_format = 'Particle_', sers_format = 'kinetic_SERS', show = True,
                                rc_params = timescan_params, dft_polarisations = ['yz'], plot_averages = True,
                                x_min = None, x_max = None, x_scale = 1, x_shift = 0, excitation_wl = 633,
                                save_figs = True, title = None, **kwargs):

        old_rc_params = plt.rcParams.copy()
        if rc_params is not None:
            plt.rcParams.update(rc_params)

        fig = plt.figure(figsize = (16, 16))

        if title != False:
            if title is None:
                title = self.particle_name
            
        ax = plt.subplot2grid((17, 1), (4, 0), rowspan = 9)

        x_lim = [self.x_min, self.x_max]  

        '''
        DFT
        '''

        if self.dft_collection is not None:
            ax_dft = plt.subplot2grid((17, 1), (0, 0), rowspan = 4, sharex = ax)
        
            self.dft_collection.plot_dft(polarisations = dft_polarisations, ax = ax_dft, **kwargs)

            #ax_dft.set_ylim(-0.1, y.max() + 0.1)
            ax_dft.set_ylabel('DFT Raman\nActivity')
            ax_dft.set_xlim(*x_lim)
            ax_dft.set_yticks([])
            #ax_dft.set_xticks([])
            ax_dft.set_zorder(-1)
            ax_dft.set_title(f'{title}'.replace('_', ' '))

        '''
        Timescan
        '''
                
        self.scale_x(x_scale, x_shift)
        self.plot_timescan(ax = ax, plot_averages = plot_averages, x_lim = x_lim, **kwargs) 
        ax.xaxis.set_minor_locator(MultipleLocator(25))
        if self.dft_collection is None:
            ax.set_title(f'{title}'.replace('_', ' '))

    
        '''
        Agg SERS
        '''

        if self.agg_sers_spectrum is not None:
            ax_agg = plt.subplot2grid((17, 1), (13, 0), rowspan = 2, sharex = ax)
            ax_agg.plot(self.agg_sers_spectrum.x, self.agg_sers_spectrum.y, color = plt.cm.Dark2(3), label = 'Agg SERS')
            ax_agg.set_yticks([])
            position = (0, 0)
            if self.powder_spectrum is None:
                position = (0, 0.5)

            ax_agg.set_ylabel('Counts', position = position)
            ax_agg.legend(loc = 'upper left', bbox_to_anchor = (0.25, 1))
            ax_agg.set_xlim(*x_lim)
        
        '''
        Powder
        ''' 
        if self.powder_spectrum is not None:

            if self.agg_sers_spectrum is None:
                ax_powder = plt.subplot2grid((17, 1), (13, 0), rowspan = 2, sharex = ax)
            else:
                ax_powder = plt.subplot2grid((17, 1), (15, 0), rowspan = 2, sharex = ax)

            ax_powder.plot(self.powder_spectrum.x, self.powder_spectrum.y, 'k', label = 'Powder Raman')
            ax_powder.set_yticks([])
            if self.agg_sers_spectrum is None:
                ax_powder.set_ylabel('Counts')
            ax_powder.legend(loc = 'upper left', bbox_to_anchor = (0.25, 1))
            ax_powder.set_xlim(*x_lim)

        
        plt.xlabel('Raman Shift (cm$^{-1}$)')
        #fig.tight_layout()            
        plt.subplots_adjust(hspace = 0, wspace = 0)

        if save_figs == True:
            fig.savefig(f'Timescans/{self.particle_name}.png', facecolor = 'white', transparent = False, bbox_inches = 'tight')
    
        if show == True:
            plt.show()
        else:
            plt.close('all')

        plt.rcParams.update(old_rc_params)