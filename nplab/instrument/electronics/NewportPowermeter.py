# -*- coding: utf-8 -*-
"""
Modified from https://github.com/plasmon360/python_newport_1918_powermeter

"""
from __future__ import division
from __future__ import print_function

from builtins import str
from past.utils import old_div
from nplab.instrument import Instrument
from ctypes import *
import time
import numpy as np


class NewportPowermeter(Instrument):
    def __init__(self, product_id, **kwargs):
        """

        :param product_id: go to Device Manager, double click on instrument, go to Details, in the Property drop-down,
                select Hardware IDs. If the ID is something like PID_ABC1, use product_id = 0xACB1
        :param kwargs:
        """
        super(NewportPowermeter, self).__init__()
        if "libname" in kwargs:
            libname = kwargs["libname"]
        else:
            libname = "usbdll.dll"
        self.dll = windll.LoadLibrary(libname)

        self.product_id = product_id

        self.open_device_with_product_id()
        self.instrument = self.get_instrument_list()
        self.device_id, self.model_number, self.serial_number = self.instrument

        self.wvl_range = [int(self.query('PM:MIN:Lambda?')), int(self.query('PM:MAX:Lambda?'))]

    # def __del__(self):
    #     self.close_device()

    def _dllWrapper(self, command, *args):
        """Simple dll wrapper
        Takes care of the error checking for all dll calls
        :param command: string with the command name
        :param args: list of (optional) arguments to pass to the dll function
        :return:
        """
        self._logger.debug("Calling DLL with: %s %s" % (command, args))
        status = getattr(self.dll, command)(*args)
        if status != 0:
            raise Exception('%s failed with status %s' % (command, status))
        else:
            pass

    def open_device_all_products_all_devices(self):
        self._dllWrapper("newp_usb_init_system")
        self._logger.info("You have connected to one or more Newport products")

    def open_device_with_product_id(self):
        """
        opens a device with a certain product id

        """
        cproductid = c_int(self.product_id)
        useusbaddress = c_bool(1)  # We will only use deviceids or addresses
        num_devices = c_int()

        self._dllWrapper("newp_usb_open_devices", cproductid, useusbaddress, byref(num_devices))

    def close_device(self):
        self._dllWrapper("newp_usb_uninit_system")

    def get_instrument_list(self):
        arInstruments = c_int()
        arInstrumentsModel = c_int()
        arInstrumentsSN = c_int()
        nArraySize = c_int()
        self._dllWrapper("GetInstrumentList", byref(arInstruments), byref(arInstrumentsModel), byref(arInstrumentsSN),
                         byref(nArraySize))
        instrument_list = [arInstruments.value, arInstrumentsModel.value, arInstrumentsSN.value]
        return instrument_list

    def query(self, query_string):
        """
        Write a query and read the response from the device
        :rtype : String
        :param query_string: Check Manual for commands, ex '*IDN?'
        :return:
        """
        self.write(query_string)
        return self.read()

    def read(self):
        cdevice_id = c_long(self.device_id)
        time.sleep(0.2)
        response = create_string_buffer(('\000' * 1024).encode())
        leng = c_ulong(1024)
        read_bytes = c_ulong()
        self._dllWrapper("newp_usb_get_ascii", cdevice_id, byref(response), leng, byref(read_bytes))
        answer = response.value[0:read_bytes.value].rstrip(b'\r\n')
        return answer

    def write(self, command_string):
        """
        Write a string to the device

        :param command_string: Name of the string to be sent. Check Manual for commands
        :raise:
        """
        command = create_string_buffer(command_string.encode())
        length = c_ulong(sizeof(command))
        cdevice_id = c_long(self.device_id)

        self._dllWrapper("newp_usb_send_ascii", cdevice_id, byref(command), length)

    @property
    def channel(self):
        return self.query("PM:CHANnel?")

    @channel.setter
    def channel(self, channel):
        assert channel in [1, 2]

        self.write("PM:CHANnel " + str(channel))

    @property
    def wavelength(self):
        self._logger.debug("Reading wavelength")
        return self.query('PM:Lambda?')

    @wavelength.setter
    def wavelength(self, wavelength):
        """
        Sets the wavelength on the device
        :param wavelength int: float
        """
        self._logger.debug("Setting wavelength")
        if not isinstance(wavelength, int):
            self._logger.info('Wavelength has to be an integer. Converting to integer')
            wavelength = int(wavelength)
        assert self.wvl_range[0] <= wavelength <= self.wvl_range[1]

        self.write('PM:Lambda ' + str(wavelength))

    def set_filtering(self, filter_type=0):
        """
        Set the filtering on the device
        :param filter_type:
        0:No filtering
        1:Analog filter
        2:Digital filter
        3:Analog and Digital filter
        """
        if filter_type in [0, 1, 2, 3]:
            self.write("PM:FILT %d" % filter_type)
        else:
            raise ValueError("filter_type needs to be between 0 and 3")

    def read_buffer(self, wavelength=700, buff_size=1000, interval_ms=1):
        """
        Stores the power values at a certain wavelength.
        :param wavelength: float: Wavelength at which this operation should be done. float.
        :param buff_size: int: nuber of readings that will be taken
        :param interval_ms: float: Time between readings in ms.
        :return: [actualwavelength,mean_power,std_power]
        """
        self.wavelength = wavelength
        self.write('PM:DS:Clear')
        self.write('PM:DS:SIZE ' + str(buff_size))
        self.write('PM:DS:INT ' + str(
            interval_ms * 10))  # to set 1 ms rate we have to give int value of 10. This is strange as manual says the INT should be in ms
        self.write('PM:DS:ENable 1')
        while int(self.query('PM:DS:COUNT?')) < buff_size:  # Waits for the buffer is full or not.
            time.sleep(old_div(0.001 * interval_ms * buff_size, 10))
        actualwavelength = self.query('PM:Lambda?')
        mean_power = self.query('PM:STAT:MEAN?')
        std_power = self.query('PM:STAT:SDEV?')
        self.write('PM:DS:Clear')
        return [actualwavelength, mean_power, std_power]

    @property
    def power(self):
        """
        Reads the instantaneous power
        """

        power = self.query('PM:Power?')
        return float(power)


if __name__ == '__main__':
    nd = NewportPowermeter(0xCEC7)
    nd._logger.setLevel("DEBUG")
    print('Init finished')
    print(nd.get_instrument_list())
    print(nd.wavelength)
    print(nd.power)
    print(nd.wavelength)
    print(nd.power)
