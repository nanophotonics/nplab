"""
This test file requires hardware and user interaction - it's more or less useless
otherwise.  So, it will not be picked up by the test harness, as all the code
runs in the main block.
"""

import nplab
import nplab.instrument.camera.lumenera as lumenera

def invert_image(rgb):
    return 255-rgb

if __name__ == '__main__':
    device = int(input("Enter the number of the camera to use: "))
    cam = lumenera.LumeneraCamera(device)
    cam.live_view = True
    cam.video_priority = True
    #let's test this new-fangled "get_image" method (should be fresh images)
    images = [cam.get_image() for i in range(10)] #get 10 images
    assert not any([(a==b).all() for a,b in zip(images[:-1],images[1:])]), "some images returned by the camera were identical - that's suspicious"
    print "test passed: acquired 10 images, which were unique, i.e. fresh."    
    cam.show_gui()
    cam.filter_function = invert_image
    cam.show_gui()
    cam.live_view = False
    cam.close()
