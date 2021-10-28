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
import h5py
from nplab.datafile import DataFile 
from nplab.utils.array_with_attrs import ArrayWithAttrs
from pathlib import Path
from nplab.utils.thread_utils import background_action
import time
from tqdm import tqdm
CCD_Size = 1600  # Size of ccd in pixels


 # Grating 1
 # 633 is at 6134
 # 785 is at 8500 steps 
 # so steps = 14.38wl -2790
 # rougly 5_000 steps to 10_000 steps
class Trandor(Andor):  # Andor
    ''' Wrapper class for the Triax and the andor
    '''

    def __init__(self, white_shutter=None, triax_address='GPIB0::1::INSTR', use_shifts=False, laser='_633'):
        super(Trandor, self).__init__()
        self.triax = Triax(triax_address, CCD_Size)  # Initialise triax
        self.white_shutter = white_shutter
        self.triax.ccd_size = CCD_Size
        self.use_shifts = use_shifts
        self.laser = laser
        self.metadata_property_names += ('slit_width', 'wavelengths')
        self.calibration_filepath = Path(__file__).parent / 'wavelength calibration.h5'
    
    def generate_wavelength_axis(self, use_shifts=None):

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
            return self.wavelengths
    x_axis = property(generate_wavelength_axis)

    # @property
    # def wavelengths(self):
    #     return self.Generate_Wavelength_Axis(use_shifts=False)
    @property
    def wavelengths(self):
        return range(1600)
    @property
    def slit_width(self):
        return self.triax.slit
    
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
    
    @background_action
    def take_calibration_spectra(self, step_bounds=(5_000, 10_000), steps=200):
        '''todo'''
       
        step_range = np.linspace(*step_bounds, steps)
        specs = []
        for step in tqdm(step_range):
            self.triax.motor_steps = step
            time.sleep(0.2)
            spec = self.raw_image(update_latest_frame=True)
            specs.append(spec)
        with h5py.File(self.calibration_filepath, 'w') as calibration_file:
            dset = calibration_file.create_dataset(
                f'wavelength_calibration_grating_{self.triax.grating}',
                data=specs)
            dset.attrs['steps'] = step_range


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


# setattr(AndorUI, 'Capture', Capture)


if __name__ == '__main__':
    t = Trandor()
    t.show_gui(False)
    # t.triax.show_gui(False)
    
