# -*- coding: utf-8 -*-

from nplab.instrument.visa_instrument import VisaInstrument
from nplab.instrument.camera.ST133.pvcam import Pvcam
import re
import time
from visa import VisaIOError


class SP2750(VisaInstrument):
    """ftp://ftp.princetoninstruments.com/public/manuals/Acton/SP-2750.pdf"""

    def __init__(self, address):
        port_settings = dict(baud_rate=9600, read_termination="\r\n", write_termination="\r", timeout=3000)
        super(SP2750, self).__init__(address, port_settings)
        self.clear_read_buffer()

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
        elif status == "ok":
            return reply.rstrip("").lstrip("")
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
        wvl = float(re.findall(" ([0-9]+\.[0-9]+) ", string)[0])
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


class Pvacton(Pvcam):
    def __init__(self, camera_device, spectrometer_address, **kwargs):
        # super(Pvacton, self).__init__(camera_device, **kwargs)
        # SP2750.__init__(self, spectrometer_address)
        Pvcam.__init__(self, camera_device, **kwargs)
        self.spectrometer = SP2750(spectrometer_address)

    def get_wavelength(self):
        wvl = self.spectrometer.get_wavelength()
        self.unit_offset[0] = wvl
        return wvl

    def set_wavelength(self, wvl):
        self.spectrometer.set_wavelength(wvl)
        self.unit_offset[0] = self.spectrometer.calibrate(wvl) - self.unit_scale[0] * self.resolution[0] / 2

    wavelength = property(get_wavelength, set_wavelength)


if __name__ == "__main__":
    spec = SP2750("COM12")

    print spec.query("?NM")
    print spec.query("?GRATINGS")

    print spec.set_wavelength_fast(0)
    print spec.get_wavelength()

    print spec.set_wavelength_fast(200)
    print spec.get_wavelength()
