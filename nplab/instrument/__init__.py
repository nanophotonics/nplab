"""
Instrument Class
================

This base class defines the standard behaviour for NPLab's instrument
classes.
"""

from nplab.utils.thread_utils import locked_action_decorator, background_action_decorator
import nplab
#from traits.api import HasTraits, String

from weakref import WeakSet
import nplab.utils.log
from nplab.utils.array_with_attrs import ArrayWithAttrs

class Instrument(object):
    """Base class for all instrument-control classes.

    This class takes care of management of instruments, saving data, etc.
    """
    __instances = None
#    description = String
    metadata_property_names = () #"Tuple of names of properties that should be automatically saved as HDF5 metadata

    def __init__(self):
        """Create an instrument object."""
        super(Instrument, self).__init__()
        Instrument.instances_set().add(self) #keep track of instances (should this be in __new__?)

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

        Other arguments are passed to `create_dataset`.
        """
        if "%d" not in name:
            name = name + '_%d'
        df = cls.get_root_data_folder()
        dset = df.create_dataset(name, *args, **kwargs)
        if 'data' in kwargs and flush:
            dset.file.flush() #make sure it's in the file if we wrote data
        return dset

    def log(self, message):
        """Save a log message to the current datafile.

        This is the preferred way to output debug/informational messages.  They
        will be saved in the current HDF5 file and optionally shown in the
        nplab console.
        """
        nplab.utils.log.log(message, from_object=self)

    def get_metadata(self):
        """A dictionary of settings, properties, etc. to save along with data.

        This returns the value of each property in self.metadata_property_names."""
        return {name: getattr(self,name) for name in self.metadata_property_names}

    metadata = property(get_metadata)

    def bundle_metadata(self, data, enable=True):
        """Add metadata to a dataset, if enable=True."""
        if enable:
            return ArrayWithAttrs(data, attrs=self.metadata)
        else:
            return data

    def show_gui(self, blocking=True):
        """Display a GUI window for the item of equipment.

        You should override this method to display a window to control the
        instrument.  If edit_traits/configure_traits methods exist, we'll fall
        back to those as a default.

        If you use blocking=False, it will return immediately - this may cause
        issues with the Qt/Traits event loop.
        """
        if hasattr(self,'get_qt_ui'):
            from nplab.utils.gui import get_qt_app, qt
            app = get_qt_app()
            ui = self.get_qt_ui()
            ui.show()
            if blocking:
                print "Running GUI, this will block the command line until the window is closed."
                ui.windowModality = qt.Qt.ApplicationModal
                try:
                    return app.exec_()
                except:
                    print "Could not run the Qt application: perhaps it is already running?"
                    return
            else:
                return ui
        else:
            try:
                if blocking:
                    self.configure_traits()
                else:
                    self.edit_traits()
            except NotImplementedError:
                raise NotImplementedError("It looks like the show_gui \
                          method hasn't been subclassed, there isn't a \
                          get_qt_ui() method, and the instrument is not \
                          using traitsui.")
