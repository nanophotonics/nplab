# -*- coding: utf-8 -*-
"""
Created on Mon Aug  9 16:22:04 2021

@author: Hera
"""
'''
author: im354
'''


from nplab.utils.notified_property import NotifiedProperty
from nplab.ui.ui_tools import QuickControlBox
from nplab.instrument.stage.thorlabs_ello import ElloDevice, bytes_to_binary, twos_complement_to_int, int_to_hex, int_to_twos_complement
import numpy as np

class Ell20(ElloDevice):

    def __init__(self, serial_device, device_index=0, debug=0):
        '''can be passed either a BusDistributor instance, or  "COM5"  '''
        super().__init__(serial_device, device_index=0, debug=0)
        
        
        self.configuration = self.get_device_info()
        self.TRAVEL = self.configuration["travel"]
        self.PULSES_PER_MM = self.configuration["pulses"]
        if self.debug > 0:
            print("Travel (degrees):", self.TRAVEL)
            print("Pulses per revolution", self.PULSES_PER_MM)
            print("Device status:", self.get_device_status())
    
    
    def _position_to_pulse_count(self, position):
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

    def _pulse_count_to_position(self, pulse_count):
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

        # convert position to number of pulses used to drive motors:
        pulses_int = self._position_to_pulse_count(position)
        if self.debug > 0:
            print("Pulses (int)", pulses_int)
        # make two's complement to allow for -ve values
        pulses_int = int_to_twos_complement(pulses_int)
        if self.debug > 0:
            print("Pulses (int,2s compl)", pulses_int)
        # convert integer to hex
        pulses_hex = int_to_hex(pulses_int)
        if self.debug > 0:
            print("Pulses hex:", pulses_hex)
        return pulses_hex

    def _hex_pulses_to_position(self, hex_pulse_position):
        '''
        Convert position to position - full method for processing responses from stage
        '''
        binary_pulse_position = bytes_to_binary(hex_pulse_position)
        int_pulse_position = twos_complement_to_int(binary_pulse_position)
        return self._pulse_count_to_position(int_pulse_position)
    
    
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

        header = response[0:3]

        if blocking:
            self._block_until_stopped()
        return self._decode_position_response(response)
    
    def get_position(self, axis=None):
        '''
        Query stage for its current position, in degrees
        This method overrides the Stage class' method
        '''
        response = self.query_device("gp")
        header = response[0:3]
        if header == "{0}PO".format(self.device_index):
            # position given in twos complement representation
            byte_position = response[3:11]
            binary_position = bytes_to_binary(byte_position)
            pulse_position = twos_complement_to_int(binary_position)
            position = float(pulse_position)/self.PULSES_PER_MM
            return position
        else:
            raise ValueError("Incompatible Header received:{}".format(header))

    def move_home(self, blocking=True):
        '''
        Move stage to factory default home location. 
        Note: Thorlabs API allows resetting stages home but this not implemented as it isnt' advised 
        '''

        response = self.query_device("ho")
        if blocking:
            self._block_until_stopped()
        return self._decode_position_response(response)

    def get_qt_ui(self):
        return ELL20UI(self)


class ELL20UI(QuickControlBox):

    def __init__(self, stage):
        super().__init__()
        self.add_doublespinbox('position', 0, stage.TRAVEL)
        self.auto_connect_by_name(controlled_object=stage)


class Ell20BiPositional(Ell20):
    SLOTS = (0.05, 0.95)  # fractions of travel
    TOLERANCE = 0.05

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.move_home()
        # self.slot = 0
        self.PULSES_PER_REVOLUTION = self.PULSES_PER_MM

    def get_slot(self):
        frac = self.get_position() / self.TRAVEL
        for i, slot in enumerate(self.SLOTS):
            if abs(frac - slot) < self.TOLERANCE:
                return i
        self.log('not in either position', level='warn')

    def set_slot(self, index):
        self.move(self.SLOTS[index]*self.TRAVEL)
    slot = NotifiedProperty(get_slot, set_slot)

    def center(self):
        slot = min(enumerate(self.SLOTS),
                   key=lambda i_s: abs(i_s[1] - (self.get_position() / self.TRAVEL)))[0]
        self.slot = slot

    def get_qt_ui(self):
        return Ell20BiPositionalUi(self)


class Ell20BiPositionalUi(QuickControlBox):

    def __init__(self, stage):
        super().__init__()

        self.add_spinbox('slot', 0, len(stage.SLOTS))
        self.auto_connect_by_name(controlled_object=stage)


if __name__ == "__main__":
    stage = Ell20BiPositional('COM6')
    # stage = Thorlabs_ELL20("COM10", debug=False)
    stage.show_gui(False)
