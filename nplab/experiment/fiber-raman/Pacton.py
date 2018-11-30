import numpy as np 
import matplotlib.pyplot as plt 


from nplab.analysis.smoothing import convex_smooth
from nplab.instrument import Instrument


def spectrum_pixel_offset(spectrum_1,spectrum_2):
	sp1 = spectrum_1
	sp2 = spectrum_2

	sp1 = sp1 - np.mean(sp1)
	sp2 = sp2 - np.mean(sp2)

	#compute cross correlation to match
	xcs = np.correlate(sp1,sp2,mode="full")
	#perform fftshift to center zero offset on 0th position
	xcs = np.fft.fftshift(xcs)

	#return peak position of xcs
	return np.argmax(xcs),np.array(xcs)

def pixel_wavelength_conversion(pixel_offset,wavelength_offset):
	return wavelength_offset/float(pixel_offset)

class Pacton(Instrument):

	def __init__(self,pixis,acton,boundary_cut=5):

		self.pixis = pixis
		self.acton = acton 

		#####
		# Wavelength bounds
		#####
		self.min_wavelength = 0.000 #[nm]
		self.max_wavelength = 1200.000 #[nm]
		
		self.boundary_cut = boundary_cut


		#Used to background subtract when stitching together spectra
		#To initialize run: get_pixel_response_calibration_spectrum
		self.pixel_response = None
		self.raw_pixel_response = None

		#conversion factor from pixels to nm [units: nm/pixel]
		#default obtained from calibration
		self.pixel_to_wl_sf = 0.0289082 

	def get_image(self,center_wavelength,roi = None,debug=0):
		self.acton.set_wavelength(center_wavelength,blocking=True,debug=debug)
		if roi is not None:

			if debug>0: print "starting try-catch"
			try:
				[x_min,x_max,y_min,y_max] = roi
				if debug > 0:
					print "Pacton.get_image: region of interest:", roi
				return self.pixis.get_roi(x_min=x_min, x_max = x_max, y_min=y_min,y_max = y_max,debug=debug)

			except: 
				raise ValueError("Unable to unpack region of interest")
		else:
			return self.pixis.get_roi()
		

	def pixel_to_wavelength(self,pixels,center_wavelength):
		center_pixel = np.round(self.pixis.x_max)/2.0
		if self.pixel_to_wl_sf is None:
			raise ValueError("No conversion factor set, please run Pacton.calibrate routine")
		else:
			wavelengths = center_wavelength + self.pixel_to_wl_sf*(pixels - center_pixel)
		return wavelengths

	def get_pixel_response_calibration_spectrum(self,debug=0):
		'''
		Scan over spectrum in the region where you don't expect to see anyting (ie. UV)
		Take spectra at each position and average. This then gives you the pixel response (strange I know).
		Smooth the average using cvx and use this in furthre processing for background subtraction on the LHS
		to make it easier to stitch together spectra
		'''
		wavelengths = range(50,80,10)
		spectra = []
		for wl in wavelengths:
			self.acton.set_wavelength(wl,blocking=True,fast=True,debug=debug)
			spectrum,_= self.pixis.get_spectrum()
			spectra.append(spectrum)

		spectra = np.array(spectra)
		calibration_spectrum = np.mean(spectra,axis=0)
		#subtract minimum value to remove edge effects
		ys = np.array(calibration_spectrum)
		
		ymin = np.min(ys)
		ys = ys - ymin
		#smooth to get less fluctuations in background
		smoothed,_,_ = convex_smooth(ys,2)
		smoothed = np.array(smoothed) + ymin
		#replace first 3 pixel values with 
		smoothed[0:3] = np.mean(calibration_spectrum[0:3])
		
		self.pixel_response = smoothed
		self.raw_pixel_response = calibration_spectrum
		return smoothed, calibration_spectrum

	def get_spectrum(self,center_wavelength,subtract_background=True, roi = None,debug=0):

		self.acton.set_wavelength(center_wavelength,blocking=True,debug=debug)
		if subtract_background == True and self.pixel_response is None:
			raise ValueError("Error getting spectrum with background subtraction - no background to subtract, please run: Pacton.get_pixel_response_calibration_spectrum ") 
		if roi is not None:
			try:
				[x_min,x_max,y_min,y_max] = roi
				spectrum,pixels = self.pixis.get_spectrum(x_min=x_min, x_max = x_max, y_min=y_min,y_max = y_max)

			except: 
				raise ValueError("Unable to unpack region of interest")
		else:
			spectrum,pixels = self.pixis.get_spectrum()
		
		if subtract_background == True:
			spectrum = np.array(spectrum) - self.pixel_response
		wavelengths = self.pixel_to_wavelength(pixels,center_wavelength)
		return spectrum,wavelengths

	
	def calibrate(self,wavelengths,with_background_subtraction= False,plot=False,debug = 0):
		if with_background_subtraction == True:
			smoothed,_ = self.get_pixel_response_calibration_spectrum()

		if plot == True:
			fig, axarr = plt.subplots(2,figsize=(8,16))
		
		#grab calibration spectra
		spectra = []
		for wl in wavelengths:
			self.acton.set_wavelength(wl,fast=True,debug=debug)  
			sp = np.array(self.pixis.get_spectrum()[0])
			if with_background_subtraction == True:

				sp_bgsub = sp - smoothed
			else:
				sp_bgsub = sp
			spectra.append(sp_bgsub)

			if plot == True:
				axarr[0].plot(sp_bgsub,label="WL: {} nm".format(wl))
				
		#compute correlations to match positions
		scale_factors =  []
		for i in range(0,len(spectra)-1):
			for j in range(i+1,len(spectra)):
				sp1 = spectra[i]
				sp2 = spectra[j]
				peak,xcs = spectrum_pixel_offset(sp1,sp2)
				if debug > 0:
					print "Correlation peak (=pixel offset): {0}".format(peak)
				d_wl = wavelengths[j] - wavelengths[i]
				d_pixel = peak
				sf = pixel_wavelength_conversion(d_pixel,d_wl)
				scale_factors.append(sf)

				if plot == True:
					p  =axarr[1].plot(xcs,"-",label="spectra: {0}nm vs {1}nm [offset: {2:.3g}, scale factor: {3:.3g}]".format(wavelengths[i],wavelengths[j],peak,sf))
					axarr[1].plot(peak,xcs[peak],"o",color=p[0].get_color())

				if debug > 0:
					print "Scale factor [{0} nm] vs [{1} nm]:".format(wavelengths[i],wavelengths[j]), sf

		#compute mean of scaling factor
		sf_mean = np.mean(scale_factors)
		sf_std = np.std(scale_factors)
		if debug > 0:
			print "Final pixel to wavelength conversion  factor: {0:4g} +/- {1:4g} [nm/pixel]".format(sf_mean,sf_std)
		
		if plot == True:
			axarr[0].legend()
			axarr[0].set_xlabel("Pixel index")
			axarr[0].set_ylabel("Counts")

			axarr[1].legend()

			axarr[1].set_xlabel("Pixel offset")
			axarr[1].set_ylabel("Crosscorrelation [unnormalized]")

			plt.show()

		#set the device pixel to wavelength scale factor
		self.pixel_to_wl_sf = sf_mean 
		return sf_mean,sf_std


	def scan_spectrum(self,start_wavelength, stop_wavelength,step_size = 10):
		
		assert(start_wavelength >= self.min_wavelength)
		assert(stop_wavelength <= self.max_wavelength)
		assert(step_size > 0)

			
		pass
		#make center wavelengths
		#scan over center wavelengths
		#stitch together by finding peak in correlation("valid")
		# return stitched spectrum

if __name__ == "__main__":
	print "pass"