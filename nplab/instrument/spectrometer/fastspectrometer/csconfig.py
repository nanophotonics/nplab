import os
from threading import Lock, Semaphore

from numpy import int32
import pyjisa.autoload
import pyqtgraph as pg

import numpy as np
from qtpy import uic
from qtpy.QtCore import QThreadPool, Qt, Signal
from qtpy.QtGui import QImage, QPainter, QPen, QPixmap
from qtpy.QtWidgets import *

from jisa                               import Util
from jisa.results                       import ResultTable, ResultList, Column
from jisa.devices.camera                import Camera
from jisa.devices.camera.frame          import Frame
from jisa.devices.spectrometer          import CameraSpectrometer
from jisa.devices.spectrometer.spectrum import Spectrum

from typing import TypeVar, Generic

from nplab.ui.widgets.jisa import JISAConfigPanel
from nplab.ui.widgets.jisa.widgets import ResultTableWidget

S = TypeVar("S", bound=CameraSpectrometer)
C = TypeVar("C", bound=Camera)

class CSConfigGUI(QWidget, Generic[S, C]):

    drawFrameSignal    = Signal(np.ndarray)
    drawSpectrumSignal = Signal(Spectrum)

    def __init__(self, cs: S):

        super().__init__()

        self.spectrometer : S        = cs
        self.camera       : C        = cs.getCamera()
        self.buffer                  = None
        self.arr                     = None
        self.specBuffer   : Spectrum = None

        self.imageBox        : QGroupBox
        self.spectrumBox     : QGroupBox
        self.configBox       : QGroupBox
        self.startX          : QSpinBox
        self.startY          : QSpinBox
        self.endX            : QSpinBox
        self.endY            : QSpinBox
        self.binning         : QSpinBox
        self.wavelengths     : QHBoxLayout
        self.showWavelengths : QPushButton
        self.addRow          : QPushButton
        self.remRow          : QPushButton
        self.closeButton     : QPushButton
        self.liveViewButton  : QPushButton
        self.applyButton     : QPushButton
        self.typeBox         : QComboBox
        self.fitOrder        : QSpinBox
        
        # Load UI from file
        uic.loadUi((os.path.dirname(__file__) + '/resources/csconfig.ui'), self)

        # Create other QT elements
        self.pool           = QThreadPool()
        self.errorMessage   = QErrorMessage()
        self.cameraLock     = Lock()
        self.cameraDrawLock = Lock()
        self.spectrumLock   = Lock()
        self.cameraSem      = Semaphore(0)
        self.specSem        = Semaphore(0)
        self.configPanel    = JISAConfigPanel(self.camera)
        self.plot           = pg.plot(left="Counts")
        self.plotData       = self.plot.plotItem.plot([], [])
        self.image          = pg.ImageView(view=pg.PlotItem())
        self.table          = ResultTableWidget()

        self.I = Column.ofIntegers("Channel Index")
        self.W = Column.ofDoubles("Wavelength", "m")
        data   = ResultList(self.I, self.W)

        self.table.setResultTable(data)

        self.wavelengths.addWidget(self.table)
        self.configBox.layout().addWidget(self.configPanel)
        self.imageBox.layout().addWidget(self.image.ui.graphicsView)
        self.spectrumBox.layout().addWidget(self.plot)

        self.camera.addFrameListener(self.frameListener)
        self.spectrometer.addSpectrumListener(self.spectrumListener)
        self.spectrometer.addAcquisitionListener(self.updateAcquisition)

        self.setupConnections()
        self.typeChange()


    def setupConnections(self):

        self.liveViewButton.clicked.connect(self.live)
        self.applyButton.clicked.connect(self.setConverter)
        self.typeBox.currentTextChanged.connect(self.typeChange)
        self.closeButton.clicked.connect(self.close)
        self.drawFrameSignal.connect(self.drawFrame)
        self.drawSpectrumSignal.connect(self.drawSpectrum)


    def typeChange(self):

        disabled = self.typeBox.currentText() == "Full Vertical Binning"

        self.startX.setDisabled(disabled)
        self.startY.setDisabled(disabled)
        self.endX.setDisabled(disabled)
        self.endY.setDisabled(disabled)
        self.binning.setDisabled(disabled)


    def updateAcquisition(self, count: int, acquiring: bool):

        if count != 0:
            return

        if acquiring:
            self.liveViewButton.setStyleSheet("color: brown;")
            self.liveViewButton.setText("Stop Continuous Acquisition")
        else:
            self.liveViewButton.setStyleSheet("")
            self.liveViewButton.setText("Start Continuous Acquisition")


    def live(self):

        if self.spectrometer.isAcquiring():
            self.spectrometer.stopAcquisition()
        else:
            self.spectrometer.startAcquisition()


    def setConverter(self):

        if self.spectrometer.isAcquiring():
            self.spectrometer.stopAcquisition()
            stopped = True
        else:
            stopped = False

        wavelengths = {r.get(self.I): r.get(self.W) for r in self.table.getResultTable()}

        if self.typeBox.currentText() == "Full Vertical Binning":

            self.spectrometer.setConverterFullVerticalBinning(wavelengths, self.fitOrder.value())

        else:

            startX      = int32(self.startX.value())
            startY      = int32(self.startY.value())
            endX        = int32(self.endX.value())
            endY        = int32(self.endY.value())
            binning     = int32(self.binning.value())

            if len(wavelengths) < 2:
                wavelengths.clear()
                wavelengths[int32(0)] = 0.0
                wavelengths[int32(1)] = 1.0

            self.spectrometer.setConverter(startX, startY, endX, endY, binning, wavelengths)


        if stopped:
            self.spectrometer.startAcquisition()


    def frameListener(self, frame: Frame):

        width  = frame.getWidth()
        height = frame.getHeight()

        try:

            # So that we don't have multiple threads trying to access the buffer at the same time
            with self.cameraLock:

                # If the frame size has changed, then we need to recreate the buffer, otherwise we should reuse it
                if self.buffer is None or len(self.buffer) != frame.size():
                    self.buffer = frame.getScaledARGBData()
                    self.arr    = np.array(self.buffer)
                    self.rgb    = np.empty((width, height, 3), dtype=np.uint8)
                else:
                    frame.readScaledARGBData(self.buffer)
                    np.copyto(self.arr, self.buffer)

                # Record dimensions incase we need to redraw before a new frame comes in

                # Convert the buffer into a pixmap
                argb2d = self.arr.view(np.uint8).reshape(width, height, 4)

                self.rgb[..., 0] = argb2d[..., 2]
                self.rgb[..., 1] = argb2d[..., 1]
                self.rgb[..., 2] = argb2d[..., 0]

                self.drawFrameSignal.emit(self.rgb)

        except:
            print("Exception when drawing frame")
        finally:
            self.cameraSem.acquire()
    

    def drawFrame(self, pixmap: np.ndarray):

        # So that we don't have multiple threads trying to access the buffer at the same time
        with self.cameraLock:

            try:
                self.image.setImage(pixmap, autoRange=False)
            except Exception as e:
                print("Exception occurred when drawing frame. " + str(e))
            finally:
                self.cameraSem.release()



    def spectrumListener(self, spec: Spectrum):

        # So that we don't have multiple threads trying to access the buffer at the same time
        with self.spectrumLock:

            if self.specBuffer is None or self.specBuffer.size() != spec.size():
                self.specBuffer = spec.copy()
            else:
                self.specBuffer.copyFrom(spec)

            self.drawSpectrumSignal.emit(self.specBuffer)

        self.specSem.acquire()


    def drawSpectrum(self, spec: Spectrum):
            
        with self.spectrumLock:

            try:
                if self.showWavelengths.isChecked():
                    self.plotData.setData(spec.listWavelengths(), spec.listCounts())
                else:
                    self.plotData.setData(np.arange(spec.size()), spec.listCounts())

            except:
                print("Exception when drawing spectrum")
            finally:
                self.specSem.release()
