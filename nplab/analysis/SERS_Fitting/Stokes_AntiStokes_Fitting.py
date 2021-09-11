from __future__ import division
from __future__ import print_function
from builtins import range
from past.utils import old_div
import numpy as np 
import scipy.ndimage.filters as ndimf
import scipy.interpolate as scintp
import copy
import scipy.optimize as spo
import matplotlib.pyplot as pl
import scipy.integrate as scint

"""
Author: Jack Griffiths Oct 2019

This code changed purpose slighly while writing convoluted. Could do with rewrite.

The purpose of this code is to automatically fit a spectrum containing both Stokes and Anti-Stokes SERS. Getting an accurate fit of the peaks is not the absolute
priority, these must simply fit well enough to give context when removing the SERS background in this region. Other peak fitting tools can then be applied to 
the signal with background removed is required.

This module runs (kind of bad design) through the function 
Fit(Shift,Signal,Poly_Order_AS=4,Poly_Order_S=4,Smoothing_Width=30,Noise_Smoothing=2,Peak_Threshold_Window=5,Default_Peak_Width=10.,Minimum_Peak_Width=5.,Maximum_Peak_Width=30.,Iterations=2,Plot=False,Allowed_Peak_Fraction_In_Notch=0.1)

Shift is the x-axis (lower to higher) and Signal is the y axis. The signal is Guassian smoothed by a amount Smoothing_Width which is in cm-1. This is a large value
to smear out spectral featrues but retain the edge of the notch filter. This smoothed signal is used to idenfity the probable width of the notch. On the anti-Stokes
and Stokes sides of the spectrum, the background is fit by polynomials of order Poly_Order_AS and Poly_Order_S respectivly. As an intial fit for these, the signal is
gently smoothed by width Noise_Smoothing and local minima found for the background fits to pass through. The notch filter is represented by a sum of two sigmoid
functions that the final fit is multiplied by. A small laser leak peak is added back in.

The add peaks to the fit, the standard deviation of the noise is estimated. Any regions where the signal deviateds from the current fit by more than this for 
Peak_Threshold_Window points in a row is defined as a possible peak area. All possible peak areas are checked to see which best suits the addition of a peak.
This peak has default width of Default_Peak_Width, and a minimum and maximum width of Minimum_Peak_Width and Maximum_Peak_Width. The new peak and all current peaks
are optimised and the possible peak areas re-evaluated.This repeats.

The background and peaks are then optimised together. It is likely the number of peaks added has been over-zealous, so the system then next starts removing peaks
and seeing if the system actually fits better. After each peak is removed everything is re-optimised together.

It is possible for the edge of the notch to be spoofed with a peak, so any peaks whose area supressed by the notch is greater than Allowed_Peak_Fraction_In_Notch
is removed.

Finally, the loop of adding and removing peaks is repeated Iterations times.

The function returns two things, the first is an array containing:
	-The full fit of the signal
	-The original signal with the fitted background removed
	-The fit of the signal peaks

The second is a dictionary containing the centres, widths and heights of the found peaks.
"""

def Sigmoid(x,O,S):
	return 1./(1.+np.exp(-(old_div((x-O),S))))

def Polynomial(x,Anchors,Anchor_Values):
	return  np.polyval(np.polyfit(Anchors,Anchor_Values,len(Anchors)-1),x)

def L(x,H,C,W):
	return old_div(H,(1.+((old_div((x-C),W))**2)))

def Fit(Shift,Signal,Poly_Order_AS=4,Poly_Order_S=4,Smoothing_Width=30,Noise_Smoothing=2,Peak_Threshold_Window=5,Default_Peak_Width=10.,Minimum_Peak_Width=5.,Maximum_Peak_Width=30.,Iterations=2,Allowed_Peak_Fraction_In_Notch=0.1):
	
	Smooth=ndimf.gaussian_filter(Signal,old_div(Smoothing_Width,np.median(np.abs(np.diff(Shift)))))

	#--Gradient: Find notch filter--

	x=np.linspace(np.min(Shift),np.max(Shift),int(np.round(old_div((np.max(Shift)-np.min(Shift)),np.min(np.abs(np.diff(Shift))))))+1)
	y=scintp.interp1d(Shift,Smooth,kind='cubic')(x)

	A=np.array(np.array(y).tolist()+[y[-1],y[-2]])
	B=np.array([y[1],y[0]]+np.array(y).tolist())

	Grad=(A-B)[1:-1]

	x2=np.linspace(0,np.min([np.max(Shift),-np.min(Shift)]),int(np.round(old_div((np.max(Shift)-np.min(Shift)),np.min(np.abs(np.diff(Shift))))))+1)
	y2=scintp.interp1d(x,Grad,kind='cubic')(x2)-scintp.interp1d(x,Grad,kind='cubic')(-x2)

	Notch_Filter_Edge=x2[np.argmax(y2)]

	#--Set up initial background estimate for the highest signal spectrum--
	
	Smooth=ndimf.gaussian_filter(Signal,Noise_Smoothing)
	Constant=np.min(Smooth)

	AS_Anchors=[]
	AS_Anchor_Values=[]

	Position=np.argmin(np.abs(Shift+Notch_Filter_Edge))
	while Smooth[Position-1]>Smooth[Position]:
		Position-=1

	AS_Anchors.append(copy.deepcopy(Shift[Position]))
	AS_Anchor_Values.append(copy.deepcopy(Smooth[Position])-Constant)

	Edges=np.round(np.linspace(0,Position,Poly_Order_AS+2)).astype(int)

	for i in range(len(Edges))[1:-1]:
		Best=np.argmin(Smooth[Edges[i-1]:Edges[i]])+Edges[i-1]
		AS_Anchors.append(Shift[Best])
		AS_Anchor_Values.append(Smooth[Best]-Constant)

	AS_Anchor_Values=AS_Anchor_Values[1:]+[AS_Anchor_Values[0]]
	AS_Anchors=AS_Anchors[1:]+[AS_Anchors[0]]


	S_Anchors=[]
	S_Anchor_Values=[]

	Position=np.argmin(np.abs(Shift-Notch_Filter_Edge))
	while Smooth[Position+1]>Smooth[Position]:
		Position+=1

	Edges=np.round(np.linspace(Position,len(Smooth)-1,Poly_Order_S+2)).astype(int)

	S_Anchors.append(copy.deepcopy(Shift[Position]))
	S_Anchor_Values.append(copy.deepcopy(Smooth[Position])-Constant)

	for i in range(len(Edges))[2:]:
		Best=np.argmin(Smooth[Edges[i-1]:Edges[i]])+Edges[i-1]
		S_Anchors.append(Shift[Best])
		S_Anchor_Values.append(Smooth[Best]-Constant)

	def Generate(Vector):
		Constant=Vector[0]
		Sigmoid_Data_AS=Vector[1:3]
		Sigmoid_Data_S=Vector[3:5]
		Poly_AS=Vector[5:6+Poly_Order_AS]
		Poly_S=Vector[6+Poly_Order_AS:7+Poly_Order_AS+Poly_Order_S]
		Laser_Leak=Vector[7+Poly_Order_AS+Poly_Order_S:10+Poly_Order_AS+Poly_Order_S]

		Output=Shift*0
		Output+=Polynomial(Shift,AS_Anchors,Poly_AS)*(Shift<0)
		Output+=Polynomial(Shift,S_Anchors,Poly_S)*(Shift>=0)
		

		Mask=Sigmoid(Shift,*Sigmoid_Data_AS)+Sigmoid(Shift,*Sigmoid_Data_S)

		return (Output*Mask)+Constant+L(Shift,*Laser_Leak)

	Vector=[Constant,-Notch_Filter_Edge,-1.,Notch_Filter_Edge,1.]
	for i in AS_Anchor_Values:
		Vector.append(i)
	for i in S_Anchor_Values:
		Vector.append(i)
	Vector+=[1.,0.,10.]

	#--Optimise Notch Edges--

	def Loss(Input):
		V=copy.deepcopy(Vector)
		for i in range(4):
			V[i+1]=Input[i]
		return np.sum(np.abs(Generate(V)-Signal))

	Vector[1:5]=spo.minimize(Loss,Vector[1:5]).x.tolist()

	#--Add Laser Leak--

	def Loss(Input):
		V=copy.deepcopy(Vector)
		for i in range(3):
			V[i-3]=Input[i]
		return np.sum(np.abs(Generate(V)-Signal))

	Vector[-3]=np.max(Smooth[np.argmin(np.abs(Shift+10)):np.argmin(np.abs(Shift-10))])-Constant
	Vector[-3:]=spo.minimize(Loss,Vector[-3:]).x.tolist()

	#--Iterate Background---

	Mask=(Shift*0).astype(bool)

	End=False
	def Loss(Vector):
		Gen=Generate(Vector)
		return np.sum(np.abs(Gen-Signal)[Mask==False])

	while End is False:
		Vector=spo.minimize(Loss,Vector).x.tolist()

		Sub=Signal-Generate(Vector)
		Below=Sub[Sub<0]
		Std=np.mean(np.square(Below))**0.5

		Above_Std=(Sub>=Std)
		if Peak_Threshold_Window%2==0:
			Peak_Threshold_Window+=1
		Skip=old_div((Peak_Threshold_Window-1),2)
		Possible_Peak=[]
		for i in range(Skip):
			Possible_Peak.append(False)
		for i in range(len(Above_Std))[Skip:-Skip]:
			if np.sum(Above_Std[i-Skip:i-Skip+Peak_Threshold_Window])==Peak_Threshold_Window:
				Possible_Peak.append(True)
			else:
				Possible_Peak.append(False)
		for i in range(Skip):
			Possible_Peak.append(False)

		Possible_Peak=np.array(Possible_Peak)

		if np.sum(Possible_Peak==Mask)==len(Possible_Peak):
			End=True
		else:
			Mask=Possible_Peak

	def Generate_Peaks(Input):
		Output=Shift*0
		n=0
		while n<len(Input):
			Output+=L(Shift,*Input[n:n+3])
			n+=3
		Output*=(Sigmoid(Shift,*Vector[1:3])+Sigmoid(Shift,*Vector[3:5]))
		return Output

	def Sub_Loss(Input):
		return np.sum(np.abs(Generate_Peaks(Input)-Sub))

	Peaks_Vector=[]
	for Iteration in range(Iterations):
		print('Iteration:',Iteration+1)

		Bounds=[]
		for i in range(old_div(len(Peaks_Vector),3)):
			Bounds+=[(0,np.inf),(-np.inf,np.inf),(Minimum_Peak_Width,Maximum_Peak_Width)]

		End=False
		while End is False:

			#print Peaks_Vector

			Sub=Signal-Generate(Vector)-Generate_Peaks(Peaks_Vector)

			Below=Sub[Sub<0]
			Std=np.mean(np.square(Below))**0.5

			Above_Std=(Sub>=Std)

			if Peak_Threshold_Window%2==0:
				Peak_Threshold_Window+=1
			Skip=old_div((Peak_Threshold_Window-1),2)
			Possible_Peak=[]
			for i in range(Skip):
				Possible_Peak.append(False)
			for i in range(len(Above_Std))[Skip:-Skip]:
				if np.sum(Above_Std[i-Skip:i-Skip+Peak_Threshold_Window])==Peak_Threshold_Window:
					Possible_Peak.append(True)
				else:
					Possible_Peak.append(False)
			for i in range(Skip):
				Possible_Peak.append(False)

			Possible_Peak=np.array(Possible_Peak)
			if np.sum(Possible_Peak)>0:

				Sub=Signal-Generate(Vector)
				Loss=[]
				Checked=[]
				for i in np.array(list(range(len(Shift))))[Possible_Peak]:
					Loss.append(np.sum(np.abs(L(Shift,np.max([Sub[i],0]),Shift[i],Default_Peak_Width)-Sub)))
					Checked.append(i)
				
				Peaks_Vector+=[Sub[Checked[np.argmin(Loss)]],Shift[Checked[np.argmin(Loss)]],Default_Peak_Width]
				Bounds+=[(0,np.inf),(-np.inf,np.inf),(Minimum_Peak_Width,Maximum_Peak_Width)]

				n=0
				while n<len(Peaks_Vector):
					Peaks_Vector[n+2]=Default_Peak_Width
					n+=3

				Peaks_Vector=spo.minimize(Sub_Loss,Peaks_Vector,bounds=Bounds).x.tolist()

				Heights=[]
				n=0
				while n<len(Peaks_Vector):
					Heights.append(Peaks_Vector[n])
					n+=3
				if np.min(Heights)<Std:
					Non_Zero=[]
					n=0
					while n<len(Peaks_Vector):
						if Peaks_Vector[n]>=Std:
							Non_Zero+=Peaks_Vector[n:n+3]
						n+=3
					Peaks_Vector=Non_Zero
					End=True

			else:
				End=True

		#---Full_Optimize---

		def Full_Generate(x,*Input):
			Constant=Input[0]
			Sigmoid_Data_AS=Input[1:3]
			Sigmoid_Data_S=Input[3:5]
			Poly_AS=Input[5:6+Poly_Order_AS]
			Poly_S=Input[6+Poly_Order_AS:7+Poly_Order_AS+Poly_Order_S]
			Laser_Leak=Input[7+Poly_Order_AS+Poly_Order_S:10+Poly_Order_AS+Poly_Order_S]

			Peaks=Input[10+Poly_Order_AS+Poly_Order_S:]

			Output=Shift*0
			Output+=Polynomial(Shift,AS_Anchors,Poly_AS)*(Shift<0)
			Output+=Polynomial(Shift,S_Anchors,Poly_S)*(Shift>=0)
			n=0
			while n<len(Peaks):
				Output+=L(Shift,*Peaks[n:n+3])
				n+=3

			Mask=Sigmoid(Shift,*Sigmoid_Data_AS)+Sigmoid(Shift,*Sigmoid_Data_S)

			return (Output*Mask)+Constant+L(Shift,*Laser_Leak)

		def Full_Loss(Input):
			return np.sum(np.abs(Full_Generate(None,*Input)-Signal))

		Full_Bounds=[]
		for i in Vector:
			Full_Bounds.append((-np.inf,np.inf))	
		for i in range(old_div(len(Peaks_Vector),3)):
			Full_Bounds+=[(0,np.inf),(-np.inf,np.inf),(Minimum_Peak_Width,Maximum_Peak_Width)]
			

		Output=spo.minimize(Full_Loss,Vector+Peaks_Vector,bounds=Full_Bounds).x.tolist()
		Vector=Output[:len(Vector)]
		Peaks_Vector=Output[len(Vector):]

		#---Test for Redundent Peaks---

		Sub=Signal-Generate(Vector)

		Current_Loss=Sub_Loss(Peaks_Vector)

		Bounds=[[],[]]
		for i in Peaks_Vector:
			Bounds[0]+=[0,-np.inf,0]
			Bounds[1]+=[np.inf,np.inf,np.inf]
		Bounds[0]=Bounds[:-3]
		Bounds[1]=Bounds[:-3]

		End=False
		def To_Fit(x,*Input):
			return Generate_Peaks(Input)
		while End is False:
			print(old_div(len(Peaks_Vector),3))
			Options=[]
			Loss=[]
			for i in range(old_div(len(Peaks_Vector),3)):
				try:
					Options.append(spo.curve_fit(To_Fit,Shift,Sub,Peaks_Vector[:i*3]+Peaks_Vector[i*3+3:],bounds=Bounds)[0].tolist())
					Loss.append(Sub_Loss(Options[-1]))
				except RuntimeError:
					Options.append(None)
					Loss.append(np.inf)
			if np.min(Loss)<Current_Loss:
				Arg=np.argmin(Loss)
				Peaks_Vector=Peaks_Vector[:Arg*3]+Peaks_Vector[Arg*3+3:]
				Bounds[0]=Bounds[:-3]
				Bounds[1]=Bounds[:-3]

				Full_Bounds=[]
				for i in Vector:
					Full_Bounds.append((-np.inf,np.inf))	
				for i in range(old_div(len(Peaks_Vector),3)):
					Full_Bounds+=[(0,np.inf),(-np.inf,np.inf),(Minimum_Peak_Width,Maximum_Peak_Width)]
				Output=spo.minimize(Full_Loss,Vector+Peaks_Vector,bounds=Full_Bounds).x.tolist()
				Vector=Output[:len(Vector)]
				Peaks_Vector=Output[len(Vector):]
				
				Sub=Signal-Generate(Vector)
				Current_Loss=Sub_Loss(Peaks_Vector)
			else:
				End=True

		#--Edge of notch could be spoofed with fake peak, check for this---

		Mask=Sigmoid(Shift,*Vector[1:3])+Sigmoid(Shift,*Vector[3:5])

		Temp=[]
		for i in range(old_div(len(Peaks_Vector),3)):
			Peak=L(Shift,*Peaks_Vector[i*3:i*3+3])
			Fraction=old_div(scint.simps(Peak*Mask,Shift),scint.simps(Peak,Shift))
			if 1.-Fraction<Allowed_Peak_Fraction_In_Notch:
				Temp+=Peaks_Vector[i*3:i*3+3]

		Peaks_Vector=Temp
	
	Background_Removed=Signal-Generate(Vector)
	Fit=Full_Generate(None,*(Vector+Peaks_Vector))
	No_Background_Fit=Full_Generate(None,*(Vector+Peaks_Vector))-Generate(Vector)

	Peak_Dictionary={'Centres':[],'Widths':[],'Heights':[]}

	Centres=[]
	for i in range(old_div(len(Peaks_Vector),3)):
		Centres.append(Peaks_Vector[i*3+1])
	while np.sum(np.isinf(Centres))!=len(Centres):
		Arg=np.argmin(Centres)
		Peak_Dictionary['Centres'].append(Peaks_Vector[Arg*3+1])
		Peak_Dictionary['Widths'].append(Peaks_Vector[Arg*3+2])
		Peak_Dictionary['Heights'].append(Peaks_Vector[Arg*3])
		Centres[Arg]=np.inf

	return np.array([Fit,Background_Removed,No_Background_Fit]),Peak_Dictionary


	