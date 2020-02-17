from __future__ import print_function
from __future__ import absolute_import

from .pixis import Pixis256EQt
import pyqtgraph as pg
from PyQt5 import QtGui
import numpy as np 
import time


EXPOSURE =1 
def initialize_measurement():
	p = Pixis256EQt()
	p.exposure = EXPOSURE
	return p

def make_app(pixis, refresh_time):
	print("one")
	app = QtGui.QApplication([])
	print("two")

	w = QtGui.QWidget()
	plot = pg.ImageView()

	layout = QtGui.QGridLayout() 
	w.setLayout(layout) 
	layout.addWidget(plot, 0, 0) 
	w.show()
	
	timer = pg.QtCore.QTimer() 
	def update(): 

		img = pixis.read_image(pixis.exposure, timing='timed', mode='kinetics', new=False, end= True, k_size=1)
		# img = np.random.uniform(0,1,(500,500))
		plot.setImage(img.T)

	timer.timeout.connect(update)
	timer.start(refresh_time)
	app.exec_()

pixis = initialize_measurement()
make_app(pixis,50)

