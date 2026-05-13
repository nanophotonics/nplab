from threading import Lock, Semaphore

import h5py
import pyjisa.autoload
import os
import numpy as np

from typing import Callable, Dict, Generic, List, Tuple, TypeVar, Union

from jisa.results                       import ResultTable
from jisa.devices                       import Instrument
from jisa.devices.spectrometer          import CameraSpectrometer, Spectrometer as JSpectrometer
from jisa.devices.spectrometer.spectrum import Spectrum, SpectrumReader, SpectrumThread
from jisa.devices.features              import TemperatureControlled
from jisa                               import Util

from qtpy import uic
from qtpy.QtCore import QTimer, Qt, QThreadPool, Signal
from qtpy.QtGui import QBrush, QColor, QIcon, QImage, QPainter, QPen, QPixmap, QResizeEvent
from qtpy.QtWidgets import *


import nplab.datafile as df

import pyqtgraph as pg

from nplab.instrument.spectrometer.fastspectrometer.csconfig import CSConfigGUI
from nplab.ui.widgets.jisa import JISAConfigPanel

S = TypeVar("S", bound=JSpectrometer)

class FastSpectrometerGUI(QWidget, Generic[S]):

    spectrumSignal        = Signal(Spectrum)
    progressSignal        = Signal(float)
    acquisitionSignal     = Signal(bool)
    exceptionSignal       = Signal(Exception)
    captureCompleteSignal = Signal()
    captureWritingSignal  = Signal()
    mp4Signal             = Signal()
    h5Signal              = Signal()
    warningIcon           = QIcon.fromTheme("dialog-warning")

    def __init__(self, spectrometer: S, fs, preview = True):

        super().__init__()
        
        # Hold onto camera
        self.spectrometer = spectrometer
        self.fs           = fs

        # Create buffers
        self.wlBuffer    : Spectrum                   = None
        self.params      : List[Instrument.Parameter] = []
        self.stream      : SpectrumThread             = None
        self.lastWidth   : int                        = None
        self.lastHeight  : int                        = None
        self.lastSpectra : Spectrum                   = None

        # Define types for automatically linked widgets
        self.cameraParameters   : QVBoxLayout 
        self.numberOfFrames     : QSpinBox    
        self.delayTime          : QSpinBox
        self.captureButton      : QPushButton 
        self.liveViewButton     : QPushButton 
        self.spectrumGroup      : QGroupBox      
        self.applyButton        : QPushButton
        self.refreshButton      : QPushButton
        self.statusGroup        : QGroupBox
        self.streamBox          : QGroupBox
        self.temperatureLabel   : QLabel
        self.currentTemperature : QLCDNumber
        self.fpsCounter         : QLCDNumber
        self.h5SaveButton       : QPushButton
        self.streamToDiskButton : QPushButton
        self.streamFile         : QLineEdit
        self.streamBrowse       : QPushButton
        self.h5Button           : QPushButton
        self.writingH5          : QLabel
        self.deleteButton       : QPushButton
        self.namePattern        : QLineEdit
        self.capturedImages     : QGroupBox
        self.h5Label            : QLabel
        self.h5Group            : QLineEdit
        self.countLabel         : QLabel
        self.delayLabel         : QLabel
        self.configBox          : QGroupBox
        self.progressBar        : QProgressBar
        self.saveLastButton     : QPushButton
         
        # Load UI from file
        if preview:
            uic.loadUi((os.path.dirname(__file__) + '/resources/fsgui.ui'), self)
        else:
            uic.loadUi((os.path.dirname(__file__) + '/resources/fsgui-controls.ui'), self)

        # Create other QT elements
        self.pool         = QThreadPool()
        self.errorMessage = QErrorMessage()
        self.bufferLock   = Lock()
        self.semaphore    = Semaphore(0)

        if preview:
            self.plot     = pg.plot(title="Spectrum", left="Counts", bottom="Wavelength [m]")
            self.plotData = self.plot.plotItem.plot([],[])
            self.spectrumGroup.layout().addWidget(self.plot)
            self.spectrometer.addSpectrumListener(self.spectrumListener)

        self.configPanel  = JISAConfigPanel(self.spectrometer)

        # Add custom GUI elements to the overall layout
        self.configBox.layout().addWidget(self.configPanel)

        # If this is a camera-based spectrometer, then include a button to configure the frame to spectrum conversion
        if isinstance(self.spectrometer, CameraSpectrometer):
            self.csconfig = CSConfigGUI(self.spectrometer)
            self.csbutton = QPushButton("Configure Transformation...")
            self.csbutton.clicked.connect(self.csconfig.show)
            self.configBox.layout().addWidget(self.csbutton)


        self.progressBar.setVisible(False)

        self.setupStatusMonitoring()
        self.setupStreamer()
        self.setupConnections()

        # Connect listeners
        self.spectrometer.addAcquisitionListener(lambda c, a: self.acquisitionSignal.emit(bool(a)) if c == 0 else None)


    def setupStatusMonitoring(self):

        self.timer = QTimer()
        self.timer.setInterval(1000)

        # Check if the camera implements some sort of temperature control
        if isinstance(self.spectrometer, TemperatureControlled) or (isinstance(self.spectrometer, CameraSpectrometer) and isinstance(self.spectrometer.getCamera(), TemperatureControlled)):
            self.timer.timeout.connect(self.updateTemperature)
            self.currentTemperature.setEnabled(True)
            self.temperatureLabel.setEnabled(True)

        else:
            self.currentTemperature.setEnabled(False)
            self.temperatureLabel.setEnabled(False)

        self.timer.timeout.connect(self.updateFPS)

        self.timer.start()
    

    def setupStreamer(self):

        self.writingH5.setVisible(False)

        def _reenable():

            if not self.writingH5.isVisible():

                if self.deleteButton.isChecked():
                    try:
                        os.remove(self.streamPath)
                    except:
                        pass

                self.streamFile.setDisabled(False)
                self.streamBrowse.setDisabled(False)
                self.streamToDiskButton.setDisabled(False)
                self.h5Button.setDisabled(False)
                self.deleteButton.setDisabled(False)
                self.streamToDiskButton.setStyleSheet("")
                self.streamToDiskButton.setText("Start Streaming to Disk")


        def _doneH5():
            self.writingH5.setVisible(False)
            _reenable()

        
        def _checkDelete():

            checked = False

            if self.h5Button.isChecked():
                self.h5Button.setStyleSheet("color: purple;")
                checked = True
            else:
                self.h5Button.setStyleSheet("")

            if checked:
                self.deleteButton.setDisabled(False)
            else:
                self.deleteButton.setChecked(False)
                self.deleteButton.setDisabled(True)

            if self.deleteButton.isChecked():
                self.deleteButton.setStyleSheet("color: brown;")
            else:
                self.deleteButton.setStyleSheet("")


        self.h5Signal.connect(_doneH5)
        self.h5Button.clicked.connect(_checkDelete)
        self.deleteButton.clicked.connect(_checkDelete)


    def setupConnections(self):

        self.captureButton.clicked.connect(self.capture)
        self.liveViewButton.clicked.connect(self.live)
        self.captureWritingSignal.connect(lambda: self.captureButton.setText("Writing..."))
        self.captureCompleteSignal.connect(self.captureComplete)
        self.streamToDiskButton.clicked.connect(self.streamClick)
        self.streamBrowse.clicked.connect(self.browseStreamFile)
        self.h5SaveButton.clicked.connect(self.updateSaveButtons)
        self.progressSignal.connect(self.updateCaptureProgress)
        self.acquisitionSignal.connect(self.updateAcquisition)
        self.exceptionSignal.connect(self.showException)
        self.saveLastButton.clicked.connect(self.saveLastSpectrum)

        if hasattr(self, "spectrumGroup"):
            self.spectrumSignal.connect(self.drawSpectrum)


    def updateFPS(self):
        self.fpsCounter.display(self.spectrometer.getAcquisitionRate())


    def updateSaveButtons(self):

        if self.h5SaveButton.isChecked():
            self.h5SaveButton.setStyleSheet("color: purple;")
        else:
            self.h5SaveButton.setStyleSheet("")


    def browsePNGDirectory(self):

        file = QFileDialog.getExistingDirectory()

        if not isinstance(file, str):
            file = file[0]

        if len(file) == 0:
            return
        
        self.pngDirectory.setText(file)


    def browseStreamFile(self):

        file = QFileDialog.getSaveFileName()

        if not isinstance(file, str):
            file = file[0]

        if len(file) == 0:
            return
        
        self.streamFile.setText(file)


    def streamClick(self):

        if self.stream is None:

            if str(self.streamFile.text()).strip() == "":
                self.errorMessage.showMessage("You must choose a file to output to before starting the stream.")
                return


            self.streamFile.setDisabled(True)
            self.streamBrowse.setDisabled(True)

            self.streamAttrs = self.spectrometer.getAllParametersAsMap()
            self.streamPath  = self.streamFile.text()
            self.stream      = self.spectrometer.streamToFile(self.streamPath)

            self.streamToDiskButton.setStyleSheet("color: brown;")
            self.streamToDiskButton.setText("Stop Streaming")

        else:

            self.stream.stop()
            self.stream = None

            self.streamToDiskButton.setDisabled(True)
            self.h5Button.setDisabled(True)
            self.deleteButton.setDisabled(True)
            self.streamToDiskButton.setText("Converting...")
            self.streamToDiskButton.setStyleSheet("")

            if self.h5Button.isChecked():

                self.writingH5.setVisible(True)

                def saveH5():

                    try:
                        
                        file = df.current()

                        j = 0
                        nm = "Stream %d" % j

                        while nm in file:
                            j += 1
                            nm = "Stream %d" % j

                        group  = file.create_group(nm)

                        self.writeAttributes(group, self.streamAttrs)

                        reader = SpectrumReader(self.streamPath)

                        i = 0

                        while reader.hasSpectrum():
                            self.spectrumToDataset(group, reader.readSpectrum(), r"spectrum_%d", i)
                            i += 1

                    finally:
                        self.h5Signal.emit()


                self.pool.start(saveH5)

            if not self.writingH5.isVisible():

                if self.deleteButton.isChecked():
                    try:
                        os.remove(self.streamPath)
                    except:
                        pass

                self.streamFile.setDisabled(False)
                self.streamBrowse.setDisabled(False)
                self.streamToDiskButton.setDisabled(False)
                self.h5Button.setDisabled(False)
                self.deleteButton.setDisabled(False)
                self.streamToDiskButton.setStyleSheet("")
                self.streamToDiskButton.setText("Start Streaming to Disk")



    def updateTemperature(self):

        if isinstance(self.spectrometer, TemperatureControlled):
            self.currentTemperature.display(self.spectrometer.getControlledTemperature())

        elif isinstance(self.spectrometer, CameraSpectrometer):

            camera = self.spectrometer.getCamera()

            if isinstance(camera, TemperatureControlled):
                self.currentTemperature.display(camera.getControlledTemperature())


    def showException(self, e: Exception):
        self.errorMessage.showMessage(str(e))


    def capture(self):

        # Lock down the GUI inputs
        self.captureButton.setDisabled(True)
        self.capturedImages.setDisabled(True)
        self.liveViewButton.setVisible(False)
        self.countLabel.setDisabled(True)
        self.numberOfFrames.setDisabled(True)
        self.delayLabel.setDisabled(True)
        self.delayTime.setDisabled(True)
        self.captureButton.setText("Capturing...")
        self.captureButton.setStyleSheet("color: brown;")
        self.progressBar.setValue(0)
        self.progressBar.setVisible(True)
        self.configPanel.setDisabled(True)

        # Define what we want to happen
        def _thread():

            try:

                wasAcquiring = self.spectrometer.isAcquiring()

                delay   = max(self.delayTime.value(), 0)
                count   = max(self.numberOfFrames.value(), 1)
                timeout = self.spectrometer.getAcquisitionTimeout()
                spectra = []

                if count == 1:
                    
                    spectra.append(self.spectrometer.getSpectrum())
                    self.progressSignal.emit(100.0)
                    self.spectrumListener(spectra[0], False)
                    self.fs.updateSpectrum(spectra[0])

                else:

                    if not wasAcquiring:
                        self.spectrometer.startAcquisition()

                    queue = self.spectrometer.openSpectrumQueue(1)

                    for i in range(count - 1):
                        Util.sleep(delay)
                        spectra.append(queue.nextSpectrum(timeout) if timeout > 0 else queue.nextSpectrum())
                        self.progressSignal.emit(100.0 * ((i + 1) / count))

                    spectra.append(queue.nextSpectrum(timeout) if timeout > 0 else queue.nextSpectrum())
                    self.progressSignal.emit(100.0)

                    queue.close()
                    queue.clear()

                    if not wasAcquiring:
                        self.spectrometer.stopAcquisition() 


                self.lastSpectra = spectra

                if self.h5SaveButton.isChecked():
                    self.captureWritingSignal.emit()
                    self.saveToH5(spectra)

            except Exception as e:
                self.exceptionSignal.emit(e)

            finally:

                # When done, we need to signal the GUI to re-enable everything
                self.captureCompleteSignal.emit()

                if not wasAcquiring:
                    self.spectrometer.stopAcquisition()


        # Give the method to our thread pool to execute in the background
        self.pool.start(_thread)


    def saveLastSpectrum(self):

        if self.lastSpectra is None:
            return
        
        self.saveToH5(self.lastSpectra)


    def updateCaptureProgress(self, value: float):
        self.progressBar.setValue(int(value))


    def captureComplete(self):

        self.captureButton.setDisabled(False)
        self.captureButton.setText("Capture")
        self.captureButton.setStyleSheet("")
        self.capturedImages.setDisabled(False)
        self.countLabel.setDisabled(False)
        self.numberOfFrames.setDisabled(False)
        self.delayLabel.setDisabled(False)
        self.delayTime.setDisabled(False)
        self.progressBar.setVisible(False)
        self.liveViewButton.setVisible(True)
        self.configPanel.setDisabled(False)

    
    def live(self):

        if self.spectrometer.isAcquiring():
            self.spectrometer.stopAcquisition()
        else:
            self.spectrometer.startAcquisition()


    def updateAcquisition(self, acquiring: bool):

        if acquiring:
            self.liveViewButton.setStyleSheet("color: brown;")
            self.liveViewButton.setText("Stop Continuous Acquisition")
        else:
            self.liveViewButton.setStyleSheet("")
            self.liveViewButton.setText("Start Continuous Acquisition")


    def spectrumListener(self, spec: Spectrum, wait = True):

        with self.bufferLock:

            if self.wlBuffer is None or self.wlBuffer.size() != spec.size():
                self.wlBuffer = spec.copy()
            else:
                self.wlBuffer.copyFrom(spec)

            self.spectrumSignal.emit(self.wlBuffer)

        if wait:
            self.semaphore.acquire()

        
    def drawSpectrum(self, spec: Spectrum):

        with self.bufferLock:

            try:
                self.plotData.setData(spec.listWavelengths(), spec.listCounts())
            except:
                print("Exception when drawing spectrum")
            finally:
                self.semaphore.release()


    def saveToH5(self, spectra):

        # Attempt to get the currently opened H5 file
        try:
            file = df.current()
        except:
            self.errorMessage.showMessage("No HDF5 data file currently open to save to.")
            return

        try:

            # Parse the path specified by the user
            groupName = self.h5Group.text().strip("/")
            parts     = [p for p in groupName.split("/") if p.strip() != ""]
            group     = file
            counter   = 0

            # Traverse through path specified by user
            for part in parts:

                if part in group:
                    group = group[part]
                else:
                    group = group.create_group(part)


            pattern = self.namePattern.text()

            # Check that the pattern has a format specifier in it
            try:
                pattern % 1
            except:
                pattern += r"_%d"


            # Create a new dataset for each spectrum
            for spectrum in spectra:
                self.spectrumToDataset(group, spectrum, pattern, counter)
                counter += 1


        finally:
            # When done, make sure any changes are flushed to the backing file
            file.flush()


    def spectrumToDataset(self, group: h5py.Group, spectrum: Spectrum, pattern: str, counter: int = 0) -> h5py.Dataset:
        
        # Attempt to find a name that hasn't already been used
        name = pattern % counter

        while name in group:

            counter += 1
            name     = pattern % counter


        # Create the dataset and write the attributes to it
        ds = group.create_dataset(name, data = np.array([np.array(spectrum.getWavelengths()), np.array(spectrum.getCounts())]))
        self.writeAttributes(ds, spectrum)

        return ds


    def writeAttributes(self, ds: h5py.HLObject, data: Union[Dict[str, object], Spectrum]):

        if isinstance(data, Spectrum):
            ds.attrs["Timestamp"] = data.getTimestamp()
            data = data.getAttributes()

        for key, value in data.items():
            
            if isinstance(value, Instrument.AutoQuantity):

                ds.attrs[key + ": Auto"]  = value.isAuto()

                key   = key + ": Value"
                value = value.getValue()
        

            elif isinstance(value, Instrument.OptionalQuantity):

                ds.attrs[key + ": Used"]  = value.isUsed()

                key   = key + ": Value"
                value = value.getValue()


            if isinstance(value, ResultTable):
                ds.attrs[key] = [[str(c.getTitle()) for c in value.getColumns()]] + [[str(v) for v in r] for r in value.asStringArray()]
            else:
                ds.attrs[key] = str(value)



    def savePNGs(self, frames):

        counter   = 0
        directory = self.pngDirectory.text()
        pattern   = self.namePattern.text()

        os.makedirs(directory, exist_ok=True)

        try:
            pattern % counter
        except:
            pattern += r"_%d"

        pattern += ".png"

        for frame in frames:

            nm = pattern % counter

            while os.path.isfile(os.path.join(directory, nm)):
                counter += 1
                nm = pattern % counter

            frame.savePNG(os.path.join(directory, nm))

            counter += 1

        
class FastSpectrometerPreviewGUI(QWidget, Generic[S]):

    drawSignal = Signal(Spectrum)

    def __init__(self, spectrometer: S):

        super().__init__()
        self.setLayout(QVBoxLayout())

        plot = pg.plot(left="Counts", bottom="Wavelength [m]")
        self.layout().addWidget(plot)
        
        self.data = plot.plotItem.plot([], [])
        self.sem  = Semaphore(0)

        self.buffer: Spectrum = None
        self.bufferLock       = Lock()

        self.drawSignal.connect(self.draw)
        spectrometer.addSpectrumListener(self.update)

    
    def update(self, spectrum: Spectrum):

        with self.bufferLock:

            if self.buffer is None or self.buffer.size() != spectrum.size():
                self.buffer = spectrum.copy()
            else:
                self.buffer.copyFrom(spectrum)

            self.drawSignal.emit(self.buffer)

        self.sem.acquire()


    def draw(self, spectrum: Spectrum):
        try:
            with self.bufferLock:
                self.data.setData(spectrum.listWavelengths(), spectrum.listCounts())
        finally:
            self.sem.release()

