from __future__ import print_function
import os 
import numpy as np 
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt 
from nplab import datafile as df

DIRPATH = os.path.dirname(os.path.abspath(__file__))

def least_squares(xs,ys):
	xs_augmented = np.transpose([xs,np.ones(len(xs))])
	m,_,_,_ = np.linalg.lstsq(xs_augmented,ys)
	return m

def single_position_fit(spectra,calibration_wavelengths,center_wavelength = None,debug =0):
	'''
	spectra: spectra taken at same position (center wavelength) but with different incident laser wavelengths
	calibration_wavelengths - the wavelengths of the laser
	'''
	
	xs = peak_positions = [np.argmax(s) for s in spectra]
	ys = calibration_wavelengths

	#assuming that this is linear in the give pixel range
	[gradient, offset] = least_squares(xs,ys)
	if debug > 0:
		fig, ax = plt.subplots(1)
		ax.plot(xs,ys,'x',label="data")
		ax.plot(xs,gradient*np.array(xs) + offset,label="linear fit")
		ax.set_xlabel("Pixel index")
		ax.set_ylabel("Wavelength [nm]")
		ax.set_title("Pixel position vs Wavelength\n Center wavelength: {0}".format(center_wavelength))

		plt.show()
	return gradient, offset


def scan_fit(dataset,debug = 0):

	center_wls = []
	offsets = []
	gradients = []

	if debug > 0:
		print("-="*10)
		print("scan_fit dataset debug")
		print("-="*10)
		for d in dataset:
			print(d)
	for (center_wavelength,spectra,calibration_wavelengths) in dataset:

		if len(spectra) > 1:

			print(center_wavelength,len(spectra),len(calibration_wavelengths))
			gradient, offset = single_position_fit(spectra,calibration_wavelengths,debug=debug,center_wavelength=center_wavelength)

			center_wls = center_wls + [center_wavelength]
			offsets = offsets + [offset]
			gradients = gradients + [gradient]

	if debug > 0:
		print("len(offsets)", len(offsets))
		print("len(gradients)", len(gradients))
		fig, [ax1,ax2] = plt.subplots(2)
		ax1.plot(center_wls,offsets,'x-')
		ax1.set_title("scan_fit: center wavelength vs wavelength offset (=$\lambda$ at pixel_index=0)")
		ax2.plot(center_wls,gradients,'x-')
		ax1.set_xlabel("Center wavelength [nm]")
		ax1.set_ylabel("Pixel 0 wavelength (offset) [nm]")
		ax2.set_title("scan_fit: center wavelength vs wavelength gradient (for determining wavelength for pixel_index > 0)")
		ax2.set_xlabel("Center wavelength [nm]")
		ax2.set_ylabel("Wavelength increment (gradient) [nm/pixel]")
		
		plt.show()

	print("center_wls:",np.max(center_wls),np.min(center_wls))
	def mapper(cw,pixel_index):
		wavelength_offset = interp1d(center_wls,offsets,kind='linear')
		wavelength_gradient = interp1d(center_wls,gradients,kind='linear')

		return wavelength_offset(cw) + wavelength_gradient(cw)*pixel_index

	return mapper


def test(debug):
	if debug:
		print("---TESTING---")

	pixels = np.arange(0,1014)
	def make_test_spectrum(mu,sigma=30.0):
		return np.exp(-(pixels-mu)**2/float(2*sigma**2))
	
	center_wavelengths=700
	calibration_wavelengths=[704,726,744]
	centers = [300,600,800]
	spectra = [make_test_spectrum(p) for p in centers]
	dset0 = [center_wavelengths,spectra,calibration_wavelengths]

	center_wavelengths=740
	calibration_wavelengths=[744,766,784]
	centers = [200,500,900]
	spectra = [make_test_spectrum(p) for p in centers]
	dset1 = [center_wavelengths,spectra,calibration_wavelengths]


	fig, ax = plt.subplots(1)
	for s in spectra:
		plt.plot(pixels,s)
	plt.show()

	dataset = [dset0,dset1]
	scan_fit(dataset,debug=1)

def main(filepath,debug=0):
	f =df.DataFile(filepath,"r")
	g = f["calibration"]
	keys = list(g.keys())

	center_wavelengths = []
	for k in keys:
		center_wavelengths = center_wavelengths + [g[k].attrs["center_wavelength"]]
		
	center_wavelengths = sorted(np.unique(center_wavelengths))
	print("main:max center wavelength:",np.max(center_wavelengths))

	dataset = []
	for cw in center_wavelengths:

		entry = (cw,[],[])
		for k in keys:
			if g[k].attrs["center_wavelength"] == cw:
				entry[2].append(g[k].attrs["laser_wavelength"])
				entry[1].append(np.array(g[k]))
		dataset.append(entry)

	# print "-="*10
	# for d in dataset:
	# 	print d
	# print "-="*10
	mapper = scan_fit(dataset,debug=debug)

	return mapper


def grating_1200gmm(debug=0):
	return main(DIRPATH+"\\"+"ir_calibration_1200gmm.hdf5",debug=debug)

def grating_300gmm(debug=0):
	return main(DIRPATH+"\\"+"ir_calibration_300gmm.hdf5",debug=debug)

def mapper_tester_300gmm(mapper):

	center_wavelengths = np.linspace(760,910,10)
	pixels = np.arange(0,1014,1)
	# print pixels
	# print mapper
	# print center_wavelengths
	for cw in center_wavelengths:
		print("cW:",cw)
		wls = [mapper(cw,p) for p in pixels]
		plt.plot(pixels,wls,label="center wavelength:{}".format(cw))
	plt.xlabel("Pixel index")
	plt.ylabel("Wavelength [nm]")
	plt.legend()
	plt.show()

def mapper_tester_1200gmm(mapper):

	center_wavelengths = np.linspace(750,885,10)
	pixels = np.arange(0,1014,1)
	# print pixels
	# print mapper
	# print center_wavelengths
	for cw in center_wavelengths:
		print(cw)
		wls = []
		for p in pixels:
			# print cw,p
			wls.append(mapper(cw,p))
		# wls = [mapper(cw,p) for p in pixels]
		plt.plot(pixels,wls,label="center wavelength:{}".format(cw))
	plt.xlabel("Pixel index")
	plt.ylabel("Wavelength [nm]")
	plt.legend()
	plt.show()
			

if __name__ == "__main__":
	mapper = grating_1200gmm(1)
	mapper_tester_1200gmm(mapper)
	# mapper_tester(mapper) #for 1200 g/mm grating - hand crafted code
	# test(debug=1)
	print("pass")