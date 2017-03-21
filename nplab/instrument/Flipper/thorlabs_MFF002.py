from nplab.instrument.Flipper import Flipper
import struct
import numpy as np

class ThorlabsMFF(Flipper):
    def __init__(self, port):
        Flipper.__init__(self, port)

    def set_state(self, value):
        if value:
            self.write(0x046A, param1=0x01, param2=0x01)
        else:
            self.write(0x046A, param1=0x01, param2=0x02)

    def get_status(self):
        self.write(0x0429, param1=0x01)
        msg = self.read()['data']
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
    import time
#    from nplab.utils.gui import *
#    app = get_qt_app()
    flipper = ThorlabsMFF('COM19')
    flipper.get_status()
    # print flipper.model
    flipper.set_state(0)
    time.sleep(10)
    print flipper.get_status()
    time.sleep(2)
    flipper.set_state(1)
    time.sleep(10)
    print flipper.get_status()
    # print flipper.state
    # flipper.state = 0
    # print flipper.state
    # print flipper._last_set_state
#    ui = shutter.get_qt_ui()
#    ui.show()
#    sys.exit(app.exec_())
#     shutter.show_gui()