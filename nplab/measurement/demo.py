import h5py
import pyjisa.autoload
from typing import List, Tuple

from nplab.measurement import Action, Instrument, Parameter, SimpleAction
from nplab.measurement.sweep import H5Sweep

from jisa.devices.translator import Translator

class Move(SimpleAction):

    def __init__(self, xAxis: Translator.Linear, yAxis: Translator.Linear, speed, position): 

        super().__init__("Move to (%.02g m, %.02g m)" % (position[0], position[1]), "%.02g m, %.02g m"  % (position[0], position[1]))

        self.xAxis = xAxis
        self.yAxis = yAxis
        self.speed = speed
        self.position = position


    def main(self, data = None):

        self.xAxis.setMaxSpeed(self.speed)
        self.yAxis.setMaxSpeed(self.speed)

        self.xAxis.setPosition(self.position[0])
        self.yAxis.setPosition(self.position[1])


    def finish(self, data = None):
        self.xAxis.waitUntilStationary()
        self.yAxis.waitUntilStationary()



class PositionSweep(H5Sweep[Tuple[float, float]]):

    def __init__(self, tag, actions = []): super().__init__("Position Sweep", tag, actions)

    positions = Parameter(name = "Positions [m]", defaultValue = [(0.0, 0.0), (0.0, 1.0), (1.0, 0.0), (1.0, 1.0)])
    speed     = Parameter(name = "Speed",         defaultValue = 100.0, range=(0.0, 100.0))

    xAxis = Instrument(name = "X Axis Translator", type = Translator.Linear, required = True)
    yAxis = Instrument(name = "Y Axis Translator", type = Translator.Linear, required = True)

    def generate(self, value: Tuple[float, float], actions: List[Action]):
        return [Move(self.xAxis, self.yAxis, value)] + actions

    def valueToString(self, value: Tuple[float, float]) -> str:
        return "(%.02g m, %.02g m)"

    def getValues(self) -> List[Tuple[float, float]]:
        return self.positions


    