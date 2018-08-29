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
                      'Double Peak?',
                      'Weird Peak?',
                      'Transverse mode wavelength',
                      'Transverse mode intensity (norm)',
                      'Transverse mode intensity (raw)',
                      'Coupled mode wavelength',
                      'Coupled mode intensity (norm)',
                      'Coupled mode intensity (raw)',
                      'Intensity ratio (from norm)',
                      'Intensity ratio (raw)',
                      'Raw data',
                      'Raw data (normalised)',
                      'Full Wavelengths',
                      'Raw data (truncated, normalised)',
                      'Smoothed data (truncated, normalised)',
                      'Initial guess',
                      'Best fit',
                      'Residuals',
                      'Final components',
                      'Final parameters',
                      'Wavelengths (truncated)',
                      'secondDerivative']

        if metadata == 'N/A':
            self.metadata = {key : 'N/A' for key in metadataKeys}

        else:
            self.metadata = metadata #All other relevant info (dictionary)

'''FUNCTIONS'''

def retrieveData(summaryFile, startSpec, finishSpec, attrsOnly = False):

    '''Retrieves data from summary file'''

    if attrsOnly == False:
        print '\nRetrieving data...'

    else:
        print '\nRetrieving sample preparation info'

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
    scan = summaryFile['particleScanSummaries/scan%s' % scanNumber]
    summaryAttrs = {key : scan.attrs[key] for key in scan.attrs.keys()}

    if finishSpec == 0:
        spectra = summaryFile['particleScanSummaries/scan%s/spectra' % scanNumber][()][startSpec:]

    else:
        spectra = summaryFile['particleScanSummaries/scan%s/spectra' % scanNumber][()][startSpec:finishSpec]

    wavelengths = summaryFile['particleScanSummaries/scan%s/spectra' % scanNumber].attrs['wavelengths'][()]
    background = summaryFile['particleScanSummaries/scan%s/spectra' % scanNumber].attrs['background'][()]
    reference = summaryFile['particleScanSummaries/scan%s/spectra' % scanNumber].attrs['reference'][()]

    summaryFile.close()


    if attrsOnly == True:
        print '\tInfo retrieved from particleScanSummaries/scan%s' % scanNumber
        print '\t\t%s spectra in total' % max(spectraLengths)
        return summaryAttrs

    else:

        if finishSpec == 0:
            finishSpec = max(spectraLengths)

        nSpec = finishSpec - startSpec

        print '\t%s spectra retrieved from particleScanSummaries/scan%s' % (nSpec, scanNumber)

        return spectra, wavelengths, background, reference, summaryAttrs

def findKey(inputDict, value):
    return next((k for k, v in inputDict.items() if v == value), None)

def removeNaNs(spectrum):
    '''Removes NaN values'''
    #Identifies NaN values and sets the corresponding data point as an average of the two either side
    #If multiple sequential NaN values are encountered a straight line is made between the two closest data points
    #Input = 1D array
    #Works like list.sort() rather than sorted(list), i.e. manipulates array directly rather than returning a new one
    '''A bit clunky; will rewrite at some point'''

    nans = False

    for i in spectrum:

        if not np.isfinite(i):
            nans = True

        else:
            continue

    if nans == False:
        return spectrum

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

    print '\nPreparing data...'

    removeNaNs(wavelengths)

    for spectrum in spectra:
        removeNaNs(spectrum)

    referencedSpectra = [correctSpectrum(spectrum, reference) for spectrum in spectra]

    prepEnd = time.time()
    prepTime = prepEnd - prepStart

    print '\tAll spectra cleared of NaNs and referenced in %s seconds\n' % (prepTime)

    return wavelengths, referencedSpectra

def createOutputFile(filename):

    '''Auto-increments new filename if file exists'''

    print '\nCreating output file...'

    outputFile = '%s.h5' % filename

    if outputFile in os.listdir('.'):
        print '\n%s already exists' % outputFile
        n = 0
        outputFile = '%s_%s.h5' % (filename, n)

        while outputFile in os.listdir('.'):
            print '%s already exists' % outputFile
            n += 1
            outputFile = '%s_%s.h5' % (filename, n)

    print '\tOutput file %s created' % outputFile
    return outputFile

def truncateSpectrum(wavelengths, spectrum, startWl = 450, finishWl = 900):
    #Truncates spectrum within a certain wavelength range. Useful for removing high and low-end noise
    wavelengths = np.array(wavelengths)
    spectrum = np.array(spectrum)

    startIndex = abs(wavelengths - startWl).argmin()
    finishIndex = abs(wavelengths - finishWl).argmin()

    if startIndex > finishIndex:
        ind1 = finishIndex
        ind2 = startIndex
        startIndex = ind1
        finishIndex = ind2

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

def testIfNpom(x, y, lower = 0.05, upper = 2.5, NpomThreshold = 1.5):
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

    if np.sum(yTrunc) > lower and y.min() > -0.1:
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
    yMaxs = detectMinima(-yTruncSmooth)

    if len(yMaxs) == 0:
        weird = False
        return weird

    maxHeight = yTruncSmooth[yMaxs].max()
    maxWl = xTrunc[yTruncSmooth.argmax()]

    if maxHeight >= transHeight * factor and maxWl > 533:
        weird = True

    else:
        weird = False

    if plot == 'all' or plot == True:

        if weird == True:
            color = 'k'
        elif weird == False:
            color = 'g'

        plt.figure()
        plt.plot(xTrunc, yTrunc, color = color)
        plt.plot(maxWl, maxHeight, 'o')
        plt.xlabel('Wavelength (nm)')
        plt.ylabel('Scattered Intensity')
        plt.title('Weird peak = %s' % weird)

    return weird

def centDiff(x, y):

    '''Numerically calculates dy/dx using central difference method'''

    x1 = np.concatenate((x[:2][::-1], x))
    x2 = np.concatenate((x, x[-2:][::-1]))
    dx = x2 - x1
    dx = dx[1:-1]

    y1 = np.concatenate((y[:2][::-1], y))
    y2 = np.concatenate((y, y[-2:][::-1]))
    dy = y2 - y1
    dy = dy[1:-1]

    d = (dy/dx)
    d /= 2

    return d

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

def normToTrans(x, y, transNorm = 1, troughNorm = 0.61):

    isNpom = True

    xy = truncateSpectrum(x, y)

    xTrunc = xy[0]
    yTrunc = xy[1]

    ySmooth = butterLowpassFiltFilt(yTrunc)

    mIndices = detectMinima(ySmooth, negOnly = False)
    yMins = ySmooth[mIndices]
    xMins = xTrunc[mIndices]
    mins = [[xMin, yMins[n]] for n, xMin in enumerate(xMins)]

    initMins = [minimum for minimum in mins if minimum[0] < 533]

    if len(initMins) == 0:
        #print 'No initial minima'
        d1 = centDiff(xTrunc, ySmooth)
        d2 = centDiff(xTrunc, d1)
        mIndices = detectMinima(d2, negOnly = False)

        yMins = ySmooth[mIndices]
        xMins = xTrunc[mIndices]
        mins = [[xMin, yMins[n]] for n, xMin in enumerate(xMins)]

        initMins = [minimum for minimum in mins if minimum[0] < 533]

    initMinWls = [minimum[0] for minimum in mins]
    initMinHeights = [minimum[1] for minimum in mins]
    initMinWl = initMinWls[0]

    a0 = initMinHeights[0]
    t0 = ySmooth[abs(xTrunc - 533).argmin()]

    #plt.figure()
    #plt.plot(x, y)
    #plt.plot(xTrunc, ySmooth)
    #plt.plot(initMinWl, a0, 'o')
    #plt.plot(533, t0, 'o')
    #plt.title('Normalisation')
    #plt.show()

    aN = troughNorm
    tN = transNorm

    if a0 < t0:
        yNorm = y - a0
        yNorm /= (t0 - a0)
        yNorm *= (tN - aN)
        yNorm += aN

    else:
        #print 'a0 > t0'
        isNpom = False

        yNorm = y / t0


    return isNpom, yNorm, initMinWl

def multiPeakFind(x, y, cutoff = 1500, fs = 60000, detectionThreshold = 0, returnAll = True,
                  monitorProgress = False):

        '''Finds spectral peaks (including shoulders) by smoothing and then finding minima in the
           second derivative'''

        peakFindMetadata = {}

        ySmooth = butterLowpassFiltFilt(y, cutoff = cutoff, fs = fs)
        peakFindMetadata['Smoothed data (truncated, normalised)'] = ySmooth

        if monitorProgress == True:
            print '\nData smoothed'

        '''Differentiation'''

        firstDerivative = centDiff(x, y)
        secondDerivative = centDiff(x, firstDerivative)
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

def multiPeakFit(x, y, indices, needsSmoothing = True, cutoff = 1500, fs = 60000, constrainPeakpos = False,
                 returnAll = False, monitorProgress = True):
    '''Performs the actual fitting (given a list of peak indices) using Python's lmfit module'''
    '''You can generate indices using multiPeakFind or input them manually'''
    #x, y = 1D arrays of same length
    #indices = 1D array or list of integers, to be used as indices of x and y
    #setting constrainPeakpos = True forces peaks to stay between the indices either side when fitting
    #e.g. for indices of [7, 10, 14], the final centre position of the second peak (initial index = 10) must be between index 7 and 14

    fitStart = time.time()
    peakFitMetadata = {}

    if needsSmoothing == True:
        ySmooth = butterLowpassFiltFilt(y, cutoff = cutoff, fs = fs) #smoothes data

    else:
        ySmooth = y

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

    peakFitMetadata['Initial guess'] = init

    yFloat16 = np.float16(y) #Reduces the number of decimal places in data to speed up fitting
    xFloat16 = np.float16(x)

    out = gaussMod.fit(yFloat16, pars, x=xFloat16) #Performs the fit, based on initial guesses

    #out = gaussMod.fit(ySmooth, pars, x=x) #Can fit to smoothed data instead if you like
    comps = out.eval_components(x=xFloat16)
    peakFitMetadata['Final components'] = comps

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
    peakFitMetadata['Best fit'] = out.best_fit
    peakFitMetadata['Final parameters'] = finalParams
    peakFitMetadata['Residuals'] = out.residual

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
    '''Estimates FWHM of largest peak in a given dataset'''
    '''Also returns xy coords of peak'''

    if smooth == True:
        y = butterLowpassFiltFilt(y)

    maxdices = detectMinima(-y, negOnly = False)
    yMax = y[maxdices].max()
    halfMax = yMax/2
    maxdex = maxdices[y[maxdices].argmax()]
    xMax = x[maxdex]

    halfDex1 = abs(y[:maxdex][::-1] - halfMax).argmin()
    halfDex2 = abs(y[maxdex:] - halfMax).argmin()

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

    xy = truncateSpectrum(x, y, finishWl = 987)
    xTrunc = xy[0]
    yTrunc = xy[1]

    ySmooth = butterLowpassFiltFilt(yTrunc)

    mIndices = detectMinima(ySmooth, negOnly = False)

    xMins = xTrunc[mIndices]
    yMins = ySmooth[mIndices]

    mins = [[xMin, yMins[n]] for n, xMin in enumerate(xMins)]
    minsSorted = sorted(mins, key = lambda minimum: abs(minimum[0] - midpoint))

    try:
        if abs(minsSorted[0][1] - minsSorted[1][1]) > ySmooth.max() * 0.6:
            midMin = sorted(minsSorted[:2], key = lambda minimum: minimum[1])[0][0]

        else:
            midMin = xMins[abs(xMins - midpoint).argmin()]

    except:
        midMin = xMins[abs(xMins - midpoint).argmin()]

    initMin = xMins[0]

    if initMin == midMin:
        initMin = 450

    xy1 = truncateSpectrum(xTrunc, ySmooth, startWl = initMin, finishWl = midMin)
    xy2 = truncateSpectrum(xTrunc, ySmooth, startWl = midMin, finishWl = 987)

    if weirdPeak == True:
        x1 = xy1[0]
        y1 = xy1[1]

        fwhm, xMax, yMax = getFWHM(x1, y1, fwhmFactor = fwhmFactor)

        peakFindMetadata['Weird peak FWHM'] = fwhm
        peakFindMetadata['Weird peak intensity'] = yMax
        peakFindMetadata['Weird peak wavelength'] = xMax
        weirdGauss = [gaussian(i, yMax, xMax, fwhm) for i in x]

    else:
        peakFindMetadata['Weird peak FWHM'] = 'N/A'
        peakFindMetadata['Weird peak intensity'] = 'N/A'
        peakFindMetadata['Weird peak wavelength'] = 'N/A'
        weirdGauss = 'N/A'

    x2 = xy2[0]
    y2 = xy2[1]

    fwhm, xMax, yMax = getFWHM(x2, y2, fwhmFactor = fwhmFactor)

    peakFindMetadata['Coupled mode FWHM'] = fwhm
    peakFindMetadata['Coupled mode intensity'] = yMax
    peakFindMetadata['Coupled mode wavelength'] = xMax
    cmGauss = [gaussian(i, yMax, xMax, fwhm) for i in x]

    if plot == True or plot == 'all':
        weirdHeight = peakFindMetadata['Weird peak intensity']
        weirdWl = peakFindMetadata['Weird peak wavelength']
        weirdFwhm = peakFindMetadata['Weird peak FWHM']

        cmHeight = peakFindMetadata['Coupled mode intensity']
        cmWl = peakFindMetadata['Coupled mode wavelength']
        cmFwhm = peakFindMetadata['Coupled mode FWHM']

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

def testIfDouble(x, y, doublesThreshold = 2, plot = False, raiseExceptions = True):
    isDouble = False
    isNpom = True

    xy = truncateSpectrum(x, y)
    xTrunc = xy[0]
    yTrunc = xy[1]
    ySmooth = butterLowpassFiltFilt(yTrunc)

    mIndices = detectMinima(ySmooth, negOnly = False)
    maxdices = detectMinima(-ySmooth, negOnly = False)

    xMins = xTrunc[mIndices]
    yMins = yTrunc[mIndices]

    xMaxs = xTrunc[maxdices]
    yMaxs = yTrunc[maxdices]
    maxs = [[xMax, yMaxs[n]] for n, xMax in enumerate(xMaxs)]

    if len(yMaxs) == 0:
        isNpom = False
        isDouble = 'N/A'

    else:

        try:
            yMax = max(yMaxs)

        except Exception as e:

            if raiseExceptions == True:
                pass

            else:
                print e
                return False

        maxsSortedY = sorted(maxs, key = lambda maximum: maximum[1])

        yMax = maxsSortedY[-1][1]
        xMax = maxsSortedY[-1][0]

        try:

            yMax2 = maxsSortedY[-2][1]

            if yMax2 > yMax / doublesThreshold:
                isDouble = True

        except:
            isDouble = False

        if xMax < 600:
            isNpom = False
            isDouble = 'N/A'

    if plot == True or plot == 'all' or plot == 'double test':

        if isDouble == True:
            title = 'Double Peak'

        elif isDouble == False:
            title = 'Single Peak'

        elif isDouble == 'N/A':
            title = 'No Peak'

        plt.figure(figsize = (8, 6))
        plt.plot(x, y, 'purple', lw = 0.3, label = 'Raw')
        plt.xlabel('Wavelength (nm)', fontsize = 14)
        plt.ylabel('Intensity', fontsize = 14)
        plt.plot(xTrunc, ySmooth, 'g', label = 'Smoothed')
        plt.plot(xMins, yMins, 'ko', label = 'Minima')
        plt.plot(xMaxs, yMaxs, 'go', label = 'Maxima')
        plt.legend(loc = 0, ncol = 3, fontsize = 10)
        plt.ylim(0, ySmooth.max()*1.23)
        plt.xlim(450, 900)
        plt.title(title, fontsize = 16)
        plt.show()

    return isNpom, isDouble

def analyseNpomPeaks(x, y, cutoff = 1500, fs = 60000, doublesThreshold = 2, doublesDist = 0, monitorProgress = False, raiseExceptions = False,
                     transPeakPos = 533, plot = False):

    yRaw = np.array(y)
    xRaw = np.array(x)

    allMetadataKeys = ['NPoM?',
                      'Weird Peak?',
                      'Weird peak intensity (norm)',
                      'Weird peak wavelength',
                      'Weird peak FWHM',
                      'Weird peak intensity (raw)',
                      'Weird peak FWHM (raw)',
                      'Double Peak?',
                      'Transverse mode wavelength',
                      'Transverse mode intensity (norm)',
                      'Transverse mode intensity (raw)',
                      'Coupled mode wavelength',
                      'Coupled mode intensity (norm)',
                      'Coupled mode FWHM',
                      'Coupled mode FWHM (raw)',
                      'Coupled mode intensity (raw)',
                      'Intensity ratio (norm)',
                      'Intensity ratio (raw)',
                      'Raw data',
                      'Raw data (normalised)',
                      'Full Wavelengths',
                      'Raw data (truncated, normalised)',
                      'Smoothed data (truncated, normalised)',
                      'Initial guess',
                      'Best fit',
                      'Residuals',
                      'Final components',
                      'Final parameters',
                      'Wavelengths (truncated)',
                      'secondDerivative']

    metadata = {key : 'N/A' for key in allMetadataKeys}
    metadata['Raw data'] = yRaw
    metadata['Full Wavelengths'] = xRaw

    '''Testing if NPoM'''

    isNpom1 = testIfNpom(xRaw, yRaw)
    isNpom2, isDouble = testIfDouble(xRaw, yRaw, doublesThreshold = doublesThreshold, raiseExceptions = raiseExceptions, plot = plot)

    if isNpom1 == True and isNpom2 == True:
        isNpom = True

    else:
        isNpom = False

    metadata['Double Peak?'] = isDouble
    metadata['NPoM?'] = isNpom

    if monitorProgress == True:
        print 'NPoM:', isNpom

    if isNpom == True:

        weird = testIfWeirdPeak(x, y, factor = 1.3)
        metadata['Weird Peak?'] = weird

        isNpom, yRawNorm, initMinWl = normToTrans(xRaw, yRaw, transNorm = 1, troughNorm = 0.61)

        #plt.figure()
        #plt.plot(xRaw, yRaw)
        #plt.title('raw')
        #plt.show()

        #plt.figure()
        #plt.plot(xRaw, yRawNorm)
        #plt.title('norm')
        #plt.show()

        metadata['Raw data (normalised)'] = yRawNorm
        metadata['Transverse mode wavelength'] = transPeakPos

        rawPeakFindMetadata, weirdGauss, cmGauss = findMainPeaks(xRaw, yRaw, fwhmFactor = 1.1, plot = False, midpoint = 680, weirdPeak = weird)
        metadata['Coupled mode intensity (raw)'] = rawPeakFindMetadata['Coupled mode intensity']
        metadata['Coupled mode FWHM (raw)'] = rawPeakFindMetadata['Coupled mode FWHM']
        metadata['Coupled mode wavelength'] = rawPeakFindMetadata['Coupled mode wavelength']
        metadata['Weird peak intensity (raw)'] = rawPeakFindMetadata['Weird peak intensity']
        metadata['Weird peak FWHM (raw)'] = rawPeakFindMetadata['Weird peak FWHM']
        metadata['Weird peak wavelength'] = rawPeakFindMetadata['Weird peak wavelength']

        normPeakFindMetadata, weirdGauss, cmGauss = findMainPeaks(x, yRawNorm, fwhmFactor = 1.1, plot = False, midpoint = 680, weirdPeak = weird)
        metadata['Coupled mode intensity (norm)'] = normPeakFindMetadata['Coupled mode intensity']
        metadata['Coupled mode FWHM (norm)'] = normPeakFindMetadata['Coupled mode FWHM']
        metadata['Weird peak intensity (norm)'] = normPeakFindMetadata['Weird peak intensity']
        metadata['Weird peak FWHM (norm)'] = normPeakFindMetadata['Weird peak FWHM']

        if isDouble == True:
            metadata['Coupled mode FWHM'] = 'N/A'
            metadata['Coupled mode FWHM (raw)'] = 'N/A'

        xyRawTruncNorm = truncateSpectrum(x, yRawNorm)
        xTrunc = xyRawTruncNorm[0]
        yRawTruncNorm = xyRawTruncNorm[1]
        ySmoothTruncNorm = butterLowpassFiltFilt(yRawTruncNorm)
        yRawSmooth = butterLowpassFiltFilt(yRaw)

        transHeightRaw = yRawSmooth[abs(xRaw - transPeakPos).argmin()]
        transHeightNorm = ySmoothTruncNorm[abs(xTrunc - transPeakPos).argmin()]

        intensityRatio = metadata['Coupled mode intensity (norm)'] / transHeightNorm
        rawIntensityRatio = metadata['Coupled mode intensity (raw)'] / transHeightRaw

        metadata['Smoothed data (truncated, normalised)'] = ySmoothTruncNorm
        metadata['Raw data (truncated, normalised)'] = yRawTruncNorm
        metadata['Raw data (normalised)'] = yRawNorm
        metadata['Transverse mode intensity (norm)'] = transHeightNorm
        metadata['Transverse mode intensity (raw)'] = transHeightRaw
        metadata['Intensity ratio (from norm)'] = intensityRatio
        metadata['Intensity ratio (raw)'] = rawIntensityRatio

    return metadata

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

    tcMetadata['Coupled mode wavelength'] = cmPeakPos
    tcMetadata['Coupled mode intensity (norm)'] = cmHeight
    tcMetadata['Coupled mode intensity (raw)'] = cmHeightRaw

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

    tcMetadata['Transverse mode wavelength'] = transPeakPos
    transIndex = np.where(abs(x - transPeakPos) == abs(x - transPeakPos).min())[0][0]
    transIndexRaw = np.where(abs(xRaw - transPeakPos) == abs(xRaw - transPeakPos).min())[0][0]
    transHeight = ySmooth[transIndex]#Takes height of smoothed spectrum at transverse peak position
    transHeightRaw = yRawSmooth[transIndexRaw]
    tcMetadata['Transverse mode intensity (norm)'] = transHeight
    tcMetadata['Transverse mode intensity (raw)'] = transHeightRaw

    intensityRatio = cmHeight/transHeight
    rawIntensityRatio = cmHeightRaw/transHeightRaw
    tcMetadata['Intensity ratio (from norm)'] = intensityRatio
    tcMetadata['Intensity ratio (raw)'] = rawIntensityRatio

    return tcMetadata

def fitNpomSpectrum(x, y, cutoff = 1500, fs = 60000, lambd = 10**6.7, baselineP = 0.003, detectionThreshold = 0, doublesThreshold = 2,
                    doublesDist = 0, constrainPeakpos = False, printReport = False, plot = False, monitorProgress = False, fukkit = False,
                    simpleFit = True, raiseExceptions = False, transPeakPos = 533):

    yRaw = np.array(y)
    xRaw = np.array(x)

    allMetadataKeys = ['NPoM?',
                      'Weird Peak?',
                      'Weird peak intensity (norm)',
                      'Weird peak wavelength',
                      'Weird peak FWHM',
                      'Weird peak intensity (raw)',
                      'Double Peak?',
                      'Transverse mode wavelength',
                      'Transverse mode intensity (norm)',
                      'Transverse mode intensity (raw)',
                      'Coupled mode wavelength',
                      'Coupled mode intensity (norm)',
                      'Coupled mode FWHM',
                      'Coupled mode intensity (raw)',
                      'Intensity ratio (from norm)',
                      'Intensity ratio (raw)',
                      'Raw data',
                      'Raw data (normalised)',
                      'Full Wavelengths',
                      'Raw data (truncated, normalised)',
                      'Smoothed data (truncated, normalised)',
                      'Initial guess',
                      'Best fit',
                      'Residuals',
                      'Final components',
                      'Final parameters',
                      'Wavelengths (truncated)',
                      'secondDerivative']

    metadata = {key : 'N/A' for key in allMetadataKeys}
    metadata['Raw data'] = yRaw
    metadata['Full Wavelengths'] = xRaw

    '''Testing if NPoM'''

    isNpom1 = testIfNpom(xRaw, yRaw)
    isNpom2, isDouble = testIfDouble(x, y, doublesThreshold = doublesThreshold, raiseExceptions = raiseExceptions)

    if isNpom1 == True and isNpom2 == True:
        isNpom = True

    else:
        isNpom = False

    metadata['NPoM?'] = isNpom
    metadata['Double Peak?'] = isDouble

    if monitorProgress == True:
        print 'NPoM:', isNpom

    if isNpom == True:

        weird = testIfWeirdPeak(x, y, factor = 1.3)
        metadata['Weird Peak?'] = weird

        isNpom, yRawNorm, initMinWl = normToTrans(x, y, transNorm = 1, troughNorm = 0.61)

        metadata['Raw data (normalised)'] = yRawNorm
        metadata['Transverse mode wavelength'] = transPeakPos

        xTrunc, yTrunc = truncateSpectrum(x, yRawNorm, startWl = initMinWl, finishWl = 850)

        metadata['Raw data (truncated, normalised)'] = yTrunc
        metadata['Wavelengths (truncated)'] = xTrunc

        if monitorProgress == True:
            print '\nData baseline subtracted and normalised'

        ySmooth, indices, peakFindMetadata = multiPeakFind(xTrunc, yTrunc, cutoff = 1500, fs = 60000,
                                                            detectionThreshold = 0, returnAll = True,
                                                            monitorProgress = False)
        metadata.update(peakFindMetadata)

        '''Reassignment of x and y below is v. important'''

        y = yTrunc
        x = xTrunc

        if len(indices) != 0:
            out, peakFitMetadata = multiPeakFit(x, y, indices, needsSmoothing = True, cutoff = 1500, fs = 60000,
                                                returnAll = True, monitorProgress = monitorProgress,
                                                constrainPeakpos = constrainPeakpos)
            metadata.update(peakFitMetadata)

            isNpom, isDouble = testIfDouble(x, y, doublesThreshold = doublesThreshold, raiseExceptions = raiseExceptions)
            metadata['Double Peak?'] = isDouble

            if isDouble == False and weird == True:

                rawPeakFindMetadata, weirdGauss, cmGauss = findMainPeaks(xRaw, yRaw, fwhmFactor = 1.1, plot = False, midpoint = 680, weirdPeak = weird)
                metadata['Coupled mode intensity (raw)'] = rawPeakFindMetadata['Coupled mode intensity']
                metadata['Coupled mode FWHM (raw)'] = rawPeakFindMetadata['Coupled mode FWHM']
                metadata['Coupled mode wavelength'] = rawPeakFindMetadata['Coupled mode wavelength']
                metadata['Weird peak intensity (raw)'] = rawPeakFindMetadata['Weird peak intensity']
                metadata['Weird peak FWHM (raw)'] = rawPeakFindMetadata['Weird peak FWHM']
                metadata['Weird peak wavelength'] = rawPeakFindMetadata['Weird peak wavelength']

                normPeakFindMetadata, weirdGauss, cmGauss = findMainPeaks(x, y, fwhmFactor = 1.1, plot = False, midpoint = 680, weirdPeak = weird)
                metadata['Coupled mode intensity (norm)'] = rawPeakFindMetadata['Coupled mode intensity']
                metadata['Coupled mode FWHM (norm)'] = rawPeakFindMetadata['Coupled mode FWHM']
                metadata['Weird peak intensity (norm)'] = rawPeakFindMetadata['Weird peak intensity']
                metadata['Weird peak FWHM (raw)'] = rawPeakFindMetadata['Weird peak FWHM']

            if monitorProgress == True:
                print 'Fitting complete'

            if printReport == True:
                print 'Fit report:\n'
                print out.fit_report()

            tcMetadata = findTransAndCoupledMode(x, xRaw, yRaw, ySmooth, metadata['Final parameters'],
                                                 transGuess = transPeakPos, plot = plot, fukkit = fukkit)
            metadata.update(tcMetadata)
            transHeight = metadata['Transverse mode intensity (norm)']

            ySmooth /= transHeight
            yTrunc /= transHeight
            yRawNorm /= transHeight

            metadata['Smoothed data (truncated, normalised)'] = ySmooth
            metadata['Raw data (truncated, normalised)'] = yTrunc
            metadata['Raw data (normalised)'] = yRawNorm

        else:
            metadata['NPoM?'] = False

            if monitorProgress == True:
                print 'Not a NPoM'

            metadata['NPoM?'] = isNpom
            return DF_Spectrum(y, 'N/A', isNpom, 'N/A', 'N/A', metadata)

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

def plotHistogram(outputFile, histName = 'Histogram', startWl = 450, endWl = 987, binNumber = 80, plot = True,
                  minBinFactor = 5, closeFigures = False, irThreshold = 8, which = 'all', plotTitle = ''):

    rootDir = os.getcwd()

    try:
        os.stat('%s/Histograms' % rootDir)

    except:
        os.mkdir('%s/Histograms' % rootDir)

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

    print '\t\t%s spectra' % len(spectra)

    for n, spectrum in enumerate(outputFile['Fitted spectra']):

        x = outputFile['Fitted spectra/%s/Raw/Raw data (normalised)' % spectrum].attrs['wavelengths'][()]

        if type(x) != str:
            break

    #try:
    spectraNames = [spectrum for spectrum in spectra if spectrum[:8] == 'Spectrum']

    binSize = (endWl - startWl) / binNumber
    bins = np.linspace(startWl, endWl, num = binNumber)
    frequencies = np.zeros(len(bins))
    binPops = np.zeros(len(bins))
    yDataBinned = [np.zeros(len(x)) for f in frequencies]
    yDataRawBinned = [np.zeros(len(x)) for f in frequencies]
    binnedSpectraList = {binStart : [] for binStart in bins}

    for n, spectrum in enumerate(spectraNames):

        #print spectrum

        for nn, binStart in enumerate(bins):

            #print [attr for attr in spectra[spectrum].attrs]
            cmPeakPos = outputFile['Fitted spectra'][spectrum].attrs['Coupled mode wavelength']
            #print cmPeakPos
            intensityRatio = outputFile['Fitted spectra'][spectrum].attrs['Intensity ratio (from norm)']
            yData = outputFile['Fitted spectra'][spectrum]['Raw/Raw data (normalised)']
            yDataRaw = outputFile['Fitted spectra'][spectrum]['Raw/Raw data']

            if cmPeakPos != 'N/A' and binStart <= cmPeakPos < binStart + binSize and 600 < cmPeakPos < 850:
                frequencies[nn] += 1

                if intensityRatio < irThreshold and yData[()].min() > -1:
                    yDataBinned[nn] += yData
                    yDataRawBinned[nn] += yDataRaw
                    binPops[nn] += 1

                binnedSpectraList[binStart].append(spectrum)

    for n, yDataSum in enumerate(yDataBinned):
        yDataBinned[n] /= binPops[n]
        yDataRawBinned[n] /= binPops[n]

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

        yDataPlot = []
        freqsPlot = []
        binsPlot = []
        yMax = 0
        yMin = 7

        for n, yDatum in enumerate(yDataBinned):

            if frequencies[n] > minBin:
                yDataPlot.append(yDatum)
                freqsPlot.append(frequencies[n])
                binsPlot.append(bins[n])

        colors = [cmap(256 - n*(256/len(yDataPlot))) for n, yDataSum in enumerate(yDataPlot)][::-1]

        for n, yDataSum in enumerate(yDataPlot):

            ySmooth = reduceNoise(yDataSum, factor = 7)
            currentYMax = truncateSpectrum(x, ySmooth)[1].max()
            currentYMin = truncateSpectrum(x, ySmooth)[1].min()

            if currentYMax > yMax:
                yMax = currentYMax

            if currentYMin < yMin:
                yMin = currentYMin

            ax1.plot(x, ySmooth, lw = 0.7, color = colors[n])

        ax1.set_ylim(0.8 * yMin, yMax * 1.45)
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
        plt.title('%s: %s' % (plotTitle, which))

        fig.tight_layout()

        if not histName.endswith('.png'):
            histName += '.png'

        fig.savefig('%s/Histograms/%s' % (rootDir, histName), bbox_inches = 'tight')

        if closeFigures == True:
            plt.close('all')

    return frequencies, bins, yDataBinned, yDataRawBinned, binnedSpectraList, x

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
    sigma = out.params['sigma'].value

    return resonance, stderr, fwhm, sigma

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
                        closeFigures = False, normalised = True, filterWeird = False, plotTitle = ''):

    rootDir = os.getcwd()

    try:
        os.stat('%s/Intensity ratios' % rootDir)

    except:
        os.mkdir('%s/Intensity ratios' % rootDir)

    if plot == True:
        print '\nPlotting intensity ratios...'

    else:
        print '\n Gathering intensity ratios...'

    if filterWeird == True:
        print '\t(Filtering out weird peaks)'

    allSpectra = outputFile['Fitted spectra']

    cmPeakPositions = []
    intensityRatios = []

    spectra = sorted([spectrum for spectrum in allSpectra if spectrum[:8] == 'Spectrum'],
                     key = lambda spectrum: int(spectrum[9:]))

    for spectrum in spectra:
        #print '\n', spectrum
        spectrum = allSpectra[spectrum]

        cmPeakPos = spectrum.attrs['Coupled mode wavelength']

        if normalised == True:
            intensityRatio = spectrum.attrs['Intensity ratio (from norm)']
            imgSuffix = 'normalised'

        else:
            intensityRatio = spectrum.attrs['Intensity ratio (raw)']
            imgSuffix = 'raw'

        if filterWeird == True:

            irImgName = 'Intensity Ratios (filtered, %s).png' % imgSuffix

            if (spectrum.attrs['NPoM?'] == True and spectrum.attrs['Double Peak?'] == False and
                cmPeakPos != 'N/A' and cmPeakPos < 849 and intensityRatio != 'N/A' and
                spectrum.attrs['Weird Peak?'] == False) == True:

                cmPeakPositions.append(cmPeakPos)
                intensityRatios.append(intensityRatio)

        elif filterWeird == False:
            irImgName = 'Intensity Ratios (%s).png' % imgSuffix

            if (spectrum.attrs['NPoM?'] == True and spectrum.attrs['Double Peak?'] == False and
                cmPeakPos != 'N/A' and cmPeakPos < 849 and intensityRatio != 'N/A') == True:

                cmPeakPositions.append(cmPeakPos)
                intensityRatios.append(intensityRatio)

    if normalised == True:
        imgSuffix = 'normalised'

    elif normalised == False:
        imgSuffix = 'raw'

    if filterWeird == True:

        irImgName = 'Intensity Ratios (filtered, %s).png' % imgSuffix

    elif filterWeird == False:
        irImgName = 'Intensity Ratios (%s).png' % imgSuffix

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

            ax.scatter(xFilt, yFilt, marker = '+', color = 'r', s = 3)
            ax = sns.kdeplot(xFilt, yFilt, shade=True, ax=ax, gridsize=200, cmap='Reds', cbar = True,
                             shade_lowest = False, linewidth = 20, alpha = 0.6, clim=(0.5, 1))

            ax.set_ylim(0, 10)
            ax.set_ylabel('Intensity Ratio', fontsize = 18)
            ax.tick_params(which = 'both', labelsize = 15)
            ax.set_xlim(550, 900)
            ax.set_xlabel('Coupled Mode Resonance', fontsize = 18)
            #ax.set_xticksize(fontsize = 15)
            plt.title('%s%s' % (plotTitle, irImgName))

            fig.tight_layout()
            fig.savefig('%s/Intensity ratios/%s' % (rootDir, irImgName), bbox_inches = 'tight')

            if closeFigures == True:
                plt.close('all')

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
            plt.title('%s%s' % (plotTitle, irImgName))

            fig.tight_layout()
            fig.savefig('%s/Intensity ratios/%s' % (rootDir, irImgName), bbox_inches = 'tight')

            if closeFigures == True:
                plt.close('all')

            print '\tIntensity ratios plotted'

    else:
        print 'Intensity ratios gathered'

    return intensityRatios, cmPeakPositions

def visualiseIntensityRatios(outputFile):

    '''OutputFile = an open h5py.File or nplab.datafile.DataFile object with read/write permission'''
    '''Plots all spectra in separate tree with lines indicating calculated peak heights and positions'''

    irVisStart = time.time()

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

    irVisEnd = time.time()

    timeElapsed = irVisEnd - irVisStart

    print '\tIntensity ratios visualised in %s seconds' % timeElapsed

def updateTransAndCoupledMode(outputFile, transGuess = 533, transRange = [500, 550], reNormalise = True):
    '''Doesn't work properly yet - needs fixing'''

    print '\nUpdating trans and coupled mode parameters'

    gSpectra = outputFile['Fitted spectra']

    allSpectra = sorted([spectrum for spectrum in outputFile['Fitted spectra']],
                        key = lambda spectrum: int(spectrum[9:]))
    allSpectra = [spectrum for spectrum in allSpectra if gSpectra[spectrum].attrs['NPoM?'] == True]

    for spectrum in allSpectra:
        spectrum = gSpectra[spectrum]
        x = spectrum['Fit/Smoothed data (truncated, normalised)'].attrs['wavelengths'][()]
        xRaw = spectrum['Raw/Raw data'].attrs['wavelengths'][()]
        yRaw = spectrum['Raw/Raw data'][()]
        ySmooth = np.array(spectrum['Fit/Smoothed data (truncated, normalised)'][()])
        fitComps = spectrum['Fit/Final components/']
        fitParams = {'g%s' % n : {key : fitComps[n].attrs[key] for key in fitComps[n].attrs.keys() if
                                  key != 'wavelengths'} for n in fitComps}

        tcMetadata = findTransAndCoupledMode(x, xRaw, yRaw, ySmooth, fitParams, transGuess = transGuess,
                                             transRange = transRange, plot = False)

        spectrum.attrs['Transverse mode intensity (norm)'] = tcMetadata['Transverse mode intensity (norm)']
        spectrum.attrs['Transverse mode intensity (raw)'] = tcMetadata['Transverse mode intensity (raw)']
        spectrum.attrs['Transverse mode wavelength'] = tcMetadata['Transverse mode wavelength']
        spectrum.attrs['Coupled mode intensity (norm)'] = tcMetadata['Coupled mode intensity (norm)']
        spectrum.attrs['Coupled mode intensity (raw)'] = tcMetadata['Coupled mode intensity (raw)']
        spectrum.attrs['Coupled mode wavelength'] = tcMetadata['Coupled mode wavelength']
        spectrum.attrs['Intensity ratio'] = tcMetadata['Intensity ratio (from norm)']
        spectrum.attrs['Intensity ratio (raw)'] = tcMetadata['Intensity ratio (raw)']

        if reNormalise == True:

            transHeight = tcMetadata['Transverse mode intensity (norm)']

            datasetsToUpdate = ['Fit/Best fit',
                                'Fit/Final components',
                                'Fit/Raw data (truncated, normalised)',
                                'Fit/Smoothed data (truncated, normalised)',
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
        plt.close('all')

    #except Exception as e:
    #    print 'Plotting of %s failed because %s' % (imgName, str(e))
    #    img = 'N/A'

    stackEndTime = time.time()
    timeElapsed = stackEndTime - stackStartTime

    print '\tInitial stack plotted in %s seconds' % timeElapsed

def plotStackedMap(spectraSorted, imgName = 'Stack', plotTitle = 'Stack', closeFigures = False):

    rootDir = os.getcwd()

    try:
        os.stat('%s/Stacks' % rootDir)

    except:
        os.mkdir('%s/Stacks' % rootDir)

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
            plt.title(plotTitle)

        else:
            plt.title(plotTitle)
            imgName = '%s.png' % imgName

        fig.savefig('%s/Stacks/%s' % (rootDir, imgName), bbox_inches = 'tight')

        if closeFigures == True:
            plt.close('all')

    except Exception as e:
        print 'Plotting of %s failed because %s' % (imgName, str(e))

def plotAllStacks(outputFile, plotTitle = '', closeFigures = False, filterWeird = True):

    print '\nPlotting stacked spectral maps...'

    stackStartTime = time.time()

    gSpectra = outputFile['Fitted spectra']
    outputFile.create_group('Statistics/Stacks')

    title = plotTitle

    if filterWeird == True:
        '''Spectra without weird peaks'''

        cmWlName = 'Coupled mode wavelength'
        imgName = 'Stack (No weird peaks)'
        plotTitle = '%s%s' % (title, imgName)

        spectra = [gSpectra[spectrum] for spectrum in gSpectra if spectrum[:8] == 'Spectrum' and
                   gSpectra[spectrum].attrs['Weird Peak?'] == False and
                   gSpectra[spectrum].attrs[cmWlName] != 'N/A']
        spectraSorted = sorted(spectra, key = lambda spectrum: spectrum.attrs[cmWlName])
        plotStackedMap(spectraSorted, imgName = imgName, plotTitle = plotTitle, closeFigures = closeFigures)

    '''By order of measurement'''

    spectra = [spectrum for spectrum in gSpectra if spectrum[:8] == 'Spectrum']
    spectraSorted = sorted(spectra, key = lambda spectrum: int(spectrum[9:]))
    spectraSorted = [gSpectra[spectrum] for spectrum in spectraSorted]
    imgName = 'Stack (all)'
    plotTitle = '%s%s' % (title, imgName)
    plotStackedMap(spectraSorted, imgName = imgName, plotTitle = plotTitle, closeFigures = closeFigures)
    '''By CM wavelength'''

    cmWlName = 'Coupled mode wavelength'
    imgName = 'Stack (CM wavelength)'
    plotTitle = '%s%s' % (title, imgName)

    spectra = [gSpectra[spectrum] for spectrum in gSpectra if spectrum[:8] == 'Spectrum' and
               gSpectra[spectrum].attrs[cmWlName] != 'N/A']
    spectraSorted = sorted(spectra, key = lambda spectrum: spectrum.attrs[cmWlName])

    plotStackedMap(spectraSorted, imgName = imgName, plotTitle = plotTitle, closeFigures = closeFigures)

    '''By TM wavelength'''

    tmWlName = 'Transverse mode wavelength'
    imgName = 'Stack (TM wavelength)'
    plotTitle = '%s%s' % (title, imgName)

    spectra = [gSpectra[spectrum] for spectrum in gSpectra if spectrum[:8] == 'Spectrum' and
               gSpectra[spectrum].attrs[tmWlName] != 'N/A']

    spectraSorted = sorted(spectra, key = lambda spectrum: spectrum.attrs[tmWlName])

    plotStackedMap(spectraSorted, imgName = imgName, plotTitle = plotTitle, closeFigures = closeFigures)

    '''By intensity ratio'''

    irName = 'Intensity ratio (raw)'
    imgName = 'Stack (intensity ratio)'
    plotTitle = '%s%s' % (title, imgName)

    spectra = [gSpectra[spectrum] for spectrum in gSpectra if spectrum[:8] == 'Spectrum' and
               gSpectra[spectrum].attrs[irName] != 'N/A']
    spectraSorted = sorted(spectra, key = lambda spectrum: spectrum.attrs[irName])

    plotStackedMap(spectraSorted, imgName = imgName, plotTitle = plotTitle, closeFigures = closeFigures)

    '''Doubles in order of measurement'''

    spectra = [spectrum for spectrum in gSpectra if spectrum[:8] == 'Spectrum' and
               gSpectra[spectrum].attrs['Double Peak?'] == True]

    if len(spectra) > 0:

        spectraSorted = sorted(spectra, key = lambda spectrum: int(spectrum[9:]))
        spectraSorted = [gSpectra[spectrum] for spectrum in spectraSorted]

        '''By order of measurement'''

        imgName = 'Stack (all doubles)'
        plotTitle = '%s%s' % (title, imgName)
        plotStackedMap(spectraSorted, imgName = imgName, plotTitle = plotTitle, closeFigures = closeFigures)

        '''Doubles by CM wavelength'''

        cmWlName = 'Coupled mode wavelength'
        imgName = 'Stack (Doubles by CM wavelength)'
        plotTitle = '%s%s' % (title, imgName)
        spectra = [gSpectra[spectrum] for spectrum in gSpectra if spectrum[:8] == 'Spectrum' and
                   gSpectra[spectrum].attrs[cmWlName] != 'N/A' and
                   gSpectra[spectrum].attrs['Double Peak?'] == True]
        spectraSorted = sorted(spectra, key = lambda spectrum: spectrum.attrs[cmWlName])

        plotStackedMap(spectraSorted, imgName = imgName, plotTitle = plotTitle, closeFigures = closeFigures)

        '''Doubles by TM wavelength'''

        tmWlName = 'Transverse mode wavelength'
        imgName = 'Stack (Doubles by TM wavelength)'
        plotTitle = '%s%s' % (title, imgName)

        spectra = [gSpectra[spectrum] for spectrum in gSpectra if spectrum[:8] == 'Spectrum' and
                   gSpectra[spectrum].attrs[tmWlName] != 'N/A' and
                   gSpectra[spectrum].attrs['Double Peak?'] == True]

        spectraSorted = sorted(spectra, key = lambda spectrum: spectrum.attrs[tmWlName])

        plotStackedMap(spectraSorted, imgName = imgName, plotTitle = plotTitle, closeFigures = closeFigures)

        '''Doubles by intensity ratio'''

        irName = 'Intensity ratio (raw)'
        imgName = 'Stack (Doubles by intensity ratio)'
        plotTitle = '%s%s' % (title, imgName)

        spectra = [gSpectra[spectrum] for spectrum in gSpectra if spectrum[:8] == 'Spectrum' and
                   gSpectra[spectrum].attrs[irName] != 'N/A' and
                   gSpectra[spectrum].attrs['Double Peak?'] == True]
        spectraSorted = sorted(spectra, key = lambda spectrum: spectrum.attrs[irName])

        plotStackedMap(spectraSorted, imgName = imgName, plotTitle = plotTitle, closeFigures = closeFigures)

    else:
        print '\tNo doubles to plot'

    stackEndTime = time.time()

    timeElapsed = stackEndTime - stackStartTime

    print '\tStacks plotted in %s seconds' % timeElapsed

def sortSpectra(outputFile, replace = False, method = 'basic', npomLower = 0.1, npomUpper = 2.5, NpomThreshold = 1.5,
                doublesThreshold = 2, minDoublesDist = 30, cmPosThreshold = 650, monitorProgress = False, doublesPlot = False, returnAll = False,
                weirdFactor = 1.3, weirdPlot = False, raiseExceptions = False):

    specSortStart = time.time()
    print '\nSorting spectra...'

    gAll = outputFile['All spectra']

    if replace == False and method == 'basic':

        if 'NPoMs' in gAll:
            print '\tSpectra already sorted'
            return

    elif method == 'full' or replace == True:

        if method == 'full' and replace == False:
            print '\tFull sorting in place. Data will be overwritten'

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

               isNpom, isDouble = testIfDouble(xRaw, yRaw, doublesThreshold = doublesThreshold, plot = doublesPlot, raiseExceptions = raiseExceptions)
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

def plotHistAndFit(outputFile, which = 'all', plotTitle = '', startWl = 450, endWl = 987, binNumber = 80, plot = True,
                  minBinFactor = 5, closeFigures = False, irThreshold = 8):

    frequencies, bins, yDataBinned, yDataRawBinned, binnedSpectraList, histyWl = plotHistogram(outputFile,
                                                              histName = 'Histogram (%s)' % which,
                                                              minBinFactor = minBinFactor, plotTitle = plotTitle,
                                                              closeFigures = closeFigures, which = which, irThreshold = irThreshold)

    try:
        avgResonance, stderr, fwhm, sigma = histyFit(frequencies, bins)
        gHist = outputFile.create_group('Statistics/Histogram/%s' % which)
        gHist.attrs['Average resonance'] = avgResonance
        gHist.attrs['Error'] = stderr
        gHist.attrs['FWHM'] = fwhm
        gHist.attrs['Standard deviation'] = sigma

        dBins = gHist.create_dataset('Bins', data = bins)
        dFreq = gHist.create_dataset('Frequencies', data = frequencies)
        dFreq.attrs['wavelengths'] = dBins
        gSpectraBinned = gHist.create_group('Binned y data/')
        binSize = bins[1] - bins[0]
        binsSorted = sorted(bins, key = lambda binStart: float(binStart))

        for binStart in binsSorted:
            binnedSpectraList[binStart].sort(key = lambda spectrum: int(spectrum[9:]))

        for n, binStart in enumerate(binsSorted):
            if len(binnedSpectraList[binStart]) > 0:

                binEnd = binStart + binSize

                if n < 10:
                    binName = 'Bin 0%s' % n

                else:
                    binName = 'Bin %s' % n

                gBin = gSpectraBinned.create_group(binName)
                gBin.attrs['Bin start (nm)'] = binStart
                gBin.attrs['Bin end (nm)'] = binEnd
                dSum = gBin.create_dataset('Sum', data = yDataRawBinned[n])
                dSum.attrs['wavelengths'] = histyWl

                for spectrum in binnedSpectraList[binStart]:
                    yDataBin = outputFile['Fitted spectra/%s/Raw/Raw data' % spectrum]
                    dSpec = gBin.create_dataset(spectrum, data = yDataBin)
                    dSpec.attrs['wavelengths'] = yDataBin.attrs['wavelengths']
                    dSpec.attrs.update(outputFile['Fitted spectra'][spectrum].attrs)

    except Exception as e:
        print e
        avgResonance = 'N/A'
        stderr = 'N/A'
        fwhm = 'N/A'

def pointyPeakStats(outputFile, closeFigures = True, plotTitle = ''):
    pointyPeakStart = time.time()

    rootDir = os.getcwd()

    try:
        os.stat('%s/Peak stats' % rootDir)

    except:
        os.mkdir('%s/Peak stats' % rootDir)

    print '\nAnalysing funky peaks'

    allNpoms = outputFile['All spectra/NPoMs/All NPoMs']
    gStats = outputFile['Statistics']

    if 'Peak stats' in gStats:
        try:
            del gStats['Peak stats']

        except:
            pass

    gStats.create_group('Peak stats')

    weirdFwhmsRaw = []
    weirdFwhmsNorm = []
    weirdPositions = []
    weirdHeightsRaw = []
    weirdHeightsNorm = []
    cmFwhmsRaw = []
    cmFwhmsNorm = []
    cmPositions = []
    cmHeightsRaw = []
    cmHeightsNorm = []

    for spectraName in allNpoms:
        attrNames = ['Weird peak FWHM (raw)', 'Weird peak FWHM (norm)', 'Weird peak wavelength', 'Weird peak intensity (raw)',
                     'Weird peak intensity (norm)', 'Coupled mode FWHM (raw)', 'Coupled mode FWHM (norm)',
                     'Coupled mode wavelength', 'Coupled mode intensity (raw)', 'Coupled mode intensity (norm)']
        attrLists = [weirdFwhmsRaw, weirdFwhmsNorm, weirdPositions, weirdHeightsRaw, weirdHeightsNorm, cmFwhmsRaw, cmFwhmsNorm,
                     cmPositions, cmHeightsRaw, cmHeightsNorm]

        for n, attrName in enumerate(attrNames):
            attr = allNpoms[spectraName].attrs[attrName]

            if attr == 'N/A':
                attr = np.nan

            attrLists[n].append(attr)

    for n, attrName in enumerate(attrNames):

        for m, attrlist in enumerate(attrLists):
            xName = attrNames[m]
            yName = attrNames[n]

            if m <= n or xName[:-6] == yName[:-6]:
                continue

            else:
                imgName = '%s vs %s.png' % (xName, yName)
                plotTitle = '%s%s' % (plotTitle, imgName)
                y = attrLists[n]
                x = attrLists[m]

                fig = plt.figure()
                plt.scatter(x, y, s = 14)
                plt.xlabel(xName, fontsize = 14)
                plt.ylabel(yName, fontsize = 14)
                plt.title(plotTitle)

                try:
                    fig.tight_layout()

                except:
                    pass

                fig.savefig('%s/Peak stats/%s' % (rootDir, imgName), bbox_inches = 'tight')

                if closeFigures == True:
                    plt.close('all')

    pointyPeakEnd = time.time()
    timeElapsed = pointyPeakEnd - pointyPeakStart

    print '\tFunky peaks analysed in %s seconds' % timeElapsed

def doubBoolsHists(outputFile, binNumber = 80, plot = True, closeFigures = False, plotTitle = ''):
    doubBoolsStart = time.time()

    print '\nAnalysing doubles stats'

    rootDir = os.getcwd()

    try:
        os.stat('%s/Doubles stats' % rootDir)

    except:
        os.mkdir('%s/Doubles stats' % rootDir)

    allNpoms = outputFile['All spectra/NPoMs/All NPoMs']
    gStats = outputFile['Statistics']

    if 'Doubles stats' in gStats:
        print 'Doubles stats exists'

        try:
            del gStats['Double stats']
            gDoubleStats = gStats.create_group('Double stats')

        except:
            pass

        try:
            gDoubleStats = gStats.create_group('Double stats')

        except:
            pass
    try:
        del gStats['Double stats']
        gDoubleStats = gStats.create_group('Double stats')

    except:
        pass

    try:
        gDoubleStats = gStats.create_group('Double stats')

    except:
        pass

    weirdFwhmsRaw = []
    weirdFwhmsNorm = []
    weirdPositions = []
    weirdHeightsRaw = []
    weirdHeightsNorm = []
    doubBools = []

    for spectraName in allNpoms:
        attrNames = ['Weird peak FWHM (raw)', 'Weird peak FWHM (norm)', 'Weird peak wavelength', 'Weird peak intensity (raw)',
                     'Weird peak intensity (norm)', 'Double Peak?']
        attrNamesShort = ['FWHM', 'FWHM', 'Peakpos', 'Peak height', 'Peak height']
        attrLists = [weirdFwhmsRaw, weirdFwhmsNorm, weirdPositions, weirdHeightsRaw, weirdHeightsNorm, doubBools]

        for n, attrName in enumerate(attrNames):
            attr = allNpoms[spectraName].attrs[attrName]

            if attr == 'N/A' or attr < 0:
                attr = 0

            attrLists[n].append(attr)

    start = 0

    for i, attrList in enumerate(attrLists[start:-1]):
        i += start

        startWl = min(attrList)
        endWl = max(attrList)
        binSize = (endWl - startWl) / binNumber
        bins = np.linspace(startWl, endWl, num = binNumber)
        totalFreqs = np.zeros(len(bins))
        doubleFreqs = np.zeros(len(bins))
        binnedSpectraList = {binStart : [] for binStart in bins}

        for n, spectraName in enumerate(allNpoms):

            for nn, binStart in enumerate(bins):
                #print binStart

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
        imgName = 'P(Double) vs %s.png' % attrNames[i]
        plotTitle = plotTitle + imgName
        plt.title(plotTitle)

        try:
            fig.tight_layout()

        except:
            pass

        fig.savefig('%s/Doubles stats/%s' % (rootDir, imgName), bbox_inches = 'tight')

        gPlot = gDoubleStats.create_group(attrNames[i])
        gPlot.attrs[attrNames[i]] = attrList
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

    if closeFigures == True:
        plt.close('all')

    doubBoolsEnd = time.time()
    timeElapsed = doubBoolsEnd - doubBoolsStart
    print '\tDoubles stats done in %s seconds' % timeElapsed

def peakAverages(outputFile, singleBin = False, peakPos = 0):
    '''If singleBin = False, function averages peak data from all NPoM spectra'''
    '''If True, specify wavelength and function will average peak data from all spectra contained in that histogram bin'''

    peakAvgStart = time.time()

    print '\nCollecting peak averages'

    allNpoms = outputFile['All spectra/NPoMs/All NPoMs']

    hists = ['all', 'no doubles', 'filtered']

    for histName in hists:

        yDataBinned = outputFile['Statistics/Histogram/%s/Binned y data' % histName]

        if singleBin == False:

            npomList = [yDataBinned[binName] for binName in yDataBinned]
            yDataBinned = outputFile['Statistics/Histogram/%s/Binned y data' % histName]

            npomList.append(allNpoms)

            for listName in npomList:
                weirdFwhmsRaw = []
                weirdFwhmsNorm = []
                weirdPositions = []
                weirdHeightsRaw = []
                weirdHeightsNorm = []
                cmFwhmsRaw = []
                cmFwhmsNorm = []
                cmPositions = []
                cmHeightsRaw = []
                cmHeightsNorm = []
                tmHeightsRaw = []
                irsNorm = []
                irsRaw = []
                attrAvgs = {}

                for spectraName in listName:

                    if spectraName != 'Sum':
                        attrNames = ['Weird peak FWHM (raw)', 'Weird peak FWHM (norm)', 'Weird peak wavelength', 'Weird peak intensity (raw)',
                                     'Weird peak intensity (norm)', 'Coupled mode FWHM (raw)', 'Coupled mode FWHM (norm)', 'Coupled mode wavelength',
                                     'Coupled mode intensity (raw)', 'Coupled mode intensity (norm)', 'Transverse mode intensity (raw)',
                                     'Intensity ratio (from norm)', 'Intensity ratio (raw)']
                        attrLists = [weirdFwhmsRaw, weirdFwhmsNorm, weirdPositions, weirdHeightsRaw, weirdHeightsNorm, cmFwhmsRaw, cmFwhmsNorm,
                                     cmPositions, cmHeightsRaw, cmHeightsNorm, tmHeightsRaw, irsNorm, irsRaw]

                        for n, attrName in enumerate(attrNames):
                            attr = allNpoms[spectraName].attrs[attrName]

                            if attr != 'N/A':
                                attrLists[n].append(attr)

                for n, attrList in enumerate(attrLists):
                    attrList = np.array(attrList)

                    if len(attrList) != 0:
                        attrAvg = np.average(attrList)

                    else:

                        if 'Weird peak intensity' in attrNames[n]:
                            attrAvg = 0

                        else:
                            attrAvg = 'N/A'

                    attrAvgs[attrNames[n] + '(average)'] = attrAvg

                listName.attrs.update(attrAvgs)

        elif singleBin == True:

            for binName in yDataBinned:
                binStart = yDataBinned[binName].attrs['Bin start (nm)']
                binEnd = yDataBinned[binName].attrs['Bin end (nm)']

                if binStart < peakPos < binEnd:
                    npomList = yDataBinned[binName]
                    break

            weirdFwhmsRaw = []
            weirdFwhmsNorm = []
            weirdPositions = []
            weirdHeightsRaw = []
            weirdHeightsNorm = []
            cmFwhmsRaw = []
            cmFwhmsNorm = []
            cmPositions = []
            cmHeightsRaw = []
            cmHeightsNorm = []
            tmHeightsRaw = []
            attrAvgs = {}

            for spectraName in npomList:
                attrNames = ['Weird peak FWHM (raw)', 'Weird peak FWHM (norm)', 'Weird peak wavelength', 'Weird peak intensity (raw)',
                             'Weird peak intensity (norm)', 'Coupled mode FWHM (raw)', 'Coupled mode FWHM (norm)', 'Coupled mode wavelength',
                             'Coupled mode intensity (raw)', 'Coupled mode intensity (norm)', 'Transverse mode intensity (raw)',
                             'Intensity ratio (from norm)', 'Intensity ratio (raw)']
                attrLists = [weirdFwhmsRaw, weirdFwhmsNorm, weirdPositions, weirdHeightsRaw, weirdHeightsNorm, cmFwhmsRaw, cmFwhmsNorm,
                             cmPositions, cmHeightsRaw, cmHeightsNorm, tmHeightsRaw, irsNorm, irsRaw]

                for n, attrName in enumerate(attrNames):
                    print attrName
                    attr = allNpoms[spectraName].attrs[attrName]

                    if attr != 'N/A':
                        attrLists[n].append(attr)

            for n, attrList in enumerate(attrLists):
                attrList = np.array(attrList)
                attrAvgs[attrNames[n]] = np.average(attrList)

            npomList.attrs.update(attrAvgs)

    peakAvgEnd = time.time()
    timeElapsed = peakAvgEnd - peakAvgStart

    print '\tPeak averages collected in %s seconds' % timeElapsed

def analyseRepresentative(outputFile):
    print '\nCollecting representative spectrum info'

    hists = ['all', 'filtered', 'no doubles']

    for histName in hists:
        gHist = outputFile['Statistics/Histogram'][histName]
        cmPeakPos = gHist.attrs['Average resonance']
        gBins = gHist['Binned y data']
        binNames = [binName for binName in gBins]
        binPops = np.array([len(gBins[gBin]) for gBin in gBins])
        biggestBin = binNames[binPops.argmax()]
        print '\t%s' % histName
        print '\t\tBin with largest population:', biggestBin
        avgBin = False

        for binName in gBins:
            binStart = gBins[binName].attrs['Bin start (nm)']
            binEnd = gBins[binName].attrs['Bin end (nm)']

            if binStart < cmPeakPos < binEnd:
                print '\t\tMain/average peak in %s\n' % binName
                avgBin = binName

                break

        analStyles = ['Average', 'Max']
        binStyles = [avgBin, biggestBin]

        for n, binName in enumerate(binStyles):

            if binName != False:

                representativeSpectrum = gBins[binName]['Sum']
                ySmooth = butterLowpassFiltFilt(representativeSpectrum)
                x = representativeSpectrum.attrs['wavelengths']
                repMetadata = analyseNpomPeaks(x, representativeSpectrum)
                cmRegMinWl = cmPeakPos - 25
                cmRegMaxWl = cmPeakPos + 25
                cmRegion = truncateSpectrum(x, ySmooth, cmRegMinWl, cmRegMaxWl)
                cmHeightRaw = cmRegion[1].max()
                repSpecNorm = representativeSpectrum / cmHeightRaw
                weirdHeight = gBins[binName].attrs['Weird peak intensity (raw)(average)']
                weirdHeight /= cmHeightRaw

                try:
                   del outputFile['Statistics/Representative spectrum (%s, %s)' % (analStyles[n], histName)]

                except:
                    pass

                dRep = outputFile['Statistics'].create_dataset('Representative spectrum (%s, %s)' % (analStyles[n], histName), data = repSpecNorm)
                dRep.attrs['Bin number'] = binName
                dRep.attrs['wavelengths'] = x
                dRep.attrs['Raw'] = representativeSpectrum[()]
                dRep.attrs['Weird peak height (norm to CM)'] = weirdHeight
                dRepAttrs = {key : gBins[binName].attrs[key] for key in gBins[binName].attrs.keys()}
                dRep.attrs.update(dRepAttrs)
                dRep.attrs.update(repMetadata)

    print '\tRepresentative spectrum info collected'

def doStats(outputFile, minBinFactor = 5, sortSpec = True, replaceWhenSorting = False, sortMethod = 'basic', stacks = True,
            hist = True, intensityRatios = True, pointyPeaks = True, doubBools = True, peakAvgs = True, analRep = True, raiseExceptions = False,
            closeFigures = False, irThreshold = 8):

    if 'Statistics' not in outputFile:
        outputFile.create_group('Statistics')

    try:
        gSpectra = outputFile['Fitted spectra']
        datePrepared = gSpectra.attrs['Date']
        metalCentre = gSpectra.attrs['Metal centre']
        subs = bool(gSpectra.attrs['Substituted?'])

        if subs == True:
            subs = '(Subs)'

        solvent = gSpectra.attrs['Deposition solvent']
        depositionTime = gSpectra.attrs['Deposition time']

        plotTitle = '%s: %s %s %s %s min\n' % (datePrepared, metalCentre, subs, solvent, depositionTime)

    except Exception as e:

        if 'date' in e:
            e = 'no date was specified'

        print 'Couldn\'t extract plot title because %s' % e
        plotTitle = ''

    if sortSpec == True:
        sortSpectra(outputFile, replace = replaceWhenSorting, method = sortMethod)

    if stacks == True:

        if 'Stacks' in outputFile['Statistics']:
            try:
                del outputFile['Statistics/Stacks']

            except:
                pass

        plotAllStacks(outputFile, closeFigures = closeFigures, plotTitle = plotTitle)

    if hist == True:

        histStartTime = time.time()

        if 'Histogram' in outputFile['Statistics']:
            try:
                del outputFile['Statistics/Histogram']

            except:
                pass

        for histyWhich in ['all', 'no doubles', 'filtered']:
            plotHistAndFit(outputFile, which = histyWhich, minBinFactor = minBinFactor, plotTitle = plotTitle,
                           closeFigures = closeFigures, irThreshold = irThreshold)

        histEndTime = time.time()
        timeElapsed = histEndTime - histStartTime

        print '\n\tAll histograms plotted (hopefully) in %s seconds' % timeElapsed

    if intensityRatios == True:

        irStart = time.time()

        try:
            del outputFile['Statistics/Intensity ratios']

        except:
            pass

        gIr = outputFile.create_group('Statistics/Intensity ratios')

        numberOfSpectra = len(outputFile['Fitted spectra'])
        xBins = numberOfSpectra / 12
        yBins = numberOfSpectra / 12

        intensityRatios, cmPeakPositions = plotIntensityRatios(outputFile, plot = True, xBins = xBins,
                                                                      yBins = yBins, closeFigures = closeFigures,
                                                                      normalised = True, filterWeird = False,
                                                                      plotTitle = plotTitle)

        dIr = gIr.create_dataset('Normalised', data = intensityRatios)
        dIr.attrs['Intensity ratios'] = intensityRatios
        dIr.attrs['Peak positions'] = cmPeakPositions
        dIr.attrs['wavelengths'] = dIr.attrs['Peak positions']

        intensityRatios, cmPeakPositions = plotIntensityRatios(outputFile, plot = True, xBins = xBins,
                                                                      yBins = yBins, closeFigures = closeFigures,
                                                                      normalised = True, filterWeird = True,
                                                                      plotTitle = plotTitle)

        dIr = gIr.create_dataset('Filtered, normalised', data = intensityRatios)
        dIr.attrs['Intensity ratios'] = intensityRatios
        dIr.attrs['Peak positions'] = cmPeakPositions
        dIr.attrs['wavelengths'] = dIr.attrs['Peak positions']

        intensityRatios, cmPeakPositions = plotIntensityRatios(outputFile, plot = True, xBins = xBins,
                                                                      yBins = yBins, closeFigures = closeFigures,
                                                                      normalised = False, filterWeird = False,
                                                                      plotTitle = plotTitle)

        dIr = gIr.create_dataset('Raw', data = intensityRatios)
        dIr.attrs['Intensity ratios'] = intensityRatios
        dIr.attrs['Peak positions'] = cmPeakPositions
        dIr.attrs['wavelengths'] = dIr.attrs['Peak positions']

        intensityRatios, cmPeakPositions = plotIntensityRatios(outputFile, plot = True, xBins = xBins,
                                                                      yBins = yBins, closeFigures = closeFigures,
                                                                      normalised = False, filterWeird = True,
                                                                      plotTitle = plotTitle)

        dIr = gIr.create_dataset('Filtered, raw', data = intensityRatios)
        dIr.attrs['Intensity ratios'] = intensityRatios
        dIr.attrs['Peak positions'] = cmPeakPositions
        dIr.attrs['wavelengths'] = dIr.attrs['Peak positions']

        irEnd = time.time()
        timeElapsed = irEnd - irStart

        print '\n\tAll intensity ratios plotted in %s seconds' % timeElapsed

        visualiseIntensityRatios(outputFile)

    if pointyPeaks == True:
        pointyPeakStats(outputFile, closeFigures = True, plotTitle = plotTitle)

    if doubBools == True:
        doubBoolsHists(outputFile, binNumber = 80, plot = True, closeFigures = False, plotTitle = plotTitle)

    if peakAvgs == True:
        peakAverages(outputFile, singleBin = False)

    if analRep == True:
        analyseRepresentative(outputFile)

    if closeFigures == True:
        plt.close('all')

    print '\nStats done'

def fitAllSpectra(x, yData, outputFile, summaryAttrs = {}, startSpec = 0, monitorProgress = False, plot = False,
                  raiseExceptions = False, doublesThreshold = 2, closeFigures = False, fukkit = False, simpleFit = True, stats = True):

    absoluteStartTime = time.time()

    '''Fits all spectra and populates h5 file with relevant output data.
       h5 file must be opened before the function and closed afterwards'''

    print '\nBeginning fit procedure...'

    if len(yData) > 2500:
        print 'About to fit %s spectra. This may take a while...' % len(yData)

    '''SPECIFY INITIAL FIT PARAMETERS HERE'''

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
    gFitted.attrs.update(summaryAttrs)
    gFitted.attrs.update(summaryAttrs)
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

                if simpleFit == True:
                    fittedSpectrum = analyseNpomPeaks(x, y, cutoff = 1500, fs = 60000, doublesThreshold = doublesThreshold, doublesDist = 0,
                                                      monitorProgress = False, raiseExceptions = False, transPeakPos = 533, plot = plot)

                else:
                    fittedSpectrum = fitNpomSpectrum(x, y, detectionThreshold = detectionThreshold, doublesThreshold = doublesThreshold,
                                                     doublesDist = doublesDist, monitorProgress = monitorProgress, plot = plot, fukkit = fukkit,
                                                     simpleFit = simpleFit, raiseExceptions = raiseExceptions)
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
            #print n

            if simpleFit == True:

                fittedSpectrum = analyseNpomPeaks(x, y, cutoff = 1500, fs = 60000, doublesThreshold = doublesThreshold, doublesDist = 0,
                                                  monitorProgress = False, raiseExceptions = raiseExceptions, transPeakPos = 533, plot = plot)

            else:
                fittedSpectrum = fitNpomSpectrum(x, y, detectionThreshold = detectionThreshold, doublesThreshold = doublesThreshold,
                                                 doublesDist = doublesDist, monitorProgress = monitorProgress, plot = plot, fukkit = fukkit,
                                                 simpleFit = simpleFit, raiseExceptions = raiseExceptions)
            fittedSpectra.append(fittedSpectrum)
            fitError = 'N/A'

        '''Adds data to open HDF5 file'''

        if fittedSpectrum['NPoM?'] == True:
            rawData = fittedSpectrum['Raw data']

        else:
            rawData = y

        mainRawSpec = gSpecOnly.create_dataset('Spectrum %s' % n, data = rawData)
        mainRawSpec.attrs['wavelengths'] = x

        if fittedSpectrum['NPoM?'] == True:
            g = gFitted.create_group('Spectrum %s/' % n)

            g.attrs['NPoM?'] = fittedSpectrum['NPoM?']
            g.attrs['Double Peak?'] = fittedSpectrum['Double Peak?']
            g.attrs['Weird Peak?'] = fittedSpectrum['Weird Peak?']
            g.attrs['Weird peak intensity (norm)'] = fittedSpectrum['Weird peak intensity (norm)']
            g.attrs['Weird peak intensity (raw)'] = fittedSpectrum['Weird peak intensity (raw)']
            g.attrs['Weird peak wavelength'] = fittedSpectrum['Weird peak wavelength']
            g.attrs['Weird peak FWHM (norm)'] = fittedSpectrum['Weird peak FWHM (norm)']
            g.attrs['Weird peak FWHM (raw)'] = fittedSpectrum['Weird peak FWHM (raw)']
            g.attrs['Transverse mode intensity (norm)'] = fittedSpectrum['Transverse mode intensity (norm)']
            g.attrs['Transverse mode intensity (raw)'] = fittedSpectrum['Transverse mode intensity (raw)']
            g.attrs['Transverse mode wavelength'] = fittedSpectrum['Transverse mode wavelength']
            g.attrs['Coupled mode intensity (norm)'] = fittedSpectrum['Coupled mode intensity (norm)']
            g.attrs['Coupled mode intensity (raw)'] = fittedSpectrum['Coupled mode intensity (raw)']
            g.attrs['Coupled mode wavelength'] = fittedSpectrum['Coupled mode wavelength']
            g.attrs['Coupled mode FWHM (norm)'] = fittedSpectrum['Coupled mode FWHM (norm)']
            g.attrs['Coupled mode FWHM (raw)'] = fittedSpectrum['Coupled mode FWHM (raw)']
            g.attrs['Intensity ratio (from norm)'] = fittedSpectrum['Intensity ratio (from norm)']
            g.attrs['Intensity ratio (raw)'] = fittedSpectrum['Intensity ratio (raw)']
            g.attrs['Error(s)'] = str(fitError)

            gRaw = g.create_group('Raw/')

            dRaw = gRaw.create_dataset('Raw data', data = rawData)
            dRaw.attrs['wavelengths'] = fittedSpectrum['Full Wavelengths']

            dRawNorm = gRaw.create_dataset('Raw data (normalised)', data = fittedSpectrum['Raw data (normalised)'])
            dRawNorm.attrs['wavelengths'] = dRaw.attrs['wavelengths']

            gFit = g.create_group('Fit/')

            dRawTrunc = gFit.create_dataset('Raw data (truncated, normalised)',
                                               data = fittedSpectrum['Raw data (truncated, normalised)'])
            dRawTrunc.attrs['wavelengths'] = fittedSpectrum['Wavelengths (truncated)']

            dSmooth = gFit.create_dataset('Smoothed data (truncated, normalised)', data = fittedSpectrum['Smoothed data (truncated, normalised)'])
            dSmooth.attrs['wavelengths'] = dRawTrunc.attrs['wavelengths']
            dSmooth.attrs['secondDerivative'] = fittedSpectrum['secondDerivative']

            dBestFit = gFit.create_dataset('Best fit', data = fittedSpectrum['Best fit'])
            dBestFit.attrs['wavelengths'] = dRawTrunc.attrs['wavelengths']
            dBestFit.attrs['Initial guess'] = fittedSpectrum['Initial guess']
            dBestFit.attrs['Residuals'] = fittedSpectrum['Residuals']

            gComps = gFit.create_group('Final components/')

            comps = fittedSpectrum['Final components']

            if comps != 'N/A':

                for i in range(len(comps.keys())):
                    component = gComps.create_dataset(str(i), data = comps['g%s_' % i])
                    componentParams = fittedSpectrum['Final parameters']['g%s' % i]
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

    if stats == True:
        doStats(outputFile, closeFigures = closeFigures, doubBools = False, pointyPeaks = False, irThreshold = irThreshold)

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

    '''Set basic initial parameters'''

    method = 'All'
    summaryNameFormat = 'summary'
    outputNameFormat = 'MultiPeakFitOutput'

    '''The options below are for post-fitting analysis'''

    minBinFactor = 6 #Factor for displaying averaged spectra in histogram. e.g. 6 => only spectra from bins with > 1/6 the population of largest bin will be plotted
    sortSpec = False #Re-sorts spectra into correspoinging groups
    replaceWhenSorting = True #If false and spectra have already been sorted, command will be ignored
    sortMethod = 'full' #If 'full', re-calculates parameters required for sorting. otherwise write 'basic'
    stacks = False #Plot stacked maps
    hist = True #Calculate and plot histograms
    irThreshold = 8
    intensityRatios = False #Calculate and plot intensity ratios
    pointyPeaks = False #Calculate (and plot correlations between) height, position and FWHM of coupled mode and abnormal quadrupolar modes
    doubBools = False #Calculate and plot relationship between split coupled mode and abnormal quadrupolar mode
    #Doesn't actually work and is very slow. I'll fix it later...
    peakAvgs = False #Collects peak metadata for each spectrum and calculated average across all NPoMs and for each histogram bin
    analRep = False #Collects and analyses metadata for "representative" spectra, i.e. those with near-average coupled modes
    raiseExceptions = False #If True, code will stop if anything goes wrong; useful for debugging
    closeFigures = True #Set this equal to True unless you want a fuckton of open, unresponsive Spyder windows during analysis
    plotOption = False #Useful for debugging
    startSpec = 0 #Use these values to truncate the dataset before fitting; useful for testing/debugging new functions
    finishSpec = 0 #Set to 0 if you want to analyse all spectra

    if method == 'All':

        spectra, wavelengths, background, reference, summaryAttrs = retrieveData(summaryNameFormat, startSpec, finishSpec)
        x, yData = prepareData(spectra, wavelengths, reference)
        initImg = plotInitStack(x, yData, imgName = 'Initial Stack', closeFigures = True)

        outputFile = createOutputFile(outputNameFormat)

        with h5py.File(outputFile, 'a') as f:
            fitAllSpectra(x, yData, f, summaryAttrs = summaryAttrs, startSpec = startSpec, raiseExceptions = raiseExceptions, closeFigures = closeFigures,
                          fukkit = True, simpleFit = True, stats = True, plot = plotOption)

    elif method == 'Stats':

        summaryAttrs = retrieveData(summaryNameFormat, startSpec, finishSpec, attrsOnly = True)

        outputFile = sorted([fileName for fileName in os.listdir('.') if
                             fileName.startswith(outputNameFormat) and (fileName.endswith('.h5') or fileName.endswith('.hdf5'))],
                             key = lambda fileName: os.path.getmtime(fileName))[-1]#Finds most recent outputfile

        with h5py.File(outputFile, 'a') as f:
            f['All spectra'].attrs.update(summaryAttrs)
            f['Fitted spectra'].attrs.update(summaryAttrs)
            doStats(f, minBinFactor = minBinFactor, sortSpec = sortSpec, replaceWhenSorting = replaceWhenSorting, sortMethod = sortMethod,
                    stacks = stacks, hist = hist, intensityRatios = intensityRatios, pointyPeaks = pointyPeaks, doubBools = doubBools,
                    peakAvgs = peakAvgs, analRep = analRep, raiseExceptions = raiseExceptions, closeFigures = closeFigures, irThreshold = irThreshold)

    elif method == 'Stack':
        print '\nRetrieving data...'

        spectra, wavelengths, background, reference, summaryAttrs = retrieveData(summaryNameFormat, startSpec, finishSpec)
        x, yData = prepareData(spectra, wavelengths, reference)
        initImg = plotInitStack(x, yData, imgName = 'Initial Stack', closeFigures = False)