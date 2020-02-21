# -*- coding: utf-8 -*-
"""
Message Bus Instrument
======================

This base class

@author: Richard Bowman
"""
from __future__ import print_function
#from traits.api import HasTraits, Bool, Int, Str, Button, Array, Enum, List
#import nplab
from past.builtins import basestring
from builtins import str
from builtins import zip
from builtins import map
from builtins import object
import re
import nplab.instrument
from functools import partial
import threading
import numpy as np
import types


class MessageBusInstrument(nplab.instrument.Instrument):
    """
    Message Bus Instrument
    ======================

    An instrument that communicates by sending strings back and forth over a bus.

    This base class provides commonly-used mechanisms that support the use of
    serial or VISA instruments.  The SerialInstrument and VISAInstrument classes
    both inherit from this class.  Most interactions with this class involve
    a call to the `query` method.  This writes a message and returns the reply.
    
    

    Subclassing Notes
    -----------------

    The minimum you need to do to create a working subclass is override the
    `write()` and `readline()` methods.  You probably also want to provide an
    open() and close() method to deal with the underlying port, and put
    something sensible in __init__ to open your port when it's created.

    It's also a very good idea to provide some way to flush the input buffer
    with `flush_input_buffer()`.
    
    Threading Notes
    ---------------
    
    The message bus protocol includes a property, `communications_lock`.  All
    commands that use the communications bus should be protected by this lock.
    It's also permissible to use it to protect sequences of calls to the bus 
    that must be atomic (e.g. a multi-part exchange of messages).  However, try
    not to hold it too long - or odd things might happen if other threads are 
    blocked for a long time.  The lock is reentrant so there's no issue with
    acquiring it twice.
    """
    termination_character = "\n" #: All messages to or from the instrument end with this character.
    termination_read = None  #: Can be used if the writing and reading termination characters are different. Currently implemented in serial_instrument
    termination_line = None #: If multi-line responses are recieved, they must end with this string
    ignore_echo = False

    _communications_lock = None
    @property
    def communications_lock(self):
        """A lock object used to protect access to the communications bus"""
        # This requires initialisation but our init method won't be called - so
        # the property initialises it on first use.
        if self._communications_lock is None:
            self._communications_lock = threading.RLock()
        return self._communications_lock

    def write(self,query_string):
        """Write a string to the unerlying communications port"""
        with self.communications_lock:
            raise NotImplementedError("Subclasses of MessageBusInstrument must override the write method!")
            
    def flush_input_buffer(self):
        """Make sure there's nothing waiting to be read.

        This function should be overridden to make sure nothing's lurking in
        the input buffer that could confuse a query.
        """
        with self.communications_lock:
            pass
    
    def readline(self, timeout=None):
        """Read one line from the underlying bus.  Must be overriden."""
        with self.communications_lock:
            raise NotImplementedError("Subclasses of MessageBusInstrument must override the readline method!")
            
    def read_multiline(self, termination_line=None, timeout=None):
        """Read one line from the underlying bus.  Must be overriden.

        This should not need to be reimplemented unless there's a more efficient
        way of reading multiple lines than multiple calls to readline()."""
        with self.communications_lock:
            if termination_line is None:
                termination_line = self.termination_line
            
            # assert isinstance(termination_line, basestring), "If you perform a multiline query, you must specify a termination line either through the termination_line keyword argument or the termination_line property of the NPSerialInstrument."
           
            # assert type(termination_line) == types.StringType , "If you perform a multiline query, you must specify a termination line either through the termination_line keyword argument or the termination_line property of the NPSerialInstrument."        
            try:
                assert isinstance(termination_line, basestring), "If you perform a multiline query, you must specify a termination line either through the termination_line keyword argument or the termination_line property of the NPSerialInstrument."
            except NameError:
                assert isinstance(termination_line, str), "If you perform a multiline query, you must specify a termination line either through the termination_line keyword argument or the termination_line property of the NPSerialInstrument."
            
            
            response = ""
            last_line = "dummy"
            while termination_line not in last_line and len(last_line) > 0: #read until we get the termination line.
                last_line = self.readline(timeout)
                response += last_line
            return response
            
    def query(self,queryString,multiline=False,termination_line=None,timeout=None):
        """
        Write a string to the stage controller and return its response.

        It will block until a response is received.  The multiline and termination_line commands
        will keep reading until a termination phrase is reached.
        """
        with self.communications_lock:
            self.flush_input_buffer()
            self.write(queryString)
            if self.ignore_echo:
                echo_line = self.readline(timeout).strip()
                if echo_line != queryString:
                    self._logger.warn('Command did not echo: %s' % queryString)
                    return echo_line

            if termination_line is not None:
                multiline = True
            if multiline:
                return self.read_multiline(termination_line)
            else:
                return self.readline(timeout).strip() #question: should we strip the final newline?
    
    def parsed_query_old(self, query_string, response_string=r"(\d+)", re_flags=0, parse_function=int, **kwargs):
        """
        Perform a query, then parse the result.

        By default it looks for an integer and returns one, otherwise it will
        match a custom regex string and return the subexpressions, parsed through
        the supplied functions.

        TODO: make this accept friendlier sscanf style arguments, and produce parse functions automatically
        """
        # NB no need for the lock here - `query` is already an atomic operation.
        reply = self.query(query_string, **kwargs)
        res = re.search(response_string, reply, flags=re_flags)
        if res is None:
            raise ValueError("Stage response to '%s' ('%s') wasn't matched by /%s/" % (query_string, reply, response_string))
        try:
            if len(res.groups()) == 1:
                return parse_function(res.groups()[0])
            else:
                return list(map(parse_function,res.groups()))
        except ValueError:
            raise ValueError("Stage response to %s ('%s') couldn't be parsed by the supplied function" % (query_string, reply))
    def parsed_query(self, query_string, response_string=r"%d", re_flags=0, parse_function=None, **kwargs):
        """
        Perform a query, returning a parsed form of the response.

        First query the instrument with the given query string, then compare
        the response against a template.  The template may contain text and
        placeholders (e.g. %i and %f for integer and floating point values
        respectively).  Regular expressions are also allowed - each group is
        considered as one item to be parsed.  However, currently it's not
        supported to use both % placeholders and regular expressions at the
        same time.

        If placeholders %i, %f, etc. are used, the returned values are
        automatically converted to integer or floating point, otherwise you
        must specify a parsing function (applied to all groups) or a list of
        parsing functions (applied to each group in turn).
        """

        response_regex = response_string
        noop = lambda x: x #placeholder null parse function
        placeholders = [ #tuples of (regex matching placeholder, regex to replace it with, parse function)
            (r"%c",r".", noop),
            (r"%(\\d+)c",r".{\1}", noop), #TODO support %cn where n is a number of chars
            (r"%d",r"[-+]?\\d+", int),
            (r"%[eEfg]",r"[-+]?(?:\\d+(?:\.\\d*)?|\.\\d+)(?:[eE][-+]?\\d+)?", float),
            # (r"%(\\d+)c",r".{\\1}", noop), #TODO support %cn where n is a number of chars
            # (r"%d",r"[-+]?\\d+", int),
            # (r"%[eEfg]",r"[-+]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:[eE][-+]?\\d+)?", float),
            (r"%i",r"[-+]?(?:0[xX][\\dA-Fa-f]+|0[0-7]*|\\d+)", lambda x: int(x, 0)), #0=autodetect base
            (r"%o",r"[-+]?[0-7]+", lambda x: int(x, 8)), #8 means octal
            (r"%s",r"\\S+",noop),
            (r"%u",r"\\d+",int),
            (r"%[xX]",r"[-+]?(?:0[xX])?[\\dA-Fa-f]+",lambda x: int(x, 16)), #16 forces hexadecimal
        ]
        matched_placeholders = []
        for placeholder, regex, parse_fun in placeholders:
            response_regex = re.sub(placeholder, '('+regex+')', response_regex) #substitute regex for placeholder
            matched_placeholders.extend([(parse_fun, m.start()) for m in re.finditer(placeholder, response_string)]) #save the positions of the placeholders
        if parse_function is None:
            parse_function = [f for f, s in sorted(matched_placeholders, key=lambda m: m[1])] #order parse functions by their occurrence in the original string
        if not hasattr(parse_function,'__iter__'):
            parse_function = [parse_function] #make sure it's a list.

        reply = self.query(query_string, **kwargs) #do the query
        res = re.search(response_regex, reply, flags=re_flags)
        if res is None:
            raise ValueError("Stage response to '%s' ('%s') wasn't matched by /%s/ (generated regex /%s/" % (query_string, reply, response_string, response_regex))
        try:
            parsed_result= [f(g) for f, g in zip(parse_function, res.groups())] #try to apply each parse function to its argument
            if len(parsed_result) == 1:
                return parsed_result[0]
            else:
                return parsed_result
        except ValueError:
            print("Parsing Error")
            print("Matched Groups:", res.groups())
            print("Parsing Functions:", parse_function)
            raise ValueError("Stage response to %s ('%s') couldn't be parsed by the supplied function" % (query_string, reply))
    def int_query(self, query_string, **kwargs):
        """Perform a query and return the result(s) as integer(s) (see parsedQuery)"""
        return self.parsed_query(query_string, "%d", **kwargs)
    def float_query(self, query_string, **kwargs):
        """Perform a query and return the result(s) as float(s) (see parsedQuery)"""
        return self.parsed_query(query_string, "%f", **kwargs)

    #@staticmethod  # this was an attempt at making a property factory - now using a descriptor
    #def queried_property(self, get_cmd, set_cmd, dtype='float', docstring=''):
    #    get_func = self.float_query if dtype=='float' else self.query
    #    return property(fget=partial(get_func, get_cmd), fset=self.write, docstring=docstring)


class queried_property(object):
    """A Property interface that reads and writes from the instrument on the bus.
    
    This returns a property-like (i.e. a descriptor) object.  You can use it
    in a class definition just like a property.  The property it creates will
    interact with the instrument over the communication bus to set and retrieve
    its value.
    """
    def __init__(self, get_cmd=None, set_cmd=None, validate=None, valrange=None,
                 fdel=None, doc=None, dtype='float'):
        self.dtype = dtype
        self.get_cmd = get_cmd
        self.set_cmd = set_cmd
        self.validate = validate
        self.valrange = valrange
        self.fdel = fdel
        self.__doc__ = doc

    # TODO: standardise the return (single value only vs parsed result), consider bool
    def __get__(self, obj, objtype=None):
        #print 'get', obj, objtype
        if obj is None:
            return self
        if self.get_cmd is None:
            raise AttributeError("unreadable attribute")
        if self.dtype == 'float':
            getter = obj.float_query
        elif self.dtype == 'int':
            getter = obj.int_query
        else:
            getter = obj.query
        value = getter(self.get_cmd)
        if self.dtype == 'bool':
            value = bool(value)
        return value

    def __set__(self, obj, value):
        #print 'set', obj, value
        if self.set_cmd is None:
            raise AttributeError("can't set attribute")
        if self.validate is not None:
            if value not in self.validate:
                raise ValueError('invalid value supplied - value must be one of {}'.format(self.validate))
        if self.valrange is not None:
            if value < min(self.valrange) or value > max(self.valrange):
                raise ValueError('invalid value supplied - value must be in the range {}-{}'.format(*self.valrange))
        message = self.set_cmd
        if '{0' in message:
            message = message.format(value)
        elif '%' in message:
            message = message % value
        obj.write(message)

    def __delete__(self, obj):
        if self.fdel is None:
            raise AttributeError("can't delete attribute")
        self.fdel(obj)


class queried_channel_property(queried_property):
    # I'm not sure what this does or who uses it.  I assume it's Alan's? --rwb27
    def __init__(self, get_cmd=None, set_cmd=None, validate=None, valrange=None,
                 fdel=None, doc=None, dtype='float'):
        super(queried_channel_property, self).__init__(get_cmd, set_cmd, validate, valrange,
                                                       fdel, doc, dtype)

    def __get__(self, obj, objtype=None):
        assert hasattr(obj, 'ch') and hasattr(obj, 'parent'),\
        'object must have a ch attribute and a parent attribute'
        if obj is None:
            return self
        if self.get_cmd is None:
            raise AttributeError("unreadable attribute")
        if self.dtype == 'float':
            getter = obj.parent.float_query
        elif self.dtype == 'int':
            getter = obj.parent.int_query
        else:
            getter = obj.parent.query
        message = self.get_cmd
        if '{0' in message:
            message = message.format(obj.ch)
        elif '%' in message:
            message = message % obj.ch
        value = getter(message)
        if self.dtype == 'bool':
            value = bool(value)
        return value

    def __set__(self, obj, value):
        assert hasattr(obj, 'ch') and hasattr(obj, 'parent'),\
        'object must have a ch attribute and a parent attribute'
        if self.set_cmd is None:
            raise AttributeError("can't set attribute")
        if self.validate is not None:
            if value not in self.validate:
                raise ValueError('invalid value supplied - value must be one of {}'.format(self.validate))
        if self.valrange is not None:
            if value < min(self.valrange) or value > max(self.valrange):
                raise ValueError('invalid value supplied - value must be in the range {}-{}'.format(*self.valrange))
        message = self.set_cmd
        if '{0' in message:
            message = message.format(obj.ch, value)
        elif '%' in message:
            message = message % (obj.ch, value)
        obj.parent.write(message)


class EchoInstrument(MessageBusInstrument):
    """Trivial test instrument, it simply echoes back what we write."""
    def __init__(self):
        super(EchoInstrument, self).__init__()
        self._last_write = ""
    def write(self, msg):
        self._last_write = msg
    def readline(self, timeout=None):
        return self._last_write


def wrap_with_echo_to_console(obj):
    """Modify an object on-the-fly so all its write and readline calls are echoed to the console"""
    import functools

    obj._debug_echo = True
    obj._original_write = obj.write
    obj._original_readline = obj.readline

    def write(self, q, *args, **kwargs):
        print("Sent: "+str(q))
        return self._original_write(q, *args, **kwargs)
    obj.write = functools.partial(write, obj)

    def readline(self, *args, **kwargs):
        ret = self._original_readline(*args, **kwargs)
        print("Recv: "+str(ret))
        return ret
    obj.readline = functools.partial(readline, obj)


if __name__ == '__main__':
    class DummyInstrument(EchoInstrument):
        x = queried_property('gx', 'sx {0}', dtype='str')

    instr = DummyInstrument()
    print(instr.x)
    instr.x = 'y'
    print(instr.x)
    instr.x = 'x'
    print(instr.x)
