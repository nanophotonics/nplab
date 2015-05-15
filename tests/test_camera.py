import nplab
import nplab.instrument.camera

if __name__ == '__main__':
    device = int(input("Enter the number of the camera to use"))
    cam = nplab.instrument.camera.Camera(device)
    cam.live_view = True
    cam.configure_traits()
    cam.live_view = False
    cam.cap.release()

