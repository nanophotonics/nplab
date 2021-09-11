from __future__ import print_function
from __future__ import absolute_import
import numpy as np 
import matplotlib.pyplot as plt 

from nplab.instrument.spectrometer.acton_2300i import Acton
from nplab.instrument.camera.Picam.pixis import Pixis
from .Pacton import Pacton


def initialize_measurement(acton_port, exposure_time = 100):
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

def single_shot(acton_port="COM5",center_wavelength = 840, exposure_time =10000):
	pacton = initialize_measurement(acton_port=acton_port,exposure_time=exposure_time)
	fi = [0,1024,514,600]
	img = pacton.get_image(center_wavelength,roi = fi ,debug=0)
	fig, ax = plt.subplots(1)
	ax.imshow(img, cmap='viridis')
	plt.show()

single_shot()
