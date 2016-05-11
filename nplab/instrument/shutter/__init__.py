__author__ = 'alansanders'

from nplab.instrument import Instrument
from nplab.utils.gui import QtGui, QtCore, uic, get_qt_app
from nplab.ui.ui_tools import UiTools, QuickControlBox
import os
from nplab.utils.notified_property import DumbNotifiedProperty, register_for_property_changes


class Shutter(Instrument):

    def __init__(self, shutter=None):
        super(Shutter, self).__init__()

    def toggle(self):
        """Toggle the state of the shutter."""
        raise NotImplementedError("This shutter has no way to toggle!""")

    def get_state(self):
        """Return whether the shutter is 'Open' or 'Closed'."""
        raise NotImplementedError("This shutter has no way to get its state!""")

    def set_state(self, value):
        """Set the shutter to be either 'Open' or 'Closed'."""
        raise NotImplementedError("This shutter has no way to set its state!""")
        
    def open_shutter(self):
        """Open the shutter."""
        self.set_state("Open")
    
    def close_shutter(self):
        """Close the shutter."""
        self.set_state("Closed")

    state = property(get_state, set_state)

    def get_qt_ui(self):
        """Return a graphical interface for the shutter."""
        return ShutterUI(self)


class ShutterUI(QtGui.QWidget, UiTools):
    def __init__(self, shutter, parent=None):
        assert isinstance(shutter, Shutter), 'instrument must be a Shutter'
        self.shutter = shutter
        super(ShutterUI, self).__init__(parent)
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'shutter.ui'), self)
        self.auto_connect_by_name(controlled_object = self.shutter,verbose = False)
    #    self.state.stateChanged.connect(self.on_change)

    def on_change(self):
        self.shutter.toggle()

class DummyShutter(Shutter):
    """A stub class to simulate a shutter"""
    _open = DumbNotifiedProperty(False)
    def __init__(self):
        """Create a dummy shutter object"""
        self._open = False
        super(DummyShutter, self).__init__()
        
    def toggle(self):
        """toggle the state of the shutter"""
        self._open = not self._open
    
    def get_state(self):
        """Return the state of the shutter, a string reading 'open' or 'closed'"""
        return "Open" if self._open else "Closed"
        
    def set_state(self, value):
        """Set the state of the shutter (to open or closed)"""
        if isinstance(value, str):
            self._open = (value.lower() == "open")
        elif isinstance(value, bool):
            self._open = value
        

if __name__ == '__main__':
    import sys
    app = get_qt_app()
    shutter = DummyShutter()

    state_peek = QuickControlBox(title="Internal State")
    state_peek.add_checkbox("_open", title="Shutter Open")
    state_peek.auto_connect_by_name(controlled_object=shutter)
    state_peek.show()    
    
    ui = shutter.get_qt_ui()
    ui.show()
    sys.exit(app.exec_())
