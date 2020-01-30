"""
Instrument Class
================

This base class defines the standard behaviour for NPLab's instrument
classes, including default locations for saving data, the ability to find
currently-existing instances of a given instrument class, and some GUI helper
functions.

There's also some support mechanisms for metadata creation, and the bundling
of metadata in ArrayWithAttrs objects that include both data and metadata.
"""

from builtins import str
from nplab.utils.thread_utils import locked_action_decorator, background_action_decorator
import nplab
from weakref import WeakSet
import nplab.utils.log
from nplab.utils.array_with_attrs import ArrayWithAttrs
from nplab.utils.show_gui_mixin import ShowGUIMixin
import logging
from nplab.utils.log import create_logger
import inspect
import os
import h5py
import datetime
LOGGER = create_logger('Instrument')
LOGGER.setLevel('INFO')

class Instrument(ShowGUIMixin):
    """Base class for all instrument-control classes.

    This class takes care of management of instruments, saving data, etc.
    """
    __instances = None
    metadata_property_names = () #"Tuple of names of properties that should be automatically saved as HDF5 metadata

    def __init__(self):
        """Create an instrument object."""
        super(Instrument, self).__init__()
        Instrument.instances_set().add(self) #keep track of instances (should this be in __new__?)
        self._logger = logging.getLogger('Instrument.' + str(type(self)).split('.')[-1].split('\'')[0])

    @classmethod
    def instances_set(cls):
        if Instrument.__instances is None:
            Instrument.__instances = WeakSet()
        return Instrument.__instances

    @classmethod
    def get_instances(cls):
        """Return a list of all available instances of this class."""
        return [i for i in Instrument.instances_set() if isinstance(i, cls)]

    @classmethod
    def get_instance(cls, create=True, exceptions=True, *args, **kwargs):
        """Return an instance of this class, if one exists.

        Usually returns the first available instance.
        """
        instances = cls.get_instances()
        if len(instances)>0:
            return instances[0]
        else:
            if create:
                return cls(*args, **kwargs)
            else:
                if exceptions:
                    raise IndexError("There is no available instance!")
                else:
                    return None

    @classmethod
    def get_root_data_folder(cls):
        """Return a sensibly-named data folder in the default file."""
        if nplab.datafile._use_current_group == True:
            if nplab.datafile._current_group != None:
                return nplab.datafile._current_group
        f = nplab.current_datafile()
        return f.require_group(cls.__name__)

    @classmethod
    def create_data_group(cls, name, *args, **kwargs):
        """Return a group to store a reading.

        :param name: should be a noun describing what the reading is (image,
        spectrum, etc.)
        :param attrs: may be a dictionary, saved as HDF5 metadata
        """
        if "%d" not in name:
            name = name + '_%d'
        df = cls.get_root_data_folder()
        return df.create_group(name, auto_increment=True, *args, **kwargs)

    @classmethod
    def create_dataset(cls, name, flush=True, *args, **kwargs):
        """Store a reading in a dataset (or make a new dataset to fill later).

        :param name: should be a noun describing what the reading is (image,
        spectrum, etc.)

        Other arguments are passed to `nplab.datafile.Group.create_dataset`.
        """
        if "%d" not in name: # is this really necessary?
            name = name + '_%d'
        df = cls.get_root_data_folder()
        dset = df.create_dataset(name, *args, **kwargs)
        if 'data' in kwargs and flush:
            dset.file.flush() #make sure it's in the file if we wrote data
        return dset

    def log(self, message,level = 'info'):
        """Save a log message to the current datafile.

        This is the preferred way to output debug/informational messages.  They
        will be saved in the current HDF5 file and optionally shown in the
        nplab console.
        """
        nplab.utils.log.log(message, from_object=self,level = level)

    def get_metadata(self, 
                     property_names=[], 
                     include_default_names=True,
                     exclude=None
                     ):
        """A dictionary of settings, properties, etc. to save along with data.

        This returns the value of each property specified in the arguments or
        in `self.metadata_property_names`.
        
        Arguments:
        property_names : list of strings, optional
            A list specifying the names of properties (of this object) to be
            retrieved and returned in the dictionary.
        include_default_names : boolean, optional (default True)
            If True (the default), include the default metadata along with the
            specified names.  This means that get_metadata can be used with no
            arguments to retrieve the default metadata.
        exclude : list of strings, optional
            A list of properties to exclude (primarily useful when you want to
            remove some of the default entries).  Nothing is excluded by 
            default.
        """
        # Convert everything to lists to:
        # * ensure we don't modify the arguments (it copies list arguments)
        # * make it all mutable so we can remove items
        # * prevent errors when adding lists and tuples
        keys = list(property_names)
        if include_default_names:
            keys += list(self.metadata_property_names)
        if exclude is not None:
            for p in exclude:
                try:
                    keys.remove(p)
                except ValueError:
                    pass # Don't worry if we exclude items that are not there!
        return {name: getattr(self,name) for name in keys}

    metadata = property(get_metadata)

    def bundle_metadata(self, data, enable=True, **kwargs):
        """Add metadata to a dataset, returning an ArrayWithAttrs.
        
        Arguments:
        data : np.ndarray
            The data with which to bundle the metadata
        enable : boolean (optional, default to True)
            Set this argument to False to do nothing, i.e. just return data.
        **kwargs
            Addditional arguments are passed to get_metadata (for example, you 
            can specify a list of `property_names` to add to the default
            metadata, or a list of names to exclude.
        """
        if enable:
            return ArrayWithAttrs(data, attrs=self.get_metadata(**kwargs))
        else:
            return data

    def open_config_file(self):
        """Open the config file for the current spectrometer and return it, creating if it's not there"""
        if not hasattr(self,'_config_file'):
            f = inspect.getfile(self.__class__)
            d = os.path.dirname(f)
            self._config_file = nplab.datafile.DataFile(h5py.File(os.path.join(d, 'config.h5')))
            self._config_file.attrs['date'] = datetime.datetime.now().strftime("%H:%M %d/%m/%y")
        return self._config_file

    config_file = property(open_config_file)
    
    def update_config(self, name, data, attrs= None):
        """Update the configuration file for this spectrometer.
        
        A file is created in the nplab directory that holds configuration
        data for the spectrometer, including reference/background.  This
        function allows values to be stored in that file."""
        f = self.config_file
        if name in f:
            try: del f[name]
            except: 
                f[name][...] = data
                f.flush()    
        else:
            f.create_dataset(name, data=data ,attrs = attrs)