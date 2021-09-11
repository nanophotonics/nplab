
import numpy as np 
import scipy.optimize as spo 

"""
Author: Jack Griffiths October 2019

A spiritual successor to Adpative_Polynomial.py, hopefully correcting some of the quirks in that code.

This script removes a polynomial approximation of SERS backgrounds from a spectrum, using the function
Run(x,y,Poly_Order=4,Auto_Remove=True,Maximum_Iterations=100):

x and y are the x and y axis of the signal. Poly_Order is the order of polynomial to use. If Auto_Remove is True, the signal without
background is returned. If False, the background is returned. Maximum_Iterations prevents infinite loops.

The code defines polynomials via points it passes through rather than coefficients. This is more stable to optimisation.

These points are intially defined as the lowest points in equal sized chunks of y. The noise level is estiamated using the points
below the background estimate. Only the points below this noise level above the current background are used to optimise it.
This is repeated until convergance.

"""

def Polynomial(x,Anchors,Anchor_Values):
	"""
	Defines a polynomial by the points it passed through. Anchors are points x, Anchor_Values are point y.
	"""
	return np.polyval(np.polyfit(Anchors,Anchor_Values,len(Anchors)-1),x)

def Initial_Guess(x,y,Order=3):
	"""
	Find smallest signal values in equally sized chunks of y
	"""
	Edges=np.round(np.linspace(0,len(y)-1,Order+2)).astype(int)
	Anchors=[]
	Anchor_Values=[]
	for i in range(len(Edges))[1:]:
		Arg=np.argmin(y[Edges[i-1]:Edges[i]])+Edges[i-1]
		Anchors.append(Arg)
		Anchor_Values.append(y[Arg])
	return Anchors,Anchor_Values

def Update_Polynomial(x,y,Mask,Anchors,Anchor_Values):
	"""
	Optimise polynomial defined by Anchors and Anchor_Values to fit (x,y) elements defined by bool Mask
	"""
	def Loss(Anchor_Values):
		return np.sum(np.abs((Polynomial(x,Anchors,Anchor_Values)-y)[Mask]))
	return spo.minimize(Loss,Anchor_Values).x 

def Run(x,y,Poly_Order=4,Auto_Remove=True,Maximum_Iterations=100):
	"""
	Main function. Described above.
	"""
	Iteration=0

	Anchors,Anchor_Values=Initial_Guess(x,y,Poly_Order)

	Mask=(np.array(y)*0+1).astype(bool)

	while True:
		Anchor_Values=Update_Polynomial(x,y,Mask,Anchors,Anchor_Values)

		Noise_Elements=(np.array(y)-Polynomial(x,Anchors,Anchor_Values))[np.array(y)<Polynomial(x,Anchors,Anchor_Values)]
		Noise=np.mean(np.square(Noise_Elements))**0.5

		New_Mask=(np.array(y)<=(Polynomial(x,Anchors,Anchor_Values)+Noise))

		Iteration+=1

		if np.sum(New_Mask==Mask)==len(Mask) or Iteration==Maximum_Iterations:
			BG=Polynomial(x,Anchors,Anchor_Values)
			if Auto_Remove is True:
				return y-BG
			else:
				return BG 
		else:
			Mask=New_Mask


