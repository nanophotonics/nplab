"""
jpg66
"""

from nplab.instrument.visa_instrument import VisaInstrument
import numpy as np
import time

import os

from nplab.utils.gui import QtWidgets, uic
from nplab.ui.ui_tools import UiTools
"""
This is the base class for the Triax spectrometer. This should be wrapped for each lab use, due to the differences in calibrations.
"""


class Triax(VisaInstrument):
    metadata_property_names = ('wavelength', )

    def __init__(self, Address, CCD_size=2000, calibrator=None):
        """
        Initialisation function for the triax class. Address in the port address of the triax connection.

        calibrator is a Calibrator instance that needs 3 methods:
            calibrator.wl_to_steps(steps) - converterts a given wavelength to motor steps
            calibrator.steps_to_wl(wl) - the inverse
            calibrator.wavelength_axis property - returns a wavelength axis of appropriate length
        it should also support switching between gratings.
        """

        #--------Attempt to open communication------------

        try:

            VisaInstrument.__init__(self,
                                    Address,
                                    settings=dict(timeout=4000,
                                                  write_termination='\n'))
            Attempts = 0
            End = False
            while End is False:
                if self.query(" ") == 'F':
                    End = True
                else:
                    self.instr.write_raw(
                        '\x4f\x32\x30\x30\x30\x00'
                    )  #Move from boot program to main program
                    time.sleep(2)
                    Attempts += 1
                    if Attempts == 5:
                        raise Exception('Triax communication error!')

        except:
            raise Exception('Triax communication error!')
        self.ccd_size = CCD_size
        self.calibrator = calibrator

    def get_grating(self):
        return int(self.query("Z452,0,0,0\r")[1:])

    def set_grating(self, grating_number):

        assert grating_number in (0, 1, 2), 'Invalid grating'
        self.write("Z451,0,0,0,%i\r" % (grating_number))
        self.calibrator.grating = grating_number
        self.waitTillReady()

    grating = property(get_grating, set_grating)

    def move_steps(self, Steps):  # relative
        """
        Function to move the grating by a number of stepper motor Steps.
        """

        if (
                Steps <= 0
        ):  # Taken from original code, assume there is an issue moving backwards that this corrects
            self.write("F0,%i\r" % (Steps - 1000))
            self.waitTillReady()
            self.write("F0,1000\r")
            self.waitTillReady()
        else:
            self.write("F0,%i\r" % Steps)
            self.waitTillReady()

    def motor_steps(self):
        """
        Returns the current rotation of the grating in units of steps of the internal stepper motor
        """

        self.write("H0\r")
        return int(self.read()[1:])

    def move_steps_absolute(self, steps):
        current = self.motor_steps
        self.move_steps(steps - current)

    motor_steps = property(motor_steps, move_steps_absolute)

    def set_center_wavelength(self, wavelength):
        if self.ccd_size is None:
            raise ValueError('ccd_size must be set in child class')
        self.motor_steps = self.calibrator.wl_to_steps(wavelength)

    def get_center_wavelength(self):
        return self.calibrator.steps_to_wl(self.motor_steps)

    center_wavelength = property(get_center_wavelength, set_center_wavelength)

    def get_wavelength_axis(self):
        return np.asarray(self.calibrator.wavelength_axis(self.motor_steps))

    wavelength_axis = property(get_wavelength_axis)

    def get_slit(self):
        return int(self.query("j0,0\r")[1:])

    def set_slit(self, width):
        """
        Function to return or set the triax slit with in units of um. If Width is None, the current width is returned. 
        """

        if width > 0:
            To_Move = width - self.slit
        if To_Move == 0:
            return
        elif To_Move > 0:  # backlash correction
            self.write("k0,0,%i\r" % (To_Move + 100))
            self.waitTillReady()

            self.write("k0,0,-100\r")
            self.waitTillReady()
        else:
            self.write("k0,0,%i\r" % To_Move)
            self.waitTillReady()

    slit = property(get_slit, set_slit)

    def _isBusy(self):
        """
        Queries whether the Triax is willing to accept further commands
        """

        if self.query("E") == 'oz':
            return False
        else:
            return True

    def waitTillReady(self, Timeout=120):
        """
        When called, this function checks the triax status once per second to check if it is busy. When it is not, the function returns. Also return automatically 
        after Timeout seconds.
        """

        Start_Time = time.time()

        while self._isBusy():
            time.sleep(0.2)
            if (time.time() - Start_Time) > Timeout:
                self._logger.warn('Timed out')
                print('Timed out')
                break

    def get_qt_ui(self):
        return TriaxUI(self)

    #-------------------------------------------------------------------------------------------------
    """
	Held here are functions from old code by Hamid Ohadi that, at this point in time, I do not wish to touch
    """

    def reset(self):

        self.instr.write_raw(b'\xde')
        time.sleep(5)
        buff = self.query(" ")
        if buff == 'B':
            self.instr.write_raw(b'\x4f\x32\x30\x30\x30\x00')  # <O2000>0
            buff = self.query(" ")
        if buff == 'F':
            self._logger.debug("Triax is reset")
            self.setup()

    def setup(self):
        self.grating = 1
        time.sleep(5)
        self._logger.info("Initiating motor. This will take some time...")
        self.write("A")
        time.sleep(120)
        self.waitTillReady()
        print("changing to G1")
        self.grating = 1
        #self.Grating_Number = self.Grating()

    def exitLateral(self):
        self.write("e0\r")
        self.write("c0\r")  # sets entrance mirror to lateral as well

    def exitAxial(self):
        self.write("f0\r")
        self.write("d0\r")  # sets the entrance mirror to axial as well


class TriaxUI(QtWidgets.QWidget, UiTools):
    def __init__(self,
                 triax,
                 ui_file=os.path.join(os.path.dirname(__file__),
                                      'triax_ui.ui'),
                 parent=None):
        assert isinstance(triax, Triax), "instrument must be a Triax"
        super(TriaxUI, self).__init__()
        uic.loadUi(ui_file, self)
        self.triax = triax
        self.centre_wl_lineEdit.returnPressed.connect(self.set_wl_gui)
        self.slit_lineEdit.returnPressed.connect(self.set_slit_gui)
        self.centre_wl_lineEdit.setText(
            str(np.around(self.triax.center_wavelength)))
        self.slit_lineEdit.setText(str(self.triax.slit))
        eval('self.grating_' + str(self.triax.grating) +
             '_radioButton.setChecked(True)')
        for radio_button in range(3):
            eval('self.grating_' + str(radio_button) +
                 '_radioButton.clicked.connect(self.set_grating_gui)')

    def set_wl_gui(self):
        self.triax.center_wavelength = float(
            self.centre_wl_lineEdit.text().strip())

    def set_slit_gui(self):
        self.triax.slit = float(self.slit_lineEdit.text().strip())

    def set_grating_gui(self):
        s = self.sender()
        if s is self.grating_0_radioButton:
            self.triax.grating = 0
        elif s is self.grating_1_radioButton:
            self.triax.grating = 1
        elif s is self.grating_2_radioButton:
            self.triax.grating = 2
        else:
            raise ValueError('radio buttons not connected!')
