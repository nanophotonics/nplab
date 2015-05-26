# -*- coding: utf-8 -*-
"""
Created on Tue May 26 08:45:40 2015

@author: rwb27
"""

from nplab import ArrayWithAttrs
from nplab.utils.array_with_attrs import ensure_attrs

#define the prefixes here, with tuples containing 3 elements:
#exponent, abbreviation (text), symbol (for graphs, etc. in laTeX/MathJax)
prefixes = {
                'peta': (15, 'P', 'P'),
                'tera': (12, 'T', 'T'),
                'giga': (9, 'G', 'G'),
                'mega': (6, 'M', 'M'),
                'kilo': (3, 'k', 'k'),
#                '': (0, '', ''),
                'deci': (-1, 'd', 'd'),
                'centi': (-2, 'c', 'c'),
                'milli': (-3, 'm', 'm'),
                'micro': (-6, 'u', '\mu'),
                'nano': (-9, 'n', 'n'),
                'pico': (-12, 'p', 'p'),
                'femto': (-15, 'f', 'f'),
                'atto': (-18, 'a', 'a'),
                }
                
# units are defined by abbreviation (text), symbol (for graphs etc.) and
# optionally a base unit tuple of (coefficient, unit_string).
units = {
                'metre': ('m', 'm', None),
                'gram': ('g', 'g', None),
                'second': ('s', 's', None),
                'Angstrom': ('A', 'A', (0.1, 'nanometre')),
                'micron': ('um', '\mu m', (1, 'micrometre')),
                'Ohm': ('Ohm', '\omega', None),
 #               '': ('', '', None),
        }
        
def array_with_units(obj, units):
    """Bundle an object as an ArrayWithAttrs having a "units" attribute."""
    ret = ensure_attrs(obj)
    ret.attrs.create('units', units)
    return ret
    
def extract_units(obj, default=None, warn=False):
    """Return the unparsed units string from an object"""
    try:
        return obj.attrs.get('units')
    except AttributeError as e:
        if warn:
            print "Warning: no units found on " + str(obj)
        if default is not None:
            return default
        else:
            raise e
            
def parse_units(unit_string):
    """Take a unit string and return a (prefix,unit) tuple."""
    prefix, unit = None, None
    for k, v in units.iteritems():
        if unit_string == k:
            unit = k
            unit_string = ''
            break
    for k, v in prefixes.iteritems():
        if unit_string.startswith(k):
            prefix = k
            unit_string = unit_string[len(prefix):] #remove prefix once parsed
            break
    for k, v in units.iteritems():
        if unit_string.endswith(k):
            unit = k
            unit_string = unit_string[:-len(unit)]
            break
    if prefix is None:
        for k, v in prefixes.iteritems():
            if unit_string.startswith(v[1]):
                prefix = k
                unit_string = unit_string[len(v[1]):] #remove prefix once parsed
                break
    if unit is None:
        for k, v in units.iteritems():
            if unit_string.endswith(v[1]):
                unit = k
                unit_string = unit_string[:-len(v[1])]
                break
    return prefix, unit

def to_base_units(unit_string):
    """Given a unit, convert it to standard form (e.g. angstroms/microns become metre-derivatives)"""
    prefix, unit = parse_units(unit_string)
    raise NotImplementedError("TODO: implement this")
    
    
def convert_units(obj, dest_units):
    """Return a copy of obj in the required units."""
    from_units = parse_units(extract_units(obj))
    to_units = parse_units(dest_units)
    