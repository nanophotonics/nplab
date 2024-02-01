# -*- coding: utf-8 -*-
"""
Created on Sat Feb 11 17:17:54 2023

BG removal based on ALS

@author: jb2444
"""
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
from scipy.signal import find_peaks
import matplotlib.pyplot as plt
#%% find index
# given an array and a value, find the index of the array cell with the value closest to the given value
# the value does not have to be equal.

def find_index(data_array, number):    
    result=np.where(np.abs(data_array-number) == np.min(np.abs(data_array-number)))
    return result


#%% Baseline ALS removel
def baseline_als(data, lda , p, niter=10):
    # see: https://stackoverflow.com/questions/29156532/python-baseline-correction-library
    # lda and p are parameters for smoothness and assymetry, respectively
    # generally 0.001 ≤ p ≤ 0.1 is a good choice (for a signal with positive peaks),
    # and 10^2 ≤ λ ≤ 10^9 , but exceptions may occur. 
    # In any case one should vary λ on a grid that is approximately linear for log λ

  L = len(data)
  D = sparse.csc_matrix(np.diff(np.eye(L), 2))
  w = np.ones(L)
  for i in range(niter):
    W = sparse.spdiags(w, 0, L, L)
    Z = W + lda * D.dot(D.transpose())
    z = spsolve(Z, w*data)
    w = p * (data > z) + (1-p) * (data < z)
  return z


#%% find local minima of vector for pre-processing of signal before ALS BG removal

def fluorescence_BG_removal(xdata,ydata,test=True,peakWidthRange=[3,20],exclude_region=[1000,1700],ALSparams=[1e4,1e-2]):
# drives a few cycles of minima finding using find_peaks on the inverted signal, then returns the vectors of the detected background,
# with excluded region.
    BG1=np.zeros(np.shape(ydata)) # create the BG matrix
    # find the minima by finding peaks of the inverted signal
    mins,mins_props=find_peaks(-ydata/np.max(ydata),width=peakWidthRange) # mins are detected minima in the signal.
                # while len(mins)<=1 and peakWidthRange[0]>=0:
                #     peakWidthRange[0]=peakWidthRange[0]-1
                #     mins,mins_props=find_peaks(-ydata/np.max(ydata),width=peakWidthRange)
    
    # create a vector of same size as ydata which is linear lines connecting the detected minima
    prev=ydata[0]
    prev_ind=0
    current=ydata[0]        
    current_ind=0
    
    # the following section creates a vector of linear lines connecting the detected minima, and stores it to BG1
    if len(mins)==1:
        current=ydata[mins[0]]
        current_ind=mins[0]
        BG1[prev_ind:current_ind+1]=np.linspace(prev,current,current_ind-prev_ind+1)
        prev_ind=current_ind
        prev=current
    if len(mins)>1:
        for qq in range(1,len(mins)):
            current=ydata[mins[qq]]
            current_ind=mins[qq]
            BG1[prev_ind:current_ind+1]=np.linspace(prev,current,current_ind-prev_ind+1)
            prev_ind=current_ind
            prev=current

    BG1[current_ind:len(BG1)]=np.linspace(current,ydata[-1],len(BG1)-current_ind) # BG1 is the line connecting from one detected minimum to the next.
    
    BG2=[min(a,b) for a,b in zip(BG1,ydata)] # BG2 takes the minimum value between BG1 and the signal in every point
    # mins 2 is the list of minima under 1000wn or above 1700
    if exclude_region is not None: # used to exclude a part of the signal from the background calculation
        mins2=[x for x in mins if ((xdata[x] < exclude_region[0]) or (xdata[x]>exclude_region[1]))] # finding the local minima which are in the exclusion region
        ind_min=find_index(xdata[mins2],exclude_region[0])[0][0]
        ind_max=find_index(xdata[mins2],exclude_region[1])[0][0]
        BG3=BG2[:] # BG3 initial value is same as BG2
        BG3[mins2[ind_min]:mins2[ind_max]+1]=np.linspace(BG3[mins2[ind_min]],
                                                         BG3[mins2[ind_max]],
                                                         mins2[ind_max]-mins2[ind_min]+1) 
        # BG3 in the exclusion region is changed to be a linear
        # line between the detected minima at the edges of the exclusion region
        
        BG3=[min(a,b) for a,b in zip(BG3,BG2)] # finally, BG3 is compared to BG2 and the minimum is taken.

    else:
        mins2=mins[:]
        BG3=BG2[:]

    BG=np.zeros(np.shape(BG2)) # create the BG matrix
    BG = baseline_als(BG3, lda=ALSparams[0] , p=ALSparams[1], niter=20) # BG is the smooth background curve made by ALS method on BG3 line
    clean_data=ydata-BG #clean spectrum
    if test: # plot all steps
        plt.figure()
        plt.plot(xdata,ydata,label='signal')
        plt.scatter(xdata[mins],ydata[mins],label='detected minima')
        plt.plot(xdata,BG1,label='BG1')
        plt.plot(xdata,BG2,label='BG2')
        plt.plot(xdata,BG3,label='BG3')
        plt.plot(xdata,BG,label='smooth BG')
        plt.plot(xdata,clean_data,color='red',label='clean data')
        plt.legend()
    return clean_data, BG

#%% how to use background removal - uncomment and run

# import h5py
# import os

# # example usage of ALS method, data taken from Blatter radical NPoM
# # need to unzip example file for this to run

# dirc = os.getcwd()
# file = h5py.File(dirc+'\\example_file_for_ALS.h5','r')
# data_set = file['example_spectrum']
# data = data_set[()] # spectrum to be fitted
# lda = data_set.attrs['wavelengths'] # wavelengths
# wn = data_set.attrs['wavenumbers'] # wavenumbers

# clean_data, BG = fluorescence_BG_removal(xdata = wn,ydata = data ,
#                                           test=True,
#                                           peakWidthRange=[3,20],
#                                           exclude_region=[1000,1700],
#                                           ALSparams=[1e4,1e-2])
# file.close()
