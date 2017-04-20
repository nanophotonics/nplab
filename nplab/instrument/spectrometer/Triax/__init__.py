# -*- coding: utf-8 -*-
"""
Created on Tue Apr 14 18:45:32 2015

@author: Hamid Ohadi (hamid.ohadi@gmail.com)
"""

from nplab.utils.gui import QtWidgets, QtCore, uic
from nplab.instrument.visa_instrument import VisaInstrument
import os
import time
from math import sqrt
from numpy.polynomial.polynomial import polyval


class Triax550(VisaInstrument):
    metadata_property_names = ('wavelength', )

    def __init__(self, address, **kwargs):
        VisaInstrument.__init__(self, address, settings=dict(timeout=4000, write_termination='\n'))

        if 'wl_offset' in kwargs:
            self.zero_WL_offset = kwargs['wl_offset']
        else:
            self.zero_WL_offset = -90.0
        self.KKcoef = [13413.3, 381.485, 0.0795158]
        self.waitTimeout = 120

    def reset(self):
        self.instr.write_raw('\xde')
        time.sleep(5)
        buff = self.query(" ")
        if buff == 'B':
            self.instr.write_raw('\x4f\x32\x30\x30\x30\x00')  # <O2000>0
            buff = self.query(" ")
        if buff == 'F':
            self._logger.debug("Triax is reset")
            self.setup()

    def setup(self):
        self._logger.info("Initiating motor. This will take some time...")
        self.write("A")
        time.sleep(60)
        self.waitTillReady()
        self.wavelength = 0
        self.grating(1)

    def get_wavelength(self):
        Tstep = self.counts()
        return self.counts_to_wavelength(Tstep)

    def set_wavelength(self, wlNew):
        curstep = self.counts()
        NewPos = self.wavelength_to_counts(wlNew) - curstep
        self.moveSteps(NewPos)
    wavelength = property(get_wavelength, set_wavelength)

    def exitLateral(self):
        self.write("e0\r")
        self.write("c0\r")  # sets entrance mirror to lateral as well

    def exitAxial(self):
        self.write("f0\r")
        self.write("d0\r")  # sets the entrance mirror to axial as well

    def counts_to_wavelength(self, Tstep):
        KKcoef = self.KKcoef
        return (-KKcoef[1] + sqrt(KKcoef[1] ** 2 - 4 * KKcoef[2] * (KKcoef[0] - Tstep))) / (2 * KKcoef[2]) - self.zero_WL_offset

    def wavelength_to_counts(self, wl):
        return polyval(wl + self.zero_WL_offset, self.KKcoef)

    def counts(self):
        self.write("H0\r")
        return int(self.read()[1:])

    def grating(self, grat=None):
        if grat is None:
            return int(self.query("Z452,0,0,0\r")[1:]) + 1
        else:
            self.write("Z451,0,0,0,%i\r" % (grat - 1))
            time.sleep(1)
            self.waitTillReady()

    def moveSteps(self, newpos):
        if (newpos <= 0):  # backlash correction
            self.write("F0,%i\r" % (newpos - 1000))
            time.sleep(1)
            self.waitTillReady()
            self.write("F0,1000\r")
            self.waitTillReady()
        else:
            self.write("F0,%i\r" % newpos)
            time.sleep(1)
            self.waitTillReady()

    def _isBusy(self):
        if self.query("E") == 'oz':
            return 0
        else:
            return 1

    def waitTillReady(self):
        start = time.time()
        while self._isBusy():
            time.sleep(1)
            if (time.time() - start) > self.waitTimeout:
                self._logger.warn('Waiting timeout')
                break

    def slit(self, width=None):
        if width is None:
            return int(self.query("j0,0\r")[1:])
        elif width > 0:
            tomove = width - self.slit()
            if tomove == 0:
                return
            elif tomove > 0:  # backlash correction
                self.write("k0,0,%i\r" % (tomove + 100))
                self.waitTillReady()

                self.write("k0,0,-100\r")
                self.waitTillReady()
            else:
                self.write("k0,0,%i\r" % tomove)
                self.waitTillReady()

    def get_qt_ui(self):
        return TriaxUI(self)


class TriaxUI(QtWidgets.QWidget):
    def __init__(self, triax):
        assert isinstance(triax, Triax550), "instrument must be a Triax550"
        super(TriaxUI, self).__init__()
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'Triax.ui'), self)

        self.lineEditTriaxWL.returnPressed.connect(self.txtChangedTriaxWL)
        self.lineEditSlitWidth.returnPressed.connect(self.txtChangedSlitWidth)
        self.pushButtonTriaxReset.clicked.connect(self.btnClickedTriaxReset)

        self.Triax = triax
        self.updateGUI()

    def txtChangedTriaxWL(self):
        self.Triax.wavelength = float(self.lineEditTriaxWL.text())
        self.focusNextChild()

    def txtChangedSlitWidth(self):
        self.Triax.slit(int(self.lineEditSlitWidth.text()))
        self.focusNextChild()

    def btnClickedTriaxReset(self):
        self.Triax.reset()

    def updateGUI(self):
        self.lineEditTriaxWL.setText(str(self.Triax.wavelength))


if __name__ == '__main__':
    triax = Triax550('GPIB0::1::INSTR')
    triax.show_gui()
