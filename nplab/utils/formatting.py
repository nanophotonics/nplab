"""
Formatting Utilities
====================
"""
from __future__ import division
from __future__ import print_function

from past.utils import old_div
import numpy as np


def engineering_format(number, base_unit='', significant_figures=None, digits_of_precision=None,
                       print_errors=False):
    """Format a number into a string using SI prefixes."""
    assert not (significant_figures is not None and digits_of_precision is not None), "You may not specify both the number of digits of precision and the number of significant digits."
    if significant_figures is None and digits_of_precision is None:
        digits_of_precision = 3 #default to 3 significant figures
    
    incPrefixes = ['', 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
    decPrefixes = ['', 'm', 'u', 'n', 'p', 'f', 'a', 'z', 'y']
    
    if number == 0:
        return "0 "+base_unit
    else:
        exponent = int(np.floor(old_div(np.log10(np.abs(number)),3)))*3 #first power-of-three exponent smaller than number
        mantissa = float(number) / 10**exponent
        try:
            if exponent >= 0:
                prefix = incPrefixes[old_div(exponent,3)]
            else:
                prefix = decPrefixes[old_div(-exponent,3)]
        except IndexError:
            if print_errors:
                print("mantissa",mantissa,"exponent",exponent)
            raise ValueError("The number provided was too big (or too small) to convert to an SI prefix!")
    return "%.{0}g %s%s".format(digits_of_precision) % (mantissa,prefix,base_unit)


if __name__ == '__main__':
    print(engineering_format(2.0001e-6, base_unit='m', significant_figures=None, digits_of_precision=6))