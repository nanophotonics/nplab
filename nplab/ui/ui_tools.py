# -*- coding: utf-8 -*-
from __future__ import print_function
from builtins import object
__author__ = 'alansanders'


from nplab.utils.gui import QtCore, QtGui, QtWidgets, uic
from nplab.utils.notified_property import NotifiedProperty, register_for_property_changes
import os
import sys

def strip_suffices(name, suffices=[]):
    """strip a string from the end of a name, if it's present."""
    for s in suffices:
        if name.endswith(s):
            return name[:-len(s)]
    return name
    
def first_object_with_attr(objects, name, raise_exception=True):
    """Return the first object from a list that has the given attribute.
    
    Raise an exception if none of them has the object, if raise_exception
    is True, otherwise return None.
    """
    for obj in objects:
        if hasattr(obj, name):
            return obj
    if raise_exception:
        raise AttributeError("None of the supplied objects had attribute '{0}'".format(name))
    else:
        return None
    

class UiTools(object):
    """Methods useful to inherit when creating Qt user interfaces."""
    def load_ui_from_file(self, current_file, filename):
        """Load a form from a Qt Designer file, into the current object.
        
        Usually current_file should just be __file__, if the ui file is located
        in the same directory as the python module you're writing.  Filename
        is the UI file."""
        uic.loadUi(os.path.join(os.path.dirname(current_file), filename), self)
        
    def replace_widget(self, layout, old_widget, new_widget, **kwargs):
        if isinstance(layout, QtWidgets.QGridLayout):
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
    
    def auto_connect_by_name(self, 
                             controlled_object=None, 
                             controlled_objects=[], 
                             control_self=True, 
                             verbose=False,
                             ):
        """Try to intelligently connect up widgets to an object's properties.
        
        Enumerate widgets of supported types, and connect them to properties
        of the object with the same name.  The object in question is the
        `controlled object` parameter, and multiple objects can be searched
        in order - first `controlled_object`, then `controlled_objects`, then
        this object (if control_self is True).
        
        The exception to this is buttons: they look in `self` first of all, 
        then try the list of controlled objects.
        
        e.g. if there's a button called "save_button", we'll first try to
        connect self.save_button.clicked to self.save, then (if a controleld
        object is specified) to self._controlled_object.save.
        
        """
        self.slots_to_update_properties = {} # holds callback functions to 
                                # update properties when their controls change.
        self.callbacks_to_update_controls = {} # holds callback functions to
                                # update controls when their properties change.
        if controlled_object is not None:
            controlled_objects = [controlled_object] + controlled_objects
        if control_self:
            controlled_objects = controlled_objects + [self]
        
        # Connect buttons to methods with the same name
        for button in self.findChildren(QtWidgets.QPushButton):
            name = strip_suffices(button.objectName(), ["_button","_pushButton","Button"])
            try:
                # look for the named function first in this object, then in the controlled objects
                obj = first_object_with_attr([self] + controlled_objects, name)
                action=getattr(obj, name)
                assert callable(action), "To call it from a button, it must be callable!"
                button.clicked.connect(action)
                if verbose:
                    print("connected button '{0}' to {1}".format(name, action))
            except:
                if verbose:
                    print("didn't connect button with name '%s'" % name)    
        
        # Now, we try to connect properties with their controls.  This only
        # works for the most common controls, defined in 
        # auto_connectable_controls
        
        # Connect controls to properties with the same name
        for control_type, c in list(auto_connectable_controls.items()):
            for control in self.findChildren(c['qt_type']):
                name = strip_suffices(control.objectName(), c['suffices'])
                try:
                    # look for the named property on the controlled objects
                    obj = first_object_with_attr(controlled_objects, name)
                    assert getattr(obj, name) is not control, "Didn't connect"\
                        " the object, as it would have overwritten itself!"
                    
                    # make a function to update the property, and keep track of it.
                    control_changed = c['control_change_handler'](obj, name)
                    getattr(control, c['control_change_slot_name']).connect(control_changed)
                    self.slots_to_update_properties[name] = control_changed
                    
                    # Also try to register for updates in the other direction
                    # using NotifiedProperties
                    update_handler = c['property_change_handler'](control)
                    try:
                        register_for_property_changes(obj, name, update_handler)
                        self.callbacks_to_update_controls[name] = update_handler
                    except:
                        if verbose:
                            print("Couldn't register for updates on {0}, perhaps "\
                                   "it's not a NotifiedProperty?".format(name))
                    
                    # whether or not it's a NotifiedProperty, we can at least 
                    # try to ensure we *start* with the same values!
                    try:
                        update_handler(getattr(obj, name))
                        # this should fail if the property doesn't exist...
                    except:
                        if verbose:
                            print("Failed to initialise {0}, perhaps there's "\
                                   "no matching property...".format(name))
                            
                    
                    if verbose:
                        print("connected {0} '{1}' to {2}".format(control_type, 
                                 name, "UI" if obj is self else "target"))
                except Exception as e:
                    if verbose:
                        print("didn't connect {0} '{1}'".format(control_type, name))
                        print(e)

class QuickControlBox(QtWidgets.QGroupBox, UiTools):
    "A groupbox that can quickly add controls that synchronise with properties."
    def __init__(self, title="Quick Settings", *args, **kwargs):
        super(QuickControlBox, self).__init__(*args, **kwargs)
        self.setTitle(title)
        self.setLayout(QtWidgets.QFormLayout())
        self.controls = dict()
    
    def add_doublespinbox(self, name, vmin=-float("inf"), vmax=float("inf")):
        """Add a floating-point spin box control."""
        sb = QtWidgets.QDoubleSpinBox()
        self.controls[name] = sb
        sb.setObjectName(name + "_spinbox")
        sb.setMinimum(vmin)
        sb.setMaximum(vmax)
        sb.setKeyboardTracking(False)
        self.layout().addRow(name.title(), sb)
    
    def add_spinbox(self, name, vmin=-2**31, vmax=2**31-1):
        """Add a floating-point spin box control."""
        sb = QtWidgets.QSpinBox()
        self.controls[name] = sb
        sb.setObjectName(name + "_spinbox")
        sb.setMinimum(vmin)
        sb.setMaximum(vmax)
        sb.setKeyboardTracking(False)
        self.layout().addRow(name.title(), sb)
        
    def add_lineedit(self, name):
        """Add a single-line text box control."""
        le = QtWidgets.QLineEdit()
        self.controls[name] = le
        le.setObjectName(name + "_lineedit")
        self.layout().addRow(name.title(), le)
        
    def add_button(self, name, title=None):
        """Add a button."""
        if title is None:
            title = name.title()
        button = QtWidgets.QPushButton()
        self.controls[name] = button
        button.setObjectName(name + "_button")
        button.setText(title)
        self.layout().addRow(button)
        
    def add_checkbox(self, name, title=None):
        if title is None:
            title = name.title()
        checkbox = QtWidgets.QCheckBox()
        self.controls[name] = checkbox
        checkbox.setObjectName(name + "_checkbox")
        checkbox.setText(title)
        self.layout().addRow("", checkbox)
        
    def add_combobox(self, name,options, title=None):
        if title is None:
            title = name.title()
        combobox = QtWidgets.QComboBox()
        for option in options:
            combobox.addItem(option)

        self.controls[name] = combobox
        combobox.setObjectName(name + "_combobox")
        self.layout().addRow(title, combobox)

auto_connectable_controls = {}

def control_change_handler(conversion=lambda x: x):
    """Generate a function that produces callback functions.
    
    This function returns another function, which makes functions.  Sorry.
    
    The function returned by this function will have a docstring (!), it
    takes in an object and a property name, and returns a callback function
    that can be used to update a property when a Qt control changes.
    
    conversion (optional) specifies a function that converts between the
    data type returned by Qt and the data type expected by the property.
    """
    def handler_generator(obj, name):
        """Generate a function to update a property when a Qt control changes.
        
        Arguments:
        obj: object
            The object to which the property is attached
        name: string
            The name of the property to update
        """
        def update_property(value):
            try:
                setattr(obj, name, conversion(value))
            except AttributeError:
                print(name,'has no setter?')
        return update_property
    return handler_generator
def property_change_handler(value_name, 
                            conversion=lambda x: x, 
                            setter_name=None, 
                            getter_name=None):
    """Generate a function that produces callback functions.
    
    These callback functions are for properties changing, and update controls,
    but otherwise see `control_change_handler`.
    
    value_name: string
        The name of the Qt property representing the control's value
    conversion: function (optional)
        A function to convert between the property's value and the control's
    setter_name: string
        The name of the setter method called to change the value.  Usually this
        can be left as the default, which uses ``setName`` where value_name is
        name.
    getter_name: string
        The name of the getter method called to retrieve the value.  Usually
        this can be omitted as the getter name is the same as the value_name.
    """
    if setter_name is None:
        setter_name = "set" + value_name[0].upper() + value_name[1:]
    if getter_name is None:
        getter_name = value_name
    def handler_generator(control):
        """Generate a function to update a control when a property changes."""
        # first get hold of functions to get and set the control's value
        getter = getattr(control, getter_name)
        setter = getattr(control, setter_name)
        def update_control(value):
            if getter() != conversion(value):
                # If we're syncing in both directions, this is important to
                # avoid infinite loops.  Qt is reasonably good about doing this
                # but let's do belt-and-braces for safety.
                setter(conversion(value))
        return update_control
    return handler_generator
    
auto_connectable_controls['checkbox'] = {
    'qt_type': QtWidgets.QCheckBox,
    'suffices': ["_checkbox","CheckBox","_checkBox"],
    'control_change_handler': control_change_handler(lambda x: x==QtCore.Qt.Checked),
    'control_change_slot_name': 'stateChanged',
    'property_change_handler': property_change_handler("checkState", 
                lambda x: QtCore.Qt.Checked if x else QtCore.Qt.Unchecked),
    }
auto_connectable_controls['lineedit'] = {
    'qt_type': QtWidgets.QLineEdit,
    'suffices': ["_lineedit","LineEdit","_lineEdit"],
    'control_change_handler': control_change_handler(),
    'control_change_slot_name': 'textChanged',
    'property_change_handler': property_change_handler("text", str),
    }
auto_connectable_controls['plaintextedit'] = {
    'qt_type': QtWidgets.QPlainTextEdit,
    'suffices': ["_plaintextedit","PlainTextEdit","_textedit","_textbox"],
    'control_change_handler': control_change_handler(),
    'control_change_slot_name': 'textChanged',
    'property_change_handler': property_change_handler("plainText", str, getter_name="toPlainText"),
    }
auto_connectable_controls['spinbox'] = {
    'qt_type': QtWidgets.QSpinBox,
    'suffices': ["_spinbox","SpinBox","_spin",'_spinBox'],
    'control_change_handler': control_change_handler(),
    'control_change_slot_name': 'valueChanged',
    'property_change_handler': property_change_handler("value", int),
    }
auto_connectable_controls['doublespinbox'] = {
    'qt_type': QtWidgets.QDoubleSpinBox,
    'suffices': ["_doubleSpinBox","_spinbox","SpinBox","_spin","_doublespinbox","DoubleSpinBox"],
    'control_change_handler': control_change_handler(),
    'control_change_slot_name': 'valueChanged',
    'property_change_handler': property_change_handler("value", float),
    }
auto_connectable_controls['combobox'] = {
    'qt_type': QtWidgets.QComboBox,
    'suffices': ["_Combobox","_combobox","combobox","_comboBox","comboBox","ComboBox"],
    'control_change_handler': control_change_handler(),
    'control_change_slot_name': 'currentIndexChanged',
    'property_change_handler': property_change_handler("currentIndex", int),
    }