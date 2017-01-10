"""
Qt adaptation of Gael Varoquaux's tutorial to integrate Matplotlib
http://docs.enthought.com/traitsui/tutorials/traits_ui_scientific_app.html#extending-traitsui-adding-a-matplotlib-figure-to-our-application

based on Qt-based code shared by Didrik Pinte, May 2012
http://markmail.org/message/z3hnoqruk56g2bje

adapted and tested to work with PySide from Anaconda in March 2014
"""
__author__ = 'alansanders'

from nplab.utils.gui import QtCore
import matplotlib
matplotlib.use('Qt4Agg')
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas


class FigureCanvasWithDeferredDraw(FigureCanvas):
    # This class allows us to use Qt's event loop to draw the canvas from
    # the GUI thread, even if the call comes from outside the GUI thread.
    # this is necessary if you want to plot from a background thread.
    ask_for_redraw = QtCore.Signal()

    def __init__(self, figure):
        FigureCanvas.__init__(self, figure)
        # We connect the ask_for_redraw signal to the FigureCanvas's draw() method.
        # using a QueuedConnection ensures that draw() is correctly called in the
        # application's main GUI thread.
        self.ask_for_redraw.connect(self.draw, type=QtCore.Qt.QueuedConnection)

    def draw_in_main_loop(self):
        """Draw the canvas, but do so in the Qt main loop to avoid threading nasties."""
        self.ask_for_redraw.emit()