# -*- coding: utf-8 -*-
"""
Created on Tue Apr 26 09:50:40 2016

@author: rwb27

This module extends (actually reimplements sadly) Python's properties so that
they can do extra things when their values changed.  It's a super-lightweight
alternative to Traits.  Note that you must be using a new-style class for this
to work (i.e. you must inherit from object).

`DumbNotifiedProperty` instances work just like regular variables:

>>> class foo(object):
...     a = DumbNotifiedProperty()
>>>
>>> f = foo()
>>> f.a = 4
>>> f.a
4
>>> f.a=5
>>> f.a
5

They can also have default values:

>>> class foo(object):
...     b = DumbNotifiedProperty(10)
>>>
>>> f = foo()
>>> f.b
10

`NotifiedProperty` just extends the usual `property` mechanism:

>>> class foo(object):
...     a = DumbNotifiedProperty()
...     b = DumbNotifiedProperty(10)
...     @NotifiedProperty
...     def c(self):
...         return 99
...     @c.setter
...     def c(self, val):
...         print("discarding {0}".format(val))
>>>
>>> f = foo()
>>> f.c
99
>>> f.c = 10
discarding 10
>>> f.c
99

To register for notification, use register_for_property_changes

>>> def a_changed(a):
...     print("A changed to '{0}'".format(a))
>>> register_for_property_changes(f, "a", a_changed)
>>> f.a=6
A changed to '6'

If you inherit from `NotifiedPropertiesMixin` there will also be a method of
the object called `register_for_property_changes` that doesn't require the
object to be passed in.
        
"""

from builtins import str
from builtins import object
import functools
from weakref import WeakKeyDictionary
import numpy as np

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
    def __init__(self, fget=None, fset=None, fdel=None, doc=None, read_back=False,single_update = True):
        """Return a property that notifies when it's changed.
        
        This subclasses the pure Python implementation of properties, adding
        support for notifying objects when it's changed.
        
        If read_back is True, the property is read immediately after it is
        written, so that the value that's notified to any listening functions
        is the correct one (this allows for validation of the new value, and
        will make sure controls display what was actually done, rather than 
        the value that was requested).  It's False by default, in case the
        property that's connected to it is expensive to read.
        """
        super(NotifiedProperty, self).__init__(fget=fget, fset=fset, fdel=fdel, doc=doc)
        # We store a set of callbacks for each object (NB there's one property
        # per *class* not per object, so we have to keep track of instances)
        # This is weakly-referenced so if the objects die, we don't stop
        # Python garbage-collecting them.
        self.callbacks_by_object = WeakKeyDictionary()
        self.read_back = read_back
        self.single_update = single_update
        self.last_value=None
    
    def __set__(self, obj, value):
        """Update the property's value, and notify listeners of the change."""
        super(NotifiedProperty, self).__set__(obj, value)
        if self.read_back:
            # This ensures the notified value is correct, at the expense of a read
            if self.single_update:
                if value!=self.last_value:
                    if len(str(value).split('.'))==1:
                        self.last_value=self.__get__(obj)
                    else:
                        self.last_value = np.round(self.__get__(obj),len(str(value).split('.')[-1]))
                    self.send_notification(obj, self.__get__(obj))
                    
         #   
            else:
                self.send_notification(obj, self.__get__(obj))
        else:
            # This is faster, but notifies the requested value, not the actual one
            self.send_notification(obj, value)
        
    def register_callback(self, obj, callback):
        """Add a function to be called whenever the value changes.
        
        The function should accept one argument, which is the new value.
        
        NB if the function raises an exception, it will not be called again.
        """
        if obj not in list(self.callbacks_by_object.keys()):
            self.callbacks_by_object[obj] = set()
        self.callbacks_by_object[obj].add(callback)
        
    def deregister_callback(self, obj, callback):
        """Remove a function from the list of callbacks."""
        try:
            callbacks = self.callbacks_by_object[obj]
        except KeyError:
            raise KeyError("There don't appear to be any callbacks defined on this object!")
        try:
            callbacks.remove(callback)
        except KeyError:
            pass # Don't worry if callbacks are removed pointlessly!
        
        
    def send_notification(self, obj, value):
        """Notify anyone that's interested that the value changed."""
        if obj in self.callbacks_by_object:
            for callback in self.callbacks_by_object[obj].copy():
                try:
                    callback(value)
                except:
                    # Get rid of failed/deleted callbacks
                    # Sometimes Qt objects don't delete cleanly, hence this bodge.
                    self.deregister_callback(obj, callback)
            
class DumbNotifiedProperty(NotifiedProperty):
    "A property that acts as a variable, except it notifies when it changes."
    
    def __init__(self, default=None, fdel=None, doc=None):
        "A property that acts as a variable, except it notifies when it changes."
        
        super(DumbNotifiedProperty, self).__init__(fget=self.fget, 
                                               fset=self.fset, 
                                               fdel=fdel, 
                                               doc=doc)
        self._value = default
        self.values_by_object = WeakKeyDictionary() # we store callbacks here

    # Emulate a variable with the functions below:
    def fget(self, obj):
        try:
            # First, try tp return the stored value for that object
            return self.values_by_object[obj]
        except KeyError:
            # Fall back on the default if not.
            return self._value
            
    def fset(self, obj, value):
        self.values_by_object[obj] = value
        
def register_for_property_changes(obj, property_name, callback):
    """Register a function to be called when the property changes.
    
    Whenever the value of the named property changes, the callback
    function will be called, with the new value as the only argument.
    Note that it's the value that was passed as input to the setter, so
    if you have cunning logic in there, it may be wrong and you might
    want to consider retrieving the property at the start of this function
    (at which point the setter has run, so any changes it makes are done)
    """
    prop = getattr(obj.__class__, property_name, None)
    assert isinstance(prop, NotifiedProperty), "The specified property isn't available"
    
    # register the callback.  Note we need to pass the current object in so
    # the property knows which object we're talking about.
    prop.register_callback(obj, callback)

class NotifiedPropertiesMixin(object):
    """A mixin class that adds support for notified properties.
    
    Notified proprties are a very, very lightweight alternative to Traits.
    They don't (currently) do any data validation, though nothing in principle
    stops you extending them to do that.  Essentially, you decorate the setter
    of a property with @add_notification, and add this mixin to the class.
    
    It's then possible to register to find out whenever that property changes.
    """
    @functools.wraps(register_for_property_changes)
    def register_for_property_changes(self, property_name, callback):
        return register_for_property_changes(self, property_name, callback)
        

if __name__ == '__main__':
    import doctest
    doctest.testmod()
    class foo():
        a = DumbNotifiedProperty(10)
    f = foo()
    f.a = 11
    def a_changed(new):
        print('a changed to ' + str(new))
    register_for_property_changes(f, 'a', a_changed)
    f.a = 12