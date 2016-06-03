"""
A Qt GUI to browse the contents of an HDF5 file

This uses a tree view to show the file's contents, and has a plugin-based "renderer"
system to display the datasets.  See `nplab.ui.data_renderers` for that.

"""

__author__ = 'Alan Sanders, Will Deacon, Richard Bowman'

from nplab.utils.gui import uic, QtGui, QtCore
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

class HDF5ItemViewer(QtGui.QWidget, UiTools):
    """A Qt Widget for visualising one HDF5 element (group or dataset)."""
    def __init__(self, item=None, parent=None, show_controls=True, show_refresh=True):
        """Create a viewer widget for any dataset or datagroup object"""
        super(HDF5ItemViewer, self).__init__(parent)
        
        self.figure_widget = QtGui.QWidget()
        self.renderer_combobox = QtGui.QComboBox()
        self.renderer_combobox.activated[int].connect(self.renderer_selected)        
        
        self.refresh_button = QtGui.QPushButton()
        self.refresh_button.setText("Refresh")
        self.refresh_button.clicked.connect(self.refresh)
        
        self.setLayout(QtGui.QVBoxLayout())
        self.layout().addWidget(self.figure_widget, stretch=1)
        self.layout().setContentsMargins(0,0,0,0)
        
        if show_controls:
            hb = QtGui.QHBoxLayout()
            hb.addWidget(self.renderer_combobox, stretch=1)
            if show_refresh:
                hb.addWidget(self.refresh_button, stretch=0)
            self.layout().addLayout(hb, stretch=0)
        
    _data = None
        
    @property
    def data(self):
        """The dataset or group we are displaying"""
        return self._data
        
    @data.setter
    def data(self, newdata):
        self._data = newdata

        # When data changes, update the list of renderers
        renderers = suitable_renderers(self.data)
        combobox = self.renderer_combobox
        previous_selection = combobox.currentIndex() # remember previous choice
        combobox.clear()
        for i, renderer in enumerate(renderers):
            combobox.addItem(renderer.__name__, renderer)
            
        # Attempt to keep the same renderer as we had before - or use the 
        # "best" one.  NB setting the current index will trigger the renderer
        # to be created in renderer_selected
        try:
            if previous_selection == 0:
                raise ValueError() # if we didn't choose the last renderer, just
                            # pick the best one.  Otherwise, try to use the same
                            # renderer as we used before
            else:
                index = renderers.index(self.renderer.__class__)
                combobox.setCurrentIndex(index)
                self.renderer_selected(index)
        except ValueError:
            combobox.setCurrentIndex(0)
            self.renderer_selected(0)
            
    _renderer = None
    
    @property
    def renderer(self):
        """The data renderer currently in use in the widget"""
        return self._renderer
        
    @renderer.setter
    def renderer(self, new_renderer):
        self._renderer = new_renderer
        # Replace the current renderer in the GUI with the new one:
        self.figure_widget = self.replace_widget(self.layout(), self.figure_widget, new_renderer)
    
    def renderer_selected(self, index):
        """Change the figure widget to use the selected renderer."""
        # The class of the renderer is stored as the combobox data
        RendererClass = self.renderer_combobox.itemData(index)
        try:
            self.renderer = RendererClass(self.data, self)
        except TypeError:
            # If the box is empty (e.g. it's just been cleared) use a blank widget
            self.renderer = QtGui.QWidget()
        
    def refresh(self):
        """Re-render the data, using the current renderer (if it is still appropriate)"""
        self.data = self.data


class HDF5Browser(QtGui.QWidget, UiTools):
    """A Qt Widget for browsing an HDF5 file and graphing the data.
    """

    def __init__(self, f, parent=None):
        super(HDF5Browser, self).__init__(parent)
        self.f = f #TODO: don't call this f - call it data_group or something.
        # self.setupUi(self)
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'hdf5_browser.ui'), self)

        try:
            self.root_name = self.f.filename
        except AttributeError:
            self.root_name = self.f.file.filename
        self.setWindowTitle(self.root_name)
        
        self.viewer = HDF5ItemViewer(parent=self, show_controls=False)     
        self.replace_widget(self.figureWidgetContainer, self.figureWidget, self.viewer)
        
        self.addItems(self.treeWidget.invisibleRootItem())
        self.treeWidget.expandToDepth(0) # auto expand to first level
        self.treeWidget.itemClicked.connect(self.on_click)
        self.treeWidget.customContextMenuRequested.connect(self.context_menu)
        self.treeWidget.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection) #allow multiple items to be selected
        
        self.refreshButton.clicked.connect(self.refresh)
        self.CopyButton.clicked.connect(self.CopyActivated)
        self.clipboard = QtGui.QApplication.clipboard()
        
        self.replace_widget(self.controlLayout, self.rendererselection, self.viewer.renderer_combobox)
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
        self.treeWidget.expandToDepth(0) # auto expand to first level
        
  
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
            self.viewer.data = [treeitem.data(column, QtCore.Qt.UserRole) for treeitem in self.treeWidget.selectedItems() ]
        else:
            self.viewer.data = item.data(column, QtCore.Qt.UserRole)
        
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
