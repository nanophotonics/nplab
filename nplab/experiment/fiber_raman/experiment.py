from __future__ import print_function
from __future__ import absolute_import
from builtins import zip
from builtins import range
import numpy as np 
import matplotlib.pyplot as plt 

from nplab.instrument.spectrometer.acton_2300i import Acton
from nplab.instrument.camera.Picam.pixis import Pixis
from .Pacton import Pacton
from nplab import datafile as df 

from .spectrum_aligner_ir import grating_300gmm as get_wavelength_map #grating_300gmm
mapper = get_wavelength_map()

def SetSensorTemperatureSetPoint(self,temperature):
        param_name = "PicamParameter_SensorTemperatureSetPoint"
        return self.set_parameter(parameter_name=param_name,parameter_value=temperature)

def nm_to_raman_shift(laser_wavelength,wavelength):
	raman_shift = 1e7*(1.0/laser_wavelength - 1.0/wavelength)
	return raman_shift

def initialize_datafile(path):
	"""
	This function defines the format of the group structure

	Parameters are path on filesystem 
	
	"""
	f = df.DataFile(path, 'a')

	return f 


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
	# print pacton.acton.read_grating()
	pacton.acton.set_grating(1)
	# print "New grating",pacton.acton.read_grating_name()  
	return pacton

# Maunually find the COM port of Acton Spectrometer - set exposure time (default)


def single_shot(pacton, file, center_wavelength = 0, show_ = True):
	data_group = file.require_group("zero_wavelength_images")
	img = pacton.get_image(center_wavelength,debug=0)
	exptime = pacton.pixis.GetExposureTime()
	attrs = {"exposure_time":exptime,"center_wavelength":center_wavelength}

	data_group.create_dataset("image_%d",data=img, attrs = attrs)
	data_group.file.flush()
	if show_ == True:
		#exercise: put in if statement, only run when suitable flag (ie. input parameter is set to true)
		fig, ax = plt.subplots(1)
		ax.imshow(img, cmap='gray')
		plt.show()


def get_spectrum(pacton,file,y_roi,center_wavelength,exposure_time,show_= False, debug = 0, laser_wavelength = None):

	if debug > 0:
		print("y_roi",y_roi)
		print("center_wavelength",center_wavelength)
		print("exposure_time",exposure_time)
	spectrum_group = file.require_group("spectrum")

	#run calibration to get rid of low pixel value high intensity peaks due to camera response
	
	#get spectrum, drop interpolated wavelengths - they are wrong!
	[ymin,ymax] = y_roi
	xmin,xmax = [0,1024] #default to be over entire range!
	roi = [xmin,xmax,ymin,ymax]
	
	if debug > 0: print("Fiddling with exposure...")
	previous_exposure_time = pacton.pixis.GetExposureTime()
	pacton.pixis.SetExposureTime(exposure_time)
	if debug > 0: print("Getting spectrum...")
	spectrum,_ = pacton.get_spectrum(center_wavelength=center_wavelength,roi=roi)
	
	pacton.pixis.SetExposureTime(previous_exposure_time)
	
	pixel_indices = np.arange(0,1014)
	
	if debug > 0: print("Starting wavelength map...") 
	wavelengths = [mapper(center_wavelength,i) for i in pixel_indices]
	if laser_wavelength is not None:
		raman_shifts = [nm_to_raman_shift(laser_wavelength=laser_wavelength,wavelength=wl) for wl in wavelengths]
	attrs = {
		"wavelengths":wavelengths,
		"raman_shift": raman_shifts,
		"center_wavelength":center_wavelength,
		"roi":roi,
		"exposure_time[ms]": exposure_time
	}
	if debug > 0: print("writing data...")
	spectrum_group.create_dataset("series_%d",data=spectrum,attrs=attrs)

	if show_ == True:
		if laser_wavelength is None:
			fig, ax =plt.subplots(1)
			ax.plot(wavelengths,spectrum)
			ax.set_xlabel("wavelength [nm]")
			ax.set_ylabel("intensity [a.u.]")
		elif laser_wavelength is not None:
			fig, [ax1,ax2] = plt.subplots(2)
			ax1.plot(wavelengths,spectrum)
			ax2.plot(raman_shifts,spectrum)

			ax1.set_xlabel("wavelength [nm]")
			ax1.set_ylabel("intensity [a.u.]")
			ax2.set_xlabel("raman shift [$cm^{-1}$]")
			ax2.set_ylabel("intensity [a.u.]")
		plt.show()



def experiment(pacton, file, functions,argss,kwargss):
	for f, args,kwargs in zip(functions,argss,kwargss):
		f(pacton,file,*args,**kwargs)

	return 0


if __name__ == "__main__":
	file = initialize_datafile('C:\\Users\\Hera\\Desktop\\New folder\\20190315\\spectra\\ECDMCCenter840_vc1percent.hdf5')
	pacton = initialize_measurement('COM5', 100)

	pacton.get_pixel_response_calibration_spectrum()
	# experiment(pacton,file, [single_shot],[()],[({"show_":True})])
	for i in range(30):
		get_spectrum(pacton,file,y_roi=[514,600],center_wavelength=840,exposure_time=10000,laser_wavelength=785,debug=0)
		print(i)
	#single_shot(pacton,file,show_ = True)
