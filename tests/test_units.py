# -*- coding: utf-8 -*-
"""
Created on Tue May 26 16:11:56 2015

@author: rwb27
"""

import numpy as np
import pytest

import nplab
import nplab.utils.units as units
from nplab.utils.units import (array_with_units, convert_quantity, ensure_unit,
                               get_unit_string, get_units, unit_to_string)


def test_array_with_attrs_init():
    a = nplab.ArrayWithAttrs(np.array([1,2,3,4,5]))
    a.attrs.create('foo',142)
    a.attrs.modify('foo',98)
    assert a.attrs.get('foo')==98
    assert isinstance(a, np.ndarray)
    assert isinstance(a[2:4], nplab.ArrayWithAttrs)
    
def test_array_with_attrs_casting():
    n = np.array(10)
    b = n.view(nplab.ArrayWithAttrs)
    assert isinstance(b, np.ndarray)
    assert isinstance(b, nplab.ArrayWithAttrs)
    assert b==10
    
def test_get_unit_string():
    a = nplab.ArrayWithAttrs(np.array([1,2,3,4,5]),attrs={'units':'um/s'})
    q = units.ureg('um/second')
    assert get_unit_string(a)=='um/s'
    assert get_unit_string(q)=='micrometer / second'
    assert get_unit_string(10, default='foo') == 'foo'
    with pytest.raises(ValueError):
        get_unit_string(10,fail=True)
    
def test_get_units():
    a = nplab.ArrayWithAttrs(np.array([1,2,3,4,5]),attrs={'units':'um/s'})
    q = units.ureg('um/second')
    assert get_units(a)==units.ureg('um/s')
    assert get_units(q)==units.ureg('um/s')
    assert get_units(10,default='um/s')==units.ureg('um/s')
    
def test_get_units_missing():
    with pytest.raises(ValueError):
        get_units(10)
    
def test_unit_to_string_unity():
    q = units.ureg('um/second')
    assert unit_to_string(q) == 'micrometer / second'
    
def test_unit_to_string():
    q = units.ureg('7 um/second')
    assert unit_to_string(q) == '7.0 micrometer / second'
    
def test_array_with_units():
    a = array_with_units([1,2,3],'V/nm')
    assert get_units(a) == ensure_unit('V/nm')
    assert get_unit_string(a) == 'V/nm'
    
def test_convert_quantity():
    a = nplab.ArrayWithAttrs(np.array(0.1),attrs={'units':'um'})
    q = units.ureg('0.1 um')
    na = np.array(0.1)
    assert convert_quantity(a,'nm') == 100
    assert convert_quantity(q,'nm') == 100
    with pytest.raises(ValueError):
        convert_quantity(na, 'nm')
    assert convert_quantity(na, 'nm', default='um') == 100
    assert convert_quantity(0.1, 'nm', default='um') == 100
    
def test_ensure_unit():
    assert ensure_unit('um/s')==units.ureg('micrometer/second')
    assert isinstance(ensure_unit('um/s'), units.ureg.Quantity)
    assert isinstance(ensure_unit(units.ureg('um/s').units), units.ureg.Quantity)
