# -*- coding: utf-8 -*-
"""
Created on Thu May 31 01:11:45 2018

@author: car72
"""
if __name__ == '__main__':
    print('Importing modules...')

import os
import numpy as np
import time
import matplotlib.pyplot as plt
from nplab.analysis import DF_MultipeakfitBeta as mpf
from nplab.analysis import Condense_DF_Spectra as cdf

if __name__ == '__main__':
    absoluteStartTime = time.time()
    print('\tModules imported')

    startSpec = 0
    finishSpec = 0
    raiseExceptions = True #If the code keeps returning errors, try setting this to False. This will ignore and discard individual spectra that cause errors

    summaryFile = 'summary.h5'

    if summaryFile not in os.listdir('.'):
        summaryFile = cdf.extractAllSpectra(os.getcwd(), returnIndividual = True, start = startSpec, finish = finishSpec)

    if raiseExceptions == True:
        x, yData, summaryAttrs = mpf.retrieveData(os.getcwd())
        initImg = mpf.plotInitStack(x, yData, imgName = 'Initial Stack', closeFigures = True)
        outputFileName = mpf.createOutputFile('MultiPeakFitOutput')
        mpf.fitAllSpectra(x, yData, outputFileName, summaryAttrs = summaryAttrs, stats = True, raiseExceptions = True)
        #mpf.doStats('MultiPeakFitOutput.h5', closeFigures = True)

        print('\nData fitting complete')

    else:
        try:
            x, yData, summaryAttrs = mpf.retrieveData(os.getcwd())
            initImg = mpf.plotInitStack(x, yData, imgName = 'Initial Stack', closeFigures = True)
            outputFileName = mpf.createOutputFile('MultiPeakFitOutput')
            mpf.fitAllSpectra(x, yData, outputFileName, summaryAttrs = summaryAttrs, stats = True, raiseExceptions = raiseExceptions)
            #mpf.doStats('MultiPeakFitOutput.h5', closeFigures = True)

            print('\nData fitting complete')

        except Exception as e:
            print('\nData fitting failed because %s' % (e))

    plt.close('all')

    absoluteEndTime = time.time()
    timeElapsed = absoluteEndTime - absoluteStartTime

    hours = int(timeElapsed / 3600)
    mins = int(np.round((timeElapsed % 3600)/60))
    secs = int(np.round(timeElapsed % 60))

    if hours > 0:
        print('\nM8 that took ages. %s hours %s min %s sec' % (hours, mins, secs))

    else:
        print('\nFinished in %s min %s sec' % (mins, secs))
