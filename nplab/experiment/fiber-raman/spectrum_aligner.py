import numpy as np 
import matplotlib.pyplot as plt 
import sys
from scipy.signal import resample, argrelmax
from nplab import datafile as df 
from nplab.analysis.signal_alignment import correlation_align
from scipy.signal import find_peaks_cwt, argrelmax
from nplab.analysis.wavelets import SUREShrink
from nplab.analysis.smoothing import convex_smooth
from scipy.interpolate import interp1d
from nplab.analysis.smoothing import convex_smooth
	

def least_squares(xs,ys):
	xs_augmented = np.transpose([xs,np.ones(len(xs))])
	m,_,_,_ = np.linalg.lstsq(xs_augmented,ys)
	return m


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
			print "Warning! - No padding of ys0 matrix!"
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


	xs_interp = range(0,np.max(inds)+1)
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
		ax.plot(inds, shifts[inds],"o",label="Threshold shifts [threshold value: {}".format(threshold))
		# ax.plot(inds[0], smoothed,"-",label="Threshold shifts [threshold value: {}".format(threshold))
		ax.plot(range(len(shifts)), shifts,"x-",label="Raw shift values".format(threshold))

		ax.plot(xs_interp, ys_interp ,"x-",label="Linearly interpolated shift values".format(threshold))
		ax.plot(xs_interp, smoothed_shifts ,"x-",label="Smoothed shift values".format(threshold))
		print len(shifts), len(padded_smoothed_shifts)

		ax.plot(padded_smoothed_shifts,"x-",label="Smoothed shift values with end-padding")
		ax.plot(outp,label="Final output")
		ax.legend()
		# plt.show()

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
	for k in measurement_file["spectra"].keys():
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
	peak_indices = argrelmax(ref_ys)[0]


	if debug > 0:
		fig3, ax3 = plt.subplots(1)
		ax3.plot(ref_xs,ref_ys)
		ax3.plot(ref_xs[peak_indices],ref_ys[peak_indices],"o")
		ax3.set_xlabel("Reference Wavelength [nm]")
		ax3.set_ylabel("Counts")
		ax3.set_title("Reference spectrum,\n Wavelength lower bound:{0}\n Wavelength upper bound:{1}".format(lower_wavelength,upper_wavelength))
	return ref_xs, ref_ys

def plot_layers(center_wavelengths, data,mapper,show_plot=True,with_normalisation=False,reference = None):
	fig, ax = plt.subplots(1)
	if reference is not None:
			ref_ys = np.array(reference[1])
			ref_ys = ref_ys - np.nanmin(ref_ys)
			ref_ys = ref_ys/np.nanmax(ref_ys) * 80
			ax.plot(reference[0],ref_ys,color="red")


	for i in range(len(data)):
		center_wl, ys = data[i][0], data[i][2]
		xs = range(len(ys)) 
		if with_normalisation == True:
			ys = ys - np.nanmin(ys)
			ys = ys/np.nanmax(ys)
			ys = i + (ys*0.9) 
		
		wls = [mapper(center_wl,x) for x in range(len(ys))]
		ax.plot(wls,ys,color="blue")
	if show_plot == True:
		plt.show()
	else:
		return ax

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
			ys = i + (ys/(1.1*np.nanmax(ys)))
			axarr2[0].plot(ys,"blue")
		axarr2[0].set_xlim(0,14000)
		axarr2[1].set_xlim(0,14000)

		fig, ax = plt.subplots(1)
		#make different spectra by computing medians, means stdevs etc from the data_matrix
		spectrum = apply_function(data_matrix, [np.median,np.mean,np.std,max_fun,min_fun, len])	

		labels = ["median", "mean", "std", "max_fun","min_fun"]
		fig, axarr = plt.subplots(2)	
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
		wavelengths = range(450,700,1)
		lower_bound = 0
		upper_bound = 1014 
		fig, ax = plt.subplots(1)
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
	
	#Version2 - linear interpolation directly!
	M = len(xs)
	intervals = M - 1
	interval_length = 1/float(intervals)
	rescaling_factor = float(N)/float(M-1)
	new_interval_length = interval_length*rescaling_factor

	new_interval_starts = [i*rescaling_factor for i in range(len(xs))]
	fxs = interp1d(new_interval_starts,xs)
	fys = interp1d(new_interval_starts,ys)
	N_max = int(np.floor(new_interval_starts[-1]))
	assert(N==N_max)
	print M,N,N_max
	new_xs = np.array([fxs(i) for i in range(N)])
	new_ys = np.array([fys(i) for i in range(N)])

	#Version1	
	# ys = zero_min(ys)
	# ys = ys*np.nanmax(max_size)/float(np.nanmax(ys))
	# ys = SUREShrink(ys)
	# ys = resample(ys,N)
	# xs = resample(xs,N)


	array_indices = range(0,len(new_xs))
	wavelengths = new_xs
	[gradient, offset] = least_squares(array_indices,wavelengths)
	if debug > 0:
	
		fig, [ax,ax2] = plt.subplots(2)
		ax.plot(array_indices,wavelengths)
		ax.plot(array_indices,[offset+gradient*x for x in  array_indices],"--",label="least_squares fit")
		ax.legend();

		ax.set_title("Rescale Reference(xs,ys,max_size,N) plot")

		ax2.plot(xs,ys,label="Raw reference")
		ax2.plot(new_xs,new_ys,label="Resampled reference")
		ax2.legend()


	return new_xs, new_ys, gradient, offset

def get_peaks(signal,threshold):
		indices = argrelmax(signal)[0]
		all_peaks =  np.vstack([indices, signal[indices]])
		return peak_threshold(all_peaks, threshold)

def prune_peaks(peaks):
		to_drop = []
		for i in range(peaks.shape[1]):
			v = peaks[:,i]
			print peaks
			diff = [np.linalg.norm(peaks[:,j].T-v) for j in range(peaks.shape[1]) ]
			diff[i] = np.inf
			min_diff = np.argmin(diff)
			print diff
			if diff[min_diff] < 50:
				to_drop.append(min_diff)
		peaks = peaks.T
		peaks = [peaks[i,:] for i in range(peaks.shape[0]) if i not in to_drop]
		peaks = np.array(peaks)
		peaks = peaks.T
		return peaks

def remove_indices(peaks, indices):
	print "peaks:", peaks 
	print "indices:",indices

	peaks = np.array([peaks[:,i] for i in range(peaks.shape[1]) if i not in indices]).T
	return peaks

def link_peaks(signal_peaks, reference_peaks, signal_indices,reference_indices,debug=0):
	signal_peaks = remove_indices(signal_peaks, [i for i in range(signal_peaks.shape[1]) if i not in signal_indices])
	reference_peaks = remove_indices(reference_peaks, [i for i in range(reference_peaks.shape[1]) if i not in reference_indices])
	
	N = min(signal_peaks.shape[1],reference_peaks.shape[1])
	print signal_peaks.shape
	print reference_peaks.shape

	signal_pos = []
	diff = []
	lines = []
	
	for i in range(N):
		xs = [reference_peaks[0,i],signal_peaks[0,i]]
		ys = [reference_peaks[1,i],signal_peaks[1,i]]
		
		signal_pos.append(signal_peaks[0,i])
		diff.append(xs[1]-xs[0])
		lines = lines + [(xs,ys)]
	
	interpolator_function = interp1d(signal_pos, diff,"quadratic")
	
	if debug > 0:
		fig, ax = plt.subplots(1)
		ax.plot(signal_pos,diff,"o-",label="Raw peak shift [indices]")
		interp_diff = [interpolator_function(x) for x in range(int(np.min(signal_pos)),int(np.max(signal_pos)))]
		ax.plot(interp_diff,"-",label="Interpolated peak shift")
		ax.set_xlabel("Array index")
		ax.set_ylabel("Index shift")

	bounds = [int(np.min(signal_pos)),int(np.max(signal_pos))]
	#interpolator_function will generate shift for an array index
	#lines - for plotting 
	return interpolator_function,bounds,lines  
	
def min_max_normalise(ys):
	signal = ys
	signal = signal - np.nanmin(signal)
	signal = signal/np.nanmax(signal)
	return signal

def annotate_points(xs,ys,ax):
	for i in range(len(xs)):
		x = xs[i]
		y = ys[i]
		ax.annotate('i:{0}'.format(i,x,y), xy=(x,y), textcoords='data')
	ax.grid()
def main(debug=1):
	#Measurements and Calibration files
	measurement_file = df.DataFile("measured_spectrum.hdf5","r")
	reference_file = df.DataFile("maxwell_room_light_spectrum_calibration.hdf5","r")

	#Load reference within given range 
	ref_xs, ref_ys = load_reference_data(reference_file,lower_wavelength=430,upper_wavelength=714,debug=debug)
	
	#Load measured data from file
	data = load_measured_data(measurement_file)

	center_wavelengths = [d[0] for d in data]
	#Load the raw counts from the measured data 

	#Merge individual spectra (using median) and normalise to set minimum value to zero
	signal_spectrum,mapper_1 = median_spectrum(data,debug=debug)
	signal_spectrum = zero_min(signal_spectrum)
	#handcrafted truncation to "valid range" where we can see peaks & that matches the reference spectrum
	signal_spectrum = signal_spectrum[1550:10570]
	#Apply smoothing to the measured signal - want to eliminate most false peaks
	signal_spectrum = SUREShrink(signal_spectrum)
	signal_spectrum,_,_ = convex_smooth(signal_spectrum,1.0)

	#rescale the reference and fit a line to the wavelength range [nm]
 	ref_xs,ref_ys, gradient, offset = rescale_reference(xs=ref_xs,ys=ref_ys,max_size=np.nanmax(signal_spectrum),N=len(signal_spectrum),debug=1)
	
 	ref_ys = ref_ys - np.nanmin(ref_ys)
 	ref_ys = ref_ys/float(np.nanmax(ref_ys))

 	signal_spectrum = signal_spectrum - np.nanmin(signal_spectrum)
 	signal_spectrum = signal_spectrum/float(np.nanmax(signal_spectrum))
	#Get peaks from the signal, with thresholding to eliminate low order maxima/minima
	signal_peaks = get_peaks(signal_spectrum,threshold =0.6)
	ref_peaks = get_peaks(ref_ys,threshold =0.7)

	#Link peaks, handcrated to ignore false peaks
	interpolator_function,interpolator_bounds, lines = link_peaks(
		signal_peaks = signal_peaks,
		reference_peaks = ref_peaks,
		signal_indices=[0,1,2,3,4,5,7,8,10,12,13,14,15,16,17,19,21,22,23],
		reference_indices=[0,8,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,26,27]
	)

	if debug > 0:
		fig, ax = plt.subplots(1,figsize=(12,10))
		ax.plot(ref_ys,"-",label="Reference")
		ax.plot(signal_spectrum,label="Signal")
		
		ax.plot(ref_peaks[0,:],ref_peaks[1,:],"o",label="Reference peaks")
		ax.plot(signal_peaks[0,:],signal_peaks[1,:],"o",label="Signal peaks")
		annotate_points(signal_peaks[0,:],signal_peaks[1,:],ax)
		annotate_points(ref_peaks[0,:],ref_peaks[1,:],ax)
		for (xs,ys) in lines:
			ax.plot(xs,ys,"-",color="red")

		ax.set_xlabel("Array index")
		ax.set_ylabel("Counts [arb. units]")

		ax.legend()

	def make_mapper2(interpolator_function,gradient,offset,debug=0):

		def index_to_wavelength(index,with_correction= True):
			index = index - 1550
			try:
				if with_correction:
					alignment_correction = int(np.round(interpolator_function(index)))
					#1550 - zero of median spectrum
					index = index - alignment_correction 
				#this out linear model
				wavelength = index*gradient + offset
				return wavelength
			except:
				return np.nan
		if debug > 0:
			xs = range(1550,10570)
			ys = [index_to_wavelength(x) for x in xs]
			fig, ax = plt.subplots(1)
			ax.plot(xs,ys)
			ax.set_title("Index to wavelength (mapper_2)")		
		return index_to_wavelength

	index_to_wavelength = mapper_2 = make_mapper2(interpolator_function,gradient,offset,debug=debug)
	if debug > 0:
		fig, ax = plt.subplots(1)
		xs = range(np.min(interpolator_bounds),np.max(interpolator_bounds))
		ys = [index_to_wavelength(x) for x in xs]
		plt.plot(xs,ys)

		fig, ax = plt.subplots(1)


		wavelengths_reference = [index_to_wavelength(x,with_correction=False) for x in range(len(ref_ys))]
		rx,ry = load_reference_data(reference_file,lower_wavelength=430,upper_wavelength=714)
		ry = ry - np.nanmin(ry)
		ry= np.array(ry)/np.nanmax(ry)
		ry = ry
		ax.plot(rx,ry,label="Reference spectrum (raw)")
		
		ax.plot(wavelengths_reference,ref_ys,label="Reference spectrum (rescaled)")
		xs = range(interpolator_bounds[0],interpolator_bounds[1])

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
			wavelength= mapper_2(array_index,with_correction=True)
			return wavelength
		except:
			return np.nan	

	#This tests the data
	ax = plot_layers(center_wavelengths=center_wavelengths,data=data,reference = None,mapper=mapper,show_plot=False,with_normalisation=True)
	y = ref_ys

	
	ref_xs, ref_ys = load_reference_data(reference_file,lower_wavelength=430,upper_wavelength=714)
	ax.plot(ref_xs,50* min_max_normalise(ref_ys),label="Raw reference")
	ref_xs,ref_ys, _, _ = rescale_reference(xs=ref_xs,ys=ref_ys,max_size=np.nanmax(signal_spectrum),N=len(signal_spectrum),debug=0)
	ax.plot(ref_xs, 50*min_max_normalise(ref_ys),label="Rescaled reference")

	spectrum,_ = median_spectrum(data)
	spectrum = spectrum[1550:10570]
	indices = np.array(range(len(spectrum)))

	wls = [mapper_2(i+1550,with_correction=False) for i in indices]
	ax.plot(wls, 50*min_max_normalise(spectrum),label="Median stitched spectrum (without correction)")

	wls = [mapper_2(i+1550,with_correction=True) for i in indices]
	ax.plot(wls, 50*min_max_normalise(spectrum),label="Median stitched spectrum (with correction)")
	
	ax.legend()

	if debug> 0:
		plt.show()
	return mapper

mapper = main()
