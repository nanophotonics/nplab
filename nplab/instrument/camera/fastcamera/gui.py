from threading import Lock

import h5py
import pyjisa.autoload
import os
import numpy as np

from typing import Callable, Dict, Generic, List, Tuple, TypeVar, Union

from jisa.devices                import Instrument
from jisa.devices.camera         import Camera as JCamera
from jisa.devices.camera.frame   import Frame, FrameThread, IntFrame, LongFrame, RGBFrame, ShortFrame, U16RGBFrame
from jisa.devices.camera.feature import KineticSeries
from jisa.devices.features       import TemperatureControlled
from jisa                        import Util

from qtpy import uic
from qtpy.QtCore import QTimer, Qt, QThreadPool, Signal
from qtpy.QtGui import QBrush, QColor, QIcon, QImage, QPainter, QPen, QPixmap, QResizeEvent
from qtpy.QtWidgets import *

from nplab.instrument.camera.fastcamera.datastream import DataStreamGUI
from nplab.instrument.camera.fastcamera.widgets import *

import nplab.datafile as df
from nplab.ui.widgets.jisa import JISAConfigPanel

from PIL import Image


C = TypeVar("C", bound=JCamera)

class FastCameraGUI(QWidget, Generic[C]):

    drawSignal            = Signal(QPixmap)
    frameCapturedSignal   = Signal(Frame)
    progressSignal        = Signal(float)
    acquisitionSignal     = Signal(bool)
    exceptionSignal       = Signal(Exception)
    captureCompleteSignal = Signal()
    captureWritingSignal  = Signal()
    mp4Signal             = Signal()
    h5Signal              = Signal()
    gifSignal             = Signal()

    def __init__(self, camera: C, fastCamera, preview=True):

        super().__init__()
        
        # Hold onto camera
        self.camera     = camera
        self.fastCamera = fastCamera

        # Create buffers
        self.buffer                                  = None
        self.params     : List[Instrument.Parameter] = []
        self.stream     : FrameThread                = None
        self.lastWidth  : int                        = None
        self.lastHeight : int                        = None

        # Define types for automatically linked widgets
        self.configBox           : QGroupBox
        self.numberOfFrames      : QSpinBox    
        self.delayTime           : QSpinBox
        self.captureButton       : QPushButton 
        self.liveViewButton      : QPushButton 
        self.cameraImage         : QLabel      
        self.statusGroup         : QGroupBox
        self.streamBox           : QGroupBox
        self.temperatureLabel    : QLabel
        self.currentTemperature  : QLCDNumber
        self.fpsCounter          : QLCDNumber
        self.crosshairButton     : QPushButton
        self.crosshairPixels     : QSpinBox
        self.h5SaveButton        : QPushButton
        self.pngSaveButton       : QPushButton
        self.streamToDiskButton  : QPushButton
        self.streamFile          : QLineEdit
        self.streamBrowse        : QPushButton
        self.mp4Button           : QPushButton
        self.h5Button            : QPushButton
        self.gifButton           : QPushButton
        self.writingMP4          : QLabel
        self.writingH5           : QLabel
        self.writingGIF          : QLabel
        self.deleteButton        : QPushButton
        self.namePattern         : QLineEdit
        self.pngLabel            : QLabel
        self.pngDirectory        : QLineEdit
        self.pngBrowse           : QPushButton
        self.capturedImages      : QGroupBox
        self.h5Label             : QLabel
        self.h5Group             : QLineEdit
        self.countLabel          : QLabel
        self.delayLabel          : QLabel
        self.keepRatio           : QPushButton
        self.progressBar         : QProgressBar
        self.normaliseButton     : QPushButton
        self.kineticGroup        : QGroupBox
         
        # Load UI from file
        if preview:
            uic.loadUi((os.path.dirname(__file__) + '/resources/fcgui.ui'), self)
        else:
            uic.loadUi((os.path.dirname(__file__) + '/resources/fcgui-controls.ui'), self)

        # Create other QT elements
        self.pool         = QThreadPool()
        self.errorMessage = QErrorMessage()
        self.bufferLock   = Lock()
        self.drawLock     = Lock()
        self.configPanel  = JISAConfigPanel(self.camera)

        self.configBox.layout().addWidget(self.configPanel)
        self.progressBar.setVisible(False)

        self.setupStatusMonitoring()
        self.setupStreamer()
        self.setupConnections()

        self.camera.addAcquisitionListener(lambda c, a: self.acquisitionSignal.emit(bool(a)) if c == 0 else None)

        if preview:
            self.camera.addFrameListener(self.frameListener)

        if not isinstance(self.camera, KineticSeries):
            self.layout().removeWidget(self.kineticGroup)
            self.kineticGroup.deleteLater()


    def setupStatusMonitoring(self):

        self.timer = QTimer()
        self.timer.setInterval(1000)

        # Check if the camera implements some sort of temperature control
        if isinstance(self.camera, TemperatureControlled):
            self.timer.timeout.connect(self.updateTemperature)
            self.currentTemperature.setEnabled(True)
            self.temperatureLabel.setEnabled(True)

        else:
            self.currentTemperature.setEnabled(False)
            self.temperatureLabel.setEnabled(False)


        self.timer.timeout.connect(self.updateFPS)
        self.timer.start()


    def setupConnections(self):

        self.captureButton.clicked.connect(self.capture)
        self.liveViewButton.clicked.connect(self.live)
        self.captureWritingSignal.connect(lambda: self.captureButton.setText("Writing..."))
        self.captureCompleteSignal.connect(self.captureComplete)
        self.streamToDiskButton.clicked.connect(self.streamClick)
        self.streamBrowse.clicked.connect(self.browseForStream)
        self.h5SaveButton.clicked.connect(self.updateSaveButtons)
        self.pngSaveButton.clicked.connect(self.updateSaveButtons)
        self.pngBrowse.clicked.connect(self.browsePNGDirectory)
        self.progressSignal.connect(self.updateProgress)
        self.acquisitionSignal.connect(self.updateAcquisition)
        self.exceptionSignal.connect(self.showException)
        self.kineticAcquire.clicked.connect(self.kinetic)

        if hasattr(self, "cameraImage"):
            self.keepRatio.clicked.connect(self.redrawFrame)
            self.crosshairButton.clicked.connect(self.crosshairClick)
            self.frameCapturedSignal.connect(self.frameListener)
            self.drawSignal.connect(self.drawFrame)


    def setupStreamer(self):

        self.writingGIF.setVisible(False)
        self.writingMP4.setVisible(False)
        self.writingH5.setVisible(False)

        def _reenable():

            if not (self.writingMP4.isVisible() or self.writingH5.isVisible() or self.writingGIF.isVisible()):

                if self.deleteButton.isChecked():

                    try:
                        os.remove(self.streamPath)
                    except:
                        pass


                self.streamFile.setDisabled(False)
                self.streamBrowse.setDisabled(False)
                self.streamToDiskButton.setDisabled(False)
                self.mp4Button.setDisabled(False)
                self.h5Button.setDisabled(False)
                self.gifButton.setDisabled(False)
                self.deleteButton.setDisabled(False)
                self.streamToDiskButton.setStyleSheet("")
                self.streamToDiskButton.setText("Start Streaming to Disk")


        def _doneMP4():
            self.writingMP4.setVisible(False)
            _reenable()


        def _doneH5():
            self.writingH5.setVisible(False)
            _reenable()


        def _doneGIF():
            self.writingGIF.setVisible(False)
            _reenable()
        

        def _checkDelete():

            checked = False

            if self.mp4Button.isChecked():
                self.mp4Button.setStyleSheet("color: teal;")
                checked = True
            else:
                self.mp4Button.setStyleSheet("")

            if self.h5Button.isChecked():
                self.h5Button.setStyleSheet("color: purple;")
                checked = True
            else:
                self.h5Button.setStyleSheet("")

            if self.gifButton.isChecked():
                self.gifButton.setStyleSheet("color: navy;")
                checked = True
            else:
                self.gifButton.setStyleSheet("")

            if checked:
                self.deleteButton.setDisabled(False)
            else:
                self.deleteButton.setChecked(False)
                self.deleteButton.setDisabled(True)

            if self.deleteButton.isChecked():
                self.deleteButton.setStyleSheet("color: brown;")
            else:
                self.deleteButton.setStyleSheet("")


        self.mp4Signal.connect(_doneMP4)
        self.h5Signal.connect(_doneH5)
        self.gifSignal.connect(_doneGIF)
        self.mp4Button.clicked.connect(_checkDelete)
        self.h5Button.clicked.connect(_checkDelete)
        self.gifButton.clicked.connect(_checkDelete)
        self.deleteButton.clicked.connect(_checkDelete)


    def resizeEvent(self, a0):

        if not self.camera.isAcquiring():
            self.redrawFrame()

        return super().resizeEvent(a0)


    def updateFPS(self):
        self.fpsCounter.display(self.camera.getAcquisitionRate())


    def updateSaveButtons(self):

        if self.h5SaveButton.isChecked():
            self.h5SaveButton.setStyleSheet("color: purple;")
            self.h5Group.setEnabled(True)
            self.h5Label.setEnabled(True)
        else:
            self.h5SaveButton.setStyleSheet("")
            self.h5Group.setEnabled(False)
            self.h5Label.setEnabled(False)


        if self.pngSaveButton.isChecked():
            self.pngSaveButton.setStyleSheet("color: teal;")
            self.pngLabel.setEnabled(True)
            self.pngDirectory.setEnabled(True)
            self.pngBrowse.setEnabled(True)
        else:
            self.pngSaveButton.setStyleSheet("")
            self.pngLabel.setEnabled(False)
            self.pngDirectory.setEnabled(False)
            self.pngBrowse.setEnabled(False)


    def browsePNGDirectory(self):

        file = QFileDialog.getExistingDirectory()

        if not isinstance(file, str):
            file = file[0]

        if len(file) == 0:
            return
        
        self.pngDirectory.setText(file)


    def crosshairClick(self):

        if self.crosshairButton.isChecked():
            self.crosshairButton.setText("Hide Crosshair")
        else:
            self.crosshairButton.setText("Show Crosshair")

        self.redrawFrame()


    def browseForStream(self):

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

            self.streamAttrs = self.camera.getAllParametersAsMap()
            self.streamPath  = self.streamFile.text()
            self.stream      = self.camera.streamToFile(self.streamPath)

            self.streamToDiskButton.setStyleSheet("color: brown;")
            self.streamToDiskButton.setText("Stop Streaming")

        else:

            self.stream.stop()
            self.stream = None

            self.streamToDiskButton.setDisabled(True)
            self.mp4Button.setDisabled(True)
            self.h5Button.setDisabled(True)
            self.gifButton.setDisabled(True)
            self.deleteButton.setDisabled(True)
            self.streamToDiskButton.setText("Converting...")
            self.streamToDiskButton.setStyleSheet("")

            if self.mp4Button.isChecked():

                self.writingMP4.setVisible(True)

                def _saveMP4():

                    try:
                        self.camera.openFrameReader(self.streamPath).convertToMP4(self.streamPath + ".mp4")
                    finally:
                        self.mp4Signal.emit()

                self.pool.start(_saveMP4)


            if self.h5Button.isChecked():

                self.writingH5.setVisible(True)

                def _saveH5():

                    try:
                        
                        file = df.current()

                        j = 0
                        nm = "Stream %d" % j

                        while nm in file:
                            j += 1
                            nm = "Stream %d" % j

                        group  = file.create_group(nm)

                        self.writeAttributes(group, self.streamAttrs)

                        reader = self.camera.openFrameReader(self.streamPath)

                        i = 0

                        while reader.hasFrame():
                            self.frameToDataset(group, reader.readFrame(), r"frame_%d", i)
                            i += 1

                    finally:
                        reader.close()
                        self.h5Signal.emit()


                self.pool.start(_saveH5)

            if self.gifButton.isChecked():

                self.writingGIF.setVisible(True)

                def _saveGIF():

                    try:

                        reader = self.camera.openFrameReader(self.streamPath)
                        output = self.streamPath + ".gif"
                        images = []
                        last   = None
                        diff   = 0.0

                        while reader.hasFrame():

                            frame     = reader.readFrame()
                            argbArray = np.fromstring( bytes(frame.getARGBData()), 'c' ).reshape( -1, 4 )
                            rgbArray  = argbArray[ :, 2::-1 ]
                            pilData   = rgbArray.reshape( -1 ).tostring()
                            image     = Image.frombuffer("RGB", (frame.getWidth(), frame.getHeight()), pilData, "raw", "RGB", 0, 1 )
                            images.append(image)

                            if diff == 0.0:
                                timestamp = frame.getTimestamp()

                                if last is not None:
                                    diff = timestamp - last

                                last = timestamp

                        dur = diff * len(images) / 1e9

                        image: Image = images[0]
                        images.remove(image)
                        image.save(fp=output, format="GIF", append_images=images, save_all=True, duration=dur, loop=0)

                    finally:
                        self.gifSignal.emit()
                    
                self.pool.start(_saveGIF)


            if not (self.writingMP4.isVisible() or self.writingH5.isVisible() or self.writingGIF.isVisible()):

                if self.deleteButton.isChecked():
                    
                    try:
                        os.remove(self.streamPath)
                    except:
                        pass


                self.streamFile.setDisabled(False)
                self.streamBrowse.setDisabled(False)
                self.streamToDiskButton.setDisabled(False)
                self.mp4Button.setDisabled(False)
                self.h5Button.setDisabled(False)
                self.gifButton.setDisabled(False)
                self.deleteButton.setDisabled(False)
                self.streamToDiskButton.setStyleSheet("")
                self.streamToDiskButton.setText("Start Streaming to Disk")



    def updateTemperature(self):
        self.currentTemperature.display(self.camera.getControlledTemperature())


    def showException(self, e: Exception):
        self.errorMessage.showMessage(str(e))


    def capture(self):

        # Lock down the GUI inputs
        self.captureButton.setDisabled(True)
        self.capturedImages.setDisabled(True)
        self.countLabel.setDisabled(True)
        self.numberOfFrames.setDisabled(True)
        self.delayLabel.setDisabled(True)
        self.delayTime.setDisabled(True)
        self.captureButton.setText("Capturing...")
        self.captureButton.setStyleSheet("color: brown;")
        self.progressBar.setValue(0)
        self.progressBar.setVisible(True)
        self.liveViewButton.setVisible(False)
        self.configPanel.setDisabled(True)

        # Define what we want to happen
        def _thread():

            try:

                wasAcquiring = self.camera.isAcquiring()

                delay   = max(self.delayTime.value(), 0)
                count   = max(self.numberOfFrames.value(), 1)
                timeout = self.camera.getAcquisitionTimeout()
                frames  = []

                if count == 1:

                    frames.append(self.camera.getFrame())
                    self.progressSignal.emit(100.0)
                    self.frameListener(frames[0])
                    self.fastCamera.updateFrame(frames[0])

                else:

                    if not wasAcquiring:
                        self.camera.startAcquisition()

                    queue = self.camera.openFrameQueue(1)

                    for i in range(count - 1):
                        Util.sleep(delay)
                        frames.append(queue.nextFrame(timeout) if timeout > 0 else queue.nextFrame())
                        self.progressSignal.emit(100.0 * ((i + 1) / count))
                    
                    frames.append(queue.nextFrame(timeout) if timeout > 0 else queue.nextFrame())
                    self.progressSignal.emit(100.0)

                    queue.close()
                    queue.clear()

                    if not wasAcquiring:
                        self.camera.stopAcquisition()
                
                if self.h5SaveButton.isChecked():
                    self.captureWritingSignal.emit()
                    self.saveToH5(frames)
                    
                if self.pngSaveButton.isChecked():
                    self.captureWritingSignal.emit()
                    self.savePNGs(frames)
                    
            except Exception as e:
                self.exceptionSignal.emit(e)

            finally:
                # When done, we need to signal the GUI to re-enable everything
                self.captureCompleteSignal.emit()

                if not wasAcquiring:
                    self.camera.stopAcquisition()


        # Give the method to our thread pool to execute in the background
        self.pool.start(_thread)


    def kinetic(self):

        count = self.kineticCount.value()
        acc   = self.kineticAcc.value()
        cycle = self.kineticCycle.value()
        accC  = self.kineticAccCycle.value()

        if isinstance(self.camera, KineticSeries):

            queue = self.camera.getKineticFrameSeries(count, acc, cycle, accC)
            tmo   = self.camera.getAcquisitionTimeout()

            def _wait():

                while queue.isAlive():

                    frame = queue.nextFrame(tmo)
                    self.frameCapturedSignal.emit(frame)

                    if self.h5SaveButton.isChecked():
                        self.saveToH5([frame])

            self.pool.start(_wait)


    def updateProgress(self, progress: float):
        self.progressBar.setValue(int(progress))


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

    
    def updateAcquisition(self, acquiring: bool):

        if acquiring:
            self.liveViewButton.setStyleSheet("color: brown;")
            self.liveViewButton.setText("Stop Continuous Acquisition")
        else:
            self.liveViewButton.setStyleSheet("")
            self.liveViewButton.setText("Start Continuous Acquisition")



    def live(self):

        if self.camera.isAcquiring():
            self.camera.stopAcquisition()
        else:
            self.camera.startAcquisition()


    def frameListener(self, frame: Frame):

        if self.drawLock.locked():
            Util.sleep(10)
            return

        try:

            with self.bufferLock:

                # If the frame size has changed, then we need to recreate the buffer, otherwise we should reuse it
                if self.buffer is None or len(self.buffer) != frame.size():
                    self.buffer = frame.getScaledARGBData() if self.normaliseButton.isChecked() else frame.getARGBData()
                    self.arr    = np.array(self.buffer)
                else:
                    frame.readScaledARGBData(self.buffer) if self.normaliseButton.isChecked() else frame.readARGBData(self.buffer)
                    np.copyto(self.arr, self.buffer)

                # Record dimensions incase we need to redraw before a new frame comes in
                self.lastWidth  = frame.getWidth()
                self.lastHeight = frame.getHeight()

                # Convert the buffer into a pixmap
                pixmap = QPixmap(QImage(self.arr, self.lastWidth, self.lastHeight, QImage.Format.Format_ARGB32))

                # If crosshair is enabled, then paint one on top of the image in the pixmap 
                if self.crosshairButton.isChecked():

                    painter = QPainter(pixmap)
                    midX    = int(self.lastWidth / 2)
                    midY    = int(self.lastHeight  / 2)

                    painter.setPen(QPen(Qt.white, self.crosshairPixels.value()))
                    painter.drawLine(midX, 0, midX, self.lastHeight - 1)
                    painter.drawLine(0, midY, self.lastWidth - 1, midY)
                    painter.end()


                # Display the pixmap, scaled to the size of the GUI element at this moment
                self.drawSignal.emit(pixmap)

        except:
            print("Exception when drawing frame")

        finally:
            # Limit display to 100 Hz. Anything more is just excessive.
            Util.sleep(10)


    def redrawFrame(self):

        with self.bufferLock:

            try:

                # If these haven't been set, then we can't possibly redraw, so give up
                if self.lastWidth is None or self.lastHeight is None:
                    return

                # Convert the buffer into a pixmap
                pixmap = QPixmap(QImage(np.array(self.buffer), self.lastWidth, self.lastHeight, QImage.Format.Format_ARGB32))
                
                # If crosshair is enabled, then paint one on top of the image in the pixmap
                if self.crosshairButton.isChecked():

                    painter = QPainter(pixmap)
                    midX    = int(self.lastWidth / 2)
                    midY    = int(self.lastHeight  / 2)

                    painter.setPen(QPen(Qt.white, self.crosshairPixels.value()))
                    painter.drawLine(midX, 0, midX, self.lastHeight - 1)
                    painter.drawLine(0, midY, self.lastWidth - 1, midY)
                    painter.end()


                # Display the pixmap, scaled to the size of the GUI element at this moment
                self.drawSignal.emit(pixmap)

            except:
                print("Exception when redrawing frame")

            finally:
                # Limit display to 100 Hz. Anything more is just excessive.
                Util.sleep(10)
        

    def drawFrame(self, pixmap: QPixmap):

        with self.drawLock:
            try:
                self.cameraImage.setPixmap(pixmap.scaled(self.cameraImage.width(), self.cameraImage.height(), Qt.KeepAspectRatio if self.keepRatio.isChecked() else Qt.IgnoreAspectRatio))      
            except Exception as e:
                print("Exception occurred when drawing frame." + e)


    def saveToH5(self, frames):

        try:
            file = df.current()
        except:
            self.errorMessage.showMessage("No HDF5 data file currently open to save to.")
            return

        try:

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

            for frame in frames:
                self.frameToDataset(group, frame, pattern, counter)
                counter += 1

        finally:

            file.flush()


    def frameToDataset(self, group: h5py.Group, frame: Frame, pattern: str, counter: int = 0) -> h5py.Dataset:
        
        name = pattern % counter

        while name in group:

            counter += 1
            name     = pattern % counter


        if isinstance(frame, (ShortFrame, IntFrame, LongFrame)):

            ds = group.create_dataset(name, data=np.array(frame.data()).reshape(frame.getHeight(), frame.getWidth()))

        elif isinstance(frame, U16RGBFrame):

            argb2d      = np.array(frame.getLongARGBData()).view(np.uint16).reshape(frame.getHeight(), frame.getWidth(), 4)
            rgb         = np.empty((frame.getHeight(), frame.getWidth(), 3), dtype=np.uint16)
            rgb[..., 0] = argb2d[..., 2]
            rgb[..., 1] = argb2d[..., 1]
            rgb[..., 2] = argb2d[..., 0]
            ds          = group.create_dataset(name, data=rgb)

        else:

            argb2d      = np.array(frame.getARGBData()).view(np.uint8).reshape(frame.getHeight(), frame.getWidth(), 4)
            rgb         = np.empty((frame.getHeight(), frame.getWidth(), 3), dtype=np.uint8)
            rgb[..., 0] = argb2d[..., 2]
            rgb[..., 1] = argb2d[..., 1]
            rgb[..., 2] = argb2d[..., 0]
            ds          = group.create_dataset(name, data=rgb)


        self.writeAttributes(ds, frame)

        return ds


    def writeAttributes(self, ds: h5py.HLObject, data: Union[Dict[str, object], Frame]):

        if isinstance(data, Frame):

            ds.attrs["Timestamp"] = data.getTimestamp()
            data = data.getAttributes()


        for key, value in data.items():
            
            if isinstance(value, Instrument.AutoQuantity):

                ds.attrs[key + ": Auto"]  = value.isAuto()
                value = value.getValue()
                key   = key + ": Value"
        

            if isinstance(value, Instrument.OptionalQuantity):

                ds.attrs[key + ": Used"]  = value.isUsed()
                value = value.getValue()
                key   = key + ": Value"


            if isinstance(value, ResultTable):

                con = [[str(v) for v in r] for r in value.asStringArray()]
                con = [[str(c.getTitle()) for c in value.getColumns()]] + con
                ds.attrs[key] = con

            else:
                ds.attrs[key] = str(value)


    def savePNGs(self, frames):

        counter   = 0
        directory = self.pngDirectory.text()
        pattern   = self.namePattern.text()

        os.makedirs(directory, exist_ok=True)

        if r"%d" not in pattern and r"%s" not in pattern:
            pattern = pattern + r" %d"

        pattern += ".png"

        for frame in frames:

            nm = pattern % counter

            while os.path.isfile(os.path.join(directory, nm)):
                counter += 1
                nm = pattern % counter

            frame.savePNG(os.path.join(directory, nm))

            counter += 1


class FastCameraPreviewGUI(QWidget, Generic[C]):

    drawSignal = Signal(QPixmap)

    def __init__(self, camera: C):

        super().__init__()

        self.camera      = camera
        self.vbox        = QVBoxLayout()
        self.cameraImage = QLabel()
        self.buffer      = None
        self.bufferLock  = Lock()
        self.drawLock    = Lock()
        self.keepRatio   = QPushButton("Keep Aspect Ratio")
        self.lastWidth   = None
        self.lastHeight  = None

        self.keepRatio.setCheckable(True)
        self.keepRatio.setChecked(True)
        self.cameraImage.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored))

        self.setLayout(self.vbox)
        self.vbox.addWidget(self.cameraImage)
        self.vbox.addWidget(self.keepRatio)

        self.camera.addFrameListener(self.frameListener)

        self.drawSignal.connect(self.drawFrame)


    def resizeEvent(self, a0):
        self.redrawFrame()
        return super().resizeEvent(a0)
    

    def frameListener(self, frame: Frame):

        try:

            with self.bufferLock:

                # If the frame size has changed, then we need to recreate the buffer, otherwise we should reuse it
                if self.buffer is None or len(self.buffer) != frame.size():
                    self.buffer = frame.getARGBData()
                else:
                    frame.readARGBData(self.buffer)

                # Record dimensions incase we need to redraw before a new frame comes in
                self.lastWidth  = frame.getWidth()
                self.lastHeight = frame.getHeight()

                # Convert the buffer into a pixmap
                pixmap = QPixmap(QImage(self.buffer, self.lastWidth, self.lastHeight, QImage.Format.Format_ARGB32))

                # # If crosshair is enabled, then paint one on top of the image in the pixmap
                if self.crosshairButton.isChecked():

                    painter = QPainter(pixmap)
                    midX    = int(self.lastWidth / 2)
                    midY    = int(self.lastHeight  / 2)

                    painter.setPen(QPen(Qt.white, self.crosshairPixels.value()))
                    painter.drawLine(midX, 0, midX, self.lastHeight - 1)
                    painter.drawLine(0, midY, self.lastWidth - 1, midY)
                    painter.end()


                # Display the pixmap, scaled to the size of the GUI element at this moment
                self.drawSignal.emit(pixmap)

        except:
            print("Exception when drawing frame")


    def redrawFrame(self):

        with self.bufferLock:

            try:

                # If these haven't been set, then we can't possibly redraw, so give up
                if self.lastWidth is None or self.lastHeight is None:
                    return

                # Convert the buffer into a pixmap
                pixmap = QPixmap(QImage(self.buffer, self.lastWidth, self.lastHeight, QImage.Format.Format_ARGB32))

                # # If crosshair is enabled, then paint one on top of the image in the pixmap
                if self.crosshairButton.isChecked():

                    painter = QPainter(pixmap)
                    midX    = int(self.lastWidth / 2)
                    midY    = int(self.lastHeight  / 2)

                    painter.setPen(QPen(Qt.white, self.crosshairPixels.value()))
                    painter.drawLine(midX, 0, midX, self.lastHeight - 1)
                    painter.drawLine(0, midY, self.lastWidth - 1, midY)
                    painter.end()


                # Display the pixmap, scaled to the size of the GUI element at this moment
                self.drawSignal.emit(pixmap)

            except:
                print("Exception when redrawing frame")
        

    def drawFrame(self, pixmap: QPixmap):
        
        with self.drawLock:
            try:
                self.cameraImage.setPixmap(pixmap.scaled(self.cameraImage.width(), self.cameraImage.height(), Qt.KeepAspectRatio if self.keepRatio.isChecked() else Qt.IgnoreAspectRatio))      
            except:
                print("Exception occurred when drawing frame.")

