# -*- coding: utf-8 -*-
"""
Created on Mon Sep  6 15:13:41 2021

@author: dk515, aj619, trr30
"""

"""
Class for Keysight DSOX1204A digital oscilloscope.
"""

from nplab.instrument.visa_instrument import VisaInstrument
#import numpy as np


class Keysight_DSOX1204A(VisaInstrument):
    """Interface to the DSOX1204A oscilloscope."""
    def __init__(self, address='USB0::0x2A8D::0x0386::CN60476268::0::INSTR'):
        super(Keysight_DSOX1204A, self).__init__(address)
        self.instr.read_termination = '\n'
        self.instr.write_termination = '\n'
        self.reset()

    def reset(self):
        """Reset the instrument to its default state."""
        self.write('*RST')
        
if __name__ == '__main__':
    myDSOX1204A = Keysight_DSOX1204A()