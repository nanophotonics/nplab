from __future__ import division
from past.utils import old_div
import numpy as np

"""
Author: jpg66

This is a rewrite of the z-scan analysis code, but hopefully cleaner and without a lot of fluff.

To use, input the z_scan array into the run function. For each wavelength, the centroid z-postion will be calcualted and the corresponding
intensity linearly interpolated. The resulting 1D spectrum is returned.

Note: The Z scan array should already be background subtracted and referenced.
"""

def Linear_Interpolation(Value1,Value2,Frac):
    #Value 1 and 2 are two numbers. Frac is between 0 and 1 and tells you fractionally how far between the two values you want ot interpolate

    m=Value2-Value1
    c=Value1

    return (m*Frac)+c

def Run(Z_Scan,Threshold=0.2, Smoothing_width=1.5):
    """
    Here, the Z_Scan is assumed to already by background subtracted and referenced.
    """

    Thresholded=np.nan_to_num(Z_Scan)

    Thresholded=Thresholded.astype(np.float64)
    Thresholded=old_div((Thresholded - Thresholded.min(axis=0)),(Thresholded.max(axis=0)-Thresholded.min(axis=0)))
    Thresholded-=Threshold
    Thresholded*=(Thresholded>0)       #Normalise and Threshold array

    Ones=np.zeros([Z_Scan.shape[1]])+1
    Positions=[]
    while len(Positions)<Z_Scan.shape[0]:
        Positions.append(Ones*len(Positions))
    Positions=np.array(Positions).astype(np.float64)

    Centroids=old_div(np.sum((Thresholded*Positions),axis=0),np.sum(Thresholded,axis=0)) #Find Z centroid position for each wavelength

    Centroids=np.nan_to_num(Centroids)

    Rotated=np.transpose(Z_Scan)

    Output=[]
    n=0
    while n<len(Centroids):
        Lower=int(Centroids[n])
        Upper=Lower+1

        Frac=Centroids[n]-Lower
        if Upper==len(Rotated[n]):
            Upper-=1
            Frac=0
        #if Lower==len(Rotated):
            #Lower-=1

        #print Lower,Upper

        Output.append(Linear_Interpolation(Rotated[n][Lower],Rotated[n][Upper],Frac))

        n+=1

    return np.array(Output)






