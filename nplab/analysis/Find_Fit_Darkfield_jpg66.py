import numpy as np 
import scipy.ndimage as im
import scipy.optimize as spo
import itertools

"""
Author: jpg66

Module to quickly and simply fit dark field spectra, using the function Run(x,y,Number_of_Peaks,Smoothing_Simga=10,Percentile_Height=70,Narrowing_Factor=3).

Input x and y as 1-D arrays reperenting wavelength/energy and scattering intensity respectively. Might be worth scaling y so it has values around 1.

y is smoothed by a gaussian filter of width Smoothing_Sigma. This is differentiated twice using a central difference method to find all local maxima.
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

def Check_Fit_Quality(Params):
	for i in range(len(Params[0]))[1:]:
		if abs(Params[0][i])<Params[1][i]:
			return False

	if len(Params[0])>4:
		Centres=[]
		Widths=[]
		n=1
		while n<len(Params[0]):
			Centres.append(Params[0][n])
			Widths.append(Params[0][n+1])
			n+=3

		Centres_Sorted=[]
		Widths_Sorted=[]

		while len(Centres)>0:
			Pick=np.argmin(Centres)
			Centres_Sorted.append(Centres[Pick])
			Widths_Sorted.append(Widths[Pick])
			Centres.remove(Centres[Pick])
			Widths.remove(Widths[Pick])

		n=1
		while n<len(Centres_Sorted):
			if (Widths_Sorted[n]+Widths_Sorted[n-1])>Centres_Sorted[n]-Centres_Sorted[n-1]:
				return False
			n+=1

		return True

def Generate_Parameters_from_Centres(x,y,Centres,Percentile_Height,Narrowing_Factor):

	Default_Height=np.percentile(y,Percentile_Height)-np.min(y)
	Default_Width=0.
	if len(Centres)==1:
		Default_Width=np.max(x)-np.min(x)
	else:
		n=1
		while n<len(Centres):
			Default_Width+=Centres[n]-Centres[n-1]
			n+=1
		Default_Width/=len(Centres)-1

	Default_Width/=Narrowing_Factor

	Initial_Params=[0.]


	for i in Centres:
		Initial_Params+=[i,Default_Width,Default_Height]

	return Initial_Params

def Attempt_Fit(x,Smoothed,Raw,Initial_Params):
	Lower_Bounds=[-np.inf]
	Upper_Bounds=[np.inf]

	while len(Lower_Bounds)<len(Initial_Params):
		Lower_Bounds+=[np.min(x)-(0.5*(np.max(x)-np.min(x))),0,0]
		Upper_Bounds+=[np.max(x)+(0.5*(np.max(x)-np.min(x))),np.inf,np.inf]

	for i in range(len(Lower_Bounds)):
		if Initial_Params[i]<Lower_Bounds[i]:
			Initial_Params[i]=Lower_Bounds[i]
		if Initial_Params[i]>Upper_Bounds[i]:
			Initial_Params[i]=Upper_Bounds[i]


	try:
		Params=spo.curve_fit(Multi_G_constant,x,Smoothed,Initial_Params,bounds=(Lower_Bounds,Upper_Bounds))[0]
	except RuntimeError:
		Params=Initial_Params #Reverts to intial guess if fails

	#-------Update parameters by re-fitting to raw data 

	try:
		Params=spo.curve_fit(Multi_G_constant,x,Raw,Params,bounds=(Lower_Bounds,Upper_Bounds))
		Params=[Params[0],np.sqrt(np.diag(Params[1]))]
	except RuntimeError:
		return None

	if Check_Fit_Quality(Params) is False:
		return None

	else:
		return Params

def Constant_func(x,A):
	return (x*0)+A

def Run(x,y,Number_of_Peaks,Energy=True,Scale_To_Percentile=90,Smoothing_Simga=10,Percentile_Height=70,Narrowing_Factor=3,Spike_Value=2,Noise_Threshold=0.9):
	"""
	Main function for this module. x is a 1d array of either wavelength or energy etc, y is the corresponding array for scattering intensity.
	Smoothing_Sigma=standard deivation of smoothing gaussian filter. Percentile_Height=percentile of the signal to take as an initial peak
	height guess. Narrowing_Factor= Default guess for peak width: (Average seperation between possible peaks)/Narrowing Factor 
	"""

	#Scale

	y=np.array(y).astype(np.float64)/np.percentile(y,Scale_To_Percentile)

	#-----Check if noise-------------

	Elements=[]
	for i in y:
		if i<=Spike_Value:
			Elements.append(i)
	Metric=np.median(Elements)/np.median(np.abs(Elements))

	if Metric<=Noise_Threshold:
		return None,None

	#--------Smooth and find all local maxima-----------
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

	Options=[Convert_Units]
	Complete=None

	while Complete is None:
		Results=[]
		for i in Options:
			Result=Attempt_Fit(x,Smooth,y,Generate_Parameters_from_Centres(x,y,i,Percentile_Height,Narrowing_Factor))
			if Result is not None:
				Results.append(Result)
		if len(Results)>0:
			Errors=[]
			for i in Results:
				Errors.append(np.sum(np.abs(Multi_G_constant(x,*i[0])-y)))
			Params=Results[np.argmin(Errors)]
			Complete=True
			

		else:
			if len(Options[0])==1:
				Complete=False
				Params=None
			else:
				New_Options=[]
				for i in Options:
					for n in range(len(i)):
						New_Option=i[:n]+i[n+1:]
						if New_Option not in New_Options:
							New_Options.append(New_Option)
				Options=New_Options
				
	if Params is None:
		return None,None

	#---Attempt to work out if have missed a coupled mode shoulder------------

	Centres=[]
	n=1
	while n<len(Params[0]):
		Centres.append(Params[0][n])
		n+=3
	if Energy is True:
		Coupled=np.argmin(Centres)
	else:
		Coupled=np.argmax(Centres)

	Coupled*=3
	Coupled+=1

	Constant=Params[0][0]
	Coupled_Peak=[]
	Other_Peaks=[]
	n=1
	while n<len(Params[0]):
		if n==Coupled:
			Coupled_Peak=Params[0][n:n+3]
		else:
			Other_Peaks.append(Params[0][n:n+3].tolist())
		n+=3

	Permutations=[Other_Peaks]
	while len(Permutations[0])>Number_of_Peaks-2:
		New_Permuations=[]
		for i in Permutations:
			for j in range(len(i)):
				New=i[:j]+i[j+1:]
				if New not in New_Permuations:
					New_Permuations.append(New)
		Permutations=New_Permuations

	Coupled_Peak=[[Coupled_Peak[0]+(0.5*Coupled_Peak[1]),0.5*Coupled_Peak[1],0.5*np.exp(0.5)*Coupled_Peak[2]],[Coupled_Peak[0]-(0.5*Coupled_Peak[1]),0.5*Coupled_Peak[1],0.5*np.exp(0.5)*Coupled_Peak[2]]]

	Current_Error= np.sum(np.abs(Multi_G_constant(x,*Params[0])-y))

	for i in Permutations:
		Attempt=[Constant]
		for j in i+Coupled_Peak:
			Attempt+=j

		Split_Fit=Attempt_Fit(x,Smooth,y,Attempt)
		if Split_Fit is not None:
			New_Error=np.sum(np.abs(Multi_G_constant(x,*Split_Fit[0])-y))
			if New_Error<Current_Error:
				Params=Split_Fit
				Current_Error=New_Error


	#------Repackage parameters------------

	Centres,Widths,Heights=[],[],[]
	for i in range(len(Params[0]))[1:]:
		if (i-1)%3==0:
			Centres.append([Params[0][i],Params[1][i]])
		elif (i-1)%3==1:
			Widths.append([Params[0][i],Params[1][i]])
		elif (i-1)%3==2:
			Heights.append([Params[0][i],Params[1][i]])

	#-------Return parameter and fit-----------

	Output_Parameters=[[Params[0][0],Params[1][0]],Centres,Widths,Heights]
	Fit=Multi_G_constant(x,*Params[0])
	return Output_Parameters,Fit







