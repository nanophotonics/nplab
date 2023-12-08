# -*- coding: utf-8 -*-
"""
Created on Wed Apr 26 18:32:45 2023

@author: il322

Plotter for M-TAPP-SMe 633nm SERS before/after plasma cleaning


(samples:
     2023-11-28_Co-TAPP-SMe_60nm_MLAgg_on_Glass_a)

"""

import gc
import numpy as np
import scipy as sp
from matplotlib import pyplot as plt
import matplotlib as mpl
import tkinter as tk
from tkinter import filedialog
import statistics
from scipy.stats import linregress
from scipy.interpolate import interp1d
from scipy.signal import find_peaks
from scipy.signal import find_peaks_cwt
from scipy.signal import savgol_filter
from pylab import *
import nplab
import h5py
import natsort
import os

from nplab.analysis.general_spec_tools import spectrum_tools as spt
from nplab.analysis.general_spec_tools import npom_sers_tools as nst
from nplab.analysis.general_spec_tools import agg_sers_tools as ast
from nplab.analysis.SERS_Fitting import Auto_Fit_Raman as afr
from nplab.analysis.il322_analysis import il322_calibrate_spectrum as cal
from nplab.analysis.il322_analysis import il322_SERS_tools as SERS
from nplab.analysis.il322_analysis import il322_DF_tools as df


#%% Get text files into arrays from Reni, plot for screening


def process_text_file(file_path):
    # Read the text file into a NumPy array
    data = np.loadtxt(file_path, delimiter='\t')  # Adjust the delimiter as per your file format

    # Assuming the first column is x and the second column is y
    x = data[:, 1]
    y = data[:, 2]

    return x, y


# Iterate through all files in the folder
folder_path = r'C:\Users\ishaa\OneDrive\Desktop\Offline Data\2023-11-30_Co-TAPP-SMe_Powder'
for filename in os.listdir(folder_path):
    if 'Co' in filename and filename.lower().endswith('.txt'):
        file_path = os.path.join(folder_path, filename)
        
        # Process the file and get arrays x and y
        x, y = process_text_file(file_path)
        
        plt.plot(x,y)
        plt.title(filename)
        plt.show()
        
        # Print or further process the data as needed
        print(f"File: {filename}")
        print(f"x: {x}")
        print(f"y: {y}")
        print()



#%% Plot good files

'''
Co-TAPP-SMe_633nm_1200grating_1200cm-11.txt
Co-TAPP-SMe_633nm_1200grating_1900cm-1_.txt
Co-TAPP-SMe_785nm_1200grating_1300cm-1_.txt
'''

file_list = ['Co-TAPP-SMe_633nm_1200grating_1200cm-11.txt',
             'Co-TAPP-SMe_633nm_1200grating_1900cm-1_.txt',
             'Co-TAPP-SMe_785nm_1200grating_1300cm-1_2.txt']

for filename in os.listdir(folder_path):
    if filename in file_list:
        file_path = os.path.join(folder_path, filename)
        
        # Process the file and get arrays x and y
        x, y = process_text_file(file_path)
        
        fig, ax = plt.subplots(1,1,figsize=[12,9])
        ax.set_xlabel('Raman Shifts (cm$^{-1}$)')
        ax.set_ylabel('Raman Intensity (cts/mW/s)')
        ax.set_title('Co-TAPP-SMe Powder Raman')
        ax.plot(x,y)
        fig.suptitle(filename)
        
        save_dir = r'C:\Users\ishaa\OneDrive\Desktop\Offline Data\2023-11-30_Co-TAPP-SMe_Powder_Raman_Plots\_'
        # plt.savefig(save_dir + filename[0:len(filename)-4] + '.svg', format = 'svg')
        # plt.close(fig)

        
        # Print or further process the data as needed
        print(f"File: {filename}")
        print(f"x: {x}")
        print(f"y: {y}")
        print()
