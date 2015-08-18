"""
Experiment Module
=================

Experiments are usually subclasses of `Experiment`, as it provides the basic mechanisms for running things in the background.
"""

__author__ = 'alansanders'

from nplab.utils.thread_utils import locked_action, background_action
# import nplab
# from traits.api import HasTraits, Code, Button, String
# from traitsui.api import View, VGroup, Item, TextEditor

from Queue import Queue
from collections import deque
import h5py
import numpy as np
import threading


class Experiment(object):

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

    def show_gui(self, blocking=True):
        """Display a GUI window for the item of equipment.

        You should override this method to display a window to control the
        instrument.  If edit_traits/configure_traits methods exist, we'll fall
        back to those as a default.

        If you use blocking=False, it will return immediately - this may cause
        issues with the Qt/Traits event loop.
        """
        try:
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
            elif blocking:
                self.configure_traits()
            else:
                self.edit_traits()
        except AttributeError:
            raise NotImplementedError("It looks like the show_gui method hasn't been subclassed, there isn't a get_qt_ui() method, and the instrument is not using traitsui.")


# class Experiment(HasTraits):
#     experiment_code = Code #This is what runs in the background thread
#     run = Button
#     experiment_log = String() #This is where the output goes
#
#     traits_view = View(VGroup(
#                                Item("experiment_code",springy=True),
#                                Item("run"),
#                                Item("experiment_log", editor=TextEditor(multi_line=True),springy=True, style='custom' ),
#                               ),resizable=True)
#     def _run_fired(self):
#         self.run_experiment_in_background()
#         #We can't decorate this directly as it doesn't work with traits handlers!
#     @background_action
#     @locked_action
#     def run_experiment_in_background(self):
#         """run the experiment in a background thread"""
#         def log(message):
#             """Add the message to our output log."""
#             self.experiment_log += str(message) + "\n"
#         try:
#             exec self.experiment_code in globals(), locals()
#         except Exception as e:
#             log("\n\nEXCEPTION!!\n\n"+str(e))
