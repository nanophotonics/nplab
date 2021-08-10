# -*- coding: utf-8 -*-
"""
Created on Thu Aug 01 16:38:56 2019

@author: ee306
"""

import os
import numpy as np
from scipy import interpolate
import time
from qtpy import QtWidgets, uic
from nplab.ui.ui_tools import UiTools
from nplab.experiment.gui import run_function_modally
from nplab.instrument import Instrument
from nplab.instrument.stage import Stage
from nplab.instrument.electronics.aom import AOM as Aom
from nplab.instrument.stage.Thorlabs_ELL8K import Thorlabs_ELL8K as RStage
from nplab.instrument.electronics.power_meter import PowerMeter
from nplab.instrument.electronics.thorlabs_pm100 import ThorlabsPowermeter
from nplab import datafile
from nplab.datafile import sort_by_timestamp

def isMonotonic(A):

    return (all(A[i] <= A[i + 1] for i in range(len(A) - 1)) or
            all(A[i] >= A[i + 1] for i in range(len(A) - 1)))


class PowerControl(Instrument):
    '''
    Controls the power. power_controller is something with a continuous input parameter like a filter wheel, or an AOM. 
    '''

    def __init__(self, power_controller, power_meter, calibration_points=25, title='power control', move_range=(0, 1)):
        super().__init__()
        self.pc = power_controller
        self.pometer = power_meter
        self.calibration_points = calibration_points
        self.title = title
        assert isinstance(power_controller, (Aom, Stage)), \
            ('power_controller must be AOM or Stage')
        assert isinstance(power_meter, PowerMeter), \
            ('Power meter have power_meter.PowerMeter base class')
        
        
        if isinstance(self.pc, RStage):
            self.min_param, self.max_param = 0, 360
     
        elif isinstance(self.pc, Aom):
            self.min_param, self.max_param = 0, 1
        else: 
            self.min_param, self.max_param =  move_range
        self.maxpower = None
        self.minpower = None
        self.update_power_calibration()
        
        if isinstance(self.pc, Stage):
            self.set_param = self.pc.move
            self.get_param = self.pc.get_position
        if isinstance(self.pc, Aom):
            self.set_param = self.pc.Power
            self.get_param = self.pc.Get_Power

    @property
    def param(self):
        return self.get_param()

    @param.setter
    def param(self, value):
        self.set_param(value)

    @property
    def mid_param(self):
        return (self.max_param - self.min_param)/2

    @property
    def points(self):
        if isinstance(self.pc, RStage):
            if self.min_param < self.max_param:
                return np.logspace(0, np.log10(self.max_param-self.min_param), self.number_points)+self.min_param
            return self.min_param - np.logspace(0, np.log10(self.min_param-self.max_param), self.number_points)
        else:  # isinstance(self.pc, Aom):
            return np.linspace(self.min_param, self.max_param, num=self.number_points, endpoint=True)

    def calibrate_power(self, update_progress=lambda p: p):
        '''

        '''
        live = self.pometer.live
        self.pometer.live = False
        attrs = {}
    
        if isinstance(self.pc, RStage):
            attrs['Angles'] = self.points
        if isinstance(self.pc, Aom):
            attrs['Voltages'] = self.points

        attrs['x_axis'] = self.points
        attrs['parameters'] = self.points
        attrs['wavelengths'] = self.points

        powers = []
        
        for counter, point in enumerate(self.points):
            self.param = point
            time.sleep(.2)
            powers.append(self.pometer.power)
            update_progress(counter)

        group = self.create_data_group(self.title+'_%d')
        group.create_dataset('measured_powers', data=powers, attrs=attrs)
        
        
        self.param = self.mid_param
        self.update_power_calibration()
        self.pometer.live = live

    def update_power_calibration(self, specific_calibration=None, laser=None):
        '''
        specific_calibration should be the exact name of the power calibration group, otherwise
        the most recent calibration for the given laser is used.
        '''

        
        initial = datafile._use_current_group
        datafile._use_current_group = False
        search_in = self.get_root_data_folder()
        datafile._use_current_group = initial
        if specific_calibration is not None:
            try:
                power_calibration_group = search_in[specific_calibration]
            except ValueError:
                print('This calibration doesn\'t exist!')
                return
        else:
            
            candidates = [g for g in sort_by_timestamp(search_in) 
                                       if '_'.join(g.split('_')[:-1]) == self.title]
            if candidates: 
                power_calibration_group = candidates[-1]
                pc = power_calibration_group['powers']
                self.power_calibration = {'powers': pc[()],
                                          'parameters': pc.attrs['parameters']}
                if isMonotonic(self.power_calibration['powers']):
                    self.update_config('parameters_'+self.title,
                                       pc.attrs['parameters'])
                    self.update_config('powers_'+self.title, pc[()])
                else:
                    print('power curve isn\'t monotonic, not saving to config file')
            else:
                if len(self.config_file) > 0:
                    self.power_calibration = {'_'.join(n.split(
                        '_')[:-1]): f for n, f in self.config_file.items() if n.endswith(self.title)}
                    print(
                        f'No power calibration in current file, using inaccurate configuration ({self.title})')
                else:
                    print(f'No power calibration found ({self.title})')

    @property
    def power(self):
        return self.pometer.power

    @power.setter
    def power(self, value):
        self._power = value
        self.param = self.power_to_param(value)

    def power_to_param(self, power):
        params = self.power_calibration['parameters']
        powers = np.array(self.power_calibration['powers'])
        curve = interpolate.interp1d(powers, params, kind='cubic')
        return curve(power)

    def get_qt_ui(self):
        return PowerControl_UI(self)


class PowerControl_UI(QtWidgets.QWidget, UiTools):
    def __init__(self, PC):
        super(PowerControl_UI, self).__init__()
        uic.loadUi(os.path.join(os.path.dirname(
            __file__), 'power_control.ui'), self)
        self.PC = PC
        self.SetupSignals()
        self.number_points_spinBox.setValue(self.PC.number_points)

    def SetupSignals(self):
        self.pushButton_calibrate_power.clicked.connect(
            self.calibrate_power_gui)
        self.doubleSpinBox_min_param.setValue(self.PC.min_param)
        self.doubleSpinBox_max_param.setValue(self.PC.max_param)
        self.doubleSpinBox_max_param.valueChanged.connect(
            self.update_min_max_params)
        self.doubleSpinBox_min_param.valueChanged.connect(
            self.update_min_max_params)
        self.laser_label.setText(self.PC.title)
        self.doubleSpinBox_set_input_param.valueChanged.connect(self.set_param)
        self.doubleSpinBox_set_input_param.setValue(self.PC.param)
        self.measured_power_lineEdit.textChanged.connect(
            self.update_measured_power)
        self.doubleSpinBox_set_power.valueChanged.connect(self.set_power_gui)
        self.number_points_spinBox.valueChanged.connect(
            self.update_number_points)

    def update_min_max_params(self):
        self.PC.min_param = self.doubleSpinBox_min_param.value()
        self.PC.max_param = self.doubleSpinBox_max_param.value()

    def update_measured_power(self):
        if self.doubleSpinBox_measured_power.text().isdigit():
            self.PC.measured_power = float(
                self.doubleSpinBox_measured_power.value())

    def set_param(self):
        self.PC.param = self.doubleSpinBox_set_input_param.value()

    def set_power_gui(self):
        self.PC.power = float(self.doubleSpinBox_set_power.value())

    def update_number_points(self):
        self.PC.number_points = self.number_points_spinBox.value()

    def calibrate_power_gui(self):
        run_function_modally(self.PC.calibrate_power,
                             progress_maximum=len(self.PC.points))


if __name__ == '__main__':

    from nplab.instrument.shutter.BX51_uniblitz import Uniblitz
    from nplab.instrument.electronics.thorlabs_pm100 import ThorlabsPowermeter
    from nplab.instrument.shutter.thorlabs_sc10 import ThorLabsSC10
    from nplab import datafile

    filter_wheel = RStage('COM8')    
    powermeter = ThorlabsPowermeter('USB0::0x1313::0x807B::201029132::0::INSTR')
    power_control = PowerControl(filter_wheel, powermeter)
    power_control.show_gui(False)