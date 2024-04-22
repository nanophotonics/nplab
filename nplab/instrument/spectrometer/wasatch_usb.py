#!/usr/bin/env python
# coding: utf-8

# # SIG Spectrometer Test
# 
# An import python file to talk to a SIG spetrometer - replaces 'spectrometer.py' used for regular spectrometers.
# 
# Like the latter, probably needs the following:
# 
# Needs: python3-usb and python3-psutil. Install with apt-get:
# 
# * sudo apt-get install python3-dev
# * sudo apt-get install python3-psutil
# * sudo apt-get install python3-usb
# * sudo apt-get install libusb-1.0-0-dev
# 
# Libraries needed:
# 
# * numpy
# * For Plot: matplotlib
# * For Save: pandas
# 
# Need to set udev rules: Copy 10-wasatch.rules to /etc/udev/rules.d
# then refresh: sudo udevadm control --reload-rules && sudo udevadm trigger
# then unplug USB and plug back in

# In[1]:

import usb.core
import struct
import math

from time import sleep
from datetime import datetime

# In[2]:

HOST_TO_DEVICE = 0x40
DEVICE_TO_HOST = 0xC0
TIMEOUT_MS = 1000

MAX_PAGES = 8
PAGE_SIZE = 64

# In[3]:

# An extensible, stateful "Test Fixture" 
class SIGspectrometer(object):

    ############################################################################
    # Lifecycle 
    ############################################################################

    def __init__(self):
        self.device = None
        self.DEBUG = False
        
        # grab first spectrometer on the chain
        device = usb.core.find(idVendor=0x24aa, idProduct=0x4000)
        if device is None:
            print("No spectrometers found")
            return
        self.debug(device)
        self.device = device

        # claim device (I'm never sure when this is required)
        if False:
            self.debug("claiming spectrometer")
            self.device.set_configuration(1)
            usb.util.claim_interface(self.device, 0)
            self.debug("claimed device")
            

        # read configuration
        self.fw_version = self.get_firmware_version()
        self.fpga_version = self.get_fpga_version()
        self.read_eeprom()
        self.generate_wavelengths()
        print(f"Connected to {self.model} {self.serial_number} with {self.pixels} pixels ({self.wavelengths[0]:.2f}, {self.wavelengths[-1]:.2f}nm) ({self.wavenumbers[0]:.2f}, {self.wavenumbers[-1]:.2f}cm-1)")
        print(f"ARM {self.fw_version}, FPGA {self.fpga_version}")

    def printable(self, buf):
        s = ""
        for c in buf:
            if 31 < c < 127:
                s += chr(c)
            elif c == 0:
                break
            else:
                s += '.'
        return s

    def read_eeprom(self):
        """
        Quick copy-paste from wasatch.EEPROM until such time as we port dependent
        scripts entirely to Wasatch.PY. 

        Basically, Wasatch.PY pre-dated SIGspectrometer.py, yet SIGspectrometer.py
        was created anyway...implying that at least some users didn't want the 
        complexity of Wasatch.PY.

        Which means that Wasatch.PY should be made simpler.

        And it will be. Until that time, this is a useful and easy upgrade to 
        SIGspectrometer.
        """
        self.buffers = [self.get_cmd(0xff, 0x01, page) for page in range(8)]
        self.eeprom = {}
        for k in ["wavelength_coeffs", "linearity_coeffs", "laser_power_coeffs", "degC_to_dac_coeffs", "adc_to_degC_coeffs", "raman_intensity_coeffs"]:
            self.eeprom[k] = []

        # page 0
        self.eeprom["format"]                       = self.unpack((0, 63,  1), "B")
        self.eeprom["model"]                        = self.unpack((0,  0, 16), "s")
        self.eeprom["serial_number"]                = self.unpack((0, 16, 16), "s")
        self.eeprom["has_battery"]                  = self.unpack((0, 37,  1), "?")
        self.eeprom["has_laser"]                    = self.unpack((0, 38,  1), "?")
        self.eeprom["feature_mask"]                 = self.unpack((0, 39,  2), "H")
        self.eeprom["slit_size_um"]                 = self.unpack((0, 41,  2), "H")
        self.eeprom["startup_integration_time_ms"]  = self.unpack((0, 43,  2), "H")
        self.eeprom["startup_temp_degC"]            = self.unpack((0, 45,  2), "h")
        self.eeprom["startup_triggering_scheme"]    = self.unpack((0, 47,  1), "B")
        self.eeprom["detector_gain"]                = self.unpack((0, 48,  4), "f")
        self.eeprom["detector_offset"]              = self.unpack((0, 52,  2), "h")
        self.eeprom["detector_gain_odd"]            = self.unpack((0, 54,  4), "f")
        self.eeprom["detector_offset_odd"]          = self.unpack((0, 58,  2), "h")

        # page 1
        self.eeprom["wavelength_coeffs"]      .append(self.unpack((1,  0,  4), "f"))
        self.eeprom["wavelength_coeffs"]      .append(self.unpack((1,  4,  4), "f"))
        self.eeprom["wavelength_coeffs"]      .append(self.unpack((1,  8,  4), "f"))
        self.eeprom["wavelength_coeffs"]      .append(self.unpack((1, 12,  4), "f"))
        self.eeprom["wavelength_coeffs"]      .append(self.unpack((2, 21,  4), "f"))
        self.eeprom["degC_to_dac_coeffs"]     .append(self.unpack((1, 16,  4), "f"))
        self.eeprom["degC_to_dac_coeffs"]     .append(self.unpack((1, 20,  4), "f"))
        self.eeprom["degC_to_dac_coeffs"]     .append(self.unpack((1, 24,  4), "f"))
        self.eeprom["max_temp_degC"]                = self.unpack((1, 28,  2), "h")
        self.eeprom["min_temp_degC"]                = self.unpack((1, 30,  2), "h")
        self.eeprom["adc_to_degC_coeffs"]     .append(self.unpack((1, 32,  4), "f"))
        self.eeprom["adc_to_degC_coeffs"]     .append(self.unpack((1, 36,  4), "f"))
        self.eeprom["adc_to_degC_coeffs"]     .append(self.unpack((1, 40,  4), "f"))
        self.eeprom["tec_r298"]                     = self.unpack((1, 44,  2), "h")
        self.eeprom["tec_beta"]                     = self.unpack((1, 46,  2), "h")
        self.eeprom["calibration_date"]             = self.unpack((1, 48, 12), "s")
        self.eeprom["calibrated_by"]                = self.unpack((1, 60,  3), "s")

        # page 2
        self.eeprom["pixels"]                       = self.unpack((2, 16,  2), "H")
        self.eeprom["detector"]                     = self.unpack((2,  0, 16), "s")
        self.eeprom["active_pixels_horizontal"]     = self.unpack((2, 16,  2), "H")
        self.eeprom["laser_warmup_sec"]             = self.unpack((2, 18,  1), "B")
        self.eeprom["active_pixels_vertical"]       = self.unpack((2, 19,  2), "H")
        self.eeprom["actual_horizontal"]            = self.unpack((2, 25,  2), "H")
        self.eeprom["roi_horizontal_start"]         = self.unpack((2, 27,  2), "H")
        self.eeprom["roi_horizontal_end"]           = self.unpack((2, 29,  2), "H")
        self.eeprom["roi_vertical_region_1_start"]  = self.unpack((2, 31,  2), "H")
        self.eeprom["roi_vertical_region_1_end"]    = self.unpack((2, 33,  2), "H")
        self.eeprom["roi_vertical_region_2_start"]  = self.unpack((2, 35,  2), "H")
        self.eeprom["roi_vertical_region_2_end"]    = self.unpack((2, 37,  2), "H")
        self.eeprom["roi_vertical_region_3_start"]  = self.unpack((2, 39,  2), "H")
        self.eeprom["roi_vertical_region_3_end"]    = self.unpack((2, 41,  2), "H")
        self.eeprom["linearity_coeffs"]       .append(self.unpack((2, 43,  4), "f"))
        self.eeprom["linearity_coeffs"]       .append(self.unpack((2, 47,  4), "f"))
        self.eeprom["linearity_coeffs"]       .append(self.unpack((2, 51,  4), "f"))
        self.eeprom["linearity_coeffs"]       .append(self.unpack((2, 55,  4), "f"))
        self.eeprom["linearity_coeffs"]       .append(self.unpack((2, 59,  4), "f"))

        # page 3
        self.eeprom["excitation_nm"]                = self.unpack((3, 36,  4), "f")
        self.eeprom["laser_power_coeffs"]     .append(self.unpack((3, 12,  4), "f"))
        self.eeprom["laser_power_coeffs"]     .append(self.unpack((3, 16,  4), "f"))
        self.eeprom["laser_power_coeffs"]     .append(self.unpack((3, 20,  4), "f"))
        self.eeprom["laser_power_coeffs"]     .append(self.unpack((3, 24,  4), "f"))
        self.eeprom["max_laser_power_mW"]           = self.unpack((3, 28,  4), "f")
        self.eeprom["min_laser_power_mW"]           = self.unpack((3, 32,  4), "f")
        self.eeprom["excitation_nm_float"]          = self.unpack((3, 36,  4), "f")
        self.eeprom["min_integration_time_ms"]      = self.unpack((3, 40,  4), "I")
        self.eeprom["max_integration_time_ms"]      = self.unpack((3, 44,  4), "I")
        self.eeprom["avg_resolution"]               = self.unpack((3, 48,  4), "f")
        self.eeprom["laser_watchdog_sec"]           = self.unpack((3, 52,  2), "H")
        self.eeprom["light_source_type"]            = self.unpack((3, 54,  1), "B")

        # page 4
        self.eeprom["user_text"] = self.printable(self.buffers[4][:63])

        # page 5
        bad = set()
        for count in range(15):
            pixel = self.unpack((5, count * 2, 2), "h")
            if pixel != -1:
                bad.add(pixel)
        self.eeprom["bad_pixels"] = list(bad)
        self.eeprom["bad_pixels"].sort()

        self.eeprom["product_configuration"]       = self.unpack((5,  30, 16), "s")
        self.eeprom["subformat"]                   = self.unpack((5,  63,  1), "B")

        # page 6
        if self.eeprom["subformat"] == 1:
            self.eeprom["raman_intensity_calibration_order"] = self.unpack((6, 0, 1), "B")
            for i in range(self.eeprom["raman_intensity_calibration_order"] + 1):
                self.eeprom["raman_intensity_coeffs"].append(self.unpack((6, i * 4 + 1, 4), "f"))

        # expand feature_mask
        self.eeprom["invert_x_axis"]           = 0 != self.eeprom["feature_mask"] & 0x0001
        self.eeprom["bin_2x2"]                 = 0 != self.eeprom["feature_mask"] & 0x0002
        self.eeprom["gen15"]                   = 0 != self.eeprom["feature_mask"] & 0x0004
        self.eeprom["cutoff_filter_installed"] = 0 != self.eeprom["feature_mask"] & 0x0008
        self.eeprom["hardware_even_odd"]       = 0 != self.eeprom["feature_mask"] & 0x0010
        self.eeprom["sig_laser_tec"]           = 0 != self.eeprom["feature_mask"] & 0x0020
        self.eeprom["has_interlock_feedback"]  = 0 != self.eeprom["feature_mask"] & 0x0040
        self.eeprom["has_shutter"]             = 0 != self.eeprom["feature_mask"] & 0x0080

        # normalize any NaN
        for k in ["wavelength_coeffs", "linearity_coeffs", "laser_power_coeffs", "degC_to_dac_coeffs", "adc_to_degC_coeffs", "raman_intensity_coeffs"]:
            for i in range(len(self.eeprom[k])):
                if math.isnan(self.eeprom[k][i]):
                    self.debug(f"normalizing NaN {k}[{i}] to 0") 
                    self.eeprom[k][i] = 0

        ########################################################################
        # legacy members (trying to avoid breaking existing callers)
        ########################################################################

        self.excitation_nm = self.eeprom["excitation_nm_float"]
        for k in ["format", "model", "serial_number", "pixels", "max_laser_power_mW", "min_laser_power_mW"]:
            setattr(self, k, self.eeprom[k])
        for i in range(5):
            setattr(self, f"wavecal_C{i}", self.eeprom["wavelength_coeffs"][i])
        for i in range(4):
            setattr(self, f"laser_power_C{i}", self.eeprom["laser_power_coeffs"][i])

        for k in sorted(self.eeprom):
            self.debug(f"EEPROM: {k} = {self.eeprom[k]}")

    def generate_wavelengths(self):
        self.wavelengths = []
        self.wavenumbers = []
        for i in range(self.pixels):
            wavelength = self.eeprom["wavelength_coeffs"][0]
            wavelength += self.eeprom["wavelength_coeffs"][1] * i
            wavelength += self.eeprom["wavelength_coeffs"][2] * i * i
            wavelength += self.eeprom["wavelength_coeffs"][3] * i * i * i
            wavelength += self.eeprom["wavelength_coeffs"][4] * i * i * i * i
            
            wavenumber = 1e7 / self.eeprom["excitation_nm_float"] - 1e7 / wavelength
            self.wavelengths.append(wavelength)
            self.wavenumbers.append(wavenumber)

    ############################################################################
    # opcodes
    ############################################################################

    def get_firmware_version(self):
        result = self.get_cmd(0xc0)
        if result is not None and len(result) >= 4:
            return "%d.%d.%d.%d" % (result[3], result[2], result[1], result[0]) 

    def get_fpga_version(self):
        s = ""
        result = self.get_cmd(0xb4)
        if result is not None:
            for i in range(len(result)):
                c = result[i]
                if 0x20 <= c < 0x7f:
                    s += chr(c)
        return s

    def set_laser_enable(self, flag=True, laser_warmup_ms=0):
        self.debug(f"setting laserEnable {flag}")
        self.send_cmd(0xbe, 1 if flag else 0)

        if flag and laser_warmup_ms > 0:
            self.debug(f"{datetime.now()} starting laser warmup")
            sleep(laser_warmup_ms / 1000.0)
            self.debug(f"{datetime.now()} finished laser warmup")

    def set_integration_time_ms(self, ms):
        if ms < 1 or ms > 0xffff:
            print("ERROR: integrationTimeMS requires positive uint16")
            return

        self.debug(f"setting integrationTimeMS to {ms}")
        self.send_cmd(0xb2, ms)

    def set_gain_db(self, db):
        db = round(db, 1)
        msb = int(db)
        lsb = int((db - int(db)) * 10)
        raw = (msb << 8) | lsb
        self.debug("setting gainDB 0x%04x (FunkyFloat)" % raw)
        self.send_cmd(0xb7, raw)

    def set_raman_mode(self, flag):
        self.debug(f"setting ramanMode {flag}")
        self.send_cmd(0xff, 0x16, 1 if flag else 0)

    def set_raman_delay_ms(self, ms):
        if ms < 0 or ms > 0xffff:
            print("ERROR: ramanDelay requires uint16")
            return

        self.debug(f"setting ramanDelay {ms} ms")
        self.send_cmd(0xff, 0x20, ms)

    def set_watchdog_sec(self, sec):
        if sec < 0 or sec > 0xffff:
            print("ERROR: laserWatchdog requires uint16")
            return

        self.debug(f"setting laserWatchdog {sec} sec")
        self.send_cmd(0xff, 0x18, sec)

    def get_spectrum(self, integration_time_ms, bin2x2=True):
        timeout_ms = TIMEOUT_MS + integration_time_ms * 2
        self.send_cmd(0xad, 0)
        data = self.device.read(0x82, self.pixels * 2, timeout=timeout_ms)
        if data is None:
            return

        spectrum = []
        for i in range(0, len(data), 2):
            spectrum.append(data[i] | (data[i+1] << 8))

        if len(spectrum) != self.pixels:
            return

        # stomp blank SiG pixels (first 3 and last)
        for i in range(3):
            spectrum[i] = spectrum[3]
        spectrum[-1] = spectrum[-2]

        # 2x2 binning
        if bin2x2:
            for i in range(self.pixels-1):
                spectrum[i] = (spectrum[i] + spectrum[i+1]) / 2.0

        return spectrum

    ## perc is a float (0.0, 100.0) 
    def set_laser_power_perc(self, perc):
        value = float(max(0, min(100, perc)))

        self.set_mod_enable(False)
        if value >= 100:
            return 

        if value < 0.1:
            self.set_laser_enable(False)
            return

        period_us = 1000
        width_us = int(round(1.0 * value * period_us / 100.0, 0)) # note value is in range (0, 100) not (0, 1)
        width_us = max(1, min(width_us, period_us))

        self.set_mod_period_us(period_us)
        self.set_mod_width_us(width_us)
        self.set_mod_enable(True)


    def set_modulation_enable(self, flag):
        self.debug(f"setting laserModulationEnable {flag}")
        self.send_cmd(0xbd, 1 if flag else 0)

    def set_mod_enable(self, flag):
        return self.send_cmd(0xbd, 1 if flag else 0)

    def set_mod_period_us(self, us):
        (lsw, msw, buf) = self.to40bit(us)
        return self.send_cmd(0xc7, lsw, msw, buf)

    def set_mod_width_us(self, us):
        (lsw, msw, buf) = self.to40bit(us)
        return self.send_cmd(0xdb, lsw, msw, buf)



    ############################################################################
    # Utility Methods
    ############################################################################


    def to40bit(self, us):
        lsw = us & 0xffff
        msw = (us >> 16) & 0xffff
        buf = [ (us >> 32) & 0xff, 0 * 7 ]
        return (lsw, msw, buf)

    def debug(self, msg):
        if self.DEBUG:
            print(f"DEBUG: {msg}")

    def send_cmd(self, cmd, value=0, index=0, buf=None):
        if buf is None:
            buf = [0] * 8
        self.debug("ctrl_transfer(0x%02x, 0x%02x, 0x%04x, 0x%04x) >> %s" % (HOST_TO_DEVICE, cmd, value, index, buf))
        self.device.ctrl_transfer(HOST_TO_DEVICE, cmd, value, index, buf, TIMEOUT_MS)

    def get_cmd(self, cmd, value=0, index=0, length=64, lsb_len=None, msb_len=None, label=None):
        self.debug("ctrl_transfer(0x%02x, 0x%02x, 0x%04x, 0x%04x, len %d, timeout %d)" % (DEVICE_TO_HOST, cmd, value, index, length, TIMEOUT_MS))
        result = self.device.ctrl_transfer(DEVICE_TO_HOST, cmd, value, index, length, TIMEOUT_MS)
        self.debug("ctrl_transfer(0x%02x, 0x%02x, 0x%04x, 0x%04x, len %d, timeout %d) << %s" % (DEVICE_TO_HOST, cmd, value, index, length, TIMEOUT_MS, result))

        value = 0
        if msb_len is not None:
            for i in range(msb_len):
                value = value << 8 | result[i]
            return value
        elif lsb_len is not None:
            for i in range(lsb_len):
                value = (result[i] << (8 * i)) | value
            return value
        else:
            return result

    def unpack(self, address, data_type, label=None):
        page       = address[0]
        start_byte = address[1]
        length     = address[2]
        end_byte   = start_byte + length

        buf = self.buffers[page]
        if buf is None or end_byte > len(buf):
            raise("error unpacking EEPROM page %d, offset %d, len %d as %s: buf is %s (label %s)" %
                (page, start_byte, length, data_type, buf, label))

        if data_type == "s":
            result = ""
            for c in buf[start_byte:end_byte]:
                if c == 0:
                    break
                result += chr(c)
        else:
            result = struct.unpack(data_type, buf[start_byte:end_byte])[0]
        return result


# ## Test
# 
# A few test calls

# In[4]:

if __name__ == "__main__":

    import matplotlib.pyplot as plt
    import traceback
    import numpy as np
    import time
    import pandas as pd

    # In[5]:

    spec = SIGspectrometer()

    # In[6]:

    def get_averaged_spectrum(spec, integration_time_ms, 
                              scans_to_average=1, bin2x2=True,
                              inter_spectra_delay_ms=10):
        #spec.set_integration_time_ms(integration_time_ms)
        #time.sleep(inter_spectra_delay_ms/1000.0)
        spectrum = spec.get_spectrum(integration_time_ms, bin2x2)
        time.sleep(inter_spectra_delay_ms / 1000.0)
        if spectrum is None or scans_to_average < 2:
            return spectrum

        

        for i in range(scans_to_average - 1):
            tmp = spec.get_spectrum(integration_time_ms, bin2x2)
            if tmp is None:
                return
            for j in range(len(spectrum)):
                spectrum[j] += tmp[j]
            time.sleep(inter_spectra_delay_ms / 1000.0)

        for i in range(len(spectrum)):
            spectrum[i] = spectrum[i] / scans_to_average

        return spectrum

    # In[53]:

    gain_db = 8.0 # up to 32 analog gain 8.216 example
    laser_warmup_ms = 1000
    integration_time_ms = 1000  #do not go beyond 2500
    min_int_time = 100  #clears off increase if no signal
    scans_to_avg = 1
    inter_spectra_delay_ms = 100
    plot = True

    # ironically, if True, we record no Raman
    spec.set_raman_mode(False)

    # disable laser
    spec.set_laser_enable(False)

    # set integration time
    spec.set_integration_time_ms(integration_time_ms)

    # set gain dB
    spec.set_gain_db(gain_db)

    # perform one throwaway (seems to help SiG)
    dummy=spec.get_spectrum(integration_time_ms=integration_time_ms)
    time.sleep(0.5)
    # take dark
    print("taking dark")
    dark = np.array(get_averaged_spectrum(spec, integration_time_ms, scans_to_avg, 
                                          inter_spectra_delay_ms=inter_spectra_delay_ms))
    time.sleep(0.5)
    # enable laser
    spec.set_laser_power_perc(20)
    spec.set_laser_enable(True, laser_warmup_ms) 
    print("laser on")
    # perform one throwaway (seems to help SiG)
    dummy=spec.get_spectrum(integration_time_ms=integration_time_ms)
    time.sleep(0.5)
    # take measurements
    try:
        # take dark-corrected measurement
        spectrum = np.array(get_averaged_spectrum(spec, integration_time_ms, scans_to_avg,
                                                 inter_spectra_delay_ms=inter_spectra_delay_ms))

        if dark is not None:
            spectrum -= dark

    except:
        print("caught exception reading spectra")
        traceback.print_exc()
    time.sleep(0.5)
    print("measurment done")
    # disable laser
    spec.set_laser_enable(False)
    Wavenumbers=spec.wavenumbers
    pixels=np.arange(len(Wavenumbers))
    data=pd.DataFrame({"Pixel": pixels,"Wavenumber": Wavenumbers,"Signal": spectrum})
    data.to_csv("test.csv")
    
    # graph
    if plot:
        plt.plot(spectrum)
        plt.grid()
        plt.title(f"integration time {integration_time_ms}ms, gain {gain_db}dB, {scans_to_avg} Avg")
        plt.show()
        
        
