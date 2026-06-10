import pyjisa.autoload
import pyqtgraph as pg
from qtpy.QtCore import Signal

from typing import Generic, List, Tuple, Callable, TypeVar
from jisa.devices.spectrometer import Spectrometer as JSpectrometer, Spectrograph as JSpectrograph
from jisa.devices.spectrometer.spectrum import Spectrum
from qtpy.QtWidgets import QVBoxLayout, QWidget

from nplab.instrument import Instrument
from nplab.instrument.spectrometer import Spectrometer
from nplab.instrument.spectrometer.fastspectrometer.gui import FastSpectrometerGUI, FastSpectrometerPreviewGUI

S = TypeVar("S", bound=JSpectrometer)

class FastSpectrometer(Instrument, Generic[S]):

    def __init__(self, spectrometer: S):

        super().__init__()

        self.spectrometer = spectrometer

        self.previews: List[FastSpectrometerPreviewGUI] = []


    def getSpectrometer(self) -> S:
        return self.spectrometer
    

    def get_qt_ui(self, control_only=False, display_only=False):
        return FastSpectrometerGUI(self.spectrometer, self, not control_only)
    
    def get_control_widget(self):
        return self.get_qt_ui(control_only=True)
    
    def updateSpectrum(self, spectrum: Spectrum):

        for preview in self.previews:
            preview.update(spectrum)


    def get_preview_widget(self):
        preview = FastSpectrometerPreviewGUI(self.spectrometer)
        self.previews.append(preview)
        return preview

        
