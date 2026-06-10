import pyjisa.autoload
import numpy as np
import pyqtgraph

from nplab.measurement.action import *
from h5py import Group

from jisa.devices.meter import VMeter, IMeter, TMeter
from jisa.devices.source import VSource, ISource


class IVCurve(H5Action):

    voltages = Parameter(name = "Voltages [V]", defaultValue = [0.0, 1.0, 2.0, 3.0], type = Type.AUTO)
    delay    = Parameter(name = "Delay Time",   defaultValue = 50,                   type = Type.TIME)
    autoOff  = Parameter(name = "Auto Off?",    defaultValue = True,                 type = Type.AUTO)

    vsource  = Instrument(name = "Voltage Source", type = VSource, required = True)
    imeter   = Instrument(name = "Ammeter",        type = IMeter,  required = True)
    tmeter   = Instrument(name = "Thermometer",    type = TMeter,  required = False)

    def __init__(self, description): 

        super().__init__("IV Curve", description)
        self.sweepData = None


    def main(self, data: Group):
            
        self.vsource.setVoltage(self.voltages[0])
        self.vsource.turnOn()
        self.imeter.turnOn()

        if self.tmeter is not None:
            self.tmeter.turnOn()

        self.sweepData = np.zeros((len(self.voltages), 3))

        for (i, voltage) in enumerate(self.voltages):

            self.infoMessage("Sourcing %.02g V" % voltage)

            self.vsource.setVoltage(voltage)

            self.sleep(self.delay)

            self.sweepData[i, 0] = voltage
            self.sweepData[i, 1] = self.imeter.getCurrent()
            self.sweepData[i, 2] = self.tmeter.getTemperature() if self.tmeter is not None else np.nan


    def finish(self, data: Group):

        if self.sweepData is not None:
            data.create_dataset("Sweep", data=self.sweepData)

        if self.autoOff:

            self.vsource.turnOff()
            self.imeter.turnOff()

            if self.tmeter is not None:
                self.tmeter.turnOff()