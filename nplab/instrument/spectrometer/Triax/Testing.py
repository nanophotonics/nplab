# -*- coding: utf-8 -*-
"""
Created on Wed Aug 08 14:48:05 2018

@author: jpg66


"""

from nplab.instrument.spectrometer.seabreeze import OceanOpticsSpectrometer
from nplab.instrument.camera.lumenera import LumeneraCamera
from nplab.instrument.camera.camera_with_location import CameraWithLocation
from nplab.instrument.spectrometer.spectrometer_aligner import SpectrometerAligner
from nplab.instrument.stage.prior import ProScan

from nplab.instrument.shutter.BX51_uniblitz import Uniblitz


from nplab.instrument.spectrometer.Triax.Trandor_Lab5 import Trandor




cam = LumeneraCamera(1)
stage = ProScan("COM1",hardware_version=2)
CWL = CameraWithLocation(cam, stage)
CWL.show_gui(blocking=False)

spectrometer = OceanOpticsSpectrometer(0)
spectrometer.show_gui(blocking = False)

#aligner
aligner = SpectrometerAligner(spectrometer,stage)

# Display white light shutter control

whiteShutter = Uniblitz("COM8")
whiteShutter.show_gui(blocking=False)
#
trandor=Trandor(whiteShutter)
Trandor.HSSpeed=2
trandor.Grating(1)
trandor.triax.Slit(100)

#trandor.SetParameter('SetTemperature',-90)
#trandor.CoolerON()
andor_gui = trandor.get_qt_ui()
andor_gui.show()




