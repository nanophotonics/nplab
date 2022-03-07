
r'''
You'll need the drivers for ximc, from https://files.xisupport.com/Software.en.html. - libximc-2.13.3-all.tar.gz

Extract this and place the ximc folder (C:\Users\Hera\Downloads\XIMC_Software_package-2022.02.15-win32_win64\libximc-2.13.3-all.tar\libximc-2.13.3-all\ximc-2.13.3\ximc)
in C:\Program Files.


Full path to the wrapper should be: C:\Program Files\ximc\crossplatform\wrappers\python\pyximc.py

'''

from ctypes import byref, c_uint, POINTER, c_int
import time
import os
import sys
import platform
from pathlib import Path

from nplab.instrument import Instrument
from nplab.ui.ui_tools import QuickControlBox
from nplab.utils.notified_property import NotifiedProperty
# Dependences


ximc_dir = Path(r'C:\Program Files\ximc')
ximc_package_dir = ximc_dir / "crossplatform" / "wrappers" / "python"
sys.path.append(str(ximc_package_dir.resolve()))

if platform.system() == "Windows":
    arch_dir = "win64" if "64" in platform.architecture()[0] else "win32"
    libdir = os.path.join(ximc_dir, arch_dir)
    if sys.version_info >= (3, 11):
        os.add_dll_directory(libdir)
    else:
     
        os.environ["Path"] = libdir + ";" + os.environ["Path"]


import pyximc as xi

def test_info(lib, device_id):
    print("\nGet device info")
    x_device_information = xi.device_information_t()
    result = xi.lib.get_device_information(
        device_id, byref(x_device_information))
    print("Result: " + repr(result))
    if result == xi.Result.Ok:
        print("Device information:")
        print(" Manufacturer: " +
              repr(xi.string_at(x_device_information.Manufacturer).decode()))
        print(" ManufacturerId: " +
              repr(xi.string_at(x_device_information.ManufacturerId).decode()))
        print(" ProductDescription: " +
              repr(xi.string_at(x_device_information.ProductDescription).decode()))
        print(" Major: " + repr(x_device_information.Major))
        print(" Minor: " + repr(x_device_information.Minor))
        print(" Release: " + repr(x_device_information.Release))


def test_status(lib, device_id):
    print("\nGet status")
    x_status = xi.status_t()
    result = xi.lib.get_status(device_id, byref(x_status))
    print("Result: " + repr(result))
    if result == xi.Result.Ok:
        print("Status.Ipwr: " + repr(x_status.Ipwr))
        print("Status.Upwr: " + repr(x_status.Upwr))
        print("Status.Iusb: " + repr(x_status.Iusb))
        print("Status.Flags: " + repr(hex(x_status.Flags)))


def test_get_position(lib, device_id):
    print("\nRead position")
    x_pos = xi.get_position_t()
    result = xi.lib.get_position(device_id, byref(x_pos))
    print("Result: " + repr(result))
    if result == xi.Result.Ok:
        print("Position: {0} steps, {1} microsteps".format(
            x_pos.Position, x_pos.uPosition))
    return x_pos.Position, x_pos.uPosition


def test_left(lib, device_id):
    print("\nMoving left")
    result = lib.command_left(device_id)
    print("Result: " + repr(result))


def test_move(lib, device_id, distance, udistance):
    print("\nGoing to {0} steps, {1} microsteps".format(distance, udistance))
    result = lib.command_move(device_id, distance, udistance)
    print("Result: " + repr(result))


def test_wait_for_stop(lib, device_id, interval):
    print("\nWaiting for stop")
    result = lib.command_wait_for_stop(device_id, interval)
    print("Result: " + repr(result))


def test_serial(lib, device_id):
    print("\nReading serial")
    x_serial = c_uint()
    result = lib.get_serial_number(device_id, byref(x_serial))
    if result == xi.Result.Ok:
        print("Serial: " + repr(x_serial.value))


def test_get_speed(lib, device_id):
    print("\nGet speed")
    # Create move settings structure
    mvst = xi.move_settings_t()
    # Get current move settings from controller
    result = lib.get_move_settings(device_id, byref(mvst))
    # Print command return status. It will be 0 if all is OK
    print("Read command result: " + repr(result))

    return mvst.Speed


def test_set_speed(lib, device_id, speed):
    print("\nSet speed")
    # Create move settings structure
    mvst = xi.move_settings_t()
    # Get current move settings from controller
    result = lib.get_move_settings(device_id, byref(mvst))
    # Print command return status. It will be 0 if all is OK
    print("Read command result: " + repr(result))
    print("The speed was equal to {0}. We will change it to {1}".format(
        mvst.Speed, speed))
    # Change current speed
    mvst.Speed = int(speed)
    # Write new move settings to controller
    result = lib.set_move_settings(device_id, byref(mvst))
    # Print command return status. It will be 0 if all is OK
    print("Write command result: " + repr(result))


def test_set_microstep_mode_256(lib, device_id):
    print("\nSet microstep mode to 256")
    # Create engine settings structure
    eng = xi.engine_settings_t()
    # Get current engine settings from controller
    result = lib.get_engine_settings(device_id, byref(eng))
    # Print command return status. It will be 0 if all is OK
    print("Read command result: " + repr(result))
    # Change MicrostepMode parameter to MICROSTEP_MODE_FRAC_256
    # (use MICROSTEP_MODE_FRAC_128, MICROSTEP_MODE_FRAC_64 ... for other microstep modes)
    eng.MicrostepMode = xi.MicrostepMode.MICROSTEP_MODE_FRAC_256
    # Write new engine settings to controller
    result = lib.set_engine_settings(device_id, byref(eng))
    # Print command return status. It will be 0 if all is OK
    print("Write command result: " + repr(result))



sbuf = xi.create_string_buffer(64)
xi.lib.ximc_version(sbuf)

result = xi.lib.set_bindy_key(os.path.join(
    ximc_dir, "win32", "keyfile.sqlite").encode("utf-8"))
if result != xi.Result.Ok:
    xi.lib.set_bindy_key("keyfile.sqlite".encode("utf-8"))

probe_flags = xi.EnumerateFlags.ENUMERATE_PROBE + \
    xi.EnumerateFlags.ENUMERATE_NETWORK
enum_hints = b"addr="
devenum = xi.lib.enumerate_devices(probe_flags, enum_hints)
dev_count = xi.lib.get_device_count(devenum)
controller_name = xi.controller_name_t()
for dev_ind in range(0, dev_count):
    enum_name = xi.lib.get_device_name(devenum, dev_ind)
    result = xi.lib.get_enumerate_device_controller_name(
        devenum, dev_ind, byref(controller_name))


open_name = None
if len(sys.argv) > 1:
    open_name = sys.argv[1]
elif dev_count > 0:
    open_name = xi.lib.get_device_name(devenum, 0)
else:
    raise Exception('Port closed')



if type(open_name) is str:
    open_name = open_name.encode()


class Iris(Instrument):
    def __init__(self):
        super().__init__()
        self.device_id = xi.lib.open_device(open_name)
        eng = xi.engine_settings_t()
        xi.lib.get_engine_settings(self.device_id, byref(eng))
        eng.MicrostepMode = xi.MicrostepMode.MICROSTEP_MODE_FRAC_256
        xi.lib.set_engine_settings(self.device_id, byref(eng))
        self.set_speed(500_000)
        xi.lib.command_homezero(self.device_id)
        self._wait()
        self.close_fully()
        self.open_fully()
        
    def _wait(self):
        xi.lib.command_wait_for_stop(self.device_id, 100)  
        # 100 ms refresh rate
    
    def get_range(self):
        sst  = xi.stage_settings_t()
        xi.lib.get_stage_settings(ir.device_id, byref(sst))
        rang = sst.TravelRange
        return rang
    
        
    def _close_fully(self):
        xi.lib.command_left(self.device_id)
        
    def _open_fully(self):
        xi.lib.command_right(self.device_id)
        
    def close_fully(self):
        self._close_fully()
        self._wait()
        self._close_pos = self.get_position() # open, closed    
        self._close_fraction = 1
        
    def open_fully(self):
        self._open_fully()
        self._wait()
        self._close_fraction = 0
        self._open_pos = self.get_position()
        
    
    def close_partially(self, frac):
        try:
            self.set_position(*(int((c - o)*frac + o) for c, o in zip(self._close_pos, self._open_pos)))
            self._close_fraction = frac
        except AttributeError:
            self.log('must close fully before partially to calibrate range', level='warn')
    def open_partially(self, frac):
        self.close_partially(1-frac)
        
    def get_close_fraction(self):
        return self._close_fraction
    
    def get_open_fraction(self):
        return 1 - self.get_close_fraction()
    
    open_fraction = NotifiedProperty(get_open_fraction, open_partially)
        
    
    def set_position(self, pos, upos):
        xi.lib.command_move(self.device_id, pos, upos)
        self._wait()

    def get_position(self):
        x_pos = xi.get_position_t()
        xi.lib.get_position(self.device_id, byref(x_pos))
        return x_pos.Position, x_pos.uPosition
    position = property(get_position, set_position)
    
    def set_speed(self, speed):
        mvst = xi.move_settings_t()
        mvst.Speed = int(speed)
        xi.lib.set_move_settings(self.device_id, byref(mvst))

    def get_speed(self):
        mvst = xi.move_settings_t()
        xi.lib.get_move_settings(self.device_id, byref(mvst))
        return mvst.Speed
    
    def get_control_settings(self):
        cst = xi.control_settings_t()
        xi.lib.get_control_settings(self.device_id, cst)
        return cst

    def _test(self):
        test_info(xi.lib, self.device_id)
        test_status(xi.lib, self.device_id)
        test_set_microstep_mode_256(xi.lib, self.device_id)
        startpos, ustartpos = test_get_position(xi.lib, self.device_id)
        # first move
        test_left(xi.lib, self.device_id)
        time.sleep(3)
        test_get_position(xi.lib, self.device_id)
        # second move
        current_speed = test_get_speed(xi.lib, self.device_id)
        test_set_speed(xi.lib, self.device_id, current_speed * 2)
        test_move(xi.lib, self.device_id, startpos, ustartpos)
        test_wait_for_stop(xi.lib, self.device_id, 100)
        test_status(xi.lib, self.device_id)
        test_serial(xi.lib, self.device_id)

    def __del__(self):
        self._close()

    def _close(self):
        xi.lib.close_device(byref(xi.cast(self.device_id, POINTER(c_int))))
        
    def get_qt_ui(self):
        return IrisGui(self)
    
    
class IrisGui(QuickControlBox):
    def __init__(self, iris):
        self.iris = iris
        super().__init__()
        self.add_doublespinbox('open_fraction')
        self.auto_connect_by_name(controlled_object=self.iris)
        
        
if __name__ == '__main__':
    ir = Iris()
    # ir.close_fully()
    # ir.close_partially(0.5)
    ir.show_gui(False)