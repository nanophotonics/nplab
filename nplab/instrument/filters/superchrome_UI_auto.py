# -*- coding: utf-8 -*-
"""
Created on Thu Aug  8 08:53:24 2019

@author: fo263
"""
from __future__ import division

from builtins import str
from builtins import object
from past.utils import old_div
from pywinauto.application import Application
import numpy as np


class SuperChromeUIAuto(object):
    """ A class for controlling the fianium superchrome filter using UI automation
    """
    def __init__(self):
        self.filter_app = Application().connect(path = r"C:\Program Files (x86)\Fianium\SuperChrome\SuperChromeTest.exe")
        self.filter_diag = self.filter_app.TestDualVariableFilter
        
    def select_filter(self, filter_str):
        
        if filter_str.lower() == 'filter1':
            self.filter_diag.Filter1.click()
            self.filter_diag.InBeamPath.click()
        else: 
            if filter_str.lower() == 'filter2':
                self.filter_diag.Filter2.click()
                self.filter_diag.InBeamPath.click()
    
    def move_filter_pos(self, filter_str = 'Filter2', filter_pos = 5800):
        
        if filter_str.lower() == 'filter1' or filter_str.lower() == 'filter2':
            self.select_filter(filter_str)
            self.filter_diag.Edit6.type_keys(str(filter_pos))
            self.filter_diag.Apply.click()
        else:
            display('Invalid filter name')
    
    def move_out_of_beam(self, filter_str = 'Filter2'):
        
        if filter_str.lower() == 'filter1':
            self.filter_diag.Filter1.click()
            self.filter_diag.OutBeamPath.click()
            self.filter_diag.Apply.click()
            
        else: 
            if filter_str.lower() == 'filter2':
                self.filter_diag.Filter2.click()
                self.filter_diag.OutBeamPath.click()
                self.filter_diag.Apply.click()
            else: 
                display('Invalid filter name')
                
    def move_filter_wavelength(self, filter_str = 'Filter2', cut_off = 650):
        

        if filter_str.lower() == 'filter2':
            self.lookup_table = np.loadtxt(r'E:\OneDrive - University Of Cambridge\Ultrafast Raman Rig\fo263\filter2_lookup_table.txt')
        if filter_str.lower() == 'filter1':
            display('Filter1 is not yet calibrated. Sorry!')
            return
        
        filter_pos = old_div(np.abs(self.lookup_table - cut_off).argmin(),2)
        self.move_filter_pos(filter_str, self.lookup_table[int(filter_pos)][0])
        
        

        
 

        
        
        
            
            
        