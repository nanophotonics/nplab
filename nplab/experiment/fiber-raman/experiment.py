import numpy as np 
import matplotlib.pyplot as plt 

from nplab.instrument.spectrometer.acton_2300i import Acton
from nplab.instrument.camera.Picam.pixis import Pixis
from Pacton import Pacton
from nplab import datafile as df 

def initialize_datafile(path):
	"""
	This function defines the format of the group structure

	Parameters are path on filesystem 
	
	"""
	f = df.DataFile(path, 'a')

	return f 


def initialize_measurement(acton_port, exposure_time = 100):
	print "Starting.."

	print "Pixis..."
	p = Pixis(debug=1)

	p.StartUp()
	print "Acton..."
	act = Acton(port=acton_port, debug=1)
	print "Done..."
	pacton = Pacton(pixis=p,acton=act)
	print "Measuring..."
	p.SetExposureTime(exposure_time)
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


if __name__ == "__main__":
	file = initialize_datafile('.\experiment_testfile.hdf5')
	pacton = initialize_measurement('COM5', 100)
	for i in range(5):
		single_shot(pacton,file,show_ = False)