__author__ = 'alansanders'

import h5py
from nplab.utils.gui import *
from PyQt4 import uic
import matplotlib

matplotlib.use('Qt4Agg')
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class DataRenderer(object):
    def __init__(self, h5object, parent=None):
        assert self.is_suitable(h5object) >= 0, "Can't render that object: {0}".format(h5object)
        super(DataRenderer, self).__init__()
        self.parent = parent
        self.h5object = h5object

    @classmethod
    def is_suitable(cls, h5object):
        """Return a score of how well suited this renderer is to the object.
        
        This should be a quick function, as it's called often (every renderer
        gives a score each time we look for a suitable renderer).  Return a
        number < 0 if you can't render the data.
        """
        return -1

renderers = set()

def add_renderer(renderer_class):
    """Add a renderer to the list of available renderers"""
    renderers.add(renderer_class)
    
def suitable_renderers(h5object, return_scores=False):
    """Find renderers that can render a given object, in order of suitability.
    """
    renderers_and_scores = [(r.is_suitable(h5object), r) for r in renderers]
    renderers_and_scores.sort(key=lambda (score, r): score, reverse=True)
    if return_scores:
        return [(score, r) for score, r in renderers_and_scores if score >= 0]
    else:
        return [r for score, r in renderers_and_scores if score >= 0]

hdf5_info_base, hdf5_info_widget = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'hdf5_info_renderer.ui'))


class HDF5InfoRenderer(DataRenderer, hdf5_info_base, hdf5_info_widget):
    def __init__(self, h5object, parent=None):
        super(HDF5InfoRenderer, self).__init__(h5object, parent)
        self.parent = parent
        self.h5object = h5object

        self.setupUi(self)
        self.lineEdit.setText(h5object.name)
        self.lineEdit2.setText(h5object.parent.name)

    @classmethod
    def is_suitable(cls, h5object):
        return 2

add_renderer(HDF5InfoRenderer)

class TextRenderer(DataRenderer, QtGui.QWidget):
    def __init__(self, h5object, parent=None):
        super(TextRenderer, self).__init__(h5object, parent)
        
        #our layout is simple - just a single QLabel
        self.label = QtGui.QLabel()
        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(self.label)
        self.setLayout(layout)
        
        self.label.setText(self.text(h5object))
        
    def text(self, h5object):
        """Return the text that is displayed in the label"""
        return str(h5object)

    @classmethod
    def is_suitable(cls, h5object):
        return 0

add_renderer(TextRenderer)


class AttrsRenderer(TextRenderer):
    def text(self, h5object):
        text = "Attributes:\n"
        for key, value in h5object.attrs.iteritems():
            text += "{0}: {1}\n".format(key, str(value))
        return text
        
    @classmethod
    def is_suitable(cls, h5object):
        return 1
add_renderer(AttrsRenderer)

class FigureRenderer(DataRenderer, QtGui.QWidget):
    def __init__(self, h5object, parent=None):
        super(FigureRenderer, self).__init__(h5object, parent)
        self.fig = Figure()

        layout = QtGui.QVBoxLayout(self)
        self.figureWidget = FigureCanvas(self.fig)
        layout.addWidget(self.figureWidget)
        self.setLayout(layout)

        self.display_data()

    def display_data(self):
        self.fig.canvas.draw()


class DataRenderer1D(FigureRenderer):
    def display_data(self):
        ax = self.fig.add_subplot(111)
        ax.plot(self.h5object)
        ax.set_aspect("auto")
        ax.relim()
        ax.autoscale_view()
        self.fig.canvas.draw()

    @classmethod
    def is_suitable(cls, h5object):
        if not isinstance(h5object, h5py.Dataset):
            return -1
        if len(h5object.shape) == 1:
            return 10
        elif len(h5object.shape) > 1:
            return -1
            
add_renderer(DataRenderer1D)


class DataRenderer2D(FigureRenderer):
    def display_data(self):
        ax = self.fig.add_subplot(111)
        ax.imshow(self.h5object, aspect="auto", cmap="cubehelix")
        # ax.relim()
        # ax.autoscale_view()
        self.fig.canvas.draw()

    @classmethod
    def is_suitable(cls, h5object):
        if not isinstance(h5object, h5py.Dataset):
            return -1
        if len(h5object.shape) == 2:
            return 10
        elif len(h5object.shape) < 2:
            return -1
            
add_renderer(DataRenderer2D)


class DataRendererRGB(FigureRenderer):
    """This renderer is suitable for showing RGB images"""
    def display_data(self):
        ax = self.fig.add_subplot(111)
        ax.imshow(self.h5object)
        # ax.relim()
        # ax.autoscale_view()
        self.fig.canvas.draw()

    @classmethod
    def is_suitable(cls, h5object):
        if not isinstance(h5object, h5py.Dataset):
            return -1
        if len(h5object.shape) == 3 and h5object.shape[2]==3:
            return 15
        elif len(h5object.shape) != 2:
            return -1
            
add_renderer(DataRendererRGB)


if __name__ == '__main__':
    import sys, h5py, os, numpy as np

    print os.getcwd()
    app = get_qt_app()
    f = h5py.File('test.h5', 'w')
    dset = f.create_dataset('dset1', data=np.linspace(-1, 1, 100))
    ui = HDF5InfoRenderer(dset)
    ui.show()
    sys.exit(app.exec_())
    f.close()
