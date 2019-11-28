from builtins import range
import numpy as np

"""
Author: jpg66

Module for removing SERS background in cases where Adaptive Polynomial produces too many artifacts. This may include cases with negative curvature and a low SNR. 
This should be used in cases where the peaks are sparse.

Run using Run(Signal,Window=50,Maximum_Iterations=10,Peak_Tolerance=0.5). This will return the bacgkround subtracted signal.

Signal is a 1D array containing the signal to the be background removed. All pairs of points Window apart in the array are considered, and the gradient of the straight
line between them calculated. This window must be an interger >=2, and if not will be increases to one. This window should be slightly larger than the peaks in the signal.
Each line gradient will be assigned to every point bounded by the line. The gradient at each point is taken as the median of all the gradient assigned to it. The resulting
smooth background is reconstructed from these gradients. The background substracted signal is shifted to have a median of 0.

This background will be overestimated slightly at peak positions. To account for this, peak postions are estimated. A noise threshold is estimated as the median of the
absolute background subtracted signal. Any runs of points over this theshold that are over a set length are registered as possible peak positions. This set length is given 
by 100.*((1./6)**Set Length) = Peak_Tolerance. The backround signal gradients are now recalculated ignoring any contributions from lines including points registered as
possible peak positions. 

These iterations are stopped when they reach Maximum_Iterations or when the list of possible peak positions converges.
"""

def Construct_Background(Gradient,Not_Allowed,Window,Signal_Length):
	"""
	Function that takes a list of gradients (Gradient), a list indicating whether points represent possible peak postions (Not_Allowed), the window size
	and the length of the signal and reconstructs the BG signal + a constant.
	"""

	#---Estimate gradient at each position----

	Average=[]
	while len(Average)<Signal_Length:
		Average.append([])

	for i in range(len(Gradient)):
		if Not_Allowed[i] is False and Not_Allowed[i+Window] is False:
			n=0
			while n<=Window:
				Average[n+i].append(Gradient[i])
				n+=1

	#--- Ensure every point has a gradient----

	if len(Average[0])==0:
		Average[0]=[0]
	for i in range(len(Average)):
		if len(Average[i])==0:
			Average[i]=Average[i-1]

	#---Integrate up output------

	Output=[0.]
	for i in Average:
		Output.append(Output[-1]+np.median(i))

	return np.array(Output[:-1])


def Run(Signal,Window=50,Maximum_Iterations=10,Peak_Tolerance=0.5):
	"""
	Main function, explained at the top of the page.
	"""

	#---Ensure Window fits contraints---

	Window=int(Window)
	if Window<2:
		Window=2

	#--Calcuate gradients-------

	Gradient=[]
	n=Window
	while n<len(Signal):
		Gradient.append(float(Signal[n]-Signal[n-Window])/Window)
		n+=1
	Not_Allowed=[]
	while len(Not_Allowed)<len(Signal):
		Not_Allowed.append(False)

	#----Initial estimate-----

	Background=Construct_Background(Gradient,Not_Allowed,Window,len(Signal))

	Clean=np.array(Signal)-Background
	Clean=Clean-np.median(Clean)

	#---Calculate number of points over the noise threshold that correspond to a possible peak

	Point_Run=0
	while 100.*((1./6)**Point_Run)>Peak_Tolerance:
		Point_Run+=1

	#---Iterate background estimation, ignoring possible peak positions-----

	Iterate=True
	Iterations=0
	while Iterate is True and Iterations<Maximum_Iterations:
		Iterations+=1
		Possible_Peak_Regions=[]
		Current_Run=[]
		Threshold=np.median(np.abs(Clean))
		for i in range(len(Signal)):
			if Clean[i]>=Threshold:
				Current_Run.append(i)
			else:
				if len(Current_Run)>=Point_Run:
					Possible_Peak_Regions+=Current_Run
				Current_Run=[]
		if len(Current_Run)>=Point_Run:
			Possible_Peak_Regions+=Current_Run

		New_Not_Allowed=[]
		for i in range(len(Signal)):
			if i in Possible_Peak_Regions:
				New_Not_Allowed.append(True)
			else:
				New_Not_Allowed.append(False)

		if np.array_equal(Not_Allowed,New_Not_Allowed)==False:
			Not_Allowed=New_Not_Allowed
			Background=Construct_Background(Gradient,Not_Allowed,Window,len(Signal))
			Clean=np.array(Signal)-Background
			Clean=Clean-np.median(Clean)
		else:
			Iterate=False

	return Clean