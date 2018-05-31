# -*- coding: utf-8 -*-
"""
First created on Thu Feb 01 13:21:40 2018

@author: Charlie Readman
"""
if __name__ == '__main__':
    print 'Importing modules...'

import h5py
import numpy as np
import os
import matplotlib.pyplot as plt
from scipy import sparse
import scipy.sparse.linalg as splu
from scipy.signal import butter, filtfilt
from lmfit.models import GaussianModel
import time
from PIL import Image
from random import randint
import scipy.optimize as spo

if __name__ == '__main__':
    absoluteStartTime = time.time()
    print '\tModules imported\n'
    print 'Initialising functions...'

'''OBJECTS'''

class DF_Spectrum(object):

    def __init__(self, intensities, fitParams, isNpom, isDouble, cmPeakPos, metadata):
        self.intensities = intensities #y data (1D array)
        self.fitParams = fitParams #parameters that describe the multiple gaussians that make up each spectrum (dictionary)
        self.isNpom = isNpom #Whether or not the spectrum describes an NPoM (bool)
        self.isDouble = isDouble #Whether or not the spectrum contains a double coupled mode (bool)
        self.cmPeakPos = cmPeakPos #What it says on the tin (float)
        metadataKeys = ['NPoM?',
                      'doublePeak?',
                      'weirdPeak?',
                      'transverseModePosition',
                      'transverseModeIntensity',
                      'rawTransverseModeIntensity',
                      'coupledModePosition',
                      'coupledModeIntensity',
                      'rawCoupledModeIntensity',
                      'intensityRatio',
                      'rawIntensityRatio',
                      'rawData',
                      'normalisedSpectrum',
                      'fullWavelengths',
                      'truncatedSpectrum',
                      'smoothedSpectrum',
                      'initialGuess',
                      'bestFit',
                      'residuals',
                      'finalComponents',
                      'finalParams',
                      'truncatedWavelengths',
                      'secondDerivative']

        if metadata == 'N/A':
            self.metadata = {key : 'N/A' for key in metadataKeys}

        else:
            self.metadata = metadata #All other relevant info (dictionary)

'''FUNCTIONS'''

def retrieveData(summaryFile, startSpec, finishSpec):

    '''Retrieves data from summary file'''

    try:
        summaryFile = h5py.File('%s.h5' % summaryFile, 'r')

    except:

        try:
            summaryFile = h5py.File('%s.hdf5' % summaryFile, 'r')

        except:
            print 'Summary file not found'
            return

    allScans = summaryFile['particleScanSummaries/']
    spectraLengths = []

    for scan in allScans:

        if len(allScans[scan]) != 0:
            spectraLengths.append(len(allScans[scan]['spectra']))

        else:
            spectraLengths.append(0)

    scanNumber = np.array(spectraLengths).argmax()

    if finishSpec == 0:
        spectra = summaryFile['particleScanSummaries/scan%s/spectra' % scanNumber][()][startSpec:]

    else:
        spectra = summaryFile['particleScanSummaries/scan%s/spectra' % scanNumber][()][startSpec:finishSpec]

    wavelengths = summaryFile['particleScanSummaries/scan%s/spectra' % scanNumber].attrs['wavelengths'][()]
    background = summaryFile['particleScanSummaries/scan%s/spectra' % scanNumber].attrs['background'][()]
    reference = summaryFile['particleScanSummaries/scan%s/spectra' % scanNumber].attrs['reference'][()]

    summaryFile.close()

    print 'Data retrieved from particleScanSummaries/scan%s\n' % scanNumber
    return spectra, wavelengths, background, reference

def findKey(inputDict, value):
    return next((k for k, v in inputDict.items() if v == value), None)

def removeNaNs(spectrum):
    '''Removes NaN values'''
    #Identifies NaN values and sets the corresponding data point as an average of the two either side
    #If multiple sequential NaN values are encountered a straight line is made between the two closest data points
    #Input = 1D array
    #Works like list.sort() rather than sorted(list), i.e. manipulates array directly rather than returning a new one
    '''A bit clunky; will rewrite at some point'''

    i = -1

    if not np.isfinite(spectrum[i]) == True:

        while not np.isfinite(spectrum[i]) == True:
            i -= 1

        for j in range(len(spectrum[i:])):
            spectrum[i+j] = spectrum[i]

    for i in range(len(spectrum)):

        if not np.isfinite(spectrum[i]) == True:

            if i == 0:
                j = i

                while not np.isfinite(spectrum[j]) == True:
                    j += 1

                for k in range(len(spectrum[i:j])):
                    spectrum[i+k] = spectrum[j]

            elif i != len(spectrum) - 1:
                j = i

                while not np.isfinite(spectrum[j]) == True:
                    j += 1

                start = spectrum[i-1]
                end = spectrum[j]
                diff = end - start

                for k in range(len(spectrum[i:j])):
                    spectrum[i+k] = float(start) + float(k)*float(diff)/(len(spectrum[i:j]))

def correctSpectrum(spectrum, reference):
    #Removes any NaNs from all spectra in list and divides each by a 1D array of the same length (designed for referencing)
    #spectra = list of arrays, 2D array with size (n, 1)
    #reference = 1D array

    for n in range(len(reference)):

        if reference[n] == 0.:
            reference[n] = np.nan

    removeNaNs(reference)
    return spectrum/reference

def printEnd():
    print '%sDONE' % ('\n' * randint(0, 12))

    print '%s%s%sv gud' % ('\t' * randint(0, 12), '\n' * randint(0, 5), ' ' * randint(0, 4))

    print '%s%ssuch python' % ('\n' * randint(0, 5), ' ' * randint(0, 55))
    print '%s%smany spectra' % ('\n' * randint(0, 5), ' ' * randint(10, 55))
    print '%s%smuch fitting' % ('\n' * randint(0, 5), ' ' * randint(8, 55))
    print '%s%swow' % ('\n' * randint(2, 5), ' ' * randint(5, 55))
    print '\n' * randint(0, 7)

def prepareData(spectra, wavelengths, reference):
    '''Removes NaN values from and references spectra'''
    #spectra = list of 1D arrays
    #wavelengths = 1D array or list
    #reference = 1D array or list

    prepStart = time.time()

    '''INITIAL FIT PARAMETERS'''

    print 'Preparing data...'

    removeNaNs(wavelengths)

    for spectrum in spectra:
        removeNaNs(spectrum)

    referencedSpectra = [correctSpectrum(spectrum, reference) for spectrum in spectra]

    prepEnd = time.time()
    prepTime = prepEnd - prepStart

    print '%s spectra cleared of NaNs and referenced in %s seconds\n' % (len(spectra), prepTime)

    return wavelengths, referencedSpectra

def createOutputFile(filename):

    '''Auto-increments new filename if file exists'''

    print 'Creating output file...'

    outputFile = '%s.h5' % filename

    if outputFile in os.listdir('.'):
        print '\n%s already exists' % outputFile
        n = 0
        outputFile = '%s_%s.h5' % (filename, n)

        while outputFile in os.listdir('.'):
            print '%s already exists' % outputFile
            n += 1
            outputFile = '%s_%s.h5' % (filename, n)

    print '\nOutput file %s created' % outputFile
    return outputFile

def truncateSpectrum(wavelengths, spectrum, startWl = 450, finishWl = 900):
    #Truncates spectrum within a certain wavelength range. Useful for removing high and low-end noise

    for n, wl in enumerate(wavelengths):

        if n == 0 and wl > startWl:
            startIndex = n

        if int(np.round(wl)) == int(np.round(startWl)):
            startIndex = n

        elif int(np.round(wl)) == int(np.round(finishWl)):
            finishIndex = n

        elif n == len(wavelengths) - 1 and wl < finishWl:
            finishIndex = n

    wavelengthsTrunc = np.array(wavelengths[startIndex:finishIndex])
    spectrumTrunc = np.array(spectrum[startIndex:finishIndex])
    return np.array([wavelengthsTrunc, spectrumTrunc])

def baselineAls(y, lambd, p, iterations = 10):
    '''Calculates baseline for data
    lambd ~ 10^n
    p ~10^(-m)'''

    L = y.size
    D = sparse.csc_matrix(np.diff(np.eye(L), 2))
    w = np.ones(L)
    for i in xrange(iterations):
        W = sparse.spdiags(w, 0, L, L)
        Z = W + lambd * D.dot(D.transpose())
        z = splu.spsolve(Z, w*y)
        w = p * (y > z) + (1-p) * (y < z)
    return z

def butterLowpassFiltFilt(data, cutoff = 1500, fs = 60000, order=5):
    '''Smoothes data without shifting it'''
    nyq = 0.5 * fs
    normalCutoff = cutoff / nyq
    b, a = butter(order, normalCutoff, btype='low', analog=False)
    yFiltered = filtfilt(b, a, data)
    return yFiltered

def detectMinima(y, negOnly = True, threshold = 0):
    '''Finds and returns list of minima in a data set'''
    ind = False

    ySign = np.sign(y + threshold)
    dy = np.zeros(len(y))
    dy[1:] = np.diff(y)

    if len(dy) > 1:
        dy[0] = dy[1]
        dy = np.sign(dy)
        d2y = np.zeros(len(y))
        d2y[1:] = np.diff(dy)
        d2y[0] = d2y[1]
        d2y = np.sign(d2y)

        if negOnly == True:
            '''Finds only minima that exist below zero'''
            ind = np.nonzero((-ySign + dy + d2y) == 3)
            ind = ind[0]
            ind = [int(i) for i in ind]

        elif negOnly == False:
            '''Finds all minima'''
            ind = np.nonzero((dy + d2y) == 2)
            ind = ind[0]
            ind = [int(i) for i in ind]

        return ind

def testIfNpom(x, y, lower = 0.1, upper = 2.5, NpomThreshold = 1.5):
    '''Filters out spectra that are obviously not from NPoMs'''

    isNpom = False #Guilty until proven innocent

    '''To be accepted as an NPoM, you must first pass four trials'''

    x = np.array(x)
    y = np.array(y)

    try:
        [xTrunc, yTrunc] = truncateSpectrum(x, y)
        [xUpper, yUpper] = truncateSpectrum(x, y, startWl = 900, finishWl = x.max())

    except Exception as e:
        print 'NPoM test failed because %s' % e
        return False

    '''Trial the first: do you have a reasonable signal?'''

    if np.sum(yTrunc) > lower and np.sum(yTrunc) < upper:
        #If sum of all intensities lies outside a given range, it's probably not an NPoM
        #Can adjust range to suit system

        '''Trial the second: do you slant in the correct direction?'''

        firstHalf = yTrunc[:int(len(yTrunc)/2)]
        secondHalf = yTrunc[int(len(yTrunc)/2):]

        if np.sum(firstHalf) < np.sum(secondHalf) * NpomThreshold:
            #NPoM spectra generally have greater total signal at longer wavelengths due to coupled mode

            '''Trial the third: are you more than just noise?'''

            if np.sum(yTrunc) > np.sum(yUpper) / NpomThreshold:
                #If the sum of the noise after 900 nm is greater than that of the spectrum itself, it's probably crap

                '''Trial the fourth: do you have more than one maximum?'''
                ySmooth = butterLowpassFiltFilt(y)
                minima = detectMinima(-ySmooth, negOnly = False)

                if len(minima) > 1:
                    #NPoM spectra usually have more than one distinct peak, separated by a minimum
                    isNpom = True

    return isNpom

def testIfWeirdPeak(x, y, factor = 1.3, plot = False):

    xy = truncateSpectrum(x, y, finishWl = 670)

    xTrunc = xy[0]
    yTrunc = xy[1]
    yTruncSmooth = butterLowpassFiltFilt(yTrunc)
    transHeight = yTruncSmooth[np.where(abs(xTrunc - 533) == abs(xTrunc - 533).min())[0][0]]
    maxHeight = yTruncSmooth.max()

    if maxHeight >= transHeight * factor:
        weird = True

    else:
        weird = False

    if plot == 'all' or plot == True:

        if weird == True:
            color = 'k'
        elif weird == False:
            color = 'g'

        plt.figure()
        plt.plot(x, y, color = color)
        plt.xlabel('Wavelength (nm)')
        plt.ylabel('Scattered Intensity')
        plt.title('Weird peak = %s' % weird)

    return weird

def takeDerivs(y, x):
    '''Numerically differentiates y wrt x twice and returns both derivatives'''
    #y, x = 1D array

    dy = np.diff(y)
    dx = np.diff(x)
    firstDerivative = dy/dx

    dDyDx = np.diff(firstDerivative)

    secondDerivative = dDyDx/dx[:-1]

    return firstDerivative, secondDerivative

def removeBaseline(x, y, cutoff = 1500, fs = 60000, lambd = 10**6.7, p = 0.003, returnTrunc = False):
    '''Specifically designed for NPoM spectra'''

    xRaw = x
    yRaw = y

    xTrunc1, yTrunc1 = truncateSpectrum(xRaw, yRaw, startWl = 450, finishWl = 1000) #Truncate to remove low-end noise
    yTrunc1Smooth = butterLowpassFiltFilt(yTrunc1, cutoff, fs) #Smooth truncated data
    yTrunc1Minima = detectMinima(yTrunc1Smooth, negOnly = False) #Finds indices of minima in smoothed data

    initMinIndex = yTrunc1Minima[0] #Index of first minimum in truncated spectrum
    initWl = xTrunc1[initMinIndex] #Wavelength corresponding to this minimum
    initMinIndex = np.where(abs(xRaw - initWl) == abs(xRaw - initWl).min())[0][0] #Corresponding index in full spectrum

    xTrunc2, yTrunc2 = truncateSpectrum(xRaw, yRaw, startWl = 850, finishWl = 1100) #Truncate to only probe data after CM peak
    yTrunc2Smooth = butterLowpassFiltFilt(yTrunc2, cutoff, fs) #Smooth truncated data
    yTrunc2Minima = detectMinima(yTrunc2Smooth, negOnly = False) #Finds indices of minima in smoothed data

    finalMinIndex = yTrunc2Minima[0] #Index of first minimum after CM peak
    finalWl = xTrunc2[finalMinIndex] #Wavelength corresponding to this minimum
    finalMinIndex = np.where(abs(xRaw - finalWl) == abs(xRaw - finalWl).min())[0][0] #Corresponding index in full spectrum


    '''These two minima are taken as the start and end points of the "real" spectrum'''

    xTrunc3, yTrunc3 = truncateSpectrum(xRaw, yRaw, startWl = initWl, finishWl = finalWl) #Truncate spectrum between two minima
    yTrunc3Baseline = baselineAls(yTrunc3, lambd, p) #Take baseline of this data
    yTrunc3Subtracted = yTrunc3 - yTrunc3Baseline

    '''Baseline extrapolated with straight line at each end so it can be subtracted from the raw spectrum'''

    yBaseline1 = [yTrunc3Baseline[0]] * initMinIndex
    yBaseline2 = [i for i in yTrunc3Baseline]
    yBaseline3 = [yTrunc3Baseline[-1]] * (len(yRaw) - finalMinIndex)

    yFullBaseline = yBaseline1 + yBaseline2 + yBaseline3

    '''Due to rounding errors when truncating, extrapolated baseline may have different length to raw data '''

    lenDiff = len(yRaw) - len(yFullBaseline) #Calculate this difference

    if lenDiff < 0:
        yFullBaseline = yFullBaseline[:lenDiff] #Remove data point(s) from end if necessary

    elif lenDiff > 0:

        for j in range(lenDiff):
            yFullBaseline.append(yTrunc3Baseline[-1]) #Add data point(s) to end if necessary

    yFullBaseline = np.array(yFullBaseline)
    ySubtracted = yRaw - yFullBaseline #Subtract baseline from raw data

    '''Baseline calculation isn't perfect, so this subtraction sometimes leads to unrealistically negative
       y-values'''
    '''Data truncated and smoothed once more, and minimum subtracted from data'''

    subtractedTrunc = truncateSpectrum(xRaw, ySubtracted, startWl = 450, finishWl = 850)
    ySubTrunc = subtractedTrunc[1]
    ySubTruncSmooth = butterLowpassFiltFilt(ySubTrunc, cutoff, fs)

    ySubtracted -= ySubTruncSmooth.min()

    if returnTrunc == True:
        return ySubtracted, xTrunc3, yTrunc3Subtracted

    else:
        return ySubtracted

def normToTrans(x, y, cutoff = 1500, fs = 60000, lambd = 10**6.7, p = 0.003, plot = False,
                monitorProgress = False, baseline = True, returnPeakpos = True, fukkit = False):
    '''Specifically for use with NPoM spectra'''
    '''Finds the first shoulder in the spectrum after 500 nm and normalises the spectrum to the corresponding
       intensity'''

    xRaw = x
    yRaw = y

    if baseline == True:
        ySubtracted, xTrunc, yTrunc = removeBaseline(xRaw, yRaw, lambd = lambd, p = p, returnTrunc = True)#Baseline subtraction if requested

    else:
        xTrunc, yTrunc = truncateSpectrum(xRaw, yRaw, startWl = 450, finishWl = 900)#Otherwise just truncated to standard range

    yTruncSmooth = butterLowpassFiltFilt(yTrunc, cutoff = cutoff, fs = fs)#Smooth data

    if fukkit == False:
        firstDeriv, secondDeriv = takeDerivs(yTruncSmooth, xTrunc)#Take second derivative
        peakIndices = detectMinima(secondDeriv, negOnly = False)#Detect minima in second derivative to find spectral peaks/shoulders

        xPeaks = [xTrunc[index] for index in peakIndices]#Peak positions

        for n, peakWl in enumerate(xPeaks):

            if peakWl > 500:
                transIndex = peakIndices[n]#Finds index of first peak after x=500 - most likely the transverse mode
                break

        transWl = xTrunc[transIndex]

    elif fukkit == True:
        transWl = 533
        transIndex = np.where(abs(xTrunc - transWl) == abs(xTrunc - transWl).min())[0][0]

    if baseline == False: #Sets the spectral minimum to zero
        ySubtracted = yRaw - min(yTruncSmooth)
        yTrunc = yTrunc - min(yTruncSmooth)

    transHeight = yTruncSmooth[transIndex]

    yNorm = ySubtracted / transHeight
    yTruncNorm = yTrunc / transHeight #Normalisation

    if returnPeakpos == True:
        return yNorm, transWl, xTrunc, yTruncNorm#Returns transverse peak position along with normalised data, if requested

    else:
        return yNorm, xTrunc, yTruncNorm

def normTo533(x, yRaw, ySmooth = False):

    if ySmooth == False:
        ySmooth = butterLowpassFiltFilt(yRaw)

    ind533 = np.where(abs(x - 533) == abs(x - 533).min())[0][0]
    transHeight = ySmooth[ind533]

    yRawNorm = yRaw / transHeight
    ySmoothNorm = ySmooth / transHeight

    return yRawNorm, ySmoothNorm

def multiPeakFind(x, y, cutoff = 1500, fs = 60000, detectionThreshold = 0, returnAll = True,
                  monitorProgress = False):

        '''Finds spectral peaks (including shoulders) by smoothing and then finding minima in the
           second derivative'''

        peakFindMetadata = {}

        ySmooth = butterLowpassFiltFilt(y, cutoff = cutoff, fs = fs)
        peakFindMetadata['smoothedSpectrum'] = ySmooth

        if monitorProgress == True:
            print '\nData smoothed'

        '''Differentiation'''

        firstDerivative, secondDerivative = takeDerivs(ySmooth, x)
        peakFindMetadata['secondDerivative'] = secondDerivative

        if monitorProgress == True:
            print 'Derivatives taken'

        '''Peak detection in 2nd derivative'''

        peakIndices = detectMinima(secondDerivative, negOnly = True,
                                   threshold = secondDerivative.max()*detectionThreshold)

        if monitorProgress == True:
            print '%s peaks detected' % (len(peakIndices))

        if returnAll == True:
            return ySmooth, peakIndices, peakFindMetadata

def multiPeakFit(x, y, indices, ySmooth = np.array([]), cutoff = 1500, fs = 60000, constrainPeakpos = False,
                 returnAll = False, monitorProgress = True):
    '''Performs the actual fitting (given a list of peak indices) using Python's lmfit module'''
    '''You can generate indices using multiPeakFind or input them manually'''
    #x, y = 1D arrays of same length
    #indices = 1D array or list of integers, to be used as indices of x and y
    #ySmooth (optional). Include this to save time, otherwise the function will smooth the y data for you
    #setting constrainPeakpos = True forces peaks to stay between the indices either side when fitting
    #e.g. for indices of [7, 10, 14], the final centre position of the second peak (initial index = 10) must be between index 7 and 14

    fitStart = time.time()
    peakFitMetadata = {}

    if ySmooth.size == 0:
        ySmooth = butterLowpassFiltFilt(y, cutoff = cutoff, fs = fs) #smoothes data

    if monitorProgress == True:
        print '\n%s peaks about to be fitted' % (len(indices))

    modelElements = [] #Empty list to be populated with components of model
    component = GaussianModel(prefix = 'g0_')
    component.set_param_hint('amplitude', min = 0)
    component.set_param_hint('center', min = x.min(), max = 850) #Above 850 is v. noisy, so NO PEAKS ALLOWED
    modelElements.append(component) #One gaussian added for starters

    if len(indices) == 1: #If only one peak detected
        pars = modelElements[0].guess(ySmooth, x = x) #initial parameter guess based on entire spectrum
        gaussMod = modelElements[0] #total model set equal to gaussian component

    else: #If more than one peak detected
        #Sets data range for first peak initial guess
        peakEnd = int((indices[0] + indices[1])/2) #Midpoint between 1st and 2nd peak taken as end of data range for 1st peak
        pars = modelElements[0].guess(ySmooth[:peakEnd], x[:peakEnd]) #initial guess performed within this range
        gaussMod = modelElements[0] #total model initially set equal to first gaussian component

        if constrainPeakpos == True:
            modelElements[0].set_param_hint('center', max = x[peakEnd])

        for i in range(len(indices))[1:]:
            component = GaussianModel(prefix = 'g%s_' % (i))
            component.set_param_hint('amplitude', min = 0)
            component.set_param_hint('center', min = x.min(), max = 850) #Above 850 is v. noisy, so NO PEAKS ALLOWED
            modelElements.append(component) #Components list populated with appropriate number of gaussians to be calculated

            if i > 0 and i != len(indices) - 1: #Sets initial guess data range for subsequent peaks
                peakStart = int((indices[i - 1] + indices[i])/2)
                peakEnd = int((indices[i] + indices[i + 1])/2)

            elif i > 0 and i == len(indices) - 1: #Sets initial guess data range for final peak
                peakStart = int((indices[i - 1] + indices[i])/2)
                peakEnd = len(x)

            if constrainPeakpos == True:
                modelElements[i].set_param_hint('center', min = x[peakStart + 1], max = x[peakEnd - 1])

            pars.update(modelElements[i].guess(ySmooth[peakStart:peakEnd], x[peakStart:peakEnd]))#List of parameters updated with initial guesses for each peak
            gaussMod += modelElements[i]#Total model updated to include each subsequent peak

    if monitorProgress == True:
        print 'Initial guesses made for %s gaussians' % (len(indices))

    init = gaussMod.eval(pars, x=x)#Function formed from initial guesses

    peakFitMetadata['initialGuess'] = init

    yFloat16 = np.float16(y) #Reduces the number of decimal places in data to speed up fitting
    xFloat16 = np.float16(x)

    out = gaussMod.fit(yFloat16, pars, x=xFloat16) #Performs the fit, based on initial guesses

    #out = gaussMod.fit(ySmooth, pars, x=x) #Can fit to smoothed data instead if you like
    comps = out.eval_components(x=xFloat16)
    peakFitMetadata['finalComponents'] = comps

    fitEnd = time.time()
    fitTime = fitEnd - fitStart

    if monitorProgress == 'time' or monitorProgress == True:
        print '\n\nFit performed in %s seconds' % fitTime

    if monitorProgress == True:
        print '%s components' % len(comps)
        print '\nFit performed'

    finalParams = {}
    componentParamNames = ['sigma', 'center', 'amplitude', 'fwhm', 'height', 'wavelengths']

    for prefix in [model.prefix for model in modelElements]:
        finalParams[prefix[:-1]] = {}

        for name in componentParamNames:

            if name != 'wavelengths':
                finalParams[prefix[:-1]][name] = out.params[prefix + name].value

            elif name == 'wavelengths':
                finalParams[prefix[:-1]][name] = x

    peakFitMetadata['lmfitOutput'] = out
    peakFitMetadata['bestFit'] = out.best_fit
    peakFitMetadata['finalParams'] = finalParams
    peakFitMetadata['residuals'] = out.residual

    if returnAll == True:
        return out, peakFitMetadata

    else:
        return out

def gaussian(x, height, center, fwhm):
    a = height
    b = center
    c = fwhm

    N = 4*np.log(2)*(x - b)**2
    D = c**2
    F = -(N / D)
    E = np.exp(F)
    y = a*E

    return y

def getFWHM(x, y, fwhmFactor = 1.5, smooth = False):
    '''Finds FWHM of largest peak in a given dataset'''
    '''Also returns xy coords of peak'''

    if smooth == True:
        y = butterLowpassFiltFilt(y)

    yMax = y.max()
    halfMax = yMax/2
    maxdex = np.where(abs(y - yMax) == abs(y - yMax).min())[0][0]
    xMax = x[maxdex]

    halfDex1 = np.where(abs(y[:maxdex][::-1] - halfMax) == abs(y[:maxdex][::-1] - halfMax).min())[0][0]
    halfDex2 = np.where(abs(y[maxdex:] - halfMax) == abs(y[maxdex:] - halfMax).min())[0][0]

    xHalf1 = x[:maxdex][::-1][halfDex1]
    xHalf2 = x[maxdex:][halfDex2]

    hwhm1 = abs(xMax - xHalf1)
    hwhm2 = abs(xMax - xHalf2)
    hwhms = [hwhm1, hwhm2]

    hwhmMax, hwhmMin = max(hwhms), min(hwhms)

    if hwhmMax > hwhmMin*fwhmFactor:
        fwhm = hwhmMin * 2

    else:
        fwhm = sum(hwhms)

    return fwhm, xMax, yMax

def findMainPeaks(x, y, fwhmFactor = 1.1, plot = False, midpoint = 680, weirdPeak = True):
    peakFindMetadata = {}

    xy = truncateSpectrum(x, y)
    xTrunc = xy[0]
    yTrunc = xy[1]
    ySmooth = butterLowpassFiltFilt(yTrunc)

    mIndices = detectMinima(ySmooth, negOnly = False)
    xMins = np.array([xTrunc[mIndex] for mIndex in mIndices])
    midMin = xMins[np.where(abs(xMins - midpoint) == abs(xMins - midpoint).min())[0][0]]

    xy1 = truncateSpectrum(xTrunc, ySmooth, startWl = 450, finishWl = midMin)
    xy2 = truncateSpectrum(xTrunc, ySmooth, startWl = midMin, finishWl = 900)

    if weirdPeak == True:
        x1 = xy1[0]
        y1 = xy1[1]
        fwhm, xMax, yMax = getFWHM(x1, y1, fwhmFactor = fwhmFactor)

        peakFindMetadata['weirdPeakFwhm'] = fwhm
        peakFindMetadata['weirdPeakIntensity'] = yMax
        peakFindMetadata['weirdPeakPosition'] = xMax
        weirdGauss = [gaussian(i, yMax, xMax, fwhm) for i in x]

    else:
        peakFindMetadata['weirdPeakFwhm'] = 'N/A'
        peakFindMetadata['weirdPeakIntensity'] = 'N/A'
        peakFindMetadata['weirdPeakPosition'] = 'N/A'
        weirdGauss = 'N/A'

    x2 = xy2[0]
    y2 = xy2[1]
    fwhm, xMax, yMax = getFWHM(x2, y2, fwhmFactor = fwhmFactor)

    peakFindMetadata['coupledModeFwhm'] = fwhm
    peakFindMetadata['coupledModeIntensity'] = yMax
    peakFindMetadata['coupledModePosition'] = xMax
    cmGauss = [gaussian(i, yMax, xMax, fwhm) for i in x]

    if plot == True or plot == 'all':
        weirdHeight = peakFindMetadata['weirdPeakIntensity']
        weirdWl = peakFindMetadata['weirdPeakPosition']
        weirdFwhm = peakFindMetadata['weirdPeakFwhm']

        cmHeight = peakFindMetadata['coupledModeIntensity']
        cmWl = peakFindMetadata['coupledModePosition']
        cmFwhm = peakFindMetadata['coupledModeFwhm']

        weirdFwhmHorizX = np.linspace(weirdWl - weirdFwhm/2, weirdWl + weirdFwhm/2, 2)
        weirdFwhmHorizY = np.array([weirdHeight/2] * 2)
        cmFwhmHorizX = np.linspace(cmWl - cmFwhm/2, cmWl + cmFwhm/2, 2)
        cmFwhmHorizY = np.array([cmHeight/2] * 2)

        plt.plot(x, y, 'purple', lw = 0.3, label = 'Raw')
        plt.xlabel('Wavelength (nm)', fontsize = 14)
        plt.ylabel('Intensity', fontsize = 14)
        plt.plot(xTrunc, ySmooth, 'g', label = 'Smoothed')
        plt.plot(weirdFwhmHorizX, weirdFwhmHorizY, 'k', lw = 0.4)
        plt.plot(cmFwhmHorizX, cmFwhmHorizY, 'k', lw = 0.4)
        plt.plot(x, weirdGauss, 'k', lw = 0.5)
        plt.plot(x, cmGauss, 'k', lw = 0.5)
        plt.xlim(450, 900)
        plt.ylim(0, ySmooth.max()*1.1)
        plt.show()

    return peakFindMetadata, weirdGauss, cmGauss

def testIfDouble(x, y, doublesThreshold = 2, midpoint = 680, plot = False):
    isDouble = False

    xy = truncateSpectrum(x, y)
    xTrunc = xy[0]
    yTrunc = xy[1]
    ySmooth = butterLowpassFiltFilt(yTrunc)

    mIndices = detectMinima(ySmooth, negOnly = False)
    xMins = np.array([xTrunc[mIndex] for mIndex in mIndices])
    midMin = xMins[np.where(abs(xMins - midpoint) == abs(xMins - midpoint).min())[0][0]]

    xy2 = truncateSpectrum(xTrunc, ySmooth, startWl = midMin, finishWl = 900)

    x2 = xy2[0]
    y2 = xy2[1]

    maximaIndices = detectMinima(-y2, negOnly = False)

    xMaxes = x2[maximaIndices]
    yMaxes = y2[maximaIndices]
    yMax = max(yMaxes)

    xMaxes4RealzThisTime = []
    yMaxes4RealzThisTime = []

    if len(yMaxes > 0):

        for nn, maximum in enumerate(yMaxes):

            if maximum > yMax / doublesThreshold:
                yMaxes4RealzThisTime.append(maximum)
                xMaxes4RealzThisTime.append(xMaxes[nn])

    xMaxes = xMaxes4RealzThisTime
    yMaxes = yMaxes4RealzThisTime

    if len(yMaxes) > 1:
        isDouble = True

    if plot == True or plot == 'all':

        if len(yMaxes) > 1:
            title = 'Double Peak'

        elif len(yMaxes) == 1:
            title = 'Single Peak'

        elif len(yMaxes) < 1:
            title = 'No Peak'

        plt.figure(figsize = (8, 6))
        plt.plot(x, y, 'purple', lw = 0.3, label = 'Raw')
        plt.xlabel('Wavelength (nm)', fontsize = 14)
        plt.ylabel('Intensity', fontsize = 14)
        plt.plot(xTrunc, ySmooth, 'g', label = 'Smoothed')
        plt.plot(x2, y2,'k', label = 'Truncated')
        #plt.plot(xMins, yMins, 'ko', label = 'Minima')
        #plt.plot(xMaxes, yMaxes, 'go', label = 'Maxima in CM Region')
        plt.legend(loc = 0, ncol = 3, fontsize = 10)
        plt.ylim(0, ySmooth.max()*1.23)
        plt.xlim(450, 900)
        plt.title(title, fontsize = 16)
        plt.show()

    return isDouble

def findTransAndCoupledMode(x, xRaw, yRaw, ySmooth, fitParams, transGuess = 533, transRange = [500, 550],
                            cmMin = 650, plot = False, fukkit = False):

    '''Finds CM and transverse peak heights/positions using fit data (dictionary) and smoothed spectrum'''
    '''Returns dictionary of relevant data'''
    tcMetadata = {}
    yRawSmooth = butterLowpassFiltFilt(yRaw)
    ySmoothTrunc = truncateSpectrum(x, ySmooth, startWl = 600, finishWl = 850) #Truncates smoothed spectrum to neighbourhood of the coupled mode
    yRawSmoothTrunc = truncateSpectrum(xRaw, yRawSmooth, startWl = 600, finishWl = 850)
    cmHeight = ySmoothTrunc[1].max() #maximum value is likely the coupled mode height
    cmHeightRaw = yRawSmoothTrunc[1].max()
    cmPeakPos = ySmoothTrunc[0][ySmoothTrunc[1].argmax()] #coupled mode wavelength assigned to this

    if int(cmPeakPos) < cmMin:
        '''If whatever comes before ~650 nm is much larger than the coupled mode, then the start of the
           truncated region may be assigned as the coupled mode'''
        '''If this is the case, the minimum after this is found, and the truncation performed again from
           this point'''
        try:
            newMinimum = detectMinima(ySmoothTrunc, negOnly = False)[0]
            newMinWl = ySmoothTrunc[0][newMinimum]
        except:
            newMinWl = cmMin

        ySmoothTrunc = truncateSpectrum(x, ySmooth, startWl = newMinWl, finishWl = 850)
        yRawSmoothTrunc = truncateSpectrum(xRaw, yRawSmooth, startWl = newMinWl, finishWl = 850)
        cmHeight = ySmoothTrunc[1].max()
        cmHeightRaw = yRawSmoothTrunc[1].max()
        cmPeakPos = ySmoothTrunc[0][ySmoothTrunc[1].argmax()]

    tcMetadata['coupledModePosition'] = cmPeakPos
    tcMetadata['coupledModeIntensity'] = cmHeight
    tcMetadata['rawCoupledModeIntensity'] = cmHeightRaw

    if fukkit == True:
        transPeakPos = 533

    else:

        for prefix in sorted(fitParams.keys(), key = lambda prefix: int(prefix[1:])):
            '''Identifies the transverse mode among the component gaussian functions'''
            #prefix in the form 'gn'
            comp = fitParams[prefix]#gives dictionary containing parameters of gaussian component

            if transRange[0] < comp['center'] < transRange[1]:#Only wavelengths between 500 and 550 nm are considered
                transPeakPos = comp['center']
                break #Stops after first peak between 500 and 550

            elif comp['center'] > 550:

                transPeakPos = transGuess #If no peaks are detected, initial transverse mode guess (533 nm unless specified otherwise) is used as the final value
                break

    tcMetadata['transverseModePosition'] = transPeakPos
    transIndex = np.where(abs(x - transPeakPos) == abs(x - transPeakPos).min())[0][0]
    transIndexRaw = np.where(abs(xRaw - transPeakPos) == abs(xRaw - transPeakPos).min())[0][0]
    transHeight = ySmooth[transIndex]#Takes height of smoothed spectrum at transverse peak position
    transHeightRaw = yRawSmooth[transIndexRaw]
    tcMetadata['transverseModeIntensity'] = transHeight
    tcMetadata['rawTransverseModeIntensity'] = transHeightRaw

    intensityRatio = cmHeight/transHeight
    intensityRatioRaw = cmHeightRaw/transHeightRaw
    tcMetadata['intensityRatio'] = intensityRatio
    tcMetadata['rawIntensityRatio'] = intensityRatioRaw

    return tcMetadata

def fitNpomSpectrum(x, y, cutoff = 1500, fs = 60000, lambd = 10**6.7, baselineP = 0.003,
                    detectionThreshold = 0, doublesThreshold = 0.5, doublesDist = 0,
                    constrainPeakpos = False, printReport = False, plot = False, monitorProgress = False, fukkit = False, simpleFit = True):

    yRaw = np.array(y)
    xRaw = np.array(x)

    allMetadataKeys = ['NPoM?',
                      'weirdPeak?',
                      'weirdPeakIntensity',
                      'weirdPeakPosition',
                      'weirdPeakFwhm',
                      'rawWeirdPeakIntensity',
                      'doublePeak?',
                      'transverseModePosition',
                      'transverseModeIntensity',
                      'rawTransverseModeIntensity',
                      'coupledModePosition',
                      'coupledModeIntensity',
                      'coupledModeFwhm',
                      'rawCoupledModeIntensity',
                      'intensityRatio',
                      'rawIntensityRatio',
                      'rawData',
                      'normalisedSpectrum',
                      'fullWavelengths',
                      'truncatedSpectrum',
                      'smoothedSpectrum',
                      'initialGuess',
                      'bestFit',
                      'residuals',
                      'finalComponents',
                      'finalParams',
                      'truncatedWavelengths',
                      'secondDerivative']

    metadata = {key : 'N/A' for key in allMetadataKeys}
    metadata['rawData'] = yRaw
    metadata['fullWavelengths'] = xRaw

    '''Testing if NPoM'''

    isNpom = testIfNpom(xRaw, yRaw)
    metadata['NPoM?'] = isNpom

    if plot == 'raw' or plot == 'all':
        plt.figure(figsize = (10,7))
        yMax = yRaw[67:661].max()
        yLimFrac = yMax/10
        plt.ylim(-yLimFrac, yMax + yLimFrac)

        if isNpom == True:
            plt.plot(xRaw, yRaw, 'g', label = 'Raw Data')

        else:
            plt.plot(xRaw, yRaw, 'r', label = 'Raw Data')

        plt.xlim(xRaw.min(), xRaw.max())
        plt.xlabel('Wavelength (nm)')
        plt.ylabel('Scattering Intensity')
        plt.title('Raw Data\nNPoM = %s' % isNpom)
        plt.show()

    if monitorProgress == True:
        print 'NPoM:', isNpom

    if isNpom == True:

        weird = testIfWeirdPeak(x, y, factor = 1.3)
        metadata['weirdPeak?'] = weird

        yRawNorm, transShoulderPeakPos, xTrunc, yTrunc = normToTrans(x, y, cutoff = cutoff, fs = fs,
                                                                         lambd = lambd, p = baselineP,
                                                                         plot = False, monitorProgress = False,
                                                                         baseline = True, fukkit = fukkit)

        metadata['normalisedSpectrum'] = yRawNorm
        metadata['transverseModePosition'] = transShoulderPeakPos

        xTrunc, yTrunc = truncateSpectrum(xTrunc, yTrunc, startWl = xTrunc[0], finishWl = 850)
        metadata['truncatedSpectrum'] = yTrunc
        metadata['truncatedWavelengths'] = xTrunc

        if monitorProgress == True:
            print '\nData baseline subtracted and normalised'

        if plot == 'all':
            plt.figure(figsize = (10,7))
            yMax = yRawNorm[67:661].max()
            yLimFrac = yMax/10
            plt.ylim(-0.02, yMax + yLimFrac)
            plt.plot(xRaw, yRawNorm, 'purple')
            plt.xlim(xRaw.min(), xRaw.max())
            plt.xlabel('Wavelength (nm)')
            plt.ylabel('Scattering Intensity')
            plt.title('Baselined/Normalised Data')
            plt.show()

        if simpleFit == False:

            ySmooth, indices, peakFindMetadata = multiPeakFind(xTrunc, yTrunc, cutoff = 1500, fs = 60000,
                                                                detectionThreshold = 0, returnAll = True,
                                                                monitorProgress = False)
            metadata.update(peakFindMetadata)

            '''Reassignment of x and y below is v. important'''

            y = yTrunc
            x = xTrunc

            if len(indices) != 0:
                out, peakFitMetadata = multiPeakFit(x, y, indices, ySmooth = ySmooth, cutoff = 1500, fs = 60000,
                                                    returnAll = True, monitorProgress = monitorProgress,
                                                    constrainPeakpos = constrainPeakpos)
                metadata.update(peakFitMetadata)

                isDouble = testIfDouble(x, y, doublesThreshold = 2, midpoint = 680, plot = plot)
                metadata['doublePeak?'] = isDouble

                if isDouble == False and weird == True:
                    simplePeakFindMetadata, weirdGauss, cmGauss = findMainPeaks(x, y, fwhmFactor = 1.1, plot = False, midpoint = 680, weirdPeak = True)
                    metadata.update(simplePeakFindMetadata)

                if monitorProgress == True:
                    print 'Fitting complete'

                if printReport == True:
                    print 'Fit report:\n'
                    print out.fit_report()

                if plot == 'basic' or plot == 'both':
                    plt.figure(figsize = (10,7))
                    plt.plot(xRaw, yRawNorm, label = 'raw')
                    plt.plot(x, out.best_fit, 'r-', label = 'fit')
                    plt.legend(loc = 0)
                    plt.xlabel('Wavelength (nm)')
                    plt.tick_params(axis = 'y', labelleft = 'off')
                    plt.ylabel('Intensity')
                    plt.xlim(450, 1050)
                    plt.show()

                elif plot == 'full' or plot == 'all':

                    plt.figure(figsize = (10,7))

                    if monitorProgress == True:

                        if isDouble == True:
                            plt.title('Double Peak')

                        elif isDouble == False:
                            plt.title('Single Peak')

                    plt.plot(xRaw, yRawNorm, label = 'raw', linewidth = 0.7)
                    plt.plot(x, ySmooth, label = 'smoothed', linewidth = 0.5)
                    plt.plot(x, metadata['initialGuess'], 'k-', label = 'initial guess', linewidth = 0.3)

                    for i in range(len(indices)):
                        plt.plot(x, metadata['finalComponents']['g%s_' % (i)], '--', label = 'Component %s' % (i),
                                 linewidth = 0.3)

                    plt.plot(x, out.best_fit, 'r-', label = 'fit')
                    plt.legend(loc = 0, ncol = 2, fontsize = 9)
                    plt.xlabel('Wavelength (nm)')
                    #plt.tick_params(axis = 'y', labelleft = 'off')
                    plt.ylabel('Intensity')
                    limFrac = ySmooth.max()/10
                    plt.ylim(-limFrac/2, ySmooth.max() + limFrac)
                    plt.xlim(450, 900)
                    plt.yticks([])
                    plt.show()

                    plt.figure(figsize = (10, 4))
                    plt.title('Residuals')
                    plt.plot(x, out.residual)
                    plt.xlabel('Wavelength (nm)')
                    plt.ylabel('Residuals')
                    plt.yticks([])
                    plt.xlim(450, 900)
                    plt.show()

                #if isDouble == False:

                tcMetadata = findTransAndCoupledMode(x, xRaw, yRaw, ySmooth, metadata['finalParams'],
                                                     transGuess = transShoulderPeakPos, plot = plot, fukkit = fukkit)
                metadata.update(tcMetadata)
                transHeight = metadata['transverseModeIntensity']

                ySmooth /= transHeight
                yTrunc /= transHeight
                yRawNorm /= transHeight

                metadata['smoothedSpectrum'] = ySmooth
                metadata['truncatedSpectrum'] = yTrunc
                metadata['normalisedSpectrum'] = yRawNorm

                if plot == 'all':
                    limFrac = ySmooth.max()/10

                    plt.plot(xRaw, yRawNorm, lw = 0.5)
                    plt.plot(x, y)
                    plt.plot(x, ySmooth)
                    plt.plot(x, [0] * len(x), '--')
                    plt.plot([metadata['transverseModePosition']] * 10, np.linspace(transHeight,
                             metadata['coupledModeIntensity'], 10), 'k--')
                    plt.plot(x, [metadata['coupledModePosition']] * len(x))
                    plt.plot(x, [transHeight] * len(x))
                    plt.title('Intensity Ratio: %s' % (metadata['intensityRatio']))
                    plt.xlabel('Wavelength(nm)')
                    plt.ylabel('Intensity')
                    plt.ylim(-limFrac/2, ySmooth.max() + limFrac)
                    plt.xlim(450, 900)
                    plt.show()

            else:
                metadata['NPoM?'] = False

                if monitorProgress == True:
                    print 'Not a NPoM'

                metadata['NPoM?'] = isNpom
                return DF_Spectrum(y, 'N/A', isNpom, 'N/A', 'N/A', metadata)

        elif simpleFit == True:

            isDouble = testIfDouble(x, y, doublesThreshold = 2, midpoint = 680, plot = plot)
            metadata['doublePeak?'] = isDouble

            if weird == True:
                simplePeakFindMetadata, weirdGauss, cmGauss = findMainPeaks(x, y, fwhmFactor = 1.1, plot = False, midpoint = 680, weirdPeak = True)
                metadata['rawCoupledModeIntensity'] = simplePeakFindMetadata['coupledModeIntensity']
                metadata['rawWeirdPeakIntensity'] = simplePeakFindMetadata['weirdPeakIntensity']

                simplePeakFindMetadata, weirdGauss, cmGauss = findMainPeaks(x, yRawNorm, fwhmFactor = 1.1, plot = False, midpoint = 680,
                                                                            weirdPeak = True)
                metadata.update(simplePeakFindMetadata)

            elif weird == False:
                simplePeakFindMetadata, weirdGauss, cmGauss = findMainPeaks(x, y, fwhmFactor = 1.1, plot = False, midpoint = 680, weirdPeak = False)
                metadata['rawCoupledModeIntensity'] = simplePeakFindMetadata['coupledModeIntensity']

                simplePeakFindMetadata, weirdGauss, cmGauss = findMainPeaks(x, yRawNorm, fwhmFactor = 1.1, plot = False, midpoint = 680,
                                                                            weirdPeak = True)
                metadata.update(simplePeakFindMetadata)

            if isDouble == True:
                metadata['coupledModeFwhm'] = 'N/A'

            transWl = 533
            transIndex = np.where(abs(xTrunc - transWl) == abs(xTrunc - transWl).min())[0][0]
            transIndexRaw = np.where(abs(xRaw - transWl) == abs(xRaw - transWl).min())[0][0]

            ySmooth = butterLowpassFiltFilt(yTrunc)
            yRawSmooth = butterLowpassFiltFilt(yRaw)
            transHeight = ySmooth[transIndex]
            transHeightRaw = yRawSmooth[transIndexRaw]

            ySmooth /= transHeight
            yTrunc /= transHeight
            yRawNorm /= transHeight

            intensityRatio = metadata['coupledModeIntensity'] / transHeight
            rawIntensityRatio = metadata['rawCoupledModeIntensity'] / transHeightRaw

            metadata['smoothedSpectrum'] = ySmooth
            metadata['truncatedSpectrum'] = yTrunc
            metadata['normalisedSpectrum'] = yRawNorm
            metadata['transverseModeIntensity'] = transHeight
            metadata['rawTransverseModeIntensity'] = transHeightRaw
            metadata['intensityRatio'] = intensityRatio
            metadata['rawIntensityRatio'] = rawIntensityRatio

    else:

        if monitorProgress == True:
            print 'Not a NPoM'

        metadata['NPoM?'] = isNpom

    return metadata

def reduceNoise(y, factor = 10):
    ySmooth = butterLowpassFiltFilt(y)
    yNoise = y - ySmooth
    yNoise /= factor
    y = ySmooth + yNoise
    return y

def plotHistogram(outputFile, histName = 'Histogram', startWl = 450, endWl = 900, binNumber = 80, plot = True,
                  minBinFactor = 5, closeFigures = False, which = 'all'):

    print '\nCombining spectra and plotting histogram...'
    print '\tFilter: %s' % which

    if which == 'all':
        spectra = outputFile['Fitted spectra']

    elif which == 'doubles only':
        spectra = [spectrum for spectrum in outputFile['Fitted spectra']
                   if outputFile['Fitted spectra/%s' % spectrum].attrs['Double Peak?'] == True]

    elif which == 'no doubles':
        spectra = [spectrum for spectrum in outputFile['Fitted spectra']
                   if outputFile['Fitted spectra/%s' % spectrum].attrs['Double Peak?'] == False]

    elif which == 'weird only':
        spectra = [spectrum for spectrum in outputFile['Fitted spectra']
                   if outputFile['Fitted spectra/%s' % spectrum].attrs['Weird Peak?'] == True]

    elif which == 'no weird':
        spectra = [spectrum for spectrum in outputFile['Fitted spectra']
                   if outputFile['Fitted spectra/%s' % spectrum].attrs['Weird Peak?'] == False]

    elif which == 'filtered':
        spectra = [spectrum for spectrum in outputFile['Fitted spectra']
                   if outputFile['Fitted spectra/%s' % spectrum].attrs['Weird Peak?'] == False
                   and outputFile['Fitted spectra/%s' % spectrum].attrs['Double Peak?'] == False
                   and  outputFile['Fitted spectra/%s' % spectrum].attrs['NPoM?'] == True]

    else:
        print 'Choice of spectra not recognised. Plotting all spectra by default'
        spectra = outputFile['Fitted spectra']

    print '\t%s spectra' % len(spectra)

    for n, spectrum in enumerate(outputFile['Fitted spectra']):

        x = outputFile['Fitted spectra/%s/Raw/Raw data (normalised)' % spectrum].attrs['wavelengths'][()]

        if type(x) != str:
            break

    #try:
    spectraNames = [spectrum for spectrum in spectra if spectrum[:8] == 'Spectrum']

    binSize = (endWl - startWl) / binNumber
    bins = np.linspace(startWl, endWl, num = binNumber)
    frequencies = np.zeros(len(bins))

    startIndex = np.where(np.round(x) == np.round(startWl))[0][0]
    endIndex = np.where(np.round(x) == np.round(endWl))[0][0]

    yDataBinned = [np.zeros(len(x)) for f in frequencies]
    yDataRawBinned = [np.zeros(len(x)) for f in frequencies]
    binnedSpectraList = {binStart : [] for binStart in bins}

    for n, spectrum in enumerate(spectraNames):

        #print spectrum

        for nn, binStart in enumerate(bins):

            #print [attr for attr in spectra[spectrum].attrs]
            cmPeakPos = outputFile['Fitted spectra'][spectrum].attrs['Coupled mode wavelength']
            #print cmPeakPos
            yData = outputFile['Fitted spectra'][spectrum]['Raw/Raw data (normalised)']
            yDataRaw = outputFile['Fitted spectra'][spectrum]['Raw/Raw data']

            if cmPeakPos != 'N/A' and binStart <= cmPeakPos < binStart + binSize and 600 < cmPeakPos < 850:
                frequencies[nn] += 1
                yDataBinned[nn] += yData
                yDataRawBinned[nn] += yDataRaw
                binnedSpectraList[binStart].append(spectrum)

    for n, yDataSum in enumerate(yDataBinned):
        yDataBinned[n] /= frequencies[n]
        yDataRawBinned[n] /= frequencies[n]

    if minBinFactor == 0:
        minBin = 0

    else:
        minBin = max(frequencies)/minBinFactor

    fig = plt.figure(figsize = (8, 6))

    if plot == True:
        fig = plt.figure(figsize = (8, 6))

        cmap = plt.get_cmap('jet')

        ax1 = fig.add_subplot(111)
        ax1.set_zorder(1)
        ax2 = ax1.twinx()
        ax2.set_zorder(0)
        ax1.patch.set_visible(False)

        yMax = 0

        yDataPlot = []
        freqsPlot = []
        binsPlot = []

        for n, yDatum in enumerate(yDataBinned):

            if frequencies[n] > minBin:
                yDataPlot.append(yDatum)
                freqsPlot.append(frequencies[n])
                binsPlot.append(bins[n])

        colors = [cmap(256 - n*(256/len(yDataPlot))) for n, yDataSum in enumerate(yDataPlot)][::-1]

        for n, yDataSum in enumerate(yDataPlot):

            currentYMax = yDataSum[startIndex:endIndex].max()

            ySmooth = reduceNoise(yDataSum, factor = 7)
            ax1.plot(x, ySmooth, lw = 0.7, color = colors[n])

            if currentYMax > yMax:
                yMax = currentYMax

        ax1.set_ylim(-0.1, yMax*1.2)
        ax1.set_ylabel('Normalised Intensity', fontsize = 18)
        ax1.tick_params(labelsize = 15)
        ax1.set_xlabel('Wavelength (nm)', fontsize = 18)
        #ax1.set_xticks(range(500, 900, 50))
        ax2.bar(bins, frequencies, color = 'grey', width = 0.8*binSize, alpha = 0.8, linewidth = 0.6)
        ax2.bar(binsPlot, freqsPlot, color = colors, width = 0.8*binSize, alpha = 0.4, linewidth = 1)
        ax2.set_xlim(450, 900)
        ax2.set_ylim(0, max(frequencies)*1.05)
        ax2.set_ylabel('Frequency', fontsize = 18, rotation = 270)
        ax2.yaxis.set_label_coords(1.11, 0.5)
        ax2.set_yticks([int(tick) for tick in ax2.get_yticks() if tick > 0][:-1])
        ax2.tick_params(labelsize = 15)

        fig.tight_layout()

        if not histName.endswith('.png'):
            histName += '.png'

        fig.savefig(histName, bbox_inches = 'tight')

        if closeFigures == True:
            plt.close(fig)

        img = Image.open(histName)
        img = np.array(img)
        img = img.transpose((1, 0, 2))

    return frequencies, bins, yDataBinned, yDataRawBinned, binnedSpectraList, x, img

def histyFit(frequencies, bins):

    gaussMod = GaussianModel()
    pars = gaussMod.guess(frequencies, x = bins)
    out = gaussMod.fit(frequencies, pars, x=bins)#Performs the fit, based on initial guesses
    print '\nAverage peakpos:', out.params['center'].value, '+/-', out.params['center'].stderr, 'nm'
    print '\tFWHM:', out.params['fwhm'].value, 'nm'
    #print out.fit_report()

    resonance = out.params['center'].value
    stderr = out.params['center'].stderr
    fwhm = out.params['fwhm'].value

    return resonance, stderr, fwhm

def isNumber(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def createDensityArray(x, y, xBins = 20, yBins = 20):
    '''Author: Jack Griffiths'''

    array, xEdges, yEdges = np.histogram2d(x, y, [xBins, yBins])
    xCentres=[]
    yCentres=[]

    for i in range(len(xEdges))[1:]:
        xCentres.append(0.5 * (xEdges[i] + xEdges[i - 1]))

    for i in range(len(yEdges))[1:]:
        yCentres.append(0.5 * (yEdges[i] + yEdges[i - 1]))

    return array, xCentres, yCentres

def gaussian2D((x, y), height, xMean, yMean, xSigma, ySigma, cor):
    '''Author: Jack Griffiths'''

    x = np.array(x).astype(np.float64)
    y = np.array(y).astype(np.float64)
    exponent = (((x - xMean) / xSigma) ** 2)
    exponent += (((y - yMean) / ySigma) ** 2)
    exponent -= (2. * cor * (x - xMean) * (y - yMean)) / (xSigma * ySigma)
    exponent /= (2 * (1 - (cor ** 2)))
    output = height * np.exp(-1. * exponent)

    return output

def fitGauss2D(array, xCentres, yCentres):
    '''Author: Jack Griffiths'''

    x,y,z=[],[],[]

    for i in range(len(yCentres)):
        for j in range(len(xCentres)):
            x.append(xCentres[j])
            y.append(yCentres[i])
            z.append(array[j][i])

    xMean = np.sum(np.array(x) * np.array(z)) / np.sum(np.array(z))
    xSigma =np.sum(abs(np.array(x) - xMean) * np.array(z)) / np.sum(np.array(z))
    yMean = np.sum(np.array(y) * np.array(z)) / np.sum(np.array(z))
    ySigma = np.sum(abs(np.array(y) -yMean) * np.array(z)) / np.sum(np.array(z))

    try:
        params = spo.curve_fit(gaussian2D, (x,y), z, [np.max(z), xMean, yMean, xSigma, ySigma, 0.])

    except RuntimeError:
        print 'Fit Failed!'

        return None

    params = [params[0], np.sqrt(np.diag(params[1]))]

    return params

def halfMaximumLine2D(fit, heightFraction, numberOfPoints, accuracy = 0.00000001):
    '''Author: Jack Griffiths'''

    radius = []
    theta = np.linspace(0, 2 * np.pi, numberOfPoints)

    cut = fit[0][0]*heightFraction

    for i in theta:
        r = 0.
        step=1.
        x = np.cos(i)
        y = np.sin(i)

        while step > accuracy:

            while gaussian2D(((x * r + fit[0][1]), (y * r + fit[0][2])), * fit[0]) > cut:
                r += step

            r -= step
            step *= 0.1

        radius.append(r)

    x=[]
    y=[]

    for i in range(len(radius)):
        x.append(radius[i]*np.cos(theta[i]))
        y.append(radius[i]*np.sin(theta[i]))

    x = np.array(x) + fit[0][1]
    y = np.array(y) + fit[0][2]

    return x, y

def containingRing(fit, xData, yData, fractionInside, numberOfPoints, accuracy = 0.00000001):
    '''Author: Jack Griffiths'''

    height = 1.
    step = 1.

    while step > accuracy:
        numberInside = 0.

        for i in range(len(xData)):
            h = gaussian2D((xData[i], yData[i]), * fit[0])

            if h >= height * fit[0][0]:
                numberInside += 1

        if numberInside/len(xData) < fractionInside:
            height -= step

        else:
            height += step
            step /= 10

    return halfMaximumLine2D(fit, height, numberOfPoints)

def plotIntensityRatios(outputFile, plot = True, xBins = 150, yBins = 120, ringFraction = 0.5,
                        closeFigures = False, filterWeird = False):

    if plot == True:
        print '\nPlotting intensity ratios...'

    else:
        print '\n Gathering intensity ratios...'

    if filterWeird == True:
        print '\t(Filtering out weird peaks)'

    img = 'N/A'
    allSpectra = outputFile['Fitted spectra']

    cmPeakPositions = []
    intensityRatios = []

    spectra = sorted([spectrum for spectrum in allSpectra if spectrum[:8] == 'Spectrum'],
                     key = lambda spectrum: int(spectrum[9:]))

    for spectrum in spectra:
        #print '\n', spectrum
        spectrum = allSpectra[spectrum]

        cmPeakPos = spectrum.attrs['Coupled mode wavelength']
        intensityRatio = spectrum.attrs['Intensity ratio (raw)']

        if filterWeird == True:

            irImgName = 'Intensity Ratios (filtered).png'

            if (spectrum.attrs['NPoM?'] == True and spectrum.attrs['Double Peak?'] == False and
                cmPeakPos != 'N/A' and cmPeakPos < 849 and intensityRatio != 'N/A' and
                spectrum.attrs['Weird Peak?'] == False) == True:

                cmPeakPositions.append(cmPeakPos)
                intensityRatios.append(intensityRatio)

        elif filterWeird == False:
            irImgName = 'Intensity Ratios.png'

            if (spectrum.attrs['NPoM?'] == True and spectrum.attrs['Double Peak?'] == False and
                cmPeakPos != 'N/A' and cmPeakPos < 849 and intensityRatio != 'N/A') == True:

                cmPeakPositions.append(cmPeakPos)
                intensityRatios.append(intensityRatio)

    if plot == True:

        import seaborn as sns
        sns.set_style('white')

        y = np.array(intensityRatios)
        x = np.array(cmPeakPositions)

        yFilt = np.array([i for n, i in enumerate(y) if 0 < i < 10 and x[n] < 848])
        xFilt = np.array([x[n] for n, i in enumerate(y) if 0 < i < 10 and x[n] < 848])

        x = xFilt
        y = yFilt

        try:

            fig, ax = plt.subplots(figsize = (9, 9))

            ax = sns.kdeplot(xFilt, yFilt, shade=True, ax=ax, gridsize=200, cmap='Reds', cbar = True,
                             shade_lowest = False, linewidth = 20, alpha = 0.5, clim=(0.5, 1))
            ax.set_ylim(0, 10)
            ax.set_ylabel('Intensity Ratio', fontsize = 18)
            ax.tick_params(which = 'both', labelsize = 15)
            ax.set_xlim(550, 900)
            ax.set_xlabel('Coupled Mode Resonance', fontsize = 18)
            #ax.set_xticksize(fontsize = 15)

            fig.tight_layout()
            fig.savefig(irImgName, bbox_inches = 'tight')

            if closeFigures == True:
                plt.close(fig)

            img = Image.open(irImgName)
            img = np.array(img)
            img = img.transpose((1, 0, 2))

            print '\tIntensity ratios plotted'

        except Exception as e:

            print 'Intensity ratio plot failed because %s' % str(e)

            if len(xFilt) < 100:
                print '\t(probably because dataset was too small)'

            print '\nAttempting simple scatter plot instead...'

            fig, ax = plt.subplots(figsize = (9, 9))
            ax.scatter(xFilt, yFilt, marker = 'o')
            ax.set_ylim(0, 10)
            ax.set_ylabel('Intensity Ratio', fontsize = 18)
            ax.tick_params(which = 'both', labelsize = 15)
            ax.set_xlim(550, 900)
            ax.set_xlabel('Coupled Mode Resonance', fontsize = 18)
            #ax.set_xticksize(fontsize = 15)

            fig.tight_layout()
            fig.savefig(irImgName, bbox_inches = 'tight')

            if closeFigures == True:
                plt.close(fig)

            img = Image.open(irImgName)
            img = np.array(img)
            img = img.transpose((1, 0, 2))

            print '\tIntensity ratios plotted'

    else:
        img = 'N/A'
        print 'Intensity ratios gathered'

    return intensityRatios, cmPeakPositions, img

def visualiseIntensityRatios(outputFile):

    '''OutputFile = an open h5py.File or nplab.datafile.DataFile object with read/write permission'''
    '''Plots all spectra in separate tree with lines indicating calculated peak heights and positions'''

    print '\nVisualising intensity ratios for individual spectra...'

    allSpectra = outputFile['Fitted spectra']

    for spectrum in sorted(allSpectra, key = lambda spectrum: int(spectrum[9:])):
        specNumber = int(spectrum[9:])
        spectrum = allSpectra[spectrum]
        #gFit = spectrum['Fit']
        intensityRatio = spectrum.attrs['Intensity ratio (raw)']

        if intensityRatio != 'N/A':
            y = spectrum['Raw/Raw data'][()]
            x = spectrum['Raw/Raw data'].attrs['wavelengths'][()]
            xyTrunc = truncateSpectrum(x, y)
            xTrunc = xyTrunc[0]
            ySmooth = butterLowpassFiltFilt(xyTrunc[1])
            zeroLine = np.array([0] * len(xTrunc))
            transHeight = spectrum.attrs['Transverse mode intensity (raw)']
            transWl = spectrum.attrs['Transverse mode wavelength']
            cmHeight = spectrum.attrs['Coupled mode intensity (raw)']
            cmWl = spectrum.attrs['Coupled mode wavelength']
            xTransVert = np.array([transWl] * 10)
            yTransVert = np.linspace(0, transHeight, 10)
            xCmVert = np.array([cmWl] * 10)
            yCmVert = np.linspace(0, cmHeight, 10)
            transHoriz = np.array([transHeight] * len(xTrunc))
            cmHoriz = np.array([cmHeight] * len(xTrunc))

            if 'Intensity ratio measurement' in spectrum:
                del spectrum['Intensity ratio measurement']

            gIrVis = spectrum.create_group('Intensity ratio measurement')

            dRaw = gIrVis.create_dataset('Raw', data = y)
            dRaw.attrs['wavelengths'] = x
            dSmooth = gIrVis.create_dataset('Smoothed', data = ySmooth)
            dSmooth.attrs['wavelengths'] = xTrunc
            dZero = gIrVis.create_dataset('Zero', data = zeroLine)
            dZero.attrs['wavelengths'] = dSmooth.attrs['wavelengths']
            dTransVert = gIrVis.create_dataset('Transverse mode position', data = yTransVert)
            dTransVert.attrs['wavelengths'] = xTransVert
            dCmVert = gIrVis.create_dataset('Coupled mode position', data = yCmVert)
            dCmVert.attrs['wavelengths'] = xCmVert
            dTransHoriz = gIrVis.create_dataset('Transverse mode height', data = transHoriz)
            dTransHoriz.attrs['wavelengths'] = xTrunc
            dCmHoriz = gIrVis.create_dataset('Coupled mode height', data = cmHoriz)
            dCmHoriz.attrs['wavelengths'] = xTrunc

            if '/All spectra/Spectra with peak heights/Spectrum %s' % specNumber in outputFile:
                del outputFile['All spectra/Spectra with peak heights/Spectrum %s' % specNumber]

            outputFile['All spectra/Spectra with peak heights/Spectrum %s' % specNumber] = gIrVis

    print '\tIntensity ratios visualised'

def updateTransAndCoupledMode(outputFile, transGuess = 533, transRange = [500, 550], reNormalise = True):
    '''Doesn't work properly yet - needs fixing'''

    print '\nUpdating trans and coupled mode parameters'

    gSpectra = outputFile['Fitted spectra']

    allSpectra = sorted([spectrum for spectrum in outputFile['Fitted spectra']],
                        key = lambda spectrum: int(spectrum[9:]))
    allSpectra = [spectrum for spectrum in allSpectra if gSpectra[spectrum].attrs['NPoM?'] == True]

    for spectrum in allSpectra:
        spectrum = gSpectra[spectrum]
        x = spectrum['Fit/Smoothed data'].attrs['wavelengths'][()]
        xRaw = spectrum['Raw/Raw data'].attrs['wavelengths'][()]
        yRaw = spectrum['Raw/Raw data'][()]
        ySmooth = np.array(spectrum['Fit/Smoothed data'][()])
        fitComps = spectrum['Fit/Final components/']
        fitParams = {'g%s' % n : {key : fitComps[n].attrs[key] for key in fitComps[n].attrs.keys() if
                                  key != 'wavelengths'} for n in fitComps}

        tcMetadata = findTransAndCoupledMode(x, xRaw, yRaw, ySmooth, fitParams, transGuess = transGuess,
                                             transRange = transRange, plot = False)

        spectrum.attrs['Transverse mode intensity (norm)'] = tcMetadata['transverseModeIntensity']
        spectrum.attrs['Transverse mode intensity (raw)'] = tcMetadata['rawTransverseModeIntensity']
        spectrum.attrs['Transverse mode wavelength'] = tcMetadata['transverseModePosition']
        spectrum.attrs['Coupled mode intensity (norm)'] = tcMetadata['coupledModeIntensity']
        spectrum.attrs['Coupled mode intensity (raw)'] = tcMetadata['rawCoupledModeIntensity']
        spectrum.attrs['Coupled mode wavelength'] = tcMetadata['coupledModePosition']
        spectrum.attrs['Intensity ratio'] = tcMetadata['intensityRatio']
        spectrum.attrs['Intensity ratio (raw)'] = tcMetadata['rawIntensityRatio']

        if reNormalise == True:

            transHeight = tcMetadata['transverseModeIntensity']

            datasetsToUpdate = ['Fit/Best fit',
                                'Fit/Final components',
                                'Fit/Raw data (truncated, normalised)',
                                'Fit/Smoothed data',
                                'Raw/Raw data (normalised)']

            for dataset in datasetsToUpdate:

                if dataset == 'Fit/Final components':

                    for comp in spectrum[dataset]:
                        data = spectrum[dataset][comp] / transHeight
                        del spectrum[dataset][comp]
                        compDset = spectrum.create_dataset('%s/%s' % (dataset, comp), data = data)
                        compDset.attrs['wavelengths'] = x

                        '''May need to update component parameters also'''

                        for key in fitParams['g%s' % comp].keys():
                            compDset.attrs[key] = fitParams['g%s' % comp][key]

                else:
                    attrs = {key : spectrum[dataset].attrs[key] for key in spectrum[dataset].attrs.keys()}
                    data = spectrum[dataset][()] / transHeight
                    del spectrum[dataset]
                    dSet = spectrum.create_dataset(dataset, data = data)

                    for key in attrs:
                        dSet.attrs[key] = attrs[key]

    print 'Transverse and coupled mode updated'

def plotInitStack(x, yData, imgName = 'Initial Stack', closeFigures = False):

    print 'Plotting initial stacked map'

    stackStartTime = time.time()
    wavelengths = x

    yDataTrunc = [truncateSpectrum(wavelengths, spectrum)[1] for spectrum in yData]
    xTrunc = truncateSpectrum(x, yData[0])[0]

    transIndex = np.where(xTrunc > 533)[0][0]
    yDataTrunc = np.array([spectrum / spectrum[transIndex] for spectrum in yDataTrunc])

    xStack = xTrunc
    yStack = range(len(yDataTrunc))
    zStack = np.vstack(yDataTrunc)

    fig = plt.figure(figsize = (9, 7))

    plt.pcolormesh(xStack, yStack, zStack, cmap = 'inferno', vmin = 0, vmax = 5)
    plt.xlim(450, 900)
    plt.xlabel('Wavelength (nm)', fontsize = 14)
    plt.ylabel('Spectrum #', fontsize = 14)
    cbar = plt.colorbar()
    cbar.set_ticks([])
    cbar.set_label('Intensity (a.u.)', fontsize = 14)
    plt.ylim(min(yStack), max(yStack))
    plt.yticks(fontsize = 14)
    plt.xticks(fontsize = 14)

    if imgName.endswith('.png'):
        plt.title(imgName[:-4])

    else:
        plt.title(imgName)
        imgName = '%s.png' % imgName

    plt.show()
    fig.savefig(imgName, bbox_inches = 'tight')

    if closeFigures == True:
        plt.close(fig)

    img = np.array(Image.open(imgName)).transpose((1, 0, 2))

    #except Exception as e:
    #    print 'Plotting of %s failed because %s' % (imgName, str(e))
    #    img = 'N/A'

    stackEndTime = time.time()
    timeElapsed = stackEndTime - stackStartTime

    print '\tInitial stack plotted in %s seconds' % timeElapsed

    return img

def plotStackedMap(spectraSorted, imgName = 'Stack', closeFigures = False):

    try:
        yDataRaw = [spectrum['Raw/Raw data (normalised)'][()] for spectrum in spectraSorted]
        yDataRaw = np.array([spectrum for spectrum in yDataRaw if type(spectrum) != str])

        n = 0
        wavelengths = spectraSorted[n]['Raw/Raw data (normalised)'].attrs['wavelengths']

        while type(wavelengths) == str:
            n += 1
            wavelengths = spectraSorted[n]['Raw/Raw data (normalised)'].attrs['wavelengths']

        yDataTrunc = np.array([truncateSpectrum(wavelengths, spectrum)[1] for spectrum in yDataRaw])
        wavelengthsTrunc = truncateSpectrum(wavelengths, yDataRaw[0])[0]

        xStack = wavelengthsTrunc
        yStack = range(len(yDataTrunc))
        zStack = np.vstack(yDataTrunc)

        fig = plt.figure(figsize = (9, 7))

        plt.pcolormesh(xStack, yStack, zStack, cmap = 'inferno', vmin = 0, vmax = 5)
        plt.xlim(450, 900)
        plt.xlabel('Wavelength (nm)', fontsize = 14)
        plt.ylabel('Spectrum #', fontsize = 14)
        cbar = plt.colorbar()
        cbar.set_ticks([])
        cbar.set_label('Intensity (a.u.)', fontsize = 14)
        plt.ylim(min(yStack), max(yStack))
        plt.yticks(fontsize = 14)
        plt.xticks(fontsize = 14)

        if imgName.endswith('.png'):
            plt.title(imgName[:-4])

        else:
            plt.title(imgName)
            imgName = '%s.png' % imgName

        fig.savefig(imgName, bbox_inches = 'tight')

        if closeFigures == True:
            plt.close(fig)

        img = np.array(Image.open(imgName)).transpose((1, 0, 2))

    except Exception as e:
        print 'Plotting of %s failed because %s' % (imgName, str(e))
        img = 'N/A'

    return img

def plotAllStacks(outputFile, closeFigures = False, filterWeird = True):

    print '\nPlotting stacked spectral maps...'

    gSpectra = outputFile['Fitted spectra']
    gStackOutput = outputFile.create_group('Statistics/Stacks')

    if filterWeird == True:
        '''Spectra without weird peaks'''

        cmWlName = 'Coupled mode wavelength'
        spectra = [gSpectra[spectrum] for spectrum in gSpectra if spectrum[:8] == 'Spectrum' and
                   gSpectra[spectrum].attrs['Weird Peak?'] == False and
                   gSpectra[spectrum].attrs[cmWlName] != 'N/A']
        spectraSorted = sorted(spectra, key = lambda spectrum: spectrum.attrs[cmWlName])
        gStackOutput.create_dataset('By C mode, weird peaks removed',
                                    data = plotStackedMap(spectraSorted, imgName = 'Stack (No weird peaks)',
                                                          closeFigures = closeFigures))

    '''By order of measurement'''

    spectra = [spectrum for spectrum in gSpectra if spectrum[:8] == 'Spectrum']
    spectraSorted = sorted(spectra, key = lambda spectrum: int(spectrum[9:]))
    spectraSorted = [gSpectra[spectrum] for spectrum in spectraSorted]

    gStackOutput.create_dataset('All',
                                data = plotStackedMap(spectraSorted, imgName = 'Stack (all)',
                                                      closeFigures = closeFigures))
    '''By CM wavelength'''

    cmWlName = 'Coupled mode wavelength'
    spectra = [gSpectra[spectrum] for spectrum in gSpectra if spectrum[:8] == 'Spectrum' and
               gSpectra[spectrum].attrs[cmWlName] != 'N/A']
    spectraSorted = sorted(spectra, key = lambda spectrum: spectrum.attrs[cmWlName])

    gStackOutput.create_dataset('By C mode',
                                data = plotStackedMap(spectraSorted, imgName = 'Stack (CM wavelength)',
                                                      closeFigures = closeFigures))

    '''By TM wavelength'''

    tmWlName = 'Transverse mode wavelength'

    try:
        spectra = [gSpectra[spectrum] for spectrum in gSpectra if spectrum[:8] == 'Spectrum' and
               gSpectra[spectrum].attrs[tmWlName] != 'N/A']

    except:
        tmWlName = 'Transverse mode wavelength)'
        spectra = [gSpectra[spectrum] for spectrum in gSpectra if spectrum[:8] == 'Spectrum' and
               gSpectra[spectrum].attrs[tmWlName] != 'N/A']

    spectraSorted = sorted(spectra, key = lambda spectrum: spectrum.attrs[tmWlName])

    gStackOutput.create_dataset('By T mode',
                                data = plotStackedMap(spectraSorted, imgName = 'Stack (TM wavelength)',
                                                      closeFigures = closeFigures))

    '''By intensity ratio'''

    irName = 'Intensity ratio (raw)'

    spectra = [gSpectra[spectrum] for spectrum in gSpectra if spectrum[:8] == 'Spectrum' and
               gSpectra[spectrum].attrs[irName] != 'N/A']
    spectraSorted = sorted(spectra, key = lambda spectrum: spectrum.attrs[irName])

    gStackOutput.create_dataset('By intensity ratio',
                                data = plotStackedMap(spectraSorted, imgName = 'Stack (intensity ratio)',
                                                      closeFigures = closeFigures))

    '''Doubles in order of measurement'''

    spectra = [spectrum for spectrum in gSpectra if spectrum[:8] == 'Spectrum' and
               gSpectra[spectrum].attrs['Double Peak?'] == True]

    if len(spectra) > 0:

        spectraSorted = sorted(spectra, key = lambda spectrum: int(spectrum[9:]))
        spectraSorted = [gSpectra[spectrum] for spectrum in spectraSorted]

        '''By order of measurement'''

        gStackOutput.create_dataset('All doubles',
                                    data = plotStackedMap(spectraSorted, imgName = 'Stack (all doubles)',
                                                          closeFigures = closeFigures))

        '''Doubles by CM wavelength'''

        cmWlName = 'Coupled mode wavelength'
        spectra = [gSpectra[spectrum] for spectrum in gSpectra if spectrum[:8] == 'Spectrum' and
                   gSpectra[spectrum].attrs[cmWlName] != 'N/A' and
                   gSpectra[spectrum].attrs['Double Peak?'] == True]
        spectraSorted = sorted(spectra, key = lambda spectrum: spectrum.attrs[cmWlName])

        gStackOutput.create_dataset('Doubles by C mode',
                                    data = plotStackedMap(spectraSorted,
                                                          imgName = 'Stack (Doubles by CM wavelength)',
                                                          closeFigures = closeFigures))

        '''Doubles by TM wavelength'''

        tmWlName = 'Transverse mode wavelength'

        try:
            spectra = [gSpectra[spectrum] for spectrum in gSpectra if spectrum[:8] == 'Spectrum' and
                   gSpectra[spectrum].attrs[tmWlName] != 'N/A' and
                   gSpectra[spectrum].attrs['Double Peak?'] == True]

        except:
            tmWlName = 'Transverse mode wavelength)'

        spectraSorted = sorted(spectra, key = lambda spectrum: spectrum.attrs[tmWlName])

        gStackOutput.create_dataset('Doubles by T mode',
                                    data = plotStackedMap(spectraSorted,
                                                          imgName = 'Stack (Doubles by TM wavelength)',
                                                          closeFigures = closeFigures))

        '''Doubles by intensity ratio'''

        irName = 'Intensity ratio (raw)'

        spectra = [gSpectra[spectrum] for spectrum in gSpectra if spectrum[:8] == 'Spectrum' and
                   gSpectra[spectrum].attrs[irName] != 'N/A' and
                   gSpectra[spectrum].attrs['Double Peak?'] == True]
        spectraSorted = sorted(spectra, key = lambda spectrum: spectrum.attrs[irName])

        gStackOutput.create_dataset('Doubles by intensity ratio',
                                    data = plotStackedMap(spectraSorted,
                                                          imgName = 'Stack (Doubles by intensity ratio)',
                                                          closeFigures = closeFigures))

    else:
        print '\tNo doubles to plot'

    print '\tStacks plotted'

def sortSpectra(outputFile, replace = False, method = 'basic', npomLower = 0.1, npomUpper = 2.5, NpomThreshold = 1.5,
                doublesThreshold = 0.5, minDoublesDist = 30, cmPosThreshold = 650, monitorProgress = False, doublesPlot = False, returnAll = False,
                weirdFactor = 1.3, weirdPlot = False):

    specSortStart = time.time()
    print '\nSorting spectra...'

    gAll = outputFile['All spectra']

    if replace == False and method == 'basic':

        if 'NPoMs' in gAll:
            print 'Spectra already sorted'
            return

    elif method == 'full' or replace == True:

        if method == 'full' and replace == False:
            print 'Full sorting in place. Data will be overwritten'

        try:

            if 'NPoMs' in gAll:
                del gAll['NPoMs']

        except Exception as e:
            print e

    if method == 'full':

        for spectrumName in outputFile['Fitted spectra']:
           spectrum = outputFile['Fitted spectra'][spectrumName]

           yRaw = spectrum['Raw/Raw data']
           xRaw = yRaw.attrs['wavelengths']
           isNpom = testIfNpom(xRaw, yRaw, lower = npomLower, upper = npomUpper, NpomThreshold = NpomThreshold)

           if isNpom == True:

               isDouble = testIfDouble(xRaw, yRaw, doublesThreshold = 2, midpoint = 680, plot = doublesPlot)
               isWeird = testIfWeirdPeak(xRaw, yRaw, factor = weirdFactor, plot = weirdPlot)

           else:
               isDouble = 'N/A'
               isWeird = 'N/A'

           spectrum.attrs['NPoM?'] = isNpom
           spectrum.attrs['Double Peak?'] = isDouble
           spectrum.attrs['Weird Peak?'] = isWeird

    gNPoMs = gAll.create_group('NPoMs')
    gAllNPoMs = gNPoMs.create_group('All NPoMs')
    gDoubles = gNPoMs.create_group('Doubles')
    gSingles = gNPoMs.create_group('Singles')
    gWeirds = gNPoMs.create_group('Spectra with weird peaks')
    gNoWeird = gNPoMs.create_group('No weird peaks')
    gNormal = gNPoMs.create_group('\"Normal\" spectra')

    for spectrumName in outputFile['Fitted spectra']:
        spectrum = outputFile['Fitted spectra'][spectrumName]
        dRaw = spectrum['Raw/Raw data']

        dAllNPoMs = gAllNPoMs.create_dataset(spectrumName, data = dRaw)
        dAllNPoMs.attrs['wavelengths'] = dRaw.attrs['wavelengths']
        dAllNPoMs.attrs.update(spectrum.attrs)

        if spectrum.attrs['Double Peak?'] == True:
            dDouble = gDoubles.create_dataset(spectrumName, data = dRaw)
            dDouble.attrs['wavelengths'] = dRaw.attrs['wavelengths']
            dDouble.attrs.update(spectrum.attrs)

        if spectrum.attrs['Double Peak?'] == False:
            dSingle = gSingles.create_dataset(spectrumName, data = dRaw)
            dSingle.attrs['wavelengths'] = dRaw.attrs['wavelengths']
            dSingle.attrs.update(spectrum.attrs)

        if spectrum.attrs['Weird Peak?'] == True:
            dWeird = gWeirds.create_dataset(spectrumName, data = dRaw)
            dWeird.attrs['wavelengths'] = dRaw.attrs['wavelengths']
            dWeird.attrs.update(spectrum.attrs)

        if spectrum.attrs['Weird Peak?'] == False:
            dNoWeird = gNoWeird.create_dataset(spectrumName, data = dRaw)
            dNoWeird.attrs['wavelengths'] = dRaw.attrs['wavelengths']
            dNoWeird.attrs.update(spectrum.attrs)

        if spectrum.attrs['NPoM?'] == True and spectrum.attrs['Double Peak?'] == False and spectrum.attrs['Weird Peak?'] == False:
            dNormal = gNormal.create_dataset(spectrumName, data = dRaw)
            dNormal.attrs['wavelengths'] = dRaw.attrs['wavelengths']
            dNormal.attrs.update(spectrum.attrs)

    specSortEnd = time.time()
    timeElapsed = specSortEnd - specSortStart
    print '\tSpectra sorted in %s seconds' % timeElapsed

def plotHistAndFit(outputFile, which = 'all', startWl = 450, endWl = 900, binNumber = 80, plot = True,
                  minBinFactor = 5, closeFigures = False):

    frequencies, bins, yDataBinned, yDataRawBinned, binnedSpectraList, histyWl, histImg = plotHistogram(outputFile,
                                                              histName = 'Histogram (%s)' % which,
                                                              minBinFactor = minBinFactor,
                                                              closeFigures = closeFigures, which = which)

    try:
        avgResonance, stderr, fwhm = histyFit(frequencies, bins)
        gHist = outputFile.create_group('Statistics/Histogram/%s' % which)
        gHist.attrs['Average resonance'] = avgResonance
        gHist.attrs['Error'] = stderr
        gHist.attrs['FWHM'] = fwhm

        dBins = gHist.create_dataset('Bins', data = bins)
        dFreq = gHist.create_dataset('Frequencies', data = frequencies)
        dFreq.attrs['wavelengths'] = dBins
        gHist.create_dataset('Histogram', data = histImg)
        gSpectraBinned = gHist.create_group('Binned y data/')
        binSize = bins[1] - bins[0]
        binsSorted = sorted(bins, key = lambda binStart: float(binStart))

        for binStart in binsSorted:
            binnedSpectraList[binStart].sort(key = lambda spectrum: int(spectrum[9:]))

        for n, binStart in enumerate(binsSorted):
            if len(binnedSpectraList[binStart]) > 0:

                binEnd = binStart + binSize

                if n < 10:
                    binName = 'Bin 0%s data, %s <= peakpos < %s' % (n, binStart, binEnd)

                else:
                    binName = 'Bin %s data, %s <= peakpos < %s' % (n, binStart, binEnd)

                gBin = gSpectraBinned.create_group(binName)
                dSum = gBin.create_dataset('Sum', data = yDataRawBinned[n])
                dSum.attrs['wavelengths'] = histyWl

                for spectrum in binnedSpectraList[binStart]:
                    yDataBin = outputFile['Fitted spectra/%s/Raw/Raw data' % spectrum]
                    dSpec = gBin.create_dataset(spectrum, data = yDataBin)
                    dSpec.attrs['wavelengths'] = yDataBin.attrs['wavelengths']

    except Exception as e:
        print e
        avgResonance = 'N/A'
        stderr = 'N/A'
        fwhm = 'N/A'

def pointyPeakStats(outputFile, closeFigures = True):
    allNpoms = outputFile['All spectra/NPoMs/All NPoMs']
    gStats = outputFile['Statistics']

    if 'Peak stats' in gStats:
        try:
            del gStats['Peak stats']

        except:
            pass

    gPeakStats = gStats.create_group('Peak stats')

    weirdFwhms = []
    weirdPositions = []
    weirdHeights = []
    cmFwhms = []
    cmPositions = []
    cmHeights = []
    imgs = {}

    for spectraName in allNpoms:
        attrNames = ['Weird peak FWHM', 'Weird peak wavelength', 'Weird peak intensity (raw)', 'Coupled mode FWHM',
                     'Coupled mode wavelength', 'Coupled mode intensity (raw)']
        attrLists = [weirdFwhms, weirdPositions, weirdHeights, cmFwhms, cmPositions, cmHeights]

        for n, attrName in enumerate(attrNames):
            attr = allNpoms[spectraName].attrs[attrName]

            if attr == 'N/A':
                attr = np.nan

            attrLists[n].append(attr)

    for n, attrName in enumerate(attrNames):

        for m, attrlist in enumerate(attrLists):

            if m <= n:
                continue

            else:
                xName = attrNames[m]
                yName = attrNames[n]
                imgName = '%s vs %s.png' % (xName, yName)
                y = attrLists[n]
                x = attrLists[m]

                fig = plt.figure()
                plt.scatter(x, y, s = 14)
                plt.xlabel(xName, fontsize = 14)
                plt.ylabel(yName, fontsize = 14)

                fig.tight_layout()
                fig.savefig('%s' % imgName, bbox_inches = 'tight')

                if closeFigures == True:
                    plt.close(fig)

                img = Image.open(imgName)
                img = np.array(img)
                img = img.transpose((1, 0, 2))

                imgs[imgName] = img

                dPlot = gPeakStats.create_dataset(imgName, data = img)
                dPlot.attrs[xName] = x
                dPlot.attrs[yName] = y

def doubBoolsHists(outputFile, binNumber = 80, plot = True, closeFigures = False):
    allNpoms = outputFile['All spectra/NPoMs/All NPoMs']
    gStats = outputFile['Statistics']

    if 'Doubles stats' in gStats:
        try:
            del gStats['Double stats']

        except:
            pass

    gDoubleStats = gStats.create_group('Double stats')

    weirdFwhms = []
    weirdPositions = []
    weirdHeights = []
    doubBools = []
    imgs = {}

    for spectraName in allNpoms:
        attrNames = ['Weird peak FWHM', 'Weird peak wavelength', 'Weird peak intensity (raw)', 'Double Peak?']
        attrNamesShort = ['FWHM', 'Peakpos', 'Peak height']
        attrLists = [weirdFwhms, weirdPositions, weirdHeights, doubBools]

        for n, attrName in enumerate(attrNames):
            attr = allNpoms[spectraName].attrs[attrName]

            if attr == 'N/A':
                attr = np.nan

            attrLists[n].append(attr)

    for i, attrList in enumerate(attrLists[:-1]):

        startWl = min(attrList)
        endWl = max(attrList)

        binSize = (endWl - startWl) / binNumber
        bins = np.linspace(startWl, endWl, num = binNumber)
        totalFreqs = np.zeros(len(bins))
        doubleFreqs = np.zeros(len(bins))
        binnedSpectraList = {binStart : [] for binStart in bins}

        for n, spectraName in enumerate(allNpoms):

            for nn, binStart in enumerate(bins):

                #print [attr for attr in spectra[spectrum].attrs]
                attrValue = allNpoms[spectraName].attrs[attrNames[i]]
                isDouble = allNpoms[spectraName].attrs['Double Peak?']

                if attrValue != 'N/A' and binStart <= attrValue < binStart + binSize:
                    totalFreqs[nn] += 1

                    if isDouble == True:
                        doubleFreqs[nn] += 1
                        binnedSpectraList[binStart].append(spectraName)

        frequencies = doubleFreqs / totalFreqs

        fig = plt.figure(figsize = (8, 6))
        plt.bar(bins, frequencies, color = 'grey', width = 0.8*binSize, alpha = 0.8, linewidth = 0.6)
        plt.ylim(0, max(frequencies)*1.05)
        plt.xlabel(attrNames[i], fontsize = 14)
        plt.ylabel('Frequency', fontsize = 14)
        fig.tight_layout()
        imgName = 'P(Double) vs %s.png' % attrNames[i]
        fig.savefig(imgName, bbox_inches = 'tight')

        if closeFigures == True:
            plt.close(fig)

        img = Image.open(imgName)
        img = np.array(img)
        img = img.transpose((1, 0, 2))

        imgs[imgName] = img

        gPlot = gDoubleStats.create_group(attrNames[i])
        gPlot.attrs[attrNames[i]] = attrList
        gPlot.create_dataset(imgName, data = img)
        gSpectraBinned = gPlot.create_group('Binned spectra')
        binSize = bins[1] - bins[0]
        binsSorted = sorted(bins, key = lambda binStart: float(binStart))

        for binStart in binsSorted:
            binnedSpectraList[binStart].sort(key = lambda spectrum: int(spectrum[9:]))

        for n, binStart in enumerate(binsSorted):

            if len(binnedSpectraList[binStart]) > 0:

                binEnd = binStart + binSize

                if n < 10:
                    binName = 'Bin 0%s data, %s <= %s < %s' % (n, binStart, attrNamesShort[i], binEnd)

                else:
                    binName = 'Bin %s data, %s <= %s < %s' % (n, binStart, attrNamesShort[i], binEnd)

                gBin = gSpectraBinned.create_group(binName)

                for spectrumName in binnedSpectraList[binStart]:
                    yDataBin = allNpoms[spectrumName]
                    dSpec = gBin.create_dataset(spectrumName, data = yDataBin)
                    dSpec.attrs['wavelengths'] = yDataBin.attrs['wavelengths']

def doStats(outputFile, minBinFactor = 5, sortSpec = True, replaceWhenSorting = False, sortMethod = 'basic', stacks = True,
            hist = True, intensityRatios = True, pointyPeaks = True, raiseExceptions = False, closeFigures = False):

    if 'Statistics' not in outputFile:
        outputFile.create_group('Statistics')

    if sortSpec == True:
        sortSpectra(outputFile, replace = replaceWhenSorting, method = sortMethod)

    if stacks == True:

        if 'Stacks' in outputFile['Statistics']:
            try:
                del outputFile['Statistics/Stacks']

            except:
                pass

        plotAllStacks(outputFile, closeFigures = closeFigures)

    if hist == True:

        if 'Histogram' in outputFile['Statistics']:
            try:
                del outputFile['Statistics/Histogram']

            except:
                pass

        for histyWhich in ['all', 'no doubles', 'filtered']:
            plotHistAndFit(outputFile, which = histyWhich, minBinFactor = minBinFactor, closeFigures = closeFigures)

        print '\nAll histograms plotted (hopefully)'

    if intensityRatios == True:

        if 'Intensity ratios' in outputFile['Statistics']:
            try:
                del outputFile['Statistics/Intensity ratios']

            except:
                pass

        if 'Intensity ratios (filtered)' in outputFile['Statistics']:
            try:
                del outputFile['Statistics/Intensity ratios (filtered)']

            except:
                pass

        numberOfSpectra = len(outputFile['Fitted spectra'])
        xBins = numberOfSpectra / 12
        yBins = numberOfSpectra / 12

        intensityRatios, cmPeakPositions, irImg = plotIntensityRatios(outputFile, plot = True, xBins = xBins,
                                                                      yBins = yBins, closeFigures = closeFigures,
                                                                      filterWeird = False)

        outputFile['Statistics/Intensity ratios'] = irImg
        dIr = outputFile['Statistics/Intensity ratios']
        dIr.attrs['Intensity ratios'] = intensityRatios
        dIr.attrs['Peak positions'] = cmPeakPositions


        intensityRatios, cmPeakPositions, irImg = plotIntensityRatios(outputFile, plot = True, xBins = xBins,
                                                                      yBins = yBins, closeFigures = closeFigures,
                                                                      filterWeird = True)

        outputFile['Statistics/Intensity ratios (filtered)'] = irImg
        dIr = outputFile['Statistics/Intensity ratios']
        dIr.attrs['Intensity ratios'] = intensityRatios
        dIr.attrs['Peak positions'] = cmPeakPositions

        visualiseIntensityRatios(outputFile)

    if pointyPeaks == True:

        print '\nAnalysing funky peaks'
        pointyPeakStats(outputFile, closeFigures = True)
        doubBoolsHists(outputFile, binNumber = 80, plot = True, closeFigures = False)
        print '\tFunky peaks analysed'

    print '\nStats done'

def fitAllSpectra(x, yData, outputFile, startSpec = 0, monitorProgress = False, plot = False,
                  raiseExceptions = False, closeFigures = False, fukkit = False, simpleFit = True):

    absoluteStartTime = time.time()

    '''Fits all spectra and populates h5 file with relevant output data.
       h5 file must be opened before the function and closed afterwards'''

    print '\nBeginning fit procedure...'

    if len(yData) > 2500:
        print 'About to fit %s spectra. This may take a while...' % len(yData)

    '''SPECIFY INITIAL FIT PARAMETERS HERE'''

    doublesThreshold = 0.4
    detectionThreshold = 0
    doublesDist = 0

    fittedSpectra = []
    failedSpectra = []
    failedSpectraIndices = []

    nummers = range(5, 101, 5)

    totalFitStart = time.time()
    print '\n0% complete'

    gFitted = outputFile.create_group('Fitted spectra/')
    gAll = outputFile.create_group('All spectra')
    gCrap = gAll.create_group('Non-NPoMs')
    gSpecOnly = gAll.create_group('Raw')

    for n, y in enumerate(yData[:]):

        nn = n
        n += startSpec

        if monitorProgress in [True, 'main']:
            print 'Spectrum %s' % n

        if int(100 * nn / len(yData[:])) in nummers:
            currentTime = time.time() - totalFitStart
            mins = int(currentTime / 60)
            secs = (np.round((currentTime % 60)*100))/100
            print '%s%% (%s spectra) complete in %s min %s sec' % (nummers[0], nn, mins, secs)
            nummers = nummers[1:]

        if raiseExceptions == False:

            try:
                fittedSpectrum = fitNpomSpectrum(x, y, detectionThreshold = detectionThreshold,
                                                  doublesThreshold = doublesThreshold,
                                                  doublesDist = doublesDist,
                                                  monitorProgress = monitorProgress, plot = plot, fukkit = fukkit, simpleFit = simpleFit)
                fittedSpectra.append(fittedSpectrum)
                fitError = 'N/A'

            except Exception as e:
                #raise e
                fittedSpectrum = DF_Spectrum(y, 'N/A', False, 'N/A', 'N/A', 'N/A')
                fittedSpectrum = fittedSpectrum.metadata
                failedSpectra.append(fittedSpectrum)
                failedSpectraIndices.append(n)
                fitError = e

                print 'Spectrum %s failed because: \n\t"%s"' % (n, e)

        elif raiseExceptions == True:
            fittedSpectrum = fitNpomSpectrum(x, y, detectionThreshold = detectionThreshold,
                                              doublesThreshold = doublesThreshold,
                                              doublesDist = doublesDist, monitorProgress = monitorProgress,
                                              plot = plot, fukkit = fukkit, simpleFit = simpleFit)
            fittedSpectra.append(fittedSpectrum)
            fitError = 'N/A'

        '''Adds data to open HDF5 file'''

        if fittedSpectrum['NPoM?'] == True:
            rawData = fittedSpectrum['rawData']

        else:
            rawData = y

        mainRawSpec = gSpecOnly.create_dataset('Spectrum %s' % n, data = rawData)
        mainRawSpec.attrs['wavelengths'] = x

        if fittedSpectrum['NPoM?'] == True:
            g = gFitted.create_group('Spectrum %s/' % n)

            g.attrs['NPoM?'] = fittedSpectrum['NPoM?']
            g.attrs['Double Peak?'] = fittedSpectrum['doublePeak?']
            g.attrs['Weird Peak?'] = fittedSpectrum['weirdPeak?']
            g.attrs['Weird peak intensity (norm)'] = fittedSpectrum['weirdPeakIntensity']
            g.attrs['Weird peak intensity (raw)'] = fittedSpectrum['rawWeirdPeakIntensity']
            g.attrs['Weird peak wavelength'] = fittedSpectrum['weirdPeakPosition']
            g.attrs['Weird peak FWHM'] = fittedSpectrum['weirdPeakFwhm']
            g.attrs['Transverse mode intensity (norm)'] = fittedSpectrum['transverseModeIntensity']
            g.attrs['Transverse mode intensity (raw)'] = fittedSpectrum['rawTransverseModeIntensity']
            g.attrs['Transverse mode wavelength'] = fittedSpectrum['transverseModePosition']
            g.attrs['Coupled mode intensity (norm)'] = fittedSpectrum['coupledModeIntensity']
            g.attrs['Coupled mode intensity (raw)'] = fittedSpectrum['rawCoupledModeIntensity']
            g.attrs['Coupled mode wavelength'] = fittedSpectrum['coupledModePosition']
            g.attrs['Coupled mode FWHM'] = fittedSpectrum['coupledModeFwhm']
            g.attrs['Intensity ratio (from norm)'] = fittedSpectrum['intensityRatio']
            g.attrs['Intensity ratio (raw)'] = fittedSpectrum['rawIntensityRatio']
            g.attrs['Error(s)'] = str(fitError)

            gRaw = g.create_group('Raw/')

            dRaw = gRaw.create_dataset('Raw data', data = rawData)
            dRaw.attrs['wavelengths'] = fittedSpectrum['fullWavelengths']

            dRawNorm = gRaw.create_dataset('Raw data (normalised)', data = fittedSpectrum['normalisedSpectrum'])
            dRawNorm.attrs['wavelengths'] = dRaw.attrs['wavelengths']

            gFit = g.create_group('Fit/')

            dRawTrunc = gFit.create_dataset('Raw data (truncated, normalised)',
                                               data = fittedSpectrum['truncatedSpectrum'])
            dRawTrunc.attrs['wavelengths'] = fittedSpectrum['truncatedWavelengths']

            dSmooth = gFit.create_dataset('Smoothed data', data = fittedSpectrum['smoothedSpectrum'])
            dSmooth.attrs['wavelengths'] = dRawTrunc.attrs['wavelengths']
            dSmooth.attrs['secondDerivative'] = fittedSpectrum['secondDerivative']

            dBestFit = gFit.create_dataset('Best fit', data = fittedSpectrum['bestFit'])
            dBestFit.attrs['wavelengths'] = dRawTrunc.attrs['wavelengths']
            dBestFit.attrs['Initial guess'] = fittedSpectrum['initialGuess']
            dBestFit.attrs['Residuals'] = fittedSpectrum['residuals']

            gComps = gFit.create_group('Final components/')

            comps = fittedSpectrum['finalComponents']

            if comps != 'N/A':

                for i in range(len(comps.keys())):
                    component = gComps.create_dataset(str(i), data = comps['g%s_' % i])
                    componentParams = fittedSpectrum['finalParams']['g%s' % i]
                    component.attrs['center'] = componentParams['center']
                    component.attrs['height'] = componentParams['height']
                    component.attrs['amplitude'] = componentParams['amplitude']
                    component.attrs['sigma'] = componentParams['sigma']
                    component.attrs['fwhm'] = componentParams['fwhm']
                    component.attrs['wavelengths'] = dRawTrunc.attrs['wavelengths']

        else:
            dCrap = gCrap.create_dataset('Spectrum %s' % n, data = mainRawSpec)
            dCrap.attrs['wavelengths'] = mainRawSpec.attrs['wavelengths']

        if fitError != 'N/A':
            mainRawSpec.attrs['Fitting error'] = str(fitError)

    gFitted.attrs['Failed spectra indices'] = failedSpectraIndices

    print '100% complete'
    totalFitEnd = time.time()
    timeElapsed = totalFitEnd - totalFitStart

    mins = int(timeElapsed / 60)
    secs = int(np.round(timeElapsed % 60))

    print '\n%s spectra fitted in %s min %s sec' % (nn + 1, mins, secs)

    doStats(outputFile, closeFigures = closeFigures)

    absoluteEndTime = time.time()
    timeElapsed = absoluteEndTime - absoluteStartTime

    mins = int(timeElapsed / 60)
    secs = int(np.round(timeElapsed % 60))

    printEnd()

    if len(failedSpectra) == 0:
        print '\nFinished in %s min %s sec. Smooth sailing.' % (mins, secs)

    elif len(failedSpectra) == 1:
        print '\nPhew... finished in %s min %s sec with only %s failure' % (mins, secs, len(failedSpectra))

    elif len(failedSpectra) > len(fittedSpectra):
        print '\nHmmm... finished in %s min %s sec but with %s failures and only %s successful fits' % (mins, secs, len(failedSpectra),
                                                                                                        len(fittedSpectra))

    elif mins > 30:
        print '\nM8 that took ages. %s min %s sec' % (mins, secs)

    else:
        print '\nPhew... finished in %s min %s sec with only %s failures' % (mins, secs, len(failedSpectra))

    print ''

if __name__ == '__main__':
    print '\tFunctions initialised'

    method = 'All'

    startSpec = 0
    finishSpec = 0

    if method == 'All':

        #Set to 0 if you want to analyse all spectra

        print '\nRetrieving data...'

        spectra, wavelengths, background, reference = retrieveData('summary', startSpec, finishSpec)
        x, yData = prepareData(spectra, wavelengths, reference)
        initImg = plotInitStack(x, yData, imgName = 'Initial Stack', closeFigures = True)

        outputFile = createOutputFile('MultiPeakFitOutput')

        with h5py.File(outputFile, 'a') as f:
            fitAllSpectra(x, yData, f, startSpec = startSpec, raiseExceptions = False, closeFigures = True, fukkit = True, simpleFit = True)

    elif method == 'Stats':
        outputFile = 'MultiPeakFitOutput_0.h5'

        with h5py.File(outputFile, 'a') as f:
            doStats(f, minBinFactor = 6, sortSpec = True, replaceWhenSorting = True, sortMethod = 'full', stacks = False, hist = False,
                    intensityRatios = False, closeFigures = True)

    elif method == 'Stack':
        print '\nRetrieving data...'

        spectra, wavelengths, background, reference = retrieveData('summary', startSpec, finishSpec)
        x, yData = prepareData(spectra, wavelengths, reference)
        initImg = plotInitStack(x, yData, imgName = 'Initial Stack', closeFigures = False)