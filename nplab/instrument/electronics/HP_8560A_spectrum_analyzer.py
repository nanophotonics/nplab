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


class SpectrumAnalyzer(VisaInstrument):
    def __init__(self, address='GPIB0::18::INSTR'):
        super(SpectrumAnalyzer, self).__init__(address)
        self.instr.read_termination = '\n'
        self.instr.write_termination = '\n'
        self.freq_points=601

    # frequency = queried_property('freq?', 'freq {0}')
    # function = queried_property('function:shape?', 'function:shape {0}',
    #                             validate=['sinusoid', 'dc'], dtype='str')
    # voltage = queried_property('voltage?', 'voltage {0}')
    # offset = queried_property('voltage:offset?', 'voltage:offset {0}')
    # output_load = queried_property('output:load?', 'output:load {0}',
    #                                validate=['inf'], dtype='str')
    # volt_high = queried_property('volt:high?', 'volt:high {0}')
    # volt_low = queried_property('volt:low?', 'volt:low {0}')
    # output = queried_property('output?', 'output {0}',
    #                           validate=['OFF', 'ON'], dtype='str')

    def reset(self):
        self.write('*rst')
        
    def get_center_freq(self):
        return float(self.query('CF?'))/1e6 #return span in MHz
    
    def set_center_freq(self,CF): # center frequency in MHz
        self.write('CF '+str(CF)+' MHZ')
        return float(self.query('CF?'))/1e6 #return span in MHz
        
    def get_span(self):
        return float(self.query('SP?'))/1e6 #return span in MHz
    
    def set_span(self,SP): #span in MHz
        self.write('SP '+str(SP)+' MHZ')
        return float(self.query('SP?'))/1e6 #return span in MHz
    
    def get_res(self): # get resolution bandwidth
        return float(self.query('RB?'))/1e3 # returns resolution in MHz
    
    def set_res(self,res): # set resolution, res in kHz
        self.write('RB '+str(res)+' KHZ')
        return float(self.query('RB?'))/1e3 #return span in MHz
    
    def get_sweep_time(self):
        return float(self.query('ST?')) #return sweep time in sec
    
    def set_sweep_time(self,ST): #sweep time in sec
        self.write('ST '+str(ST)+' S')
        sleep(1)
        return float(self.query('ST?')) #return span in MHz
    
    def set_single_sweep(self): # set to single sweep
        self.write('SNGLS')
        
    def set_cont_sweep(self):
        self.write('CONTS')
    
    def command_completed(self):
        done=False
        while not done:
            try: 
                done=bool(self.query('DONE?'))
            except:
                done=False
        return done
    
    # def take_sweep(self):
        
    #     self.write('TS')
    #     done=False
    #     while not done:
    #         try: 
    #             done=bool(self.query('DONE?'))
    #         except:
    #             done=False
    #     print('sweep ended')
    #     return True
    
    def take_sweep(self):
        
        self.write('TS')
        if self.command_completed():
            print('sweep completed')
            return True
    
    def get_data(self):
        self.clear_read_buffer()
        data=self.query('TRA?')
        data=np.fromstring(data,dtype=float,sep=',')
        return(data)
    
    def get_freq_axis(self):
        fa=float(self.query('FA?'))/1e6
        fb=float(self.query('FB?'))/1e6
        return np.linspace(fa,fb,self.freq_points)
        
        


#%% make instrument        
if __name__ == '__main__':
    SA = SpectrumAnalyzer(address='GPIB0::18::INSTR')
    SA.clear_read_buffer()
    print('center freq: '+str(SA.get_center_freq()))
    print('sweep span: '+str(SA.get_span()))
    print('sweep time: '+str(SA.get_sweep_time()))
    #SA.take_sweep()
    # data=SA.get_data()
    # f=SA.get_freq_axis()
    # plt.figure()
    # plt.plot(f,data)