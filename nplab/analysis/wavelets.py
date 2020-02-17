'''
author: im354
'''
from __future__ import division

from builtins import zip
from builtins import range
from past.utils import old_div
import numpy as np
import matplotlib.pyplot as plt
import pywt
from scipy.optimize import minimize_scalar

def blocks():

	N = 2048
	t = np.linspace(0,1,N)

	Tj = [0.1,0.13,0.15,0.23,0.25,0.40,0.44,0.65,0.76,0.78,0.81]
	Hj = [4,-5,3,-4,5,-4.2,2.1,4.3,-3.1,2.1,-4.2]
	def K(t):
		return (1 + np.sign(t))/2.0
	y = np.zeros(t.shape)
	for tj,hj in zip(Tj,Hj):
		y = y + hj*K(t - tj)

	return t,4*y

def bumps():
	N = 2048
	t = np.linspace(0,1,N)

	Tj = [0.1,0.13,0.15,0.23,0.25,0.40,0.44,0.65,0.76,0.78,0.81]
	Hj = [4,5,3,4,5,4.2,2.1,4.3,3.1,5.1,4.2]
	Wj = [0.005,0.005,0.006,0.01,0.01,0.03,0.01,0.01,0.005,0.008,0.005]
	def K(t):
		return (1 + np.absolute(t))**-4
	y = np.zeros(t.shape)
	for (tj,hj,wj) in zip(Tj,Hj,Wj):
		y = y + hj*K(old_div((t - tj),wj))
	return t,10*y


def heavisine():
	N = 2048
	t = np.linspace(0,1,N)

	y = 4*np.sin(4*np.pi*t) - np.sign(t-0.3)-np.sign(0.72-t)
	return t,y*(10.0/4.0)

def doppler():
	N = 2048
	t = np.linspace(0,1,N)
	eps = 0.05
	y = np.sqrt(t*(1-t))*np.sin(old_div(2*np.pi*(1+eps),(t+eps)))
	return t,y*(12.5/0.5)



def SUREThresh(coefs):
	'''
	Single level SURE adaptive thresholding of wavelet coefficients from:
	'Adapting to Unknown Smoothness via Wavelet Shrinkage', D. Donoho, I. Johnstone,
	Dec 1995

	Performs softmax thresholding of wavelet coefficients ('coefs') at this level. 
	Threshold is selected by minimization of SURE objective for threshold ('t') values in range:
	0 < t < sqrt(2*log(d)) where 'd' is the number of coefficients at this level.
	
	For more details see paper.

	Args:
        coefs (float list): Single level wavelet coefficients.

    Returns:
        float list: Softmax thresholded wavelet coefficients.

	'''
	d = coefs.shape[0]
	t_max = np.sqrt(2*np.log(d))
	t_min = 0
	def SURE(t):
		return d-2*np.sum(np.abs(coefs) <= t) + np.sum(np.minimum(coefs,t)**2)

	trsh = minimize_scalar(SURE,bounds=[t_min,t_max]).x
	def soft_threshold(y):

		a = np.absolute(y) - trsh
		sgn = np.sign(y)
		if a <= 0:
			return 0
		else:
			return sgn*a
	
	thresholded = np.vectorize(soft_threshold)(coefs)
	
	return thresholded

def SUREShrink(data):
	'''
	Multilevel SURE adaptive thresholding of wavelet coefficients from:
	'Adapting to Unknown Smoothness via Wavelet Shrinkage', D. Donoho, I. Johnstone,
	Dec 1995

	Performs adaptive SURE denoising of input signal ('data') by adaptive softmax thresholding
	each level of wavelet coefficients representing the original signal. Works under the assumption
	of Gaussian additive noise in the case when energy signal is concentrated in relatively
	few wavelet transform components allowing softmax thresholding to remove unwanted noise contributions.

	Args:
        data (float list): .

    Returns:
        float list: SUREShrink Denoised signal.

	'''
	mode = "periodic"
	wl = "sym8"
	n = data.shape[0]
	J = np.ceil(np.log2(n))
	
	dwt = pywt.wavedec(data,wavelet=wl,mode=mode)  

	for i in range(len(dwt)):
		dwt[i] = SUREThresh(dwt[i])

	return pywt.waverec(dwt,wavelet=wl,mode=mode)

def SkellamThresh(wavelet_coefs,scaling_coefs):
	yi = wavelet_coefs
	ti = scaling_coefs
	# print len(yi), len(ti)
	d = yi.shape[0]
	t_max = np.sqrt(2*np.log(d))
	t_min = 0

	def SkellamObjective(t):
			t1 = np.sum(np.sign(np.abs(yi)-t)*ti)
			t2 = np.sum(np.minimum(yi**2,np.ones(yi.shape)*t**2))
			t3 = -t*np.sum(np.abs(yi)==t)
			# print t1,t2,t3
			return np.sum([t1,t2,t3])


	def SS(t):
		t1 = np.sum(np.sign(np.abs(yi)-t)*ti)
		t2 = np.sum(np.minimum(yi**2,np.ones(yi.shape)*t**2))
		t3 = -t*np.sum(np.abs(yi)==t)
		# print t1,t2,t3
		return np.sum([t1,t2,t3])

	trsh = minimize_scalar(SkellamObjective,bounds=[t_min,t_max]).x
	# print "threshold", trsh
	def soft_threshold(y):

		a = np.absolute(y) - trsh
		sgn = np.sign(y)
		if a <= 0:
			return 0
		else:
			return sgn*a

	# sigma_x = np.std(yi)
	# def adjusted_threshold(y,t):
	# 	if np.abs(y) >= (np.sqrt(2)*t)/sigma_x:
	# 		return -np.sign(y)*(np.sqrt(2)*t)/sigma_x
	# 	else:
	# 		return -y

	# thresholded = np.zeros(yi.shape)
	# for i in range(yi.shape[0]):
	# 	thresholded[i] = adjusted_threshold(y=yi[i],t=ti[i])
	# soft threshold:
	thresholded = np.vectorize(soft_threshold)(yi)
	return thresholded


def multiscale_function_apply(func,wavelet_name,max_level=None):

	def multiscale_apply(ys,):
		# print len(ys)
		wl = pywt.Wavelet(wavelet_name)
		
		if max_level is None:
			level = pywt.dwt_max_level(len(ys),wl)
		else:
			level = max_level

		coeffs_list = []
		a = ys
		for i in range(level):
			a, d = pywt.dwt(a, wavelet=wl)
			f = func(approx =a, detail=d)
			coeffs_list.append(f)
		coeffs_list.append(a)
		coeffs_list.reverse()
		return coeffs_list

	return multiscale_apply 

def SkellamShrink(data,max_level=-1):
	'''
	Based on: Skellam Shrinkage: Wavelet-Based Intensity Estimation for Inhomogeneous Poisson data
	Related papers: Fast Haar-Wavelet denoising of multidimensional fluorescence microscopy data
	'''

	mode = "periodic"
	wl = "haar"
	n = data.shape[0]
	J = np.ceil(np.log2(n))
	
	def identify(approx,detail):
		return detail

	def skellam(approx,detail):
		return SkellamThresh(wavelet_coefs=detail,scaling_coefs=approx)

	if max_level == -1 :
		f = multiscale_function_apply(func=skellam,wavelet_name=wl)
	else:
		f = multiscale_function_apply(func=skellam,wavelet_name=wl,max_level=max_level)
	dwt = f(data)
	return pywt.waverec(dwt,wavelet=wl,mode=mode)






def plot_test_functions():
	fig, [[ax1,ax2],[ax3,ax4]] = plt.subplots(2,2)
	
	xs,ys = blocks()
	ax1.plot(xs,ys)
	ax1.set_title("Original Blocks")
	
	xs,ys = bumps()
	ax2.plot(xs,ys)
	ax2.set_title("Original Bumps")

	xs,ys = heavisine()
	ax3.plot(xs,ys)
	ax3.set_title("Original HeaviSine")

	xs,ys = doppler()
	ax4.plot(xs,ys)
	ax4.set_title("Original Doppler")

	plt.show()

def plot_noisy_test_functions():
	N = 2048
	noise = np.random.normal(loc=0,scale=1.0,size=N)
	fig, [[ax1,ax2],[ax3,ax4]] = plt.subplots(2,2)
	
	xs,ys = blocks()
	ax1.plot(xs,ys+noise)
	ax1.set_title("Noisy Blocks (noise~N(0,1)")
	
	xs,ys = bumps()
	ax2.plot(xs,ys+noise)
	ax2.set_title("Noisy Bumps (noise~N(0,1)")

	xs,ys = heavisine()
	ax3.plot(xs,ys+noise)
	ax3.set_title("Noisy HeaviSine (noise~N(0,1)")

	xs,ys = doppler()
	ax4.plot(xs,ys+noise)
	ax4.set_title("Noisy Doppler (noise~N(0,1)")

	plt.show()

def plot_denoised_functions():
	N = 2048
	noise = np.random.normal(loc=0,scale=1.0,size=N)
	fig, [[ax1,ax2],[ax3,ax4]] = plt.subplots(2,2)
	axarr = [ax1,ax2,ax3,ax4]
	
	for i,f in enumerate([blocks,bumps,heavisine,doppler]):
		xs,ys = f()
		ys = ys + noise
		denoised = SUREShrink(ys)
		axarr[i].plot(xs,denoised)
		axarr[i].set_title("Denoised {}".format(f.__name__))
	plt.show()


if __name__ == "__main__":
	#Gaussian noise:
	plot_test_functions()
	plot_noisy_test_functions()
	plot_denoised_functions()