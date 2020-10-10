# -*- coding: utf-8 -*-
# Generalised from https://github.com/trautsned/thorlabs_kenesis_python/blob/master/lts300_xyz_sweep.py
# So far only tested on PRM1-Z8 actuators
"""
This is a Python 3 wrapper for the Thorlabs BPC203 Benchtop Piezo controller.

It relies on the Thorlabs Kinesis API (so you should copy in, or add to your
Python path, the Kinesis DLLs).  The easiest way to copy the right DLLs is
to use the "DLL copying utility" which is probably located in 
c:/Program Files/Thorlabs/Kinesis

Currently, we append this directory to the system path - that is a nasty hack
but it works for now.

It also uses the excellent ``pythonnet`` package to get access to the .NET API.
This is by far the least painful way to get Kinesis to work nicely as it 
avoids the low-level faffing about.
"""
from __future__ import print_function
from builtins import zip
from builtins import range
from nplab.instrument.stage import Stage
import clr
import sys
import time

clr.AddReference("System")
from System import Decimal  # System is part of the .NET framework, which clr provides

try:
    sys.path.append(r'C:\Program Files\Thorlabs\Kinesis')
    clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
    import Thorlabs.MotionControl.DeviceManagerCLI as DeviceManagerCLI
except Exception as e:
    print("Error importing the ThorLabs Kinesis .NET API.  It may not be in your PATH. "
          "Check you have installed the correct version (64/32 bit) of Kinesis, and that "
          "it is located in C:\\Program Files\\Thorlabs\\Kinesis.")

DeviceManagerCLI.DeviceManagerCLI.BuildDeviceList()
# list the serial numbers of the Kinesis-recognised devices connected
# devices = DeviceManagerCLI.DeviceManagerCLI.GetDeviceList()

def list_devices():
    """Return a list of Kinesis serial numbers"""
    DeviceManagerCLI.DeviceManagerCLI.BuildDeviceList()
    return DeviceManagerCLI.DeviceManagerCLI.GetDeviceList()

"""KCUBE"""
clr.AddReference("Thorlabs.MotionControl.KCube.DCServoCLI")
import Thorlabs.MotionControl.KCube.DCServoCLI as KcubeDCServoCLI


class KCube(Stage):
    axis_names = ('theta', )

    def __init__(self, serial_number):
        super(Stage, self).__init__()

        DeviceManagerCLI.DeviceManagerCLI.BuildDeviceList()
        self.device = KcubeDCServoCLI.KCubeDCServo.CreateKCubeDCServo(serial_number)
        self.device.Connect(serial_number)
        self.device.WaitForSettingsInitialized(5000)
        self.device.EnableDevice()

    def move(self, pos, axis=None, relative=False):
        self.device.MoveTo(Decimal(pos), 60000)

    def get_position(self, axis=None):
        return float(self.device.Position.ToString())


"""TCUBE"""
clr.AddReference("Thorlabs.MotionControl.TCube.DCServoCLI")
import Thorlabs.MotionControl.TCube.DCServoCLI as TcubeDCServoCLI


class TCube(Stage):
    axis_names = ('theta', )

    def __init__(self, serial_number):
        super(Stage, self).__init__()

        DeviceManagerCLI.DeviceManagerCLI.BuildDeviceList()
        self.device = TcubeDCServoCLI.TCubeDCServo.CreateTCubeDCServo(serial_number)
        self.device.Connect(serial_number)
        self.device.WaitForSettingsInitialized(5000)
        self.device.EnableDevice()

    def move(self, pos, axis=None, relative=False):
        self.device.MoveTo(Decimal(pos), 60000)

    def get_position(self, axis=None):
        return float(self.device.Position.ToString())

"""Benchtop Piezo

Currently tested with BCP203 (may not be correct)
"""
clr.AddReference("Thorlabs.MotionControl.Benchtop.PiezoCLI")
import Thorlabs.MotionControl.Benchtop.PiezoCLI as BenchtopPiezoCLI

class BenchtopPiezo(Stage):
    axis_names = None
    connected = False
    channels = []
    device = None

    def __init__(self, serial_number):
        self._serial_number = serial_number
        DeviceManagerCLI.DeviceManagerCLI.BuildDeviceList()
        self.device = BenchtopPiezoCLI.BenchtopPiezo.CreateBenchtopPiezo(serial_number)
        self.connect()
        super(Stage, self).__init__()
    
    def connect(self):
        """Initialise communications, populate channel list, etc."""
        self.device.Connect(self._serial_number)
        self.connected = True
        assert len(self.channels) == 0, "Error connecting: we've already initialised channels!"
        for i in range(self.device.ChannelCount):
            chan = self.device.GetChannel(i+1) # Kinesis channels are one-indexed
            chan.WaitForSettingsInitialized(5000)
            chan.StartPolling(250) # getting the voltage only works if you poll!
            time.sleep(0.5) # ThorLabs have this in their example...
            chan.EnableDevice()
            # I don't know if the lines below are necessary or not - but removing them
            # may or may not work...
            time.sleep(0.5)
            config = chan.GetPiezoConfiguration(chan.DeviceID)
            info = chan.GetDeviceInfo()
            max_v = Decimal.ToDouble(chan.GetMaxOutputVoltage())
            self.channels.append(chan)
        self.axis_names = tuple("channel_{}".format(i) for i in range(self.device.ChannelCount))

    def close(self):
        """Shut down communications"""
        if not self.connected:
            print(f"Not closing piezo device {self._serial_number}, it's not open!")
            return
        for chan in self.channels:
            chan.StopPolling()
        self.channels = []
        self.device.Disconnect(True)

    def __del__(self):
        try:
            if self.connected:
                self.close()
        except:
            print(f"Error closing communications on deletion of device {self._serial_number}")

    def set_output_voltages(self, voltages):
        """Set the output voltage"""
        assert len(voltages) == len(self.channels), "You must specify exactly one voltage per channel"
        for chan, v in zip (self.channels, voltages):
            chan.SetOutputVoltage(Decimal(v))
    
    def get_output_voltages(self):
        """Retrieve the output voltages as a list of floating-point numbers"""
        return [Decimal.ToDouble(chan.GetOutputVoltage()) for chan in self.channels]

    output_voltages = property(get_output_voltages, set_output_voltages)

    def move(self, pos, axis=None, relative=False):
        """Move the piezo stage.  For now, this is done in volts."""
        if axis is None:
            for p, ax in zip(pos, self.axis_names):
                self.move_axis(p, ax, relative=relative)
        else:
            self.move_axis(pos, axis, relative=relative)
    
    def move_axis(self, pos, axis, relative=False):
        """Move one axis (currently in volts)"""
        chan = self.select_axis(self.channels, axis)
        if relative:
            # emulate relative moves
            pos += Decimal.ToDouble(chan.GetOutputVoltage())
        chan.SetOutputVoltage(Decimal(pos))

    def get_position(self, axis=None):
        if axis is None:
            return [self.get_position(ax) for ax in self.axis_names]
        else:
            chan = self.select_axis(self.channels, axis)
            return Decimal.ToDouble(chan.GetOutputVoltage())

