# -*- coding: utf-8 -*-
"""
Created on Sat Feb 11 17:28:01 2023

for an np array data_array find the inde whose value data_array[index] is closest 

@author: jb2444
"""
import numpy as np

def find_index(data_array, number):    
    result=np.where(np.abs(data_array-number) == np.min(np.abs(data_array-number)))
    return result