'''
For use with AuNP aggregate extinction timescan .h5 data from OO Spectrometer in lab 9
Just call "fitAllSpectra('your_filename.h5')" to run
'''

import time
import os
import h5py
import numpy as np
from cycler import cycler
import matplotlib.pyplot as plt
from matplotlib import cm
from importlib import reload
from scipy.integrate import quad as spQuad
from scipy import sparse
from scipy.sparse.linalg import spsolve
import nplab.analysis.NPoM_DF_Analysis.DF_Multipeakfit as mpf
from matplotlib.ticker import (MultipleLocator, FormatStrFormatter,
                               AutoMinorLocator)
import matplotlib as mpl
from IPython import display as ipDisp
from lmfit.models import LorentzianModel
from lmfit.models import GaussianModel
from lmfit.models import StepModel
from lmfit.models import ExpressionModel
from lmfit.models import LinearModel
from lmfit.models import ConstantModel
from lmfit import Model

rootDir = os.getcwd()
np.seterr('ignore')

plotParDict = {
    'legend.fontsize':
    18,
    'legend.title_fontsize':
    20,
    'figure.figsize': (12, 7),
    'figure.titlesize':
    24,
    'axes.labelsize':
    24,
    'axes.titlepad':
    10,
    'axes.titlesize':
    24,
    'axes.spines.right':
    'on',
    'axes.spines.top':
    'on',
    'axes.prop_cycle':
    cycler('color', [plt.cm.Dark2(i) for i in np.linspace(0, 1., 8)]),
    'xtick.labelsize':
    22,
    'ytick.labelsize':
    22,
    'xtick.direction':
    'in',
    'ytick.direction':
    'in',
    'font.size':
    24,
    'lines.linewidth':
    2,
    'axes.linewidth':
    2,
    'patch.linewidth':
    2,
    'xtick.major.width':
    2,
    'xtick.major.size':
    4,
    'xtick.minor.width':
    1.5,
    'xtick.minor.size':
    2,
    'ytick.major.width':
    2,
    'ytick.major.size':
    4,
    'ytick.minor.width':
    1.5,
    'ytick.minor.size':
    2,
    'legend.facecolor':
    'ivory',
    'legend.fancybox':
    True,
    'legend.edgecolor':
    'darkgray',
    'legend.shadow':
    False,
    'font.family':
    'sans-serif',
    #'font.sans-serif' : 'Trebuchet MS',
    #'font.sans-serif' : 'Trebuchet MS',
    #'mathtext.fontset' : 'custom',
    #'mathtext.rm' : 'Trebuchet MS',
    #'mathtext.it' : 'Trebuchet MS:italic',
    #'mathtext.bf' : 'Trebuchet MS:bold',
    'figure.constrained_layout.hspace':
    0.082,
    'figure.constrained_layout.wspace':
    0.1,
    'savefig.bbox':
    'tight'
}
boxPropDict = {
    'boxstyle': 'round',
    'facecolor': 'ivory',
    'edgecolor': 'darkgray',
    'linewidth': 3,
    'alpha': 0.9
}

aggExtOther = {
    'titleBbox': {
        'boxstyle': 'square',
        'facecolor': 'white',
        'edgecolor': 'white',
        'linewidth': 0,
        'alpha': 1
    },
    'titleWeight': 1.3,
    'titlePosition': (0.5, 1),
    'titleHAlign': 'center',
    'titleVAlign': 'center',
    'legendTitlesize': 18,
    'figRect': [0, 0, 0.85, 1],
    'cbarLeft': 0.85,
    'cbarWidth': 0.05,
    'cmap': 'jet_r',
    'mainAlpha': 0.7,
    'mainLw': 3,
    'nullColor': 'grey',
    'nullAlpha': 0.5,
    'nullLw': 0.5
}

plt.rcParams.update(plotParDict)
totalStartTime = time.time()


def makeDir(dirName):
    if dirName not in os.listdir('.'):
        os.mkdir(dirName)


def getCol(n, dSetSize, cmap, rev=False):
    cIndex = n * 256 / dSetSize
    #print(cIndex)
    if rev == True:
        cIndex = 256 - cIndex
    color = cmap(int(cIndex))
    return color


def trapNumInt(x, y):

    for n, i in enumerate(x):
        if n == 0:
            area = 0
            continue

        h = i - x[n - 1]
        y1 = y[n]
        y0 = y[n - 1]
        yAvg = np.average([y0, y1])
        aI = yAvg * h
        area += aI

    return area


def lorentzian(x, height, center, fwhm):
    I = height
    x0 = center
    gamma = fwhm / 2
    numerator = gamma**2
    denominator = (x - x0)**2 + gamma**2
    quot = numerator / denominator

    y = I * quot
    return y


def gaussian(x, height, center, fwhm, offset=0):
    '''Gaussian as a function of height, centre, fwhm and offset'''
    a = height
    b = center
    c = fwhm

    N = 4 * np.log(2) * (x - b)**2
    D = c**2
    F = -N / D
    E = np.exp(F)
    y = a * E
    y += offset

    return y


def baseline_als(y, lam, p, niter=10):
    L = len(y)
    D = sparse.diags([1, -2, 1], [0, -1, -2], shape=(L, L - 2))
    w = np.ones(L)
    for i in range(niter):
        W = sparse.spdiags(w, 0, L, L)
        Z = W + lam * D.dot(D.transpose())
        z = spsolve(Z, w * y)
        w = p * (y > z) + (1 - p) * (y < z)
    return z


def nmToEv(nm):
    wavelength = nm * 1e-9
    c = 299792458
    h = 6.62607015e-34
    joules = h * c / wavelength
    e = 1.60217662e-19
    eV = joules / e
    return eV


def evToNm(eV):
    e = 1.60217662e-19
    joules = eV * e
    c = 299792458
    h = 6.62607015e-34
    wavelength = h * c / joules
    nm = wavelength * 1e9
    return nm


class ExtinctionSpectrum:
    def makeNull(self):
        self.dimerCenter = np.nan
        self.dimerHeight = np.nan
        self.dimerFwhm = np.nan
        self.chainCenter = np.nan
        self.chainHeight = np.nan
        self.chainFwhm = np.nan

    def debug(self):
        self.debug = True

    def __init__(self, x, y, startWl=420, endWl=950, initSpec=None):
        self.makeNull()

        if x is None:
            return

        self.xRaw = mpf.removeNaNs(x)
        self.yRaw = mpf.removeNaNs(y)

        self.startWl = startWl
        self.endWl = endWl
        self.xTrunc, self.yTrunc = mpf.truncateSpectrum(self.xRaw,
                                                        self.yRaw,
                                                        startWl=self.startWl,
                                                        finishWl=self.endWl)
        self.ySmooth = mpf.butterLowpassFiltFilt(self.yTrunc,
                                                 cutoff=1100,
                                                 fs=70000)
        self.debug = False
        self.specMaxWl = None

        if initSpec is not None:
            initX, initY, initYSmooth = initSpec.xTrunc, initSpec.yTrunc, initSpec.ySmooth
            initAunpWl = initX[initYSmooth.argmax()]

            if not np.all(initX == self.xTrunc):
                initY = np.interp(self.xTrunc, initX, initY)
                initYSmooth = mpf.butterLowpassFiltFilt(initY)

            aunpIndex = initYSmooth.argmax()
            initAunpWl = self.xTrunc[aunpIndex]

            initY -= initYSmooth[-1] - self.ySmooth[-1]
            initYSmooth -= initYSmooth[-1] - self.ySmooth[-1]

            scaling = self.ySmooth[aunpIndex] / initYSmooth[aunpIndex]

            self.aunpSpec = initY * scaling
            self.ySub = self.yTrunc - initY * scaling
            self.ySubSmooth = self.ySmooth - initYSmooth * scaling

        else:
            self.aunpSpec = None
            self.ySub = self.yTrunc

    def fitAggPeaks(self, dimerWl=None, plot=False):
        '''
        InitY is monomeric AuNP spectrum, scaled if necessary. Must have same length as x and y
        '''
        x, y = self.xTrunc, self.ySub
        ySmooth = mpf.butterLowpassFiltFilt(y, cutoff=1200, fs=65000)
        mindices = mpf.detectMinima(ySmooth)

        if plot == True:
            plt.plot(x, y)
            plt.plot(x, ySmooth)
            plt.show()

        mindices = mindices[np.where(x[mindices] > 500)]
        startMindex = mindices[0] if len(mindices) > 0 else abs(x -
                                                                500).argmin()
        #startMindex = int(np.round(np.average([startMindex, abs(x-600).argmin()])))

        xFit, yFit, yFitSmooth = x[startMindex:], y[startMindex:], ySmooth[
            startMindex:]
        yFit -= yFitSmooth.min()
        yFitSmooth -= yFitSmooth.min()
        self.specMaxWl = xFit[yFitSmooth.argmax()]

        if dimerWl is None:
            initDimerWl = self.specMaxWl
            dimerIndex = abs(xFit - initDimerWl).argmin()
            initDimerHeight = yFitSmooth.max()
        else:
            initDimerWl = dimerWl
            dimerIndex = abs(xFit - initDimerWl).argmin()
            initDimerHeight = yFitSmooth[dimerIndex]

        yOffset = -yFitSmooth.min()
        yFit += yOffset
        initDimerHeight += yOffset
        yFitSmooth += yOffset

        xFit = -nmToEv(xFit)
        xFitNm = evToNm(-xFit)
        initDimerWl = xFit[dimerIndex]

        try:
            dimerHalfMaxDex = abs(yFitSmooth[:dimerIndex] -
                                  initDimerHeight / 2).argmin()
        except:
            if self.debug == True:
                print(dimerWl, initDimerWl, dimerIndex)
            return

        initDimerFwhm = 2 * (initDimerWl - xFit[dimerHalfMaxDex])
        initDimerFwhmEv = abs(xFit[dimerHalfMaxDex] -
                              xFit[2 * dimerIndex - dimerHalfMaxDex])

        dimerInit = lorentzian(xFit, initDimerHeight, initDimerWl,
                               initDimerFwhm)

        dimerInit -= dimerInit[0] - yFitSmooth[0]
        dimerInit *= initDimerHeight / dimerInit.max()

        chainInit = yFitSmooth - dimerInit
        initChainIndex = dimerIndex + chainInit[dimerIndex:].argmax()

        if plot == True:
            plt.plot(xFit, yFit)
            plt.plot(xFit[dimerIndex:initChainIndex],
                     chainInit[dimerIndex:initChainIndex],
                     zorder=10)
            plt.plot(xFit, dimerInit)
            plt.plot(xFit, chainInit)
            plt.plot(xFit[initChainIndex], chainInit[initChainIndex], 'o')
            #plt.plot(xFit[chainHalfMaxDex], chainInit[chainHalfMaxDex], 'ko')
            plt.plot(xFit, dimerInit + chainInit, 'r--')
            plt.show()

        aggMod = LorentzianModel(prefix='Dimer_')
        aggModPars = aggMod.guess(dimerInit, x=xFit)
        aggModPars['Dimer_center'].set(initDimerWl,
                                       min=initDimerWl - initDimerFwhm / 2,
                                       max=initDimerWl + initDimerFwhm / 2)
        aggModPars['Dimer_sigma'].set(initDimerFwhm / 2)
        aggModPars['Dimer_height'].set(initDimerHeight * 2 / 3,
                                       max=initDimerHeight,
                                       min=0)
        aggModPars['Dimer_amplitude'].set(min=0)

        if initChainIndex < dimerIndex:
            chainMode = False
        else:
            chainMode = True
            initChainWl, initChainHeight = xFit[initChainIndex], chainInit[
                initChainIndex]

            try:
                chainHalfMaxDex = dimerIndex + abs(
                    chainInit[dimerIndex:initChainIndex] -
                    initChainHeight / 2).argmin()
            except:
                chainHalfMaxDex = np.average([initChainIndex, dimerHalfMaxDex])

                if self.debug == True:
                    print(initChainIndex, chainInit[dimerIndex:initChainIndex])
                    plt.plot(xFitNm, yFit)
                    plt.plot(xFitNm[dimerHalfMaxDex],
                             yFitSmooth[dimerHalfMaxDex], 'o')
                    plt.plot(xFitNm, dimerInit)
                    plt.plot(xFitNm, chainInit)
                    plt.plot(xFitNm[dimerIndex], chainInit[dimerIndex], 'ro')
                    plt.plot(xFitNm[initChainIndex], chainInit[initChainIndex],
                             'ko')
                    plt.show()
                chainMode = False

            initChainFwhm = 2 * (initChainWl - xFit[chainHalfMaxDex])
            try:
                initChainFwhmEv = abs(
                    xFit[chainHalfMaxDex] -
                    xFit[max(2 * initChainIndex - chainHalfMaxDex,
                             len(xFit) - 1)])
            except:
                if self.debug == True:
                    print(chainHalfMaxDex,
                          2 * initChainIndex - chainHalfMaxDex)
                chainMode = False

            if chainMode == True:
                chainInit = lorentzian(xFit, initChainHeight, initChainWl,
                                       initChainFwhm)
                gModC = LorentzianModel(prefix='Chain_')
                parsC = gModC.guess(chainInit, x=xFit)
                parsC['Chain_sigma'].set(initChainFwhm / 2)
                parsC['Chain_height'].set(initChainHeight * 2 / 3,
                                          max=initChainHeight,
                                          min=0)
                parsC['Chain_amplitude'].set(min=0)

                aggMod += gModC
                aggModPars.update(parsC)

                aggModPars['Chain_center'].set(initChainWl, min=initDimerWl)

        aggFit = aggMod.fit(yFit, aggModPars, x=xFit)
        xTruncEv = evToNm(-self.xTrunc)
        yAggFit = aggFit.eval(x=xTruncEv)
        finalParams = aggFit.params
        comps = aggFit.eval_components(x=xTruncEv)

        xFit = evToNm(-xFit)

        if plot == True:
            plt.plot(self.xTrunc, self.ySub, 'k')
            plt.plot(self.xTrunc, yAggFit, 'r')
            for comp in comps.keys():
                print(comp)
                plt.plot(self.xTrunc, comps[comp], label=comp)
            plt.legend(loc=0)
            plt.xlim(self.startWl, self.endWl)
            plt.xlabel('Wavelength (nm)')
            plt.ylabel('$\Delta$A')
            plt.show()

        self.dimerCenterEv = finalParams['Dimer_center'].value
        self.dimerCenter = evToNm(-self.dimerCenterEv)
        self.dimerHeight = comps['Dimer_'].max()
        self.dimerFwhmEv = finalParams['Dimer_fwhm'].value
        self.dimerFwhm = abs(
            evToNm(self.dimerCenterEv + self.dimerFwhmEv) -
            evToNm(self.dimerCenterEv - self.dimerFwhmEv))
        self.dimerFit = comps['Dimer_']

        if chainMode == True:
            self.chainCenterEv = finalParams['Chain_center'].value
            self.chainCenter = evToNm(-self.chainCenterEv)
            self.chainHeight = comps['Chain_'].max()
            self.chainFwhmEv = finalParams['Chain_fwhm'].value
            self.chainFwhm = abs(
                evToNm(self.chainCenterEv + self.chainFwhmEv) -
                evToNm(self.chainCenterEv - self.chainFwhmEv))
            self.chainFit = comps['Chain_']
        else:
            self.chainCenter = np.nan
            self.chainCenterEv = np.nan
            self.chainHeight = np.nan
            self.chainFwhm = np.nan
            self.chainFwhmEv = np.nan
            self.chainFit = np.zeros(len(self.xTrunc))

    def findDimerIndex(self, plot=False, returnAll=False):
        x = self.xTrunc
        ySmooth = mpf.butterLowpassFiltFilt(self.ySub, cutoff=1200, fs=65000)
        dimerWl = self.dimerCenter

        if dimerWl == None:
            self.dimerWl = None

            if plot == True:
                print('Dimer Wl is None')
                plt.plot(x, ySmooth)
                plt.show()

            return

        elif dimerWl < 600:
            self.dimerWl = None
            print('Dimer Wl < 600')

            #if plot == True:
            #    plt.plot(*mpf.truncateSpectrum(x, self.ySub, startWl = 550, finishWl = 900))
            #    plt.show()
            return

        dimerIndex = abs(self.xTrunc - dimerWl).argmin()
        y = self.ySub / ySmooth[dimerIndex]
        xy1 = mpf.truncateSpectrum(x, y, startWl=500, finishWl=600)
        x2, y2 = mpf.truncateSpectrum(x, y, startWl=600, finishWl=900)
        ySmooth = mpf.butterLowpassFiltFilt(y2, cutoff=1200, fs=65000)
        y2 /= ySmooth.max()
        ySmooth /= ySmooth.max()

        mindices = mpf.detectMinima(ySmooth)

        if len(mindices) == 0:
            mindices = [0]

        if x2[mindices[0]] > 700:
            mindices = [0]

        xDimer = x2[mindices[0]:]
        yDimer = y2[mindices[0]:]
        ySmooth = ySmooth[mindices[0]:]
        dimerIndex = ySmooth.argmax()

        self.dimerWl = xDimer[dimerIndex]

        #try:
        #    mpf.getFWHM(xDimer, yDimer, maxdex = dimerIndex)
        #except:
        #    print('fwhmdfgd failed')
        fwhm, center, height = mpf.getFWHM(xDimer,
                                           ySmooth,
                                           maxdex=dimerIndex,
                                           fwhmFactor=1.3)
        xLorz, yLorz = mpf.truncateSpectrum(
            xDimer,
            yDimer,
            startWl=max(xDimer.min(), center - 5 - fwhm / 2),
            endWl=min(xDimer.max(), center + 5 + fwhm / 2))
        lMod = LorentzianModel()
        lModPars = lMod.guess(ySmooth, x=xDimer)
        lModPars['center'].set(center,
                               min=center - fwhm / 2,
                               max=center + fwhm / 2)
        lModPars['sigma'].set(fwhm / 2)
        lModPars['height'].set(height, max=height * 1.5, min=0)
        lModPars['amplitude'].set(min=0)

        lOut = lMod.fit(yLorz, lModPars, x=xLorz)
        lFit = lOut.eval(x=xDimer)
        self.dimerFwhm = lOut.params['fwhm'].value

        if plot == True:
            fig, (ax1, ax2) = plt.subplots(2, sharex=True)
            ax1.plot(self.xTrunc, self.yTrunc)

            if self.aunpSpec is not None:
                ax1.plot(self.xTrunc, self.aunpSpec, 'k--')

            ax2.plot(xDimer, lFit, 'r--')
            ax1.plot(self.xTrunc, self.ySub)
            ax2.plot(x2, y2, alpha=0.5, lw=5)
            ax2.plot(xDimer, yDimer, alpha=0.5)
            ax2.plot(xDimer, ySmooth)
            ax2.plot(xDimer[dimerIndex],
                     ySmooth[dimerIndex],
                     'o',
                     ms=20,
                     alpha=0.5)
            ax2.set_xlim(420, 900)
            ax2.set_xlabel('Wavelength (nm)')
            plt.subplots_adjust(hspace=0)
            ax1.set_ylabel('Absorbance')
            ax2.set_ylabel('$\Delta$A')
            ax1.set_yticks([])
            ax2.set_yticks([])
            ax1.set_title(r'$\lambda_{\mathrm{Dimer}}$ = %.2f nm' %
                          self.dimerWl)
            plt.show()

        if returnAll == True:
            self.xDimer = xDimer
            self.yDimer = yDimer
            self.yDimerSmooth = ySmooth
            self.x2 = x2
            self.y2 = y2


class AggExtDataset:
    '''
    Class containing (x, y, t) data and methods for an aggregate extinction timescan
    dSet must be a 2-dimensional h5py.Dataset Object from an open h5py.File('a') Object
    '''
    def __init__(self,
                 dSet,
                 dataName=None,
                 exptName=None,
                 startWl=420,
                 endWl=950,
                 initSpec=None,
                 startPointPlot=False,
                 startPointThresh=2,
                 tInit=15,
                 saveFigs=False):
        self.x = dSet.attrs['wavelengths'][()]
        self.t = dSet.attrs['start times'][()]
        self.dSet = dSet

        self.dataName = dataName if dataName is not None else dSet.name.strip(
            '/')

        if exptName is not None:
            dSet.attrs['Experiment Name'] = self.exptName = exptName

        bg = dSet.attrs['background'][()]
        ref = dSet.attrs['reference'][()]
        ref -= bg
        yData = dSet[()] - bg
        yData /= ref

        self.yData = np.log10(1 / yData)
        self.startWl = startWl
        self.endWl = endWl

        self.saveFigs = saveFigs

        if 'AggInc' in dSet.attrs.keys():
            self.startPoint = dSet.attrs['Start Point']
            self.endPoint = dSet.attrs['End Point']
            self.trapDiff = dSet.attrs['AggInc']

        else:
            self.findStartPoint(plot=startPointPlot,
                                thresh=startPointThresh,
                                tInit=tInit)
            dSet.attrs['Start Point'] = self.startPoint
            dSet.attrs['End Point'] = self.endPoint
            dSet.attrs['AggInc'] = self.trapDiff

        if initSpec == False:
            self.initSpec = None

        elif initSpec is None:
            if 'AuNP Spectrum' in dSet.attrs.keys():
                x = dSet.attrs['AuNP Wavelengths'][()]
                y = dSet.attrs['AuNP Spectrum'][()]
                self.initSpec = ExtinctionSpectrum(x, y)

            self.initSpec = findAunpSpectrum(dSet.file.filename)
        else:
            self.initSpec = initSpec

        if 'Dimer Centers' in dSet.attrs.keys():
            self.dimerCenters = dSet.attrs['Dimer Centers']
            self.dimerHeights = dSet.attrs['Dimer Heights']
            self.dimerFwhms = dSet.attrs['Dimer Fwhms']

            self.chainHeights = dSet.attrs['Chain Heights']
            self.chainFwhms = dSet.attrs['Chain Fwhms']
            self.chainCenters = dSet.attrs['Chain Centers']

    def findStartPoint(self, plot=False, thresh=2, tInit=15):
        x = self.x
        t = self.t
        yData = self.yData

        startIndex = abs(x - 600).argmin()
        endIndex = abs(x - 900).argmin()

        trapInts = np.asarray([
            np.trapz(y[startIndex:endIndex], x=x[startIndex:endIndex])
            for y in yData
        ])
        trapIntMaxs = np.array(
            [i for i in mpf.detectMinima(-trapInts) if t[i] < tInit])

        if len(trapIntMaxs) == 0:
            trapIntMaxs = np.array([0])

        trapIntMins = np.array([
            i for i in mpf.detectMinima(trapInts)
            if t[i] < tInit and i > trapIntMaxs.max()
        ])

        if len(trapIntMins) == 0:
            trapAvg = np.average([i for t, i in zip(t, trapInts) if t > tInit])

            d1 = mpf.centDiff(t, trapInts)
            trapIntMaxs = np.array([
                i for i in mpf.detectMinima(trapInts)
                if t[i] < tInit and trapInts[i] > trapAvg * thresh
            ])

            if len(trapIntMaxs) == 0:
                trapIntMaxs = np.array([0])

            trapIntMins = np.array([
                i for i in mpf.detectMinima(d1) if t[i] < tInit
                and i > trapIntMaxs.max() and trapInts[i] < trapAvg * thresh
            ])

            if plot == True:
                fig = plt.figure()
                ax1 = fig.add_subplot(111)
                ax2 = ax1.twinx()
                ax1.plot(t, trapInts)
                ax2.plot(t, d1, 'k')
                ax1.plot(t[trapIntMaxs], trapInts[trapIntMaxs], 'ro')
                ax1.plot(t[trapIntMins], trapInts[trapIntMins], 'go')

                plt.show()

        startPoint = trapIntMins.min()
        endPoint = startPoint + trapInts[startPoint:].argmax()

        if endPoint < startPoint + 30:
            endPoint = len(trapInts) - 1

        self.trapDiff = trapInts[endPoint] - trapInts[startPoint]

        if plot == True:
            print(trapInts[endPoint] - trapInts[startPoint])
            plt.plot(t, trapInts)
            plt.plot(t[startPoint], trapInts[startPoint], 'go')
            plt.plot(t[endPoint], trapInts[endPoint], 'ro')
            #plt.xlim(*t[stEnd])
            plt.xlabel('Time (s)')
            plt.ylabel('Integrated aggregate modes')
            plt.show()

        self.startPoint = startPoint
        self.endPoint = endPoint

    def inputStartPoint(self, startPoint):
        self.startPoint = startPoint

    def inputEndPoint(self, endPoint):
        self.endPoint = endPoint

    def fitSpectra(self, dSet, dimerPlot=False, debug=False):
        x = self.x
        yData = self.yData

        scanTimes = self.t
        startPoint = self.startPoint
        endPoint = self.endPoint

        initSpec = self.initSpec

        specDict = {}

        nummers = np.arange(20, 101, 20)

        if len(yData[startPoint:]) > 500:
            nummers = np.arange(10, 101, 10)

        if len(yData[startPoint:]) > 1500:
            nummers = np.arange(5, 101, 5)

        totalFitStart = time.time()
        print('\n0% complete')
        failures = 0

        initDimerWl = None

        for n, (y, t) in enumerate(
                zip(yData[startPoint:], scanTimes[startPoint:]), startPoint):
            dimerWl = None if n == 0 else dSet.attrs.get('Dimer Guess', None)
            spectrum = ExtinctionSpectrum(x,
                                          y,
                                          initSpec=initSpec,
                                          startWl=self.startWl,
                                          endWl=self.endWl)
            if debug == True:
                spectrum.debug()
            try:
                spectrum.fitAggPeaks(dimerWl=dimerWl)
            except:
                #print(f'Spectrum {n} failed')
                plt.close('all')
                #spectrum.fitAggPeaks(dimerWl = dimerWl)
                spectrum.makeNull()
                failures += 1

            if initDimerWl is None:
                spectrum.findDimerIndex(plot=dimerPlot)
                initDimerWl = spectrum.dimerWl

            if (n == 0 or dimerWl is None) and spectrum.specMaxWl is not None:
                dSet.attrs['Dimer Guess'] = spectrum.specMaxWl

            if spectrum.dimerCenter is None:
                failures += 1

            specDict[n] = spectrum

            if 100 * n // len(yData[startPoint:]) in nummers:
                currentTime = time.time() - totalFitStart
                mins = int(currentTime // 60)
                secs = currentTime % 60
                print(
                    f'{nummers[0]}% ({n} spectra) analysed in {mins} min {secs:.3f} sec'
                )
                nummers = nummers[1:]

        if initDimerWl is not None:
            dSet.attrs['Dimer Wavelength (t0)'] = initDimerWl
            print(f'\nDimer Wavelength = {initDimerWl}\n')
        else:
            dSet.attrs['Dimer Wavelength (t0)'] = 'N/A'
            print(f'\nNo dimer peak detected\n')

        print

        nSpectra = np.arange(len(yData))

        if failures > len(yData) / 5:
            print(
                '\nLots of fits failed for this one (can be an issue with low concentrations)'
            )

        self.dimerCenters = np.array([
            specDict.get(n, ExtinctionSpectrum(None, None)).dimerCenter
            for n in nSpectra
        ])
        self.chainCenters = np.array([
            specDict.get(n, ExtinctionSpectrum(None, None)).chainCenter
            for n in nSpectra
        ])

        dimerWlAvg = np.nanmean(self.dimerCenters)
        dimerWlStd = np.nanstd(self.dimerCenters)
        self.dimerCenters = np.array([
            i if abs(dimerWlAvg - i) < dimerWlStd * 3 else np.nan
            for i in self.dimerCenters
        ])

        chainWlAvg = np.nanmean(self.chainCenters[2:10])
        chainWlStd = np.nanstd(self.chainCenters[2:10])
        self.chainCenters[:10] = np.array([
            i if (abs(chainWlAvg - i) < chainWlStd * 2
                  and i > self.dimerCenters[n] and i > 0) else np.nan
            for n, i in enumerate(self.chainCenters[:10])
        ])

        dSet.attrs['Dimer Centers'] = self.dimerCenters
        dSet.attrs['Chain Centers'] = self.chainCenters

        dSet.attrs['Dimer Heights'] = self.dimerHeights = np.array([
            specDict.get(n, ExtinctionSpectrum(None, None)).dimerHeight
            for n in nSpectra
        ])
        dSet.attrs['Dimer Fwhms'] = self.dimerFwhms = np.array([
            specDict.get(n, ExtinctionSpectrum(None, None)).dimerFwhm
            for n in nSpectra
        ])

        dSet.attrs['Chain Heights'] = self.chainHeights = np.array([
            specDict.get(n, ExtinctionSpectrum(None, None)).chainHeight
            for n in nSpectra
        ])
        dSet.attrs['Chain Fwhms'] = self.chainFwhms = np.array([
            specDict.get(n, ExtinctionSpectrum(None, None)).chainFwhm
            for n in nSpectra
        ])

    def plotIndividual(self,
                       specN=0,
                       plotDimer=False,
                       plotChain=False,
                       plotProgress=False,
                       saveFig=None,
                       returnOnly=False):
        makeDir('Plots')
        dataName = self.dataName
        if '/' in dataName:
            dataName = dataName.split('/')[-1]

        x = self.x
        yData = self.yData

        scanTimes = self.t
        startPoint = self.startPoint
        specN += startPoint
        endPoint = self.endPoint
        initSpec = self.initSpec

        saveFig = self.saveFigs if saveFig is None else saveFig

        y = yData[specN]
        spectrum = ExtinctionSpectrum(x,
                                      y,
                                      initSpec=initSpec,
                                      startWl=self.startWl,
                                      endWl=self.endWl)
        xTrunc, yTrunc, ySub = spectrum.xTrunc, spectrum.yTrunc, spectrum.ySub

        if returnOnly == True:
            return xTrunc, ySub

        print(f'Plotting {dataName} Spectrum {specN}...')

        if any([plotDimer, plotChain]):
            spectrum.fitAggPeaks(plot=plotProgress)

        fig, (ax1, ax2) = plt.subplots(2, sharex=True)
        ax1.plot(xTrunc, yTrunc)
        ax2.plot(xTrunc, ySub)

        if plotDimer == True:
            dimerX, dimerY = spectrum.dimerCenter, spectrum.dimerHeight
            dimerLorentz = spectrum.dimerFit
            ax2.plot(xTrunc, dimerLorentz)
            ax2.plot(dimerX, dimerY, 'ro')

        if plotChain == True:
            chainX, chainY = spectrum.chainCenter, spectrum.chainHeight
            chainLorentz = spectrum.chainFit
            ax2.plot(xTrunc, chainLorentz)
            ax2.plot(chainX, chainY, 'o', color='darkred')

        if all([plotDimer, plotChain]):
            ax2.plot(xTrunc, dimerLorentz + chainLorentz)

        fig.suptitle(dataName)
        ax1.set_xlim(xTrunc.min(), xTrunc.max())
        ax2.set_xlim(ax1.get_xlim())
        ax2.set_xlabel('Wavelength (nm)')
        ax1.set_ylabel('Absorbance')
        ax2.set_ylabel('A - A$_{\mathrm{AuNP}}$')
        plt.subplots_adjust(hspace=0.05)

        if saveFig == True:
            imgFName = f'Plots/{dataName}.svg'
            fig.savefig(imgFName, bbox_inches='tight')
            print(f'Saved as {imgFName}')
            plt.close('all')

        else:
            plt.show()

    def plotSpectra(self, cmap='jet', saveFig=None, redDots=False):
        print('Plotting...\n')
        makeDir('Plots')
        dataName = self.dataName
        if '/' in dataName:
            dataName = dataName.split('/')[-1]

        saveFig = self.saveFigs if saveFig is None else saveFig

        x = self.x
        yData = self.yData

        scanTimes = self.t
        startPoint = self.startPoint
        endPoint = self.endPoint

        initSpec = self.initSpec

        nCols = len(yData[startPoint:endPoint])

        fig, (ax1, ax2) = plt.subplots(2, sharex=True)
        initX, initY = initSpec.xTrunc, initSpec.yTrunc
        ax1.plot(initX, initY, 'k')
        cmap = plt.get_cmap(cmap, nCols)

        for n, (y, t) in enumerate(
                zip(yData[startPoint:], scanTimes[startPoint:]), startPoint):
            spectrum = ExtinctionSpectrum(x,
                                          y,
                                          initSpec=initSpec,
                                          startWl=self.startWl,
                                          endWl=self.endWl)
            xTrunc, yTrunc, ySub = spectrum.xTrunc, spectrum.yTrunc, spectrum.ySub

            if n > nCols:
                color = 'gray'
                alpha = 0.5
            else:
                color = cmap(n)
                alpha = 1

            dimerX, dimerY = self.dimerCenters[n], self.dimerHeights[n]
            chainX, chainY = self.chainCenters[n], self.chainHeights[n]

            ax1.plot(xTrunc, yTrunc, color=color, zorder=-n)
            ax2.plot(xTrunc, ySub, color=color, alpha=alpha, zorder=-2 * n)

            if redDots == True:
                ax2.plot(dimerX, dimerY, 'ro', zorder=n)
                ax2.plot(chainX, chainY, 'o', color='darkred', zorder=n)

        fig.suptitle(dataName)
        ax1.set_xlim(xTrunc.min(), xTrunc.max())
        ax2.set_xlim(ax1.get_xlim())
        ax2.set_xlabel('Wavelength (nm)')
        ax1.set_ylabel('Absorbance')
        ax2.set_ylabel('A - A$_{\mathrm{AuNP}}$')
        plt.subplots_adjust(hspace=0.05)
        if saveFig == True:
            imgFName = f'Plots/{dataName}.png'
            fig.savefig(imgFName, bbox_inches='tight')
            print(f'Saved as {imgFName}')
            plt.close('all')

        else:
            plt.show()

    def plotOverviews(self, saveFig=True):
        makeDir('Plots')
        dataName = self.dataName
        if '/' in dataName:
            dataName = dataName.split('/')[-1]
        startPoint = self.startPoint
        t = self.t[startPoint:]
        dimerX = self.dimerCenters[startPoint:]
        dimerY = self.dimerHeights[startPoint:]
        dimerW = self.dimerFwhms[startPoint:]

        chainX = self.chainCenters[startPoint:]
        chainY = self.chainHeights[startPoint:]
        chainW = self.chainFwhms[startPoint:]

        fig = plt.figure()
        ax1 = fig.add_subplot(111)

        dXPlot = ax1.plot(t, dimerX, 'o-', label='$\lambda_\mathrm{Dimer}$')
        cXPlot = ax1.plot(t, chainX, 'o-', label='$\lambda_\mathrm{Chain}$')
        ax1.legend(loc=0)

        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Peak Wavelength (nm)')
        plt.title(dataName)
        if saveFig == True:
            imgFName = f'Plots/{dataName} wl vs t.svg'
            fig.savefig(imgFName, bbox_inches='tight')
            print(f'Saved as {imgFName}')
            plt.close('all')

        else:
            plt.show()

        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.plot(t, dimerY, 'o-', color=dXPlot[0].get_color(), label='Dimer')
        ax.plot(t, chainY, 'o-', color=cXPlot[0].get_color(), label='Chain')
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Peak Absorbance')
        plt.title(dataName)
        if saveFig == True:
            imgFName = f'Plots/{dataName} i vs t.svg'
            fig.savefig(imgFName, bbox_inches='tight')
            print(f'Saved as {imgFName}')
            plt.close('all')

        else:
            plt.show()

        print('')

    def extractDimerSpectrum(self, plot=True, endWl=900, limit=15):
        x = self.x
        yData = self.yData[self.startPoint:]

        dimerWl = None
        n = 0
        while dimerWl is None and n < limit:
            spectrum = ExtinctionSpectrum(x,
                                          yData[n],
                                          endWl=endWl,
                                          initSpec=self.initSpec)
            xTrunc, ySub = spectrum.xTrunc, spectrum.ySub

            try:
                spectrum.fitAggPeaks(dimerWl=dimerWl)
                spectrum.findDimerIndex(plot=plot)
                dimerWl = spectrum.dimerWl
                dimerFwhm = spectrum.dimerFwhm

            except:
                print(
                    f'Spectrum {n + self.startPoint} failed for {self.dataName}'
                )
                dimerWl = None
                dimerFwhm = None

            n += 1

        self.dimerWl = dimerWl
        self.dimerFwhm = dimerFwhm

        if n >= 15:
            print('\tDimer detection failed')
            return spectrum

        elif n > 0:
            print(f'\tSucceeded for Spectrum {n + self.startPoint}')

        print(f'\tDimer Wl = {dimerWl:.2f} nm')
        print(f'\tFWHM = {dimerFwhm:.2f} nm\n')

        return spectrum


class AggExtH5File():
    def __init__(self, filename):
        self.filename = filename
        self.dSetNames = self.getDsetNames(nDims=2)
        self.spectraNames = self.getDsetNames(nDims=1)
        self.initialiseDatasets()
        self.initSpec = self.findAunpSpectrum()

    def getDsetNames(self, nDims=2):
        with h5py.File(self.filename, 'r') as f:
            dSetNames = []
            f.visit(dSetNames.append)
            dSetNames = [
                dSetName for dSetName in dSetNames
                if isinstance(f[dSetName], h5py.Dataset)
            ]

            return [
                dSetName for dSetName in dSetNames
                if f[dSetName][()].ndim == nDims
            ]

    def initialiseDatasets(self):
        print('Initialising timescan data...')

        with h5py.File(self.filename, 'a') as f:
            for dSetName in self.dSetNames:
                if 'Start Point' not in f[dSetName].attrs.keys():
                    print(f'\t{dSetName}')
                    dataSet = AggExtDataset(f[dSetName],
                                            dataName=dSetName,
                                            initSpec=False)

        print('\n\tData initialised\n')

    def updateAunpSpecs(self, x, y):
        with h5py.File(self.filename, 'a') as f:
            for dSetNames in self.dSetNames:
                f[dSetNames].attrs['AuNP Spectrum'] = y
                f[dSetNames].attrs['AuNP Wavelengths'] = x

    def findAunpSpectrum(self, reUse=True, extH5File=None):
        '''
        searches through h5 file for non-aggregated AuNP spectrum
        '''
        h5File = self.filename
        if extH5File is not None:
            currH5File = h5File
            h5File = extH5File

        print(f'Searching for AuNP monomer spectrum candidates in {h5File}...')

        timeScans = self.dSetNames
        singleSpecs = self.spectraNames

        with h5py.File(h5File, 'a') as f:
            candidates = []

            for i in timeScans:
                if reUse == True:
                    if 'AuNP Spectrum' in f[i].attrs.keys():
                        y = f[i].attrs['AuNP Spectrum']
                        x = f[i].attrs['AuNP Wavelengths']
                        print('\tAuNP monomer spectrum found\n')

                        if extH5File is not None:
                            updateAunpSpecs(currH5File, x, y)

                        return ExtinctionSpectrum(x, y)

                if 'AggInc' not in f[i].attrs.keys():
                    dataset = AggExtDataset(f[i], initSpec=False)

            allSpecs = sorted(
                [i for i in timeScans if 'AggInc' in f[i].attrs.keys()],
                key=lambda i: f[i].attrs['AggInc'])
            allSingles = singleSpecs

            #for specName in allSpecs:
            #    if 'AuNP Spectrum' in f[specName].attrs.keys():
            #        return f[specName].attrs['AuNP Spectrum'][()]

            integrals = []

            for i in allSingles:
                spectrum = f[i]
                x = spectrum.attrs['wavelengths'][()]
                y = spectrum[()]
                bg = spectrum.attrs['background'][()]
                ref = spectrum.attrs['reference'][()]
                ref -= bg
                y -= bg
                y /= ref
                y = np.log10(1 / y)

                candidates.append((x, y))
                xTrunc, yTrunc = mpf.truncateSpectrum(x,
                                                      y,
                                                      startWl=600,
                                                      finishWl=970)
                integrals.append(np.trapz(yTrunc, x=xTrunc))

            for dSetName in allSpecs:
                dSpectra = f[dSetName]
                x = dSpectra.attrs['wavelengths'][()]
                startPoint = dSpectra.attrs['Start Point']
                y = dSpectra[()][startPoint]
                bg = dSpectra.attrs['background'][()]
                ref = dSpectra.attrs['reference'][()]
                ref -= bg
                y -= bg
                y /= ref
                y = np.log10(1 / y)

                candidates.append((x, y))
                xTrunc, yTrunc = mpf.truncateSpectrum(x,
                                                      y,
                                                      startWl=600,
                                                      finishWl=970)
                integrals.append(np.trapz(yTrunc, x=xTrunc))

            candidates = [
                i[0]
                for i in sorted(zip(candidates, integrals), key=lambda i: i[1])
            ]

            if len(candidates) == 0:
                print('agfsfghfsgh')

            for n, (x, y) in enumerate(candidates):
                xTrunc, yTrunc = mpf.truncateSpectrum(x,
                                                      y,
                                                      startWl=400,
                                                      finishWl=950)

                plt.plot(xTrunc, yTrunc)
                plt.xlim(xTrunc.min(), xTrunc.max())
                plt.title(f'Attempt {n}')
                plt.show()

                query = 'Is this AuNP monomer spectrum acceptable? There should be no visible dimer peak.\n**If any aggregation is visible, enter "n" until you find one without it**  \
                                  \nEnter y to accept; n to find another spectrum; x to exit; anything else to see more options\n\n'

                if n > 0:
                    query = 'y to accept; n to find another spectrum; x to exit; anything else to see more options\n\n'

                decision = input(query)

                if decision == 'y':
                    print(
                        '\nOk, saving this for future use. Please wait while Dataset attributes are updated...'
                    )
                    for specName in allSpecs:
                        self.updateAunpSpecs(x, y)
                        if extH5File is not None:
                            self.updateAunpSpecs(currH5File, x, y)
                        f[specName].attrs['AuNP Spectrum'] = y
                        f[specName].attrs['AuNP Wavelengths'] = x
                    print('\tDone\n')
                    return ExtinctionSpectrum(x, y)

                elif decision == 'n':
                    continue
                elif decision == 'x':
                    print(1 / 0)
                else:
                    break

            query = ''.join([
                'No monomeric AuNP spectrum found. Please select an option to continue:\n',
                '\t1. Specify a different .h5 file with a monomeric AuNP spectrum\n',
                '\t2. Manually specify "initSpec = [x, y]" when calling fitAllSpectra\n',
                '\t3. Manually add AuNP xy data to the .h5 file before running again\n\n'
            ])

            decision = input(query)

            while decision not in ['1', '2', '3', 1, 2, 3]:
                if decision == 'x':
                    break
                decision = input(
                    'Please enter 1, 2 or 3. Enter x to exit:\n\n')

            if decision in [1, '1']:
                extH5File = input(
                    "Please enter the full path to the .h5 file containing your spectrum:\n\n"
                )

                while not extH5File.endswith('.h5'):
                    if not extH5File.endswith('.h5'):
                        extH5File = input(
                            'Are you sure this is correct? Please try again:\n\n'
                        )
                    if extH5File == 'x':
                        break

                extH5File = '/'.join(extH5File.split('\\'))

                aunpSpec = self.findAunpSpectrum(reUse=True,
                                                 extH5File=extH5File)
                print('AuNP Spectrum successfully added')

                return aunpSpec

            elif decision in [2, '2']:
                print(
                    'Find some appropriate [x, y] data and run fitAllSpectra again, specifying "initSpec = [x, y]"'
                )
                print(1 / 0)

            elif decision in [3, '3']:
                print(
                    "Find some appropriate y data and save it as a new Dataset in the current hdf5 File with Dataset.attrs['wavelengths'] = x, then try again"
                )
                print(1 / 0)

            print(1 / 0)

    def findDimerPeaks(self, plot=True, endWl=900):
        specDict = {}

        initSpec = self.initSpec

        with h5py.File(self.filename, 'a') as f:
            for dSetName in self.dSetNames[:]:
                print(dSetName)
                initSpecs = []
                dimerWls = []
                dataSet = AggExtDataset(f[dSetName],
                                        initSpec=self.initSpec,
                                        saveFigs=False,
                                        endWl=endWl)

                dimerSpectrum = dataSet.extractDimerSpectrum(plot=plot,
                                                             endWl=endWl)
                dimerWl = dataSet.dimerWl
                dimerFwhm = dataSet.dimerFwhm
                specDict[dSetName] = {
                    'xy': [dimerSpectrum.xTrunc, dimerSpectrum.ySub],
                    'dimerWl': 0 if dimerWl is None else dimerWl,
                    'dimerFwhm': 0 if dimerWl is None else dimerFwhm
                }

                f[dSetName].attrs[
                    'Dimer Wavelength (t0)'] = dimerWl if dimerWl is not None else np.nan

        print('Done')

        self.dimerSpecDict = specDict

        return specDict

    def fitAllSpectra(self,
                      nameDict={},
                      dimerPlot=False,
                      saveFigs=True,
                      startWl=420,
                      endWl=950,
                      startPointPlot=False,
                      startPointThresh=2,
                      tInit=15,
                      debug=False):

        print('Beginning fit\n')

        with h5py.File(self.filename, 'a') as f:
            for specN, dataName in enumerate(self.dSetNames):
                exptName = nameDict.get(dataName.split('/')[-1], None)
                print(dataName)
                if exptName is not None:
                    print(f'\t(= {exptName})')
                dSpectra = f[dataName]
                if len(dSpectra[()]) == 1:
                    continue

                dataSet = AggExtDataset(dSpectra,
                                        dataName=dataName,
                                        exptName=exptName,
                                        initSpec=self.initSpec,
                                        startWl=startWl,
                                        endWl=endWl,
                                        startPointPlot=startPointPlot,
                                        startPointThresh=startPointThresh,
                                        tInit=tInit)
                dataSet.fitSpectra(dSpectra, dimerPlot=dimerPlot, debug=debug)
                makeDir('Plots')
                dataSet.plotSpectra(saveFig=saveFigs)
                dataSet.plotOverviews(saveFig=saveFigs)

        print('\nAll done')


if __name__ == '__main__':
    h5File = mpf.findH5File(os.getcwd(), nameFormat='date', mostRecent=True)
    h5File = AggExtH5File(h5File)
    nameDict = {}  #dictionary to name your spectra, if desired
    h5File.fitAllSpectra()
