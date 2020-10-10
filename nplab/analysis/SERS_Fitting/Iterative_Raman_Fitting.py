# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from builtins import range
from past.utils import old_div
import numpy as np 
import pywt 
import scipy.interpolate as scint
import scipy.ndimage.filters as ndimf
import scipy.optimize as spo
import copy
import multiprocessing as mp

"""
Author: jpg66 April 2019

An alternative mathod for automatic Raman spectra fitting, suitable using Lorenztian or Gaussian peaks. Slow but may be more effective than other methods.
(Considerably brute force) 

Method works by trying to interatively add peaks one at a time until spectrum is matched. Run with function
Run(x_axis,Signal,Maximum_FWHM=40,Regions=50,Minimum_Width_Factor=0.1,Peak_Type='L',Print=True,Initial_Fit=None).

x_axis and Signal are 1d numpy arrays. The typical peak width is estimated using a Continuous Wavelet Transfrom Method, up to a maximum of Maximum_FWHM.

The x-axis is split into Regions regions and a peak is added and optimized within each in turn. The one that reduces the overall fitting error the most is taken.
With this new peak in place, all the peaks are optimised.

If any peaks have a height of zero or a width less than Minimum_Width_Factor x the estimated typical width, it is removed. 

Each time the loss does not decrease after an interation, the number of iterations is increased by a factor of 5. If the loss technically does decrease, 
but in reality the number of peaks are the same and none of them have moved by more than half a HWHM, this condition is also triggered. When the number of regions 
exceeds the size of Signal, the iterations end.

Whether a Lorentzian or Gaussian is used is controlled via Peak_Type='L' or 'G'.

So close to a local minima, the result is passed into scipy.optimize.curve_fit to generate the final fit with fitting errors.

Returns a list [Fits,Errors]

Note: If you have a set of peaks already, you can speed to porcess along by inserting them as Inital_Fit. The code will first optimise the heights of these peaks,
then all their parameters. It will then continue as normal.

Note: If you have a set of spectra to fit, you can use Fit_Set_of_Spectra which will do the fitting in parallel on a defined number of cores (default=2). If you set 
Utilise_Persistant to True, the median spectrum will first be fit and used as a starting point for each spectrum.
"""

def Quick_Sort(List,Argument):
		#Sorts a List based on the numberimal value of the Argument element.
		def Split(List,Argument):
			#List is list of lists to seperate
			#Argument is list argument to seperate via

			Output=[[],[]]

			Pivot=[]
			for i in List:
				Pivot.append(i[Argument])
			if len(Pivot)==2:
				Pivot=max(Pivot)
			else:
				Pivot=np.random.choice(Pivot)

			for i in List:
				if i[Argument]<Pivot:
					Output[0].append(i)
				else:
					Output[1].append(i)
			return Output

		def Same(List,Argument):
			for i in List:
				if i[Argument]!=List[0][Argument]:
					return False
			return True

		Sorted=[]
		To_Sort=[List]
		while len(To_Sort)>0:
			Sorting=To_Sort[0]
			To_Sort=To_Sort[1:]
			if Same(Sorting,Argument) is True:
				Sorted+=Sorting
			else:
				To_Sort=Split(Sorting,Argument)+To_Sort
		return Sorted

def Wavelet_Estimate_Width(x_axis,Signal,Maximum_Width,Smooth_Loss_Function=2):
	#Uses the CWT to estimate the typical peak FWHM in the signal
	#First, intepolates the signal onto a linear x_scale with the smallest spacing present in the signal
	#Completes CWT and sums over the position coordinate, leaving scale
	#Does minor smooth, and takes scale at maximum as FWHM

	Int=scint.splrep(x_axis,Signal)

	Step=np.min(np.abs(np.diff(x_axis)))

	New=scint.splev(np.arange(x_axis[0],x_axis[-1],Step),Int)

	Scales=np.arange(1,np.ceil(old_div(Maximum_Width,Step)),1)

	Score=np.diff(np.sum(pywt.cwt(New,Scales,'gaus1')[0],axis=1))

	Score=ndimf.gaussian_filter(Score,Smooth_Loss_Function)

	Scale=Scales[np.argmax(Score)]*Step

	return Scale 

def L(x,H,C,W):
	"""
	Defines a lorentzian
	"""
	return old_div(H,(1.+((old_div((x-C),W))**2)))

def Multi_L(x,*Params):
	"""
	Defines a sum of Lorentzians. Params goes Height1,Centre1, Width1,Height2.....
	"""
	Output=0
	n=0
	while n<len(Params):
		Output+=L(x,*Params[n:n+3])
		n+=3
	return Output

def G(x,H,C,W):
	"""
	Defines a gaussian
	"""
	return H*np.exp(-0.5*((old_div((x-C),W))**2))

def Multi_G(x,*Params):
	"""
	Defines a sum of LGuassians. Params goes Height1,Centre1, Width1,Height2.....
	"""
	Output=0
	n=0
	while n<len(Params):
		Output+=G(x,*Params[n:n+3])
		n+=3
	return Output

def Add_New_Peak(x_axis,Signal,Current_Peaks,Width,Maximum_Width,Regions=50,Peak_Type='L'):
	"""
	Given a signal (x_axis and Signal 1D arrays) and a pre-existing set of peaks (Current Peaks=list in form [Height1,Centre1,Width1,Height2...]), this function
	trys to find to best place for a new peak.

	The x-axis is slit into Regions equal regions. In each in turn, a peak in placed randomly and optimized without being allowed to leave that region.

	This peak can be gaussian or Lorentzian depending on the Peak_Type argument 'G' or 'L' .

	The peak has a default width parameter Width and Max Width Maximum_Width.

	The peak that casued the greated reduction in fitting loss is chosen.
	"""

	#-----Calc. size of x_axis regions-------
	Sections=old_div((np.max(x_axis)-np.min(x_axis)),Regions)
	Start=np.min(x_axis)

	Results=[]
	Loss_Results=[]

	#-------What does the curve look like with the current peaks?--------
	if len(Current_Peaks)==0:
		Current=np.array(x_axis)*0
	else:
		if Peak_Type=='L':
			Current=Multi_L(x_axis,*Current_Peaks)
		else:
			Current=Multi_G(x_axis,*Current_Peaks)

	#-------Set up Loss function--------	
			
	if Peak_Type=='L':
		def Loss(Vector):
			return np.sum(np.abs(Current+L(x_axis,*Vector)-Signal))
	else:
		def Loss(Vector):
			return np.sum(np.abs(Current+G(x_axis,*Vector)-Signal))

	#-----Minimise loss in each region--------- 

	for i in range(Regions):
		Bounds=[(0,np.inf),(i*Sections+Start,(i+1)*Sections+Start),(0,Maximum_Width)]
		Centre=(i+np.random.rand())*Sections+Start
		Height=Signal[np.argmin(np.abs(x_axis-Centre))]-np.min(Signal)
		Vector=[Height,Centre,Width]

		Opt=spo.minimize(Loss,Vector,bounds=Bounds).x

		Results.append(Opt)
		Loss_Results.append(Loss(Opt))

	#------Select most effective peak postion

	return Results[np.argmin(Loss_Results)].tolist()

def Optimise_Prexisting_Peaks(x_axis,Signal,Peak_Params,Max_Width,Peak_Type='L'):
	"""
	Given a signal and an existing close fit, optimises it. First optimises just the peak heights, then all the parameters.
	"""
	Peaks=[]
	Vector=[]
	n=0
	while n<len(Peak_Params):
		if Peak_Type=='L':
			Peaks.append(L(x_axis,1,Peak_Params[n+1],Peak_Params[n+2]))
		else:
			Peaks.append(G(x_axis,1,Peak_Params[n+1],Peak_Params[n+2]))
		Vector.append(Peak_Params[n])
		n+=3

	Bounds=[]
	for i in Vector:
		Bounds.append((0,np.inf))

	def Loss(Vector):
		Output=0.
		for i in range(len(Vector)):
			Output+=Vector[i]*Peaks[i]
		return np.sum(np.abs(Output-Signal))

	Heights=spo.minimize(Loss,Vector,bounds=Bounds).x

	Vector=[]
	Bounds=[]

	for i in range(len(Heights)):
		Vector+=[Heights[i],Peak_Params[i*3+1],Peak_Params[i*3+2]]
		Bounds+=[(0,np.inf),(np.min(x_axis),np.max(x_axis)),(0,Max_Width)]

	if Peak_Type=='L':
		def Loss(Vector):
			return np.sum(np.abs(Multi_L(x_axis,*Vector)-Signal))
	else:
		def Loss(Vector):
			return np.sum(np.abs(Multi_G(x_axis,*Vector)-Signal))

	return spo.minimize(Loss,Vector,bounds=Bounds).x.tolist()

def Run(x_axis,Signal,Maximum_FWHM=40,Regions=50,Minimum_Width_Factor=0.1,Peak_Type='L',Print=True,Initial_Fit=None):
	"""
	Main function. Explained at top. 
	"""

	if Regions>len(Signal):
		Regions=len(Signal)

	if Peak_Type=='L':
		def Loss(Vector):
			return np.sum(np.abs(Multi_L(x_axis,*Vector)-Signal))
		Width=Wavelet_Estimate_Width(x_axis,Signal,Maximum_FWHM)*0.5
		Max_Width=Maximum_FWHM*0.5

	else:
		def Loss(Vector):
			return np.sum(np.abs(Multi_G(x_axis,*Vector)-Signal))
		Width=old_div(Wavelet_Estimate_Width(x_axis,Signal,Maximum_FWHM),((2.*np.log(2.))**0.5))
		Max_Width=old_div(Maximum_FWHM,((2.*np.log(2.))**0.5))

	Minimum_Width=Width*Minimum_Width_Factor

	Loss_Results=[]
	Results=[[]]
	while Regions<=len(Signal):

		if Initial_Fit is None:

			Result=copy.deepcopy(Results[-1])+Add_New_Peak(x_axis,Signal,Results[-1],Width,Max_Width,Regions=Regions)

			Bounds=[]
			n=0
			while n<len(Result):
				Bounds+=[(0,np.inf),(np.min(x_axis),np.max(x_axis)),(0,Max_Width)]
				n+=3

			Opt=spo.minimize(Loss,Result,bounds=Bounds).x.tolist()

			Output=[]
			n=0
			while n<len(Opt):
				if Opt[n]!=0 and Opt[n+2]>Minimum_Width:
					Output+=Opt[n:n+3]
				n+=3

		else:
			Output=Optimise_Prexisting_Peaks(x_axis,Signal,Initial_Fit,Max_Width,Peak_Type)
			Initial_Fit=None

		Results.append(Output)
		Loss_Results.append(Loss(Output))

		if Print is True:
			print('Iteration ',len(Loss_Results),', Peaks Found: ',old_div(len(Results[-1]),3))

		#---Check to increase region by x5
		if len(Loss_Results)>1:
			if Loss_Results[-1]>=Loss_Results[-2]: #Has loss gone up?
				Regions*=5
			elif len(Results[-1])==len(Results[-2]): #Otherwise, same number of peaks?
				Old,Current=[],[]
				n=0
				while n<len(Results[-2]):
					Old.append([Results[-2][n+1],Results[-2][n+2]])
					Current.append([Results[-1][n+1],Results[-1][n+2]]) #Collect peak positions and widths for last two iterations
					n+=3

				Old=Quick_Sort(Old,0) #Order old iteration in position order

				Temp=[]
				Current=np.array(np.transpose(Current))
				for i in Old:
					Arg=np.argmin(np.abs(Current[0]-i[0]))
					Temp.append([Current[0][Arg],Current[1][Arg]])  #For each old peak, find the closest new peak
					Current[0][Arg]=np.inf 
				Current=Temp

				End=False
				while End is False:
					End=True
					for i in range(len(Old))[1:]:  #Check that swapping any adjacent sets of new peaks doesn't imporve the match between old and new peaks
						Delta=abs(Old[i-1][0]-Current[i-1][0])+abs(Old[i][0]-Current[i][0])-abs(Old[i-1][0]-Current[i][0])-abs(Old[i][0]-Current[i-1][0])
						if Delta>0:
							End=False
							Current=Current[:i-1]+[Current[i],Current[i-1]]+Current[i+1:]
				
				Current=np.transpose(Current)
				Old=np.transpose(Old)
				if Peak_Type=='L': #Scale widths to FWHM
					Current[1]*=2 
					Old[1]*=2 
				else:
					Old[1]*=((2.*np.log(2.))**0.5)
					Current[1]*=((2.*np.log(2.))**0.5)

				Seperation=np.abs(Old[0]-Current[0])
				Threshold=(Old[1]+Old[0])*0.125

				if True not in (Seperation>=Threshold).tolist():  #Check if all peaks have moved by less than 0.25 FWHM
					Regions*=5


	if Peak_Type=='L':
		def Final_Fitting_Function(x,*Params):
			return Multi_L(x,*Params[1:])+Params[0]
	else:
		def Final_Fitting_Function(x,*Params):
			return Multi_G(x,*Params[1:])+Params[0]

	Output=None
	while Output is None and len(Results)>0:
		BL,BU=[0],[np.inf]
		n=0
		while n<len(Results[-1]):
			BL+=[0,np.min(x_axis),0]
			BU+=[np.inf,np.max(x_axis),Max_Width]
			n+=3
		try:
			Fits=spo.curve_fit(Final_Fitting_Function,x_axis,Signal,[0]+Results[-1],bounds=(BL,BU))
			Fits=[Fits[0],np.sqrt(np.diag(Fits[1]))]
			Output=[Fits[0][1:],Fits[1][1:]]
		except RuntimeError:
			Results=Results[:-1]

	if Output is None:
		Output=[None,None]

	return Output

def Worker_Function(x_axis,Signal,Maximum_FWHM,Regions,Minimum_Width_Factor,Peak_Type,Initial_Fit,Number):
		Fit=Run(x_axis,Signal,Maximum_FWHM,Regions,Minimum_Width_Factor,Peak_Type,Initial_Fit=Initial_Fit,Print=False)
		print('Fit Spectrum:',Number)
		return [Fit,Number]

def Fit_Set_of_Spectra(x_axis,Signals,Maximum_FWHM=40,Regions=50,Minimum_Width_Factor=0.1,Peak_Type='L',Cores=2,Utilise_Persistent=False):

	"""
	Utilises multiprocessing to run a set of fits in parrallel.
	"""

	if Utilise_Persistent is True:
		Median_Signal=np.median(Signals,axis=0)
		Initial_Peaks=Run(x_axis,Median_Signal,Maximum_FWHM,Regions,Minimum_Width_Factor,Peak_Type,Print=False)[0]
	else:
		Initial_Peaks=None

	Processes=[]
	Pool=mp.Pool(processes=Cores)

	for i in range(len(Signals)):
		Processes.append(Pool.apply_async(Worker_Function,args=(x_axis,Signals[i],Maximum_FWHM,Regions,Minimum_Width_Factor,Peak_Type,Initial_Peaks,i)))
	
	Results=[p.get() for p in Processes]

	Pool.close()

	Results=Quick_Sort(Results,1)

	for i in range(len(Results)):
		Results[i]=Results[i][0]

	return Results