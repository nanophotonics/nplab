# -*- coding: utf-8 -*-
"""
Created on Mon Apr 17 11:51:22 2023

@author: jb2444
"""

from nplab.instrument.visa_instrument import VisaInstrument, queried_property
from functools import partial
from time import sleep
import numpy as np
import matplotlib.pyplot as plt


class PowerSupply(VisaInstrument):
    def __init__(self, address='GPIB0::5::INSTR'):
        super(PowerSupply, self).__init__(address)
        self.instr.read_termination = '\n'
        self.instr.write_termination = '\n'
    
    def reset(self):
        self.write('*rst')    
    
    def output_is_on(self):
        return self.query('OUTP:STAT?')
    
    def output_on(self):
        return self.write('OUTPUT ON')
        
    def output_off(self):
        return self.write('OUTPUT OFF')
        
    def operation_complete(self):
        return bool(self.query('*OPC?'))
    
    def clear_errors(self):
        is_error=True
        while is_error:
            ans=self.query('SYST:ERR?')
            print(ans)
            if ans == '+0,"No error"':
                is_error=False
        print('error cleared')
    
    def set_channel(self, channel=1):
        ''' channels:
            1: positive 6 V
            2: Positive 25 V
            3: Negative 25 V'''
        if channel in [1,2,3]:
            self.write('instrument:nselect '+str(channel))
        else:
            print(' channel has to be 1/2/3')
        
    def get_channel(self):
        # channels:
        # 1: positive 6 V
        # 2: Positive 25 V
        # 3: Negative 25 V
        return self.float_query('instrument:nselect?')
        

    def set_voltage(self, value=0.5):
        # set voltage to selected channel
        # performs test to see if voltage within limits for this channel
        channel = S.int_query('instrument:nselect?')
        if channel==1:
            ulim=6
            llim=0
        if channel==2:
            ulim=25
            llim=0
        if channel==3:
            ulim=0
            llim=-25
        if value<llim or value>ulim:
            print('value out of channel limits')
        else:
            S.write('voltage '+str(value))
        
    def get_voltage(self):
        # return the voltage setting
        return S.float_query('voltage?')
    
    def measure_voltage(self):
        # measure actual voltage of port
        return S.float_query('measure:voltage?')
    
    def set_current(self,value=0.01):
        # set voltage to selected channel
        # performs test to see if voltage within limits for this channel
        channel = S.int_query('instrument:nselect?')
        if channel==1:
            ulim=5
            llim=0
        if channel==2:
            ulim=1
            llim=0
        if channel==3:
            ulim=1
            llim=0
        if value<llim or value>ulim:
            print('value out of channel limits')
        else:
            S.write('current '+str(value))
    
    def get_current(self):
        # return the current setting
        return S.float_query('current?')
    
    def measure_current(self):
        # measure the actual current of port
        return S.float_query('measure:current?')
    
    def set_channel_values(self,channel=1,voltage=2,current=0.05):
        # set a n output channel to voltage and current values
        self.set_channel(channel)
        self.set_current(current)
        self.set_voltage(voltage)
   
    def get_channel_values(self):
        # print channel numbers and current\voltage values
        channel=self.get_channel()
        set_voltage_value=self.get_voltage()
        measured_voltage_value=self.measure_voltage()
        set_current_value=self.get_current()
        measured_current_value=self.measure_current()
        print('channel '+str(channel))
        print('set voltage is '+str(set_voltage_value)+'V')
        print('measured voltage is '+str(measured_voltage_value)+'V')
        print('set current is '+str(set_current_value)+'A')
        print('measured current is '+str(measured_current_value)+'A')
        
    
    def increase_voltage(self,step_size=0.05,print_flag=True):
        # increase voltage of current channel by step_size in volts
        if print_flag:
            self.get_channel_values()
        v=self.get_voltage()
        self.set_voltage(v+step_size)
        if print_flag:
            print('new values are:\n')
            self.get_channel_values()
        
    def decrease_voltage(self,step_size=0.05,print_flag=True):
        # increase voltage of current channel by step_size in volts
        if print_flag:
            self.get_channel_values()
        v=self.get_voltage()
        self.set_voltage(v-step_size)
        if print_flag:
            print('new values are:\n')
            self.get_channel_values()
                 
        
            
        
#%% make instrument        
if __name__ == '__main__':
    S = PowerSupply(address='GPIB1::5::INSTR')


