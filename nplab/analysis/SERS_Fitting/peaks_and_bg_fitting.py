# -*- coding: utf-8 -*-
"""
Created on Mon Jul 15 11:50:45 2019

@author: Eoin Elliott -ee306

The fullfit class is the main thing here - sample use:
    from nplab.analysis.peaks_and_bg_fitting import fullfit
>>>ff = fullfit( 
                 spec,
                 shifts, 
                 lineshape = 'L',
                 order = 7,
                 transmission = None,
                 bg_function = 'poly',
                 vary_const_bg = True)
    #   initialise the object.
        spec, shifts are the spectrum and their shifts
        lineshape can be 'L' (Lorentzian) or 'G' (Gaussian). Gaussians are less broad
        The 'order' key-word argument is the order of the background polynomial. 3-7 works well. 
        transmission is the instrument response function of the detector. It's necessary to include it here rather than in the raw data as most of the background is electronic, so dividing this by the IRF introduces unphysical features.
        This way, the IRF is only applied to the background-subtracted signal 
        bg function determines what function to use for the background, default is polynomial. Feel free to add your own functions here!
        set vary_const_bg to False if the spectrum is already (electronic) background subtracted and you're using an exponential fit
    
>>>ff.Run() # this does the actual fitting.
                then the peaks are stored as 
>>>ff.peaks # 1d list of parameters: height, x-position, and width. Plot with ff.multi_L(peaks)
>>>ff.peaks_stack has them in a 2d array so you can plot the peaks individually like so:
        for peak in ff.peaks_stack:
            plt.plot(ff.shifts, ff.L(ff.shifts, peak))
>>>ff.bg gives the background as a 1d array.
>>>ff.signal gives the background-subtracted spectrum, divided by the transmission
>>>ff.bg_p gives the polynomial coefficients, or in the case of exponential background Amplitude, Temperature and constant background

The fitting works as follows: 
    Run(self,
            initial_fit=None, 
            add_peaks = True, 
            allow_asymmetry = False,
            minwidth = 8, 
            maxwidth = 30, 
            regions = 20, 
            noise_factor = 0.01, 
            min_peak_spacing = 5, 
            comparison_thresh = 0.05, 
            verbose = False):  
        
        initial fit should be a 1D array of height, centre widths (or None).
        if add_peaks is True, then the code will try to add additional peaks. If you're happy with the peaks already, set = False and it will just optimize a background and the peaks
        allow_asymmetry, if true allows the peaks to become asymmetric as a final step. see optimize_asymm(self) for details
        minwidth  is the minimum  width a fitted peak can have.
        maxwidth is the maximum width a peak can have.
        regions works as in Iterative_Raman_Fitting - see add_new_peak for details
        noise_factor is the minimum height above the noise level a peak must have. It's not connected to anything physical however, just tune it to exclude/include lower S:N peaks
        min_peak_spacing is the minimum separation (in # of peak widths) a new peak must have from all existing peaks. Prevents multiple Lorentzians being fitted to the one peak.
        comparison_thresh  is the fractional difference allowed between fit optimisations for the peak to be considered fitted.
    
    initial_bg_poly() takes a guess at what the background is. The signal is (spectrum-bg)/transmission
    
    if initial_fit is included, the peak heights are then somewhat manually assigned by getting the maximum of the signal around the peak centre.
    The widths and centres of the peaks are then optimised for these heights.
    optionally, you can include the commented out self.optimize_peaks() here to optimise all the peak parameters together but I leave this to the end.
    
    add_new_peak() forcibly adds a peak to the signal similarly to in Iterative_Raman_fitting.
    
    
    
    If this new peak improves the fit, it adds another peak, repeats.
    
    Else, if it doesn't improve the fit (a sign that the right # of peaks have been added) the number of regions is multiplied by 5 to try more possible places to add a peak.
    It also now optimises the background with the peaks, as doing so before will make it cut through the un-fitted peaks
    
    If no new peak has been added (again, a good sign) the rest of the function matches each peak with its nearest neighbour (hopefully itself)
    from before the latest round of optimisation. If none of the peaks have moved by comparison_thresh*sqrt(height and width added in quadrature)
    the fit is considered optimised, and the number of peak adding regions is increased by 5x. 
    
    one last optional round of optimisation is included at the very end
    
This script uses cm-1 for shifts. Using wavelengths is fine, but make sure and adjust the maxwidth, minwidth parameters accordingly   

The time taken to fit increases a lot with spectrum size/length, so cutting out irrelevant regions such as the notch is important, 
as is fitting the stokes and anti-stokes spectra separately. 
"""
from __future__ import division
from __future__ import print_function
from builtins import zip
from builtins import range
from builtins import object
from past.utils import old_div
import numpy as np
from scipy.optimize import minimize
import matplotlib.pyplot as plt
import scipy.interpolate as scint
import scipy.ndimage.filters as ndimf
from scipy import constants as constants
from scipy.interpolate import interp1d as interp
from scipy.optimize import curve_fit
import pywt
from nplab.analysis import Auto_Gaussian_Smooth as sm
from scipy.ndimage.filters import gaussian_filter as sm2
from scipy.signal import argrelextrema



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
    if len(array) == 1:
        return array[0], 0, np.absolute(value_to_match - array[0])
    residual = []
    for value in array:
        residual.append(np.absolute(value-value_to_match))
        
    return array[np.argmin(residual)], np.argmin(residual), min(residual) # value, index, residual

def Grad(Array):
    """
    Returns something prop to the grad of 1D array Array. Does central difference method with mirroring.
    """
    
    A=np.array(list(Array)+[Array[-1],Array[-2]])
    B=np.array([Array[1],Array[0]]+Array.tolist())
    return (A-B)[1:-1]

def cm_to_omega(cm):
    '''
    converts cm^-1 to angular frequency
    '''
    return 2*np.pi*constants.c*100.*cm

def reshape(List, n):
    while len(List)>=n:
        yield List[:n]
        List = List[n:]

class fullfit(object):
    def __init__(self, 
                 spec,
                 shifts, 
                 lineshape = 'L',
                 order = 7,
                 transmission = None,
                 bg_function = 'poly',
                 vary_const_bg = True):
        
        self.spec = spec
        self.shifts = shifts
        self.order = order
        self.peaks = []
        self.peak_bounds = []
        self.asymm_peaks = None
        self.transmission = np.ones(len(spec))
        if transmission is not None: self.transmission*=transmission
        if lineshape == 'L':
            self.line = lambda H, C, W: self.L(self.shifts, H, C, W)
        if lineshape == 'G':
            self.line = lambda H, C, W: self.G(self.shifts, H, C, W)
        self.lineshape = lineshape
        
        self.bg_type = bg_function
        if bg_function == 'exponential':
            self.bg_function = self.exponential
        if bg_function == 'exponential2':
            self.bg_function = self.exponential2
        self.vary_const_bg = vary_const_bg
        if bg_function == 'exponential' or bg_function == 'exponential2':
            if vary_const_bg != True: self.bg_bounds = ([0, 0, 0,],[np.inf,np.inf, 1e-9])
            else: self.bg_bounds = ([0, 0, 0,],[np.inf,np.inf, np.inf])
        
    @staticmethod
    def L(x, H, C, W): # height centre width
        """
        Defines a lorentzian
        """
        return H/(1.+((x-C)/W)**2)
    @staticmethod
    def G(x, H, C, W ):
        '''
        A Gaussian
        '''
        return H*np.exp(-((x-C)/W)**2)
    
    def multi_line(self, parameters):
        """
        returns a sum of Lorenzians/Gaussians. 
        """
        axis = int(bool(len(parameters)))
        return np.sum(np.array([self.line(*peak) for peak in parameters]),axis=0)
    
    def exponential(self, A, T, bg):
        '''
        uses the transmission for the exponential term, not the constant background.
        '''
        omega = -cm_to_omega(self.shifts)
        return ((A*(np.exp((constants.hbar/constants.k)*omega/T) -1))**-1)*interp(self.shifts, self.transmission)(self.shifts) +bg
    def exponential2(self, A, T, bg):
        '''
        uses the a more conplicated exponential 
        '''
        omega = -cm_to_omega(self.shifts)
        return A*(((np.exp((constants.hbar/constants.k)*omega/T) -1)**-1)+(np.exp((constants.hbar/constants.k)*omega/298.) -1)**-1)*interp(self.shifts, self.transmission)(self.shifts) +bg
    
    def exponential_loss(self, bg_p):
        '''
        evaluates fit of exponential to spectrum-signal
        '''
        residual = self.bg_function(self.shifts, *bg_p) - self.bg
        above = residual[residual>0]
        below = residual[residual<0]
        obj = np.sum(np.absolute(above))+np.sum(np.array(below)**2)
        return obj
    
    def plot_result(self):
        '''
        plots the spectrum and the individual peaks, and their sums
        
        '''
        plt.figure()
        plt.plot(self.shifts, self.spec)
        plt.plot(self.shifts,self.bg)
        for peak in self.peaks:
            plt.plot(self.shifts,self.bg+self.line(*peak)*self.transmission)
        plt.plot(self.shifts, self.bg+ self.multi_line(self.peaks)*self.transmission, linestyle = '--', color = 'k')
        
    def plot_asymm_result(self):
        '''
        plots the spectrum and the individual after aysmmetrization
        '''
        plt.figure()
        plt.plot(self.shifts, self.spec)
        plt.plot(self.shifts,self.bg)
        for asymmpeak in self.asymm_peaks:
            
            plt.plot(self.shifts,self.bg+self.asymm_line(asymmpeak)*self.transmission)            
                
    def add_new_peak(self):
        '''
        lifted from Iterative_Raman_Fitting
        '''
        #-----Calc. size of x_axis regions-------
        sectionsize=(np.max(self.shifts)-np.min(self.shifts))/float(self.regions)
        Start=np.min(self.shifts)
    
        results=[]
        loss_results=[]
    
        #-------What does the curve look like with the current peaks?-------
        if not len(self.peaks):
            Current=np.array(self.shifts)*0
        else:
            Current=self.multi_line(self.peaks)

        #-------Set up Loss function--------    
        def loss(params):
            return np.sum(np.abs(Current+self.line(*params)-self.signal))#*self.multi_L(self.shifts,*self.peaks))# if this overlaps with another lorentzian it's biased against it
        
        #-----Minimise loss in each region--------- 
    
        for i in range(int(self.regions)):
            bounds=[(0,np.inf),(i*sectionsize+Start,(i+1)*sectionsize+Start),(0,max(self.shifts)-min(self.shifts))]
            Centre=(i+np.random.rand())*sectionsize+Start
            try: Height= max(truncate(self.signal, self.shifts, i*sectionsize+Start,(i+1)*sectionsize+Start)[0])-min(self.signal)
            except: Height = self.noise_threshold
            params = [Height,Centre,self.width]
    
            params = minimize(loss, params, bounds=bounds).x.tolist()
    
            results.append(params)
            loss_results.append(loss(params))
        
        sorted_indices = np.argsort(loss_results)

        self.peak_added = False
        i=-1
        while self.peak_added == False and i<(len(loss_results) -1): # test the top 50% of peaks
            i+=1
            peak_candidate = results[sorted_indices[i]]
            if peak_candidate[0]>self.noise_threshold and self.maxwidth>peak_candidate[2]>self.minwidth: #has a height, minimum width - maximum width are within bounds     
                if len(self.peaks)!=0: 
                    dump, peak, residual = find_closest(peak_candidate[1],np.transpose(self.peaks)[1])
                    if residual>self.min_peak_spacing*self.peaks[peak][2]: # is far enough away from existing peaks
                        self.peaks.append(peak_candidate)
                        self.peak_added = True    
                    
                else: # If no existing peaks, accept it
                    self.peaks.append(peak_candidate)
                    self.peak_added = True
           
        if self.peak_added:#TODO store these values
            height_bound = (self.noise_threshold,max(self.signal))
            pos_bound = (np.min(self.shifts),np.max(self.shifts))
            width_bound = (self.minwidth,self.maxwidth)
            self.peak_bounds.append([height_bound, pos_bound, width_bound])  # height, position, width
            if self.verbose: print('peak added')
        if not self.peak_added and self.verbose: print('no suitable peaks to add')
    def Wavelet_Estimate_Width(self,Smooth_Loss_Function=2):
        #Uses the CWT to estimate the typical peak FWHM in the signal
        #First, intepolates the signal onto a linear x_scale with the smallest spacing present in the signal
        #Completes CWT and sums over the position coordinate, leaving scale
        #Does minor smooth, and takes scale at maximum as FWHM
        Int=scint.splrep(self.shifts,self.spec)
        Step=np.min(np.abs(np.diff(self.shifts)))        
        New=scint.splev(np.arange(self.shifts[0],self.shifts[-1],Step),Int)                         
        Scales=np.arange(1,np.ceil(old_div(self.maxwidth,Step)),1)        
        Score=np.diff(np.sum(pywt.cwt(New,Scales,'gaus1')[0],axis=1))        
        Score=ndimf.gaussian_filter(Score,Smooth_Loss_Function)        
        Scale=Scales[np.argmax(Score)]*Step
        return Scale

    def initial_bg_poly(self):
        '''
        takes an inital guess at the background.
        takes the local minima of the smoothed spectrum, weighted by how far they are to other minima, and fits to these.
        weighting is to prioritise flatter portions of the spectrum (which would naturally have fewer minima)
        
        '''
        

        try: smoothed = sm.Run(self.spec)
        except:smoothed = smoothed = sm2(self.spec, 2)
        self.bg_indices = argrelextrema(smoothed, np.less)[0]
        self.bg_vals = smoothed[self.bg_indices]
        
        residuals = []
        for index in self.bg_indices:
            residuals.append(find_closest(index, np.setdiff1d(self.bg_indices, index))[2])
        norm_fac = 5./max(residuals)
        extra_lens = norm_fac*np.array(residuals)
        for bg_index, extra_len in zip(self.bg_indices, extra_lens):
            extra_len = int(extra_len)
            if extra_len<1: extra_len = 1
            for extra in np.arange(extra_len)+1:
                try:
                    self.bg_vals.append(smoothed[bg_index+extra])
                    self.bg_indices.append(bg_index+extra)
                except: pass
                try:
                    self.bg_vals.append(smoothed[bg_index-extra])
                    self.bg_indices.append(bg_index-extra)
                except: pass                    
        edges = np.arange(5)+1
        edges = np.append(edges, -edges).tolist()
        self.bg_indices = np.append(self.bg_indices, edges)
        self.bg_vals= np.append(self.bg_vals, smoothed[edges])
            
        if self.bg_type == 'poly':
            self.bg_bound = (min(self.spec), max(self.spec))
            self.bg_bounds = []
            while len(self.bg_bounds)<len(self.bg_vals):
                self.bg_bounds.append(self.bg_bound)
            self.bg_p = np.polyfit(self.shifts[self.bg_indices], self.bg_vals, self.order)
            self.bg = np.polyval(self.bg_p, self.shifts)
            self.signal = (old_div((np.array(self.spec - self.bg)),self.transmission)).tolist()
        else:
            
            if self.vary_const_bg == False:
                self.bg_p = curve_fit(self.bg_function, self.shifts[self.bg_indices], self.bg_vals, p0 = [0.5*max(self.spec), 300, 1E-10], maxfev = 100000, bounds = self.bg_bounds)[0]
            else:
                self.bg_p = curve_fit(self.bg_function, self.shifts[self.bg_indices], self.bg_vals, p0 = [0.5*max(self.spec), 300, min(self.spec)], maxfev = 100000, bounds = self.bg_bounds)[0]
            self.bg = self.bg_function(self.shifts, *self.bg_p)
            self.signal = (old_div((np.array(self.spec - self.bg)),self.transmission)).tolist()
            
    def bg_loss(self,bg_p):
        '''
        evaluates the fit of the background to spectrum-peaks
        '''
        
        fit = np.polyval(bg_p, self.shifts)
        residual = self.spec - self.peaks_evaluated - fit
        above = residual[residual>0]
        below = residual[residual<0]
        obj = np.sum(np.absolute(above))+np.sum(np.array(below)**2)
        
        return obj

    def optimize_bg(self):# takes bg_vals
        '''
        it's important to note that the parameter optimised isn't the polynomial coefficients bg_p , 
        but the points taken on the spectrum-peaks curve (bg_vals) at positions bg_indices, decided by initial_bg_poly().
        This is because it's easy to put the bounds of the minimum and maximum of the spectrum on these to improve optimisation time. (maybe)
        '''
        if self.asymm_peaks_stack == None:
            self.peaks_evaluated = self.multi_line(self.shifts, self.peaks)*self.transmission
        else:
            self.peaks_evaluated  = self.asymm_multi_line(self.shifts, self.asymm_peaks)*self.transmission
          
        if self.bg_type == 'poly':       
            self.bg_p = minimize(self.bg_loss, self.bg_p).x.tolist()
            self.bg = np.polyval(self.bg_p, self.shifts)
            self.signal =(old_div(np.array(self.spec - self.bg),self.transmission)).tolist()
        elif self.bg_type == 'exponential' or self.bg_type == 'exponential2':
            
            self.bg_p = curve_fit(self.bg_function,
                                  self.shifts,
                                  self.spec - self.multi_line(self.shifts, self.peaks)*self.transmission, 
                                  p0 = self.bg_p,
                                  bounds = self.bg_bounds,
                                  maxfev = 10000)[0]
            self.bg = self.bg_function(self.shifts, *self.bg_p)
    @staticmethod
    def peaks_to_matrix(peak_array):
        '''
        converts a 1d peak_array into a 2d one
        '''
        
        return [peak for peak in reshape(peak_array,3)]
        
    def peak_loss(self,peaks):
        '''
        evalutes difference between the fitted peaks and the signal (spectrum - background)
        '''
        fit = self.multi_line(self.peaks_to_matrix(peaks))
        obj = np.sum(np.square(self.signal - fit))
        return obj
   
    def optimize_peaks(self):
        '''
        optimizes the height, centres and widths of all peaks
        '''
        if len(self.peaks)<2: return
        bounds = []
        for bound in self.peak_bounds: bounds.extend(bound)
        self.peaks = self.peaks_to_matrix(minimize(self.peak_loss, np.ravel(self.peaks), bounds=bounds).x.tolist())

    def optimize_centre_and_width(self):
        '''
        optimizes the centres(positions) and widths of the peakss for a given heights.
        '''
        if len(self.peaks)<2: return
        heights = np.transpose(self.peaks)[0]
        centres_and_widths = np.transpose(self.peaks)[1:]
        # centres_and_widths = np.ravel(centres_and_widths)
        width_bound = (self.minwidth,self.maxwidth)        
        centre_and_width_bounds = []
        for centre, width in zip(*centres_and_widths):   
         centre_and_width_bounds.extend([(centre-width, centre+width),(width_bound)])  # height, position, width
        
        def multi_line_centres_and_widths(centres_and_widths):
            """
            Defines a sum of Lorentzians. Params goes Height1,Centre1, Width1,Height2.....
            """
            params = [[h, c, w] for h, (c,w) in zip(heights, reshape(centres_and_widths, 2))]
            return self.multi_line(params)
        
        def loss_centres_and_widths(centres_and_widths):
            fit = multi_line_centres_and_widths(centres_and_widths)
            obj = np.sum(np.square(self.signal - fit))
            return obj
        centres_and_widths = minimize(loss_centres_and_widths,np.ravel(centres_and_widths, 'F'), bounds = centre_and_width_bounds).x
        self.peaks = [[h, c, w] for h, (c,w) in zip(heights, reshape(centres_and_widths, 2))]
        
    def optimize_heights(self):
        '''
        crudely gets the maximum of the signal within the peak width as an estimate for the peak height
        '''
        if len(self.peaks)<1: return
        else:   
           
            for index, peak in enumerate(self.peaks):
                try:
                    self.peaks[index][0] = max(truncate(self.signal, self.shifts, peak[1]-peak[2]/4., peak[1]+peak[2]/4.)[0])
                except:
                    self.peaks[index][0] = self.signal[find_closest(peak[2], self.shifts)[1]]
         
            
    def loss_function(self):
        '''
        evaluates the overall (bg+peaks) fit to the spectrum
        '''
        
        fit = self.bg + self.multi_line(self.peaks)*self.transmission
        obj = np.sum(np.square(self.spec - fit))
        return obj            
    
    def optimize_peaks_and_bg(self):
        '''
        optimizes the peaks and background in one procedure, 
        allowing for better interplay of peaks and bg
        '''
        if self.bg_type == 'poly':
            def loss(peaks_and_bg):
                fit = np.polyval(peaks_and_bg[:self.order+1], self.shifts) 
                fit+= self.multi_line(self.peaks_to_matrix(peaks_and_bg[self.order+1:]))*self.transmission
                residual = self.spec - fit
                above = residual[residual>0]
                below = residual[residual<0]
                obj = np.sum(np.absolute(above))+np.sum(np.array(below)**2) # prioritises fitting the background to lower data points
                return obj
            peaks_and_bg = np.append(self.bg_p, np.ravel(self.peaks))
            bounds = [(-np.inf, np.inf) for p in self.bg_p]
            if len(self.peaks): 
                for bound in self.peak_bounds: bounds.extend(bound)
            peaks_and_bg = minimize(loss, peaks_and_bg, bounds=bounds).x.tolist()
             
            self.bg_p = peaks_and_bg[:self.order+1]
            self.peaks = self.peaks_to_matrix(peaks_and_bg[self.order+1:])
            self.bg = np.polyval(self.bg_p, self.shifts)
        else:
            def loss(peaks_and_bg):
                fit = self.bg_function(peaks_and_bg[:3])
                fit+= self.multi_line( peaks_and_bg[3:])*self.transmission
                residual = self.spec - fit
                above = residual[residual>0]
                below = residual[residual<0]
                obj = np.sum(np.absolute(above))+np.sum(np.array(below)**2) # prioritises fitting the background to lower data points
                return obj
            peaks_and_bg = np.append(self.bg_p, self.peaks)
            if self.vary_const_bg == False:
                bounds = [(0, max(self.spec)*10),
                         (100,1000),
                         (min(self.spec*0.7), 1e-9)]
            else:
                 bounds = [(0, max(self.spec)*10),
                         (100,1000),
                         (min(self.spec*0.7), max(self.spec))]
                     
            bounds.extend(self.peak_bounds)
            peaks_and_bg = minimize(loss, peaks_and_bg, bounds = bounds).x
            self.bg_p = peaks_and_bg[:3]
            self.peaks = self.peaks_to_matrix(peaks_and_bg[3:])
            self.bg = self.bg_function(self.shifts, *self.bg_p)


    def optimize_asymm(self):
        '''
        allows the peaks to become asymmetric by raising either side of the peaks to separate exponents (alpha and beta) 
        '''
        width_alpha_beta = []
        asymmbounds = []
        if self.asymm_peaks is None:
            self.asymm_peaks_stack = []

            for peak in self.peaks:
                width_alpha_beta.extend([peak[2],1., 1.]) # initial alpha, beta
                asymmbounds.extend([(peak[2]/5., peak[2]*5),
                                    (0.8,1.2),
                                    (0.8,1.2)])
            asymmbounds = np.array(asymmbounds)
        else:
            
            for asymm_peak in  self.asymm_peaks:
                width_alpha_beta.extend([asymm_peak[2],
                                         asymm_peak[3],
                                         asymm_peak[4]])
                asymmbounds.extend([(old_div(asymm_peak[2],5), asymm_peak[2]*5),
                                    (0.9,1.1),
                                    (0.9,1.1)])

        def asymmloss(width_alpha_beta):
            width_alpha_beta_stack = self.peaks_to_matrix(width_alpha_beta)
            params = []
            for peak, width_alpha_beta in zip(self.peaks, width_alpha_beta_stack):
                params.append([*peak[0:2], *width_alpha_beta])
            fit = self.asymm_multi_line(params)
            obj = np.sum(np.square(self.signal - fit))
            return obj 

        width_alpha_beta = minimize(asymmloss, width_alpha_beta, bounds = asymmbounds).x.tolist()     
        wab_stack = self.peaks_to_matrix(width_alpha_beta)
        self.asymm_peaks = [[*peak[0:2], *width_alpha_beta] for peak, width_alpha_beta in zip(self.peaks, wab_stack)]
        
    
    def asymm_line(self, asymmpeak):
        '''
        defines an asymmetric lineshape - depends on whether initial lineshape is L or G
        '''
        
        alpha = np.true_divide(self.line(asymmpeak[0], asymmpeak[1], asymmpeak[2]), asymmpeak[0])**asymmpeak[3]
        alpha = truncate(alpha, self.shifts, -np.inf, asymmpeak[1])[0]
        
        alpha *= asymmpeak[0]
        beta = np.true_divide(self.line(asymmpeak[0], asymmpeak[1], asymmpeak[2]), asymmpeak[0])**asymmpeak[4]
        beta = truncate(beta, self.shifts, asymmpeak[1], np.inf)[0]
        beta *= asymmpeak[0]
        return np.append(alpha, beta)
    
    def asymm_multi_line(self, params): # params is 2d
        '''
        outputs sum of many asymmetric peaks
        '''

        return np.sum([self.asymm_line(asymmpeak) for asymmpeak in params],axis=0)

    def dummyRun(self,
            initial_fit=None, 
            add_peaks = True, 
            allow_asymmetry = False,
            minwidth = 8, 
            maxwidth = 30, 
            regions = 20, noise_factor = 0.01, 
            min_peak_spacing = 5, 
            comparison_thresh = 0.05, 
            verbose = False):    
        '''
        handy to test other scripts quickly
        '''
       
        self.initial_bg_poly()
        self.minwidth = minwidth
        self.maxwidth = maxwidth
#        if initial_fit is not None:
#            self.peaks = initial_fit
#            self.peaks_stack = np.reshape(self.peaks, [len(self.peaks)/3, 3])
#            self.optimize_heights
#            #self.optimize_centre_and_width()

        try: smoothed = np.array(sm.Run(self.signal))
        except: smoothed = sm2(self.spec, 2)
        maxima = argrelextrema(smoothed, np.greater)[0]
        heights = smoothed[maxima]
        maxima = maxima[np.argsort(heights)[-5:]]
        heights = smoothed[maxima]
        
        centres = self.shifts[maxima]
        widths = np.ones(len(maxima))*17
        
        self.peaks = np.transpose(np.stack([heights, centres, widths]))
    
        self.optimize_heights
        self.optimize_centre_and_width()
        print("I'm a dummy!")        
    
    def Run(self,
            initial_fit=None, 
            add_peaks = True, 
            allow_asymmetry = False,
            minwidth = 2.5, 
            maxwidth = 20, 
            regions = 10, 
            noise_factor = 0.1, 
            min_peak_spacing = 3.1, 
            comparison_thresh = 0.01, 
            verbose = False):    
        '''
        described at the top
        '''
        if self.lineshape == 'L': 
            self.maxwidth = maxwidth/2.
            self.minwidth=minwidth/2.
        if self.lineshape == 'G':
            self.maxwidth = maxwidth/0.95
            self.minwidth = minwidth/0.95
        self.verbose = verbose
        self.min_peak_spacing = min_peak_spacing
        self.width = 4*self.Wavelet_Estimate_Width() # a guess for the peak width
        self.regions = regions # number of regions the spectrum will be split into to add a new peak
        if self.regions>len(self.spec):self.regions = len(self.spec)//2 # can't be have more regions than points in spectrum
        self.noise_threshold = noise_factor*np.std(Grad(self.spec)) # peaks must be above this to be accepted
        self.initial_bg_poly() # takes a guess at the background
        if initial_fit is not None:
            self.peaks = initial_fit
            self.regions = len(self.spec)/20.
            if add_peaks == False: self.regions*=21 # if regions is bigger than the spectrum length, then no peaks are added
            self.peaks_stack = self.peaks_to_matrix(self.peaks) # 2d array of peak parameters
            height_bound = (self.noise_threshold,max(self.signal)) # bounds for the peak parameters
            pos_bound = (np.min(self.shifts),np.max(self.shifts))
            width_bound = (self.minwidth,self.maxwidth)
            self.peak_bounds = []
            for _ in self.peaks:                          
                self.peak_bounds.append([height_bound, pos_bound, width_bound]) # creates a bound for each peak
            self.optimize_heights() # see functions for descriptions
            self.optimize_centre_and_width()            
            #self.optimize_peaks()

        
        while self.regions <= len(self.spec): 
            
            if verbose == True: print('Region fraction: ', np.around(self.regions/float(len(self.spec)), decimals = 2))
            existing_loss_score = self.loss_function() # measure of fit 'goodness'
            Old = self.peaks # peaks before new one added
            self.add_new_peak() # adds a peak
            if verbose == True: print('# of peaks:', len(self.peaks))
#            self.optimize_heights
#            self.optimize_centre_and_width()
            self.optimize_peaks_and_bg() # optimizes 
            new_loss_score = self.loss_function()
            
            #---Check to increase regions
            if new_loss_score >= existing_loss_score: #if fit has worsened, delete last peak
                if self.peak_added:                        
                    self.peaks = self.peaks[:-1]
                    self.peak_bounds = self.peak_bounds[:-1]
                    if verbose: print('peak removed as it made the fit worse')
                self.regions*=4 # increase regions, as this is a sign fit is nearly finished
                
            elif not self.peak_added:  #Otherwise, same number of peaks?
#                self.optimize_bg()
#                self.optimize_heights() # fails if no peaks
#                self.optimize_centre_and_width()
#                self.optimize_peaks()
                self.optimize_peaks_and_bg()
                New = self.peaks
                New_trnsp = np.transpose(New)
                residual = []
                for old_peak in Old:
                        new_peak = find_closest(old_peak[1], New_trnsp[1])[1]# returns index of the new peak which matches it
                        old_height = old_peak[0]
                        old_pos = old_div(old_peak[1],self.width)
                        new_height = old_div(New[new_peak][0],old_height)
                        new_pos = old_div(New[new_peak][1],self.width) # normalise the height and position parameters to add them into one comparison score
                        residual.append(np.linalg.norm(np.array([1,old_pos])-np.array([new_height,new_pos]))) # the difference between old and new for each peak
                comparison = np.array(residual)>comparison_thresh
                if type(comparison) == bool: # happens if only 1 peak
                    if comparison ==False:
                        self.regions*=5                
                else:
                    if any(comparison) == False: #if none of the peaks have changed by more than comparison_thresh fraction
                        self.regions*=5
                        if verbose == True: print("peaks haven't changed significantly; regions increased")
            elif not len(self.peaks): # if there wasn't a peak added, try harder
                self.regions*=5
   
        #---One last round of optimization for luck: can comment these in and out as you see fit. 
#        self.optimize_bg()
#        
        self.optimize_peaks_and_bg()
        self.optimize_heights()
        self.optimize_centre_and_width()
        self.optimize_peaks()
        if allow_asymmetry:
            if verbose: print('asymmetrizing')
            self.optimize_asymm()
#            for i in range(2): # more iteratively optimizes the asymmetric peaks
#                self.optimize_asymm()
#                self.optimize_bg()
#           
        
if __name__ == '__main__':
   from nplab.analysis.example_data import SERS_and_shifts
   spec = SERS_and_shifts[0]
   shifts = SERS_and_shifts[1]
   spec, shifts = truncate(spec, shifts, 190, np.inf)
   ff = fullfit(spec, shifts, lineshape='G', order=7)
   ff.Run(verbose=True)
   ff.plot_result()