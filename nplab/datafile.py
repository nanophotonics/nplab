"""
NPLab Data Files
================

This module provides the DataFile class, a subclass of h5py's File class with a few extended functions.  The Groups returned by a DataFile are subclassed h5py Groups, again to facilitate extended functions.


:author: Richard Bowman
"""

__author__ = "rwb27"

import h5py
from traitsui.file_dialog import save_file

class Group(h5py.Group):
    """HDF5 Group, a collection of datasets and subgroups.

    NPLab "wraps" h5py's Group objects to provide extra functions.
    """
    def __getitem__(self,key):
        item = super(Group, self).__getitem__(key) #get the dataset or group
        if isinstance(item, h5py.Group):
            return Group(item.id) #wrap groups before returning them (this makes our group objects rather than h5py.Group)
        else:
            return item #for now, don't bother wrapping datasets

    def find_unique_name(self, name):
        """Find a unique name for a subgroup or dataset in this group.
        
        :param name: If this contains a %d placeholder and auto_increment is True, it will be replaced with the lowest integer such that the new name is unique.  If no %d is included, _%d will be appended to the name if the name already exists in this group.
        """
        if "%d" not in name and name not in self:
            return name #simplest case: it's a unique name
        else:
            n=0
            if "%d" not in name:
                name += "_%d"
            while (name % n) in self:
                n += 1 #increase the number until the name's unique
            return (name % n)

    def create_group(self, name, auto_increment=True):
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
        if auto_increment:
            name = self.find_unique_name(name)
        return super(Group, self).create_group(name)

    def create_dataset(self, name, auto_increment=True, shape=None,dtype=None,data=None,*args,**kwargs):
        """Create a new dataset, optionally with an auto-incrementing name."""
        if auto_increment:
            name = self.find_unique_name(name)
        return super(Group, self).create_dataset(name, shape, dtype, data, *args, **kwargs)

class DataFile(Group):
    """Represent an HDF5 file object.  
    
    For the moment, this just represents the root group, as it's far easier!  May
    change in the future...
    """
    def __init__(self, name, mode=None, *args, **kwargs):
        """Open or create an HDF5 file.

        :param name: The filename/path of the HDF5 file to open or create.
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
        """
        f = h5py.File(name, mode, *args, **kwargs) #open the file
        super(DataFile, self).__init__(f.id) #this is actually just an h5py group object!
    def make_current(self):
        """Set this as the default location for all new data."""
        global _current_datafile
        _current_datafile = self

_current_datafile = None

def current(create_if_none=True):
    """Return the current data file, creating one if it does not exist."""
    global _current_datafile
    if _current_datafile is not None:
        return _current_datafile
    elif create_if_none:
        raise NotImplementedError("File dialog not yet implemented: create a file manually and set it as the current one, with nplab.datafile.set_current(filename).")
    else:
        raise IOError("Sorry, there is no current file to return.")

def set_current(datafile, **kwargs):
    """Set the current datafile, specified by either an HDF5 file object or a filepath"""
    global _current_datafile
    if isinstance(datafile, h5py.Group):
        _current_datafile = datafile
    else:
        _current_datafile = DataFile(datafile, **kwargs) #open a new datafile

