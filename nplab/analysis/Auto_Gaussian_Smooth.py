from __future__ import division
from builtins import range
from past.utils import old_div
import scipy.ndimage.filters as ndimf
import numpy as np 
import scipy.interpolate as scint

"""
Author: Jack Griffiths 0ct 2019

Function to automatically choose the level of gaussian smoothing to apply to a signal as to supress noise while not destroying information.

As the smoothing width increases, an de/increase in signal is more and more likely to be followed by another de/increase.

This searching for the elbow (point of max curvature) in this plot of probabilty against width.

It then applies twice this value as a smooth (just into the cuve region where you start to get diminishing returns)

Call Run(Signal)
"""

def Fraction(Signal):
	"""
	Function takes a list of numbers. Returns to fraction of inter-element changes follwed by a change in the same direction.
	"""
	Same,Different=0,0
	for i in range(len(Signal))[1:-1]:
		if Signal[i]>=Signal[i-1]:
			A=1
		else:
			A=0
		if Signal[i+1]>=Signal[i]:
			B=1
		else:
			B=0
		if A==B:
			Same+=1
		else:
			Different+=1
	return float(Same)/(Same+Different)

def Sigmoid(x,O,S):
	"""
	Sigmoid function defiend by offset O and scale S
	"""
	return 1./(1.+np.exp(old_div(-(x-O),S)))

def Grad(x,y):
	"""
	Estimates gradient of y wrt x
	"""
	Output=(np.array(np.array(y).tolist()+[y[-1],y[-2]]))-(np.array([y[1],y[0]]+np.array(y).tolist()))
	Output/=(np.array(np.array(x).tolist()+[x[-1],x[-2]]))-(np.array([x[1],x[0]]+np.array(x).tolist()))
	return Output[1:-1]

def Run(Signal):
	"""
	Main funtion. Returns smoothed Signal
	"""

	#--Quickly sample parameter space---
	Smooth=[0]
	Score=[Fraction(Signal)]
	n=1
	while n<len(Signal):
		Smooth.append(n)
		Score.append(Fraction(ndimf.gaussian_filter(Signal,n)))
		n*=2

	#--Interpolate parameter space
	y=scint.interp1d(Smooth,Score,kind='cubic')(np.linspace(0,np.max(Smooth),1000))
	x=np.linspace(0,np.max(Smooth),1000)

	#--Find elbow--

	G=Grad(x,y)
	GG=Grad(x,G)

	Max=np.argmax(np.abs(GG))
	Poly=np.polyfit(x[Max-1:Max+2],np.abs(GG)[Max-1:Max+2],2)
	Max=old_div(-Poly[1],(2*Poly[0]))

	#--Repeat porces on smaller, more accurate region--

	Smooth=np.linspace(0,2*Max,len(Score))
	Score=[]
	for i in Smooth:
		Score.append(Fraction(ndimf.gaussian_filter(Signal,i)))
	Score=np.array(Score)

	G=Grad(Smooth,Score)
	GG=Grad(Smooth,G)

	Max=np.argmax(np.abs(GG))
	Poly=np.polyfit(x[Max-1:Max+2],np.abs(GG)[Max-1:Max+2],2)
	Max=old_div(-Poly[1],(2*Poly[0]))

	#---Perform smooth---

	return ndimf.gaussian_filter(Signal,Max*2)