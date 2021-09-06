# -*- coding: utf-8 -*-
"""
Created on Mon Sep  6 13:59:17 2021

@author: dk515, aj619, trr30
"""

"""
Class for Teledyne Lecroy T3AFG30 arbitrary function generator.
"""

from nplab.instrument.visa_instrument import VisaInstrument
#import numpy as np


class Teledyne_Lecroy_T3AFG30(VisaInstrument):
    """Interface to the T3AFG30 arbitrary function generator."""
    def __init__(self, address='USB0::0xF4EC::0xEE38::T0102C21150130::INSTR'):
        super(Teledyne_Lecroy_T3AFG30, self).__init__(address)
        self.instr.read_termination = '\n'
        self.instr.write_termination = '\n'
        self.reset()

    def reset(self):
        """Reset the instrument to its default state."""
        self.write('*RST')
        
    def set_output(self, channel, state):
        """
        Set ouput state of channels.
        :channel: 'C1' or 'C2'
        :state: 'ON' or 'OFF'
        """
        self.write(channel + ':OUTP ' + state)
        
if __name__ == '__main__':
    myT3AFG30 = Teledyne_Lecroy_T3AFG30()