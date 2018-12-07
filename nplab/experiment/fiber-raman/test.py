import matplotlib.pyplot as plt
import numpy as np

from nplab import datafile as df 
from nplab.analysis.smoothing import convex_smooth

from nplab.instrument.spectrometer.acton import Acton
from nplab.instrument.camera.pixis import Pixis
from Pacton import Pacton


print "Starting.."
print "Pixis..."
pix = Pixis(with_start_up=False)
print "Acton..."
act = Acton("COM7",debug=1)
print "Done..."

pacton = Pacton(pixis=pix,acton=act)

print "Measuring..."
# smoothed,raw = pact.get_pixel_response_calibration_spectrum()

# def spectrum_pixel_offset(spectrum_1,spectrum_2):
# 	sp1 = spectrum_1
# 	sp2 = spectrum_2

# 	sp1 = sp1 - np.mean(sp1)
# 	sp2 = sp2 - np.mean(sp2)

# 	#compute cross correlation to match
# 	xcs = np.correlate(sp1,sp2,mode="full")
# 	#perform fftshift to center zero offset on 0th position
# 	xcs = np.fft.fftshift(xcs)

# 	#return peak position of xcs
# 	return np.argmax(xcs),np.array(xcs)

# def pixel_wavelength_conversion(pixel_offset,wavelength_offset):
# 	return wavelength_offset/float(pixel_offset)

# act.set_wavelength(600,fast=True)
# img = pacton.get_image(600,roi = [0,1024,600,800],debug=1)

# plt.imshow(img)
# plt.show()


fig,ax = plt.subplots(1)
pacton.get_pixel_response_calibration_spectrum()
for wl in range(550,700,10):
	spectrum,wavelengths = pacton.get_spectrum(wl,subtract_background=True,roi=[0,1024,600,800],debug=1)
	ax.plot(wavelengths[50:],spectrum[50:])

plt.show()		


# print "Calibrating..."
# pacton.calibrate(range(600,624,3),with_background_subtraction=False,plot=True,debug=1)
# print "Done!"


# import sys 
# sys.exit(0)
# fig, axarr = plt.subplots(2,figsize=(8,16))
# wavelengths = 
# spectra = []
# for wl in wavelengths:

# 	act.set_wavelength(wl,fast=True,debug=1)  
# 	sp = np.array(pix.get_spectrum())
# 	sp_bgsub = sp #- smoothed
# 	spectra.append(sp_bgsub)

# 	axarr[0].plot(sp_bgsub,label="WL: {} nm".format(wl))
# 	axarr[0].set_xlabel("Pixel index")
# 	axarr[0].set_ylabel("Counts")

# for i in range(0,len(spectra)-1):
# 	for j in range(i+1,len(spectra)):
# 		sp1 = spectra[i]
# 		sp1 = (sp1 - np.mean(sp1))
# 		sp2 = spectra[j]
# 		sp2 = (sp2 - np.mean(sp2))
		
# 		peak = spectrum_pixel_offset(sp1,sp2)
# 		xcs = np.correlate(sp1,sp2,mode="full")
# 		xcs = np.fft.fftshift(xcs)

# 		pos = spectrum_pixel_offset(sp1,sp2)
# 		axarr[1].plot(xcs,"-",label="spectra: {0} vs {1}".format(wavelengths[i],wavelengths[j]))
# 		axarr[1].plot(pos,xcs[pos],"o")

# 		d_wl = wavelengths[j] - wavelengths[i]
# 		d_pixel = pos 
# 		sf = pixel_wavelength_conversion(d_pixel,d_wl)
# 		print "Scale factor:", sf


# axarr[0].minorticks_on()
# axarr[1].minorticks_on()

# axarr[0].grid(which="major",linestyle="-",linewidth=0.4)
# axarr[1].grid(which="major",linestyle="-",linewidth=0.4)

# axarr[0].grid(which="minor",linestyle="--",linewidth=0.2)
# axarr[1].grid(which="minor",linestyle="--",linewidth=0.2)

# axarr[0].legend()
# axarr[1].legend()
# axarr[0].set_title("Background subtracted spectra")
# # act.set_wavelength(580,fast=True,debug=1)
# # sp2 = np.array(pix.get_spectrum())
# # plt.plot(sp2-smoothed,label="Spectrum 580")


# ys = np.array(calibration_spectrum)

# ymin = np.min(ys)
# ys = ys - ymin
# smoothed,_,_ = convex_smooth(ys,2)
# smoothed = np.array(smoothed) + ymin
# smoothed[0:3] = np.mean(calibration_spectrum[0:3])
# fig, axarr = plt.subplots(2,figsize=(8,16))
# axarr[0].plot(raw,'x',label="Data",alpha=0.5)
# axarr[0].plot(smoothed,'-',label="Smoothed",alpha=0.6)

# axarr[1].semilogx(raw,'x',label="Data",alpha=0.5)
# axarr[1].semilogx(smoothed,'-',label="Smoothed",alpha=0.6)



# axarr[0].legend()
# axarr[1].legend()

# ax.set_title("Calibration spectrum")
# ax.set_xlabel("Pixel index")
# ax.set_ylabel("Pixel response")


# plt.savefig("images/calibration_spectrum.png")

# for wl in range(0,900,10):

# 	act.set_wavelength(wl,fast=True,debug=1)
# 	# img = pact.get_image(wl,debug=1)
# 	img = pix.get_roi()
# 	spectrum = pix.get_spectrum()
# 	# spectrum = pact.get_spectrum(wl,debug=1)#y_min=300,y_max=400)
# 	fig, axarr = plt.subplots(2)


# 	print "Showing.."
# 	axarr[0].imshow(img)
# 	axarr[1].plot(spectrum)
# 	axarr[0].set_title("Wavelength:{}".format(wl))
# 	plt.savefig("images/take_{}.png".format(wl))

pix.ShutDown()
# plt.show()

# file = df.DataFile("test.hdf5","w")

# def scan_spectrum(pacton,start_wavelength,stop_wavelength,step_size):

# 	wavelengths = xrange(start_wavelength,stop_wavelength,step_size)
# 	spectra = []
# 	for wl in wavelengths:
# 		spectra.append(pact.get_spectrum(wl))

# 	ax = plt.gca()
# 	for s in spectra:
# 		ax.plot(s)

# fig, ax = plt.subplots(1)
# scan_spectrum(pact,600,650,25)
# plt.show()

		
# print "Stopped.."
