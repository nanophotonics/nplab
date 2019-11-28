# -*- coding: utf-8 -*-
"""
Created on Fri Aug 31 17:45:06 2018

@author: car72
Condenses particle tracking output file into summary file.
Uses functions from Analyse_Z_Scan code (Jack Griffiths).
Output (summary) is directly compatible with Igor (Bart de Nijs) and Python (Charlie Readman) multipeakfit codes.
"""
from __future__ import division
from __future__ import print_function

from builtins import range
from past.utils import old_div
if __name__ == '__main__':
    print('Importing modules')

import os
import re
import h5py
import numpy as np
from random import randint
import time
from scipy.signal import butter, filtfilt
import matplotlib.pyplot as plt
import scipy.optimize as spo

if __name__ == '__main__':
    print('Modules imported\n')
    print('Initialising...')

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
        h5Files = sorted([i for i in os.listdir('.') if re.match('\d\d\d\d-[01]\d-[0123]\d', i[:10])
                         and (i.endswith('.h5') or i.endswith('.hdf5'))],
                        key = lambda i: os.path.getmtime(i))

    else:
        h5Files = sorted([i for i in os.listdir('.') if i.startswith(nameFormat)
                         and (i.endswith('.h5') or i.endswith('.hdf5'))],
                        key = lambda i: os.path.getmtime(i))

    if len(h5Files) == 0:
        print('\nNo H5 file found')
        return None

    else:
        h5File = h5Files[n]

    print('\tH5 file %s found' % h5File)

    return h5File

def createOutputFile(filename):

    '''Auto-increments new filename if file exists. Outputs name of file to be created as a string'''

    print('\nCreating output file...')

    outputFile = '%s.h5' % filename

    if outputFile in os.listdir('.'):
        print('\n%s already exists' % outputFile)
        n = 0
        outputFile = '%s_%s.h5' % (filename, n)

        while outputFile in os.listdir('.'):
            print('%s already exists' % outputFile)
            n += 1
            outputFile = '%s_%s.h5' % (filename, n)

    print('\tOutput file %s created' % outputFile)

    return outputFile

def printEnd():
    print('%s%s%sv gud' % ('\t' * randint(0, 12), '\n' * randint(0, 5), ' ' * randint(0, 4)))
    print('%s%swow' % ('\n' * randint(2, 5), ' ' * randint(5, 55)))
    print('%s%ssuch python' % ('\n' * randint(0, 5), ' ' * randint(0, 55)))
    print('%s%swow' % ('\n' * randint(2, 5), ' ' * randint(5, 55)))
    print('%s%smany spectra' % ('\n' * randint(0, 5), ' ' * randint(10, 55)))
    print('%s%swow' % ('\n' * randint(2, 5), ' ' * randint(5, 55)))
    print('%s%smuch calculation' % ('\n' * randint(0, 5), ' ' * randint(8, 55)))
    print('%s%swow' % ('\n' * randint(2, 5), ' ' * randint(5, 55)))
    print('\n' * randint(0, 7))

def detectMinima(array):
    '''
    detectMinima(array) -> mIndices
    Finds the minima in a 1D array and returns the indices as a 1D array.
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
                    mIndices.append((begin + i - 1) // 2)

            begin = i
            ps = s

    return np.array(mIndices)

def butterLowpassFiltFilt(data, cutoff = 2000, fs = 20000, order=5):
    '''Smoothes data without shifting it'''

    padded = False

    if len(data) < 18:
        padded = True
        pad = 18 - old_div(len(data),2)
        startPad = np.array([data[0]] * (int(pad) + 1))
        endPad = np.array([data[0]] * (int(pad) + 1))
        data = np.concatenate((startPad, data, endPad))

    nyq = 0.5 * fs
    normalCutoff = old_div(cutoff, nyq)
    b, a = butter(order, normalCutoff, btype='low', analog=False)
    yFiltered = filtfilt(b, a, data)

    if padded == True:
        yFiltered = yFiltered[len(startPad):-len(endPad)]

    return yFiltered

def truncateSpectrum(x, y, startWl = 450, finishWl = 900):
    '''
    Truncates xy data spectrum within a specified wavelength range. Useful for removing high and low-end noise.
    Default range is 450-900 nm
    '''
    x = np.array(x)
    y = np.array(y)
    reverse = False

    if x[0] > x[-1]:
        reverse = True
        x = x[::-1]
        y = y[::-1]

    if x[0] > startWl:#Adds pad to start of y so that output size isn't affected
        xStart = np.arange(x[0], startWl - 2, x[0] - x[1])[1:][::-1]
        yStart = np.array([np.average(y[:5])] * len(xStart))
        x = np.concatenate((xStart, x))
        y = np.concatenate((yStart, y))

    if x[-1] < finishWl:#adds pad at end
        xFin = np.arange(x[-1], finishWl + 2, x[1] - x[0])[1:]
        yFin =  np.array([np.average(y[-5:])] * len(xFin))
        x = np.concatenate((x, xFin))
        y = np.concatenate((y, yFin))

    startIndex = (abs(x - startWl)).argmin()
    finishIndex = (abs(x - finishWl)).argmin()

    xTrunc = np.array(x[startIndex:finishIndex])
    yTrunc = np.array(y[startIndex:finishIndex])

    if reverse == True:
        xTrunc = xTrunc[::-1]
        yTrunc = yTrunc[::-1]

    if xTrunc.size <= 10 and x.size <= 100:

        if startWl > finishWl:
            wl1 = finishWl
            wl2 = startWl
            startWl = wl1
            finishWl = wl2

        xTrunc, yTrunc = np.transpose(np.array([[i, y[n]] for n, i in enumerate(x) if startWl < i < finishWl]))

    return np.array([xTrunc, yTrunc])

def checkCentering(zScan, pl = False):
    zScanTransposed = np.transpose(zScan) #Transpose to look at scan at each wavelength

    startDex = 68
    finDex = 553

    if pl == True:
        startDex = 130

    scanMaxs = np.max(zScanTransposed[startDex:finDex], axis = 1) #Find total intensity of each scan in region 450 (500 if pl taken) - 820 nm
    #Higher than 825 is unreliable for this
    fs = 50000
    scanMaxsSmooth = butterLowpassFiltFilt(scanMaxs, cutoff = 1500, fs = fs) #Smoothes the 'spectrum'
    maxWlIndices = detectMinima(-scanMaxsSmooth) + startDex #finds indices of main spectral 'peaks'

    while len(maxWlIndices) > 4:
        #unrealistic, so have another go with stronger smoothing
        fs += 3000
        scanMaxsSmooth = butterLowpassFiltFilt(scanMaxs, cutoff = 1500, fs = fs)
        maxWlIndices = detectMinima(-scanMaxsSmooth) + startDex

    maxWlIndices = np.array([list(range(i - 2, i + 3)) for i in maxWlIndices]).flatten()
    #adds a few either side of each peak for luck

    brightScansRaw = np.array([scan[1:] for scan in zScanTransposed[maxWlIndices]])
    #List of corresponding z-stacks
    #1st data point is unreliable because of spectrometer memory cache quirks

    for n, scan in enumerate(brightScansRaw):#The second point can also suffer from this
        if abs(scan[1] - scan[0]) >= (scan.max() - scan.min()) * 0.2:
            #If so, set it equal to the next data point
            scan[0] = scan[1]

    brightScans = np.array([butterLowpassFiltFilt(scan) for scan in brightScansRaw])

    #identifies the corresponding z stack for each and smoothes it
    #removes first data point from each
    centered = []

    for n, scan in enumerate(brightScans):
        maxdices = np.array([i for i in detectMinima(-scan) if
                             scan[i] - scan.min() > 0.2 * (scan.max() - scan.min()) and
                             1 < i < len(scan) - 1])
        #list of indices of distinct maxima in smoothed z-stack data
        edgeThresh = 0.4

        if len(maxdices) > 0:
            if (scan[0] - scan.min()) > edgeThresh * (scan[maxdices].max() - scan.min()):
                if (scan[0] - scan.min()) > edgeThresh * (scan[maxdices][0] - scan.min()):
                    if scan[1] - scan[0] < 0:
                        maxdices = np.insert(maxdices, 0, 0)

            if (scan[-1] - scan.min()) > edgeThresh * (scan[maxdices].max() - scan.min()):
                if (scan[-1] - scan.min()) > edgeThresh * (scan[maxdices][-1] - scan.min()):
                    if scan[-1] - scan[-2] > 0:
                        maxdices = np.append(maxdices, len(scan) - 1)
            #test if any obvious maxima exist at either end of the stack

        if len(maxdices) >= 2 and maxdices[-1] - maxdices[0] >= 5:
            #if more than maxima 2 exist in a z-stack, collection was probably off-centre
            #otherwise, probably too close to another bright object
            #intensity data not reliable in this case, so we flag it
            centered.append(False)

        elif (np.argmax(scan) <= 0  or np.argmax(scan) >= len(scan) - 1) and len(maxdices) == 0:
            #if the z-stack has a big dip in the middle, we can assume the same
            centered.append(False)

        else:
            centered.append(True)

    if centered.count(False) > old_div(len(centered),3):
        return False
        #if this happens more than a handful of times, the particle is probably off centre

    else:
        return True

def condenseZscan(zScan):
    """
    Here, the zScan is assumed to already be background subtracted and referenced.
    """
    output = np.array([scan.max() for scan in np.transpose(zScan)])

    return output

def extractAllSpectra(rootDir, returnIndividual = False, pl = False, dodgyThreshold = 0.4, start = 0, finish = 0, raiseExceptions = True):

    os.chdir(rootDir)

    print('Searching for raw data file...')

    try:
        inputFile = findH5File(rootDir, nameFormat = 'date')
    except:
        print('File not found')

    print('About to extract data from %s' % inputFile)
    outputFile = createOutputFile('summary')

    with h5py.File(inputFile, 'a') as ipf:

        try:
            ipf['nplab_log']
            fileType = '2018'

        except:

            try:
                ipf['particleScans']
                fileType = 'pre-2018'

            except Exception as e:
                print(e)
                print('File format not recognised')
                return

        with h5py.File(outputFile, 'a') as opf:

            gAllOut = opf.create_group('particleScanSummaries')

            if returnIndividual == True:
                gInd = opf.create_group('Individual NPoM Spectra')

            if fileType == 'pre-2018':
                ipf = ipf['particleScans']
                gScanFormat = 'scan'
                gParticleFormat = 'z_scan_'
                dParticleFormat = 'z_scan'

            elif fileType == '2018':
                gScanFormat = 'ParticleScannerScan_'
                gParticleFormat = 'Particle_'

            allScans = sorted([groupName for groupName in list(ipf.keys()) if groupName.startswith(gScanFormat)],
                              key = lambda groupName: len(list(ipf[groupName].keys())))[::-1]

            for n, scanName in enumerate(allScans):

                if len(ipf[scanName]) < 15:
                    continue

                if fileType == '2018':
                    dParticleFormat = 'alinger.z_scan_0'

                nummers = list(range(10, 101, 10))
                scanStart = time.time()

                dodgyParticles = []
                dodgyCount = 0

                gScan = gAllOut.create_group('scan%s' % n)

                if returnIndividual == True:
                    gIndScan = gInd.create_group('scan%s' % n)

                spectra = []
                attrs = {}
                scan = ipf[scanName]
                particleGroups = sorted([groupName for groupName in list(scan.keys()) if groupName.startswith(gParticleFormat)],
                                key = lambda groupName: int(groupName.split('_')[-1]))

                print('%s particles found in %s' % (len(particleGroups), scanName))
                print('\n0% complete')

                if finish == 0:
                    particleGroups = particleGroups[start:]

                else:
                    particleGroups = particleGroups[start:finish]

                referenced = False

                for nn, groupName in enumerate(particleGroups):

                    if int(old_div(100 * nn, len(particleGroups))) in nummers:
                        currentTime = time.time() - scanStart
                        mins = int(old_div(currentTime, 60))
                        secs = old_div((np.round((currentTime % 60)*100)),100)
                        print('%s%% (%s particles) complete in %s min %s sec' % (nummers[0], nn, mins, secs))
                        nummers = nummers[1:]

                    particleGroup = scan[groupName]

                    try:
                        zScan = particleGroup[dParticleFormat]

                    except:
                        print('Z-Stack not found in %s' % (groupName))
                        continue

                    if referenced == False:

                        for key in list(zScan.attrs.keys()):
                            attrs[key] = zScan.attrs[key]

                        x = zScan.attrs['wavelengths']
                        bg = zScan.attrs['background']
                        ref = zScan.attrs['reference']

                        referenced = True

                    z = zScan[()] - bg #Background subtraction of entire z-scan
                    z /= ref #Normalise to reference

                    if raiseExceptions == True:
                        centered = checkCentering(z, pl = pl)

                    else:
                        try:
                            centered = checkCentering(z, pl = pl)

                        except Exception as e:
                            print('Alignment check failed because', e)
                            centered = False

                    y = condenseZscan(z)

                    if centered == False:
                        dodgyParticles.append(nn)
                        dodgyCount += 1

                        if 0 < dodgyCount < 50:
                            print('Particle %s not centred properly or too close to another' % nn)

                        elif dodgyCount == 50:
                            print('\nMore than 50 dodgy Z scans found. I\'ll stop clogging up your screen. Assume there are more.\n')

                    spectra.append(y)

                currentTime = time.time() - scanStart
                mins = int(old_div(currentTime, 60))
                secs = old_div((np.round((currentTime % 60)*100)),100)
                print('100%% (%s particles) complete in %s min %s sec' % (len(particleGroups), mins, secs))
                percentDefocused = old_div(100 * len(dodgyParticles), len(spectra))

                if old_div(percentDefocused, 100) > dodgyThreshold:
                    alignment = 'Poor'
                    print('\n\n***Warning: lots of messy spectra (~%s%%). Data may not be reliable. Check nanoparticle alignment***\n' % percentDefocused)

                else:
                    alignment = 'Good'

                spectra = np.array(spectra)
                dScan = gScan.create_dataset('spectra', data = spectra)
                dScan.attrs['Collection spot alignment'] = alignment
                dScan.attrs['Misaligned particle numbers'] = dodgyParticles
                dScan.attrs['%% particles misaligned'] = percentDefocused

                if returnIndividual == True:

                    for nn, groupName in enumerate(particleGroups):
                        gSpectrum = gIndScan.create_dataset('Spectrum %s' % nn, data = dScan[nn])
                        gSpectrum.attrs['wavelengths'] = x
                        gSpectrum.attrs['Properly centred?'] = centered

                for key in list(attrs.keys()):
                    dScan.attrs[key] = attrs[key]

    return outputFile #String of output file name for easy identification later

def collectPlBackgrounds(inputFile):
    '''inputFile must be open hdf5 file object'''

    gPlBg = inputFile['PL Background']

    powerDict = {}
    freqDict = {}

    for key in list(gPlBg.keys()):
        dPlBg = gPlBg[key]

        if 'laser_power' in list(dPlBg.attrs.keys()):
            laserPower = dPlBg.attrs['laser_power']

        else:
            laserPower = int(key.split(' ')[1].split('_')[0])

        if laserPower in list(powerDict.keys()):
            freqDict[laserPower] += 1
            powerDict[laserPower] += dPlBg[()]

        else:
            freqDict[laserPower] = 1
            powerDict[laserPower] = dPlBg[()]

    for key in list(powerDict.keys()):
        powerDict[laserPower] /= freqDict[laserPower]

    return powerDict

def threshold(array, threshold):
    return np.where(array > threshold, array, threshold)

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

def trapInt(x, y):
    '''Calculates area under curve using trapezoid method'''
    '''x and y must have same first dimension'''

    area = 0

    for n, i in enumerate(x[:-1]):
        h = x[n + 1] - x[n]
        a = y[n]
        b = y[n + 1]
        area += old_div(h*(a + b),2)

    return area

def subtractPlBg(xPl, yPl, plBg, xDf, yDf, remove0 = False, returnArea = True):
    plBg = truncateSpectrum(xPl, plBg, startWl = 505, finishWl = 1000)[1]
    yDf = truncateSpectrum(xDf, yDf, startWl = 505, finishWl = 1000)[1]
    yDf = threshold(yDf, 2e-4)
    xPl, yPl = truncateSpectrum(xPl, yPl, startWl = 505, finishWl = 1000)

    bgMin = np.average(plBg[-10:])
    yMin = np.average(yPl[-10:])

    bgScaled = plBg - bgMin
    ySub = yPl - yMin

    bgScale = old_div(ySub[0],bgScaled[0])

    bgScaled *= bgScale
    bgScaled += yMin
    ySub = yPl - bgScaled
    yRef = old_div(ySub,np.sqrt(old_div(yDf,yDf.max())))

    if remove0 == True:
        ySmooth = butterLowpassFiltFilt(yRef, cutoff = 1000, fs = 90000)
        xTrunc, yTrunc = truncateSpectrum(xPl, ySmooth, startWl = 505, finishWl = 600)

        fwhm, center, height = getFWHM(xTrunc, yTrunc, smooth = True, peakpos = 545)
        yGauss = gaussian(xPl, height, center, fwhm)

        yRef -= yGauss

    if returnArea == True:
        area = trapInt(xPl, yPl)
        return xPl, yRef, area, bgScale

    return xPl, yRef

def exponential(x, amp, shift, decay, const):
    '''y = const + amp when x = 0'''
    '''stepth of curve inversely proportional to decay'''
    return const + (amp*np.exp(old_div(-(x-shift),decay)))

def approximateLaserBg(x, y, decays = [50, 50, 50], plRange = [580, 850], optimise = False, plot = False):
    xRaw = x
    yRaw = y

    if plot == True:
        fig, (ax0, ax1, ax2, ax3, ax4) = plt.subplots(5, 1, sharex = True, figsize = (7, 12))
        ax0.plot(xRaw, yRaw)

    x, y = truncateSpectrum(xRaw, yRaw, startWl = 505, finishWl = 1100)

    const = np.average(y[-10:])
    amp = np.average(y[:5]) - const
    shift = x[0]
    yBg1 = exponential(x, amp, shift, decays[0], const)

    if plot == True:
        ax1.plot(x, y, label = 'data')
        ax1.plot(x, yBg1, label = 'bg 1')
        ax1.legend(title = 'init')

    ySub1 = y - yBg1

    ySmooth = butterLowpassFiltFilt(ySub1)

    maxdices = detectMinima(-ySmooth)

    if len(maxdices) > 0:
        maxdex = maxdices[0]
        xMax = x[maxdex]
        yMax = ySmooth[maxdex]

    else:
        xMax = 542
        yMax = ySmooth[abs(x - xMax).argmin()]

    const = np.average(ySub1[-10:])
    amp = yMax - const
    shift = xMax
    xTrunc, ySub1 = truncateSpectrum(x, ySub1, startWl = xMax + 10, finishWl = 1100)
    yBg2 = exponential(xTrunc, amp, shift, decays[1], const)

    if plot == True:
        ax2.plot(xTrunc, ySub1, label = 'Baselined Data')
        ax2.plot(xTrunc, yBg2, label = 'bg 2')
        ax2.legend(title = '1 Baseline')

    ySub2 = ySub1 - yBg2
    const = np.average(ySub2[-10:])
    amp = np.average(ySub2[:20]) - const
    shift = xTrunc[0]
    yBg3 = exponential(xTrunc, amp, shift, decays[2], const)

    if plot == True:
        ax3.plot(xTrunc, ySub2, label = 'Baselined Data')
        ax3.plot(xTrunc, yBg3, label = 'bg 2')
        ax3.legend(title = '2 baselines')

    ySub3 = ySub2 - yBg3

    base0 = np.linspace(xTrunc[0], plRange[0], 10)
    base1 = np.linspace(plRange[1], xTrunc[-1], 5)

    zPts = np.append(base0, base1)

    y0s = [0]

    for zPt in zPts:
        mindex = abs(xTrunc - zPt).argmin()
        y0 = np.average(ySub3[mindex-3:mindex+3])
        y0s.append(y0)

    yEnd = np.average(ySub3[-10:])
    y0s.append(yEnd)

    if plot == True:
        ax4.plot(xTrunc, ySub3, label = 'Baselined Data')
        ax4.plot(zPts, y0s[1:-1], 'o')
        ax4.legend(title = '3 baselines')
        ax4.set_xlabel('Wavelength (nm)')

        plt.subplots_adjust(hspace = 0.05)
        plt.show()

    if optimise == True:
        diff = np.std(y0s)
        return xTrunc, ySub3, diff

    else:
        return xTrunc, ySub3

def removeLaserLeak(x, y, plotAll = False, plotFinal = False, plRange = [580, 850]):

    def loss(decays):
        '''x and y must be externally defined'''
        diff = approximateLaserBg(x, y, decays = decays, optimise = True, plot = False)[-1]
        return diff

    decaysGuess = [50, 50, 50]
    decays = spo.minimize(loss, decaysGuess, bounds = [(30, 70)] * 3).x

    xTrunc, yBld = approximateLaserBg(x, y, decays = decays, plot = plotAll)

    if plotFinal == True:
        plt.plot(xTrunc, yBld)
        plt.show()

    return xTrunc, yBld

def transferPlSpectra(rootDir, start = 0, finish = 0, startWl = 505, plRange = [580, 850]):

    os.chdir(rootDir)

    try:
        inputFile = findH5File(rootDir, nameFormat = 'date')
    except:
        print('File not found')
        return

    print('\nAbout to extract PL data from %s' % inputFile)
    print('\tLooking for summary file...')

    outputFile = findH5File(rootDir, nameFormat = 'summary')

    if outputFile == None:
        print('\tNo summary file exists; creating a new one')
        outputFile = createOutputFile('summary')

    with h5py.File(inputFile, 'a') as ipf:

        try:
            ipf['nplab_log']
            fileType = '2018'

        except:

            try:
                ipf['particleScans']
                fileType = 'pre-2018'

            except Exception as e:
                print(e)
                print('File format not recognised')
                return

        with h5py.File(outputFile, 'a') as opf:

            if 'NPoM PL Spectra' not in list(opf.keys()):
                opf.create_group('NPoM PL Spectra')

            gPl = opf['NPoM PL Spectra']
            gAllPl = opf['particleScanSummaries']

            if fileType == 'pre-2018':
                ipf = ipf['particleScans']
                gScanFormat = 'scan'
                gParticleFormat = 'z_scan_'

            elif fileType == '2018':
                gScanFormat = 'ParticleScannerScan_'
                gParticleFormat = 'Particle_'

            plGroupName = 'dark field with irradiation'

            allScans = sorted([groupName for groupName in list(ipf.keys()) if groupName.startswith(gScanFormat)],
                              key = lambda groupName: len(list(ipf[groupName].keys())))[::-1]

            for n, scanName in enumerate(allScans):

                if len(ipf[scanName]) < 15:
                    continue

                if 'scan%s' % n not in list(gPl.keys()):
                    gPl.create_group('scan%s' % n)

                gPlScan = gPl['scan%s' % n]

                if 'scan%s' % n not in list(gAllPl.keys()):
                    gPl.create_group('scan%s' % n)

                gAllPlScan = gAllPl['scan%s' % n]

                scan = ipf[scanName]
                particleGroups = sorted([groupName for groupName in list(scan.keys()) if groupName.startswith(gParticleFormat)],
                                key = lambda groupName: int(groupName.split('_')[-1]))

                print('%s particles found in %s' % (len(particleGroups), scanName))

                if finish == 0:
                    particleGroups = particleGroups[start:]

                else:
                    particleGroups = particleGroups[start:finish]

                nummers = list(range(10, 101, 10))
                scanStart = time.time()

                plSpectra = []

                for nn, groupName in enumerate(particleGroups):

                    particleGroup = scan[groupName]
                    bg = particleGroup['alinger.z_scan_0'].attrs['background']
                    ref = particleGroup['alinger.z_scan_0'].attrs['reference']

                    if int(old_div(100 * nn, len(particleGroups))) in nummers:
                        currentTime = time.time() - scanStart
                        mins = int(old_div(currentTime, 60))
                        secs = old_div((np.round((currentTime % 60)*100)),100)
                        print('%s%% (%s spectra) transferred in %s min %s sec' % (nummers[0], nn, mins, secs))
                        nummers = nummers[1:]

                    if plGroupName not in list(particleGroup.keys()):
                        print('No PL spectra in %s' % (groupName))
                        continue

                    plGroup = particleGroup[plGroupName]

                    maxDict = {}
                    plSpecNames = [i for i in list(plGroup.keys()) if i.startswith('PL')]

                    if len(plSpecNames) == 0:
                        print('No PL spectrum found for %s' % groupName)
                        continue

                    for specName in plSpecNames:
                        plData = plGroup[specName]

                        if 'wavelengths' not in list(plData.attrs.keys()):
                            try:
                                plData.attrs['wavelengths'] = scan['Particle_0/alinger.z_scan_0'].attrs['wavelengths']

                            except Exception as e:
                                print('Unable to find wavelength data (%s)' % e)

                        x = plData.attrs['wavelengths']
                        y = plData[()]

                        xTrunc, yTrunc = truncateSpectrum(x, y, startWl = 520, finishWl = 800)
                        ySmooth = butterLowpassFiltFilt(y)
                        maxima = detectMinima(-ySmooth)

                        if len(maxima) == 0:
                            continue

                        yAvg = np.average(ySmooth[maxima])
                        maxDict[yAvg] = specName

                    if len(list(maxDict.keys())) > 0:
                        maxPlName = maxDict[max(maxDict.keys())]
                    else:
                        print(groupName, list(plGroup.keys()))
                        maxPlName = plSpecNames[0]

                    plData = plGroup[maxPlName]
                    xPl = plData.attrs['wavelengths']
                    timeStamp = plData.attrs['creation_timestamp']
                    plSpecName = 'PL Spectrum %s' % nn

                    if 'PL Background' not in list(ipf.keys()):
                        rootDir = os.getcwd()
                        powerDir = r'C:\Users\car72\University Of Cambridge\OneDrive - University Of Cambridge\Documents\PhD\Data\NP\Porphyrins\NPoM\DF\2019-09-18 Zn-MTPP Cl 48 h 80 nm + PL'
                        os.chdir(powerDir)
                        h5File = '2019-09-18.h5'
                        with h5py.File(h5File) as powerFile:
                            plBgDict = collectPlBackgrounds(powerFile)

                        os.chdir(rootDir)

                    else:
                        plBgDict = collectPlBackgrounds(ipf)

                    laserPower = plData.attrs['laser_power']
                    plBg = plBgDict[laserPower]

                    #try:
                    #    xTrunc, yBld = removeLaserLeak(x, plData[()], plRange = plRange)

                    #except Exception as e:
                    #    print 'Laser leak removal failed for groupName because %s' % (e)
                    #    yBld = plData[()]
                    #    xTrunc = x

                    #xTrunc, plTrunc = truncateSpectrum(xTrunc, yBld, startWl = plRange[0], finishWl = plRange[1])

                    y = plData[()]
                    dfBefore = opf['Individual NPoM Spectra/scan0/Spectrum %s' % nn]
                    xDf = dfBefore.attrs['wavelengths']
                    yDf = dfBefore[()]

                    xPl, yRef, area, bgScale = subtractPlBg(xPl, y, plBg, xDf, yDf, remove0 = False, returnArea = True)
                    plSpectra.append(yRef)

                    if plSpecName not in list(gPlScan.keys()):
                        gPlScan.create_dataset(plSpecName, data = yRef)

                    dPl = gPlScan[plSpecName]
                    dPl.attrs['wavelengths'] = xPl
                    dPl.attrs['Raw Spectrum'] = plData[()]
                    dPl.attrs['Total Area'] = area
                    dPl.attrs['Background Scale Factor'] = bgScale

                    attrNames = ['creation_timestamp', 'integration_time', 'laser_power', 'model_name', 'serial_number', 'tec_temperature']

                    for attrName in attrNames:
                        dPl.attrs[attrName] = plData.attrs[attrName]

                    if 'alinger.z_scan_1' in list(particleGroup.keys()):
                        dfData = particleGroup['alinger.z_scan_1']
                        x = dfData.attrs['wavelengths']
                        z = dfData - bg
                        z /= ref
                        dfData = condenseZscan(z)

                    else:
                        dfSpecNames = [specName for specName in list(plGroup.keys()) if specName.startswith('DF') and
                                       plGroup[specName].attrs['creation_timestamp'] > timeStamp]

                        if len(dfSpecNames) > 0:
                            dfSpecName = dfSpecNames[1]
                            dfData = plGroup[dfSpecName][()]

                            if dfData.max() > 777:
                                dfData = dfData - bg #Background subtraction
                                dfData /= ref #Normalise to reference

                        else:
                            dfData = 'N/A'

                    dPl.attrs['DF After'] = dfData#truncateSpectrum(x, dfData, startWl = startWl, finishWl = 1000)[1]

                plSpectra = np.array(plSpectra)
                dAll = gAllPlScan.create_dataset('PL spectra', data = plSpectra)
                dAll.attrs['laser_power'] = laserPower
                dAll.attrs['Average PL Background'] = plBgDict[laserPower]
                dAll.attrs['wavelengths'] = xPl

    currentTime = time.time() - scanStart
    mins = int(old_div(currentTime, 60))
    secs = old_div((np.round((currentTime % 60)*100)),100)
    print('100%% complete in %s min %s sec' % (mins, secs))

    print('\tAll PL data transferred to summary file')

    return outputFile #String of output file name for easy identification later

if __name__ == '__main__':

    start = 0
    finish = 0
    pl = False

    extractAllSpectra(os.getcwd(), pl = pl, returnIndividual = True, start = start, finish = finish)
    transferPlSpectra(os.getcwd(), start = start, finish = finish)

    print('\nAll done')
    printEnd()