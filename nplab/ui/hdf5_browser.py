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
    def __init__(self, 
                 item=None, 
                 parent=None, 
                 figure_widget=None,
                 show_controls=True, 
                 show_refresh=True, 
                 renderer_combobox=None,
                 refresh_button=None,
                 copy_button=None,
                 default_button=None,
                 ):
        """Create a viewer widget for any dataset or datagroup object
        
        Arguments:
        item : HDF5 group or dataset (optional)
            The dataset (or group) to display
        parent : QWidget (optional)
            The Qt parent of the widget.
        show_controls : bool (optional)
            If True (default), show the refresh button and combobox.  If False,
            just show the renderer.
        show_refresh : bool (optional)
            If show_controls is True, this sets whether the refresh button is
            visible.
        renderer_combobox : QComboBox (optional)
            If this is specified, use the supplied combobox instead of creating
            a new one.  You probably want to specify show_controls=False.
        refresh_button : QPushButton (optional)
            If specified, use the supplied button instead of creating one.
        copy_button : QPushButton (optional)
            If specified, use the supplied button instead of creating one.
        default_button : QPushButton (optional)
            If specified, use the supplied button to select the default 
            rendererinstead of creating one.
        """
        super(HDF5ItemViewer, self).__init__(parent)
        
        if figure_widget is None: 
            self.figure_widget = QtGui.QWidget()
        else:
            self.figure_widget = figure_widget
            
        if renderer_combobox is None:       
            self.renderer_combobox = QtGui.QComboBox()
        else:
            self.renderer_combobox = renderer_combobox
        self.renderer_combobox.activated[int].connect(self.renderer_selected)        
        
        if refresh_button is None:
            self.refresh_button = QtGui.QPushButton()
            self.refresh_button.setText("Refresh Figure")
        else:
            self.refresh_button = refresh_button
        self.refresh_button.clicked.connect(self.refresh)
        
        if default_button is not None:
            self.default_button = default_button
            self.default_button.clicked.connect(self.default_renderer)
        
        if copy_button is None:
            self.copy_button = QtGui.QPushButton()
            self.copy_button.setText("Copy Figure")
        else:
            self.copy_button = copy_button
        self.copy_button.clicked.connect(self.CopyActivated)
        self.clipboard = QtGui.QApplication.clipboard()
        
        self.setLayout(QtGui.QVBoxLayout())
        self.layout().addWidget(self.figure_widget, stretch=1)
        self.layout().setContentsMargins(0,0,0,0)
        
        self.renderers = list()
        
        if show_controls: # this part may be broken
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
    
    def default_renderer(self):
        self.renderer_combobox.setCurrentIndex(0)
        self.renderer_selected(0)
        self.refresh()
    
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
    
    def CopyActivated(self):
        """Copy an image of the currently-displayed figure."""
        ## TO DO: move this to the HDF5 viewer
        Pixelmap = QtGui.QPixmap.grabWidget(self.figure_widget)
        self.clipboard.setPixmap(Pixelmap)
        print "Figure copied to clipboard."

def split_number_from_name(name):
    """Return a tuple with the name and an integer to allow sorting."""
    basename = name.rstrip('0123456789')
    try:
        return (basename, int(name[len(basename):-1]))
    except:
        return (basename, -1)

class HDF5Tree(QtGui.QWidget, UiTools):
    """Create a tree widget for any HDF5 file contents
    
    Arguments:
    f : HDF5 file
    treeWidget : QTreeWidget
        If this is specified, use the supplied tree widget combobox instead of 
        creating a new one.
    refresh_button : QPushButton
        If specified, use the supplied button instead of creating one.
    """
    
    def __init__(self, 
                 f,
                 treeWidget, 
                 refresh_button,
                 parent=None,
                 ):
        super(HDF5Tree, self).__init__(parent)
        self.f = f 
        
        try:
            self.root_name = self.f.filename
        except AttributeError:
            self.root_name = self.f.file.filename
        self.setWindowTitle(self.root_name)
        
        if treeWidget is None:
            self.treeWidget = QtGui.QTreeWidget()
        else:
            self.treeWidget = treeWidget
        self.addItems(self.treeWidget.invisibleRootItem()) # tried to make supplying the tree widget object but got an error here
        self.treeWidget.customContextMenuRequested.connect(self.context_menu)
        self.treeWidget.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection) #allow multiple items to be selected
        
        if refresh_button is None:
            self.refresh_button = QtGui.QPushButton()
            self.refresh_button.setText("Refresh")
        else:
            self.refresh_button = refresh_button
        self.refresh_button.clicked.connect(self.refresh)
        
        
    
    def addItems(self, parent):
        """Populate the tree view with the contents of the HDF5 file."""
        self._items_added = []
        root = self.addToTree(parent, self.f, name=self.root_name, add_children=True)
        self.treeWidget.expandToDepth(0) # auto-expand first level

    def addToTree(self, parent, h5item, name=None, add_children=True):
        """Add an HDF5 item to the tree view as a child of the given item.

        If add_children is True (default), this works recursively and adds the
        supplied HDF5 item's children (if any) to the tree.
        """
        if h5item in self._items_added: # guard against circular links
            print "Recursion detected, stopping!"
            return
        if name is None:
            name = h5item.name.rsplit('/', 1)[-1]
        item = QtGui.QTreeWidgetItem(parent, [name]) #add the item
        item.setData(0, QtCore.Qt.UserRole, h5item) #save a reference
        self._items_added.append(h5item)

        if add_children:
            try:
                keys = h5item.keys()
                keys.sort(key=split_number_from_name)
                for k in keys:
                    self.addToTree(item, h5item[k])
            except:
                pass # if there are no items to add, just stop.
        return item
        

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

    
    
    
        


class HDF5Browser(QtGui.QWidget, UiTools):
    """A Qt Widget for browsing an HDF5 file and graphing the data.
    """

    def __init__(self, f, parent=None):
        super(HDF5Browser, self).__init__(parent)
        self.f = f #TODO: don't call this f - call it data_group or something.
        # self.setupUi(self)
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'hdf5_browser.ui'), self)

        self.tree = HDF5Tree(f,
                             parent=self,
                             treeWidget=self.treeWidget, 
                             refresh_button=self.refreshTreeButton,
                             )
        self.tree.treeWidget.itemClicked.connect(self.on_click)
                
        self.viewer = HDF5ItemViewer(parent=self, 
                                     figure_widget=self.figureWidget,
                                     show_controls=False, 
                                     renderer_combobox = self.rendererselection,
                                     refresh_button=self.refreshFigureButton,
                                     copy_button=self.CopyButton,
                                     default_button=self.defaultButton,
                                     )             
        self.replace_widget(self.figureWidgetContainer, self.figureWidget, self.viewer)
        
        
    def __del__(self):
        pass  # self.f.close()
    
    
    def on_click(self, item, column):
        """Handle clicks on items in the tree."""
        item.setExpanded(True)
        if len(self.tree.treeWidget.selectedItems())>1: 
            self.viewer.data = [treeitem.data(column, QtCore.Qt.UserRole) for treeitem in self.tree.treeWidget.selectedItems() ]
        else:
            self.viewer.data = item.data(column, QtCore.Qt.UserRole)

    

if __name__ == '__main__':
    import sys, h5py, os, numpy as np
    import nplab
    from nplab.utils.gui import get_qt_app

    print os.getcwd()
    app = get_qt_app()
    
#    f = h5py.File('test.h5', 'w')
#    f.create_dataset('dset1', data=np.linspace(-1, 1, 100))
#    f.create_dataset('dset2', data=np.linspace(-1, 1, 100) ** 3)
#    g = f.create_group('group1')
#    g.create_dataset('dset2', data=np.linspace(-1, 1, 100) ** 2)
#    g = g.create_group('group2')
#    g.create_dataset('dset3', data=np.linspace(-1, 1, 100).reshape(10, 10))
#    ui = HDF5Browser(f)
#    ui.show()
#    sys.exit(app.exec_())
#    f.close()

    data_file = h5py.File('C:/Users/Ana Andres/Documents/Python Scripts/2016-05-17.h5', 'r')
#    data_file = nplab.datafile.open_file()
    ui = HDF5Browser(data_file)
    ui.show()