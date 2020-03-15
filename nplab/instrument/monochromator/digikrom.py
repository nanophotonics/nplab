# -*- coding: utf-8 -*-
"""
Created on Tue Apr 24 11:35:36 2018

@author: WMD
"""
from __future__ import division
from __future__ import print_function

from builtins import chr
from past.utils import old_div
from nplab.instrument.serial_instrument import SerialInstrument
from nplab.utils.notified_property import NotifiedProperty

import serial
import numpy as np

class Digikrom(SerialInstrument):
    port_settings = dict(baudrate=9600,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1, #wait at most one second for a response
                        writeTimeout=1, #similarly, fail if writing takes >1s
                        xonxoff=False, rtscts=False, dsrdtr=False,
                    )
    def __init__(self,port = None,serial_number = [50, 52, 51, 49, 55]):
        self.termination_character = ''
        self.serial_number = serial_number
        super(Digikrom, self).__init__(port=port)
    def query(self,message,convert_to_hex = True,return_as_dec = True,
              max_len_returned = 10,block = True):
        """The digikrom uses fixed length commands and has no termination character
        therefore the query function from serialinstrument needs to be overwritten.
        As the digikrom requires input in hex commands must be changed from decimal
        (as listed in the manual) to hex. The returned messages also need the same treatment
        The maximum length of the returned str can also be specified to maximise speed
        as currently it just waits for timeout"""
        if convert_to_hex==True:
            message_hex = self.encode_bytes(message)
        else:
            message_hex = message
        self.write(message_hex)
        returned_message = self.ser.read(max_len_returned)
        if return_as_dec == True:
            returned_message = self.decode_bytes(returned_message)

        if returned_message[-1]==24:
            block = False
            self.set_status_byte(returned_message[-2])
        elif(returned_message!=[message]):
            self.set_status_byte(returned_message[-1])
            while block == True:
                block_message = self.decode_bytes(self.ser.read_all())
                if len(block_message)==1:
                    if block_message[0] == 24:
                        block = False
        return returned_message

    @staticmethod
    def decode_bytes(byte_str):
        """The digikrom uses decimal charcters therefore it is helpful to translate
        hex (returned from the digikrom) into a list of decimal values to prevent
        asci mishaps
        """
        decimal_list = []
        for byte in byte_str:
            decimal_list.append(ord(byte))
        return decimal_list

    @staticmethod
    def encode_bytes(decimal_list):
        """The digikrom uses decimal charcters but recieves hex therefore it is
        helpful to translate decimal values into hex to send to the digikrom
        """
        if type(decimal_list)!=list:
            decimal_list = [decimal_list]
        byte_str = ''
        for decimal in decimal_list:
            byte = chr(decimal)
            byte_str+=byte
        return byte_str

    def set_status_byte(self,status_byte):
        """Extract the status from the status byte """
        binary_byte = bin(status_byte)[2:]
        if len(binary_byte)!=8:
            binary_byte = (8-len(binary_byte))*'0'+binary_byte
        if binary_byte[0]==1:
            motor_movement_order = 'negative'
        else:
            motor_movement_order = 'positive'
        if binary_byte[4]==1:
            scan_direction = 'positive'
        else:
            scan_direction = 'negative'
        if binary_byte[7]=='0':
            value_accepted = True
            value_error = None
        else:
            value_accepted=False
            if binary_byte[6] == '1':
                value_error = 'repeat set'
            elif binary_byte[5] == '1':
                value_error = 'value too large'
            elif binary_byte[5] == '0':
                value_error = 'value too small'
        CSR_mode = bool(int(binary_byte[2]))
        status_dict = {'value_accepted':value_accepted,
                       'value_error':value_error,
                       'motor_movement_order':motor_movement_order,
                       'scan_direction' :scan_direction,
                       'CSR_mode':CSR_mode
                       }

        if value_accepted==True:
            level = 'debug'
        else:
            level = 'warn'
        self.log(status_dict,level = level)
        self._status_byte = status_dict
    def get_wavelength(self):
        """The get wavlength command number is 29 and data is returned as 3 bytes,
        the high byte, the mid byte and the low bye. These byte correspond to
        multiples of 65536, 256 and 1. as shown below"""
        returned_message = self.query(29)
        wl = returned_message[1]*65536
        wl += 256*returned_message[2]
        wl += returned_message[3]
        self.set_status_byte(returned_message[-2])
        return wl/100.0
    def set_wavelength(self,wl):
        """The set wavlength command number is 16 and data is sent as 3 bytes,
        the high byte, the mid byte and the low bye. These byte correspond to
        multiples of 65536, 256 and 1. as shown below"""
        self.query(16,block = False)
        wl = wl*100
        high_byte = int(old_div(wl,65536))
        wl = wl-high_byte*65536
        mid_byte = int(old_div(wl,256))
        wl = wl-mid_byte*256
        low_byte = int(wl)
        self.query([high_byte,mid_byte,low_byte])

    centre_wavlength = NotifiedProperty(get_wavelength,set_wavelength)


    def get_grating_id(self):
        info = self.query(19)
        info_dict = {'number_of_gratings': info[1],
                     'current_grating': info[2],
                     'grating_ruling':info[3]*256+info[4],
                     'grating_blaze':info[5]*256+info[6]}
        return info_dict
    def set_grating(self,grating_number):
        """This command changes gratings , if additional gratings installed.."""
        self.query(26)
        self.query(grating_number)
    def reset(self):
        """This command returns the grating to home position """
        self.query([255,255,255])

    def clear(self):
        """This command restores factory calibration values for the grating and slits.
        This command also executes a reset, which returns the grating to home position."""
        self.query(25)

    def CSR(self,bandpass_value):
        """ This command sets monochromator to Constant Spectral Resolution mode.
        The slit width will vary throughout a scan. This is useful, for example,
        where measurement of a constant interval of frequency is desired
        (spectral power distribution measurements)."""
        self.query(28)
        high_byte = int(old_div(bandpass_value,256))
        bandpass_value = bandpass_value-high_byte*256
        low_byte = int(bandpass_value)
        self.query([high_byte,low_byte])

    def echo(self):
        """The ECHO command is used to verify communications with the DK240/480.
        """
        self.log(self.query(27),level = 'info')

    def gval(self,repositioning_wl):
        """This command allows recalibration of the monochromator positioning
        scale factor and should be used immediately after using the ZERO command
        (see page 15). The monochromator should be set to the peak of a known spectral line,
        then the position of that line is input using the CALIBRATE command.
        """
        self.query(18)
        repositioning_wl = repositioning_wl*100
        high_byte = int(old_div(repositioning_wl,65536))
        repositioning_wl = repositioning_wl-high_byte*65536
        mid_byte = int(old_div(repositioning_wl,256))
        repositioning_wl = repositioning_wl-mid_byte*256
        low_byte = int(repositioning_wl)
        self.query([high_byte,mid_byte,low_byte])
    def get_serial(self):
        """ Returns the 5 digit serial number of the monochromator."""
        return self.query(33)[1:-2]

    def get_slit_widths(self):
        """Returns the current four byte (six byte for DK242) slit width.
        First two bytes are high and low byte of the entrance slit width in microns.
        Second two bytes are the high and low byte of the exit slit width.
        For DK242, the last two bytes are for middle slit width."""
        slit_info = self.query(30)[1:-2]
        slit_info = np.array(slit_info)
        low_byte = slit_info[1::2]
        high_byte = slit_info[::2]
        slit_info = 256*high_byte+low_byte
        return slit_info

    def set_all_slits(self,slit_width):
        """ Adjusts all slits to a given width.
        """
        high_byte = int(old_div(slit_width,256))
        slit_width = slit_width-high_byte*256
        low_byte = int(slit_width)
        self.query(14)
        self.query([high_byte,low_byte])

    def set_slit_1_width(self,slit_width):
        """Adjusts entrance slit to a given width."""
        high_byte = int(old_div(slit_width,256))
        slit_width = slit_width-high_byte*256
        low_byte = int(slit_width)
        self.query(31)
        self.query([high_byte,low_byte])

    def set_slit_2_width(self,slit_width):
        """Adjusts exit slit to a given width."""
        """Slit 2 (exit) not installed 05042019"""
        high_byte = int(old_div(slit_width,256))
        slit_width = slit_width-high_byte*256
        low_byte = int(slit_width)
        self.query(32)
        self.query([high_byte,low_byte])

    def set_slit_3_width(self,slit_width):
        """Adjusts middle slit to a given width."""
        high_byte = int(old_div(slit_width,256))
        slit_width = slit_width-high_byte*256
        low_byte = int(slit_width)
        self.query(34)
        self.query([high_byte,low_byte])


    def test_communications(self):
        """Check there is the correct digikrom at other end of the COM port."""
        try:
            serial_num = self.get_serial()
        except:
            return False
        if serial_num == self.serial_number:
            return True
        else:
            return False

def init():
    spec = Digikrom(port="COM9",serial_number = [50, 52, 51, 49, 55])
    return spec 

if __name__ == '__main__':
    spec = Digikrom(serial_number = [50, 52, 51, 49, 55])
    print(spec)
    # spec.set_wavelength(0)
    wavel =spec.get_wavelength()
    print(wavel)
    slit=spec.get_slit_widths()
    print(slit)