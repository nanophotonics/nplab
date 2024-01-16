# -*- coding: utf-8 -*-
"""
Created on Sat Feb 11 17:47:01 2023

@author: jb2444
"""

import numpy as np
from scipy.optimize import curve_fit


#%% definition of fit function (polynomial)


def fit_func(x, *params):
    # fit function of a polynomial;
    # note that multiple parameters are read to the function as a tuple!
    # this is done by using the *
    # loading a list\tuple \np array of parameters is also possible in this writing
    # by loading it a s fit_func(x_vector,*parameter_sequence)
    F=np.zeros(x.shape)
    P=np.array([])
    for value in params:
        P=np.append(P,value)
    for ii,p in enumerate(P ):   
        F=F+float(p)*(x**ii)
    return F


#%% curve fitting

def my_curve_fit(func, xdata, ydata, *initial_parameters): # the * makes it possible to assign any number of parameters
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
    params1 = curve_fit(func, xdata=xdata, ydata=ydata, p0=init_params,maxfev=10000) #maxfev=10000
   
    # get the calculated parameters
    calc_params = params1[0]
    
    # y values predicted by the fit
    yfit1=func(xdata, *calc_params) # the * forces python to treat this list as seperate variables !

    # SSE - sum of squared differences between data and model prediction
    SSE=sum( (yfit1-ydata)**2 );
    # SST - sum of squared differences between the data and the mean of the data.
    # mathematically this is the variance of the data
    SST=sum( (ydata - (sum(ydata)/len(ydata)))**2 );
    # calculation of R^2 goodness of fit
    Rsquared=1-(SSE/SST);

    return calc_params, yfit1, Rsquared

#%% curve_fitting with bounds

def my_bounded_curve_fit(func, xdata, ydata, init_params, bounds):
    # func is the theoretical function, needs to be passed on to curve_fit function as a function, 
    # not as values;
    # xdata and ydata are the values;
    # initial parameters are the initial guess on parameters; given as list!
    # bounds is a tuple with structure ([list],[list])
    
    # perform fit
    # turning init params to array probably excessive
    
    # for param in initial_parameters:
    #     init_params=np.append(init_params,param)
    params1 = curve_fit(func, xdata=xdata, ydata=ydata, p0=init_params,bounds=bounds,maxfev=10000) #maxfev=10000

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