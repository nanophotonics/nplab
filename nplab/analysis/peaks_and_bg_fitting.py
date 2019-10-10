# -*- coding: utf-8 -*-
"""
Created on Mon Jul 15 11:50:45 2019

@author: Eoin Elliott -ee306

The fullfit class is the main thing here - sample use:
    from nplab.analysis.peaks_and_bg_fitting import fullfit
    ff = fullfit(self, spec, shifts, order = 3, transmission = None, use_exponential = False) # initialise the object. The order key-word argument is the order of the background polynomial. 3 works well. above 9 is unstable.
    transmission is the instrument response function of the detector. It's necessary to include it here rather than in the raw data as most of the background is electronic, so dividing this by the IRF introduces unphysical features.
    This way, the IRF is only applied to the background-subtracted signal 
    use_exponential determines whether or not to use an exponential fit rather than a polynomial - useful for extracting antistokes temperatures
    ff.Run() # this does the actual fitting.
    then the peaks are stored as 
    ff.peaks # 1d list of parameters: height, x-position, and width. Plot with ff.multi_L
    ff.peaks_stack has them in a 2d array so you can plot the peaks individually like so:
        for peak in ff.peaks_stack:
            plt.plot(ff.shifts, ff.L(ff.shifts, *peak))
    ff.bg gives the background as a 1d array.
    ff.signal gives the background-subtracted spectrum, divided by the transmission

The fitting works as follows: 
    Run(self,initial_fit=None, add_peaks = True, minwidth = 2, maxwidth = 10, regions = 20, noise_factor = 0.6, min_peak_spacing = 7, comparison_thresh = 0.1, verbose = False):   
        initial fit should be a 1D array of height, centre widths.
        if add_peaks is True, then the code will try to add additional peaks. If you're happy with the peaks already, set = False and it will just optimize a background and the peaks
        minwidth  is the minimum  width a fitted peak can have.
        maxwidth is the maximum width a peak can have.
        regions works as in Iterative_Raman_Fitting
        noise_factor is the minimum height above the noise level a peak must have. It's not connected to anything physical however, just tune it to exclude/include lower S:N peaks
        min_peak_spacing is the minimum separation (in # of peak widths) a new peak must have from all existing peaks. Prevents multiple Lorentzians being fitted to the one peak.
        comparison_thresh  is the fractional difference allowed between fit optimisations for the peak to be considered fitted.
    
    initial_bg_poly() takes a guess at what the background is. The signal is (spectrum-bg)/transmission
    
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
    
This script uses cm-1 for shifts. Using wavelengths is fine, but make sure and adjust the maxwidth, minwidth parameters accordingly   

the width parameter is not the FWHM, for computational simplicity, but is proportional.

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

def truncate(counts, wavelengths, lower_cutoff, upper_cutoff, return_indices_only = False):
    '''
    truncates a spectrum between upper and lower bounds. returns counts, wavelenghts pair.
    works with any x-axis (cm-1), not just wavelengths
    '''
    l = 0
    for index, wl in enumerate(wavelengths):
        if wl>=lower_cutoff:
            
            l = index
            break
        
    u = False
    for index, wl in enumerate(wavelengths[l:]):
        if wl>= upper_cutoff:
            u=index+l
            break
    if return_indices_only == False:
        if u == False:
            return counts[l:], wavelengths[l:]
        else:
            return counts[l:u], wavelengths[l:u]
    else:
        return l,u
def find_closest(value_to_match, array):
    '''Taking an input value and array, it searches for the value and index in the array which is closest to the input value '''
    residual = []
    for value in array:
        residual.append(np.absolute(value-value_to_match))


def Grad(Array):
	"""
	Returns something prop to the grad of 1D array Array. Does central difference method with mirroring.
	"""
	A=np.array(Array.tolist()+[Array[-1],Array[-2]])
	B=np.array([Array[1],Array[0]]+Array.tolist())
	return (A-B)[1:-1]
def cm_to_omega(cm):
    return 2*np.pi*constants.c*100.*cm

class fullfit:
    def __init__(self, spec, shifts, order = 3, transmission = None, use_exponential = False):
        
        self.spec = spec
        self.shifts = shifts
        self.order = order
        self.peaks = []
        self.peaks_stack = [[]]
        
        self.transmission = np.ones(len(spec))
        if transmission is not None: self.transmission*=transmission
        
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
        omega = -cm_to_omega(x)
        return (A*(np.exp((constants.hbar/constants.k)*omega/T) -1)**-1)*interp(self.shifts, self.transmission)(x) +bg 
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
            try: Height= max(truncate(self.signal, self.shifts, i*sectionsize+Start,(i+1)*sectionsize+Start)[0])-min(self.signal)
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
                    dump, peak, residual = find_closest(peak_candidate[1],np.transpose(self.peaks_stack)[1])
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
        takes an inital guess at the background VALUES (see optimize bg) by taking order+3 evenly spaced segments
        of the spectum, and taking the minimum as the background value
        '''
        if self.use_exponential == False:
            self.bg_vals = []
            self.bg_indices = []
            
            for section in range(self.order+3):
                seg_indices = np.array([section,section+1])*len(self.spec)/(self.order+3)
                seg = self.spec[seg_indices[0]:seg_indices[1]]
                bg_index = np.argmin(seg)+section*len(self.spec)/(self.order+3)
                self.bg_indices.append(bg_index)
                self.bg_vals.append(self.spec[bg_index])
                for extra in np.arange(3)+1:
                    try:
                        self.bg_vals.append(self.spec[bg_index+extra])
                        self.bg_indices.append(bg_index+extra)
                    except:
                        dump = 1
                    try:
                        self.bg_vals.append(self.spec[bg_index-extra])
                        self.bg_indices.append(bg_index-extra)
                        
                    except:
                        dump = 1
            self.bg_bound = (min(self.spec), max(self.spec))
            self.bg_bounds = []
            while len(self.bg_bounds)<len(self.bg_vals):
                self.bg_bounds.append(self.bg_bound)
            self.bg_p = np.polyfit(self.shifts[self.bg_indices], self.bg_vals, self.order)
            self.bg = np.polyval(self.bg_p, self.shifts)
            self.signal = ((np.array(self.spec - self.bg))/self.transmission).tolist()
        else:
            self.bg_vals = []
            self.bg_indices = []
            for section in range(3):  # A, T, bg
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
        but the points taken on the spectrum-peaks curve (bg_vals) at positions bg_indices, decided by initial_bg_poly().
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
        '''
        optimizes the height, centres and widths of all peaks
        '''
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
        '''
        optimizes the centres(positions) and widths of the peakss for a given heights.
        '''
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
            self.peaks_stack[index][0] = max(truncate(self.signal, self.shifts, peak[1]-peak[2], peak[1]+peak[2])[0])
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
    
    def Run(self,initial_fit=None, add_peaks = True, minwidth = 4, maxwidth = 20, regions = 20, noise_factor = 0.6, min_peak_spacing = 10, comparison_thresh = 0.1, verbose = False):    
    	'''
        described at the top
        '''
        self.maxwidth = maxwidth/2.
        self.min_peak_spacing = min_peak_spacing/2.
        self.width=4*self.Wavelet_Estimate_Width()
        self.regions = regions
        if self.regions>len(self.spec):	self.regions = len(self.spec)/2 
    	self.minwidth=minwidth/2.
    	self.noise_threshold = noise_factor*np.std(Grad(self.spec))
        self.initial_bg_poly()
        if initial_fit is not None:
            self.peaks = initial_fit
            self.regions = len(self.spec)/2.
            if add_peaks == False: self.regions*=4
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
                try:
                    self.optimize_heights()
                except:
                    dump = 1
                self.optimize_centre_and_width()
                self.optimize_peaks()
            
            elif self.peak_added == False:  #Otherwise, same number of peaks?
                self.optimize_bg()
                try:
                    self.optimize_heights() # fails if no peaks
                except:
                    dump = 1
                self.optimize_centre_and_width()
                self.optimize_peaks()
                self.optimize_bg()
                New = self.peaks_stack
                New_trnsp = np.transpose(New)
                residual = []
                for old_peak in Old:
                        new_peak = find_closest(old_peak[1], New_trnsp[1])[1]# returns index of the new peak which matches it
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
        
        self.optimize_peaks()
        
               
            	

