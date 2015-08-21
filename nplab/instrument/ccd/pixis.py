__author__ = 'alansanders'

import ctypes as ct

pvcam = ct.windll.pvcam32
import pvcam_h as pv
import numpy as np
import numpy.ma as ma
from time import sleep
import threading
from nplab.instrument import Instrument


def print_pv_error():
    i = pvcam.pl_error_code()
    msg = ct.create_string_buffer(20)
    pvcam.pl_error_message(i, msg)
    print 'PVCam Error:', i, msg


class PixisError(Exception):
    def __init__(self, msg):
        print msg
        print_pv_error()
        pvcam.pl_pvcam_uninit()


class Pixis256E(Instrument):
    def __init__(self):
        super(Pixis256E, self).__init__()
        cam_selection = ct.c_int16()
        # Initialize the PVCam Library and Open the Camera #
        self.open_lib()
        print 'trying to allocate0', (ct.c_int * 10)()
        self.open_cam(cam_selection)
        self._comms_lock = threading.RLock()
        self._sequence_set = False
        self._current_frame = None

        self.exposure = 50
        self.timing_mode = 'timed'  # also 'trigger'
        self.cont_clears = True
        self.latest_image = None
        self.latest_raw_image = None
        self.masked_image = None

    def __del__(self):
        if self.cam_open:
            self.close_cam()
        self.close_lib()

    def open_lib(self):
        if not pvcam.pl_pvcam_init():
            raise PixisError("failed to init pvcam")
        else:
            print 'init pvcam complete'

    def close_lib(self):
        pvcam.pl_pvcam_uninit()
        print "Pixis closed"

    def open_cam(self, cam_selection):
        cam_name = ct.create_string_buffer(20)
        self._handle = ct.c_int16()
        if not pvcam.pl_cam_get_name(cam_selection, cam_name):
            raise PixisError("didn't get cam name")
        # print 'trying to allocate1', (ct.c_int * 10)()
        if not pvcam.pl_cam_open(cam_name, ct.byref(self._handle), pv.OPEN_EXCLUSIVE):
            raise PixisError("camera didn't open")
        self.cam_open = True

    def close_cam(self):
        if self._sequence_set: self.finish_kinetics()
        pvcam.pl_cam_close(self._handle)
        self.cam_open = False

    def set_any_param(self, param_id, param_value):
        b_status = ct.c_bool()
        b_param = ct.c_bool()
        param_access = ct.c_uint16()
        param_id = ct.c_uint32(param_id)

        # if not isinstance(param_value, ctypes._SimpleCData):
        #    if param_id in [4,5,6,76]:
        #        param_value = ctypes.c_int16(param_value)

        assert isinstance(param_value,
                          ct._SimpleCData), "The parameter value must be passed as a ctypes instance, not a python value."

        b_status = pvcam.pl_get_param(self._handle, param_id,
                                      pv.ATTR_AVAIL, ct.cast(ct.byref(b_param), ct.c_void_p))
        if b_param:
            b_status = pvcam.pl_get_param(self._handle, param_id,
                                          pv.ATTR_ACCESS,
                                          ct.cast(ct.byref(param_access), ct.c_void_p))

            if param_access.value == pv.ACC_READ_WRITE or param_access.value == pv.ACC_WRITE_ONLY:
                if not pvcam.pl_set_param(self._handle, param_id,
                                          ct.cast(ct.byref(param_value), ct.c_void_p)):
                    print "error: param %d (value = %d) did not get set" % (
                    param_id.value, param_value.value)
                    return False
            else:
                print "error: param %d is not writable: %s" % (param_id.value, param_access.value)
                return False
        else:
            print "error: param %d is not available" % param_id.value
            return False
        return True

    def get_any_param(self, param_id):
        pass

    def set_full_frame(self, region):
        ser_size = ct.c_uint16()
        pvcam.pl_get_param(self._handle, pv.PARAM_SER_SIZE,
                           pv.ATTR_DEFAULT, ct.cast(ct.byref(ser_size), ct.c_void_p))
        par_size = ct.c_uint16()
        pvcam.pl_get_param(self._handle, pv.PARAM_PAR_SIZE,
                           pv.ATTR_DEFAULT, ct.cast(ct.byref(par_size), ct.c_void_p))
        region.s1, region.s2, region.p1, region.p2 = (0, ser_size.value - 1,
                                                      0, par_size.value - 1)
        region.sbin, region.pbin = (1, 1)

    def setup_kinetics(self, exposure, k_size, timing='trigger'):
        if self._sequence_set:
            self.finish_kinetics()

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
            if not status: print 'problem with %s' % params[p][1]

        read_params = [
            pv.PARAM_PIX_TIME,
        ]
        for p in read_params:
            self.get_any_param(p)

        if not pvcam.pl_exp_init_seq():
            raise PixisError("init_seq failed!")

        exp_time = ct.c_uint32(exposure)
        size = ct.c_uint32()
        region = pv.rgn_type()
        self.set_full_frame(region)

        if timing == 'trigger':
            timing_mode = pv.TRIGGER_FIRST_MODE
        elif timing == 'timed':
            timing_mode = pv.TIMED_MODE
        if pvcam.pl_exp_setup_seq(self._handle, 1, 1, ct.byref(region),
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
                print 'problem with continuous cleans 2'
            # status = self.set_any_param(pv.PARAM_CLN_WHILE_EXPO, ct.c_uint16(1))
            # if not status: print 'problem with clear while exposing'

            # frame = (ct.c_uint16 * (self.size.value//2))()
            # pvcam.pl_exp_start_seq(self._handle, frame)
            # self._current_frame = frame

    def arm_kinetics(self):
        frame = (ct.c_uint16 * (self.size.value // 2))()
        self.shutter.set_attr('arm', self.exposure)
        pvcam.pl_exp_start_seq(self._handle, frame)
        self._current_frame = frame

    def check_kinetics(self):
        status = ct.c_int16()
        pvcam.pl_exp_check_status(self._handle, ct.byref(status),
                                  ct.byref(ct.c_int32()))
        if status.value == pv.READOUT_FAILED:
            raise PixisError("Data collection error")
        elif status.value == pv.READOUT_COMPLETE:
            return 1
        else:
            return 0

    def read_kinetics(self):
        return self.frame_to_array(self._current_frame)

    def finish_kinetics(self):
        pvcam.pl_exp_finish_seq(self._handle, self._current_frame, 0)
        pvcam.pl_exp_uninit_seq()
        self._sequence_set = False

    def read_image(self):
        assert self._sequence_set, 'The acquisition sequence must be setup'
        frame = (ct.c_uint16 * (self.size.value // 2))()
        if self.timing == 'timed':
            # open shutter and wait
            self.shutter.ser.write('open\n')
            sleep(150e-3)
        elif self.timing == 'trigger':
            self.shutter.set_attr('arm', self.exposure)
        # start the acquisition
        pvcam.pl_exp_start_seq(self._handle, frame)
        # wait until the acquisition is complete
        status = ct.c_int16()
        while (pvcam.pl_exp_check_status(self._handle, ct.byref(status),
                                         ct.byref(ct.c_int32())) \
                       and (
                    status.value != pv.READOUT_COMPLETE and status.value != pv.READOUT_FAILED)):
            continue
        if self.timing == 'timed':
            # close the shutter
            self.shutter.ser.write('close\n')
        # check the result of the acquisition
        if status.value == pv.READOUT_FAILED:
            raise PixisError("Data collection error")
        # stop the acqusition sequence
        pvcam.pl_exp_finish_seq(self._handle, frame, 0)
        # pvcam.pl_exp_uninit_seq()

        a = self.frame_to_array(frame)
        # print "data written"
        return a

    def process_image(self, image):
        if self.is_background_compensated:
            assert image.shape == self.background.shape, "The supplied image was not the same shape as the background. Have you supplied background and reference images?"
            if self.is_referenced:
                old_error_settings = np.seterr(all='ignore')
                processed_image = (image - self.background) / (self.reference - self.background)
                np.seterr(**old_error_settings)
                processed_image[np.isinf(
                    processed_image)] = np.NaN  # if the reference is nearly 0, we get infinities - just make them all NaNs.
                return processed_image  # NB we shouldn't work directly with self.latest_spectrum or it will play havoc with updates...
            else:
                return image - self.background
        else:
            return image

    def update_image(self, image=None):
        self.latest_raw_image = self.read_image() if image is None else image
        self.latest_image = self.process_image(self.latest_raw_image)
        return self.latest_image

    def _get_masked_image(self):
        if self.is_referenced:
            return ma.array(self.latest_image, mask=(self.reference - self.background) < (
                                                                                         self.reference - self.background).max() * self.reference_threshold)
        else:
            return self.latest_image

    def frame_to_array(self, frame):
        a = np.array(list(frame))
        # a = np.ctypeslib.as_array(frame)
        a = a.reshape((256, 1024))
        return a

    def _take_image_fired(self):
        fin = False
        if not self._sequence_set:
            self.setup_kinetics(self.exposure, 1, timing=self.timing_mode)
            fin = True
        if self.timing_mode == 'trigger':
            self.arm_kinetics()
            while not (self.check_kinetics()): continue
            img = self.read_kinetics()
            self.update_image(img)
        else:
            self.update_image()
            # if fin: self.finish_kinetics()

    def _update_setup(self):
        self.setup_kinetics(self.exposure, 1, self.timing_mode)

    metadata_property_names = ('exposure',)


if __name__ == '__main__':
    import matplotlib.pyplot as plt

    p = Pixis256E()
    p.exposure = 40


    def test():
        # print p.check_kinetics()
        p.setup_kinetics(p.exposure, 1)
        print p.check_kinetics()
        imgs = []
        print 'ready'
        shots = 3
        for i in range(shots):
            p.arm_kinetics()
            while not (p.check_kinetics()): continue
            print "triggered"
            img = p.read_kinetics()
            img = p.process_image(img)
            imgs.append(img)
        sleep(1)
        p.setup_kinetics(p.exposure, 1, timing='timed')
        imgs.append(p.read_image())
        p.finish_kinetics()
        p.close_cam()
        print 'finished'
        # print img.shape
        # print img

        print 'plotting data'
        fig, axes = plt.subplots(shots + 1, sharex=True)
        for i, ax in enumerate(axes):
            img = ax.imshow(imgs[i])
            img.set_clim(0, 1500)
        plt.savefig('c:/users/hera/desktop/pixis_test.png')
        print 'done'
        plt.show()


    # p.setup_kinetics(p.exposure, 1, timing='timed')
    # p.read_image()
    # p.read_image()
    # p.finish_kinetics()
