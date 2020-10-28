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
from nplab.ui.widgets.msgbox import prompt_box
import logging
from nplab.utils.log import create_logger
import inspect
import os
import h5py
import datetime
import json
import numpy as np
import tempfile


LOGGER = create_logger('Instrument')
LOGGER.setLevel('INFO')

class Instrument(ShowGUIMixin):
    """Base class for all instrument-control classes.

    This class takes care of management of instruments, saving data, etc.
    """
    __instances = None
    metadata_property_names = () #"Tuple of names of properties that should be automatically saved as HDF5 metadata
    config_property_names = ()
    _CONFIG_EXTENSION = '.json'

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

    # def open_config_file(self):
    #     """Open the config file for the current spectrometer and return it, creating if it's not there"""
    #     if not hasattr(self, '_config_file'):
    #         f = inspect.getfile(self.__class__)
    #         d = os.path.dirname(f)
    #         self._config_file = nplab.datafile.DataFile(h5py.File(os.path.join(d, 'config.h5'), 'a'))
    #         self._config_file.attrs['date'] = datetime.datetime.now().strftime("%H:%M %d/%m/%y")
    #     return self._config_file
    #
    # config_file = property(open_config_file)
    #
    # def update_config(self, name, data, attrs=None):
    #     """Update the configuration file for this spectrometer.
    #
    #     A file is created in the nplab directory that holds configuration
    #     data for the spectrometer, including reference/background.  This
    #     function allows values to be stored in that file."""
    #     f = self.config_file
    #     if name in f:
    #         try: del f[name]
    #         except:
    #             f[name][...] = data
    #             f.flush()
    #     else:
    #         f.create_dataset(name, data=data ,attrs = attrs)

    def get_config(self, mode='named'):
        """Configuration dictionary
        Iterates over self.config_property_names and gets the property values

        :return: dictionary
        """
        configuration = dict()
        if mode == 'named':
            for name in self.config_property_names:
                configuration[name] = getattr(self, name)
        elif mode == 'all':
            for name in dir(self):
                if not name.startswith('_'):
                    try:
                        value = getattr(self, name)
                        if type(value) in [bool, dict, float, int, list, str, tuple, np.array]:
                            try:
                                with tempfile.TemporaryFile('w') as f:  # this check is done here rather than in self.save_config because we dump the whole configuration in self.save_config
                                    json.dump(value, f)
                                configuration[name] = value
                            except Exception as e:
                                self._logger.info('Configuration value for key: %s cannot be saved to json' % name)
                    except Exception as e:
                        self._logger.debug('Failed getting configuration for key: %s' % name)
        else:
            raise ValueError("Unrecognised configuration mode: %s. Needs to be 'named' or 'all'" % mode)
        return configuration

    def set_config(self, configuration):
        for key, value in configuration.items():
            try:
                setattr(self, key, value)
            except Exception as e:
                self._logger.info('Configuration could not be set for: %s = %s' % (key, value))

    config = property(get_config, set_config)

    def _config_filename(self, name=None, extension=None):
        """Utility function

        Ensures name is a JSON path, and if it's not an absolute path, it points it to the location of the Python file
        for the current class

        :param name: string. Can be just the filename, a filename with an extension, or a relative/absolute path
        :return:
        """
        if name is None:
            name = 'config'  # default name
        if extension is None:
            extension = self._CONFIG_EXTENSION
        # Ensure name has expected extension
        root, ext = os.path.splitext(name)
        if not ext:
            ext = extension
        else:
            assert ext == extension
        filename = root + ext

        # Default location for configuration file is wherever the instance's Python definition is
        if not os.path.isabs(filename):
            f = inspect.getfile(self.__class__)
            d = os.path.dirname(f)
            filename = os.path.join(d, filename)
        return filename

    def save_config(self, filename=None, mode='named'):
        """Saves instrument configuration to JSON
        :param filename: string
        """
        # Get filename
        filename = self._config_filename(filename)
        config = self.get_config(mode)

        # If the file exists, checks whether the user wants to overwrite it
        if os.path.exists(filename):
            reply = prompt_box(text='That configuration file exists. Do you want to overwrite it?', default=filename)
            if not reply:
                return
            filename = reply

        _, ext = os.path.splitext(filename)
        if ext == '.json':
            # Dumps the configuration dictionary to a JSON
            with open(filename, 'w') as config_file:
                json.dump(config, config_file, indent=4)
        elif ext == '.h5':
            with h5py.File(filename, 'w') as dfile:
                dfile.attrs['date'] = datetime.datetime.now().strftime("%H:%M %d/%m/%y")
                for name, value in config.items():
                    try:
                        dfile.create_dataset(name, data=value)
                    except Exception as e:
                        self._logger.info('Configuration value for key: %s cannot be saved to HDF5' % name)
        else:
            raise ValueError('Unrecognised extension: %s' % ext)

    def load_config(self, filename=None):
        """Loads configuration from JSON
        :param filename: string
        :return:
        """
        # Get filename
        filename = self._config_filename(filename)
        _, ext = os.path.splitext(filename)

        # Loads and sets the configuration
        if ext == '.json':
            with open(filename, 'r') as config_file:
                config = json.load(config_file)
        elif ext == '.h5':
            with h5py.File(filename, 'r') as dfile:
                config = dict()
                for key, value in dfile.items():
                    config[key] = value
        else:
            raise ValueError('Unrecognised extension: %s' % ext)
        self.config = config

    def update_config(self, name, data, filename=None):
        # Get filename
        filename = self._config_filename(filename)

        # If the file exists, checks whether the user wants to overwrite it
        if os.path.exists(filename):
            reply = prompt_box(text='That configuration file exists. Do you want to overwrite it?', default=filename)
            if not reply:
                return
            filename = reply

        _, ext = os.path.splitext(filename)
        if ext == '.json':
            # Dumps the configuration dictionary to a JSON
            with open(filename, 'a') as config_file:
                config = json.load(config_file)
                config[name] = data
                config_file.seek(0)
                json.dump(config, config_file)
                config_file.truncate()
        elif ext == '.h5':
            with h5py.File(filename, 'a') as f:
                if name in f:
                    del f[name]
                f.create_dataset(name, data=data)
        else:
            raise ValueError('Unrecognised extension: %s' % ext)
