# -*- coding: utf-8 -*-
"""
Created on Fri Sep 22 15:27:17 2017

@author: Femi Ojambati (fo263)
"""

import serial

ser = serial.Serial('COM39', baudrate=115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, xonxoff=True)

def getdata():
    
    out = []
    out_c = ''
    while out_c != '\r':
        out_c = ser.read()
        out.append(out_c)
    return out
    
    # open the serial port
if ser.isOpen():
     print(ser.name + ' is openning...')
 
#set counter properties
ser.write('F2\n') #sets the counter to measure the frequency of A input
ser.write('M2\n') #sets measurement time, m1- 0.3s, m2 - 1s, m3 - 10s, m4 - 100s
#ser.write('F7\n') #measures the count on input 1
ser.write('Z5\n') #Set A input to 50 ohms input impedance, Z1 for 1Mohms 
ser.write('EL\n') #Rising (ER) or falling (EL) edge of waveform
ser.write('FI\n') #low pass filter, FI - on, FO - off 
ser.write('AC\n') #AC or DC coupling
ser.write('TO60\n') #Threshold voltage for AC coupling

decide= 'c'
while decide != 'q':    
    if decide == 'c':
        #decide = input('\nEnter c to continue, q to quit: \t')
        ser.write('N?\n') #reads the current data from the counter
        data = getdata()
        
        print('Received ...')
        for p in data: print p ,
        
    else :
        print('Wrong input')
#ser.write('STOP')


    
ser.close()


        
    