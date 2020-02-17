# -*- coding: utf-8 -*-
"""
Created on Tue Nov 12 11:50:27 2019

@author: Eoin Elliott

A module for easy access to example data for testing analysis codes. 
Numpy files are loaded here
access the data by 

nplab.analysis.example_data.SERS_and_shifts 

for example.
"""

import numpy as np
import os


# Example SERS spectrum (BPT, 785nm laser, centered at 785nm)
SERS_and_shifts =  np.load(os.path.join(os.path.dirname(__file__), 'example_SERS_and_shifts.npy'))


#
