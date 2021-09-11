from __future__ import division

from past.utils import old_div
def wavelength_to_rgb(wavelength, gamma=0.8):

    '''This converts a given wavelength of light to an 
    approximate RGB color value. The wavelength must be given
    in nanometers in the range from 380 nm through 750 nm
    (789 THz through 400 THz).

    Based on code by Dan Bruton
    http://www.physics.sfasu.edu/astro/color/spectra.html
    
    Copied from: http://www.noah.org/wiki/Wavelength_to_RGB_in_Python
    '''

    wavelength = float(wavelength)
    if wavelength >= 380 and wavelength <= 440:
        attenuation = 0.3 + old_div(0.7 * (wavelength - 380), (440 - 380))
        R = ((old_div(-(wavelength - 440), (440 - 380))) * attenuation) ** gamma
        G = 0.0
        B = (1.0 * attenuation) ** gamma
    elif wavelength >= 440 and wavelength <= 490:
        R = 0.0
        G = (old_div((wavelength - 440), (490 - 440))) ** gamma
        B = 1.0
    elif wavelength >= 490 and wavelength <= 510:
        R = 0.0
        G = 1.0
        B = (old_div(-(wavelength - 510), (510 - 490))) ** gamma
    elif wavelength >= 510 and wavelength <= 580:
        R = (old_div((wavelength - 510), (580 - 510))) ** gamma
        G = 1.0
        B = 0.0
    elif wavelength >= 580 and wavelength <= 645:
        R = 1.0
        G = (old_div(-(wavelength - 645), (645 - 580))) ** gamma
        B = 0.0
    elif wavelength >= 645 and wavelength <= 750:
        attenuation = 0.3 + old_div(0.7 * (750 - wavelength), (750 - 645))
        R = (1.0 * attenuation) ** gamma
        G = 0.0
        B = 0.0
    else:
        R = 0.0
        G = 0.0
        B = 0.0
    R *= 255
    G *= 255
    B *= 255
    return (int(R), int(G), int(B))