# -*- coding: utf-8 -*-
"""
Created on Mon Jul 03 09:23:39 2017

@author: wmd22
A scipt for creating the 32 bit listener in the 64-32 control method
"""
from __future__ import print_function
import sys
import qtpy;import nplab;from nplab.instrument.virtual_instrument import inialise_listenser
print(sys.argv)
inialise_listenser(sys.argv[1],sys.argv[2])
#python32 virtual_instrument_creation.py "nplab.instrument.camera" "DummyCamera"