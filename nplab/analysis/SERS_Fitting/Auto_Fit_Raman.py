from __future__ import division
from builtins import range
from past.utils import old_div
import numpy as np 
import scipy.ndimage.filters as imf
import scipy.optimize as spo

"""
Author: jpg66 October 2018

This script is for auto detecting and fitting sparse, high SNR peaks form spectra with a flat background.

It is run using the Run(Input,Shift,Width=10,Smoothing_Factor=5,Noise_Threshold=2) function.

Input is the 1D apectrum array. Shift is the correspodning array of Raman shifts. Width is the default guess width of raman peaks.

The function runs as follows:

A gaussian smooth of width Smoothing_Factor is applied. Local maxima are identifed in this smoothed spectrum and the heights of these possible peaks in the raw spectra 
are found. The noise level is estimated as the standard devation of the differential of the raw spectrum (iffy for spectra with dense peaks). Possible peaks with heights
below Noise_Threshold*the noise level are discarded. The smoothed signal is fit to all potential peaks (as Lorentzians) and a constant background. If the fit fails
(doesn't converge, peaks below noise, peaks not spectrally resolved etc) using all N peaks, all combinations of N-1 peaks are tested and so on. The fitting results
are fit to the raw spectrum.

"""

def Grad(Array):
	"""
	Returns something prop to the grad of 1D array Array. Does central difference method with mirroring.
	"""
	A=np.array(Array.tolist()+[Array[-1],Array[-2]])
	B=np.array([Array[1],Array[0]]+Array.tolist())
	return (A-B)[1:-1]

def Find_Zeroes(Array):
	"""
	Find the zero crossing points in a 1D array Array, using linear interpolation
	"""
	Output=[]
	for i in range(len(Array))[1:]:
		if Array[i]==0:
			Output.append(float(i))
		else:
			if i!=0:
				if ((int((Array[i]>0))*2)-1)*((int((Array[i-1]>0))*2)-1)==-1:
					Frac=old_div(Array[i-1],(Array[i-1]-Array[i]))
					Output.append(i+Frac-1)
	return Output

def Find_Maxima(Array):
	"""
	Find all local maxima in 1d array Array
	"""
	Diff=Grad(Array)
	Stationary=Find_Zeroes(Diff)
	Curv=Grad(Diff)
	Output=[]
	for i in Stationary:
		Value=((Curv[int(i)+1]-Curv[int(i)])*i%1)+Curv[int(i)]
		if Value<0:
			Output.append(i)
	return Output

def L(x,H,C,W):
	"""
	Defines a lorentzian
	"""
	return old_div(H,(1.+((old_div((x-C),W))**2)))

def Multi_L_Constant(x,*Params):
	"""
	Defines a contant plus a sum of Lorentzians. Params goes Constant, Height1,Centre1, Width1,Height2.....
	"""
	Output=Params[0]
	n=1
	while n<len(Params):
		Output+=L(x,*Params[n:n+3])
		n+=3
	return Output

def Attempt_To_Fit(Shift,Array,Peak_Shifts,Peak_Heights,Width,Minimum_Height=0):
	"""
	Given a raman Shift and spectrum Array, with guesses for possible Peak_Shifts and Peak_Heights with a single guess for the Width, attempts to fit the peaks.
	Fits rejected if Height<Minimum_Height
	"""
	Number_Of_Peaks=len(Peak_Shifts)

	def Generate_Peak_Selections(Number,Options):
		Levels=Options-Number
		Output=[list(range(Options))]
		for i in range(Levels):
			New_Output=[]
			for j in Output:
				for k in range(len(j)):
					New=sorted(j[:k]+j[k+1:])
					if New not in New_Output:
						New_Output.append(New)
			Output=New_Output
		return Output

	while Number_Of_Peaks>0:

		Options=Generate_Peak_Selections(Number_Of_Peaks,len(Peak_Shifts))

		Parameters=[]

		for Option in Options:
			Initial=[0.]
			L_Bounds=[-np.inf]
			U_Bounds=[np.inf]
			for i in Option:
				Initial+=[Peak_Heights[i],Peak_Shifts[i],Width]
				L_Bounds+=[0,np.min(Shift),0]
				U_Bounds+=[np.inf,np.max(Shift),np.inf]
				#print Initial
			try:
				Params=spo.curve_fit(Multi_L_Constant,Shift,Array,Initial,bounds=(L_Bounds,U_Bounds))
				Params=[Params[0],np.sqrt(np.diag(Params[1]))]

				#print Params
						
				Fail=False
				n=1
				while n<len(Params[0]):
					if (Params[0][n]-Params[0][0])<Minimum_Height:
						Fail=True
					n+=3
				if True in (Params[0][1:]<np.abs(Params[1][1:])).tolist():
					Fail=True
				n=1
				while n<len(Params[0])-3:
					if (Params[0][n+2]+Params[0][n+5])>abs((Params[0][n+1]-Params[0][n+4])):
						Fail=True
					n+=3
				if Fail is False:
					Parameters.append(Params[0])
			except RuntimeError:
					Dump=None

		if len(Parameters)>0:
			Loss=[]
			for i in Parameters:
				Loss.append(np.sum(np.abs(Array-Multi_L_Constant(Shift,*i))))
			return Parameters[np.argmin(Loss)]

		Number_Of_Peaks-=1
	return None


def Run(Input,Shift,Width=10,Smoothing_Factor=5,Noise_Threshold=2):
	"""
	Main Function, described above
	"""
	Smooth=imf.gaussian_filter(Input,Smoothing_Factor)
	Maxima=Find_Maxima(Smooth)
	Threshold=Noise_Threshold*np.std(Grad(Input))
	Peak_Shifts=[]
	Peak_Heights=[]
	for i in Maxima:
		H=((Input[int(i)+1]-Input[int(i)])*i%1)+Input[int(i)]
		if H>=Threshold:
			Peak_Heights.append(H)
			Peak_Shifts.append(((Shift[int(i)+1]-Shift[int(i)])*i%1)+Shift[int(i)])
	First_Draft=Attempt_To_Fit(Shift,Smooth,Peak_Shifts,Peak_Heights,Width,Threshold)
	
	if First_Draft is None:
		return [None,None]

	L_Bounds=[-np.inf]
	U_Bounds=[np.inf]

	n=1
	while n<len(First_Draft):
		L_Bounds+=[0,-np.inf,0]
		U_Bounds+=[np.inf,np.inf,np.inf]
		n+=3	

	try:
		Params=spo.curve_fit(Multi_L_Constant,Shift,Input,First_Draft,bounds=(L_Bounds,U_Bounds))
		Params=[Params[0],np.sqrt(np.diag(Params[1]))]
		Params=[Params[0][1:],Params[1][1:]]
		return Params
	except RuntimeError:
		return [None,None]

