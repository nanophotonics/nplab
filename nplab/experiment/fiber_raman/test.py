from __future__ import print_function
from __future__ import absolute_import
import matplotlib.pyplot as plt
import numpy as np

from nplab import datafile as df 
from nplab.analysis.smoothing import convex_smooth

from nplab.instrument.spectrometer.acton_2300i import Acton
from nplab.instrument.camera.Picam.pixis import Pixis
from .Pacton import Pacton


def make_measurement(data_group,laser_wavelength,center_wavelength):
	spectrum,_ = pacton.get_spectrum(center_wavelength,subtract_background=True,roi=[0,1024,600,800],debug=1)
	data_group.create_dataset("spectrum"+"_%d",data=spectrum, attrs = {"center_wavelength":center_wavelength,"laser_wavelength":laser_wavelength})
	data_group.file.flush()
	return


def initialize_measurement():
	f = df.DataFile("ir_calibration.hdf5","a")
	g = f.require_group("calibration")
	print("Starting..")

	print("Pixis...")
	p = Pixis(debug=1)

	p.StartUp()
	print("Acton...")
	act = Acton("COM7",debug=1)
	print("Done...")
	pacton = Pacton(pixis=p,acton=act)
	print("Measuring...")
	fig,ax = plt.subplots(1)
	p.SetExposureTime(500)
	pacton.get_pixel_response_calibration_spectrum()
	return pacton, g 

def plot_measurement(pacton, center_wavelength):
	fig,ax = plt.subplots(1)
	spectrum,_ = pacton.get_spectrum(center_wavelength,subtract_background=True,roi=[0,1024,600,800],debug=1)
	ax.plot(spectrum)
	plt.show()

if __name__ == "__main__":

	f = df.DataFile("ir_calibration.hdf5","a")
	g = f.require_group("calibration")
	print("Starting..")

	print("Pixis...")
	p = Pixis(debug=1)

	p.StartUp()
	print("Acton...")
	act = Acton("COM7",debug=1)
	print("Done...")
	pacton = Pacton(pixis=p,acton=act)
	print("Measuring...")
	fig,ax = plt.subplots(1)
	p.SetExposureTime(500)
	pacton.get_pixel_response_calibration_spectrum()

	center_wavelength = 895
	laser_wavelength = 905.0

	# make_measurement(g,laser_wavelength,center_wavelength)

	# spectrum,_ = pacton.get_spectrum(center_wavelength,subtract_background=True,roi=[0,1024,600,800],debug=1)
	# ax.plot(spectrum)
	# plt.show()

	plot_measurement()
	p.ShutDown()
