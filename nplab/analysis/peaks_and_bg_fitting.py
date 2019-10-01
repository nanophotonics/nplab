# -*- coding: utf-8 -*-
"""
Created on Mon Jul 15 11:50:45 2019

@author: Eoin Elliott -ee306

The fullfit class is the main thing here - sample use:
    from nplab.analysis.peaks_and_bg_fitting import fullfit
    ff = fullfit(spectrum, shifts) # initialise the object. The order key-word argument is the order of the background polynomial. 3 works well. above 9 is unstable.
    use_exponential determines whether or not to use an exponential fit rather than a polynomial
    ff.Run() # this does the actual fitting.
    then the peaks are stored as 
    ff.peaks # 1d list of parameters: height, x-position, and width. Plot with ff.multi_L
    ff.peaks_stack has them in a 2d array so you can plot the peaks individually like so:
        for peak in ff.peaks_stack:
            plt.plot(ff.shifts, ff.L(ff.shifts, *peak))
    ff.bg gives the background as a 1d array.

The fitting works as follows: 
    Run(self,minwidth_fac=0.1,initial_fit=None, maxwidth = 7, regions = 20, noise_factor = 0.6, min_peak_spacing = 8, comparison_thresh = 0.1):   
        minwidth fac is the minimum fraction of the guessed peak width a fitted peak can have.
        initial_fit should be a 1d array of the  order+1 background VALUES (see below) and the peaks
        maxwidth is the maximum width a peak can have.
        regions works as in Iterative_Raman_Fitting
        noise_factor is the minimum height above the noise level a peak must have. It's not connected to anything physical however, just tune it to exclude/include lower S:N peaks
        min_peak_spacing is the minimum separation (in # of peak widths) a new peak must have from all existing peaks. Prevents multiple Lorentzians being fitted to the one peak.
        comparison_thresh  is the fractional difference allowed between fit optimisations for the peak to be considered fitted.
    
    If there's no intial fit then initial_bg_poly() takes a guess at what the background is. The signal is spectrum-bg
    
    Add_New_Peak() forcibly adds a peak to the signal as in Iterative_Raman_fitting.
        The only difference is that there are bounds on the peak parameters, and if the peak is within min_peak_separation*peak width of 
    any other peak, it picks the next best peak, and so on until the best 1/3 of the peaks have been tested. Else, it doesn't add a new peak at all.
    
    The peak heights are then somewhat manually assigned by getting the maximum of the signal around the peak centre.
    The widths and centres of the peaks are then optimised for these heights.
    optionally, you can include the commented out self.optimize_peaks() here to optimise all the peak parameters together but I leave this to the end.
    
    If this new peak improves the fit, it adds another peak, repeats.
    Else, if it doesn't improve the fit (a sign that the right # of peaks have been added) the number of regions is multiplied by 5 to try more possible places to add a peak.
    It also now optimises the background, as doing so before will make it cut through the un-fitted peaks
    
    If no new peak has been added (again, a good sign) the rest of the function matches each peak with its nearest neighbour (hopefully itself)
    from before the latest round of optimisation. If none of the peaks have moved by comparison_thresh*sqrt(height and width added in quadrature)
    the fit is considered optimised, and the number of peak adding regions is increased by 5x. 
    
    one last optional round of optimisation is included at the very end
    
This script uses cm-1 for shifts. Using wavelengths is fine, but make sure and adjust the maxwidth parameter accordingly   

The time taken to fit increases non-linearly with spectrum size/length, so cutting out irrelevant regions such as the notch is important, 
as is fitting the stokes and anti-stokes spectra separately. 
"""
import numpy as np
from scipy.optimize import minimize
from scipy.optimize import curve_fit as curve_fit
import matplotlib.pyplot as plt
import scipy.interpolate as scint
import scipy.ndimage.filters as ndimf
from scipy import constants as constants
from scipy.interpolate import interp1d as interp
import pywt
import misc as ms # these are some convenience functions I've written
import conversions as cnv


def Grad(Array):
	"""
	Returns something prop to the grad of 1D array Array. Does central difference method with mirroring.
	"""
	A=np.array(Array.tolist()+[Array[-1],Array[-2]])
	B=np.array([Array[1],Array[0]]+Array.tolist())
	return (A-B)[1:-1]


class fullfit:
    def __init__(self, spec, shifts, order = 3, transmission = None, use_exponential = False):
        
        self.spec = spec
        self.shifts = shifts
        self.order = order
        self.peaks = []
        self.peaks_stack = [[]]
        self.bg_bounds = [(0, max(self.spec))]
        self.transmission = np.ones(len(spec))
        if transmission is not None: self.transmission*=transmission
        i=0
        while i<order: 
            self.bg_bounds.append(self.bg_bounds[0])
            i+=1
        
        self.use_exponential = use_exponential
        if use_exponential == True: self.exp_bounds = ([0, 0, 0,],[np.inf,np.inf, max(self.spec)])
    
    def L(self,x,H,C,W): # height centre width
    	"""
    	Defines a lorentzian
    	"""
    	return H/(1.+(((x-C)/W)**2))

    def multi_L(self,x,*Params):
    	"""
    	Defines a sum of Lorentzians. Params goes Height1,Centre1, Width1,Height2.....
    	"""
    	Output=np.zeros(len(x))
    	n=0
        while n<len(Params):
    		Output+=self.L(x,*Params[n:n+3])
    		n+=3
    	return Output
    
    def exponential(self, x, A, T, bg):
        '''
        uses the transmission for the exponential term, not the constant background.
        '''
        omega = -cnv.cm_to_omega(x)
        return (A*(np.exp((constants.hbar/constants.k)*omega/T) -1)**-1)*interp(self.transmission, self.shifts)(x) +bg 
    def plot_result(self):
        '''
        plots the spectrum and the individual peaks
        note that areas where the peaks overlap aren't added together, so fits may appear off.
        '''
        plt.figure()
        plt.plot(self.shifts, self.spec)
        plt.plot(self.shifts,self.bg)
        for peak in self.peaks_stack:
            
            plt.plot(self.shifts,self.bg+self.L(self.shifts,*peak)*self.transmission)
                
                
    def Add_New_Peak(self):
        '''
        lifted from Iterative_Raman_Fitting
        '''
    	#-----Calc. size of x_axis regions-------
    	sectionsize=(np.max(self.shifts)-np.min(self.shifts))/float(self.regions)
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
            Bounds=[(0,np.inf),(i*sectionsize+Start,(i+1)*sectionsize+Start),(self.minwidth,self.maxwidth)]
            Centre=(i+np.random.rand())*sectionsize+Start
            try: Height= max(ms.truncate(self.signal, self.shifts, i*sectionsize+Start,(i+1)*sectionsize+Start)[0])-min(self.signal)
            except: Height = self.noise_threshold
            Vector=[Height,Centre,self.width]
    
            Opt=minimize(Loss,Vector,bounds=Bounds).x
    
            Results.append(Opt)
            Loss_Results.append(Loss(Opt))
        
        sorted_indices = np.argsort(Loss_Results)
        
        
        self.peak_added = False
        i=-1
        while self.peak_added == False and i<(self.regions/100): #self.region/5s
            i+=1
            peak_candidate = Results[sorted_indices[i]]
            if len(self.peaks)!=0:
                if peak_candidate[0]>self.noise_threshold:# and peak_candidate[2]>self.minwidth: #has a height, minimum width - maximum width is filtered already
                    dump, peak, residual = ms.find_closest(peak_candidate[1],np.transpose(self.peaks_stack)[1])
                    if residual>self.min_peak_spacing*self.peaks_stack[peak][2]:
                        self.peaks = np.append(self.peaks,peak_candidate)
                        self.peaks_stack = self.peaks_to_matrix(self.peaks)
                        self.peak_added = True
                    
                        
            else:
                self.peaks = np.append(self.peaks,peak_candidate)
                self.peaks_stack = self.peaks_to_matrix(self.peaks)
                self.peak_added = True
        

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
        if self.use_exponential == False:
            self.bg_vals = []
            self.bg_indices = []
            for section in range(self.order+1):
                seg_indices = np.array([section,section+1])*len(self.spec)/(self.order+1)
                seg = self.spec[seg_indices[0]:seg_indices[1]]
                self.bg_vals.append(np.min(seg))
                self.bg_indices.append(np.argmin(seg)+section*len(self.spec)/(self.order+1))
            self.bg_p = np.polyfit(self.shifts[self.bg_indices], self.bg_vals, self.order)
            self.bg = np.polyval(self.bg_p, self.shifts)
            self.signal = ((np.array(self.spec - self.bg))/self.transmission).tolist()
        else:
            self.bg_vals = []
            self.bg_indices = []
            for section in range(5):  # A, T, bg
                    seg_indices = np.array([section,section+1])*len(self.spec)/(5)
                    seg = self.spec[seg_indices[0]:seg_indices[1]]
                    self.bg_vals.append(np.min(seg))
                    self.bg_indices.append(np.argmin(seg)+section*len(self.spec)/(5))
            #ipdb.set_trace()
            #self.bg_p = curve_fit(self.exponential, self.shifts[self.bg_indices], self.bg_vals)[0] # p0 = [self.spec[-1]*3, 300, min(self.spec)]
            self.bg_p = curve_fit(self.exponential, self.shifts[self.bg_indices], self.bg_vals, p0 = [0.5*max(self.spec), 300, min(self.spec)], maxfev = 10000)[0]#, bounds = self.exp_bounds)[0]
            self.bg = self.exponential(self.shifts, *self.bg_p)
            self.signal = ((np.array(self.spec - self.bg))/self.transmission).tolist()
    
    
    def bg_loss(self,bg_vals):
        '''
        evaluates the fit of the background to spectrum-peaks
        '''
        self.bg_p = np.polyfit(self.shifts[self.bg_indices], bg_vals, self.order)
        fit = np.polyval(self.bg_p, self.shifts)
        obj = np.sum(np.square(self.spec - self.peaks_evaluated - fit))
        return obj

    def optimize_bg(self):# takes bg_vals
        '''
        it's important to note that the parameter optimised isn't the polynomial coefficients bg_p , 
        but order+1 points on the spectrum-peaks curve (bg_vals) at positions bg_indices.
        This is because it's easy to put the bounds of the minimum and maximum of the spectrum on these to improve optimisation time. (maybe)
        '''
        if self.use_exponential == False:    
            self.peaks_evaluated = self.multi_L(self.shifts, *self.peaks)*self.transmission
            self.bg_vals = minimize(self.bg_loss, self.bg_vals, bounds = self.bg_bounds).x       
            self.bg_p = np.polyfit(self.shifts[self.bg_indices], self.bg_vals, self.order)
            self.bg = np.polyval(self.bg_p, self.shifts)
            self.signal =(np.array(self.spec - self.bg)/self.transmission).tolist()
        else:
            self.bg_p = curve_fit(self.exponential, self.shifts, self.spec - self.multi_L(self.shifts, *self.peaks)*self.transmission, p0 = self.bg_p, bounds = self.exp_bounds, maxfev = 10000)[0]
            self.bg = self.exponential(self.shifts, *self.bg_p)

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
        height_bound = (self.noise_threshold,max(self.signal))
        pos_bound = (np.min(self.shifts),np.max(self.shifts))
        width_bound = (self.minwidth,self.maxwidth)
        while n<len(self.peaks):
           
            peak_bounds+=[height_bound, pos_bound, width_bound]  # height, position, width
            n+=3

        self.peaks = minimize(self.peak_loss, self.peaks, bounds = peak_bounds).x
        self.peaks_stack = self.peaks_to_matrix(self.peaks)


    
    def optimize_centre_and_width(self):
        heights = np.transpose(self.peaks_stack)[0]
        centres_and_widths_stack = np.transpose(self.peaks_stack)[1:]
        centres_and_widths = []
        for peak in np.transpose(centres_and_widths_stack).tolist():#flattens the stack
            centres_and_widths.extend(peak)
        width_bound = (self.minwidth,self.maxwidth)
        centre_and_width_bounds = []

        for (centre, width) in zip(centres_and_widths_stack[0], centres_and_widths_stack[1]): #
            centre_and_width_bounds+=[(centre-width, centre+width), width_bound]  # height, position, width
        
        def multi_L_centres_and_widths(x,centres_and_widths):
            """
        	Defines a sum of Lorentzians. Params goes Height1,Centre1, Width1,Height2.....
        	"""
            n = 0
            params = []
            while n<len(centres_and_widths):
                params.append(heights[n/2])
                params.extend(centres_and_widths[n:n+2])
                n+=2
            Output=0
            n=0
            while n<len(params):
        		Output+=self.L(x,*params[n:n+3])
        		n+=3
            return Output
        def loss_centres_and_widths(centres_and_widths):
            fit = multi_L_centres_and_widths(self.shifts,centres_and_widths)
            obj = np.sum(np.square(self.signal - fit))
            return obj
        centres_and_widths = minimize(loss_centres_and_widths,centres_and_widths, bounds = centre_and_width_bounds).x
        #except: ipdb.set_trace()
        n = 0
        self.peaks = []
        while n<len(centres_and_widths):
            self.peaks.extend([heights[n/2], centres_and_widths[n],centres_and_widths[n+1] ])
            n+=2   
        self.peaks_stack = self.peaks_to_matrix(self.peaks)
        
        
    def optimize_heights(self):
        '''
        crudely gets the maximum of the signal within the peak width as an estimate for the peak height
        '''
        for index, peak in enumerate(self.peaks_stack):
            self.peaks_stack[index][0] = max(ms.truncate(self.signal, self.shifts, peak[1]-peak[2], peak[1]+peak[2])[0])
        self.peaks = []
        for peak in self.peaks_stack:#flattens the stack
            for parameter in peak:
                self.peaks.append(parameter)
    
    def loss_function(self):
        '''
        evaluates the overall (bg+peaks) fit to the spectrum
        '''
        
        fit = self.bg + self.multi_L(self.shifts,*self.peaks)*self.transmission
        obj = np.sum(np.square(self.spec - fit))
        return obj
    
    def optimize_peaks_asymmetrically(self):
        
        def asymmetric_loss(alpha, beta):
            alphas = alpha*ms.truncate(np.ones(len(self.spec)), self.shifts, -np.inf, peak[1])
            betas = beta*ms.truncate(np.ones(len(self.spec)), self.shifts, peak[1], np.inf)
            exponent = np.append(alphas, betas)
            fit = np.power(self.L(*peak), exponent)
            obj = np.sum(np.square(self.signal - fit))
            return obj
        for peak in self.peaks_stack:
            minimize(asymmetric_loss, 1,1)
            
    
    def Run(self,initial_fit=None, minwidth = 2, maxwidth = 10, regions = 20, noise_factor = 0.6, min_peak_spacing = 7, comparison_thresh = 0.1, verbose = False):    
    	
        self.maxwidth = maxwidth
        self.min_peak_spacing = min_peak_spacing
        self.width=4*self.Wavelet_Estimate_Width()
        self.regions = regions
        if self.regions>len(self.spec):	self.regions = len(self.spec)/2 
    	self.minwidth=minwidth
    	self.noise_threshold = noise_factor*np.std(Grad(self.spec))
        self.initial_bg_poly()
        if initial_fit is not None:
            self.peaks = initial_fit
            self.regions = len(self.spec)/2
            self.peaks_stack = self.peaks_to_matrix(self.peaks)
            self.optimize_heights()
            self.optimize_centre_and_width()
            #self.optimize_peaks()
         # gives initial bg_vals, and bg_indices
        while self.regions <= len(self.spec):
            if verbose == True: print 'Region fraction: ', np.around(self.regions/float(len(self.spec)), decimals = 2)
            existing_loss_score = self.loss_function()
            Old = self.peaks_stack
            self.Add_New_Peak()
            if verbose == True: print '# of peaks:', len(self.peaks)/3
#            try:
#                self.optimize_heights()
#            except:
#                dump = 1
#            self.optimize_centre_and_width()
            #self.optimize_peaks()
            
            new_loss_score = self.loss_function()
    		
            #---Check to increase region by x5
            
            if new_loss_score >= existing_loss_score: #Has loss gone up?
                if self.peak_added == True:                        
                    self.peaks = self.peaks[0:-3]
                    self.peaks_stack = self.peaks_stack[0:-1]
                self.regions*=5
            
            elif self.peak_added == False:  #Otherwise, same number of peaks?
                self.optimize_bg()
                try:
                    self.optimize_heights()
                except:
                    dump = 1
                self.optimize_centre_and_width()
                self.optimize_peaks()
                #self.optimize_bg()
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
                        self.regions*=5
                else:
                    if any(comparison) == False: #if none of the peaks have changed by more than comparison_thresh fraction
                        self.regions*=5
            elif len(self.peaks)==0:
                self.regions*=5
            
        #---One last round of optimization for luck---#
        self.optimize_bg()
        try:
            self.optimize_heights()
            
        except:
            dump = 1
        
        self.optimize_centre_and_width()
        
       # self.optimize_peaks()
        
               
            	

if __name__ =='__main__':
    import time
    import h5py
    import os
    os.chdir(r'R:\ee306\Experimental data\2019.09.06 Lab 5 two temperature with full calibration')
    #File = h5py.File('Wavenumbered_plots.h5', mode = 'r')
   
    start = time.time()
    File = h5py.File(ms.findH5File(os.getcwd()), mode = 'r')
    spec = File['TPT_3']['Power_Series'][0]
    shifts = -cnv.wavelength_to_cm(File['BPT_1']['Power_Series'].attrs['wavelengths'], centre_wl = 785)
    notch = 170
    
    S_portion, S_shifts = ms.truncate(spec,shifts, notch, 850)
    AS_portion, AS_shifts = ms.truncate(spec,shifts, -np.inf, -notch)
    #S_portion, S_shifts = an.truncate(spec,shifts, 796, 850)
    transmission = np.ones(len(AS_portion))*0.4
    ff = fullfit(AS_portion, AS_shifts, use_exponential = True, transmission = transmission )
    kwargs = {'min_peak_spacing' : 4, 'noise_factor' : 0.5, 'maxwidth' : 15, 'minwidth' : 5}
    ff.Run(verbose = True, **kwargs)
    ff.plot_result()
    end = time.time()
    print 'that took '+ str(np.round(end-start,decimals = 0))+ ' seconds'