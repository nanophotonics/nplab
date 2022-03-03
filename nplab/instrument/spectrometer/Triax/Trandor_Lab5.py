"""
jpg66
"""

from nplab.instrument.spectrometer.Triax.trandor import Trandor
from nplab.instrument.camera.Andor import AndorUI

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
    from triax_calibration.auto_calibrate import Calibrator
    t = Trandor(calibrator=Calibrator(Trandor.CCD_size))
    t.show_gui(False)
    t.triax.show_gui(False)
