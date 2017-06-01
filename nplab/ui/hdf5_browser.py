"""
A Qt GUI to browse the contents of an HDF5 file

This uses a tree view to show the file's contents, and has a plugin-based "renderer"
system to display the datasets.  See `nplab.ui.data_renderers` for that.

"""

__author__ = 'Alan Sanders, Will Deacon, Richard Bowman'

import nplab
from nplab.utils.gui import QtCore, QtGui, QtWidgets, uic
import matplotlib
import numpy as np
import h5py

matplotlib.use('Qt4Agg')
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from nplab.ui.data_renderers import suitable_renderers
from nplab.ui.ui_tools import UiTools
import functools
from nplab.utils.array_with_attrs import DummyHDF5Group

import subprocess
import os


# base, widget = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'hdf5_browser.ui'))

class HDF5ItemViewer(QtWidgets.QWidget, UiTools):
    """A Qt Widget for visualising one HDF5 element (group or dataset)."""
    def __init__(self, 
                 item=None, 
                 parent=None, 
                 figure_widget=None,
                 show_controls=True, 
                 show_refresh=True,
                 show_default_button=True,
                 show_copy=True,
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
            self.figure_widget = QtWidgets.QWidget()
        else:
            self.figure_widget = figure_widget
            
        if renderer_combobox is None:       
            self.renderer_combobox = QtWidgets.QComboBox()
        else:
            self.renderer_combobox = renderer_combobox
        self.renderer_combobox.activated[int].connect(self.renderer_selected)        
        
        if refresh_button is None:
            self.refresh_button = QtWidgets.QPushButton()
            self.refresh_button.setText("Refresh Figure")
        else:
            self.refresh_button = refresh_button
        self.refresh_button.clicked.connect(self.refresh)
        
        if default_button is None:
            self.default_button = QtWidgets.QPushButton()
            self.default_button.setText("Default Renderer")
        else:
            self.default_button = default_button
        self.default_button.clicked.connect(self.default_renderer)
        
        if copy_button is None:
            self.copy_button = QtWidgets.QPushButton()
            self.copy_button.setText("Copy Figure")
        else:
            self.copy_button = copy_button
        self.copy_button.clicked.connect(self.CopyActivated)
        self.clipboard = QtWidgets.QApplication.clipboard()

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.figure_widget, stretch=1)
        self.layout().setContentsMargins(0,0,0,0)
        
        self.renderers = list()
        
        if show_controls: # this part may be broken
            hb = QtWidgets.QHBoxLayout()
            hb.addWidget(self.renderer_combobox, stretch=1)
            if show_refresh:
                hb.addWidget(self.refresh_button, stretch=0)
            if show_copy:
                hb.addWidget(self.copy_button, stretch=0)
            if show_default_button:
                hb.addWidget(self.default_button, stretch=0)
            self.layout().addLayout(hb, stretch=0)
        
    _data = None
        
    @property
    def data(self):
        """The dataset or group we are displaying"""
        return self._data
        
    @data.setter
    def data(self, newdata):
        if newdata == None:
            return None
        
        self._data = newdata

        # When data changes, update the list of renderers
        renderers = suitable_renderers(self.data)
        combobox = self.renderer_combobox
        previous_selection = combobox.currentIndex() # remember previous choice
        try:#Attempt to keep the same range
            previous_view_rect = self.figure_widget.figureWidget.viewRect()
        except AttributeError:
            previous_view_rect = None
            
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
                try:
                    self.renderer_selected(index)
                except Exception as e:
                    print 'The selected renderer failed becasue',e

        except ValueError:
            combobox.setCurrentIndex(0)
            self.renderer_selected(0)
        if previous_view_rect != None:
            try:
                self.figure_widget.figureWidget.setRange(previous_view_rect, padding=0)                                      
            except AttributeError:
                pass
    
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
            self.renderer = QtWidgets.QWidget()
        
    def refresh(self):
        """Re-render the data, using the current renderer (if it is still appropriate)"""
        self.data = self.data

    
    def CopyActivated(self):
        """Copy an image of the currently-displayed figure."""
        ## TO DO: move this to the HDF5 viewer
        print 'yes'
#        try:
#            Pixelmap = QtGui.QPixmap.grabWidget(self.figure_widget)
#        except Exception as e:
#            print 'Copy Failed due to', e
#        self.clipboard.setPixmap(Pixelmap)
#        print "Figure copied to clipboard."


def split_number_from_name(name):
    """Return a tuple with the name and an integer to allow sorting."""
    basename = name.rstrip('0123456789')
    try:
        return (basename, int(name[len(basename):-1]))
    except:
        return (basename, -1)
        
        
def igorOpen(dataset):
    """Open the currently-selected item in Igor Pro. If this is not working check your IGOR path!"""
    igorpath = '"C:\\Program Files (x86)\\WaveMetrics\\Igor Pro Folder\\Igor.exe"'
    igortmpfile = os.path.dirname(os.path.realpath(__file__))+'\Igor'
    igortmpfile=igortmpfile.replace("\\","\\\\")
    print igortmpfile
    open(igortmpfile, 'w').close()
    print "attempting to open {} in Igor".format(dataset)
    if isinstance(dataset,h5py.Dataset):
        dset = dataset
        data = np.asarray(dset[...])

        if data.ndim == 2:
            # RWB: why do we do this?  Why not just use a 2D text file and skip rescaling??
            from PIL import Image
            rescaled = (2**16 / data.max() * (data - data.min())).astype(np.uint8)

            im = Image.fromarray(rescaled.transpose())
            im.save(igortmpfile+'.tif')

            command='/X "ImageLoad/T=tiff/N= h5Data'+' \"'+ igortmpfile+'.tif\""'
            subprocess.Popen(igorpath+' '+command)
        else:
            print dataset
            np.savetxt(igortmpfile+'.txt', data, header=dataset.name)
            subprocess.Popen( igorpath+' '+ igortmpfile+'.txt')


class HDF5TreeItem(object):
    """A simple class to represent items in an HDF5 tree"""
    def __init__(self, data_file, parent, name, row):
        """Create a new item for an HDF5 tree

        data_file : HDF5 data file
            This is the file (NB must be the top-level group) containing everything
        parent : HDF5TreeItem
            The parent of the current item
        name : string
            The name of the current item (should be parent.name plus an extra component)
        row : int
            The index of the current item in the parent's children.
        """
        self.data_file = data_file
        self.parent = parent
        self.name = name
        self.row = row
        if parent is not None:
            assert name.startswith(parent.name)
            assert name in data_file

    @property
    def basename(self):
        """The last component of the item's path in the HDF5 file"""
        return self.name.rsplit('/')[-1]

    _has_children = None
    @property
    def has_children(self):
        """Whether or not this item has children"""
        if self._has_children is None:
            self._has_children = hasattr(self.data_file[self.name], "keys")
        return self._has_children

    _children = None
    @property
    def children(self):
        """Children of the current item (as HDF5TreeItems)"""
        if self.has_children is False:
            return []
        if self._children is None:
            keys = self.data_file[self.name].keys()
            keys.sort(key=split_number_from_name)
            self._children = [HDF5TreeItem(self.data_file, self, self.name.rstrip("/") + "/" + k, i)
                              for i, k in enumerate(keys)]
        return self._children

    def purge_children(self):
        """Empty the cached list of children"""
        try:
            if self._children is not None:
                for child in self._children:
                    child.purge_children() # We must delete them all the way down!
                    self._children.remove(child)
                    del child # Not sure if this is needed...
                self._children = None
            self._has_children = None
        except:
            print "{} failed to purge its children".format(self.name)

    @property
    def h5item(self):
        """The underlying HDF5 item for this tree item."""
        assert self.name in self.data_file, "Error, {} is no longer a valid HDF5 item".format(self.name)
        return self.data_file[self.name]

    def __del__(self):
        self.purge_children()

def print_tree(item, prefix=""):
    """Recursively print the HDF5 tree for debug purposes"""
    if len(prefix) > 16:
        return # recursion guard
    print prefix + item.basename
    if item.has_children:
        for child in item.children:
            print_tree(child, prefix + "  ")


class HDF5ItemModel(QtCore.QAbstractItemModel):
    """This model takes its data from an HDF5 Group for display in a tree.

    It loads the file as the tree is expanded for speed - in the future it might implement sanity checks to
    abort loading very long folders.
    """
    def __init__(self, data_group):
        """Represent an HDF5 group to a QTreeView or similar.
        :type data_group: nplab.datafile.Group
        """
        super(HDF5ItemModel, self).__init__()
        self.root_item = None
        self.data_group = data_group
        
    _data_group = None
    @property
    def data_group(self):
        """The HDF5 group object we're representing"""
        return self._data_group
    
    @data_group.setter
    def data_group(self, new_data_group):
        """Set the data group represented by the model"""
        if self.root_item is not None:
            del self.root_item
        self._data_group = new_data_group
        self.root_item = HDF5TreeItem(new_data_group.file, None, new_data_group.name, 0)

    def _index_to_item(self, index):
        """Return an HDF5TreeItem for a given index"""
        if index.isValid():
            return index.internalPointer()
        else:
            return self.root_item

    def index(self, row, column, parent_index):
        """Return the index of the <row>th child of parent

        :type row: int
        :type column: int
        :type parent: QtCore.QModelIndex
        """
        try:
            parent = self._index_to_item(parent_index)
            return self.createIndex(row, column, parent.children[row])
        except:
            return QtCore.QModelIndex()

    def parent(self, index=None):
        """Find the index of the parent of the item at a given index."""
        try:
            parent = self._index_to_item(index).parent
            return self.createIndex(parent.row, 0, parent)
        except:
            # Something went wrong with finding the parent so return an invalid index
            return QtCore.QModelIndex()

    def flags(self, index):
        """Return flags telling Qt what to do with the item"""
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def data(self, index, role):
        """The data represented by this item."""
        if role == QtCore.Qt.DisplayRole:
            return self._index_to_item(index).basename
        else:
            return None

    def headerData(self, section, orientation, role=None):
        """Return the header names - an empty string here!"""
        return [""]

    def rowCount(self, index):
        """The number of rows exposed by the model"""
        try:
            item = self._index_to_item(index)
            assert item.has_children
            return len(item.children)
        except:
            # if it doesn't have keys, assume there are no children.
            return 0

    def hasChildren(self, index):
        """Whether or not this object has children"""
        return self._index_to_item(index).has_children
        #try:
        #    assert hasattr(self._index_to_item(index), "keys")
        #    return True
        #except:
        #    return False

    def columnCount(self, index=None, *args, **kwargs):
        """Return the number of columns"""
        return 1

    def refresh_tree(self):
        """Reload the HDF5 tree, resetting the model

        This causes all cached HDF5 tree information to be deleted, and any views
        using this model will automatically reload.
        """
        self.beginResetModel()
        self.root_item.purge_children()
        self.endResetModel()

    def selected_h5item_from_view(self, treeview):
        """Given a treeview object, return the selection, as an HDF5 object, or a work-alike for multiple selection.

        If one item is selected, we will return the HDF5 group or dataset that is selected.  If multiple items are
        selected, we will return a dummy HDF5 group containing all selected items.
        """
        items = [self._index_to_item(index) for index in treeview.selectedIndexes()]
        if len(items) == 1:
            return items[0].h5item
        elif len(items) > 1:
            return DummyHDF5Group({item.name: item.h5item for item in items})
        else:
            return None

    def set_up_treeview(self, treeview):
        """Correctly configure a QTreeView to use this model.

        This will set the HDF5ItemModel as the tree's model (data source), and in the future
        may set up context menus, etc. as appropriate."""
        treeview.setModel(self) # Make the tree view use this object as its model
        # Set up a callback to allow us to customise the context menu
        treeview.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        treeview.customContextMenuRequested.connect(functools.partial(self.context_menu, treeview))
        # Allow multiple objects to be selected
        treeview.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

    def context_menu(self, treeview, position):
        """Generate a right-click menu for the items"""
        menu = QtWidgets.QMenu()
        actions = {}

        for operation in ['Refresh tree']:
            actions[operation] = menu.addAction(operation)
        action = menu.exec_(treeview.viewport().mapToGlobal(position))


        if action == actions['Refresh tree']:
            self.refresh_tree()


class HDF5TreeWidget(QtWidgets.QTreeView):
    """A TreeView for looking at an HDF5 tree"""
    def __init__(self, datafile, **kwargs):
        """Create a TreeView widget that views the contents of an HDF5 tree.

        Arguments:
            datafile : nplab.datafile.Group
            the HDF5 tree to show

        Additional keyword arguments are passed to the QTreeView constructor.
        You may want to include parent, for example."""
        QtWidgets.QTreeView.__init__(self, **kwargs)

        self.model = HDF5ItemModel(datafile)
        self.model.set_up_treeview(self)
        self.sizePolicy().setHorizontalStretch(0)


    def selected_h5item(self):
        """Return the current selection as an HDF5 item."""
        return self.model.selected_h5item_from_view(self)

    def __del__(self):
        del self.model # is this needed?  I'm never sure...
    

class HDF5Browser(QtWidgets.QWidget, UiTools):
    """A Qt Widget for browsing an HDF5 file and graphing the data.
    """

    def __init__(self, data_file, parent=None):
        super(HDF5Browser, self).__init__(parent)
        self.data_file = data_file

        self.treeWidget = HDF5TreeWidget(data_file,
                                         parent=self,
                                         )
        self.treeWidget.selectionModel().selectionChanged.connect(self.selection_changed)
        self.viewer = HDF5ItemViewer(parent=self, 
                                     show_controls=True,
                                     )
        self.refresh_tree_button = QtWidgets.QPushButton() #Create a refresh button
        self.refresh_tree_button.setText("Refresh Tree")
        
        #adding the refresh button
        self.treelayoutwidget = QtWidgets.QWidget()     #construct a widget which can then contain the refresh button and the tree
        self.treelayoutwidget.setLayout(QtWidgets.QVBoxLayout())
        self.treelayoutwidget.layout().addWidget(self.treeWidget)
        self.treelayoutwidget.layout().addWidget(self.refresh_tree_button) 
        
        self.refresh_tree_button.clicked.connect(self.treeWidget.model.refresh_tree)

        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.treelayoutwidget)       #Add newly constructed widget (treeview and button) to the splitter
        splitter.addWidget(self.viewer)
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().addWidget(splitter)

    def sizeHint(self):
        return QtCore.QSize(1024,768)

    def selection_changed(self, selected, deselected):
        """Callback function to update the displayed item when the tree selection changes."""
        try:
            self.viewer.data = self.treeWidget.selected_h5item()
        except Exception as e:
            print e, 'That could be corrupted'
            

    def __del__(self):
        pass  # self.data_file.close()
    
    
#    def on_click(self, item, column):
#        """Handle clicks on items in the tree."""
#        item.setExpanded(True) # auto expand the item upon click
#        if len(self.treeWidget.selectedItems())>1: 
#            self.viewer.data = DummyHDF5Group({treeitem.data(column, QtCore.Qt.UserRole).name : treeitem.data(column, QtCore.Qt.UserRole) \
#                                                for treeitem in self.tree.treeWidget.selectedItems() })
#        else:
#            self.viewer.data = item.data(column, QtCore.Qt.UserRole)
#             
             
if __name__ == '__main__':
    import sys, h5py, os, numpy as np
    import nplab
    from nplab.utils.gui import get_qt_app

    app = get_qt_app()
    
    data_file = h5py.File('test.h5', 'w')
    data_file.create_dataset('dset1', data=np.linspace(-1, 1, 100))
    data_file.create_dataset('dset2', data=np.linspace(-1, 1, 100) ** 3)
    g = data_file.create_group('group1')
    g.create_dataset('dset2', data=np.linspace(-1, 1, 100) ** 2)
    g = g.create_group('group2')
    g.create_dataset('dset3', data=np.linspace(-1, 1, 100).reshape(10, 10))
    ui = HDF5Browser(data_file)
    ui.show()
    sys.exit(app.exec_())
    data_file.close()

#    data_file = h5py.File('C:/Users/Ana Andres/Documents/Python Scripts/2016-05-17.h5', 'r')
#    data_file = nplab.datafile.open_file()
#    ui = HDF5Browser(data_file)
#    ui.show()
#    app.exec_()
#    data_file.close()
#    datafile = nplab.current_datafile() #datafile.DataFile("/Users/rwb27/Desktop/test.h5", mode="r")
 #   datafle.create_dataset()
#    tree = QtWidgets.QTreeView()
#    model = HDF5ItemModel(datafile)
#    model.set_up_treeview(tree)
#    tree.show()
#    app.exec_()
    #print_tree(model.root_item) (don't, it's recursive...)
  #  datafile.show_gui()
  #  datafile.close()