# -*- coding: utf-8 -*-
"""
Example experiment using a shutter and a spectrometer

This demonstrates how to carry out an experiment that runs for a while in 
the background, without locking up the UI.

rwb27, May 2016

"""

import nplab
from nplab.instrument.spectrometer import Spectrometer
from nplab.instrument.shutter import Shutter
from nplab.experiment import Experiment, ExperimentStopped
from nplab.utils.notified_property import DumbNotifiedProperty
from nplab.ui.ui_tools import QuickControlBox
from nplab.utils.gui import show_guis

class DumbIrradiationExperiment(Experiment):
    """An example experiment that opens and closes a shutter, and takes spectra."""
    irradiation_time = DumbNotifiedProperty(1.0)
    wait_time = DumbNotifiedProperty(0.5)
    log_to_console = True
    
    def __init__(self):
        super(DumbIrradiationExperiment, self).__init__()
        
        self.shutter = Shutter.get_instance()
        self.spectrometer = Spectrometer.get_instance()
        
    def run(self):
        try:
            dg = self.create_data_group("irradiation_%d")
            while True:
                self.log("opening shutter")
                self.shutter.open_shutter()
                self.wait_or_stop(self.irradiation_time)
                self.shutter.close_shutter()
                self.log("closed shutter")
                self.wait_or_stop(self.wait_time)
                spectrum = self.spectrometer.read_spectrum(bundle_metadata=True)
                print spectrum.attrs.keys()
                dg.create_dataset("spectrum_%d", data=spectrum)
        except ExperimentStopped:
            pass #don't raise an error if we just clicked "stop"
        finally:
            self.shutter.close_shutter() #close the shutter, important if we abort
            
    def get_qt_ui(self):
        """Return a user interface for the experiment"""
        gb = QuickControlBox("Irradiation Experiment")
        gb.add_doublespinbox("irradiation_time")
        gb.add_doublespinbox("wait_time")
        gb.add_button("start")
        gb.add_button("stop")
        gb.auto_connect_by_name(self)
        return gb
            
if __name__ == '__main__':
    from nplab.instrument.spectrometer import DummySpectrometer
    from nplab.instrument.shutter import DummyShutter    
    
    spectrometer = DummySpectrometer()
    shutter = DummyShutter()
    
    experiment = DumbIrradiationExperiment()
    
    df = nplab.current_datafile()
    
    show_guis([spectrometer, shutter, experiment, df])
