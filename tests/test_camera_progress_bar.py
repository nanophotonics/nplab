import nplab
import nplab.instrument.camera.opencv
from nplab.instrument.camera import CameraControlWidget
from nplab.utils.gui import QtCore, QtGui, show_guis
from nplab.utils.notified_property import DumbNotifiedProperty
from nplab.ui.ui_tools import QuickControlBox
from nplab.experiment.gui import ExperimentWithProgressBar, run_function_modally
import time
import threading

class DumbOpenCVCameraWithTimelapse(nplab.instrument.camera.opencv.OpenCVCamera):
    timelapse_n = DumbNotifiedProperty(5)
    timelapse_dt = DumbNotifiedProperty(1.0)

    def take_timelapse_foreground(self, data_group=None, n=None, dt=None, update_progress=lambda p: p):
        if data_group is None:
            data_group = self.create_data_group("timelapse_%d")
        g = data_group
        for i in range(n):
                update_progress(i)
                time.sleep(dt)
                print("acquiring image {}".format(i))
                g.create_dataset("image_%d", data=self.color_image())

    def take_timelapse(self):
        run_function_modally(self.take_timelapse_foreground,
                             progress_maximum = self.timelapse_n,
                             data_group=self.create_data_group("timelapse_%d"),
                             n=self.timelapse_n,
                             dt=self.timelapse_dt)

    def get_control_widget(self):
        "Get a Qt widget with the camera's controls (but no image display)"
        return TimelapseCameraControlWidget(self)

class OpenCVCameraWithTimelapse(nplab.instrument.camera.opencv.OpenCVCamera):
    timelapse_n = DumbNotifiedProperty(5)
    timelapse_dt = DumbNotifiedProperty(1.0)

    def take_timelapse(self, n=None, dt=None):
        n = self.timelapse_n
        dt = self.timelapse_dt
        print("starting timelapse with n:{}, dt:{}".format(n, dt))
        e = AcquireTimelapse()
        e.camera = self
        e.run_modally(n=n, dt=dt)
        print("function has finished")

    def get_control_widget(self):
        "Get a Qt widget with the camera's controls (but no image display)"
        return TimelapseCameraControlWidget(self)

class AcquireTimelapse(ExperimentWithProgressBar):
    def prepare_to_run(self, n=None, dt=None):
        if n is None:
            raise ValueError("can't run without a number of images!")
        if dt is None:
            raise ValueError("can't run without a valid time interval!")
        self.progress_maximum = n
        self.data_group = self.create_data_group("timelapse_%d")
    def run(self, n=None, dt=None):
        for i in range(n):
            self.wait_or_stop(dt)
            self.data_group.create_dataset("image_%d", data=self.camera.color_image())
            self.update_progress(i+1)

class TimelapseCameraControlWidget(CameraControlWidget):
    """A control widget for the Lumenera camera, with extra buttons."""

    def __init__(self, camera, auto_connect=True):
        super(TimelapseCameraControlWidget, self).__init__(camera, auto_connect=False)
        gb = QuickControlBox()
        gb.add_doublespinbox("exposure")
        gb.add_spinbox("timelapse_n")
        gb.add_doublespinbox("timelapse_dt")
        gb.add_button("take_timelapse", title="Acquire Timelapse")
        self.layout().insertWidget(1, gb)  # put the extra settings in the middle
        self.quick_settings_groupbox = gb

        self.auto_connect_by_name(controlled_object=self.camera, verbose=False)


if __name__ == '__main__':
    device = int(eval(input("Enter the number of the camera to use: ")))
    cam = DumbOpenCVCameraWithTimelapse(device)
    df = nplab.datafile.set_temporary_current_datafile()
    cam.live_view = True
    show_guis([cam, df])
    cam.live_view = False
    cam.close()
    nplab.close_current_datafile()

