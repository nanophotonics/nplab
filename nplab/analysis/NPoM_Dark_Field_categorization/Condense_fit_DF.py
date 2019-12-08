# -*- coding: utf-8 -*-
"""
Created on Thu May 31 01:11:45 2018

@author: car72
"""
from __future__ import division
from __future__ import print_function
from past.utils import old_div
if __name__ == '__main__':
    print('Importing modules...')

#import h5py
import os
rootDir = os.getcwd()
import numpy as np
import time
import matplotlib.pyplot as plt
from nplab.analysis import DF_PL_Multipeakfit as mpf
from nplab.analysis import Condense_DF_Spectra as cdf
#charDir = r'C:\Users\car72\Documents\GitHub\charlie\charlie'
#os.chdir(charDir)
#import DF_PL_Multipeakfit as mpf
os.chdir(rootDir) #Important

if __name__ == '__main__':
    absoluteStartTime = time.time()
    print('\tModules imported')

    '''Set raiseExceptions = True if the anaylsis fails; this will return the traceback'''
    raiseExceptions = False #Setting this to True will stop the analysis return the traceback if an individual spectrum fails

    statsOnly = False #if you have already analysed the spectra and want to re-plot histograms (etc)
    pl = True #Set to True if your dataset contains PL
    npSize = 80 #Peak analysis uses different values for different NP sizes. Valid inputs are 50, 60, 70, 80

    if statsOnly == True:
        outputFileName = mpf.findH5File(os.getcwd(), nameFormat = 'MultiPeakFitOutput', mostRecent = True)#finds the most recent file with given name format
        mpf.doStats(outputFileName, stacks = False, pl = pl)

    else:
        startSpec = 0
        finishSpec = 0

        summaryFile = cdf.extractAllSpectra(os.getcwd(), returnIndividual = True, start = startSpec,
                                            finish = finishSpec)#condenses Z-stack (inc. background subtraction and referencing) for each particle and makes summary file

        if pl == True:
            summaryFile = cdf.transferPlSpectra(os.getcwd(), startWl = 505, start = startSpec,
                                                finish = finishSpec)#background subtracts each PL spectra and transfers them to the existing summary file

        #summaryFile = 'summary.h5' #use this instead of the above functions if you already have a summary file

        if raiseExceptions == True:
            outputFileName = mpf.createOutputFile('MultiPeakFitOutput')
            mpf.fitAllSpectra(os.getcwd(), outputFileName, npSize = 80, first = startSpec, last = finishSpec, pl = pl, closeFigures = True, stats = True,
                              raiseExceptions = raiseExceptions, raiseSpecExceptions = raiseExceptions)


            print('\nData fitting complete')

        else:
            try:
                outputFileName = mpf.createOutputFile('MultiPeakFitOutput')
                mpf.fitAllSpectra(os.getcwd(), outputFileName, npSize = 80, first = startSpec, last = finishSpec, pl = pl, closeFigures = True, stats = True,
                                  raiseExceptions = raiseExceptions, raiseSpecExceptions = raiseExceptions)

                print('\nData fitting complete')

            except Exception as e:
                print('\nData fitting failed because %s' % (e))

    plt.close('all')
    absoluteEndTime = time.time()
    timeElapsed = absoluteEndTime - absoluteStartTime

    hours = int(old_div(timeElapsed, 3600))
    mins = int(np.round(old_div((timeElapsed % 3600),60)))
    secs = int(np.round(timeElapsed % 60))

    if hours > 0:
        print('\nM8 that took ages. %s hours %s min %s sec' % (hours, mins, secs))

    else:
        print('\nFinished in %s min %s sec' % (mins, secs))
