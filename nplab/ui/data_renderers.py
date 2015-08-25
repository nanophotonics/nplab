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
        super(DataRenderer, self).__init__()
        self.parent = parent
        self.h5object = h5object

    @classmethod
    def is_suitable(cls, h5object):
        return 0


hdf5_info_base, hdf5_info_widget = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'hdf5_info_renderer.ui'))


class HDF5InfoRenderer(DataRenderer, hdf5_info_base, hdf5_info_widget):
    def __init__(self, h5object, parent=None):
        super(HDF5InfoRenderer, self).__init__(h5object, parent)
        self.parent = parent
        self.h5object = h5object

        self.setupUi(self)
        self.lineEdit.setText(h5object.name)
        self.lineEdit2.setText(h5object.parent.name)


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
    def __init__(self, h5object, parent=None):
        assert isinstance(h5object, h5py.Dataset), 'h5object must be a h5py Dataset'
        super(DataRenderer1D, self).__init__(h5object, parent)

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
            return 1
        elif len(h5object.shape) > 1:
            return -1


class DataRenderer2D(FigureRenderer):
    def __init__(self, h5object, parent=None):
        super(DataRenderer2D, self).__init__(h5object, parent)

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
        if len(h5object.shape) == 2:
            return 1
        elif len(h5object.shape) < 2:
            return -1


renderers = [HDF5InfoRenderer, DataRenderer1D, DataRenderer2D]

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
