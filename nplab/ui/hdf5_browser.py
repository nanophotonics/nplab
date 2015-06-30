"""
Describes the contents of the file
"""

__author__ = 'alansanders'

from nplab.utils.gui import *
from PyQt4 import uic
import matplotlib
matplotlib.use('Qt4Agg')
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from data_renderers import *

base, widget = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'hdf5_browser.ui'))

class HDF5Browser(base, widget):
    """
    Describe the class
    """

    def __init__(self, f, parent=None):
        super(HDF5Browser, self).__init__(parent)
        self.f = f
        self.fig = Figure()
        self.setupUi(self)

        self.setWindowTitle(self.f.filename)
        self.addItems(self.treeWidget.invisibleRootItem())
        self.treeWidget.itemClicked.connect(self.on_click)
        self.treeWidget.customContextMenuRequested.connect(self.context_menu)
        self.refreshButton.clicked.connect(self.refresh)

        self.figureWidget = FigureCanvas(self.fig)
        self.figureWidget.setParent(self)
        self.horizontalLayout.addWidget(self.figureWidget)

    def __del__(self):
        pass#self.f.close()

    def addItems(self, parent):
        root = self.addParent(parent, 0, self.f.filename, self.f)
        self.parents = {self.f.name:root}
        self.f.visit(self.addChild)

    def addParent(self, parent, column, title, data):
        item = QtGui.QTreeWidgetItem(parent, [title])
        item.setData(column, QtCore.Qt.UserRole, data)
        item.setChildIndicatorPolicy(QtGui.QTreeWidgetItem.ShowIndicator)
        item.setExpanded(False)
        return item

    def addChild(self, name):
        h5parent = self.f[name].parent.name
        if h5parent in self.parents:
            parent = self.parents[h5parent]
        else:
            print 'no parent', name, h5parent
            parent = self.parents['/']
        item = QtGui.QTreeWidgetItem(parent, [name.rsplit('/', 1)[-1]])
        item.setData(0, QtCore.Qt.UserRole, self.f[name])
        self.parents['/'+name] = item

    def refresh(self):
        self.treeWidget.clear()
        self.addItems(self.treeWidget.invisibleRootItem())

    def context_menu(self, position):
        menu = QtGui.QMenu()
        actions = {}
        for operation in ['Move', 'Delete', 'Rename', 'Refresh']:
            actions[operation] = menu.addAction(operation)
        action = menu.exec_(self.treeWidget.viewport().mapToGlobal(position))
        if action == actions['Move']:
            print 'move'
        elif action == actions['Delete']:
            print 'delete'
        elif action == actions['Rename']:
            print 'rename'
        elif action == actions['Refresh']:
            self.refresh()

    def on_click(self, item, column):
        item.setExpanded(True)
        h5object = item.data(column, QtCore.Qt.UserRole)
        renderer_suitabilities = [d.is_suitable(h5object) for d in renderers]
        max_renderer = max(renderer_suitabilities)
        best_renderer = renderers[renderer_suitabilities.index(max_renderer)]
        self.figureWidget = self.renew_widget(self.figureWidget, best_renderer(h5object, self))

    def renew_widget(self, old_widget, new_widget):
        layout = self.horizontalLayout
        layout.removeWidget(old_widget)
        old_widget.setParent(None)
        layout.addWidget(new_widget)
        new_widget.setParent(self)
        return new_widget


if __name__ == '__main__':
    import sys, h5py, os, numpy as np
    print os.getcwd()
    app = get_qt_app()
    f = h5py.File('test.h5', 'w')
    f.create_dataset('dset1', data=np.linspace(-1,1,100))
    g = f.create_group('group1')
    g.create_dataset('dset2', data=np.linspace(-1,1,100)**2)
    g = g.create_group('group2')
    g.create_dataset('dset3', data=np.linspace(-1,1,100).reshape(10,10))
    ui = HDF5Browser(f)
    ui.show()
    sys.exit(app.exec_())
    f.close()