from nplab.instrument import Instrument
from nplab.instrument.apt_virtual_com_port import APT_VCP
from nplab.utils.gui import QtCore, QtGui, QtWidgets, get_qt_app, uic
from nplab.ui.ui_tools import UiTools, QuickControlBox
import os
import time
from nplab.utils.notified_property import DumbNotifiedProperty, register_for_property_changes
import contextlib


class Flipper(APT_VCP):
    """A generic instrument class for flippers.
    
    # Subclassing Notes
    The minimum required subclassing effort is overriding `set_state` and `get_state` to open
    and close the flipper.  Overriding get_state allows you to read back the
    state of the flipper.  If you want to emulate that (i.e. keep track of
    the state of the flipper in software) subclass `flipperWithEmulatedRead`
    and make sure you call its `__init__` method in your initialisation code.
    """
    def __init__(self, port):
        # Instrument.__init__(self)
        APT_VCP.__init__(self, port=port, destination=0x50)
        # super(Flipper, self).__init__()

    def toggle(self):
        """Toggle the state of the flipper.
        
        The default behaviour will emulate a toggle command if none exists.
        """
        try:
            if self.state:
                self.state = 0
            else:
                self.state = 1
        except NotImplementedError:
            raise NotImplementedError("This flipper has no way to toggle!""")

    def get_state(self):
        """Whether the flipper is 'Open' or 'Closed'."""
        raise NotImplementedError("This flipper has no way to get its state!""")

    def set_state(self, value):
        """Set the flipper to be either 0 or 1'."""
        raise NotImplementedError("This flipper has no way to set its state!""")

    # This slightly ugly hack means it's not necessary to redefine the 
    # state property every time it's subclassed.
    def _get_state_proxy(self):
        """The state of the flipper - should either be "Open" or "Closed"."""
        return self.get_state()
        
    def _set_state_proxy(self, state):
        self.set_state(state)
        self._last_set_state = state # Remember what state we're in
        
    state = property(_get_state_proxy, _set_state_proxy)

    def get_qt_ui(self):
        """Return a graphical interface for the flipper."""
        return flipperUI(self)


class flipperUI(QtWidgets.QWidget, UiTools):
    def __init__(self, flipper, parent=None):
        assert isinstance(flipper, Flipper), 'instrument must be a flipper'
        self.flipper = flipper
        super(flipperUI, self).__init__(parent)
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'flipper.ui'), self)
        self.auto_connect_by_name(controlled_object = self.flipper,verbose = False)
    #    self.state.stateChanged.connect(self.on_change)

    def on_change(self):
        self.flipper.toggle()

class Dummyflipper(Flipper):
    """A stub class to simulate a flipper"""
    _open = DumbNotifiedProperty(False)
    def __init__(self):
        """Create a dummy flipper object"""
        self._open = False
        super(Dummyflipper, self).__init__()
        
    def toggle(self):
        """toggle the state of the flipper"""
        self._open = not self._open
    
    def get_state(self):
        """Return the state of the flipper, a string reading 'open' or 'closed'"""
        return "Open" if self._open else "Closed"
        
    def set_state(self, value):
        """Set the state of the flipper (to open or closed)"""
        if isinstance(value, str):
            self._open = (value.lower() == "open")
        elif isinstance(value, bool):
            self._open = value
        

if __name__ == '__main__':
    import sys
    import time
    # app = get_qt_app()
    # flipper = Dummyflipper()

    # flipper.setstate(0)
    # time.sleep(5)
    # flipper.set_state(1)

    # state_peek = QuickControlBox(title="Internal State")
    # state_peek.add_checkbox("_open", title="flipper Open")
    # state_peek.auto_connect_by_name(controlled_object=flipper)
    # state_peek.show()
    
    # ui = flipper.get_qt_ui()
    # ui.show()
    # sys.exit(app.exec_())
