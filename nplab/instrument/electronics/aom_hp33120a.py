# -*- coding: utf-8 -*-
"""
Created on Tue Aug  1 16:59:02 2023

@author: pk525
"""

from nplab.instrument.electronics.aom import AOM as Aom
from nplab.instrument.electronics.hp_33120a_signal_generator_serial import SignalGenerator

class AOM_HP33120a(Aom):
    def __init__(self, port="COM1", *args, **kwargs):
        self.fgen_serial = SignalGenerator(port)
        self.fgen_serial.function = "dc"
        self.fgen_serial.offset = 1
        
        
    def Power(self, Fraction=None):
         
        if Fraction is None:
            return float(self.fgen_serial.offset)
        else:
            if Fraction<0:
                Fraction=0.
            if Fraction>1:
                Fraction=1.
            self.fgen_serial.offset = Fraction
            
    def Get_Power(self):
        return float(self.fgen_serial.offset)
