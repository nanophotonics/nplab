# -*- coding: utf-8 -*-
"""
Unit support for nplab
======================

Sometimes it's really useful to check the units on data, for example when using
translation stages (which can be very sensitive to being told to move 1000nm if
you only wanted to move 1um...)

@author: rwb27
"""
from __future__ import division
from __future__ import print_function

from builtins import str
from past.utils import old_div
from nplab import ArrayWithAttrs
from nplab.utils.array_with_attrs import ensure_attrs
import pint

ureg = pint.UnitRegistry() #this should always be where the unit registry comes from

def get_unit_string(obj, default=None, warn=False, fail=False):
    """Return a string representation of an object's units.
    
    This function returns obj.attrs.get('units') with no processing, or it
    converts the units of a Quantity object to a string and returns that.  The
    output should be suitable for saving to an HDF5 file."""
    try:
        return obj.attrs.get('units') #this works for things with attrs
    except AttributeError:
        try:
            return str(obj.units) #this works for Quantities
        except:
            if warn:
                print("Warning: no unit string found on " + str(obj))
            if fail:
                raise ValueError("No unit information was found on " + str(obj))
            return default

def unit_to_string(quantity):
    """Converts a quantity (used for units) to a string for saving or display.
    
    The only thing this does over and above str(quantity) is stripping the
    initial "1 " where the magnitude is unity.
    """
    if quantity.magnitude == 1:
        return str(quantity.units)
    else:
        return str(quantity)
    
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
            unit_string = get_unit_string(obj, fail=True) #look for a units attribute
            return ureg(unit_string) #convert to a pint unit
    except:
        if warn:
            print("Warning: no units found on " + str(obj))
        if default is not None:
            return ensure_unit(default)
        else:
            raise ValueError("No unit information could be found on " + str(obj) + " (it should either have an attrs dict with a 'units' attribute, or be a Quantity).")
        
        
def array_with_units(obj, units):
    """Bundle an object as an ArrayWithAttrs having a "units" attribute."""
    ret = ensure_attrs(obj)
    ret.attrs.create('units', str(units))
    return ret


def ensure_unit(obj):
    """Ensure an object is a unit (i.e. a pint quantity).
    
    Strings will be converted to units if possible, and UnitsContainers will be
    turned back into Quantities."""
    if isinstance(obj, ureg.Quantity):
        return obj #if it's a quantity, we're good.
    else:
        return ureg(str(obj)) #otherwise, convert to string and parse

def convert_quantity(obj, dest_units, default=None, warn=True, return_quantity=False):
    """Return a copy of obj in the required units."""
    if ensure_unit(dest_units)==get_units(obj, default=default, warn=False):
        return obj #make sure objects are returned unchanged if units match
    if isinstance(obj, ureg.Quantity):
        q = obj
    else:
        #convert the object to a Quantity
        fu = get_units(obj, default=default, warn=warn)
        q = old_div(ureg.Quantity(obj, fu.units),fu.magnitude)
    du = ensure_unit(dest_units)
    rq = old_div(q.to(du.units), du.magnitude)
    if return_quantity:
        return rq
    else:
        return rq.magnitude #this should return an array/whatever
    