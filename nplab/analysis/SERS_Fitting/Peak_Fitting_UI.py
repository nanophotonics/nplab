# -*- coding: utf-8 -*-
"""
Peak Fitting Program

Author: Jack Griffiths
Date: March 2018

This allows for Lorentzian peaks to be fit easily to a time series of spectra. This spectral scan should be cleaned up using the adaptive-polynomial
method to remove any non-constant background. 

To run this, use Run(Array,x_axis,Threshold=None). Array is the 2D array of the spectral scan. x_axis is a 1D array detailing the x_axis values of
each spectrum. Threshold adds a threshold to any image of the scan. This can be altered with the mouse wheel when such images are shown. Follow 
the instructions as they appear to complete the process. 

The output is a list. Each element represents one spectrum and has the form [Fitting Parameters, Fitting Errors]. The Parameters go in the order
[Peak Centre, Peak Width, Peak Height, Peak Center,.......].

To visualise the results, use View_Results(Array,x_axis,Start_Spectrum,End_Spectrum,Fit,Threshold=None). 

If the fits display "crosstalk", use the function Reorder_Peaks(Fits).
"""
from __future__ import division
from __future__ import print_function


from builtins import input
from builtins import str
from builtins import range
from past.utils import old_div
import matplotlib
matplotlib.use('Qt4Agg')
import matplotlib.pyplot as pl
import numpy as np
import multiprocessing as mp
import scipy.optimize as spo

def Select_Time_Range(Min,Max):
	"""
	Asks the user for lower and upper spectrum numbers. Min and Max define the allowed range for these values.
	"""

	Continue=False

	while Continue is False:

		Lower=None
		while Lower is None:
			Input=eval(input('Please Enter a Lower Spectrum Number (Type \'Cancel\' to cancel): '))
			if Input.upper()=='CANCEL':
				return None,None
			else:
				try:
					Input=int(Input)
					if Input<Min or Input>Max:
						print('Invalid')
					else:
						Lower=Input
				except ValueError:
					print('Invalid')

		Upper=None
		while Upper is None:
			Input=eval(input('Please Enter a Upper Spectrum Number (Type \'Cancel\' to cancel): '))
			if Input.upper()=='CANCEL':
				return None,None
			else:
				try:
					Input=int(Input)
					if Input<Min or Input>Max or Input<=Lower:
						print('Invalid')
					else:
						Upper=Input
				except ValueError:
					print('Invalid')

		Input=eval(input('Continue with range '+str(Lower)+' to '+str(Upper)+'? (Y/N): '))
		if Input.upper()=='Y':
			Continue=True

	return Lower,Upper

def Select_Peaks(Array,Threshold,Color='r',Extra_Lines=None,colormap='inferno'):
	"""
	Allows the select vertical lines on the array, and returns their x-axis positions.
	Array is an array. Threshold thresholds the colormap. Color is color of lines to draw. Extra lines goes 
	as [[List of Lines,Color],[List of Lines,Color] etc] and ditactes extra lines to be drawn on the image.
	"""

	Peaks=[]
	End=[False]
	Draw=[True]

	pl.ion()
	fig=pl.figure()

	if Threshold is None:
		Threshold=np.max(Array)
	Step=0.1*(Threshold-np.min(Array))
	Threshold=[Threshold,np.min(Array)]

	def Mouse_Press(event):
		if event.button==1:
			Peaks.append(event.xdata)
		if event.button==3 and len(Peaks)>0:
			Peaks.remove(Peaks[-1])
		Draw[0]=True

	def Button_Press(event):
		if event.key=='enter':
			End[0]=True

	def Scroll(event):
		if event.button=='up':
			Threshold[0]+=Step
		if event.button=='down':
			Threshold[0]-=Step
			if Threshold[0]<=Threshold[1]:
				Threshold[0]+=Step
		Draw[0]=True

	fig.canvas.mpl_connect('key_press_event', Button_Press)
	fig.canvas.mpl_connect('button_press_event', Mouse_Press)
	fig.canvas.mpl_connect('scroll_event', Scroll)


	while End[0] is False:
		pl.pause(0.05)
		if Draw[0] is True:
			Draw[0]=False
			pl.clf()
			pl.imshow(Array,interpolation='None',origin='lower',cmap=colormap,aspect=float(len(Array[0]))/len(Array),vmax=Threshold[0])
			pl.xlabel('Array Element')
			pl.ylabel('Spectrum')
			for i in Peaks:
				pl.plot([i,i],[0,len(Array)-1],Color+'--')
			if Extra_Lines is not None:
				for i in Extra_Lines[0]:
					pl.plot([i,i],[0,len(Array)-1],Extra_Lines[1]+'--')
			pl.xlim([0,len(Array[0])])
			pl.ylim([0,len(Array)])
	pl.ioff()
	pl.close()

	return Peaks

def Input_Width():
	Output=None
	while Output is None:
		Input=eval(input('Please Enter an Approximate Peak Width in Given X-Axis Units (Type \'Cancel\' to cancel): '))
		if Input.upper()=='CANCEL':
				return None
		else:
			try:
				Input=int(Input)
				if Input<=0:
					print('Invalid')
				else:
					Output=Input
			except ValueError:
				print('Invalid')
	return Output

def Input_Core_Number():
	"""
	Asks the user for a number of cores to use
	"""
	Maximum=mp.cpu_count()
	Output=None
	while Output is None:
		Input=eval(input('Please Enter the Number of CPU Cores to Utilise: '))
		try:
			Input=int(Input)
			if Input<=0:
				print('Invalid: Negative/Zero')
			else:
				if Input>Maximum:
					print('Invalid: This number of CPU cores is not available')
				else:
					Output=Input
		except ValueError:
			print('Invalid')
	return Output

def Quick_Sort(List,Argument):
	#Sorts a List based on the numberimal value of the Argument element.
	def Split(List,Argument):
		#List is list of lists to seperate
		#Argument is lsit argument to seperate via

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


def Lorentzian(x,Centre,Width,Height):
	"""
	Defines a Lorentzian
	"""
	return old_div(Height,(1+((old_div((x-Centre),Width))**2)))

def Constant_plus_Lorentzians(x,*Params):
	"""
	Defines a constant plus an arbitary sum of Lorentzians
	"""
	Output=Params[0]
	n=1
	while n<len(Params):
		Output+=Lorentzian(x,*Params[n:n+3])
		n+=3
	return Output

def Fitting_Worker(Function,x,y,Initial,Bounds,Label):
	"""
	Worker to complete the fitting. Function is function to fit. x and y is the data. Initial is a guess for the fitting parameters.
	Bounds are the bounds for the fitting. Label is a number labelling which spectrum is being fit here. Returns [Parameters, Errors] which can 
	all be None if the fitting fails.
	"""
	try:
		Output=spo.curve_fit(Function,x,y,Initial,bounds=Bounds)
		Output=[Output[0],np.sqrt(np.diag(Output[1])),Label]
	except RuntimeError:
		Output=[]
		while len(Output)<len(Initial):
			Output.append(None)
		Output=[Output,Output,Label]
	return Output

def Run_Fitting(Array,x_axis,Center_Guesses,Width_Guess,Cores):
	"""
	Takes an array, the x_axis list, guesses for the peak positions (Center_Guesses) and a peak width (Width_Guess) and completes the fitting using Cores cores.
	"""

	Bounds_Lower=[-np.inf]
	Bounds_Upper=[np.inf]
	for i in range(len(Center_Guesses)):
		Bounds_Lower+=[x_axis[0],0,0]
		Bounds_Upper+=[x_axis[-1],np.inf,np.inf]

	Processes=[]
	Pool=mp.Pool(processes=Cores)

	for i in range(len(Array)):

		Heights=[]

		for j in Center_Guesses:
			Lower_x=j-(0.5*Width_Guess)
			Upper_x=j+(0.5*Width_Guess)
			Lower_element=0
			while x_axis[Lower_element]<Lower_x:
				Lower_element+=1
			Upper_element=Lower_element
			while x_axis[Upper_element]<Upper_x:
				Upper_element+=1
			Heights.append(np.max(Array[i][Lower_element:Upper_element])-np.min(Array[i][Lower_element:Upper_element]))

		Initial=[0.]
		for j in range(len(Center_Guesses)):
			Initial+=[Center_Guesses[j],Width_Guess,Heights[j]]

		Processes.append(Pool.apply_async(Fitting_Worker,args=(Constant_plus_Lorentzians,x_axis,Array[i],Initial,(Bounds_Lower,Bounds_Upper),i)))

	Results=[p.get() for p in Processes]

	Pool.close()

	Results=Quick_Sort(Results,2)

	for i in range(len(Results)):
		Results[i]=Results[i][:-1]

	return Results

def Convert_to_x_value(Element,x_axis):
	"""
	Converts a postions in terms of an Element value in the array into its approx value along the x_axis.
	"""
	x0=x_axis[int(Element)]
	x1=x_axis[int(Element)+1]
	Weight=Element%1
	return (Weight*(x1-x0))+x0

def Run(Array,x_axis,Threshold=None,colormap='inferno'):
	"""
	Runs the fitting, including the UI. Array is the array to fit. x_axis is the corresponding x axis values. Threshold 
	is a value to threshold the images of the array.
	"""

	#---------Select time range---------------
	Lower,Upper=Select_Time_Range(0,len(Array)-1)
	if Lower is None:
		return
	
	To_Fit=Array[Lower:Upper+1]

	#----------Select Peaks-------------

	print('==========')
	print("Please use your left mouse button to select peaks to track. Use your right mouse button to erase the last selection. Press Enter when done.")
	print('==========')

	Peaks=Select_Peaks(To_Fit,Threshold,colormap=colormap)
	Peaks=sorted(Peaks)

	#-------------Select Interpeak Bounds

	print('==========')
	print("Fitting will be faster and less likely to fail if each spectrum is split into sections.")
	print("Please use your left mouse button to select section boundaries. Use your right mouse button to erase the last selection. Press Enter when done.")
	print('==========')

	Bounds=Select_Peaks(To_Fit,Threshold,'w',[Peaks,'r'],colormap=colormap)
	Bounds=sorted(Bounds)
	Bounds=[0]+Bounds+[len(To_Fit[0])]

	#--------Select Peak Width------

	Width=Input_Width()
	if Width is None:
		return

	#------Select Cores to Run-------

	Cores=Input_Core_Number()

	#----Define array sections to fit-----

	Sections=[]
	n=1
	while n<len(Bounds):
		In_Bounds=[]
		for i in Peaks:
			if i>Bounds[n-1] and i<Bounds[n]:
				In_Bounds.append(i)
		if len(In_Bounds)>0:
			Sections.append([Bounds[n-1],Bounds[n],In_Bounds])
		n+=1

	#-----Convert Peak Guesses to Correct units------

	for i in range(len(Sections)):
		for j in range(len(Sections[i][2])):
			Sections[i][2][j]=Convert_to_x_value(Sections[i][2][j],x_axis)

	#----Hold------

	Hold=eval(input('Press Enter to Begin'))

	#---------Fit Array Sections----------------

	Results=[]

	for i in Sections:
		print('Fitting.....')
		Results.append(Run_Fitting(np.transpose(np.transpose(To_Fit)[int(i[0]):int(i[1])]),x_axis[int(i[0]):int(i[1])],i[2],Width,Cores))

	Output=[]
	for i in range(len(To_Fit)):
		Output.append([[],[]])
		for j in Results:
			if isinstance(j[i][0],list) is True:
				Output[-1][0]+=j[i][0][1:]
			else:
				Output[-1][0]+=j[i][0][1:].tolist()
			if isinstance(j[i][1],list) is True:
				Output[-1][1]+=j[i][1][1:]
			else:
				Output[-1][1]+=j[i][1][1:].tolist()
	return Output

def View_Results(Array,x_axis,Start_Spectrum,End_Spectrum,Fit,Threshold=None):
	To_Show=Array[Start_Spectrum:End_Spectrum]
	pl.imshow(To_Show,interpolation='None',origin='lower',cmap='inferno',aspect=float(len(To_Show[0]))/len(To_Show),vmax=Threshold)

	Peaks=[]
	for i in Fit:
		Peak=[]
		n=0
		while n<len(i[0]):
			Peak.append(i[0][n])
			n+=3
		Peaks.append(Peak)
	Peaks=np.array(Peaks)
	Peaks=np.transpose(Peaks)

	for i in Peaks:
		To_Plot=[]
		for j in i:
			if j is not None:
				n=0
				while x_axis[n]<j:
					n+=1
				Weight=old_div((j-x_axis[n-1]),(x_axis[n]-x_axis[n-1]))
				To_Plot.append(n-1.+Weight)
			else:
				To_Plot.append(None)
		pl.plot(To_Plot,list(range(len(To_Show))),'b-')
	pl.xlim([0,len(To_Show[0])])
	pl.ylim([0,len(To_Show)])
	
	pl.show()

def View_Results_Video(Array,x_axis,Start_Spectrum,End_Spectrum,Fit,Frame_Time=0.1):
	To_Show=Array[Start_Spectrum:End_Spectrum]
	
	Peaks=[]
	for i in Fit:
		Peak=[]
		n=0
		while n<len(i[0]):
			Peak.append(i[0][n])
			n+=3
		Peaks.append(Peak)
	Peaks=np.array(Peaks)
	Peaks=np.transpose(Peaks)

	for i in range(len(To_Show)):
		pl.plot(x_axis,To_Show[i],'k-')
		for j in Peaks[i]:
			if j is not None:
				pl.plot([j,j],[0,np.max(To_Show[i])],'r-')
		pl.show()
		pl.pause(Frame_Time)
		pl.clf()
	pl.close()

def Reorder_Peaks(Fits):
	"""
	Function to reorder the fits to minimise the crosstalk between adjacent peaks.
	"""
	Start=0
	while Start<len(Fits) and None in Fits[Start][0]:
		Start+=1
	if Start==len(Fits):
		print('No fully sucessfull fits detected!')
		return
	else:
		Results=[Fits[Start]]
		Current=[]
		for i in range(old_div(len(Fits[Start][0]),3)):
			Current.append(Fits[Start][0][i*3])
		To_Sort=Start+1
		while To_Sort<len(Fits):
			print(To_Sort)
			Sorting_Positions=[]
			for i in range(old_div(len(Fits[To_Sort][0]),3)):
				Sorting_Positions.append(Fits[To_Sort][0][i*3])
			Sorting_Order=list(range(len(Sorting_Positions)))
			Trigger=True
			while Trigger is True:
				Trigger=False
				Pos1=0
				while Pos1<len(Sorting_Order):
					Pos2=Pos1+1
					while Pos2<len(Sorting_Order):
						Change=0
						if Sorting_Positions[Sorting_Order[Pos1]] is not None:
							Change+=abs(Current[Pos1]-Sorting_Positions[Sorting_Order[Pos1]])-abs(Current[Pos2]-Sorting_Positions[Sorting_Order[Pos1]])
						if Sorting_Positions[Sorting_Order[Pos2]] is not None:
							Change+=abs(Current[Pos2]-Sorting_Positions[Sorting_Order[Pos2]])-abs(Current[Pos1]-Sorting_Positions[Sorting_Order[Pos2]])
				
						if Change>0:
							Temp=Sorting_Order[Pos1]
							Sorting_Order[Pos1]=Sorting_Order[Pos2]
							Sorting_Order[Pos2]=Temp
							Trigger=True
						Pos2+=1
					Pos1+=1
			Result=[[],[]]
			for i in Sorting_Order:
				Result[0]+=Fits[To_Sort][0][i*3:(i+1)*3]
				Result[1]+=Fits[To_Sort][1][i*3:(i+1)*3]
			Results.append(Result)
			Current_new=[]
			for i in range(old_div(len(Result[0]),3)):
				if Result[0][i*3] is not None:
					Current_new.append(Result[0][i*3])
				else:
					Current_new.append(Current[i])
			Current=Current_new
			To_Sort+=1

		Current=[]
		for i in range(old_div(len(Fits[Start][0]),3)):
			Current.append(Fits[Start][0][i*3])
		To_Sort=Start-1
		while To_Sort>=0:
			print(To_Sort)
			Sorting_Positions=[]
			for i in range(old_div(len(Fits[To_Sort][0]),3)):
				Sorting_Positions.append(Fits[To_Sort][0][i*3])
			Sorting_Order=list(range(len(Sorting_Positions)))
			Trigger=True
			while Trigger is True:
				Trigger=False
				Pos1=0
				while Pos1<len(Sorting_Order):
					Pos2=Pos1+1
					while Pos2<len(Sorting_Order):
						Change=0
						if Sorting_Positions[Sorting_Order[Pos1]] is not None:
							Change+=abs(Current[Pos1]-Sorting_Positions[Sorting_Order[Pos1]])-abs(Current[Pos2]-Sorting_Positions[Sorting_Order[Pos1]])
						if Sorting_Positions[Sorting_Order[Pos2]] is not None:
							Change+=abs(Current[Pos2]-Sorting_Positions[Sorting_Order[Pos2]])-abs(Current[Pos1]-Sorting_Positions[Sorting_Order[Pos2]])
						
						if Change>0:
							Temp=Sorting_Order[Pos1]
							Sorting_Order[Pos1]=Sorting_Order[Pos2]
							Sorting_Order[Pos2]=Temp
							Trigger=True
						Pos2+=1
					Pos1+=1
			Result=[[],[]]
			for i in Sorting_Order:
				Result[0]+=Fits[To_Sort][0][i*3:(i+1)*3]
				Result[1]+=Fits[To_Sort][1][i*3:(i+1)*3]
			Results=[Result]+Results
			Current_new=[]
			for i in range(old_div(len(Result[0]),3)):
				if Result[0][i*3] is not None:
					Current_new.append(Result[0][i*3])
				else:
					Current_new.append(Current[i])
			Current=Current_new
			To_Sort-=1

	return Results