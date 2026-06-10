from nplab.measurement.action import *
from nplab.measurement.sweep import H5Sweep
from jisa.devices.source import VSource


class ChangeVoltage(SimpleAction):

    def __init__(self, vsource: VSource, voltage: float):
        super().__init__("Change Voltage (%.02g V)" % voltage, "V = %.02g V" % voltage)
        self.vsource = vsource
        self.voltage = voltage

    def main(self, data = None):
        self.vsource.setVoltage(self.voltage)
        self.vsource.turnOn()

    def finish(self, data = None):
        pass
    
    

class VoltageSweep(H5Sweep[float]):

    voltages = Parameter(name = "Voltages [V]",         defaultValue = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    off      = Parameter(name = "Turn Off Afterwards?", defaultValue = True)

    source = Instrument(name = "Voltage Source", type = VSource, required = True)

    def __init__(self, tag, actions=[]):
        super().__init__("Voltage Sweep", tag, actions)

    def getValues(self):
        return self.voltages
    
    def generate(self, value: float, actions: List[Action]) -> List[Action]:
        return [ChangeVoltage(self.source, value)] + actions
    
    def valueToString(self, value: float):
        return "%.02g V" % value
    
    def finish(self, data: h5py.Group = None):
        if self.off:
            self.source.turnOff()