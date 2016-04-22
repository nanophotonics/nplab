"""
Describes the contents of the file
"""

__author__ = 'alansanders'

from nplab.utils.gui import *
from PyQt4 import uic
from PyQt4 import QtGui, QtCore #TODO: I think these should be wrapped by nplab.utils.gui? rwb
import matplotlib
import numpy as np
import h5py

matplotlib.use('Qt4Agg')
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from nplab.ui.data_renderers import suitable_renderers
from nplab.ui.ui_tools import UiTools

import subprocess
import os


# base, widget = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'hdf5_browser.ui'))

class HDF5Browser(QtGui.QWidget, UiTools):
    """
    Describe the class
    """

    def __init__(self, f, parent=None):
        super(HDF5Browser, self).__init__(parent)
        self.f = f #TODO: don't call this f - call it data_group or something.
        self.fig = Figure()
        # self.setupUi(self)
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'hdf5_browser.ui'), self)

        try:
            self.root_name = self.f.filename
        except AttributeError:
            self.root_name = self.f.file.filename
        self.setWindowTitle(self.root_name)
        
        self.addItems(self.treeWidget.invisibleRootItem())   
        self.treeWidget.itemClicked.connect(self.on_click)
        self.treeWidget.customContextMenuRequested.connect(self.context_menu)
        self.treeWidget.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection) #allow multiple items to be selected
        
        self.refreshButton.clicked.connect(self.refresh)
        self.CopyButton.clicked.connect(self.CopyActivated)
        self.clipboard = QtGui.QApplication.clipboard()
        
        self.figureWidget = self.replace_widget(self.figureWidgetContainer, self.figureWidget, FigureCanvas(self.fig))
        self.figureWidget.setMinimumWidth(800)
        self.rendererselection.activated[str].connect(self.RenderSelectorActivated) 
    def __del__(self):
        pass  # self.f.close()

    def addItems(self, parent):
        """Populate the tree view with the contents of the HDF5 file."""
        root = self.addParent(parent, 0, self.root_name, self.f)
        self.parents = {self.f.name: root} #parents holds all the items in the list, organised by HDF5 path
        self.f.visit(self.addChild) #visit every item in the HDF5 tree, and add it.

    def addParent(self, parent, column, title, data):
        """Add an item to the HDF5 tree with parameters specified.
        
        Arguments:
        parent: the QTreeWidgetItem the new entry should be within
        column: the column into which we're going to put the data - always 0
        title: the title of the item
        data: the data stored with this itme (a reference to the HDF5 item)
        """
        item = QtGui.QTreeWidgetItem(parent, [title])
        item.setData(column, QtCore.Qt.UserRole, data)
        item.setChildIndicatorPolicy(QtGui.QTreeWidgetItem.ShowIndicator)
        item.setExpanded(False)
        return item

    def addChild(self, name):
        """Add an item to the tree, based only on the HDF5 path."""
        h5parent = self.f[name].parent.name
        if h5parent in self.parents:
            parent = self.parents[h5parent]
        else:
            print 'no parent', name, h5parent
            parent = self.parents['/']
        item = QtGui.QTreeWidgetItem(parent, [name.rsplit('/', 1)[-1]])
        item.setData(0, QtCore.Qt.UserRole, self.f[name]) #Question: does this read the data? Could be slow for large datasets if so...
        self.parents['/' + name] = item #Add the item to our internal list, keyed on HDF5 path

    def refresh(self):
        """Empty the tree and repopulate it."""
        self.treeWidget.clear()
        self.addItems(self.treeWidget.invisibleRootItem())
        
  
    def context_menu(self, position):
        """Generate a right-click menu for the items"""
        menu = QtGui.QMenu()
        actions = {}
        
        for operation in ['Open in Igor']:
            actions[operation] = menu.addAction(operation)
        action = menu.exec_(self.treeWidget.viewport().mapToGlobal(position))

        if action == actions['Open in Igor']:
            self.igorOpen()

    def on_click(self, item, column):
        """Handle clicks on items in the tree."""
        item.setExpanded(True)
        if len(self.treeWidget.selectedItems())>1: 
            self.selected_objects = [treeitem.data(column, QtCore.Qt.UserRole) for treeitem in self.treeWidget.selectedItems() ]
        else:
            self.selected_objects = item.data(column, QtCore.Qt.UserRole)
        
    #    print self.treeWidget.selectedItems()
        
        self.possible_renderers = suitable_renderers(self.selected_objects)
        self.figureWidget = self.replace_widget(self.figureWidgetContainer, self.figureWidget, self.possible_renderers[0](self.selected_objects, self))
        self.possible_renderer_names = [renderers.__name__ for renderers in self.possible_renderers]
    #    print self.possible_renderer_names
        self.rendererselection.clear()
        self.rendererselection.addItems(self.possible_renderer_names)
        
    def RenderSelectorActivated(self,text):
        """Change the figure widget to use the selected renderer."""
        for renderer in self.possible_renderers:
            if renderer.__name__ == text:
                self.figureWidget = self.replace_widget(self.figureWidgetContainer, self.figureWidget, renderer(self.selected_objects, self))
        
        
        
    def CopyActivated(self):
        """Copy an image of the currently-displayed figure."""
        Pixelmap = QtGui.QPixmap.grabWidget(self.figureWidget)
        self.clipboard.setPixmap(Pixelmap)
        
        
    def igorOpen(self):
        """Open the currently-selected item in Igor Pro."""
        igorpath = '"C:\\Program Files (x86)\\WaveMetrics\\Igor Pro Folder\\Igor.exe"'
        igortmpfile = os.path.dirname(os.path.realpath(__file__))+'\Igor'
        igortmpfile=igortmpfile.replace("\\","\\\\")
        print igortmpfile
        open(igortmpfile, 'w').close()
        group = self.treeWidget.currentItem().text(0)
        dataset_name = self.treeWidget.currentItem().text(1)
        dataset = self.selected_objects
        print group
        print dataset
        if isinstance(dataset,h5py.Dataset):
            print dataset_name
            dset = dataset
            data = np.asarray(dset[...])

            if data.ndim == 2:
                from PIL import Image
                rescaled = (2**16 / data.max() * (data - data.min())).astype(np.uint8)

                im = Image.fromarray(rescaled.transpose())
                im.save(igortmpfile+'.tif')

                command='/X "ImageLoad/T=tiff/N= h5Data'+' \"'+ igortmpfile+'.tif\""'
                subprocess.Popen(igorpath+' '+command)
            else:
                print dataset
                np.savetxt(igortmpfile+'.txt', data, header=dataset_name)
                subprocess.Popen( igorpath+' '+ igortmpfile+'.txt')

if __name__ == '__main__':
    import sys, h5py, os, numpy as np

    print os.getcwd()
    app = get_qt_app()
    f = h5py.File('test.h5', 'w')
    f.create_dataset('dset1', data=np.linspace(-1, 1, 100))
    g = f.create_group('group1')
    g.create_dataset('dset2', data=np.linspace(-1, 1, 100) ** 2)
    g = g.create_group('group2')
    g.create_dataset('dset3', data=np.linspace(-1, 1, 100).reshape(10, 10))
    ui = HDF5Browser(f)
    ui.show()
    sys.exit(app.exec_())
    f.close()
