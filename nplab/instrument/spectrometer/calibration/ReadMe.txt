These are some scripts for calibrating a spectrometer. They roughly work by correlating a datafile "wavelength calibration.h5" and list of known spectral lines which you measured.

You will need:
- A spectral source (e.g. Neon/Argon lamp)
- a list of spectral lines, in Angstrom separated by \n in "spectral lines.txt" file corresponding to this source
- a "wavelength calibration.h5" file containing, for each grating, a dataset with:
    - a spectrum for each motor step position
    - an attribute "steps", with all motor step positions.
    So dataset shape should be (n_steps~200, n_pixels~1600). See nplab.instrument.spectrometer.triax.trandor.take_calibration_spectra for an example.

Run manually_calibrate.py in spyder with the console graphics backed set to inline to display a subset of the calibration spectra, and manually assign the peaks to spectral positions. Each number (wl) that you enter will be assigned to the closest spectral line in "spectral lines.txt". Enter "?" to skip a peak.
Feel free to play around with the parameters in find_peaks, they may differ for your system.
This will generate 
"all_assinged_peaks_grating_x.json" and 
"all_peaks_to_assign_grating_x.json"

To use this calibration, you'll want something like
from auto_calibrate import Calibrator
calibrator = Calibrator()

This will use the manual calibration json files as a rough calibration, and use all the data/spectral lines to match each peak to its most probable spectral line, generating a full calibration.


    
