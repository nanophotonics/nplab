# -*- coding: utf-8 -*-
"""
Created on Mon Jul 18 17:59:26 2016

@author: richa
"""

import threading
import time
from builtins import input, range

import nplab
import nplab.instrument.camera.opencv


class CameraConsumer(threading.Thread):
    keep_going = True
    def __init__(self, camera):
        threading.Thread.__init__(self)
        self.camera = camera
    
    def run(self):
        while self.keep_going:
            time.sleep(0.05)
            image = self.camera.raw_image()
            assert len(image.shape)==3

if __name__ == '__main__':
    device = int(eval(input("Enter the number of the camera to use: ")))
    cam = nplab.instrument.camera.opencv.OpenCVCamera(device)
    cam.live_view = True
    consumer_threads = [CameraConsumer(cam) for i in range(3)]
    for t in consumer_threads:
        t.start()
    cam.show_gui()
    for t in consumer_threads:   
        assert t.is_alive(), '{0} died'.format(t)
        t.keep_going = False
        t.join()
    cam.live_view = False
    cam.close()
    nplab.close_current_datafile()

