# -*- coding: utf-8 -*-
"""
Created on Fri Aug 31 17:45:06 2018
Last updated 2020-09-03

@author: car72
Condenses particle tracking output file into summary file.
Uses functions from Analyse_Z_Scan code (Jack Griffiths).
Output (summary) is directly compatible with Igor (Bart de Nijs) and Python (Charlie Readman) DF multipeakfit codes.
requires lmfit (available via pip install lmfit)
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
import nplab.analysis.NPoM_DF_Analysis.DF_Multipeakfit as mpf
from lmfit.models import ExponentialModel, PowerLawModel, GaussianModel

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

def detectMinima(array, threshold = 0, returnBool = False):
    '''
    detectMinima(array) -> mIndices
    Finds the turning points within a 1D array and returns the indices of the minima.
    '''
    mIndices = []

    if (len(array) < 3):
        return mIndices

    neutral, rising, falling = np.arange(3)

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
                    mIndices.append((begin + i - 1)//2)

            begin = i
            ps = s

    if threshold > 0:
        yRange = array.max() - array.min()
        threshold = array.max() - threshold*yRange
        mIndices = [i for i in mIndices if array[i] < threshold]

    if returnBool == True and len(mIndices) == 0:
        return False

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

def checkCentering(zScan, dz = None):

    if dz is None:
        dz = np.linspace(-3, 3, len(zScan))

    zScanTransposed = np.transpose(zScan) #Transpose to look at scan at each wavelength

    startDex = 132 #500 nm; np.where(x > 500)[0][0]
    finDex = 553 #820 nm; np.where(x > 820)[0][0] - 1

    scanMaxs = np.max(zScanTransposed[startDex:finDex], axis = 1) #Find total intensity of each scan in region 500 - 820 nm; too much noise at longer wavelengths
    fs = 50000
    scanMaxsSmooth = butterLowpassFiltFilt(scanMaxs, cutoff = 1500, fs = fs) #Smoothes the 'spectrum'
    maxWlIndices = detectMinima(-scanMaxsSmooth) + startDex #finds indices of main spectral 'peaks'

    while len(maxWlIndices) > 4:
        #unrealistic, so have another go with stronger smoothing
        fs += 3000
        scanMaxsSmooth = butterLowpassFiltFilt(scanMaxs, cutoff = 1500, fs = fs)
        maxWlIndices = detectMinima(-scanMaxsSmooth) + startDex

    maxWlIndices = np.array([np.arange(i - 2, i + 3) for i in maxWlIndices]).flatten()
    #adds a few either side of each peak for luck

    brightScans = np.array([scan for scan in zScanTransposed[maxWlIndices]])
    #List of corresponding z-stacks
    testFactor = 0
    dZInterp = np.linspace(-3, 3, 41)

    for z in brightScans:
        z[0] = z[1]
        z -= z.min()
        z = np.interp(dZInterp, dz, z)     

        iEdge = np.trapz(z[:10]) + np.trapz(z[-(10):])
        iMid = np.trapz(z[10:-10])
        testFactor += iMid/iEdge

    testFactor /= len(maxWlIndices)
    
    if testFactor > 3.6:      
        #print(f'Aligned ({testFactor:.2f})')
        return True
    else:      
        #print(f'Misaligned ({testFactor:.2f})')
        return False

def lInterp(Value1,Value2,Frac):
    #Value 1 and 2 are two numbers. Frac is between 0 and 1 and tells you fractionally how far between the two values you want ot interpolate

    m=Value2-Value1
    c=Value1

    return (m*Frac)+c

def condenseZscan(zScan, returnMaxs = False, dz = None, threshold = 0.2, Smoothing_width = 1.5, aligned = True):
    """
    
    zScan is assumed to already be background subtracted and referenced.
    """
    if aligned == False:
        '''
        If NP and/or collection path off-centre, centroid method is inaccurate.
        Alternative method just takes maximum value for each wavelength.
        '''
        centroids = np.array([scan[2:].argmax() + 2 for scan in np.transpose(zScan)])
        centroids = np.where(centroids == 0, np.nan, centroids)
        centroids = np.where(centroids == len(dz) - 1, np.nan, centroids).astype(np.float64)
        centroids = mpf.removeNaNs(centroids, nBuff = 1)
        #print(centroids)
        centroidsSmuth = butterLowpassFiltFilt(centroids, cutoff = 900, fs = 80000)
        #print(centroidsSmuth)

        if True in np.isfinite(centroidsSmuth):
            centroids = centroidsSmuth

        centroids = mpf.removeNaNs(centroids)
        #print(centroids)

    else:
        '''
        Z Scan is thresholded and the centroid taken for each wavelength
        '''
        zThresh = mpf.removeNaNs(zScan, buff = True)
        zThresh = zThresh.astype(np.float64)
        zThresh = (zThresh - zThresh.min(axis = 0))/(zThresh.max(axis = 0) - zThresh.min(axis = 0))
        zThresh -= threshold
        zThresh *= (zThresh > 0) #Normalise and Threshold array
        ones = np.zeros([zScan.shape[1]]) + 1
        positions = np.array([ones*n for n in np.arange(zScan.shape[0])]).astype(np.float64)

        centroids = np.sum((zThresh*positions), axis = 0)/np.sum(zThresh, axis = 0) #Find Z centroid position for each wavelength
        centroids = mpf.removeNaNs(centroids)

    zT = np.transpose(zScan)

    output = []
    zProfile = []

    for n, centroid in enumerate(centroids):
        
        try:
            if len(zT[n]) < len(dz):
                print('Wl %s z stack too short' % n)
        except Exception as e:
            print(dz, zT)
            print(f'{n} failed in z stack')
            if len(zT[n]) < len(dz):
                print('Wl %s z stack too short' % n)
        
        if not np.isfinite(centroid):
            if n == 0:
                centroid = centroids[n + 1]
            else:
                centroid = centroids[n - 1]

        try:
            lower = int(centroid)
        except:
            print('aaaaaaa')
            #print(centroids)

        upper = lower + 1

        frac = centroid - lower

        if centroid == centroids[-1] or upper == len(dz):
            upper -= 1
            frac = 0

        try:
            output.append(lInterp(zT[n][lower], zT[n][upper], frac))
            zProfile.append(lInterp(dz[lower], dz[upper], frac))
        except Exception as e:
            print(n, lower, upper, frac)
            raise e

    return np.array(output), np.array(zProfile)

def consoliData(rootDir):
    os.chdir(rootDir)
    print('Consolidating data')
    print('Searching for raw data file...')

    try:
        inputFile = findH5File(rootDir, nameFormat = 'date')
    except:
        print('File not found')

    with h5py.File(inputFile, 'a') as ipf:
        if 'particleScans' in ipf.keys():
            fileType = 'pre-2018'

        elif 'nplab_log' in ipf.keys():
            fileType = 'post-2018'

        else:
            print('File format not recognised')
            return

        if fileType == 'pre-2018':
            ipf = ipf['particleScans']
            gScanFormat = 'scan'
            gParticleFormat = 'z_scan_'

        elif fileType == 'post-2018':
            gScanFormat = 'ParticleScannerScan_'
            gParticleFormat = 'Particle_'

        print('Sorting scans by size...')

        allScans = sorted([groupName for groupName in ipf.keys() if groupName.startswith(gScanFormat) and '%s0' % gParticleFormat in ipf[groupName].keys()],
                              key = lambda groupName: len(ipf[groupName].keys()))[::-1]

        if len(allScans) <= 1:
            print('No extra scans to consolidate')
            return

        for scanName in allScans:
            if len([i for i in ipf[scanName].keys() if i.startswith('Tiles')]) > 1:
                print('Data already consolidated')
                return

        finalScanNo = sorted([groupName for groupName in ipf.keys() if groupName.startswith(gScanFormat)],
                              key = lambda groupName: int(groupName.split('_')[-1]))[-1].split('_')[-1]
        newScanNo = int(finalScanNo) + 1
        consolidatedScan = ipf.create_group('%s%s' % (gScanFormat, newScanNo))

        for n, scanName in enumerate(allScans):
            if scanName == '%s%s' % (gScanFormat, newScanNo):
                continue
            print('Looking for data in %s...' % scanName)
            if '%s0' % gParticleFormat in ipf[scanName].keys():
                particleGroups = [i for i in ipf[scanName].keys() if i.startswith(gParticleFormat)]
                print('\tData found for %s particles' % len(particleGroups))
                scanN = scanName.split('_')[-1]
                gTiles = consolidatedScan.create_group('Tiles_%s' % scanN)
                for tileName in ipf[scanName]['Tiles'].keys():
                    dTileOld = ipf[scanName]['Tiles'][tileName]
                    dTileNew = gTiles.create_dataset(tileName, data = dTileOld)
                    dTileNew.attrs.update(dTileOld.attrs)

                dReconTilesOld = ipf[scanName]['reconstructed_tiles']
                dReconTilesnew = consolidatedScan.create_dataset('reconstructed_tiles_%s' % scanN,
                                                              data = dReconTilesOld)
                dReconTilesnew.attrs.update(dReconTilesOld.attrs)

                existingParticles = sorted([i for i in consolidatedScan.keys() if i.startswith(gParticleFormat)],
                                                key = lambda i: int(i.split('_')[-1]))

                for particleN, groupName in enumerate(particleGroups):
                    gParticleOld = ipf[scanName][groupName]
                    if groupName in consolidatedScan.keys():
                        particleNNew = particleN + int(existingParticles[-1].split('_')[-1]) + 1
                        newGroupName = '%s%s' % (gParticleFormat, particleNNew)
                    else:
                        newGroupName = groupName

                    gParticleNew = consolidatedScan.create_group(newGroupName)
                    gParticleNew.attrs.update(gParticleOld.attrs)
                    for dataName in gParticleOld.keys():
                        print(type(gParticleOld[dataName]))
                        try:
                            newDataset = gParticleNew.create_dataset(dataName, data = gParticleOld[dataName])
                        except:
                            print(type(gParticleOld[dataName]))
                        newDataset.attrs.update(gParticleOld[dataName].attrs)

def extractAllSpectra(rootDir, returnIndividual = True, pl = False, dodgyThreshold = 0.4, start = 0, finish = 0,
                      raiseExceptions = True, consolidated = False, extractZ = True):

    os.chdir(rootDir)

    print('Searching for raw data file...')

    try:
        inputFile = findH5File(rootDir, nameFormat = 'date')
    except:
        print('File not found')

    print('About to extract data from %s' % inputFile)
    outputFile = createOutputFile('summary')

    with h5py.File(inputFile, 'a') as ipf:
        
        if 'particleScans' in ipf.keys():
            fileType = 'pre-2018'

        elif 'nplab_log' in ipf.keys():
            fileType = 'post-2018'

        else:
            print('File format not recognised')
            return

        with h5py.File(outputFile, 'a') as opf:

            gAllOut = opf.create_group('particleScanSummaries')
            dParticleFormat = None

            if returnIndividual == True:
                gInd = opf.create_group('Individual NPoM Spectra')

            if fileType == 'pre-2018':
                ipf = ipf['particleScans']
                gScanFormat = 'scan'
                gParticleFormat = 'z_scan_'
                dParticleFormat = 'z_scan'

            elif fileType == 'post-2018':
                gScanFormat = 'ParticleScannerScan_'
                gParticleFormat = 'Particle_'

            allScans = sorted([groupName for groupName in list(ipf.keys()) if groupName.startswith(gScanFormat)],
                              key = lambda groupName: len(list(ipf[groupName].keys())))[::-1]

            if fileType == 'post-2018':
                particleN = 0
                while dParticleFormat is None:                    
                    for dSetName in list(ipf[allScans[0]][f'Particle_{particleN}'].keys()):
                        if dSetName.startswith('alinger.z_scan') or dSetName.startswith('zScan'):
                            dParticleFormat = dSetName
                            break
                    
                    particleN += 1

            for n, scanName in enumerate(allScans):

                if len(ipf[scanName]) < 15:
                    continue

                if consolidated == True and n > 0:
                    continue

                nummers = list(range(10, 101, 10))
                scanStart = time.time()

                dodgyParticles = []
                dodgyCount = 0

                gScan = gAllOut.create_group('scan%s' % n)

                if returnIndividual == True:
                    gIndScan = gInd.create_group('scan%s' % n)

                spectra = []
                zProfiles = []
                centereds = []
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

                cancelled = 0

                for nn, groupName in enumerate(particleGroups):
                    nn += cancelled

                    if 100 * nn//len(particleGroups) in nummers:
                        currentTime = time.time() - scanStart
                        mins = int(old_div(currentTime, 60))
                        secs = old_div((np.round((currentTime % 60)*100)),100)
                        print('%s%% (%s particles) complete in %s min %s sec' % (nummers[0], nn, mins, secs))
                        nummers = nummers[1:]

                    particleGroup = scan[groupName]
                    
                    if dParticleFormat not in particleGroup.keys():
                        for dSetName in particleGroup.keys():
                            if dSetName.startswith('alinger.z_scan') or dSetName.startswith('zScan'):
                                dParticleFormat = dSetName
                                
                    try:
                        zScan = particleGroup[dParticleFormat]
                    
                        x = zScan.attrs['wavelengths']
                        bg = zScan.attrs['background']
                        ref = zScan.attrs['reference']

                    except:
                        print('Z-Stack not found in %s' % (groupName))
                        cancelled += 1
                        continue

                    if referenced == False:

                        for key in zScan.attrs.keys():
                            attrs[key] = zScan.attrs[key]

                        x = zScan.attrs['wavelengths']
                        bg = zScan.attrs['background']
                        ref = zScan.attrs['reference']
                        ref -= bg
                        ref = np.where(ref != 0, ref, 1)
                        try:
                            dz = zScan.attrs['dz']
                        except:
                            if len(zScan) == 10:
                                dz = np.linspace(-3, 3, 10)
                            else:
                                dz = np.linspace(-2.7, 2.7, (len(zScan)))

                        referenced = True

                    z = zScan[()] - bg #Background subtraction of entire z-scan
                    z /= ref #Normalise to reference

                    if raiseExceptions == True:
                        centered = checkCentering(z, dz = dz)

                    else:
                        try:
                            centered = checkCentering(z, dz = dz)

                        except Exception as e:
                            print('Alignment check failed for Particle %s because %s' % (nn, e))
                            centered = False

                    y, zProfile = condenseZscan(z, returnMaxs = extractZ, dz = dz, aligned = centered)
                    if extractZ == True:
                        zProfiles.append(zProfile)

                    if centered == False:
                        dodgyParticles.append(nn)
                        dodgyCount += 1

                        if 0 < dodgyCount < 50:
                            print('Particle %s not centred properly or too close to another' % nn)

                        elif dodgyCount == 50:
                            print('\nMore than 50 dodgy Z scans found. I\'ll stop clogging up your screen. Assume there are more.\n')

                    spectra.append(y)
                    if returnIndividual == True:
                        gSpectrum = gIndScan.create_dataset('Spectrum %s' % nn, data = y)
                        gSpectrum.attrs['wavelengths'] = x
                        gSpectrum.attrs['Properly centred?'] = centered
                        gSpectrum.attrs['Z Profile'] = zProfile

                currentTime = time.time() - scanStart

                mins = int(old_div(currentTime, 60))
                secs = old_div((np.round((currentTime % 60)*100)),100)
                print('100%% (%s particles) complete in %s min %s sec' % (nn, mins, secs))
                percentDefocused = old_div(100 * len(dodgyParticles), len(spectra))

                if old_div(percentDefocused, 100) > dodgyThreshold:
                    alignment = 'Poor'
                    print('\n\n***Warning: lots of messy spectra (~%s%%). Data may not be reliable. Check nanoparticle alignment***\n' % percentDefocused)

                else:
                    alignment = 'Good'

                print('Adding condensed spectra to %s/spectra...' % scanName)

                spectra = np.array(spectra)
                dScan = gScan.create_dataset('spectra', data = spectra)
                dScan.attrs['Collection spot alignment'] = alignment
                dScan.attrs['Misaligned particle numbers'] = dodgyParticles
                dScan.attrs['%% particles misaligned'] = percentDefocused       

                dScan.attrs.update(attrs)

    print('\nAll spectra condensed and added to summary file\n')

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

def boltzmann(x, height, center, x0 = 0):
    '''
    Maxwell-Boltzmann probability density function with xmax (center), ymax (height) and x offset (x0) as inputs
    '''
    X = x - x0
    center = center - x0
    a = center/np.sqrt(2)
    A = height*np.sqrt(np.pi/2)*(a*np.exp(1)/2)
    return A*np.sqrt(2/np.pi)*(X**2*np.exp(-X**2/(2*a**2)))/a**3

from scipy import sparse
from scipy.sparse.linalg import spsolve

def baseline_als(y, lam, p, niter=10):
    L = len(y)
    D = sparse.diags([1,-2,1],[0,-1,-2], shape=(L,L-2))
    w = np.ones(L)
    for i in range(niter):
        W = sparse.spdiags(w, 0, L, L)
        Z = W + lam * D.dot(D.transpose())
        z = spsolve(Z, w*y)
        w = p * (y > z) + (1-p) * (y < z)
    return z

def approximateLaserBg(xPl, yPl, yDf, plRange = [540, 820], plot = False):
    xTrunc, yTrunc = truncateSpectrum(xPl, yPl, startWl = 505, finishWl = plRange[1])#removes spike from laser leak
    x2, y2 = truncateSpectrum(xPl, yPl, startWl = plRange[1], finishWl = 900)
    xDfTrunc, yDfTrunc = truncateSpectrum(xPl, yDf, startWl = 505)
    yDfSmooth = mpf.butterLowpassFiltFilt(yDfTrunc)
    
    dfMax = yDfSmooth.max()
    
    if np.isfinite(dfMax):
        yDfNorm = yDf/dfMax
    else:
        dfMax = yDfTrunc.max()
        yDfNorm = yDf/dfMax
    
    for xN, yN in zip(xDfTrunc, yDfTrunc):
        if not np.isfinite(yN):
            print(f'nan value at {xN} nm for {groupName}')
            plt.plot(xDfTrunc, yDfTrunc)
            plt.title(groupName)
            plt.show()
        
    yDfNorm = np.where(yDfNorm >= 0, np.sqrt(abs(yDfNorm)), -np.sqrt(abs(yDfNorm)))
    yDfNorm = np.where(yDfNorm != 0, yDfNorm, np.nan)
    yPl /= yDfNorm
    yRef = mpf.removeNaNs(yPl)
    
    x1, y1 = truncateSpectrum(xPl, yRef, startWl = 505, finishWl = plRange[0])
    
    xJoin = np.concatenate((x1, x2))
    yJoin = np.concatenate((y1, y2))
    yJoinMin = np.average(y2[-len(y2)//5:])
    yJoin -= max(yJoinMin, 1e-4)
    #xJoin = x2
    #yJoin = y2

    expMod0 = ExponentialModel(prefix = 'Exp0_')
    expPars = expMod0.make_params(Exp0_amplitude = 1.6e23, Exp0_decay = 8.5)
    expPars['Exp0_amplitude'].set(min = 0)

    expMod1 = ExponentialModel(prefix = 'Exp1_')
    expPars1 = expMod1.make_params(Exp1_amplitude = 2, Exp1_decay = 90)
    expPars1['Exp1_amplitude'].set(min = 0)

    expMod = expMod0 + expMod1
    expPars.update(expPars1)
    initFit = expMod.eval(expPars, x = xTrunc)

    expOut = expMod.fit(yJoin, expPars, x = xJoin, nan_policy = 'propagate')
    yFit = expOut.eval(x = xPl)
    yFit += yJoinMin
    yOut = yPl - yFit
    yOut = mpf.removeNaNs(yOut)

    if plot == True:
        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        yTruncSub = truncateSpectrum(xPl, yOut, startWl = 505, finishWl = plRange[1])[1]
        ax1.plot(xTrunc, yTruncSub, label = 'Processed')
        ax1.plot(x2, y2)
        yTruncFit = truncateSpectrum(xPl, yFit, startWl = 505, finishWl = plRange[1])[1]
        ax1.plot(xTrunc, yTrunc, label = 'Raw')
        yTruncRef = truncateSpectrum(xPl, yPl, startWl = 505, finishWl = plRange[1])[1]
        ax1.plot(xTrunc, yTruncRef, label = 'Referenced')
        ax1.plot(xTrunc, yTruncFit, label = 'Exponential Fit')
        xDf, yDf = truncateSpectrum(xPl, yDf, startWl = 505, finishWl = plRange[1])
        ax2.plot(xDf, yDf, 'k', alpha = 0.5)
        comps = expOut.eval_components()
        print(expOut.params)
        for compName in comps.keys():
            ax1.plot(xJoin, comps[compName], '--', label = compName)
        #ax1.plot(xTrunc, initFit, 'k--', label = 'init')

        ax1.legend()
        plt.show()

    return yOut, yRef

def subtractPlBg(xPl, yPl, plBg, xDf, yDf, remove0 = False, returnArea = True, startWl = 505):

    plBg = truncateSpectrum(xPl, plBg, startWl = startWl, finishWl = 1000)[1]
    xDf, yDf = truncateSpectrum(xDf, yDf, startWl = startWl, finishWl = 1000)
    yDf = threshold(yDf, 2e-4)
    xPl, yPl = truncateSpectrum(xPl, yPl, startWl = startWl, finishWl = 1000)


    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()

    
    ax2.plot(xDf, yDf, 'k', alpha = 0.5)
    #ax1.plot(xPl, plBg)

    bgMin = np.average(plBg[-10:])
    yMin = np.average(yPl[-10:])    

    bgScaled = plBg - bgMin

    ySub = yPl - yMin
    ax1.plot(xPl, ySub, 'k', lw = 2)

    bgScale = ySub[0]/bgScaled[0]

    bgScaled *= bgScale
    bgScaled += yMin
    ax1.plot(xPl, bgScaled)

    ySub = yPl - bgScaled
    yRef = ySub/np.sqrt(yDf/yDf.max())

    ySmooth = butterLowpassFiltFilt(yRef, cutoff = 1000, fs = 90000)
    xTrunc, yTrunc = truncateSpectrum(xPl, ySmooth, startWl = startWl, finishWl = 600)

    fwhm, center, height = getFWHM(xTrunc, yTrunc, smooth = True, peakpos = 545)
    yBoltz = boltzmann(xPl, height, center, x0 = startWl)

    if remove0 == True:
        yRef -= yBoltz

    plt.show()

    if returnArea == True:
        area = trapInt(xPl, yPl)
        return xPl, yRef, yBoltz, area, bgScale

    return xPl, yRef, yBoltz

def exponential(x, amp, shift, decay, const):
    '''y = const + amp when x = 0'''
    '''stepth of curve inversely proportional to decay'''
    return const + (amp*np.exp(old_div(-(x-shift),decay)))

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

def transferPlSpectra(rootDir, start = 0, finish = 0, startWl = 505, plRange = [580, 820], plGroupName = 'PL Spectra'):

    os.chdir(rootDir)

    try:
        inputFile = mpf.findH5File(rootDir, nameFormat = 'date')
    except:
        print('File not found')
        return

    print('\nAbout to extract PL data from %s' % inputFile)
    print('\tLooking for summary file...')

    outputFile = mpf.findH5File(rootDir, nameFormat = 'summary')

    if outputFile == None:
        print('\tNo summary file exists; creating a new one')
        outputFile = createOutputFile('summary')

    with h5py.File(inputFile, 'a') as ipf:

        if 'particleScans' in ipf.keys():
            fileType = 'pre-2018'

        elif 'nplab_log' in list(ipf.keys()):
            fileType = 'post-2018'

        else:
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

            elif fileType == 'post-2018':
                gScanFormat = 'ParticleScannerScan_'
                gParticleFormat = 'Particle_'


            allScans = sorted([groupName for groupName in list(ipf.keys()) if groupName.startswith(gScanFormat)],
                              key = lambda groupName: len(list(ipf[groupName].keys())))[::-1]
            dParticleFormat = None
            if fileType == 'post-2018':
                particleN = 0
                while dParticleFormat is None:                    
                    for dSetName in list(ipf[allScans[0]][f'Particle_{particleN}'].keys()):
                        if dSetName.startswith('alinger.z_scan') or dSetName.startswith('zScan'):
                            dParticleFormat = dSetName
                            break
                    
                    particleN += 1

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
                    plGroupNames = [i for i in ['dark field with irradiation', 'PL Spectra'] if i in particleGroup.keys()]
                    
                    if len(plGroupNames) > 0:
                        plGroupName = plGroupNames[0]
                        if nn == 0:
                            print(plGroupName)
                            
                    if dParticleFormat not in particleGroup.keys():
                        print(f'No Z-Stack in {groupName}')
                        continue

                    bg = particleGroup[dParticleFormat].attrs['background']
                    ref = particleGroup[dParticleFormat].attrs['reference']

                    if int(old_div(100 * nn, len(particleGroups))) in nummers:
                        currentTime = time.time() - scanStart
                        mins = int(old_div(currentTime, 60))
                        secs = old_div((np.round((currentTime % 60)*100)),100)
                        print('%s%% (%s spectra) transferred in %s min %s sec' % (nummers[0], nn, mins, secs))
                        nummers = nummers[1:]

                    if plGroupName not in particleGroup.keys():
                        print(f'{plGroupName} not found in {groupName}')
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
                                plData.attrs['wavelengths'] = scan['Particle_0/%s' % dParticleFormat].attrs['wavelengths']

                            except Exception as e:
                                print('Unable to find wavelength data (%s)' % e)

                        x = plData.attrs['wavelengths']
                        y = plData[()]

                        xTrunc, yTrunc = truncateSpectrum(x, y, startWl = plRange[0], finishWl = plRange[1])
                        ySmooth = butterLowpassFiltFilt(y)
                        maxima = detectMinima(-ySmooth)

                        if len(maxima) == 0:
                            continue

                        yAvg = np.average(ySmooth[maxima])
                        maxDict[yAvg] = specName

                    if len(maxDict.keys()) > 0:
                        maxPlName = maxDict[max(maxDict.keys())]
                    else:
                        print(groupName, plGroup.keys())
                        maxPlName = plSpecNames[0]

                    plData = plGroup[maxPlName]
                    
                    try:
                        bg = plData.attrs.get('background', bg)
                        ref = plData.attrs.get('reference', ref)
                        xPl = plData.attrs['wavelengths']
                        timeStamp = plData.attrs['creation_timestamp']
                        laserPower = plData.attrs['laser_power']
                        plSpecName = f'PL Spectrum {nn}'
                    except Exception as e:
                        plSpecName = f'PL Spectrum {nn}'
                        print(f'{plSpecName} transfer failed because {e}')

                    yRaw = (plData[()] - bg)/ref
                    dfBefore = opf[f'Individual NPoM Spectra/scan0/Spectrum {nn}']
                    xDf = dfBefore.attrs['wavelengths']
                    yDf = dfBefore[()]

                    yPl, yRef = approximateLaserBg(xPl, yRaw, yDf, plRange = plRange, plot = False)
                    
                    #xPl, yRef, yBoltz, area, bgScale = subtractPlBg(xPl, y, plBg, xDf, yDf, remove0 = False, returnArea = True)
                    plSpectra.append(yPl)

                    if plSpecName not in list(gPlScan.keys()):
                        gPlScan.create_dataset(plSpecName, data = yPl)

                    dPl = gPlScan[plSpecName]
                    dPl.attrs['wavelengths'] = xPl
                    dPl.attrs['Raw Spectrum'] = yRef
                    #dPl.attrs['Total Area'] = area
                    #dPl.attrs['Background Scale Factor'] = bgScale

                    attrNames = ['creation_timestamp', 'integration_time', 'laser_power', 'model_name', 'serial_number', 'tec_temperature']

                    for attrName in attrNames:
                        if attrName in plData.attrs.keys():
                            dPl.attrs[attrName] = plData.attrs[attrName]

                    '''if dParticleFormat in particleGroup.keys():
                        dfData = particleGroup[dParticleFormat]

                        x = dfData.attrs['wavelengths']
                        z = dfData[()] - bg
                        z /= ref
                        try:
                            dz = dfData.attrs['dz']
                        except:
                            if len(z) == 10:
                                dz = np.linspace(-3, 3, 10)
                            else:
                                dz = np.linspace(-2.7, 2.7, (len(z)))
                                
                        dfData = condenseZscan(z, dz = dz)

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

                    dPl.attrs['DF After'] = dfData#truncateSpectrum(x, dfData, startWl = startWl, finishWl = 1000)[1]'''

                plSpectra = np.array(plSpectra)
                dAll = gAllPlScan.create_dataset('PL spectra', data = plSpectra)
                dAll.attrs['laser_power'] = laserPower
                #dAll.attrs['Average PL Background'] = plBgDict[laserPower]
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