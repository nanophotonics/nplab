# -*- coding: utf-8 -*-
"""
Basic GUI methods for the Experiment class.

"""

from nplab.experiment import Experiment
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