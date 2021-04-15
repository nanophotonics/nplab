# -*- coding: utf-8 -*-

from builtins import str
from nplab.instrument.visa_instrument import VisaInstrument
import re
import time
from visa import VisaIOError
import os
import json
import numpy as np


class SP2750(VisaInstrument):
    """ Monochromator class
    ftp://ftp.princetoninstruments.com/public/manuals/Acton/SP-2750.pdf
    """

    @property
    def wavelength(self):
        return self.get_wavelength()

    @wavelength.setter
    def wavelength(self, value):
        self.set_wavelength_fast(value)

    def __init__(self, address, calibration_file=None):
        port_settings = dict(baud_rate=9600, read_termination="\r\n", write_termination="\r", timeout=10000)
        super(SP2750, self).__init__(address, port_settings)
        self.clear_read_buffer()
        self._calibration_file = calibration_file

        self.metadata_property_names += ('wavelength', )

    def query(self, *args, **kwargs):
        """
        Simple query wrapper that checks whether the command was received properly
        :param args:
        :param kwargs:
        :return:
        """
        full_reply = self.instr.query(*args, **kwargs)

        status = full_reply[-2:]
        reply = full_reply[:-2]

        if "?" in full_reply:
            self._logger.warn("Message  %s" % full_reply)

        if status == "ok":
            return reply.strip()
        else:
            self._logger.info("Multiple reads")
            read = str(full_reply)
            idx = 0
            while "ok" not in read:
                read += " | " + self.read()
                idx += 1
                if idx > 10:
                    raise ValueError("Too many multiple reads")
            return read

    def calibrate(self, wvl, to_device=True):
        if to_device:
            calibrated = wvl
        else:
            calibrated = wvl
        return calibrated

    # MOVEMENT COMMANDS
    def _wait(self):
        """Checks whether movement has finished"""
        time.sleep(1)
        t0 = time.time()
        while time.time() - t0 < 10 and not self.is_ready():
            try:
                if self.is_ready():
                    break
            except VisaIOError as e:
                time.sleep(1)  # This you get from testing

    def set_wavelength_fast(self, wvl):
        """
        Goes to a destination wavelength at maximum motor speed. Accepts destination wavelength in nm as a floating
        point number with up to 3 digits after the decimal point or whole number wavelength with no decimal point.
        :param wvl:
        :return:
        """

        self.write("%0.3f GOTO" % self.calibrate(wvl))
        # TODO: wait until the spectrometer replies OK
        self._wait()
        return self.read()

    def set_wavelength(self, wvl):
        """
        Goes to a destination wavelength at constant nm/min rate specified by last NM/MIN
        command. Accepts destination wavelength in nm as a floating point number with up
        to 3 digits after the decimal point or whole number wavelength with no decimal point.
        :param wvl:
        :return:
        """

        self.write("%0.3f NM" % self.calibrate(wvl))

    def get_wavelength(self):
        """
        Returns present wavelength in nm to 0.01nm resolution with units nm appended.
        :return:
        """
        string = self.query("?NM")
        wvl = float(re.findall("([0-9]+\.[0-9]+) ", string)[0])
        return self.calibrate(wvl, False)

    def set_speed(self, rate):
        """
        Sets the scan rate in nm/min to 0.01 nm/min resolution with units nm/min
        :param rate:
        :return:
        """
        self.query("%0.3f NM/MIN" % rate)

    def is_ready(self):
        return bool(self.query("MONO-?DONE"))

    # GRATING CONTROL
    def set_grating(self, index):
        """
        Places specified grating in position to the wavelength of the wavelength on the
        present grating. Up to nine (9) gratings are allowed on three (3) turrets. This
        command takes a grating number from 1 -9. IMPORTANT NOTE: This command
        assumes that the correct turret is specified by the TURRET command. For example,
        using grating numbers 1, 4 and 7 will place the first grating on the installed turret into
        that position and call up the parameters for the grating number specified.
        :param index:
        :return:
        """

        self.query("%d GRATING" % index)

    def get_grating(self):
        """
        Returns the number of gratings presently being used numbered 1 -9.
        :return:
        """
        return self.query("?GRATING")

    def get_gratings(self):
        """
        Returns the list of installed gratings with position groove density and blaze. The
        present grating is specified with an arrow.
        :return:
        """
        return self.query("?GRATINGS")

    # DIVERTER MIRRORS
    @property
    def exit_mirror(self):
        self.query('EXIT-MIRROR')
        return self.query('?MIRROR')

    @exit_mirror.setter
    def exit_mirror(self, value):
        assert value in ['SIDE', 'FRONT']
        self.query('EXIT-MIRROR')
        self.query(value)

    @property
    def entrance_mirror(self):
        self.query('ENT-MIRROR')
        return self.query('?MIRROR')

    @entrance_mirror.setter
    def entrance_mirror(self, value):
        assert value in ['SIDE', 'FRONT']
        self.query('ENT-MIRROR')
        self.query(value)

    # CALIBRATED MEASUREMENT
    @property
    def calibration_file(self):
        """Path to the calibration file"""
        if self._calibration_file is None:
            self._calibration_file = os.path.join(os.path.dirname(__file__), 'default_calibration.json')
        return self._calibration_file

    @calibration_file.setter
    def calibration_file(self, path):
        """Ensures the path is absolute and points to a .json file"""
        if not os.path.isabs(path):
            default_directory = os.path.dirname(__file__)
            path, ext = os.path.splitext(path)
            if ext != 'json':
                if ext != '':
                    self._logger.warn('Changing file type to JSON')
                ext = 'json'
                path = os.path.join(default_directory, path + '.' + ext)
        self._calibration_file = path

    def get_wavelengths(self):
        """Returns the current wavelength range being shown on a detector attached to the SP2750

        Reads from a calibration file that contains the detector size being used, and the dispersion. Example JSONs:
            {
              "detector_size": 100,
              "dispersion": 0.01
            }
            {
              "detector_size": 100,
              "dispersion": [0.0001, 0.02]
            }
            {
              "detector_size": 2048,
              "dispersion": {"1": 0.014, "2": [0.0001, 0.02]},
              "offset": {"1": [0.00001, 1]}
            }
        :return:
        """
        central_wavelength = self.wavelength

        with open(self.calibration_file, 'r') as dfile:
            calibration = json.load(dfile)
        detector_size = calibration['detector_size']

        dispersion = calibration['dispersion']
        if isinstance(dispersion, dict):
            current_grating = self.get_grating()
            dispersion = dispersion[current_grating]
        poly = np.poly1d(dispersion)  # poly1d handles it whether you give it a number on an iterable
        dispersion_value = poly(central_wavelength)

        offset_value = 0
        if 'offset' in calibration:
            offset = calibration['offset']
            if isinstance(offset, dict):
                current_grating = self.get_grating()
                offset = offset[current_grating]

            poly = np.poly1d(offset)
            offset_value = poly(central_wavelength)

        pixels = np.arange(detector_size, dtype=np.float)
        pixels -= np.mean(pixels)
        delta_wvl = pixels * dispersion_value
        return central_wavelength + delta_wvl + offset_value
