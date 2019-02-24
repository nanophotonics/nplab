# -*- coding: utf-8 -*-
"""
Created on Thu May 31 01:11:45 2018

@author: car72
"""
if __name__ == '__main__':
    print 'Importing modules...'

import h5py
import os
import numpy as np
import time
import matplotlib.pyplot as plt
from nplab.analysis import DF_MultipeakfitBeta as mpf
from nplab.analysis import Condense_DF_Spectra as cdf
#from charlie import UpdateNpomAttrs as unpa

if __name__ == '__main__':
    absoluteStartTime = time.time()
    print '\tModules imported'

    startSpec = 0
    finishSpec = 0

    summaryFile = cdf.extractAllSpectra(os.getcwd(), returnIndividual = True, start = startSpec, finish = finishSpec)
    #summaryFile = 'summary.h5'
    #overviewFile = r'C:\Users\car72\University Of Cambridge\OneDrive - University Of Cambridge\Documents\PhD\Data\NP\ArV CB\NPoM\DF\ArV CB NPoM Sample Details Overview.csv'
    #dateMeasured = cdf.findH5File(os.getcwd(), nameFormat = 'date')[:10]
    #npomAttrs = unpa.collectNpomAttrs(overviewFile, date = dateMeasured)
    #npomAttrs = npomAttrs[0]
    #unpa.updateSummaryAttrs(summaryFile, npomAttrs)

    raiseExceptions = True

    if raiseExceptions == True:
        x, yData, summaryAttrs = mpf.retrieveData(os.getcwd())
        initImg = mpf.plotInitStack(x, yData, imgName = 'Initial Stack', closeFigures = True)
        outputFileName = mpf.createOutputFile('MultiPeakFitOutput')
        mpf.fitAllSpectra(x, yData, outputFileName, summaryAttrs = summaryAttrs, stats = True, raiseExceptions = True)
        #outputFileName = mpf.findH5File(os.getcwd(), nameFormat = 'MultiPeakFitOutput', mostRecent = True)
        #mpf.doStats(outputFileName, closeFigures = True, stacks = True, hist = True, irThreshold = 8, minBinFactor = 5, intensityRatios = True,
        #        peakAvgs = True, analRep = True)

        print '\nData fitting complete'

    else:
        try:
            spectra, wavelengths, background, reference, summaryAttrs = mpf.retrieveData(summaryFile, startSpec, finishSpec)
            x, yData = mpf.prepareData(spectra, wavelengths, reference)
            initImg = mpf.plotInitStack(x, yData, imgName = 'Initial Stack', closeFigures = True)

            outputFile = mpf.createOutputFile('MultiPeakFitOutput')

            with h5py.File(outputFile, 'a') as f:
                mpf.fitAllSpectra(x, yData, f, startSpec, raiseExceptions = raiseExceptions,
                                  closeFigures = True, fukkit = True, simpleFit = True, summaryAttrs = summaryAttrs)

            print '\nData fitting complete'

        except Exception as e:
            print '\nData fitting failed because %s' % (e)

    plt.close('all')

    #unpa.updateOutputAttrs(summaryFile)

    absoluteEndTime = time.time()
    timeElapsed = absoluteEndTime - absoluteStartTime

    hours = int(timeElapsed / 3600)
    mins = int(np.round((timeElapsed % 3600)/60))
    secs = int(np.round(timeElapsed % 60))

    if hours > 0:
        print '\nM8 that took ages. %s hours %s min %s sec' % (hours, mins, secs)

    else:
        print '\nFinished in %s min %s sec' % (mins, secs)
