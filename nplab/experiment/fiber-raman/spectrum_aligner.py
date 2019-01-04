import numpy as np 
import matplotlib.pyplot as plt 
import sys
from scipy.signal import resample

def find_index_closest_to_value(value, array):
	index = np.argmin(np.abs(array - value))
	return index

def generate_new_xs(previous_xs, current_xs,shift,debug=0):
	assert(shift < 0)
	index = find_index_closest_to_value(current_xs[0],previous_xs)

	diff = previous_xs[index]-current_xs[0]
	
	lower_wavelengths = previous_xs[index+shift:index]
	if debug > 0:
		print previous_xs[index], current_xs[0]
		print "diff:", diff
		print "indices:", index+shift, index
		print "lower_wavelengths", lower_wavelengths

	lower_wavelengths = lower_wavelengths - diff
	assert(len(lower_wavelengths)==np.abs(shift))
	truncated_current = current_xs[0:len(current_xs)+shift]
	assert(len(truncated_current)==len(current_xs)+shift)
	new_xs = np.concatenate([lower_wavelengths, truncated_current])
	print len(new_xs),len(current_xs)
	assert(len(new_xs)==len(current_xs))
	return new_xs

from nplab import datafile as df 
from nplab.analysis.signal_alignment import correlation_align
measurement_file = df.DataFile("measured_spectrum.hdf5","r")
reference_file = df.DataFile("maxwell_room_light_spectrum_calibration.hdf5","r")

reference = np.array(reference_file["calibration"]["spectrum_10"])
ref_xs = reference[0]
inds = np.logical_and(ref_xs >= 400,ref_xs <= 800)

ref_ys = reference[1]
ref_ys = ref_ys[inds]



# sys.exit()
#load data from file, order by center wavelength
data = []
for k in measurement_file["spectra"].keys():
	v = measurement_file["spectra"][k]
	wl =  v.attrs["center_wavelength"]
	xs = np.array(v)[0,:]
	ys = np.array(v)[1,:]
	data = data + [ (v.attrs["center_wavelength"], xs, ys)]

#sort data by center wavelength
data = sorted(data, key= lambda x: x[0])
shifts = []
debug = 1

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
	return outp 

# def recursive_merge(data,shifts):
# 	N = len(data)
# 	if N == 1:
# 		return data[0]
# 	else:
# 		groups = N/2
# 		new_data = []
# 		for i in range(0,2*groups,2):
# 			ys0, ys1 = data[i],data[i+1]
# 			new_data = new_data + [merge_spectra(ys0,ys1,shift[i+1])]

# 		new_shifts = compute_shifts(new_data)
# 		return recursive_merge(new_data,new_shifts)

	
def compute_shifts(data,threshold=-105,debug=0):
	from scipy.interpolate import interp1d
	from nplab.analysis.smoothing import convex_smooth
	shifts = []
	for i in range(1,len(data)):
		d0 = data[i-1]
		d1 = data[i]

		ys0,ys1 = d0[2],d1[2]
		xs0,xs1 = d0[1],d1[1]

		shift,_ = correlation_align(ys0,ys1,upsampling=10.0, return_integer_shift = True)
		shifts.append(shift)
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
	print end_pad_length
	padded_smoothed_shifts = np.concatenate([smoothed_shifts,([smoothed_shifts[-1]]*end_pad_length)])
	assert(len(inds) == len(shifts[inds]))
	if debug > 0:
		fig, ax = plt.subplots(1)
		ax.plot(inds, shifts[inds],"o",label="Threshold shifts [threshold value: {}".format(threshold))
		# ax.plot(inds[0], smoothed,"-",label="Threshold shifts [threshold value: {}".format(threshold))
		ax.plot(range(len(shifts)), shifts,"x-",label="Raw shift values".format(threshold))

		ax.plot(xs_interp, ys_interp ,"x-",label="Linearly interpolated shift values".format(threshold))
		ax.plot(xs_interp, smoothed_shifts ,"x-",label="Smoothed shift values".format(threshold))
		print len(shifts), len(padded_smoothed_shifts)
		ax.plot(range(0,len(shifts)), padded_smoothed_shifts,"x-",label="Smoothed shift values with end-padding")
		
		ax.legend()
		plt.show()

	#pad the end too - so that for every spectrum measured we ge a shift value
	
	padded_smoothed_shifts = [0] + list(padded_smoothed_shifts)
	print len(padded_smoothed_shifts)
	print len(data)
	assert(len(padded_smoothed_shifts)==len(data))
	outp = np.array(np.round(padded_smoothed_shifts),dtype=int)
	# outp = np.array((np.ones(outp.shape)*np.mean(outp)),dtype=int)
	return inds,outp


shifts_indices, ys_shift = compute_shifts(data,debug=1)
# plt.plot(xs_shifts,ys_shifts,'-')
# plt.plot(range(len(all_shifts)),all_shifts,'x')
plt.show()

# spectra = range(34,39)

ys0 = [data[0][2]]
for i in range(1,len(data)):
	ys1 = [data[i][2]]
	ys0 = merge_spectra(ys0,ys1,ys_shift[i])
	print ys0.shape

print ys0.shape

fig, ax = plt.subplots(1)
def apply_function(data_matrix, functions):
	spectrum = np.zeros((len(functions),data_matrix.shape[1]))
	for i in range(ys0.shape[1]):
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
spectrum = apply_function(ys0, [np.median,np.mean,np.std,max_fun,min_fun, len])	

labels = ["median", "mean", "std", "max_fun","min_fun"]
fig, axarr = plt.subplots(2)	
for i in range(spectrum.shape[0]-1):
	axarr[0].plot(spectrum[i,:],label=labels[i])

axarr[1].plot(spectrum[-1,:],label="nonzero Column length")
axarr[0].legend()
axarr[1].legend()
plt.legend()
# plt.show()

fig, [ax,ax_xcs] = plt.subplots(2)
ys0 = spectrum[0,:]
ys0 = ys0 - np.nanmin(ys0)
ys0 = ys0

ref_ys = np.array(resample(ref_ys, len(ys0)))
ref_ys = ref_ys - np.min(ref_ys)
ref_ys = (ref_ys/np.nanmax(ref_ys))*np.nanmax(ys0)

shift,xcs = correlation_align(ys0,ref_ys,upsampling=1.0, return_integer_shift = True)
xs = np.array(range(0,len(ref_ys)))
print "SHIFT", shift
ax.plot(xs,ref_ys,"-",label="Reference")
ax.plot(xs,ys0,label="Spectrum")
ax.plot(xs+shift,ys0,label="Shifted Spectrum")
ax.legend()
plt.show()


sys.exit(0)

# shifted = []
# print len(data)
# for i in range(34,39):
# 	print "i:", i
# 	d0 = data[i-1]
# 	d1 = data[i]

# 	ys0,ys1 = d0[2],d1[2]
# 	xs0,xs1 = d0[1],d1[1]

# 	print i, len(ys_shift),len(data)
# 	shift = ys_shift[i]
# 	print "SHIFT",shift
# 	new_xs = generate_new_xs(previous_xs=xs0, current_xs=xs1,shift=shift,debug=1)
# 	assert(new_xs[0] < xs1[0])

# 	data[i] = (d1[0],new_xs,ys1)

# 	shifted = shifted + [(d1[0],new_xs,xs1,ys1,shift)]
# fig,axarr = plt.subplots(2)
# for i in range(1,len(shifted)):
# 	d = shifted[i]
# 	cwl, xs,old_xs, ys,shift = d[0],d[1],d[2],d[3],d[4]
# 	print i,"shift:", shift
# 	axarr[0].plot(xs,ys,"x-")
# 	axarr[1].plot(old_xs,ys,"x-")

# plt.show() 