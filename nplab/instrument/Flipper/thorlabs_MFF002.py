from nplab.instrument.flipper import Flipper
import struct
import numpy as np
import time
from nplab.utils.thread_utils import locked_action, background_action


class ThorlabsMFF(Flipper):
    def __init__(self, port, **kwargs):
        Flipper.__init__(self, port)

    # @background_action    # background_actions do not work well with properties
    @locked_action
    def set_state(self, value):
        if value:
            self.write(0x046A, param1=0x01, param2=0x01)
            time.sleep(0.1)
            t0 = time.time()
            while self.get_state() != 1:
                time.sleep(0.1)
                if time.time() - t0 > self.port_settings['timeout']:
                    raise RuntimeError('Timed out while waiting for position change')
        else:
            self.write(0x046A, param1=0x01, param2=0x02)
            time.sleep(0.1)
            t0 = time.time()
            while self.get_state() != 0:
                time.sleep(0.1)
                if time.time() - t0 > self.port_settings['timeout']:
                    raise RuntimeError('Timed out while waiting for position change')

    def get_state(self):
        self.write(0x0429, param1=0x01)
        read = self.read()
        msg = read['data']
        unpacked = self.unpack_binary_mask(struct.unpack('<HI', msg)[1])
        if np.sum(unpacked) != 1:
            return 'Fuck'
        elif unpacked[1]:
            return 0
        elif unpacked[0]:
            return 1
        else:
            return 'Fuck2'


if __name__ == '__main__':
    import sys

    # from nplab.utils.gui import *
    # app = get_qt_app()
    flipper = ThorlabsMFF('COM19')

    # flipper.get_status()
    # print flipper.model
    # flipper.set_state(0)
    # time.sleep(2)
    # print flipper.get_status()
    # #time.sleep(2)
    # flipper.set_state(1)
    # time.sleep(2)
    # print flipper.get_status()

    # print flipper.state
    # flipper.state = 0
    # print flipper.state
    # print flipper._last_set_state
    # ui = flipper.get_qt_ui()
    # ui.show()
    # sys.exit(app.exec_())
    flipper.show_gui()
