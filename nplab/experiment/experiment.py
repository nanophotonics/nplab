"""
Experiment Module
=================

Experiments are usually subclasses of `Experiment`, as it provides the basic 
mechanisms for running things in the background without the need to write a
lot of threading code.

"""

__author__ = 'alansanders, richard bowman'

from nplab.utils.thread_utils import locked_action, background_action
from nplab.instrument import Instrument
from nplab.utils.notified_property import NotifiedProperty, DumbNotifiedProperty
from collections import deque
import numpy as np
import threading


class Experiment(Instrument):
    """A class representing an experimental protocol.
    
    This base class is a subclass of Instrument, so it provides all the GUI
    code and data management that instruments have.  It's also got an
    improved logging mechanism, designed for use as a status display, and some
    template methods for running a long experiment in the background.
    """
    
    latest_data = DumbNotifiedProperty(doc="The last dataset/group we acquired")
    log_messages = DumbNotifiedProperty(doc="Log messages from the latest run")
    
    def run(self, *args, **kwargs):
        """This method should be the meat of the experiment (needs overriden)."""
        raise NotImplementedError()

    @background_action
    @locked_action
    def run_in_background(self, *args, **kwargs):
        """Run the experiment in a background thread.
        
        This is important in order to keep the GUI responsive.
        """
        self.log_messages = ""
        self.run(*args, **kwargs)
    
    def log(self, message):
        """Log a message to the current HDF5 file and to the experiment's history"""
        self.log_messages += message + "\n"
        super(Experiment, self).log(message)


class ExperimentWithDataDeque(Experiment):
    """Alan's Experiment class, using a deque for data management."""

    latest_data = None    
    
    def __init__(self):
        super(Experiment, self).__init__()
        #self.queue = Queue()
        self.latest_data = deque([], maxlen=1)
        self.lock = threading.Lock()  # useful in threaded experiments
        self.acquiring = threading.Event()
        self.data_requested = False
        self.request_complete = False

    def run(self, *args, **kwargs):
        raise NotImplementedError()

    @background_action
    @locked_action
    def run_in_background(self, *args, **kwargs):
        self.run(*args, **kwargs)

    def set_latest_data(self, *data):
        self.latest_data.append(data)

    def check_for_data(self):
        #self.notifier.wait()
        if len(self.latest_data):
            return self.latest_data.pop()
        else:
            return False

    def request_data(self):
        if not self.request_complete:
            self.data_requested = True
            return False
        self.request_complete = False
        data = self.check_for_data()
        return data

    def check_for_data_request(self, *data):
        """
        Be careful when giving sequences/iterables e.g. lists, arrays as these are passed
        by reference and can cause threading issues. Be sure to send a copy.
        :param data:
        :return:
        """
        if self.data_requested:
            data = tuple(d.copy() if hasattr(d, 'copy') else np.array(d) for d in data)
            self.set_latest_data(*data)
            self.data_requested = False
            self.request_complete = True

    @staticmethod
    def queue_data(queue, *data):
        with queue.mutex:
            queue.queue.clear()
            queue.all_tasks_done.notify_all()
            queue.unfinished_tasks = 0
        queue.put(data)
        queue.task_done()

    @staticmethod
    def check_queue(queue):
        queue.join()
        if not queue.empty():
            while not queue.empty():
                #print queue.qsize()
                item = queue.get()
            return item
        else:
            return False

    @staticmethod
    def append_dataset(h5object, name, value, shape=(0,)):
        if name not in h5object:
            dset = h5object.require_dataset(name, shape, dtype=np.float64, maxshape=(None,), chunks=True)
        else:
            dset = h5object[name]
        index = dset.shape[0]
        dset.resize(index+1,0)
        dset[index,...] = value
