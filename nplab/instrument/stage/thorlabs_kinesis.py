# -*- coding: utf-8 -*-
# Generalised from https://github.com/trautsned/thorlabs_kenesis_python/blob/master/lts300_xyz_sweep.py
# So far only tested on PRM1-Z8 actuators
from nplab.instrument.stage import Stage
import clr
import sys
sys.path.append(r'C:\Program Files\Thorlabs\Kinesis')

from System import Decimal  # System is part of clr
clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
import Thorlabs.MotionControl.DeviceManagerCLI as DeviceManagerCLI

DeviceManagerCLI.DeviceManagerCLI.BuildDeviceList()
# list the serial numbers of the Kinesis-recognised devices connected
# devices = DeviceManagerCLI.DeviceManagerCLI.GetDeviceList()


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
