# -*- coding: utf-8 -*-
"""
Created on Tue Oct 27 13:09:09 2015

@author: rwb27
"""
from __future__ import print_function

import nplab
# import numpy as np
# import matplotlib.pyplot as plt
from numpy.random import random
from nplab.ui.data_renderers import suitable_renderers

if __name__ == '__main__':
    df = nplab.current_datafile()
    group = df.create_group("test_items")
    
    d = group.create_dataset("1d_generic",data=random((100)))
    print(suitable_renderers(d))
    d = group.create_dataset("2d_generic",data=random((100,100)))
    print(suitable_renderers(d))
    d = group.create_dataset("3d_rgb",data=random((100,100,3)))
    print(suitable_renderers(d))
    d = group.create_dataset("3d_generic",data=random((100,100,100)))
    print(suitable_renderers(d))
    
    df.show_gui(block=True)
    df.close()