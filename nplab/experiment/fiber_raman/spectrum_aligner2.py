from __future__ import division
from __future__ import print_function
from builtins import range
from past.utils import old_div
import numpy as np 
import matplotlib.pyplot as plt 
import sys
from scipy.signal import resample
from nplab import datafile as df 
from nplab.analysis.signal_alignment import correlation_align
from scipy.signal import find_peaks_cwt, argrelmax,correlate
from nplab.analysis.wavelets import SUREShrink
from nplab.analysis.smoothing import convex_smooth
from scipy.interpolate import interp1d
from nplab.analysis.smoothing import convex_smooth
	

# def find_index_closest_to_value(value, array):
# 	index = np.argmin(np.abs(array - value))
# 	return index

# def generate_new_xs(previous_xs, current_xs,shift,debug=0):
# 	assert(shift < 0)
# 	index = find_index_closest_to_value(current_xs[0],previous_xs)

# 	diff = previous_xs[index]-current_xs[0]
	
# 	lower_wavelengths = previous_xs[index+shift:index]
# 	if debug > 0:
# 		print previous_xs[index], current_xs[0]
# 		print "diff:", diff
# 		print "indices:", index+shift, index
# 		print "lower_wavelengths", lower_wavelengths

# 	lower_wavelengths = lower_wavelengths - diff
# 	assert(len(lower_wavelengths)==np.abs(shift))
# 	truncated_current = current_xs[0:len(current_xs)+shift]
# 	assert(len(truncated_current)==len(current_xs)+shift)
# 	new_xs = np.concatenate([lower_wavelengths, truncated_current])
# 	print len(new_xs),len(current_xs)
# 	assert(len(new_xs)==len(current_xs))
# 	return new_xs

def least_squares(xs,ys):
	xs_augmented = np.transpose([xs,np.ones(len(xs))])
	m,_,_,_ = np.linalg.lstsq(xs_augmented,ys)
	return m

def annotate_points(xs,ys,ax):
	assert(len(xs)==len(ys))
	texts = []
	for i in range(len(xs)):
		label = "ind:{}".format(i)
		print(xs[i], ys[i],label)
		t = ax.text(xs[i],ys[i],label,fontsize=10)
		texts.append(t)
	return texts

def merge_spectra(ys0,ys1,shift):
	shift = np.abs(shift)
	ys0 = np.array(ys0)
	ys1 = np.array(ys1)
	prev_row = ys0[-1,:]
	first_nonzero = np.min(np.where(prev_row > 0))
	relative_shift = first_nonzero + shift
	#new dimension: relative_shift + ys1.shape[1]
	#padding: relative_shift + ys1.shape[1] - ys0.shape[1]
	if (relative_shift + ys1.shape[1]) - ys0.shape[1] > 0:
		ys0_pad = np.zeros( (ys0.shape[0],(relative_shift + ys1.shape[1]) - ys0.shape[1]))
		ys0 = np.concatenate((ys0,ys0_pad),axis=1)
	else:
		if debug> 0:
			print("Warning! - No padding of ys0 matrix!")
	ys1_pad = np.zeros((1,relative_shift))
	
	ys1 =np.concatenate((ys1_pad,ys1),axis=1)
	outp = np.vstack((ys0,ys1))
	return outp, relative_shift

def apply_function(data_matrix, functions):
	spectrum = np.zeros((len(functions),data_matrix.shape[1]))
	for i in range(data_matrix.shape[1]):
		column = data_matrix[:,i]
		nonzero_indices = np.where(column > 0)
		
		for j,f in enumerate(functions):
			spectrum[j,i] = f(column[nonzero_indices])

	return spectrum
def max_fun(column):
	if len(column) > 0:
		return np.max(column)
	else:
		return 0
def min_fun(column):
	if len(column) > 0:
		return np.min(column)
	else:
		return 0

	
def compute_shifts(spectra,threshold=-105,debug=0):
	shifts = []
	for i in range(1,len(spectra)):
		ys0 = spectra[i-1]
		ys1 = spectra[i]

		shift,_ = correlation_align(ys0,ys1,upsampling=1.0, return_integer_shift = True)
		shifts.append(shift)
	#threshold - some shifts fail when there are no spectral features	
	shifts = np.array(shifts)
	inds = np.where(shifts <= threshold)
	inds = inds[0]


	xs_interp = list(range(0,np.max(inds)+1))
	f0 = interp1d(inds, shifts[inds])
	ys_interp = [f0(x) for x in xs_interp]
	pad_length = 5
	smoothed_shifts,_,_ = convex_smooth([ys_interp[0]]*pad_length+ys_interp,0.0,"quadratic")
	smoothed_shifts= smoothed_shifts[pad_length:]
	end_pad_length = len(shifts) - len(smoothed_shifts) 
	# print end_pad_length
	padded_smoothed_shifts = np.concatenate([smoothed_shifts,([smoothed_shifts[-1]]*end_pad_length)])
	padded_smoothed_shifts = [0] + list(padded_smoothed_shifts)
	outp = np.array(np.round(padded_smoothed_shifts),dtype=int)
	assert(len(inds) == len(shifts[inds]))
	N = len(outp)
	
	if debug > 0:
		fig, ax = plt.subplots(1)
		ax.set_title("fname:compute_shifts, debug plot")
		ax.plot(inds, shifts[inds],"o",label="Threshold shifts [threshold value: {}".format(threshold))
		# ax.plot(inds[0], smoothed,"-",label="Threshold shifts [threshold value: {}".format(threshold))
		ax.plot(list(range(len(shifts))), shifts,"x-",label="Raw shift values".format(threshold))

		ax.plot(xs_interp, ys_interp ,"x-",label="Linearly interpolated shift values".format(threshold))
		ax.plot(xs_interp, smoothed_shifts ,"x-",label="Smoothed shift values".format(threshold))
		print(len(shifts), len(padded_smoothed_shifts))

		ax.plot(padded_smoothed_shifts,"x-",label="Smoothed shift values with end-padding")
		ax.plot(outp,label="Final output")
		ax.legend()
		plt.show()

	assert(len(padded_smoothed_shifts)==len(spectra))
	return inds,outp

def peak_threshold(peaks,sf=1.0):
		xs = peaks[0,:]
		ys = peaks[1,:]
		median_ys = np.median(ys)
		
		ind = ys > median_ys*sf
		xs = xs[ind]
		ys = ys[ind]
		return np.vstack([xs,ys])

def load_measured_data(measurement_file):
	#measurement file - HDF5 file contanining individual measurements from the Acton/Pixis
	data = []
	for k in list(measurement_file["spectra"].keys()):
		v = measurement_file["spectra"][k]
		wl =  v.attrs["center_wavelength"]
		xs = np.array(v)[0,:]
		ys = np.array(v)[1,:]
		#make array of data
		data = data + [ (v.attrs["center_wavelength"], xs, ys)]

	#sort data by center wavelength
	data = sorted(data, key= lambda x: x[0])
	return data 

def load_reference_data(reference_file,lower_wavelength,upper_wavelength, debug = 0):
	lower_wl = np.floor(430)
	upper_wl = np.ceil(714)
	reference = np.array(reference_file["calibration"]["spectrum_10"])
	ref_xs = reference[0]
	ref_ys = reference[1]
	#Get valid indices
	inds = np.logical_and(ref_xs >= lower_wl,ref_xs <= upper_wl)
	#Get valid intensities
	ref_ys = ref_ys[inds]
	ref_xs = ref_xs[inds]
	if debug > 0:
		fig3, ax3 = plt.subplots(1)
		ax3.plot(ref_xs,ref_ys)
		ax3.set_xlabel("Reference Wavelength [nm]")
		ax3.set_ylabel("Counts")
		ax3.set_title("Reference spectrum,\n Wavelength lower bound:{0}\n Wavelength upper bound:{1}".format(lower_wavelength,upper_wavelength))
	return ref_xs, ref_ys

def plot_layers(center_wavelengths, data,mapper,show_plot=True):
	fig, ax = plt.subplots(1)
	ax.set_title("fname: plot_layers, debug plot")
	for i in range(len(data)):
		center_wl, ys = data[i][0], data[i][2]
		xs = list(range(len(ys))) 
		
		ys = ys - np.nanmin(ys)
		ys = i + (old_div(ys,(1.1*np.nanmax(ys)))) 
		wls = [mapper(center_wl,x) for x in range(len(ys))]
		plt.plot(wls,ys,color="blue")
	if show_plot == True:
		plt.show()

def make_data_matrix(data):
	spectra = [d[2] for d in data]
	#Compute shifts between each spectrum
	shifts_indices, ys_shift = compute_shifts(spectra,debug=0)
	data_matrix = np.array([data[0][2]])
	relative_shifts = []
	for i in range(1,len(data)):
		ys1 = [data[i][2]]
		data_matrix,relative_shift = merge_spectra(data_matrix,ys1,ys_shift[i])
		relative_shifts = relative_shifts + [relative_shift]
	# absolute_offsets = [relative_shifts[0:i]) for i in range(len(relative_shifts))]
	return relative_shifts, data_matrix
		
def median_spectrum(data,debug=0):
	
	absolute_offsets, data_matrix = make_data_matrix(data)
	absolute_offsets = [0] + absolute_offsets 		# print ys0.shape

	if debug > 0:
		fig2, axarr2 = plt.subplots(2)
		for i in range(data_matrix.shape[0]):
			ys = data_matrix[i,:]
			ys = ys - np.nanmin(ys)
			ys = i + (old_div(ys,(1.1*np.nanmax(ys))))
			axarr2[0].plot(ys,"blue")
		axarr2[0].set_xlim(0,14000)
		axarr2[1].set_xlim(0,14000)

		
		#make different spectra by computing medians, means stdevs etc from the data_matrix
		spectrum = apply_function(data_matrix, [np.median,np.mean,np.std,max_fun,min_fun, len])	

		labels = ["median", "mean", "std", "max_fun","min_fun"]
		fig, axarr = plt.subplots(2)	
		axarr[0].set_title("fname: median_spectrum, debug plot 1")
		for i in range(spectrum.shape[0]-1):
			x = spectrum[i,:]
			x = x[~np.isnan(x)]
			axarr[0].plot(spectrum[i,:],label=labels[i])
		axarr2[1].plot(spectrum[0,:],"blue")
		
		axarr[1].plot(spectrum[-1,:],label="nonzero Column length")
		axarr[0].legend()
		axarr[1].legend()

	center_wavelengths = [d[0] for d in data]
	
	def pixel_to_index_map_generator(debug = 0):
		center_to_offset = interp1d(center_wavelengths,absolute_offsets)
		
		def mapper_1(center_wavelength,pixel_index):
			offset = int(np.round(center_to_offset(center_wavelength))) 
			return offset + pixel_index
		
		return mapper_1

	pixel_to_index = pixel_to_index_map_generator()
	
	if debug > 0:
		wavelengths = list(range(450,700,1))
		lower_bound = 0
		upper_bound = 1014 
		fig, ax = plt.subplots(1)
		ax.set_title("fname: median_spectrum, debug plot 3")
		ax.plot(wavelengths, [pixel_to_index(wl,lower_bound) for wl in wavelengths],label="Leftmost pixel index (0) (real pixel value: 10)")
		ax.plot(wavelengths, [pixel_to_index(wl,upper_bound) for wl in wavelengths],label="Rightmost pixel index (1014)")
		ax.legend()
		ax.set_xlabel("Wavelength [nm]")
		ax.set_ylabel("Array index") 


	#Merged spectrum taken by computing median of nonzero values in each column
	output = apply_function(data_matrix,[np.median])
	return output[0,:],pixel_to_index

def zero_min(xs,with_nan_replacement=True):
	xs = xs - np.nanmin(xs)
	xs = np.nan_to_num(xs,0)
	return xs


def rescale_reference(xs,ys,max_size,N,debug=0):
	#Normalise and rescale so that the 
	ys = zero_min(ys)
	ys = ys*np.nanmax(max_size)/float(np.nanmax(ys))
	

	#Smooth the reference and resample to the same length as the stitched spectrum
	ys = SUREShrink(ys)
	ys = resample(ys,N)

	#Resample the wavelength scale as well:
	xs = resample(xs,N)

	[gradient, offset] = least_squares(list(range(0,len(xs))),xs)
	if debug > 0:
	
		fig, ax = plt.subplots(1)
		ax.set_title("fname: rescale_reference, debug plot 0")
		ax.plot(xs)
		plt.plot(list(range(0,len(xs))),[offset+gradient*x for x in  range(0,len(xs))],label="least_squares fit")
		plt.legend();
	return xs, ys, gradient, offset

def get_peaks(signal,threshold):
		indices = argrelmax(signal)[0]
		all_peaks =  np.vstack([indices, signal[indices]])
		return peak_threshold(all_peaks, threshold)

def prune_peaks(peaks):
		to_drop = []
		for i in range(peaks.shape[1]):
			v = peaks[:,i]
			print(peaks)
			diff = [np.linalg.norm(peaks[:,j].T-v) for j in range(peaks.shape[1]) ]
			diff[i] = np.inf
			min_diff = np.argmin(diff)
			print(diff)
			if diff[min_diff] < 50:
				to_drop.append(min_diff)
		peaks = peaks.T
		peaks = [peaks[i,:] for i in range(peaks.shape[0]) if i not in to_drop]
		peaks = np.array(peaks)
		peaks = peaks.T
		return peaks

def remove_indices(peaks, indices):
	peaks = np.array([peaks[:,i] for i in range(peaks.shape[1]) if i not in indices]).T
	return peaks

def link_peaks(signal_peaks, reference_peaks, ignored_signal_indices,ignored_reference_indices,debug=0):
	signal_peaks = remove_indices(signal_peaks,ignored_signal_indices)
	reference_peaks = remove_indices(reference_peaks,ignored_reference_indices)

	signal_pos = []
	diff = []
	lines = []
	
	for i in range(min(reference_peaks.shape[1],signal_peaks.shape[1])):
		xs = [reference_peaks[0,i],signal_peaks[0,i]]
		ys = [reference_peaks[1,i],signal_peaks[1,i]]
		
		signal_pos.append(signal_peaks[0,i])
		diff.append(xs[1]-xs[0])
		lines = lines + [(xs,ys)]
	
	interpolator_function = interp1d(signal_pos, diff,"quadratic")
	
	if debug > 0:
		fig, ax = plt.subplots(1)
		ax.set_title("fname: link_peaks, debug plot 0")
		ax.plot(signal_pos,diff,"o-",label="Raw peak shift [indices]")
		interp_diff = [interpolator_function(x) for x in range(int(np.min(signal_pos)),int(np.max(signal_pos)))]
		ax.plot(interp_diff,"-",label="Interpolated peak shift")
		ax.set_xlabel("Array index")
		ax.set_ylabel("Index shift")
		ax.legend()

	bounds = [int(np.min(signal_pos)),int(np.max(signal_pos))]
	#interpolator_function will generate shift for an array index
	#lines - for plotting 
	return interpolator_function,bounds,lines  
		

def main(debug=0):
	#Measurements and Calibration files
	measurement_file = df.DataFile("measured_spectrum.hdf5","r")
	reference_file = df.DataFile("maxwell_room_light_spectrum_calibration.hdf5","r")

	#Load reference within given range 
	ref_xs, ref_ys = load_reference_data(reference_file,lower_wavelength=430,upper_wavelength=714)
	
	#Load measured data from file
	data = load_measured_data(measurement_file)

	center_wavelengths = [d[0] for d in data]
	#Load the raw counts from the measured data 

	#Merge individual spectra (using median) and normalise to set minimum value to zero
	signal_spectrum,mapper_1 = median_spectrum(data,debug=1)
	signal_spectrum = zero_min(signal_spectrum)
	#handcrafted truncation to "valid range" where we can see peaks & that matches the reference spectrum
	signal_spectrum = signal_spectrum[1550:10570]
	#Apply smoothing to the measured signal - want to eliminate most false peaks
	signal_spectrum = SUREShrink(signal_spectrum)
	signal_spectrum,_,_ = convex_smooth(signal_spectrum,1.0)

	#rescale the reference and fit a line to the wavelength range [nm]
 	ref_xs,ref_ys, gradient, offset = rescale_reference(xs=ref_xs,ys=ref_ys,max_size=np.nanmax(signal_spectrum),N=len(signal_spectrum),debug=1)
	

	#Get peaks from the signal, with thresholding to eliminate low order maxima/minima
	signal_peaks = get_peaks(signal_spectrum,threshold =1.0)
	ref_peaks = get_peaks(ref_ys,threshold =2.0)

	#Link peaks, handcrated to ignore false peaks
	interpolator_function,interpolator_bounds, lines = link_peaks(
		signal_peaks = signal_peaks,
		reference_peaks = ref_peaks,
		ignored_signal_indices=[3,8,11,13,19,22,23],
		ignored_reference_indices=[11,14,18],
		debug = debug
	)

	if debug > 0:
		fig, ax = plt.subplots(1,figsize=(12,10))
		ax.set_title("fname: main, debug 0")
		ax.plot(ref_ys,"-",label="Reference")
		ax.plot(signal_spectrum,label="Signal")


		
		ax.plot(ref_peaks[0,:],ref_peaks[1,:],"o",label="Reference peaks")
		t1s = annotate_points(ref_peaks[0,:],ref_peaks[1,:],ax)
		ax.plot(signal_peaks[0,:],signal_peaks[1,:],"o",label="Signal peaks")
		t2s = annotate_points(signal_peaks[0,:],signal_peaks[1,:],ax)
		
		for (xs,ys) in lines:
			ax.plot(xs,ys,"-",color="red")

		ax.set_xlabel("Array index")
		ax.set_ylabel("Counts [arb. units]")
		
		ax.legend()

	def make_mapper2(interpolator_function,gradient,offset):

		def index_to_wavelength(index,with_correction= True):
			
			if with_correction:
				alignment_correction = int(np.round(interpolator_function(index)))
				index = index - alignment_correction
			#this out linear model
			wavelength = index*gradient + offset
			return wavelength

		return index_to_wavelength

	index_to_wavelength = mapper_2 = make_mapper2(interpolator_function,gradient,offset)
	if debug > 0:
		fig, ax = plt.subplots(1)
		ax.set_title("fname: main, debug plot 1")
		xs = list(range(np.min(interpolator_bounds),np.max(interpolator_bounds)))
		ys = [index_to_wavelength(x) for x in xs]
		plt.plot(xs,ys)

		fig, ax = plt.subplots(1)
		ax.set_title("fname: main, debug plot 2")
		wavelengths_reference = [index_to_wavelength(x,with_correction=False) for x in range(len(ref_ys))]
		ax.plot(wavelengths_reference,ref_ys,label="Reference spectrum (rescaled)")
		xs = list(range(interpolator_bounds[0],interpolator_bounds[1]))

		ax.plot([index_to_wavelength(x,with_correction=True) for x in xs],[signal_spectrum[x] for x in xs],label="Stitched signal (corrected)")
		ax.plot([index_to_wavelength(x,with_correction=False) for x in xs],[signal_spectrum[x] for x in xs],alpha=0.4,label="Stitched signal (uncorrected)")
		ax.set_ylim(0)

		ax.set_xlabel("Wavelength [nm]")
		ax.set_ylabel("Intensity (arb. units)")
		ax.set_title("Alignment to reference spectrum\n Reference: Ocean Optics Spectrometer\n Signal: Acton+Pixis")
		ax.legend()

		
	# mapper_1 : maps from (center_wavelength, pixel_index) to index in spectrum array
	# mapper_2 : maps from index in spectrum array to wavelenegth
	def mapper(center_wavelength, pixel_index):
		try:
			array_index = mapper_1(center_wavelength,pixel_index)
			wavelength= mapper_2(array_index)
			return wavelength
		except:
			return np.nan

	if debug> 0:

		plt.show()

	#This tests the data
	plot_layers(center_wavelengths, data,mapper,show_plot=True)
	return mapper


mapper = main(1)
