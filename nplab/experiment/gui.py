# -*- coding: utf-8 -*-
"""
Basic GUI methods for the Experiment class.

"""
from __future__ import print_function

from builtins import object
from nplab.experiment import Experiment, ExperimentStopped
from nplab.utils.gui import QtCore, QtGui, QtWidgets
from nplab.ui.ui_tools import UiTools, QuickControlBox

class ExperimentGuiMixin(object):
    """This class will add a basic GUI to an experiment, showing logs & data.
    
    The `get_control_widget()` method is essentially empty, and is intended
    to be overridden with useful settings for the experiment, for example 
    using a QuickControlBox.
    """
    def get_qt_ui(self):
        """Create a Qt Widget representing the experiment."""
        return ExperimentWidget(self)
    
    def get_data_widget(self):
        """Create a QWidget that shows the latest data"""
        return DataWidget(self)
    
    def get_log_widget(self):
        """A widget that displays logs in a scrolling display."""
        return LogWidget(self)
        
    def get_control_widget(self):
        """Return a widget that controls the experiment's settings."""
        return QuickControlBox()

class ExperimentWithGui(Experiment, ExperimentGuiMixin):
    """Experiment class, extended to have a basic GUI including logs & data."""
    pass #see the mixin for what happens here...
    
class LogWidget(QuickControlBox):
    """A widget for displaying the logs from an Experiment."""
    def __init__(self, experiment):
        """Create a widget to display an experiment's logs."""
        self.experiment = experiment
        super(LogWidget, self).__init__()
        
        self.text_edit = QtWidgets.QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.layout().addRow(self.text_edit)
        self.add_button("clear", title="Clear Logs")
        self.auto_connect_by_name()
        
    def clear(self):
        """Clear the text box, and the logs of the experiment."""
        self.experiment.log_messages = ""

class QProgressDialogWithDeferredUpdate(QtWidgets.QProgressDialog):
    """A QProcessDialog that can have its value updated from a background thread."""
    set_new_value = QtCore.Signal(int)

    def __init__(self, *args, **kwargs):
        QtWidgets.QProgressDialog.__init__(self, *args, **kwargs)
        self.set_new_value.connect(self.setValue, type=QtCore.Qt.QueuedConnection)

    def setValueLater(self, progress):
        """Update the progress bar - but do it in a thread-safe way."""
        self.set_new_value.emit(progress)


class ExperimentWithProgressBar(Experiment):
    """A class that extends an Experiment by adding a modal Qt progress bar for basic feedback.

    Use it exactly like Experiment, but with a couple of extra steps:
    * make sure you override ``prepare_to_run()`` and:
      - set self.progress_maximum (and minimum, if desired)
    * in your ``run()`` method, call ``self.update_progress(i)`` periodically.
    The progress bar will disappear once you have called update_progress(n) where n is the
    value you specified in self.progress_maximum earlier.  NB changing progress_maximum from
    within run() has no effect currently.

    If the user clicks abort on the progress bar, or stops the experiment by some other means,
    an exception will be raised from calls to ``update_progress`` that stops the experiment.
    """
    progress_maximum = None
    progress_minimum = 0
    def prepare_to_run(self, *args, **kwargs):
        """Set up the experiment.  Must be overridden to set self.progress_maximum"""
        if self.progress_maximum is not None:
            return # If progress_maximum has been set elsewhere, that's ok...
        raise NotImplementedError("Experiments with progress bars must set self.progress_maximum"
                                  "in the prepare_to_run method.")

    def run_modally(self, *args, **kwargs):
        """Run the experiment in the background.

        This method replaces `Experiment.start()` and is blocking; it can safely be called
        from a Qt signal from a button.
        """
     #   self.prepare_to_run(*args, **kwargs)
        if self.progress_maximum is None:
            raise NotImplementedError("self.progress_maximum was not set - this is necessary.")
        self._progress_bar = QProgressDialogWithDeferredUpdate(
                                                   self.__class__.__name__,
                                                   "Abort",
                                                   self.progress_minimum,
                                                   self.progress_maximum)
        self._progress_bar.show()
        self._progress_bar.setAutoClose(True)
        self._progress_bar.canceled.disconnect()
        self._progress_bar.canceled.connect(self.stop_and_cancel_dialog)
        self._experiment_thread = self.run_in_background(*args, **kwargs)
   #     self._progress_bar.exec_()

    def stop_and_cancel_dialog(self):
        """Abort the experiment and cancel the dialog once done."""
        try:
            self.stop(True)
        finally:
            self._progress_bar.cancel()

    def update_progress(self, progress):
        """Update the progress bar (NB should only be called from within run()"""
        if not self.running:
            # if run was called directly, fail gracefully
            print("Progress: {}".format(progress))
            return
        try:
            self._progress_bar.setValueLater(progress)
        except AttributeError:
            print("Error setting progress bar to {} (are you running via run_modally()?)".format(progress))
        if self._stop_event.is_set():
            raise ExperimentStopped()

class RunFunctionWithProgressBar(ExperimentWithProgressBar):
    """An Experiment object that simply runs a function modally"""
    def __init__(self, target, progress_maximum=None, *args, **kwargs):
        super(RunFunctionWithProgressBar, self).__init__(*args, **kwargs)
        self.target = target
        assert callable(target), ValueError("The target function is not callable!")
        self.progress_maximum = progress_maximum

    def run(self, *args, **kwargs):
        print("running function {}".format(self.target))
        #, update_progress=self.update_progress,
        self.target(update_progress=self.update_progress,*args, **kwargs)
        self.update_progress(self.progress_maximum) # Ensure the progress dialog closes unless we're aborted.

def run_function_modally(function, progress_maximum, *args, **kwargs):
    """Create a temporary ExperimentWithProgressBar and run it modally.

    This convenience function allows a function to be run with a nice progress bar, without the hassle
    of setting up an Experiment object.  The function must accept a keyword argument, update_progress,
    which is a function - it should be called periodically, with a numeric argument that starts at zero
    and increments up to a final value of progress_maximum.  A sensible default for this argument would
    be ``lambda p: p``, which is a function that does nothing.

    Positional and keyword arguments are passed through, the only other argument needed is
    progress_maximum, which sets the final value of progress.
    """
 #   function(*args, **kwargs)
    e = RunFunctionWithProgressBar(function, progress_maximum = progress_maximum)
    e.run_modally(*args, **kwargs)