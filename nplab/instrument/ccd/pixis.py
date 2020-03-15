# -*- coding: utf-8 -*-

from __future__ import print_function
from builtins import range
__author__ = 'alansanders'
import ctypes as ct
import os

pvcam=PVCAM = ct.WinDLL(os.path.dirname(__file__) +"/DLL/Pvcam32.dll")

import nplab.instrument.ccd.pvcam_h as pv
import numpy as np
import time
from nplab.instrument.ccd import CCD
from nplab.instrument.camera import Camera
from nplab.utils.gui import *
from nplab.ui.ui_tools import UiTools
from nplab import inherit_docstring


class PixisError(Exception):
    def __init__(self, msg):
        print(msg)
        i = pvcam.pl_error_code()
        msg = ct.create_string_buffer(20)
        pvcam.pl_error_message(i, msg)
        print('self.pvcam Error:', i, msg)
        pvcam.pl_self.pvcam_uninit()


class Pixis256E(CCD,Camera):
    def __init__(self):
        super(Pixis256E, self).__init__()
        try:
            self.pvcam = PVCAM #ct.windll.pvcam32
        except WindowsError as e:
            print('pvcam not found')
        cam_selection = ct.c_int16()
        # Initialize the self.pvcam library and open the camera #
        self.open_lib()
        self.open_cam(cam_selection)
        self._sequence_set = False
        self._current_frame = None

        self.exposure = 50
        self.timing_mode = 'timed'  # also 'trigger'
        self.cont_clears = True
        self.latest_image = None
        self.latest_raw_image = None
        self.masked_image = None

        #print 'trying to allocate0', (ct.c_int16 * 10)()

    def __del__(self):
        print('deleting')
        if self.cam_open:
            self.close_cam()
        self.close_lib()

    def read_image(self, exposure, timing='timed', mode='kinetics', new=True, end=True, *args,
                   **kwargs):
        """
        Read an image.

        :param exposure: Exposure time
        :param timing: 'timed' or 'trigger'
        :param mode: 'kinetics'
        :param new: If it is the first sequence in a set then new (True) sets up the sequence
        :param end: If it is the last sequence in a set then end (True) finishes the sequence
        :param kwargs: k_size=1

        :return:
        """
        if new:  # only setup the first time in a set of sequences
            # setup sequence
            if mode == 'kinetics':
                k_size = kwargs['k_size'] if 'k_size' in kwargs else 1
                self.setup_kinetics(exposure, k_size, timing)
        self.start_sequence()  # start acquisition
        while not self.check_readout():  # wait for image
            continue
        image = self.readout_image()  # readout
        if end:  # shutdown sequence if it is the last one
            self.finish_sequence()
        return image

    def open_lib(self):
        if not self.pvcam.pl_pvcam_init():
            raise PixisError("failed to init self.pvcam")
        else:
            print('init self.pvcam complete')

    def close_lib(self):
        self.pvcam.pl_pvcam_uninit()
        print("pvcam closed")

    def open_cam(self, cam_selection):
        cam_name = ct.create_string_buffer(20)
        self._handle = ct.c_int16()
        if not self.pvcam.pl_cam_get_name(cam_selection, cam_name):
            raise PixisError("didn't get cam name")
        if not self.pvcam.pl_cam_open(cam_name, ct.byref(self._handle), pv.OPEN_EXCLUSIVE):
            raise PixisError("camera didn't open")
        self.cam_open = True

    def close_cam(self):
        if self._sequence_set:
            self.finish_sequence()
        self.pvcam.pl_cam_close(self._handle)
        self.cam_open = False
        print('cam closed')

    def set_any_param(self, param_id, param_value):
        b_status = ct.c_bool()
        b_param = ct.c_bool()
        param_access = ct.c_uint16()
        param_id = ct.c_uint32(param_id)

        if not isinstance(param_value, ct._SimpleCData):
            raise TypeError("The parameter value must be passed as a ctypes instance, not a python value.")

        b_status = self.pvcam.pl_get_param(self._handle, param_id,
                                      pv.ATTR_AVAIL, ct.cast(ct.byref(b_param), ct.c_void_p))
        if b_param:
            b_status = self.pvcam.pl_get_param(self._handle, param_id,
                                          pv.ATTR_ACCESS,
                                          ct.cast(ct.byref(param_access), ct.c_void_p))

            if param_access.value == pv.ACC_READ_WRITE or param_access.value == pv.ACC_WRITE_ONLY:
                if not self.pvcam.pl_set_param(self._handle, param_id,
                                          ct.cast(ct.byref(param_value), ct.c_void_p)):
                    print("error: param %d (value = %d) did not get set" % (
                    param_id.value, param_value.value))
                    return False
            else:
                print("error: param %d is not writable: %s" % (param_id.value, param_access.value))
                return False
        else:
            print("error: param %d is not available" % param_id.value)
            return False
        return True

    def get_any_param(self, param_id):
        pass

    def set_full_frame(self, region):
        ser_size = ct.c_uint16()
        self.pvcam.pl_get_param(self._handle, pv.PARAM_SER_SIZE,
                           pv.ATTR_DEFAULT, ct.cast(ct.byref(ser_size), ct.c_void_p))
        par_size = ct.c_uint16()
        self.pvcam.pl_get_param(self._handle, pv.PARAM_PAR_SIZE,
                           pv.ATTR_DEFAULT, ct.cast(ct.byref(par_size), ct.c_void_p))
        region.s1, region.s2, region.p1, region.p2 = (0, ser_size.value - 1,
                                                      0, par_size.value - 1)
        region.sbin, region.pbin = (1, 1)

    def setup_kinetics(self, exposure, k_size, timing='trigger'):
        if self._sequence_set:  # uninitialise all previous sequences
            self.finish_sequence()

        params = {
            pv.PARAM_PMODE: (ct.c_uint32(pv.PMODE_KINETICS), 'pmode'),
            pv.PARAM_KIN_WIN_SIZE: (ct.c_uint16(k_size), 'kinetics window size'),
            pv.PARAM_PAR_SHIFT_TIME: (ct.c_uint32(9200), 'parallel shift time'),
            # pv.PARAM_SER_SHIFT_TIME : (ct.c_uint32(9200), 'serial shift time'),
            pv.PARAM_EXP_RES_INDEX: (ct.c_uint16(pv.EXP_RES_ONE_MICROSEC), 'exposure resolution'),
            pv.PARAM_CLEAR_CYCLES: (ct.c_uint16(1), 'clear cycles'),
            pv.PARAM_NUM_OF_STRIPS_PER_CLR: (ct.c_uint16(1), 'number of clear strips'),
            pv.PARAM_SHTR_OPEN_MODE: (ct.c_uint16(pv.OPEN_PRE_SEQUENCE), 'shutter open mode'),
            pv.PARAM_EDGE_TRIGGER: (ct.c_uint32(pv.EDGE_TRIG_POS), 'edge trigger'),
            pv.PARAM_GAIN_INDEX: (ct.c_uint16(3), 'gain index'),
            # pv.PARAM_CONT_CLEARS : (ct.c_bool(True), 'continuous clears 1'),
        }
        for p in params:
            status = self.set_any_param(p, params[p][0])
            if not status: print('problem with %s' % params[p][1])

        read_params = [
            pv.PARAM_PIX_TIME,
        ]
        for p in read_params:
            self.get_any_param(p)

        if not self.pvcam.pl_exp_init_seq():
            raise PixisError("init_seq failed!")

        exp_time = ct.c_uint32(exposure)
        size = ct.c_uint32()
        region = pv.rgn_type()
        self.set_full_frame(region)

        if timing == 'trigger':
            timing_mode = pv.TRIGGER_FIRST_MODE
        elif timing == 'timed':
            timing_mode = pv.TIMED_MODE
        if self.pvcam.pl_exp_setup_seq(self._handle, 1, 1, ct.byref(region),
                                  timing_mode, exp_time, ct.byref(size)):
            # print "frame size = %d" % size.value
            pass
        else:
            raise PixisError("experiment setup failed!")
        self._sequence_set = True
        self.exposure = exposure
        self.size = size
        self.timing = timing

        if timing == 'trigger':
            # status = self.set_any_param(pv.PARAM_CLEAR_MODE, ct.c_uint16(pv.CLEAR_PRE_SEQUENCE))
            # if not status: print 'problem with clear mode'
            status = self.set_any_param(pv.PARAM_CONT_CLEARS, ct.c_bool(self.cont_clears))
            if not status:
                print('problem with continuous cleans 2')
            # status = self.set_any_param(pv.PARAM_CLN_WHILE_EXPO, ct.c_uint16(1))
            # if not status: print 'problem with clear while exposing'

            # frame = (ct.c_uint16 * (self.size.value//2))()
            # self.pvcam.pl_exp_start_seq(self._handle, frame)
            # self._current_frame = frame

    def start_sequence(self):
        """
        Create a frame and start the kinetics exposure sequence. Call this method
        after setting up the trigger and then wait until check_kinetics confirms
        readout.
        """
        frame = (ct.c_uint16 * (self.size.value // 2))()
        self.pvcam.pl_exp_start_seq(self._handle, frame)
        self._current_frame = frame

    def check_readout(self):
        """
        Poll the readout status and return if the readout is complete or if it
        fails.
        """
        status = ct.c_int16()
        self.pvcam.pl_exp_check_status(self._handle, ct.byref(status),
                                  ct.byref(ct.c_int32()))
        if status.value == pv.READOUT_FAILED:
            raise PixisError("Data collection error")
        elif status.value == pv.READOUT_COMPLETE:
            return True
        else:
            return False

    def readout_image(self):
        """If the readout is complete a valid frame is returned."""
        return np.array(list(self._current_frame)).reshape((256, 1024))

    def finish_sequence(self):
        self.pvcam.pl_exp_finish_seq(self._handle, self._current_frame, 0)
        self.pvcam.pl_exp_uninit_seq()
        self._sequence_set = False

    metadata_property_names = ('exposure',)

    def read_background(self):
        """Acquire a new spectrum and use it as a background measurement."""
        self.background = self.read_image(self.exposure, self.timing, self.mode,
                                          new=True, end=True)
        self.update_config('background', self.background)

    def read_reference(self):
        """Acquire a new spectrum and use it as a reference."""
        self.reference = self.read_image(self.exposure, self.timing, self.mode,
                                         new=True, end=True)
        self.update_config('reference', self.reference)
    
    def raw_snapshot(self):
        try:
            image = self.read_image(self.exposure, timing='timed', mode='kinetics', new=False, end= True, k_size=1)
            return 1, image
        except Exception as e:
            self._logger.warn("Couldn't Capture because %s" % e)


@inherit_docstring(Pixis256E)
class Pixis256EQt(Pixis256E, QtCore.QObject):
    """Pixis256E subclass with Qt signals for GUI interaction."""

    image_taken = QtCore.Signal(np.ndarray)

    @inherit_docstring(Pixis256E.__init__)
    def __init__(self):
        super(Pixis256EQt, self).__init__()

    @inherit_docstring(Pixis256E.read_image)
    def read_image(self, exposure, timing='timed', mode='kinetics', new=True, end=True, *args,
                   **kwargs):
        image = super(Pixis256EQt, self).read_image(exposure, timing='timed', mode='kinetics',
                                                    new=True, end=True, *args, **kwargs)
        self.image_taken.emit(image)
        return image


class Pixis256EUI(QtWidgets.QWidget, UiTools):
    def __init__(self, pixis):
        if not isinstance(pixis, Pixis256EQt):
            raise TypeError('pixis is not an instance of Pixis256EQt')
        super(Pixis256EUI, self).__init__()
        self.pixis = pixis

        # self.exposure.setValidator(QtWidgets.QIntValidator())
        # self.exposure.textChanged.connect(self.check_state)
        # self.exposure.textChanged.connect(self.on_text_change)
        # self.mode.activated.connect(self.on_activated)
        # self.timing.activated.connect(self.on_activated)
        # self.cont_clears.stateChanged.connect(self.on_state_change)
        # self.take_image_button.clicked.connect(self.on_click)
        # self.take_bkgd_button.clicked.connect(self.on_click)
        # self.clear_bkgd_button.clicked.connect(self.on_click)
        # self.take_ref_button.clicked.connect(self.on_click)
        # self.clear_ref_button.clicked.connect(self.on_click)

        # self.pixis.image_taken.connect()

    def on_text_change(self, text):
        sender = super(Pixis256EUI, self).on_text_change(text)
        if sender == False:
            return
        elif sender == self.exposure:
            self.pixis.exposure = float(sender)

    def on_click(self):
        sender = self.sender()
        if sender == self.take_image_button:
            self.pixis.read_image(self.pixis.exposure, self.pixis.timing, self.pixis.mode,
                                  new=True, end=True)
        elif sender == self.take_bkgd_button:
            self.pixis.read_background()
        elif sender == self.clear_bkgd_button:
            self.pixis.clear_background()
        elif sender == self.take_ref_button:
            self.pixis.read_reference()
        elif sender == self.clear_ref_button:
            self.pixis.clear_reference()

    def on_activated(self, item):
        sender = self.sender()
        if sender == self.mode:
            self.pixis.mode = item
        elif sender == self.timing:
            self.pixis.timing = item

    def on_state_change(self, state):
        sender = self.sender()
        if sender == self.cont_clears:
            if state == QtCore.Qt.Checked:
                self.pixis.cont_clears = True
            elif state == QtCore.Qt.Unchecked:
                self.pixis.cont_clears = False


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    p = Pixis256EQt()
    p.exposure = 1

    def test():
        p.setup_kinetics(p.exposure, 1)
        print(p.check_readout())
        imgs = []
        print('ready')
        shots = 3
        for i in range(shots):
            print('shot {0}'.format(i+1))
            p.start_sequence()
            time.sleep(0.1)
            while not (p.check_readout()): continue
            print("triggered")
            img = p.readout_image()
            imgs.append(img)
        p.finish_sequence()
        time.sleep(0.1)
        img = p.read_image(p.exposure, timing='timed', mode='kinetics', k_size=1)
        imgs.append(img)
        #p.close_cam()
        print('finished')

        print('plotting data')
        fig, axes = plt.subplots(shots+1, sharex=True)
        for i, ax in enumerate(axes):
            img = ax.imshow(imgs[i])
        print('done')
        plt.show()

    print("one")
#    app = get_qt_app()
#    ui = Pixis256EUI(pixis=p)
#    print "two"

#    ui.show()
 #   sys.exit(app.exec_())

    # p.read_image(p.exposure, timing='timed', mode='kinetics', new=True, end= False, k_size=1)
    # img = p.read_image(p.exposure, timing='timed', mode='kinetics', new=False, end= True, k_size=1)
    # plt.imshow(img)
    # plt.show()
