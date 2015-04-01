"""
Experiment Module
=================

Experiments are usually subclasses of `Experiment`, as it provides the basic mechanisms for running things in the background.
"""

from nplab.utils.thread_utils import locked_action, background_action
import nplab
from traits.api import HasTraits, Code, Button, String 
from traitsui.api import View, VGroup, Item, TextEditor

class Experiment(HasTraits):
    experiment_code = Code #This is what runs in the background thread
    run = Button
    experiment_log = String() #This is where the output goes

    traits_view = View(VGroup(
                               Item("experiment_code",springy=True),
                               Item("run"),
                               Item("experiment_log", editor=TextEditor(multi_line=True),springy=True, style='custom' ),
                              ),resizable=True)
    def _run_fired(self):
        self.run_experiment_in_background()
        #We can't decorate this directly as it doesn't work with traits handlers!
    @background_action
    @locked_action
    def run_experiment_in_background(self):
        """run the experiment in a background thread"""
        def log(message):
            """Add the message to our output log."""
            self.experiment_log += str(message) + "\n"
        try:
            exec self.experiment_code in globals(), locals()
        except Exception as e:
            log("\n\nEXCEPTION!!\n\n"+str(e))

