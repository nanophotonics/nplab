# -*- coding: utf-8 -*-
"""
Created on Sun May 14 14:22:50 2023

@author: il322

Module with specific functions for processing GC files from Shannon and analysing Gas Chromatography spectra
Inherits spectral classes from spectrum_tools.py
"""

import h5py
import os
import math
from math import log10, floor
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from importlib import reload
import pandas as pd

from nplab.analysis.general_spec_tools import spectrum_tools as spt
from nplab.analysis.general_spec_tools import npom_sers_tools as nst



def process_file(filename):
    
    ''' 
    Takes GC data .txt file and returns spectrum data and peak data
    
    Parameters:
        filename(str)
            
    Returns:
        spectrum_data(2DArray float): 2d float array of spectrum data
        peak_data(2DArray float): 2d float array of GC peak data (from GC GUI)
    '''
    
    # Import file as pandas df for easier processing
    
    file_df = pd.read_csv(filename, sep='\t', names = np.linspace(0,20,21))
    file_df.fillna(0, inplace=True)
    
    ## Find indices of target data
    spectrum_start = file_df.loc[file_df[0.0] == '[Chromatogram (Ch1)]'].index[0] + 6
    peak_start = file_df.loc[file_df[0.0] == '[Peak Table(Ch1)]'].index[0] + 3
    peak_end = file_df.loc[file_df[0.0] == '[Compound Results(Ch1)]'].index[0]
    
    ## Get spectrum & peak data in numpy arrays
    spectrum_data = np.array(file_df[spectrum_start:])
    spectrum_data = spectrum_data[:,0:2]
    spectrum_data = spectrum_data.astype(float)
    peak_data = np.array(file_df[peak_start:peak_end])
    peak_data = peak_data[:,0:8]
    peak_data = peak_data.astype(float)
    
    return spectrum_data, peak_data

     
#%% GC_Spectrum class

class GC_Spectrum(spt.Spectrum):
    
    '''
    Object containing xy data and functions for GC spectral analysis and plotting
    Inherits from "Spectrum" object class in spectrum_tools module
    args can be y data, x and y data
    '''
    
    def __init__(self, peak_data = None, *args, **kwargs):

        super().__init__(*args, **kwargs)


        self.x_min = self.x.min()
        self.x_max = self.x.max()
        
        if peak_data is not None:
            self.peaks = peak_data
            
        
        
    def normalise(self, norm_range = (0, 1), norm_y = None):
        
        '''
        Function for normalizing spectra in timescan
        
        Parameters:
            norm_range: (tuple = (0, 1)) Normalization range
            norm_y: (None) Which y to normalize (self.y_smooth, self.y_baselined, etc). Default is just self.y
        '''
        
        if norm_y is None:
            self.y_norm = self.y.copy()
        else:
            self.y_norm = norm_y.copy()
        self.y_norm = self.y_norm.astype('float64')
        
        ## Normalize
        self.y_norm = self.y_norm - self.y_norm.min()
        self.y_norm = (self.y_norm / self.y_norm.max()) * (norm_range[1] - norm_range[0])
        self.y_norm = self.y_norm + norm_range[0]
        
        
    def plot(self, ax = None, plot_y = None, title = None, **kwargs):
        
        '''
        Plotting function
        requires docstring
        '''
        
        if ax is None:
            fig, ax = plt.subplots(1,1,figsize=[8,6])
            ax.set_xlabel('Retention Time (min)')
            ax.set_ylabel('Intensity (a.u.)')
            
        if plot_y is None:
            y_plot = self.y.copy()
        else:
            y_plot = plot_y.copy()
            
        if title is None:
            ax.set_title(self.name)
        else:
            ax.set_title(title)
            
        ax.plot(self.x, y_plot, **kwargs)


#%% Testing




