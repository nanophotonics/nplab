# -*- coding: utf-8 -*-
"""
Created on Mon Apr  5 15:28:19 2021

@author: Hera
"""

from nplab.instrument.visa_instrument import VisaInstrument, queried_property
from functools import partial

class TBS1032B(VisaInstrument):
    """Visa Interface for TBS1032B Tektronix Digital Oscilloscope"""
    def __init__(self, address='GPIB0::3::INSTR'):
        super(TBS1032B, self).__init__(address)
    
    def channel(self, channel):
        self.write('MEASUrement:IMMed:SOUrce CH' + str(channel))
    
    def set_probe(self, channel, probe):
        self.write('CH'+str(channel)+':PRObe' + str(probe))
    
    def autoset(self):
        self.write('AUTOSet EXECute')
    
    def acquisition(self, acq):
        """ RUN or STOP"""
        self.write('ACQuire:STATE ' + str(acq))
    
    def read_par(self, channel, parameter):
        """Reading given parameter value and returning a list of (value type, value)"""
        avoid_random_output=False
        
        if parameter in ['frequency', 'freq', 'Frequency', 'Freq', 'FREQUENCY', 'FREQ']:
            par='FREQuency'
        elif parameter in ['Mean', 'mean', 'MEAN']:
            par='MEAN'
        elif parameter in ['period', 'per', 'Period', 'PERIOD', 'PER']:
            par='PERIod'
        elif parameter in ['phase','Phase','PHASE']:
            par='PHAse'
        elif parameter in ['peak-peak','peak_to_peak','V_pp', 'pk2pk', 'Vpp', 'VPP']:
            par='PK2pk'
        elif parameter in ['Vrms','Voltage_rms']:
            par='CRMs'
        elif parameter in ['minimum','min','Minimum', 'Min']:
            par='MINImum'    
        elif parameter in ['maximum','max','Maximum', 'Max']:
            par='MAXImum' 
        elif parameter in ['rise','Rise']:
            par='RISe'      
        elif parameter in ['Fall','fall']:
            par='FALL'   
        elif parameter in ['ampl', 'amplitude', 'Amplitude','Ampl', 'AMPLITUDE', 'AMPL']:
            par='amplitude' 
        elif parameter in ['attenuation', 'probe', 'att']:
            par='CH'+ str(channel) + ':PRObe?'
            return self.output_typo_adjust('probe',self.query(str(par)))
        else:
            print('Having problem reading oscilloscope query')
            avoid_random_output=True
        
        if (avoid_random_output==False) and (parameter not in ['attenuation', 'probe', 'att']):
            self.write('MEASUrement:IMMed:TYPe ' + str(par))
            a=self.query('MEASUrement:IMMed:TYPe?')
            b=self.query('MEASUrement:IMMed:VALue?')
            return self.output_typo_adjust(a,b)
        else:
            return ('Nothing', None)


    def output_typo_adjust(self, a, b):
        a=a
        b=b
        if a[len(a)-1]=='\n':
            a=a[:len(a)-1]
        if b[len(b)-1]=='\n':
            b=float(b[:len(b)-1])
      
        return (a,b)

o=TBS1032B(address='USB0::0x0699::0x0368::C010300::0::INSTR')