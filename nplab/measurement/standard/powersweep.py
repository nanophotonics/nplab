from nplab.instrument.electronics.power_control import PowerControl
from nplab.measurement.sweep import *
from nplab.measurement.action import *


class ChangePower(SimpleAction):

    power = Parameter(name = "Power [W]", defaultValue = 1e-6, type = Type.SCIENTIFIC)

    controller = Instrument(name = "Power Controller", type = PowerControl)

    def __init__(self, description):
        super().__init__("Change Power", description)

    def main(self, data = None):
        self.controller.power = self.power

    def finish(self, data = None):
        pass



class PowerSweep(H5Sweep[float]):

    powers = Parameter(name = "Powers [W]", defaultValue = [1e-6, 2e-6, 3e-6])
    
    controller = Instrument(name = "Power Controller", type = PowerControl)

    def __init__(self, tag, actions = []):
        super().__init__("Power Sweep", tag, actions)


    def generate(self, value, actions):

        change            = ChangePower(self.valueToString(value))
        change.power      = value
        change.controller = self.controller

        return [change] + actions


    def valueToString(self, value):
        return "%.02g W" % value

    def getValues(self):
        return self.powers
