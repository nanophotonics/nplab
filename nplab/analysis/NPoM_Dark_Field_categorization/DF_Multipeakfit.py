# -*- coding: utf-8 -*-
"""
Created on Fri Nov 02 14:01:17 2018

@author: car72

Contains all necessary functions for analysis of NPoM darkfield and photoluminescence spectra
Best used in conjunction with Condense_Fit_DF or Condense_Fit_DF_PL scripts

"""
from __future__ import division
from __future__ import print_function
from builtins import zip
from builtins import str
from builtins import range
from past.utils import old_div
if __name__ == '__main__':
    print('Importing modules...')

import h5py
import numpy as np
import os
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt
from lmfit.models import GaussianModel
import time
from random import randint
import re
import scipy.optimize as spo
from scipy.signal import savgol_filter as sgFilt

if __name__ == '__main__':
    absoluteStartTime = time.time()
    print('\tModules imported\n')
    print('Initialising functions...')

def findH5File(rootDir, mostRecent = True, nameFormat = 'date'):
    '''
    Finds either oldest or most recent .h5 file in a folder whose name begins with a specified string
    Default name format ('date') is yyyy-mm-dd
    '''

    os.chdir(rootDir)

    if mostRecent == True:
        n = -1

    else:
        n = 0

    if nameFormat == 'date':

        if mostRecent == True:
            print('Searching for most recent instance of yyyy-mm-dd.h5 or similar...')

        else:
            print('Searching for oldest instance of yyyy-mm-dd.h5 or similar...')

        h5File = sorted([i for i in os.listdir('.') if re.match('\d\d\d\d-[01]\d-[0123]\d', i[:10])
                         and (i.endswith('.h5') or i.endswith('.hdf5'))],#finds list of filenames with yyyy-mm-dd(...).h(df)5 format
                        key = lambda i: os.path.getmtime(i))[n]#sorts them by date and picks either oldest or newest depending on value of 'mostRecent'

    else:

        if mostRecent == True:
            print('Searching for most recent instance of %s.h5 or similar...' % nameFormat)

        else:
            print('Searching for oldest instance of %s.h5 or similar...' % nameFormat)

        h5File = sorted([i for i in os.listdir('.') if i.startswith(nameFormat)#finds list of filenames with (nameFormat)(...).h(df)5 format
                         and (i.endswith('.h5') or i.endswith('.hdf5'))],
                        key = lambda i: os.path.getmtime(i))[n]#sorts them by date and picks either oldest or newest depending on value of 'mostRecent'

    print('\tH5 file %s found\n' % h5File)

    return h5File

def removeNaNs(array):
    '''
    Converts NaN values to numbers via linear interpolation between adjacent finite elements.
    Input = 1D array or list.
    Output = copy of same array/list with no NaNs
    '''

    numNaNs = len([i for i in array if not np.isfinite(i)])#checks for NaN values

    if numNaNs == 0:
        return array#returns original array if no NaNs

    newArray = np.copy(array)#so we don't change original array

    for n, i in enumerate(newArray):#checks for NaNs at start of array

        if np.isfinite(i):#finds index of first finite value in array
            break

    newArray[:n] = np.average(newArray[n:n+3])#turns any initial missing values into a flat line

    for n, i in enumerate(newArray[::-1]):#checks for NaNs at end of array

        if np.isfinite(i):#finds index of last finite value in array
            break

    if n > 0:
        newArray[-n:] = np.average(newArray[-(n+4):-(n + 1)])#turns any final missing values into a flat line

    nandices = np.array([n for n, i in enumerate(newArray) if not np.isfinite(i)])#locates indices of remaining NaN values

    for nandex in nandices:

        if np.isfinite(newArray[nandex]):#if NaN value has already been fixed on a previous iteration, moves to the next one
            continue

        for n, i in enumerate(newArray[nandex:]):#scans forward to look for consecutive NaNs
            if np.isfinite(i):#finds length of NaN sequence
                break

        interpInit = np.average(newArray[nandex - 3:nandex])#start point for linear interpolation; corrects for noise by averaging a few values
        interpEnd = np.average(newArray[nandex + n :nandex + n + 3])#interpolation end point; also de-noised
        interPlump = np.linspace(interpInit, interpEnd, n + 2)#linearly interpolates between the finite values either side of the NaN sequence
        newArray[nandex:nandex+n] = interPlump[1:-1]#replaces NaNs with the new data points

    return newArray

def removeCosmicRays(x, y, reference = 1, factor = 15):

    '''
    Looks for large sharp spikes in spectrum via 1st derivative
    Threshold of "large" determined by 'factor'
    If correecting a referenced DF spectrum (or similar), reference = reference spectrum (1D array). Otherwise, reference= 1
    Erases a small window around each spike and replaces it with a straight line via the removeNaNs function
    '''

    newY = np.copy(y)
    cosmicRay = True#Guilty until proven innocent
    iteration = 0
    rayDex = 0
    nSteps = 1

    while cosmicRay == True and iteration < 20:
        d1 = centDiff(x, newY)#takes dy/dx via central difference method
        d1 *= np.sqrt(reference)#de-references the spectrum to enhance cosmic ray detection in noisy regions

        d1 = abs(d1)#takes magnitude of first derivative
        d1Med = np.median(d1)#finds median gradient -> dy/dx should be larger than this for a cosmic ray

        if old_div(max(d1),d1Med) > factor:#if the maximum dy/dx value is more than a certain mutliple of the median, a cosmic ray exists
            oldRayDex = rayDex
            rayDex = d1.argmax() - 1#cosmic ray spike happens just before largest |dy/dx| value

            if abs(rayDex - oldRayDex) < 5:#if a cosmic ray still exists near where the old one was 'removed':
                nSteps += 1#the erasure window is iteratively widened

            else:#otherwise, just clean up to one data point either side
                nSteps = 1

            iteration += 1

            for i in np.linspace(0 - nSteps, nSteps, 2*nSteps + 1):#for a window centred around the spike
                newY[rayDex + int(i)] = np.nan #erase the data points

            newY = removeNaNs(newY)#linearly interpolate between data points adjacent to the spike

        else:#if no 'large' spikes exist in the spectrum
            cosmicRay = False #no cosmic rays left to fix

    return newY

def truncateSpectrum(x, y, startWl = 450, finishWl = 900):
    '''
    Truncates xy data spectrum within a specified wavelength range. Useful for removing high and low-end noise or analysing certain spectral regions.
    x and y must be 1D arrays (or lists) of identical length
    Default range is 450-900 nm (good for lab 3)
    '''
    x = np.array(x)
    y = np.array(y)
    reverse = False

    if x[0] > x[-1]:#if x is in descending order, x and y are reversed
        reverse = True
        x = x[::-1]
        y = y[::-1]

    if x[0] > startWl:#if truncation window extends below spectral range:
        xStart = np.arange(x[0], startWl - 2, x[0] - x[1])[1:][::-1]
        yStart = np.array([np.average(y[:5])] * len(xStart))
        x = np.concatenate((xStart, x))
        y = np.concatenate((yStart, y))#Adds buffer to start of x and y to ensure the truncated length is still defined by startWl and finishWl

    if x[-1] < finishWl:#if truncation window extends above spectral range:
        xFin = np.arange(x[-1], finishWl + 2, x[1] - x[0])[1:]
        yFin =  np.array([np.average(y[-5:])] * len(xFin))
        x = np.concatenate((x, xFin))
        y = np.concatenate((y, yFin))#Adds buffer to end of x and y to ensure the truncated length is still defined by startWl and finishWl

    startIndex = (abs(x - startWl)).argmin()#finds index corresponding to startWl
    finishIndex = (abs(x - finishWl)).argmin()#index corresponding to finishWl

    xTrunc = np.array(x[startIndex:finishIndex])#truncates x using these indices
    yTrunc = np.array(y[startIndex:finishIndex])#truncates y using these indices

    if reverse == True:#if the spectrum had to be reversed earlier, this flips it back.
        xTrunc = xTrunc[::-1]
        yTrunc = yTrunc[::-1]

    if xTrunc.size <= 10 and x.size <= 100:#sometimes fails for very short arrays; this extra bit works better in those cases

        if startWl > finishWl:
            wl1 = finishWl
            wl2 = startWl
            startWl = wl1
            finishWl = wl2

        xTrunc, yTrunc = np.transpose(np.array([[i, y[n]] for n, i in enumerate(x) if startWl < i < finishWl]))

    return np.array([xTrunc, yTrunc])

def retrieveData(directory, summaryNameFormat = 'summary', first = 0, last = 0, attrsOnly = False):

    '''
    Retrieves darkfield data and metadata from summary file
    Use 'first' and 'last' to truncate dataset if necessary. Setting last = 0 -> last = (end of dataset). Useful if initial spectra failed or if someone switched the lights on in the morning
    '''

    summaryFile = findH5File(directory, nameFormat = summaryNameFormat)#looks for most recent file titled 'summary(...).h(df)5 in current directory

    if attrsOnly == False:
        print('Retrieving data...')

    else:
        print('Retrieving sample attributes...')

    with h5py.File(summaryFile) as f:#opens summary file

        mainDatasetName = sorted([scan for scan in list(f['particleScanSummaries/'].keys())],
                           key = lambda scan: len(f['particleScanSummaries/'][scan]['spectra']))[-1]#finds largest datset. Useful if you had to stop and start your particle tracking before leaving it overnight

        mainDataset = f['particleScanSummaries/'][mainDatasetName]['spectra']#opens dataset object
        summaryAttrs = {key : mainDataset.attrs[key] for key in list(mainDataset.attrs.keys())}#creates python dictionary from dataset attributes/metadata

        if attrsOnly == True:#If you only want the metadata to update your main output file
            print('\tInfo retrieved from %s' % mainDatasetName)
            print('\t\t%s spectra in total\n' % len(mainDataset))
            return summaryAttrs

        if last == 0:
            last = len(mainDataset)#last = 0 -> last = (end of dataset)

        spectra = mainDataset[()][first:last]#truncates dataset, if specified
        wavelengths = summaryAttrs['wavelengths'][()]#x axis

        print('\t%s spectra retrieved from %s\n' % (len(spectra), mainDatasetName))

        print('Removing cosmic ray events...')

        prepStart = time.time()

        wavelengths = removeNaNs(wavelengths)#what it says on the tin
        reference = summaryAttrs['reference']#for use in cosmic ray removal

        for n, spectrum in enumerate(spectra):

            try:
                newSpectrum = removeCosmicRays(wavelengths, spectrum, reference = reference)#attempts to remove cosmic rays from spectrum

                if False in np.where(newSpectrum == newSpectrum[0], True, False):#if removeCosmicRays and removeNaNs have worked properly
                    spectra[n] = newSpectrum#replaces spectrum with cleaned up version

                else:
                    print('Cosmic ray removal failed for spectrum %s' % n)

            except Exception as e:
                print('Cosmic ray removal failed for spectrum %s because %s' % (n, e))
                pass

        prepEnd = time.time()
        prepTime = prepEnd - prepStart

        print('\tAll cosmic rays removed in %.2f seconds\n' % (prepTime))

        print('Cleaning up NaN values...')

        prepStart = time.time()

        spectra = np.array([removeNaNs(spectrum) for spectrum in spectra])#Extra NaN removal in case removeCosmicRays failed

        prepEnd = time.time()
        prepTime = prepEnd - prepStart#time elapsed

        print('\tAll spectra cleared of NaNs in %.2f seconds\n' % (prepTime))

        return wavelengths, spectra, summaryAttrs

def retrievePlData(directory, summaryNameFormat = 'summary', first = 0, last = 0):
    '''
    Retrieves photolumineasence data and metadata from summary file
    Use 'first' and 'last' to truncate dataset if necessary. Setting last = 0 -> last = (end of dataset). Useful if initial spectra failed or if someone switched the lights on in the morning
    '''
    summaryFile = findH5File(directory, nameFormat = summaryNameFormat) #looks for most recent file titled 'summary(...).h(df)5 in current directory

    print('Retrieving PL data...')

    with h5py.File(summaryFile) as f:#Opens summary file

        gPlName = sorted([scan for scan in list(f['particleScanSummaries/'].keys())],
                           key = lambda scan: len(f['particleScanSummaries/'][scan]['spectra']))[-1]#finds largest datset. Useful if you had to stop and start your particle tracking before leaving it overnight
        reference = f['particleScanSummaries/%s/spectra' % gPlName].attrs['reference'][()]#gets reference from DF spectra metadata

        gPl = f['NPoM PL Spectra/%s' % gPlName]#opens dataset object

        if last == 0:
            last = len(list(gPl.keys()))#last = 0 -> last = (end of dataset)

        dPlNames = sorted(list(gPl.keys()), key = lambda dPlName: int(dPlName.split(' ')[-1]))[first:last]#creates list of PL spectrum names within specified bounds
        print('\t%s PL spectra retrieved from %s\n' % (len(dPlNames), gPlName))
        print('Removing cosmic ray events...')
        prepStart = time.time()

        xPl = gPl[dPlNames[0]].attrs['wavelengths']#x axis
        xPl = removeNaNs(xPl)#what it says on the tin

        reference = truncateSpectrum(xPl, reference, startWl = xPl[0], finishWl = xPl[-1])[1]
        reference = np.append(reference, reference[-1])#for processing post-PL DF

        plData = np.array([gPl[dPlName][()] for dPlName in dPlNames])#collects all PL spectra of interest
        dfAfter = np.array([gPl[dPlName].attrs['DF After'][()] for dPlName in dPlNames])#collects corresponding DF spectra
        areas = np.array([gPl[dPlName].attrs['Total Area'] for dPlName in dPlNames])#corresponding integrated PL intensities
        bgScales = np.array([gPl[dPlName].attrs['Background Scale Factor'] for dPlName in dPlNames])#corresponding scaling factors for PL background subtraction

        for n, plSpectrum in enumerate(plData):

            try:
                plSpectrum = removeCosmicRays(xPl, plSpectrum, reference = plSpectrum)#attempts to remove cosmic rays from PL spectrum

                if False in np.where(plSpectrum == plSpectrum[0], True, False):#if removeCosmicRays and removeNaNs have worked properly
                    plData[n] = plSpectrum#replaces PL spectrum with cleaned up version

                else:
                    print('Cosmic ray removal failed for PL spectrum spectrum %s' % n)

            except:
                pass

            try:
                dfAfterSpec = removeCosmicRays(xPl, dfAfter[n], reference = reference)#attempts to remove cosmic rays from DF spectrum

                if False in np.where(dfAfterSpec == dfAfterSpec[0], True, False):#if removeCosmicRays and removeNaNs have worked properly
                    dfAfter[n] = dfAfterSpec#replaces DF spectrum with cleaned up version

                else:
                    print('Cosmic ray removal failed for post-PL DF spectrum spectrum %s' % n)

            except:
                pass

        prepEnd = time.time()
        prepTime = prepEnd - prepStart#time elapsed

        print('\tAll cosmic rays removed in %.2f seconds\n' % (prepTime))
        print('Cleaning up NaN values...')

        prepStart = time.time()
        plData = np.array([removeNaNs(plSpec) for plSpec in plData])#Extra NaN removal in case removeCosmicRays failed
        dfAfter = np.array([removeNaNs(dfSpectrum) for dfSpectrum in dfAfter])#Extra NaN removal in case removeCosmicRays failed
        prepEnd = time.time()
        prepTime = prepEnd - prepStart#time elapsed

        print('\tAll spectra cleared of NaNs in %.2f seconds\n' % (prepTime))

        return xPl, plData, dfAfter, areas, bgScales

def determineVLims(zData, threshold = 1e-4):
    '''
    Calculates appropriate intensity limits for 2D plot based on frequency distribution of intensities.
    '''

    zFlat = zData.flatten()

    frequencies, bins = np.histogram(zFlat, bins = 100, density = False)
    freqThresh = frequencies.max()*threshold

    binCentres = np.array([np.average([bins[n], bins[n + 1]]) for n in range(len(bins) - 1)])

    #plt.plot(binCentres, frequencies)
    #plt.plot(binCentres, [freqThresh]*len(binCentres))
    #plt.show()

    binsThreshed = binCentres[np.nonzero(np.where((frequencies > freqThresh), frequencies, 0))]

    #plt.plot(binsThreshed, frequencies)
    #plt.show()

    vMin = binsThreshed[0]
    vMax = binsThreshed[-1]

    return vMin, vMax

def plotStackedMap(x, yData, imgName = 'Stack', plotTitle = 'Stack', closeFigures = False, init = False, vThresh = 1e-4, xLims = (450, 900)):

    '''
    Plots stack of xy data.
    x = 1d array
    y = list/array of 1d arrays. Must all be the same length as x.
    Stacks will be saved as [imgName].png in 'Stacks'
    If init == False, image will be saved in current directory
    '''

    if init == True:
        print('Plotting %s...' % imgName)
        stackStartTime = time.time()

    elif init == False:

        if 'Stacks' not in os.listdir('.'):
            os.mkdir('Stacks')

    #try:
    xStack = x # Wavelength range
    yStack = list(range(len(yData))) # Number of spectra
    zStack = np.vstack(yData) # Spectral data

    vmin, vmax = determineVLims(zStack, threshold = vThresh)

    fig = plt.figure(figsize = (9, 7))

    plt.pcolormesh(xStack, yStack, zStack, cmap = 'inferno', vmin = vmin, vmax = vmax)
    plt.xlim(xLims)
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

        print('\tInitial stack plotted in %s seconds\n' % timeElapsed)


def plotInitStack(x, yData, imgName = 'Initial Stack', closeFigures = True, vThresh = 2e-4):
    '''Quickly plots stack of all DF spectra before doing the full analysis. Useful for quickly assessing the dataset quality'''

    yDataTrunc = np.array([truncateSpectrum(x, spectrum)[1] for spectrum in yData])#truncate to NPoM range
    xStack = truncateSpectrum(x, yData[0])[0]#x axis

    transIndex = abs(xStack - 533).argmin()
    yDataTrunc = np.array([old_div(spectrum, spectrum[transIndex]) for spectrum in yDataTrunc])#normalise to ~transverse mode

    plotStackedMap(xStack, yDataTrunc, imgName = imgName, plotTitle = imgName, closeFigures = closeFigures, init = True, vThresh = vThresh)

def plotInitPlStack(xPl, plData, imgName = 'Initial PL Stack', closeFigures = True, vThresh = 5e-5):
    '''Same as above, but for PL data'''

    yDataTrunc = np.array([truncateSpectrum(xPl, plSpectrum, startWl = 580)[1] for plSpectrum in plData])# truncate to remove laser leak
    xStack = truncateSpectrum(xPl, plData[0], startWl = 580)[0] # x axis
    yDataTrunc = np.array([old_div(plSpectrum, plSpectrum[0]) for plSpectrum in yDataTrunc])# normalise to 580 nm value
    plotStackedMap(xStack, yDataTrunc, imgName = imgName, plotTitle = imgName, closeFigures = closeFigures, vThresh = vThresh, init = True, xLims = (580, 900))

def createOutputFile(filename):

    '''Auto-increments new filename if file exists'''

    print('Creating output file...')

    if not (filename.endswith('.h5') or filename.endswith('.hdf5')):
        outputFile = '%s.h5' % filename

    if outputFile in os.listdir('.'):
        print('\t%s already exists' % outputFile)
        n = 0
        outputFile = '%s_%s.h5' % (filename, n)

        while outputFile in os.listdir('.'):
            print('\t%s already exists' % outputFile)
            n += 1
            outputFile = '%s_%s.h5' % (filename, n)

    print('\tOutput file %s created\n' % outputFile)
    return outputFile

def butterLowpassFiltFilt(data, cutoff = 1500, fs = 60000, order=5):
    '''
    Decent smoothing function for DF spectra
    Increase cutoff/decrease fs for more wibbles
    '''
    nyq = 0.5 * fs
    normalCutoff = old_div(cutoff, nyq)
    b, a = butter(order, normalCutoff, btype='low', analog=False)
    yFiltered = filtfilt(b, a, data)
    return yFiltered

def printEnd():
    '''Some Doge approval for when you finish'''

    print('%s%s%sv gud' % ('\t' * randint(0, 12), '\n' * randint(0, 5), ' ' * randint(0, 4)))
    print('%s%ssuch python' % ('\n' * randint(0, 5), ' ' * randint(0, 55)))
    print('%s%smany spectra' % ('\n' * randint(0, 5), ' ' * randint(10, 55)))
    print('%s%smuch fitting' % ('\n' * randint(0, 5), ' ' * randint(8, 55)))
    print('%s%swow' % ('\n' * randint(2, 5), ' ' * randint(5, 55)))
    print('\n' * randint(0, 7))

def detectMinima(array, threshold = 0):
    '''
    detectMinima(array) -> mIndices
    Finds the turning points within a 1D array and returns the indices of the minima.
    '''
    mIndices = []

    if (len(array) < 3):
        return mIndices

    neutral, rising, falling = list(range(3))

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
                    mIndices.append(old_div((begin + i - 1), 2))

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
        print('NPoM test failed because %s' % e)
        return False

    '''Trial the first: do you have a reasonable signal?'''

    YuNoNpom = 'Signal too low'

    if np.sum(yTrunc) > lower and y.min() > -0.1:
        #If sum of all intensities lies outside a given range, it's probably not an NPoM
        #Can adjust range to suit system

        YuNoNpom = 'CM region too weak'

        '''Trial the second: do you slant in the correct direction?'''

        firstHalf = yTrunc[:int(old_div(len(yTrunc),3))]
        secondHalf = yTrunc[int(old_div(len(yTrunc),3)):]

        if np.sum(firstHalf) < np.sum(secondHalf) * NpomThreshold:
            #NPoM spectra generally have greater total signal at longer wavelengths due to coupled mode

            YuNoNpom = 'Just Noise'

            '''Trial the third: are you more than just noise?'''

            if np.sum(yTrunc)*3 > old_div(np.sum(yUpper), NpomThreshold):
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
                print(e)
                return False

        maxsSortedY = sorted(maxs, key = lambda maximum: maximum[1])

        yMax = maxsSortedY[-1][1]
        xMax = maxsSortedY[-1][0]

        try:

            yMax2 = maxsSortedY[-2][1]

            if yMax2 > old_div(yMax, doublesThreshold):
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

    if 0 in dx:
        dx = removeNaNs(np.where(dx == 0, dx, np.nan))

    d = (old_div(dy,dx))
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
        mins = np.array(list(zip(*[xMins, yMins])))#Corresponding (x, y) values

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
            mins = np.array(list(zip(*[xMins, yMins])))

            initMins = [minimum for minimum in mins if minimum[0] < transWl]

        initMinWls = np.array(list(zip(*mins))[0])
        initMinHeights = np.array(list(zip(*mins))[1])
        initMindex = abs(initMinWls - transInit).argmin()
        initMinWl = initMinWls[initMindex]

        a0 = initMinHeights[initMindex]
        t0 = ySmooth[trandex]
        tInit = ySmooth[abs(xTrunc - transInit).argmin()]

        if old_div(tInit,ySmooth[trandex]) > 2:
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

def getFWHM(x, y, fwhmFactor = 1.1, smooth = False, peakpos = 0):
    '''Estimates FWHM of largest peak in a given dataset'''
    '''Also returns xy coords of peak'''

    if smooth == True:
        y = butterLowpassFiltFilt(y)

    maxdices = detectMinima(-y)

    if len(maxdices) == 0:

        if peakpos != 0:
            maxdices = np.array([abs(x - peakpos).argmin()])

        else:
            return None, None, None

    yMax = y[maxdices].max()
    halfMax = old_div(yMax,2)
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
    F = -(old_div(N, D))
    E = np.exp(F)
    y = a*E
    y += offset

    return y

def gaussArea(height, fwhm):
    h = height
    c = fwhm
    area = h*np.sqrt(old_div((np.pi*c**2),(4*np.log(2))))

    return area

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

        weirdFwhmHorizX = np.linspace(weirdWl - old_div(weirdFwhm,2), weirdWl + old_div(weirdFwhm,2), 2)
        weirdFwhmHorizY = np.array([old_div(weirdHeight,2)] * 2)
        cmFwhmHorizX = np.linspace(cmWl - old_div(cmFwhm,2), cmWl + old_div(cmFwhm,2), 2)
        cmFwhmHorizY = np.array([old_div(cmHeight,2)] * 2)

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

        weird = testIfWeirdPeak(x, y, factor = weirdFactor, upperLimit = peakFindMidpoint, plot = plot, transWl = transWl)
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

        normIntensityRatio = old_div(metadata['Coupled mode intensity (normalised)'], metadata['Transverse mode intensity (normalised)'])
        rawIntensityRatio = old_div(metadata['Coupled mode intensity (raw)'], metadata['Transverse mode intensity (raw)'])

        metadata['Intensity ratio (normalised)'] = normIntensityRatio
        metadata['Intensity ratio (raw)'] = rawIntensityRatio

    return metadata

def calcNoise(y, ySmooth, windowSize = 5):

    '''Calculates noise using moving window'''

    if windowSize % 2 != 0:
        windowSize += 1

    noise = y - ySmooth
    newNoise = np.concatenate((noise[:old_div(windowSize,2)][::-1], noise, noise[old_div(-windowSize,2):][::-1]))
    noiseLevel = np.array([np.std(newNoise[n:n + windowSize]) for n, i in enumerate(noise)])

    return noiseLevel

def findGausses(x, y, fwhmFactor = 1.8, regStart = 505, regEnd = 600, initPeakPos = 545, noiseThresh = 1,
                windowLength = 221, polyorder = 7, cutoff = 1000, fs = 80000, noiseWindow = 20, savGol = True):

    if savGol == True:
        ySmooth = sgFilt(y, window_length = windowLength, polyorder = polyorder)
    else:
        ySmooth = y

    ySmooth = butterLowpassFiltFilt(ySmooth, cutoff = cutoff, fs = fs)
    noise = calcNoise(y, ySmooth)

    xTrunc, yTrunc = truncateSpectrum(x, ySmooth, startWl = regStart, finishWl = regEnd)
    inMins = detectMinima(-yTrunc)

    while len(inMins) == 0:
        regEnd += 5
        xTrunc, yTrunc = truncateSpectrum(x, ySmooth, startWl = regStart, finishWl = regEnd)
        inMins = detectMinima(-yTrunc)

        if regEnd > 900:
            break

    fwhm, center, height = getFWHM(xTrunc, yTrunc, smooth = True, fwhmFactor = fwhmFactor, peakpos = initPeakPos)
    peakMetadata = {}
    peakMetadata['Peak_0'] = {'Height' : height, 'Center' : center, 'FWHM' : fwhm,
                              'Fit' : gaussian(x, height, center, fwhm)}

    if fwhm != None:
        yGauss = gaussian(x, height, center, fwhm)
        ySub = y - yGauss

    else:
        return peakMetadata

    for n in range(1, 10):
        if savGol == True:

            try:
                ySmooth = sgFilt(ySub, window_length = windowLength, polyorder = polyorder)
            except:
                if np.average(y) < 0:
                    return peakMetadata

        ySmooth = butterLowpassFiltFilt(ySmooth, cutoff = cutoff, fs = fs)
        noise = calcNoise(y, ySmooth, windowSize = noiseWindow)
        oldCenter = peakMetadata['Peak_%s' % (n - 1)]['Center']
        maxdices = detectMinima(-ySmooth)

        maxdices = [i for i in maxdices if x[i] > oldCenter and ySmooth[i] > 0 and ySmooth[i] > noise[i]*noiseThresh]

        if len(maxdices) == 0:
            break

        if len(maxdices)> 1:
            upLim = x[maxdices[1]]

        else:
            upLim = x.max()

        xTrunc, yTrunc = truncateSpectrum(x, ySmooth, startWl = oldCenter, finishWl = upLim)
        fwhm, center, height = getFWHM(xTrunc, yTrunc, smooth = True, fwhmFactor = fwhmFactor, peakpos = x[maxdices[0]])
        #fwhm, center, height = getFWHM(x, ySmooth, smooth = True, fwhmFactor = fwhmFactor, peakpos = x[y[maxdices].argmax()])

        if np.nan in [fwhm, center, height] or 0. in [fwhm, center, height]:
            break

        #print fwhm, center, height

        peakMetadata['Peak_%s' % n] = {'Height' : height, 'Center' : center, 'FWHM' : fwhm,
                                       'Fit' : gaussian(x, height, center, fwhm)}
        ySub -= peakMetadata['Peak_%s' % n]['Fit']

    return peakMetadata

def makeGausses(x, pars):

    peakMetadata = {}
    peakPars = []

    for n, par in enumerate(pars):
        peakPars.append(par)

        if len(peakPars) == 3:
            gauss = gaussian(x, peakPars[0], peakPars[1], peakPars[2])#height, center, fwhm
            peakMetadata['Peak_%s' % n] = {'Height' : peakPars[0], 'Center' : peakPars[1], 'FWHM' : peakPars[2],
                                           'Area' : gaussArea(peakPars[0], peakPars[2]), 'Fit' : gauss}

            peakPars = []

    return peakMetadata

def gaussMinimize(x, y, fwhmFactor = 1.8, regStart = 505, regEnd = 630, initPeakPos = 545, noiseThresh = 1,
                  windowLength = 251, polyorder = 6, cutoff = 1000, fs = 80000, noiseWindow = 20, savGol = True):

    peakMetadata = findGausses(x, y, fwhmFactor = fwhmFactor, regStart = regStart, regEnd = regEnd,
                               initPeakPos = initPeakPos, noiseThresh = noiseThresh, windowLength = windowLength,
                               polyorder = polyorder, cutoff = cutoff, fs = fs, noiseWindow = noiseWindow, savGol = savGol)

    def calcGaussResiduals(pars):
        '''pars = list of lists of gaussian parameters (center, height, fwhm)'''

        fit = np.zeros(len(x))
        peakPars = []

        for n, par in enumerate(pars):
            peakPars.append(par)

            if len(peakPars) == 3:
                gauss = gaussian(x, peakPars[0], peakPars[1], peakPars[2])#height, center, fwhm
                fit += gauss
                peakPars = []

        diff = np.sum(abs(y - fit))

        return diff

    peaks = sorted(list(peakMetadata.keys()), key = lambda peak: int(peak.split('_')[1]))
    bounds = []
    parsGuess = []

    for n, peak in enumerate(peaks):
        height = peakMetadata[peak]['Height']
        center = peakMetadata[peak]['Center']
        fwhm = peakMetadata[peak]['FWHM']

        heightBound = (old_div(height,2), height*2)

        if n == 0 and n < len(peaks) - 1:
            center1 = peakMetadata[peaks[n + 1]]['Center']
            maxlim = np.average([center, center1, center1])
            centerBound = (x.min(), maxlim)

        elif n == len(peaks) - 1:
            center0 = peakMetadata[peaks[n - 1]]['Center']
            minLim = np.average([center0, center0, center])
            centerBound = (minLim, x.max())

        elif 0 < n <  len(peaks) - 1:
            center0 = peakMetadata[peaks[n - 1]]['Center']
            center1 = peakMetadata[peaks[n + 1]]['Center']
            minLim = np.average([center0, center0, center])
            maxlim = np.average([center, center1, center1])
            centerBound = (minLim, maxlim)

        else:
            centerBound = (x.min(), x.max())

        fwhmBound = (10, 10*height)

        parsGuess.append(height)
        parsGuess.append(center)
        parsGuess.append(fwhm)

        bounds.append(heightBound)
        bounds.append(centerBound)
        bounds.append(fwhmBound)

    newPars = spo.minimize(calcGaussResiduals, parsGuess, bounds = bounds).x

    peakMetadata = makeGausses(x, newPars)

    peaks = sorted(list(peakMetadata.keys()), key = lambda peak: peakMetadata[peak]['Center'])

    #print 'Heights : %s' % [peakMetadata[i]['Height'] for i in peaks]
    #print 'FWHMs : %s' % [peakMetadata[i]['FWHM'] for i in peaks]
    #print 'Areas : %s' % [peakMetadata[i]['Area'] for i in peaks]
    #print 'H/W: %s' % [peakMetadata[i]['FWHM']/peakMetadata[i]['Height'] for i in peaks]

    return peakMetadata

def analysePlSpectrum(x, y, windowLength = 221, polyorder = 7, cutoff = 1000, fs = 80000, raiseExceptions = False, plot = False, specNo = 0, noiseThresh = 0.8,
                      savGol = True):
    plMetadataKeys = ['Fit Error', 'Peak Heights', 'Peak FWHMs', 'Fit', 'Peak Centers']
    plMetadata = {key : 'N/A' for key in plMetadataKeys}
    plMetadata['NPoM?'] = True #Innocent until proven guilty

    peakMetadata = gaussMinimize(x, y, windowLength = windowLength, polyorder = polyorder, cutoff = cutoff, fs = fs, noiseThresh = noiseThresh, fwhmFactor = 1.8,
                                 savGol = savGol)

    fit = np.zeros(len(x))

    for peak in peakMetadata:
        gauss = peakMetadata[peak]['Fit']

        if plot == True or plot == 'all':
            plt.plot(x, gauss, 'b--')

        fit += gauss

    if plot == True or plot == 'all':
        plt.plot(x, y, 'g-', lw = 0.5)
        plt.plot(x, fit, 'k')
        plt.show()

    peaks = sorted(list(peakMetadata.keys()), key = lambda k: int(k.split('_')[1]))

    plMetadata['Peak Heights'] = [peakMetadata[peak]['Height'] for peak in peaks]

    if True not in np.where(plMetadata['Peak Heights'] > 0, True, False):# If spectrum only has negative peaks, there is no fluorescence
        plMetadata['NPoM?'] = False

    plMetadata['Peak Centers'] = [peakMetadata[peak]['Center'] for peak in peaks]
    plMetadata['Peak FWHMs'] = [peakMetadata[peak]['FWHM'] for peak in peaks]
    plMetadata['Fit'] = fit
    residual = y - fit
    plMetadata['Fit Error'] = np.std(residual)

    return plMetadata

def plotAllStacks(outputFileName, fullSort = False, closeFigures = True, vThresh = 2e-4):
    stackStart = time.time()

    print('Plotting stacked spectral maps...')

    with h5py.File(outputFileName) as opf:
        date = opf['All Spectra (Raw)'].attrs['Date measured']

        for groupName in list(opf['NPoMs'].keys()):
            gSpectra = opf['NPoMs/%s/Normalised' % groupName]
            spectraNames = sorted(list(gSpectra.keys()), key = lambda spectrumName: int(spectrumName[9:]))
            try:
                x = gSpectra[spectraNames[0]].attrs['wavelengths']
            except:
                print('No data for %s' % groupName)
                continue
            yData = [gSpectra[spectrumName][()] for spectrumName in spectraNames]

            if fullSort == True:
                sortingMethods = ['Coupled mode wavelength', 'Transverse mode wavelength', 'Weird peak wavelength',
                                  'Coupled mode intensity (raw)', 'Transverse mode intensity (raw)', 'Weird peak intensity (raw)']

                for sortingMethod in sortingMethods:
                    sortingMethod = (' ').join(sortingMethod.split(' ')[:3])
                    imgName = '%s\n%s by %s' % (date, groupName, sortingMethod)
                    plotStackedMap(x, yData, imgName = imgName, plotTitle = imgName, closeFigures = closeFigures, vThresh = vThresh)

            else:
                imgName = '%s in order of measurement' % (groupName)
                plotStackedMap(x, yData, imgName = imgName, plotTitle = imgName, closeFigures = closeFigures, vThresh = vThresh)

    stackEnd = time.time()
    timeElapsed = stackEnd - stackStart
    print('\tStacks plotted in %s seconds\n' % timeElapsed)

def histyFit(frequencies, bins, nPeaks = 1, xMaxs = [], yMaxs = []):

    if nPeaks == 1:
        gMod = GaussianModel()
        pars = gMod.guess(frequencies, x = bins)
        out = gMod.fit(frequencies, pars, x = bins)#Performs the fit, based on initial guesses
        resonance = out.params['center'].value
        stderr = out.params['center'].stderr
        fwhm = out.params['fwhm'].value
        sigma = out.params['sigma'].value
        fit = out.best_fit

        print('\t\tAverage peakpos: %s +/- %s nm' % (resonance, stderr))
        print('\t\tFWHM: %s nm\n' % fwhm)

    else:
        gMod = GaussianModel(prefix = 'g0_')
        pars = gMod.guess(frequencies, x = bins)

        center = xMaxs[0]
        height = yMaxs[0]

        pars['g0_center'].set(center, min = bins.min(), max = old_div((xMaxs[1] + xMaxs[0]),2))
        pars['g0_height'].set(height, min = 0)

        for n in range(nPeaks)[1:]:

            if n == nPeaks - 1:
                cMax = bins.max()

            else:
                cMax = old_div((xMaxs[n] + xMaxs[n + 1]),2)

            cMin = old_div((xMaxs[n] + xMaxs[n - 1]),2)

            center = xMaxs[n]
            height = yMaxs[n]

            gModN = GaussianModel(prefix = 'g%s_' % n)
            parsN = gModN.guess(frequencies, x = bins)
            parsN['g%s_center' % n].set(center, min = cMin, max = cMax)
            parsN['g%s_height' % n].set(height, min = 0)

            gMod += gModN
            pars.update(parsN)

        out = gMod.fit(frequencies, pars, x = bins)
        fit = out.best_fit
        resonance = []
        stderr = []
        fwhm = []
        sigma = []

        for n in range(nPeaks):
            resonance.append(out.params['g%s_center' % n].value)
            stderr.append(out.params['g%s_center' % n].stderr)
            fwhm.append(out.params['g%s_fwhm' % n].value)
            sigma.append(out.params['g%s_sigma' % n].value)

        try:
            print('\t\tAverage peak positions: %s' % [float('%.03f' % i) for i in resonance])
            print('\t\tStdErrs: %s' % [float('%.03f' % i) for i in stderr])
            print('\t\tFWHMs: %s nm\n' % [float('%.03f' % i) for i in fwhm])

        except:
            stderr = [0] * len(sterr)
            print('\t\tAverage peak positions: %s' % resonance)
            print('\t\tStdErrs: %s' % stderr)
            print('\t\tFWHMs: %s nm\n' % fwhm)

    return resonance, stderr, fwhm, sigma, fit

def reduceNoise(y, factor = 10, cutoff = 1500, fs = 60000, pl = False):

    if pl == True:
        ySmooth = sgFilt(y, window_length = 221, polyorder = 7)

    ySmooth = butterLowpassFiltFilt(y, cutoff = cutoff, fs = fs)
    yNoise = y - ySmooth
    yNoise /= factor
    y = ySmooth + yNoise
    return y

def plotHistogram(outputFileName, npomType = 'All NPoMs', startWl = 450, endWl = 987, binNumber = 80, plot = True, minBinFactor = 5, closeFigures = False,
                  irThreshold = 8, cmLowLim = 600, density = False):

    plotStart = time.time()

    if 'Histograms' not in os.listdir('.'):
        os.mkdir('Histograms')

    print('Preparing to create DF histogram...')
    print('\tFilter: %s' % npomType)

    with h5py.File(outputFileName) as opf:
        date = opf['All Spectra (Raw)'].attrs['Date measured']
        gSpectra = opf['NPoMs/%s/Normalised' % npomType]
        gSpecRaw = opf['NPoMs/%s/Raw' % npomType]
        spectraNames = sorted([i for i in list(gSpectra.keys())
                               if gSpectra[i].attrs['Coupled mode wavelength'] != 'N/A'
                               and cmLowLim < gSpectra[i].attrs['Coupled mode wavelength'] < endWl],
                              key = lambda i: int(i[9:]))

        x = gSpectra[spectraNames[0]].attrs['wavelengths']

        peakPositions = [gSpectra[i].attrs['Coupled mode wavelength']
                         for n, i in enumerate(spectraNames)]

        frequencies, bins = np.histogram(peakPositions, bins = 80, range = (450., 900.), density = density)
        binSize = bins[1] - bins[0]
        print('\tFrequency distribution created for %s DF spectra' % len(spectraNames))

        print('\tPerforming Gaussian fit')

        try:
            resonance, stderr, fwhm, sigma, fit = histyFit(frequencies, bins[:-1])

        except Exception as e:
            print(e)
            resonance = 'N/A'
            stderr = 'N/A'
            fwhm = 'N/A'
            sigma = 'N/A'

        print('\tCollecting and averaging spectra for plot...')

        yDataBinned = []
        yDataRawBinned = []
        binnedSpectraList = {}

        for n, binEdge in enumerate(bins[:-1]):
            binSpecNames = np.array([i for i in spectraNames
                                     if binEdge < gSpectra[i].attrs['Coupled mode wavelength'] < bins[n + 1]
                                     and gSpectra[i].attrs['Intensity ratio (normalised)'] < irThreshold
                                     and truncateSpectrum(x, gSpectra[i][()]).min() > -irThreshold])

            binnedSpectraList[binEdge] = binSpecNames

            if len(binSpecNames) > 0:
                avgSpec = old_div(np.sum(np.array([gSpectra[i][()] for i in binSpecNames]), 0), len(binSpecNames))
                avgSpecRaw = old_div(np.sum(np.array([gSpecRaw[i][()] for i in binSpecNames]), 0), len(binSpecNames))

            else:
                avgSpec = np.zeros(len(x))
                avgSpecRaw = np.zeros(len(x))

            yDataBinned.append(avgSpec)
            yDataRawBinned.append(avgSpecRaw)

        yDataBinned = np.array(yDataBinned)
        yDataRawBinned = np.array(yDataRawBinned)

        if minBinFactor == 0:
            minBin = 0

        else:
            minBin = old_div(max(frequencies),minBinFactor)

        if plot == True:
            print('\tPlotting Histogram...')
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

            yDataPlot = np.array(yDataPlot)
            freqsPlot = np.array(freqsPlot)
            binsPlot = np.array(binsPlot)

            colors = [cmap(256 - n*(old_div(256,len(yDataPlot)))) for n, yDataSum in enumerate(yDataPlot)][::-1]

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
            ax2.bar(bins[:-1], frequencies, color = 'grey', width = 0.8*binSize, alpha = 0.8, linewidth = 0.6)
            ax2.bar(binsPlot, freqsPlot, color = colors, width = 0.8*binSize, alpha = 0.4, linewidth = 1)
            ax2.plot(bins[:-1], fit, 'k--')
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

            fig.savefig('Histograms/DF %s' % (npomType), bbox_inches = 'tight')

            if closeFigures == True:
                plt.close('all')

            else:
                plt.show()

            plotEnd = time.time()
            plotTime = plotEnd - plotStart
            print('\tHistogram plotted in %.02f seconds\n' % plotTime)

    return frequencies, bins, yDataBinned, yDataRawBinned, binnedSpectraList, x, resonance, stderr, fwhm, sigma, fit

def plotHistAndFit(outputFileName, npomType = 'All NPoMs', startWl = 450, endWl = 987, binNumber = 80, plot = True,
                  minBinFactor = 5, closeFigures = False, irThreshold = 8):

    #try:

    dfHistyBits = plotHistogram(outputFileName, npomType = npomType, minBinFactor = minBinFactor, closeFigures = closeFigures, irThreshold = irThreshold, plot = plot)

    frequencies = dfHistyBits[0]
    bins = dfHistyBits[1]
    yDataBinned = dfHistyBits[2]
    binnedSpectraList = dfHistyBits[4]
    histyWl = dfHistyBits[5]
    avgResonance = dfHistyBits[6]
    stderr = dfHistyBits[7]
    fwhm = dfHistyBits[8]
    sigma = dfHistyBits[9]
    fit = dfHistyBits[10]

    #except:
    #    print '\tHistogram plot failed for %s' % npomType
    #    return

    with h5py.File(outputFileName) as opf:

        if 'Histogram data' in opf['NPoMs/%s' % npomType]:
            del opf['NPoMs/%s/Histogram data' % npomType]

        gHist = opf.create_group('NPoMs/%s/Histogram data' % npomType)
        gSpectraBinned = gHist.create_group('Binned y data')

        gHist.attrs['Average resonance'] = avgResonance
        gHist.attrs['Error'] = stderr
        gHist.attrs['FWHM'] = fwhm
        gHist.attrs['Standard deviation'] = sigma
        gHist.attrs['Gaussian Fit'] = fit
        gHist.attrs['wavelengths'] = histyWl

        gHist['Bins'] = bins
        gHist['Frequencies'] = frequencies

        gHist['Frequencies'].attrs['wavelengths'] = gHist['Bins']
        binSize = bins[1] - bins[0]
        binsSorted = sorted(bins[:-1], key = lambda binStart: float(binStart))

        for binStart in binsSorted:
            binnedSpectraList[binStart] = sorted(binnedSpectraList[binStart], key = lambda spectrum: int(spectrum[9:]))

        wLenned = False

        for n, binStart in enumerate(binsSorted):
            if len(binnedSpectraList[binStart]) > 0:

                binEnd = binStart + binSize
                binName = 'Bin %.02d' % n
                gBin = gSpectraBinned.create_group(binName)

                gBin.attrs['Bin start (nm)'] = binStart
                gBin.attrs['Bin end (nm)'] = binEnd
                gBin['Sum'] = yDataBinned[n]

                if wLenned == False:
                    wlenN = n
                    gBin['Sum'].attrs['wavelengths'] = histyWl
                    wLenned = True

                else:
                    gBin['Sum'].attrs['wavelengths'] = gSpectraBinned['Bin %s/Sum' % wlenN].attrs['wavelengths']

                for spectrumName in binnedSpectraList[binStart]:
                    gBin[spectrumName] = opf['NPoMs/%s/Raw/%s' % (npomType, spectrumName)]
                    gBin[spectrumName].attrs.update(opf['NPoMs/%s/Raw/%s' % (npomType, spectrumName)].attrs)

def plotPlHistogram(outputFileName, npomType = 'All NPoMs', startWl = 504, endWl = 900, binNumber = 80, plot = True,
                    minBinFactor = 5, closeFigures = False, peak = 'all'):

    plotStart = time.time()

    if 'Histograms' not in os.listdir('.'):
        os.mkdir('Histograms')

    print('Preparing to create PL histogram...')
    print('\tFilter: %s' % npomType)

    with h5py.File(outputFileName) as opf:
        date = opf['All Spectra (Raw)'].attrs['Date measured']
        gSpectra = opf['NPoMs/%s/PL Data (Normalised)' % npomType]
        gSpecRaw = opf['NPoMs/%s/PL Data' % npomType]

        if peak.lower() == 'all':
            nPeaks = 0

        else:
            nPeaks = peak

        spectraNames = sorted([i for i in list(gSpectra.keys()) if len(gSpectra[i].attrs['Peak Centers']) > nPeaks and gSpectra[i][()].max() < 10],
                               key = lambda i: int(i.split(' ')[-1]))

        x = gSpectra[spectraNames[0]].attrs['wavelengths']

        if peak.lower() == 'all':
            peakPositions = np.array([gSpectra[i].attrs['Peak Centers'] for n, i in enumerate(spectraNames)])
            peakPositions = np.concatenate(peakPositions).ravel()

            peakHeights = np.array([gSpectra[i].attrs['Peak Heights'] for n, i in enumerate(spectraNames)])
            peakHeights = np.concatenate(peakHeights).ravel()

            density = True
            weights = peakHeights

        else:
            peakPositions = [gSpectra[i].attrs['Peak Centers'][peak] for n, i in enumerate(spectraNames)]

            density = False
            weights = None

        frequencies, bins = np.histogram(peakPositions, bins = binNumber, range = (startWl, endWl), density = density, weights = weights)
        binSize = bins[1] - bins[0]
        print('\tFrequency distribution created for %s PL spectra' % len(spectraNames))

        if peak.lower() == 'all':
            print('\tPerforming Gaussian fits')

            #try:
            freqInterp = np.interp(x, bins[:-1], frequencies)
            freqSmooth = butterLowpassFiltFilt(freqInterp, cutoff = 1200, fs = 85000)
            peaks = detectMinima(-freqSmooth)
            peaks = np.array([i for i in peaks if old_div(freqSmooth.max(),freqSmooth[i]) < minBinFactor])
            xMaxs = x[peaks]
            yMaxs = freqSmooth[peaks]
            #plt.plot(x, freqSmooth)
            #plt.plot(xMaxs, yMaxs, 'o')
            #plt.show()
            nPeaks = len(peaks)

            resonance, stderr, fwhm, sigma, fit = histyFit(freqInterp, x, nPeaks = nPeaks, xMaxs = xMaxs, yMaxs = yMaxs)

            if nPeaks == 1:
                resonance = [resonance]
                stderr = [stderr]
                fwhm = [fwhm]
                sigma = [sigma]

            #for n, res in enumerate(resonance):
            #print '\t\tAverage peakpos: %s' % (resonance)
            #print '\t\tFWHM: %s nm\n' % fwhm

            #except Exception as e:
            #    print 'Gaussfit for histogram failed because %s' % e
            #    resonance = 'N/A'
            #    stderr = 'N/A'
            #    fwhm = 'N/A'
            #    sigma = 'N/A'

        else:
            print('\tPerforming Gaussian fit')

            try:
                resonance, stderr, fwhm, sigma, fit = histyFit(frequencies, bins[:-1])

            except Exception as e:
                print('Gaussfit for histogram failed because %s' % e)
                resonance = 'N/A'
                stderr = 'N/A'
                fwhm = 'N/A'

        print('\tCollecting and averaging spectra for plot...')

        yDataBinned = []
        yDataRawBinned = []
        binnedSpectraList = {}

        for n, binEdge in enumerate(bins[:-1]):#for each bin

            if peak.lower() == 'all':
                binSpecNames = np.array([i for i in spectraNames
                                         if True in gSpectra[i].attrs['Peak Centers'][()] > binEdge
                                         and True in gSpectra[i].attrs['Peak Centers'][()] < bins[n + 1]])
                #finds names of all spectra with a peak in the bin

            else:
                binSpecNames = np.array([i for i in spectraNames if binEdge < gSpectra[i].attrs['Peak Centers'][peak] < bins[n + 1]])

            binnedSpectraList[binEdge] = binSpecNames #list of names added to the bin's entry in a dictionary

            if len(binSpecNames) > 0:#if there are spectra that fit this criteria
                avgSpec = old_div(np.sum(np.array([gSpectra[i][()] for i in binSpecNames]), 0), len(binSpecNames))#take the average

                if avgSpec.max() > 100: #this means something has gone wrong with initial analysis
                    print('\n\tAnomaly detected in bin %s (%s nm)' % (n, binEdge))
                    print('\tSearching for offending spectra...')
                    specFound = False

                    for binSpecName in binSpecNames:
                        if gSpectra[binSpecName][()].max() > 100:
                            print('\t%s looks dodgy. Max point = %s' % (binSpecName, gSpectra[binSpecName][()].max()))
                            specFound = True

                    if specFound == False:
                        print('\tCulprit not found. Please investigate the following spectra:')
                        print([i for i in binSpecNames])

                avgSpecRaw = old_div(np.sum(np.array([gSpecRaw[i][()] for i in binSpecNames]), 0), len(binSpecNames))

            else:
                avgSpec = np.zeros(len(x))
                avgSpecRaw = np.zeros(len(x))

            yDataBinned.append(avgSpec)
            yDataRawBinned.append(avgSpecRaw)

        yDataBinned = np.array(yDataBinned)
        yDataRawBinned = np.array(yDataRawBinned)

        print('\tPlotting Histogram...')

        if minBinFactor == 0:
            minBin = 0

        else:
            minBin = old_div(max(frequencies),minBinFactor)

        if plot == True:
            fig = plt.figure(figsize = (8, 6))

            cmap = plt.get_cmap('jet')

            if peak.lower() != 'all':
                ax1 = fig.add_subplot(111)
                ax1.set_zorder(1)
                ax2 = ax1.twinx()
                ax2.set_zorder(0)
                ax1.patch.set_visible(False)

            else:
                ax2 = fig.add_subplot(111)

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

            yDataPlot = np.array(yDataPlot)
            freqsPlot = np.array(freqsPlot)
            binsPlot = np.array(binsPlot)

            colors = [cmap(256 - n*(old_div(256,len(yDataPlot)))) for n, yDataSum in enumerate(yDataPlot)][::-1]

            if peak.lower() != 'all':

                for n, yDataSum in enumerate(yDataPlot):
                    ySmooth = reduceNoise(yDataSum, cutoff = 1000, fs = 80000, factor = 7, pl = True)
                    currentYMax = truncateSpectrum(x, ySmooth)[1].max()
                    currentYMin = truncateSpectrum(x, ySmooth)[1].min()

                    if currentYMax > yMax:
                        yMax = currentYMax

                    if currentYMin < yMin:
                        yMin = currentYMin

                    ax1.plot(x, ySmooth, lw = 0.7, color = colors[n])

            if peak.lower() != 'all':
                ax1.set_ylim(0, yMax * 1.45)
                ax1.set_ylabel('Normalised Intensity', fontsize = 18)
                ax1.tick_params(labelsize = 15)
                ax1.set_xlabel('Wavelength (nm)', fontsize = 18)

            ax2.bar(bins[:-1], frequencies, color = 'grey', width = 0.8*binSize, alpha = 0.8, linewidth = 0.6)
            ax2.bar(binsPlot, freqsPlot, color = colors, width = 0.8*binSize, alpha = 0.4, linewidth = 1)
            ax2.set_xlim(500, 900)
            ax2.set_ylim(0, max(frequencies)*1.05)

            if peak.lower() != 'all':
                ax2.set_ylabel('Frequency', fontsize = 18, rotation = 270)
                ax2.yaxis.set_label_coords(1.11, 0.5)
                ax2.set_yticks([int(tick) for tick in ax2.get_yticks() if tick > 0][:-1])
                plt.title('%s: %s\nRes = %s $\pm$ %s\nFWHM = %s' % (date, npomType, str(resonance), str(stderr), str(fwhm)))

            else:
                ax2.set_ylabel('Frequency', fontsize = 18)
                ax2.plot(x, fit, 'k--')
                try:
                    plt.title('%s: %s\n%s peaks at:\n%s' % (date, npomType, nPeaks, str([float('%.02f' % i) for i in resonance])[1:-1]))
                except:
                    plt.title('%s: %s' % (date, npomType))

            ax2.tick_params(labelsize = 15)
            fig.tight_layout()

            if not npomType.endswith('.png'):
                npomType += '.png'

            fig.savefig('Histograms/PL %s' % (npomType), bbox_inches = 'tight')

            if closeFigures == True:
                plt.close('all')

            else:
                plt.show()

            plotEnd = time.time()
            plotTime = plotEnd - plotStart
            print('\tHistogram plotted in %.02f seconds\n' % plotTime)

    return frequencies, bins, yDataBinned, yDataRawBinned, binnedSpectraList, x, resonance, stderr, fwhm, sigma, fit

def plotPlHistAndFit(outputFileName, npomType = 'All NPoMs', startWl = 504, endWl = 900, binNumber = 80, plot = True,
                     minBinFactor = 50, closeFigures = False, peak = 'all'):

    #try:
    plHistyBits = plotPlHistogram(outputFileName, npomType = npomType, startWl = startWl, endWl = endWl, binNumber = binNumber, minBinFactor = minBinFactor, peak = peak,
                                  closeFigures = closeFigures, plot = plot)

    frequencies = plHistyBits[0]
    bins = plHistyBits[1]
    yDataBinned = plHistyBits[2]
    binnedSpectraList = plHistyBits[4]
    histyWl = plHistyBits[5]
    avgResonance = plHistyBits[6]
    stderr = plHistyBits[7]
    fwhm = plHistyBits[8]
    sigma = plHistyBits[9]
    fit = plHistyBits[10]
    #except:
    #    print '\tHistogram plot failed for %s' % npomType
    #    return

    with h5py.File(outputFileName) as opf:

        if 'PL Histogram data' in opf['NPoMs/%s' % npomType]:
            del opf['NPoMs/%s/PL Histogram data' % npomType]

        gHist = opf.create_group('NPoMs/%s/PL Histogram data' % npomType)
        gSpectraBinned = gHist.create_group('Binned y data')

        gHist.attrs['Average resonance'] = avgResonance
        gHist.attrs['Error'] = stderr

        gHist.attrs['FWHM'] = fwhm
        gHist.attrs['Standard deviation'] = sigma
        gHist.attrs['Gaussian Fit'] = fit
        gHist.attrs['wavelengths'] = histyWl

        gHist['Bins'] = bins
        gHist['Frequencies'] = frequencies

        gHist['Frequencies'].attrs['wavelengths'] = gHist['Bins']
        binSize = bins[1] - bins[0]
        binsSorted = sorted(bins[:-1], key = lambda binStart: float(binStart))

        for binStart in binsSorted:
            binnedSpectraList[binStart] = sorted(binnedSpectraList[binStart], key = lambda spectrum: int(spectrum[9:]))

        wLenned = False

        for n, binStart in enumerate(binsSorted):
            if len(binnedSpectraList[binStart]) > 0:

                binEnd = binStart + binSize
                binName = 'Bin %.02d' % n
                gBin = gSpectraBinned.create_group(binName)

                gBin.attrs['Bin start (nm)'] = binStart
                gBin.attrs['Bin end (nm)'] = binEnd
                gBin['Sum'] = yDataBinned[n]

                if wLenned == False:
                    wlenN = n
                    gBin['Sum'].attrs['wavelengths'] = histyWl
                    wLenned = True

                else:
                    gBin['Sum'].attrs['wavelengths'] = gSpectraBinned['Bin %s/Sum' % wlenN].attrs['wavelengths']

                for spectrumName in binnedSpectraList[binStart]:
                    gBin[spectrumName] = opf['NPoMs/%s/PL Data/%s' % (npomType, spectrumName)]
                    gBin[spectrumName].attrs.update(opf['NPoMs/%s/PL Data/%s' % (npomType, spectrumName)].attrs)

def plotHistComb1D(outputFileName, npomType = 'All NPoMs', dfStartWl = 450, dfEndWl = 987, plStartWl = 504,
                   plEndWl = 900, binNumber = 80, plot = True, minBinFactor = 5, closeFigures = False,
                   irThreshold = 8, cmLowLim = 600):

    with h5py.File(outputFileName) as opf:
        date = opf['All Spectra (Raw)'].attrs['Date measured']

        print('Collecting DF Histogram data...')

        gDfHist = opf['NPoMs/%s/Histogram data' % npomType]
        dfFrequencies = gDfHist['Frequencies'][()]
        dfBins = gDfHist['Bins'][()]
        dfX = gDfHist.attrs['wavelengths'][()]

        yDataBinned = []

        for n in np.arange(binNumber):

            if 'Bin %s' % n in list(gDfHist['Binned y data'].keys()):
                yDataBinned.append(gDfHist['Binned y data/Bin %s/Sum' % n][()])
            else:
                yDataBinned.append(np.zeros(len(dfX)))

        yDataBinned = np.array(yDataBinned)
        dfFit = gDfHist.attrs['Gaussian Fit'][()]
        dfResonance = gDfHist.attrs['Average resonance']
        dfStdErr = gDfHist.attrs['Error']
        dfFwhm = gDfHist.attrs['FWHM']

        print('\tCollected\n')

        print('Collecting PL Histogram data...')
        gPlHist = opf['NPoMs/%s/PL Histogram data' % npomType]
        plFrequencies = gPlHist['Frequencies'][()]
        plBins = gPlHist['Bins'][()]
        plX = gPlHist.attrs['wavelengths'][()]
        plFit = gPlHist.attrs['Gaussian Fit'][()]
        plResonance = gPlHist.attrs['Average resonance'][()]
        print(plResonance)
        nPeaks = len(plResonance)

        dfFrequencies = np.array([float(i) for i in dfFrequencies])
        dfFrequencies /= float(dfFrequencies.max())
        dfFrequencies *= float(plFrequencies.max())

        dfFrequencies -= dfFrequencies.min()
        dfFrequencies /= dfFrequencies.max()

        plFrequencies -= plFrequencies.min()
        plFrequencies /= plFrequencies.max()

        dfFit -= dfFit.min()
        dfFit /= dfFit.max()

        plFit -= plFit.min()
        plFit /= plFit.max()

        print('\tCollected\n')

    print('\tPlotting Combined Histogram...')

    if minBinFactor == 0:
        dfMinBin = 0

    else:
        dfMinBin = old_div(dfFrequencies.max(),minBinFactor)

    fig = plt.figure(figsize = (8, 6))

    cmap = plt.get_cmap('jet')

    ax1 = fig.add_subplot(111)
    ax1.set_zorder(1)
    ax2 = ax1.twinx()
    ax2.set_zorder(0)
    ax1.patch.set_visible(False)

    yDataPlot = []
    dfFreqsPlot = []
    dfBinsPlot = []
    plFreqsPlot = []
    plBinsPlot = []
    yMax = 0
    yMin = 7

    for n, yDatum in enumerate(yDataBinned):

        if dfFrequencies[n] > dfMinBin:
            yDataPlot.append(yDatum)
            dfFreqsPlot.append(dfFrequencies[n])
            dfBinsPlot.append(dfBins[n])

    yDataPlot = np.array(yDataPlot)
    dfFreqsPlot = np.array(dfFreqsPlot)
    dfBinsPlot = np.array(dfBinsPlot)

    plFreqsPlot = np.array(plFreqsPlot)
    plBinsPlot = np.array(plBinsPlot)

    colors = [cmap(256 - n*(old_div(256,len(yDataPlot)))) for n, yDataSum in enumerate(yDataPlot)][::-1]

    for n, yDataSum in enumerate(yDataPlot):

        ySmooth = reduceNoise(yDataSum, factor = 7)
        currentYMax = truncateSpectrum(dfX, ySmooth)[1].max()
        currentYMin = truncateSpectrum(dfX, ySmooth)[1].min()

        if currentYMax > yMax:
            yMax = currentYMax

        if currentYMin < yMin:
            yMin = currentYMin

        ax1.plot(dfX, ySmooth, lw = 0.7, color = colors[n])

    ax1.set_ylim(0, yMax * 1.45)
    ax1.set_ylabel('Normalised Intensity', fontsize = 18)
    ax1.set_yticks([])
    ax1.tick_params(labelsize = 15)
    ax1.set_xlabel('Wavelength (nm)', fontsize = 18)

    plBinSize = plBins[1] - plBins[0]
    dfBinSize = dfBins[1] - dfBins[0]

    ax2.bar(plBins[:-1], plFrequencies, color = 'blue', width = 0.8*plBinSize, alpha = 0.8, linewidth = 0.6)
    ax2.bar(dfBins[:-1], dfFrequencies, color = 'grey', width = 0.8*dfBinSize, alpha = 0.8, linewidth = 0.6)
    ax2.bar(dfBinsPlot, dfFreqsPlot, color = colors, width = 0.8*dfBinSize, alpha = 0.4, linewidth = 1)
    ax2.plot(plX, plFit, 'k--')
    ax2.plot(dfBins[:-1], dfFit, 'k--')

    ax2.set_xlim(500, 850)
    ax2.set_ylim(0, 1.05)
    ax2.set_ylabel('Normalised Frequency', fontsize = 18, rotation = 270)
    ax2.yaxis.set_label_coords(1.05, 0.5)
    ax2.set_yticks([])
    ax2.tick_params(labelsize = 15)
    plt.title('%s: %s\n%s PL peaks: %s\nDF Res = %s $\pm$ %s\nFWHM = %s'
              % (date, npomType, nPeaks, str([float('%.02f' % i) for i in plResonance])[1:-1], dfResonance, dfStdErr,
                 dfFwhm))

    fig.tight_layout()

    if not npomType.endswith('.png'):
        npomType += '.png'

    fig.savefig('Histograms/DF + PL %s' % (npomType), bbox_inches = 'tight')

    if closeFigures == True:
        plt.close('all')

    else:
        plt.show()

    print('\tHistogram plotted\n')

def plotAllHists(outputFileName, closeFigures = True, irThreshold = 8, minBinFactor = 5, plotAll = True, pl = False):
    histPlotStart = time.time()

    npomTypes = ['All NPoMs', 'Non-Weird-Peakers', 'Weird Peakers', 'Ideal NPoMs', 'Doubles', 'Singles']

    for npomType in npomTypes:
        plotHistAndFit(outputFileName, npomType = npomType, irThreshold = irThreshold, minBinFactor = minBinFactor, closeFigures = closeFigures)

        if pl == True:
             plotPlHistAndFit(outputFileName, npomType = npomType, minBinFactor = minBinFactor*10, closeFigures = closeFigures, peak = 'all')
             plotHistComb1D(outputFileName, npomType = npomType, minBinFactor = minBinFactor, closeFigures = closeFigures, irThreshold = irThreshold, plot = plotAll)

    histPlotEnd = time.time()
    histTimeElapsed = histPlotEnd - histPlotStart
    print('\tAll histograa plotted in %.02f seconds\n' % histTimeElapsed)

def plotHistComb2D(outputFileName, npomType = 'All NPoMs', dfStartWl = 450, dfEndWl = 987, plStartWl = 504,
                   plEndWl = 900, binNumber = 80, plot = True, minBinFactor = 5, closeFigures = False,
                   irThreshold = 8, cmLowLim = 600):

    with h5py.File(outputFileName) as opf:

        dfKeys = ['Coupled Mode', 'Coupled Mode Intensity', 'Weird peak wavelength', 'Weird peak intensity']
        plKeys = ['PL Peaks', 'PL Signal']

        scatterKeys = np.concatenate([['%s vs %s' % (dfKey, plKey) for dfKey in dfKeys] for plKey in plKeys]).ravel()

        print(scatterKeys)
        scatterDict = {key : [] for key in scatterKeys}

        gDf = opf['NPoMs/%s/Raw' % npomType]
        gPl = opf['NPoMs/%s/PL Data' % npomType]
        spectraNames = sorted(list(gDf.keys()), key = lambda i: int(i.split(' ')[-1]))

        for spectrumName in spectraNames:
            dfSpectrum = gDf[spectrumName]
            n = int(spectrumName.split(' ')[-1])
            plSpecName = 'PL Spectrum %s' % n
            plSpectrum = gPl[plSpecName]

            cmWl = dfSpectrum.attrs['Coupled mode wavelength']
            cmH = dfSpectrum.attrs['Coupled mode intensity (raw)']

            wrdWl = dfSpectrum.attrs['Weird peak wavelength']
            wrdH = dfSpectrum.attrs['Weird peak intensity (raw)']

            plWls = plSpectrum.attrs['Peak Centers']
            plArea = plSpectrum.attrs['Total Area']

            scatterDict['Coupled Mode vs PL Signal'].append(np.array([cmWl, plArea]))
            scatterDict['Coupled Mode Intensity vs PL Signal'].append(np.array([cmH, plArea]))

            if wrdWl != 'N/A':
                scatterDict['Weird peak intensity vs PL Signal'].append(np.array([wrdH, plArea]))
                scatterDict['Weird peak wavelength vs PL Signal'].append(np.array([wrdWl, plArea]))

            for wl in plWls:
                scatterDict['Coupled Mode vs PL Peaks'].append(np.array([cmWl, wl]))
                scatterDict['Coupled Mode Intensity vs PL Peaks'].append(np.array([cmH, wl]))

                if wrdWl != 'N/A':
                    scatterDict['Weird peak intensity vs PL Peaks'].append(np.array([wrdH, wl]))
                    scatterDict['Weird peak wavelength vs PL Peaks'].append(np.array([wrdWl, wl]))


        for key in list(scatterDict.keys()):
            scatterDict[key] = np.transpose(np.array(scatterDict[key]))
            x = scatterDict[key][0]
            y = scatterDict[key][1]

            plt.plot(x, y, '.')
            plt.xlabel(key.split(' vs ')[0])
            plt.ylabel(key.split(' vs ')[-1])
            plt.title(key)
            plt.show()

def plotIntensityRatios(outputFileName, plotName = 'All NPoMs', dataType = 'Raw', closeFigures = False, plot = True):

    if 'Intensity ratios' not in os.listdir('.'):
        os.mkdir('Intensity ratios')

    if plot == True:
        print('Plotting intensity ratios for %s, %s...' % (plotName, dataType))

    else:
        print('Gathering intensity ratiosfor %s, %s...' % (plotName, dataType))

    with h5py.File(outputFileName) as opf:
        date = opf['All Spectra (Raw)'].attrs['Date measured']
        gSpectra = opf['NPoMs/%s/%s' % (plotName, dataType)]
        dataType = dataType.lower()
        spectraNames = sorted(list(gSpectra.keys()), key = lambda spectrumName: int(spectrumName[9:]))

        x = np.array([gSpectra[spectrumName].attrs['Coupled mode wavelength'] for spectrumName in spectraNames])
        y = np.array([gSpectra[spectrumName].attrs['Intensity ratio (%s)' % dataType] for spectrumName in spectraNames])

        if plot == True:

            import seaborn as sns
            sns.set_style('white')

            xy = np.array([[x[n], i] for n, i in enumerate(y) if 0 < i < 10 and x[n] < 848])
            x = np.array(list(zip(*xy))[0])
            y = np.array(list(zip(*xy))[1])

            fig, ax1 = plt.subplots(figsize = (9, 9))
            cmap = plt.get_cmap('Greys')
            ax1.scatter(x, y, marker = 'o', color = 'r', s = 2, alpha = 0.5)

            try:
                ax = sns.kdeplot(x, y, ax=ax1, n_levels = 100, gridsize=200)
                ax1Colls = ax1.collections


                for n, line in enumerate(ax1Colls):
                    total = len(ax1Colls)

                    if n == int(np.round(old_div(total,2))):

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

                ax.plot([0], [0], color = 'k', label = '1 Layer')

            except Exception as e:
                print('Intensity ratio plot failed because %s' % str(e))

                if len(x) < 100:
                    print('\t(probably because dataset was too small)')

                print('\nAttempting simple scatter plot instead...')

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

            print('\tIntensity ratios plotted\n')

        else:
            print('\tIntensity ratios gathered\n')

    return x, y

def plotAllIntensityRatios(outputFileName, closeFigures = True, plot = True):

    print('Plotting all intensity ratios...\n')
    irStart = time.time()

    with h5py.File(outputFileName) as opf:
        plotNames = list(opf['NPoMs'].keys())

    for plotName in plotNames:
        for dataType in ['Raw', 'Normalised']:
            plotIntensityRatios(outputFileName, plotName = plotName, dataType = dataType, closeFigures = closeFigures, plot = plot)

    irEnd = time.time()
    timeElapsed = irEnd - irStart

    print('\tAll intensity ratios plotted in %s seconds\n' % timeElapsed)

def visualiseIntensityRatios(outputFileName):

    '''outputFileName = h5py filename in current directory'''
    '''Plots all spectra with lines indicating calculated peak heights and positions'''

    irVisStart = time.time()

    print('Visualising intensity ratios for individual spectra...')

    with h5py.File(outputFileName) as opf:
        gNPoMs = opf['NPoMs/All NPoMs/Raw']

        if 'Intensity ratio measurements' in list(opf['NPoMs/All NPoMs'].keys()):
            overWrite = True
            gIrVis = opf['NPoMs/All NPoMs/Intensity ratio measurements']

        else:
            overWrite = False
            gIrVis = opf['NPoMs/All NPoMs'].create_group('Intensity ratio measurements')

        spectraNames = sorted(list(gNPoMs.keys()), key = lambda spectrumName: int(spectrumName[9:]))

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
    print('\tIntensity ratios visualised in %s seconds\n' % timeElapsed)

def calcGroupAttrAvgs(group):
    '''group must be instance of (open) hdf5 group object'''

    spectraNames = sorted([spectrumName for spectrumName in list(group.keys()) if spectrumName != 'Sum'],
                                           key = lambda spectrumName: int(spectrumName[9:]))
    attrAvgs = {}

    for spectrumName in spectraNames:
        spectrum = group[spectrumName]

        for attrName in list(spectrum.attrs.keys()):
            attrVal = spectrum.attrs[attrName]

            if type(attrVal) in [int, float]:

                if attrName in list(attrAvgs.keys()):
                    attrAvgs[attrName].append(attrVal)

                else:
                    attrAvgs[attrName] = [attrVal]

    for attrName in list(attrAvgs.keys()):
        attrAvgs[attrName] = np.average(np.array(attrAvgs[attrName]))

    group.attrs.update(attrAvgs)

def calcAllPeakAverages(outputFileName, groupAvgs = True, histAvgs = True, singleBin = False, peakPos = 0):
    '''If singleBin = False, function averages peak data from all NPoM spectra'''
    '''If True, specify wavelength and function will average peak data from all spectra contained in that histogram bin'''

    peakAvgStart = time.time()

    print('Collecting peak averages...')

    with h5py.File(outputFileName) as opf:

        gNPoMs = opf['NPoMs']
        npTypes = ['All NPoMs', 'Non-Weird-Peakers', 'Weird Peakers', 'Ideal NPoMs', 'Doubles', 'Singles']
        for npType in npTypes:

            try:

                if histAvgs == True:

                    histBins = gNPoMs['%s/Histogram data/Binned y data' % npType]
                    binNames = sorted(list(histBins.keys()), key = lambda binName: int(binName[4:]))

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
                print('Peak data collection failed for %s because %s' % (npType, e))


    peakAvgEnd = time.time()
    timeElapsed = peakAvgEnd - peakAvgStart

    print('\tPeak averages collected in %s seconds\n' % timeElapsed)

def analyseRepresentative(outputFileName, peakFindMidpoint = 680):
    print('Collecting representative spectrum info...')

    with h5py.File(outputFileName) as opf:

        gNPoMs = opf['NPoMs']
        npTypes = ['All NPoMs', 'Non-Weird-Peakers', 'Weird Peakers', 'Ideal NPoMs', 'Doubles', 'Singles']

        for npType in npTypes:

            try:
                gHist = gNPoMs['%s/Histogram data' % npType]

            except:
                print('Data not found for %s' % npType)
                continue

            cmPeakPos = gHist.attrs['Average resonance']
            histBins = gHist['Binned y data']
            binNames = list(histBins.keys())
            biggestBinName = binNames[np.array([len(histBins[binName]) for binName in binNames]).argmax()]
            avgBinNames = [binName for binName in binNames if
                           histBins[binName].attrs['Bin start (nm)'] < cmPeakPos < histBins[binName].attrs['Bin end (nm)']]

            print('\t%s' % npType)
            print('\t\tBin with largest population:', biggestBinName)

            for binName in binNames:

                try:
                    gBin = histBins[binName]
                    dAvg = gBin['Sum']
                    x = dAvg.attrs['wavelengths']
                    y = dAvg[()]
                    avgMetadata = analyseNpomSpectrum(x, y, avg = True, peakFindMidpoint = peakFindMidpoint)
                    gBin.attrs.update(avgMetadata)

                except Exception as e:

                    if str(e) == 'arrays used as indices must be of integer (or boolean) type':
                          print('\t\t%s empty; analysis failed' % binName)

                    else:
                        print('\t\t%s analysis failed because %s' % (binName, e))

            if 'Modal representative spectrum' in list(gHist.keys()):
                del gHist['Modal representative spectrum']

            gHist['Modal representative spectrum'] = histBins[biggestBinName]['Sum']
            gHist['Modal representative spectrum'].attrs.update(histBins[biggestBinName]['Sum'].attrs)

            for n, binName in enumerate(avgBinNames):

                if len(avgBinNames) > 1:
                    n = ''

                else:
                    n = ' %s' % n

                if 'Average representative spectrum%s' % n in list(gHist.keys()):
                    del gHist['Average representative spectrum%s' % n]

                gHist['Average representative spectrum%s' % n] = histBins[binName]['Sum']
                gHist['Average representative spectrum%s' % n].attrs.update(histBins[binName]['Sum'].attrs)

    print('\n\tRepresentative spectrum info collected\n')

def doStats(outputFileName, closeFigures = True, stacks = True, hist = True, allHists = True, irThreshold = 8, minBinFactor = 5, intensityRatios = False,
            peakAvgs = True, analRep = True, peakFindMidpoint = 680, pl = False):

    if stacks == True:
        plotAllStacks(outputFileName, closeFigures = closeFigures)

    if hist == True:
        plotAll = allHists
        plotAllHists(outputFileName, closeFigures = closeFigures, irThreshold = irThreshold, minBinFactor = minBinFactor, plotAll = plotAll, pl = pl)

    if intensityRatios == True:
        plotAllIntensityRatios(outputFileName, closeFigures = closeFigures, plot = True)
        visualiseIntensityRatios(outputFileName)

    if peakAvgs == True:
        calcAllPeakAverages(outputFileName, groupAvgs = True, histAvgs = True, singleBin = False)

    if analRep == True:
        analyseRepresentative(outputFileName, peakFindMidpoint = peakFindMidpoint)

def fitAllSpectra(rootDir, outputFileName, npSize = 80, summaryAttrs = False, first = 0, last = 0, stats = True, pl = False, raiseExceptions = False,
                  raiseSpecExceptions = False, closeFigures = True):

    absoluteStartTime = time.time()

    x, yData, summaryAttrs = retrieveData(rootDir, first = first, last = last)
    plotInitStack(x, yData, imgName = 'Initial DF Stack', closeFigures = closeFigures)

    if pl == True:
        xPl, plData, dfAfter, areas, bgScales = retrievePlData(rootDir, first = first, last = last)
        plotInitPlStack(xPl, plData, imgName = 'Initial PL Stack', closeFigures = closeFigures)

    peakFindMidpointDict = {80: 680, 70 : 630, 60 : 580, 50 : 550, 40 : 540}
    peakFindMidpoint = peakFindMidpointDict[npSize]
    cmLowLimDict = {80: 580, 70 : 560, 60 : 540, 50 : 520, 40 : 500}
    cmLowLim = cmLowLimDict[npSize]

    #if last == 0:
    #    last = len(yData)

    print('Beginning fit procedure...')
    if pl == True:
        print('\tPL Fit uses spo.minimize, so this will take a while')

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

        if pl == True:
            gFailedPl = opf.create_group('Failed PL Spectra')
            gAllPl = opf.create_group('All PL Spectra')
            gAllNPoMsPl = gAllNPoMs.create_group('PL Data')
            gDoublesPl = gDoubles.create_group('PL Data')
            gSinglesPl = gSingles.create_group('PL Data')
            gWeirdsPl = gWeirds.create_group('PL Data')
            gNormalPl = gNormal.create_group('PL Data')
            gIdealPl = gIdeal.create_group('PL Data')
            gNonPomsPl = gNonPoms.create_group('PL Data')

            gAllNPoMsPlNorm = gAllNPoMs.create_group('PL Data (Normalised)')
            gDoublesPlNorm = gDoubles.create_group('PL Data (Normalised)')
            gSinglesPlNorm = gSingles.create_group('PL Data (Normalised)')
            gWeirdsPlNorm = gWeirds.create_group('PL Data (Normalised)')
            gNormalPlNorm = gNormal.create_group('PL Data (Normalised)')
            gIdealPlNorm = gIdeal.create_group('PL Data (Normalised)')

        if summaryAttrs:
            if len(summaryAttrs['Misaligned particle numbers']) > 0.3*len(yData):
                gAligned = gNPoMs.create_group('Aligned NPoMs')
                gAlignedRaw = gAligned.create_group('Raw')
                gAlignedNorm = gAligned.create_group('Normalised')

        if len(yData) > 2500:
            print('\tAbout to fit %s spectra. This may take a while...' % len(yData))

        nummers = list(range(5, 101, 5))
        totalFitStart = time.time()
        print('\n0% complete')


        for n, spectrum in enumerate(yData):
            nn = n # Keeps track of our progress through our list of spectra
            n = n + first # For correlation with particle groups in original dataset
            #print nn, n

            if int(old_div(100 * nn, len(yData[:]))) in nummers:
                currentTime = time.time() - totalFitStart
                mins = int(old_div(currentTime, 60))
                secs = old_div((np.round((currentTime % 60)*100)),100)
                print('%s%% (%s spectra) analysed in %s min %s sec' % (nummers[0], nn, mins, secs))
                nummers = nummers[1:]

            spectrumName = 'Spectrum %s' % n
            gAllRaw[spectrumName] = spectrum
            plMetadataKeys = ['Fit Error', 'Peak Heights', 'Peak FWHMs', 'Fit', 'Peak Centers', 'NPoM?']
            plSpecAttrs = {key : 'N/A' for key in plMetadataKeys}

            if nn == 0:
                gAllRaw[spectrumName].attrs['wavelengths'] = x

            else:
                gAllRaw[spectrumName].attrs['wavelengths'] = gAllRaw['Spectrum %s' % first].attrs['wavelengths']

            if pl == True:
                plSpectrum = plData[nn]
                dfAfterPl = dfAfter[nn]
                plArea = areas[nn]
                plBgScale = bgScales[nn]

                plSpecName = 'PL Spectrum %s' % n
                gAllPl[plSpecName] = plSpectrum
                gAllPl[plSpecName].attrs['DF After'] = dfAfterPl
                gAllPl[plSpecName].attrs['Total Area'] = plArea
                gAllPl[plSpecName].attrs['Background Scale Factor'] = plBgScale

                if nn == 0:
                    gAllPl[plSpecName].attrs['wavelengths'] = xPl

                else:
                    gAllPl[plSpecName].attrs['wavelengths'] = gAllPl['PL Spectrum %s' % first].attrs['wavelengths']

            if raiseExceptions == True:
                specAttrs = analyseNpomSpectrum(x, spectrum, peakFindMidpoint = peakFindMidpoint, raiseExceptions = raiseSpecExceptions,
                                                cmLowLim = cmLowLim)#Main spectral analysis function

                if pl == True:
                    plSpecAttrs = analysePlSpectrum(xPl, plSpectrum, specNo = nn, raiseExceptions = raiseSpecExceptions)#Main PL analysis function

            else:

                try:
                    specAttrs = analyseNpomSpectrum(x, spectrum, peakFindMidpoint = peakFindMidpoint, cmLowLim = cmLowLim,
                                                    raiseExceptions = raiseSpecExceptions)#Main spectral analysis function
                    plMetadataKeys = ['Fit Error', 'Peak Heights', 'Peak FWHMs', 'Fit', 'Peak Centers', 'NPoM?']
                    plSpecAttrs = {key : 'N/A' for key in plMetadataKeys}

                except Exception as e:

                    print('DF %s failed because %s' % (spectrumName, e))
                    gAllRaw[spectrumName].attrs['Failure reason'] = str(e)
                    gAllRaw[spectrumName].attrs['wavelengths'] = gAllRaw['Spectrum %s' % first].attrs['wavelengths']
                    gFailed[spectrumName] = gAllRaw[spectrumName]
                    gFailed[spectrumName].attrs['Failure reason'] = gAllRaw[spectrumName].attrs['Failure reason']
                    gFailed[spectrumName].attrs['wavelengths'] = gAllRaw[spectrumName].attrs['wavelengths']
                    plMetadataKeys = ['Fit Error', 'Peak Heights', 'Peak FWHMs', 'Fit', 'Peak Centers', 'NPoM?']
                    plSpecAttrs = {key : 'N/A' for key in plMetadataKeys}

                    if pl != True:
                        continue

                if pl == True:

                    try:
                        plSpecAttrs = analysePlSpectrum(xPl, plSpectrum, specNo = nn, raiseExceptions = raiseSpecExceptions)#Main PL analysis function

                    except Exception as e:

                        print('%s failed because %s' % (plSpecName, e))
                        gAllPl[plSpecName].attrs['Failure reason'] = str(e)
                        gAllPl[plSpecName].attrs['wavelengths'] = gAllPl['PL Spectrum %s' % first].attrs['wavelengths']
                        gFailedPl[plSpecName] = gAllRaw[plSpecName]
                        gFailedPl[plSpecName].attrs['Failure reason'] = gAllPl[plSpecName].attrs['Failure reason']
                        gFailedPl[plSpecName].attrs['wavelengths'] = gAllPl[plSpecName].attrs['wavelengths']
                        plMetadataKeys = ['Fit Error', 'Peak Heights', 'Peak FWHMs', 'Fit', 'Peak Centers']
                        plSpecAttrs = {key : 'N/A' for key in plMetadataKeys}
                        continue

            if ['Raw data'] in list(specAttrs.keys()):
                del specAttrs['Raw data']

            gAllRaw[spectrumName].attrs.update(specAttrs)

            if pl == True:
                gAllPl[plSpecName].attrs.update(plSpecAttrs)

            if summaryAttrs:

                if n in summaryAttrs['Misaligned particle numbers']:
                    gMisaligned[spectrumName] = gAllRaw[spectrumName]
                    gMisaligned[spectrumName].attrs.update(gAllRaw[spectrumName].attrs)

                else:
                    if 'Aligned NPoMs' in list(gNPoMs.keys()) and 'Spectrum %s' % n in list(gAllNPoMsNorm.keys()):
                        gAlignedRaw[spectrumName] = gAllRaw[spectrumName]
                        gAlignedRaw[spectrumName].attrs.update(gAllRaw[spectrumName].attrs)

                        gAlignedNorm[spectrumName] = gAllNPoMsNorm[spectrumName]
                        gAlignedNorm[spectrumName].attrs.update(gAllNPoMsNorm[spectrumName].attrs)

            if False in [specAttrs['NPoM?'], plSpecAttrs['NPoM?']]:
                gNonPoms[spectrumName] = gAllRaw[spectrumName]
                gNonPoms[spectrumName].attrs.update(gAllRaw[spectrumName].attrs)

                if pl == True:
                    gNonPomsPl[plSpecName] = gAllPl[plSpecName]
                    gNonPomsPl[plSpecName].attrs.update(gAllPl[plSpecName].attrs)

            else:
                gAllNPoMsRaw[spectrumName] = gAllRaw[spectrumName]
                gAllNPoMsNorm[spectrumName] = gAllRaw[spectrumName].attrs['Raw data (normalised)']

                del gAllRaw[spectrumName].attrs['Raw data (normalised)']

                gAllNPoMsRaw[spectrumName].attrs.update(gAllRaw[spectrumName].attrs)
                gAllNPoMsNorm[spectrumName].attrs.update(gAllRaw[spectrumName].attrs)

                if pl == True:
                    gAllNPoMsPl[plSpecName] = gAllPl[plSpecName]
                    gAllNPoMsPl[plSpecName].attrs.update(gAllPl[plSpecName].attrs)

                    if gAllPl[plSpecName].attrs['Fit'] != 'N/A' and abs(gAllPl[plSpecName].attrs['Fit'].max()) > 1:
                        gAllNPoMsPlNorm[plSpecName] = old_div(gAllPl[plSpecName][()], gAllPl[plSpecName].attrs['Fit'][()].max())
                        gAllNPoMsPlNorm[plSpecName].attrs.update(gAllPl[plSpecName].attrs)
                        gAllNPoMsPlNorm[plSpecName].attrs['Peak Heights'] = old_div(gAllPl[plSpecName].attrs['Peak Heights'][()], gAllPl[plSpecName].attrs['Fit'][()].max())

                    else:
                        gAllNPoMsPlNorm[plSpecName] = old_div(gAllPl[plSpecName][()], gAllPl[plSpecName][()].max())
                        gAllNPoMsPlNorm[plSpecName].attrs.update(gAllPl[plSpecName].attrs)
                        gAllNPoMsPlNorm[plSpecName].attrs['Peak Heights'] = old_div(gAllPl[plSpecName].attrs['Peak Heights'][()], gAllPl[plSpecName][()].max())

                if specAttrs['Double Peak?'] == True:
                    gDoublesRaw[spectrumName] = gAllNPoMsRaw[spectrumName]
                    gDoublesRaw[spectrumName].attrs.update(gAllNPoMsRaw[spectrumName].attrs)

                    gDoublesNorm[spectrumName] = gAllNPoMsNorm[spectrumName]
                    gDoublesNorm[spectrumName].attrs.update(gAllNPoMsNorm[spectrumName].attrs)

                    if pl == True:
                        gDoublesPl[plSpecName] = gAllNPoMsPl[plSpecName]
                        gDoublesPl[plSpecName].attrs.update(gAllNPoMsPl[plSpecName].attrs)

                        gDoublesPlNorm[plSpecName] = gAllNPoMsPlNorm[plSpecName]
                        gDoublesPlNorm[plSpecName].attrs.update(gAllNPoMsPlNorm[plSpecName].attrs)

                else:
                    gSinglesRaw[spectrumName] = gAllNPoMsRaw[spectrumName]
                    gSinglesRaw[spectrumName].attrs.update(gAllNPoMsRaw[spectrumName].attrs)

                    gSinglesNorm[spectrumName] = gAllNPoMsNorm[spectrumName]
                    gSinglesNorm[spectrumName].attrs.update(gAllNPoMsNorm[spectrumName].attrs)

                    if pl == True:
                        gSinglesPl[plSpecName] = gAllNPoMsPl[plSpecName]
                        gSinglesPl[plSpecName].attrs.update(gAllNPoMsPl[plSpecName].attrs)

                        gSinglesPlNorm[plSpecName] = gAllNPoMsPlNorm[plSpecName]
                        gSinglesPlNorm[plSpecName].attrs.update(gAllNPoMsPlNorm[plSpecName].attrs)


                if specAttrs['Weird Peak?'] == True:
                    gWeirdsRaw[spectrumName] = gAllNPoMsRaw[spectrumName]
                    gWeirdsRaw[spectrumName].attrs.update(gAllNPoMsRaw[spectrumName].attrs)

                    gWeirdsNorm[spectrumName] = gAllNPoMsNorm[spectrumName]
                    gWeirdsNorm[spectrumName].attrs.update(gAllNPoMsNorm[spectrumName].attrs)

                    if pl == True:
                        gWeirdsPl[plSpecName] = gAllNPoMsPl[plSpecName]
                        gWeirdsPl[plSpecName].attrs.update(gAllNPoMsPl[plSpecName].attrs)

                        gWeirdsPlNorm[plSpecName] = gAllNPoMsPlNorm[plSpecName]
                        gWeirdsPlNorm[plSpecName].attrs.update(gAllNPoMsPlNorm[plSpecName].attrs)

                else:
                    gNormalRaw[spectrumName] = gAllNPoMsRaw[spectrumName]
                    gNormalRaw[spectrumName].attrs.update(gAllNPoMsRaw[spectrumName].attrs)

                    gNormalNorm[spectrumName] = gAllNPoMsNorm[spectrumName]
                    gNormalNorm[spectrumName].attrs.update(gAllNPoMsNorm[spectrumName].attrs)

                    if pl == True:
                        gNormalPl[plSpecName] = gAllNPoMsPl[plSpecName]
                        gNormalPl[plSpecName].attrs.update(gAllNPoMsPl[plSpecName].attrs)

                        gNormalPlNorm[plSpecName] = gAllNPoMsPlNorm[plSpecName]
                        gNormalPlNorm[plSpecName].attrs.update(gAllNPoMsPlNorm[plSpecName].attrs)

                if specAttrs['Weird Peak?'] == False and specAttrs['Double Peak?'] == False:
                    gIdealRaw[spectrumName] = gAllNPoMsRaw[spectrumName]
                    gIdealRaw[spectrumName].attrs.update(gAllNPoMsRaw[spectrumName].attrs)

                    gIdealNorm[spectrumName] = gAllNPoMsNorm[spectrumName]
                    gIdealNorm[spectrumName].attrs.update(gAllNPoMsNorm[spectrumName].attrs)

                    if pl == True:
                        gIdealPl[plSpecName] = gAllNPoMsPl[plSpecName]
                        gIdealPl[plSpecName].attrs.update(gAllNPoMsPl[plSpecName].attrs)

                        gIdealPlNorm[plSpecName] = gAllNPoMsPlNorm[plSpecName]
                        gIdealPlNorm[plSpecName].attrs.update(gAllNPoMsPlNorm[plSpecName].attrs)

    currentTime = time.time() - totalFitStart
    mins = int(old_div(currentTime, 60))
    secs = old_div((np.round((currentTime % 60)*100)),100)
    print('100%% (%s spectra) analysed in %s min %s sec\n' % (last, mins, secs))

    if stats == True:
        doStats(outputFileName, closeFigures = closeFigures, peakFindMidpoint = peakFindMidpoint, pl = pl)

    absoluteEndTime = time.time()
    timeElapsed = absoluteEndTime - absoluteStartTime
    mins = int(old_div(timeElapsed, 60))
    secs = int(np.round(timeElapsed % 60))

    printEnd()

    with h5py.File(outputFileName) as opf:
        gFailed = opf['Failed Spectra']

        if len(gFailed) == 0:
            print('\nFinished in %s min %s sec. Smooth sailing.' % (mins, secs))

        elif len(gFailed) == 1:
            print('\nPhew... finished in %s min %s sec with only %s failure' % (mins, secs, len(gFailed)))

        elif len(gFailed) > len(gAllRaw) * 2:
            print('\nHmmm... finished in %s min %s sec but with %s failures and only %s successful fits' % (mins, secs, len(gFailed),
                                                                                                            len(gAllRaw) - len(gFailed)))
        elif mins > 30:
            print('\nM8 that took ages. %s min %s sec' % (mins, secs))

        else:
            print('\nPhew... finished in %s min %s sec with only %s failures' % (mins, secs, len(gFailed)))

        print('')

if __name__ == '__main__':
    print('\tFunctions initialised')
    #x, yData, summaryAttrs = retrieveData(os.getcwd())
    #initImg = plotInitStack(x, yData, imgName = 'Initial Stack', closeFigures = True)
    outputFileName = createOutputFile('MultiPeakFitOutput')
    fitAllSpectra(os.getcwd(), outputFileName, stats = True, raiseExceptions = True)
    #outputFileName = findH5File(os.getcwd(), nameFormat = 'MultiPeakFitOutput', mostRecent = True)
    #doStats(outputFileName, closeFigures = True, stacks = True, hist = True, irThreshold = 8, minBinFactor = 5, intensityRatios = True,
    #        peakAvgs = True, analRep = True)