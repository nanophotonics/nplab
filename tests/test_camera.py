import nplab
import nplab.instrument.camera.opencv

if __name__ == '__main__':
    device = int(input("Enter the number of the camera to use: "))
    cam = nplab.instrument.camera.opencv.OpenCVCamera(device)
    cam.live_view = True
    cam.show_gui()
    cam.live_view = False
    cam.close()
    nplab.current_datafile(create_if_none=False).close()

