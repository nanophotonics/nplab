"""
Experiment Module
=================

Experiments are usually subclasses of `Experiment`, as it provides the basic 
mechanisms for running things in the background without the need to write a
lot of threading code.

"""
from __future__ import print_function

__author__ = 'alansanders, richard bowman'

from nplab.utils.thread_utils import locked_action, background_action, background_actions_running
from nplab.instrument import Instrument
from nplab.utils.notified_property import NotifiedProperty, DumbNotifiedProperty
from collections import deque
import numpy as np
import threading
import warnings

class ExperimentStopped(Exception):
    """An exception raised to stop an experiment running in a background thread."""
    pass

class Experiment(Instrument):
    """A class representing an experimental protocol.
    
    This base class is a subclass of Instrument, so it provides all the GUI
    code and data management that instruments have.  It's also got an
    improved logging mechanism, designed for use as a status display, and some
    template methods for running a long experiment in the background.
    """
    
    latest_data = DumbNotifiedProperty(doc="The last dataset/group we acquired")
    log_messages = DumbNotifiedProperty(doc="Log messages from the latest run")
    log_to_console = False
    experiment_can_be_safely_aborted = False # set to true if you want to suppress warnings about ExperimentStopped
    
    def __init__(self):
        """Create an instance of the Experiment class"""
        super(Experiment, self).__init__()
        self._stop_event = threading.Event()
        self._finished_event = threading.Event()
        self._experiment_thread = None
        self.log_messages = ""

    def prepare_to_run(self, *args, **kwargs):
        """This method is always run in the foreground thread before run()

        Use this method if you might need to pop up a GUI, for example.  The
        most common use of this would be to create a data group or to ensure
        the current data file exists - doing that in run() could give rise
        to nasty threading problems.  By default, it does nothing.

        The arguments are passed through from start() to here, so you should
        either use or ignore them as appropriate.  These are the same args
        as are passed to run(), so if one of the two functions requires an
        argument you should make sure the other won't fail if the same
        argument is passed to it (simple rule: accept *args, **kwargs in
        both, in addition to any arguments you might have).
        """
        pass

    def run(self, *args, **kwargs):
        """This method should be the meat of the experiment (needs overriden).
        
        This is where your experiment code goes.  Note that you should use
        `self.wait_or_stop()` to pause your experiment between readings, to
        allow the background thread to be stopped if necessary.
        
        If you set `self.latest_data`, this may be used to display your
        results in real time.  You can also use `self.log()` to output text
        describing the experiment's progress; this may be picked up and 
        displayed graphically or in the console.

        The arguments are passed through from start() to here, so you should
        either use or ignore them as appropriate.  These are the same args
        as are passed to run(), so if one of the two functions requires an
        argument you should make sure the other won't fail if the same
        argument is passed to it (simple rule: accept *args, **kwargs in
        both, in addition to any arguments you might have).
        """
        NotImplementedError("The run() method of an Experiment must be overridden!")
        
    def wait_or_stop(self, timeout, raise_exception=True):
        """Wait for the specified time in seconds.  Stop if requested.
        
        This waits for a given time, unless the experiment has been manually 
        stopped, in which case it will terminate the thread by raising an
        ExperimentStopped exception.  You should call this whenever your
        experiment is in a state that would be OK to stop, such as between
        readings.
        
        If raise_exception is False, it will simply return False when the
        experiment should stop.  This is appropriate if you want to use it in a
        while loop, e.g. ``while self.wait_or_stop(10,raise_exception=False):``
        
        You may want to explicitly handle the ExperimentStopped exception to
        close down cleanly.
        """
        if self._stop_event.wait(timeout):
            if raise_exception:
                raise ExperimentStopped()
        return True

    @background_action
    @locked_action
    def run_in_background(self, *args, **kwargs):
        """Run the experiment in a background thread.
        
        This is important in order to keep the GUI responsive.
        """
        self.log_messages = ""
        self._stop_event.clear()
        self._finished_event.clear()
        self.run(*args, **kwargs)
        self._finished_event.set()
        
    def start(self, *args, **kwargs):
        """Start the experiment running in a background thread.  See run_in_background."""
        assert self.running == False, "Can't start the experiment when it is already running!"
        self.prepare_to_run(*args, **kwargs)
        self._experiment_thread = self.run_in_background(*args, **kwargs)
        
    def stop(self, join=False):
        """Stop the experiment running, if supported.  May take a little while."""
        self._stop_event.set()
        if join:
            try:
                self._experiment_thread.join()
            except ExperimentStopped as e:
                if not self.experiment_can_be_safely_aborted:
                    raise e

    @property
    def running(self):
        """Whether the experiment is currently running in the background."""
        return background_actions_running(self)
    
    def log(self, message):
        """Log a message to the current HDF5 file and to the experiment's history"""
        self.log_messages += message + "\n"
        if self.log_to_console:
            print(message)
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
