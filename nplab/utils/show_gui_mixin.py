"""
Show gui mixin
==============

This module defines a mixin class that sets the handling of GUI display 
for instruments, experiments, etc. It's deliberately not in nplab.ui
to avoid dependencies on Qt, etc. as it's intended to be toolkit-neutral

author: Richard Bowman
"""

class ShowGUIMixin:
    def show_gui(self, blocking=True):
        """Display a GUI window for the class.

        You may override this method to display a window to control the
        object.  However, it's better (and less work) to provide a
        method `get_qt_ui()`.  This shoudl return a QWidget subclass that
        is the GUI for the object.  This method will take care of ensuring
        there's a Qt application object and displaying the GUI.
        
        If you are using traitsui, then edit_traits/configure_traits 
        methods exist, and this method will simply pop up a traits window
        for the object.

        If you use blocking=False, it will return immediately - this allows
        you to continue using the console, assuming there's already a Qt
        application running (usually the case if you're running from 
        Spyder).  NB you should hold on to the return value if using this
        mode, as otherwise the GUI may be garbage-collected and disappear.

        In the future, blocking=False may spawn a Qt application object in
        a background thread - but that's not currently done.
        """
        if hasattr(self,'get_qt_ui'):
            # NB this dynamic import is important to avoid saddling all of
            # nplab with dependencies on Qt.
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
