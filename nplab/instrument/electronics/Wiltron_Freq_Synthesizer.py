# uncompyle6 version 3.5.1
# Python bytecode 2.7 (62211)
# Decompiled from: Python 2.7.16 |Anaconda, Inc.| (default, Mar 14 2019, 15:42:17) [MSC v.1500 64 bit (AMD64)]
# Embedded file name: C:\Users\Hera\Documents\GitHub\nplab\nplab\instrument\electronics\SR810.py
# Compiled at: 2019-10-23 12:11:02
"""
Created on Tue Jul 14 18:50:08 2015

@author: wmd22
"""
from time import sleep
import numpy as np
import nplab.instrument.visa_instrument as vi
import pyvisa

class freq_source(vi.VisaInstrument):
    """Software control for the Wiltron 6769B swept frequency source
    """

    def __init__(self, address='GPIB0::5::INSTR'):
        """Sets up visa communication and class dictionaries
        
        The class dictionaries are manully inputed translations between what 
        the source will send/recieve and the real values. 
        
            
        Args:
            address(str):   Visa address
        
        """
        super(freq_source, self).__init__(address)
        self.instr.read_termination = '\n'
        self.instr.write_termination = '\n'
        self.instr.timeout = None
        print(self.query('OI'))
        #print(self.instr.read_termination)
        
        
        # self.filter_list = {}
        print('source connected successfully')
        return
    #def output_on(self):
        
    # def RF_on(self):
    #     return self.query('RF')
        
    # def get_power(self):
    #     return self.query('OPM')
    
    # def set_power(self,target_power=-10d):
    #     return(self.query(''))
    def set_freq(self,mem_slot=1,target_freq=2.2): # frequency in GHz
    # mem_slot is pre-set memory slot, from 1 to 9
        self._write('F'+str(mem_slot)+str(target_freq)+'GH')
        return
    
    def RF_on(self):
        self._write('RF1')
    
    def RF_off(self):
        self._write('RF0')
    
    def set_power(self,power=-10): # power in dBm
        self._write('L1'+str(power)+'DM')
        
    def get_power(self):
        return self.query('OL1')
        
    def close(self):
        self.instr.close()
    
    #sweep between two frequencies
    def freq_sweep(self,f1=2.1,f2=2.5,T=30):
        #scan between f1 and f2 with time T
        self.set_freq(mem_slot=2,target_freq=f2)
        self.set_freq(mem_slot=1,target_freq=f1)
        self._write('SWT'+str(T)+'SEC') #set scan time to 30sec
        self._write('SF1')# start scan
    
    def set_cw(self,mem_slot=1,freq=2.1):
        self.set_freq(mem_slot=mem_slot,target_freq=freq)
        self._write('CF1')
        
    def AM_on(self):
        self._write('AM1')
    
    def AM_off(self):
        self._write('AM0')
        
    def FM_on(self):
        self._write('FM1')
    
    def FM_off(self):
        self._write('FM0')
        
        
    
if __name__ == '__main__':
    #testlockin = Lockin_SR844()
    source = freq_source(address='GPIB0::5::INSTR')
# okay decompiling SR810.pyc
