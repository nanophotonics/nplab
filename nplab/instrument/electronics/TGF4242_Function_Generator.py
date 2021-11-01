# -*- coding: utf-8 -*-
"""
Created on Fri Mar 12 16:51:30 2021

@author: fh403
"""
import nplab
from nplab.instrument.serial_instrument import SerialInstrument


class TGF4242(SerialInstrument):
    
    def __init__(self, port=None):
        """Serial Interface to TGF4242 function generator."""
        SerialInstrument.__init__(self, port=port) #this opens the port
    
    def channel(self, channel):
        """Select Channel: 1 or 2"""
        self.write('CHN ' + str(channel)) 
        #be carefull needs space between CHN and channel. Same everywhere
    
    def output(self, output):
        """Turn ON or OFF the output of selected channel:
            
            type 'ON' or 1 to turn on
            
            type 'OFF' or 0 to turn off
        """
        if output==1:
            self.write('OUTPUT ON')
        elif output==0:
            self.write('OUTPUT OFF')
        else:
            self.write('OUTPUT ' + output)
     
    
    def freq(self, freq):
        """Set signal frequency in Hz"""
        self.write('FREQ ' + str(freq))
        
    def ampl(self, ampl):
        """Set signal amplitude (Vpp) in VOLTS"""
        self.write('ampl ' + str(ampl))
        
    def offset(self, offset):
        """Set the signal DC offset in VOLTS"""
        self.write('DCOFFS ' +  str(offset))
        
    def phase(self, phase):
        """Set the waveform phase offset in DEGREES"""
        self.write('PHASE ' + str(phase))
        
    def align(self, align):
        """Align phase for both channels"""
        self.write('ALIGN')
        
    def waveform(self, wave):
        """Set the waveform: SINE, SQUARE, TRIANG, PULSE, NOISE, ARB"""
        if wave=='triangular' or wave=='Triangular' or wave=='TRIANGULAR':
            self.write('WAVE TRIANG')
        elif wave=='arbitrary' or wave=='Arbitrary' or wave=='ARBITRARY':
            self.write('WAVE ARB')
        else:
            self.write('WAVE ' + wave)
