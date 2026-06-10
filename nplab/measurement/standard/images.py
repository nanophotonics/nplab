import numpy as np
import pyjisa.autoload

from nplab.measurement.action import *
from jisa.devices.camera import Camera
from jisa.devices.camera.frame import Frame

from h5py import Group

class TakeImages(H5Action):

    count = Parameter(name = "Count", defaultValue = 1, range = (1, None))
    delay = Parameter(name = "Delay", defaultValue = 0, type  = Type.TIME)

    camera = Instrument(name = "Camera", type = Camera, required = True)

    def __init__(self, description: str):
        super().__init__("Take Images", description)


    def main(self, data: Group = None):
        
        if self.camera.isAcquiring():
            self.triggered = False
        else:
            self.triggered = True
            self.camera.startAcquisition()

        self.frames: List[Frame] = []

        for i in range(self.count):
            self.infoMessage("Acquiring image %d" % i)
            self.frames.append(self.camera.getFrame())
            self.sleep(self.delay)
        
        if self.triggered:
            self.camera.stopAcquisition()

        for i, frame in enumerate(self.frames):
            self.infoMessage("Writing image %d" % i)
            self.writeFrame(frame, data, "Frame %d" % i)


    def finish(self, data: Group = None):

        if self.triggered:
            self.camera.stopAcquisition()
            

        

    
