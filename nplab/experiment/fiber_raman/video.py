from __future__ import print_function
from __future__ import absolute_import
from nplab.instrument.spectrometer.acton_2300i import Acton
import pyqtgraph as pg
from PyQt4 import QtGui
import numpy as np 
import time

from nplab.instrument.camera.Picam.pixis import Pixis
from .Pacton import Pacton


def initialize_measurement(acton_port, exposure_time = 50):
	print("Starting..")

	print("Pixis...")
	p = Pixis(debug=1)

	p.StartUp()
	print("Acton...")
	act = Acton(port=acton_port, debug=1)
	print("Done...")
	pacton = Pacton(pixis=p,acton=act)
	print("Measuring...")
	p.SetExposureTime(exposure_time)
	return pacton

def make_app(pacton, refresh_time):

	app = QtGui.QApplication([])

	w = QtGui.QWidget()

	plot = pg.ImageView()

	layout = QtGui.QGridLayout() 
	w.setLayout(layout) 

	layout.addWidget(plot, 0, 0) 

	w.show()

	timer = pg.QtCore.QTimer() 
	def update(): 
		_,img = pacton.pixis.raw_snapshot()
		plot.setImage(img.T)

	timer.timeout.connect(update)
	timer.start(refresh_time)
	app.exec_()

pacton = initialize_measurement("COM5",300)
pacton.get_image(0)
make_app(pacton,50)