"""
jpg66
"""
from __future__ import division
from __future__ import print_function

from builtins import input
from builtins import str
from past.utils import old_div
from nplab.instrument.spectrometer.Triax import Triax
import numpy as np
from nplab.instrument.camera.Andor import Andor, AndorUI
import types
import future


CCD_Size = 1600  # Size of ccd in pixels

# Make a deepcopy of the andor capture function, to add a white light shutter close command to if required later
# Andor_Capture_Function=types.FunctionType(Andor.capture.__code__, Andor.capture.__globals__, 'Unimportant_Name',Andor.capture.__defaults__, Andor.capture.__closure__)


class Trandor(Andor):  # Andor
    ''' Wrapper class for the Triax and the andor
    '''

    def __init__(self, white_shutter=None, triax_address='GPIB0::1::INSTR', use_shifts=False, laser='_633'):
        print('Triax Information:')
        super(Trandor, self).__init__()
        self.triax = Triax(triax_address, CCD_Size)  # Initialise triax
        self.white_shutter = white_shutter
        self.triax.ccd_size = CCD_Size
        self.use_shifts = use_shifts
        self.laser = laser

        print('Current Grating:'+str(self.triax.Grating()))
        print('Current Slit Width:'+str(self.triax.Slit())+'um')
        self.metadata_property_names += ('slit_width', 'wavelengths')

    def Grating(self, Set_To=None):
        return self.triax.Grating(Set_To)

    def Generate_Wavelength_Axis(self, use_shifts=None):

        if use_shifts is None:
            use_shifts = self.use_shifts
        if use_shifts:
            if self.laser == '_633':
                centre_wl = 632.8
            elif self.laser == '_785':
                centre_wl = 784.81
            wavelengths = np.array(self.triax.Get_Wavelength_Array()[::-1])
            return (1./(centre_wl*1e-9) - 1./(wavelengths*1e-9))/100
        else:
            return self.triax.Get_Wavelength_Array()[::-1]
    x_axis = property(Generate_Wavelength_Axis)

    @property
    def wavelengths(self):
        return self.Generate_Wavelength_Axis(use_shifts=False)

    @property
    def slit_width(self):
        return self.triax.Slit()

    def Test_Notch_Alignment(self):
        Accepted = False
        while Accepted is False:
            Input = input(
                'WARNING! A slight misalignment of the narrow band notch filters could be catastrophic! Has the laser thoughput been tested? [Yes/No]')
            if Input.upper() in ['Y', 'N', 'YES', 'NO']:
                Accepted = True
                if len(Input) > 1:
                    Input = Input.upper()[0]
        if Input.upper() == 'Y':
            print('You are now free to capture spectra')
            self.Notch_Filters_Tested = True
        else:
            print('The next spectrum capture will be allowed for you to test this. Please LOWER the laser power and REDUCE the integration time.')
            self.Notch_Filters_Tested = None

    def Set_Center_Wavelength(self, wavelength):
        ''' backwards compatability with lab codes that use trandor.Set_Center_Wavelength'''
        self.triax.Set_Center_Wavelength(wavelength)

    def take_calibration_spectra(self):
        pass


def Capture(_AndorUI):
    if _AndorUI.Andor.white_shutter is not None:
        isopen = _AndorUI.Andor.white_shutter.is_open()
        if isopen:
            _AndorUI.Andor.white_shutter.close_shutter()
        _AndorUI.Andor.raw_image(update_latest_frame=True)
        if isopen:
            _AndorUI.Andor.white_shutter.open_shutter()
    else:
        _AndorUI.Andor.raw_image(update_latest_frame=True)


setattr(AndorUI, 'Capture', Capture)


if __name__ == '__main__':
    t = Trandor()
    t.show_gui(False)
    # t.triax.show_gui(False)
    
