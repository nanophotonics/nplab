"""
GUI Utilities
=============

Various utility functions for GUI-related stuff.
"""
from __future__ import print_function

from builtins import range
import os
import sys
import warnings
import qtpy #removing this breaks line 42 in some cases
ui_toolkit = 'native'  # by default use pyqt4
if os.environ.get('QT_API') is None:
    os.environ['QT_API'] = 'pyqt'  # by default use pyqt4
qt_api = os.environ.get('QT_API')

#print "api environment variable is (gui): "+os.environ['QT_API']

import sip
API_NAMES = ["QDate", "QDateTime", "QString", "QTextStream", "QTime", "QUrl", "QVariant"]
API_VERSION = 2
for name in API_NAMES:
    sip.setapi(name, API_VERSION)
if ui_toolkit == 'native' and os.environ['QT_API'] == 'pyside':
    try:
        from PySide import QtCore, QtGui
    except:
        warnings.warn("Warning: falling back to PyQt4", UserWarning)
        ui_toolkit = 'pyqt'
        from PyQt4 import QtCore, QtGui
        from PyQt4 import uic
elif ui_toolkit == 'pyface':
    from traits.etsconfig.api import ETSConfig
    ETSConfig.toolkit = 'qt4'
    from pyface.qt import QtCore, QtGui
elif ui_toolkit == 'native':
    try:
 #       from PyQt4 import QtCore, QtGui
 #       from PyQt4 import QtCore as qt
 #       from PyQt4 import QtGui as qtgui
  #      from PyQt4 import uic
      from qtpy import QtGui,QtCore,QtWidgets, uic
    except Exception as e:
        warnings.warn("Warning: failed to load qtpy, are you sure qtpy is installed?, falling back to pyside", UserWarning)
        print(e)
        from PySide import QtCore, QtGui
else:
    raise ImportError("Invalid ui_toolkit or QT_API")
#print QtCore, QtGui

# this is to rectify differences between pyside and pyqt4
try:
    assert QtCore.Signal
    assert QtCore.Slot
except AttributeError:
    # if Signal and Slot don't exist, we're probably using the old API, so work around.
    QtCore.Signal = QtCore.pyqtSignal
    QtCore.Slot = QtCore.pyqtSlot

#QtGui.QApplication.setGraphicsSystem("raster")

_retained_qt_app = None # this lets us hold on to the Qt Application if needed.
def get_qt_app(prevent_garbage_collection=True):
    """Retrieve or create the QApplication instance.

    If running inside Spyder, or if you've used TraitsUI, the application
    will already exist so you can't create another.  However, if you are
    running from the command line you need to create an instance before
    you can do anything.  This function takes care of it - it should always
    return a valid QApplication, unless something goes wrong!
    """
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    assert app is not None, "Problem creating the QApplication."
    if prevent_garbage_collection:
        # Keep a reference to the application if appropriate, to stop
        # it disappearing due to garbage collection.
        global _retained_qt_app
        _retained_qt_app = app
    return app


def popup_widget(widget): # TODO: what is "widget"?
    if widget.isVisible():  # doesn't need to be created and shown just brought to the front
        pass
    else:
        ui = widget()
        ui.show()


def show_widget(Widget, *args, **kwargs):
    """Show the specified widget GUI in a QT application.  
    
    NB Widget is a class."""
    app = get_qt_app()
    ui = Widget(*args, **kwargs)
    ui.show()
    sys.exit(app.exec_())

def show_guis(instruments, block=True):
    """Display the Qt user interfaces of a list of instruments."""
    app = get_qt_app()
    uis = [i.show_gui(blocking=False) for i in instruments if hasattr(i, "get_qt_ui")]
    # DataBrowserImprovements swapped get_qt_ui for show_gui(block=False)
    traits = [i.edit_traits() for i in instruments if hasattr(i, "edit_traits")]
    for ui in uis:
        ui.show()
    if block:
        return app.exec_()
    else:
        return uis, traits

if __name__ == '__main__':
    import matplotlib
    # We want matplotlib to use a QT backend
    matplotlib.use('Qt4Agg')
    from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import numpy as np

    print("QT Backend: " + matplotlib.rcParams['backend.qt4'])

    class Widget(QtGui.QWidget):
        def __init__(self):
            super(Widget, self).__init__()
            self.setWindowTitle(self.__class__.__name__)
            # a figure instance to plot on
            self.figure = Figure()
            self.ax = self.figure.add_subplot(111)
            # this is the Canvas Widget that displays the `figure`
            # it takes the `figure` instance as a parameter to __init__
            self.canvas = FigureCanvas(self.figure)
            # Just some button connected to `plot` method
            self.button = QtGui.QPushButton('Plot')
            self.button.clicked.connect(self.plot)
            self.button.setToolTip('This is a <b>QPushButton</b> widget')
            self.button.resize(self.button.sizeHint())
            # set the layout
            layout = QtGui.QVBoxLayout()
            layout.addWidget(self.canvas)
            layout.addWidget(self.button)
            self.setLayout(layout)

        def plot(self):
            ''' plot some random stuff '''
            # random data
            print('plot')
            data = [np.random.random() for i in range(1000)]
            # create an axis
            #ax = self.figure.add_subplot(111)
            ax = self.figure.axes[0]
            # discards the old graph
            ax.hold(False)
            # plot data
            ax.plot(data, '*-')
            # refresh canvas
            self.canvas.draw()

    show_widget(Widget())
