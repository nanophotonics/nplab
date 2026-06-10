import numpy as np
import pyjisa.autoload

from jisa.devices.camera import Camera, FakeCamera, Andor2, Andor3, Lumenera
from jisa.devices.camera.frame import Frame
from jisa.devices.features import *
from jisa.devices.camera.feature import *
from jisa.devices.spectrometer import CameraSpectrometer, FakeSpectrometer, OceanOptics
from jisa.devices.smu import K1234
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication

from nplab.instrument.camera.camera_with_location import CameraWithLocation
from nplab.instrument.camera.fastcamera import FastCamera
from nplab.instrument.spectrometer.fastspectrometer import FastSpectrometer
from nplab.instrument.spectrometer.fastspectrometer.csconfig import CSConfigGUI
from nplab.instrument.stage import DummyStage
from nplab.utils.gui_generator import GuiGenerator

from java.lang import Throwable, Exception as JException

# ==== CONNECTING ====

# Connect to camera
camera = Andor2(0)


# ==== CONFIGURING ====
# You should be able to find every parameter you can configure in the form of a camera.setXXX(...) method
# where XXX is the name of the parameter.

camera.setIntegrationTime(10e-6)          # 10 us exposure time
camera.setImageMode(Camera.ImageMode.ROI) # Set camera to Region-of-Interest mode

# Returns a list of all image modes this camera is capable of
possibleModes = camera.getImageModes()
print(possibleModes)

# Could set to different modes depending on what's available
# camera.setImageMode(Camera.ImageMode.FULL_VERTICAL_BINNING)
# camera.setImageMode(Camera.ImageMode.FULL_IMAGE)
# camera.setImageMode(Camera.ImageMode.MULTI_TRACK)
# camera.setImageMode(Camera.ImageMode.SINGLE_TRACK)
# camera.setImageMode(Camera.ImageMode.TRACK_SEQUENCE)

# Set region of interest (512x256 image centred on the sensor)
camera.setImageWidth(512)
camera.setImageHeight(256)
camera.setImageCentredX(True)
camera.setImageCentredY(True)

# If it's temperature controlled, enable and set target of 183 K
if isinstance(camera, TemperatureControlled):
    camera.setTemperatureControlEnabled(True)
    camera.setTemperatureControlTarget(183.0)
    camera.waitForTemperatureControlStable()

# ==== SYNCHRONOUS ACQUISITION ====
# Asking the camera for frame(s) and having it return them synchronously is quite easy

# Acquire a single frame
frame: Frame = camera.getFrame()

# Acquire 10 frames as a list
frames = camera.getFrameSeries(10)

# If the camera is capable of taking a kinetic series, do it
if isinstance(camera, KineticSeries):
    # 10 frames, 1 accumulation per frame, 50 ms between frames, 50 ms between accumulations
    series = camera.getKineticFrameSeries(10, 1, 50e-3, 50e-3)


# You can write a frame to a PNG file by calling
frame.savePNG("/path/to/file.png")

# Frames can be turned into raw numpy arrays using
frameData = np.array(frame.getRawImage())

# ==== CONTINUOUS ACQUISITION ====

# We can start the camera continuously acquiring by calling
camera.startAcquisition()

# And can be stopped by calling
camera.stopAcquisition()

# Then, to access the frames acquired, we have a few options.

# The first is to define a "Frame Listener", which is a bit of code that will get given each frame
# as it comes in and does something with it. These listeners will reject new frames while they're
# still working with a previous frame, so they are lossy, but a good choice for things like updating
# a gui.

def frameListener(frame: Frame):
    # do something with the frame here, for example here we will just print its timestamp
    print("New frame, timestamp: %d" % frame.getTimestamp())

# Attach the listener to the camera
listener = camera.addFrameListener(frameListener)

# To acquire frames losslessly, we can open a "Frame Queue". This is a buffer that will hold a copy
# of every single frame that comes in via continuous acquisition.
queue = camera.openFrameQueue() # or to limit its size (e.g., to 100 frames): camera.openFrameQueue(100)

# then, one can remove frames from the head of the queue one-by-one like so
while queue.isAlive():
    frame = queue.nextFrame(10000) # Will timeout after waiting 10 seconds (10000 ms) for a frame, don't specify a timeout if you want it to wait forever
    print("New frame, timestamp: %d" % frame.getTimestamp())


# Therefore, if our while loop cannot get through the frames as fast as they are coming in, then the queue
# will grow.

# To help with threading, you can open a queue and spawn a thread to work with whatever enters the queue all in one go
# using the startFrameThread method

def forEachFrame(frame: Frame):
    print("New frame, timestamp: %d" % frame.getTimestamp())

thread = camera.startFrameThread(forEachFrame)

# Then, later, you can stop the thread gracefully
thread.stop()

# Or, forcefully
thread.stopNow()

# You can even launch pre-defined thread designed to stream frame data directly to disk by calling
thread = camera.streamToFile("/path/to/file.bin")


