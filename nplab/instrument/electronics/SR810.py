# uncompyle6 version 3.5.1
# Python bytecode 2.7 (62211)
# Decompiled from: Python 2.7.16 |Anaconda, Inc.| (default, Mar 14 2019, 15:42:17) [MSC v.1500 64 bit (AMD64)]
# Embedded file name: C:\Users\Hera\Documents\GitHub\nplab\nplab\instrument\electronics\SR810.py
# Compiled at: 2019-10-23 12:11:02
"""
Created on Tue Jul 14 18:50:08 2015

@author: wmd22
"""
from __future__ import print_function
from builtins import str
from builtins import range
from time import sleep
import numpy as np, nplab.instrument.visa_instrument as vi

class Lockin_SR810(vi.VisaInstrument):
    """Software control for the Stanford Research Systems SR844 Lockin
    """

    def __init__(self, address='GPIB0::8::INSTR'):
        """Sets up visa communication and class dictionaries
        
        The class dictionaries are manully inputed translations between what 
        the lockin will send/recieve and the real values. 
        These have been built for:
            - channel number i.e. X,Y ...   
            - Sensitivity i.e. Voltage range
            - time constant i.e. integration time
            - Filter options i.e. 6 dB etc
            
        Args:
            address(str):   Visa address
        
        """
        super(Lockin_SR810, self).__init__(address)
        self.instr.read_termination = '\n'
        self.instr.write_termination = '\n'
        self.instr.timeout = None
        print(self.instr.read_termination)
        print(self.write('OUTX'))
        self.write('ICPL 0')
        self.ch_list = {}
        self.sens_list = {}
        self.time_list = {}
        self.filter_list = {}
        return

    def measure_variables(self, channels='1,2'):
        """Upto six variable read, must be greater than 1 measure via a string
        Args:
            channels(str):  A string containing integers seperated by a comma 
                            refering to each of the Variable that you which to 
                            measure (as shown below):
                            1   X
                            2   Y
                            3   R [V]
                            4   R [dBm]
                            5   \xce\xb8
                            6   AUX IN 1
                            7   AUX IN 2
                            8   Reference Frequency
                            9   CH1 display
                            10  CH2 display 
        """
        variables = self.query('SNAP? ' + channels)
        variables = variables.split(',')
        variables = [ float(i) for i in variables ]
        return variables

    def measure_X(self):
        """Measure the current X value
        Notes :
            Offsets and Ratio applied"""
        return self.float_query('OUTP? 1')

    def measure_Y(self):
        """Measure the current Y value
        Notes :
            Offsets and Ratio applied"""
        return self.float_query('OUTP? 2')

    def measure_R(self):
        """Measure the current R value
        Notes :
            Offsets and Ratio applied"""
        output = -1
        while output > 1 or output < 0:
            output = self.float_query('OUTP? 3')

        return self.float_query('OUTP? 3')

    def measure_theta(self):
        """Measure the current phase (theta) 
        Notes :
            Offsets and Ratio applied"""
        return self.float_query('OUTP? 4')

    def check_frequency(self):
        """ Return current measurement frequesncy
        Returns:
            Current measreument frequency"""
        return self.float_query('FREQ?')

    def get_sens(self):
        """ The sensitivity property 
        
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
                        2               1 \xce\xbcVrms / -107 dBm 
                        3               3 \xce\xbcVrms / -97 dBm 
                        4               10 \xce\xbcVrms / -87 dBm 
                        5               30 \xce\xbcVrms / -77 dBm 
                        6               100 \xce\xbcVrms / -67 dBm 
                        7               300 \xce\xbcVrms / -57 dBm
                        8               1 mVrms / -47 dBm
                        9               3 mVrms / -37 dBm
                        10              10 mVrms / -27 dBm
                        11              30 mVrms / -17 dBm
                        12              100 mVrms / -7 dBm
                        13              300 mVrms / +3 dBm
                        14              1 Vrms / +13 dBm
        """
        num = self.int_query('SENS?')
        return (
         num, self.sens_list[num])

    def set_sens(self, i):
        self.write('SENS%s' % i)

    sensitivity = property(get_sens, set_sens)

    def get_time_costant(self):
        """ The time_constant property 
        
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
                        0       100 \xce\xbcs 
                        1       300 \xce\xbcs 
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
        """
        num = self.int_query('OFLT?')
        return (
         num, self.time_list[num])

    def set_time_costant(self, i):
        self.write('OFLT' + str(i))

    time_constant = property(get_time_costant, set_time_costant)

    def set_time_constant_from_int(self, integrationtime):
        """Command to reverse read a dictionary and set the time_constant
        
        Args:
            integrationtime(float):     The real value for the time constant in seconds
                                        for allowed values see self.time_list
        """
        for i in range(len(list(self.time_list.values())[:])):
            if list(self.time_list.values())[i] == integrationtime:
                self.time_constant = list(self.time_list.keys())[i]
                return True

        print('Setting integration time failed. ' + str(integrationtime) + ' is not in self.time_list')
        return False

    def get_line_filter(self):
        """ Gets filter related to power line, 
            0 - no filter
            1 - line filter
            2 - 2xline filter
            3 - Both """
        num_filter = self.int_query('ILIN?')
        return num_filter

    def set_line_filter(self, filter_mode):
        """ Sets filter related to power line, 
            0 - no filter
            1 - line filter
            2 - 2xline filter
            3 - Both """
        self.write('ILIN' + str(filter_mode))

    linefilter = property(get_line_filter, set_line_filter)

    def set_input_mode(self, mode):
        """Sets the input mode:
            A (i=0), A-B (i=1), I (1 M\xce\xa9) (i=2) or I (100 M\xce\xa9) (i=3)."""
        self.write('ISRC' + str(mode))

    def get_input_mode(self):
        return self.int_query('ISRC?')

    inputmode = property(get_input_mode, set_input_mode)

    def get_filter(self):
        """ The filterslope property 
        
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
        """
        num = self.int_query('OFSL?')
        return (
         num, self.filter_list[num])

    def set_filter(self, i):
        self.write('OFSL%s' % i)

    filterslope = property(get_filter, set_filter)

    def get_res(self):
        """ Gets the dynamic reserve of the lockin
         0 = High, 1 = normal, 2 = low noise
        """
        return self.int_query('RMOD?')

    def set_res(self, i):
        self.write('RMOD%s' % i)

    reserve = property(get_res, set_res)

    def set_phase(self, phase):
        self.write('PHAS' + str(phase))

    def get_phase(self):
        return self.float_query('PHAS?')

    phase = property(get_phase, set_phase)
    
    def set_harmonic(self, harmonic):
        self.write('HARM' + str(harmonic))
        print('HARM' + str(harmonic))
    def get_harmonic(self, harmonic):
        return self.int_query('HARM?')
    harmonic = property(get_harmonic, set_harmonic)

    def autosens(self):
        """checks measurement is with range and auto changes sensitivty and reserve respectively
        Returns:
            sens(i,float):  The new sensitivty in both forms
            wide_res(int):  The new wide reserve (high = 0, normal = 1, low noise = 2)
            close_res(int): The new close reserve (high = 0, normal = 1, low noise = 2)
        """
        testmax = np.max([np.abs(self.measure_R()), np.abs(self.measure_X()), np.abs(self.measure_Y())])
        try:
            Lowersense = self.sens_list[(self.sensitivity[0] - 1)]
        except KeyError:
            Lowersense = 0.0
        else:
            while testmax > self.sensitivity[1] or testmax < Lowersense:
                testmax = np.max([np.abs(self.measure_R()), np.abs(self.measure_X()), np.abs(self.measure_Y())])
                try:
                    Lowersense = self.sens_list[(self.sensitivity[0] - 1)]
                except KeyError:
                    Lowersense = 0.0
                else:
                    if testmax > self.sensitivity[1]:
                        if self.sensitivity[0] == 14:
                            print('OVERLOADED RUNNNNNN')
                        self.sensitivity = self.sensitivity[0] + 1
                    elif testmax < Lowersense:
                        self.sensitivity = self.sensitivity[0] - 1
                    sleep(1)
                    self.write('AWRS')
                    wide_res = self.wide_res
                    self.write('ACRS')
                    close_res = self.close_res

        sens = self.sensitivity
        wide_res = self.wide_res
        close_res = self.close_res
        return (
         sens, wide_res, close_res)


if __name__ == '__main__':
    testlockin = Lockin_SR844()
# okay decompiling SR810.pyc
