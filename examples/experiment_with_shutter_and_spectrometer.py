# -*- coding: utf-8 -*-
"""
Example experiment using a shutter and a spectrometer

This demonstrates how to carry out an experiment that runs for a while in 
the background, without locking up the UI.

rwb27, May 2016

"""

import nplab
import nplab.utils.gui
from nplab.experiment import Experiment, ExperimentStopped
from nplab.instrument.shutter import Shutter
from nplab.instrument.spectrometer import Spectrometer
from nplab.ui.ui_tools import QuickControlBox, UiTools
from nplab.utils.gui import (QtCore, QtGui, QtWidgets, get_qt_app, show_guis,
                             uic)
from nplab.utils.notified_property import DumbNotifiedProperty


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

class DumbIrradiationExperiment_Gui(QtWidgets.QMainWindow, UiTools):
    """
    Import and editing of Pump probe gui including the replacement of widgets and formating of buttons
    """
    #, lockin, XYstage, Zstage, spectrometer, stepper,
    def __init__(self, spec,shutter, experiment, parent=None):
        super(DumbIrradiationExperiment_Gui, self).__init__(parent)
        #Load ui code
        uic.loadUi('DumbIrradiationExperimentGui.ui', self)
        
        #grabbing the current H5PY and intiating the data_browser
        self.data_file = nplab.current_datafile()
        self.data_file_tab = self.replace_widget(self.DataBrowser_tab_layout,self.DataBrowser_widget,self.data_file.get_qt_ui())
        
        #setup spectrometer tab gui and widget
        self.spectrometer = spec
        self.Spectrometer_widget = self.replace_widget(self.Spectrometer_Layout,self.Spectrometer_widget,self.spectrometer.get_qt_ui(display_only = True))
        self.spectrometer_tab = self.replace_widget(self.Spectrometer_tab_Layout,self.Spectrometer_tab_widget,self.spectrometer.get_qt_ui())
        
        #Setting up stepper and Lockin widget 
            # Display
        self.Experiment = experiment
        self.Experiment_controls_widget = self.replace_widget(self.Main_layout,self.Experiment_controls_widget,self.Experiment.get_qt_ui())
            #Shutter control widget
        self.shutter = shutter
        self.StageControls_widget = self.replace_widget(self.Main_layout,self.shutter_controls_widget,self.shutter.get_qt_ui())


    
            
if __name__ == '__main__':
    from nplab.instrument.shutter import DummyShutter
    from nplab.instrument.spectrometer import DummySpectrometer    
    
    spectrometer = DummySpectrometer()
    shutter = DummyShutter()
    
    experiment = DumbIrradiationExperiment()
    
    df = nplab.current_datafile()
    
#    show_guis([spectrometer, shutter, experiment, df])
    app = get_qt_app()
    gui = DumbIrradiationExperiment_Gui(spec = spectrometer, shutter = shutter, experiment = experiment)
    gui.show()    
