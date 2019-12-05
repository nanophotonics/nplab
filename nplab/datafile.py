"""
NPLab Data Files
================

This module provides the DataFile class, a subclass of h5py's File class with a few extended functions.  The Groups returned by a DataFile are subclassed h5py Groups, again to facilitate extended functions.


:author: Richard Bowman
"""
from __future__ import print_function

from builtins import str
from past.builtins import basestring
__author__ = "rwb27"

import h5py
import os
import os.path
import datetime
import re
import sys
from collections import Sequence
import nplab.utils.version
import numpy as np
from nplab.utils.show_gui_mixin import ShowGUIMixin
from nplab.utils.array_with_attrs import DummyHDF5Group


def attributes_from_dict(group_or_dataset, dict_of_attributes):
    """Update the metadata of an HDF5 object with a dictionary."""
    attrs = group_or_dataset.attrs
    for key, value in list(dict_of_attributes.items()):
        if value is not None:
            try:
                attrs[key] = value
            except TypeError:
                print("Warning, metadata {0}='{1}' can't be saved in HDF5.  Saving with str()".format(key, value))
                attrs[key] = str(value)
    #group_or_dataset.attrs.update(dict_of_attributes) #We can't do this - we'd lose the error handling.


def h5_item_number(group_or_dataset):
    """Returns the number at the end of a group/dataset name, or None."""
    m = re.search(r"(\d+)$", group_or_dataset.name)  # match numbers at the end of the name
    return int(m.groups()[0]) if m else None


#TODO: merge with the current_datafile system
def get_data_dir(destination='local', rel_path='Desktop/Data'):
    """Creates a path to a specified data storage location."""
    if destination == 'local':
        home_dir = os.path.expanduser('~')
        path = os.path.join(home_dir, rel_path)
    elif destination == 'server':
        if sys.platform == 'windows':
            network_dir = 'R:'
        elif sys.platform == 'darwin':
            network_dir = '/Volumes/NPHome'
        path = os.path.join(network_dir, rel_path)
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def get_filename(data_dir, basename='data', fformat='.h5'):
    """Creates a dated directory path and returns a file name to open a file there."""
    date = datetime.datetime.now()
    output_dir = os.path.join(data_dir, str(date.year),
                              '{:02d}'.format(date.month)+'. '+date.strftime('%b'),
                              '{:02d}'.format(date.day))
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    file_path = os.path.join(output_dir,basename+fformat)
    return file_path


def get_unique_filename(data_dir, basename='data', fformat='.h5'):
    """Creates a dated directory path and returns a unique file name to open a file there."""
    date = datetime.datetime.now()
    output_dir = os.path.join(data_dir, str(date.year),
                              '{:02d}'.format(date.month)+'. '+date.strftime('%b'),
                              '{:02d}'.format(date.day), basename+'s')
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    unique_id = 1
    file_path = os.path.join(output_dir,basename+'_'+str(unique_id)+fformat)
    while os.path.exists(file_path):
        unique_id += 1
        file_path = os.path.join(output_dir,basename+'_'+str(unique_id)+fformat)
    return file_path


def get_file(destination='local', rel_path='Desktop/Data',
             basename='data', fformat='.h5', set_current=True):
    """Convenience function to quickly get a current DataFile object."""
    data_dir = get_data_dir(destination, rel_path)
    fname = get_filename(data_dir, basename, fformat)
    f = DataFile(fname)
    if set_current:
        f.make_current()
    return f
    

def transpose_datafile(data_set):
    ''' A function that opens a datafile, transposes and resaves'''
    parent = data_set.parent
    transposed_datafile = np.copy(data_set[...].T)
    file_name = data_set.name.split('/')[-1]
    del parent[file_name]
    parent.create_dataset(file_name,data = transposed_datafile)

def wrap_h5py_item(item):
    """Wrap an h5py object: groups are returned as Group objects, datasets are unchanged."""
    if isinstance(item, h5py.Group):
        # wrap groups before returning them (this makes our group objects rather than h5py.Group)
        return Group(item.id)
    else:
        return item  # for now, don't bother wrapping datasets
        
def sort_by_timestamp(hdf5_group):
    """a quick function for sorting hdf5 groups (or files or dictionarys...) by timestamp """
    keys = list(hdf5_group.keys())
    try:
        time_stamps = []
        for value in list(hdf5_group.values()):
            time_stamp_str = value.attrs['creation_timestamp']
            try:
                time_stamp_float = datetime.datetime.strptime(time_stamp_str,"%Y-%m-%dT%H:%M:%S.%f")
            except ValueError:
                time_stamp_str =  time_stamp_str+'.0'
                time_stamp_float = datetime.datetime.strptime(time_stamp_str,"%Y-%m-%dT%H:%M:%S.%f")
            time_stamps.append(time_stamp_float)
        keys = np.array(keys)[np.argsort(time_stamps)]
    except KeyError:
        keys.sort(key=split_number_from_name)
    items_lists = [[key,hdf5_group[key]] for key in keys]
    return items_lists
class Group(h5py.Group, ShowGUIMixin):
    """HDF5 Group, a collection of datasets and subgroups.

    NPLab "wraps" h5py's Group objects to provide extra functions.
    """

    def __getitem__(self, key):
        item = super(Group, self).__getitem__(key)  # get the dataset or group
        return wrap_h5py_item(item) #wrap as a Group if necessary
        
    @property
    def parent(self):
        """Return the group to which this object belongs."""
        return wrap_h5py_item(super(Group,self).parent)

    def find_unique_name(self, name):
        """Find a unique name for a subgroup or dataset in this group.

        :param name: If this contains a %d placeholder, it will be replaced with the lowest integer such that the new name is unique.  If no %d is included, _%d will be appended to the name if the name already exists in this group.
        """
        if "%d" not in name and name not in list(self.keys()):
            return name  # simplest case: it's a unique name
        else:
            n = 0
            if "%d" not in name:
                name += "_%d"
            while (name % n) in self:
                n += 1  # increase the number until the name's unique
            return (name % n)

    def numbered_items(self, name):
        """Get a list of datasets/groups that have a given name + number,
        sorted by the number appended to the end.

        This function is intended to return items saved with
        auto_increment=True, in the order they were added (by default they
        come in alphabetical order, so 10 comes before 2).  `name` is the
        name passed in without the _0 suffix.
        """
        items = [wrap_h5py_item(v) for k, v in list(self.items())
                 if k.startswith(name)  # only items that start with `name`
                 and re.match(r"_*(\d+)$", k[len(name):])]  # and end with numbers
        return sorted(items, key=h5_item_number)

    def count_numbered_items(self, name):
        """Count the number of items that would be returned by numbered_items
        
        If all you need to do is count how many items match a name, this is
        a faster way to do it than len(group.numbered_items("name")).
        """
        n = 0
        for k in list(self.keys()):
            if k.startswith(name) and re.match(r"_*(\d+)$", k[len(name):]):
                n += 1
                return n

    def create_group(self, name, attrs=None, auto_increment=True, timestamp=True):
        """Create a new group, ensuring we don't overwrite old ones.

        A new group is created within this group, with the specified name.
        If auto_increment is True (the default) then a number is used to ensure
        the name is unique.

        :param name: The name of the new group.  May contain a %d placeholder
        as described in find_unique_name()
        :param auto_increment: True by default, which invokes the unique name
        behaviour described in find_unique_name.  Set this to False to cause
        an error if the desired name exists already.
        """
        if auto_increment and name is not None:
            name = self.find_unique_name(name) #name is None if creating via the dict interface
        g = super(Group, self).create_group(name)
        if timestamp:
            g.attrs.create('creation_timestamp', datetime.datetime.now().isoformat().encode())
        if attrs is not None:
            attributes_from_dict(g, attrs)
        return Group(g.id)  # make sure it's wrapped!

    def require_group(self, name):
        """Return a subgroup, creating it if it does not exist."""
        return Group(super(Group, self).require_group(name).id)  # wrap the returned group

    def create_dataset(self, name, auto_increment=True, shape=None, dtype=None,
                       data=None, attrs=None, timestamp=True,autoflush = True, *args, **kwargs):
        """Create a new dataset, optionally with an auto-incrementing name.

        :param name: the name of the new dataset
        :param auto_increment: if True (default), add a number to the dataset name to
            ensure it's unique.  To force the addition of a number, append %d to the dataset name.
        :param shape: a tuple describing the dimensions of the data (only needed if data is not specified)
        :param dtype: data type to be saved (if not specifying data)
        :param data: a numpy array or equivalent, to be saved - this specifies dtype and shape.
        :param attrs: a dictionary of metadata to be saved with the data
        :param timestamp: if True (default), we save a "creation_timestamp" attribute with the current time.

        Further arguments are passed to h5py.Group.create_dataset.
        """
        if auto_increment and name is not None: #name is None if we are creating via the dict interface
            name = self.find_unique_name(name)
        dset = super(Group, self).create_dataset(name, shape, dtype, data, *args, **kwargs)
        if timestamp:
            dset.attrs.create('creation_timestamp', datetime.datetime.now().isoformat().encode())
        if hasattr(data, "attrs"): #if we have an ArrayWithAttrs, use the attrs!
            attributes_from_dict(dset, data.attrs)
        if attrs is not None:
            attributes_from_dict(dset, attrs)  # quickly set the attributes
        if autoflush==True:
            dset.file.flush()
        return dset

    create_dataset.__doc__ += '\n\n'+h5py.Group.create_dataset.__doc__

    def require_dataset(self, name, auto_increment=True, shape=None, dtype=None, data=None, attrs=None, timestamp=True,
                        *args, **kwargs):
        """Require a new dataset, optionally with an auto-incrementing name."""
        if name not in self:
            dset = self.create_dataset(name, auto_increment, shape, dtype, data, attrs, timestamp,
                                       *args, **kwargs)
        else:
            dset = self[name]
        return dset

    def create_resizable_dataset(self, name, shape=(0,), maxshape=(None,), auto_increment=True, dtype=None, attrs=None, timestamp=True,
                                 *args, **kwargs):
        """See create_dataset documentation"""
        return self.create_dataset(name, auto_increment, shape, dtype, attrs, timestamp,
                                   maxshape=maxshape, chunks=True, *args, **kwargs)

    def require_resizable_dataset(self, name, shape=(0,), maxshape=(None,), auto_increment=True, dtype=None, attrs=None, timestamp=True,
                                  *args, **kwargs):
        """Create a resizeable dataset, or return the dataset if it exists."""
        if name not in self:
            dset = self.create_resizable_dataset(name, shape, maxshape, auto_increment, dtype, attrs, timestamp,
                                                 *args, **kwargs)
        else:
            dset = self[name]
        return dset

    def update_attrs(self, attribute_dict):
        """Update (create or modify) the attributes of this group."""
        attributes_from_dict(self, attribute_dict)

    def append_dataset(self, name, value, dtype=None):
        """Append the given data to an existing dataset, creating it if it doesn't exist."""
        if name not in self:
            if hasattr(value, 'shape'):
                shape = (0,)+value.shape
                maxshape = (None,)+value.shape
            elif isinstance(value, Sequence):
                shape = (0, len(value))
                maxshape = (None, len(value))  # tuple(None for i in shape)
            else:
                shape=(0,)
                maxshape = (None,)
            dset = self.require_dataset(name, shape=shape, dtype=dtype,
                                        maxshape=maxshape, chunks=True)
        else:
            dset = self[name]
        index = dset.shape[0]
        dset.resize(index+1,0)
        dset[index,...] = value

    def get_qt_ui(self):
        """Return a file browser widget for this group."""
        # Sorry about the dynamic import - the alternative is always
        # requiring Qt to access data files, and I think that's worse.
        from nplab.ui.hdf5_browser import HDF5Browser
        return HDF5Browser(self)

    @property
    def basename(self):
        """Return the last part of self.name, i.e. just the final component of the path."""
        return self.name.rsplit("/", 1)[-1]
        
    def timestamp_sorted_items(self):
        """Return a sorted list of items """
        return sort_by_timestamp(self)

class DataFile(Group):
    """Represent an HDF5 file object.

    For the moment, this just represents the root group, as it's far easier!  May
    change in the future...
    """

    def __init__(self, name, mode=None, save_version_info=False,
                 update_current_group = True, *args, **kwargs):
        """Open or create an HDF5 file.

        :param name: The filename/path of the HDF5 file to open or create, or an h5py File object
        :param mode: Mode to open the file in, one of:
            r
                Read-only, file must exist
            r+
                Read/write, file must exist
            w
                Create the file, deleting it if it exists
            w-
                Create the file, fail with an error if it exists
            a
                Open read/write if the file exists, otherwise create it.
        :param save_version_info: If True (default), save a string attribute at top-level
        with information about the current module and system.
        """
        if isinstance(name, h5py.File):
            f=name #if it's already an open file, just use it
        else:
            f = h5py.File(name, mode, *args, **kwargs)  # open the file
        super(DataFile, self).__init__(f.id)  # initialise a Group object with the root group of the file (saves re-wrapping all the functions for File)
        if save_version_info and self.file.mode != 'r':
            #Save version information if needed
            n=0
            while "version_info_%04d" % n in self.attrs:
                n += 1
            try:
                self.attrs.create("version_info_%04d" % n, np.string_(nplab.utils.version.version_info_string()))
            except:
               print("Error: could not save version information")
        self.update_current_group = update_current_group

    def flush(self):
        self.file.flush()

    def close(self):
        self.file.close()

    def make_current(self):
        """Set this as the default location for all new data."""
        global _current_datafile
        _current_datafile = self
        
    @property
    def filename(self):
        """ Returns the filename (full path) of the current datafile """
        return self.file.filename
     
    @property
    def dirname(self):
        """ Returns the path of the datafolder the current datafile is in"""
        return os.path.dirname(self.file.filename)

_current_datafile = None

def current(create_if_none=True, create_if_closed=True, mode='a',working_directory = None):
    """Return the current data file, creating one if it does not exist.

    Arguments:
        create_if_none : bool (optional, default True)
            Attempt to pop up a file dialog and create a new file if necessary.
            The default is True, i.e. do this if there's no current file.
        create_if_closed: bool (optional, default True)
            If the current data file is closed, create a new one.
        mode : str (optional, default 'a')
            The HDF5 mode to use for the file.  Sensible modes would be:
                'a': create if it doesn't exist, or append to an existing file
                'r': read-only
                'w-': read-write, delete the file if it already exists
                'r+': read-write, file must exist already.
    """
    # TODO: if file previously used but closed don't ask to recreate but use config to open
    global _current_datafile
    if create_if_closed:  # try to access the file - if it's closed, it will fail
        try:
            list(_current_datafile.keys())
        except:  # if the file is closed, set it to none so we make a new one.
            _current_datafile = None

    if _current_datafile is None and create_if_none:
        print("No current data file, attempting to create...")
        if working_directory==None:
            working_directory=os.getcwd()
        try:  # we try to pop up a Qt file dialog
            import nplab.utils.gui
            from nplab.utils.gui import QtGui
            from nplab.utils.gui import QtWidgets
            app = nplab.utils.gui.get_qt_app()  # ensure Qt is running
            fname = QtWidgets.QFileDialog.getSaveFileName(
                caption="Select Data File",
                directory=os.path.join(working_directory, datetime.date.today().strftime("%Y-%m-%d.h5")),
                filter="HDF5 Data (*.h5 *.hdf5)",
                options=QtWidgets.QFileDialog.DontConfirmOverwrite,
            )
            if not isinstance(fname, str):
                fname = fname[0]  # work around version-dependent Qt behaviour :(
            if len(fname) > 0:
                print(fname)
                if not "." in fname:
                    fname += ".h5"
                set_current(fname, mode=mode)
            #                if os.path.isfile(fname): #FIXME: dirty hack to work around mode=a not working
            #                    set_current(fname,mode='r+')
            #                else:
            #                    set_current(fname,mode='w-') #create the datafile
            else:
                print("Cancelled by the user.")
        except Exception as e:
            print("File dialog went wrong :(")
            print(e)

    if _current_datafile is not None:
        return _current_datafile  # if there is a file (or we created one) return it
    else:
        raise IOError("Sorry, there is no current file to return.")


def set_current(datafile, **kwargs):
    """Set the current datafile, specified by either an HDF5 file object or a filepath"""
    global _current_datafile
    if isinstance(datafile, DataFile):
        _current_datafile = datafile
        return _current_datafile
    elif isinstance(datafile, h5py.Group):
        _current_datafile = DataFile(datafile)
        return _current_datafile
    else:
        print("opening file: ", datafile)
        try:
            _current_datafile = DataFile(datafile, **kwargs)  # open a new datafile
            return _current_datafile
        except Exception as e:
            print("problem opening file:")
            print(e)
            print("trying with mode=r+")
            kwargs['mode'] = 'r+'  # dirty hack to work around mode=a not working
            _current_datafile = DataFile(datafile, **kwargs)

def set_temporary_current_datafile():
    """Create a temporary datafile, for testing purposes."""
    nplab.log("WARNING: using a temporary file")
    print("WARNING: using a file in memory as the current datafile.  DATA WILL NOT BE SAVED.")
    df = h5py.File("temporary_file.h5", driver='core', backing_store=False)
    return set_current(df)

def close_current():
    """Close the current datafile"""
    if _current_datafile is not None:
        try:
            _current_datafile.close()
        except:
            print("Error closing the data file")
_current_group = None
_use_current_group = False
def set_current_group(selected_object):
    '''Grabs the currently selected group, using the parent group if a dataset is selected.
    This only works if the datafile the group resides in is the current datafile'''
    global _current_group
    try:
        if type(selected_object) == DummyHDF5Group:
            potential_group = list(selected_object.values())[0]
        else:
            potential_group = selected_object
        if type(selected_object) == Group or type(selected_object)==h5py.Group:
            _current_group =  wrap_h5py_item(selected_object)
        else:
            _current_group = wrap_h5py_item(potential_group.parent)
    except AttributeError:
        _current_group = current()

def open_file(set_current_bool = True,mode = 'a'):
    """Open an existing data file"""
    global _current_datafile
    try:  # we try to pop up a Qt file dialog
        import nplab.utils.gui
        from nplab.utils.gui import QtGui,QtWidgets
        app = nplab.utils.gui.get_qt_app()  # ensure Qt is running
        fname = QtWidgets.QFileDialog.getOpenFileName(
            caption="Select Existing Data File",
            directory=os.path.join(os.getcwd()),
            filter="HDF5 Data (*.h5 *.hdf5)",
#            options=qtgui.QFileDialog.DontConfirmOverwrite,
        )
        if not isinstance(fname, str):
            fname = fname[0]  # work around version-dependent Qt behaviour :(
        if len(fname) > 0:
            print(fname)
            if set_current_bool == True:
                set_current(fname, mode=mode)
            else:
                return DataFile(fname,mode = mode )
        else:
            print("Cancelled by the user.")
    except Exception as e:
            print("File dialog went wrong :(")
            print(e)

    return _current_datafile  # if there is a file return it

def create_file(set_current_bool = False,mode = 'a'):
    """Create a data file"""
    global _current_datafile
    try:  # we try to pop up a Qt file dialog
        import nplab.utils.gui
        from nplab.utils.gui import QtGui,QtWidgets
        app = nplab.utils.gui.get_qt_app()  # ensure Qt is running
        fname = QtWidgets.QFileDialog.getSaveFileName(
            caption="Select Existing Data File",
            directory=os.path.join(os.getcwd()),
            filter="HDF5 Data (*.h5 *.hdf5)",
#            options=qtgui.QFileDialog.DontConfirmOverwrite,
        )
        if not isinstance(fname, str):
            fname = fname[0]  # work around version-dependent Qt behaviour :(
        if len(fname) > 0:
            print(fname)
            if set_current_bool == True:
                set_current(fname, mode=mode)
            else:
                return DataFile(fname,mode = mode )
        else:
            print("Cancelled by the user.")
    except Exception as e:
            print("File dialog went wrong :(")
            print(e)

    return _current_datafile  # if there is a file return it


if __name__ == '__main__':
    help(Group.create_dataset)
