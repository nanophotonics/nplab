# -*- coding: utf-8 -*-
'''
Created on 2023-02-09
@author: car72

Module with specific functions for processing and analysing aggregate SERS spectra
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

from nplab.analysis import spc_to_h5 as sph

from nplab.analysis.general_spec_tools import particle_track_analysis as pta
from nplab.analysis.general_spec_tools import spectrum_tools as spt
from nplab.analysis.general_spec_tools import dft_raman_tools as drt

from nplab.analysis.general_spec_tools import all_rc_params as arp

agg_sers_rc_params = arp.master_param_dict['Agg SERS']
dft_rc_params = arp.master_param_dict['DFT Raman']
bbox_params = arp.bbox_params

other_plot_params = {'title_bbox' : 
                                {'boxstyle' : 'square',
                                'facecolor' : 'white',
                                'edgecolor' : 'white',
                                'linewidth' : 0,
                                'alpha' : 1},

                'title_weight' : 1.3,
                'title_position' : (0.5, 0.993),

                'title_ha' : 'center', 'title_va' : 'center',
                'legend_titlesize' : 18,
                'fig_rect' : [0, 0, 0.85, 1], 
                'cbar_left' : 0.82, 
                'cbar_width' : 0.05,
                'laser_colors' : {532 : 'green', 633 : 'red', 785 : 'darkred'}
                }

def extract_all_spc(data_dir = None):
    if data_dir is not None:
        os.chdir(data_dir)

    print(f'Extracting .spc data from {os.getcwd()}')

    for i in os.listdir('.'):
        if 'Raman Data' in i and i.endswith('.h5'):
            print('Deleting existing file: %s' % i)
            os.remove(i)

    return sph.run(nameOnly = True)

def inspect_data(data_dir = None, name_format = None, **kwargs):
    '''
    Quickly plots all Raman spectra (extracted using extract_all_spc()), for inspection
    '''
    if name_format is None:
        name_format = os.path.split(os.getcwd())[-1]

    h5_file = pta.find_h5_file(root_dir = data_dir, name_format = name_format, **kwargs)

    with h5py.File(h5_file, 'r') as F:
        print(list(F['All Raw'].keys()))
        for dset_name, dset in F['All Raw'].items():
            spectrum = Renishaw_Raman_Spectrum(dset)
            spectrum.plot_raman()

def tidy_h5(dset_names, new_dset_names = None, old_h5_name = None, new_h5_name = None, 
            sum_timescans = False, **kwargs):

    if old_h5_name is None:
        name_format = os.path.split(os.getcwd())[-1]
        old_h5_name = pta.find_h5_file(exclude = 'Summary', name_format = name_format, **kwargs)

    if new_h5_name is None:
        new_h5_name = f'{old_h5_name.replace(".h5", "").replace(" Raman Data", "")} Summary.h5'

    if new_h5_name in os.listdir():
        os.remove(new_h5_name)

    if new_dset_names is None:
        new_dset_names = dset_names

    print(f'Creating summary of {old_h5_name}\n')

    with h5py.File(old_h5_name, 'r') as F:
        with h5py.File(new_h5_name, 'a') as G:
            for old_dset_name, new_dset_name in zip(dset_names, new_dset_names):
                old_dset = F[old_dset_name]
                old_data = old_dset[()]

                if len(old_data.shape) > 1 and sum_timescans == True:
                    old_data = np.sum(old_data, axis = 0)

                new_dset = G.create_dataset(new_dset_name, data = old_data)
                new_dset.attrs.update(old_dset.attrs)
                print(f'{old_dset_name} moved to {new_dset_name}')

    print(f'\nSummary file: {new_h5_name} created')
    return new_h5_name

class Renishaw_Raman_Spectrum(spt.Spectrum):
    '''
    Object containing xy data and functions for NPoM SERS spectral analysis and plotting
    Inherits from "Spectrum" object class in spectrum_tools.py
    args can be y data, x and y data, h5 dataset (with or without its name as a string)
    '''    
    def __init__(self, *args, x_range = None, norm_range = None, concentration = None, **kwargs):
        super().__init__(*args, **kwargs)

        self.x_range = x_range
        self.norm_range = norm_range        
        self.concentration = concentration

        if len(self.y.shape) == 2:
            self.Y = self.y.copy()
            self.y = np.sum(self.Y, axis = 0)

        self.y_raw = self.y.copy()
        self.x_raw = self.x.copy()

        for arg in args:
            if type(arg) == str:
                if arg.endswith('.spc'):
                    pass
                    '''
                    !!! Need to update spc_to_h5 module to include functions for individual spectra
                    '''

    def subtract_baseline(self, lam = 1e4, p = 1e-4, niter = 10, plot = False, smooth_first = False, **kwargs):
        if smooth_first == True:
            y = spt.butter_lowpass_filt_filt(self.y, **kwargs)
        else:
            y = self.y

        self.baseline = spt.baseline_als(y, lam, p, niter)
        self.y_baselined = self.y - self.baseline

        if plot == True:
            self.plot_raman(baseline = True)

    def normalise(self, baselined = False):
        '''
        Normalise spectrum
        If norm_range (in form of [x1, x2]) is specified, normalises to local maximum within that range
        '''
        x = self.x

        if baselined == True:
            y = self.y_baselined
        else:
            y = self.y

        if self.norm_range is None:
            y_max = np.nanmax(y)
        else:
            x_trunc, y_trunc = spt.truncate_spectrum(x, y, *self.norm_range)

            y_max = np.nanmax(y_trunc)

        y_norm = y - np.nanmin(y)
        self.y_norm = y_norm/y_max

    def clean_spectrum(self, x_range = None, **kwargs):
        '''
        remove nans, truncate, subtract baseline and normalise
        '''

        if self.x_range is not None:
            self.x, self.y = spt.truncate_spectrum(self.x_raw, self.y_raw, *self.x_range)

        else:
            self.x, self.y = self.x_raw, self.y_raw

        self.y = spt.remove_nans(self.y)

        self.subtract_baseline(**kwargs)

        self.normalise(baselined = True)
        self.y_clean = self.y_norm
        #print(len(self.x), len(self.y_clean))

    def set_color(self, color):
        self.color = color

    def plot_raman(self, ax = None, rc_params = agg_sers_rc_params, baseline = False, clean = False, title = True):
        old_rc_params = plt.rcParams.copy()

        if ax is None:
            external_ax = False

            if rc_params is not None:
                plt.rcParams.update(rc_params)

            fig, ax = plt.subplots()

        y = self.y
        x = self.x

        if clean == True:
            y = self.y_clean

        if len(y.shape) > 1:
            y = np.sum(y, axis = 0)       

        else:
            external_ax = True

        ax.plot(x, y)

        if baseline == True:
            ax.plot(x, self.baseline)
        
        ax.set_xlabel('Raman Shift (cm$^{-1}$)')
        ax.set_yticks([])
        ax.set_ylabel('Scattering Intensity')

        ax.xaxis.set_minor_locator(MultipleLocator(20))
        
        if title == True:
            ax.set_title(self.name)

        if external_ax == False:
            plt.show()
            plt.rcParams.update(old_rc_params)

class Concentration_Series:
    '''
    Data object containing plotting function for agg SERS concentration series
    required inputs
        h5 file containing data
        aggregant concentrations in uM
            these can be provided as attributes in the h5 file, or explicitly specified
            if explicitly specified, concentration attribute will be created and/or overwritten for each dataset

    !!! turn this class into more general Renishaw Series so it can be used for power series as well

    '''

    def __init__(self, h5_root = None, dft_dir = None, dft_collection = None, sample_names = None, concentrations = None, data_names = None,
                 norm_range = None, x_range = None, powder_spectrum = None, baseline_plot = False, init_plot = False, **kwargs):

        self.raman_spectra = []
        self.x_range = x_range
        self.norm_range = norm_range
        self.dft_dir = dft_dir
        self.dft_collection = dft_collection

        if self.dft_collection is not None:
            assert type(self.dft_collection) == drt.DFT_Raman_Collection, 'dft_collection must be an instance of drt.DFT_Raman_Collection'
            self.dft_names = list(self.dft_collection.dft_dict.keys())

        if concentrations is not None:
            if type(concentrations) == str:
                with open(concentrations, 'r') as F:
                    concentrations = np.array([float(line) for line in F])

        self.concentrations = concentrations
        self.real_concentrations = True
        self.powder_spectrum = powder_spectrum

        F = h5_root

        if sample_names is None:
            sample_names = sorted(F.keys())

        if self.concentrations is None:                
            if 'Concentration' in F[sample_names[0]].attrs.keys():
                self.concentrations = [F[i].attrs['Concentration'] for i in sample_names]
            else:
                self.concentrations = np.linspace(1, 10, len(F.keys()))#dummy concentrations to keep everything else happy
                self.real_concentrations = False
                print('Warning: No concentrations specified')

        if 'Powder' in sample_names and len(self.concentrations) == len(sample_names) - 1:
            self.concentrations = list(self.concentrations)
            self.concentrations.append(np.average(self.concentrations))
            self.concentrations = np.array(self.concentrations)

        for sample_name, concentration in zip(sample_names, self.concentrations):
            #print(sample_name)

            if sample_name == 'Powder':
                norm_range = None
            else:
                norm_range = self.norm_range

            spectrum = Renishaw_Raman_Spectrum(F[sample_name], x_range = x_range, norm_range = norm_range,
                                               concentration = concentration)
            spectrum.clean_spectrum(plot = baseline_plot, **kwargs)
            if init_plot == True:
                spectrum.plot_raman(clean = True)

            if sample_name == 'Powder':
                self.powder_spectrum = spectrum

            else:
                self.raman_spectra.append(spectrum)

        self.concentrations = np.array(self.concentrations)

        if self.x_range is None:
            self.x_range = [min([spectrum.x.min() for spectrum in self.raman_spectra]), 
                            max([spectrum.x.max() for spectrum in self.raman_spectra])]

        self.x_range = np.array(self.x_range)
        self.kwargs = kwargs
        self.dft_collection = None
        self.dft_names = []

    def load_dft(self, dft_dir = None, dft_names = None, polarisation = None, x_min = None, x_max = None):
        if dft_dir is None:
            dft_dir = self.dft_dir

        self.dft_collection = drt.DFT_Raman_Collection(dft_dir, dft_names, polarisation, x_min, x_max)
        self.dft_names = list(self.dft_collection.dft_dict.keys())

    def plot_conc_series(self, dft_spectra = {}, x_range = None, dft_text_loc = None, label_x_loc = 500, 
                         expt_labels = False, title = None, cbar_label = 'Aggregant Concentration ($\mathrm{\mu}$M)',
                         text_pad = 0.08, y_squish = 1, rc_params = agg_sers_rc_params, bbox_params = bbox_params, 
                         threshold_conc = 0, powder_color = 'grey', **kwargs):

        old_rc_params = plt.rcParams.copy()

        if rc_params is not None:
            plt.rcParams.update(rc_params)

        n_expt_spectra = len(self.raman_spectra)

        if self.dft_collection is not None:
            self.dft_collection.get_polar_dict(polarisations = dft_spectra)
            n_dft_spectra = self.dft_collection.n_spectra
        else:
            n_dft_spectra = 0

        if x_range is None:
            x_range = self.x_range

        fig_height = n_expt_spectra + n_dft_spectra
        fig_height *= 1.5

        fig = plt.figure(figsize = (14, fig_height))
        ax = fig.add_subplot(111)

        len_cols = 1000

        #print('Concentrations:', self.concentrations)

        conc_cont = np.logspace(np.log10(self.concentrations.min()), np.log10(self.concentrations.max()), len_cols)
        cmap = plt.get_cmap('jet_r', len_cols)

        '''
        Powder Spectrum
        '''
        n_start = 0

        if self.powder_spectrum is not None:
            n_start = 1
            x = self.powder_spectrum.x
            y = self.powder_spectrum.y_clean
            x, y = spt.truncate_spectrum(x, y, *x_range)
            ax.plot(x, y, 'k', lw = 4, alpha = 0.7)
            ax.plot(x, y, color = powder_color)

            label_y_loc = y[abs(x - label_x_loc).argmin()] + 0.5
            ax.text(label_x_loc, label_y_loc, 'Powder', va = 'center', ha = 'center', transform = ax.transData, bbox = bbox_params)

        '''
        Experimental Spectra
        '''

        for n, spectrum in enumerate(sorted(self.raman_spectra, key = lambda spectrum: spectrum.concentration), n_start):
            x = spectrum.x

            if spectrum.concentration > threshold_conc:
                y = spectrum.y_clean
            else:
                y = spectrum.y_raw/100

            x, y = spt.truncate_spectrum(x, y, *x_range)

            y += n*y_squish

            color = cmap(abs(conc_cont - spectrum.concentration).argmin())
            ax.plot(x, y, 'k', lw = 4, alpha = 0.7)
            ax.plot(x, y, color = color)

            if expt_labels == True:
                label_y_loc = y[abs(x - label_x_loc).argmin()]
                ax.text(label_x_loc, label_y_loc, spectrum.name, va = 'center', ha = 'left', transform = ax.transData, bbox = bbox_params)

        y_offset = np.nanmax(y) + 0.4

        if not np.isfinite(y_offset):
            y_offset = len(self.raman_spectra)*y_squish + 1#for plotting DFT spectra above

        label_y_loc = y[abs(x - label_x_loc).argmin()] + y_squish/2 + 0.15
        color = np.array(color)
        color *= 0.7
        current_bbox_params = bbox_params.copy()
        current_bbox_params['edgecolor'] = tuple(color)
        current_bbox_params['alpha'] = 1

        ax.text(label_x_loc, label_y_loc, 'Agg SERS:', ha = 'left',
                fontsize = plt.rcParams['legend.fontsize'], bbox = current_bbox_params)

        ax.set_yticks([])
        ax.set_xlim(*x_range)
        ax.set_ylim(bottom = -0.1)
        ax.xaxis.set_major_locator(MultipleLocator(200))
        ax.xaxis.set_minor_locator(MultipleLocator(20))

        ax.set_xlabel('Raman Shift (cm$^{-1}$)')
        ax.set_ylabel('Counts')

        if title is not None:
            ax.set_title(title)

        plt.rcParams['legend.title_fontsize'] = plt.rcParams['legend.fontsize']

        '''
        Colorbar
        '''

        if self.real_concentrations == True:
            cbar_width = other_plot_params['cbar_width']
            cbar_left = other_plot_params['cbar_left']
            fig_rect = other_plot_params['fig_rect']
        
            fig.tight_layout(rect = fig_rect)
            plt.subplots_adjust(hspace = 0, wspace = 0.05)
            ax_left, ax_bottom, ax_width, ax_height = ax.get_position().bounds
            ax_cbar = fig.add_axes([cbar_left, ax_bottom, cbar_width, ax_height])
            cbar_norm = mpl.colors.LogNorm(vmin = conc_cont.min(), vmax = conc_cont.max())
            cbar = mpl.colorbar.ColorbarBase(ax_cbar, cmap = cmap, norm = cbar_norm, orientation = 'vertical')#, 
            cbar.set_label(cbar_label, rotation = 270, verticalalignment = 'bottom')

        '''
        DFT Raman
        '''

        if self.dft_collection is not None:
            self.dft_collection.plot_dft(polarisations = None, x_range = x_range, text_loc = dft_text_loc,
                                   text_pad = text_pad, ax = ax, y_offset = y_offset, rc_params = None)

        fig.savefig('Agg SERS Conc Series.png', bbox_inches = 'tight', transparent = True)
        plt.show()

        plt.rcParams.update(old_rc_params)