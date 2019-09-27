# -*- coding: utf-8 -*-
"""
Created on Fri Aug 04 13:52:33 2017

@author: Hera
"""

from ctypes import *
from nplab.instrument import Instrument
import os

class SuperChrome(Instrument):
    """ A class for controlling the fianium superchrome filter
    """
    def __init__(self):
#        self.dll = cdll.LoadLibrary(os.path.dirname(__file__) + "\\SuperChromeSDK")
#        self.dll.InitialiseDll(windll.kernel32._handle)
#        self.dll = windll

        self.dll = cdll.LoadLibrary(r'C:\Users\Hera\Documents\GitHub\nplab\nplab\instrument\filters' + "\\SuperChromeSDK.dll")
    def init(self):
        self.dll.InitialiseDll(windll.kernel32._handle)
        self.dll = windll