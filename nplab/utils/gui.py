"""
GUI Utilities
=============

Various utility functions for GUI-related stuff.
"""

import sip
API_NAMES = ["QDate", "QDateTime", "QString", "QTextStream", "QTime", "QUrl", "QVariant"]
API_VERSION = 2
for name in API_NAMES:
    sip.setapi(name, API_VERSION)

from pyface.qt import QtCore as qt
from pyface.qt import QtGui as qtgui
from pyface.qt import QtCore, QtGui

try:
    assert QtCore.Signal
    assert QtCore.Slot
except AssertionError:
    # if Signal and Slot don't exist, we're probably using the old API, so work around.
    QtCore.Signal = QtCore.pyqtSignal
    QtCore.Slot = QtCore.pyqtSlot


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
