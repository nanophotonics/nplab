'''
author: im354
'''
from __future__ import division
from __future__ import print_function

from builtins import str
from builtins import range
from past.utils import old_div
import struct,sys,math
from bitarray import bitarray
import numpy as np 
from nplab.instrument.serial_instrument import SerialInstrument
from nplab.instrument.stage import Stage
from nplab.utils.gui import *
from nplab.ui.ui_tools import *
import time

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

class Thorlabs_ELL8K(SerialInstrument,Stage):

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

    def __init__(self,port=None,device_index=0,debug=0):
        self.debug = debug
        self.termination_character = '\n'
        self.port_settings = dict(baudrate=9600,
                                  bytesize=8,
                                  stopbits=1,
                                  parity='N',
                                  timeout=2,
                                  writeTimeout=2,
                                  xonxoff=False
        )

        SerialInstrument.__init__(self, port)
        Stage.__init__(self)
        self.ui = None

        #configure stage parameters
        if str(device_index) not in Thorlabs_ELL8K.VALID_DEVICE_IDs:
            raise ValueError("Device ID: {} is not valid!".format(device_index))
        self.device_index = device_index
        
        configuration = self.get_device_info()
        self.TRAVEL = configuration["travel"]
        self.PULSES_PER_REVOLUTION = configuration["pulses"]
        
        if self.debug > 0:
            print("Travel (degrees):", self.TRAVEL)
            print("Pulses per revolution", self.PULSES_PER_REVOLUTION)
            print("Device status:",self.get_device_status())

    def query_device(self,query):

        '''
        Wrap a generic query with the ID of the device (integer in range: 0-F)
        so that we dont need to be explicit about this id
        '''
        raw_query = "{0}{1}".format(self.device_index,query)
        if self.debug > 0:
            print("raw_query",raw_query)
        raw_response = self.query(raw_query) 
        if self.debug > 0:
            print("raw_response",raw_response)
        return raw_response

    
    def __angle_to_pulse_count(self,angle):
        '''
        Convert from an angle (specified in degrees) into the number of pulses
        that need to be applied to the motor to turn it. 

        pulses_per_revolution - specified by Thorlabs as number of pulses for a revolution (360 deg) of stage
        travel - the maximum angular motion of stage (==360 for ELL8K)

        Method used when sending instructions to move to stage
        '''
        pulse_per_deg = self.PULSES_PER_REVOLUTION/float(self.TRAVEL)
        pulses = int(np.rint(angle*pulse_per_deg))
        if self.debug > 0:
            print("Input angle:", angle) 
            print("Pulses:", pulses) 
        return pulses

    def __pulse_count_to_angle(self,pulse_count):
        '''
        Convert from an pulse count into the degrees. 

        pulses_per_revolution - specified by Thorlabs as number of pulses for a revolution (360 deg) of stage
        travel - the maximum angular motion of stage (==360 for ELL8K)

        Method used when reading data received from stage
        '''
        return float(self.TRAVEL)*pulse_count/self.PULSES_PER_REVOLUTION

    def __angle_to_hex_pulses(self,angle):
        '''
        Convert angle in range (-360.0,360.0) (exclusive of edges) into a hex representation of pulse
        count required for talking to the ELL8K stage
        
        '''
        if angle < -360.0 or angle > 360.0:
            raise ValueError("Valid angle bounds are: (-360,360) [exclusive]")

        #convert angle to number of pulses used to drive motors:
        pulses_int = self.__angle_to_pulse_count(angle)    
        if self.debug > 0 : print("Pulses (int)", pulses_int)
        #make two's complement to allow for -ve values
        pulses_int = int_to_twos_complement(pulses_int)
        if self.debug > 0 : print("Pulses (int,2s compl)", pulses_int)
        #convert integer to hex
        pulses_hex = int_to_hex(pulses_int) 
        if self.debug > 0 : print("Pulses hex:", pulses_hex)
        return pulses_hex

    def __hex_pulses_to_angle(self, hex_pulse_position):
        '''
        Convert position to angle - full method for processing responses from stage
        '''
        binary_pulse_position = bytes_to_binary(hex_pulse_position)
        int_pulse_position = twos_complement_to_int(binary_pulse_position)
        return self.__pulse_count_to_angle(int_pulse_position)


    def __decode_position_response(self,response):
        '''
        Method for decoding positional response from stage for responses from:
            mode_absolute, mode_relative, move_home
        '''
        header = response[0:3]
        if header == "{0}GS".format(self.device_index):
            #still moving
            status_code = int(response[3:5],base=16)
            status = Thorlabs_ELL8K.DEVICE_STATUS_CODES[status_code]
            outp = {"header": header,"status": status}
            return outp
        elif header == "{0}PO".format(self.device_index):
            hex_pulse_position = response[3:11]
            position = self.__hex_pulses_to_angle(hex_pulse_position)
            outp = {"header": header,"position": position}
            return outp

    def __block_until_stopped(self):
       '''
       Method for blocking move_absolute and move_relative and move_home commands until stage has stopped
       Spins on get_position command comparing returned results. If between two calls position doesn't change
       Then assume stage has stopped and exit
       '''
       stopped = False
       previous_angle = 0.0
       current_angle = 1.0
        
       try:    
           while(stopped == False):
               time.sleep(Thorlabs_ELL8K.BLOCK_SLEEPING_TIME)
               current_angle = self.get_position()
               stopped =(np.absolute(current_angle - previous_angle) < Thorlabs_ELL8K.POSITION_JITTER_THRESHOLD)
               previous_angle = current_angle
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
            degrees_position = self.TRAVEL*(float(pulse_position)/self.PULSES_PER_REVOLUTION)
            return degrees_position
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


    def get_qt_ui(self):
        '''
        Get UI for stage
        '''
        if self.ui is None:
            self.ui = Thorlabs_ELL8K_UI(stage=self) 
        return self.ui

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

        if int_status in list(Thorlabs_ELL8K.DEVICE_STATUS_CODES.keys()):
            return {"header": header, "status": Thorlabs_ELL8K.DEVICE_STATUS_CODES[int_status]}
        else:
            return {"header": header, "status": Thorlabs_ELL8K.DEVICE_STATUS_CODES["OutOfBounds"]}

    def move_home(self,clockwise=True,blocking=True):
        '''
        Move stage to factory default home location. 
        Note: Thorlabs API allows resetting stages home but this not implemented as it isnt' advised 
        '''
        if clockwise:
            direction = 0
        else:
            direction = 1
        response = self.query_device("ho{0}".format(direction))

        if blocking:
            self.__block_until_stopped()
        return self.__decode_position_response(response)
        

    def move_absolute(self,angle,blocking=True):
        """Move to absolute position relative to home setting

        Args:
            angle (float): angle to move to, specified in degrees.

        Returns:
            None

        Raises:
            None

        """
        if -360>angle or angle>360:
            angle %= 360
        if angle<0:
            angle = 360+angle    
        pulses_hex = self.__angle_to_hex_pulses(angle)
        response = self.query_device("ma{0}".format(pulses_hex))
        
        header  = response[0:3]

        if blocking:
            self.__block_until_stopped()
        return self.__decode_position_response(response)
        
    def move_relative(self,angle,blocking=True):
        """Moves relative to current position

        Args:
            angle (float): relative angle to move to, specified in degrees.
            clockwise(bool): specifies whether we are moving in the clockwise direction. 
                    False if moving anticlockwise
        
        Returns:
            None

        Raises:
            None

        """
        pulses_hex = self.__angle_to_hex_pulses(angle)
        response = self.query_device("mr{0}".format(pulses_hex))
        if blocking:
            self.__block_until_stopped()
        return self.__decode_position_response(response)
    def optimize_motors(self, save_new_params = False):
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
        self.query_device('om')
        if save_new_params:
            self.save_new_parameters()
    def save_new_parameters(self):
        self.query_device('us')

class Thorlabs_ELL8K_UI(QtWidgets.QWidget, UiTools):

    def __init__(self,stage, parent=None,debug = 0):
        if not isinstance(stage, Thorlabs_ELL8K):
            raise ValueError("Object is not an instance of the Thorlabs_ELL8K Stage")
        super(Thorlabs_ELL8K_UI, self).__init__()
        self.stage = stage #this is the actual rotation stage
        self.parent = parent
        self.debug =  debug

        uic.loadUi(os.path.join(os.path.dirname(__file__), 'thorlabs_ell8k.ui'), self)

        self.move_relative_btn.clicked.connect(self.move_relative)
        self.move_absolute_btn.clicked.connect(self.move_absolute)
        self.move_home_btn.clicked.connect(self.move_home)
        self.current_angle_btn.clicked.connect(self.update_current_angle)
   
    def move_relative(self):
        try:
            angle = float(self.move_relative_textbox.text())
        except ValueError as e:
            print(e)
            return 
        self.stage.move(pos=angle,relative=True)


    def move_absolute(self):
        try:
            angle = float(self.move_absolute_textbox.text())
        except ValueError as e:
            print(e)
            return 
        self.stage.move(pos=angle,relative=False)

    def move_home(self):
        self.stage.move_home()

    def update_current_angle(self):
        angle = self.stage.get_position()
        self.current_angle_value.setText(str(angle))
                



def test_stage(s):
    '''
    Run from main to test stage
    '''
    debug = False
    
    print("Status",s.get_device_status())
    print("Info",s.get_device_info())
    print("Homing",s.move_home())
    print("Home position",s.get_position())
    angle = 30
    s.move(angle,relative=True)
    print("30==",s.get_position())
    angle = -30
    s.move(angle,relative=True)
    print("-30==",s.get_position())

    angle = 150
    s.move(angle,relative=False)
    print("150==", s.get_position())

    angle = -10
    s.move(angle,relative=False)
    print("350==", s.get_position())

def test_ui():
    '''
    Run from main to test ui + stage
    '''
    s = Thorlabs_ELL8K("COM14")
    app = get_qt_app()
    ui = Thorlabs_ELL8K_UI(stage=s)
    ui.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    stage = Thorlabs_ELL8K("COM14",debug=False)
    test_stage(stage)
    # test_ui()

    
