# -*- coding: utf-8 -*-
"""
Created on Jan 15 10:23:36 2019

@author: Hera
"""
#import nplab.datafile
from nplab.instrument.camera.Andor import Andor
from nplab.instrument.spectrometer.shamrock import Shamrock
#from nplab.instrument.spectrometer.shamdor import Shamdor
from nplab.instrument.spectrometer.seabreeze import OceanOpticsSpectrometer
#import arduinoLab3
#from nplab.instrument.light_sources.matchbox_laser import MatchboxLaser

import nplab
import nplab.utils.gui 
import nplab.datafile as datafile
#from nplab.instrument.spectrometer import Spectrometer
from nplab.experiment import Experiment, ExperimentStopped
from nplab.utils.notified_property import DumbNotifiedProperty, NotifiedProperty
from nplab.utils.gui import QtCore, QtGui, uic, get_qt_app
from nplab.ui.ui_tools import UiTools
#import Rotation_Stage as RS
#import visa
import time
import threading
import numpy as np
import pyqtgraph as pg
from nplab.ui.ui_tools import QtWidgets



#myOceanOptics = OceanOpticsSpectrometer(0)



class Lab3_experiment(Experiment, QtWidgets.QWidget, UiTools):
    # To use auto_connect_by_name name all widgets using _WidgetType, e.g. Vhigh_DoubleSpinBox
    # Then define DumbNotifiedProperty with the same name without _WidgetType, e.g. Vhigh
    Vmax = DumbNotifiedProperty(1.0)
    Vmin = DumbNotifiedProperty(-1.0)
    rampStep = DumbNotifiedProperty(0.1)
    Vhigh = DumbNotifiedProperty(1.0)
    Vlow = DumbNotifiedProperty(-1.0)
    smu_wait = DumbNotifiedProperty(0.0)
    RamanIntegrationTime = DumbNotifiedProperty(1.0)
    laser633_power = DumbNotifiedProperty(0)
    centre_row = DumbNotifiedProperty(100)
    num_rows = DumbNotifiedProperty(15)
    stepwiseHoldNumber = DumbNotifiedProperty(3)
    rampHoldNumber = DumbNotifiedProperty(1)
    rampIntermediateV = DumbNotifiedProperty(0.0)
    
    description = DumbNotifiedProperty("description")
    single_Raman_spectrum_description = DumbNotifiedProperty('single spectrum description')
    
    log_to_console = True
    live_Raman_spectrum_signal = QtCore.Signal(np.ndarray)
    live_darkfield_spectrum_signal = QtCore.Signal(np.ndarray)
    live_electronic_signal = QtCore.Signal(float, float, float)
    
    def __init__ (self, activeDatafile):
        super(Lab3_experiment, self).__init__()
        uic.loadUi('lab3_interface.ui', self)
        self.initialise_Andor()
        self.initilise_Shamrock()
#        self.initialise_Arduino()
        self.setup_plot_widgets()
        
        self.activeDatafile = activeDatafile
        self.singleRamanSpectraGroup = self.create_data_group('Single Raman spectra')
        
        self.auto_connect_by_name(self)
        
        self.live_Raman_spectrum_signal.connect(self.update_Raman_spectrum_plot)
        #self.live_electronic_signal.connect(self.update_electronic_plot)
        #self.live_darkfield_spectrum_signal.connect(self.update_darkfield_spectrum_plot)
        self.cooler_isON_checkbox.toggled.connect(self.Shamrock_cooler)
        
#        self.myArduino.shutterIN() #To ensure shutter is closed
        
    def initialise_Andor(self):
        self.myAndor = Andor()
        print('Andor initialised')
        
    def initilise_Shamrock(self):
        self.myShamrock = Shamrock()
        print('Shamrock initialised')
        
    def Shamrock_cooler(self):
        if self.cooler_isON_checkbox.isChecked():
            self.myAndor.CoolerON()
            print('Cooler ON')
        else:
            self.myAndor.CoolerOFF()
            print('Cooler OFF')
            
    def set_shamrock_grating(self):
        self.myShamrock.SetGrating(grating_num=int(self.TriaxGratingNumber_comboBox.currentText()))
        
    def set_shamrock_wavelength(self):
        self.myShamrock.SetWavelength(self.shamrockWavelength_spinBox.value())
        
    def set_shamrock_slit(self):
        self.myShamrock.SetSlit(self.triaxSlit_spinBox.value())
        
#    def initialise_Arduino(self):
#        self.myArduino = arduinoLab3.ArduinoLab3()
#        print('Arduino initialised')
    
    def setup_plot_widgets(self):
        print('In development')
#        self.electronics_plot = pg.PlotWidget()
        self.RamanSpectrum_plot = pg.PlotWidget()
#        self.electronics_IVplot = pg.PlotWidget()
#        self.RamanSpectrum_vs_time_plot = pg.PlotWidget()
#        self.darkfieldSpectrum_plot = pg.PlotWidget()
#        self.darkfieldSpectrum_vs_time_plot = pg.PlotWidget()
#        self.replace_widget(self.plotGrid, self.plot1, self.electronics_plot)
#        self.replace_widget(self.plotGrid, self.plot2, self.electronics_IVplot)
        self.replace_widget(self.plotGrid, self.plot3, self.RamanSpectrum_plot)
#        self.replace_widget(self.plotGrid, self.plot4, self.RamanSpectrum_vs_time_plot)
#        self.replace_widget(self.plotGrid, self.plot5, self.darkfieldSpectrum_plot)
#        self.replace_widget(self.plotGrid, self.plot6, self.darkfieldSpectrum_vs_time_plot)
#        # have to use pg.ImageItem() for an image plot. ImageItem is not a widget so it can't replace a PlotWidget directly,
#        # but it can be added as an ImageItem to a PlotWidget
        self.RamanImagePlotItem = pg.ImageItem()
#        self.RamanSpectrum_vs_time_plot.addItem(self.RamanImagePlotItem)
#        self.darkfieldImagePlotItem = pg.ImageItem()
#        self.darkfieldSpectrum_vs_time_plot.addItem(self.darkfieldImagePlotItem)
        
    def update_Raman_spectrum_plot(self, spectrum):
        self.RamanSpectrum_plot.plot(spectrum, clear = True, pen = 'r')  # plot current Raman spectrum in real time
        self.RamanSpectrumImagePlotData.append(spectrum)     # plot Raman spectra over time as image plot        
        self.RamanImagePlotItem.setImage(np.asarray(self.RamanSpectrumImagePlotData))
        
    def open_Andor_UI(self):
        self.AndorControlUI = self.myAndor.get_control_widget()
        self.AndorPreviewUI = self.myAndor.get_preview_widget()
        self.AndorControlUI.show()
        self.AndorPreviewUI.show()
        
    def open_OO_spectrometer(self):
        self.OOspectrometer = OceanOpticsSpectrometer(0)
        self.gui_OOspectrometer= self.OOspectrometer.get_qt_ui()
        self.gui_OOspectrometer.show()
    
#    def flipMirror(self):
#        self.myArduino.mirrorFlip()
    
    def acquire_single_Raman_spectrum(self):
# ALICE self.myAndor.SetParameter('Exposure', self.RamanIntegrationTime)
        self.myAndor.set_camera_parameter('Exposure', self.RamanIntegrationTime)
        self.myAndor.AcquisitionMode = 1
        self.myAndor.ReadMode = 3
# ALICE self.myAndor.SetParameter('SingleTrack', self.centre_row, self.num_rows)
        self.myAndor.set_camera_parameter('SingleTrack', self.centre_row, self.num_rows)
        #self.RamanWavelengths = self.myAndor.get_xaxis()
#        self.myArduino.shutterOUT()
        time.sleep(0.5)
        self.RamanSpectrum = np.asarray( self.myAndor.capture()[0] )
        self.RamanSpectrum_plot.plot(self.RamanSpectrum, clear = True, pen = 'r')
#        self.myArduino.shutterIN()
        
    def save_single_Raman_spectrum(self):
        activeSingleRamanDataset = self.singleRamanSpectraGroup.create_dataset('singleRamanSpectrum_%d', data = self.RamanSpectrum)
        activeSingleRamanDataset.attrs.create("singleSpectrumDescription", str(self.single_Raman_spectrum_description))
        #activeSingleRamanDataset.attrs.create("RamanWavelengths", self.RamanWavelengths)
        activeSingleRamanDataset.attrs.create('RamanIntegrationTime', self.RamanIntegrationTime)
        activeSingleRamanDataset.attrs.create('RamanSlit_um', self.myShamrock.GetSlit())
                
    def shutdown(self):
        self.activeDatafile.close()
#        self.myArduino.shutterIN()
        self.myAndor.CoolerOFF()
        self.myShamrock.SetSlit(100)
        self.myAndor.close()
        self.OOspectrometer.shutdown_seabreeze()
        print('----Experiment ended----')
    
    def get_qt_ui(self):
        return self


if __name__ == '__main__':
    activeDatafile = nplab.current_datafile()    
    gui_activeDatafile = activeDatafile.get_qt_ui()
    gui_activeDatafile.show()
    
    experiment = Lab3_experiment(activeDatafile)
    experiment.show_gui()
    print('Done')