__author__ = 'alansanders'

from nplab.utils.gui import *
from nplab.utils.gui import QtGui, QtCore
from nplab.utils.notified_property import NotifiedProperty, register_for_property_changes

def strip_suffices(name, suffices=[]):
    """strip a string from the end of a name, if it's present."""
    for s in suffices:
        if name.endswith(s):
            return name[:-len(s)]
    return name

class UiTools(object):
    """Methods useful to inherit when creating Qt user interfaces."""
    def load_ui_from_file(self, current_file, filename):
        """Load a form from a Qt Designer file, into the current object.
        
        Usually current_file should just be __file__, if the ui file is located
        in the same directory as the python module you're writing.  Filename
        is the UI file."""
        uic.loadUi(os.path.join(os.path.dirname(current_file), filename), self)
        
    def replace_widget(self, layout, old_widget, new_widget, **kwargs):
        if isinstance(layout, QtGui.QGridLayout):
            index = layout.indexOf(old_widget)
            position = layout.getItemPosition(index)
            layout.removeWidget(old_widget)
            old_widget.setParent(None)
            layout.addWidget(new_widget, *position, **kwargs)
            #new_widget.setParent(self)
        else:
            index = layout.indexOf(old_widget)
            layout.removeWidget(old_widget)
            old_widget.setParent(None)
            layout.insertWidget(index, new_widget, **kwargs)
        return new_widget

    def check_state(self, *args, **kwargs):
        sender = self.sender()
        validator = sender.validator()
        state = validator.validate(sender.text(), 0)[0]
        if state == QtGui.QValidator.Acceptable:
            color = '#c4df9b'  # green
        elif state == QtGui.QValidator.Intermediate:
            color = '#fff79a'  # yellow
        else:
            color = '#f6989d'  # red
        sender.setStyleSheet('QLineEdit { background-color: %s }' % color)
        return True if state == QtGui.QValidator.Acceptable else False

    def on_text_change(self, text):
        """This method makes it easy to validate text input.
        
        TODO: instructions on how to use it!"""
        sender = self.sender()
        if sender.validator() is not None:
            state = sender.validator().validate(text, 0)[0]
            if state != QtGui.QValidator.Acceptable:
                return False
        return sender
    
    def auto_connect_by_name(self, controlled_object=None, names=None, verbose=False):
        """Try to intelligently connect up widgets to an object's properties.
        
        Enumerate widgets of supported types, and connect them to properties
        of the object with the same name, or to another object's properties if
        they are not properties of this object.
        
        e.g. if there's a button called "save_button", we'll first try to
        connect self.save_button.clicked to self.save, then (if a controleld
        object is specified) to self._controlled_object.save.
        
        """
        self._ui_controlled_object = controlled_object
        self._ui_polled_properties = []
        
        self.slots_to_update_properties = {}
        
        # Connect buttons to methods with the same name
        for button in self.findChildren(QtGui.QPushButton):
            name = strip_suffices(button.objectName(), ["_button","Button"])
            try:
                # look for the named function first in this object, then in the controlled object
                try:
                    action = getattr(self, name)
                except AttributeError:
                    action = getattr(controlled_object, name)
                    
                assert callable(action), "To call it from a button, it must be callable!"
                button.clicked.connect(action)
                if verbose:
                    print "connected button '{0}' to {1}".format(name, action)
            except:
                if verbose:
                    print "didn't connect button with name '%s'" % name    
        
        # Connect checkboxes to properties with the same name
        def checkbox_state_change_handler(obj, name):
            "Generate a function to update a property when a checkbox changes."
            def stateChanged(state):
                if verbose:
                    print "setting {0} to {1}".format(name, state == QtCore.Qt.Checked)
                setattr(obj, name, state == QtCore.Qt.Checked)
            return stateChanged
            
        for checkbox in self.findChildren(QtGui.QCheckBox):
            name = strip_suffices(checkbox.objectName(), ["_checkbox","CheckBox"])
            try:
                # look for the named property first the controlled object, then use this one
                obj = controlled_object if hasattr(controlled_object, name) else self
                if checkbox.objectName() == name and obj is self:
                    # don't overwrite the checkbox!
                    if verbose:
                        print "Warning: '{0}' not connected, name clash!".format(name)
                    break
                
                # make a function to update the property, and keep track of it.
                # NB this will always run - it makes a spurious property on
                # the UI object if there's no connection to make.
                stateChanged = checkbox_state_change_handler(obj, name)
                checkbox.stateChanged.connect(stateChanged)
                self.slots_to_update_properties[name] = stateChanged
                
                if verbose:
                    if obj is self:
                        print "connected checkbox '{0}' to UI object".format(name)
                    else:
                        print "connected checkbox '{0}' to target".format(name)
            except Exception as e:
                if verbose:
                    print "didn't connect checkbox with name '%s'" % name
                    print e
                


