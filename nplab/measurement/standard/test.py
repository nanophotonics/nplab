import pyjisa.autoload
import numpy as np

from nplab.measurement.action import *
from h5py import Group

from jisa.devices.spectrometer import Spectrometer
from jisa.devices.camera import Camera

class TakeSpectra(H5Action):

    # Define parameters we want to ask the user for
    count        = Parameter(name = "Number of Spectra", defaultValue = 5,      range = (0, None))
    delay        = Parameter(name = "Delay Time",        defaultValue = 500,    type  = Type.TIME)
    integration  = Parameter(name = "Integration Time",  defaultValue = 100e-3, type  = Type.SCIENTIFIC)

    spectrometer = Instrument(name = "Spectrometer", type = Spectrometer)

    def __init__(self, description): 

        super().__init__("Take Spectra", description)
        self.spectra = []


    def main(self, data: Group):

        self.spectra.clear()
        self.spectrometer.setIntegrationTime(self.integration)

        for i in range(self.count):

            self.infoMessage("Taking spectrum %d / %d." % (i + 1, self.count))

            spectrum = self.spectrometer.getSpectrum()
            self.spectra.append(spectrum)

            self.sleep(self.delay)


    def finish(self, data: Group = None):
        
        for (i, spectrum) in enumerate(self.spectra):

            self.message("Writing spectrum %d / %d." % (i + 1, self.count))
            self.writeSpectrum(spectrum, data, "Spectrum %d" % i)
