"""
Program to iteratively remove a non-trivial background from a spectrum of peaks. Note that this is not a rapid process.

Author: Jack Griffiths 2017

METHOD:

This uses the adaptive polynomial method.

First, the spectrum is fit to a high order polynomial. We want this fit to use low weights around peaks and high weights otherwise, but everywhere
is initially equally weighted. The counts at each wavelength are taken as Poisson distributed with the fit value as the mean. The probabilities that 
the observed counts or higher would be seen in this case are calculated. This will be high for points below the fit and low for points above
the fit. These are used as weights for the next round of fitting. This continues until the fit converges.
"""

import numpy as np
import scipy.stats as stat

def Find_Weights(Background,Data):
	"""
	Given a background fit (Background) and a spectrum (Data), calculates the probabilities for seeing the number of counts observed or greater
	at each wavelength assuming they are Poisson distributed with means at the background fit value.
	"""
	Weights=[]
	for i in range(len(Background)):
		Weights.append(1-stat.poisson.cdf(Data[i],Background[i]))
	return Weights

def Iterative_Step(Data,Current_Params,Degree,Return_BG=False):
	"""
	Given a spectrum and background fit, updates the background fit. 

	Data=1D array for spectrum. Current_Params=List of polynomial coefficents for the BG fit, highest power first. Degree=order of polynomial fit. 

	If Return_BG=False, the next polynomial coefficents will be returned. If Return_BG=True, the 1D array of the background for the 
	INPUT coefficents is also returned.
	"""

	Background=np.polyval(Current_Params,range(len(Data)))
	Background*=(Background>0)  #For a Poisson distribution, negative values are meaningless

	Weights=Find_Weights(Background,Data)
	
	Poly_Params=np.polyfit(range(len(Data)),Data,Degree,w=Weights)

	if Return_Weights is False:
		return Poly_Params
	else:
		return Poly_Params,Background

def Run(Data,Degree,Threshold=0.0001,Max_Steps=None,Auto_Remove=True):
	"""
	Main function that completes the background subtraction. 

	Data=1D array for spectrum. Degree is the polynomial degree to fit. The initial sum squared difference between the first two backgrounds is 
	calculated. The function returns when this sum between two successive background fits is less than Threshold*the original difference. If
	Max_Steps is a number, the function will automatically return after Max_Steps iterations. 

	If Auto_Remove is True, the background subtracted spectrum is returned. If it is False, the Background is returned.
	"""

	Background=None
	Intial_Difference=None
	End=False

	Params=np.polyfit(range(len(Data)),Data,Degree)

	Steps=0

	while End is False:
		Params,New_Background=Iterative_Step(Data,Params,Degree,True)
		if Background is None:
			Background=New_Background
		else:
			Difference=np.sum(np.square(np.array(New_Background)-np.array(Background)))**0.5
			if Intial_Difference is None:
				Intial_Difference=Difference
			else:
				if Difference<Threshold*Intial_Difference:
					End=True
				else:
					Background=New_Background
		if Max_Steps is not None:
			if Steps>Max_Steps:
				End=True
		Steps+=1

	Background=np.polyval(Params,range(len(Data)))
	Background*=(Background>0)

	if Auto_Remove is True:
		return np.array(Data)-np.array(Background)
	else:
		return np.array(Background)

