"""
GUI Utilities
=============

Various utility functions for GUI-related stuff.
"""

import os
ui_toolkit = 'native'  # by default use pyqt4
if os.environ.get('QT_API') is None:
    os.environ['QT_API'] = 'pyqt'  # by default use pyqt4
qt_api = os.environ.get('QT_API')

print "api environment variable is (gui): "+os.environ['QT_API']

import sip
API_NAMES = ["QDate", "QDateTime", "QString", "QTextStream", "QTime", "QUrl", "QVariant"]
API_VERSION = 2
for name in API_NAMES:
    sip.setapi(name, API_VERSION)

if ui_toolkit == 'native' and os.environ['QT_API'] == 'pyside':
    try:
        from PySide import QtCore, QtGui
        from PySide import QtCore as qt
        from PySide import QtGui as qtgui
    except:
        print "Warning: falling back to PyQt4"
        ui_toolkit = 'pyqt'
        from PyQt4 import QtCore, QtGui
        from PyQt4 import QtCore as qt
        from PyQt4 import QtGui as qtgui
elif ui_toolkit == 'pyface':
    from traits.etsconfig.api import ETSConfig
    ETSConfig.toolkit = 'qt4'
    from pyface.qt import QtCore as qt
    from pyface.qt import QtGui as qtgui
    from pyface.qt import QtCore, QtGui
elif ui_toolkit == 'native' and os.environ['QT_API'] == 'pyqt':
    from PyQt4 import QtCore, QtGui
    from PyQt4 import QtCore as qt
    from PyQt4 import QtGui as qtgui
else:
    raise ImportError("Invalid ui_toolkit or QT_API")
print QtCore, QtGui

# this is to rectify differences between pyside and pyqt4
try:
    assert QtCore.Signal
    assert QtCore.Slot
except AttributeError:
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


if __name__ == '__main__':
    import matplotlib
    # We want matplotlib to use a QT backend
    matplotlib.use('Qt4Agg')
    from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import numpy as np

    print "QT Backend: " + matplotlib.rcParams['backend.qt4']

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
            print 'plot'
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


    import sys
    app = get_qt_app()
    ui = Widget()
    ui.show()
    sys.exit(app.exec_())