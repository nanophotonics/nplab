# -*- coding: utf-8 -*-
"""
Created on Fri Nov 02 14:01:17 2018

@author: car72
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
import re

if __name__ == '__main__':
    absoluteStartTime = time.time()
    print '\tModules imported\n'
    print 'Initialising functions...'

def findH5File(rootDir, mostRecent = True, nameFormat = 'date'):
    '''
    Finds either oldest or most recent .h5 file in a folder containing specified string
    '''

    os.chdir(rootDir)

    if mostRecent == True:
        n = -1

    else:
        n = 0

    if nameFormat == 'date':

        if mostRecent == True:
            print 'Searching for most recent instance of yyyy-mm-dd.h5 or similar...'

        else:
            print 'Searching for oldest instance of yyyy-mm-dd.h5 or similar...'

        h5File = sorted([i for i in os.listdir('.') if re.match('\d\d\d\d-[01]\d-[0123]\d', i[:10])
                         and (i.endswith('.h5') or i.endswith('.hdf5'))],
                        key = lambda i: os.path.getmtime(i))[n]

    else:

        if mostRecent == True:
            print 'Searching for most recent instance of %s.h5 or similar...' % nameFormat

        else:
            print 'Searching for oldest instance of %s.h5 or similar...' % nameFormat

        h5File = sorted([i for i in os.listdir('.') if i.startswith(nameFormat)
                         and (i.endswith('.h5') or i.endswith('.hdf5'))],
                        key = lambda i: os.path.getmtime(i))[n]

    print '\tH5 file %s found\n' % h5File

    return h5File

def removeNaNs(array):
    '''
    Converts NaN values to numbers via linear interpolation between adjacent finite elements.
    Input = 1D array or list.
    Output = copy of same array/list with no NaNs
    '''

    numNaNs = len([i for i in array if not np.isfinite(i)])

    if numNaNs == 0:
        return array

    newArray = np.copy(array)

    i = -1

    if not np.isfinite(newArray[i]) == True:

        while not np.isfinite(newArray[i]) == True:
            i -= 1

        for j in range(len(newArray[i:])):
            array[i+j] = newArray[i]

    for i in range(len(newArray)):

        if not np.isfinite(newArray[i]) == True:

            if i == 0:
                j = i

                while not np.isfinite(newArray[j]) == True:
                    j += 1

                for k in range(len(newArray[i:j])):
                    newArray[i+k] = newArray[j]

            elif i != len(newArray) - 1:
                j = i

                while not np.isfinite(newArray[j]) == True:
                    j += 1

                start = newArray[i-1]
                end = newArray[j]
                diff = end - start

                for k in range(len(newArray[i:j])):
                    newArray[i+k] = float(start) + float(k)*float(diff)/(len(newArray[i:j]))

    return newArray

def removeCosmicRays(x, y, ref, factor = 15):
    newY = np.copy(y)
    cosmicRay = True
    iteration = 0
    rayDex = 0
    nSteps = 1

    while cosmicRay == True and iteration < 20:
        d2 = centDiff(x, newY)
        d2 *= np.sqrt(ref)
        d2 = abs(d2)
        d2Med = np.median(d2)

        if max(d2)/d2Med > factor:
            oldRayDex = rayDex
            rayDex = d2.argmax() - 1

            if abs(rayDex - oldRayDex) < 5:
                nSteps += 1

            else:
                nSteps = 1

            iteration += 1

            for i in np.linspace(0 - nSteps, nSteps, 2*nSteps + 1):
                newY[rayDex + int(i)] = np.nan

            newY = removeNaNs(newY)

        else:
            cosmicRay = False

    return newY

def retrieveData(directory, summaryNameFormat = 'summary', first = 0, last = 0, attrsOnly = False):

    '''Retrieves data and metadata from summary file'''

    summaryFile = findH5File(directory, nameFormat = summaryNameFormat)

    if attrsOnly == False:
        print 'Retrieving data...'

    else:
        print 'Retrieving sample attributes...'

    with h5py.File(summaryFile) as f:

        mainDatasetName = sorted([scan for scan in f['particleScanSummaries/'].keys()],
                           key = lambda scan: len(f['particleScanSummaries/'][scan]['spectra']))[-1]

        mainDataset = f['particleScanSummaries/'][mainDatasetName]['spectra']
        summaryAttrs = {key : mainDataset.attrs[key] for key in mainDataset.attrs.keys()}

        if attrsOnly == True:
            print '\tInfo retrieved from %s' % mainDatasetName
            print '\t\t%s spectra in total\n' % len(mainDataset)
            return summaryAttrs

        if last == 0:
            last = len(mainDataset)

        spectra = mainDataset[()][first:last]
        wavelengths = summaryAttrs['wavelengths'][()]
        nSpec = len(spectra)

        print '\t%s spectra retrieved from %s\n' % (nSpec, mainDatasetName)

        print 'Removing cosmic ray events...'

        prepStart = time.time()

        wavelengths = removeNaNs(wavelengths)
        reference = summaryAttrs['reference']

        for n, spectrum in enumerate(spectra):

            try:
                spectra[n] = removeCosmicRays(wavelengths, spectrum, reference)

            except:
                pass

        prepEnd = time.time()
        prepTime = prepEnd - prepStart

        print '\tAll cosmic rays removed in %.2f seconds\n' % (prepTime)

        print 'Cleaning up NaN values...'

        prepStart = time.time()

        spectra = np.array([removeNaNs(spectrum) for spectrum in spectra])

        prepEnd = time.time()
        prepTime = prepEnd - prepStart

        print '\tAll spectra cleared of NaNs in %.2f seconds\n' % (prepTime)

        return wavelengths, spectra, summaryAttrs

def truncateSpectrum(wavelengths, spectrum, startWl = 450, finishWl = 900):
    '''
    Truncates spectrum within a certain wavelength range. Useful for removing high and low-end noise.
    Default range is 450-900 nm
    '''
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

def plotStackedMap(x, yData, imgName = 'Stack', plotTitle = 'Stack', closeFigures = False, init = False, vmin = 0, vmax = 6):

    '''
    Plots stack of xy data.
    x = 1d array
    y = list/array of 1d arrays. Must all be the same length as x.
    Stacks will be saved as [imgName].png in 'Stacks'
    If init == False, image will be saved in current directory
    '''
    if init == True:
        print 'Plotting initial stacked map...'
        stackStartTime = time.time()

    elif init == False:

        if 'Stacks' not in os.listdir('.'):
            os.mkdir('Stacks')

    try:
        xStack = x # Wavelength range
        yStack = range(len(yData)) # Number of spectra
        zStack = np.vstack(yData) # Spectral data

        fig = plt.figure(figsize = (9, 7))

        plt.pcolormesh(xStack, yStack, zStack, cmap = 'inferno', vmin = vmin, vmax = vmax)
        plt.xlim(450, 900)
        plt.xlabel('Wavelength (nm)', fontsize = 14)
        plt.ylabel('Spectrum #', fontsize = 14)
        cbar = plt.colorbar()
        cbar.set_ticks([])
        cbar.set_label('Intensity (a.u.)', fontsize = 14)
        plt.ylim(min(yStack), max(yStack))
        plt.yticks(fontsize = 14)
        plt.xticks(fontsize = 14)
        plt.title(plotTitle)

        if not imgName.endswith('.png'):
            imgName = '%s.png' % imgName

        if init == True:
            imgPath = imgName

        elif init == False:
            imgPath = 'Stacks/%s' % (imgName)

        fig.savefig(imgPath, bbox_inches = 'tight')

        if closeFigures == True:
            plt.close('all')

        if init == True:
            stackEndTime = time.time()
            timeElapsed = stackEndTime - stackStartTime

            print '\tInitial stack plotted in %s seconds\n' % timeElapsed

    except Exception as e:
        print '\tPlotting of %s failed because %s' % (imgName, str(e))

def plotInitStack(x, yData, imgName = 'Initial Stack', closeFigures = True):

    yDataTrunc = np.array([truncateSpectrum(x, spectrum)[1] for spectrum in yData])
    xStack = truncateSpectrum(x, yData[0])[0] # Wavelength range

    transIndex = abs(xStack - 533).argmin()
    yDataTrunc = np.array([spectrum / spectrum[transIndex] for spectrum in yDataTrunc])

    plotStackedMap(xStack, yDataTrunc, imgName = imgName, plotTitle = 'All Spectra', closeFigures = closeFigures, init = True, vmax = 6)

def createOutputFile(filename):

    '''Auto-increments new filename if file exists'''

    print 'Creating output file...'

    outputFile = '%s.h5' % filename

    if outputFile in os.listdir('.'):
        print '\t%s already exists' % outputFile
        n = 0
        outputFile = '%s_%s.h5' % (filename, n)

        while outputFile in os.listdir('.'):
            print '\t%s already exists' % outputFile
            n += 1
            outputFile = '%s_%s.h5' % (filename, n)

    print '\tOutput file %s created\n' % outputFile
    return outputFile

def butterLowpassFiltFilt(data, cutoff = 1500, fs = 60000, order=5):
    '''Smoothes data without shifting it'''
    nyq = 0.5 * fs
    normalCutoff = cutoff / nyq
    b, a = butter(order, normalCutoff, btype='low', analog=False)
    yFiltered = filtfilt(b, a, data)
    return yFiltered

def printEnd():
    print '%s%s%sv gud' % ('\t' * randint(0, 12), '\n' * randint(0, 5), ' ' * randint(0, 4))
    print '%s%ssuch python' % ('\n' * randint(0, 5), ' ' * randint(0, 55))
    print '%s%smany spectra' % ('\n' * randint(0, 5), ' ' * randint(10, 55))
    print '%s%smuch fitting' % ('\n' * randint(0, 5), ' ' * randint(8, 55))
    print '%s%swow' % ('\n' * randint(2, 5), ' ' * randint(5, 55))
    print '\n' * randint(0, 7)

def detectMinima(array):
    '''
    detectMinima(array) -> mIndices
    Finds the turning points within a 1D array and returns the indices of the minima.
    '''
    mIndices = []

    if (len(array) < 3):
        return mIndices

    neutral, rising, falling = range(3)

    def getState(a, b):
        if a < b: return rising
        if a > b: return falling
        return neutral

    ps = getState(array[0], array[1])
    begin = 1

    for i in range(2, len(array)):
        s = getState(array[i - 1], array[i])

        if s != neutral:

            if ps != neutral and ps != s:

                if s != falling:
                    mIndices.append((begin + i - 1) / 2)

            begin = i
            ps = s

    return np.array(mIndices)

def testIfNpom(x, y, lower = 0.05, upper = 2.5, NpomThreshold = 1.5):
    '''Filters out spectra that are obviously not from NPoMs'''

    isNpom = False #Guilty until proven innocent

    '''To be accepted as an NPoM, you must first pass four trials'''

    x = np.array(x)
    y = np.array(y)

    try:
        [xTrunc, yTrunc] = truncateSpectrum(x, y)
        [xUpper, yUpper] = truncateSpectrum(x, y, startWl = 900, finishWl = x.max())
        yTrunc -= yTrunc.min()

    except Exception as e:
        print 'NPoM test failed because %s' % e
        return False

    '''Trial the first: do you have a reasonable signal?'''

    YuNoNpom = 'Signal too low'

    if np.sum(yTrunc) > lower and y.min() > -0.1:
        #If sum of all intensities lies outside a given range, it's probably not an NPoM
        #Can adjust range to suit system

        YuNoNpom = 'CM region too weak'

        '''Trial the second: do you slant in the correct direction?'''

        firstHalf = yTrunc[:int(len(yTrunc)/3)]
        secondHalf = yTrunc[int(len(yTrunc)/3):]

        if np.sum(firstHalf) < np.sum(secondHalf) * NpomThreshold:
            #NPoM spectra generally have greater total signal at longer wavelengths due to coupled mode

            YuNoNpom = 'Just Noise'

            '''Trial the third: are you more than just noise?'''

            if np.sum(yTrunc)*3 > np.sum(yUpper) / NpomThreshold:
                #If the sum of the noise after 900 nm is greater than that of the spectrum itself, it's probably crap

                YuNoNpom = 'Too few peaks detected'

                '''Trial the fourth: do you have more than one maximum?'''

                ySmooth = butterLowpassFiltFilt(y)
                minima = detectMinima(-ySmooth)

                if len(minima) > 1:
                    #NPoM spectra usually have more than one distinct peak, separated by a minimum
                    isNpom = True
                    YuNoNpom = 'N/A'

    return isNpom, YuNoNpom

def testIfDouble(x, y, doublesThreshold = 2, lowerLimit = 600, plot = False, raiseExceptions = True):
    isDouble = False
    isNpom = True

    xy = truncateSpectrum(x, y)
    xTrunc = xy[0]
    yTrunc = xy[1]
    ySmooth = butterLowpassFiltFilt(yTrunc)

    mIndices = detectMinima(ySmooth)
    maxdices = detectMinima(-ySmooth)

    if len(mIndices) == 0 or len(maxdices) == 0:
        isNpom = False
        isDouble = 'N/A'
        return isNpom, isDouble

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

        if xMax < lowerLimit:
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

def normToTrans(x, y, transNorm = 1, troughNorm = 0.61, transInit = 533):

    xy = truncateSpectrum(x, y, finishWl = 600)#Truncate data from 450 to 600 nm

    xTrunc = xy[0]
    yTrunc = xy[1]

    ySmooth = butterLowpassFiltFilt(yTrunc)#Smooth data

    #try:

    mIndices = detectMinima(ySmooth)#Find minima

    if len(mIndices) > 0:
        yMins = ySmooth[mIndices]
        xMins = xTrunc[mIndices]
        mins = np.array(zip(*[xMins, yMins]))#Corresponding (x, y) values

        d1 = centDiff(xTrunc, ySmooth)
        d2 = centDiff(xTrunc, d1)
        d2Mindices = detectMinima(d2)
        trandex = abs(xTrunc[d2Mindices] - transInit).argmin()#Closest minimum in second derivative to 533 nm is likely the transverse mode
        transWl = xTrunc[d2Mindices][trandex]
        trandex = abs(xTrunc - transWl).argmin()

        initMins = [minimum for minimum in mins if minimum[0] < transWl]#Minima occuring before transverse mode

        if len(initMins) == 0:
            d2Maxdices = detectMinima(-d2)
            yMins = ySmooth[d2Maxdices]
            xMins = xTrunc[d2Maxdices]
            mins = np.array(zip(*[xMins, yMins]))

            initMins = [minimum for minimum in mins if minimum[0] < transWl]

        initMinWls = np.array(zip(*mins)[0])
        initMinHeights = np.array(zip(*mins)[1])
        initMindex = abs(initMinWls - transInit).argmin()
        initMinWl = initMinWls[initMindex]

        a0 = initMinHeights[initMindex]
        t0 = ySmooth[trandex]
        tInit = ySmooth[abs(xTrunc - transInit).argmin()]

        if tInit/ySmooth[trandex] > 2:
            t0 = tInit
            transWl = transInit

        aN = troughNorm
        tN = transNorm

        if a0 < t0:
            yNorm = y - a0
            yNorm /= (t0 - a0)
            yNorm *= (tN - aN)
            yNorm += aN

        else:
            yNorm = y - ySmooth.min()
            yNorm /= t0

    else:
        yNorm = y - ySmooth.min()
        trandex = abs(xTrunc - transInit).argmin()
        transWl = xTrunc[trandex]
        t0 = ySmooth[trandex]
        yNorm /= t0
        initMinWl = 'N/A'

    return yNorm, initMinWl, t0, transWl

def testIfWeirdPeak(x, y, factor = 1.4, transWl = 533, upperLimit = 670, plot = False, debug = False):

    '''
    Probes NPoM spectrum for presence of 'weird' sharp peak at ~600 nm
    Truncates spectrum from 450 to 670 nm, smoothes and finds maxima
    If maximum is greater than transverse mode intensity by a certain factor and at a longer wavelength, spectrum has the weird peak.
    '''

    xy = truncateSpectrum(x, y, finishWl = upperLimit)

    xTrunc = xy[0]
    yTrunc = xy[1]

    yTruncSmooth = butterLowpassFiltFilt(yTrunc)
    transHeight = yTruncSmooth[abs(xTrunc - transWl).argmin()]
    yMaxs = detectMinima(-yTruncSmooth)

    if len(yMaxs) == 0:
        return False

    peakHeight = yTruncSmooth[yMaxs].max()
    peakWl = xTrunc[yTruncSmooth.argmax()]

    if peakHeight >= transHeight * factor and peakWl > transWl:
        weird = True

    else:
        weird = False

    if plot == 'all' or plot == True:

        if weird == True:
            color = 'k'

        elif weird == False:
            color = 'b'

        plt.figure()
        plt.plot(xTrunc, yTrunc, color = color)
        plt.plot(peakWl, peakHeight, 'ro')
        plt.plot(transWl, transHeight, 'go')
        plt.xlabel('Wavelength (nm)')
        plt.ylabel('Scattered Intensity')
        plt.title('Weird peak = %s' % weird)

    if debug == True:
        return weird, peakHeight, peakWl

    else:
        return weird

def getFWHM(x, y, fwhmFactor = 1.1, smooth = False):
    '''Estimates FWHM of largest peak in a given dataset'''
    '''Also returns xy coords of peak'''

    if smooth == True:
        y = butterLowpassFiltFilt(y)

    maxdices = detectMinima(-y)
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

def gaussian(x, height, center, fwhm, offset = 0):

    '''Gaussian as a function of height, centre, fwhm and offset'''
    a = height
    b = center
    c = fwhm

    N = 4*np.log(2)*(x - b)**2
    D = c**2
    F = -(N / D)
    E = np.exp(F)
    y = a*E
    y += offset

    return y

def findMainPeaks(x, y, fwhmFactor = 1.1, plot = False, midpoint = 680, weirdPeak = True):
    peakFindMetadata = {}

    xy = truncateSpectrum(x, y, finishWl = 987)
    xTrunc = xy[0]
    yTrunc = xy[1]

    ySmooth = butterLowpassFiltFilt(yTrunc)

    mIndices = detectMinima(ySmooth)

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

def analyseNpomSpectrum(x, y, cutoff = 1500, fs = 60000, doublesThreshold = 2, cmLowLim = 600, raiseExceptions = False, plot = False,
                     weirdFactor = 1.4, transPeakPos = 533, peakFindMidpoint = 680, avg = False):
    yRaw = np.array(y)
    xRaw = np.array(x)

    allMetadataKeys = [
                      'NPoM?',
                      'Not NPoM because',
                      'Weird Peak?',
                      'Weird peak intensity (normalised)',
                      'Weird peak wavelength',
                      'Weird peak FWHM',
                      'Weird peak intensity (raw)',
                      'Weird peak FWHM (raw)',
                      'Double Peak?',
                      'Transverse mode wavelength',
                      'Transverse mode intensity (normalised)',
                      'Transverse mode intensity (raw)',
                      'Coupled mode wavelength',
                      'Coupled mode intensity (normalised)',
                      'Coupled mode FWHM',
                      'Coupled mode FWHM (raw)',
                      'Coupled mode intensity (raw)',
                      'Intensity ratio (normalised)',
                      'Intensity ratio (raw)',
                      'Raw data',
                      'Raw data (normalised)',
                      'wavelengths',
                       ]

    metadata = {key : 'N/A' for key in allMetadataKeys}
    metadata['Raw data'] = yRaw
    metadata['wavelengths'] = xRaw

    '''Testing if NPoM'''

    isNpom1, YuNoNpom = testIfNpom(xRaw, yRaw)
    isNpom2, isDouble = testIfDouble(xRaw, yRaw, doublesThreshold = doublesThreshold, lowerLimit = cmLowLim, raiseExceptions = raiseExceptions,
                                     plot = plot)

    if isNpom1 == True and isNpom2 == True:
        isNpom = True

    else:
        isNpom = False

    if isNpom2 == False:
        YuNoNpom = 'Spectral maximum < specified cm lower limit (%s nm)' % cmLowLim

    if avg == True:
       isNpom = True
       YuNoNpom = 'N/A'

    metadata['Double Peak?'] = isDouble
    metadata['NPoM?'] = isNpom
    metadata['Not NPoM because'] = YuNoNpom

    if isNpom == True:

        yRawNorm, initMinWl, transHeight, transWl = normToTrans(xRaw, yRaw, transNorm = 1, troughNorm = 0.61, transInit = transPeakPos)
        metadata['Raw data (normalised)'] = yRawNorm
        metadata['Transverse mode wavelength'] = transWl
        metadata['Transverse mode intensity (raw)'] = transHeight
        metadata['Transverse mode intensity (normalised)'] = 1.

        weird = testIfWeirdPeak(x, y, factor = weirdFactor, plot = plot, transWl = transWl)
        metadata['Weird Peak?'] = weird

        rawPeakFindMetadata, weirdGauss, cmGauss = findMainPeaks(xRaw, yRaw, fwhmFactor = 1.1, plot = False, midpoint = peakFindMidpoint,
                                                                 weirdPeak = weird)
        metadata['Coupled mode intensity (raw)'] = rawPeakFindMetadata['Coupled mode intensity']
        metadata['Coupled mode FWHM (raw)'] = rawPeakFindMetadata['Coupled mode FWHM']
        metadata['Coupled mode wavelength'] = rawPeakFindMetadata['Coupled mode wavelength']
        metadata['Weird peak intensity (raw)'] = rawPeakFindMetadata['Weird peak intensity']
        metadata['Weird peak FWHM (raw)'] = rawPeakFindMetadata['Weird peak FWHM']
        metadata['Weird peak wavelength'] = rawPeakFindMetadata['Weird peak wavelength']

        normPeakFindMetadata, weirdGauss, cmGauss = findMainPeaks(x, yRawNorm, fwhmFactor = 1.1, plot = False, midpoint = peakFindMidpoint,
                                                                  weirdPeak = weird)
        metadata['Coupled mode intensity (normalised)'] = normPeakFindMetadata['Coupled mode intensity']
        metadata['Coupled mode FWHM (normalised)'] = normPeakFindMetadata['Coupled mode FWHM']
        metadata['Weird peak intensity (normalised)'] = normPeakFindMetadata['Weird peak intensity']
        metadata['Weird peak FWHM (normalised)'] = normPeakFindMetadata['Weird peak FWHM']

        if isDouble == True:
            metadata['Coupled mode FWHM'] = 'N/A'
            metadata['Coupled mode FWHM (raw)'] = 'N/A'

        normIntensityRatio = metadata['Coupled mode intensity (normalised)'] / metadata['Transverse mode intensity (normalised)']
        rawIntensityRatio = metadata['Coupled mode intensity (raw)'] / metadata['Transverse mode intensity (raw)']

        metadata['Intensity ratio (normalised)'] = normIntensityRatio
        metadata['Intensity ratio (raw)'] = rawIntensityRatio

    return metadata

def plotAllStacks(outputFileName, fullSort = False, closeFigures = True, vmin = 0, vmax = 6):
    stackStart = time.time()

    print 'Plotting stacked spectral maps...'

    with h5py.File(outputFileName) as opf:
        date = opf['All Spectra (Raw)'].attrs['Date measured']

        for groupName in opf['NPoMs'].keys():
            gSpectra = opf['NPoMs/%s/Normalised' % groupName]
            spectraNames = sorted(gSpectra.keys(), key = lambda spectrumName: int(spectrumName[9:]))
            try:
                x = gSpectra[spectraNames[0]].attrs['wavelengths']
            except:
                print 'No data for %s' % groupName
                continue
            yData = [gSpectra[spectrumName][()] for spectrumName in spectraNames]

            if fullSort == True:
                sortingMethods = ['Coupled mode wavelength', 'Transverse mode wavelength', 'Weird peak wavelength',
                                  'Coupled mode intensity (raw)', 'Transverse mode intensity (raw)', 'Weird peak intensity (raw)']

                for sortingMethod in sortingMethods:
                    sortingMethod = (' ').join(sortingMethod.split(' ')[:3])
                    imgName = '%s\n%s by %s' % (date, groupName, sortingMethod)
                    plotStackedMap(x, yData, imgName = imgName, plotTitle = imgName, closeFigures = closeFigures, vmin = vmin, vmax = vmax)

            else:
                imgName = '%s in order of measurement' % (groupName)
                plotStackedMap(x, yData, imgName = imgName, plotTitle = imgName, closeFigures = closeFigures, vmin = vmin, vmax = vmax)

    stackEnd = time.time()
    timeElapsed = stackEnd - stackStart
    print '\tStacks plotted in %s seconds\n' % timeElapsed

def histyFit(frequencies, bins):

    gaussMod = GaussianModel()
    pars = gaussMod.guess(frequencies, x = bins)
    out = gaussMod.fit(frequencies, pars, x = bins)#Performs the fit, based on initial guesses
    print '\t\tAverage peakpos: %s +/- %s nm' % (out.params['center'].value, out.params['center'].stderr)
    print '\t\tFWHM: %s nm\n' % out.params['fwhm'].value
    #print out.fit_report()

    resonance = out.params['center'].value
    stderr = out.params['center'].stderr
    fwhm = out.params['fwhm'].value
    sigma = out.params['sigma'].value

    return resonance, stderr, fwhm, sigma

def reduceNoise(y, factor = 10):
    ySmooth = butterLowpassFiltFilt(y)
    yNoise = y - ySmooth
    yNoise /= factor
    y = ySmooth + yNoise
    return y

def plotHistogram(outputFileName, npomType = 'All NPoMs', startWl = 450, endWl = 987, binNumber = 80, plot = True,
                  minBinFactor = 5, closeFigures = False, irThreshold = 8):

    if 'Histograms' not in os.listdir('.'):
        os.mkdir('Histograms')

    print 'Combining spectra and plotting histogram...'

    with h5py.File(outputFileName) as opf:
        date = opf['All Spectra (Raw)'].attrs['Date measured']
        gSpectra = opf['NPoMs/%s/Normalised' % npomType]
        gSpecRaw = opf['NPoMs/%s/Raw' % npomType]
        spectraNames = sorted(gSpectra.keys(), key = lambda spectrumName: int(spectrumName[9:]))
        x = gSpectra[spectraNames[0]].attrs['wavelengths'][()]

        print '\tFilter: %s (%s spectra)' % (npomType, len(spectraNames))

        binSize = (endWl - startWl) / binNumber
        bins = np.linspace(startWl, endWl, num = binNumber)
        frequencies = np.zeros(len(bins))
        binPops = np.zeros(len(bins))
        yDataBinned = [np.zeros(len(x)) for f in frequencies]
        yDataRawBinned = [np.zeros(len(x)) for f in frequencies]
        binnedSpectraList = {binStart : [] for binStart in bins}

        for n, spectrumName in enumerate(spectraNames):
            dSpectrum = gSpectra[spectrumName]

            for nn, binStart in enumerate(bins):
                cmPeakPos = dSpectrum.attrs['Coupled mode wavelength']
                intensityRatio = dSpectrum.attrs['Intensity ratio (normalised)']
                yData = dSpectrum[()]
                yDataRaw = gSpecRaw[spectrumName][()]

                if cmPeakPos != 'N/A' and binStart <= cmPeakPos < binStart + binSize and 600 < cmPeakPos < 900:
                    frequencies[nn] += 1

                    if intensityRatio < irThreshold and truncateSpectrum(x, yData[()]).min() > -irThreshold:
                        yDataBinned[nn] += yData
                        yDataRawBinned[nn] += yDataRaw
                        binPops[nn] += 1

                    binnedSpectraList[binStart].append(spectrumName)

        for n, yDataSum in enumerate(yDataBinned):
            yDataBinned[n] /= binPops[n]
            yDataRawBinned[n] /= binPops[n]

        if minBinFactor == 0:
            minBin = 0

        else:
            minBin = max(frequencies)/minBinFactor

        try:
            resonance, stderr, fwhm, sigma = histyFit(frequencies, bins)

        except Exception as e:
            print e
            resonance = 'N/A'
            stderr = 'N/A'
            fwhm = 'N/A'

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

            ax1.set_ylim(0, yMax * 1.45)
            ax1.set_ylabel('Normalised Intensity', fontsize = 18)
            ax1.tick_params(labelsize = 15)
            ax1.set_xlabel('Wavelength (nm)', fontsize = 18)
            ax2.bar(bins, frequencies, color = 'grey', width = 0.8*binSize, alpha = 0.8, linewidth = 0.6)
            ax2.bar(binsPlot, freqsPlot, color = colors, width = 0.8*binSize, alpha = 0.4, linewidth = 1)
            ax2.set_xlim(450, 900)
            ax2.set_ylim(0, max(frequencies)*1.05)
            ax2.set_ylabel('Frequency', fontsize = 18, rotation = 270)
            ax2.yaxis.set_label_coords(1.11, 0.5)
            ax2.set_yticks([int(tick) for tick in ax2.get_yticks() if tick > 0][:-1])
            ax2.tick_params(labelsize = 15)
            plt.title('%s: %s\nRes = %s $\pm$ %s\nFWHM = %s' % (date, npomType, str(resonance), str(stderr), str(fwhm)))

            fig.tight_layout()

            if not npomType.endswith('.png'):
                npomType += '.png'

            fig.savefig('Histograms/%s' % (npomType), bbox_inches = 'tight')

            if closeFigures == True:
                plt.close('all')

    return frequencies, bins, yDataBinned, yDataRawBinned, binnedSpectraList, x, resonance, stderr, fwhm, sigma

def plotHistAndFit(outputFileName, npomType = 'All NPoMs', startWl = 450, endWl = 987, binNumber = 80, plot = True,
                  minBinFactor = 5, closeFigures = False, irThreshold = 8):

    frequencies, bins, yDataBinned, yDataRawBinned, binnedSpectraList, histyWl, avgResonance, stderr, fwhm, sigma = plotHistogram(outputFileName,
                                                              npomType = npomType, minBinFactor = minBinFactor,
                                                              closeFigures = closeFigures, irThreshold = irThreshold, plot = plot)

    with h5py.File(outputFileName) as opf:

        if 'Histogram data' in opf['NPoMs/%s' % npomType]:
            overWrite = True
            gHist = opf['NPoMs/%s/Histogram data' % npomType]
            gSpectraBinned = gHist['Binned y data']

        else:
            overWrite = False
            gHist = opf.create_group('NPoMs/%s/Histogram data' % npomType)
            gSpectraBinned = gHist.create_group('Binned y data')

        gHist.attrs['Average resonance'] = avgResonance
        gHist.attrs['Error'] = stderr
        gHist.attrs['FWHM'] = fwhm
        gHist.attrs['Standard deviation'] = sigma

        gHist['Bins'] = bins
        gHist['Frequencies'] = frequencies

        gHist['Frequencies'].attrs['wavelengths'] = gHist['Bins']
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

                if overWrite:
                    gBin = gSpectraBinned[binName]

                else:
                    gBin = gSpectraBinned.create_group(binName)
                gBin.attrs['Bin start (nm)'] = binStart
                gBin.attrs['Bin end (nm)'] = binEnd
                gBin['Sum'] = yDataRawBinned[n]
                gBin['Sum'].attrs['wavelengths'] = histyWl

                for spectrumName in binnedSpectraList[binStart]:
                    gBin[spectrumName] = opf['NPoMs/%s/Raw/%s' % (npomType, spectrumName)]
                    gBin[spectrumName].attrs.update(opf['NPoMs/%s/Raw/%s' % (npomType, spectrumName)].attrs)

def plotAllHists(outputFileName, closeFigures = True, irThreshold = 8, minBinFactor = 5, plotAll = True):
    histPlotStart = time.time()

    with h5py.File(outputFileName) as opf:
        npomTypes = opf['NPoMs'].keys()

        if plotAll == False:
            npomTypes = ['All NPoMs', 'Non-Weird-Peakers', 'Weird Peakers', 'Ideal NPoMs']

        #if 'Aligned NPoMs' in opf['NPoMs'].keys():
        #    npomTypes.append('Aligned NPoMs')

    for npomType in npomTypes:
        try:
            plotHistAndFit(outputFileName, npomType = npomType, irThreshold = irThreshold, minBinFactor = minBinFactor,
                       closeFigures = closeFigures)
        except:
            print 'No data for %s' % (npomType)

    histPlotEnd = time.time()
    histTimeElapsed = histPlotEnd - histPlotStart
    print '\tAll histograa plotted in %.02f seconds\n' % histTimeElapsed

def plotIntensityRatios(outputFileName, plotName = 'All NPoMs', dataType = 'Raw', closeFigures = False, plot = True):

    if 'Intensity ratios' not in os.listdir('.'):
        os.mkdir('Intensity ratios')

    if plot == True:
        print 'Plotting intensity ratios for %s, %s...' % (plotName, dataType)

    else:
        print 'Gathering intensity ratiosfor %s, %s...' % (plotName, dataType)

    with h5py.File(outputFileName) as opf:
        date = opf['All Spectra (Raw)'].attrs['Date measured']
        gSpectra = opf['NPoMs/%s/%s' % (plotName, dataType)]
        dataType = dataType.lower()
        spectraNames = sorted(gSpectra.keys(), key = lambda spectrumName: int(spectrumName[9:]))

        x = np.array([gSpectra[spectrumName].attrs['Coupled mode wavelength'] for spectrumName in spectraNames])
        y = np.array([gSpectra[spectrumName].attrs['Intensity ratio (%s)' % dataType] for spectrumName in spectraNames])

        if plot == True:

            import seaborn as sns
            sns.set_style('white')

            xy = np.array([[x[n], i] for n, i in enumerate(y) if 0 < i < 10 and x[n] < 848])
            x = np.array(zip(*xy)[0])
            y = np.array(zip(*xy)[1])

            fig, ax1 = plt.subplots(figsize = (9, 9))
            cmap = plt.get_cmap('Greys')
            ax1.scatter(x, y, marker = 'o', color = 'r', s = 2, alpha = 0.5)

            try:
                ax = sns.kdeplot(x, y, ax=ax1, n_levels = 100, gridsize=200)
                ax1Colls = ax1.collections


                for n, line in enumerate(ax1Colls):
                    total = len(ax1Colls)

                    if n == int(np.round(total/2)):

                        line.set_linestyle('--')
                        line.set_edgecolor(cmap(256))
                        line.set_facecolor(cmap(50))
                        line.set_alpha(0.5)

                    elif n == int(np.round(total * 0.95)):

                        line.set_edgecolor(cmap(256))
                        line.set_facecolor(cmap(256))
                        line.set_alpha(0.9)

                    else:
                        line.set_alpha(0)

                plt.plot([0], [0], color = 'k', label = '1 Layer')

            except Exception as e:
                print 'Intensity ratio plot failed because %s' % str(e)

                if len(x) < 100:
                    print '\t(probably because dataset was too small)'

                print '\nAttempting simple scatter plot instead...'

            ax1.set_ylim(1, 7)
            ax1.set_ylabel('Intensity Ratio', fontsize = 18)
            ax1.tick_params(which = 'both', labelsize = 15)
            ax1.set_xlim(600, 900)
            ax1.set_xlabel('Coupled Mode Resonance', fontsize = 18)
            #ax.set_xticksize(fontsize = 15)
            plt.title('%s\n%s,%s' % (date, plotName, dataType))

            fig.tight_layout()
            fig.savefig('Intensity ratios/%s,%s' % (plotName, dataType), bbox_inches = 'tight')

            if closeFigures == True:
                plt.close('all')

            print '\tIntensity ratios plotted\n'

        else:
            print '\tIntensity ratios gathered\n'

    return x, y

def plotAllIntensityRatios(outputFileName, closeFigures = True, plot = True):

    print 'Plotting all intensity ratios...\n'
    irStart = time.time()

    with h5py.File(outputFileName) as opf:
        plotNames = opf['NPoMs'].keys()

    for plotName in plotNames:
        for dataType in ['Raw', 'Normalised']:
            plotIntensityRatios(outputFileName, plotName = plotName, dataType = dataType, closeFigures = closeFigures, plot = plot)

    irEnd = time.time()
    timeElapsed = irEnd - irStart

    print '\tAll intensity ratios plotted in %s seconds\n' % timeElapsed

def visualiseIntensityRatios(outputFileName):

    '''outputFileName = h5py filename in current directory'''
    '''Plots all spectra with lines indicating calculated peak heights and positions'''

    irVisStart = time.time()

    print 'Visualising intensity ratios for individual spectra...'

    with h5py.File(outputFileName) as opf:
        gNPoMs = opf['NPoMs/All NPoMs/Raw']

        if 'Intensity ratio measurements' in opf['NPoMs/All NPoMs'].keys():
            overWrite = True
            gIrVis = opf['NPoMs/All NPoMs/Intensity ratio measurements']

        else:
            overWrite = False
            gIrVis = opf['NPoMs/All NPoMs'].create_group('Intensity ratio measurements')

        spectraNames = sorted(gNPoMs.keys(), key = lambda spectrumName: int(spectrumName[9:]))

        for n, spectrumName in enumerate(spectraNames):
            spectrum = gNPoMs[spectrumName]
            intensityRatio = spectrum.attrs['Intensity ratio (raw)']

            if intensityRatio != 'N/A':
                zeroLine = np.array([0, 0])
                transHeight = spectrum.attrs['Transverse mode intensity (raw)']
                transWl = spectrum.attrs['Transverse mode wavelength']
                cmHeight = spectrum.attrs['Coupled mode intensity (raw)']
                cmWl = spectrum.attrs['Coupled mode wavelength']
                xTransVert = np.array([transWl] * 10)
                yTransVert = np.linspace(0, transHeight, 10)
                xCmVert = np.array([cmWl] * 10)
                yCmVert = np.linspace(0, cmHeight, 10)
                transHoriz = np.array([transHeight] * 10)
                cmHoriz = np.array([cmHeight] * 10)

                if overWrite:
                    gSpecIrVis = gIrVis[spectrumName]

                else:
                    gSpecIrVis = gIrVis.create_group(spectrumName)

                gSpecIrVis['Raw'] = gNPoMs[spectrumName]
                gSpecIrVis['Raw'].attrs['wavelengths'] = gNPoMs[spectrumName].attrs['wavelengths']
                wavelengths = gNPoMs[spectrumName].attrs['wavelengths']

                if n == 0:

                    gSpecIrVis['Zero'] = zeroLine
                    gSpecIrVis['Zero'].attrs['wavelengths'] = np.array([wavelengths[0], wavelengths[1]])

                else:
                    gSpecIrVis['Zero'] = gIrVis[spectraNames[0]]['Zero']
                    gSpecIrVis['Zero'].attrs.update(gIrVis[spectraNames[0]]['Zero'].attrs)

                gSpecIrVis['Transverse mode position'] = yTransVert
                gSpecIrVis['Transverse mode position'].attrs['wavelengths'] = xTransVert

                gSpecIrVis['Coupled mode position'] = yCmVert
                gSpecIrVis['Coupled mode position'].attrs['wavelengths'] = xCmVert

                gSpecIrVis['Transverse mode height'] = transHoriz
                gSpecIrVis['Transverse mode height'].attrs['wavelengths'] = np.array([wavelengths[0], wavelengths[1]])

                gSpecIrVis['Coupled mode height'] = cmHoriz
                gSpecIrVis['Coupled mode height'].attrs['wavelengths'] = np.array([wavelengths[0], wavelengths[1]])

    irVisEnd = time.time()
    timeElapsed = irVisEnd - irVisStart
    print '\tIntensity ratios visualised in %s seconds\n' % timeElapsed

def calcGroupAttrAvgs(group):
    '''group must be instance of (open) hdf5 group object'''

    spectraNames = sorted([spectrumName for spectrumName in group.keys() if spectrumName != 'Sum'],
                                           key = lambda spectrumName: int(spectrumName[9:]))
    attrAvgs = {}

    for spectrumName in spectraNames:
        spectrum = group[spectrumName]

        for attrName in spectrum.attrs.keys():
            attrVal = spectrum.attrs[attrName]

            if type(attrVal) in [int, float]:

                if attrName in attrAvgs.keys():
                    attrAvgs[attrName].append(attrVal)

                else:
                    attrAvgs[attrName] = [attrVal]

    for attrName in attrAvgs.keys():
        attrAvgs[attrName] = np.average(np.array(attrAvgs[attrName]))

    group.attrs.update(attrAvgs)

def calcAllPeakAverages(outputFileName, groupAvgs = True, histAvgs = True, singleBin = False, peakPos = 0):
    '''If singleBin = False, function averages peak data from all NPoM spectra'''
    '''If True, specify wavelength and function will average peak data from all spectra contained in that histogram bin'''

    peakAvgStart = time.time()

    print 'Collecting peak averages...'

    with h5py.File(outputFileName) as opf:

        gNPoMs = opf['NPoMs']
        npTypes = gNPoMs.keys()

        for npType in npTypes:

            try:

                if histAvgs == True:

                    histBins = gNPoMs['%s/Histogram data/Binned y data' % npType]
                    binNames = sorted(histBins.keys(), key = lambda binName: int(binName[4:]))

                    if singleBin == False:

                        for binName in binNames:
                            gBin = histBins[binName]
                            calcGroupAttrAvgs(gBin)

                    elif singleBin == True:

                        binNames = [binName for binName in binNames if
                                    histBins[binName].attrs['Bin start (nm)'] < peakPos < histBins[binName].attrs['Bin end (nm)']]

                        for binName in binNames:
                            gBin = histBins[binName]
                            calcGroupAttrAvgs(gBin)

                if groupAvgs == True:
                    gSpectra = gNPoMs['%s/Normalised' % npType]
                    calcGroupAttrAvgs(gSpectra)

            except Exception as e:
                print 'PEak data collection failed for %s because %s' % (npType, e)


    peakAvgEnd = time.time()
    timeElapsed = peakAvgEnd - peakAvgStart

    print '\tPeak averages collected in %s seconds\n' % timeElapsed

def analyseRepresentative(outputFileName):
    print 'Collecting representative spectrum info...'

    with h5py.File(outputFileName) as opf:

        gNPoMs = opf['NPoMs']
        npTypes = gNPoMs.keys()

        for npType in npTypes:

            try:
                gHist = gNPoMs['%s/Histogram data' % npType]

            except:
                print 'Data not found for %s' % npType
                continue

            cmPeakPos = gHist.attrs['Average resonance']
            histBins = gHist['Binned y data']
            binNames = histBins.keys()
            biggestBinName = binNames[np.array([len(histBins[binName]) for binName in binNames]).argmax()]
            avgBinNames = [binName for binName in binNames if
                           histBins[binName].attrs['Bin start (nm)'] < cmPeakPos < histBins[binName].attrs['Bin end (nm)']]

            print '\t%s' % npType
            print '\t\tBin with largest population:', biggestBinName

            for binName in binNames:

                try:
                    gBin = histBins[binName]
                    dAvg = gBin['Sum']
                    x = dAvg.attrs['wavelengths']
                    y = dAvg[()]
                    avgMetadata = analyseNpomSpectrum(x, y, avg = True)
                    gBin.attrs.update(avgMetadata)

                except Exception as e:

                    if str(e) == 'arrays used as indices must be of integer (or boolean) type':
                          print '\t\t%s empty; analysis failed' % binName

                    else:
                        print '\t\t%s analysis failed because %s' % (binName, e)

            if 'Modal representative spectrum' in gHist.keys():
                del gHist['Modal representative spectrum']

            gHist['Modal representative spectrum'] = histBins[biggestBinName]['Sum']
            gHist['Modal representative spectrum'].attrs.update(histBins[biggestBinName]['Sum'].attrs)

            for n, binName in enumerate(avgBinNames):

                if len(avgBinNames) > 1:
                    n = ''

                else:
                    n = ' %s' % n

                if 'Average representative spectrum%s' % n in gHist.keys():
                    del gHist['Average representative spectrum%s' % n]

                gHist['Average representative spectrum%s' % n] = histBins[binName]['Sum']
                gHist['Average representative spectrum%s' % n].attrs.update(histBins[binName]['Sum'].attrs)

    print '\n\tRepresentative spectrum info collected\n'

def doStats(outputFileName, closeFigures = True, stacks = True, hist = True, allHists = True, irThreshold = 8, minBinFactor = 5, intensityRatios = False,
            peakAvgs = True, analRep = True):

    if stacks == True:
        plotAllStacks(outputFileName, closeFigures = closeFigures)

    if hist == True:
        plotAll = allHists
        plotAllHists(outputFileName, closeFigures = closeFigures, irThreshold = irThreshold, minBinFactor = minBinFactor, plotAll = plotAll)

    if intensityRatios == True:
        plotAllIntensityRatios(outputFileName, closeFigures = closeFigures, plot = True)
        visualiseIntensityRatios(outputFileName)

    if peakAvgs == True:
        calcAllPeakAverages(outputFileName, groupAvgs = True, histAvgs = True, singleBin = False)

    if analRep == True:
        analyseRepresentative(outputFileName)

def fitAllSpectra(x, yData, outputFileName, summaryAttrs = False, first = 0, last = 0, stats = True, raiseExceptions = False, closeFigures = True):
    absoluteStartTime = time.time()

    if last == 0:
        last = len(yData)

    print 'Beginning fit procedure...'

    with h5py.File(outputFileName, 'a') as opf:
        gAllRaw = opf.create_group('All Spectra (Raw)')

        if summaryAttrs:

            try:
                gAllRaw.attrs['Date measured'] = summaryAttrs['creation_timestamp'][:10]
            except:
                gAllRaw.attrs['Date measured'] = summaryAttrs['timestamp'][:10]

        gFailed = opf.create_group('Failed Spectra')
        gMisaligned = opf.create_group('Misaligned NPoMs')
        gNonPoms = opf.create_group('Non-NPoMs')
        gNPoMs = opf.create_group('NPoMs')

        gAllNPoMs = gNPoMs.create_group('All NPoMs')
        gAllNPoMsRaw = gAllNPoMs.create_group('Raw')
        gAllNPoMsNorm = gAllNPoMs.create_group('Normalised')

        gDoubles = gNPoMs.create_group('Doubles')
        gDoublesRaw = gDoubles.create_group('Raw')
        gDoublesNorm = gDoubles.create_group('Normalised')

        gSingles = gNPoMs.create_group('Singles')
        gSinglesRaw = gSingles.create_group('Raw')
        gSinglesNorm = gSingles.create_group('Normalised')

        gWeirds = gNPoMs.create_group('Weird Peakers')
        gWeirdsRaw = gWeirds.create_group('Raw')
        gWeirdsNorm = gWeirds.create_group('Normalised')

        gNormal = gNPoMs.create_group('Non-Weird-Peakers')
        gNormalRaw = gNormal.create_group('Raw')
        gNormalNorm = gNormal.create_group('Normalised')

        gIdeal = gNPoMs.create_group('Ideal NPoMs')
        gIdealRaw = gIdeal.create_group('Raw')
        gIdealNorm = gIdeal.create_group('Normalised')

        if summaryAttrs:
            if len(summaryAttrs['Misaligned particle numbers']) > 0.3*len(yData):
                gAligned = gNPoMs.create_group('Aligned NPoMs')
                gAlignedRaw = gAligned.create_group('Raw')
                gAlignedNorm = gAligned.create_group('Normalised')

        if len(yData) > 2500:
            print '\tAbout to fit %s spectra. This may take a while...' % len(yData)

        nummers = range(5, 101, 5)
        totalFitStart = time.time()
        print '\n0% complete'

        for n, spectrum in enumerate(yData[first:last]):
            nn = n # Keeps track of our progress through our list of spectra
            n += first # For correlation with particle groups in original dataset

            if int(100 * nn / len(yData[:])) in nummers:
                currentTime = time.time() - totalFitStart
                mins = int(currentTime / 60)
                secs = (np.round((currentTime % 60)*100))/100
                print '%s%% (%s spectra) analysed in %s min %s sec' % (nummers[0], nn, mins, secs)
                nummers = nummers[1:]

            spectrumName = 'Spectrum %s' % n
            gAllRaw[spectrumName] = spectrum

            if nn == 0:
                gAllRaw[spectrumName].attrs['wavelengths'] = x

            else:
                gAllRaw[spectrumName].attrs['wavelengths'] = gAllRaw['Spectrum 0'].attrs['wavelengths']

            if raiseExceptions == True:
                specAttrs = analyseNpomSpectrum(x, spectrum)

            else:

                try:
                    specAttrs = analyseNpomSpectrum(x, spectrum)#Main spectral analysis function

                except Exception as e:

                    print '%s failed because %s' % (spectrumName, e)
                    gAllRaw[spectrumName].attrs['Failure reason'] = str(e)
                    gAllRaw[spectrumName].attrs['wavelengths'] = x


                    gFailed[spectrumName] = gAllRaw[spectrumName]
                    gFailed[spectrumName].attrs['Failure reason'] = gAllRaw[spectrumName].attrs['Failure reason']
                    gFailed[spectrumName].attrs['wavelengths'] = gAllRaw[spectrumName].attrs['wavelengths']
                    continue

            del specAttrs['Raw data']
            gAllRaw[spectrumName].attrs.update(specAttrs)

            if summaryAttrs:

                if n in summaryAttrs['Misaligned particle numbers']:
                    gMisaligned[spectrumName] = gAllRaw[spectrumName]
                    gMisaligned[spectrumName].attrs.update(gAllRaw[spectrumName].attrs)

                else:
                    if 'Aligned NPoMs' in gNPoMs.keys() and 'Spectrum %s' % n in gAllNPoMsNorm.keys():
                        gAlignedRaw[spectrumName] = gAllRaw[spectrumName]
                        gAlignedRaw[spectrumName].attrs.update(gAllRaw[spectrumName].attrs)

                        gAlignedNorm[spectrumName] = gAllNPoMsNorm[spectrumName]
                        gAlignedNorm[spectrumName].attrs.update(gAllNPoMsNorm[spectrumName].attrs)

            if specAttrs['NPoM?'] == False:
                gNonPoms[spectrumName] = gAllRaw[spectrumName]
                gNonPoms[spectrumName].attrs.update(gAllRaw[spectrumName].attrs)

            else:
                gAllNPoMsRaw[spectrumName] = gAllRaw[spectrumName]
                gAllNPoMsNorm[spectrumName] = gAllRaw[spectrumName].attrs['Raw data (normalised)']

                del gAllRaw[spectrumName].attrs['Raw data (normalised)']

                gAllNPoMsRaw[spectrumName].attrs.update(gAllRaw[spectrumName].attrs)
                gAllNPoMsNorm[spectrumName].attrs.update(gAllRaw[spectrumName].attrs)

                if specAttrs['Double Peak?'] == True:
                    gDoublesRaw[spectrumName] = gAllNPoMsRaw[spectrumName]
                    gDoublesRaw[spectrumName].attrs.update(gAllNPoMsRaw[spectrumName].attrs)

                    gDoublesNorm[spectrumName] = gAllNPoMsNorm[spectrumName]
                    gDoublesNorm[spectrumName].attrs.update(gAllNPoMsNorm[spectrumName].attrs)

                else:
                    gSinglesRaw[spectrumName] = gAllNPoMsRaw[spectrumName]
                    gSinglesRaw[spectrumName].attrs.update(gAllNPoMsRaw[spectrumName].attrs)

                    gSinglesNorm[spectrumName] = gAllNPoMsNorm[spectrumName]
                    gSinglesNorm[spectrumName].attrs.update(gAllNPoMsNorm[spectrumName].attrs)

                if specAttrs['Weird Peak?'] == True:
                    gWeirdsRaw[spectrumName] = gAllNPoMsRaw[spectrumName]
                    gWeirdsRaw[spectrumName].attrs.update(gAllNPoMsRaw[spectrumName].attrs)

                    gWeirdsNorm[spectrumName] = gAllNPoMsNorm[spectrumName]
                    gWeirdsNorm[spectrumName].attrs.update(gAllNPoMsNorm[spectrumName].attrs)

                else:
                    gNormalRaw[spectrumName] = gAllNPoMsRaw[spectrumName]
                    gNormalRaw[spectrumName].attrs.update(gAllNPoMsRaw[spectrumName].attrs)

                    gNormalNorm[spectrumName] = gAllNPoMsNorm[spectrumName]
                    gNormalNorm[spectrumName].attrs.update(gAllNPoMsNorm[spectrumName].attrs)

                if specAttrs['Weird Peak?'] == False and specAttrs['Double Peak?'] == False:
                    gIdealRaw[spectrumName] = gAllNPoMsRaw[spectrumName]
                    gIdealRaw[spectrumName].attrs.update(gAllNPoMsRaw[spectrumName].attrs)

                    gIdealNorm[spectrumName] = gAllNPoMsNorm[spectrumName]
                    gIdealNorm[spectrumName].attrs.update(gAllNPoMsNorm[spectrumName].attrs)


    currentTime = time.time() - totalFitStart
    mins = int(currentTime / 60)
    secs = (np.round((currentTime % 60)*100))/100
    print '100%% (%s spectra) analysed in %s min %s sec\n' % (last, mins, secs)

    if stats == True:
        doStats(outputFileName, closeFigures = closeFigures)

    absoluteEndTime = time.time()
    timeElapsed = absoluteEndTime - absoluteStartTime

    mins = int(timeElapsed / 60)
    secs = int(np.round(timeElapsed % 60))

    printEnd()

    with h5py.File(outputFileName) as opf:
        gFailed = opf['Failed Spectra']

        if len(gFailed) == 0:
            print '\nFinished in %s min %s sec. Smooth sailing.' % (mins, secs)

        elif len(gFailed) == 1:
            print '\nPhew... finished in %s min %s sec with only %s failure' % (mins, secs, len(gFailed))

        elif len(gFailed) > len(gAllRaw) * 2:
            print '\nHmmm... finished in %s min %s sec but with %s failures and only %s successful fits' % (mins, secs, len(gFailed),
                                                                                                            len(gAllRaw) - len(gFailed))
        elif mins > 30:
            print '\nM8 that took ages. %s min %s sec' % (mins, secs)

        else:
            print '\nPhew... finished in %s min %s sec with only %s failures' % (mins, secs, len(gFailed))

        print ''

if __name__ == '__main__':
    print '\tFunctions initialised'
    x, yData, summaryAttrs = retrieveData(os.getcwd())
    initImg = plotInitStack(x, yData, imgName = 'Initial Stack', closeFigures = True)
    outputFileName = createOutputFile('MultiPeakFitOutput')
    fitAllSpectra(x, yData, outputFileName, summaryAttrs = summaryAttrs, stats = True, raiseExceptions = True)
    #outputFileName = findH5File(os.getcwd(), nameFormat = 'MultiPeakFitOutput', mostRecent = True)
    #doStats(outputFileName, closeFigures = True, stacks = True, hist = True, irThreshold = 8, minBinFactor = 5, intensityRatios = True,
    #        peakAvgs = True, analRep = True)