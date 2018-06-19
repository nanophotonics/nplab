import numpy as np 
import scipy.ndimage as im
import scipy.optimize as spo

"""
Author: jpg66

Module to quickly and simply fit dark field spectra, using the function Run(x,y,Number_of_Peaks,Smoothing_Simga=10,Percentile_Height=70,Narrowing_Factor=3).

Input x and y as 1-D arrays reperenting wavelength/energy and scattering intensity respectively. Might be worth scaling y so it has values around 1.

y is smoothed by a gaussian filter of width Smoothing_Sigma. This is differentiated twice using a central differnce method to find all local maxima.
If more are found than Number_of_Peaks, the possible peaks with the smallest scattering intesities are dropped. A defualt guess height is set as the
Percentile_Height percentile of y minus the minimus value of y. The default width is set as (Average seperation between possible peaks)/Narrowing Factor.

Using these parameters, an initial fit is done to the smoothed spectrum of a constant and a set of Gaussians. The result is updated and improved by a further fit to the raw data. 

Returns 2 lists. The first has 4 elements. The first is the [Constant, Constant Error]. The second is a list of all the [Peak Position, Peak Position Error]. 
The third is for width and the last is for peak peak. The second list is the fitted spectrum itself.
"""

def Grad(x,y):
	"""
	Given 1-D arrays x and y, performs a quick central difference method differentiation of y with respect to x. (More accurate than numpy)
	"""
	Shifted_y=np.array(([y[1],y[0]]+y.tolist())[:-2])
	Shifted_x=np.array(([x[1],x[0]]+x.tolist())[:-2])
	return (Shifted_y-y)/(x-Shifted_x)

def Find_Zeros(Array):
	"""
	Given a 1D array Array, return the indexes where the values flip sign. Uses linear interpolation to give fractional index values.
	"""
	Output=[]
	n=1
	while n<len(Array):
		if Array[n]==0:
			Output.append(n)
		else:
			if (Array[n]>0 and Array[n-1]<0) or (Array[n]<0 and Array[n-1]>0):
				m=(Array[n]-Array[n-1])
				c=Array[n]-(m*n)
				Output.append(-c/m)
		n+=1
	return Output

def Find_Peaks(x,y):
	"""
	Given 1-D arrays x and y, find index positions off all local maxima. Uses linear interpolation to give fractional index values.
	"""
	Diff=Grad(x,y)
	Diff/=np.max(np.abs(Diff))
	Zeros=Find_Zeros(Diff)
	Output=[]
	Diff2=Grad(x,Diff)
	for i in Zeros:
		Value=((Diff2[int(i)+1]-Diff2[int(i)])*(i%1))+Diff2[int(i)]
		if Value<0:
			Output.append(i)
	return Output

def Gaussian(x,C,W,H):
	"""
	Returns a gaussian at x with height H, width W and centre position at x=C
	"""
	return H*np.exp(-0.5*(((x-C)/W)**2))

def Multi_G_constant(x,*Params):
	"""
	Returns a sum of Guassians plus a constant at x. The arguments Params go constant, Centre1, Width1, Height1, Centre2,......
	"""
	Output=Params[0]
	n=1
	while n<len(Params):
		Output+=Gaussian(x,*Params[n:n+3])
		n+=3
	return Output

def Run(x,y,Number_of_Peaks,Smoothing_Simga=10,Percentile_Height=70,Narrowing_Factor=3):
	"""
	Main function for this module. x is a 1d array of either wavelength or energy etc, y is the corresponding array for scattering intensity.
	Smoothing_Sigma=standard deivation of smoothing gaussian filter. Percentile_Height=percentile of the signal to take as an initial peak
	height guess. Narrowing_Factor= Default guess for peak width: (Average seperation between possible peaks)/Narrowing Factor 
	"""

	#--------Smooth and find all loacl maxima-----------
	Smooth=im.filters.gaussian_filter1d(y,10)
	All_Peaks=Find_Peaks(x,Smooth)

	if len(All_Peaks)==0:
		return None,None

	#----Extract the largest peaks-----------------
	if len(All_Peaks)<=Number_of_Peaks:
		Peaks=All_Peaks
	else:
		Peaks=[]
		Heights=[]
		for i in All_Peaks:
			Index=int(i)
			Frac=i%1
			Heights.append((Smooth[Index]*(1.-Frac))+(Smooth[Index+1]*(Frac)))
		while len(Peaks)<Number_of_Peaks:
			Max=np.argmax(Heights)
			Peaks.append(All_Peaks[Max])
			Heights=Heights[:Max]+Heights[Max+1:]
			All_Peaks=All_Peaks[:Max]+All_Peaks[Max+1:]

	#-------Convert the index postions of the peaks into the values given in the x-array ------------
	Convert_Units=[]
	for i in Peaks:
		Index=int(i)
		Frac=i%1
		Convert_Units.append((x[Index]*(1.-Frac))+(x[Index+1]*(Frac)))

	Convert_Units=sorted(Convert_Units)

	#-------Define default guesses to the peak height and width

	Default_Height=np.percentile(Smooth,Percentile_Height)-np.min(Smooth)
	Default_Width=0.
	if len(Peaks)==1:
		Default_Width=np.max(x)-np.min(x)
	else:
		n=1
		while n<len(Convert_Units):
			Default_Width+=Convert_Units[n]-Convert_Units[n-1]
			n+=1
		Default_Width/=len(Convert_Units)-1

	Default_Width/=Narrowing_Factor


	#-----Define intial fitting paramters-----------

	Initial_Params=[0.]
	Lower_Bounds=[-np.inf]
	Upper_Bounds=[np.inf]


	for i in Convert_Units:
		Initial_Params+=[i,Default_Width,Default_Height]
		Lower_Bounds+=[-np.inf,0,0]
		Upper_Bounds+=[np.inf,np.inf,np.inf]

	#----------Fit to smoothed curve--------------

	try:
		Params=spo.curve_fit(Multi_G_constant,x,Smooth,Initial_Params,bounds=(Lower_Bounds,Upper_Bounds))[0]
	except RuntimeError:
		Params=Initial_Params #Reverts to intial guess if fails

	#-------Update parameters by re-fitting to raw data 

	try:
		Params=spo.curve_fit(Multi_G_constant,x,y,Params,bounds=(Lower_Bounds,Upper_Bounds))
		Params=[Params[0],np.sqrt(np.diag(Params[1]))]
	except RuntimeError:
		return None,None

	#-----Repackage fit parameters into desired format

	Centres,Widths,Heights=[],[],[]
	for i in range(len(Params[0]))[1:]:
		if (i-1)%3==0:
			Centres.append([Params[0][i],Params[1][i]])
		elif (i-1)%3==1:
			Widths.append([Params[0][i],Params[1][i]])
		elif (i-1)%3==2:
			Heights.append([Params[0][i],Params[1][i]]) 

	#--------Check Fit Quality------------

	for i in Centres:
		if i[1]>abs(i[0]):
			return None,None
	for i in Widths:
		if i[1]>abs(i[0]):
			return None,None
	for i in Heights:
		if i[1]>abs(i[0]):
			return None,None

	#-------Return parameter and fit-----------

	Output_Parameters=[[Params[0][0],Params[1][0]],Centres,Widths,Heights]
	Fit=Multi_G_constant(x,*Params[0])
	return Output_Parameters,Fit







