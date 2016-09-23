"""
NPLab
=====
This module contains lots of classes and functions to support the
NanoPhotonics group's lab work.
"""

__author__ = 'alansanders,rwb27'
__all__ = []
__version__ = '0.1-dev'

from nplab.datafile import current as current_datafile, close_current as close_current_datafile
from nplab.utils.array_with_attrs import ArrayWithAttrs
from nplab.utils.decorators import inherit_docstring
from nplab.utils.log import log
