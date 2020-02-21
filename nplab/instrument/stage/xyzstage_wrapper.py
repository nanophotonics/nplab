# -*- coding: utf-8 -*-
"""
Created on Mon Jul 31 11:10:09 2017

@author: Hera
"""
from __future__ import print_function
from nplab.instrument.stage import Stage
from UltrafastRig.Equipment.Piezoconcept_micro import Piezoconcept
from nplab.instrument.stage.apt_vcp_motor import DC_APT
import numpy as np

class fake_stage(Stage):
    def move(self,a,axis = 1,relative = False):
        print(a)
    def get_position(self):
        return 0


class piezoconcept_thorlabsMSL02_wrapper(Stage):
    axis_names = ('x','y','z')
    def __init__(self,no_z = False):
        self.xy = DC_APT.get_instance()
        self.unit = 'u'
        if no_z:
            self.z = fake_stage()  
        else:
            self.z = Piezoconcept.get_instance()
        
    def get_position(self):
        return np.append(self.xy.position,self.z.position)
  #  postion = property(get_position)
    def move(self, x,axis=None, relative=False, block=True):
        """ move wrapper

        """
        print('move command' ,x,axis,relative)
        if axis == None:
            if len(x)==3:
                self.z.move(x[2],relative = relative)
                try:
                    self.xy.move(x[:2],relative = relative,block = block)
                except Exception as e:
                    print(e)
                    self.xy.move(x[:2],relative = relative,block = block)
            elif len(x)==2:
                try:
                    self.xy.move(x,relative = relative,block = block)
                except Exception as e:
                    print(e)
                    self.xy.move(x[:2],relative = relative,block = block)
        if axis in self.axis_names:
            if axis=='x' or axis=='y':
                self.xy.move(x,axis = axis,relative = relative)
            if axis == 'z':
                self.z.move(x,relative = relative)
                
                