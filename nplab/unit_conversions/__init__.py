# -*- coding: utf-8 -*-
"""
Created on Tue Oct 12 13:45:53 2021

@author: Eoin

The idea is to provide a nice object oriented interface to common spectroscopic
conversions. Typical use:
    >>>from nplab.unit_conversions import convert
    >>>convert.nm.to.ev(600) # 600 nm in eV
    # 1.96 eV

There is also a separate raman_convert, where all quantities other than nm are
assumed to be the raman shift from the laser
    >>>from nplab.unit_conversions import raman_convert
    >>>raman_convert.nm.to.cm(650, laser=633)
    # 412 cm^-1 : correct
    >>>convert.nm.to.cm(650)
    #15385 : absurdly high as usually convert IR wls to cm^-1.
raman_convert also has the alias rconvert.


the names of units are:
    hz: Hertz
    thz: TeraHertz
    nm: nanometers
    ev: electron Volts
    cm: inverse centimeters 

to add a unit you'll need to know its conversion to and from Hertz.  
syntax loosely inspired by https://schedule.readthedocs.io/en/
"""
from functools import wraps

from nplab.unit_conversions.raman_conversions import raman_conversions
from nplab.unit_conversions.spectroscopy_conversions import \
    spectroscopy_conversions


full_unit_names = {
    'hz': 'Hertz',
    'thz': 'TeraHertz',
    'nm': 'nanometers',
    'ev': 'electron Volts',
    'cm': 'inverse centimeters',
}


class _to:
    pass

def _conversion_factory(conversions_dict, start_unit, end_unit):
    f = conversions_dict['to_hz'][start_unit]

    @wraps(f)
    def conv(value, *args, **kwargs):
        return conversions_dict['hz_to'][end_unit](f(value, *args, **kwargs))

    conv.__doc__ = f'{full_unit_names[start_unit]} to {full_unit_names[end_unit]}'
    return conv

class Convert():
    def __init__(self, conversions):
        for start_unit in conversions['to_hz']:
            setattr(
                self, start_unit,
                To(start_unit,
                   end_units=conversions['hz_to'],
                   conversions=conversions))

class To():
    def __init__(self, start_unit, end_units, conversions):
        self.to = _to()
        for end_unit in end_units:
            setattr(self.to, end_unit,
                    _conversion_factory(
                        conversions,
                        start_unit,
                        end_unit,
                    ))


convert = Convert(spectroscopy_conversions)
raman_convert = Convert(raman_conversions)
rconvert = raman_convert

if __name__ == '__main__':
    print(convert.nm.to.cm(3000))
    print(raman_convert.nm.to.cm(700, laser=633))
