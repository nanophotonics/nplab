from typing import List

from nplab.measurement.action import *
from nplab.measurement.sweep import H5Sweep


class RepeatSweep(H5Sweep[int]):

    repeats = Parameter(name = "Repeats", defaultValue = 5)

    def __init__(self, tag, actions = []):
        super().__init__("Repeat Sweep", tag, actions)

    def getValues(self):
        return list(range(self.repeats))

    def generate(self, value: int, actions: List[Action]) -> List[Action]:
        return list(actions)
    
    def valueToString(self, value: int) -> str:
        return "%d" % value