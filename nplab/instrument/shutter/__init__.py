__author__ = 'alansanders'

from nplab.instrument import Instrument
from nplab.utils.gui import QtCore, QtGui, QtWidgets, get_qt_app, uic
from nplab.ui.ui_tools import UiTools, QuickControlBox
import os
import time
from nplab.utils.notified_property import DumbNotifiedProperty, register_for_property_changes
import contextlib


class Shutter(Instrument):
    """A generic instrument class for optical shutters.
    
    An optical shutter can be "Open" (allowing light to pass) or "Closed" (not
    allowing light through).  This generic class provides a GUI and some
    convenience methods.  You can set and (usually) check the state of the
    shutter using the property `Shutter.state` which is a string that's either
    "Open" or "Closed".  If you need a boolean answer, use `Shutter.is_open()`
    or `Shutter.is_closed`.  There's also `expose()` that opens for a number
    of seconds, and `toggle()` that changes state.
    
    # Subclassing Notes
    The minimum required subclassing effort is overriding `set_state` to open
    and close the shutter.  Overriding get_state allows you to read back the
    state of the shutter.  If you want to emulate that (i.e. keep track of
    the state of the shutter in software) subclass `ShutterWithEmulatedRead`
    and make sure you call its `__init__` method in your initialisation code.
    """
    def __init__(self):
        super(Shutter, self).__init__()

    def toggle(self):
        """Toggle the state of the shutter.
        
        The default behaviour will emulate a toggle command if none exists.
        """
        try:
            if self.is_closed():
                self.state = "Open"
            else:
                self.state = "Closed"
        except NotImplementedError:
            raise NotImplementedError("This shutter has no way to toggle!""")
        
    @contextlib.contextmanager
    def hold(self, state="Open", default_state="Closed"):
        """Hold the shutter in a given state (for use in a `with` block).
        
        This returns a context manager, so it can be used in a `with` block,
        so that the shutter is held in the given position (default Open) while
        something else happens, then returns to its previous state (usually
        Closed) afterwards, even if exceptions occur.
        
        If the shutter can't report it's current state it should raise a
        `NotImplementedError` (this is the default) in which case we will 
        default to closing the shutter afterwards unless `default_state` has
        been set in which case we use that.
        
        In the future, this might block other threads from touching the 
        shutter - currently it does not.
        """
        try:
            oldstate = self.state
        except NotImplementedError:
            oldstate = default_state
        try:
            self.state = state
            yield
        finally:
            self.state = oldstate
            
    def expose(self, time_in_seconds):
        """Open the shutter for a specified time, then close again.
        
        This function will block until the exposure is over.  NB if you 
        override this function in a subclass, take care with what happens to
        reads/writes of the self.state property.  If you are in a subclass
        of `ShutterWithEmulatedRead` you might need to update
        `_last_set_state`.
        """
        with self.hold("Open"):
            time.sleep(time_in_seconds)

    def get_state(self):
        """Whether the shutter is 'Open' or 'Closed'."""
        raise NotImplementedError("This shutter has no way to get its state!""")

    def set_state(self, value):
        """Set the shutter to be either 'Open' or 'Closed'."""
        raise NotImplementedError("This shutter has no way to set its state!""")
        
    def open_shutter(self):
        """Open the shutter."""
        self._set_state_proxy("Open")
    
    def close_shutter(self):
        """Close the shutter."""
        self._set_state_proxy("Closed")

    # This slightly ugly hack means it's not necessary to redefine the 
    # state property every time it's subclassed.
    def _get_state_proxy(self):
        """The state of the shutter - should either be "Open" or "Closed"."""
        return self.get_state()
        
    def _set_state_proxy(self, state):
        self.set_state(state)
        self._last_set_state = state.title() # Remember what state we're in
        
    state = property(_get_state_proxy, _set_state_proxy)
    
    def is_open(self):
        """Return `True` if the shutter is open."""
        return self.state.title() == "Open"
        
    def is_closed(self):
        """Return `True` if the shutter is closed."""
        return self.state.title() == "Closed"

    def get_qt_ui(self):
        """Return a graphical interface for the shutter."""
        return ShutterUI(self)

class ShutterWithEmulatedRead(Shutter):
    """A shutter class that keeps track in software of whether it's open.
    
    Use this instead of `Shutter` if you don't want to communicate with the
    shutter to check whether it's open or closed.
    
    # Subclassing Notes
    See the subclassing notes from `Shutter`.  All you need to override is
    `set_state`, the rest is dealt with.  NB if you have to initialise the
    hardware, make sure you do that *before* calling 
    `ShutterWithEmulatedRead.__init__()` as it closes the shutter to start
    with.
    """
    def __init__(self):
        """Initialise the shutter to the closed position."""
        self._last_set_state = 'Closed'
        self.state = "Closed"
    
    def get_state(self):
        """Whether the shutter is Open or Closed."""
        return self._last_set_state
    

class ShutterUI(QtWidgets.QWidget, UiTools):
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
