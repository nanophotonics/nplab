# -*- coding: utf-8 -*-
"""
Created on Thu Sep 12 15:35:06 2019

@author: np-albali
"""

from nplab.instrument.camera import Camera, CameraControlWidget
from pyvcam.camera import Camera as VCamera
from pyvcam import pvc

from nplab.utils.notified_property import NotifiedProperty
from nplab.utils.thread_utils import locked_action, background_action
from nplab.ui.ui_tools import QuickControlBox
from functools import wraps

try: 
    pvc.uninit_pvcam()
except RuntimeError:
    pass

def disarmer(f):
    '''pauses live view during the calling of these functions
    '''
    @wraps(f)
    def inner_func(self, *args, **kwargs):
        if (l := self.live_view):
            self.live_view = False
        out = f(self, *args, **kwargs)
        
        if l:
            self.live_view = True
        return out
    return inner_func

class PrimeBSI(Camera):
    notified_properties = ('gain',) # properties that are in the gui
    disarmed_properties = ('gain', 'exp_time') # properties that break live view if changed
    def __init__(self):  
        super().__init__()
        pvc.init_pvcam()
        self._camera = next(VCamera.detect_camera())
        if not self._camera.is_open:
            self._camera.open()
        self._populate_properties()

    
    def _populate_properties(self):
        ''' adds all the properties from TLCamera to Kiralux, for easy access.
        
        '''
        def prop_factory(prime_prop,  notified=False, disarmed=False): # to get around late binding
            def fget(self):
                return prime_prop.fget(self._camera)
            def fset(self, val):
                return prime_prop.fset(self._camera, val)
            if disarmed: fset = disarmer(fset)
            if notified: return NotifiedProperty(*map(locked_action, (fget, fset)))
            return property(*map(locked_action, (fget, fset)))
        
        cls = self.__class__    
        for prime_attr in dir(prime_cls := self._camera.__class__):
            if hasattr(prime_prop := getattr(prime_cls, prime_attr), 'fget'): 
                # if it's a property
                if not hasattr(cls, prime_attr):
                    # and it's not in Kiralux already
                    setattr(cls,
                            prime_attr, # add the property
                            prop_factory(prime_prop,
                                         prime_attr in cls.notified_properties,
                                         prime_attr in cls.disarmed_properties))
                                         # if it's in disarmed_properties, 
                                         # decorate the setter and return a 
                                         # notified property appropriately.
    @NotifiedProperty
    def exposure(self): # always in ms
        if self.exp_res_index: # us
            return self.exp_time // 1_000 
        return self.exp_time
    
    @exposure.setter
    def exposure(self, val): # ms
        if self.exp_res_index: # us
            val *= 1_000
        self.exp_time = val
            
    def raw_snapshot(self):
        if self.live_view:
            frame = self._camera.poll_frame()[0]['pixel_data']
        else:
        
           frame = self._camera.get_frame()
     
        return True, frame
        
    
    @Camera.live_view.setter
    def live_view(self, live_view):
        if live_view == self._live_view: return # small redundancy with Camera.live_view
        Camera.live_view.fset(self, live_view)
        if live_view:
            self._camera.start_live()
        else:
            self._camera.finish()
            
    def get_control_widget(self):
        "Get a Qt widget with the camera's controls (but no image display)"
        return PrimeCameraControlWidget(self)
        
class PrimeCameraControlWidget(CameraControlWidget):
    """A control widget for the Thorlabs camera, with extra buttons."""
    def __init__(self, camera):
        super().__init__(camera, auto_connect=False)
        gb = QuickControlBox()
        gb.add_spinbox("exposure", 0, 10_000) 
        gb.add_spinbox("gain", 1, 3) # setting range
        gb.add_button("show_camera_properties_dialog", title="Camera Setup")
        gb.add_button("show_video_format_dialog", title="Video Format")
        self.layout().insertWidget(1, gb) # put the extra settings in the middle
        self.quick_settings_groupbox = gb        
        self.auto_connect_by_name(controlled_object=self.camera)


if __name__ == '__main__':
    p = PrimeBSI()
    p.show_gui(False)
    