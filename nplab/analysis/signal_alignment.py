from builtins import range
import numpy as np 
import matplotlib.pyplot as plt 
from scipy.signal import correlate
#Perform phase correlation alignment
def get_window(N, window_type ="hamming"):
	if window_type == "hamming":
		#Symmetric window for filter design? But doing spectral analysis
		return scipy.signal.hamming(N,sym=False)
	elif window_type == "hann":
		return scipy.signal.hann(N,sym=False)

def correlation_align(signal_0,signal_1,upsampling=1.0,return_integer_shift=True):
	#Returns the shift (integer) which signal_1 must be moved to 
	#Align it with signal_0. Upsampling used to provide higher resolution.
	N = signal_0.shape[0]
	# assert(signal_0.shape==signal_1.shape)

	if upsampling > 1.0:
		raise ValueError("Forbidden")
		#TODO replace resample
		# signal_0 = scipy.signal.resample(signal_0,int(np.round(N*upsampling)))
		# signal_1 = scipy.signal.resample(signal_1,int(np.round(N*upsampling)))
		N = int(np.round(N*upsampling))

	xcorr = correlate(in1=signal_0,in2=signal_1, method='fft',mode="same")
	full_precision_shift = shift = (np.round(N/2.0)-np.argmax(xcorr))/float(upsampling)
	integer_shift = int(np.round(shift))
	if return_integer_shift == True:
		return integer_shift,xcorr
	else:
		return full_precision_shift,xcorr

def overlap_align(signal_0, signal_1):
	pass

def demo():
	N = 1014
	signal0 = np.zeros(N)
	signal0[300:500] = 1
	signal1 = np.zeros(N)
	signal1[350:550] = 1

	signal0 = signal0 + np.random.normal(0,0.1,N)
	signal1 = signal1 + np.random.normal(0,0.1,N)
	

	fig, axarr = plt.subplots(2)
	up = 1.0
	shift, xcorr = correlation_align(signal0,signal1,upsampling=up)
	
	xs = np.array(list(range(0,N)))
	axarr[0].plot(xs,signal0,label="signal0")
	axarr[0].plot(xs,signal1,label="signal1")
	axarr[0].plot(xs-shift,signal1,label="signal1_shifted")
	axarr[0].legend()
	axarr[1].plot(xcorr)
	plt.show()

if __name__ == "__main__": 
	demo()
	

