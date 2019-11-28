from __future__ import division
from __future__ import print_function
from builtins import range
from past.utils import old_div
import cvxpy as cvx
import numpy as np


#Initialize the CVX problem variables
#TODO - generalize to N-dimensional signals
def init_problem(n):
	x = cvx.Variable(n)
	D = np.identity(n, int)
	for i in range(1,n):
		D[i][i-1] = -1
	return x, D

def convex_smooth(signal,weight, objective_type="quadratic",normalise = True):
	'''Smoothing signal based on weight parameter
		@param signal - your 1D signal
		@param weight - the strength of your smoothing. 0 for no smoothing 
		@param objective_type - sets the type of smoothing you want
			See: wikipedia - Tikhonov_regularization
			quadratic - what you will most often want
			total_variation [See: https://en.wikipedia.org/wiki/Total_variation_denoising]
	'''

	#you can't add noise to your data
	signal = np.array(signal,dtype=float)
	assert(weight >= 0)
	signal_max = np.max(signal)
	if normalise==True: signal=old_div(signal,signal_max)

	#initialize the problem)
	dims = signal.shape[0]
	x,D = init_problem(dims)

	####
	#select the type of smoothing
	####

	#total variational smoothing:
	if objective_type == "total_variation":
		f2 = cvx.norm(D*x,1)

	#quadratic 
	elif objective_type == "quadratic":
		f2 = cvx.sum_squares(D*x)
	else:
		raise ValueError("Only allowed values: [ total_variation | quadratic ]")
	
	#set up problem
	f1 = cvx.sum_squares(x-signal)
	objective = cvx.Minimize(f1 + weight*f2)
	prob = cvx.Problem(objective)
	#solve
	prob.solve()
	#return answer
	x_out =  np.asarray(x.value)
	x_out = x_out.reshape(signal.shape)
	if normalise==True: x_out=x_out*signal_max
	return x_out, prob.value, prob.status


if __name__ == "__main__":

	import matplotlib.pyplot as plt 
	import numpy as np

	xs = np.linspace(0,2*np.pi,500)
	noise = np.random.uniform(-0.4,0.4,xs.shape)*100000.0
	ys = np.sin(xs)*100000.0
	ys_corrupted = ys + noise

	fig, ax = plt.subplots(1)
	plt.plot(xs, ys, label="True signal")
	plt.plot(xs, ys_corrupted, label="Noisy signal");print(ys_corrupted.shape,type(ys_corrupted))
	for weight in [1,10,100]:
		ys_denoised,_,_ = convex_smooth(signal = ys_corrupted, weight = weight, objective_type="quadratic",normalise = True)
		plt.plot(xs, ys_denoised, label="Recovered signal [Weight:{}]".format(weight))

	plt.legend()
	plt.show()