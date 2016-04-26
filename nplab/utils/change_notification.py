# -*- coding: utf-8 -*-
"""
Created on Tue Apr 26 09:50:40 2016

@author: rwb27
"""

import functools
from weakref import WeakSet

def add_notification(function, name=None):
    """Wrap a function so that, after it's executed, we notify that it's run.
    
    This is designed to be used on the setter method of a property, so that
    we can synchronise the property easily with a GUI.  It requires that the
    first argument of the function is `self`.  We assume the name of the 
    property is the name of the function - if this is not true, use the
    optional argument "name" (though you can't do that from the decorator).
    
    It also requires that the object has a function `notify_parameter_changed`
    that deals with notifications.  This is provided by the 
    `NotifiedPropertiesMixin` class.
    
    Use this to decorate your setter functions, so that it updates the UI if
    the setting is changed in software.
    
    Example::
    
    class foo():
        @property
        def a(self):
            return 0
        @a.setter
        @add_notification
        def a(self, newa):
            pass
    
    NB that you should put this decorator *after* the setter decorator.
    """
    if name is None:
        name = function.__name__ # Default to the function's name
    @functools.wraps(function)
    def f(self, *args, **kwargs):
        ret = function(self, *args, **kwargs)
        self.notify_parameter_changed(name)
        return ret
    return f

class Property(object):
    """Emulate PyProperty_Type() in Objects/descrobject.c
    
    This is copied from 
    https://docs.python.org/2/howto/descriptor.html#properties
    as I'd otherwise be reimplementing.  Plus, having this here makes it
    clearer how my properties differ."""

    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        if doc is None and fget is not None:
            doc = fget.__doc__
        self.__doc__ = doc

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        if self.fget is None:
            raise AttributeError("unreadable attribute")
        return self.fget(obj)

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError("can't set attribute")
        self.fset(obj, value)

    def __delete__(self, obj):
        if self.fdel is None:
            raise AttributeError("can't delete attribute")
        self.fdel(obj)

    def getter(self, fget):
        return type(self)(fget, self.fset, self.fdel, self.__doc__)

    def setter(self, fset):
        return type(self)(self.fget, fset, self.fdel, self.__doc__)

    def deleter(self, fdel):
        return type(self)(self.fget, self.fset, fdel, self.__doc__)

class NotifiedProperty(Property):
    """A property that notifies when it's changed."""        
    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        """Return a property that notifies when it's changed.
        
        This subclasses the pure Python implementation of properties, adding
        support for notifying objects when it's changed.
        """
        super(NotifiedProperty, self).__init__(fget=fget, fset=fset, fdel=fdel, doc=doc)
        self.callbacks = WeakSet()
    
    def __set__(self, obj, value):
        super(NotifiedProperty, self).__set__(self, obj, value)
        # TODO: should I replace value below with self.__get__()?
        self.send_notification(value)
        
    def register_callback(self, callback):
        """Add a function to be called whenever the value changes.
        
        The function should accept one argument, which is the new value.
        """
        self.callbacks.add(callback)
        
    def deregister_callback(self, callback):
        """Remove a function from the list of callbacks."""
        self.callbacks.remove(callback)
        
    def send_notification(self, value):
        """Notify anyone that's interested that the value changed."""
        for callback in self.callbacks:
            callback(value)
            
class DumbNotifiedProperty(NotifiedProperty):
    "A property that acts as a variable, except it notifies when it changes."
    
    def __init(self, default=None, fdel=None, doc=None):
        "A property that acts as a variable, except it notifies when it changes."
        super(DumbNotifiedProperty, self).__init__(fget=self.fget, 
                                               fset=self.fset, 
                                               fdel=fdel, 
                                               doc=doc)
        self._value = default
        
    # Emulate a variable with the functions below:
    def fget(self):
        return self._value
    def fset(self, value):
        self._value = value


#def notified_property(name, default=None, doc=None, fget=None, fset=None, fdel=None):
#    """Return a property that notifies when it's changed.
#    
#    If you don't specify a getter or setter function, we'll generate them (and
#    the property just behaves like a regular variable).  If you do specify a
#    setter, you must also specify a setter - read-only properties
#    don't make sense here, you can just use a regular property for that."""
#    if fget is not None:
#        assert fset is not None, ("You must specify both or neither of fget " +
#                                  "and fset.  Read-only properties should be "+
#                                  "reguar properties, not notified properties.")
#        return property(fget=fget, fset=add_notification(fset, name=name), 
#                        fdel=fdel)
#        
#    else:
#        # make getter/setter methods that do nothing, so it is a dumb variable.
#        internal_name = "_notified_property_internal_state_"+name
#        def getter(self):
#            return getattr(self, internal_name, None)
#        def setter(self, newvalue):
#            setattr(self, internal_name, newvalue)
#            self.notify_parameter_changed(name)
#        return property(fget=getter, fset=setter, fdel=fdel)
        
#class NotifiedPropertiesMixin():
#    """A mixin class that adds support for notified properties.
#    
#    Notified proprties are a very, very lightweight alternative to Traits.
#    They don't (currently) do any data validation, though nothing in principle
#    stops you extending them to do that.  Essentially, you decorate the setter
#    of a property with @add_notification, and add this mixin to the class.
#    
#    It's then possible to register to find out whenever that property changes.
#    """
#    