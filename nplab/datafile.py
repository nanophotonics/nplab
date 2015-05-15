"""
NPLab Data Files
================

This module provides the DataFile class, a subclass of h5py's File class with a few extended functions.  The Groups returned by a DataFile are subclassed h5py Groups, again to facilitate extended functions.


:author: Richard Bowman
"""

__author__ = "rwb27"

import h5py
import os
import os.path
import datetime
import re

def attributes_from_dict(group_or_dataset, dict_of_attributes):
    """Update the metadata of an HDF5 object with a dictionary."""
    attrs = group_or_dataset.attrs
    for key, value in dict_of_attributes.iteritems():
	if value is not None:
	   if key in attrs.keys():
               attrs.modify(key, value)
     	   else:
               attrs.create(key, value)

def h5_item_number(group_or_dataset):
    """Returns the number at the end of a group/dataset name, or None."""
    m = re.search(r"(\d)+$", group_or_dataset.name) #match numbers at the end of the name
    return int(m.groups()[0]) if m else None

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
    def numbered_items(self,name):
        """Get a list of datasets/groups that have a given name + number, 
        sorted by the number appended to the end.
        
        This function is intended to return items saved with 
        auto_increment=True, in the order they were added (by default they
        come in alphabetical order, so 10 comes before 2).  `name` is the 
        name passed in without the _0 suffix.
        """
        items = [v for k, v in self.iteritems() 
                        if k.startswith(name)   #only items that start with `name`
                        and re.match(r"_*(\d+)$",k[len(name):])] #and end with numbers
        return sorted(items, key=h5_item_number)

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
        if auto_increment:
            name = self.find_unique_name(name)
        g = super(Group, self).create_group(name)
	if timestamp:
	    g.attrs.create('creation_timestamp',datetime.datetime.now().isoformat())
        if attrs is not None:
            attributes_from_dict(g, attrs)
        return Group(g.id) #make sure it's wrapped!
    def require_group(self, name):
        """Return a subgroup, creating it if it does not exist."""
        return Group(super(Group, self).require_group(name).id) #wrap the returned group

    def create_dataset(self, name, auto_increment=True, shape=None,dtype=None,data=None,attrs=None,timestamp=True,*args,**kwargs):
        """Create a new dataset, optionally with an auto-incrementing name."""
        if auto_increment:
            name = self.find_unique_name(name)
        dset = super(Group, self).create_dataset(name, shape, dtype, data, *args, **kwargs)
	if timestamp:
	    dset.attrs.create('creation_timestamp',datetime.datetime.now().isoformat())
        if attrs is not None:
            attributes_from_dict(dset, attrs) #quickly set the attributes
        return dset

    def update_attrs(self, attribute_dict):
        """Update (create or modify) the attributes of this group."""
        attributes_from_dict(self, attribute_dict)

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
    def flush(self):
	self.file.flush()
    def close(self):
	self.file.close()
    def make_current(self):
        """Set this as the default location for all new data."""
        global _current_datafile
        _current_datafile = self

_current_datafile = None

def current(create_if_none=True):
    """Return the current data file, creating one if it does not exist."""
    global _current_datafile
    if _current_datafile is None and create_if_none:
        print "No current data file, attempting to create..."
        try: #we try to pop up a Qt file dialog
            import nplab.utils.gui
            from nplab.utils.gui import qtgui
            app = nplab.utils.gui.get_qt_app() #ensure Qt is running
            fname = qtgui.QFileDialog.getSaveFileName(
                                caption = "Select Data File",
                                directory = os.path.join(os.getcwd(),datetime.date.today().strftime("%Y-%m-%d.h5")),
                                filter = "HDF5 Data (*.h5 *.hdf5)",
                                options = qtgui.QFileDialog.DontConfirmOverwrite,
                            )
            if not isinstance(fname, basestring):
                fname = fname[0] #work around version-dependent Qt behaviour :(
            if len(fname) > 0:
                print fname
                if not "." in fname:
                    fname += ".h5"
                set_current(fname, mode='a')
#                if os.path.isfile(fname): #FIXME: dirty hack to work around mode=a not working
#                    set_current(fname,mode='r+')
#                else:
#                    set_current(fname,mode='w-') #create the datafile
            else:
                print "Cancelled by the user."
        except:
            print "File dialog went wrong :("
    
    if _current_datafile is not None:
        return _current_datafile #if there is a file (or we created one) return it
    else:
        raise IOError("Sorry, there is no current file to return.")

def set_current(datafile, **kwargs):
    """Set the current datafile, specified by either an HDF5 file object or a filepath"""
    global _current_datafile
    if isinstance(datafile, h5py.Group):
        _current_datafile = datafile
    else:
        print "opening file: ", datafile
        try:
            _current_datafile = DataFile(datafile, **kwargs) #open a new datafile
        except Exception as e:
            print "problem opening file:"
            print e
            print "trying with mode=r+"
            kwargs['mode'] = 'r+' #dirty hack to work around mode=a not working
            _current_datafile = DataFile(datafile, **kwargs)

