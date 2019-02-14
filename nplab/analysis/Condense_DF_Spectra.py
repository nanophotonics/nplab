# -*- coding: utf-8 -*-
"""
Created on Fri Aug 31 17:45:06 2018

@author: car72
Condenses particle tracking output file into summary file.
Uses functions from Analyse_Z_Scan code (Jack Griffiths).
Output (summary) is directly compatible with Igor (Bart de Nijs) and Python (Charlie Readman) multipeakfit codes.
"""

if __name__ == '__main__':
    print 'Importing modules'

import os
import re
import h5py
import numpy as np
from random import randint
import time
from scipy.signal import butter, filtfilt

if __name__ == '__main__':
    print 'Modules imported\n'
    print 'Initialising...'

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
        h5File = sorted([i for i in os.listdir('.') if re.match('\d\d\d\d-[01]\d-[0123]\d', i[:10])
                         and (i.endswith('.h5') or i.endswith('.hdf5'))],
                        key = lambda i: os.path.getmtime(i))[n]

    else:
        h5File = sorted([i for i in os.listdir('.') if i.startswith(nameFormat)
                         and (i.endswith('.h5') or i.endswith('.hdf5'))],
                        key = lambda i: os.path.getmtime(i))[n]

    print '\nH5 file %s found' % h5File

    return h5File

def createOutputFile(filename):

    '''Auto-increments new filename if file exists. Outputs name of file to be created as a string'''

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

def printEnd():
    print '%s%s%sv gud' % ('\t' * randint(0, 12), '\n' * randint(0, 5), ' ' * randint(0, 4))
    print '%s%swow' % ('\n' * randint(2, 5), ' ' * randint(5, 55))
    print '%s%ssuch python' % ('\n' * randint(0, 5), ' ' * randint(0, 55))
    print '%s%swow' % ('\n' * randint(2, 5), ' ' * randint(5, 55))
    print '%s%smany spectra' % ('\n' * randint(0, 5), ' ' * randint(10, 55))
    print '%s%swow' % ('\n' * randint(2, 5), ' ' * randint(5, 55))
    print '%s%smuch calculation' % ('\n' * randint(0, 5), ' ' * randint(8, 55))
    print '%s%swow' % ('\n' * randint(2, 5), ' ' * randint(5, 55))
    print '\n' * randint(0, 7)

def detectMinima(array):
    '''
    detectMinima(array) -> mIndices
    Finds the minima in a 1D array and returns the indices as a 1D array.
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
                    mIndices.append((begin + i - 1) // 2)

            begin = i
            ps = s

    return np.array(mIndices)

def butterLowpassFiltFilt(data, cutoff = 2000, fs = 20000, order=5):
    '''Smoothes data without shifting it'''
    nyq = 0.5 * fs
    normalCutoff = cutoff / nyq
    b, a = butter(order, normalCutoff, btype='low', analog=False)
    yFiltered = filtfilt(b, a, data)
    return yFiltered

def checkCentering(zScan):
    zScanTransposed = np.transpose(zScan) #Transpose to look at scan at each wavelength
    scanMaxs = np.max(zScanTransposed[68:553], axis = 1) #Find total intensity of each scan in region 450 - 820 nm
    #Higher than 825 is unreliable for this
    fs = 50000
    scanMaxsSmooth = butterLowpassFiltFilt(scanMaxs, cutoff = 1500, fs = fs) #Smoothes the 'spectrum'
    maxWlIndices = detectMinima(-scanMaxsSmooth) + 68 #finds indices of main spectral 'peaks'

    while len(maxWlIndices) > 4:
        #unrealistic, so have another go with stronger smoothing
        fs += 3000
        scanMaxsSmooth = butterLowpassFiltFilt(scanMaxs, cutoff = 1500, fs = fs)
        maxWlIndices = detectMinima(-scanMaxsSmooth) + 68

    maxWlIndices = np.array([range(i - 2, i + 3) for i in maxWlIndices]).flatten()
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

    if centered.count(False) > len(centered)/3:
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

def extractAllSpectra(rootDir, returnIndividual = False, dodgyThreshold = 0.4, start = 0, finish = 0):

    os.chdir(rootDir)

    try:
        inputFile = findH5File(rootDir, nameFormat = 'date')
    except:
        print 'File not found'

    print 'About to extract data from %s' % inputFile
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
                print e
                print 'File format not recognised'
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

            allScans = sorted([groupName for groupName in ipf.keys() if groupName.startswith(gScanFormat)],
                              key = lambda groupName: len(ipf[groupName].keys()))[::-1]

            for n, scanName in enumerate(allScans):

                if len(ipf[scanName]) < 15:
                    continue

                if fileType == '2018':
                    dParticleFormat = 'alinger.z_scan_%s' % n

                nummers = range(10, 101, 10)
                scanStart = time.time()

                dodgyParticles = []
                dodgyCount = 0

                gScan = gAllOut.create_group('scan%s' % n)

                if returnIndividual == True:
                    gIndScan = gInd.create_group('scan%s' % n)

                spectra = []
                attrs = {}
                scan = ipf[scanName]
                particleGroups = sorted([groupName for groupName in scan.keys() if groupName.startswith(gParticleFormat)],
                                key = lambda groupName: int(groupName.split('_')[-1]))

                print '%s particles found in %s' % (len(particleGroups), scanName)
                print '\n0% complete'

                if finish == 0:
                    particleGroups = particleGroups[start:]

                else:
                    particleGroups = particleGroups[start:finish]

                referenced = False

                for nn, groupName in enumerate(particleGroups):

                    if int(100 * nn / len(particleGroups)) in nummers:
                        currentTime = time.time() - scanStart
                        mins = int(currentTime / 60)
                        secs = (np.round((currentTime % 60)*100))/100
                        print '%s%% (%s particles) complete in %s min %s sec' % (nummers[0], nn, mins, secs)
                        nummers = nummers[1:]

                    particleGroup = scan[groupName]

                    try:
                        zScan = particleGroup[dParticleFormat]

                    except:
                        print 'Z-Stack not found in %s' % (groupName)
                        continue

                    if referenced == False:

                        for key in zScan.attrs.keys():
                            attrs[key] = zScan.attrs[key]

                        x = zScan.attrs['wavelengths']
                        bg = zScan.attrs['background']
                        ref = zScan.attrs['reference']

                        referenced = True

                    z = zScan[()] - bg #Background subtraction of entire z-scan
                    z /= ref #Normalise to reference
                    try:
                        centered = checkCentering(z)
                    except:
                        centered = False
                    y = condenseZscan(z)

                    if centered == False:
                        dodgyParticles.append(nn)
                        dodgyCount += 1

                        if 0 < dodgyCount < 50:
                            print 'Particle %s not centred properly or too close to another' % nn

                        elif dodgyCount == 50:
                            print '\nMore than 50 dodgy Z scans found. I\'ll stop clogging up your screen. Assume there are more.\n'

                    if returnIndividual == True:
                        gSpectrum = gIndScan.create_dataset('Spectrum %s' % nn, data = y)
                        gSpectrum.attrs['wavelengths'] = x
                        gSpectrum.attrs['Properly centred?'] = centered

                    spectra.append(y)

                currentTime = time.time() - scanStart
                mins = int(currentTime / 60)
                secs = (np.round((currentTime % 60)*100))/100
                print '100%% (%s particles) complete in %s min %s sec' % (len(particleGroups), mins, secs)
                percentDefocused = 100 * len(dodgyParticles) / len(spectra)

                if percentDefocused / 100 > dodgyThreshold:
                    alignment = 'Poor'
                    print '\n\n***Warning: lots of messy spectra (~%s%%). Data may not be reliable. Check nanoparticle alignment***\n' % percentDefocused

                else:
                    alignment = 'Good'

                spectra = np.array(spectra)
                dScan = gScan.create_dataset('spectra', data = spectra)
                dScan.attrs['Collection spot alignment'] = alignment
                dScan.attrs['Misaligned particle numbers'] = dodgyParticles
                dScan.attrs['%% particles misaligned'] = percentDefocused

                for key in attrs.keys():
                    dScan.attrs[key] = attrs[key]

    return outputFile #String of output file name for easy identification later

if __name__ == '__main__':

    start = 0
    finish = 0

    extractAllSpectra(os.getcwd(), returnIndividual = True, start = start, finish = finish)

    print '\nAll done'
    printEnd()