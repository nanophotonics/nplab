__author__ = 'alansanders'

from nplab.instrument import Instrument
from nplab.utils.gui import *
from PyQt4 import uic
from nplab.ui.ui_tools import UiTools


class Shutter(Instrument):

    def __init__(self, shutter=None):
        super(Shutter, self).__init__()

    def toggle(self):
        pass

    def get_state(self):
        pass

    def set_state(self, value):
        print value

    state = property(get_state, set_state)

    def get_qt_ui(self):
        return ShutterUI(self)


class ShutterUI(QtGui.QWidget, UiTools):
    def __init__(self, shutter, parent=None):
        assert isinstance(shutter, Shutter), 'instrument must be a Shutter'
        self.shutter = shutter
        super(ShutterUI, self).__init__(parent)
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'shutter.ui'), self)
        self.auto_connect_by_name(controlled_object = self.shutter)
    #    self.state.stateChanged.connect(self.on_change)

    def on_change(self):
        self.shutter.toggle()


if __name__ == '__main__':
    import sys
    app = get_qt_app()
    shutter = Shutter()
    ui = shutter.get_qt_ui()
    ui.show()
    sys.exit(app.exec_())
