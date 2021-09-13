"""

"""
from nplab.instrument.stage import Stage
import numpy as np


class XY_ZWrapper(Stage):
    axis_names = ('x', 'y', 'z')
    
    def __init__(self, XY, Z, unit='u'):
        self.XY = XY
        self.Z = Z
        super().__init__(unit=unit)
        
    
    def get_position(self, axis=None):
       if axis is  None:
           return np.append(self.XY.position, self.Z.position)
       elif axis in self.axis_names:
           if axis in 'xy':
               return self.XY.get_position(axis=axis)
           elif axis == 'z':
               return self.Z.get_position()
    
    def move(self, x, axis=None, relative=False):
        """ move wrapper """
        if axis is None:
            self.XY.move(x[:2], relative=relative)
            if len(x) == 3:
                self.Z.move(x[2], relative=relative)
               
        elif axis in self.axis_names:
            if axis in 'xy':
                self.XY.move(x, axis=axis, relative=relative)
            elif axis == 'z':
                self.Z.move(x, relative=relative)
                