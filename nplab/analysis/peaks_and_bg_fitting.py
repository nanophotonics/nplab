# -*- coding: utf-8 -*-
"""
Created on Mon Jul 15 11:50:45 2019

@author: Eoin Elliott -ee306

The fullfit class is the main thing here - sample use:
    from nplab.analysis.peaks_and_bg_fitting import fullfit
    ff = fullfit(spectrum, shifts) # initialise the object. The order key-word argument is the order of the background polynomial. 3 works well. above 9 is unstable.
    ff.Run() # this does the actual fitting.
    then the peaks are stored as 
    ff.peaks # 1d list of parameters: height, x-position, and width. Plot with ff.multi_L
    ff.peaks_stack has them in a 2d array so you can plot the peaks individually like so:
        for peak in ff.peaks_stack:
            plt.plot(ff.shifts, ff.L(ff.shifts, *peak))
    ff.bg gives the background as a 1d array.

The fitting works as follows: 
    Run(self,minwidth_fac=0.1,initial_fit=None, maxwidth = 7, regions = 20, noise_factor = 0.6, min_peak_overlap = 3, comparison_thresh = 0.1):   
        minwidth fac is the minimum fraction of the guessed peak width a fitted peak can have.
        initial_fit should be a 1d array of the  order+1 background VALUES (see below) and the peaks
        maxwidth is the maximum width a peak can have.
        regions works as in Iterative_Raman_Fitting
        noise_factor is the minimum height above the noise level a peak must have. It's not connected to anything physical however, just tune it to exclude/include lower S:N peaks
        min_peak_overlap is the minimum separation (in # of peak widths) a new peak must have from all existing peaks. Prevents multiple Lorentzians being fitted to the one peak.
        comparison_thresh  is the fractional difference allowed between fit optimisations for the peak to be considered fitted.
    
    If there's no intial fit then initial_bg_poly() takes a guess at what the background is. The signal is spectrum-bg
    Add_New_Peak() forcibly adds a peak to the signal as in Iterative_Raman_fitting.
    If the peak passes some filtering conditions (see Run() for more details) its added to the peaks.
    The peak heights are then somewhat manually assigned by getting the maximum of the signal around the peak centre.
    The background is optimised for these new peaks, and then the peaks are optimised.
    If this new peak improves the fit, it adds another peak, repeats.
    Else, if it doesn't improve the fit (a sign that the right # of peaks have been added) the number of regions is multiplied by 5 to try more possible places to add a peak.
    if the peak doesn't pass the initial filtering (again, a good sign) the rest of the function matches each peak with its nearest neighbour (hopefully itself)
    from before the latest round of optimisation. If none of the peaks have moved by comparison_thresh*sqrt(height and width added in quadrature)
    the fit is considered optimised, and the number of peak adding regions is increased by 5x. 
    
This script uses cm-1 for shifts. Using wavelengths is fine, but make sure and adjust the maxwidth parameter accordingly   

The time taken to fit increases non-linearly with spectrum size/length, so cutting out irrelevant regions such as the notch is important, 
as is fitting the stokes and anti-stokes spectra separately. 
"""
import numpy as np
from scipy.optimize import minimize
import matplotlib.pyplot as plt
import scipy.interpolate as scint
import scipy.ndimage.filters as ndimf
import pywt
import misc as ms # these are some convenience functions I've written

def Grad(Array):
	"""
	Returns something prop to the grad of 1D array Array. Does central difference method with mirroring.
	"""
	A=np.array(Array.tolist()+[Array[-1],Array[-2]])
	B=np.array([Array[1],Array[0]]+Array.tolist())
	return (A-B)[1:-1]


class fullfit:
    def __init__(self, spec, shifts, order = 3):
        self.spec = spec
        self.shifts = shifts
        self.order = order
        self.peaks = []
        self.peaks_stack = [[]]
        self.bg_bounds = [(0, max(self.spec))]
        i=0
        while i<order: 
            self.bg_bounds.append(self.bg_bounds[0])
            i+=1
    def L(self,x,H,C,W): # height centre width
    	"""
    	Defines a lorentzian
    	"""
    	return H/(1.+(((x-C)/W)**2))

    def multi_L(self,x,*Params):
    	"""
    	Defines a sum of Lorentzians. Params goes Height1,Centre1, Width1,Height2.....
    	"""
    	Output=0
    	n=0
        while n<len(Params):
    		Output+=self.L(x,*Params[n:n+3])
    		n+=3
    	return Output
    
    def plot_result(self):
        '''
        plots the spectrum and the individual peaks
        note that areas where the peaks overlap aren't added together, so fits may appear off.
        '''
        plt.figure()
        plt.plot(self.shifts, self.spec)
        plt.plot(self.shifts,self.bg)
        peaks_stack = []
        n = 0
        while n < len(self.peaks):
                peaks_stack.append(self.peaks[n:n+3])
                n+=3
        for peak in peaks_stack:
            
            plt.plot(self.shifts,self.bg+self.L(self.shifts,*peak))
                
                
    def Add_New_Peak(self):
        '''
        lifted from Iterative_Raman_Fitting
        '''
    	#-----Calc. size of x_axis regions-------
    	Sections=(np.max(self.shifts)-np.min(self.shifts))/self.regions
    	Start=np.min(self.shifts)
    
    	Results=[]
    	Loss_Results=[]
    
    	#-------What does the curve look like with the current peaks?-------
        if len(self.peaks)==0:
    		Current=np.array(self.shifts)*0
    	else:
            Current=self.multi_L(self.shifts,*self.peaks)
    
    	#-------Set up Loss function--------	
    	def Loss(Vector):
    		return np.sum(np.abs(Current+self.L(self.shifts,*Vector)-self.signal))#*self.multi_L(self.shifts,*self.peaks))# if this overlaps with another lorentzian it's biased against it
    	
    	#-----Minimise loss in each region--------- 
    
    	for i in range(int(self.regions)):
    		Bounds=[(0,np.inf),(i*Sections+Start,(i+1)*Sections+Start),(0,self.maxwidth)]
    		Centre=(i+np.random.rand())*Sections+Start
    		Height=self.signal[np.argmin(np.abs(self.shifts-Centre))]-np.min(self.signal)
    		Vector=[Height,Centre,self.width]
    
    		Opt=minimize(Loss,Vector,bounds=Bounds).x
    
    		Results.append(Opt)
    		Loss_Results.append(Loss(Opt))
    
    	#------Select most effective peak postion
        #print Results[np.argmin(Loss_Results)]
    	return Results[np.argmin(Loss_Results)] # return one peak
        
    def Wavelet_Estimate_Width(self,Smooth_Loss_Function=2):
    	#Uses the CWT to estimate the typical peak FWHM in the signal
    	#First, intepolates the signal onto a linear x_scale with the smallest spacing present in the signal
    	#Completes CWT and sums over the position coordinate, leaving scale
    	#Does minor smooth, and takes scale at maximum as FWHM
      	Int=scint.splrep(self.shifts,self.spec)
    	Step=np.min(np.abs(np.diff(self.shifts)))        
    	New=scint.splev(np.arange(self.shifts[0],self.shifts[-1],Step),Int)                         
    	Scales=np.arange(1,np.ceil(self.maxwidth/Step),1)        
    	Score=np.diff(np.sum(pywt.cwt(New,Scales,'gaus1')[0],axis=1))        
    	Score=ndimf.gaussian_filter(Score,Smooth_Loss_Function)        
    	Scale=Scales[np.argmax(Score)]*Step
        return Scale

    def initial_bg_poly(self):
        '''
        takes an inital guess at the background VALUES (see optimize bg) by taking order+1 evenly spaced segments
        of the spectum, and taking the minimum as the background value
        '''

        self.bg_vals = []
        self.bg_indices = []
        for section in range(self.order+1):
            seg_indices = np.array([section,section+1])*len(self.spec)/(self.order+1)
            seg = self.spec[seg_indices[0]:seg_indices[1]]
            self.bg_vals.append(np.min(seg))
            self.bg_indices.append(np.argmin(seg)+section*len(self.spec)/(self.order+1))
        self.bg_p = np.polyfit(self.shifts[self.bg_indices], self.bg_vals, self.order)
        self.bg = np.polyval(self.bg_p, self.shifts)
        self.signal = self.spec - self.bg

    def bg_loss(self,bg_vals):
        '''
        evaluates the fit of the background to spectrum-peaks
        '''
        self.bg_p = np.polyfit(self.shifts[self.bg_indices], bg_vals, self.order)
        fit = np.polyval(self.bg_p, self.shifts)
        obj = np.sum(np.square(self.spec - self.multi_L(self.shifts,*self.peaks) - fit))
        return obj
    
    def optimize_bg(self):# takes bg_vals
        '''
        it's important to note that the parameter optimised isn't the polynomial coefficients bg_p , 
        but order+1 points on the spectrum-peaks curve (bg_vals) at positions bg_indices.
        This is because it's easy to put the bounds of the minimum and maximum of the spectrum on these to improve optimisation time. (maybe)
        '''
        self.bg_vals = minimize(self.bg_loss, self.bg_vals, bounds = self.bg_bounds).x       
        self.bg_p = np.polyfit(self.shifts[self.bg_indices], self.bg_vals, self.order)
        self.bg = np.polyval(self.bg_p, self.shifts)
        self.signal = self.spec - self.bg
    def peaks_to_matrix(self, peak_array):
        '''
        converts a 1d peak_array into a 2d one
        '''
        peaks_stack = []
        n =0
        while n < len(peak_array):
           peaks_stack.append(peak_array[n:n+3])
           n+=3
        return peaks_stack
        
    def peak_loss(self,peaks):
        '''
        evalutes difference between the fitted peaks and the signal (spectrum - background)
        '''
        fit = self.multi_L(self.shifts, *peaks)
        obj = np.sum(np.square(self.signal - fit))
        return obj
            
        
    def optimize_peaks(self):
        peak_bounds = []
        n=0
        height_bound = (0,max(self.spec))
        pos_bound = (np.min(self.shifts),np.max(self.shifts))
        width_bound = (0,self.maxwidth)
        while n<len(self.peaks):
           
            peak_bounds+=[height_bound, pos_bound, width_bound]  # height, position, width
            n+=3
        self.peaks = minimize(self.peak_loss, self.peaks, bounds = peak_bounds).x
        self.peaks_stack = self.peaks_to_matrix(self.peaks)

    def optimize_heights(self):
        '''
        crudely gets the maximum of the signal within the peak widht as an estimate for the peak height
        '''
        for index, peak in enumerate(self.peaks_stack):
            self.peaks_stack[index][0] = max(ms.truncate(self.signal, self.shifts, peak[1]-peak[2], peak[1]+peak[2])[0])
        self.peaks = []
        for peak in self.peaks_stack:#flattens the stack
            for parameter in peak:
                self.peaks.append(parameter)
    def loss_function(self, loss_vector):
        '''
        evaluates the overall (bg+peaks) fit to the spectrum
        '''
        self.bg_p = np.polyfit(self.shifts[self.bg_indices], loss_vector[0:self.order+1], self.order)
        self.bg = np.polyval(self.bg_p, self.shifts)
        fit = self.bg + self.multi_L(self.shifts,*loss_vector[self.order+1:])
        obj = np.sum(np.square(self.spec - fit))
        return obj
    def Run(self,initial_fit=None, minwidth_fac=0.1, maxwidth = 7, regions = 20, noise_factor = 0.6, min_peak_spacing = 8, comparison_thresh = 0.1, verbose = False):    
    	self.maxwidth = maxwidth
        self.width=self.Wavelet_Estimate_Width()*0.5
        self.regions = regions
        if self.regions>len(self.spec):	self.regions = len(self.spec)/2
    	minwidth=self.width*minwidth_fac
    	self.noise_threshold = noise_factor*np.std(Grad(spec))
        if initial_fit is not None:
            self.bg_vals = initial_fit[0:self.order+1]
            self.peaks = initial_fit[self.order+1:]
        else:
            self.initial_bg_poly() # gives initial bg_vals, and bg_indices
        
        #self.optimize_bg()
        while self.regions <= len(self.spec):
            if verbose == True: print 'Region fraction: ', np.around(self.regions/float(len(self.spec)), decimals = 2)
            
            loss_vector = np.append(self.bg_vals,self.peaks)
            existing_loss_score = self.loss_function(loss_vector)
           

            peak_added = False
            peak_candidate = self.Add_New_Peak()
            if peak_candidate[0]>self.noise_threshold and peak_candidate[2]>minwidth: #has a height, and is above minimum width - maximum width is filtered already
                if len(self.peaks)!=0:
                    dump, peak, residual = ms.find_closest(peak_candidate[1],np.transpose(self.peaks_stack)[1])
                    if residual>min_peak_spacing*self.peaks_stack[peak][2]:
                        self.peaks = np.append(self.peaks,peak_candidate)
                        self.peaks_stack = self.peaks_to_matrix(self.peaks)
                        peak_added = True
                else:
                    self.peaks = np.append(self.peaks,peak_candidate)
                    self.peaks_stack = self.peaks_to_matrix(self.peaks)
                    peak_added = True
            else:
                if verbose == True: print 'peak rejected'
            
            if verbose == True: print '# of peaks:', len(self.peaks)/3
            self.optimize_bg()
            self.optimize_heights()
            self.optimize_peaks()
            vector = np.append(self.bg_vals, self.peaks)
            new_loss_score = self.loss_function(vector)
    		
            #---Check to increase region by x5
            if existing_loss_score is not None:
                if new_loss_score >= existing_loss_score: #Has loss gone up?
                    if peak_added == True:
                        self.peaks = self.peaks[0:-3]
                        self.peaks_stack = self.peaks_stack[0:-1]
                    self.regions*=3
                elif peak_added == False: #Otherwise, same number of peaks?
               
                    Old = self.peaks_to_matrix(loss_vector[self.order+1:].tolist())
                    New = self.peaks_stack
                    New_trnsp = np.transpose(New)
                    residual = []
                    for old_peak in Old:
                            new_peak = ms.find_closest(old_peak[1], New_trnsp[1])[1]# returns index of the new peak which matches it
                            old_height = old_peak[0]
                            old_height
                            old_pos = old_peak[1]/self.width
                            
                            new_height = New[new_peak][0]/old_height
                            new_pos = New[new_peak][1]/self.width
                            residual.append(np.linalg.norm(np.array([1,old_pos])-np.array([new_height,new_pos])))
                    comparison = residual>comparison_thresh
                    if type(comparison) == bool:
                        if comparison ==False:
                            self.regions*=3
                    else:
                        if any(comparison) == False: #if none of the peaks have changed by more than comparison_thresh fraction
                            self.regions*=3

            	
            
                    
                    

    



if __name__ =='__main__':
    import time
    import h5py
    import conversions as cnv
    import os
    os.chdir(r'R:\ee306\Experimental data\2019.09.06 Lab 5 two temperature with full calibration')
    #File = h5py.File('Wavenumbered_plots.h5', mode = 'r')
   
    start = time.time()
    File = h5py.File(ms.findH5File(os.getcwd()), mode = 'r')
    spec = File['BPT_1']['Power_Series'][-1]
    shifts = -cnv.wavelength_to_cm(File['BPT_1']['Power_Series'].attrs['wavelengths'], centre_wl = 785)
    notch = 200
    S_portion, S_shifts = ms.truncate(spec,shifts, notch, 850)
    #S_portion, S_shifts = an.truncate(spec,shifts, 796, 850)
    ff = fullfit(S_portion, S_shifts, order = 3)
    ff.Run(min_peak_spacing = 4, noise_factor = 0.01, verbose = True)
    ff.plot_result()
    end = time.time()
    print 'that took '+ str(np.round(end-start,decimals = 0))+ ' seconds'