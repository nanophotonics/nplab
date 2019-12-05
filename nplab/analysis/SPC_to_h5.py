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

class Raman_Spectrum(object):
    #Object class containing spectral data and metadata for single Raman spectrum
    def __init__(self, filename, metadata, laserWl, laserPower, absLaserPower, integrationTime,
                 accumulations, nScans, wavenumbers, ramanIntensities, absRamanIntensities):
        self.filename = filename
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
       .spc files must be directly exported at time of measurement. If .wdf file was re-opened with WiRE and then saved as .spc, use old code ('2017-04-14_Spectra_Class')
       Plots ASCII table with relevant metadata. Set table=False to omit this
       Also plots table for background files if user specifies bg_table = True'''

    '''Actual power values for each % laser power in μW. Measured on 09/05/2017.'''

    print('\nGathering .spc (meta)data...\n')

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
        #try:
        filename = spcFile[:-4] #Removes extension from filename string
        f = spc.File(spcFile) #Create File object from .spc file

        laserWlKeys = ['Laser', ' Laser']

        for laserWlKey in laserWlKeys:

            if laserWlKey in list(f.log_dict.keys()):
                break

        laserWl = int(f.log_dict[laserWlKey][7:10]) #Grabs appropriate part of laser wavelength entry from log and converts to integer (must be 3 characters long)

        lpKeys = ['Laser_power', ' Laser_power']

        for lpKey in lpKeys:

            if lpKey in list(f.log_dict.keys()):
                break

        try:
            laserPower = float(f.log_dict[lpKey][13:-1]) #Grabs numeric part of string containing laser power info and converts to float

        except:
            laserPower = 'Undefined'

        if laserPower in [0.0001, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0]:
            absLaserPower = float(powerConverter[laserWl][laserPower])/1000 #Returns absolute laser power (in mW), given laser wavelength and % laser power.

        else:
            absLaserPower = 'Undefined' #To avoid errors if laser power is not recorded correctly

        try:
            integrationTime = float(f.log_dict['Exposure_time'][6:])
        except:
            integrationTime = float(f.log_dict[' Exposure_time'][6:])

        accumulations = f.log_dict['Accumulations'].split(': ')[1]

        wavenumbers = f.x #Pulls x data from spc file
        nScans = int(f.__dict__['fnsub']) #Number of Raman spectra contained within the spc file (>1 if file contains a kinetic scan)
        ramanIntensities = np.array([f.sub[i].y for i in range(nScans)]) #Builds list of y data arrays

        metadata = f.__dict__ #Pulls metadata dictionary from spc file for easy access

        if absLaserPower != 'Undefined':
            absRamanIntensities = [old_div((spectrum * 1000), (absLaserPower * integrationTime * float(accumulations))) for spectrum in ramanIntensities]

        else:
            absRamanIntensities = ['N/A'] * nScans

        if nScans == 1:
            ramanIntensities = ramanIntensities[0] #Reduces to single array if not a kinetic scan
            absRamanIntensities = absRamanIntensities[0] #Also for this

        spectra.append(Raman_Spectrum(filename, metadata, laserWl, laserPower, absLaserPower, integrationTime, accumulations, nScans,
                                      wavenumbers, ramanIntensities, absRamanIntensities))

        #except Exception as e:
        #    print 'Something went wrong with %s:' % filename
        #    print e
        #    continue

    return spectra

def populateH5(spectra, h5File):

    print('\nPopulating h5 file...')

    with h5py.File(h5File) as f:
        gSpectra = f.create_group('Spectra')

        for n, spectrum in enumerate(spectra):
            name = 'Spectrum %02d: %s' % (n, spectrum.filename)
            gSpectrum = gSpectra.create_group(name)
            attrs = {'Original Filename' : spectrum.filename,
                     'Laser Wavelength'  : spectrum.laserWl,
                     'Laser Power (%%)'  : spectrum.laserPower,
                     'Laser Power (mW)'  : spectrum.absLaserPower,
                     'Integration Time'  : spectrum.integrationTime,
                     'Accumulations'     : spectrum.accumulations,
                     'Number of Scans'   : spectrum.nScans,
                     'Wavenumbers'       : spectrum.wavenumbers}
            attrs.update(spectrum.metadata)

            for key in attrs:

                try:
                    gSpectrum.attrs[key] = attrs[key]
                except:
                    continue

            x = spectrum.wavenumbers
            yRaw = spectrum.ramanIntensities
            yAbs = spectrum.absRamanIntensities

            if spectrum.nScans == 1:
                yNorm = old_div(spectrum.ramanIntensities, spectrum.ramanIntensities.max())

            else:
                yNorm = np.array([old_div(yData,yData.max()) for yData in spectrum.ramanIntensities])

            dRaw = gSpectrum.create_dataset('Raman (cts)', data = yRaw)
            dRaw.attrs['wavelengths'] = x
            dAbs = gSpectrum.create_dataset('Raman (cts mw^-1 s^-1)', data = yAbs)
            dAbs.attrs['wavelengths'] = x
            dNorm = gSpectrum.create_dataset('Raman (normalised)', data = yNorm)
            dNorm.attrs['wavelengths'] = x


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

    print('\th5 file populated')

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

if __name__ == '__main__':

    rootDir = os.getcwd()
    print('Extracting data from %s' % rootDir)
    spectra = extractRamanSpc(rootDir)
    dirName = '%s Raman Data' % rootDir.split('\\')[-1]
    h5FileName = createOutputFile(dirName)
    populateH5(spectra, h5FileName)