# -*- coding: utf-8 -*-
"""
Created on Thu Jul 30 13:13:27 2015

"""

from nplab.utils.gui import QtWidgets, uic, QtCore
import os

from nplab.instrument.visa_instrument import VisaInstrument
from nplab.instrument.temperatureControl import TemperatureControl


class OxfordITC(VisaInstrument, TemperatureControl):
    def __init__(self, address, **kwargs):
        TemperatureControl.__init__(self)
        if 'GPIB' in address:
            VisaInstrument.__init__(self, address, settings=dict(timeout=10000, read_termination='\r',
                                                                 write_termination='\r'))
        else:
            VisaInstrument.__init__(self, address, settings=dict(baud_rate=9600, read_termination='\r',
                                                                 write_termination='\r', timeout=1000))

        self.setControlMode(3)

        self.params = {'T': 0, 'SetT': 0, 'PID': [0, 0, 0]}
        self.flush_input_buffer()
        self.clear_read_buffer()
        self.get_temperature()
        self.get_target_temperature()

    def __del__(self):
        try:
            self.heaterOff()
            self.setControlMode(0)
            self.instr.close()
        except:
            self._logger.warn("Couldn't close %s on port %s" %(self.__name__, self._address))

    def get_temperature(self):
        temp = self.query('R1', delay=1)
        temp = float(temp[1:len(temp)])  # Remove the first character ('R')

        self.params['T'] = temp

        return temp

    def setControlMode(self, mode):
        """
        Sets the operation mode (local or remote)
        :param mode:
            0 LOCAL & LOCKED (Default State),
            1 REMOTE & LOCKED (Front Panel Disabled),
            2 LOCAL & UNLOCKED,
            3 REMOTE & UNLOCKED (Front Panel Active)
        :return:
        """
        if (mode not in [0, 1, 2, 3]):
            raise Exception('valid modes are 0-3, see documentation')
        self.write('C' + str(mode))

    def get_target_temperature(self):
        temp = self.query('R0')
        temp = float(temp[1:len(temp)])  # Remove the first character ('R')

        self.params['SetT'] = temp

        return temp

    def set_target_temperature(self, temp):
        """
        Sets the set temperature
        :param temp: Temperature in Kelvin (int)
        :return:
        """
        self.params['SetT'] = temp

        self.write('T' + str(int(temp)))

    def setHeaterMode(self, mode):
        """
        Sets the heater mode (auto, manual)
        :param mode:
            0 HEATER MANUAL - GAS MANUAL,
            1 HEATER AUTO - GAS MANUAL,
            2 HEATER MANUAL - GAS AUTO,
            3 HEATER AUTO - GAS AUTO
        :return:
        """
        if (mode not in [0, 1, 2, 3]):
            raise Exception('valid modes are 0-3, see documentation')
        self.write('A' + str(mode))

        self.params['Heater'] = mode

    def setHeaterPower(self, power):
        self.params['HeaterPower'] = power
        self.write('O' + str(int(power)))

    def heaterOff(self):
        self.setHeaterMode(0)
        self.setHeaterPower(0)

    def setAutoPID(self, mode):
        """
        Sets the PID mode (auto or manual)
        :param mode:
            0 disable auto-PID,
            1 enable auto-PID
        :return:
        """
        if (mode not in [0, 1]):
            raise Exception('valid modes are 0 (off) or 1 (on)')
        self.write('L' + str(mode))

        self.params['autoPID'] = mode

    def setPID(self, P, I, D):
        """
        Sets the PID parameters for manual PID control
        :param P: PROPORTIONAL BAND in Kelvin (resolution 0.001K, ideally 5 to 50K)
        :param I: INTEGRAL ACTION TIME in minutes (0 to 140, ideally 1 to 10)
        :param D: DERIVATIVE ACTION TIME in minutes (0 to 273, can be left at 0)
        :return:
        """
        self.write('P' + str(P))
        self.write('I' + str(I))
        self.write('D' + str(D))

        self.params['PID'] = [P, I, D]


    def get_qt_ui(self):
        return OxfordITCUI(self)


class OxfordITCUI(QtWidgets.QWidget):
    updateGUI = QtCore.Signal()

    def __init__(self, itc):
        assert isinstance(itc, OxfordITC), "instrument must be an Oxford ITC"
        super(OxfordITCUI, self).__init__()

        self.ITC = itc

        uic.loadUi(os.path.join(os.path.dirname(__file__), 'OxfordITC.ui'), self)

        self.lineEditSetT.returnPressed.connect(self.setT)

        self.updateGUI.connect(self.SentUpdateGUI)
        self.SentUpdateGUI()

    def SentUpdateGUI(self):
        self.textEditT.setText(str(self.ITC.params['T']))
        self.lineEditSetT.setText(str(self.ITC.params['SetT']))
        self.lineEditP.setText(str(self.ITC.params['PID'][0]))
        self.lineEditI.setText(str(self.ITC.params['PID'][1]))
        self.lineEditD.setText(str(self.ITC.params['PID'][2]))
        return

    def setT(self):
        temp = float(self.lineEditSetT.text())
        self.ITC.setSetTemperature(temp)


if __name__ == '__main__':
    ITC = OxfordITC('GPIB0::24::INSTR')

    ITC.show_gui()
