import pyjisa.autoload
import numpy as np

from nplab.measurement.action import *
from h5py import Group

from jisa.devices.spectrometer import Spectrometer
from jisa.devices.camera import Camera

class TakeSpectra(H5Action):

    def __init__(self, description): 
        super().__init__("Take Spectra", description)

    # =====[ Measurement Parameters ]================================================================ 
    count       = Parameter(name = "Number of Spectra", defaultValue = 5,      range = (0, None))
    delay       = Parameter(name = "Delay Time",        defaultValue = 500,    type  = Type.TIME)
    integration = Parameter(name = "Integration Time",  defaultValue = 100e-3, type  = Type.SCIENTIFIC)

    # =====[ Instruments ]===========================================================================
    spectrometer = Instrument(name = "Spectrometer",      type = Spectrometer, required = True)
    camera       = Instrument(name = "Microscope Camera", type = Camera,       required = False)


    # =====[ Main Method ]===========================================================================
    def main(self, data: Group):

        self.spectrometer.setIntegrationTime(self.integration)

        if self.spectrometer.isAcquiring():
            self.triggered = False
        else:
            self.triggered = True
            self.spectrometer.startAcquisition()

        spectra = data.create_group("Spectra")

        if self.camera is not None:
            snapshots = data.create_group("Snapshots")

        message = r"Taking spectrum %d." if self.camera is None else r"Taking spectrum and snapshot %d"

        for i in range(self.count):

            self.message(type = MessageType.INFO, message = message % i)

            spectrum = self.spectrometer.getSpectrum()
            ds       = self.writeSpectrum(spectrum, spectra, "Spectrum %d" % i)

            ds.attrs["Integration Time [s]"] = self.integration

            if self.camera is not None:
                self.writeFrame(self.camera.getFrame(), snapshots, "Snapshot %d" % i)


            self.sleep(self.delay)


    # =====[ On Finish ]============================================================================
    def finish(self, data: Group = None):
        if self.triggered:
            self.spectrometer.stopAcquisition()