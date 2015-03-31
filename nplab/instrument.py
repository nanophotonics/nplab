"""
Instrument Class
================

This base class defines the standard behaviour for NPLab's instrument 
classes.  
"""

from nplab.utils.thread_utils import locked_action_decorator, background_action_decorator
import nplab
from traits.api import HasTraits


class Instrument(HasTraits):
    """Base class for all instrument-control classes.

    This class takes care of management of instruments, saving data, etc.
    """
    __instances = []

    def __init__(self):
        """Create an instrument object."""
        super(Instrument, self).__init__()
        Instrument.__instances.append(self)

    @classmethod
    def get_instances(cls):
        """Return a list of all available instances of this class."""
        return [i for i in Instrument.__instances if isinstance(i, cls)]

    @classmethod
    def get_instance(cls, create=True, exceptions=True):
        """Return an instance of this class, if one exists.  
        
        Usually returns the first available instance.
        """
        instances = cls.get_instances()
        if len(instances)>0:
            return instances[0]
        else:
            if create:
                return cls()
            else:
                if exceptions:
                    raise IndexError("There is no available instance!")
                else:
                    return None

    @classmethod
    def get_root_data_folder(cls):
        """Return a sensibly-named data folder in the default file."""
        f = nplab.current_datafile()
        return f.require_group(cls.__name__)

    @classmethod
    def create_data_group(cls, name, *args, **kwargs):
        """Return a group to store a reading.

        :param name: should be a noun describing what the reading is (image,
        spectrum, etc.)
        """
        df = cls.get_root_data_folder()
        return df.create_group(name+'_%d', auto_increment=True, *args, **kwargs)

    @classmethod
    def create_dataset(cls, name, *args, **kwargs):
        """Store a reading in a dataset (or make a new dataset to fill later).

        :param name: should be a noun describing what the reading is (image,
        spectrum, etc.)

        Other arguments are passed to `create_dataset`.
        """
        df = cls.get_root_data_folder()
        return df.create_dataset(name+'_%d', *args, **kwargs)

