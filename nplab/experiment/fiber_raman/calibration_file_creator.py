from __future__ import print_function
from __future__ import absolute_import
from builtins import range
import matplotlib.pyplot as plt
import numpy as np

from nplab import datafile as df 
from nplab.analysis.smoothing import convex_smooth

from nplab.instrument.spectrometer.acton_2300i import Acton
from nplab.instrument.camera.Picam.pixis import Pixis
from .Pacton import Pacton

from nplab.instrument.light_sources.SolsTiS import SolsTiS
import time

laser_ip = ('172.24.60.15',39933)

LASER = SolsTiS(laser_ip)

def get_wavelength(laser):
	laser.system_status()
	wl = laser.message_in_history[-1]["message"]["parameters"]["wavelength"]
	return wl[0]

def tune(wl,laser):
	laser.change_wavelength(wl)
	max_tries = 10
	while (np.absolute(wl - get_wavelength(laser)) > 0.05) and max_tries > 0:
		time.sleep(0.5)
		max_tries = max_tries - 1
	return


def make_measurement(data_group,laser_wavelength,center_wavelength,reruns=0):
	spectrum,_ = pacton.get_spectrum(center_wavelength,subtract_background=True,roi=[0,1024,600,800],debug=1)
	if reruns > 0:
		N = spectrum.shape[0]
		spectra = np.zeros((reruns,N))
		spectra[0,:] = spectrum
		for i in range(1,reruns):
			spectrum,_ = pacton.get_spectrum(center_wavelength,subtract_background=True,roi=[0,1024,600,800],debug=1)
			spectra[i,:] = spectrum
		spectrum = np.mean(spectra,axis=0)

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

	f = df.DataFile("ir_calibration_1200gmm.hdf5","a")
	g = f.require_group("calibration")
	print("Starting..")

	print("Pixis...")
	p = Pixis(debug=0)

	p.StartUp()
	print("Acton...")
	act = Acton("COM5",debug=0)
	print("Done...")
	pacton = Pacton(pixis=p,acton=act)
	
	print("Setting grating...")
	pacton.acton.set_grating(1) # 1 : 1200g/mm, 2: 300g/mm
	# print pacton.acton.read_grating()
	p.SetExposureTime(200)
	pacton.get_pixel_response_calibration_spectrum()

	# tune(wl,laser)
	# measured = get_wavelength(laser)
	# print wl, measured

	center_wavelengths = list(range(870,890,10))
	p.SetExposureTime(200)
	
	
	bandwidth = 10
	for c_wl in center_wavelengths:
		laser_wavelengths = np.linspace(c_wl-bandwidth,c_wl+bandwidth,5)
		for l_wl in laser_wavelengths:
			print("acton wl: {0}, laser wl: {1}".format(c_wl,l_wl))
			tune(l_wl,LASER)
			measured_wl = get_wavelength(LASER)	
			#plot_measurement(pacton,c_wl)
			make_measurement(g,measured_wl,c_wl,reruns=5)

	
	p.ShutDown()
