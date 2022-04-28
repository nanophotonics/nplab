# -*- coding: utf-8 -*-
"""
Created on Mon Aug  9 16:22:04 2021

@author: Hera
"""
'''
author: im354
'''

import sys

import numpy as np 
from nplab.instrument.serial_instrument import SerialInstrument
from nplab.instrument.stage import Stage
# from nplab.utils.gui import *
from nplab.ui.ui_tools import QuickControlBox
import time
from nplab.utils.notified_property import NotifiedProperty

def bytes_to_binary(bytearr,debug = 0):
    '''
    Helper method for converting a bytearray datatype to a binary representation
    '''
    if debug > 0: print(bytearr)
    bytes_as_binary =[ format(int(b,base=16),"#06b").replace("0b","") for b in bytearr ]  
    if debug > 0: print(bytes_as_binary)
    binary = "".join(bytes_as_binary)
    return binary 

def twos_complement_to_int(binary,debug = 0):
    '''
    Compute 2s complement of binary number representation
    '''
    if debug > 0: print(binary)
    N = len(binary)
    a_N = int(binary[0])
    return float(-a_N*2**(N-1) + int(binary[1:],base=2))


def int_to_hex(integer,padded_length=8,debug=0):
    '''
    Convert integer number to hexidecimal. Return value is zero-padded at the beginning
    until its length matches the value passed in "padded_length"
    '''
    outp = (format(integer,"#0{}x".format(padded_length+2)).replace("0x","")).upper()
    return outp 

def int_to_twos_complement(integer, padded_length=16,debug = 0):
    '''
    Two's complement in integer representation. Padded length specifies the padding on the 
    binary representation used to compute the twos complement
    '''
    #number is above 0 - return binary representation:
    if integer >= 0:
        return integer

    #number is below zero - return twos complement representation:
    elif integer < 0:
        if debug > 0: print("Below zero - returning twos complement")
        integer = -1*integer
        binary = format(integer,"0{}b".format(padded_length+2)).replace("0b","")
        ones_complement = [str(1-int(b)) for b in str(binary)]
        ones_complement = int("".join(ones_complement))
        twos_complement = int("0b"+str(ones_complement),base=2) + 1
        twos_complement = format(twos_complement,"034b").replace("0b","")
        if debug > 0:
            print("input:",integer)
            print("binary:",binary) 
            print("ones comp:", ones_complement)
            print("twos comp (int):", int(twos_complement,base=2)) 
        return int("0b"+twos_complement,base=2)

class BusDistributor(SerialInstrument):
    ''' a class to handle the port settings of a thorlabs ELLB distributor bus.
    Each of these can have several devices attached. They are assigned device
    indices by the thorlabs Ello software - otherwise they all default to 0 and
    don't work separately. 
    '''
    def __init__(self, port):
        self.termination_character = '\n'
        self.port_settings = dict(baudrate=9600,
                                  bytesize=8,
                                  stopbits=1,
                                  parity='N',
                                  timeout=2,
                                  writeTimeout=2,
                                  xonxoff=False)
        super().__init__(port)
        


class Thorlabs_ELL20(Stage):

    #default id is 0, but if multiple devices of same type connected may have others
    VALID_DEVICE_IDs = [str(v) for v in list(range(0,11)) + ["A","B","C","D","E","F"]]

    #How much a stage sleeps (in seconds) between successive calls to .get_position.
    #Used to make blocking calls to move_absolute and move_relative. 
    BLOCK_SLEEPING_TIME = 0.02
    #Theshold for position accuracy when stage is meant to be stationary
    #If difference between successive calls to get_position returns value 
    #whose difference is less than jitter - consider stage to have stopped 
    POSITION_JITTER_THRESHOLD = 0.02

    #human readable status codes
    DEVICE_STATUS_CODES = {
            0: "OK, no error",
            1: "Communication Timeout",
            2: "Mechanical time out",
            3: "Command error or not supported",
            4: "Value out of range",
            5: "Module isolated",
            6: "Module out of isolation",
            7: "Initialization error",
            8: "Thermal error",
            9: "Busy",
            10: "Sensor Error",
            11: "Motor Error",
            12: "Out of Range",
            13: "Over current error",
            14: "OK, no error",
            "OutOfBounds" : "Reserved"
        }

    def __init__(self, serial_device, device_index=0, debug=0):
        '''can be passed either a BusDistributor instance, or  "COM5"  '''
        if type(serial_device) is str:
            self.serial_device = BusDistributor(serial_device)
        else:
            self.serial_device = serial_device
        self.debug = debug

        Stage.__init__(self)
        self.ui = None

        #configure stage parameters
        if str(device_index) not in self.VALID_DEVICE_IDs:
            raise ValueError("Device ID: {} is not valid!".format(device_index))
        self.device_index = device_index
        
        configuration = self.get_device_info()
        self.TRAVEL = configuration["travel"]
        self.PULSES_PER_MM = configuration["pulses"]
        
        if self.debug > 0:
            print("Travel (degrees):", self.TRAVEL)
            print("Pulses per mm", self.PULSES_PER_MM)
            print("Device status:",self.get_device_status())

    def query_device(self,query):

        '''
        Wrap a generic query with the ID of the device (integer in range: 0-F)
        so that we dont need to be explicit about this id
        '''
        raw_query = "{0}{1}".format(self.device_index,query)
        if self.debug > 0:
            print("raw_query", raw_query)
        raw_response = self.serial_device.query(raw_query) 
        if self.debug > 0:
            print("raw_response",raw_response)
        return raw_response

    
    def _position_to_pulse_count(self,position):
        '''
        Convert from an position (specified in degrees) into the number of pulses
        that need to be applied to the motor to turn it. 

        pulses_per_revolution - specified by Thorlabs as number of pulses for a revolution (360 deg) of stage
        travel - the maximum angular motion of stage (==360 for ELL8K)

        Method used when sending instructions to move to stage
        '''
        pulses = int(np.rint(position*self.PULSES_PER_MM))
        if self.debug > 0:
            print("Input position:", position) 
            print("Pulses:", pulses) 
        return pulses

    def _pulse_count_to_position(self,pulse_count):
        '''
        Convert from an pulse count into the degrees. 

        pulses_per_revolution - specified by Thorlabs as number of pulses for a revolution (360 deg) of stage
        travel - the maximum angular motion of stage (==360 for ELL8K)

        Method used when reading data received from stage
        '''
        return pulse_count/self.PULSES_PER_MM

    def _position_to_hex_pulses(self, position):
        '''
        Convert position in range (-360.0,360.0) (exclusive of edges) into a hex representation of pulse
        count required for talking to the ELL8K stage
        
        '''
        
        #convert position to number of pulses used to drive motors:
        pulses_int = self._position_to_pulse_count(position)    
        if self.debug > 0 : print("Pulses (int)", pulses_int)
        #make two's complement to allow for -ve values
        pulses_int = int_to_twos_complement(pulses_int)
        if self.debug > 0 : print("Pulses (int,2s compl)", pulses_int)
        #convert integer to hex
        pulses_hex = int_to_hex(pulses_int) 
        if self.debug > 0 : print("Pulses hex:", pulses_hex)
        return pulses_hex

    def _hex_pulses_to_position(self, hex_pulse_position):
        '''
        Convert position to position - full method for processing responses from stage
        '''
        binary_pulse_position = bytes_to_binary(hex_pulse_position)
        int_pulse_position = twos_complement_to_int(binary_pulse_position)
        return self._pulse_count_to_position(int_pulse_position)


    def _decode_position_response(self,response):
        '''
        Method for decoding positional response from stage for responses from:
            mode_absolute, mode_relative, move_home
        '''
        header = response[0:3]
        if header == "{0}GS".format(self.device_index):
            #still moving
            status_code = int(response[3:5],base=16)
            status = self.DEVICE_STATUS_CODES[status_code]
            outp = {"header": header,"status": status}
            return outp
        elif header == "{0}PO".format(self.device_index):
            hex_pulse_position = response[3:11]
            position = self._hex_pulses_to_position(hex_pulse_position)
            outp = {"header": header,"position": position}
            return outp

    def _block_until_stopped(self):
       '''
       Method for blocking move_absolute and move_relative and move_home commands until stage has stopped
       Spins on get_position command comparing returned results. If between two calls position doesn't change
       Then assume stage has stopped and exit
       '''
       stopped = False
       previous_position = 0.0
       current_position = 1.0
        
       try:    
           while(stopped == False):
               time.sleep(self.BLOCK_SLEEPING_TIME)
               current_position = self.get_position()
               stopped =(np.absolute(current_position - previous_position) < self.POSITION_JITTER_THRESHOLD)
               previous_position = current_position
       except KeyboardInterrupt:
           return
       return 


    def get_position(self,axis=None):
        '''
        Query stage for its current position, in degrees
        This method overrides the Stage class' method
        '''
        response = self.query_device("gp")
        header = response[0:3]
        if header == "{0}PO".format(self.device_index):
        #position given in twos complement representation
            byte_position = response[3:11]
            binary_position = bytes_to_binary(byte_position)
            pulse_position = twos_complement_to_int(binary_position)
            position = float(pulse_position)/self.PULSES_PER_MM
            return position
        else:
            raise ValueError("Incompatible Header received:{}".format(header)) 
        
    def move(self,pos, axis=None, relative=False):
        '''
        Send command to move stage.
        pos:  specified in degrees and can be in range (-360,360)
        relative: whether motion is relative to current position or relative to global home
        This method overrides the Stage class' method
        '''
        if relative:
            self.move_relative(pos)
        else:
            self.move_absolute(pos)


    def get_device_info(self):
        '''
        Instruct hardware to identify itself. 
        Give information about model, serial numbner, firmware. 

        This MUST be called at initialization of the stage as the key parameters:

        TRAVEL, PULSES are extracted here

        TRAVEL - the range of travel of the stage, specified in units (mm or deg) relevant to the type of stage
        PULSES - specifieid the number of pulses applied to motors to move stage over entire range of travel

        Hence: ratio of PULSES/TRAVEL gives number of pulses to move 1 mm or 1 deg
        '''
             
        response = self.query_device("in")

        #decode the response
        header = response[0:3]
        ell = response[3:5]
        sn = response[5:13]
        year = response[13:17]
        firmware_release = response[17:19]
        hardware_release = response[19:21]
        
        bytes_travel = response[21:25] #units: mm/deg
        
        binary_travel = bytes_to_binary(bytes_travel)
        travel = twos_complement_to_int(binary_travel)
        
        bytes_pulses = response[25:33]
        binary_pulses = bytes_to_binary(bytes_pulses)
        pulses = twos_complement_to_int(binary_pulses)

        outp = {
            "header" : header,
            "ell" : ell,
            "sn": sn,
            "year": year,
            "firmware_release": firmware_release,
            "hardware_release": hardware_release,
            "travel": travel,
            "pulses": pulses
        }
        return outp 

    def get_device_status(self):
        '''
        Query device to get its status code  - for testing that device is functioning correctly
        '''

        response = self.query_device("gs")
        #read response and decode it:
        header = response[0:3]
        byte_status = response[3:5]
        if self.debug > 0: print("Byte status:", byte_status)

        binary_status = bytes_to_binary(byte_status)
        if self.debug > 0: print("Binary status", binary_status)
        int_status = int(binary_status,base=2)

        if int_status in list(self.DEVICE_STATUS_CODES.keys()):
            return {"header": header, "status": self.DEVICE_STATUS_CODES[int_status]}
        else:
            return {"header": header, "status": self.DEVICE_STATUS_CODES["OutOfBounds"]}

    def move_home(self, blocking=True):
        '''
        Move stage to factory default home location. 
        Note: Thorlabs API allows resetting stages home but this not implemented as it isnt' advised 
        '''

        
        response = self.query_device("ho")
        if blocking:
            self._block_until_stopped()
        return self._decode_position_response(response)
        

    def move_absolute(self, position, blocking=True):
        """Move to absolute position relative to home setting

        Args:
            position (float): position to move to, specified in degrees.

        Returns:
            None

        Raises:
            None

        """
   
        pulses_hex = self._position_to_hex_pulses(position)
        response = self.query_device("ma{0}".format(pulses_hex))
        
        header  = response[0:3]

        if blocking:
            self._block_until_stopped()
        return self._decode_position_response(response)
        
    def move_relative(self,position,blocking=True):
        """Moves relative to current position

        Args:
            position (float): relative position to move to, specified in degrees.
            clockwise(bool): specifies whether we are moving in the clockwise direction. 
                    False if moving anticlockwise
        
        Returns:
            None

        Raises:
            None

        """
        pulses_hex = self._position_to_hex_pulses(position)
        response = self.query_device("mr{0}".format(pulses_hex))
        if blocking:
            self._block_until_stopped()
        return self._decode_position_response(response)
    
    def optimize_motors(self, save_new_params=False):
        '''Due to load, build tolerances and other mechanical variances, the
        default resonating frequency of a particular motor may not be that
        which delivers best performance.
        This message fine tunes the frequency search performed by the
        SEARCHFREQ messages. When this message is called, the
        SEARCHFREQ message is called first automatically to optimize the
        operating frequency. After completion, another frequency search is
        performed and the mechanical performance is monitored to further
        optimize the operating frequencies for backward and forward
        movement. The values then need to be saved
        '''
        reply = self.query_device('om')
        if save_new_params:
            self.save_new_parameters()
        return reply
    def save_new_parameters(self):
        return self.query_device('us')
    
    position = NotifiedProperty(get_position, move_absolute)
    def get_qt_ui(self):
        return ELL20UI(self)

class ELL20UI(QuickControlBox):

    def __init__(self, stage):
        super().__init__()
        
        self.add_doublespinbox('position', 0, stage.TRAVEL)
        self.auto_connect_by_name(controlled_object=stage)   



if __name__ == "__main__":

    stage = Thorlabs_ELL20("COM10", debug=False)
    stage.show_gui(False)

    
