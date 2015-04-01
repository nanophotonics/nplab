"""
Formatting Utilities
====================
"""

def engineering_format(number, base_unit='', significant_figures=None, digits_of_precision=None):
    """Format a number into a string using SI prefixes."""
    assert not (significant_figures is not None and digits_of_precision is not None), "You may not specify both the number of digits of precision and the number of significant digits."
    if significant_figures is None and digits_of_precision is None:
        significant_figures = 3 #default to 3 significant figures
    
    incPrefixes = ['', 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
    decPrefixes = ['', 'm', 'u', 'n', 'p', 'f', 'a', 'z', 'y']
    
    if number == 0:
        return "0 "+base_unit
    else:
        exponent = int(np.floor(np.log10(np.abs(number))/3))*3 #first power-of-three exponent smaller than number
        mantissa = number / 10**exponent
        try:
            if exponent >= 0:
                prefix = incPrefixes[exponent/3]
            else:
                prefix = decPrefixes[-exponent/3]
        except IndexError:
            print "mantissa",mantissa,"exponent",exponent
            raise ValueError("The number provided was too big (or too small) to convert to an SI prefix!")
    return "%.3g %s%s" % (mantissa,prefix,base_unit)
