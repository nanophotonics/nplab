# -*- coding: utf-8 -*-
"""
Created on Jan 15 10:23:36 2019

@author: Hera
"""
#import nplab.datafile
from nplab.instrument.camera.Andor import Andor
#from nplab.instrument.spectrometer.shamrock import Shamrock
#from nplab.instrument.spectrometer.Triax.Trandor_Lab3 import Trandor
from nplab.instrument.spectrometer.shamdor import Shamdor
from nplab.instrument.spectrometer.seabreeze import OceanOpticsSpectrometer
from nplab.instrument.electronics.keithley_2636b_smu import Keithley2636B as Keithley
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
        self.initialise_Shamdor()
        self.initialise_Andor()
        self.initialise_smu()
#        self.initialise_Shamrock()
#        self.initialise_Arduino()
        self.setup_plot_widgets()
        
        self.activeDatafile = activeDatafile
        self.singleRamanSpectraGroup = self.create_data_group('Single Raman spectra')
        
        self.auto_connect_by_name(self)
        
        self.live_Raman_spectrum_signal.connect(self.update_Raman_spectrum_plot)
        self.live_electronic_signal.connect(self.update_electronic_plot)
        #self.live_darkfield_spectrum_signal.connect(self.update_darkfield_spectrum_plot)
        self.cooler_isON_checkbox.toggled.connect(self.Shamrock_cooler)
        
#        self.myArduino.shutterIN() #To ensure shutter is closed
        
    def initialise_Andor(self):
        self.myAndor = Andor()
        print('Andor initialised')
        
    def initialise_Shamdor(self):
        self.myShamdor = Shamdor()
#        self.myShamdor.use_shifts = True   #Uncomment For Raman Shift (Instead of Plotting with wavelength)
        print('Shamdor initialised')
        
    def run(self, *args):
        # *args collects extra unnecessary arguments from qt
        self.voltages_data = []
        self.times_data = []
        self.currents_data = []
        stepwiseCounter = 1
        rampCounter = 1
        runningRampInterval = False
        try:
            activeDatagroup = self.create_data_group('scan_%d')
            activeDatagroup.attrs.create('description', str(self.description))
            if not self.mode_smuOnly.isChecked():
                if (self.mode_RamanOnly.isChecked() or self.mode_RamanAndDarkfield.isChecked() ):
                    self.RamanSpectrumImagePlotData = []
                    self.RamanWavelengths = self.AndorSpectrometer.Generate_Wavelength_Axis()
                    activeDatagroup.attrs.create('RamanWavelengths', self.RamanWavelengths)
                    activeDatagroup.attrs.create('RamanIntegrationTime', self.RamanIntegrationTime)
                    activeDatagroup.attrs.create('RamanSlit_um', self.AndorSpectrometer.triax.Slit())
                    self.AndorSpectrometer.SetParameter('Exposure', self.RamanIntegrationTime)
                    self.AndorSpectrometer.AcquisitionMode = 1    # acquisition mode = 1 for single frame acquisition
                    self.AndorSpectrometer.ReadMode = 3          # read mode = single track (reads centre_row +- num_rows). Output is one spectrum.
                    self.AndorSpectrometer.SetParameter('SingleTrack', self.centre_row, self.num_rows)
                if (self.mode_DarkfieldOnly.isChecked() or self.mode_RamanAndDarkfield.isChecked() ):
                    self.darkfieldSpectrumImagePlotData = []
                    self.darkfieldWavelengths = self.OOspectrometer.read_wavelengths()
                    activeDatagroup.attrs.create('DarkfieldWavelengths', self.darkfieldWavelengths)
                    activeDatagroup.attrs.create('DarkfieldBackground', self.OOspectrometer.background)
                    activeDatagroup.attrs.create('DarkfieldReference', self.OOspectrometer.reference)
                    activeDatagroup.attrs.create('DarkfieldIntegrationTime', self.OOspectrometer.get_integration_time())
            self.smu.src_voltage_range = float(self.Vrange_comboBox.currentText())
            self.smu.meas_current_range = float(self.Irange_comboBox.currentText())
            self.smu.src_voltage_limit = float(self.Vlimit_doubleSpinBox.value())
            self.smu.src_current_limit = float(self.Ilimit_doubleSpinBox.value())
            activeVoltage = 0.0
            rampActiveVoltage = 0.0
            self.voltageRampSign = 1
            self.smu.output = 1
            t0 = time.time()
            print "----- Measurement started -----"
            
            while True:
                self.smu.src_voltage = activeVoltage
                #spectrum = self.spectrometer.read_spectrum(bundle_metadata=True)
                if self.mode_smuOnly.isChecked():
                    self.acquireIVdatapoint(activeVoltage, t0, activeDatagroup)
                else:
                    if (self.mode_RamanOnly.isChecked() or self.mode_RamanAndDarkfield.isChecked() ):
                        RamanSpectrum_thread = threading.Thread(target = self.acquire_Raman_spectrum )    # acquiring Raman spectrum in new thread
                        RamanSpectrum_thread.start()
                        spectraActiveTime = (time.time()-t0)
                        activeDatagroup.append_dataset("RamanSpectra_times", spectraActiveTime)
                        while RamanSpectrum_thread.isAlive():       # collect current measurements while spectrum is being acquired
                            self.acquireIVdatapoint(activeVoltage, t0, activeDatagroup)
                        self.live_Raman_spectrum_signal.emit(self.RamanSpectrum)
                        activeDatagroup.append_dataset("RamanSpectrum", self.RamanSpectrum)
                    
                    if (self.mode_DarkfieldOnly.isChecked() or self.mode_RamanAndDarkfield.isChecked() ):
                        DarkfieldSpectrum_thread = threading.Thread(target = self.acquire_darkfield_spectrum )    # acquiring Raman spectrum in new thread
                        DarkfieldSpectrum_thread.start()
                        spectraActiveTime = (time.time()-t0)
                        activeDatagroup.append_dataset("darkfieldSpectra_times", spectraActiveTime)
                        while DarkfieldSpectrum_thread.isAlive():       # collect current measurements while spectrum is being acquired
                            self.acquireIVdatapoint(activeVoltage, t0, activeDatagroup)
                        self.live_darkfield_spectrum_signal.emit(self.darkfieldSpectrum)
                        activeDatagroup.append_dataset("darkfieldSpectrum", self.darkfieldSpectrum)
                
                if self.hold.isChecked():       # if hold checkbox is checked do not change the voltage
                    pass
                else:                           # running in ramp or stepwise mode?
                    if self.RampON.isChecked():
                        if rampCounter < self.rampHoldNumber:
                            rampCounter += 1
                        else:                   # check if running a ramp with intermediate voltage value between steps
                            if (not self.RampIntermediateStep.isChecked()) or runningRampInterval:
                                if (rampActiveVoltage >= self.Vmax):    # if activeVoltage not in [Vmin,Vmax], e.g. after stepwise mode, reset it to Vmax or Vmin
                                    if (rampActiveVoltage > (self.Vmax + self.rampStep) ):
                                        rampActiveVoltage = self.Vmax + self.rampStep
                                    self.voltageRampSign = -1
                                elif (rampActiveVoltage <= self.Vmin):
                                    if (rampActiveVoltage < (self.Vmin - self.rampStep) ):
                                        rampActiveVoltage = self.Vmin - self.rampStep
                                    self.voltageRampSign = 1
                                rampActiveVoltage += self.voltageRampSign * self.rampStep
                                activeVoltage = rampActiveVoltage
                                runningRampInterval = False
                            elif self.RampIntermediateStep.isChecked() and (not runningRampInterval):
                                activeVoltage = self.rampIntermediateV
                                runningRampInterval = True
                            rampCounter = 1                            
                    elif self.StepwiseON.isChecked():
                        if stepwiseCounter < self.stepwiseHoldNumber:
                            stepwiseCounter += 1        # keep the same voltage if the counter is <= the hold number
                        else:
                            if (activeVoltage > (self.Vhigh + self.Vlow)/2 ):
                                activeVoltage = self.Vlow
                            else:
                                activeVoltage = self.Vhigh
                            stepwiseCounter = 1
                self.wait_or_stop(self.smu_wait)
                
        except ExperimentStopped:
            print "----- Measurement stopped -----"
        finally:
            self.activeDatafile.flush()
            self.smu.output = 0
            #self.AndorSpectrometer.light_shutter.open_shutter()

    def initialise_smu(self)            :
        self.smu = Keithley.get_instance(address = 'USB0::0x05E6::0x2636::4439367::INSTR')
        self.smu.display = 0    # display current readings
        self.smu.src_voltage_range = float(self.Vrange_comboBox.currentText())
        self.smu.meas_current_range = float(self.Irange_comboBox.currentText())
        self.smu.src_voltage_limit = float(self.Vlimit_doubleSpinBox.value())
        self.smu.src_current_limit = float(self.Ilimit_doubleSpinBox.value())
        
        
    def Shamrock_cooler(self):
        if self.cooler_isON_checkbox.isChecked():
            self.myAndor.CoolerON()
            print('Cooler ON')
        else:
            self.myAndor.CoolerOFF()
            print('Cooler OFF')
            
    def set_shamrock_grating(self):
        self.myShamdor.shamrock.SetGrating(grating_num=int(self.TriaxGratingNumber_comboBox.currentText()))
        
    def set_shamrock_wavelength(self):
        self.myShamdor.shamrock.SetWavelength(self.shamrockWavelength_spinBox.value())
        
    def set_shamrock_slit(self):
        self.myShamdor.shamrock.SetSlit(self.triaxSlit_spinBox.value())
        
#    def initialise_Arduino(self):
#        self.myArduino = arduinoLab3.ArduinoLab3()
#        print('Arduino initialised')
    
    def setup_plot_widgets(self):
        print('In development')
        self.electronics_plot = pg.PlotWidget()
        self.RamanSpectrum_plot = pg.PlotWidget()
        self.electronics_IVplot = pg.PlotWidget()
#        self.RamanSpectrum_vs_time_plot = pg.PlotWidget()
#        self.darkfieldSpectrum_plot = pg.PlotWidget()
#        self.darkfieldSpectrum_vs_time_plot = pg.PlotWidget()
        self.replace_widget(self.plotGrid, self.plot1, self.electronics_plot)
        self.replace_widget(self.plotGrid, self.plot2, self.electronics_IVplot)
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
        
    def update_electronic_plot(self, timePlotInput, voltagePlotInput, currentPlotInput):
        if not hasattr(self,'voltages_data'):
            self.electronics_plot.clear()
            self.electronicsIV_plot.clear()
            self.times_data = [timePlotInput]
            self.voltages_data = [voltagePlotInput]
            self.currents_data = [currentPlotInput]
        else:
            self.times_data.append(timePlotInput)
            self.voltages_data.append(voltagePlotInput)
            self.currents_data.append(currentPlotInput)
        self.electronics_plot.plot(self.times_data, self.currents_data, clear = True, pen = 'r')
        self.electronics_IVplot.plot(self.voltages_data, self.currents_data, clear = True, pen = 'r')

    def rampChangeDirection(self):
        self.voltageRampSign *= -1  
        
    def open_Andor_UI(self):
        self.AndorControlUI = self.myAndor.get_control_widget()
        self.AndorPreviewUI = self.myAndor.get_preview_widget()
        self.AndorControlUI.show()
        self.AndorPreviewUI.show()
        
    def acquireIVdatapoint(self, activeVoltage, t0, activeDatagroup):
        measuredCurrent = self.smu.read_current()
        electronicActiveTime = (time.time()-t0)
        activeDatagroup.append_dataset("voltages", activeVoltage)
        activeDatagroup.append_dataset("currents", measuredCurrent)
        activeDatagroup.append_dataset("electronic_times", electronicActiveTime)
        self.live_electronic_signal.emit(electronicActiveTime, activeVoltage, measuredCurrent)
        
    def open_OO_spectrometer(self):
        self.OOspectrometer = OceanOpticsSpectrometer(0)
        self.gui_OOspectrometer= self.OOspectrometer.get_qt_ui()
        self.gui_OOspectrometer.show()
    
#    def flipMirror(self):
#        self.myArduino.mirrorFlip()
    
    def acquire_single_Raman_spectrum(self):
        self.myAndor.set_camera_parameter('Exposure', self.RamanIntegrationTime)
        self.myAndor.AcquisitionMode = 1
        self.myAndor.ReadMode = 3
        self.myAndor.set_camera_parameter('SingleTrack', self.centre_row, self.num_rows)
        self.myShamdor.shamrock.SetWavelength(self.spinBox_centre_wavelength.value())
        self.RamanWavelengths = self.myShamdor.get_xaxis()
        time.sleep(0.5)
        self.RamanSpectrum = np.asarray( self.myAndor.capture()[0] )
        self.RamanSpectrum_plot.plot(self.RamanWavelengths, self.RamanSpectrum, clear = True, pen = 'r')
        
    def save_single_Raman_spectrum(self):
        activeSingleRamanDataset = self.singleRamanSpectraGroup.create_dataset('singleRamanSpectrum_%d', data = self.RamanSpectrum)
        activeSingleRamanDataset.attrs.create("singleSpectrumDescription", str(self.single_Raman_spectrum_description))
        activeSingleRamanDataset.attrs.create("RamanWavelengths", self.RamanWavelengths)
        activeSingleRamanDataset.attrs.create('RamanIntegrationTime', self.RamanIntegrationTime)
        activeSingleRamanDataset.attrs.create('RamanSlit_um', self.myShamdor.shamrock.GetSlit())
                
    def shutdown(self):
        self.activeDatafile.close()
        self.myAndor.CoolerOFF()
        self.myShamdor.shamrock.SetSlit(100)
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