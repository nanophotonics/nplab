from builtins import input

import nplab
import nplab.instrument.camera.opencv

if __name__ == '__main__':
    device = int(eval(input("Enter the number of the camera to use: ")))
    cam = nplab.instrument.camera.opencv.OpenCVCamera(device)
    cam.live_view = True
    cam.show_gui()
    cam.live_view = False
    cam.close()
    nplab.close_current_datafile()

