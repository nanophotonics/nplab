"""
GUI Utilities
=============

Various utility functions for GUI-related stuff.
"""

from pyface.qt import QtCore as qt
from pyface.qt import QtGui as qtgui

def get_qt_app():
    """Retrieve or create the QApplication instance.

    If running inside Spyder, or if you've used TraitsUI, the application
    will already exist so you can't create another.  However, if you are
    running from the command line you need to create an instance before
    you can do anything.  This function takes care of it - it should always
    return a valid QApplication, unless something goes wrong!
    """
    app = qtgui.QApplication.instance()
    if app is None:
        app = qtgui.QApplication([])
    assert app is not None, "Problem creating the QApplication."
    return app
