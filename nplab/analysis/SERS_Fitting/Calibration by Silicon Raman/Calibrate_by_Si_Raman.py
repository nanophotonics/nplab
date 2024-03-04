# -*- coding: utf-8 -*-
"""
Created on Mon Mar  4 11:47:08 2024

this file holds functions allowing to calibrate the wavelength vector given by a spectrometer to absolute values of wavelength and wavenumbers,
based on the measurment of the Silicon Raman spectrum.

the functions defined here are:
    * find index: for an array and a number, returns the index in which the value is closes to the number.
    for example: 
        A=np.array(np.array([1,2.5,700]))
        x=3
        find_index(A,x)[0][0]
        Out[7]: 1
        
    * wavenumbers_from_si: inputs an np.array which is a wavelength vector obtained from spectrometer wavelength_vector, 
    and exact locations of the Stokes and anti-Stokes Raman peaks (si_stokes_wl,si_antistokes_wl),
    and outputs: 
    wavenumber_vector - a calibrated wavenumber vector, 
    wl_corrected - a calibrated wavelength vector, 
    lda_laser - actual laser wavelength, 
    lda_shift - the shift between spectrometed wavelength vector and reality.
    
    this function does not work well with wavelength vectors with weird calibrations but does a good job when wavelength vector is just shifted.
    
    * my_curve_fit: a curve-fitting function, wrapping the scipy curve_fit, returning the R^2 and fit parameters value.
    used here to fit Lorentzian shaped curves to the Stokes and anti-Stokes lines.
    
to run this properly you need a Si Raman spectrum measured in your system,
containing both Stokes and anti-Stokes peaks,
and an initial guess on what is the wavelength of these peaks - it doesn't need to be accurate because the peaks are fitted.
    

@author: jb2444
"""

#%% general imports
import matplotlib.pyplot as plt
import numpy as np
import h5py
from nplab.analysis import Spectrum, latest_scan, load_h5
from scipy.optimize import curve_fit
from os import getcwd


plt.rcParams['figure.dpi'] = 150

#%% general parameters
# 1st guess for positions of stokes and anti-stokes peaks
lda_stokes=658 # in nm!
lda_anti=616
fname='Sample_Si_Raman' # data file
data_set_name='Si_Raman_633' # this is the name of your saved measurement

dirc = getcwd()
file=h5py.File(dirc+'/'+fname+'.h5','r')

#%% just some auxillary functions

def find_index(data_array, number): 
    # input a np array data_array and value number. 
    # returns a tupple with the 1st object being the array index who;s value is the closest to number.
    
    result=np.where(np.abs(data_array-number) == np.min(np.abs(data_array-number)))
    return result


#%% wavenumbers and actual laser wavelength from Si Raman

def wavenumbers_from_si(wavelength_vector,si_stokes_wl,si_antistokes_wl):
    # lda_det is the naive calculation for the laser wavelength based on the stokes and antistokes peaks,
    # knowing that they should have the same wavenumber with opposit sign
    lda_det=(2*si_stokes_wl*si_antistokes_wl)/(si_stokes_wl+si_antistokes_wl)
    si_wn=520.6*1e-7 # Si wavenumber in nm^-1
    # lda_laser 1 and 3 are the roots of the second degree polynomial, 
    # that results from assuming that the spectrometer is not calibrated
    lda_laser1= (-(si_stokes_wl-lda_det)+np.sqrt( (si_stokes_wl-lda_det)**2 + 4*( (si_stokes_wl-lda_det)/si_wn )  ))/2
    lda_laser3= (-(si_antistokes_wl-lda_det)+np.sqrt( (si_antistokes_wl-lda_det)**2 - 4*( (si_antistokes_wl-lda_det)/si_wn )  ))/2
    #lda_laser=(lda_laser1+lda_laser3)/2
    # the 'final' calculation is a mean of lda_laser 1 and 3
    lda_laser=np.sqrt(lda_laser1*lda_laser3)
    lda_shift=lda_laser-lda_det
    wl_corrected=wavelength_vector+lda_shift
    wavenumber_vector=(1/lda_laser - 1/wl_corrected)*1e7
    return wavenumber_vector, wl_corrected, lda_laser, lda_shift

#%% curve fitting function

def fit_func(x, *params):
    # fit function of a Lorentzian;
    # note that multiple parameters are read to the function as a tuple!
    F=np.zeros(x.shape)
    P=np.array([])
    for value in params:
        P=np.append(P,value)
    for ii,p in enumerate(P ):   
        #F=P[0]*np.exp((-(x-P[1])/P[2])**2)+P[3]
        F=P[0]*1/((x-P[1])**2+P[2])+P[3]
    return F

def my_curve_fit(func, xdata, ydata, *initial_parameters):
    # func is the theoretical function, needs to be passed on to curve_fit function as a function, 
    # not as values;
    # xdata and ydata are the values;
    # initial parameters are the initial guess on parameters; loaded to function as a tuple!
    # perform fit
    # turning init params to array probably excessive
    init_params=[]
    for value in initial_parameters:
        init_params.append(value)
    # for param in initial_parameters:
    #     init_params=np.append(init_params,param)
    params1 = curve_fit(func, xdata=xdata, ydata=ydata, p0=init_params,maxfev=100000) #maxfev=10000

    # get the calculated parameters
    calc_params = params1[0]

    # y values predicted by the fit
    yfit1=func(xdata, calc_params)

    # SSE - sum of squared differences between data and model prediction
    SSE=sum( (yfit1-ydata)**2 );
    # SST - sum of squared differences between the data and the mean of the data.
    # mathematically this is the variance of the data
    SST=sum( (ydata - (sum(ydata)/len(ydata)))**2 );
    # calculation of R^2 goodness of fit
    Rsquared=1-(SSE/SST);

    return calc_params, yfit1, Rsquared

#%% load file

plt.close("all")
# open file
#dirc=r'C:\Users\jb2444\Documents\Temp_data_folder\Eowyn150 from Elsa file'

si_spec=file[data_set_name][()]
lda=file[data_set_name].attrs['wavelengths']

plt.figure()
plt.plot(lda,si_spec)
plt.title('original spectrum')


#%% fit a gaussian to the peaks and detect Stokes and anti-Stokes wavelengths
ROI=10
ind1=find_index(lda,lda_stokes-ROI/2)[0][0]
ind2=find_index(lda,lda_stokes+ROI/2)[0][0]
ind3=find_index(lda,lda_anti-ROI/2)[0][0]
ind4=find_index(lda,lda_anti+ROI/2)[0][0]

x_stokes1=lda[ind1:ind2]
y_stokes1=si_spec[ind1:ind2]

x_stokes2=lda[ind3:ind4]
y_stokes2=si_spec[ind3:ind4]

calc_params1, yfit1, Rsquared1 = my_curve_fit(fit_func,x_stokes1, y_stokes1, [1000,lda_stokes,1,300])
calc_params2, yfit2, Rsquared2 = my_curve_fit(fit_func,x_stokes2, y_stokes2, [300,lda_anti,1,300])


plt.figure()
plt.plot(lda,si_spec,label='original data')
plt.plot(x_stokes1,y_stokes1,label='Stokes data')
plt.plot(x_stokes2,y_stokes2,label='antiStokes data')
plt.plot(x_stokes1,yfit1,label='Stokes fit')
plt.plot(x_stokes2,yfit2,label='antiStokes fit')
plt.title('fitted data')
plt.legend()

print('Si Stokes peak detected at ',str(calc_params1[1]),' nm')
print('Si anti-Stokes peak detected at ',str(calc_params2[1]),' nm')


#%% actually calculate the wavenumber vector

wn, lda_corrected, lda_laser, lda_shift = wavenumbers_from_si(wavelength_vector=lda,
                                                si_stokes_wl=calc_params1[1],
                                                si_antistokes_wl=calc_params2[1])
# draw
plt.figure()
plt.plot(wn,si_spec,label='si')
plt.title('corrected Raman spectrum')

print('detected laser wavelength ',str(lda_laser),' nm')
print('detected spectrometer shift ',str(lda_shift),' nm')

