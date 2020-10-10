# -*- coding: utf-8 -*-
"""
Created on Tue Jul 03 13:04:50 2018

@author: car72

Gathers Raman data and attributes from directory full of .spc files and turns it into an h5 file'''
Put this script in the same folder as a list of .spc files (must be exported directly from WiRE at time of measurement), set cwd and run
"""
from __future__ import division
from __future__ import print_function

from builtins import range
from past.utils import old_div
from builtins import object
import os
import spc
import h5py
import numpy as np
import matplotlib.pyplot as plt

class Raman_Spectrum(object):
    #Object class containing spectral data and metadata for single Raman spectrum
    def __init__(self, filename, timestamp, metadata, laserWl, laserPower, absLaserPower, integrationTime,
                 accumulations, nScans, wavenumbers, ramanIntensities, absRamanIntensities):
        self.filename = filename
        self.timestamp = timestamp
        self.metadata = metadata
        self.laserWl = laserWl
        self.laserPower = laserPower
        self.absLaserPower = absLaserPower
        self.integrationTime = integrationTime
        self.accumulations = accumulations
        self.nScans = nScans
        self.wavenumbers = wavenumbers
        self.ramanIntensities = ramanIntensities
        self.absRamanIntensities = absRamanIntensities

def extractRamanSpc(path, bg_path = False, combine_statics = False):
    '''Takes all .spc files from a directory and creates Raman_Spectrum object for each and also background subtracts, if specified
       .spc files must be directly exported at time of measurement. 
       Also plots table for background files if user specifies bg_table = True'''

    '''Actual power values for each % laser power in μW. Measured on 09/05/2017.'''

    print('Gathering .spc (meta)data from %s...' % path.split('\\')[-1])

    p532 = { 0.0001 :    0.01,
             0.05   :    4.75,
             0.1    :   12.08,
             0.5    :   49.6 ,
             1.0    :   88.1 ,
             5.0    :  666.  ,
            10.0    : 1219.  ,
            50.0    : 5360.  ,
           100.0    : 9650.   }

    p633 = { 0.0001 :    0.01,
             0.05   :    1.  ,
             0.1    :    2.  ,
             0.5    :   10.  ,
             1.0    :   20.  ,
             5.0    :  112.  ,
            10.0    :  226.  ,
            50.0    : 1130.  ,
           100.0    : 2200.   }

    p785 = { 0.0001 :    0.17,
             0.05   :    8.8 ,
             0.1    :   19.1 ,
             0.5    :   47.8 ,
             1.0    :  104.  ,
             5.0    :  243.  ,
            10.0    :  537.  ,
            50.0    : 1210.  ,
           100.0    : 2130.   }

    powerConverter = {532 : p532, 633 : p633, 785 : p785} #Assigns each laser power dictionary to the appropriate wavelength.

    os.chdir(path)
    spcFiles = [f for f in os.listdir('.') if f.endswith('.spc')]
    spectra = []

    for n, spcFile in enumerate(spcFiles):
        filename = spcFile[:-4] #Removes extension from filename string
        #print(filename)
        f = spc.File(spcFile)
        plt.show()
        #try:
        #    f = spc.File(spcFile) #Create File object from .spc file
        #except:
        #    print(filename)
        #    f = spc.File(spcFile) #Create File object from .spc file

        metadata = {}
        fLogDict = {}
        
        fDicts = [f.__dict__, f.log_dict]#main dictionaries containing spectral metadata
        newFDicts = [metadata, fLogDict]
        
        for dictN, fDict in enumerate(fDicts):
            for k in list(fDict.keys()):
                i = fDict[k]
                #print('%s (%s) = %s (%s)' % (k, type(k), i, type(i)))
                if type(k) == bytes:
                    k = k.decode()#spc module is written in python 2 and hasn't been updated yet; this ensures all strings are in the same (unicode) format
                if type(i) == bytes:
                    try:
                        i = i.decode()
                    except:
                        continue
                    
                if k.startswith(' '):#spc module imperfectly pulls data from some files and includes extra spaces in the dict keys
                    k = k[1:]
                if k.endswith(' '):
                    k = k[:-1]

                if k in ['log_content', 'log_other', 'x']:
                    continue
                    
                newFDicts[dictN][k] = i
            #print('%s (%s) = %s (%s)' % (k, type(k), i, type(i)))

        metadata.update(fLogDict)
        tStamp = []

        for unit in ['year', 'month', 'day', 'hour', 'minute']:#the timestamp values are actually arbitrary, so this is obsolete
            if unit == 'year':
                zFill = 4
            else:
                zFill = 2
            try:
                metadata[unit]
                tStamp.append(str(metadata[unit]).zfill(zFill))
            except:
                tStamp.append(str(0).zfill(zFill))

        try:
            timestamp = np.datetime64('%s-%s-%sT%s:%s' % tuple(tStamp))
        except:
            timestamp = 'N/A'

        try:
            laserWl = int(fLogDict['Laser'][7:10]) #Grabs appropriate part of laser wavelength entry from log and converts to integer (must be 3 characters long)
        except:
            laserWl = 'N/A'

        if 'Laser_power' in list(fLogDict.keys()):
            laserPower = float(fLogDict['Laser_power'][13:-1]) #Grabs numeric part of string containing laser power info and converts to float
        elif 'ND Transmission' in list(fLogDict.keys()):
            laserPower = float(('').join([char for char in fLogDict['ND Transmission'].split(' ')[1] if char == '.' or char.isdigit()]))
        else:
            print(fLogDict.keys())
            laserPower = 'Undefined'

        if laserPower in [0.0001, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0]:
            absLaserPower = float(powerConverter[laserWl][laserPower]) #Returns absolute laser power (in uW), given laser wavelength and % laser power.

        else:
            absLaserPower = 'Undefined' #To avoid errors if laser power is not recorded correctly

        integrationTime = float(fLogDict['Exposure_time'][6:])

        accumulations = int(fLogDict['Accumulations'].split(': ')[-1])#number of scans
        
        wavenumbers = f.x #Pulls x data from spc file
        nScans = int(metadata['fnsub']) #Number of Raman spectra contained within the spc file (>1 if file contains a kinetic scan)
        ramanIntensities = np.array([f.sub[i].y for i in range(nScans)]) #Builds list of y data arrays
        if absLaserPower != 'Undefined':
            #print(filename, absLaserPower)
            absRamanIntensities = np.array([spectrum*1000/(absLaserPower*integrationTime*float(accumulations/1000)) for spectrum in ramanIntensities])

        else:
            absRamanIntensities = ['N/A'] * nScans

        if nScans == 1:
            ramanIntensities = ramanIntensities[0] #Reduces to single array if not a kinetic scan
            absRamanIntensities = absRamanIntensities[0] #Also for this

        spectra.append(Raman_Spectrum(filename, timestamp, metadata, laserWl, laserPower, absLaserPower, integrationTime, accumulations, nScans,
                                      wavenumbers, ramanIntensities, absRamanIntensities))

        #except Exception as e:
        #    print 'Something went wrong with %s:' % filename
        #    print e
        #    continue

    return spectra

def populateH5(spectra, h5File):

    print('\nPopulating h5 file...')

    with h5py.File(h5File, 'a') as f:
        gSpectra = f.create_group('Spectra')

        for n, spectrum in enumerate(spectra):
            
            if len(spectra) < 10:
                name = 'Spectrum %01d: %s' % (n, spectrum.filename)
            elif len(spectra) < 100:
                name = 'Spectrum %02d: %s' % (n, spectrum.filename)
            elif len(spectra) < 1000:
                name = 'Spectrum %03d: %s' % (n, spectrum.filename)
            elif len(spectra) < 10000:
                name = 'Spectrum %04d: %s' % (n, spectrum.filename)

            gSpectrum = gSpectra.create_group(name)
            attrs = spectrum.metadata
            mainAttrs = {'Original Filename' : spectrum.filename,
                         'Laser Wavelength'  : spectrum.laserWl,
                         'Laser Power (%)'   : spectrum.laserPower,
                         'Laser Power (uW)'  : spectrum.absLaserPower,
                         'Integration Time'  : spectrum.integrationTime,
                         'Accumulations'     : spectrum.accumulations,
                         'Number of Scans'   : spectrum.nScans,
                         'Wavenumbers'       : spectrum.wavenumbers,
                         'Timestamp'         : str(spectrum.timestamp)}

            attrs.update(mainAttrs)
            
            for key in attrs:

                try:
                    gSpectrum.attrs[key] = attrs[key]
                except:
                    continue

            x = spectrum.wavenumbers
            yRaw = spectrum.ramanIntensities
            yAbs = spectrum.absRamanIntensities
            
            if type(yAbs) == str or type(yAbs[0]) == str:
                yAbs = np.zeros(len(x))

            if spectrum.nScans == 1:
                if spectrum.ramanIntensities.max() != 0:
                    yNorm = spectrum.ramanIntensities/spectrum.ramanIntensities.max()
                else:
                    yNorm = spectrum.ramanIntensities

            else:
                yNorm = []
                
                for yData in spectrum.ramanIntensities:
                    if np.count_nonzero(yData) > 0:
                        yDataNorm = yData/yData.max()
                    else:
                        yDataNorm = yData
                    yNorm.append(yDataNorm)

                yNorm = np.array(yNorm)

            dRaw = gSpectrum.create_dataset('Raman (cts)', data = yRaw)
            dRaw.attrs['wavelengths'] = x
            dAbs = gSpectrum.create_dataset('Raman (cts mw^-1 s^-1)', data = np.array(yAbs))
            dAbs.attrs['wavelengths'] = dRaw.attrs['wavelengths']
            dNorm = gSpectrum.create_dataset('Raman (normalised)', data = yNorm)
            dNorm.attrs['wavelengths'] = dRaw.attrs['wavelengths']

        gRaw = f.create_group('All Raw')
        gAbs = f.create_group('All Abs')
        gNorm = f.create_group('All Norm')

        spectraNames = sorted(list(f['Spectra'].keys()), key = lambda spectrumName: int(spectrumName.split(':')[0][9:]))

        for spectrumName in spectraNames:
            dRaw = f['Spectra'][spectrumName]['Raman (cts)']
            dRaw = gRaw.create_dataset(spectrumName, data = dRaw)
            dRaw.attrs.update(f['Spectra'][spectrumName].attrs)
            dRaw.attrs.update(f['Spectra'][spectrumName]['Raman (cts)'].attrs)

            dAbs = f['Spectra'][spectrumName]['Raman (cts mw^-1 s^-1)']
            dAbs = gAbs.create_dataset(spectrumName, data = dAbs)
            dAbs.attrs.update(f['Spectra'][spectrumName].attrs)
            dAbs.attrs.update(f['Spectra'][spectrumName]['Raman (cts mw^-1 s^-1)'].attrs)

            dNorm = f['Spectra'][spectrumName]['Raman (normalised)']
            dNorm = gNorm.create_dataset(spectrumName, data = dNorm)
            dNorm.attrs.update(f['Spectra'][spectrumName].attrs)
            dNorm.attrs.update(f['Spectra'][spectrumName]['Raman (normalised)'].attrs)

    print('\th5 file populated\n')

def createOutputFile(filename):

    '''Auto-increments new filename if file exists'''

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

def run():
    rootDir = os.getcwd()
    spectra = extractRamanSpc(rootDir)
    dirName = '%s Raman Data' % rootDir.split('\\')[-1]
    h5FileName = createOutputFile(dirName)
    populateH5(spectra, h5FileName)

if __name__ == '__main__':
    run()