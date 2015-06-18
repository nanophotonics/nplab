import nplab
import nplab.instrument.camera.lumenera as lumenera

if __name__ == '__main__':
    device = int(input("Enter the number of the camera to use: "))
    cam = lumenera.LumeneraCamera(device)
    cam.live_view = True
    cam.configure_traits()
    cam.live_view = False
    cam.close()
