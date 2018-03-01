import numpy as np
import matplotlib.pyplot as plt
import math
import scipy.signal

def signal_diff(voltage):
	d_voltage = voltage[0:-1] - voltage[1:]
	return d_voltage


def threshold(voltages, count_threshold = 0.5):
	vmin = np.min(voltages)
	vmax = np.max(voltages)
	vspan = abs(vmax-vmin)
	#Piecewise difference between voltage measurements
	#	+ve if rise edge
	#	-ve if falling edge
	#Assertions:
	#	No consequtive +ve,+ve or -ve,-ve edges
	#	+ve followed by -ve and -ve followed by +ve
	diff = signal_diff(voltages)

	#threshold the absolute values of the pulses, relative to the fraction of the Vpp value
	abs_threshold = np.absolute(diff) > count_threshold*vspan
	
	#Get signs of the pulses
	#Expected outputs
	# +1 - rising edge
	# -1 - falling edge
	#  0 - no edge
	pulses = np.sign(diff*abs_threshold)

	assert(pulses.shape==diff.shape)
	for i in xrange(len(pulses)): #DELETE LOOP
		assert(pulses[i] in [-1,0,1])

	#Get indices of the pulse positions
	nonzero_indices = np.flatnonzero(pulses)
 
	assert(len(nonzero_indices) == int(np.sum(np.absolute(pulses)))),"NONZERO LENGTH:{0},ABS SUM PULSES:{1}".format(len(nonzero_indices),np.sum(np.absolute(pulses)))
	for i in xrange(len(nonzero_indices)): #DELETE LOOP
		assert(pulses[nonzero_indices[i]] != 0)

	#Clean up consecutive pulses that are +ve,+ve or -ve,-ve:
	# Example:
	# 0 1 -1 1 1 1 -1 1 -1 -1 
	#          | |  	    |
	# 0 1 -1 1 0 0 -1 1 -1  0


	for i in xrange(1,len(nonzero_indices)):
		if pulses[nonzero_indices[i]]== pulses[nonzero_indices[i-1]]:
			pulses[nonzero_indices[i]] == 0

	#return absolute values of the pulses
	return np.absolute(pulses)
	
def binning(thresholded, index_bin_width):
	#length of input thresholded array of 0s and 1s

	thresholded_len = len(thresholded)

	for i in xrange(thresholded_len): #DELETE LOOP
		assert(thresholded[i] in [0,1])

	#length of output [int]
	outp_len = int(math.ceil(float(thresholded_len)/float(index_bin_width)))
	output = np.zeros(outp_len)
	for i in xrange(outp_len):
		output[i] = np.sum(np.absolute(thresholded[i*index_bin_width:min(thresholded_len,(i+1)*index_bin_width)]))

	return output

def autocorrelation(x,mode="fft"):
	x=np.asarray(x)
	n = len(x)
	mean = x.mean()
	if mode == "fft":
		r = scipy.signal.correlate(x,x,mode="full",method="fft")[-n:]
		outp = np.divide(r,np.multiply(mean**2,np.arange(n,0,-1)))
		return outp
	elif mode == "direct":
		r = np.correlate(x, x, mode = 'full')[-n:]
		outp =  np.divide(r,np.multiply(mean**2,np.arange(n,0,-1)))
		return outp


if __name__ == "__main__":

	#test count_photons - general pulse
	voltage = np.zeros(10000)
	voltage[3000:6000] = 1
	#add gaussian random noise to corrupt data - we want to make it tolerant to noise too!
	voltage = voltage + np.random.normal(0,0.1,voltage.shape)
	counts = count_photons(voltage,count_threshold=0.5)
	plt.plot(voltage)
	plt.xlabel("Simulated Time")
	plt.ylabel("Simulated Voltage")
	plt.title("Simulated time trace, Counts: {}".format(counts))
	plt.show()