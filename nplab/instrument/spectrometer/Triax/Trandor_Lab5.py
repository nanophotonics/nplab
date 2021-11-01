"""
jpg66
"""

from nplab.instrument.spectrometer.Triax import Triax
import numpy as np
from nplab.instrument.camera.Andor import Andor, AndorUI
import h5py
from pathlib import Path
from nplab.utils.thread_utils import background_action
import time
from tqdm import tqdm


# Grating 1
# 633 is at 6134
# 785 is at 8500 steps
# so steps = 14.38wl -2790
# rougly 5_000 steps to 10_000 steps
class Trandor(Andor):  # Andor
    ''' Wrapper class for the Triax and the andor
    '''
    CCD_size = 1600  # Size of ccd in pixels

    def __new__(cls, *args, **kwargs):
        cls.metadata_property_names += ('slit_width', 'wavelengths')
        return super(Trandor, cls).__new__(cls)  #, *args, **kwargs)

    def __init__(self,
                 white_shutter=None,
                 triax_address='GPIB0::1::INSTR',
                 use_shifts=False,
                 laser='_633',
                 calibrator=None):
        super(Trandor, self).__init__()
        self.triax = Triax(triax_address,
                           CCD_size=self.CCD_size,
                           calibrator=calibrator)  # Initialise triax
        self.white_shutter = white_shutter
        self.use_shifts = use_shifts
        self.laser = laser
        self.calibration_filepath = Path(
            __file__).parent / 'wavelength calibration.h5'

    def get_x_axis(self, use_shifts=None):

        if use_shifts is None:
            use_shifts = self.use_shifts
        if use_shifts:
            if self.laser == '_633':
                centre_wl = 632.8
            elif self.laser == '_785':
                centre_wl = 784.81
            wavelengths = np.array(self.triax.wavelength_axis[::-1])
            return (1. / (centre_wl * 1e-9) - 1. / (wavelengths * 1e-9)) / 100
        else:
            return self.wavelengths

    x_axis = property(get_x_axis)

    @property
    def wavelengths(self):
        return self.x_axis

    @property
    def wavelengths(self):
        return range(self.CCD_size)

    @property
    def shifts(self):
        return self.get_x_axis(use_shifts=True)

    @property
    def slit_width(self):
        return self.triax.slit

    @background_action
    def take_calibration_spectra(self, step_bounds=(3500, 7000), steps=200):
        '''todo'''

        step_range = np.linspace(*step_bounds, steps)
        specs = []
        for step in tqdm(step_range):
            self.triax.motor_steps = step
            time.sleep(0.1)
            spec = self.raw_image(update_latest_frame=True)
            specs.append(spec)
        with h5py.File(self.calibration_filepath, 'a') as calibration_file:
            if (name := f'wavelength_calibration_grating_{self.triax.grating}') in calibration_file:
                del calibration_file[name]
            dset = calibration_file.create_dataset(
                name,
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
    from triax_calibration.auto_calibrate import Calibrator
    t = Trandor(calibrator=Calibrator())
    t.show_gui(False)
    # t.triax.show_gui(False)
