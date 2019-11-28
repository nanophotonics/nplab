# -*- coding: utf-8 -*-
"""
Created on Tue Jul 14 18:50:08 2015

@author: wmd22
"""
from __future__ import print_function

from builtins import str
from builtins import range
from time import sleep

import numpy as np

import nplab.instrument.visa_instrument as vi


class Lockin_SR844(vi.VisaInstrument):
    '''Software control for the Stanford Research Systems SR844 Lockin
    '''
    def __init__(self, address='GPIB0::8::INSTR'):
        '''Sets up visa communication and class dictionaries
        
        The class dictionaries are manully inputed translations between what 
        the lockin will send/recieve and the real values. 
        These have been built for:
            - channel number i.e. X,Y ...   
            - Sensitivity i.e. Voltage range
            - time constant i.e. integration time
            - Filter options i.e. 6 dB etc
            
        Args:
            address(str):   Visa address
        
        '''
        super(Lockin_SR844, self).__init__(address)
        self.instr.read_termination = '\n'
        self.instr.write_termination = '\n'
        self.instr.timeout = None
        print(self.instr.read_termination)
 
        print(self.write("OUTX"))
        
        self.ch_list = {'X': 1, 'Y': 2,'R[V]' : 3,'R [dBm]' : 4,"theta" : 5, "AUX1" : 6, "AUX2" : 7, "Ref Freq" : 8,
                        "CH1" : 9, "CH2" :10}
        self.sens_list = {0 : 100E-9,1 : 300E-9, 2 : 1E-6, 3 : 3E-6, 4 : 10E-6, 
                          5 : 30E-6, 6 : 100E-6, 7 : 300E-6, 8 : 1E-3, 9 : 3E-3, 
                          10 : 10E-3, 11 : 30E-3, 12 : 100E-3,13 : 300E-3, 14 : 1}
        self.time_list = {0 : 100E-6,1 : 300E-6, 2 : 1E-3, 3 : 3E-3, 4 : 10E-3,
                          5 : 30E-3, 6 : 100E-3,  7 : 300E-3, 8 : 1, 9 : 3, 
                          10 : 10, 11 : 30, 12 : 100,13 : 300, 14 : 1E3, 15 : 3E3, 
                          16 : 10E3, 17 : 30E3}
        self.filter_list = {0 : "No Filter", 1 : "6 dB", 2:"12 dB",3:"24 dB"}
        
    def measure_variables(self,channels = "1,2"):
        """Upto six variable read, must be greater than 1 measure via a string
        Args:
            channels(str):  A string containing integers seperated by a comma 
                            refering to each of the Variable that you which to 
                            measure (as shown below):
                            1   X
                            2   Y
                            3   R [V]
                            4   R [dBm]
                            5   θ
                            6   AUX IN 1
                            7   AUX IN 2
                            8   Reference Frequency
                            9   CH1 display
                            10  CH2 display 
        """
        variables = self.query("SNAP? "+channels)
        variables = variables.split(",")  
        variables = [float(i) for i in variables]
        return variables
    
    def measure_X(self):
        '''Measure the current X value
        Notes :
            Offsets and Ratio applied'''
        return self.float_query("OUTP? 1")
        
    def measure_Y(self):
        '''Measure the current Y value
        Notes :
            Offsets and Ratio applied'''
        return self.float_query("OUTP? 2")
        
                
    def measure_R(self):
        '''Measure the current R value
        Notes :
            Offsets and Ratio applied'''
        output=-1
        while output > 1 or output < 0:
            output = self.float_query("OUTP? 3")
        return self.float_query("OUTP? 3")
        
    def measure_theta(self):
        '''Measure the current phase (theta) 
        Notes :
            Offsets and Ratio applied'''
        return self.float_query("OUTP? 5")
        
    def check_frequency(self):
        ''' Return current measurement frequesncy
        Returns:
            Current measreument frequency'''
        return self.float_query("FREQ?")
        
    def get_sens(self):
        ''' The sensitivity property 
        
        Gettr:
            Gets the Current sensitivity as an integer and a real value
            
            Returns:
                num (int):  The integer returned by the lockin
                sens_list[num](float):  The real value for sensitivty in Vrms
                        
        Settr:
            Sets the current sensitivity as a integer 
            
            Args:
                i(int): Sets the sensitivty of the lockin as shown by the dict 
                        self.sens_list typed out below.
                        
                        i               Sensitivity
                        0               100 nVrms / -127 dBm 
                        1               300 nVrms / -117 dBm 
                        2               1 μVrms / -107 dBm 
                        3               3 μVrms / -97 dBm 
                        4               10 μVrms / -87 dBm 
                        5               30 μVrms / -77 dBm 
                        6               100 μVrms / -67 dBm 
                        7               300 μVrms / -57 dBm
                        8               1 mVrms / -47 dBm
                        9               3 mVrms / -37 dBm
                        10              10 mVrms / -27 dBm
                        11              30 mVrms / -17 dBm
                        12              100 mVrms / -7 dBm
                        13              300 mVrms / +3 dBm
                        14              1 Vrms / +13 dBm
        '''
        num = self.int_query("SENS?")
        return num,self.sens_list[num]
        
    def set_sens(self,i):
        self.write("SENS%s"%i)
    
    sensitivity = property(get_sens, set_sens)
    
    def get_time_costant(self):
        ''' The time_constant property 
        
        Gettr:
            Gets the Current time constant as an integer and a real value
            
            Returns:
                num (int):  The integer returned by the lockin
                time_list[num](float):  The real value for sensitivty in Seconds
                        
        Settr:
            Sets the current time constant as an integer 
            
            Args:
                i(int): Sets the time constant of the lockin as shown by the dict 
                        self.time_list typed out below.
                        
                        i       time constant
                        0       100 μs 
                        1       300 μs 
                        2       1 ms 
                        3       3 ms 
                        4       10 ms 
                        5       30 ms
                        6       100 ms 
                        7       300 ms 
                        8       1 s 
                        9       3 s
                        10      10 s
                        11      30 s
                        12      100 s
                        13      300 s
                        14      1 ks
                        15      3 ks
                        16      10 ks
                        17      30 ks
        '''

        num = self.int_query("OFLT?")
        return num,self.time_list[num]

    def set_time_costant(self,i):
        self.write("OFLT"+str(i))     
    
    time_constant = property(get_time_costant, set_time_costant)
    
    def set_time_constant_from_int(self,integrationtime):
        '''Command to reverse read a dictionary and set the time_constant
        
        Args:
            integrationtime(float):     The real value for the time constant in seconds
                                        for allowed values see self.time_list
        '''
        for i in range(len(list(self.time_list.values())[:])):
            if list(self.time_list.values())[i] == integrationtime:
                self.time_constant = list(self.time_list.keys())[i]
                return True
        print('Setting integration time failed. '+str(integrationtime)+' is not in self.time_list')
        return False

    def get_filter(self):
        ''' The filterslope property 
        
        Gettr:
            Gets the filter as an integer and a real value
            
            Returns:
                num (int):  The integer returned by the lockin
                time_list[num](str):  The real value for filter 
                        
        Settr:
            Sets the current filter as an integer 
            
            Args:
                i(int): Sets the filter of the lockin as shown by the dict 
                        self.time_list typed out below.
                        
                        i       Filter
                        0       No filter
                        1       6 dB
                        2       12 dB
                        3       18 dB
                        4       24 dB 
        '''
        num = self.int_query("OFSL?")
        return num,self.filter_list[num]
        
    def set_filter(self,i):
        self.write("OFSL%s" %i)
        
    filterslope = property(get_filter, set_filter)    
    
    def get_close_res(self):
        ''' The close_res property represents the close reserve of the lockin
        Gettr:
            Returns:
                i(int):     The close reserve of the lockin where
                            high = 0, normal = 1, low noise = 2
        Settr:
            Args:
                i(int):     Set the close reserve of the lockin where
                            high = 0, normal = 1, low noise = 2
        '''
        return self.int_query("CRSV?")
        
    def set_close_res(self,i):
        self.write("CRSV%s" %i)
        
    close_res = property(get_close_res,set_close_res)

    def get_wide_res(self):
        ''' The wide_res property represents the wide reserve of the lockin
        Gettr:
            Returns:
                i(int):     The close reserve of the lockin where
                            high = 0, normal = 1, low noise = 2
        Settr:
            Args:
                i(int):     Set the close reserve of the lockin where
                            high = 0, normal = 1, low noise = 2
        '''
        return self.int_query("WRSV?")
        
    def set_wide_res(self,i):
        self.write("WRSV%s" % i)
        
    wide_res = property(get_wide_res,set_wide_res)
        
    def autosens(self):
        '''checks measurement is with range and auto changes sensitivty and reserve respectively
        Returns:
            sens(i,float):  The new sensitivty in both forms
            wide_res(int):  The new wide reserve (high = 0, normal = 1, low noise = 2)
            close_res(int): The new close reserve (high = 0, normal = 1, low noise = 2)
        '''
        testmax = np.max([np.abs(self.measure_R()),np.abs(self.measure_X()),np.abs(self.measure_Y())])
        try:
            Lowersense = self.sens_list[self.sensitivity[0]-1]
        except KeyError:
            Lowersense = 0.0
        while testmax>self.sensitivity[1] or testmax<Lowersense:
            testmax = np.max([np.abs(self.measure_R()),np.abs(self.measure_X()),np.abs(self.measure_Y())])
            try:
                Lowersense = self.sens_list[self.sensitivity[0]-1]
            except KeyError:
                Lowersense = 0.0
            if testmax>self.sensitivity[1]:
                if self.sensitivity[0]==14:
                    print("OVERLOADED RUNNNNNN")
                self.sensitivity = self.sensitivity[0]+1
            elif testmax<Lowersense:
                self.sensitivity = self.sensitivity[0]-1
            sleep(1)
            self.write("AWRS")  #wideband reseve
            wide_res = self.wide_res
            self.write("ACRS") #close in  reseve
            close_res = self.close_res
        sens = self.sensitivity
        wide_res = self.wide_res
        close_res = self.close_res
        return sens, wide_res, close_res
       # else:
          #  print "Measurement within range"
    
    

if __name__ == '__main__':
    testlockin = Lockin_SR844()
    