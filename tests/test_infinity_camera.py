import nplab
import nplab.instrument.camera.lumenera as lumenera

def invert_image(rgb):
    return 255-rgb

if __name__ == '__main__':
    device = int(input("Enter the number of the camera to use: "))
    cam = lumenera.LumeneraCamera(device)
    cam.filter_function = invert_image
    cam.live_view = True
    cam.show_gui()
    cam.live_view = False
    cam.close()
