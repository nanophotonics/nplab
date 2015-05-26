# -*- coding: utf-8 -*-
"""
Created on Tue May 26 08:45:40 2015

@author: rwb27
"""

from nplab import ArrayWithAttrs
from nplab.utils.array_with_attrs import ensure_attrs
import pint

ureg = pint.UnitRegistry()

def get_unit_string(obj, default=None, warn=False, fail=False):
    """Return a string representation of an object's units.
    
    This function returns obj.attrs.get('units') with no processing, or it
    converts the units of a Quantity object to a string and returns that.  The
    output is suitable for saving to an HDF5 file."""
    try:
        return obj.attrs.get('units') #this works for things with attrs
    except AttributeError:
        try:
            return str(obj.units) #this works for Quantities
        except:
            if warn:
                print "Warning: no unit string found on " + str(obj)
            if fail:
                raise ValueError("No unit information was found on " + str(obj))
            return default
    
def get_units(obj, default=None, warn=False):
    """Return the units from an object as a pint Quantity.
    
    The object can be either an ArrayWithAttrs (i.e. obj.attrs.get('units') is
    a string with the units) or a pint Quantity object.  In both cases, we
    return a pint Quantity object.  If the input was a Quantity, the object
    will have a magnitude of one, while if the input is an array it's possible
    for the magnitude not to be one (this allows arrays to be saved in odd
    units, like "100 nm" which can be useful if it's in camera pixels, for
    example."""

    try:
        if isinstance(obj, ureg.Quantity):
            return ureg.Quantity(1, obj.units) #if we have a Quantity, return its units
        else:
            unit_string = get_unit_string(obj) #look for a units attribute
            return ureg(unit_string) #convert to a pint unit
    except AttributeError as e:
        if warn:
            print "Warning: no units found on " + str(obj)
        if default is not None:
            return default
        else:
            raise e
        
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
    